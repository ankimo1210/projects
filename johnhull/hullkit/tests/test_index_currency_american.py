"""Hull 17.6 American carry trees and independent exercise references."""
import math

import pytest
from hullkit import _index_currency as index
from hullkit._binomial_foundations import small_tree_stopping_values
from hullkit.fd import fd_vanilla


def test_source_referenced_currency_example_all_option_nodes():
    result = index.carry_exercise_comparison(.61, .6, .05, .07, .12, .25, 3)
    assert result["american"] == pytest.approx(.019, abs=.0005)
    assert [result["growth"], result["probability"]] == pytest.approx([.9983, .4673], abs=5e-5)
    for actual, printed in zip(result["american_tree"], [[.019], [.033, .007], [.054, .015, 0], [.077, .032, 0, 0]], strict=True):
        assert actual == pytest.approx(printed, abs=.0005)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_small_carry_tree_against_independent_full_stopping_policy_enumeration(kind):
    result = index.carry_exercise_comparison(.61, .6, .05, .07, .12, .25, 3, kind=kind)
    up = math.exp(.12*math.sqrt(.25/3))
    reference = small_tree_stopping_values(.61, .6, .05, .25, 3, up, 1/up, kind=kind, q=.07)
    assert result["american"] == pytest.approx(reference["price"], abs=1e-14)
    assert result["american"] >= result["european_tree_value"]-1e-14


@pytest.mark.parametrize("spot,yield_rate,kind", [(120, .12, "call"), (80, .005, "put")])
def test_american_carry_against_independent_cn_pde(spot, yield_rate, kind):
    result = index.carry_exercise_comparison(spot, 100, .04, yield_rate, .2, 1, 1000, kind=kind)
    reference = fd_vanilla(spot, 100, .04, .2, 1, q=yield_rate, kind=kind, american=True, n_s=400, n_t=600)
    assert result["american"] == pytest.approx(reference, abs=.025)
    assert result["european_tree_value"] == pytest.approx(result["european"], abs=.02)
    assert result["american"] >= result["european_tree_value"]-1e-10


def test_source_foreign_rate_direction_for_call_and_put_exercise_value():
    call_low = index.carry_exercise_comparison(120, 100, .04, 0, .2, 1, 500)
    call_high = index.carry_exercise_comparison(120, 100, .04, .12, .2, 1, 500)
    put_low = index.carry_exercise_comparison(60, 100, .04, 0, .2, 1, 500, kind="put")
    put_high = index.carry_exercise_comparison(60, 100, .04, .12, .2, 1, 500, kind="put")
    assert call_high["early_exercise_premium"] > call_low["early_exercise_premium"]+.1
    assert put_low["early_exercise_premium"] > put_high["early_exercise_premium"]+.1
    assert call_high["exercise_now"]
    assert put_low["exercise_now"]


def test_deterministic_grid_against_direct_discounted_exercise_cash():
    result = index.carry_exercise_comparison(120, 100, .04, .12, 0, 1, 10)
    cash = [math.exp(-.04*j/10)*max(120*math.exp((.04-.12)*j/10)-100, 0) for j in range(11)]
    assert result["american"] == pytest.approx(max(cash))
    assert result["european"] == pytest.approx(cash[-1])
    assert result["exercise_now"]


def test_expiry_has_intrinsic_value_and_no_waiting_decision():
    result = index.carry_exercise_comparison(120, 100, .04, .12, .2, 0, 10)
    assert [result["american"], result["european"]] == pytest.approx([20, 20])
    assert not result["exercise_now"]


def test_tree_requires_positive_integer_steps():
    with pytest.raises(ValueError):
        index.carry_exercise_comparison(120, 100, .04, .12, .2, 1, 0)


def test_rounding_tie_between_intrinsic_and_continuation_is_not_exercise():
    tree = index.carry_exercise_comparison(27000, 1000, 0, 0, .25, .25, 3)
    flat = index.carry_exercise_comparison(27000, 1000, 0, 0, 0, .25, 3)
    assert tree["exercise_now"] is False
    assert flat["exercise_now"] is False
