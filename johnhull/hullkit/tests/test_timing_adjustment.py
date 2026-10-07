"""§30.2 printed timing pins and independent raw Gaussian reweighting."""

import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad


def model():
    return importlib.import_module("hullkit._timing_adjustment")


def test_example_30_2_reproduces_all_four_printed_numbers():
    row = model().timing_adjusted_payment(1200, 0.2, 0.18, -0.4, 0.08, 5, 6, 1.08**-6)
    assert row["factor"] == pytest.approx(1.00535, abs=0.000005)
    assert row["expected_value"] == pytest.approx(1206.42, abs=0.005)
    assert row["payment_discount"] == pytest.approx(0.6302, abs=0.00005)
    assert row["pv"] == pytest.approx(760.25, abs=0.005)


@pytest.mark.parametrize(
    "T,lag,rho,rf,frequency",
    [
        (5, 1, -0.4, 0.08, 1),
        (5, 1, 0.4, 0.08, 1),
        (2, 0.5, -0.7, -0.02, 2),
        (1, 2, 1.0, 0.03, 4),
        (1, 2, -1.0, 0.03, 4),
        (0, 1, 0.4, 0.08, 1),
        (5, 0, -0.4, 0.08, 1),
        (5, 1, 0.0, 0.08, 1),
    ],
)
def test_frozen_ratio_expectation_matches_independent_quadrature_and_raw_mc(
    T, lag, rho, rf, frequency
):
    row = model().timing_adjusted_payment(1200, 0.2, 0.18, rho, rf, T, T + lag, 0.9, frequency)
    loading = -0.18 * rf * lag / (1 + rf / frequency)

    def weight(z):
        return math.exp(loading * math.sqrt(T) * z - 0.5 * loading**2 * T)

    def conditional_value(z):
        return 1200 * math.exp(rho * 0.2 * math.sqrt(T) * z - 0.5 * (rho * 0.2) ** 2 * T)

    integral = quad(
        lambda z: weight(z) * conditional_value(z) * math.exp(-z * z / 2) / math.sqrt(2 * math.pi),
        -11,
        11,
        epsabs=1e-9,
    )[0]
    assert row["expected_value"] == pytest.approx(integral, rel=1e-12)
    assert row["signed_ratio_loading"] == pytest.approx(loading, abs=1e-14)
    rng = np.random.default_rng(3022026)
    z = rng.standard_normal((2, 131072))
    density = model().frozen_ratio_density(z[0] * math.sqrt(T), loading, T)
    values = 1200 * np.exp(
        0.2 * math.sqrt(T) * (rho * z[0] + math.sqrt(1 - rho * rho) * z[1]) - 0.5 * 0.2**2 * T
    )
    for samples, target in [(density, 1), (density * values, row["expected_value"])]:
        se = np.std(samples, ddof=1) / math.sqrt(samples.size)
        assert abs(samples.mean() - target) <= 5 * se + 1e-10
    reversed_row = model().timing_adjusted_payment(
        1200, 0.2, 0.18, -rho, rf, T, T + lag, 0.9, frequency
    )
    assert reversed_row["factor"] * row["factor"] == pytest.approx(1, abs=1e-12)


@pytest.mark.parametrize(
    "args",
    [
        (1200, 0.2, 0.18, -0.4, 0.08, 5, 4, 0.9),
        (1200, 0.2, 0.18, 1.1, 0.08, 5, 6, 0.9),
        (1200, 0.2, 0.18, 0.4, -1, 5, 6, 0.9),
    ],
)
def test_invalid_mathematical_domain_rejected(args):
    with pytest.raises(ValueError):
        model().timing_adjusted_payment(*args)
