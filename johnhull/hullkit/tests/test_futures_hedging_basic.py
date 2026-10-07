"""Hull §3.1 source oil/copper hedges and cash-state replication."""

import numpy as np
import pytest
from hullkit import _futures_hedging as h


def test_source_all_eleven_values():
    oil = h.asset_hedge([45, 55], 49, [45, 55], units=1e6, contract_size=1000)
    assert oil["contracts"] == pytest.approx(1000)
    assert oil["per_unit_profit"] == pytest.approx([4, -6])
    assert oil["futures_profit"][0] == pytest.approx(4e6)
    assert oil["net_cash"] == pytest.approx([49e6, 49e6])
    copper = h.asset_hedge(
        [325, 305],
        320,
        [325, 305],
        units=100000,
        contract_size=25000,
        price_unit=0.01,
        obligation="buy",
    )
    assert copper["contracts"] == pytest.approx(4)
    assert copper["futures_profit"] == pytest.approx([5000, -15000])
    assert copper["spot_cash"] == pytest.approx([-325000, -305000])
    assert copper["net_cash"] == pytest.approx([-320000, -320000])


def test_independent_asset_and_contract_cash_vectors():
    states = np.array([10.0, 50.0, 90.0])
    # Short future (-1 underlying plus 49 cash) cancels selling 1 underlying.
    legs = np.array([[1, 0], [-1, 49]])
    expected = np.c_[states, np.ones(3)] @ legs.sum(axis=0)
    a = h.asset_hedge(states, 49, states, units=200, contract_size=10)
    assert a["net_cash"] == pytest.approx(200 * expected)
    buy = h.asset_hedge(states, 49, states, units=200, contract_size=10, obligation="buy")
    assert buy["net_cash"] == pytest.approx(-a["net_cash"])
