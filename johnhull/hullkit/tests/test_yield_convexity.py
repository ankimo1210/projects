"""§30.1 printed convexity example and an independent inverse-price model."""

import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.optimize import brentq


def model():
    return importlib.import_module("hullkit._yield_convexity")


def g(y):
    return 0.06 / (1 + y) + 0.06 / (1 + y) ** 2 + 1.06 / (1 + y) ** 3


def inverse_price_mean(vol, expiry=3.0):
    y = 0.06
    g1 = -0.06 / (1 + y) ** 2 - 0.12 / (1 + y) ** 3 - 3.18 / (1 + y) ** 4
    w = -g1 / g(y) * y * vol * math.sqrt(expiry)

    def dy(z):
        price = g(y) * math.exp(-0.5 * w * w + w * z)
        return brentq(lambda yy: g(yy) - price, -0.999, 100, xtol=1e-14) - y

    return (
        y
        + quad(
            lambda z: dy(z) * math.exp(-z * z / 2) / math.sqrt(2 * math.pi), -10, 10, epsabs=1e-13
        )[0]
    )


def test_hull_example_30_1_reproduces_all_five_printed_values():
    row = model().yield_linked_payment_pv(
        100, 0.06, 0.22, 3.0, 1.05**-3, [1, 2, 3], [0.06, 0.06, 1.06]
    )
    assert row["first"] == pytest.approx(-2.6730, abs=0.00005)
    assert row["second"] == pytest.approx(9.8910, abs=0.00005)
    assert row["expected_yield"] == pytest.approx(0.06097, abs=0.000005)
    assert row["pv"] == pytest.approx(5.27, abs=0.005)
    assert row["unadjusted_pv"] == pytest.approx(5.18, abs=0.005)
    assert row["first"] == pytest.approx(
        -0.06 / 1.06**2 - 0.12 / 1.06**3 - 3.18 / 1.06**4, abs=1e-13
    )
    assert row["second"] == pytest.approx(
        0.12 / 1.06**3 + 0.36 / 1.06**4 + 12.72 / 1.06**5, abs=1e-13
    )


@pytest.mark.parametrize("frequency", [1, 2, 4])
def test_cashflow_derivatives_match_independent_finite_differences(frequency):
    times = np.arange(1 / frequency, 3.01, 1 / frequency)
    cash = np.full(len(times), 0.05 / frequency)
    cash[-1] += 1

    def value(y):
        return np.sum(cash / (1 + y / frequency) ** (frequency * times))

    y = 0.04
    h = 1e-4
    row = model().bond_value_derivatives(y, times, cash, frequency)
    assert row["price"] == pytest.approx(value(y), abs=1e-14)
    assert row["first"] == pytest.approx((value(y + h) - value(y - h)) / (2 * h), rel=2e-7)
    assert row["second"] == pytest.approx(
        (value(y + h) - 2 * value(y) + value(y - h)) / h**2, rel=2e-7
    )


def test_convexity_bias_matches_independent_price_inversion_to_second_order():
    errors = []
    for vol in [0.22, 0.11, 0.055]:
        row = model().yield_linked_payment_pv(1, 0.06, vol, 3.0, 1, [1, 2, 3], [0.06, 0.06, 1.06])
        exact = inverse_price_mean(vol)
        assert exact > 0.06
        errors.append(abs(exact - row["expected_yield"]))
    assert errors[0] > 1e-7 and errors[1] < 0.08 * errors[0] and errors[2] < 0.08 * errors[1]


def test_figure_30_1_mean_price_yield_differs_from_mean_yield():
    prices = g(0.06) + np.array([-0.1, 0, 0.1])
    yields = [brentq(lambda y, p=p: g(y) - p, -0.5, 1) for p in prices]
    assert np.mean(prices) == pytest.approx(g(0.06), abs=1e-13)
    assert np.mean(yields) > 0.06


def test_cms_par_coupon_bond_approximation_flat_and_nonflat_curve():
    for rates in [[0.06, 0.06, 0.06], [0.03, 0.06, 0.09], [0.09, 0.06, 0.03]]:
        times = np.arange(1, 4)
        discounts = (1 + np.array(rates)) ** -times
        row = model().cms_par_yield_approximation(discounts, np.ones(3), times)
        s = (1 - discounts[-1]) / discounts.sum()
        assert row["swap_rate"] == pytest.approx(s, abs=1e-13)
        assert row["bond_yield"] == pytest.approx(s, abs=1e-12)
        # A fixed 6% bond's yield is not the swap rate on a sloped curve.
        fixed_y = brentq(
            lambda yy, discounts=discounts: g(yy) - (0.06 * discounts.sum() + discounts[-1]),
            -0.5,
            1,
        )
        if np.ptp(rates):
            assert abs(fixed_y - s) > 1e-4
        else:
            assert fixed_y == pytest.approx(s, abs=1e-12)


@pytest.mark.parametrize(
    "call",
    [
        lambda m: m.bond_value_derivatives(-1, [1], [1]),
        lambda m: m.convexity_adjusted_yield(0.06, 0.2, -1, -2, 9),
        lambda m: m.convexity_adjusted_yield(0.06, 0.2, 1, 0, 9),
    ],
)
def test_invalid_mathematical_domain_rejected(call):
    with pytest.raises(ValueError):
        call(model())
