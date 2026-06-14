"""Walk-forward splits with purge + embargo — the train/test leakage guard.

A forward walk trains on the past and tests on the *next* block, marching
forward. Two corrections make it honest when labels span ``horizon`` bars
(``irp.labels``):

  * **purge** — drop the tail of training whose label window would reach into the
    test block (a label at ``t`` needs returns through ``t+horizon``);
  * **embargo** — leave an extra buffer of ``embargo`` bars between train and test
    so neighbouring-bar leakage cannot sneak across the boundary.

Both are baked into the split by separating train and test by ``gap = horizon +
embargo`` bars, so every training label is known strictly before the test block
begins. ``is_leakage_free`` checks exactly that and is used by the tests.

This is forward-only (training is always entirely before its test block — the
realistic backtest setting), not combinatorial cross-validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass(frozen=True)
class Fold:
    """One walk-forward fold: ``train`` then (after a gap) ``test``."""

    train: pd.DatetimeIndex
    test: pd.DatetimeIndex

    def __repr__(self) -> str:
        def span(ix):
            return f"{ix[0].date()}..{ix[-1].date()} (n={len(ix)})" if len(ix) else "empty"

        return f"Fold(train={span(self.train)}, test={span(self.test)})"


def walk_forward(
    index: pd.DatetimeIndex,
    *,
    train: int,
    test: int,
    step: int | None = None,
    mode: Literal["expanding", "rolling"] = "expanding",
    horizon: int = 0,
    embargo: int = 0,
) -> list[Fold]:
    """Build walk-forward folds over ``index``.

    Parameters
    ----------
    train, test : initial training length and test-block length, in bars.
    step : how far each successive test block advances (default = ``test``, i.e.
        consecutive non-overlapping test blocks).
    mode : ``"expanding"`` (train always starts at 0) or ``"rolling"`` (train is
        the most recent ``train`` bars).
    horizon : label horizon to purge against (last ``horizon`` train bars before
        a test block are dropped, since their labels overlap the test).
    embargo : extra buffer bars between train and test.
    """
    if train <= 0 or test <= 0:
        raise ValueError("train and test must be positive")
    idx = pd.DatetimeIndex(index)
    n = len(idx)
    step = step or test
    gap = horizon + embargo
    folds: list[Fold] = []
    test_start = train + gap
    while test_start + test <= n:
        train_end = test_start - gap  # exclusive
        train_start = 0 if mode == "expanding" else max(0, train_end - train)
        train_idx = idx[train_start:train_end]
        test_idx = idx[test_start : test_start + test]
        if len(train_idx) and len(test_idx):
            folds.append(Fold(train_idx, test_idx))
        test_start += step
    return folds


def is_leakage_free(fold: Fold, index: pd.DatetimeIndex, horizon: int) -> bool:
    """True if every training label is knowable before the test block starts.

    A label at train timestamp ``t`` (position ``p`` in the *original* ``index``)
    becomes known ``horizon`` bars later, at ``index[p+horizon]``. Leakage-free
    means the latest such availability is strictly before the first test
    timestamp. Bar distance must be measured on the original ``index`` — the gap
    bars between train and test are absent from ``train ∪ test``, which would
    understate the distance.
    """
    if not len(fold.train) or not len(fold.test):
        return True
    idx = pd.DatetimeIndex(index)
    last_train_pos = idx.get_loc(fold.train[-1])
    first_test_pos = idx.get_loc(fold.test[0])
    return last_train_pos + horizon < first_test_pos
