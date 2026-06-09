import pandas as pd

import prepare


def _prices_single():
    # returns: d1=+0.10, d2=-0.10, d3=+0.10
    idx = pd.date_range("2015-01-01", periods=4, freq="B")
    return pd.DataFrame({"X": [100.0, 110.0, 99.0, 108.9]}, index=idx)


def test_no_same_day_lookahead():
    prices = _prices_single()
    rets = prices.pct_change(fill_method=None)["X"]
    # "cheat" strategy: bet today's known return today (uses day-t close)
    cheat = rets.apply(lambda r: 1.0 if r > 0 else (-1.0 if r < 0 else 0.0))
    weights = pd.DataFrame({"X": cheat})

    net, turnover = prepare._net_returns(weights, prices)

    # weight is clipped to +/-0.5, then LAGGED one day by the engine, so the
    # position held on d2 is the (sign of d1's return) = +0.5, applied to d2's
    # return (-0.10): a LOSS, not the +0.05 same-day foresight would give.
    cost_d2 = (prepare.COST_BPS / 1e4) * 0.5  # turnover entering d2 = |0.5 - 0|
    assert abs(net.iloc[2] - (-0.05 - cost_d2)) < 1e-9
    assert net.iloc[2] < 0.0  # proves foresight was neutralized


def test_transaction_cost_reduces_return():
    prices = _prices_single()
    # churny strategy: flip full position every day
    flip = pd.DataFrame({"X": [0.5, -0.5, 0.5, -0.5]}, index=prices.index)

    net_cost, _ = prepare._net_returns(flip, prices)
    old = prepare.COST_BPS
    try:
        prepare.COST_BPS = 0.0
        net_free, _ = prepare._net_returns(flip, prices)
    finally:
        prepare.COST_BPS = old

    assert net_cost.sum() < net_free.sum()  # cost strictly hurts a churny book
