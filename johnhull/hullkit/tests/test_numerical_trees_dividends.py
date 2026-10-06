"""Hull21.3: S* cash dividends, proportional jumps and same-tree control."""

import math

import numpy as np
import pytest
from hullkit import _numerical_trees as numerical
from hullkit import bsm
from scipy.linalg import solve_banded


def independent_dividend_pde(
    spot, strike, rate, vol, maturity, times, amounts, *, kind, american, n_space=600, n_time=1000
):
    schedule = [(t, d) for t, d in zip(times, amounts, strict=True) if t <= maturity]
    prepaid = spot - sum(d * math.exp(-rate * t) for t, d in schedule)
    width = max(
        math.log(5), 5 * vol * math.sqrt(maturity), abs(math.log(strike / prepaid)) + math.log(3)
    )
    x = np.linspace(math.log(prepaid) - width, math.log(prepaid) + width, n_space + 1)
    risky = np.exp(x)
    dx, dt = x[1] - x[0], maturity / n_time
    diffusion, drift = vol**2 / (2 * dx**2), (rate - vol**2 / 2) / (2 * dx)
    lower, diagonal, upper = diffusion - drift, -2 * diffusion - rate, diffusion + drift
    matrix = np.zeros((3, n_space - 1))
    matrix[0, 1:] = -0.5 * dt * upper
    matrix[1] = 1 - 0.5 * dt * diagonal
    matrix[2, :-1] = -0.5 * dt * lower

    def payoff(stock):
        return np.maximum(stock - strike, 0) if kind == "call" else np.maximum(strike - stock, 0)

    def remaining(t, before=False):
        return sum(
            d * math.exp(-rate * (ex - t))
            for ex, d in schedule
            if ex > t + 1e-10 or (before and abs(ex - t) < 1e-10)
        )

    def obstacle(t):
        return np.maximum(payoff(risky + remaining(t)), payoff(risky + remaining(t, before=True)))

    value = payoff(risky)
    if american:
        value = np.maximum(value, obstacle(maturity))
    for step in range(n_time - 1, -1, -1):
        t, tau = step * dt, maturity - step * dt
        if kind == "call":
            lo, hi = 0.0, max(risky[-1] - strike * math.exp(-rate * tau), 0)
        else:
            lo, hi = max(strike * math.exp(-rate * tau) - risky[0], 0), 0.0
        if american:
            immediate = obstacle(t)
            lo, hi = max(lo, immediate[0]), max(hi, immediate[-1])
        rhs = value[1:-1] + 0.5 * dt * (
            lower * value[:-2] + diagonal * value[1:-1] + upper * value[2:]
        )
        rhs[0] += 0.5 * dt * lower * lo
        rhs[-1] += 0.5 * dt * upper * hi
        value = np.concatenate(([lo], solve_banded((1, 1), matrix, rhs), [hi]))
        if american:
            value = np.maximum(value, immediate)
    return float(np.interp(math.log(prepaid), x, value))


