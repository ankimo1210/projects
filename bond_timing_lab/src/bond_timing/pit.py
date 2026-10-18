"""Point-in-time rules R1-R4 as checks that raise (design §5; G2 tests them).

R1  a decision at month t uses data observed by t; macro comes from vintage t-1.
R2  training pairs (x_s, y_{s->s+h}) need s + h <= t.
R3  validation is the last 15 % of the pairs, with an h-month gap before it.
R4  transforms are fitted on the training window only.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd


class LookaheadError(RuntimeError):
    """An input would let the decision at month t use information from after t."""


def check_observed(months: Iterable[pd.Period], t: pd.Period) -> None:
    late = [m for m in months if m > t]
    if late:
        raise LookaheadError(f"data for {late[0]} used at the decision of {t}")


def check_vintage(vintage: pd.Period, t: pd.Period) -> None:
    if vintage >= t:
        raise LookaheadError(f"vintage {vintage} is not certainly published by the end of {t}")


def check_targets_complete(starts: pd.PeriodIndex, t: pd.Period, horizon: int) -> None:
    if len(starts) and starts.max() + horizon > t:
        raise LookaheadError(f"the target starting {starts.max()} ends after the refit at {t}")


def training_starts(
    starts: pd.PeriodIndex, t: pd.Period, horizon: int, *, complete: bool = True
) -> pd.PeriodIndex:
    """Purchase months a refit at t may train on: s + h <= t, or s <= t - 1 for V0 (complete=False)."""
    limit = t - horizon if complete else t - 1
    chosen = starts[starts <= limit]
    if complete:
        check_targets_complete(chosen, t, horizon)
    return chosen


def check_embargo(core: pd.PeriodIndex, validation: pd.PeriodIndex, horizon: int) -> None:
    if len(core) and len(validation) and core.max() + horizon > validation.min():
        raise LookaheadError(
            f"the fitting target from {core.max()} overlaps validation from {validation.min()}"
        )


@dataclass(frozen=True)
class Split:
    core: np.ndarray  # positions of the rows that fit the candidates
    validation: np.ndarray  # positions of the rows that score them


def validation_split(
    starts: pd.PeriodIndex, horizon: int, *, fraction: float = 0.15, embargo: bool = True
) -> Split:
    order = np.argsort(starts.asi8, kind="stable")
    n_val = int(np.ceil(fraction * len(order)))
    validation = order[len(order) - n_val :]
    core = order[: len(order) - n_val]
    if embargo:
        first = starts[validation].min()
        core = core[np.asarray(starts[core] <= first - horizon)]
        check_embargo(starts[core], starts[validation], horizon)
    return Split(core, validation)


def check_fit_window(months: pd.PeriodIndex, end: pd.Period) -> None:
    if len(months) and months.max() > end:
        raise LookaheadError(
            f"a transform was fitted on {months.max()}, after the window end {end}"
        )
