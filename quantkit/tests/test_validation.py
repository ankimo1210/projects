"""Validation-rigor tests: purged combinatorial CV and MDA feature importance.

Combinatorial purged CV (López de Prado) generalizes the forward walk: it tests on
*every* size-``k`` combination of time blocks, purging train observations whose
label window overlaps a test block and embargoing a buffer after each. Because a
test block can sit in the *interior* of the timeline, the purge is two-sided.

MDA (mean-decrease-accuracy) importance permutes one feature inside each fold's
test set and measures the out-of-sample score drop — a feature that truly drives
the label loses score when shuffled; a noise feature does not.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from quantkit import backtest as B
from quantkit import models as MD


def _idx(n=120):
    return pd.bdate_range("2020-01-01", periods=n)


# --- combinatorial purged CV --------------------------------------------------
def test_combinatorial_purged_count_is_n_choose_k():
    idx = _idx(120)
    folds = B.combinatorial_purged(idx, n_groups=6, k_test=2, horizon=5, embargo=2)
    assert len(folds) == math.comb(6, 2)  # 15 test combinations


def test_combinatorial_purged_folds_are_disjoint():
    idx = _idx(120)
    for f in B.combinatorial_purged(idx, n_groups=5, k_test=2, horizon=3, embargo=1):
        assert f.train.intersection(f.test).empty
        assert len(f.test) > 0 and len(f.train) > 0


def test_combinatorial_purged_respects_two_sided_purge():
    idx = _idx(150)
    horizon, embargo = 5, 3
    folds = B.combinatorial_purged(idx, n_groups=6, k_test=2, horizon=horizon, embargo=embargo)
    # at least one fold must have an interior test block (train both before and after)
    interior = [f for f in folds if f.train[0] < f.test[0] and f.train[-1] > f.test[-1]]
    assert interior, "combinatorial CV should produce interior test blocks"
    for f in folds:
        assert B.is_purged(f, idx, horizon=horizon, embargo=embargo)


def test_is_purged_detects_a_two_sided_leak():
    idx = _idx(80)
    # interior test block at positions 40..49; horizon=5 purges train positions
    # 35..39 (their 5-bar labels reach into the block), embargo=2 purges 50..51.
    test = idx[40:50]
    leaky = B.Fold(train=idx[0:39].union(idx[55:80]), test=test)  # pos 38 in purge zone
    assert not B.is_purged(leaky, idx, horizon=5, embargo=2)
    clean = B.Fold(train=idx[0:35].union(idx[55:80]), test=test)  # train ends at 34, resumes 55
    assert B.is_purged(clean, idx, horizon=5, embargo=2)


# --- MDA feature importance ---------------------------------------------------
def _design_with_one_real_feature(n_dates=160, n_assets=25, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2019-01-01", periods=n_dates)
    assets = [f"A{i:02d}" for i in range(n_assets)]
    a = pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    b = pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    noise = pd.DataFrame(
        0.3 * rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets
    )
    label = a + noise  # label is driven by feature 'a', not 'b'
    X, y = MD.make_design({"a": a, "b": b}, label)
    return X, y, dates


def test_mda_ranks_the_real_feature_above_noise():
    X, y, dates = _design_with_one_real_feature()
    folds = B.walk_forward(dates, train=80, test=20, horizon=1, embargo=1)
    imp = MD.mda_importance(MD.ridge, X, y, folds, n_repeats=5, random_state=0)
    assert set(imp.index) == {"a", "b"}
    assert "importance" in imp.columns
    # the real feature loses much more score when permuted than the noise feature
    assert imp.loc["a", "importance"] > imp.loc["b", "importance"]
    assert imp.loc["a", "importance"] > 0.0
    assert imp.loc["b", "importance"] < imp.loc["a", "importance"] * 0.5


def test_mda_is_deterministic_given_seed():
    X, y, dates = _design_with_one_real_feature()
    folds = B.walk_forward(dates, train=80, test=20, horizon=1, embargo=1)
    a = MD.mda_importance(MD.ridge, X, y, folds, n_repeats=3, random_state=42)
    b = MD.mda_importance(MD.ridge, X, y, folds, n_repeats=3, random_state=42)
    pd.testing.assert_frame_equal(a, b)
