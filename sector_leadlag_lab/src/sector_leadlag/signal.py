"""PCA SUB: the subspace-regularised lead-lag signal, and the baseline signals (design §6).

Every value comes from the strategy paper (Nakagawa et al., SIG-FIN-036-13); nothing is tuned
here. Japanese sectors are the JPX 17-sector codes 1-17; NEXT FUNDS ETF 1616+k tracks sector k.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import pit
from .timing import Rows

LAMBDA = 0.9
K = 3
WINDOW = 60
Q = 0.3
FULL = (pd.Timestamp("2010-01-01"), pd.Timestamp("2014-12-31"))
US_CYCLICAL = ("XLB", "XLE", "XLF", "XLRE")
US_DEFENSIVE = ("XLK", "XLP", "XLU", "XLV")
JP_CYCLICAL = (2, 9, 13, 15)  # 1618 energy, 1625 electric & precision, 1629 trading, 1631 banks
JP_DEFENSIVE = (1, 5, 11, 14)  # 1617 foods, 1621 pharma, 1627 power & gas, 1630 retail


@dataclass(frozen=True)
class Spec:
    lam: float = LAMBDA
    k: int = K
    window: int = WINDOW
    kind: str = "pca"  # "pca", or "momentum" (the window mean of each Japanese sector)


def prior_subspace(us_names: Sequence[str], jp_names: Sequence[int]) -> np.ndarray:
    """V0 = [v1, v2, v3]: market, US minus Japan, cyclical minus defensive; orthonormal columns."""
    labels = [*us_names, *jp_names]
    cyclical = {*US_CYCLICAL, *JP_CYCLICAL}
    defensive = {*US_DEFENSIVE, *JP_DEFENSIVE}
    v1 = np.ones(len(labels))
    v2 = np.r_[np.ones(len(us_names)), -np.ones(len(jp_names))]
    v3 = np.array([1.0 if x in cyclical else -1.0 if x in defensive else 0.0 for x in labels])
    basis: list[np.ndarray] = []
    for v in (v1, v2, v3):
        for u in basis:
            v = v - (u @ v) * u
        basis.append(v / np.linalg.norm(v))
    return np.column_stack(basis)


def standardize(block: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Column means and standard deviations (1/L), which columns are usable, and the z-scores.

    A column is usable when it has no missing value in the block and is not constant. The others
    (an ETF before its launch, design §4) get z = 0 and no correlation with anything.
    """
    finite = np.isfinite(block)
    filled = np.where(finite, block, 0.0)
    mu = filled.mean(axis=0)
    sd = filled.std(axis=0)
    usable = finite.all(axis=0) & (sd > 0)
    safe = np.where(usable, sd, 1.0)
    z = np.where(usable, (filled - mu) / safe, 0.0)
    return mu, safe, usable, z


def correlation(z: np.ndarray, usable: np.ndarray) -> np.ndarray:
    c = z.T @ z / len(z)
    c[~usable, :] = 0.0
    c[:, ~usable] = 0.0
    np.fill_diagonal(c, 1.0)
    return c


def full_correlation(
    rows: Rows, span: tuple[pd.Timestamp, pd.Timestamp] = FULL
) -> tuple[np.ndarray, list]:
    """C_full over the estimation span, and the columns it could not use."""
    mask = (rows.dates >= span[0]) & (rows.dates <= span[1])
    block = np.hstack([rows.us[mask], rows.jp[mask]])
    _, _, usable, z = standardize(block)
    labels = [*rows.us_names, *rows.jp_names]
    return correlation(z, usable), [labels[i] for i in np.flatnonzero(~usable)]


def target(c_full: np.ndarray, v0: np.ndarray) -> np.ndarray:
    """C0: V0 diag(V0' C_full V0) V0', rescaled to a correlation matrix with a unit diagonal."""
    d0 = np.diag(np.diag(v0.T @ c_full @ v0))
    raw = v0 @ d0 @ v0.T
    scale = np.sqrt(np.diag(raw))
    c0 = raw / np.outer(scale, scale)
    np.fill_diagonal(c0, 1.0)
    return c0


