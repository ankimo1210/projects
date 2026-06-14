"""Backtest-layer tests: no train/test leakage, cost/turnover, a hand-computed
engine example, and metric correctness.

The headline invariant is leakage-freedom: with overlapping ``horizon`` labels,
every training label must be knowable before its test block starts (purge +
embargo). The engine must also never earn a same-bar return (weights are lagged).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from quantkit import backtest as B


def _idx(n=120):
    return pd.bdate_range("2020-01-01", periods=n)


# --- walk-forward split: purge + embargo, no leakage --------------------------
def test_walk_forward_folds_are_leakage_free():
    idx = _idx(120)
    folds = B.walk_forward(idx, train=40, test=10, horizon=5, embargo=2, mode="expanding")
    assert len(folds) >= 3
    for f in folds:
        assert B.is_leakage_free(f, idx, horizon=5)
        assert f.train[-1] < f.test[0]  # chronological
        assert f.train.intersection(f.test).empty  # disjoint
        assert f.train[0] == idx[0]  # expanding -> always from the start


def test_embargo_widens_the_train_test_gap():
    idx = _idx(120)
    tight = B.walk_forward(idx, train=40, test=10, horizon=5, embargo=0)[0]
    wide = B.walk_forward(idx, train=40, test=10, horizon=5, embargo=10)[0]
    gap_tight = idx.get_loc(tight.test[0]) - idx.get_loc(tight.train[-1])
    gap_wide = idx.get_loc(wide.test[0]) - idx.get_loc(wide.train[-1])
    assert gap_wide > gap_tight


def test_rolling_mode_caps_train_length():
    idx = _idx(120)
    folds = B.walk_forward(idx, train=30, test=10, horizon=0, mode="rolling")
    assert all(len(f.train) <= 30 for f in folds)
    assert folds[-1].train[0] > idx[0]  # window has moved off the start


def test_is_leakage_free_detects_a_leaky_fold():
    idx = _idx(60)
    leaky = B.Fold(train=idx[0:50], test=idx[52:60])  # only a 2-bar gap
    assert not B.is_leakage_free(leaky, idx, horizon=5)  # labels reach into test


# --- costs / turnover ---------------------------------------------------------
def test_turnover_and_cost():
    idx = _idx(3)
    w = pd.DataFrame({"X": [1.0, 1.0, 0.0], "Y": [0.0, 0.0, 1.0]}, index=idx)
    tov = B.turnover(w)
    assert tov.tolist() == [1.0, 0.0, 2.0]  # enter X (1); no change; X->Y (2)
    cm = B.CostModel(cost_bps=10.0, slippage_bps=0.0)
    assert cm.per_unit == pytest.approx(0.001)
    assert B.turnover(w).pipe(cm.on_turnover).tolist() == pytest.approx([0.001, 0.0, 0.002])


def test_cost_model_from_config():
    cm = B.CostModel.from_config({"execution": {"cost_bps": 5, "slippage_bps": 2}})
    assert cm.per_unit == pytest.approx(7 / 1e4)


# --- engine: hand-computed ----------------------------------------------------
def test_engine_lags_weights_and_charges_costs():
    idx = _idx(4)
    weights = pd.DataFrame({"X": [1.0, 1.0, 0.0, 0.0], "Y": [0.0, 0.0, 1.0, 1.0]}, index=idx)
    returns = pd.DataFrame(
        {"X": [0.10, 0.05, 0.00, 0.00], "Y": [0.00, 0.20, 0.10, 0.30]}, index=idx
    )
    res = B.run_backtest(weights, returns, cost_model=B.CostModel(10.0, 0.0), lag=1)
    # d0 dropped (no held weights yet). Decision at d0 (X=1) earns d1 return (0.05),
    # NOT d0's 0.10 -> proves no same-bar look-ahead.
    assert res.gross_returns.iloc[0] == pytest.approx(0.05)
    assert res.gross_returns.iloc[-1] == pytest.approx(0.30)  # held Y earns 0.30
    assert res.turnover.tolist() == pytest.approx([1.0, 0.0, 2.0])
    assert res.costs.iloc[-1] == pytest.approx(0.002)
    assert res.returns.tolist() == pytest.approx([0.049, 0.0, 0.298])
    assert res.total_return == pytest.approx(1.049 * 1.0 * 1.298 - 1.0)


def test_buy_and_hold_baseline_runs():
    idx = _idx(10)
    returns = pd.DataFrame({"A": np.full(10, 0.01), "B": np.full(10, 0.02)}, index=idx)
    bh = B.buy_and_hold(returns)
    # equal weight, no costs -> daily return ~ mean of 0.01 and 0.02
    assert bh.returns.iloc[0] == pytest.approx(0.015)
    assert bh.total_return > 0


# --- metrics ------------------------------------------------------------------
def test_sharpe_and_annualized_return():
    r = pd.Series([0.01] * 252)  # constant daily 1%, zero vol
    assert B.annualized_return(r, periods=252) == pytest.approx(1.01**252 - 1)
    assert np.isnan(B.sharpe(r))  # zero variance -> undefined


def test_sharpe_of_known_noisy_series():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.0005, 0.01, 2520))
    s = B.sharpe(r, periods=252)
    # mean/std*sqrt(252) ~ (0.0005/0.01)*sqrt(252) ~ 0.79, sample-dependent
    assert 0.3 < s < 1.3


def test_max_drawdown_known_path():
    # equity 1 -> 1.2 -> 0.9 -> ... worst dd = 0.9/1.2 - 1 = -0.25
    rets = pd.Series([0.2, -0.25, 0.1])
    assert B.max_drawdown(rets) == pytest.approx(0.9 / 1.2 - 1)


def test_compare_table_has_strategy_columns():
    idx = _idx(60)
    returns = pd.DataFrame({"A": np.full(60, 0.01), "B": np.full(60, -0.005)}, index=idx)
    w = pd.DataFrame({"A": np.full(60, 1.0), "B": np.full(60, 0.0)}, index=idx)
    strat = B.run_backtest(w, returns)
    base = B.buy_and_hold(returns)
    table = B.compare({"strategy": strat, "equal_weight": base}, periods=252)
    assert list(table.columns) == ["strategy", "equal_weight"]
    assert "sharpe" in table.index and "max_drawdown" in table.index
