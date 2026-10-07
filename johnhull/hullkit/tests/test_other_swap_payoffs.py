import importlib
import math

import numpy as np
import pytest


def model():
    return importlib.import_module("hullkit._other_swap_payoffs")


def test_source_commodity_one_hundred_thousand_barrels_five_million_ten_years():
    m = model()
    strike = m.commodity_fixed_unit_price(5e6, 100000)
    assert strike == pytest.approx(50)
    cash = m.commodity_swap_cashflows(np.full(10, 100000), np.arange(45, 55), strike)
    assert cash == pytest.approx(100000 * (np.arange(45, 55) - 50), abs=1e-9)
    assert m.commodity_swap_cashflows([100000], [50], strike)[0] == pytest.approx(0)


def test_pg_given_ten_percent_spread_six_percent_cp_source_payment_and_first_coupon():
    m = model()
    assert m.pg_payment_rate(0.06, 0.1) == pytest.approx(0.1525, abs=1e-14)
    # Declared synthetic indicators giving 10% spread, not historical inputs.
    row = m.pg_swap_coupons(
        2e8, np.full(10, 0.5), np.full(10, 0.06), np.full(10, 0.0578), np.full(10, 88.5)
    )
    assert row["spread"][0] == pytest.approx(0)
    assert row["spread"][1:] == pytest.approx(np.full(9, 0.1), abs=1e-14)
    assert row["pg_paid_rate"][1:] == pytest.approx(np.full(9, 0.1525), abs=1e-14)
    assert row["pg_net_cash"][1:] == pytest.approx(
        np.full(9, 2e8 * 0.5 * (0.053 - 0.1525)), abs=1e-7
    )


def test_pg_positive_part_synthetic_gaussian_payoff_mc_independent_bachelier_expectation():
    m = model()
    n = 32768
    rng = np.random.default_rng(3462026)
    z = rng.standard_normal((2, n))
    rho = 0.4
    cmt = 0.0578 + 0.002 * z[0]
    price = 98.5 + 2 * (rho * z[0] + math.sqrt(1 - rho * rho) * z[1])
    values = m.pg_spread(cmt, price)
    coefficient = 98.5 * 0.002 / 0.0578
    sd = math.sqrt(coefficient**2 + 4 - 2 * coefficient * 2 * rho) / 100
    expectation = sd / math.sqrt(2 * math.pi)
    se = values.std(ddof=1) / math.sqrt(n)
    assert abs(values.mean() - expectation) < 5 * se
    assert m.pg_spread(0.0578, 110) == pytest.approx(0)
    assert m.pg_spread(0.0578, 98.5) == pytest.approx(0, abs=1e-14)


def test_index_amortization_uses_observed_history_and_keeps_principal_conserved():
    m = model()
    rates = np.array([[0.05, 0.04, 0.03], [0.05, 0.02, 0.04]])

    def rule(i, balance, history):
        return np.where(history[:, -1] < 0.03, 0.5, 0)

    row = m.index_amortizing_notionals(100, rates, rule)
    assert row[0] == pytest.approx([100, 100, 100, 100])
    assert row[1] == pytest.approx([100, 100, 50, 50])
    changed = rates.copy()
    changed[:, -1] = 0.01
    another = m.index_amortizing_notionals(100, changed, rule)
    assert another[:, :3] == pytest.approx(row[:, :3])
    assert np.all(np.diff(another, axis=1) <= 0)
    assert np.sum(-np.diff(another, axis=1), axis=1) + another[:, -1] == pytest.approx([100, 100])


def test_known_asset_total_return_cash_and_math_domain():
    m = model()
    assert m.asset_total_return_cash(100, 80, 85, 2) == pytest.approx(100 * (7 / 80), abs=1e-12)
    with pytest.raises(ValueError):
        m.commodity_fixed_unit_price(1, 0)
    with pytest.raises(ValueError):
        m.index_amortizing_notionals(100, np.array([[0.03]]), lambda i, b, h: 1.1)