def independent_stopping(spot, strike, rate, sigma, time, steps, ex, dividend, kind, model):
    dt = time / steps
    up, down = math.exp(sigma * math.sqrt(dt)), math.exp(-sigma * math.sqrt(dt))
    p = (math.exp(rate * dt) - down) / (up - down)
    bits = (np.arange(2**steps)[:, None] >> np.arange(steps)) & 1
    downs = np.column_stack((np.zeros(2**steps, dtype=int), bits.cumsum(axis=1)))
    levels = np.arange(steps + 1)
    risky = spot - (dividend * math.exp(-rate * ex) if model == "cash" else 0)
    stock = risky * np.exp(sigma * math.sqrt(dt) * (levels - 2 * downs))
    if model == "cash":
        reserve = np.where(
            levels * dt < ex - 1e-12, dividend * np.exp(-rate * (ex - levels * dt)), 0
        )
        stock = stock + reserve
    else:
        stock = stock * np.where(levels * dt < ex - 1e-12, 1, 1 - dividend)
    sign = 1 if kind == "call" else -1
    payoffs = np.maximum(sign * (stock - strike), 0) * np.exp(-rate * levels * dt)
    weights = p ** (steps - downs[:, -1]) * (1 - p) ** downs[:, -1]
    # All node-dependent first-exercise policies, independently summed by path.
    node_ids = levels[:-1] * (levels[:-1] + 1) // 2 + downs[:, :-1]
    masks = np.arange(2 ** (steps * (steps + 1) // 2))
    chosen = ((masks[:, None, None] >> node_ids[None, :, :]) & 1).astype(bool)
    chosen = np.concatenate((chosen, np.ones((*chosen.shape[:2], 1), dtype=bool)), axis=2)
    first = chosen.argmax(axis=2)
    return float(np.max(payoffs[np.arange(2**steps)[None, :], first] @ weights))


@pytest.mark.parametrize("steps,printed", [(5, 4.44), (50, 4.208), (100, 4.214)])
def test_example_21_5_dividend_prices(steps, printed):
    result = numerical.dividend_lattice(
        52, 50, 0.1, 0.4, 5 / 12, steps, [3.5 / 12], [2.06], kind="put", american=True
    )
    assert result["price"] == pytest.approx(printed, abs=0.005 if steps == 5 else 0.0005)
    assert result["risky_spot"] == pytest.approx(52 - 2.06 * math.exp(-0.1 * 3.5 / 12), abs=1e-12)
    assert bool(result["off_grid_dividend_times"]) == (steps == 5)


def test_figure_21_9_all_stock_and_option_nodes():
    result = numerical.dividend_lattice(
        52, 50, 0.1, 0.4, 5 / 12, 5, [3.5 / 12], [2.06], kind="put", american=True
    )
    stocks = [
        [52],
        [58.14, 46.56],
        [65.02, 52.03, 41.72],
        [72.75, 58.17, 46.60, 37.41],
        [79.35, 62.99, 50, 39.69, 31.50],
        [89.06, 70.70, 56.12, 44.55, 35.36, 28.07],
    ]
    prices = [
        [4.44],
        [2.16, 6.86],
        [0.64, 3.77, 10.16],
        [0, 1.30, 6.38, 14.22],
        [0, 0, 2.66, 10.31, 18.50],
        [0, 0, 0, 5.45, 14.64, 21.93],
    ]
    for actual, source in zip(result["stock"], stocks, strict=True):
        assert actual == pytest.approx(source, abs=0.005)
    for actual, source in zip(result["option"], prices, strict=True):
        assert actual == pytest.approx(source, abs=0.005)


@pytest.mark.parametrize("model,dividend", [("cash", 2.06), ("fraction", 0.04)])
def test_grid_exercise_against_independent_all_stopping_policies(model, dividend):
    result = numerical.dividend_lattice(
        52, 50, 0.1, 0.4, 5 / 12, 5, [3.5 / 12], [dividend], kind="put", american=True, model=model
    )
    reference = independent_stopping(52, 50, 0.1, 0.4, 5 / 12, 5, 3.5 / 12, dividend, "put", model)
    assert result["price"] == pytest.approx(reference, abs=1e-11)


def test_source_cash_dividend_independent_pde_on_same_s_star_model():
    result = numerical.dividend_lattice(
        52, 50, 0.1, 0.4, 5 / 12, 400, [3.5 / 12], [2.06], kind="put", american=True
    )
    reference = independent_dividend_pde(
        52, 50, 0.1, 0.4, 5 / 12, [3.5 / 12], [2.06], kind="put", american=True
    )
    assert result["price"] == pytest.approx(reference, abs=0.007)


def test_proportional_dividends_compound_and_european_terminal_law():
    result = numerical.dividend_lattice(
        52, 50, 0.05, 0.3, 1, 1000, [0.3, 0.6], [0.04, 0.07], model="fraction", kind="call"
    )
    reference = bsm.call_price(52 * (1 - 0.04) * (1 - 0.07), 50, 0.05, 0.3, 1)
    assert result["price"] == pytest.approx(reference, abs=0.003)
    assert result["terminal_scale"] == pytest.approx(0.96 * 0.93, abs=1e-12)


def test_aligned_ex_date_american_call_can_exercise_before_cash_drop():
    result = numerical.dividend_lattice(
        60, 50, 0.05, 0.1, 0.5, 20, [0.25], [5], kind="call", american=True
    )
    assert not result["off_grid_dividend_times"]
    assert np.any(result["exercise"][10])
    assert result["before_stock"][10] - result["stock"][10] == pytest.approx(
        np.full(11, 5), abs=1e-12
    )


def test_source_control_variate_same_tree_and_unrounded_prices():
    result = numerical.dividend_control_variate(50, 50, 0.1, 0.4, 5 / 12, 5)
    assert result["american"] == pytest.approx(4.49, abs=0.005)
    assert result["european_tree"] == pytest.approx(4.32, abs=0.005)
    assert result["european_reference"] == pytest.approx(4.08, abs=0.005)
    assert result["corrected"] == pytest.approx(4.2454208, abs=1e-7)
    assert result["corrected"] == pytest.approx(4.25, abs=0.005)
    assert abs(result["corrected"] - 4.278059) < abs(result["american"] - 4.278059)


def test_cash_control_uses_same_dividend_deducted_european_reference():
    result = numerical.dividend_control_variate(52, 50, 0.1, 0.4, 5 / 12, 50, [3.5 / 12], [2.06])
    risky = 52 - 2.06 * math.exp(-0.1 * 3.5 / 12)
    reference = bsm.put_price(risky, 50, 0.1, 0.4, 5 / 12)
    assert result["european_reference"] == pytest.approx(reference, abs=1e-12)
    assert result["corrected"] == pytest.approx(
        result["american"] - result["european_tree"] + reference, abs=1e-12
    )


def independent_dividend_tree(spot, strike, rate, sigma, maturity, steps, times, amounts, *, model, kind):
    # Node-index alignment, so it does not share the module's float time comparisons.
    dt = maturity / steps
    up = math.exp(sigma * math.sqrt(dt))
    p = (math.exp(rate * dt) - 1 / up) / (up - 1 / up)
    index = [round(t / dt) for t in times]
    risky = spot - sum(d * math.exp(-rate * t) for t, d in zip(times, amounts, strict=True)) if model == "cash" else spot

    def payoff(stock):
        return np.maximum(stock - strike, 0) if kind == "call" else np.maximum(strike - stock, 0)

    def prices(i):
        base = risky * up ** (i - 2 * np.arange(i + 1))
        if model == "cash":
            after = base + sum(d * math.exp(-rate * (k - i) * dt) for k, d in zip(index, amounts, strict=True) if k > i)
            return after, after + sum(d for k, d in zip(index, amounts, strict=True) if k == i)
        after = base * math.prod(1 - f for k, f in zip(index, amounts, strict=True) if k <= i)
        return after, base * math.prod(1 - f for k, f in zip(index, amounts, strict=True) if k < i)

    after, before = prices(steps)
    value = np.maximum(payoff(after), payoff(before))
    for i in range(steps - 1, -1, -1):
        after, before = prices(i)
        value = np.maximum(math.exp(-rate * dt) * (p * value[:-1] + (1 - p) * value[1:]), np.maximum(payoff(after), payoff(before)))
    return float(value[0])


@pytest.mark.parametrize(
    "args,times,amounts,model,kind",
    [
        ((60, 50, 0.05, 0.1, 0.5, 20), [0.25], [5], "cash", "call"),
        ((52, 50, 0.1, 0.4, 5 / 12, 10), [3.5 / 12], [0.04], "fraction", "put"),
        ((60, 50, 0.05, 0.1, 0.3, 7), [5 * 0.3 / 7], [3], "cash", "call"),
    ],
)
def test_american_aligned_dividend_lattice_matches_an_independent_node_index_tree(args, times, amounts, model, kind):
    result = numerical.dividend_lattice(*args, times, amounts, model=model, kind=kind, american=True)
    assert not result["off_grid_dividend_times"]
    expected = independent_dividend_tree(*args, times, amounts, model=model, kind=kind)
    assert result["price"] == pytest.approx(expected, abs=1e-10)

