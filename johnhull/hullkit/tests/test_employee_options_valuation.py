"""Hull GE 16.4: every Figure 16.1 node and independent forward event cashflows."""

import math
from itertools import product

import numpy as np
import pytest
from hullkit import _employee_options as employee
from hullkit import bsm
from hullkit.trees import crr_price
from scipy.integrate import quad
from scipy.stats import lognorm

SOURCE = dict(spot=40, strike=40, rate=.05, sigma=.3, maturity=8, steps=4, vesting=3, departure_probability=.05, exercise_probabilities={(2, 0): .4, (3, 0): .8, (3, 1): .3})


def enumerate_cashflows(spot, strike, rate, sigma, maturity, steps, vesting, leave, probabilities, *, level=0, down_count=0, multiple=None):
    """Sum whole binary paths and event cashflows forward; no rollback."""
    dt = maturity/steps
    log_up = sigma*math.sqrt(dt)
    p = (math.exp(rate*dt)-math.exp(-log_up))/(math.exp(log_up)-math.exp(-log_up))
    value = life = 0.0
    for path in product([0, 1], repeat=steps-level):  # 1 is up
        weight = math.prod(p if up else 1-p for up in path)
        alive, downs = 1.0, down_count
        for offset, up in enumerate(path):
            i = level+offset
            stock = spot*math.exp(log_up*(i-2*downs))
            eligible = i*dt >= vesting and stock > strike
            voluntary = probabilities.get((i, downs), 0) if eligible else 0
            if multiple is not None and eligible:
                voluntary = float(stock >= strike*multiple-1e-12)
            stopping = voluntary+(1-voluntary)*leave
            if eligible:
                value += weight*alive*stopping*(stock-strike)*math.exp(-rate*offset*dt)
            life += weight*alive*stopping*i*dt
            alive *= (1-voluntary)*(1-leave)
            downs += 1-up
        terminal = spot*math.exp(log_up*(steps-2*downs))
        value += weight*alive*max(terminal-strike, 0)*math.exp(-rate*(steps-level)*dt)
        life += weight*alive*maturity
    return value, life


def test_example_16_1_expected_life_approximation_against_payoff_integral():
    result = employee.expected_life_bsm(30, 30, .05, .25, 4.5, dividend_pv=4, quantity=1000000)
    assert result["unit_value"] == pytest.approx(6.31, abs=.005, rel=0)
    assert result["total_value"]/1e6 == pytest.approx(6.31, abs=.005, rel=0)
    density = lognorm(s=.25*math.sqrt(4.5), scale=26*math.exp((.05-.25**2/2)*4.5))
    independent = math.exp(-.05*4.5)*quad(lambda s: (s-30)*density.pdf(s), 30, math.inf)[0]
    assert result["unit_value"] == pytest.approx(independent, abs=1e-9)


def test_example_16_2_all_printed_figure_nodes_and_parameters():
    result = employee.employee_option_tree(**SOURCE)
    stocks = [[40], [61.14, 26.17], [93.45, 40, 17.12], [142.83, 61.14, 26.17, 11.20], [218.31, 93.45, 40, 17.12, 7.33]]
    values = [[14.97], [29.39, 4.65], [56.44, 10.49, 0], [103.56, 23.67, 0, 0], [178.31, 53.45, 0, 0, 0]]
    for actual, printed in zip(result["stock"], stocks, strict=True):
        assert actual == pytest.approx(printed, abs=.005, rel=0)
    for actual, printed in zip(result["option"], values, strict=True):
        assert actual == pytest.approx(printed, abs=.005, rel=0)
    assert [result[k] for k in ["up", "down", "growth", "up_probability", "discount"]] == pytest.approx([1.5285, .6543, 1.1052, .5158, .9048], abs=.00005, rel=0)
    assert crr_price(40, 40, .05, .3, 8, 4) == pytest.approx(17.98, abs=.005, rel=0)


