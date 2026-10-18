"""Synthetic worlds for G1 (W0 and W2) and G3 (the spanning null) (design §8).

W0  the monthly excess returns of every maturity and instrument, redrawn jointly by a stationary
    bootstrap (mean block 12): no feature can predict them; rx12 is rebuilt from the drawn months.
W2  W0 plus k * (duration / 10) * z_{p-1} in every return of month p.
G3  yields from a VAR(1) on three yield factors plus measurement errors, macro from an
    independent VAR(1) on eight macro factors plus idiosyncratic parts; the residuals of one
    month are drawn together (iid), as in Bauer and Hamilton (2018).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .backtest import strategy_returns
from .evaluate import MEAN_BLOCK, cer, stationary_indices
from .features import Pca
from .returns import DURATION, Outcomes, world_outcomes


def resample_rows(
    frame: pd.DataFrame, index: pd.PeriodIndex, seed: int, mean_block: int = MEAN_BLOCK
) -> pd.DataFrame:
    source = frame.dropna()
    rng = np.random.default_rng(seed)
    order = stationary_indices(len(source), 1, mean_block, rng, length=len(index))[0]
    return pd.DataFrame(source.to_numpy()[order], index=index, columns=frame.columns)


def w0_world(real: Outcomes, index: pd.PeriodIndex, seed: int) -> Outcomes:
    joint = pd.concat({"log": real.monthly_log_excess, "simple": real.excess}, axis=1)
    drawn = resample_rows(joint, index, seed)
    return world_outcomes(drawn["log"], drawn["simple"])


def _next_month(z: pd.Series) -> pd.Series:
    """z by decision month, moved to the return month it affects (the last decision included)."""
    return pd.Series(z.to_numpy(), index=z.index + 1)


def plant(world: Outcomes, z: pd.Series, k: float) -> Outcomes:
    log_excess, excess = world.monthly_log_excess.copy(), world.excess.copy()
    lagged = _next_month(z)
    component = lagged.reindex(log_excess.index).fillna(0.0).to_numpy()
    for n in log_excess.columns:
        log_excess[n] = log_excess[n] + k * (n / 10.0) * component
    component = lagged.reindex(excess.index).fillna(0.0).to_numpy()
    for name in excess.columns:
        excess[name] = excess[name] + k * (DURATION[name] / 10.0) * component
    return world_outcomes(log_excess, excess)


def calibrate_k(
    excess: pd.Series,
    z: pd.Series,
    decisions: pd.PeriodIndex,
    *,
    duration: float = DURATION["tlt"],
    gain: float = 0.04,
    cost_bp: float = 2.0,
) -> float:
    """Smallest k whose hold-when-z>0 oracle beats always-hold by ``gain`` CER per year."""
    component = _next_month(z).reindex(excess.index).fillna(0.0)
    oracle = (z.reindex(decisions) > 0).astype(float)
    hold = pd.Series(1.0, index=decisions)

    def advantage(k: float) -> float:
        shifted = excess + k * (duration / 10.0) * component
        a = strategy_returns(oracle, shifted, cost_bp).dropna()
        b = strategy_returns(hold, shifted, cost_bp).dropna()
        return cer(a) - cer(b)

    high = 1e-4
    while advantage(high) < gain:
        high *= 2.0
        if high > 1.0:
            raise ValueError("no planted size reaches the target gain")
    low = 0.0
    for _ in range(60):
        middle = (low + high) / 2.0
        if advantage(middle) >= gain:
            high = middle
        else:
            low = middle
    return high


@dataclass(frozen=True)
class SpanningNull:
    months: pd.PeriodIndex
    maturities: tuple
    yield_mean: np.ndarray
    yield_loadings: np.ndarray  # maturities x factors
    factor_c: np.ndarray
    factor_a: np.ndarray
    macro_names: tuple[str, ...]
    macro_mean: np.ndarray
    macro_loadings: np.ndarray  # series x macro factors
    macro_c: np.ndarray
    macro_a: np.ndarray
    residuals: np.ndarray  # (months - 1) x (factors + maturities + macro factors + series)
    first_yields: np.ndarray
    first_macro: np.ndarray
    first_factors: np.ndarray
    first_macro_factors: np.ndarray

    @property
    def max_eigenvalue(self) -> float:
        return float(np.abs(np.linalg.eigvals(self.factor_a)).max())


def _var1(F: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = np.hstack([np.ones((len(F) - 1, 1)), F[:-1]])
    coef, *_ = np.linalg.lstsq(X, F[1:], rcond=None)
    return coef[0], coef[1:].T, F[1:] - X @ coef


def fit_spanning_null(
    zeros: pd.DataFrame, macro: pd.DataFrame, *, n_factors: int = 3, n_macro: int = 8
) -> SpanningNull:
    months = zeros.dropna().index.intersection(macro.dropna().index)
    if len(months) != len(pd.period_range(months[0], months[-1], freq="M")):
        raise ValueError("the spanning-null fit needs contiguous months")
    Y = zeros.reindex(months).to_numpy(dtype=float)
    M = macro.reindex(months).to_numpy(dtype=float)
    yield_pca = Pca(n_factors).fit(Y)
    F = yield_pca.transform(Y)
    errors = Y - (yield_pca.mean_ + F @ yield_pca.components_)
    macro_pca = Pca(n_macro).fit(M)
    G = macro_pca.transform(M)
    idiosyncratic = M - (macro_pca.mean_ + G @ macro_pca.components_)
    c, a, shocks = _var1(F)
    cg, ag, macro_shocks = _var1(G)
    return SpanningNull(
        months=months,
        maturities=tuple(zeros.columns),
        yield_mean=yield_pca.mean_,
        yield_loadings=yield_pca.components_.T,
        factor_c=c,
        factor_a=a,
        macro_names=tuple(macro.columns),
        macro_mean=macro_pca.mean_,
        macro_loadings=macro_pca.components_.T,
        macro_c=cg,
        macro_a=ag,
        residuals=np.hstack([shocks, errors[1:], macro_shocks, idiosyncratic[1:]]),
        first_yields=Y[0],
        first_macro=M[0],
        first_factors=F[0],
        first_macro_factors=G[0],
    )


def simulate(null: SpanningNull, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    T, k, km, ny = len(null.months), len(null.factor_c), len(null.macro_c), len(null.maturities)
    draws = null.residuals[rng.integers(0, len(null.residuals), T - 1)]
    shocks, errors, macro_shocks, idiosyncratic = np.split(draws, [k, k + ny, k + ny + km], axis=1)
    F, G = np.empty((T, k)), np.empty((T, km))
    F[0], G[0] = null.first_factors, null.first_macro_factors
    for t in range(1, T):
        F[t] = null.factor_c + null.factor_a @ F[t - 1] + shocks[t - 1]
        G[t] = null.macro_c + null.macro_a @ G[t - 1] + macro_shocks[t - 1]
    Y = null.yield_mean + F @ null.yield_loadings.T
    Y[1:] += errors
    Y[0] = null.first_yields
    M = null.macro_mean + G @ null.macro_loadings.T
    M[1:] += idiosyncratic
    M[0] = null.first_macro
    return (
        pd.DataFrame(Y, index=null.months, columns=list(null.maturities)),
        pd.DataFrame(M, index=null.months, columns=list(null.macro_names)),
    )
