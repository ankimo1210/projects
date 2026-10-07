"""Hull GE 15.12: cash-dividend model, fixed-date exercise and Black approximation."""

import math
from decimal import Decimal, localcontext

import pytest
from hullkit import _bsm_foundations as foundations
from hullkit import bsm
from hullkit._option_properties import cash_dividend_tree
from scipy.integrate import quad
from scipy.stats import lognorm

TIMES, AMOUNTS = [2 / 12, 5 / 12], [0.5, 0.5]


def test_example_15_9_all_printed_intermediates_and_call():
    result = foundations.cash_dividend_call_details(40, 40, 0.09, 0.3, 0.5, TIMES, AMOUNTS)
    assert [
        result["dividend_pv"],
        result["risky_spot"],
        result["d1"],
        result["d2"],
    ] == pytest.approx([0.9742, 39.0258, 0.2020, -0.0102], abs=0.00005, rel=0)
    assert [result["stock_weight"], result["exercise_probability"]] == pytest.approx(
        [0.5800, 0.4959], abs=0.00005, rel=0
    )
    assert result["price"] == pytest.approx(3.67, abs=0.005, rel=0)


def test_dividend_price_against_independent_decimal_reserve_and_payoff_integral():
    with localcontext() as context:
        context.prec = 40
        r = Decimal(".09")
        dates = [Decimal(2) / 12, Decimal(5) / 12]
        pv = sum(Decimal(".5") * (-r * t).exp() for t in dates)
        risky = Decimal(40) - pv
    density = lognorm(
        s=0.3 * math.sqrt(0.5), scale=float(risky) * math.exp((0.09 - 0.3**2 / 2) * 0.5)
    )
    price = math.exp(-0.045) * quad(lambda x: (x - 40) * density.pdf(x), 40, math.inf)[0]
    result = foundations.cash_dividend_call_details(40, 40, 0.09, 0.3, 0.5, TIMES, AMOUNTS)
    assert result["dividend_pv"] == pytest.approx(float(pv), abs=1e-14)
    assert result["price"] == pytest.approx(price, abs=1e-9)


def test_fixed_date_exercise_against_independent_risky_asset_density():
    # Synthetic comparison: the same risky GBM is used at both dates.
    s, k, r, sigma, t = 40, 35, 0.05, 0.2, 0.5
    times, amounts, exercise = [0.2, 0.45], [0.5, 3], 0.45
    risky = s - 0.5 * math.exp(-r * 0.2) - 3 * math.exp(-r * 0.45)
    density = lognorm(
        s=sigma * math.sqrt(exercise), scale=risky * math.exp((r - sigma**2 / 2) * exercise)
    )
    value = (
        math.exp(-r * exercise) * quad(lambda x: (x + 3 - k) * density.pdf(x), k - 3, math.inf)[0]
    )
    assert foundations.escrowed_fixed_call_value(
        s, k, r, sigma, t, times, amounts, exercise
    ) == pytest.approx(value, abs=1e-9)


def test_black_identity_and_fixed_model_exercise_bound_are_distinct():
    s, k, r, sigma, t = 40, 35, 0.05, 0.2, 0.5
    times, amounts = [0.2, 0.45], [0.5, 3]
    details = foundations.cash_dividend_call_details(s, k, r, sigma, t, times, amounts)
    source_early_leg = float(bsm.call_price(s - 0.5 * math.exp(-r * 0.2), k, r, sigma, 0.45))
    assert details["black_approx"] == pytest.approx(
        max(details["price"], source_early_leg), abs=1e-12
    )
    fixed_early = foundations.escrowed_fixed_call_value(s, k, r, sigma, t, times, amounts, 0.45)
    american = cash_dividend_tree(s, k, r, sigma, t, times, amounts, american=True, steps=1000)[
        "price"
    ]
    assert american >= max(details["price"], fixed_early) - 0.003
    # Black changes the risky component: it can exceed this model's American.
    assert details["black_approx"] > american + 0.04


def test_source_problem_15_13_no_exercise_conditions_against_tree():
    s, k, r, sigma, t = 70, 65, 0.1, 0.32, 8 / 12
    times, amounts = [0.25, 0.5], [1, 1]
    result = foundations.cash_dividend_call_details(s, k, r, sigma, t, times, amounts)
    independent_thresholds = [k - k * math.exp(-r * 0.25), k - k * math.exp(-r * (t - 0.5))]
    assert result["exercise_thresholds"] == pytest.approx(independent_thresholds, abs=1e-12)
    assert not any(result["exercise_possible"])
    tree = cash_dividend_tree(s, k, r, sigma, t, times, amounts, american=True, steps=1200)
    assert tree["price"] == pytest.approx(result["price"], abs=0.004)


def test_maturity_dividend_cum_exercise_differs_from_european_after_payment():
    before = foundations.escrowed_fixed_call_value(100, 95, 0.05, 0, 1, [1], [10], 1)
    after = float(bsm.call_price_cash_dividends(100, 95, 0.05, 0, 1, [1], [10]))
    risky = 100 - 10 * math.exp(-0.05)
    expected_before = math.exp(-0.05) * max(risky * math.exp(0.05) + 10 - 95, 0)
    assert before == pytest.approx(expected_before, abs=1e-12)
    assert before - after == pytest.approx(10 * math.exp(-0.05), abs=1e-12)


def test_immediate_exercise_with_large_dividend_uses_actual_stock_intrinsic():
    assert foundations.escrowed_fixed_call_value(
        40, 5, 0.05, 0.2, 0.5, [0.45], [10], 0
    ) == pytest.approx(35, abs=1e-12)


def test_fixed_exercise_date_must_be_in_contract_life():
    with pytest.raises(ValueError):
        foundations.escrowed_fixed_call_value(40, 35, 0.05, 0.2, 0.5, [0.45], [3], 0.6)
