"""Hull GE section 13.10: numerical DerivaGem examples, without UI claims."""

import pytest
from hullkit import _binomial_foundations as foundations
from hullkit.bsm import put_price
from hullkit.fd import fd_vanilla
from hullkit.trees import crr_params, crr_price


def test_hull_two_five_and_five_hundred_step_printed_prices():
    assert crr_price(50, 52, .05, .3, 2, 2, kind="put", american=True) == pytest.approx(7.428, abs=.0005)
    assert crr_price(50, 52, .05, .3, 2, 5, kind="put", american=True) == pytest.approx(7.671, abs=.0005)
    assert crr_price(50, 52, .05, .3, 2, 500, kind="put", american=True) == pytest.approx(7.47, abs=.005)
    assert crr_price(50, 52, .05, .3, 2, 500, kind="put") == pytest.approx(6.76, abs=.005)
    assert float(put_price(50, 52, .05, .3, 2)) == pytest.approx(6.76, abs=.005)


def test_five_step_american_price_against_all_32768_node_policies():
    up, down = crr_params(.3, 2/5)
    policies = foundations.small_tree_stopping_values(50, 52, .05, 2, 5, up, down, kind="put")
    assert len(policies["policy_values"]) == 32768
    assert policies["price"] == pytest.approx(7.670889, abs=.000001)
    assert policies["price"] == pytest.approx(crr_price(50, 52, .05, .3, 2, 5, kind="put", american=True), abs=1e-10)
    european = foundations.terminal_binomial_value(50, 52, .05, 2, 5, up, down, kind="put")
    assert policies["policy_values"][0] == pytest.approx(european["price"], abs=1e-10)


def test_five_hundred_step_prices_against_independent_pde_continuous_limit():
    american = crr_price(50, 52, .05, .3, 2, 500, kind="put", american=True)
    european = crr_price(50, 52, .05, .3, 2, 500, kind="put")
    # PDE and CRR discretize the continuous stopping problem differently.
    pde = fd_vanilla(50, 52, .05, .3, 2, kind="put", american=True, n_s=800, n_t=1600)
    assert american == pytest.approx(pde, abs=.01)
    assert european == pytest.approx(float(put_price(50, 52, .05, .3, 2)), abs=.005)
    assert american-european > .7
