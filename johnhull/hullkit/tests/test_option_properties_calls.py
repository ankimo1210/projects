"""Hull GE section 11.5: intrinsic 30 is not an option price."""

import math

import pytest
from hullkit import _option_properties as props
from hullkit import fd
from scipy.integrate import quad


def test_hull_70_40_one_month_intrinsic_and_interest_insurance_decomposition():
    # Only S=70, K=40, T=1m and intrinsic=30 are printed; r/sigma here are synthetic.
    result = props.exercise_comparison(70, 40, .05, .3, 1/12, steps=600)
    assert result["intrinsic"] == pytest.approx(30)
    assert result["american"] > 30
    assert result["european"] == pytest.approx(30+result["interest_deferral"]+result["put_insurance"], abs=1e-12)
    assert result["european"]-result["intrinsic"] > result["interest_deferral"]


@pytest.mark.parametrize("spot,strike,rate,volatility,maturity", [
    (70, 40, .05, .3, 1/12), (50, 50, .05, .3, 1), (40, 50, .1, .2, .5),
])
def test_nondividend_american_call_equals_european_with_independent_pde(spot, strike, rate, volatility, maturity):
    result = props.exercise_comparison(spot, strike, rate, volatility, maturity, steps=800)
    assert result["american"] == pytest.approx(result["tree_european"], abs=1e-10)
    pde = fd.fd_vanilla(spot, strike, rate, volatility, maturity, american=True, n_s=400, n_t=600)
    assert result["american"] == pytest.approx(pde, abs=.008)
    assert result["european"] == pytest.approx(pde, abs=.008)
    assert result["early_exercise_premium"] == pytest.approx(0, abs=1e-10)


def test_call_independent_terminal_payoff_integration():
    result = props.exercise_comparison(50, 50, .05, .3, 1, steps=800)
    def integrand(z):
        terminal = 50*math.exp((.05-.3**2/2)+.3*z)
        return max(terminal-50, 0)*math.exp(-z*z/2)/math.sqrt(2*math.pi)
    split = -(.05-.3**2/2)/.3
    integral = math.exp(-.05)*quad(integrand, split, 10, epsabs=1e-10)[0]
    assert result["european"] == pytest.approx(integral, abs=1e-9)
    assert result["american"] == pytest.approx(integral, abs=.008)


@pytest.mark.parametrize("factor", ["spot", "strike", "rate", "volatility"])
def test_american_call_factor_signs_tree_and_pde(factor):
    changes = {"spot": [45, 55], "strike": [45, 55], "rate": [.02, .08], "volatility": [.2, .4]}
    tree_prices, pde_prices = [], []
    for value in changes[factor]:
        params = dict(spot=50, strike=50, rate=.05, volatility=.3, maturity=1)
        params[factor] = value
        tree_prices.append(props.exercise_comparison(**params, steps=600)["american"])
        pde_prices.append(fd.fd_vanilla(params["spot"], params["strike"], params["rate"],
                                       params["volatility"], 1, american=True, n_s=300, n_t=400))
    sign = -1 if factor == "strike" else 1
    assert sign*(tree_prices[1]-tree_prices[0]) > 0
    assert sign*(pde_prices[1]-pde_prices[0]) > 0
    assert tree_prices == pytest.approx(pde_prices, abs=.02)


def test_negative_rate_early_call_exercise_is_possible():
    result = props.exercise_comparison(70, 40, -.05, .1, 1, steps=500)
    assert result["american"] == pytest.approx(30, abs=1e-10)
    assert result["american"] > result["european"]+.5
    pde = fd.fd_vanilla(70, 40, -.05, .1, 1, american=True, n_s=300, n_t=400)
    assert result["american"] == pytest.approx(pde, abs=.01)


def test_analytic_expiry_and_zero_volatility_limits():
    expiry = props.exercise_comparison(70, 40, .05, .3, 0)
    assert [expiry["european"], expiry["american"]] == pytest.approx([30, 30])
    deterministic = props.exercise_comparison(70, 40, -.05, 0, 1)
    assert deterministic["american"] == pytest.approx(30)
    assert deterministic["european"] == pytest.approx(70-40*math.exp(.05))
