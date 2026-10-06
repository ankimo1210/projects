"""Hull 18.1 all four settlement and quote examples."""
from fractions import Fraction

import pytest
from hullkit import _futures_options as futures


def test_example_18_1_copper_two_settlement_legs():
    result = futures.futures_exercise_cash(331, 330, 320, multiplier=25000/100)
    assert [result["settlement"], result["close_cash"], result["payoff"], result["position"]] == pytest.approx([2500, 250, 2750, 1])


def test_example_18_2_corn_short_futures_close_loss():
    result = futures.futures_exercise_cash(580, 579, 600, multiplier=5000/100, kind="put")
    assert [result["settlement"], result["close_cash"], result["payoff"], result["position"]] == pytest.approx([1050, -50, 1000, -1])


def test_example_18_3_sofr_quote_premium_payoff_and_profit():
    assert futures.rate_from_futures_quote(99.35) == pytest.approx(.0065)
    result = futures.futures_exercise_cash(99.7, 99.7, 99.5, multiplier=2500, premium=.05)
    assert [result["premium_cash"], result["payoff"], result["profit"]] == pytest.approx([125, 500, 375], abs=1e-9)


def test_example_18_4_treasury_fractional_quotes_and_contract_profit():
    assert futures.fractional_quote(96, 9, 32) == pytest.approx(96.28125)
    premium = futures.fractional_quote(1, 4, 64)
    assert premium == pytest.approx(1.0625)
    result = futures.futures_exercise_cash(100, 100, 98, multiplier=100000/100, premium=premium)
    assert result["profit"] == pytest.approx(937.50)


@pytest.mark.parametrize("current,last,strike,kind", [(331, 315, 320, "call"), (-40, -25, -30, "put")])
def test_independent_fraction_two_leg_ledger_including_negative_initial_cash(current, last, strike, kind):
    sign = 1 if kind == "call" else -1
    amount = Fraction(25000, 100)
    settlement = sign*(last-strike)*amount
    close_cash = sign*(current-last)*amount
    result = futures.futures_exercise_cash(current, last, strike, multiplier=float(amount), kind=kind)
    assert [result["settlement"], result["close_cash"], result["payoff"]] == pytest.approx([float(settlement), float(close_cash), float(settlement+close_cash)])
    assert settlement < 0


def test_unexercised_option_leaves_no_futures_position_but_loses_premium():
    result = futures.futures_exercise_cash(300, 330, 320, multiplier=250, premium=5)
    assert result["position"] == 0
    assert [result["settlement"], result["close_cash"], result["profit"]] == pytest.approx([0, 0, -1250])


def test_quote_ticks_and_contract_multiplier_have_mathematical_limits():
    with pytest.raises(ValueError):
        futures.fractional_quote(96, 32, 32)
    with pytest.raises(ValueError):
        futures.futures_exercise_cash(100, 100, 98, multiplier=0)
