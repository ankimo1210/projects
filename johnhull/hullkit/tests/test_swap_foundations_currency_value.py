"""Hull Examples7.2/7.3: exact value rounds .9628, unlike printed .9629."""

import numpy as np
import pytest
from hullkit import _swap_foundations as s

T = np.array([1, 2, 3])
D = np.array([0.4, 0.4, 10.4])
F = np.array([36, 36, 1236])


def test_source_all_twenty_seven_consistent_values_and_final_discrepancy():
    a = s.currency_swap_value_details(T, D, F, 0.025, 0.015, 1 / 110)
    assert a["domestic_cash"] == pytest.approx([-0.4, -0.4, -10.4])
    assert a["foreign_cash"] == pytest.approx([36, 36, 1236])
    assert 1 / 110 == pytest.approx(0.009091, abs=0.0000005)
    assert a["fx_forwards"] == pytest.approx([0.009182, 0.009275, 0.009368], abs=0.0000005)
    assert a["foreign_converted"] == pytest.approx([0.3306, 0.3339, 11.5786], abs=0.00005)
    assert a["net_domestic_cash"] == pytest.approx([-0.0694, -0.0661, 1.1786], abs=0.00005)
    assert a["present_values"] == pytest.approx([-0.0677, -0.0629, 1.0934], abs=0.00005)
    assert a["domestic_bond_pvs"] == pytest.approx([0.3901, 0.3805, 9.6485], abs=0.00005)
    assert a["foreign_bond_pvs"] == pytest.approx([35.46, 34.94, 1181.61], abs=0.005)
    assert a["domestic_bond_pvs"].sum() == pytest.approx(10.4191, abs=0.00005)
    assert a["foreign_bond_pvs"].sum() == pytest.approx(1252.01, abs=0.005)
    assert a["value"] == pytest.approx(0.9627879765, abs=1e-10)
    assert abs(a["value"] - 0.9629) > 0.00005


def test_independent_foreign_bond_cash_and_cip_conversion():
    a = s.currency_swap_value_details(T, D, F, 0.025, 0.015, 1 / 110)
    foreign_bond = sum(float(cash) * np.exp(-0.015 * int(t)) for cash, t in zip(F, T, strict=True))
    domestic_bond = sum(float(cash) * np.exp(-0.025 * int(t)) for cash, t in zip(D, T, strict=True))
    assert a["value"] == pytest.approx(foreign_bond / 110 - domestic_bond, abs=1e-12)
    forward_cash = F * a["fx_forwards"] - D
    assert np.dot(forward_cash, np.exp(-0.025 * T)) == pytest.approx(a["value"])
    assert s.currency_swap_value_details(T, D, F, 0.025, 0.015, 1 / 110, receive="domestic")[
        "value"
    ] == pytest.approx(-a["value"])
