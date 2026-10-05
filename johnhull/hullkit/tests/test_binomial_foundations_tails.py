"""Hull GE Ch13 appendix: two binomial tails and their distinct limits."""

import math

import numpy as np
import pytest
from hullkit import _binomial_foundations as foundations
from hullkit.bsm import call_price, d1, d2
from hullkit.trees import crr_params, crr_price
from scipy.stats import binom, norm


def test_source_symbolic_decomposition_against_independent_state_sums():
    spot, strike, rate, q, sigma, maturity, n = 20, 21, .04, .015, .3, .5, 20
    up, down = crr_params(sigma, maturity/n)
    states = foundations.terminal_binomial_value(spot, strike, rate, maturity, n, up, down, q=q)
    result = foundations.binomial_call_tails(spot, strike, rate, sigma, maturity, n, q=q)
    exercise = states["stock"] > strike
    u2 = states["weights"][exercise].sum()
    u1 = (states["weights"][exercise]*states["stock"][exercise]).sum()/spot
    assert result["u1"] == pytest.approx(u1, abs=1e-12)
    assert result["u2"] == pytest.approx(u2, abs=1e-12)
    assert result["price"] == pytest.approx(math.exp(-rate*maturity)*(spot*u1-strike*u2), abs=1e-12)
    assert result["price"] == pytest.approx(states["price"], abs=1e-12)
    assert result["price"] == pytest.approx(crr_price(spot, strike, rate, sigma, maturity, n, q=q), abs=1e-12)


@pytest.mark.parametrize("strike,min_ups", [(100, 3), (100*math.exp(.2), 4), (100*math.exp(.2)*(1-1e-7), 3), (100*math.exp(.2)*(1+1e-7), 4)])
def test_strict_integer_exercise_threshold_including_equal_terminal_stock(strike, min_ups):
    result = foundations.binomial_call_tails(100, strike, .05, .2, 1, 4)
    assert result["first_in_the_money_up_moves"] == min_ups
    p = (math.exp(.05/4)-math.exp(-.1))/(math.exp(.1)-math.exp(-.1))
    j = np.arange(min_ups, 5)
    expected_tail = binom.pmf(j, 4, p).sum()
    expected_payoff = math.exp(-.05)*sum(binom.pmf(k, 4, p)*max(100*math.exp((2*k-4)*.1)-strike, 0) for k in j)
    assert result["cash_tail"] == pytest.approx(expected_tail, abs=1e-12)
    assert result["price"] == pytest.approx(expected_payoff, abs=1e-12)


def test_both_tail_terms_converge_to_their_correct_normal_limits():
    spot, strike, rate, q, sigma, maturity = 50, 52, .05, .02, .3, 2
    result = foundations.binomial_call_tails(spot, strike, rate, sigma, maturity, 4000, q=q)
    assert result["cash_tail"] == pytest.approx(norm.cdf(d2(spot, strike, rate, sigma, maturity, q=q)), abs=.012)
    assert result["stock_tail"] == pytest.approx(norm.cdf(d1(spot, strike, rate, sigma, maturity, q=q)), abs=.012)
    assert result["u1"] == pytest.approx(math.exp((rate-q)*maturity)*result["stock_tail"], abs=1e-12)
    assert result["price"] == pytest.approx(float(call_price(spot, strike, rate, sigma, maturity, q=q)), abs=.003)


def test_stock_numeraire_probability_is_not_actual_world_probability():
    result = foundations.binomial_call_tails(20, 21, .04, .3, .25, 1)
    up, down = math.exp(.15), math.exp(-.15)
    p = result["probability"]
    assert result["stock_probability"] == pytest.approx(p*up/(p*up+(1-p)*down), abs=1e-12)
    actual = foundations.physical_comparison(20, 20*up, 20*down, 1, 0, .04, .25, physical_drift=.1)
    assert abs(result["stock_probability"]-actual["physical_probability"]) > .01


def test_zero_strike_and_outside_terminal_support():
    zero = foundations.binomial_call_tails(50, 0, .05, .3, 2, 10, q=.02)
    assert zero["price"] == pytest.approx(50*math.exp(-.04), abs=1e-12)
    high = foundations.binomial_call_tails(50, 10000, .05, .3, 2, 10)
    assert high["price"] == pytest.approx(0, abs=1e-12)
    low = foundations.binomial_call_tails(50, .01, .05, .3, 2, 10)
    assert low["price"] == pytest.approx(50-.01*math.exp(-.1), abs=1e-12)
