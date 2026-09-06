"""Rolling-origin backtest: score every model on every window, write one table.

The output is deliberately long-format (one row per window x model) rather than
pre-aggregated.  Aggregation choices — mean vs median MASE, per-series vs
per-window weighting — change which model "wins", so they belong in the report
where they can be shown side by side, not baked into the run.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import metrics
from .baselines import BASELINES, QUANTILE_LEVELS, Forecast
from .datasets import SPECS, DatasetSpec, Window, build_windows
from .tfm import MODEL_KEY, TimesFMRunner

RESULTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def score(window: Window, fc: Forecast) -> dict[str, float]:
    """All metrics for one (window, model) pair, scaled by the *context* only."""
    s_mae = metrics.seasonal_scale_mae(window.context, window.season)
    s_mse = metrics.seasonal_scale_mse(window.context, window.season)
    return {
        "mae": metrics.mae(window.actual, fc.point),
        "mase": metrics.mase(window.actual, fc.point, s_mae),
        "rmsse": metrics.rmsse(window.actual, fc.point, s_mse),
        "smape": metrics.smape(window.actual, fc.point),
        "scaled_crps": metrics.scaled_crps(
            window.actual, fc.quantiles, QUANTILE_LEVELS, s_mae
        ),
        "coverage_80": float(
            ((window.actual >= fc.quantiles[:, 0]) & (window.actual <= fc.quantiles[:, 8])).mean()
        ),
    }


class _Diagnostics:
    """Accumulates the two diagnostics that a per-window summary throws away.

    ``step`` is the scaled absolute error at each horizon index — it shows where
    an advantage lives (the first hours or the last), which a horizon-averaged
    MASE hides.  ``pit`` is the empirical hit rate below each predicted quantile;
    a calibrated fan puts it on the 45-degree line, and the *sign* of the
    departure says whether the intervals are too narrow or too wide.
    """

    def __init__(self) -> None:
        self.step: dict[tuple[str, str], np.ndarray] = {}
        self.pit: dict[tuple[str, str], np.ndarray] = {}
        self.n: dict[tuple[str, str], int] = {}

    def add(self, dataset: str, model: str, window: Window, fc: Forecast) -> None:
        key = (dataset, model)
        scale = metrics.seasonal_scale_mae(window.context, window.season)
        if not np.isfinite(scale):
            return
        err = np.abs(window.actual - fc.point) / scale
        a = window.actual[:, None]
        hit = ((a < fc.quantiles) + 0.5 * (a == fc.quantiles)).mean(axis=0)
        if key not in self.step:
            self.step[key] = np.zeros_like(err)
            self.pit[key] = np.zeros_like(hit)
            self.n[key] = 0
        self.step[key] += err
        self.pit[key] += hit
        self.n[key] += 1

    def frames(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        step_rows, pit_rows = [], []
        for (dataset, model), tot in self.step.items():
            n = self.n[(dataset, model)]
            for h, v in enumerate(tot / n, start=1):
                step_rows.append(
                    {"dataset": dataset, "model": model, "step": h, "scaled_abs_error": float(v)}
                )
            for lvl, v in zip(QUANTILE_LEVELS, self.pit[(dataset, model)] / n, strict=True):
                pit_rows.append(
                    {"dataset": dataset, "model": model, "level": float(lvl), "empirical": float(v)}
                )
        return pd.DataFrame(step_rows), pd.DataFrame(pit_rows)


def run_dataset(
    spec: DatasetSpec,
    runner: TimesFMRunner | None,
    seed: int = 0,
    diag: _Diagnostics | None = None,
) -> tuple[pd.DataFrame, dict[str, float]]:
    windows = build_windows(spec, seed=seed)
    rows: list[dict] = []
    timings: dict[str, float] = {}

    def record(model: str, w: Window, fc: Forecast) -> None:
        rows.append(
            {
                "dataset": spec.key,
                "series_id": w.series_id,
                "cutoff": w.cutoff,
                "model": model,
                "fallback": fc.fallback,
                **score(w, fc),
            }
        )
        if diag is not None:
            diag.add(spec.key, model, w, fc)

    for name, fn in BASELINES.items():
        t0 = time.time()
        for w in windows:
            record(name, w, fn(w.context, spec.horizon, spec.season))
        timings[name] = time.time() - t0

    if runner is not None:
        forecasts, elapsed = runner.predict([w.context for w in windows], spec.horizon)
        timings[MODEL_KEY] = elapsed
        for w, fc in zip(windows, forecasts, strict=True):
            record(MODEL_KEY, w, fc)

    df = pd.DataFrame(rows)
    timings["_n_windows"] = float(len(windows))
    return df, timings


def run_all(
    dataset_keys: list[str] | None = None,
    seed: int = 0,
    use_timesfm: bool = True,
    device: str = "cuda",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    specs = [s for s in SPECS if dataset_keys is None or s.key in dataset_keys]
    runner = TimesFMRunner(device=device) if use_timesfm else None
    if runner is not None:
        print(f"TimesFM loaded in {runner.load_seconds:.1f}s")

    diag = _Diagnostics()
    frames, timing_rows = [], []
    for spec in specs:
        t0 = time.time()
        df, timings = run_dataset(spec, runner, seed=seed, diag=diag)
        frames.append(df)
        n = int(timings.pop("_n_windows"))
        for model, secs in timings.items():
            timing_rows.append(
                {
                    "dataset": spec.key,
                    "model": model,
                    "seconds": secs,
                    "n_windows": n,
                    "ms_per_window": 1000.0 * secs / max(n, 1),
                }
            )
        print(f"{spec.key:22s} {n:4d} windows  {time.time()-t0:6.1f}s")
    step_df, pit_df = diag.frames()
    return pd.concat(frames, ignore_index=True), pd.DataFrame(timing_rows), step_df, pit_df


def paired_win_rate(df: pd.DataFrame, model: str, other: str, metric: str = "mase") -> dict:
    """Window-by-window comparison of two models, plus a Wilcoxon signed-rank p.

    Paired on the *window*, because the windows differ enormously in difficulty;
    an unpaired comparison of mean MASE is dominated by which series happened to
    be sampled, not by which model is better.
    """
    from scipy.stats import wilcoxon

    a = df[df.model == model].set_index(["dataset", "series_id", "cutoff"])[metric]
    b = df[df.model == other].set_index(["dataset", "series_id", "cutoff"])[metric]
    joined = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if joined.empty:
        return {"n": 0, "win_rate": float("nan"), "p_value": float("nan"), "median_ratio": float("nan")}
    wins = float((joined.a < joined.b).mean())
    try:
        p = float(wilcoxon(joined.a, joined.b).pvalue)
    except ValueError:
        p = float("nan")
    return {
        "n": len(joined),
        "win_rate": wins,
        "p_value": p,
        "median_ratio": float(np.median(joined.a / joined.b.replace(0, np.nan))),
    }


def attach_contamination(df: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    """Add ``covered`` / ``exposure`` columns saying whether a window was pretrained on.

    Rejoined after the fact rather than computed in the loop, so a benchmark run
    stays valid even when the contamination index has not been built.
    """
    from .contamination import covered_fraction, label, load_index

    index = load_index()
    if not index:
        df = df.copy()
        df["covered"] = np.nan
        df["exposure"] = "unknown"
        return df

    frac: dict[tuple[str, str, int], float] = {}
    for spec in SPECS:
        if spec.key not in index:
            continue
        for w in build_windows(spec, seed=seed):
            frac[(w.dataset, w.series_id, w.cutoff)] = covered_fraction(w, index)

    keys = list(zip(df.dataset, df.series_id, df.cutoff, strict=True))
    out = df.copy()
    out["covered"] = [frac.get(k, float("nan")) for k in keys]
    out["exposure"] = [label(v) for v in out["covered"]]
    return out
