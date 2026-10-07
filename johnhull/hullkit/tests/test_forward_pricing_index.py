"""Hull Example5.5 index carry and independent basket replication."""

import math

import pytest
from hullkit import _forward_pricing as f


def test_source_index_forward():
    a = f.index_delivery_replication(1300, 0.05, 0.01, 0.25, multiplier=1)
    assert a["forward"] == pytest.approx(1313.07, abs=0.005)


def test_independent_reinvested_index_basket_and_conversion_units():
    a = f.index_delivery_replication(1300, 0.05, 0.01, 0.25, multiplier=5)
    initial_units = 5 / math.exp(0.01 * 0.25)
    purchase = initial_units * 1300
    terminal_units = initial_units * math.exp(0.01 * 0.25)
    terminal_loan = purchase * math.exp(0.05 * 0.25)
    assert a["initial_units"] == pytest.approx(initial_units)
    assert a["delivery_units"] == pytest.approx(terminal_units)
    assert 5 * a["forward"] == pytest.approx(terminal_loan)
    assert f.converted_index_value(1300, 5, 1.2) == pytest.approx(7800)
