"""Hull GE section 11.7: four relations, no printed numeric option example.

Synthetic dates/amounts use an explicit escrowed-dividend model. The PDE
reference solves the log risky-component diffusion with calendar-based obstacles;
it does not call the production lattice or convert cash dividends to a yield.
"""

import math

import numpy as np
import pytest
from hullkit import _option_properties as props
from hullkit import bsm
from scipy.linalg import solve_banded


def independent_dividend_pde(spot, strike, rate, vol, maturity, times, amounts, *, kind, american,
                             n_space=600, n_time=1000):
    schedule = [(t, d) for t, d in zip(times, amounts, strict=True) if t <= maturity]
    prepaid = spot-sum(d*math.exp(-rate*t) for t, d in schedule)
    width = max(math.log(5), 5*vol*math.sqrt(maturity), abs(math.log(strike/prepaid))+math.log(3))
    x = np.linspace(math.log(prepaid)-width, math.log(prepaid)+width, n_space+1)
    risky = np.exp(x)
    dx, dt = x[1]-x[0], maturity/n_time
    diffusion, drift = vol**2/(2*dx**2), (rate-vol**2/2)/(2*dx)
    lower, diagonal, upper = diffusion-drift, -2*diffusion-rate, diffusion+drift
    matrix = np.zeros((3, n_space-1))
    matrix[0, 1:] = -.5*dt*upper
    matrix[1] = 1-.5*dt*diagonal
    matrix[2, :-1] = -.5*dt*lower

    def payoff(stock):
        return np.maximum(stock-strike, 0) if kind == "call" else np.maximum(strike-stock, 0)

    def remaining(t, before=False):
        return sum(d*math.exp(-rate*(ex-t)) for ex, d in schedule
                   if ex > t+1e-10 or (before and abs(ex-t) < 1e-10))

    def obstacle(t):
        return np.maximum(payoff(risky+remaining(t)), payoff(risky+remaining(t, before=True)))

    value = payoff(risky)
    if american:
        value = np.maximum(value, obstacle(maturity))
    for step in range(n_time-1, -1, -1):
        t, tau = step*dt, maturity-step*dt
        if kind == "call":
            lo, hi = 0., max(risky[-1]-strike*math.exp(-rate*tau), 0)
        else:
            lo, hi = max(strike*math.exp(-rate*tau)-risky[0], 0), 0.
        if american:
            immediate = obstacle(t)
            lo, hi = max(lo, immediate[0]), max(hi, immediate[-1])
        rhs = value[1:-1]+.5*dt*(lower*value[:-2]+diagonal*value[1:-1]+upper*value[2:])
        rhs[0] += .5*dt*lower*lo
        rhs[-1] += .5*dt*upper*hi
        value = np.concatenate(([lo], solve_banded((1, 1), matrix, rhs), [hi]))
        if american:
            value = np.maximum(value, immediate)
    return float(np.interp(math.log(prepaid), x, value))


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("american", [False, True])
def test_cash_dividend_tree_independent_pde_and_grid_convergence(kind, american):
    args = (50, 50, .05, .3, 1, [.25, .75], [2, 2])
    coarse = props.cash_dividend_tree(*args, kind=kind, american=american, steps=400)
    fine = props.cash_dividend_tree(*args, kind=kind, american=american, steps=800)
    pde = independent_dividend_pde(*args, kind=kind, american=american)
    assert coarse["price"] == pytest.approx(fine["price"], abs=.006)
    assert fine["price"] == pytest.approx(pde, abs=.003)
    if not american:
        prepaid = 50-2*math.exp(-.05*.25)-2*math.exp(-.05*.75)
        closed = bsm.call_price(prepaid, 50, .05, .3, 1) if kind == "call" else bsm.put_price(prepaid, 50, .05, .3, 1)
        assert fine["price"] == pytest.approx(closed, abs=.001)


def test_hull_11_8_to_11_11_with_actual_american_cash_dividend_prices():
    spot, strike, rate, maturity = 50, 50, .05, 1
    times, amounts = [.25, .75], [2, 2]
    pv = sum(d*math.exp(-rate*t) for t, d in zip(times, amounts, strict=True))
    european, american = {}, {}
    for kind in ("call", "put"):
        european[kind] = props.cash_dividend_tree(spot, strike, rate, .3, maturity, times, amounts,
                                                kind=kind, steps=800)["price"]
        american[kind] = props.cash_dividend_tree(spot, strike, rate, .3, maturity, times, amounts,
                                               kind=kind, american=True, steps=800)["price"]
    assert european["call"] >= bsm.european_call_lower_bound(spot, strike, rate, maturity, pv)-1e-9
    assert european["put"] >= bsm.european_put_lower_bound(spot, strike, rate, maturity, pv)-1e-9
    assert bsm.put_call_parity_residual(european["call"], european["put"], spot, strike, rate, maturity, pv) == pytest.approx(0, abs=1e-9)
    interval = props.american_put_interval(american["call"], spot, strike, rate, maturity, dividend_pv=pv)
    assert interval["put_lower"] <= american["put"] <= interval["put_upper"]
    for kind in ("call", "put"):
        reference = independent_dividend_pde(spot, strike, rate, .3, maturity, times, amounts, kind=kind, american=True)
        assert american[kind] == pytest.approx(reference, abs=.003)


