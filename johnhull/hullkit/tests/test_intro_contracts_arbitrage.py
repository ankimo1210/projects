"""Hull §1.9 dual-market trade and independent currency-balance replication."""

import numpy as np
import pytest
from hullkit import _intro_contracts as c


def test_source_cross_market_profit():
    a = c.cross_market_cashflows(100, 120, 100, 1.23)
    assert a["net_cash"] == pytest.approx(300)
    assert [
        a["domestic_purchase"],
        a["foreign_proceeds"],
        a["converted_proceeds"],
    ] == pytest.approx([-12000, 10000, 12300])


def test_independent_two_currency_balance_solve_and_currency_units():
    q, buy, sell, fx, usd_fee, gbp_fee = 100, 120, 100, 1.23, 70, 25
    a = c.cross_market_cashflows(q, buy, sell, fx, fee_domestic=usd_fee, fee_foreign=gbp_fee)
    # Unknown USD profit and GBP sold in FX. Both currency balances close.
    profit, gbp_sold = np.linalg.solve([[1, -fx], [0, 1]], [-q * buy - usd_fee, q * sell - gbp_fee])
    assert [a["net_cash"], a["foreign_proceeds"]] == pytest.approx([profit, gbp_sold])
    pence = c.cross_market_cashflows(
        q, buy, 100 * sell, fx / 100, fee_domestic=usd_fee, fee_foreign=100 * gbp_fee
    )
    assert pence["net_cash"] == pytest.approx(profit)
    assert c.cross_market_cashflows(q, buy, sell, fx, fee_domestic=400)["net_cash"] < 0
