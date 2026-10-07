"""RB-F05: independent density integrals and noise-aware digital teacher tests."""

import numpy as np
import pytest
from hullkit import _digital_teachers as dt
from hullkit import bsm, exotics
from scipy.integrate import quad
from scipy.stats import norm


@pytest.mark.parametrize("spot,maturity", [(80.0, 0.05), (100.0, 1 / 3), (120.0, 2.0)])
def test_analytic_matches_existing_binary_and_independent_density(spot, maturity):
    price, delta = dt.analytic(spot, 100, 0.03, 0.2, maturity)
    threshold = (np.log(100 / spot) - (0.03 - 0.2**2 / 2) * maturity) / (0.2 * np.sqrt(maturity))
    discount = np.exp(-0.03 * maturity)
    integral_p = discount * quad(norm.pdf, threshold, np.inf, epsabs=1e-13)[0]
    integral_d = (
        discount
        * quad(
            lambda z: z * norm.pdf(z) / (spot * 0.2 * np.sqrt(maturity)),
            threshold,
            np.inf,
            epsabs=1e-13,
        )[0]
    )
    assert price == pytest.approx(integral_p, abs=2e-12)
    assert delta == pytest.approx(integral_d, abs=2e-12)
    assert price == pytest.approx(exotics.cash_or_nothing(spot, 100, 0.03, 0.2, maturity))
    h = 1e-3
    central = (
        exotics.cash_or_nothing(spot + h, 100, 0.03, 0.2, maturity)
        - exotics.cash_or_nothing(spot - h, 100, 0.03, 0.2, maturity)
    ) / (2 * h)
    assert delta == pytest.approx(central, rel=2e-6, abs=1e-10)


def test_payoff_score_and_crn_use_same_normal_draws():
    z = np.array([-1.2, -0.1, 0.0, 0.2, 1.7])
    values = dt.samples(100, 100, 0.03, 0.2, 0.5, z, bump=0.2, ramp_width=2)
    multiplier = np.exp(0.005 + 0.2 * np.sqrt(0.5) * z)
    payoff = np.exp(-0.015) * (100 * multiplier > 100)
    assert np.allclose(values["payoff"], payoff)
    assert np.allclose(values["lrm"], payoff * z / (100 * 0.2 * np.sqrt(0.5)))
    central = (
        np.exp(-0.015)
        * ((100.2 * multiplier > 100).astype(float) - (99.8 * multiplier > 100))
        / 0.4
    )
    assert np.allclose(values["crn_bump"], central)
    assert np.allclose(values["pathwise"], 0)


@pytest.mark.parametrize("spot,maturity", [(95.0, 0.05), (100.0, 1 / 3), (110.0, 1.0)])
def test_unbiased_teachers_with_fixed_seed_and_six_standard_errors(spot, maturity):
    z = np.random.default_rng(607).standard_normal(160_000)
    values = dt.samples(spot, 100, 0.03, 0.2, maturity, z)
    target_p, target_d = dt.analytic(spot, 100, 0.03, 0.2, maturity)
    for name, target in [
        ("payoff", target_p),
        ("lrm", target_d),
        ("conditional_price", target_p),
        ("conditional_delta", target_d),
    ]:
        mean, se = dt.summarize(values[name])
        assert abs(mean - target) <= 6 * se + 2e-12
    mean, se = dt.summarize(values["crn_bump"])
    h = 0.1
    bumped = (
        dt.analytic(spot + h, 100, 0.03, 0.2, maturity)[0]
        - dt.analytic(spot - h, 100, 0.03, 0.2, maturity)[0]
    ) / (2 * h)
    assert abs(mean - bumped) <= 6 * se + 2e-12
    # Pathwise 0 is a biased negative control, even with zero reported SE.
    assert target_d > 0
    assert dt.summarize(values["pathwise"]) == pytest.approx((0, 0))


