"""Hull GE section 11.3: all eleven printed values and physical arbitrage."""

from decimal import Decimal, localcontext

import numpy as np
import pytest
from hullkit import _option_properties as props
from hullkit import trees


def test_hull_call_lower_bound_and_arbitrage_five_printed_values():
    bounds = props.no_dividend_bounds(20, 18, .10, 1)
    assert bounds["call_lower"] == pytest.approx(3.71, abs=.005)
    result = props.bound_arbitrage([25, 17], 20, 18, .10, 1, 3, kind="call")
    assert result["initial_bank"] == pytest.approx(17)
    assert result["terminal_bank"] == pytest.approx(18.79, abs=.005)
    assert result["profit"] == pytest.approx([.79, 1.79], abs=.005)
    assert result["minimum_profit"] == pytest.approx(.79, abs=.005)


def test_hull_put_lower_bound_and_arbitrage_four_printed_values():
    bounds = props.no_dividend_bounds(37, 40, .05, .5)
    assert bounds["put_lower"] == pytest.approx(2.01, abs=.005)
    result = props.bound_arbitrage([35, 42], 37, 40, .05, .5, 1, kind="put")
    assert result["initial_bank"] == pytest.approx(-38)
    assert -result["terminal_bank"] == pytest.approx(38.96, abs=.005)
    assert result["profit"] == pytest.approx([1.04, 3.04], abs=.005)


def test_hull_examples_11_1_and_11_2():
    assert props.no_dividend_bounds(51, 50, .12, .5)["call_lower"] == pytest.approx(3.91, abs=.005)
    assert props.no_dividend_bounds(38, 40, .10, .25)["put_lower"] == pytest.approx(1.01, abs=.005)


@pytest.mark.parametrize("kind,spot,strike,rate,maturity,quote", [
    ("call", 20, 18, .1, 1, 3), ("put", 37, 40, .05, .5, 1),
])
def test_lower_bound_arbitrage_independent_physical_settlement(kind, spot, strike, rate, maturity, quote):
    terminals = [0, strike-1, strike, strike+1, 100]
    result = props.bound_arbitrage(terminals, spot, strike, rate, maturity, quote, kind=kind)
    with localcontext() as ctx:
        ctx.prec = 40
        growth = (Decimal(str(rate)) * Decimal(str(maturity))).exp()
        expected = []
        for terminal in terminals:
            if kind == "call":
                # Exercise to buy the cover stock for K, or buy it at the market.
                cover_cost = strike if terminal > strike else terminal
                expected.append(float(Decimal(str(spot-quote))*growth-Decimal(cover_cost)))
            else:
                # Sell the owned share through exercise, or at the market.
                sale_cash = strike if terminal < strike else terminal
                expected.append(float(Decimal(sale_cash)-Decimal(str(spot+quote))*growth))
    assert result["profit"] == pytest.approx(expected, abs=1e-12)
    assert np.min(result["profit"]) == pytest.approx(result["minimum_profit"], abs=1e-12)


@pytest.mark.parametrize("spot,strike,rate,maturity", [(20, 18, .1, 1), (37, 40, .05, .5),
                                                      (50, 50, .05, 1)])
@pytest.mark.parametrize("american", [False, True])
def test_model_free_bounds_contain_independent_crr_prices(spot, strike, rate, maturity, american):
    bounds = props.no_dividend_bounds(spot, strike, rate, maturity, american=american)
    for kind in ("call", "put"):
        price = trees.crr_price(spot, strike, rate, .3, maturity, 500, kind=kind, american=american)
        assert bounds[kind+"_lower"] - 1e-10 <= price <= bounds[kind+"_upper"] + 1e-10


def test_bounds_zero_endpoints_and_negative_rate_american_extension():
    bounds = props.no_dividend_bounds(0, 10, .05, 0, american=True)
    assert [bounds["call_lower"], bounds["call_upper"]] == pytest.approx([0, 0])
    assert [bounds["put_lower"], bounds["put_upper"]] == pytest.approx([10, 10])
    # For negative rates K is no longer an American-put upper bound.
    negative = props.no_dividend_bounds(1, 10, -.05, 1, american=True)
    assert negative["put_upper"] > 10
    assert negative["put_lower"] > 9


@pytest.mark.parametrize("maturity,terminal", [(-1, [20]), (1, [-1])])
def test_arbitrage_undefined_inputs(maturity, terminal):
    with pytest.raises(ValueError):
        props.bound_arbitrage(terminal, 20, 18, .1, maturity, 3, kind="call")
