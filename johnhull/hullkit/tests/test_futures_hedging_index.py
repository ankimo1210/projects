"""Hull Table3.4, beta targets and stock-picking source calculations."""

import numpy as np
import pytest
from hullkit import _futures_hedging as h


def test_source_all_thirty_seven_values():
    a = h.index_hedge_scenarios(
        5050000,
        1.5,
        1000,
        1010,
        [900, 950, 1000, 1050, 1100],
        [902, 952, 1003, 1053, 1103],
        multiplier=250,
        rate=0.04,
        dividend_yield=0.01,
        maturity=0.25,
    )
    assert a["futures_profit"] == pytest.approx([810000, 435000, 52500, -322500, -697500])
    assert 100 * a["market_return"] == pytest.approx([-9.75, -4.75, 0.25, 5.25, 10.25])
    assert 100 * a["portfolio_return"] == pytest.approx([-15.125, -7.625, -0.125, 7.375, 14.875])
    assert a["portfolio_value"] == pytest.approx(
        [4286187, 4664937, 5043687, 5422437, 5801187], abs=1
    )
    assert a["total_value"] == pytest.approx([5096187, 5099937, 5096187, 5099937, 5103687], abs=1)
    assert a["contract_value"] == pytest.approx(252500)
    assert h.beta_contracts(5050000, 252500, 1)["contracts"] == pytest.approx(20)
    assert a["short_contracts"] == pytest.approx(30)
    assert h.beta_contracts(5050000, 252500, 1.5, target=0.75)["contracts"] == pytest.approx(15)
    assert h.beta_contracts(5050000, 252500, 1.5, target=2)["contracts"] == pytest.approx(-10)
    b = h.beta_contracts(2e6, 105000, 1.1)
    p = h.stock_picking_profit(20000, 100, 90, 2100, 1850, short_contracts=21, multiplier=50)
    assert [
        b["exposure_value"],
        b["contract_value"],
        b["contracts"],
        b["rounded"],
        p["stock_profit"],
        p["futures_profit"],
        p["total_profit"],
    ] == pytest.approx([2e6, 105000, 20.95, 21, -200000, 262500, 62500], abs=0.005)


def test_independent_factor_loading_and_cash_ledger():
    va, vf, beta, target = 5050000, 252500, 1.5, 0.75
    count = h.beta_contracts(va, vf, beta, target=target)["contracts"]
    shock = 0.001
    # Same relative shock, independent factor exposure balance.
    stock_change = va * beta * shock
    future_change = -count * vf * shock
    assert (stock_change + future_change) / (va * shock) == pytest.approx(target)
    p = h.stock_picking_profit(20000, 100, 90, 2100, 1850, short_contracts=21, multiplier=50)
    cash = np.dot([20000, 20000, 21 * 50, 21 * 50], [-100, 90, 2100, -1850])
    assert p["total_profit"] == pytest.approx(cash)