def test_source_d_g_h_exercise_weights_and_continuations():
    result = employee.employee_option_tree(**SOURCE)
    assert [result["exercise_probability"][2][0], result["exercise_probability"][3][0], result["exercise_probability"][3][1]] == pytest.approx([.43, .81, .335], abs=1e-12)
    assert [result["continuation"][2][1], result["continuation"][3][0], result["continuation"][3][1]] == pytest.approx([11.05, 106.64, 24.95], abs=.005, rel=0)
    assert result["survival_probability"][0][0] == pytest.approx(.95)
    assert result["forfeiture_probability"][0][0] == pytest.approx(.05)


def test_all_nodes_against_independent_whole_path_cashflow_enumeration():
    result = employee.employee_option_tree(**SOURCE)
    for i in range(5):
        for j in range(i+1):
            value, life = enumerate_cashflows(40, 40, .05, .3, 8, 4, 3, .05, SOURCE["exercise_probabilities"], level=i, down_count=j)
            assert result["option"][i][j] == pytest.approx(value, abs=1e-11)
            assert result["life_nodes"][i][j] == pytest.approx(life, abs=1e-11)


def test_source_model_against_independent_simulated_departures_and_exercise():
    result = employee.employee_option_tree(**SOURCE)
    rng = np.random.default_rng(164)
    n, dt, sigma = 100000, 2, .3
    log_up = sigma*math.sqrt(dt)
    p = (math.exp(.05*dt)-math.exp(-log_up))/(math.exp(log_up)-math.exp(-log_up))
    ups = rng.random((n, 4)) < p
    leaves = rng.random((n, 4)) < .05
    exercises = rng.random((n, 4))
    alive = np.ones(n, dtype=bool)
    downs = np.zeros(n, dtype=int)
    payoffs = np.zeros(n)
    lives = np.full(n, 8.0)
    for i in range(4):
        stock = 40*np.exp(log_up*(i-2*downs))
        eligible = (i*dt >= 3) & (stock > 40)
        q = np.array([SOURCE["exercise_probabilities"].get((i, j), 0) for j in downs])
        voluntary = eligible & (exercises[:, i] < q)
        stopping = alive & (voluntary | leaves[:, i])
        pays = stopping & eligible
        payoffs[pays] = (stock[pays]-40)*math.exp(-.05*i*dt)
        lives[stopping] = i*dt
        alive[stopping] = False
        downs += ~ups[:, i]
    terminal = 40*np.exp(log_up*(4-2*downs))
    payoffs[alive] = np.maximum(terminal[alive]-40, 0)*math.exp(-.4)
    for observations, target in [(payoffs, result["price"]), (lives, result["expected_life"])]:
        assert abs(observations.mean()-target) < 6*observations.std(ddof=1)/math.sqrt(n)


def test_no_departure_or_voluntary_exercise_is_ordinary_european_call():
    for q in [0, .08]:
        for optimal in [False, True]:
            result = employee.employee_option_tree(40, 40, .05, .3, 8, 4, optimal_exercise=optimal, dividend_yield=q)
            assert result["price"] == pytest.approx(crr_price(40, 40, .05, .3, 8, 4, q=q, american=optimal), abs=1e-12)
    retained = employee.employee_option_tree(40, 40, .05, .3, 8, 4, exercise_multiple=math.inf)
    assert retained["price"] == pytest.approx(crr_price(40, 40, .05, .3, 8, 4), abs=1e-12)
    assert retained["expected_life"] == pytest.approx(8)


def test_voluntary_exercise_before_vesting_is_suppressed():
    result = employee.employee_option_tree(100, 40, .05, .3, 8, 4, vesting=3, exercise_probabilities={(0, 0): 1, (1, 0): 1})
    assert result["price"] == pytest.approx(crr_price(100, 40, .05, .3, 8, 4), abs=1e-11)
    assert np.allclose(result["exercise_probability"][0], 0)


@pytest.mark.parametrize("vesting,expected", [(3, 0), (0, 60)])
def test_certain_root_departure_forfeits_unvested_or_exercises_vested(vesting, expected):
    result = employee.employee_option_tree(100, 40, .05, .3, 8, 4, vesting=vesting, departure_probability=1)
    assert result["price"] == pytest.approx(expected)
    assert result["expected_life"] == pytest.approx(0)


