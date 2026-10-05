"""Hull GE section 11.1: printed baselines, factors and maturity counterexamples."""

import math
from itertools import pairwise

import numpy as np
import pytest
from hullkit import _option_properties as props
from hullkit import fd, trees
from scipy.integrate import quad


def integrated_price(spot, strike, rate, volatility, maturity, kind):
    if maturity == 0 or volatility == 0 or spot == 0 or strike == 0:
        terminal = spot * math.exp(rate * maturity)
        payoff = max(terminal - strike, 0) if kind == "call" else max(strike - terminal, 0)
        return math.exp(-rate * maturity) * payoff
    width = volatility * math.sqrt(maturity)
    drift = (rate - volatility**2 / 2) * maturity
    split = (math.log(strike / spot) - drift) / width

    def integrand(z):
        terminal = spot * math.exp(drift + width * z)
        payoff = max(terminal - strike, 0) if kind == "call" else max(strike - terminal, 0)
        return payoff * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)

    points = sorted({-10.0, 10.0, min(max(split, -10), 10)})
    return math.exp(-rate * maturity) * sum(
        quad(integrand, a, b, epsabs=1e-10)[0] for a, b in pairwise(points)
    )


def test_hull_figure_11_1_and_11_2_printed_baselines():
    result = props.factor_prices([50], factor="spot")
    assert result["call"] == pytest.approx([7.116], abs=0.0005)
    assert result["put"] == pytest.approx([4.677], abs=0.0005)
    for kind in ("call", "put"):
        assert result[kind][0] == pytest.approx(integrated_price(50, 50, .05, .3, 1, kind), abs=1e-9)


@pytest.mark.parametrize("factor,values", [
    ("spot", [0, 20, 50, 100]), ("strike", [0, 20, 50, 100]),
    ("maturity", [0, .5, 1, 1.6]), ("volatility", [0, .1, .3, .5]),
    ("rate", [0, .02, .05, .08]),
])
def test_factor_curves_match_independent_payoff_integration(factor, values):
    result = props.factor_prices(values, factor=factor)
    for i, value in enumerate(values):
        inputs = dict(spot=50, strike=50, rate=.05, volatility=.3, maturity=1)
        inputs[factor] = value
        for kind in ("call", "put"):
            assert result[kind][i] == pytest.approx(integrated_price(**inputs, kind=kind), abs=1e-8)


@pytest.mark.parametrize("factor,call_sign,put_sign", [
    ("spot", 1, -1), ("strike", -1, 1), ("volatility", 1, 1), ("rate", 1, -1),
    ("dividend_scale", -1, 1),
])
def test_european_table_11_1_signs(factor, call_sign, put_sign):
    values = {"spot": [45, 50, 55], "strike": [45, 50, 55],
              "volatility": [.2, .3, .4], "rate": [.02, .05, .08],
              "dividend_scale": [0, 1, 2]}[factor]
    result = props.factor_prices(values, factor=factor, dividend_times=[.5], dividend_amounts=[2])
    assert np.all(call_sign * np.diff(result["call"]) > 0)
    assert np.all(put_sign * np.diff(result["put"]) > 0)


def test_european_maturity_question_mark_two_synthetic_counterexamples():
    put = props.factor_prices([.25, 2], factor="maturity", spot=5)["put"]
    assert put[0] > put[1]
    call = props.factor_prices([1/12, 2/12], factor="maturity",
                              dividend_times=[6/52], dividend_amounts=[5])["call"]
    assert call[0] > call[1]
    # Dates stay fixed as maturity changes; this is the declared escrowed-dividend model.
    for maturity, got in zip([1/12, 2/12], call, strict=True):
        prepaid = 50 - (5 * math.exp(-.05 * 6/52) if 6/52 <= maturity else 0)
        assert got == pytest.approx(integrated_price(prepaid, 50, .05, .3, maturity, "call"), abs=1e-9)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_american_maturity_opportunities_nested_and_confirmed_by_pde(kind):
    u = math.exp(.3 * math.sqrt(.01))
    prices = [trees.binomial_tree(50, 50, .05, t, n, u, 1/u, kind=kind, american=True)[1][0][0]
              for t, n in [(.5, 50), (1, 100)]]
    pde = [fd.fd_vanilla(50, 50, .05, .3, t, kind=kind, american=True, n_s=300, n_t=400)
           for t in [.5, 1]]
    assert prices[1] >= prices[0]
    assert pde[1] >= pde[0]
    assert prices == pytest.approx(pde, abs=.03)


@pytest.mark.parametrize("factor,values", [("maturity", [-1]), ("volatility", [-.1]),
                                          ("spot", [-1]), ("strike", [-1])])
def test_undefined_factor_inputs(factor, values):
    with pytest.raises(ValueError):
        props.factor_prices(values, factor=factor)
