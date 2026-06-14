"""Walk-forward splits with purge + embargo — the train/test leakage guard.

A forward walk trains on the past and tests on the *next* block, marching
forward. Two corrections make it honest when labels span ``horizon`` bars
(``quantkit.labels``):

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

import itertools
import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
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


def _contiguous_blocks(positions: np.ndarray) -> list[tuple[int, int]]:
    """Group sorted integer positions into ``(start, end)`` inclusive runs."""
    pos = np.sort(np.asarray(positions, dtype=int))
    if len(pos) == 0:
        return []
    blocks: list[tuple[int, int]] = []
    start = prev = int(pos[0])
    for p in pos[1:]:
        p = int(p)
        if p == prev + 1:
            prev = p
        else:
            blocks.append((start, prev))
            start = prev = p
    blocks.append((start, prev))
    return blocks


def _forbidden_positions(test_pos: np.ndarray, n: int, horizon: int, embargo: int) -> set[int]:
    """Positions that may not be used for training given test blocks.

    For each contiguous test block ``[a, b]``: the block itself, the **purge**
    zone ``[a-horizon, a)`` (training labels whose ``horizon`` window reaches into
    the block) and the **embargo** zone ``(b, b+embargo]`` (a buffer after the
    block against serial-correlation leakage). Two-sided because a combinatorial
    test block can sit in the interior of the timeline.
    """
    forbidden = {int(p) for p in test_pos}
    for a, b in _contiguous_blocks(test_pos):
        forbidden.update(range(max(0, a - horizon), a))
        forbidden.update(range(b + 1, min(n, b + 1 + embargo)))
    return forbidden


def combinatorial_purged(
    index: pd.DatetimeIndex,
    *,
    n_groups: int,
    k_test: int,
    horizon: int = 0,
    embargo: int = 0,
) -> list[Fold]:
    """Combinatorial purged cross-validation folds (López de Prado).

    Partition ``index`` into ``n_groups`` contiguous time blocks and, for **every**
    size-``k_test`` combination of blocks, use that combination as the test set and
    the rest as training — after a two-sided purge+embargo (:func:`_forbidden_positions`)
    so no training label overlaps a test block. Yields ``C(n_groups, k_test)`` folds,
    each an honest train/test split; unlike the forward walk, test blocks may sit in
    the interior, which probes many more train/test configurations.

    Parameters
    ----------
    n_groups : number of contiguous time blocks to partition the index into.
    k_test : how many blocks form the test set in each combination (``1 <= k_test < n_groups``).
    horizon, embargo : label horizon to purge against and extra buffer bars, as in
        :func:`walk_forward`.
    """
    if n_groups < 2:
        raise ValueError("n_groups must be >= 2")
    if not 1 <= k_test < n_groups:
        raise ValueError("k_test must satisfy 1 <= k_test < n_groups")
    idx = pd.DatetimeIndex(index)
    n = len(idx)
    if n < n_groups:
        raise ValueError("index is shorter than n_groups")
    groups = np.array_split(np.arange(n), n_groups)
    folds: list[Fold] = []
    for combo in itertools.combinations(range(n_groups), k_test):
        test_pos = np.concatenate([groups[g] for g in combo])
        test_pos.sort()
        forbidden = _forbidden_positions(test_pos, n, horizon, embargo)
        train_pos = np.fromiter((p for p in range(n) if p not in forbidden), dtype=int)
        if len(train_pos) and len(test_pos):
            folds.append(Fold(idx[train_pos], idx[test_pos]))
    return folds


def n_combinatorial_folds(n_groups: int, k_test: int) -> int:
    """Number of folds :func:`combinatorial_purged` produces: ``C(n_groups, k_test)``."""
    return math.comb(n_groups, k_test)


def is_purged(fold: Fold, index: pd.DatetimeIndex, horizon: int, embargo: int = 0) -> bool:
    """True if no training bar falls in any test block's purge/embargo zone.

    The two-sided counterpart of :func:`is_leakage_free`, valid even when test
    blocks are interior (training on both sides). Distances are measured on the
    original ``index`` so absent gap bars do not understate them.
    """
    if not len(fold.train) or not len(fold.test):
        return True
    idx = pd.DatetimeIndex(index)
    test_pos = idx.get_indexer(fold.test)
    train_pos = idx.get_indexer(fold.train)
    forbidden = _forbidden_positions(test_pos, len(idx), horizon, embargo)
    return not any(int(p) in forbidden for p in train_pos)


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
