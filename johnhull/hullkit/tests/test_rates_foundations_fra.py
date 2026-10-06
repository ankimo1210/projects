"""Hull §4.9 numerical FRA examples and independent replication."""

import math

import pytest
from hullkit import _rates_foundations as r


def test_source_both_fra_amounts():
    cash = r.fra_settlement(1e8, 0.03, 0.035, 0.25, receive="floating")
    assert cash["end_payment"] == pytest.approx(125000)
    assert r.fra_contract_value(1e8, 0.058, 0.05, 1.5, 2, 0.04) == pytest.approx(369200, abs=50)


def test_independent_two_zero_bond_replication_and_advance_cash_growth():
    p2 = math.exp(-0.04 * 2)
    p1 = p2 * (1 + 0.05 * 0.5)
    # Fixed repayment bond minus deposit-funded floating repayment (including principal).
    replication = 1e8 * ((1 + 0.058 * 0.5) * p2 - p1)
    value = r.fra_contract_value(1e8, 0.058, 0.05, 1.5, 2, 0.04)
    assert value == pytest.approx(replication, abs=1e-7)
    assert r.fra_contract_value(
        1e8, 0.058, 0.05, 1.5, 2, 0.04, receive="floating"
    ) == pytest.approx(-value)
    cash = r.fra_settlement(1e8, 0.03, 0.035, 0.25, receive="floating")
    assert cash["advance_payment"] * (1 + 0.035 * 0.25) == pytest.approx(cash["end_payment"])
    assert r.fra_contract_value(1e8, 0.05, 0.05, 1.5, 2, 0.04) == pytest.approx(0, abs=1e-9)
