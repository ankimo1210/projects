"""G1's broken worlds, the planted effect of the power report, and the stale-open diagnostic.

G1 (design §8) rotates the US returns against Japan so that no US day lines up with the
Japanese day it used to precede; the signal is then rebuilt from the rotated returns. The
stale-open diagnostic (design §9) imitates an index whose opening value still carries the
previous close of the names that have not opened yet.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .evaluate import SEED

SHIFTS = 20
MIN_SHIFT = 60


def shift_amounts(
    n: int, count: int = SHIFTS, *, seed: int = SEED, min_shift: int = MIN_SHIFT
) -> list[int]:
    rng = np.random.default_rng(seed)
    return [int(k) for k in rng.integers(min_shift, n - min_shift, size=count)]


def circular_shift(frame: pd.DataFrame, k: int) -> pd.DataFrame:
    """Rows rotated down by k positions; the dates stay where they are."""
    return pd.DataFrame(
        np.roll(frame.to_numpy(), k, axis=0), index=frame.index, columns=frame.columns
    )


def plant(returns: pd.DataFrame, sz: pd.DataFrame, beta: float) -> pd.DataFrame:
    """Returns plus beta times the standardised signal, where both exist."""
    signal = sz.reindex(index=returns.index, columns=returns.columns)
    return returns + beta * signal.fillna(0.0).where(returns.notna())


def stale_returns(
    o2c: pd.DataFrame,
    price_c2c: pd.DataFrame,
    c2o: pd.DataFrame,
    fraction: float,
    *,
    mode: str,
    seed: int = SEED,
) -> pd.DataFrame:
    """Each name's return from an opening value that, for a share of names, is the previous close.

    ``mode`` "random" marks a random ``fraction`` of the names each day; "largest_gap" marks the
    names with the largest overnight moves, which are the ones that open late (design §2.3).
    """
    live = o2c.notna() & price_c2c.notna()
    if mode == "random":
        rng = np.random.default_rng(seed)
        stale = pd.DataFrame(rng.random(o2c.shape) < fraction, index=o2c.index, columns=o2c.columns)
    elif mode == "largest_gap":
        gap = c2o.abs().where(live)
        rank = gap.rank(axis=1, ascending=False, method="first")
        stale = rank.le(np.ceil(fraction * live.sum(axis=1)), axis=0)
    else:
        raise ValueError(f"unknown mode {mode!r}")
    return o2c.where(~(stale & live), price_c2c)
