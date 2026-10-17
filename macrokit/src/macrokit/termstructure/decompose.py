"""The shared result type, the share s, and the pre-registered verdict (design §2)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np

GRID_MONTHS = np.arange(3, 121, 3)
VERDICT_BAND = (0.35, 0.65)
MIN_MODELS = 3


@dataclass(frozen=True)
class Decomposition:
    model: str
    dates: tuple[date, ...]
    yield_pct: np.ndarray  # observed zero yield from the fitted curve, common to all models
    expected_pct: np.ndarray  # average expected one-month rate over the maturity

    def __post_init__(self) -> None:
        if not len(self.dates) == len(self.yield_pct) == len(self.expected_pct):
            raise ValueError("Decomposition arrays must match the dates")

    @property
    def term_premium_pct(self) -> np.ndarray:
        return self.yield_pct - self.expected_pct

    def share(self, t0: date, t1: date) -> float:
        i0, i1 = self.dates.index(t0), self.dates.index(t1)
        return float(share_of(self.expected_pct, self.yield_pct, i0, i1))


def share_of(expected: np.ndarray, yields: np.ndarray, i0: int, i1: int) -> np.ndarray:
    """(E[i1] - E[i0]) / (Y[i1] - Y[i0]); ``expected`` may have leading bootstrap rows."""
    dy = yields[i1] - yields[i0]
    if abs(dy) < 1e-8:
        raise ValueError("the window is flat: the yield did not change, so s is undefined")
    return (expected[..., i1] - expected[..., i0]) / dy


def month_end_in(dates: Sequence[date], year: int, month: int) -> date:
    for day in dates:
        if (day.year, day.month) == (year, month):
            return day
    raise KeyError(f"no date in {year}-{month:02d}")


def verdict(shares: Mapping[str, float]) -> str:
    """Design §2.3: robust only if every gate-passing model lies inside the band."""
    if len(shares) < MIN_MODELS:
        return "undetermined"
    lower, upper = VERDICT_BAND
    values = list(shares.values())
    if all(lower <= s <= upper for s in values):
        return "robust_half"
    if all(s > upper for s in values):
        return "expectations_dominant"
    if all(s < lower for s in values):
        return "term_premium_dominant"
    return "model_dependent"


def interval(samples: np.ndarray, level: float = 0.90) -> tuple[float, float]:
    tail = (100 - 100 * level) / 2
    lo, hi = np.percentile(samples, [tail, 100 - tail])
    return float(lo), float(hi)


def largest_rise_window(y: np.ndarray, length: int) -> tuple[int, int]:
    """(i, i + length) maximizing y[i + length] - y[i]."""
    rises = y[length:] - y[:-length]
    start = int(np.argmax(rises))
    return start, start + length
