#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import socket
import ssl
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Target:
    host: str
    label: str | None = None


@dataclass
class AttemptResult:
    ts_utc: str
    host: str
    label: str | None
    attempt: int
    ip: str | None
    port: int
    path: str
    ok: bool
    status_code: int | None
    dns_ms: float | None
    tcp_ms: float | None
    tls_ms: float | None
    ttfb_ms: float | None
    http_total_ms: float | None
    end_to_end_ms: float | None
    error: str | None = None


def _now_utc_iso() -> str:
    # Keep it simple and stable (no timezone dependency).
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _percentile(values: list[float], p: float) -> float:
    if not values:
        raise ValueError("values is empty")
    if p <= 0:
        return min(values)
    if p >= 100:
        return max(values)
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(values_sorted) - 1)
    if f == c:
        return values_sorted[f]
    d0 = values_sorted[f] * (c - k)
    d1 = values_sorted[c] * (k - f)
    return d0 + d1


def _read_targets(hosts: list[str], hosts_file: Path | None) -> list[Target]:
    targets: list[Target] = []
    for host in hosts:
        host = host.strip()
        if not host:
            continue
        targets.append(Target(host=host))

    if hosts_file is not None:
        for raw in hosts_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # Support "label,host" or just "host"
            if "," in line:
                label, host = [part.strip() for part in line.split(",", 1)]
                targets.append(Target(host=host, label=label or None))
            else:
                targets.append(Target(host=line))

    # De-dup while preserving order (host+label).
    seen: set[tuple[str, str | None]] = set()
    deduped: list[Target] = []
    for t in targets:
        key = (t.host, t.label)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(t)
    return deduped


def _resolve(host: str, port: int, timeout_s: float) -> tuple[list[str], float]:
    start = time.perf_counter()
    # Python doesn't provide a direct per-call DNS timeout. This timeout is best-effort:
    # we set the default socket timeout for the duration of the call.
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout_s)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    finally:
        socket.setdefaulttimeout(old_timeout)
    ips: list[str] = []
    for family, _socktype, _proto, _canonname, sockaddr in infos:
        if family == socket.AF_INET:
            ips.append(sockaddr[0])
        elif family == socket.AF_INET6:
            ips.append(sockaddr[0])
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    # De-dup IPs while preserving order.
    seen: set[str] = set()
    ips_deduped: list[str] = []
    for ip in ips:
        if ip in seen:
            continue
        seen.add(ip)
        ips_deduped.append(ip)
    return ips_deduped, elapsed_ms


def _connect_tcp(ip: str, port: int, timeout_s: float) -> tuple[socket.socket, float]:
    start = time.perf_counter()
    sock = socket.create_connection((ip, port), timeout=timeout_s)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return sock, elapsed_ms


def _handshake_tls(
    sock: socket.socket,
    server_hostname: str,
    timeout_s: float,
    insecure: bool,
) -> tuple[ssl.SSLSocket, float]:
    if insecure:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        ctx = ssl.create_default_context()
    start = time.perf_counter()
    tls_sock = ctx.wrap_socket(sock, server_hostname=server_hostname)
    tls_sock.settimeout(timeout_s)
    tls_sock.do_handshake()
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return tls_sock, elapsed_ms


