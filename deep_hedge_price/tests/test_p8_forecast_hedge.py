"""P8 train-only mean retransformation and forecast-sensitive common-path cash."""

import math

import numpy as np
import pytest
from hullkit import bsm

from deep_hedge_price import frontier_reference as f
from deep_hedge_price import hedge_capstone as h


def test_log_mean_retransformation_fitted_only_to_training_residuals():
    result, factor = f._mean_log_forecast(np.array([-0.3, 0.3]), np.zeros(2), np.array([0.0, 1.0]))
    assert factor == pytest.approx(math.cosh(0.3), abs=1e-14)
    assert result == pytest.approx(np.array([1, math.e]) * math.cosh(0.3), abs=1e-14)
    assert f._mean_log_forecast(np.ones(2), np.ones(2), np.array([0.0]))[0] == pytest.approx(
        [1], abs=1e-14
    )


def test_forecast_vol_changes_the_hedge_without_changing_paths_or_fair_premium():
    config = dict(path_volatility=0.2, maturity=5 / 252, n_paths=256, n_steps=8, seed=830)
    low, a = h._forecast_hedge_case(forecast_volatility=0.12, **config)
    high, b = h._forecast_hedge_case(forecast_volatility=0.4, **config)
    assert a["spot"] == pytest.approx(b["spot"], abs=1e-13)
    assert a["premium"] == pytest.approx(bsm.call_price(100, 100, 0, 0.2, 5 / 252), abs=1e-12)
    assert low.pnl["no hedge"] == pytest.approx(high.pnl["no hedge"], abs=1e-12)
    assert np.mean(np.abs(low.pnl["delta"] - high.pnl["delta"])) > 0.01
    names = a["strategy_names"]
    for i, name in enumerate(names):
        stock = a["stock_positions"][i]
        options = a["option_positions"][i]
        moves = np.diff(a["spot"], axis=1)
        option_moves = np.diff(a["secondary_price"], axis=1)
        trades = np.diff(np.column_stack([np.zeros(256), stock]), axis=1)
        option_trades = np.diff(np.column_stack([np.zeros(256), options]), axis=1)
        turnover = (np.abs(trades) * a["spot"][:, :-1]).sum(axis=1)
        turnover += (np.abs(option_trades) * a["secondary_price"][:, :-1]).sum(axis=1)
        turnover += np.abs(stock[:, -1]) * a["spot"][:, -1]
        cash = a["premium"] + (stock * moves).sum(axis=1) + (options * option_moves).sum(axis=1)
        cash -= np.maximum(a["spot"][:, -1] - 100, 0) + h.DEFAULT_TRANSACTION_COST * turnover
        assert low.pnl[name] == pytest.approx(cash, abs=1e-11)
        assert low.turnover[name] == pytest.approx(turnover, abs=1e-11)
