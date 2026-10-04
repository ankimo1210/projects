"""Independent kernels and conditional identities for private §28.4 APIs."""

import math

import numpy as np
import pytest
from hullkit._numeraire_choices import (
    FlatHW,
    annuity_statistics,
    annuity_values,
    bond,
    joint_moments,
    ou_moments,
    rate_statistics,
    sample_joint,
    stock_statistics,
)
from scipy.integrate import quad


@pytest.mark.parametrize(
    "a,eta,h", [(0.2, 0.02, 2.0), (1e-8, 0.03, 1e-7), (3.0, 0.1, 5.0), (0.2, 0.0, 2.0)]
)
def test_moments_match_independent_kernels_and_preserve_rank_two(a, eta, h):
    model = FlatHW(a, eta, -0.01)

    def kx(u):
        return eta * math.exp(-a * u)

    def ki(u):
        return eta * (-math.expm1(-a * u)) / a

    actual = ou_moments(h, model)
    expected = [
        quad(lambda u: kx(u) ** 2, 0, h)[0],
        quad(lambda u: ki(u) ** 2, 0, h)[0],
        quad(lambda u: kx(u) * ki(u), 0, h)[0],
        quad(kx, 0, h)[0],
        quad(ki, 0, h)[0],
    ]
    np.testing.assert_allclose(actual, expected, rtol=2e-13, atol=1e-35)
    _mean, cov = joint_moments(0, h, 0, model)
    np.testing.assert_allclose(cov @ np.array([1.0, a, -eta]), 0.0, atol=1e-16)
    assert np.linalg.eigvalsh(cov).min() >= -1e-15
    assert bond(0, h, 0, model) == pytest.approx(math.exp(0.01 * h), abs=1e-14)


@pytest.mark.parametrize(
    "loading,price,futures",
    [
        (0.25, 16.371618639526922, 109.37244366983968),
        (-0.25, 14.457903895380923, 107.46647739330601),
        (0.0, 3.262096905703644, 108.41527219490550),
    ],
)
def test_same_stock_payoff_measures_and_wrong_measure_control(loading, price, futures):
    row = stock_statistics(0, 2, 0, 100, 105, loading, FlatHW())
    assert row["price_q"] == pytest.approx(price, abs=3e-12)
    assert row["price_payment"] == pytest.approx(price, abs=3e-12)
    assert row["futures"] == pytest.approx(futures, abs=3e-12)
    assert row["forward"] == pytest.approx(108.32870676749582, abs=3e-12)
    assert abs(row["price_wrong_q_outer_discount"] - price) > 0.05


@pytest.mark.parametrize(
    "t,x", [(0, 0), (0.25, -0.015), (0.25, 0.02), (0.75, -0.015), (0.75, 0.02)]
)
@pytest.mark.parametrize("zero,eta", [(0.04, 0.02), (-0.01, 0.02), (0.04, 0.0)])
def test_conditional_payment_and_annuity_martingales(t, x, zero, eta):
    model = FlatHW(0.2, eta, zero)
    row = rate_statistics(t, 1, 1.5, x, model)
    assert row["term_payment"] == pytest.approx(row["forward"], abs=2e-13)
    assert row["overnight_payment"] == pytest.approx(row["forward"], abs=2e-13)
    assert abs(row["fra_pv"]) < 2e-13
    pay = (1.5, 2.0, 2.5, 3.0)
    for basis in (None, (0.01,) * 4):
        row = annuity_statistics(t, 1, pay, x, model, basis)
        sd = math.sqrt(row["state_variance"])
        means = row["component_means"]

        def fn(z, m, sd=sd, basis=basis):
            _, _, rate = annuity_values(1, 1, pay, m + sd * z, model, basis)
            return rate * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)

        expected = sum(
            w * quad(lambda z, m=m: fn(z, m), -11, 11, epsabs=1e-13)[0]
            for w, m in zip(row["weights"], means, strict=True)
        )
        assert expected == pytest.approx(row["rate"], abs=2e-13)
        assert sum(row["weights"]) == pytest.approx(1, abs=1e-15)
    no_basis = annuity_statistics(t, 1, pay, x, model)
    assert no_basis["annuity"] == row["annuity"]


def test_sampler_discount_and_rank_two_and_zero_horizon():
    model = FlatHW()
    samples = sample_joint(0.25, 2, -0.015, model, 131072, 123)
    mean, _cov = joint_moments(0.25, 2, -0.015, model)
    centered = samples - mean
    np.testing.assert_allclose(
        centered[:, 0] + model.a * centered[:, 1] - model.eta * centered[:, 2], 0, atol=3e-17
    )
    discounted = np.exp(-samples[:, 1])
    assert abs(discounted.mean() - bond(0.25, 2, -0.015, model)) < 5 * discounted.std(
        ddof=1
    ) / math.sqrt(len(samples))
    at_zero = sample_joint(0.5, 0.5, 0.02, model, 3, 1)
    np.testing.assert_array_equal(at_zero, [[0.02, 0, 0]] * 3)


@pytest.mark.parametrize(
    "bad",
    [
        True,
        "0.2",
        1j,
        np.nan,
        np.inf,
        np.timedelta64(365, "D"),
        np.datetime64("2026-10-04"),
        [],
        [1.0],
    ],
)
def test_model_rejects_non_scalar_finite_real_and_temporal(bad):
    with pytest.raises(ValueError):
        FlatHW(bad, 0.02, 0.04)
    with pytest.raises(ValueError):
        FlatHW(0.2, bad, 0.04)
    with pytest.raises(ValueError):
        FlatHW(0.2, 0.02, bad)


@pytest.mark.parametrize("args", [(-1, 2, 0), (2, 1, 0), (0, 2, np.timedelta64(1, "D"))])
def test_joint_rejects_invalid_times_and_state(args):
    with pytest.raises(ValueError):
        joint_moments(*args, FlatHW())


def test_schedule_counts_domains_and_overflow_rejected():
    model = FlatHW()
    for pay in [(), (1, 2), (2, 1.5), (1.5, np.inf), (1.5, 1.5)]:
        with pytest.raises(ValueError):
            annuity_statistics(0, 1, pay, 0, model)
    with pytest.raises(ValueError):
        annuity_statistics(0, 1, (1.5, 2), 0, model, (0.01,))
    with pytest.raises(ValueError):
        FlatHW(0, 0.01, 0.04)
    with pytest.raises(ValueError):
        FlatHW(0.2, -0.01, 0.04)
    with pytest.raises(ValueError):
        rate_statistics(0, 1, 1, 0, model)
    with pytest.raises(ValueError):
        sample_joint(0, 1, 0, model, True, 1)
    with pytest.raises(ValueError):
        sample_joint(0, 1, 0, model, 10, -1)
    with pytest.raises(ValueError):
        stock_statistics(0, 1, 0, -100, 105, 0.2, model)
    with pytest.raises(ValueError):
        bond(0, 10000, 0, FlatHW(0.2, 0.02, -1))
