"""Turning the raw window scores into the claims the report makes.

Two of these deserve care, because they are where a benchmark most easily lies
to itself:

``selector_table`` separates the *oracle* best-of-N baseline from a selector
that could actually have been run at the time.  Taking a per-window minimum over
five noisy estimates is not a method, it is a lower bound on the noise; quoting
it as "the best classical model" makes every foundation model look worse than it
is.

``contamination_table`` splits windows by whether the held-out target is inside
the pretraining corpus, and compares each model's *relative* error so that the
comparison is not confounded by covered windows simply being older.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .baselines import BASELINES
from .tfm import MODEL_KEY

BASELINE_NAMES = list(BASELINES)
KEY = ["dataset", "series_id", "cutoff"]


def wide(df: pd.DataFrame, metric: str = "mase") -> pd.DataFrame:
    """One row per evaluation window, one column per model."""
    return df.pivot_table(index=KEY, columns="model", values=metric).reset_index()


def selector_table(df: pd.DataFrame, metric: str = "mase") -> pd.DataFrame:
    """Per-window scores for the oracle and for a walk-forward baseline selector.

    The walk-forward selector uses the baseline that won the *previous*
    (older, non-overlapping) window of the same series — information that was
    genuinely available before the forecast was made.  The first window of each
    series has no predecessor and is dropped.
    """
    w = wide(df, metric).sort_values(KEY)
    rows: list[dict] = []
    for (dataset, series_id), g in w.groupby(["dataset", "series_id"], sort=False):
        g = g.sort_values("cutoff")
        prev_best: str | None = None
        for _, r in g.iterrows():
            avail = r[BASELINE_NAMES].astype(float)
            if prev_best is not None and np.isfinite(avail).any():
                rows.append(
                    {
                        "dataset": dataset,
                        "series_id": series_id,
                        "cutoff": int(r["cutoff"]),
                        "picked": prev_best,
                        "walkforward": float(r[prev_best]),
                        "oracle": float(avail.min()),
                        "oracle_pick": str(avail.idxmin()),
                        MODEL_KEY: float(r[MODEL_KEY]),
                        **{b: float(r[b]) for b in BASELINE_NAMES},
                    }
                )
            if np.isfinite(avail).any():
                prev_best = str(avail.idxmin())
    return pd.DataFrame(rows)


def head_to_head(sel: pd.DataFrame, opponents: list[str], metric_name: str = "MASE") -> pd.DataFrame:
    """TimesFM against each opponent column, paired on the window."""
    from scipy.stats import wilcoxon

    out = []
    for opp in opponents:
        d = sel[[MODEL_KEY, opp]].dropna()
        if d.empty:
            continue
        try:
            p = float(wilcoxon(d[MODEL_KEY], d[opp]).pvalue)
        except ValueError:
            p = float("nan")
        out.append(
            {
                "opponent": opp,
                "n": len(d),
                "opponent_mean": float(d[opp].mean()),
                "timesfm_mean": float(d[MODEL_KEY].mean()),
                "timesfm_win_rate": float((d[MODEL_KEY] < d[opp]).mean()),
                "p_value": p,
                "metric": metric_name,
            }
        )
    return pd.DataFrame(out)


def selector_skill(sel: pd.DataFrame) -> dict:
    """How much of the oracle's advantage a real selector can actually capture."""
    match = float((sel.picked == sel.oracle_pick).mean())
    chance = 1.0 / len(BASELINE_NAMES)
    oracle, wf = float(sel.oracle.mean()), float(sel.walkforward.mean())
    tfm = float(sel[MODEL_KEY].mean())
    return {
        "n": len(sel),
        "match_rate": match,
        "chance_rate": chance,
        "oracle_mean": oracle,
        "walkforward_mean": wf,
        "timesfm_mean": tfm,
        # Share of the oracle-to-walkforward gap that TimesFM closes.
        "gap_closed": (wf - tfm) / (wf - oracle) if wf > oracle else float("nan"),
    }


def contamination_table(df: pd.DataFrame, metric: str = "mase") -> pd.DataFrame:
    """Relative error of each model by pretraining exposure.

    ``rel`` is a model's error divided by the *median baseline* error on the same
    window, which removes the window-difficulty confound: covered windows are
    systematically older than uncovered ones, and older windows are not equally
    hard.
    """
    w = wide(df, metric)
    exposure = (
        df.drop_duplicates(KEY).set_index(KEY)["exposure"].rename("exposure")
    )
    w = w.set_index(KEY).join(exposure).reset_index()
    med = w[BASELINE_NAMES].median(axis=1)
    rows = []
    for model in [*BASELINE_NAMES, MODEL_KEY]:
        rel = w[model] / med.replace(0.0, np.nan)
        rows.append(
            pd.DataFrame(
                {"dataset": w.dataset, "exposure": w.exposure, "model": model, "rel": rel}
            )
        )
    return pd.concat(rows, ignore_index=True)


def contamination_test(df: pd.DataFrame, dataset: str, metric: str = "mase") -> dict:
    """Is TimesFM relatively better on windows its pretraining corpus contains?

    One-sided Mann-Whitney: contamination would show up as a *smaller* relative
    error on the ``in corpus`` side.  A null result here is the interesting one —
    it says a win on this dataset is not explained by memorisation.
    """
    from scipy.stats import mannwhitneyu

    tab = contamination_table(df, metric)
    t = tab[(tab.dataset == dataset) & (tab.model == MODEL_KEY)]
    a = t[t.exposure == "in corpus"].rel.dropna()
    b = t[t.exposure == "past corpus"].rel.dropna()
    if len(a) < 5 or len(b) < 5:
        return {"dataset": dataset, "n_in": len(a), "n_past": len(b), "p_value": float("nan")}
    u = mannwhitneyu(a, b, alternative="less")
    return {
        "dataset": dataset,
        "n_in": len(a),
        "n_past": len(b),
        "median_in": float(np.median(a)),
        "median_past": float(np.median(b)),
        "u": float(u.statistic),
        "p_value": float(u.pvalue),
    }
