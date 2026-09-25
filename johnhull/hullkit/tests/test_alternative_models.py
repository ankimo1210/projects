"""Hull 11e Global Edition §27.1: alternative-model pricing checks."""

import math

import numpy as np
import pytest
from hullkit import alternative_models, bsm
from scipy.integrate import quad
from scipy.special import ndtr
from scipy.stats import gamma as gamma_dist
from scipy.stats import poisson


def test_cev_bsm_limit_parity_and_skew():
    args = (100.0, 100.0, 0.05, 0.20, 0.5)
    assert alternative_models.cev_price(*args, beta=1.0) == pytest.approx(
        bsm.call_price(*args), abs=1e-12
    )
    for beta in (0.8, 1.2):
        sigma = 0.2 * 100.0 ** (1.0 - beta)
        prices = [
            alternative_models.cev_price(100.0, strike, 0.05, sigma, 0.5, beta=beta)
            for strike in (80.0, 100.0, 120.0)
        ]
        assert all(value >= 0 for value in prices)
        put = alternative_models.cev_price(100.0, 100.0, 0.05, sigma, 0.5, beta=beta, kind="put")
        assert prices[1] - put == pytest.approx(100.0 - 100.0 * math.exp(-0.025), abs=1e-9)
    for beta in (0.99, 1.01):
        sigma = 0.2 * 100.0 ** (1.0 - beta)
        assert alternative_models.cev_price(
            100.0, 120.0, 0.05, sigma, 0.5, beta=beta
        ) == pytest.approx(bsm.call_price(100.0, 120.0, 0.05, 0.2, 0.5), abs=0.05)


def test_cev_numerically_stable_near_beta_one():
    reference = bsm.call_price(100.0, 120.0, 0.05, 0.2, 0.5)
    for beta in (1 - 1e-6, 1 + 1e-6):
        got = alternative_models.cev_price(100, 120, 0.05, 0.2 * 100 ** (1 - beta), 0.5, beta)
        assert math.isfinite(got) and got > 0
        assert got == pytest.approx(reference, abs=1e-4)


def _merton_conditional_reference(spot, strike, rate, sigma, expiry, intensity, mean, jump_vol):
    """Original Poisson law, conditional lognormal payoff; no Hull reweighting."""
    jump_mean = math.exp(mean + jump_vol**2 / 2) - 1
    result = 0.0
    for count in range(50):
        width = math.sqrt(sigma**2 * expiry + count * jump_vol**2)
        log_mean = (
            math.log(spot) + (rate - intensity * jump_mean - sigma**2 / 2) * expiry + count * mean
        )
        d2 = (log_mean - math.log(strike)) / width
        conditional = math.exp(log_mean + width**2 / 2) * ndtr(d2 + width) - strike * ndtr(d2)
        result += poisson.pmf(count, intensity * expiry) * conditional
    return math.exp(-rate * expiry) * result


def test_merton_independent_conditional_and_limits():
    for strike in (75.0, 100.0, 125.0):
        got = alternative_models.merton_jump_price(100.0, strike, 0.05, 0.2, 0.25, 1.0, -0.1, 0.15)
        want = _merton_conditional_reference(100.0, strike, 0.05, 0.2, 0.25, 1.0, -0.1, 0.15)
        assert got == pytest.approx(want, abs=1e-10)
    assert alternative_models.merton_jump_price(
        100.0, 100.0, 0.05, 0.2, 1.0, 0.0, -0.1, 0.15
    ) == pytest.approx(bsm.call_price(100.0, 100.0, 0.05, 0.2, 1.0), abs=1e-12)


def test_merton_and_vg_dividend_put_call_parity():
    forward_pv = 100 * math.exp(-0.03 * 0.5) - 105 * math.exp(-0.05 * 0.5)
    for price in (
        lambda kind: alternative_models.merton_jump_price(
            100, 105, 0.05, 0.2, 0.5, 0.8, -0.1, 0.15, 0.03, kind=kind
        ),
        lambda kind: alternative_models.variance_gamma_price(
            100, 105, 0.05, 0.2, 0.5, 0.5, 0.1, 0.03, kind=kind
        ),
    ):
        assert price("call") - price("put") == pytest.approx(forward_pv, abs=1e-10)