def propagate(vectors: np.ndarray, n_us: int, z_us: np.ndarray) -> np.ndarray:
    """V_J V_U' z_U: project the US shock on the leading modes and map it to Japan."""
    return vectors[n_us:] @ (vectors[:n_us].T @ z_us)


def lead_lag_signal(
    rows: Rows,
    us_ret: pd.DataFrame,
    s_map: pd.Series,
    c0: np.ndarray,
    days: pd.DatetimeIndex,
    spec: Spec = Spec(),
) -> pd.DataFrame:
    """The signal of each Japanese day d in ``days`` that has a full window (design §6).

    The window of d is the last ``spec.window`` rows dated before d. z_U,s(d) is the US return of
    s(d) standardised with the window's US means and standard deviations.
    """
    n_us = rows.us.shape[1]
    block = np.hstack([rows.us, rows.jp])
    days = pd.DatetimeIndex(days).intersection(s_map.index)
    us_days = pd.DatetimeIndex(s_map.reindex(days).to_numpy())
    us_now = us_ret.reindex(us_days).to_numpy()
    ends = rows.dates.searchsorted(days, side="left")
    out = np.full((len(days), rows.jp.shape[1]), np.nan)
    for i, end in enumerate(ends):
        if end < spec.window:
            continue
        lo = end - spec.window
        pit.check_window(rows.dates[lo:end], rows.us_dates[lo:end], us_days[i], days[i])
        mu, sd, usable, z = standardize(block[lo:end])
        if spec.kind == "momentum":
            out[i] = np.where(usable[n_us:], mu[n_us:], np.nan)
            continue
        c_reg = (1.0 - spec.lam) * correlation(z, usable) + spec.lam * c0
        values, vectors = np.linalg.eigh(c_reg)
        top = vectors[:, np.argsort(values)[::-1][: spec.k]]
        x = us_now[i]
        live = usable[:n_us] & np.isfinite(x)
        z_us = np.where(live, (np.where(live, x, 0.0) - mu[:n_us]) / sd[:n_us], 0.0)
        out[i] = propagate(top, n_us, z_us)
    frame = pd.DataFrame(out, index=days, columns=list(rows.jp_names))
    return frame.dropna(how="all")


def cross_standardize(signal: pd.DataFrame) -> pd.DataFrame:
    """sz_{j,d}: each day's signal across the sectors, mean 0 and standard deviation 1."""
    mean = signal.mean(axis=1)
    sd = signal.std(axis=1, ddof=0)
    return signal.sub(mean, axis=0).div(sd.where(sd > 0), axis=0)


def _descending(values: np.ndarray, idx: np.ndarray) -> np.ndarray:
    return idx[np.argsort(-values[idx], kind="stable")]  # ties keep the lower sector code first


def long_short(signal: pd.DataFrame, available: pd.DataFrame, q: float = Q) -> pd.DataFrame:
    """+1/n on the top ⌊q·|J_d|⌋ available sectors and −1/n on the bottom ones (design §6)."""
    values = signal.to_numpy()
    ok = available.reindex(index=signal.index, columns=signal.columns, fill_value=False)
    ok = ok.to_numpy(dtype=bool) & np.isfinite(values)
    weights = np.zeros(values.shape)
    for i in range(len(values)):
        idx = np.flatnonzero(ok[i])
        n = int(np.floor(q * len(idx) + 1e-9))
        if n == 0 or np.ptp(values[i, idx]) == 0:
            continue
        order = _descending(values[i], idx)
        weights[i, order[:n]] = 1.0 / n
        weights[i, order[-n:]] = -1.0 / n
    return pd.DataFrame(weights, index=signal.index, columns=signal.columns)


def top_sectors(signal: pd.DataFrame, n: int) -> pd.DataFrame:
    """The n sectors with the highest signal each day."""
    values = signal.to_numpy()
    chosen = np.zeros(values.shape, dtype=bool)
    for i in range(len(values)):
        idx = np.flatnonzero(np.isfinite(values[i]))
        if len(idx) < n or np.ptp(values[i, idx]) == 0:
            continue
        chosen[i, _descending(values[i], idx)[:n]] = True
    return pd.DataFrame(chosen, index=signal.index, columns=signal.columns)
