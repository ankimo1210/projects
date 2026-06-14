"""Common signal schema.

The platform's signals come from different families (trend, value, quality,
carry, risk, macro) but must be *comparable and combinable*. So every signal is
expressed in one standard form: a :class:`Signal` carrying a cross-sectionally
standardized **score** panel (rows = dates, columns = assets), a **category**, and
a **direction** (+1 means "higher score → prefer long"). Standardization (z-score
or rank across assets, per date) puts every family on the same scale, so a
composite is just a weighted average of scores.

A score on date ``t`` is built from features known at ``t``. Before using a
signal to trade on the *next* bar, call :meth:`Signal.lag` so date-``t`` decisions
use only date-``t-1`` information — the explicit guard against same-bar look-ahead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import pandas as pd


class SignalCategory(StrEnum):
    TREND = "trend"
    VALUE = "value"
    QUALITY = "quality"
    CARRY = "carry"
    RISK = "risk"
    MACRO = "macro"


@dataclass
class Signal:
    """A standardized, comparable signal.

    ``score`` is a panel (DatetimeIndex × assets). It is expected to be
    cross-sectionally standardized (see :mod:`quantkit.signals.normalize`); raw,
    unstandardized panels should be wrapped via :func:`from_raw`.
    """

    name: str
    category: SignalCategory
    score: pd.DataFrame
    direction: int = 1
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.direction not in (-1, 1):
            raise ValueError("direction must be +1 or -1")
        if not isinstance(self.score, pd.DataFrame):
            raise TypeError("score must be a DataFrame (dates × assets)")

    @property
    def oriented(self) -> pd.DataFrame:
        """Score multiplied by ``direction`` (so higher always means 'prefer long')."""
        return self.score * self.direction

    def lag(self, periods: int = 1) -> Signal:
        """Shift the score forward in time so a date-``t`` value uses date-``t-periods``
        information — the guard against acting on same-bar data."""
        return Signal(
            self.name, self.category, self.score.shift(periods), self.direction, dict(self.meta)
        )

    def align(self, index: pd.DatetimeIndex) -> Signal:
        """Reindex the score onto ``index`` WITHOUT filling (gaps stay NaN)."""
        return Signal(
            self.name, self.category, self.score.reindex(index), self.direction, dict(self.meta)
        )


def from_raw(
    name: str,
    category: SignalCategory,
    raw: pd.DataFrame,
    *,
    direction: int = 1,
    method: str = "zscore",
    meta: dict | None = None,
) -> Signal:
    """Build a :class:`Signal` by standardizing a raw feature panel cross-sectionally.

    ``method`` is ``"zscore"`` (default) or ``"rank"`` (centered to [-0.5, 0.5]).
    """
    from . import normalize

    if method == "zscore":
        score = normalize.zscore_xs(raw)
    elif method == "rank":
        score = normalize.rank_xs(raw, centered=True)
    else:
        raise ValueError(f"unknown standardization method: {method!r}")
    return Signal(name, category, score, direction, meta or {})
