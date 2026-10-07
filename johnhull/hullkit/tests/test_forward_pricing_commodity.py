"""Hull Example5.8 storage costs and consumption-asset bounds."""

import math

import pytest
from hullkit import _forward_pricing as f


def test_source_two_storage_values():
    a = f.storage_forward(450, [1], [2], [0.07], 0.07, 1)
    assert a["storage_pv"] == pytest.approx(1.865, abs=0.0005)
    assert a["carry_forward"] == pytest.approx(484.63, abs=0.005)


def test_independent_financed_spot_plus_terminal_storage_and_convenience():
    a = f.storage_forward(450, [1], [2], [0.07], 0.07, 1, consumption=True)
    assert a["carry_forward"] == pytest.approx(450 * math.exp(0.07) + 2)
    assert a["relation"] == "upper_bound"
    quote = 450 * math.exp((0.07 + 0.01 - 0.02) * 1)
    y = f.implied_convenience_yield(450, quote, 0.07, 0.01, 1)
    assert y == pytest.approx(0.02)
    assert quote < 450 * math.exp(0.08)
