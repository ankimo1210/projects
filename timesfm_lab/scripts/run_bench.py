"""Run the full rolling-origin benchmark and write the long-format results."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import time
from datetime import UTC, datetime
from importlib.metadata import version

from timesfm_lab.bench import RESULTS_DIR, run_all
from timesfm_lab.datasets import SPECS


def provenance() -> dict:
    import torch

    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        commit = "unknown"
    return {
        "run_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": commit,
        "timesfm_version": version("timesfm"),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "python": platform.python_version(),
        "statsmodels": version("statsmodels"),
        "numpy": version("numpy"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="*", default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--no-timesfm", action="store_true")
    args = ap.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    df, timings, step_df, pit_df = run_all(
        dataset_keys=args.datasets,
        seed=args.seed,
        use_timesfm=not args.no_timesfm,
        device=args.device,
    )
    wall = time.time() - t0

    df.to_parquet(RESULTS_DIR / "results.parquet", index=False)
    timings.to_parquet(RESULTS_DIR / "timings.parquet", index=False)
    step_df.to_parquet(RESULTS_DIR / "horizon_profile.parquet", index=False)
    pit_df.to_parquet(RESULTS_DIR / "calibration.parquet", index=False)
    meta = provenance() | {
        "wall_seconds": round(wall, 1),
        "seed": args.seed,
        "n_rows": len(df),
        "specs": [
            {
                "key": s.key, "title": s.title, "season": s.season, "freq": s.freq_label,
                "context_length": s.context_length, "horizon": s.horizon,
                "n_series": s.n_series, "n_windows": s.n_windows, "note": s.note,
            }
            for s in SPECS
            if args.datasets is None or s.key in args.datasets
        ],
    }
    (RESULTS_DIR / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"\nwall {wall:.1f}s, {len(df)} rows -> {RESULTS_DIR}")
    print(df.groupby("model")[["mase", "smape", "scaled_crps", "coverage_80"]].mean().round(3).to_string())
    fb = df[df.fallback != ""].groupby(["model", "fallback"]).size()
    if len(fb):
        print("\nfallbacks:")
        print(fb.to_string())


if __name__ == "__main__":
    main()
