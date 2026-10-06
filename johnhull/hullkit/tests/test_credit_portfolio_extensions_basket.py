"""Hull §25.6 basket definitions and independent default-year state valuation."""

import math
from itertools import product

import numpy as np
import pytest
from hullkit import _credit_portfolio_extensions as e


def test_add_up_and_ranked_contracts_stop_at_relevant_default():
    # Source definitions, illustrative three names with explicitly different recoveries.
    for k, when, loss in [(1, 0.5, 80), (2, 1.2, 60), (3, 2.2, 40)]:
        cf = e.basket_contract_cashflows(
            [2.2, 0.5, 1.2], 100, 0.01, 4, recoveries=[0.6, 0.2, 0.4], k=k
        )
        assert cf["times"][-1] == pytest.approx(when)
        assert sum(cf["protection"]) == pytest.approx(loss)
        assert sum(cf["premium"]) == pytest.approx(when)
    add = e.basket_contract_cashflows(
        [2.2, 0.5, 1.2], 100, 0.01, 4, recoveries=[0.6, 0.2, 0.4], kind="add_up"
    )
    assert sum(add["protection"]) == pytest.approx(180)
    assert sum(add["premium"]) == pytest.approx(3.9)
    assert add["buyer_cashflows"] == pytest.approx(-add["seller_cashflows"])


@pytest.mark.parametrize("k", [1, 2, 3])
def test_kth_prices_against_independent_27_default_year_cashflow_states(k):
    # Two annual periods, defaults at midpoint, hazard .2/year, R=.4, r=.03.
    probs = [1 - math.exp(-0.2), math.exp(-0.2) - math.exp(-0.4), math.exp(-0.4)]
    a = b = c = 0.0
    for states in product(range(3), repeat=3):
        weight = math.prod(probs[i] for i in states)
        trigger = sorted(states)[k - 1]
        for year in (1, 2):
            if trigger >= year:
                a += weight * math.exp(-0.03 * year)
        if trigger < 2:
            mid = trigger + 0.5
            b += weight * 0.5 * math.exp(-0.03 * mid)
            c += weight * 0.6 * math.exp(-0.03 * mid)
    val = e.basket_valuation(k, 3, 0.2, 0.4, 0.03, 2, 0, frequency=1)
    assert [val.annuity, val.accrual, val.payoff] == pytest.approx([a, b, c], abs=2e-14)
    assert val.spread == pytest.approx(c / (a + b))


def test_surviving_basket_and_invalid_rank():
    cf = e.basket_contract_cashflows([5, np.inf], 100, 0.01, 4, k=2)
    assert sum(cf["protection"]) == 0
    assert sum(cf["premium"]) == pytest.approx(4)
    with pytest.raises(ValueError):
        e.basket_contract_cashflows([1], 100, 0.01, 4, k=2)
