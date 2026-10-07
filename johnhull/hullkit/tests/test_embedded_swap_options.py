import importlib
import itertools
import math
from datetime import date, timedelta

import numpy as np
import pytest
from hullkit.rfr import BusinessCalendar
from scipy.integrate import quad
from scipy.stats import norm


def model():
    return importlib.import_module("hullkit._embedded_swap_options")


def test_daily_accrual_two_percent_source_trigger_weekend_and_exact_complement():
    m = model()
    start = date(2021, 1, 22)
    dates = [start + timedelta(days=i) for i in range(5)]
    fix = {start: 0.019, date(2021, 1, 25): 0.021, date(2021, 1, 26): 0.020}
    row = m.known_accrual_coupon(dates, fix, 0.04, 1e6, 0.02, 365, calendar=BusinessCalendar())
    assert row["accruing_days"] == 3
    assert row["coupon"] == pytest.approx(0.04 * 1e6 * 3 / 365, abs=1e-10)
    assert row["coupon"] + row["binary_savings"] == pytest.approx(0.04 * 1e6 * 5 / 365, abs=1e-10)
    assert row["reference_dates"][:3] == (start, start, start)


@pytest.mark.parametrize("loading", [-0.02, 0, 0.02])
def test_binary_actual_pay_measure_independent_normalized_density_and_known_boundary(loading):
    m = model()
    F = 0.025
    K = 0.02
    sigma = 0.3
    T = 0.1
    amount = 100
    discount = 0.99
    rho = 0.4
    row = m.rate_binary(amount, F, K, sigma, T, discount, ratio_loading=loading, correlation=rho)
    boundary = (math.log(K / F) + 0.5 * sigma * sigma * T) / (sigma * math.sqrt(T))
    probability = quad(
        lambda z: (
            math.exp(rho * loading * math.sqrt(T) * z - 0.5 * (rho * loading) ** 2 * T)
            * norm.pdf(z)
        ),
        boundary,
        12,
        epsabs=1e-13,
    )[0]
    assert row["price"] == pytest.approx(amount * discount * probability, abs=1e-11)
    below = m.rate_binary(
        amount, F, K, sigma, T, discount, ratio_loading=loading, correlation=rho, below=True
    )
    assert row["price"] + below["price"] == pytest.approx(amount * discount, abs=1e-12)
    assert m.rate_binary(amount, K, K, 0, T, discount)["price"] == pytest.approx(amount * discount)
    assert m.rate_binary(amount, K, K, 0, T, discount, below=True)["price"] == pytest.approx(0)


def test_source_cancel_right_directions_six_by_four_and_semianual_two_to_five():
    m = model()
    own = m.cancellation_option_terms(True, "owner", [6], 10)
    assert own["kind"] == "payer" and own["position"] == "long"
    assert own["tenors"] == pytest.approx([4])
    opp = m.cancellation_option_terms(True, "counterparty", np.arange(2, 5.01, 0.5), 5)
    assert opp["kind"] == "receiver" and opp["position"] == "short"
    assert m.cancellation_option_terms(False, "owner", [6], 10)["kind"] == "receiver"


def simple_rate(prefix):
    return 0.045 + 0.02 * (2 * sum(prefix) - len(prefix))


def binary_plain_tree():
    discounts = []
    successors = []
    probabilities = []
    cash = []
    for i in range(3):
        prefixes = list(itertools.product([0, 1], repeat=i))
        r = np.array([simple_rate(p) for p in prefixes])
        discounts.append(1 / (1 + r))
        successors.append(np.arange(2 ** (i + 1)).reshape(-1, 2))
        probabilities.append(np.full((2**i, 2), 0.5))
        cash.append(1e6 * (0.05 - r))
    return discounts, successors, probabilities, cash


def enumerate_policies(compound=False, spread=0.0):
    nodes = [p for i in [1, 2] for p in itertools.product([0, 1], repeat=i)]
    results = []
    for actions in itertools.product([False, True], repeat=6):
        policy = dict(zip(nodes, actions, strict=True))
        values = []
        for bits in itertools.product([0, 1], repeat=3):
            df = 1.0
            value = 0.0
            af = ax = 0.0
            for i in range(3):
                r = simple_rate(bits[:i])
                df /= 1 + r
                if compound:
                    # Independent sum of each coupon times remaining products,
                    # truncated at the policy's first exercise date.
                    af = af * (1 + r + spread) + 1e6 * r
                    ax = ax * 1.039 + 1e6 * 0.04
                else:
                    value += df * 1e6 * (0.05 - r)
                if i == 2 or policy.get(bits[: i + 1], False):
                    if compound:
                        value = df * (af - ax)
                    break
            values.append(value)
        results.append(np.mean(values))
    return np.array(results)