def _http_get_v2(
    tls_sock: ssl.SSLSocket,
    host: str,
    path: str,
    timeout_s: float,
) -> tuple[int | None, float, float, int]:
    tls_sock.settimeout(timeout_s)
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "User-Agent: tcr-speed-test/1.0\r\n"
        "Accept: */*\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("utf-8")

    start = time.perf_counter()
    tls_sock.sendall(req)

    first_byte: bytes
    try:
        first_byte = tls_sock.recv(1)
    except socket.timeout:
        raise TimeoutError("timeout waiting first byte") from None
    if not first_byte:
        raise ConnectionError("connection closed before first byte")
    ttfb_ms = (time.perf_counter() - start) * 1000.0

    buf = bytearray(first_byte)
    while b"\r\n" not in buf:
        chunk = tls_sock.recv(1024)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > 64 * 1024:
            break

    status_code: int | None = None
    try:
        line = bytes(buf).split(b"\r\n", 1)[0].decode("iso-8859-1", errors="replace")
        parts = line.split()
        if len(parts) >= 2:
            status_code = int(parts[1])
    except Exception:
        status_code = None

    total_bytes = len(buf)
    while True:
        chunk = tls_sock.recv(64 * 1024)
        if not chunk:
            break
        total_bytes += len(chunk)
    http_total_ms = (time.perf_counter() - start) * 1000.0
    return status_code, ttfb_ms, http_total_ms, total_bytes


def run_attempt(
    target: Target,
    attempt: int,
    *,
    port: int,
    path: str,
    timeout_s: float,
    insecure: bool,
) -> AttemptResult:
    ts = _now_utc_iso()
    ip: str | None = None
    dns_ms: float | None = None
    tcp_ms: float | None = None
    tls_ms: float | None = None
    ttfb_ms: float | None = None
    http_total_ms: float | None = None
    end_to_end_ms: float | None = None
    status_code: int | None = None

    overall_start = time.perf_counter()
    try:
        ips, dns_ms = _resolve(target.host, port, timeout_s)
        if not ips:
            raise RuntimeError("no IPs resolved")
        ip = ips[0]

        sock, tcp_ms = _connect_tcp(ip, port, timeout_s)
        try:
            tls_sock, tls_ms = _handshake_tls(
                sock,
                server_hostname=target.host,
                timeout_s=timeout_s,
                insecure=insecure,
            )
        except Exception:
            sock.close()
            raise

        try:
            status_code, ttfb_ms, http_total_ms, _bytes = _http_get_v2(
                tls_sock,
                host=target.host,
                path=path,
                timeout_s=timeout_s,
            )
        finally:
            try:
                tls_sock.close()
            except Exception:
                pass

        end_to_end_ms = (time.perf_counter() - overall_start) * 1000.0
        ok = True
        err = None
    except Exception as e:
        ok = False
        err = f"{type(e).__name__}: {e}"
        end_to_end_ms = (time.perf_counter() - overall_start) * 1000.0

    return AttemptResult(
        ts_utc=ts,
        host=target.host,
        label=target.label,
        attempt=attempt,
        ip=ip,
        port=port,
        path=path,
        ok=ok,
        status_code=status_code,
        dns_ms=dns_ms,
        tcp_ms=tcp_ms,
        tls_ms=tls_ms,
        ttfb_ms=ttfb_ms,
        http_total_ms=http_total_ms,
        end_to_end_ms=end_to_end_ms,
        error=err,
    )


def _safe_median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def _safe_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.mean(values))


def _safe_p90(values: list[float]) -> float | None:
    if not values:
        return None
    return float(_percentile(values, 90))


def _safe_min(values: list[float]) -> float | None:
    if not values:
        return None
    return float(min(values))


def _safe_max(values: list[float]) -> float | None:
    if not values:
        return None
    return float(max(values))


def _collect_metric(results: list[AttemptResult], name: str) -> list[float]:
    values: list[float] = []
    for r in results:
        if not r.ok:
            continue
        v = getattr(r, name)
        if isinstance(v, (int, float)) and v is not None:
            values.append(float(v))
    return values


