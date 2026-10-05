"""Hull GE section 11.6: the K=10 zero-stock limit and distinct A/B levels."""

import math

import numpy as np
import pytest
from hullkit import _option_properties as props
from hullkit import bsm, fd
from scipy.integrate import quad
from scipy.optimize import brentq


def test_hull_k10_zero_stock_limit_is_not_a_finite_stock_price_pin():
    result = props.exercise_profile([0, .001], 10, .05, .3, 1, kind="put")
    assert result["intrinsic"][0] == pytest.approx(10)
    assert result["american"][0] == pytest.approx(10)
    assert result["european"][0] == pytest.approx(10*math.exp(-.05))
    assert result["american"][1] == pytest.approx(9.999, abs=1e-10)
    assert np.all(result["exercise_now"])


def test_hull_a_b_e_structure_on_a_synthetic_spot_grid():
    spots = np.arange(20, 50.1, .5)
    result = props.exercise_profile(spots, 50, .1, .25, 1, kind="put", steps=500)
    assert np.all(result["american"] >= result["intrinsic"]-1e-10)
    assert np.all(result["american"] >= result["tree_european"]-1e-10)
    american_a = max(spots[result["exercise_now"]])
    european_b = brentq(lambda s: bsm.put_price(s, 50, .1, .25, 1)-(50-s), 1e-6, 50)
    assert american_a < european_b < 50
    # A is a current-price exercise level; it is not the time-varying PDE boundary array.
    pde_at_a = fd.fd_vanilla(american_a, 50, .1, .25, 1, kind="put", american=True, n_s=400, n_t=700)
    pde_at_b = fd.fd_vanilla(european_b, 50, .1, .25, 1, kind="put", american=True, n_s=400, n_t=700)
    assert pde_at_a == pytest.approx(50-american_a, abs=.03)
    assert pde_at_b > 50-european_b+.1


@pytest.mark.parametrize("spot", [20, 35, 45, 50])
def test_put_price_profile_independent_pde_and_grid_refinement(spot):
    coarse = props.exercise_profile([spot], 50, .1, .25, 1, kind="put", steps=300)
    fine = props.exercise_profile([spot], 50, .1, .25, 1, kind="put", steps=600)
    pde = fd.fd_vanilla(spot, 50, .1, .25, 1, kind="put", american=True, n_s=400, n_t=700)
    assert fine["american"][0] == pytest.approx(pde, abs=.015)
    assert coarse["american"][0] == pytest.approx(fine["american"][0], abs=.02)
    if spot == 20:
        def integrand(z):
            terminal = spot*math.exp((.1-.25**2/2)+.25*z)
            return max(50-terminal, 0)*math.exp(-z*z/2)/math.sqrt(2*math.pi)
        split = (math.log(50/spot)-(.1-.25**2/2))/.25
        independent = math.exp(-.1)*quad(integrand, -10, split, epsabs=1e-10)[0]
        assert fine["european"][0] == pytest.approx(independent, abs=1e-9)
        assert fine["european"][0] < 50-spot


@pytest.mark.parametrize("factor", ["spot", "strike", "rate", "volatility"])
def test_american_put_factor_signs_tree_and_pde(factor):
    changes = {"spot": [45, 55], "strike": [45, 55], "rate": [.02, .08], "volatility": [.2, .4]}
    tree_prices, pde_prices = [], []
    for value in changes[factor]:
        params = dict(spot=50, strike=50, rate=.05, volatility=.3, maturity=1)
        params[factor] = value
        tree_prices.append(props.exercise_comparison(**params, kind="put", steps=600)["american"])
        pde_prices.append(fd.fd_vanilla(params["spot"], params["strike"], params["rate"],
                                       params["volatility"], 1, kind="put", american=True, n_s=400, n_t=600))
    sign = -1 if factor in ("spot", "rate") else 1
    assert sign*(tree_prices[1]-tree_prices[0]) > 0
    assert sign*(pde_prices[1]-pde_prices[0]) > 0
    assert tree_prices == pytest.approx(pde_prices, abs=.02)


def test_negative_rate_put_zero_stock_prefers_deferral():
    result = props.exercise_profile([0], 10, -.05, .3, 1, kind="put")
    assert result["american"][0] == pytest.approx(10*math.exp(.05))
    assert not result["exercise_now"][0]
