"""Run the covariate ablation: the same windows, with and without extra channels."""

from __future__ import annotations

import argparse
import json

import pandas as pd
from timesfm_lab.bench import RESULTS_DIR
from timesfm_lab.covariates import SETTINGS, paired_arm_test, run_setting
from timesfm_lab.tfm import TimesFMRunner


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    runner = TimesFMRunner(device=args.device)
    rows, meta = [], []
    for setting in SETTINGS:
        out = run_setting(setting, runner, seed=args.seed)
        rows.extend(out["rows"])
        meta.append(
            {
                "setting": setting.key,
                "title": setting.title,
                "note": setting.note,
                "dataset": setting.dataset,
                "n_windows": out["n_windows"],
            }
        )
        print(f"{setting.key}: {out['n_windows']} windows")

    df = pd.DataFrame(rows)
    df.to_parquet(RESULTS_DIR / "covariates.parquet", index=False)

    tests = [paired_arm_test(df, s.key, m) for s in SETTINGS for m in ("mase", "scaled_crps")]
    (RESULTS_DIR / "covariates_meta.json").write_text(
        json.dumps({"settings": meta, "tests": tests}, indent=2), encoding="utf-8"
    )
    print()
    print(pd.DataFrame(tests).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
