"""Panel regressions, bootstraps, the H3 label and the verdict (design §3.3, §3.4).

The panel regression is the decay paper's eq. (9) without its post-publication terms:
r_{j,d} = a_j + d_d + b sz_{j,d} + e, with sector and day fixed effects removed by alternating
projections and standard errors clustered by day (the day effects are nested in the clusters, so
only the sector effects count as parameters in the small-sample factor).
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

N_BOOT = 10_000
MEAN_BLOCK = 20
SEED = 20261019
ALPHA = 0.05
GAMMA = 5.0
YEAR = 252
CHUNK = 500


def two_way_demean(
    values: np.ndarray, day: np.ndarray, sector: np.ndarray, *, tol: float = 1e-12
) -> np.ndarray:
    """Remove day and sector means from every column (alternating projections)."""
    x = np.array(values, dtype=float, copy=True).reshape(len(day), -1)
    n_day, n_sector = int(day.max()) + 1, int(sector.max()) + 1
    per_day = np.maximum(np.bincount(day, minlength=n_day), 1)
    per_sector = np.maximum(np.bincount(sector, minlength=n_sector), 1)
    for column in range(x.shape[1]):
        v = x[:, column]
        scale = max(1.0, float(np.abs(v).max()))
        for _ in range(10_000):
            by_day = np.bincount(day, v, n_day) / per_day
            v = v - by_day[day]
            by_sector = np.bincount(sector, v, n_sector) / per_sector
            v = v - by_sector[sector]
            if max(np.abs(by_day).max(), np.abs(by_sector).max()) < tol * scale:
                break
        x[:, column] = v
    return x


@dataclass(frozen=True)
class PanelFit:
    beta: tuple[float, ...]  # the signal first, then the controls
    se: tuple[float, ...]
    t: float  # of the signal
    p: float  # one-sided: the signal's coefficient is positive
    n_obs: int
    n_days: int
    days: pd.DatetimeIndex
    score: np.ndarray  # per day: sum of x*y over sectors, after the fixed effects
    weight: np.ndarray  # per day: sum of x*x

    def summary(self) -> dict:
        return {
            "beta": self.beta[0],
            "se": self.se[0],
            "t": self.t,
            "p": self.p,
            "obs": self.n_obs,
            "days": self.n_days,
        }


def panel_fit(
    returns: pd.DataFrame, signal: pd.DataFrame, controls: Sequence[pd.DataFrame] = ()
) -> PanelFit:
    index = returns.index.intersection(signal.index)
    columns = [c for c in returns.columns if c in signal.columns]
    arrays = [
        frame.reindex(index=index, columns=columns).to_numpy(dtype=float)
        for frame in (returns, signal, *controls)
    ]
    mask = np.logical_and.reduce([np.isfinite(a) for a in arrays])
    rows, cols = np.nonzero(mask)
    used_days, day = np.unique(rows, return_inverse=True)
    used_sectors, sector = np.unique(cols, return_inverse=True)
    data = two_way_demean(np.column_stack([a[mask] for a in arrays]), day, sector)
    y, x = data[:, 0], data[:, 1:]
    xtx = x.T @ x
    beta = np.linalg.solve(xtx, x.T @ y)
    resid = y - x @ beta
    n, g, k = len(y), len(used_days), x.shape[1] + len(used_sectors) - 1
    scores = np.column_stack([np.bincount(day, x[:, j] * resid, g) for j in range(x.shape[1])])
    bread = np.linalg.inv(xtx)
    factor = g / (g - 1) * (n - 1) / (n - k)
    se = np.sqrt(np.diag(factor * bread @ (scores.T @ scores) @ bread))
    t = float(beta[0] / se[0])
    return PanelFit(
        tuple(float(b) for b in beta),
        tuple(float(s) for s in se),
        t,
        float(stats.t.sf(t, g - 1)),
        n,
        g,
        index[used_days],
        np.bincount(day, x[:, 0] * y, g),
        np.bincount(day, x[:, 0] ** 2, g),
    )


def stationary_indices(
    n: int, n_boot: int, mean_block: int, rng: np.random.Generator
) -> np.ndarray:
    """Politis-Romano stationary bootstrap: blocks of geometric length with the given mean."""
    idx = np.empty((n_boot, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, n_boot)
    restart = rng.random((n_boot, n)) < 1.0 / mean_block
    jumps = rng.integers(0, n, (n_boot, n))
    for t in range(1, n):
        idx[:, t] = np.where(restart[:, t], jumps[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def _draws(n: int, n_boot: int, mean_block: int, seed: int) -> Iterator[np.ndarray]:
    rng = np.random.default_rng(seed)
    done = 0
    while done < n_boot:
        size = min(CHUNK, n_boot - done)
        yield stationary_indices(n, size, mean_block, rng)
        done += size


def ratio_interval(
    numerator: PanelFit,
    denominator: PanelFit,
    *,
    n_boot: int = N_BOOT,
    mean_block: int = MEAN_BLOCK,
    seed: int = SEED,
    level: float = 0.95,
) -> tuple[float, float]:
    """Interval of b_num / b_den from resampled days (the sector effects stay at their estimates)."""
    days = numerator.days.intersection(denominator.days)
    parts = [
        pd.Series(values, index=fit.days).reindex(days).to_numpy()
        for fit in (numerator, denominator)
        for values in (fit.score, fit.weight)
    ]
    ratios = []
    for idx in _draws(len(days), n_boot, mean_block, seed):
        top = parts[0][idx].sum(axis=1) / parts[1][idx].sum(axis=1)
        bottom = parts[2][idx].sum(axis=1) / parts[3][idx].sum(axis=1)
        ratios.append(top / bottom)
    low, high = np.quantile(np.concatenate(ratios), [(1 - level) / 2, (1 + level) / 2])
    return float(low), float(high)


@dataclass(frozen=True)
class MeanTest:
    mean: float  # daily
    p: float  # one-sided: the mean is positive
    days: int


def mean_test(
    x: pd.Series, *, n_boot: int = N_BOOT, mean_block: int = MEAN_BLOCK, seed: int = SEED
) -> MeanTest:
    """Centred stationary bootstrap: p = (1 + #{m* - m >= m}) / (B + 1)."""
    v = x.dropna().to_numpy(dtype=float)
    m = float(v.mean())
    star = np.concatenate([v[idx].mean(axis=1) for idx in _draws(len(v), n_boot, mean_block, seed)])
    return MeanTest(m, float((1 + np.sum(star - m >= m)) / (n_boot + 1)), len(v))


def describe(daily: pd.Series) -> dict:
    r = daily.dropna()
    sd = float(r.std(ddof=1)) if len(r) > 1 else 0.0
    mean = float(r.mean()) if len(r) else float("nan")
    return {
        "mean_ann": YEAR * mean,
        "vol_ann": float(np.sqrt(YEAR) * sd),
        "sharpe": float(np.sqrt(YEAR) * mean / sd) if sd > 0 else 0.0,
        "cer": YEAR * (mean - GAMMA / 2 * sd**2),
        "cumulative": float((1 + r).prod() - 1),
        "days": len(r),
    }


def monthly_metrics(daily: pd.Series) -> dict:
    """The strategy paper's AR, RISK, R/R and maximum drawdown, from monthly compounded returns."""
    r = daily.dropna()
    monthly = (1 + r).groupby(r.index.to_period("M")).prod() - 1
    wealth = (1 + monthly).cumprod()
    ar = float(12 * monthly.mean())
    risk = float(np.sqrt(12) * monthly.std(ddof=1))
    return {
        "ar": ar,
        "risk": risk,
        "rr": ar / risk if risk > 0 else 0.0,
        "mdd": float((1 - wealth / wealth.cummax()).max()),
        "months": len(monthly),
    }


def h3_label(b2: pd.Series, a: pd.Series, alpha: float = ALPHA) -> dict:
    """Did the ETF long-short keep losing after the decay paper's sample (design §3.3)?"""
    x, y = b2.dropna().to_numpy(), a.dropna().to_numpy()
    p_zero = float(stats.ttest_1samp(x, 0.0, alternative="less").pvalue)
    p_drop = float(stats.ttest_ind(x, y, equal_var=False, alternative="less").pvalue)
    if p_zero < alpha:
        label = "decay_continued"
    elif x.mean() >= 0 and p_drop >= alpha:
        label = "decay_faded"
    else:
        label = "unclear"
    return {
        "label": label,
        "p_below_zero": p_zero,
        "p_below_a": p_drop,
        "mean_b2_ann": YEAR * float(x.mean()),
        "mean_a_ann": YEAR * float(y.mean()),
        "days_b2": len(x),
    }


@dataclass(frozen=True)
class Evidence:
    replicated: bool  # G0: some pairing reproduced the ETF result
    h1_p: float  # period A, basket coefficient > 0
    beta_b_period_b: float  # the basket coefficient in period B
    h2_p_cash: float  # period A, the cash-only strategy beats doing nothing
    h2_p_spread: float  # period A, the chosen sectors beat all 17
    robust: bool  # the signs of both stay at 2 bp, at 3 and at 10 million yen
    b_mean_cash: float  # period B means of the two
    b_mean_spread: float


def verdict(e: Evidence, alpha: float = ALPHA) -> str:
    if not e.replicated:
        return "replication_failed"
    if not e.h1_p < alpha:
        return "etf_only"
    if not e.beta_b_period_b > 0:
        return "real_then_decayed"
    if (
        e.h2_p_cash < alpha
        and e.h2_p_spread < alpha
        and e.robust
        and e.b_mean_cash > 0
        and e.b_mean_spread > 0
    ):
        return "usable"
    return "real_not_usable"
