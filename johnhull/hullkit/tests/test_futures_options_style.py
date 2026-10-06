"""Hull 18.11 futures-style quotes, optional stopping and variation cash."""
import math
from fractions import Fraction
from itertools import pairwise

import pytest
from hullkit import _futures_options as futures
from hullkit._binomial_foundations import small_tree_stopping_values
from scipy.integrate import quad
from scipy.stats import norm


@pytest.mark.parametrize("kind", ["call", "put"])
def test_source_quote_is_ordinary_premium_compounded_and_independent_of_rate(kind):
    result = futures.futures_style_details(20, 20, .25, 4/12)
    for rate in [-.02, 0, .09, .2]:
        premium = futures.black_details(20, 20, rate, .25, 4/12)[kind]
        assert result[kind+"_quote"] == pytest.approx(premium*math.exp(rate*4/12), abs=1e-14)
    assert result["initial_premium_cash"] == pytest.approx(0)
    # Derived on reused example inputs, not a printed Hull pin.
    assert result["put_quote"] == pytest.approx(1.1506, abs=5e-5)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_quote_against_independent_undiscounted_payoff_integral(kind):
    width = .25*math.sqrt(4/12)
    log_mean = math.log(23)-width**2/2
    cutoff = (math.log(20)-log_mean)/width
    sign = 1 if kind == "call" else -1
    low, high = (cutoff, 12) if kind == "call" else (-12, cutoff)
    reference = quad(lambda z: max(sign*(math.exp(log_mean+width*z)-20), 0)*norm.pdf(z), low, high, epsabs=1e-11)[0]
    assert futures.futures_style_details(23, 20, .25, 4/12)[kind+"_quote"] == pytest.approx(reference, abs=1e-11)


def test_source_parity_and_convex_quote_above_intrinsic():
    for forward in [10, 20, 30]:
        result = futures.futures_style_details(forward, 20, .25, 4/12)
        assert result["put_quote"]+forward == pytest.approx(result["call_quote"]+20, abs=1e-13)
        assert result["call_quote"] >= max(forward-20, 0)-1e-13
        assert result["put_quote"] >= max(20-forward, 0)-1e-13


@pytest.mark.parametrize("kind", ["call", "put"])
def test_no_strictly_better_early_exercise_against_independent_all_stopping_policies(kind):
    result = futures.futures_style_exercise_comparison(23, 20, .25, 4/12, 3, kind=kind)
    up = math.exp(.25*math.sqrt((4/12)/3))
    reference = small_tree_stopping_values(23, 20, 0, 4/12, 3, up, 1/up, q=0, kind=kind)
    assert result["american_quote"] == pytest.approx(reference["price"], abs=1e-13)
    assert result["american_quote"] == pytest.approx(result["european_tree_quote"], abs=1e-13)
    assert not result["exercise_now"]


def test_zero_volatility_or_expiry_has_intrinsic_quote_and_exercise_ties():
    for sigma, time in [(0, .5), (.25, 0)]:
        result = futures.futures_style_exercise_comparison(23, 20, sigma, time, 3)
        assert [result["american_quote"], result["european_quote"]] == pytest.approx([3, 3])
        assert not result["exercise_now"]


def test_daily_quote_changes_against_independent_fraction_settlement_ledger():
    quotes = [Fraction(3, 2), Fraction(7, 4), Fraction(5, 4), Fraction(3)]
    cash = [futures.futures_style_variation_cash(float(a), float(b), quantity=2, multiplier=100) for a, b in pairwise(quotes)]
    independent = [float(2*100*(b-a)) for a, b in pairwise(quotes)]
    assert cash == pytest.approx(independent)
    assert sum(cash) == pytest.approx(float(2*100*(quotes[-1]-quotes[0])))


def test_deep_in_the_money_futures_style_tie_is_not_strict_early_exercise():
    # Every node is in the money, so continuation equals intrinsic up to rounding.
    result = futures.futures_style_exercise_comparison(27000, 1000, .25, .25, 3)
    assert result["american_quote"] == pytest.approx(result["european_tree_quote"], rel=1e-14)
    assert result["exercise_now"] is False
