"""Tests for hullkit.rates against Hull 11e Ch.4 tables."""

import numpy as np
import pytest
from hullkit import rates

# Hull Table 4.3: (maturity, annual coupon on face 100 semiannual, price)
TABLE_4_3 = [
    (0.25, 0.0, 99.6),
    (0.50, 0.0, 99.0),
    (1.00, 0.0, 97.8),
    (1.50, 4.0, 102.5),
    (2.00, 5.0, 105.0),
]


def test_compounding_conversions():
    assert rates.to_continuous(0.10, 2) == pytest.approx(0.097580, abs=1e-5)  # Hull 9.758%
    for m in (1, 2, 4, 12):
        round_trip = rates.from_continuous(rates.to_continuous(0.07, m), m)
        assert round_trip == pytest.approx(0.07, abs=1e-12)


def test_bond_price_and_yield_table_4_2():
    times = [0.5, 1.0, 1.5, 2.0]
    cfs = [3.0, 3.0, 3.0, 103.0]
    zeros = [0.050, 0.058, 0.064, 0.068]
    p = rates.bond_price(times, cfs, zeros)
    assert p == pytest.approx(98.385, abs=5e-3)  # Hull 98.39
    assert rates.bond_yield(times, cfs, p) == pytest.approx(0.0676, abs=2e-4)


def test_bootstrap_table_4_3():
    times, zeros = rates.bootstrap_zero_curve(TABLE_4_3)
    assert times == [0.25, 0.5, 1.0, 1.5, 2.0]
    expected = [0.016032, 0.020101, 0.022245, 0.022845, 0.024162]
    for got, want in zip(zeros, expected, strict=True):
        assert got == pytest.approx(want, abs=5e-5)


def test_forward_rate_and_fra():
    assert rates.forward_rate(0.03, 1.0, 0.04, 2.0) == pytest.approx(0.05, abs=1e-12)
    v = rates.fra_value(100e6, 0.058, 0.050, 1.5, 2.0, 0.040)
    assert v == pytest.approx(369_246.5, abs=1.0)  # Hull ~369,200


def test_duration_convexity_table_4_6():
    times = np.arange(0.5, 3.01, 0.5)
    cfs = [5.0] * 5 + [105.0]
    y = 0.12
    b = rates.bond_price(times, cfs, y)
    assert b == pytest.approx(94.213, abs=5e-3)
    d = rates.macaulay_duration(times, cfs, y)
    assert d == pytest.approx(2.653, abs=2e-3)
    # dB ~ -B D dy (Hull eq. 4.12)
    dy = 0.001
    actual = rates.bond_price(times, cfs, y + dy) - b
    assert actual == pytest.approx(-b * d * dy, abs=1e-3)
    # convexity improves the approximation for a large move
    dy = 0.02
    actual = rates.bond_price(times, cfs, y + dy) - b
    approx_lin = -b * d * dy
    c = rates.convexity(times, cfs, y)
    approx_conv = -b * d * dy + 0.5 * c * b * dy**2
    assert abs(actual - approx_conv) < abs(actual - approx_lin)


def test_bootstrap_coverage_gap_raises():
    # 2.0y coupon bond (semiannual) follows only a 0.25y zero:
    # coupon dates 0.5, 1.0, 1.5 are not covered by the 0.25y node -> ValueError
    instruments = [
        (0.25, 0.0, 99.6),  # zero-coupon at 0.25y
        (2.00, 5.0, 105.0),  # coupon bond whose intermediate dates are uncovered
    ]
    with pytest.raises(ValueError, match="not covered"):
        rates.bootstrap_zero_curve(instruments)


def test_zero_interp_flat_extrapolation():
    assert rates.zero_interp(0.10, [0.25, 1.0], [0.02, 0.03]) == pytest.approx(0.02)
    assert rates.zero_interp(5.00, [0.25, 1.0], [0.02, 0.03]) == pytest.approx(0.03)
    assert rates.zero_interp(0.625, [0.25, 1.0], [0.02, 0.03]) == pytest.approx(0.025)


def test_discount_and_forward_helpers_on_flat_curve():
    curve = ([0.25, 1.0, 5.0], [0.03, 0.03, 0.03])
    assert rates.discount_factor(0.0, curve) == 1.0
    assert rates.discount_factor(2.0, curve) == pytest.approx(np.exp(-0.06), abs=1e-14)
    assert rates.forward_discount(1.0, 2.0, curve) == pytest.approx(np.exp(-0.03), abs=1e-14)
    assert rates.instantaneous_forward(0.0, curve) == pytest.approx(0.03, abs=1e-10)
    assert rates.instantaneous_forward(2.0, curve) == pytest.approx(0.03, abs=1e-10)


def test_new_curve_helpers_reject_invalid_inputs():
    with pytest.raises(ValueError, match="strictly increasing"):
        rates.discount_factor(1.0, ([1.0, 0.5], [0.02, 0.03]))
    with pytest.raises(ValueError, match="0 <= start <= end"):
        rates.forward_discount(2.0, 1.0, ([1.0, 2.0], [0.02, 0.03]))
    with pytest.raises(ValueError, match="bump"):
        rates.instantaneous_forward(1.0, ([1.0], [0.02]), bump=0.0)