def test_dividend_parity_independent_state_cash_ledger():
    times, amounts = [.25, .75, 1.2], [2, 3, 100]
    rate, maturity, strike = .05, 1., 50.
    # Share dividends are reinvested; the matching portfolio funds each payment date.
    funded_payments = sum(d*math.exp(rate*(maturity-t)) for t, d in zip(times, amounts, strict=True) if t <= maturity)
    for terminal_stock in [0, 20, 50, 80, 100]:
        call_and_bond_and_payments = max(terminal_stock-strike, 0)+strike+funded_payments
        put_and_stock_with_payments = max(strike-terminal_stock, 0)+terminal_stock+funded_payments
        assert call_and_bond_and_payments == pytest.approx(put_and_stock_with_payments)
    assert bsm.pv_dividends(times, amounts, rate, maturity) == pytest.approx(funded_payments*math.exp(-rate*maturity), abs=1e-12)


def test_call_early_exercise_only_at_ex_dates_and_positive_premium():
    args = (40, 35, .05, .2, .5, [.2, .45], [.5, 3])
    american = props.cash_dividend_tree(*args, american=True, steps=600)
    european = props.cash_dividend_tree(*args, steps=600)
    assert american["price"] > european["price"]+.2
    assert american["exercise_times"]
    for time in american["exercise_times"]:
        assert min(abs(time-ex) for ex in [.2, .45]) < 1e-10
    reference = independent_dividend_pde(*args, kind="call", american=True, n_time=1200)
    assert american["price"] == pytest.approx(reference, abs=.012)


@pytest.mark.parametrize("kind,sign", [("call", -1), ("put", 1)])
def test_american_dividend_factor_direction_tree_and_pde(kind, sign):
    prices, references = [], []
    for amount in [1, 3]:
        args = (50, 50, .05, .3, 1, [.5], [amount])
        prices.append(props.cash_dividend_tree(*args, kind=kind, american=True, steps=600)["price"])
        references.append(independent_dividend_pde(*args, kind=kind, american=True))
    assert sign*(prices[1]-prices[0]) > 0
    assert sign*(references[1]-references[0]) > 0
    assert prices == pytest.approx(references, abs=.008)


def test_maturity_dividend_paid_before_european_exercise_with_american_pre_ex_right():
    result_e = props.cash_dividend_tree(60, 50, 0, 0, 1, [1], [15], steps=10)
    result_a = props.cash_dividend_tree(60, 50, 0, 0, 1, [1], [15], american=True, steps=10)
    assert result_e["price"] == pytest.approx(0)
    assert result_a["price"] == pytest.approx(10)


def test_after_maturity_dividends_ignored_and_no_dividend_limit():
    base = props.cash_dividend_tree(50, 50, .05, .3, 1, [], [], steps=600)
    later = props.cash_dividend_tree(50, 50, .05, .3, 1, [1.2], [100], steps=600)
    assert later["price"] == pytest.approx(base["price"], abs=1e-12)
    assert base["price"] == pytest.approx(bsm.call_price(50, 50, .05, .3, 1), abs=.006)


@pytest.mark.parametrize("times,amounts", [([.251], [2]), ([.25], [60])])
def test_tree_unrepresentable_date_or_negative_risky_component(times, amounts):
    with pytest.raises(ValueError):
        props.cash_dividend_tree(50, 50, .05, .3, 1, times, amounts, steps=400)


@pytest.mark.parametrize("volatility", [0, .2])
def test_discounted_dividend_reserve_rebuilds_the_cum_dividend_stock(volatility):
    # D > K: an undiscounted reserve would overstate early exercise by D(1-exp(-r*t_ex)).
    args = (50, 10, .1, volatility, 1, [.5], [20])
    price = props.cash_dividend_tree(*args, american=True, steps=400)["price"]
    expected = 50-10*math.exp(-.05) if volatility == 0 else independent_dividend_pde(*args, kind="call", american=True)
    assert price == pytest.approx(expected, abs=1e-3)


def test_put_can_exercise_just_after_a_large_ex_dividend_drop():
    args = (50, 60, .1, .2, 1, [.5], [15])
    tree = props.cash_dividend_tree(*args, kind="put", american=True, steps=800)
    assert tree["price"] == pytest.approx(independent_dividend_pde(*args, kind="put", american=True), abs=.002)
    assert .5 in tree["exercise_times"]

