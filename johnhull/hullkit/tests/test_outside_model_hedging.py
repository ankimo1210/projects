"""One-factor pricing permits multiple external curve/vol hedge shocks."""

import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.stats import norm


def model():
    return importlib.import_module("hullkit._outside_model_hedging")


def quote():
    return dict(
        expiry=1.0,
        payment_times=np.array([2.0, 3.0]),
        accruals=np.ones(2),
        fixed_rate=0.06,
        kind="receiver",
        notional=100.0,
    )


def independent_price(z, s):
    E = 1.0
    a = 0.1
    pay = np.array([2.0, 3.0])
    cash = np.array([0.06, 1.06])
    pe = math.exp(-z[0])
    ps = np.exp(-pay * np.asarray(z[1:]))
    variance = quad(lambda u: s[0] ** 2 * math.exp(-2 * a * (E - u)), 0, E)[0]
    loadings = np.array([quad(lambda u: math.exp(-a * u), 0, t - E)[0] for t in pay])
    sd = math.sqrt(variance)

    def bond(x):
        return float(cash @ (ps / pe * np.exp(-loadings * sd * x - 0.5 * variance * loadings**2)))

    boundary = brentq(lambda x: bond(x) - 1, -30, 30)
    return (
        100 * pe * quad(lambda x: max(bond(x) - 1, 0) * norm.pdf(x), -12, boundary, epsabs=1e-12)[0]
    )


def test_multiple_external_shocks_in_one_factor_pricer_and_same_model_price():
    m = model()
    z = np.array([0.03, 0.035, 0.04])
    s = np.array([0.01, 0.02])
    dirs = np.array([[1, -1], [1, 0], [1, 1]])
    row = m.outside_model_sensitivities(
        [quote()], [1, 2, 3], z, 0.1, [0, 1.5, 3], s, dirs, np.eye(2)
    )
    assert row["pricing_factors"] == 1
    assert row["curve_buckets"] == 3
    assert row["vol_buckets"] == 2
    assert np.count_nonzero(abs(row["curve"]["bucket_delta_cash"]) > 1e-8) == 3
    assert row["value"] == pytest.approx(independent_price(z, s), abs=1e-10)
    assert row["curve"]["unique_gamma_count"] == 6
    assert row["vol"]["pca_vega_per_point"][1] == pytest.approx(0, abs=1e-12)


def test_deterministic_receiver_cashflow_bucket_pv01_and_gamma_independent_analytic():
    m = model()
    z = np.array([0.03, 0.035, 0.04])
    bump = 1e-4
    row = m.outside_model_sensitivities(
        [quote()], [1, 2, 3], z, 0.1, [0, 3], [0], np.eye(3), np.eye(1), rate_bump=bump
    )
    t = np.array([1, 2, 3])
    c = np.array([-100, 6, 106])
    values = c * np.exp(-t * z)
    expected_delta = -t * values * bump
    expected_gamma = np.diag(t * t * values)
    assert row["value"] == pytest.approx(values.sum(), abs=1e-12)
    assert row["curve"]["bucket_delta_cash"] == pytest.approx(expected_delta, rel=2e-8)
    assert row["curve"]["hessian"] == pytest.approx(expected_gamma, abs=0.0001)
    assert row["vol"]["parallel_vega_per_point"] == pytest.approx(0, abs=1e-12)


def test_stochastic_delta_gamma_vega_independent_payoff_quadrature():
    m = model()
    z = np.array([0.03, 0.035, 0.04])
    s = np.array([0.01])
    h = 1e-4
    row = m.outside_model_sensitivities(
        [quote()], [1, 2, 3], z, 0.1, [0, 3], s, np.eye(3), np.eye(1), rate_bump=h, vol_bump=h
    )
    base = independent_price(z, s)
    for i in range(3):
        shock = np.eye(3)[i] * h
        up = independent_price(z + shock, s)
        down = independent_price(z - shock, s)
        assert row["curve"]["bucket_delta_cash"][i] == pytest.approx((up - down) / 2, abs=2e-10)
        assert row["curve"]["hessian"][i, i] == pytest.approx(
            (up - 2 * base + down) / h**2, abs=0.0001
        )
    vega = (independent_price(z, s + h) - independent_price(z, s - h)) / (2 * h) * 0.01
    assert row["vol"]["parallel_vega_per_point"] == pytest.approx(vega, abs=2e-9)


def test_external_curve_shape_and_vol_environment_remain_distinct():
    m = model()
    z = np.array([0.03, 0.035, 0.04])
    s = np.array([0.01, 0.012])
    q = quote()
    base = m.gaussian_environment_price([q], [1, 2, 3], z, 0.1, [0, 2, 3], s)
    slope = m.gaussian_environment_price(
        [q], [1, 2, 3], z + np.array([-0.001, 0, 0.001]), 0.1, [0, 2, 3], s
    )
    vol = m.gaussian_environment_price([q], [1, 2, 3], z, 0.1, [0, 2, 3], s + 0.001)
    assert abs(slope - base) > 0.01
    assert vol > base
    with pytest.raises(ValueError):
        m.gaussian_environment_price([q], [1, 1, 3], z, 0.1, [0, 3], [0.01])


def test_atm_zero_sigma_has_positive_one_sided_vega():
    q = dict(
        expiry=1.0,
        payment_times=[2.0],
        accruals=[1.0],
        fixed_rate=math.expm1(0.04),
        kind="payer",
        notional=100.0,
    )
    row = model().outside_model_sensitivities(
        [q], [1, 2], [0.04, 0.04], 0.1, [0, 2], [0], np.eye(2), np.eye(1), vol_bump=0.0001
    )
    b = quad(lambda u: math.exp(-0.1 * u), 0, 1)[0]
    kernel = quad(lambda u: math.exp(-0.2 * (1 - u)), 0, 1)[0]
    exact = 100 * math.exp(-0.04) * b * math.sqrt(kernel) / math.sqrt(2 * math.pi) * 0.01
    assert row["vol"]["parallel_vega_per_point"] == pytest.approx(exact, rel=1e-8)
