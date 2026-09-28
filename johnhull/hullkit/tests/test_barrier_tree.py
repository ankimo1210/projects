"""Hull GE §27.6 barrier trees: simple, inner/outer interpolation, nodes on the barrier."""

import math

import pytest
from hullkit.barrier_tree import (
    barrier_log_spacing,
    binomial_barrier,
    interpolated_barrier,
    standard_log_spacing,
    trinomial_barrier,
    trinomial_probabilities,
)
from hullkit.bsm import call_price
from hullkit.exotics import barrier_call, barrier_put

UP = dict(spot=100.0, strike=100.0, barrier=120.0, rate=0.05, volatility=0.30, maturity=1.0)
DOWN = dict(UP, barrier=80.0)


def _analytic_up_and_out_call():
    return barrier_call(100.0, 100.0, 120.0, 0.05, 0.30, 1.0, barrier="up-and-out")


def test_hull_rule_puts_the_barrier_on_the_nearest_level():
    dt = 0.01
    x = math.log(1.2) / (0.30 * math.sqrt(3 * dt))
    levels, log_spacing = barrier_log_spacing(100.0, 120.0, 0.30, dt)
    assert levels == int(x + 0.5) == 4
    assert log_spacing == pytest.approx(math.log(1.2) / 4, rel=1e-15)
    down_levels, down_spacing = barrier_log_spacing(100.0, 80.0, 0.30, dt)
    assert down_levels == -int(math.log(1.25) / (0.30 * math.sqrt(3 * dt)) + 0.5)
    assert down_spacing == pytest.approx(math.log(1.25) / abs(down_levels), rel=1e-15)


def test_probabilities_match_the_mean_exactly_and_the_second_moment_to_first_order():
    rate, dividend, volatility, dt = 0.05, 0.02, 0.30, 0.01
    log_spacing = barrier_log_spacing(100.0, 120.0, volatility, dt)[1]
    p_up, p_mid, p_down = trinomial_probabilities(
        log_spacing, rate, volatility, dt, dividend_yield=dividend
    )
    drift = (rate - dividend - volatility**2 / 2) * dt
    assert p_up + p_mid + p_down == pytest.approx(1.0, abs=1e-15)
    assert (p_up - p_down) * log_spacing == pytest.approx(drift, rel=1e-12)
    assert (p_up + p_down) * log_spacing**2 == pytest.approx(volatility**2 * dt, rel=1e-12)
    variance = (p_up + p_down) * log_spacing**2 - drift**2
    assert volatility**2 * dt - variance == pytest.approx(drift**2, rel=1e-9)


def test_standard_spacing_reproduces_section_21_4_probabilities():
    rate, volatility, dt = 0.05, 0.30, 0.01
    spacing = standard_log_spacing(volatility, dt)
    assert spacing == pytest.approx(volatility * math.sqrt(3 * dt), rel=1e-15)
    p_up, p_mid, p_down = trinomial_probabilities(spacing, rate, volatility, dt)
    shift = math.sqrt(dt / (12 * volatility**2)) * (rate - volatility**2 / 2)
    assert p_mid == pytest.approx(2 / 3, abs=1e-15)
    assert p_up == pytest.approx(shift + 1 / 6, abs=1e-15)
    assert p_down == pytest.approx(-shift + 1 / 6, abs=1e-15)


def test_probability_function_reports_a_negative_middle_branch_without_raising():
    dt = 0.01
    levels, spacing = barrier_log_spacing(100.0, 102.8, 0.30, dt)
    assert levels == 1
    assert trinomial_probabilities(spacing, 0.05, 0.30, dt)[1] < 0


def test_simple_method_treats_the_outer_barrier_as_the_true_barrier():
    tree = trinomial_barrier(**UP, steps=100, method="simple")
    spacing = standard_log_spacing(0.30, 0.01)
    outer_level = math.ceil(math.log(1.2) / spacing)
    assert tree.barrier_level == outer_level
    assert tree.tree_barrier == pytest.approx(100.0 * math.exp(outer_level * spacing), rel=1e-14)
    assert tree.tree_barrier > 120.0 > tree.tree_barrier * math.exp(-spacing)
    moved = trinomial_barrier(**dict(UP, barrier=tree.tree_barrier), steps=100, method="simple")
    assert moved.price == pytest.approx(tree.price, abs=1e-13)