def test_zero_volatility_is_deterministic_without_zero_division():
    result = employee.employee_option_tree(40, 40, .05, 0, 8, 4)
    assert result["price"] == pytest.approx(math.exp(-.4)*max(40*math.exp(.4)-40, 0), abs=1e-12)


def test_expected_life_bsm_does_not_equal_stochastic_exercise_value():
    result = employee.employee_option_tree(40, 30, .05, .3, 8, 200, exercise_probabilities={(0, 0): .5})
    assert result["expected_life"] == pytest.approx(4)
    approximation = employee.expected_life_bsm(40, 30, .05, .3, result["expected_life"])["unit_value"]
    assert abs(approximation-result["price"]) > .1


def test_source_multiple_45_on_a_boundary_aligned_crr_grid():
    dt = (math.log(1.5)/.3)**2
    result = employee.employee_option_tree(30, 30, .05, .3, 4*dt, 4, vesting=dt, exercise_multiple=1.5)
    assert result["stock"][1][0] == pytest.approx(45, abs=1e-12)
    assert result["exercise_probability"][1][0] == pytest.approx(1)
    assert result["option"][1][0] == pytest.approx(15, abs=1e-12)
    independent, _ = enumerate_cashflows(30, 30, .05, .3, 4*dt, 4, dt, 0, {}, multiple=1.5)
    assert result["price"] == pytest.approx(independent, abs=1e-12)


def test_multiple_estimation_excludes_departure_and_maturity_exercises():
    estimate = employee.exercise_multiple_estimate([45, 100, 80], [30, 20, 40], ["voluntary", "departure", "maturity"])
    assert estimate == pytest.approx(1.5)
    with pytest.raises(ValueError):
        employee.exercise_multiple_estimate([100], [20], ["departure"])


@pytest.mark.parametrize("stock,fraction,payoff", [(60, .01, 20), (65, .02, 25)])
def test_source_market_based_mirrored_exercise_cash(stock, fraction, payoff):
    result = employee.mirrored_exercise_cash(stock, 40, fraction, 100)
    assert result["per_option_payoff"] == pytest.approx(payoff)
    assert result["exercised_units"] == pytest.approx(100*fraction)
    assert result["cash_total"] == pytest.approx(payoff*100*fraction)


@pytest.mark.parametrize("kwargs", [{"vesting": 9}, {"departure_probability": -.1}, {"exercise_probabilities": {(1, 0): .5}, "exercise_multiple": 1.5}])
def test_undefined_or_conflicting_tree_inputs(kwargs):
    with pytest.raises(ValueError):
        employee.employee_option_tree(40, 40, .05, .3, 8, 4, **kwargs)


def test_vesting_on_a_rounded_node_time_is_vested():
    # dt=0.3/3 rounds below 0.1; the node at t=0.1 is still the vesting date.
    leaver = employee.employee_option_tree(100, 40, .05, .3, .3, 3, vesting=.1, departure_probability=[0, 1, 0])
    assert leaver["price"] == pytest.approx(100-40*math.exp(-.05*.1), abs=1e-12)
    chosen = employee.employee_option_tree(100, 40, .05, .3, .3, 3, vesting=.1, exercise_probabilities={(1, 0): 1, (1, 1): 1})
    assert np.allclose(chosen["exercise_probability"][1], 1)


@pytest.mark.parametrize("maturity,steps,vesting", [(1, 98, .5), (3, 94, 1.5), (.3, 3, .1)])
def test_on_node_vesting_matches_a_vesting_date_just_before_the_node(maturity, steps, vesting):
    exact = employee.employee_option_tree(40, 40, .05, .3, maturity, steps, vesting=vesting, departure_probability=.05)
    earlier = employee.employee_option_tree(40, 40, .05, .3, maturity, steps, vesting=vesting*(1-1e-9), departure_probability=.05)
    assert exact["price"] == pytest.approx(earlier["price"], abs=1e-12)
