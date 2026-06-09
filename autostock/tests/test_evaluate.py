import numpy as np
import pandas as pd

import prepare


def _synthetic_prices():
    # daily prices 2011-06 .. 2026-06 for all 7 names, reproducible random walk
    idx = pd.bdate_range("2011-06-01", "2026-06-09")
    rng = np.random.default_rng(0)
    data = {}
    for t in prepare.UNIVERSE:
        steps = rng.normal(0.0005, 0.02, size=len(idx))
        data[t] = 100.0 * np.exp(np.cumsum(steps))
    return pd.DataFrame(data, index=idx)


def _equal_weight(prices):
    n = len(prices.columns)
    return pd.DataFrame(1.0 / n, index=prices.index, columns=prices.columns)


def test_lockbox_withheld_by_default():
    prices = _synthetic_prices()
    m = prepare.evaluate(_equal_weight(prices), prices)
    assert "lockbox_sharpe" not in m
    assert "sharpe" in m and np.isfinite(m["sharpe"])
    assert "train_sharpe" in m


def test_lockbox_revealed_on_flag():
    prices = _synthetic_prices()
    m = prepare.evaluate(_equal_weight(prices), prices, reveal_lockbox=True)
    assert "lockbox_sharpe" in m and np.isfinite(m["lockbox_sharpe"])


def test_rolling_and_annual_present():
    prices = _synthetic_prices()
    m = prepare.evaluate(_equal_weight(prices), prices)
    for k in ("roll_sharpe_mean", "roll_sharpe_min", "roll_sharpe_pos_frac"):
        assert k in m and np.isfinite(m[k])
    assert isinstance(m["annual_sharpe"], dict) and len(m["annual_sharpe"]) > 5
