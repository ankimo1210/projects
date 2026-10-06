"""Hull 18.3 matching maturities and European cash equivalence."""
import math

import pytest
from hullkit import _futures_options as futures
from scipy.integrate import quad
from scipy.stats import norm


@pytest.mark.parametrize("yield_rate", [0, .05, .12])
def test_matching_maturity_prices_and_each_terminal_state(yield_rate):
    result = futures.spot_futures_equivalence(100, 105, .05, yield_rate, .25, .8, futures_maturity=.8)
    assert result["forward"] == pytest.approx(100*math.exp((.05-yield_rate)*.8))
    assert [result["futures_call"], result["futures_put"]] == pytest.approx([result["spot_call"], result["spot_put"]], abs=1e-12)
    for terminal in [70, 105, 150]:
        ending_future = futures.futures_at_option_expiry(terminal, .05, yield_rate, .8, .8)
        for sign in [-1, 1]:
            assert max(sign*(ending_future-105), 0) == pytest.approx(max(sign*(terminal-105), 0))


@pytest.mark.parametrize("kind", ["call", "put"])
def test_black_input_path_against_independent_spot_terminal_density(kind):
    result = futures.spot_futures_equivalence(100, 105, .05, .02, .25, .8)
    width = .25*math.sqrt(.8)
    log_mean = math.log(100)+(.05-.02-.25**2/2)*.8
    cutoff = (math.log(105)-log_mean)/width
    sign = 1 if kind == "call" else -1
    low, high = (cutoff, 12) if kind == "call" else (-12, cutoff)
    value = math.exp(-.05*.8)*quad(lambda z: max(sign*(math.exp(log_mean+width*z)-105), 0)*norm.pdf(z), low, high, epsabs=1e-10)[0]
    assert result["futures_"+kind] == pytest.approx(value, abs=1e-10)


def test_mismatched_maturities_have_terminal_basis_and_are_not_claimed_equivalent():
    later_future = futures.futures_at_option_expiry(105, .05, .02, .8, 1.2)
    assert later_future > 105
    assert max(later_future-105, 0) > 0
    with pytest.raises(ValueError):
        futures.spot_futures_equivalence(100, 105, .05, .02, .25, .8, futures_maturity=1.2)


def test_deterministic_carry_basis_converges_to_spot_at_futures_maturity():
    spot = 100
    levels = [futures.futures_at_option_expiry(spot, .05, .02, .8, time) for time in [1.2, 1, .8]]
    assert levels[0] > levels[1] > levels[2]
    assert levels[-1] == pytest.approx(spot)
