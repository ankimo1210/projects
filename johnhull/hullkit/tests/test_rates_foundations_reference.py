"""Hull §4.2 formula: source has no numerical example."""

from decimal import Decimal

import numpy as np
import pytest
from hullkit import _rates_foundations as r


def test_source_formula_on_explicit_synthetic_weekend_example():
    a = r.compounded_reference_rate([0.01, 0.012, 0.011], [1, 3, 1])
    expected = ((1 + 0.01 / 360) * (1 + 0.012 * 3 / 360) * (1 + 0.011 / 360) - 1) * 360 / 5
    assert a["annualized_rate"] == pytest.approx(expected)
    assert a["days"] == pytest.approx(5)


def test_independent_decimal_reinvestment_and_constant_rate_law():
    capital = Decimal(1)
    for rate, days in [("0.01", 1), ("0.012", 3), ("0.011", 1)]:
        capital += capital * Decimal(rate) * Decimal(days) / Decimal(360)
    a = r.compounded_reference_rate([0.01, 0.012, 0.011], [1, 3, 1])
    assert a["growth"] == pytest.approx(float(capital), abs=1e-14)
    assert r.compounded_reference_rate(np.full(30, 0.04), np.ones(30))["growth"] == pytest.approx(
        (1 + 0.04 / 360) ** 30, abs=1e-13
    )
