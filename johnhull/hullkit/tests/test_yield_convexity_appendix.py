"""Ch30 appendix: exact moment identity and omitted Taylor/variance terms."""

import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.optimize import brentq


def model():
    return importlib.import_module("hullkit._yield_convexity")


def independent_moments(vol, expiry):
    y = 0.06

    def price(yy):
        return 0.06 / (1 + yy) + 0.06 / (1 + yy) ** 2 + 1.06 / (1 + yy) ** 3

    first = -0.06 / (1 + y) ** 2 - 0.12 / (1 + y) ** 3 - 3.18 / (1 + y) ** 4
    second = 0.12 / (1 + y) ** 3 + 0.36 / (1 + y) ** 4 + 12.72 / (1 + y) ** 5
    p = price(y)
    w = -first / p * y * vol * math.sqrt(expiry)

    def offset(z):
        return (
            brentq(lambda yy: price(yy) - p * math.exp(-w * w / 2 + w * z), -0.999, 100, xtol=1e-14)
            - y
        )

    def mean(f):
        return quad(
            lambda z: f(z) * math.exp(-z * z / 2) / math.sqrt(2 * math.pi), -10, 10, epsabs=1e-13
        )[0]

    bias = mean(offset)
    second_moment = mean(lambda z: offset(z) ** 2)
    actual_mean_price = mean(lambda z: p * math.exp(-w * w / 2 + w * z))
    return dict(
        y=y,
        first=first,
        second=second,
        mean_y=y + bias,
        variance=second_moment - bias * bias,
        mean_price=actual_mean_price,
        forward_price=p,
        vol=vol,
        expiry=expiry,
    ), second_moment


@pytest.mark.parametrize("axis", ["vol", "time"])
def test_independent_inverse_price_integral_verifies_each_taylor_approximation(axis):
    residuals = []
    moment_errors = []
    for scale in [1, 0.5, 0.25]:
        vol = 0.22 * scale if axis == "vol" else 0.22
        expiry = 3 if axis == "vol" else 3 * scale * scale
        inputs, second_moment = independent_moments(vol, expiry)
        row = model().convexity_taylor_decomposition(**inputs)
        bias = inputs["mean_y"] - 0.06
        assert row["second_moment"] == pytest.approx(second_moment, rel=1e-12, abs=1e-15)
        assert row["variance_plus_bias_squared"] == pytest.approx(second_moment, abs=1e-15)
        assert abs(row["mean_price_minus_forward"]) < 1e-13
        assert row["linear_term"] == pytest.approx(inputs["first"] * bias, abs=1e-14)
        assert row["quadratic_term"] == pytest.approx(
            0.5 * inputs["second"] * second_moment, abs=1e-14
        )
        assert row["omitted_price_remainder"] == pytest.approx(
            -row["linear_term"] - row["quadratic_term"], abs=1e-13
        )
        assert row["approximated_yield"] == pytest.approx(
            0.06 - 0.5 * 0.06**2 * vol**2 * expiry * inputs["second"] / inputs["first"], abs=1e-14
        )
        residuals.append(abs(row["omitted_price_remainder"]))
        moment_errors.append(abs(row["second_moment"] - row["local_second_moment"]))
    assert residuals[1] < 0.1 * residuals[0] and residuals[2] < 0.1 * residuals[1]
    assert moment_errors[1] < 0.1 * moment_errors[0] and moment_errors[2] < 0.1 * moment_errors[1]


def test_appendix_degenerate_zero_variance_and_known_symmetric_yield_distribution():
    zero = model().convexity_taylor_decomposition(0.06, -2, 9, 0.06, 0, 1, 1, 0.2, 0)
    assert zero["approximated_yield"] == pytest.approx(0.06)
    assert zero["linear_term"] == pytest.approx(0)
    # Independent exact quadratic price, two equiprobable yields.
    y = np.array([0.05, 0.08])
    base = 0.06
    g1 = -2
    g2 = 9
    prices = 1 + g1 * (y - base) + 0.5 * g2 * (y - base) ** 2
    row = model().convexity_taylor_decomposition(
        base, g1, g2, y.mean(), y.var(), prices.mean(), 1, 0.2, 1
    )
    assert row["omitted_price_remainder"] == pytest.approx(0, abs=1e-15)
    assert row["mean_price_minus_forward"] != pytest.approx(0, abs=1e-5)


def test_appendix_invalid_variance_rejected():
    with pytest.raises(ValueError):
        model().convexity_taylor_decomposition(0.06, -2, 9, 0.06, -0.01, 1, 1, 0.2, 1)
