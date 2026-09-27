import numpy as np
import pandas as pd
import pytest
from market_research.backtest import run_backtest, run_prefix_strategy

DATES = pd.date_range("2026-09-21", periods=4, tz="UTC")


def frames():
    weights = pd.DataFrame({"XNAS:ACME": [1.0, 0.0, -1.0, -1.0]}, index=DATES)
    returns = pd.DataFrame({"XNAS:ACME": [np.nan, 0.10, -0.05, 0.02]}, index=DATES)
    return weights, returns


def run_usd_backtest(weights, returns, **kwargs):
    return run_backtest(
        weights,
        returns,
        base_currency="USD",
        return_currencies={"XNAS:ACME": "USD"},
        **kwargs,
    )


def test_lag_one_cost_entry_exit_and_short_from_hand_calculation():
    weights, returns = frames()
    result = run_usd_backtest(weights, returns, commission_bps=6, slippage_bps=4)
    assert result.held_weights["XNAS:ACME"].tolist() == [0.0, 1.0, 0.0, -1.0]
    assert result.turnover.tolist() == [0.0, 1.0, 1.0, 1.0]
    assert result.costs.tolist() == pytest.approx([0.0, 0.001, 0.001, 0.001])
    assert result.net_returns.tolist() == pytest.approx([0.0, 0.099, -0.001, -0.021])
    assert result.equity.iloc[-1] == pytest.approx(1.074845079)


def test_reversal_charges_two_units_of_turnover():
    weights, returns = frames()
    weights.iloc[1, 0] = -1.0
    result = run_usd_backtest(weights, returns, commission_bps=10)
    assert result.turnover.iloc[2] == 2.0
    assert result.costs.iloc[2] == pytest.approx(0.002)


def test_column_loss_is_an_error_not_an_intersection():
    weights, returns = frames()
    with pytest.raises(ValueError, match="asset columns"):
        run_usd_backtest(weights.rename(columns={"XNAS:ACME": "XNAS:OTHER"}), returns)


def test_missing_return_for_held_asset_is_an_error():
    weights, returns = frames()
    returns.iloc[1, 0] = np.nan
    with pytest.raises(ValueError, match="held return"):
        run_usd_backtest(weights, returns)


def test_infinite_return_for_held_asset_is_rejected():
    weights, returns = frames()
    returns.iloc[1, 0] = np.inf
    with pytest.raises(ValueError, match="held return"):
        run_usd_backtest(weights, returns)


def test_missing_return_when_flat_does_not_change_other_days():
    weights, returns = frames()
    returns.iloc[2, 0] = np.nan
    result = run_usd_backtest(weights, returns)
    assert result.gross_returns.iloc[2] == 0.0
    assert result.net_returns.iloc[1] == pytest.approx(0.1)


def test_empty_backtest_is_rejected():
    index = pd.DatetimeIndex([], tz="UTC")
    weights = pd.DataFrame(columns=["XNAS:ACME"], index=index, dtype=float)
    returns = pd.DataFrame(columns=["XNAS:ACME"], index=index, dtype=float)
    with pytest.raises(ValueError, match="empty"):
        run_usd_backtest(weights, returns)


def test_pre_lagged_input_is_rejected_when_declared():
    weights, returns = frames()
    weights.attrs["timing"] = "held"
    with pytest.raises(ValueError, match="unlagged"):
        run_usd_backtest(weights, returns)


def test_prefix_strategy_cannot_observe_future_rows_through_input():
    index = pd.date_range("2026-09-21", periods=3, tz="UTC")
    prices = pd.DataFrame({"XNAS:ACME": [100.0, 101.0, 150.0]}, index=index)
    lengths = []

    def strategy(prefix):
        lengths.append(len(prefix))
        return pd.Series({"XNAS:ACME": float(prefix.iloc[-1, 0] > 100.0)})

    original = run_prefix_strategy(prices, strategy)
    changed = prices.copy()
    changed.iloc[-1, 0] = 1.0
    alternative = run_prefix_strategy(changed, strategy)
    assert lengths == [1, 2, 3, 1, 2, 3]
    assert original.iloc[:2, 0].tolist() == alternative.iloc[:2, 0].tolist() == [0.0, 1.0]
    assert prices.iloc[-1, 0] == 150.0


def test_prefix_strategy_cannot_mutate_the_source_frame():
    prices = pd.DataFrame({"XNAS:ACME": [100.0, 101.0]}, index=DATES[:2])

    def strategy(prefix):
        prefix.iloc[-1, 0] = 999.0
        return pd.Series({"XNAS:ACME": 0.0})

    run_prefix_strategy(prices, strategy)
    assert prices["XNAS:ACME"].tolist() == [100.0, 101.0]


def test_currency_contract_rejects_mixed_or_undeclared_returns():
    weights, returns = frames()
    with pytest.raises(ValueError, match="currency"):
        run_backtest(weights, returns)
    with pytest.raises(ValueError, match="currency"):
        run_backtest(
            weights,
            returns,
            base_currency="USD",
            return_currencies={"XNAS:ACME": "JPY"},
        )