def test_inner_method_uses_the_level_just_inside_the_barrier():
    outer = trinomial_barrier(**UP, steps=100, method="simple")
    inner = trinomial_barrier(**UP, steps=100, method="inner")
    assert inner.barrier_level == outer.barrier_level - 1
    moved = trinomial_barrier(**dict(UP, barrier=inner.tree_barrier), steps=100, method="simple")
    assert moved.price == pytest.approx(inner.price, abs=1e-13)
    assert inner.price < outer.price


def test_interpolation_is_linear_in_the_barrier_between_inner_and_outer_prices():
    result = interpolated_barrier(**UP, steps=100)
    weight = (120.0 - result.inner.tree_barrier) / (
        result.outer.tree_barrier - result.inner.tree_barrier
    )
    assert result.weight == pytest.approx(weight, abs=1e-15)
    assert result.price == pytest.approx(
        result.inner.price + weight * (result.outer.price - result.inner.price), abs=1e-14
    )
    on_node = interpolated_barrier(**dict(UP, barrier=result.outer.tree_barrier), steps=100)
    assert on_node.weight == pytest.approx(1.0, abs=1e-12)
    assert on_node.price == pytest.approx(on_node.outer.price, abs=1e-12)


def test_nodes_on_barrier_place_a_level_exactly_on_the_barrier():
    tree = trinomial_barrier(**UP, steps=100, method="on_barrier")
    assert tree.barrier_level == 4
    assert tree.tree_barrier == pytest.approx(120.0, rel=1e-14)
    assert tree.probabilities == pytest.approx(
        trinomial_probabilities(tree.log_spacing, 0.05, 0.30, 0.01), abs=1e-15
    )


def test_one_step_matches_the_direct_discounted_expectation():
    tree = trinomial_barrier(**UP, steps=1, method="simple")
    p_up, p_mid, p_down = tree.probabilities
    up, down = math.exp(tree.log_spacing), math.exp(-tree.log_spacing)
    payoff = [0.0 if s >= 120.0 else max(s - 100.0, 0.0) for s in (100 * up, 100.0, 100 * down)]
    expected = math.exp(-0.05) * (p_up * payoff[0] + p_mid * payoff[1] + p_down * payoff[2])
    assert tree.price == pytest.approx(expected, abs=1e-13)


def test_simple_trees_oscillate_while_barrier_aware_methods_converge():
    analytic = _analytic_up_and_out_call()
    simple = [trinomial_barrier(**UP, steps=n, method="simple").price for n in (40, 200)]
    assert max(abs(price - analytic) for price in simple) > 0.5
    errors = [
        trinomial_barrier(**UP, steps=n, method="on_barrier").price - analytic for n in (800, 1600)
    ]
    assert abs(errors[0]) < 0.005
    assert errors[1] / errors[0] == pytest.approx(0.5, abs=0.05)
    assert interpolated_barrier(**UP, steps=800).price == pytest.approx(analytic, abs=0.005)


def test_down_and_out_put_mirrors_the_up_barrier():
    analytic = barrier_put(100.0, 100.0, 80.0, 0.05, 0.30, 1.0, barrier="down-and-out")
    tree = trinomial_barrier(
        **DOWN, steps=800, option="put", barrier_type="down-and-out", method="on_barrier"
    )
    assert tree.barrier_level < 0
    assert tree.tree_barrier == pytest.approx(80.0, rel=1e-14)
    finer = trinomial_barrier(
        **DOWN, steps=1600, option="put", barrier_type="down-and-out", method="on_barrier"
    )
    assert abs(tree.price - analytic) < 0.006
    assert (finer.price - analytic) / (tree.price - analytic) == pytest.approx(0.5, abs=0.05)
    inner = trinomial_barrier(
        **DOWN, steps=100, option="put", barrier_type="down-and-out", method="inner"
    )
    outer = trinomial_barrier(
        **DOWN, steps=100, option="put", barrier_type="down-and-out", method="simple"
    )
    assert outer.tree_barrier <= 80.0 < inner.tree_barrier
    assert inner.barrier_level == outer.barrier_level + 1


