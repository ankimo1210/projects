"""Annual refits, monthly allocations, costs and the execution delay (design §3.1, §5, §6.3).

A refit at the end of January of year Y trains on every pair the rules allow at that date and
serves the decisions of January..December of Y. A decision with no forecast holds cash.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from .features import INPUTS, InputTransform
from .models import ModelSpec, Params, en_grid, fit_predict
from .pit import (
    check_fit_window,
    check_observed,
    check_targets_complete,
    training_starts,
    validation_split,
)

TRAIN_START = pd.Period("1971-08", "M")
MIN_PAIRS = 60


@dataclass(frozen=True)
class Rules:
    complete_targets: bool = True  # R2
    embargo: bool = True  # R3
    in_window: bool = True  # R4
    real_time_macro: bool = True  # R1 for macro: vintage t-1 and publication lags


REAL_TIME = Rules()
V0 = Rules(False, False, False, False)
V1 = Rules(True, False, False, False)
V2 = Rules(True, True, True, False)
V3 = REAL_TIME


@dataclass(frozen=True)
class RefitTask:
    refit: pd.Period
    decisions: pd.PeriodIndex
    starts: pd.PeriodIndex
    Y: np.ndarray  # training rows x 10 yields
    M: np.ndarray | None  # training rows x macro series
    y: np.ndarray  # training rows x targets
    Y_pred: np.ndarray  # decisions x 10 yields
    M_pred: np.ndarray | None
    horizon: int
    rules: Rules
    Y_full: np.ndarray | None = None  # rows for full-sample transforms (R4 off)
    M_full: np.ndarray | None = None


def build_tasks(
    yields: pd.DataFrame,
    targets: pd.DataFrame,
    macro,
    *,
    refit_years: Iterable[int],
    window: tuple[pd.Period, pd.Period],
    horizon: int,
    rules: Rules,
    train_start: pd.Period = TRAIN_START,
    full_end: pd.Period | None = None,
) -> list[RefitTask]:
    if not rules.in_window and full_end is None:
        raise ValueError("full-sample transforms (R4 off) need full_end")
    usable = targets.dropna().index.intersection(yields.dropna().index)
    usable = usable[usable >= train_start].sort_values()
    full_rows = None
    if not rules.in_window:
        full_rows = yields.dropna().index
        full_rows = full_rows[(full_rows >= train_start) & (full_rows <= full_end)]
    tasks = []
    for year in refit_years:
        t = pd.Period(f"{year}-01", "M")
        decisions = pd.period_range(t, t + 11, freq="M")
        decisions = decisions[(decisions >= window[0]) & (decisions <= window[1])]
        decisions = decisions[yields.reindex(decisions).notna().all(axis=1).to_numpy()]
        if len(decisions) == 0:
            continue
        starts = training_starts(usable, t, horizon, complete=rules.complete_targets)
        if len(starts) < MIN_PAIRS:
            continue
        check_observed(starts, t)
        M = M_pred = M_full = None
        if macro is not None:
            view = macro.view(t)
            M = macro.history(t, view, starts)
            M_pred = np.vstack([macro.edge(d, view) for d in decisions])
            if full_rows is not None:
                M_full = macro.history(t, view, full_rows)
        tasks.append(
            RefitTask(
                refit=t,
                decisions=decisions,
                starts=starts,
                Y=yields.reindex(starts).to_numpy(dtype=float),
                M=M,
                y=targets.reindex(starts).to_numpy(dtype=float),
                Y_pred=yields.reindex(decisions).to_numpy(dtype=float),
                M_pred=M_pred,
                horizon=horizon,
                rules=rules,
                Y_full=None
                if full_rows is None
                else yields.reindex(full_rows).to_numpy(dtype=float),
                M_full=M_full,
            )
        )
    return tasks


@dataclass(frozen=True)
class TaskResult:
    model: str
    refit: pd.Period
    decisions: pd.PeriodIndex
    prediction: np.ndarray
    params: dict


def _rows(matrix: np.ndarray | None, rows: np.ndarray) -> np.ndarray | None:
    return None if matrix is None else matrix[rows]


def _fit_transform(
    spec: ModelSpec, task: RefitTask, rows: np.ndarray | None = None
) -> InputTransform:
    transform = InputTransform(INPUTS[spec.inputs])
    if not task.rules.in_window:
        return transform.fit(task.Y_full, task.M_full)
    if rows is None:
        return transform.fit(task.Y, task.M)
    return transform.fit(task.Y[rows], _rows(task.M, rows))


def _select(task: RefitTask, spec: ModelSpec) -> Params:
    """Pick the candidate with the lowest validation MSE (each target scaled by its variance)."""
    if spec.kind != "en" and len(spec.grid) == 1:
        return spec.grid[0]
    split = validation_split(task.starts, task.horizon, embargo=task.rules.embargo)
    transform = _fit_transform(spec, task, split.core)
    X_core = transform.transform(task.Y[split.core], _rows(task.M, split.core))
    X_val = transform.transform(task.Y[split.validation], _rows(task.M, split.validation))
    y_core, y_val = task.y[split.core], task.y[split.validation]
    candidates = spec.grid
    if spec.kind == "en":
        sd = y_core.std(axis=0)
        candidates = en_grid(X_core, (y_core - y_core.mean(axis=0)) / np.where(sd > 0, sd, 1.0))
    scale = y_core.var(axis=0)
    scale = np.where(scale > 0, scale, 1.0)
    best, best_loss = candidates[0], np.inf
    for params in candidates:
        prediction = fit_predict(spec.kind, params, spec.n_seeds, X_core, y_core, X_val)
        loss = float(np.mean((prediction - y_val) ** 2 / scale))
        if loss < best_loss:
            best, best_loss = params, loss
    return best


def fit_task(task: RefitTask, spec: ModelSpec, fixed: Params | None = None) -> TaskResult:
    if task.rules.complete_targets:
        check_targets_complete(task.starts, task.refit, task.horizon)
    if task.rules.in_window:
        end = task.refit - task.horizon if task.rules.complete_targets else task.refit - 1
        check_fit_window(task.starts, end)
    params = fixed if fixed is not None else _select(task, spec)
    transform = _fit_transform(spec, task)
    X = transform.transform(task.Y, task.M)
    X_new = transform.transform(task.Y_pred, task.M_pred)
    prediction = fit_predict(spec.kind, params, spec.n_seeds, X, task.y, X_new)
    return TaskResult(spec.name, task.refit, task.decisions, prediction, dict(params))


@dataclass(frozen=True)
class Forecasts:
    predictions: dict[str, pd.DataFrame]  # model -> decision month x target column
    params: dict[str, dict[str, dict]]  # model -> refit month -> chosen hyperparameters


def as_params(params: Mapping | None) -> Params | None:
    """Hyperparameters back from JSON: sorted items, with lists turned back into tuples."""
    if params is None:
        return None
    return tuple(
        sorted(
            (key, tuple(value) if isinstance(value, list) else value)
            for key, value in params.items()
        )
    )


def _single_thread() -> None:
    threadpool_limits(1)


def _run_job(job: tuple[RefitTask, ModelSpec, Params | None]) -> TaskResult:
    task, spec, fixed = job
    return fit_task(task, spec, fixed)


def run_forecasts(
    tasks: Sequence[RefitTask],
    specs: Sequence[ModelSpec],
    *,
    workers: int = 1,
    fixed: Mapping[str, Mapping[str, Mapping]] | None = None,
) -> Forecasts:
    fixed = fixed or {}
    jobs = [
        (task, spec, as_params(fixed.get(spec.name, {}).get(str(task.refit))))
        for spec in specs
        for task in tasks
    ]
    if workers > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(
            max_workers=min(workers, len(jobs)), initializer=_single_thread
        ) as pool:
            results = list(pool.map(_run_job, jobs, chunksize=1))
    else:
        with threadpool_limits(1):
            results = [_run_job(job) for job in jobs]
    frames: dict[str, list[pd.DataFrame]] = {}
    params: dict[str, dict[str, dict]] = {}
    for result in results:
        frames.setdefault(result.model, []).append(
            pd.DataFrame(result.prediction, index=result.decisions)
        )
        params.setdefault(result.model, {})[str(result.refit)] = result.params
    return Forecasts({model: pd.concat(f).sort_index() for model, f in frames.items()}, params)


def signal_weights(signal: pd.Series, decisions: pd.PeriodIndex) -> pd.Series:
    """1 (hold) where the signal is positive; 0 (cash) where it is not or does not exist."""
    return (signal.reindex(decisions) > 0).astype(float)


def strategy_returns(weights: pd.Series, excess: pd.Series, cost_bp: float = 2.0) -> pd.Series:
    """r[t+1] = w_t * excess[t+1] - cost * |w_t - w_{t-1}|; the first month pays no cost."""
    w = weights.astype(float).to_numpy()
    turnover = np.abs(np.diff(w, prepend=w[:1]))
    months = weights.index + 1
    r = w * excess.reindex(months).to_numpy(dtype=float) - cost_bp * 1e-4 * turnover
    return pd.Series(r, index=months)


def delayed_returns(
    weights: pd.Series, excess: pd.Series, legs: pd.DataFrame, cost_bp: float = 2.0
) -> pd.Series:
    """As strategy_returns, but a switch executes on the 5th trading day (R5): the switch month
    earns the ``in`` or ``out`` leg instead of the month-end-to-month-end return."""
    w = weights.astype(float).to_numpy()
    if not np.isin(w, (0.0, 1.0)).all():
        raise ValueError("the delayed execution is defined for hold-or-cash weights only")
    prev = np.concatenate([w[:1], w[:-1]])
    months = weights.index + 1
    ex = excess.reindex(months).to_numpy(dtype=float)
    leg_in = legs["in"].reindex(months).to_numpy(dtype=float)
    leg_out = legs["out"].reindex(months).to_numpy(dtype=float)
    held = np.where(w == prev, w * ex, np.where(w > prev, leg_in, leg_out))
    return pd.Series(held - cost_bp * 1e-4 * np.abs(w - prev), index=months)


def fractional_weights(
    forecast: pd.Series,
    excess: pd.Series,
    decisions: pd.PeriodIndex,
    *,
    gamma: float = 5.0,
    window: int = 60,
    min_months: int = 36,
) -> pd.Series:
    """Secondary 0-100 % weights: clip((12-month forecast / 12) / (gamma * monthly variance), 0, 1)."""
    variance = excess.rolling(window, min_periods=min_months).var()
    weight = (forecast.reindex(decisions) / 12.0) / (gamma * variance.reindex(decisions))
    return weight.clip(0.0, 1.0).fillna(0.0)
