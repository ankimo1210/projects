"""Forward-looking labels (supervised targets).

Labels are the one place future data is used *on purpose*: ``label[t]`` describes
what happens AFTER ``t`` (e.g. the next ``horizon``-bar return). That is correct
for a training target but dangerous for evaluation, so this module makes the
"when is the label actually known" explicit:

  * the last ``horizon`` rows are NaN — there is no future yet, and we never
    fabricate one (no fill);
  * :func:`label_available_date` maps each ``t`` to ``t+horizon`` — the date the
    label becomes known — so the backtest layer can **embargo** test windows and
    avoid train/test leakage.

Features (causal, known at ``t``) predict labels (known only at ``t+horizon``).
Keeping the two timelines separate is what makes a walk-forward split honest.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def forward_return(price: pd.Series | pd.DataFrame, horizon: int = 21, *, log: bool = False):
    """Return realized over the *next* ``horizon`` bars: price[t+h]/price[t] - 1.

    The trailing ``horizon`` rows are NaN (the future is unknown) and are left as
    NaN, never filled.
    """
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    fwd = price.shift(-horizon)
    if log:
        return np.log(fwd) - np.log(price)
    return fwd / price - 1.0


def binary_label(forward: pd.Series | pd.DataFrame, threshold: float = 0.0):
    """1 where forward return > ``threshold``, 0 where <=, NaN where forward is NaN."""
    out = (forward > threshold).astype("float64")
    return out.where(forward.notna(), other=np.nan)


def ternary_label(forward: pd.Series | pd.DataFrame, upper: float, lower: float | None = None):
    """+1 / 0 / -1 for forward return above ``upper`` / between / below ``lower``.

    ``lower`` defaults to ``-upper`` (a symmetric dead-zone). NaNs are preserved.
    """
    if lower is None:
        lower = -upper
    if lower > upper:
        raise ValueError("require lower <= upper")
    out = (
        pd.DataFrame(0.0, index=forward.index, columns=getattr(forward, "columns", None))
        if isinstance(forward, pd.DataFrame)
        else pd.Series(0.0, index=forward.index)
    )
    out = out.where(forward <= upper, other=1.0)
    out = out.where(forward >= lower, other=-1.0)
    return out.where(forward.notna(), other=np.nan)


def triple_barrier(
    price: pd.Series,
    horizon: int = 21,
    up: float = 0.05,
    down: float = 0.05,
) -> pd.DataFrame:
    """First-touch label over the next ``horizon`` bars (single asset).

    From each ``t`` walk forward up to ``horizon`` bars: +1 if the price rises by
    ``up`` first, -1 if it falls by ``down`` first, 0 if neither barrier is hit by
    the horizon ("time barrier"). Returns columns ``label`` and ``touch_offset``
    (bars until the decisive touch, or ``horizon`` for the time barrier). The last
    ``horizon`` rows are NaN (insufficient future).
    """
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    p = price.to_numpy(dtype="float64")
    n = len(p)
    labels = np.full(n, np.nan)
    offsets = np.full(n, np.nan)
    for i in range(n - horizon):
        p0 = p[i]
        if not np.isfinite(p0) or p0 == 0:
            continue
        hi, lo = p0 * (1.0 + up), p0 * (1.0 - down)
        lab, off = 0, horizon
        for j in range(1, horizon + 1):
            pj = p[i + j]
            if not np.isfinite(pj):
                continue
            if pj >= hi:
                lab, off = 1, j
                break
            if pj <= lo:
                lab, off = -1, j
                break
        labels[i], offsets[i] = lab, off
    return pd.DataFrame({"label": labels, "touch_offset": offsets}, index=price.index)


def label_available_date(index: pd.DatetimeIndex, horizon: int) -> pd.Series:
    """Map each label timestamp ``t`` to when it is known: the timestamp ``horizon``
    bars later in ``index`` (NaT for the last ``horizon`` entries).

    Use this to embargo: a test window must not include labels whose availability
    date falls inside the training window's future.
    """
    idx = pd.DatetimeIndex(index)
    avail = idx.to_series().shift(-horizon)
    avail.name = "label_available_date"
    return avail