@pytest.mark.parametrize("holder", ["owner", "counterparty"])
def test_plain_cancelable_tree_against_all_sixty_four_stopping_policies(holder):
    m = model()
    ds, children, p, cf = binary_plain_tree()
    row = m.cancelable_cashflow_tree(ds, children, p, cf, [1, 2], holder=holder)
    policies = enumerate_policies()
    exact = policies.max() if holder == "owner" else policies.min()
    assert row["price"] == pytest.approx(exact, abs=1e-8)
    base = m.cancelable_cashflow_tree(ds, children, p, cf, [], holder=holder)["price"]
    if holder == "owner":
        assert row["price"] >= base
    else:
        assert row["price"] <= base


@pytest.mark.parametrize("spread", [0.0, 0.01])
@pytest.mark.parametrize("holder", ["owner", "counterparty"])
def test_compounding_cancel_settles_full_balances_and_matches_exhaustive_policies(spread, holder):
    m = model()
    row = m.compounding_cancellation_tree(
        [0, 1, 2, 3], simple_rate, 1e6, 0.04, 0.039, [1, 2], compound_spread=spread, holder=holder
    )
    prices = enumerate_policies(compound=True, spread=spread)
    exact = prices.max() if holder == "owner" else prices.min()
    assert row["price"] == pytest.approx(exact, abs=1e-8)
    first = row["states"][1][(0,)]
    assert first["settlement"] == pytest.approx(5000, abs=1e-9)
    assert first["floating_balance"] == pytest.approx(45000, abs=1e-9)
    assert first["fixed_balance"] == pytest.approx(40000, abs=1e-9)
    assert abs(row["price"]) > 1000


def test_single_cancel_plain_equals_swap_plus_opposite_european_on_identical_tree():
    m = model()
    ds, children, p, cf = binary_plain_tree()
    base = m.cancelable_cashflow_tree(ds, children, p, cf, [], holder="owner")
    cancel = m.cancelable_cashflow_tree(ds, children, p, cf, [2], holder="owner")
    # At date2, offset swaption payoff=max(-remaining receiver swap,0).
    premium = 0.0
    for bits in itertools.product([0, 1], repeat=2):
        rate = simple_rate(bits)
        remaining = 1e6 * (0.05 - rate) / (1 + rate)
        df = math.prod(1 / (1 + simple_rate(bits[:i])) for i in range(2))
        premium += 0.25 * df * max(-remaining, 0)
    assert cancel["price"] == pytest.approx(base["price"] + premium, abs=1e-8)


def test_four_step_compounding_spread_proxy_is_labeled_approximate():
    m = model()
    rates = np.array([0.045, 0.05, 0.055])
    growth = 1 + rates
    P = 1 / math.prod(growth)
    row = m.compounding_spread_proxy(
        rates,
        np.ones(3),
        1e6,
        0.04,
        0.039,
        P,
        compound_spread=0.01,
        floating_balance=2000,
        fixed_balance=1000,
    )
    coupon = 1e6 * rates
    terminal = sum(
        c * math.prod((growth + 0.01)[i + 1 :]) for i, c in enumerate(coupon)
    ) + 2000 * math.prod(growth + 0.01)
    assert row["step1_floating_pv"] == pytest.approx(P * terminal, abs=1e-8)
    assert row["step2_no_spread_pv"] == pytest.approx(2000 + 1e6 * (1 - P), abs=1e-8)
    assert row["spread_pv"] > 0
    assert row["exercise_settlement"] == pytest.approx(1000)
    assert "approximation" in row["method"]
    with pytest.raises(ValueError):
        m.compounding_cancellation_tree([0, 1], simple_rate, 1e6, 0.04, 0.039, [2])


def test_binary_earlier_later_payment_loading_and_same_rate_different_accrued_states():
    m = model()
    earlier = m.binary_payment_loading(0.1, 0.3, 0.2, 0.04, 0.2)
    later = m.binary_payment_loading(0.1, 0.2, 0.3, 0.04, 0.2)
    assert earlier == pytest.approx(-later, abs=1e-15)
    assert earlier > 0
    assert m.binary_payment_loading(0.1, 0.3, 0.3, 0.04, 0.2) == pytest.approx(0)
    row = m.compounding_cancellation_tree([0, 1, 2, 3], simple_rate, 1e6, 0.04, 0.039, [1, 2])
    assert simple_rate((0, 1)) == pytest.approx(simple_rate((1, 0)), abs=1e-15)
    assert (
        abs(
            row["states"][2][(0, 1)]["floating_balance"]
            - row["states"][2][(1, 0)]["floating_balance"]
        )
        > 1000
    )
