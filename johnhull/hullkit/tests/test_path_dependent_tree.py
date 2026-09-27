"""Hull GE §27.5 arithmetic-average tree and Figure 27.3."""

import pytest
from hullkit.path_dependent_tree import arithmetic_average_call_tree

PARAMS = dict(spot=50.0, strike=50.0, rate=0.10, volatility=0.40, maturity=1.0)


def test_hull_figure_27_3_average_grids_and_node_values():
    tree = arithmetic_average_call_tree(**PARAMS, steps=20, average_points=4)
    assert tree.average_grids[4][2] == pytest.approx((46.65, 49.04, 51.44, 53.83), abs=0.01)
    assert tree.average_grids[5][3] == pytest.approx((47.99, 51.12, 54.26, 57.39), abs=0.01)
    assert tree.average_grids[5][2] == pytest.approx((43.88, 46.75, 49.61, 52.48), abs=0.01)
    assert tree.value_grids[4][2][2] == pytest.approx(6.206, abs=0.01)
    assert tree.price == pytest.approx(7.17, abs=0.01)


def test_hull_american_and_refined_prices():
    euro_coarse = arithmetic_average_call_tree(**PARAMS, steps=20, average_points=4)
    american_coarse = arithmetic_average_call_tree(
        **PARAMS, steps=20, average_points=4, american=True
    )
    euro_fine = arithmetic_average_call_tree(**PARAMS, steps=60, average_points=100)
    american_fine = arithmetic_average_call_tree(
        **PARAMS, steps=60, average_points=100, american=True
    )
    assert american_coarse.price == pytest.approx(7.77, abs=0.01)
    assert euro_fine.price == pytest.approx(5.58, abs=0.01)
    assert american_fine.price == pytest.approx(6.17, abs=0.01)
    assert american_coarse.price > euro_coarse.price
    assert american_fine.price > euro_fine.price


def test_one_step_matches_direct_discounted_expectation():
    tree = arithmetic_average_call_tree(**PARAMS, steps=1, average_points=4)
    up = tree.stock_levels[1][1]
    down = tree.stock_levels[1][0]
    expected = tree.discount_factor * (
        tree.up_probability * max((50 + up) / 2 - 50, 0)
        + (1 - tree.up_probability) * max((50 + down) / 2 - 50, 0)
    )
    assert tree.price == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize(
    "change",
    [
        {"spot": 0},
        {"strike": -1},
        {"volatility": 0},
        {"maturity": 0},
        {"steps": 0},
        {"average_points": 1},
    ],
)
def test_invalid_inputs_are_rejected(change):
    with pytest.raises(ValueError):
        arithmetic_average_call_tree(**{**PARAMS, "steps": 20, "average_points": 4, **change})
