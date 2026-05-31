import numpy as np
import pandas as pd
from stockkit.analysis import technical as t


def test_sma_simple_average_and_nan_count():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    out = t.sma(s, window=3)
    # first window-1 values are NaN, then the simple moving average
    assert out.iloc[:2].isna().all()
    np.testing.assert_allclose(out.iloc[2:].to_numpy(), [2.0, 3.0, 4.0])


def test_ema_hand_computed_span2():
    s = pd.Series([1, 2, 3], dtype=float)
    out = t.ema(s, window=2)  # alpha = 2/(2+1) = 2/3, adjust=False
    np.testing.assert_allclose(out.to_numpy(), [1.0, 5 / 3, 23 / 9])


def test_rsi_bounds_and_extremes():
    # strictly increasing -> no losses -> RSI undefined (NaN)
    inc = pd.Series(range(1, 9), dtype=float)
    assert np.isnan(t.rsi(inc).iloc[-1])
    # strictly decreasing -> no gains -> RSI == 0
    dec = pd.Series(range(8, 0, -1), dtype=float)
    assert t.rsi(dec).iloc[-1] == 0.0
    # mixed series stays within [0, 100]
    mixed = pd.Series([1, 2, 1, 3, 2, 4, 3, 5], dtype=float)
    r = t.rsi(mixed).dropna()
    assert ((r >= 0) & (r <= 100)).all()


def test_macd_hist_is_macd_minus_signal():
    s = pd.Series(np.linspace(100, 120, 60))
    m = t.macd(s)
    assert list(m.columns) == ["macd", "signal", "hist"]
    np.testing.assert_allclose(m["hist"], m["macd"] - m["signal"])


def test_bollinger_band_symmetry():
    s = pd.Series(np.linspace(100, 120, 30))
    bb = t.bollinger(s, window=20, k=2.0)
    valid = bb.dropna()
    np.testing.assert_allclose(valid["upper"] - valid["mid"], valid["mid"] - valid["lower"])


def test_atr_non_negative(ohlcv):
    a = t.atr(ohlcv, window=3)
    assert (a.dropna() >= 0).all()


def test_returns_simple_and_log():
    s = pd.Series([100.0, 110.0])
    np.testing.assert_allclose(t.returns(s).iloc[-1], 0.1)
    np.testing.assert_allclose(t.returns(s, log=True).iloc[-1], np.log(1.1))


def test_add_indicators_appends_expected_columns(ohlcv):
    out = t.add_indicators(ohlcv)
    for col in [
        "sma20", "sma50", "sma200", "ema20", "rsi14",
        "macd", "macd_signal", "macd_hist",
        "bb_mid", "bb_upper", "bb_lower", "atr14",
    ]:
        assert col in out.columns


def test_golden_cross_values_in_domain():
    # uptrending series produces a +1 golden cross with small windows
    s = pd.Series([10, 9, 8, 7, 9, 11, 13, 15, 17, 19], dtype=float)
    sig = t.signal_golden_cross(pd.DataFrame({"close": s}), fast=2, slow=3)
    assert set(sig.unique()).issubset({-1, 0, 1})
    assert (sig == 1).any()
