#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _as_float(v: str) -> float | None:
    v = (v or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Plot TCR speed test summary CSV.")
    p.add_argument("--summary-csv", type=Path, default=Path("tcr-speed-test-out/summary.csv"))
    p.add_argument("--out", type=Path, default=Path("tcr-speed-test-out/plot.png"))
    p.add_argument(
        "--metric",
        type=str,
        default="end_to_end_ms_median",
        help="CSV column to plot (e.g. end_to_end_ms_median, tls_ms_median)",
    )
    p.add_argument("--top", type=int, default=0, help="Plot only top-N fastest (0=all)")
    args = p.parse_args(argv)

    rows = _read_rows(args.summary_csv)
    if not rows:
        raise SystemExit(f"Empty CSV: {args.summary_csv}")

    # Filter rows that have metric values and non-zero success
    filtered: list[dict[str, str]] = []
    for r in rows:
        sr = _as_float(r.get("success_rate", "0")) or 0.0
        mv = _as_float(r.get(args.metric, ""))
        if sr <= 0.0 or mv is None:
            continue
        filtered.append(r)

    filtered.sort(key=lambda r: _as_float(r.get(args.metric, "")) or 1e18)
    if args.top and args.top > 0:
        filtered = filtered[: args.top]

    labels: list[str] = []
    values: list[float] = []
    success: list[float] = []
    for r in filtered:
        host = (r.get("host") or "").strip()
        label = (r.get("label") or "").strip()
        name = f"{label} {host}".strip()
        v = _as_float(r.get(args.metric, "")) or 0.0
        labels.append(name)
        values.append(v)
        success.append(_as_float(r.get("success_rate", "0")) or 0.0)

    try:
        import matplotlib.pyplot as plt
    except Exception as e:  # pragma: no cover
        raise SystemExit(
            "matplotlib is required for plotting. Install it first, e.g.\n"
            "  python -m pip install matplotlib\n"
            f"Error: {e}"
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig_h = max(4.0, 0.35 * len(labels) + 1.5)
    fig, ax = plt.subplots(figsize=(10, fig_h))
    y = list(range(len(labels)))
    ax.barh(y, values)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel(f"{args.metric} (ms)")
    ax.set_title("GitHub Runner → TCR endpoints")

    # Annotate success rates.
    for i, (v, sr) in enumerate(zip(values, success)):
        ax.text(v, i, f"  {v:.1f}ms, ok={sr*100:.0f}%", va="center", ha="left", fontsize=9)

    fig.tight_layout()
    fig.savefig(args.out, dpi=160)
    print(f"Wrote: {args.out}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))

