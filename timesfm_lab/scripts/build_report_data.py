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
from timesfm_lab.bench import ORACLE_KEY, RESULTS_DIR
from timesfm_lab.contamination import load_index
from timesfm_lab.datasets import ALL_SPECS
from timesfm_lab.tfm import MODEL_KEY
from timesfm_lab.tiers import TIER_LABEL, TIER_ORDER, TIER_SHORT, tier_of

ALL_MODELS = [*BASELINE_NAMES, MODEL_KEY]
KEY = ["dataset", "series_id", "cutoff"]
METRICS = ["mase", "smape", "scaled_crps", "coverage_80"]
FIVE = ["naive", "seasonal_naive", "theta", "ets", "fourier_ols"]


def _wide(df: pd.DataFrame, metric: str = "mase") -> pd.DataFrame:
    w = df[df.model != ORACLE_KEY].pivot_table(index=KEY, columns="model", values=metric)
    return w.reset_index()


def main() -> None:
    df = pd.read_parquet(RESULTS_DIR / "results.parquet")
    timings = pd.read_parquet(RESULTS_DIR / "timings.parquet")
    calib = pd.read_parquet(RESULTS_DIR / "calibration.parquet")
    meta = json.loads((RESULTS_DIR / "run_meta.json").read_text())
    index = load_index()

    df = df.assign(tier=df.dataset.map(tier_of))
    scored = df[df.model != ORACLE_KEY]
    sel = selector_table(scored)
    sel["tier"] = sel.dataset.map(tier_of)

    w = _wide(df)
    w["tier"] = w.dataset.map(tier_of)

    def per_dataset(metric: str) -> dict:
        return (
            df.pivot_table(index="dataset", columns="model", values=metric, aggfunc="mean")
            .round(4)
            .to_dict()
        )

    # --- tier gradient, against four different opponents ------------------- #
    gradient = []
    for tier in TIER_ORDER:
        g = w[w.tier == tier]
        s = sel[sel.tier == tier]
        tf = g[MODEL_KEY]
        gradient.append(
            {
                "tier": tier,
                "label": TIER_LABEL[tier],
                "short": TIER_SHORT[tier],
                "n_windows": len(g),
                "datasets": sorted(g.dataset.unique().tolist()),
                "vs_seasonal_naive": float(100 * (1 - (tf / g.seasonal_naive).median())),
                "vs_ets": float(100 * (1 - (tf / g.ets).median())),
                "vs_median_baseline": float(
                    100 * (1 - (tf / g[BASELINE_NAMES].median(axis=1)).median())
                ),
                "vs_best_baseline": float(
                    100 * (1 - (tf / g[BASELINE_NAMES].min(axis=1)).median())
                ),
                "vs_selector": float(100 * (1 - s[MODEL_KEY].mean() / s.walkforward.mean())),
                "selector_win_rate": float((s[MODEL_KEY] < s.walkforward).mean()),
                "timesfm_mean": float(s[MODEL_KEY].mean()),
                "selector_mean": float(s.walkforward.mean()),
            }
        )

    # --- synthetic: distance from the achievable floor --------------------- #
    syn = df[df.tier == "C_synthetic"]
    pm = syn.pivot_table(index="dataset", columns="model", values="mase", aggfunc="mean")
    pc = syn.pivot_table(index="dataset", columns="model", values="scaled_crps", aggfunc="mean")
    bl_m, bl_c = pm[BASELINE_NAMES], pc[BASELINE_NAMES]
    ceiling = []
    for k in pm.index:
        opt, tf = float(pm.loc[k, ORACLE_KEY]), float(pm.loc[k, MODEL_KEY])
        best = float(bl_m.loc[k].min())
        ceiling.append(
            {
                "dataset": k,
                "optimum": opt,
                "timesfm": tf,
                "best_baseline": best,
                "best_baseline_name": str(bl_m.loc[k].idxmin()),
                # "how far above the floor", the only framing that survives a
                # floor of exactly zero and a baseline that ties the floor.
                "timesfm_excess_pct": float(100 * (tf / opt - 1)) if opt > 1e-9 else None,
                "baseline_excess_pct": float(100 * (best / opt - 1)) if opt > 1e-9 else None,
                "optimum_crps": float(pc.loc[k, ORACLE_KEY]),
                "timesfm_crps": float(pc.loc[k, MODEL_KEY]),
                "best_baseline_crps": float(bl_c.loc[k].min()),
                # How much error the best classical method still carries that a
                # perfect forecaster would not, as a share of that method's own
                # error. Zero headroom means the process is already solved and
                # no model of any kind can win — the reading that turns "TimesFM
                # cannot beat classical methods" into a statement about the test.
                "headroom_pct": float(100 * (best - opt) / best) if best > 1e-9 else 0.0,
                # Of that headroom, the share TimesFM actually took.
                "captured_pct": (
                    float(100 * (best - tf) / (best - opt)) if best - opt > 1e-9 else None
                ),
            }
        )

    # --- the oracle is a noise floor: adding weak candidates lowers it ------ #
    public = [s.key for s in ALL_SPECS if tier_of(s.key) in ("A", "B")]
    pub = scored[scored.dataset.isin(public)]
    s5, s7 = selector_table(pub, baselines=FIVE), selector_table(pub)
    oracle_shrink = {
        "n": len(s7),
        "oracle_5": float(s5.oracle.mean()),
        "oracle_7": float(s7.oracle.mean()),
        "selector_5": float(s5.walkforward.mean()),
        "selector_7": float(s7.walkforward.mean()),
        "timesfm": float(s7[MODEL_KEY].mean()),
        "added": ["har", "ewma"],
        "added_mean_mase": {b: float(pub[pub.model == b].mase.mean()) for b in ("har", "ewma")},
    }

    out: dict = {
        "meta": meta,
        "display_names": DISPLAY_NAMES | {ORACLE_KEY: "過程の理論限界"},
        "models": ALL_MODELS,
        "oracle_key": ORACLE_KEY,
        "tier_label": TIER_LABEL,
        "tier_short": TIER_SHORT,
        "tier_order": list(TIER_ORDER),
        "specs": {
            s.key: {
                "title": s.title, "season": s.season, "freq": s.freq_label,
                "context": s.context_length, "horizon": s.horizon, "note": s.note,
                "tier": tier_of(s.key),
                "n_windows": int(scored[(scored.dataset == s.key) & (scored.model == MODEL_KEY)].shape[0]),
                "n_series": int(scored[scored.dataset == s.key].series_id.nunique()),
            }
            for s in ALL_SPECS
        },
        "overall": {
            m: {k: float(scored[scored.model == m][k].mean()) for k in METRICS}
            for m in ALL_MODELS
        },
        "per_dataset": {m: per_dataset(m) for m in METRICS},
        "gradient": gradient,
        "ceiling": ceiling,
        "oracle_shrink": oracle_shrink,
        "head_to_head": head_to_head(sel, ["oracle", "walkforward", *BASELINE_NAMES]).to_dict("records"),
        "selector_skill": selector_skill(sel),
        "selector_per_dataset": [
            {
                "dataset": ds, "n": len(g), "tier": tier_of(ds),
                "timesfm": float(g[MODEL_KEY].mean()),
                "walkforward": float(g.walkforward.mean()),
                "oracle": float(g.oracle.mean()),
                "win_rate": float((g[MODEL_KEY] < g.walkforward).mean()),
            }
            for ds, g in sel.groupby("dataset")
        ],
        "finance_h2h": [],
        "contamination": {
            "index": {
                k: {
                    "gep_name": c.gep_name, "n_series": c.n_series_gep,
                    "checked": c.checked, "identical": c.identical,
                    "min_len": min(c.lengths.values()), "max_len": max(c.lengths.values()),
                }
                for k, c in index.items()
            },
            "tests": [contamination_test(scored, k) for k in index],
            "by_exposure": [
                {"dataset": ds, "exposure": ex, "model": m,
                 "n": int(g.rel.notna().sum()), "median_rel": float(g.rel.median())}
                for (ds, ex, m), g in contamination_table(scored).groupby(["dataset", "exposure", "model"])
                if ds in index and m == MODEL_KEY
            ],
        },
        "calibration": calib.assign(gap=lambda d: d.empirical - d.level).to_dict("records"),
        "timings": [
            {
                "model": m,
                "ms_per_window": float(
                    (timings[timings.model == m].seconds.sum() * 1000)
                    / max(timings[timings.model == m].n_windows.sum(), 1)
                ),
            }
            for m in ALL_MODELS
        ],
    }

    # --- finance: paired tests against every opponent ---------------------- #
    from scipy.stats import wilcoxon

    for ds in [k for k in w.dataset.unique() if tier_of(k) == "C_post_cutoff"]:
        sub = w[w.dataset == ds]
        for b in BASELINE_NAMES:
            x = sub[[MODEL_KEY, b]].dropna()
            out["finance_h2h"].append(
                {
                    "dataset": ds, "opponent": b, "n": len(x),
                    "win_rate": float((x[MODEL_KEY] < x[b]).mean()),
                    "p_value": float(wilcoxon(x[MODEL_KEY], x[b]).pvalue),
                    "timesfm": float(x[MODEL_KEY].mean()), "opponent_mean": float(x[b].mean()),
                }
            )

    # --- covariates: the same windows, with and without extra channels ----- #
    cov_path = RESULTS_DIR / "covariates.parquet"
    if cov_path.exists():
        from timesfm_lab.covariates import SETTINGS as COV_SETTINGS
        from timesfm_lab.covariates import paired_arm_test

        cov = pd.read_parquet(cov_path)
        cmeta = json.loads((RESULTS_DIR / "covariates_meta.json").read_text())
        n_by = {m["setting"]: m["n_windows"] for m in cmeta["settings"]}
        out["covariates"] = [
            {
                "setting": c.key, "title": c.title, "note": c.note,
                "dataset": c.dataset, "n_windows": n_by.get(c.key),
                "n_covariates": int(cov[cov.setting == c.key].n_covariates.iloc[0]),
                "optimum": (
                    float(cov[(cov.setting == c.key) & (cov.arm == ORACLE_KEY)].mase.mean())
                    if (cov.setting == c.key).any()
                    and (cov[cov.setting == c.key].arm == ORACLE_KEY).any()
                    else None
                ),
                **{m: paired_arm_test(cov, c.key, m) for m in ("mase", "scaled_crps")},
            }
            for c in COV_SETTINGS
        ]

    # --- the domain control: same domain, opposite side of the cutoff ------ #
    pair = ("traffic_hourly", "traffic_uk_2026")
    if set(pair) <= set(sel.dataset.unique()):
        out["domain_control"] = [
            {
                "dataset": ds, "tier": tier_of(ds),
                "n": len(g), "n_series": int(g.series_id.nunique()),
                "timesfm": float(g[MODEL_KEY].mean()),
                "walkforward": float(g.walkforward.mean()),
                "oracle": float(g.oracle.mean()),
                "vs_selector_pct": float(100 * (1 - g[MODEL_KEY].mean() / g.walkforward.mean())),
                "win_rate": float((g[MODEL_KEY] < g.walkforward).mean()),
            }
            for ds in pair
            for g in [sel[sel.dataset == ds]]
        ]

    rank_mase = scored.groupby("model").mase.mean().rank()
    rank_smape = scored.groupby("model").smape.mean().rank()
    out["metric_disagreement"] = {
        m: {"mase_rank": int(rank_mase[m]), "smape_rank": int(rank_smape[m])} for m in ALL_MODELS
    }

    path = RESULTS_DIR / "report_data.json"
    path.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"wrote {path} ({path.stat().st_size/1024:.0f} KB)")
    print(pd.DataFrame(gradient)[["short", "n_windows", "vs_selector", "selector_win_rate"]].round(3).to_string(index=False))
    print(pd.DataFrame(ceiling)[["dataset", "optimum", "best_baseline", "timesfm", "headroom_pct", "captured_pct"]].round(2).to_string(index=False))
    print(json.dumps(oracle_shrink, indent=1, default=float))


if __name__ == "__main__":
    main()