def test_full_conditioning_integrates_out_all_randomness_exactly():
    z = np.random.default_rng(72).standard_normal(100)
    values = dt.samples(103, 100, 0.03, 0.2, 0.25, z, conditioning_fraction=0)
    price, delta = dt.analytic(103, 100, 0.03, 0.2, 0.25)
    assert np.allclose(values["conditional_price"], price, atol=1e-14)
    assert np.allclose(values["conditional_delta"], delta, atol=1e-14)


def test_ramp_is_a_different_contract_and_matches_call_spread():
    z = np.random.default_rng(196).standard_normal(240_000)
    spot, maturity, width = 98, 0.05, 8
    values = dt.samples(spot, 100, 0.03, 0.2, maturity, z, ramp_width=width)
    price = (
        bsm.call_price(spot, 100 - width, 0.03, 0.2, maturity)
        - bsm.call_price(spot, 100 + width, 0.03, 0.2, maturity)
    ) / (2 * width)
    delta = (
        bsm.call_delta(spot, 100 - width, 0.03, 0.2, maturity)
        - bsm.call_delta(spot, 100 + width, 0.03, 0.2, maturity)
    ) / (2 * width)
    for name, target in [("ramp_price", price), ("ramp_delta", delta)]:
        mean, se = dt.summarize(values[name])
        assert abs(mean - target) <= 6 * se + 2e-12
    digital_delta = dt.analytic(spot, 100, 0.03, 0.2, maturity)[1]
    assert abs(delta - digital_delta) > 0.005


def test_lrm_variance_matches_independent_second_moment_and_short_time_growth():
    variances = []
    for maturity in [0.01, 0.25]:
        variance = dt.lrm_variance(100, 100, 0.03, 0.2, maturity)
        a = -0.01 * np.sqrt(maturity) / 0.2
        second = quad(
            lambda z, maturity=maturity: (
                (np.exp(-0.03 * maturity) * z / (20 * np.sqrt(maturity))) ** 2 * norm.pdf(z)
            ),
            a,
            np.inf,
        )[0]
        delta = dt.analytic(100, 100, 0.03, 0.2, maturity)[1]
        assert variance == pytest.approx(second - delta**2, rel=1e-10)
        variances.append(variance)
    assert variances[0] > 20 * variances[1]


def test_batched_scenarios_and_standard_errors_keep_units_and_path_axis():
    z = np.random.default_rng(3).standard_normal((2, 1000))
    values = dt.samples(np.array([90, 110]), 100, 0.03, 0.2, np.array([0.1, 1.0]), z)
    assert values["lrm"].shape == (2, 1000)
    mean, se = dt.summarize(values["lrm"])
    assert np.allclose(mean, values["lrm"].mean(axis=-1))
    assert np.allclose(se, values["lrm"].std(axis=-1, ddof=1) / np.sqrt(1000))


@pytest.mark.parametrize(
    "args",
    [
        (0, 100, 0.03, 0.2, 1),
        (100, 0, 0.03, 0.2, 1),
        (100, 100, 0.03, 0, 1),
        (100, 100, 0.03, 0.2, 0),
    ],
)
def test_mathematically_invalid_parameters(args):
    with pytest.raises(ValueError):
        dt.analytic(*args)


def test_meaningless_estimator_controls_are_rejected():
    for kwargs in [
        {"bump": 0},
        {"bump": 100},
        {"ramp_width": 0},
        {"ramp_width": 101},
        {"conditioning_fraction": 1},
    ]:
        with pytest.raises(ValueError):
            dt.samples(100, 100, 0.03, 0.2, 1, np.arange(5), **kwargs)
    with pytest.raises(ValueError):
        dt.summarize(np.array([1.0]))


@pytest.mark.parametrize(
    "spot,maturity,expected",
    [
        (1e-12, 1, 0),
        (1e12, 1, np.exp(-0.03)),
        (99, 1e-10, 0),
        (101, 1e-10, np.exp(-0.03e-10)),
    ],
)
def test_digital_price_limits_and_bounds(spot, maturity, expected):
    price, delta = dt.analytic(spot, 100, 0.03, 0.2, maturity)
    assert price == pytest.approx(expected, abs=1e-12)
    assert 0 <= price <= np.exp(-0.03 * maturity)
    assert delta >= 0 and np.isfinite(delta)
