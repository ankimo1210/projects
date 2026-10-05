"""Hull GE section 11.4: thirteen printed values, parity and capital structure."""

import math
from decimal import Decimal, localcontext

import numpy as np
import pytest
from hullkit import _option_properties as props
from hullkit import bsm, fd, trees
from scipy.integrate import quad


def test_hull_table_11_3_first_arbitrage_five_printed_values():
    result = props.parity_arbitrage([0, 29, 30, 31, 80], 31, 30, .1, .25, 3, 2.25)
    assert result["portfolio_a"] == pytest.approx(32.26, abs=.005)
    assert result["portfolio_c"] == pytest.approx(33.25)
    assert result["initial_bank"] == pytest.approx(30.25)
    assert result["terminal_bank"] == pytest.approx(31.02, abs=.005)
    assert result["profit"] == pytest.approx(np.full(5, 1.02), abs=.005)
    assert result["call_quantity"] == pytest.approx(1)


def test_hull_table_11_3_second_arbitrage_four_printed_values():
    result = props.parity_arbitrage([0, 29, 30, 31, 80], 31, 30, .1, .25, 3, 1)
    assert result["portfolio_c"] == pytest.approx(32)
    assert result["initial_bank"] == pytest.approx(-29)
    assert -result["terminal_bank"] == pytest.approx(29.73, abs=.005)
    assert result["profit"] == pytest.approx(np.full(5, .27), abs=.005)
    assert result["call_quantity"] == pytest.approx(-1)


def test_hull_example_11_3_four_printed_values():
    result = props.american_put_interval(1.5, 19, 20, .1, 5/12)
    assert result["put_minus_call_lower"] == pytest.approx(.18, abs=.005)
    assert result["put_minus_call_upper"] == pytest.approx(1)
    assert result["put_lower"] == pytest.approx(1.68, abs=.005)
    assert result["put_upper"] == pytest.approx(2.5)


@pytest.mark.parametrize("put_quote", [2.25, 1])
def test_parity_arbitrage_independent_exercise_cash_ledger(put_quote):
    terminals = [0, 15, 30, 40, 100]
    result = props.parity_arbitrage(terminals, 31, 30, .1, .25, 3, put_quote)
    direction = 1 if put_quote == 2.25 else -1
    with localcontext() as context:
        context.prec = 40
        growth = Decimal('.025').exp()
        bank = Decimal(str(direction*(31+put_quote-3))) * growth
        expected = []
        for terminal in terminals:
            # ST>K: buy via call and return the share, or reverse both actions.
            # ST<K: assigned short put delivers the cover share, or reverse.
            exercise_cash = -direction*30
            share_purchase = direction*terminal
            cover_short = -direction*terminal
            expected.append(float(bank) + exercise_cash + share_purchase + cover_short)
    assert result["profit"] == pytest.approx(expected, abs=1e-12)
    gap = result["portfolio_a"]-result["portfolio_c"]
    assert result["profit"] == pytest.approx(np.full(5, abs(gap)*math.exp(.025)), abs=1e-12)


def test_parity_exact_replication_table_11_2():
    terminals = np.array([0, 10, 30, 50, 100.])
    call_cash = np.maximum(terminals-30, 0)
    put_cash = np.maximum(30-terminals, 0)
    assert call_cash+30 == pytest.approx(put_cash+terminals, abs=1e-12)
    implied_put = 3+30*math.exp(-.025)-31
    result = props.parity_arbitrage(terminals, 31, 30, .1, .25, 3, implied_put)
    assert result["profit"] == pytest.approx(np.zeros(5), abs=1e-12)


@pytest.mark.parametrize("spot", [15, 19, 25])
def test_american_parity_interval_with_actual_crr_and_pde_prices(spot):
    prices = []
    for kind in ("call", "put"):
        tree = trees.crr_price(spot, 20, .1, .3, 5/12, 800, kind=kind, american=True)
        pde = fd.fd_vanilla(spot, 20, .1, .3, 5/12, kind=kind, american=True, n_s=400, n_t=600)
        assert tree == pytest.approx(pde, abs=.008)
        prices.append((tree, pde))
    for call, put in zip(*prices, strict=True):
        interval = props.american_put_interval(call, spot, 20, .1, 5/12)
        assert interval["put_lower"]-1e-10 <= put <= interval["put_upper"]+1e-10


def test_business_snapshot_11_1_state_and_present_value_conservation():
    terminal = np.array([0, 10, 50, 100.])
    split = props.capital_structure_payoffs(terminal, 50)
    assert split["equity"] == pytest.approx([0, 0, 0, 50])
    assert split["debt"] == pytest.approx([0, 10, 50, 50])
    assert split["equity"]+split["debt"] == pytest.approx(terminal)
    # Independent expectation of debt min(A_T,K), contrasted with PV(K)-put.
    def discounted_debt(z):
        asset = 50*math.exp((.05-.3**2/2)+.3*z)
        return math.exp(-.05)*min(asset, 50)*math.exp(-z*z/2)/math.sqrt(2*math.pi)
    crossing = -(.05-.3**2/2)/.3
    debt = quad(discounted_debt, -10, crossing)[0]+quad(discounted_debt, crossing, 10)[0]
    assert debt == pytest.approx(50*math.exp(-.05)-bsm.put_price(50, 50, .05, .3, 1), abs=1e-9)
    assert bsm.call_price(50, 50, .05, .3, 1)+debt == pytest.approx(50, abs=1e-9)


def test_american_hull_interval_rejects_negative_rate_premise():
    with pytest.raises(ValueError, match="nonnegative rate"):
        props.american_put_interval(1, 19, 20, -.1, .5)
