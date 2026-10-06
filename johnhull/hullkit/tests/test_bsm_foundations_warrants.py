"""Hull GE 15.10: planned issue versus already-announced market dilution."""

import math
from fractions import Fraction

import pytest
from hullkit import _bsm_foundations as foundations
from hullkit._option_mechanics import option_cashflows
from scipy.integrate import quad
from scipy.stats import lognorm


def test_example_15_7_new_warrant_issue_cost():
    result = foundations.new_warrant_issue(40, 60, .03, .3, 5, 1000000, 200000)
    assert [result["ordinary_call"], result["warrant_price"], result["post_issue_spot"]] == pytest.approx([7.04, 5.87, 38.83], abs=.005, rel=0)
    assert result["issue_cost"]/1e6 == pytest.approx(1.17, abs=.005, rel=0)
    assert result["dilution_factor"] == pytest.approx(5/6)


@pytest.mark.parametrize("unaffected_spot", [30, 60, 100])
def test_terminal_new_issue_against_independent_fraction_capital_ledger(unaffected_spot):
    n, m, k = Fraction(1000000), Fraction(200000), Fraction(60)
    assets_before = n*unaffected_spot
    exercises = unaffected_spot > k
    proceeds = m*k if exercises else Fraction(0)
    final_shares = n+m if exercises else n
    share_price = (assets_before+proceeds)/final_shares
    warrant_payoff = share_price-k if exercises else Fraction(0)
    result = foundations.new_issue_terminal_allocation(unaffected_spot, 60, 1000000, 200000)
    assert result["post_exercise_spot"] == pytest.approx(float(share_price))
    assert result["warrant_payoff"] == pytest.approx(float(warrant_payoff))
    assert result["exercise_proceeds"] == pytest.approx(float(proceeds))
    assert n*(unaffected_spot-share_price) == m*warrant_payoff


def test_issue_cost_against_independent_terminal_payoff_density_integral():
    density = lognorm(s=.3*math.sqrt(5), scale=40*math.exp((.03-.3**2/2)*5))
    expected = quad(lambda s: max((1000000*s+200000*60)/1200000-60, 0)*density.pdf(s), 0, math.inf, points=None, epsabs=1e-8)[0]
    result = foundations.new_warrant_issue(40, 60, .03, .3, 5, 1000000, 200000)
    assert result["warrant_price"] == pytest.approx(math.exp(-.15)*expected, abs=1e-8)
    assert 1000000*(40-result["post_issue_spot"]) == pytest.approx(result["issue_cost"], abs=1e-8)


def test_snapshot_15_3_announced_options_have_no_second_dilution():
    payoff = float(option_cashflows(100, 50, 0)["per_unit_payoff"])
    assert payoff == pytest.approx(50)
    # Market spot 100 already values option obligations. Reconstruct assets:
    old_shares = Fraction(100000)
    rights = Fraction(100000)
    assets_before = old_shares*100+rights*50
    post_assets = assets_before+rights*50
    assert float(post_assets/(old_shares+rights)) == pytest.approx(100)
    allocation = foundations.new_issue_terminal_allocation(float(assets_before/old_shares), 50, 100000, 100000)
    assert allocation["warrant_payoff"] == pytest.approx(50)
    assert allocation["post_exercise_spot"] == pytest.approx(100)


def test_new_issue_requires_existing_shareholders():
    with pytest.raises(ValueError):
        foundations.new_warrant_issue(40, 60, .03, .3, 5, 0, 200000)
