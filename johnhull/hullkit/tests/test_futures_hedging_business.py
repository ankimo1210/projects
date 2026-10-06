"""Hull §3.2 source hedge loss and separate operating cash flows."""

import pytest
from hullkit import _futures_hedging as h


def test_source_ten_million_loss():
    a = h.business_hedge_profit(100e6, 1e6, 49, 59, pass_through=0, hedge_cash=-10e6)
    assert a["hedge_cash"] == pytest.approx(-10e6)
    assert h.asset_hedge(59, 49, 59, units=1e6, contract_size=1000)[
        "futures_profit"
    ] == pytest.approx(-10e6)


def test_independent_business_cash_scenarios():
    for transfer in [0, 1]:
        low = h.business_hedge_profit(1000, 10, 49, 49, pass_through=transfer, hedge_cash=0)
        high = h.business_hedge_profit(1000, 10, 49, 59, pass_through=transfer, hedge_cash=100)
        cash_ledger = [1000 + transfer * 100, -590, 100]
        assert high["hedged_profit"] == pytest.approx(sum(cash_ledger))
        # With full cost transfer, hedging introduces sensitivity to the input.
        assert high["hedged_profit"] - low["hedged_profit"] == pytest.approx(100 * transfer)
