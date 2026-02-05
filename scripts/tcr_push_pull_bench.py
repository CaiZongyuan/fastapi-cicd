#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path


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
    image: str
    payload_bytes: int
    ok: bool
    push_sec: float | None
    pull_sec: float | None
    error: str | None = None


def _now_utc_iso() -> str:
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


def _safe_median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def _safe_mean(values: list[float]) -> float | None:
    return float(statistics.mean(values)) if values else None


def _safe_p90(values: list[float]) -> float | None:
    return float(_percentile(values, 90)) if values else None


def _safe_min(values: list[float]) -> float | None:
    return float(min(values)) if values else None


def _safe_max(values: list[float]) -> float | None:
    return float(max(values)) if values else None


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
            if "," in line:
                label, host = [part.strip() for part in line.split(",", 1)]
                targets.append(Target(host=host, label=label or None))
            else:
                targets.append(Target(host=line))

    seen: set[tuple[str, str | None]] = set()
    deduped: list[Target] = []
    for t in targets:
        key = (t.host, t.label)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(t)
    return deduped


def _run(
    args: list[str],
    *,
    input_bytes: bytes | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        args,
        input=input_bytes,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "x"


def _write_random_file(path: Path, size_bytes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    chunk = 1024 * 1024
    remaining = size_bytes
    with path.open("wb") as f:
        while remaining > 0:
            n = min(chunk, remaining)
            f.write(os.urandom(n))
            remaining -= n


def _docker_login(host: str, username: str, password: str) -> None:
    p = _run(
        ["docker", "login", host, "-u", username, "--password-stdin"],
        input_bytes=password.encode("utf-8"),
    )
    if p.returncode != 0:
        out = p.stdout.decode("utf-8", errors="replace")
        raise RuntimeError(f"docker login failed for {host}: {out.strip()}")


def _docker_logout(host: str) -> None:
    _run(["docker", "logout", host])


def _docker_image_rm(image: str) -> None:
    _run(["docker", "image", "rm", "-f", image])


def _time_cmd(args: list[str]) -> tuple[float, str]:
    start = time.perf_counter()
    p = _run(args)
    sec = time.perf_counter() - start
    out = p.stdout.decode("utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(args)}\n{out.strip()}")
    return sec, out


def _build_image(image: str, payload_bytes: int, seed: str) -> None:
    with tempfile.TemporaryDirectory(prefix="tcr-bench-") as td:
        ctx = Path(td)
        dockerfile = ctx / "Dockerfile"
        payload = ctx / "payload.bin"
        marker = ctx / "marker.txt"

        _write_random_file(payload, payload_bytes)
        marker.write_text(seed + "\n", encoding="utf-8")

        dockerfile.write_text(
            "\n".join(
                [
                    "FROM alpine:3.20",
                    "COPY payload.bin /payload.bin",
                    "COPY marker.txt /marker.txt",
                    'CMD ["sh","-c","cat /marker.txt >/dev/null && echo ok"]',
                    "",
                ]
            ),
            encoding="utf-8",
        )

        p = _run(["docker", "build", "-t", image, str(ctx)])
        if p.returncode != 0:
            out = p.stdout.decode("utf-8", errors="replace")
            raise RuntimeError(f"docker build failed for {image}: {out.strip()}")


def _collect_metric(results: list[AttemptResult], name: str) -> list[float]:
    values: list[float] = []
    for r in results:
        if not r.ok:
            continue
        v = getattr(r, name)
        if isinstance(v, (int, float)) and v is not None:
            values.append(float(v))
    return values


def _write_jsonl(path: Path, rows: list[dict]) -> None:
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
        description="Benchmark docker push/pull time across multiple registry hosts (secrets required)."
    )
    p.add_argument("--hosts", action="append", default=[], help="Target host (repeatable)")
    p.add_argument("--hosts-file", type=Path, help="Text file: one host per line, or 'label,host'")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--payload-mb", type=int, default=8, help="Payload size in MB per attempt (default: 8)")
    p.add_argument("--namespace", type=str, default=os.getenv("TCR_NAMESPACE", ""))
    p.add_argument("--repo", type=str, default=os.getenv("TCR_BENCH_REPO", os.getenv("TCR_REPO", "")))
    p.add_argument("--username", type=str, default=os.getenv("TCR_USERNAME", ""))
    p.add_argument("--password", type=str, default=os.getenv("TCR_PASSWORD", ""))
    p.add_argument("--tag-prefix", type=str, default="bench")
    p.add_argument("--run-id", type=str, default=os.getenv("GITHUB_RUN_ID", ""))
    p.add_argument("--out-dir", type=Path, default=Path("tcr-push-pull-out"))
    args = p.parse_args(argv)

    if args.repeats <= 0:
        raise SystemExit("--repeats must be > 0")
    if args.payload_mb <= 0:
        raise SystemExit("--payload-mb must be > 0")
    if not args.namespace:
        raise SystemExit("Missing namespace. Provide --namespace or env TCR_NAMESPACE.")
    if not args.repo:
        raise SystemExit("Missing repo. Provide --repo or env TCR_BENCH_REPO (or TCR_REPO).")
    if not args.username or not args.password:
        raise SystemExit("Missing creds. Provide --username/--password or env TCR_USERNAME/TCR_PASSWORD.")

    if shutil.which("docker") is None:
        raise SystemExit("docker not found in PATH")

    targets = _read_targets(args.hosts, args.hosts_file)
    if not targets:
        raise SystemExit("No targets. Provide --hosts or --hosts-file.")

    run_id = args.run_id.strip() or time.strftime("%Y%m%d%H%M%S", time.gmtime())
    payload_bytes = args.payload_mb * 1024 * 1024
    out_dir: Path = args.out_dir
    raw_path = out_dir / "raw.jsonl"
    summary_csv = out_dir / "summary.csv"
    summary_json = out_dir / "summary.json"

    all_results: list[AttemptResult] = []

    for t in targets:
        label = f"{t.label} " if t.label else ""
        print(f"== {label}{t.host} ==")
        _docker_login(t.host, args.username, args.password)
        try:
            for i in range(1, args.repeats + 1):
                ts = _now_utc_iso()
                tag = f"{args.tag_prefix}-{run_id}-{_slug(t.host)}-{i}"
                image = f"{t.host}/{args.namespace}/{args.repo}:{tag}"
                seed = f"{ts} host={t.host} attempt={i} run_id={run_id}"
                push_sec: float | None = None
                pull_sec: float | None = None
                ok = False
                err: str | None = None

                try:
                    _build_image(image, payload_bytes=payload_bytes, seed=seed)
                    push_sec, _ = _time_cmd(["docker", "push", image])

                    _docker_image_rm(image)
                    pull_sec, _ = _time_cmd(["docker", "pull", image])
                    ok = True
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"
                finally:
                    _docker_image_rm(image)

                r = AttemptResult(
                    ts_utc=ts,
                    host=t.host,
                    label=t.label,
                    attempt=i,
                    image=image,
                    payload_bytes=payload_bytes,
                    ok=ok,
                    push_sec=push_sec,
                    pull_sec=pull_sec,
                    error=err,
                )
                all_results.append(r)

                status = "OK" if ok else "FAIL"
                push_s = f"{push_sec:.3f}s" if push_sec is not None else "-"
                pull_s = f"{pull_sec:.3f}s" if pull_sec is not None else "-"
                print(f"[{status}] #{i} push={push_s} pull={pull_s} payload={args.payload_mb}MB")
                if err:
                    print(f"      error={err}")
        finally:
            _docker_logout(t.host)

    _write_jsonl(raw_path, [asdict(r) for r in all_results])

    by_key: dict[tuple[str, str | None], list[AttemptResult]] = {}
    for r in all_results:
        by_key.setdefault((r.host, r.label), []).append(r)

    summary_rows: list[dict] = []
    for (host, label), rs in by_key.items():
        n_total = len(rs)
        n_ok = sum(1 for r in rs if r.ok)
        row: dict[str, object] = {
            "host": host,
            "label": label or "",
            "payload_mb": args.payload_mb,
            "n_total": n_total,
            "n_ok": n_ok,
            "success_rate": round((n_ok / n_total) if n_total else 0.0, 4),
        }
        for m in ["push_sec", "pull_sec"]:
            vals = _collect_metric(rs, m)
            row[f"{m}_median"] = _safe_median(vals)
            row[f"{m}_mean"] = _safe_mean(vals)
            row[f"{m}_p90"] = _safe_p90(vals)
            row[f"{m}_min"] = _safe_min(vals)
            row[f"{m}_max"] = _safe_max(vals)
        summary_rows.append(row)

    summary_rows.sort(
        key=lambda r: (
            float(r.get("push_sec_median")) if r.get("push_sec_median") is not None else float("inf"),
            float(r.get("pull_sec_median")) if r.get("pull_sec_median") is not None else float("inf"),
            -float(r.get("success_rate") or 0.0),
        )
    )

    _write_summary_csv(summary_csv, summary_rows)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(
        json.dumps(
            {
                "generated_at_utc": _now_utc_iso(),
                "repeats": args.repeats,
                "payload_mb": args.payload_mb,
                "namespace": args.namespace,
                "repo": args.repo,
                "tag_prefix": args.tag_prefix,
                "run_id": run_id,
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
    print(f"Wrote: {raw_path}")
    print(f"Wrote: {summary_csv}")
    print(f"Wrote: {summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

