"""Hull GE section 13.11: carry changes probabilities, not domestic discount."""

import math

import pytest
from hullkit import _binomial_foundations as foundations
from hullkit.bsm import call_price
from hullkit.trees import binomial_tree, crr_params, crr_price


@pytest.mark.parametrize("spot,strike,rate,q,sigma,maturity,n,kind,american,coefficients,stock_pins,option_pins,tolerance", [
    (810, 800, .05, .02, .2, .5, 2, "call", False,
     [1.1052, .9048, 1.0075, .5126],
     [[810], [895.19, 732.92], [989.34, 810, 663.17]],
     [[53.39], [100.66, 5.06], [189.34, 10, 0]], .005),
    (.61, .6, .05, .07, .12, .25, 3, "call", True,
     [1.0352, .9660, .9983, .4673],
     [[.61], [.632, .589], [.654, .610, .569], [.677, .632, .589, .550]],
     [[.019], [.033, .007], [.054, .015, 0], [.077, .032, 0, 0]], .0005),
    (31, 30, .05, .05, .3, .75, 3, "put", True,
     [1.1618, .8607, 1, .4626],
     [[31], [36.02, 26.68], [41.85, 31, 22.97], [48.62, 36.02, 26.68, 19.77]],
     [[2.84], [.93, 4.54], [0, 1.76, 7.03], [0, 0, 3.32, 10.23]], .005),
])
def test_hull_other_assets_all_nodes_against_direct_state_or_stopping_sums(spot, strike, rate, q, sigma, maturity, n, kind, american, coefficients, stock_pins, option_pins, tolerance):
    dt = maturity/n
    moments = foundations.crr_moments(sigma, dt, rate-q)
    up, down = moments["up"], moments["down"]
    assert [up, down, moments["mean"], moments["probability"]] == pytest.approx(coefficients, abs=.00005, rel=0)
    stock, option = binomial_tree(spot, strike, rate, maturity, n, up, down, q=q, kind=kind, american=american)
    for t in range(n+1):
        assert stock[t] == pytest.approx(stock_pins[t], abs=tolerance, rel=0)
        assert option[t] == pytest.approx(option_pins[t], abs=tolerance, rel=0)
        if t < n:
            evaluator = foundations.small_tree_stopping_values if american else foundations.terminal_binomial_value
            for j, state in enumerate(stock[t]):
                independent = evaluator(state, strike, rate, dt*(n-t), n-t, up, down, q=q, kind=kind)
                assert option[t][j] == pytest.approx(independent["price"], abs=1e-10)
    assert moments["probability"]*up+(1-moments["probability"])*down == pytest.approx(math.exp((rate-q)*dt), abs=1e-12)


def test_index_european_refinement_converges_to_dividend_bsm():
    up, down = crr_params(.2, .5/2000)
    direct = foundations.terminal_binomial_value(810, 800, .05, .5, 2000, up, down, q=.02)
    assert direct["price"] == pytest.approx(float(call_price(810, 800, .05, .2, .5, q=.02)), abs=.02)
    assert direct["price"] == pytest.approx(crr_price(810, 800, .05, .2, .5, 2000, q=.02), abs=1e-9)
    assert direct["weights"] @ direct["stock"] == pytest.approx(810*math.exp(.03*.5), abs=1e-8)


def test_futures_zero_drift_still_requires_domestic_discounting():
    up, down = crr_params(.3, .75/3)
    values = [foundations.terminal_binomial_value(31, 30, rate, .75, 3, up, down, kind="put", q=rate) for rate in [0, .05, .15]]
    for rate, value in zip([0, .05, .15], values, strict=True):
        assert value["weights"] @ value["stock"] == pytest.approx(31, abs=1e-12)
        assert value["price"] == pytest.approx(values[0]["price"]*math.exp(-rate*.75), abs=1e-12)
        assert value["probability"] == pytest.approx(values[0]["probability"], abs=1e-12)
    assert values[-1]["price"] < values[0]["price"]
