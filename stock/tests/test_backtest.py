import numpy as np
import pandas as pd
import pytest
from stockkit.analysis import backtest as bt


@pytest.fixture
def up_prices():
    # +10% per step, with an 'open' column so exec uses open
    idx = pd.date_range("2020-01-01", periods=3, freq="D")
    return pd.DataFrame({"open": [100.0, 110.0, 121.0], "close": [100.0, 110.0, 121.0]}, index=idx)


def test_run_requires_close():
    with pytest.raises(ValueError):
        bt.run(pd.DataFrame({"open": [1, 2, 3]}), lambda d: pd.Series([1, 1, 1]))


def test_always_long_equity_hand_computed(up_prices):
    # day0 flat (signal shifted), days 1-2 long, fee+slippage = 15bps on the entry day
    res = bt.run(up_prices, lambda d: pd.Series(1, index=d.index))
    np.testing.assert_allclose(res.equity.iloc[-1], 1_208_350.0)
    assert set(
        ["total_return", "cagr", "annual_vol", "sharpe", "max_drawdown", "win_rate_daily", "bars"]
    ).issubset(res.metrics.keys())
    assert res.metrics["max_drawdown"] <= 0.0


def test_no_lookahead_last_day_signal_stays_flat(up_prices):
    # A signal that only fires on the last bar cannot be acted on -> equity flat
    sig = pd.Series([0, 0, 1], index=up_prices.index)
    res = bt.run(up_prices, lambda d: sig)
    np.testing.assert_allclose(res.equity.to_numpy(), [1_000_000.0, 1_000_000.0, 1_000_000.0])
    assert res.trades.empty


def test_fees_reduce_terminal_equity(up_prices):
    def _always_long(d):
        return pd.Series(1, index=d.index)

    no_fee = bt.run(up_prices, _always_long, fee_bps=0.0, slippage_bps=0.0)
    with_fee = bt.run(up_prices, _always_long, fee_bps=10.0, slippage_bps=5.0)
    assert no_fee.equity.iloc[-1] > with_fee.equity.iloc[-1]


@pytest.mark.parametrize("name", ["sma_cross", "rsi_reversion", "macd_cross", "donchian"])
def test_preset_signals_produce_binary_series(name, ohlcv):
    sig_fn = bt.PRESETS[name]()
    sig = sig_fn(ohlcv)
    assert len(sig) == len(ohlcv)
    assert set(sig.dropna().unique()).issubset({0, 1})
