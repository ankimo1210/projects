"""Hull Example5.6 FX cash: one source cent differs from exact arithmetic."""

import math

import numpy as np
import pytest
from hullkit import _forward_pricing as f


def test_source_all_ten_consistent_fx_values_and_one_cent_note():
    low = f.currency_carry_cash(0.75, 0.01, 0.03, 2, 0.70)
    high = f.currency_carry_cash(0.75, 0.01, 0.03, 2, 0.76)
    assert low["fair_forward"] == pytest.approx(0.7206, abs=0.00005)
    assert [
        low["foreign_repayment"],
        low["cheap_forward_cost"],
        low["domestic_investment"],
        low["cheap_profit"],
    ] == pytest.approx([1061.84, 743.29, 765.15, 21.87], abs=0.005)
    assert [
        high["foreign_bought"],
        high["rich_forward_receipt"],
        high["domestic_repayment"],
        high["rich_profit"],
    ] == pytest.approx([1333.33, 1075.99, 1020.20, 55.79], abs=0.005)
    assert 100 * f.forward_rate_differential(1, 1.002, 0.25) == pytest.approx(0.8, abs=0.005)
    assert high["foreign_investment"] == pytest.approx(1415.782062, abs=1e-6)
    assert abs(high["foreign_investment"] - 1415.79) > 0.005


def test_independent_currency_growth_and_inverse_cip():
    a = f.currency_carry_cash(0.75, 0.01, 0.03, 2, 0.70)
    usd_asset = 750 * math.exp(0.01 * 2)
    aud_debt = 1000 * math.exp(0.03 * 2)
    assert a["cheap_profit"] == pytest.approx(usd_asset - 0.7 * aud_debt)
    fair = f.currency_carry_cash(0.75, 0.01, 0.03, 2, a["fair_forward"])
    assert [fair["cheap_profit"], fair["rich_profit"]] == pytest.approx([0, 0], abs=1e-10)
    inverse = f.currency_carry_cash(1 / 0.75, 0.03, 0.01, 2, 1 / a["fair_forward"])
    assert inverse["fair_forward"] == pytest.approx(1 / a["fair_forward"])
    growth = np.diag([math.exp(0.01 * 2), math.exp(0.03 * 2)])
    assert growth @ np.array([750, 1000]) == pytest.approx(
        [a["domestic_investment"], a["foreign_repayment"]]
    )
