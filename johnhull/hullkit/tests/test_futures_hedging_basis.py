"""Hull §3.3 all source effective-price examples."""

import numpy as np
import pytest
from hullkit import _futures_hedging as h


def test_source_thirteen_basis_values():
    a = h.basis_hedge(2.5, 2.0, 2.2, 1.9, units=1, contract_size=1)
    assert [a["initial_basis"], a["final_basis"], a["effective_price"]] == pytest.approx(
        [0.3, 0.1, 2.3]
    )
    yen = h.basis_hedge(1.08, 1.02, 1.08, 1.025, units=50e6, contract_size=12.5e6, price_unit=0.01)
    assert [
        yen["contracts"],
        yen["per_unit_profit"] / 0.01,
        yen["final_basis"],
        yen["effective_price"] / 0.01,
        yen["net_cash"],
    ] == pytest.approx([4, 0.055, -0.005, 1.075, 537500])
    oil = h.basis_hedge(48, 50, 48, 49.1, units=20000, contract_size=1000, obligation="buy")
    assert [
        oil["contracts"],
        oil["per_unit_profit"],
        oil["final_basis"],
        oil["effective_price"],
        -oil["net_cash"],
    ] == pytest.approx([20, 1.1, 0.9, 48.9, 978000])


def test_independent_cross_basis_and_physical_cash_ledger():
    s = np.array([50, 52])
    proxy = np.array([49, 51])
    f = np.array([49.1, 50.5])
    a = h.basis_hedge(48, s, 48, f, units=100, contract_size=10, proxy_spot=proxy, obligation="buy")
    paid = 100 * s - 100 * (f - 48)
    assert a["net_cash"] == pytest.approx(-paid)
    assert a["final_basis"] == pytest.approx(a["maturity_basis"] + a["asset_basis"])
    assert a["effective_price"] == pytest.approx(48 + (proxy - f) + (s - proxy))
