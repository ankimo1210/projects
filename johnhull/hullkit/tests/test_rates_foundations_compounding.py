"""Hull Table4.1 and Examples4.1/4.2 compounding pins."""

import math

import pytest
from hullkit import _rates_foundations as r


def test_source_all_twelve_values():
    assert [
        r.compound_amount(100, 0.1, 1, frequency=m) for m in [1, 2, 4, 12, 52, 365]
    ] == pytest.approx([110, 110.25, 110.38, 110.47, 110.51, 110.52], abs=0.005)
    assert r.compound_amount(100, 0.1, 1) == pytest.approx(110.52, abs=0.005)
    assert r.convert_rate(0.1, 2, 1) == pytest.approx(0.1025)
    assert r.convert_rate(0.06, 2, 4) == pytest.approx(0.0596, abs=0.00005)
    assert r.convert_rate(0.1, 2, None) == pytest.approx(0.09758, abs=0.000005)
    quarterly = r.convert_rate(0.08, None, 4)
    assert quarterly == pytest.approx(0.0808, abs=0.00005)
    assert quarterly * 1000 / 4 == pytest.approx(20.20, abs=0.005)


def test_independent_growth_units_and_large_frequency_limit():
    continuous = r.convert_rate(0.06, 2, None)
    quarterly = r.convert_rate(0.06, 2, 4)
    assert (1 + 0.06 / 2) ** 2 == pytest.approx(math.exp(continuous))
    assert (1 + 0.06 / 2) ** 2 == pytest.approx((1 + quarterly / 4) ** 4)
    assert r.compound_amount(100, 0.1, 1, frequency=1000000) == pytest.approx(
        100 * math.exp(0.1), rel=1e-8
    )
    with pytest.raises(ValueError):
        r.compound_amount(100, -3, 1, frequency=2)
