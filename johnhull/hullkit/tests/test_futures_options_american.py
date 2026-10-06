"""Hull 18.10 American spot/futures ordering and independent PDE prices."""
import math

import pytest
from hullkit import _futures_options as futures
from hullkit.fd import fd_vanilla


@pytest.mark.parametrize("yield_rate", [0, .06, .12])
def test_source_carry_ordering_and_four_prices_against_independent_cn_pde(yield_rate):
    result = futures.american_spot_futures_comparison(100, 100, .06, yield_rate, .25, 1, 1200)
    forward = 100*math.exp(.06-yield_rate)
    for kind in ["call", "put"]:
        spot_pde = fd_vanilla(100, 100, .06, .25, 1, q=yield_rate, kind=kind, american=True, n_s=400, n_t=700)
        futures_pde = fd_vanilla(forward, 100, .06, .25, 1, q=.06, kind=kind, american=True, n_s=400, n_t=700)
        assert result["spot_"+kind] == pytest.approx(spot_pde, abs=.005)
        assert result["futures_"+kind] == pytest.approx(futures_pde, abs=.005)
        assert result["spot_european_"+kind] == pytest.approx(result["futures_european_"+kind], abs=1e-11)
    if yield_rate < .06:
        assert result["futures_call"] > result["spot_call"]
        assert result["futures_put"] < result["spot_put"]
    elif yield_rate > .06:
        assert result["futures_call"] < result["spot_call"]
        assert result["futures_put"] > result["spot_put"]
    else:
        assert [result["futures_call"], result["futures_put"]] == pytest.approx([result["spot_call"], result["spot_put"]], abs=1e-12)


@pytest.mark.parametrize("yield_rate", [0, .12])
def test_source_later_futures_expiry_ordering_in_a_synthetic_example(yield_rate):
    same = futures.american_spot_futures_comparison(100, 100, .06, yield_rate, .25, 1, 800)
    later = futures.american_spot_futures_comparison(100, 100, .06, yield_rate, .25, 1, 800, futures_maturity=1.5)
    for kind in ["call", "put"]:
        assert abs(later["futures_"+kind]-later["spot_"+kind]) > abs(same["futures_"+kind]-same["spot_"+kind])
        assert abs(later["futures_european_"+kind]-later["spot_european_"+kind]) > .5
    expected_forward = 100*math.exp((.06-yield_rate)*1.5)
    assert later["forward"] == pytest.approx(expected_forward)


def test_deterministic_boundary_agrees_with_discounted_grid_cash():
    result = futures.american_spot_futures_comparison(100, 100, .06, 0, 0, 1, 20)
    forward = 100*math.exp(.06)
    spot_cash = [math.exp(-.06*j/20)*max(100*math.exp(.06*j/20)-100, 0) for j in range(21)]
    futures_cash = [math.exp(-.06*j/20)*max(forward-100, 0) for j in range(21)]
    assert [result["spot_call"], result["futures_call"]] == pytest.approx([max(spot_cash), max(futures_cash)])


def test_futures_cannot_expire_before_the_option():
    with pytest.raises(ValueError):
        futures.american_spot_futures_comparison(100, 100, .06, 0, .25, 1, futures_maturity=.5)


def test_later_futures_expiry_changes_only_the_futures_leg():
    same = futures.american_spot_futures_comparison(100, 100, .06, .02, .25, 1, 400)
    later = futures.american_spot_futures_comparison(100, 100, .06, .02, .25, 1, 400, futures_maturity=1.5)
    assert later["spot_call"] == pytest.approx(same["spot_call"], abs=1e-12)
    assert later["forward"] == pytest.approx(100*math.exp(.04*1.5), abs=1e-12)
    from scipy.stats import norm
    f0 = 100*math.exp(.04*1.5)
    d1 = (math.log(f0/100)+.25**2/2)/.25
    black = math.exp(-.06)*(f0*norm.cdf(d1)-100*norm.cdf(d1-.25))
    assert later["futures_european_call"] == pytest.approx(black, abs=1e-12)