def test_hull_table_27_1_poisson_counts():
    expected = [0.3679, 0.3679, 0.1839, 0.0613, 0.0153, 0.0031, 0.0005, 0.0001, 0.0]
    got = poisson.pmf(np.arange(9), 0.5 * 2.0)
    assert np.round(got, 4).tolist() == expected
    assert poisson.cdf(8, 1.0) == pytest.approx(1.0, abs=2e-6)


def test_vg_independent_gamma_integral_and_bsm_limit():
    spot, rate, sigma, expiry, nu, theta = 100.0, 0.02, 0.2, 0.5, 0.5, 0.1
    omega = math.log(1 - theta * nu - 0.5 * sigma**2 * nu) / nu
    for strike in (80.0, 100.0, 120.0):

        def conditional(g, strike=strike):
            width = sigma * math.sqrt(g)
            mean = math.log(spot) + (rate + omega) * expiry + theta * g
            d2 = (mean - math.log(strike)) / width
            return math.exp(-rate * expiry) * (
                math.exp(mean + width**2 / 2) * ndtr(d2 + width) - strike * ndtr(d2)
            )

        reference = quad(
            lambda g: conditional(g) * gamma_dist.pdf(g, a=expiry / nu, scale=nu),
            0,
            math.inf,
            epsabs=1e-9,
            epsrel=1e-9,
        )[0]
        got = alternative_models.variance_gamma_price(spot, strike, rate, sigma, expiry, nu, theta)
        assert got == pytest.approx(reference, abs=2e-4)
    assert alternative_models.variance_gamma_price(
        spot, spot, rate, sigma, expiry, 0.0, theta
    ) == pytest.approx(bsm.call_price(spot, spot, rate, sigma, expiry), abs=1e-12)


@pytest.mark.parametrize(
    "func,args",
    [
        ("cev_price", (100, 100, 0.05, 0.2, 1.0, 0.8)),
        ("merton_jump_price", (100, 100, 0.05, 0.2, 1.0, 0.5, -0.1, 0.15)),
        ("variance_gamma_price", (100, 100, 0.05, 0.2, 1.0, 0.5, -0.1)),
    ],
)
def test_invalid_option_kind(func, args):
    with pytest.raises(ValueError, match="kind"):
        getattr(alternative_models, func)(*args, kind="binary")


def test_vg_moment_condition():
    with pytest.raises(ValueError, match="moment"):
        alternative_models.variance_gamma_price(100, 100, 0.0, 0.2, 1.0, 1.0, 1.0)


def test_model_parameter_domains():
    with pytest.raises(ValueError, match="beta"):
        alternative_models.cev_price(100, 100, 0.05, 0.2, 0.5, 0)
    with pytest.raises(ValueError, match="intensity"):
        alternative_models.merton_jump_price(100, 100, 0.05, 0.2, 0.5, -0.1, -0.1, 0.15)
    with pytest.raises(ValueError, match="nu"):
        alternative_models.variance_gamma_price(100, 100, 0.05, 0.2, 0.5, -0.1, 0.1)


def test_vg_small_clock_variance_tends_to_bsm():
    got = alternative_models.variance_gamma_price(100, 100, 0.02, 0.2, 0.5, 0.001, 0.1)
    reference = bsm.call_price(100, 100, 0.02, 0.2, 0.5)
    assert math.isfinite(got)
    assert got == pytest.approx(reference, abs=0.02)


def test_vg_extreme_clock_shape_rejects_material_drift_instead_of_wrong_bsm_limit():
    with pytest.raises(ValueError, match="shape"):
        alternative_models.variance_gamma_price(100, 100, 0.02, 0.2, 0.5, 1e-12, 1e6)
