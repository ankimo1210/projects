"""Hull GE section 12.2: four stock/option positions and dated dividend cash."""

import math
from decimal import Decimal, localcontext

import numpy as np
import pytest
from hullkit import _option_strategies as strategies
from hullkit import bsm


@pytest.mark.parametrize(
    "name,sign,protective",
    [
        ("covered_call", 1, False),
        ("reverse_covered_call", -1, False),
        ("protective_put", 1, True),
        ("reverse_protective_put", -1, True),
    ],
)
def test_figure_12_1_four_positions_independent_piecewise_payoff_and_cost(name, sign, protective):
    terminal = np.array([0, 30, 50, 70, 100.0])
    legs = strategies.stock_option_legs(name, 50)
    result = strategies.strategy_profit(terminal, legs, [50, 4])
    independent = sign * (np.maximum(terminal, 50) if protective else np.minimum(terminal, 50))
    cost = sign * (54 if protective else 46)
    assert result["payoff"] == pytest.approx(independent)
    assert result["initial_cost"] == pytest.approx(cost)
    assert result["profit"] == pytest.approx(independent - cost)
    assert result["dividend_cash"] == pytest.approx(0)


@pytest.mark.parametrize("name", ["covered_call", "protective_put"])
def test_equation_12_1_current_cost_and_dated_terminal_replication(name):
    spot, strike, rate, vol, maturity = 50, 50, 0.05, 0.3, 1
    times, amounts = [0.25, 0.75], [1, 2]
    pv = bsm.pv_dividends(times, amounts, rate, maturity)
    call = bsm.call_price_cash_dividends(spot, strike, rate, vol, maturity, times, amounts)
    put = bsm.put_price_cash_dividends(spot, strike, rate, vol, maturity, times, amounts)
    protective = name == "protective_put"
    result = strategies.strategy_profit(
        [0, 50, 100],
        strategies.stock_option_legs(name, strike),
        [spot, put if protective else call],
        maturity=maturity,
        dividend_times=times,
        dividend_amounts=amounts,
        reinvest_rate=rate,
    )
    matched_cost = (
        call + strike * math.exp(-rate * maturity) + pv
        if protective
        else strike * math.exp(-rate * maturity) + pv - put
    )
    assert result["initial_cost"] == pytest.approx(matched_cost, abs=1e-12)
    with localcontext() as context:
        context.prec = 40
        dividends = sum(
            Decimal(d) * (Decimal(".05") * (Decimal(1) - Decimal(str(t)))).exp()
            for t, d in zip(times, amounts, strict=True)
        )
    assert result["dividend_cash"] == pytest.approx(float(dividends), abs=1e-12)
    for terminal, total_cash in zip([0, 50, 100], result["total_cash"], strict=True):
        other_option = max(terminal - strike, 0) if protective else -max(strike - terminal, 0)
        assert total_cash == pytest.approx(other_option + strike + float(dividends), abs=1e-12)


def test_short_stock_dividends_are_debits_and_after_maturity_payment_ignored():
    legs = strategies.stock_option_legs("reverse_covered_call", 50)
    result = strategies.strategy_profit(
        [60],
        legs,
        [50, 4],
        maturity=1,
        dividend_times=[0.25, 0.75, 1.25],
        dividend_amounts=[1, 2, 100],
    )
    assert result["dividend_cash"] == pytest.approx(-3)
    assert result["profit"] == pytest.approx([-7])


def test_missing_schedule_horizon_or_premium_alignment_rejected():
    legs = strategies.stock_option_legs("covered_call", 50)
    with pytest.raises(ValueError):
        strategies.strategy_profit([50], legs, [50])
    with pytest.raises(ValueError):
        strategies.strategy_profit([50], legs, [50, 4], dividend_times=[0.5], dividend_amounts=[1])
