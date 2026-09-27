"""Hull GE §27.4 convertible bond tree, including credit and issuer call."""

import math

import pytest
from hullkit.convertible_bond import convertible_bond_tree, defaultable_branch_probabilities

EXAMPLE = dict(
    spot=50.0,
    face=100.0,
    conversion_ratio=2.0,
    call_price=113.0,
    rate=0.05,
    dividend_yield=0.0,
    volatility=0.30,
    hazard_rate=0.01,
    recovery_value=40.0,
    maturity=0.75,
    steps=3,
)


def test_hull_example_27_1_nodes_and_decisions():
    tree = convertible_bond_tree(**EXAMPLE)
    assert tree.price == pytest.approx(107.44, abs=0.005)
    assert tree.bond_levels[1][1] == pytest.approx(116.18, abs=0.005)
    assert tree.bond_levels[1][0] == pytest.approx(101.37, abs=0.005)
    assert tree.bond_levels[2][2] == pytest.approx(134.99, abs=0.005)
    assert tree.bond_levels[2][1] == pytest.approx(106.78, abs=0.005)
    assert tree.bond_levels[2][0] == pytest.approx(98.61, abs=0.005)
    assert tree.decisions[1][1] == "call-convert"
    assert tree.decisions[2][1] == "hold"


def test_three_branch_probabilities_match_martingale_and_survival():
    up, down, default = defaultable_branch_probabilities(0.05, 0, 0.3, 0.01, 0.25)
    u = math.exp(0.3 * math.sqrt(0.25))
    d = 1 / u
    assert (up, down, default) == pytest.approx((0.5115, 0.4860, 0.0025), abs=5e-5)
    assert up + down == pytest.approx(math.exp(-0.01 * 0.25))
    assert up * u + down * d == pytest.approx(math.exp(0.05 * 0.25))


def test_defaultable_coupon_bond_matches_independent_cashflow_sum():
    params = dict(EXAMPLE, conversion_ratio=0, call_price=None, steps=3, coupon_amount=2.0)
    found = convertible_bond_tree(**params).price
    dt = params["maturity"] / params["steps"]
    survival = math.exp(-params["hazard_rate"] * dt)
    discount = math.exp(-params["rate"] * dt)
    expected = (
        sum(
            discount**i * (survival**i * 2.0 + survival ** (i - 1) * (1 - survival) * 40.0)
            for i in range(1, 4)
        )
        + discount**3 * survival**3 * 100.0
    )
    assert found == pytest.approx(expected, abs=1e-12)


def test_credit_and_call_reduce_value_of_same_convertible():
    risky = convertible_bond_tree(**EXAMPLE).price
    safe = convertible_bond_tree(**dict(EXAMPLE, hazard_rate=0)).price
    uncallable = convertible_bond_tree(**dict(EXAMPLE, call_price=None)).price
    assert risky < safe
    assert risky < uncallable


@pytest.mark.parametrize(
    "change",
    [
        {"steps": 0},
        {"volatility": 0},
        {"hazard_rate": -0.01},
        {"recovery_value": -1},
        {"coupon_amount": -1},
        {"face": 0},
        {"conversion_ratio": -1},
    ],
)
def test_invalid_contract_or_grid_is_rejected(change):
    with pytest.raises(ValueError):
        convertible_bond_tree(**dict(EXAMPLE, **change))


def test_coarse_grid_with_negative_branch_probability_is_rejected():
    with pytest.raises(ValueError, match="probabilit"):
        defaultable_branch_probabilities(0.5, 0, 0.01, 0, 1)
