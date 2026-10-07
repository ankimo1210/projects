"""Hull §5.12 symbolic carry cases on explicitly synthetic numerical inputs."""

import math

import pytest
from hullkit import _forward_pricing as f


def test_source_symbolic_cases_and_contract_values():
    for income, storage, convenience in [
        (0, 0, 0),
        (0.01, 0, 0),
        (0.03, 0, 0),
        (0, 0.02, 0),
        (0, 0.02, 0.04),
    ]:
        a = f.cost_of_carry(
            100, 0.05, 2, income_yield=income, storage_yield=storage, convenience_yield=convenience
        )
        expected = 100 * math.exp((0.05 + storage - income - convenience) * 2)
        assert a["forward"] == pytest.approx(expected)
        assert f.forward_value(a["forward"], 105, 0.05, 2) == pytest.approx(
            (expected - 105) * math.exp(-0.1)
        )


def test_independent_borrowed_cash_and_grown_quantity():
    a = f.cost_of_carry(100, 0.05, 2, income_yield=0.03, storage_yield=0.02, convenience_yield=0.01)
    funding = 100 * math.exp(0.05 * 2)
    stored_cost_multiplier = math.exp(0.02 * 2)
    units_multiplier = math.exp(0.03 * 2) * math.exp(0.01 * 2)
    assert a["forward"] == pytest.approx(funding * stored_cost_multiplier / units_multiplier)
    assert a["carry"] == pytest.approx(0.04)
