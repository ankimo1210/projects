"""Collapse the raw window scores into the exact figures the report prints."""

from __future__ import annotations

import json

import pandas as pd
from timesfm_lab.analysis import (
    BASELINE_NAMES,
    contamination_table,
    contamination_test,
    head_to_head,
    selector_skill,
    selector_table,
)
from timesfm_lab.baselines import DISPLAY_NAMES
from timesfm_lab.bench import RESULTS_DIR
from timesfm_lab.contamination import load_index
from timesfm_lab.datasets import SPECS
from timesfm_lab.tfm import MODEL_KEY

ALL_MODELS = [*BASELINE_NAMES, MODEL_KEY]


def main() -> None:
    df = pd.read_parquet(RESULTS_DIR / "results.parquet")
    timings = pd.read_parquet(RESULTS_DIR / "timings.parquet")
    horizon = pd.read_parquet(RESULTS_DIR / "horizon_profile.parquet")
    calib = pd.read_parquet(RESULTS_DIR / "calibration.parquet")
    meta = json.loads((RESULTS_DIR / "run_meta.json").read_text())
    index = load_index()

    sel = selector_table(df)
    out: dict = {
        "meta": meta,
        "display_names": DISPLAY_NAMES,
        "models": ALL_MODELS,
        "specs": {
            s.key: {
                "title": s.title, "season": s.season, "freq": s.freq_label,
                "context": s.context_length, "horizon": s.horizon, "note": s.note,
                "n_windows": int(df[(df.dataset == s.key) & (df.model == MODEL_KEY)].shape[0]),
                "n_series": int(df[df.dataset == s.key].series_id.nunique()),
                "in_corpus": s.key in index,
            }
            for s in SPECS
        },
        "overall": {
            m: {
                k: float(df[df.model == m][k].mean())
                for k in ["mase", "smape", "scaled_crps", "coverage_80"]
            }
            for m in ALL_MODELS
        },
        "per_dataset": {
            metric: df.pivot_table(index="dataset", columns="model", values=metric, aggfunc="mean")
            .round(4).to_dict()
            for metric in ["mase", "scaled_crps", "smape", "coverage_80"]
        },
        "head_to_head": head_to_head(sel, ["oracle", "walkforward", *BASELINE_NAMES]).to_dict("records"),
        "selector_skill": selector_skill(sel),
        "selector_per_dataset": [
            {
                "dataset": ds, "n": len(g),
                "timesfm": float(g[MODEL_KEY].mean()),
                "walkforward": float(g.walkforward.mean()),
                "oracle": float(g.oracle.mean()),
                "win_rate": float((g[MODEL_KEY] < g.walkforward).mean()),
            }
            for ds, g in sel.groupby("dataset")
        ],
        "contamination": {
            "index": {
                k: {
                    "gep_name": c.gep_name, "n_series": c.n_series_gep,
                    "checked": c.checked, "identical": c.identical,
                    "min_len": min(c.lengths.values()), "max_len": max(c.lengths.values()),
                }
                for k, c in index.items()
            },
            "tests": [contamination_test(df, k) for k in index],
            "by_exposure": [
                {
                    "dataset": ds, "exposure": ex, "model": m, "n": int(g.rel.notna().sum()),
                    "median_rel": float(g.rel.median()),
                }
                for (ds, ex, m), g in contamination_table(df).groupby(["dataset", "exposure", "model"])
                if ds in index
            ],
        },
        "horizon": horizon.to_dict("records"),
        "calibration": calib.assign(gap=lambda d: d.empirical - d.level).to_dict("records"),
        "timings": [
            {
                "model": m,
                "ms_per_window": float(
                    (timings[timings.model == m].seconds.sum() * 1000)
                    / timings[timings.model == m].n_windows.sum()
                ),
                "total_seconds": float(timings[timings.model == m].seconds.sum()),
            }
            for m in ALL_MODELS
        ],
    }

    # sMAPE vs MASE disagreement: the rank a metric choice buys you.
    rank_mase = df.groupby("model").mase.mean().rank()
    rank_smape = df.groupby("model").smape.mean().rank()
    out["metric_disagreement"] = {
        m: {"mase_rank": int(rank_mase[m]), "smape_rank": int(rank_smape[m])} for m in ALL_MODELS
    }

    path = RESULTS_DIR / "report_data.json"
    path.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"wrote {path} ({path.stat().st_size/1024:.0f} KB)")
    print(json.dumps(out["selector_skill"], indent=1))
    print(json.dumps(out["contamination"]["tests"], indent=1))
    print(pd.DataFrame(out["head_to_head"]).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
