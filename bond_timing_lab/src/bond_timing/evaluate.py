"""Certainty equivalent, Sharpe, R2oos, the stationary bootstrap, Holm and the verdict (design §3).

The test of "a beats b" uses the monthly returns of the same months, resampled with the same
stationary-bootstrap indices (Politis-Romano, mean block 12), centred:
p = (1 + #{D* - D >= D}) / (B + 1), where D is the observed CER (or Sharpe) difference.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

GAMMA = 5.0
N_BOOT = 10_000
MEAN_BLOCK = 12
SEED = 20261019
ALPHA = 0.05


def cer(r: Sequence[float] | np.ndarray | pd.Series, gamma: float = GAMMA) -> float:
    x = np.asarray(r, dtype=float)
    return float(12.0 * (x.mean() - gamma / 2.0 * x.var(ddof=1)))


def sharpe(r: Sequence[float] | np.ndarray | pd.Series) -> float:
    x = np.asarray(r, dtype=float)
    sd = x.std(ddof=1)
    return float(np.sqrt(12.0) * x.mean() / sd) if sd > 0 else 0.0


def stationary_indices(
    n: int, n_boot: int, mean_block: int, rng: np.random.Generator, length: int | None = None
) -> np.ndarray:
    length = n if length is None else length
    idx = np.empty((n_boot, length), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, n_boot)
    restart = rng.random((n_boot, length)) < 1.0 / mean_block
    jumps = rng.integers(0, n, (n_boot, length))
    for t in range(1, length):
        idx[:, t] = np.where(restart[:, t], jumps[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def _cer_rows(X: np.ndarray, gamma: float) -> np.ndarray:
    return 12.0 * (X.mean(axis=1) - gamma / 2.0 * X.var(axis=1, ddof=1))


def _sharpe_rows(X: np.ndarray) -> np.ndarray:
    sd = X.std(axis=1, ddof=1)
    ratio = np.divide(X.mean(axis=1), sd, out=np.zeros(len(X)), where=sd > 0)
    return np.sqrt(12.0) * ratio


@dataclass(frozen=True)
class DiffTest:
    delta_cer: float
    delta_sharpe: float
    p_cer: float
    p_sharpe: float
    months: int


def diff_test(
    a: pd.Series,
    b: pd.Series,
    *,
    n_boot: int = N_BOOT,
    mean_block: int = MEAN_BLOCK,
    seed: int = SEED,
    gamma: float = GAMMA,
) -> DiffTest:
    """One-sided test that strategy a has a higher CER (and Sharpe) than b."""
    joint = pd.concat([a, b], axis=1).dropna()
    x, y = joint.iloc[:, 0].to_numpy(), joint.iloc[:, 1].to_numpy()
    idx = stationary_indices(len(x), n_boot, mean_block, np.random.default_rng(seed))
    d_cer = cer(x, gamma) - cer(y, gamma)
    d_sharpe = sharpe(x) - sharpe(y)
    star_cer = _cer_rows(x[idx], gamma) - _cer_rows(y[idx], gamma)
    star_sharpe = _sharpe_rows(x[idx]) - _sharpe_rows(y[idx])
    p_cer = (1 + np.sum(star_cer - d_cer >= d_cer)) / (n_boot + 1)
    p_sharpe = (1 + np.sum(star_sharpe - d_sharpe >= d_sharpe)) / (n_boot + 1)
    return DiffTest(float(d_cer), float(d_sharpe), float(p_cer), float(p_sharpe), len(x))


def holm(pvalues: Mapping[str, float]) -> dict[str, float]:
    ordered = sorted(pvalues.items(), key=lambda item: item[1])
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (len(ordered) - rank) * p))
        adjusted[name] = running
    return adjusted


def r2_oos(y: pd.Series, forecast: pd.Series, benchmark: pd.Series) -> float:
    """Campbell-Thompson out-of-sample R2 against the prevailing mean."""
    joint = pd.concat([y, forecast, benchmark], axis=1).dropna()
    model = ((joint.iloc[:, 0] - joint.iloc[:, 1]) ** 2).sum()
    bench = ((joint.iloc[:, 0] - joint.iloc[:, 2]) ** 2).sum()
    return float(1.0 - model / bench)


def prevailing_mean(
    targets: pd.Series, decisions: pd.PeriodIndex, horizon: int, *, complete: bool = True
) -> pd.Series:
    """Mean of the targets a decision at t may use: s + h <= t, or s <= t - 1 when not complete."""
    valid = targets.dropna()
    running = valid.expanding().mean()
    span = pd.period_range(valid.index[0], max(valid.index[-1], decisions.max()), freq="M")
    running = running.reindex(span).ffill()
    limits = decisions - horizon if complete else decisions - 1
    return pd.Series(running.reindex(limits).to_numpy(), index=decisions)


@dataclass(frozen=True)
class Evidence:
    p_vs_hold: float  # H_A, Holm-adjusted over P1-P5
    robust_vs_hold: bool  # the OOS-A difference vs L0 stays positive at 4 bp and with the delay
    oos_b_vs_hold: float  # OOS-B CER difference vs L0
    p_vs_p1: float | None = None  # H_B, Holm-adjusted over P4-P5
    robust_vs_p1: bool | None = None
    oos_b_vs_p1: float | None = None
    g3_p: float | None = None  # Bauer-Hamilton style p-value (P4, P5)


def verdict(evidence: Mapping[str, Evidence], alpha: float = ALPHA) -> str:
    for name in ("P4", "P5"):
        e = evidence[name]
        if (
            e.p_vs_hold < alpha
            and e.p_vs_p1 is not None
            and e.p_vs_p1 < alpha
            and e.oos_b_vs_hold > 0
            and (e.oos_b_vs_p1 or 0.0) > 0
            and e.robust_vs_hold
            and bool(e.robust_vs_p1)
            and e.g3_p is not None
            and e.g3_p < alpha
        ):
            return "ml_signal_usable"
    for name in ("P1", "P2", "P3"):
        e = evidence[name]
        if e.p_vs_hold < alpha and e.oos_b_vs_hold > 0 and e.robust_vs_hold:
            return "simple_rule_usable"
    return "no_usable_signal"
