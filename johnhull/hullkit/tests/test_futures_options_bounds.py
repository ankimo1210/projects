"""Hull 18.5 bounds, convexity, equalities and deep-ITM limits."""

import math

import pytest
from hullkit import _futures_options as futures
from hullkit._index_currency import carry_exercise_comparison
from scipy.integrate import quad
from scipy.stats import norm


@pytest.mark.parametrize("forward", [60, 100, 140])
def test_zero_volatility_european_equals_discounted_intrinsic_lower_bound(forward):
    bounds = futures.futures_option_bounds(forward, 100, 0.05, 1)
    price = futures.black_details(forward, 100, 0.05, 0, 1)
    assert [price["call"], price["put"]] == pytest.approx(
        [bounds["call_lower"], bounds["put_lower"]]
    )
    assert [bounds["american_call_lower"], bounds["american_put_lower"]] == pytest.approx(
        [max(forward - 100, 0), max(100 - forward, 0)]
    )


def test_european_bounds_remain_valid_at_negative_rates():
    bounds = futures.futures_option_bounds(110, 100, -0.02, 1)
    price = futures.black_details(110, 100, -0.02, 0.2, 1)
    assert bounds["call_lower"] <= price["call"] <= bounds["call_upper"]
    assert bounds["put_lower"] <= price["put"] <= bounds["put_upper"]


def test_deep_itm_source_limit_and_expiry_equalities():
    call = futures.black_details(100, 10, 0.05, 0.1, 1)
    put = futures.black_details(10, 100, 0.05, 0.1, 1)
    lower = 90 * math.exp(-0.05)
    assert [call["call"], put["put"]] == pytest.approx([lower, lower], abs=1e-10)
    at_expiry = futures.futures_option_bounds(100, 100, 0.05, 0)
    assert [at_expiry["call_lower"], at_expiry["put_lower"]] == pytest.approx([0, 0])


@pytest.mark.parametrize("kind", ["call", "put"])
def test_american_tree_above_immediate_intrinsic(kind):
    for forward in [60, 100, 140]:
        bounds = futures.futures_option_bounds(forward, 100, 0.05, 1)
        result = carry_exercise_comparison(forward, 100, 0.05, 0.05, 0.25, 1, 500, kind=kind)
        assert result["american"] >= bounds["american_" + kind + "_lower"] - 1e-10
        assert result["american"] >= result["european_tree_value"] - 1e-10


def test_discounted_jensen_bound_with_independent_terminal_distribution():
    width = 0.25 * math.sqrt(0.8)
    log_mean = math.log(100) - width**2 / 2
    mean = quad(lambda z: math.exp(log_mean + width * z) * norm.pdf(z), -12, 12, epsabs=1e-10)[0]
    expected_payoff = quad(
        lambda z: max(105 - math.exp(log_mean + width * z), 0) * norm.pdf(z),
        -12,
        (math.log(105) - log_mean) / width,
        epsabs=1e-10,
    )[0]
    assert mean == pytest.approx(100, abs=1e-10)
    assert expected_payoff >= max(105 - mean, 0)
    bounds = futures.futures_option_bounds(100, 105, 0.05, 0.8)
    assert math.exp(-0.05 * 0.8) * expected_payoff >= bounds["put_lower"]