def _write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_summary_csv(path: Path, summary_rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not summary_rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in summary_rows:
        for k in row.keys():
            if k not in fieldnames:
                fieldnames.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in summary_rows:
            w.writerow(row)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        description="Measure GitHub runner -> registry host link quality via /v2/ (DNS/TCP/TLS/TTFB/Total)."
    )
    p.add_argument("--hosts", action="append", default=[], help="Target host (repeatable)")
    p.add_argument("--hosts-file", type=Path, help="Text file: one host per line, or 'label,host'")
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--timeout", type=float, default=5.0, help="Per-step timeout seconds")
    p.add_argument("--port", type=int, default=443)
    p.add_argument("--path", type=str, default="/v2/")
    p.add_argument("--insecure", action="store_true", help="Skip TLS verification (NOT recommended)")
    p.add_argument("--out-jsonl", type=Path, default=Path("tcr-speed-test-out/raw.jsonl"))
    p.add_argument("--out-summary-csv", type=Path, default=Path("tcr-speed-test-out/summary.csv"))
    p.add_argument("--out-summary-json", type=Path, default=Path("tcr-speed-test-out/summary.json"))
    args = p.parse_args(argv)

    if args.repeats <= 0:
        raise SystemExit("--repeats must be > 0")

    targets = _read_targets(args.hosts, args.hosts_file)
    if not targets:
        raise SystemExit("No targets. Provide --hosts or --hosts-file.")

    all_results: list[AttemptResult] = []
    for t in targets:
        for i in range(1, args.repeats + 1):
            r = run_attempt(
                t,
                i,
                port=args.port,
                path=args.path,
                timeout_s=args.timeout,
                insecure=args.insecure,
            )
            all_results.append(r)
            status = r.status_code if r.status_code is not None else "NA"
            ok = "OK" if r.ok else "FAIL"
            label = f"{t.label} " if t.label else ""
            print(
                f"[{ok}] {label}{t.host} #{i} ip={r.ip or '-'} "
                f"dns={r.dns_ms or 0:.1f}ms tcp={r.tcp_ms or 0:.1f}ms tls={r.tls_ms or 0:.1f}ms "
                f"ttfb={r.ttfb_ms or 0:.1f}ms total={r.http_total_ms or 0:.1f}ms status={status}"
            )
            if r.error:
                print(f"      error={r.error}")

    _write_jsonl(args.out_jsonl, [asdict(r) for r in all_results])

    # Summary per (host,label)
    summary_rows: list[dict] = []
    by_key: dict[tuple[str, str | None], list[AttemptResult]] = {}
    for r in all_results:
        by_key.setdefault((r.host, r.label), []).append(r)

    metric_names = ["dns_ms", "tcp_ms", "tls_ms", "ttfb_ms", "http_total_ms", "end_to_end_ms"]
    for (host, label), rs in by_key.items():
        n_total = len(rs)
        n_ok = sum(1 for r in rs if r.ok)
        row: dict[str, object] = {
            "host": host,
            "label": label or "",
            "n_total": n_total,
            "n_ok": n_ok,
            "success_rate": round((n_ok / n_total) if n_total else 0.0, 4),
        }
        for m in metric_names:
            vals = _collect_metric(rs, m)
            row[f"{m}_median"] = _safe_median(vals)
            row[f"{m}_mean"] = _safe_mean(vals)
            row[f"{m}_p90"] = _safe_p90(vals)
            row[f"{m}_min"] = _safe_min(vals)
            row[f"{m}_max"] = _safe_max(vals)
        summary_rows.append(row)

    # Sort by end_to_end median then success desc
    def _sort_key(r: dict) -> tuple[float, float]:
        v = r.get("end_to_end_ms_median")
        end = float(v) if isinstance(v, (int, float)) and v is not None else float("inf")
        success = float(r.get("success_rate") or 0.0)
        return (end, -success)

    summary_rows.sort(key=_sort_key)

    _write_summary_csv(args.out_summary_csv, summary_rows)
    args.out_summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_summary_json.write_text(
        json.dumps(
            {
                "generated_at_utc": _now_utc_iso(),
                "repeats": args.repeats,
                "timeout_s": args.timeout,
                "port": args.port,
                "path": args.path,
                "insecure": args.insecure,
                "targets": [asdict(t) for t in targets],
                "summary": summary_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(f"Wrote: {args.out_jsonl}")
    print(f"Wrote: {args.out_summary_csv}")
    print(f"Wrote: {args.out_summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