def test_binomial_simple_method_matches_vanilla_when_the_barrier_is_unreachable():
    far = binomial_barrier(**dict(UP, barrier=1e9), steps=400)
    vanilla = call_price(100.0, 100.0, 0.05, 0.30, 1.0)
    assert far.price == pytest.approx(vanilla, abs=0.01)
    assert far.probabilities[1] == 0.0
    tree = binomial_barrier(**UP, steps=100)
    moved = binomial_barrier(**dict(UP, barrier=tree.tree_barrier), steps=100)
    assert moved.price == pytest.approx(tree.price, abs=1e-13)


def test_barrier_too_close_to_spot_is_rejected_until_steps_increase():
    close = dict(UP, barrier=102.0)
    with pytest.raises(ValueError, match="adaptive mesh"):
        trinomial_barrier(**close, steps=100, method="on_barrier")
    negative = dict(UP, barrier=102.8)
    with pytest.raises(ValueError, match="negative"):
        trinomial_barrier(**negative, steps=100, method="on_barrier")
    finer = trinomial_barrier(**negative, steps=400, method="on_barrier")
    assert finer.barrier_level == 1
    assert min(finer.probabilities) > 0


@pytest.mark.parametrize(
    "change",
    [
        {"spot": 0.0},
        {"strike": -1.0},
        {"volatility": 0.0},
        {"maturity": 0.0},
        {"steps": 0},
        {"steps": 10.0},
        {"barrier": 100.0},
        {"barrier": 90.0},
        {"rate": math.nan},
        {"option": "digital"},
        {"barrier_type": "up-and-in"},
        {"method": "adaptive"},
    ],
)
def test_invalid_inputs_are_rejected(change):
    arguments = {**UP, "steps": 20, "method": "simple", **change}
    with pytest.raises(ValueError):
        trinomial_barrier(**arguments)


@pytest.mark.parametrize("barrier", [110.0, 100.0])
def test_down_barrier_at_or_above_spot_is_rejected(barrier):
    with pytest.raises(ValueError):
        binomial_barrier(**dict(UP, barrier=barrier), steps=20, barrier_type="down-and-out")
    with pytest.raises(ValueError):
        trinomial_barrier(**dict(UP, barrier=barrier), steps=20, barrier_type="down-and-out")


def test_binomial_down_barrier_knocks_out_a_node_exactly_on_it():
    up = math.exp(0.30 * math.sqrt(1.0))
    tree = binomial_barrier(
        **dict(UP, barrier=100.0 / up), steps=1, option="put", barrier_type="down-and-out"
    )
    assert tree.barrier_level == -1
    assert tree.price == pytest.approx(0.0, abs=1e-15)


def test_binomial_put_and_dividend_match_black_scholes_when_unreachable():
    from hullkit.bsm import put_price

    far = binomial_barrier(
        **dict(UP, barrier=1e-6),
        steps=400,
        option="put",
        barrier_type="down-and-out",
        dividend_yield=0.03,
    )
    assert far.price == pytest.approx(put_price(100.0, 100.0, 0.05, 0.30, 1.0, q=0.03), abs=0.01)
    call = binomial_barrier(**dict(UP, barrier=1e9), steps=400, dividend_yield=0.03)
    assert call.price == pytest.approx(call_price(100.0, 100.0, 0.05, 0.30, 1.0, q=0.03), abs=0.01)


@pytest.mark.parametrize(
    ("option", "barrier_type", "barrier"),
    [("call", "up-and-out", 120.0), ("call", "down-and-out", 80.0), ("put", "up-and-out", 120.0)],
)
def test_dividend_yield_enters_the_barrier_aware_trees(option, barrier_type, barrier):
    formula = barrier_call if option == "call" else barrier_put
    analytic = formula(100.0, 100.0, barrier, 0.05, 0.30, 1.0, q=0.03, barrier=barrier_type)
    arguments = dict(UP, barrier=barrier)
    options = dict(option=option, barrier_type=barrier_type, dividend_yield=0.03)
    errors = [
        trinomial_barrier(**arguments, steps=n, method="on_barrier", **options).price - analytic
        for n in (800, 1600)
    ]
    assert abs(errors[0]) < 0.006
    assert errors[1] / errors[0] == pytest.approx(0.5, abs=0.1)
