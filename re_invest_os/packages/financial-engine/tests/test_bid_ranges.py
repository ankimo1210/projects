"""bid_ranges 純粋関数のテスト (Plan F1)。"""

from __future__ import annotations

import pytest
from re_engine.bid_ranges import (
    DEFAULT_BID_POLICIES,
    BidPolicy,
    _solve_one,
    apply_shocks,
    bid_ranges,
)


def test_bid_ranges_returns_three_levels(base_assumptions):
    res = bid_ranges(base_assumptions)
    assert res.aggressive.name == "aggressive"
    assert res.base.name == "base"
    assert res.conservative.name == "conservative"
    # 全て 1 円以上
    assert res.aggressive.price_yen and res.aggressive.price_yen > 0
    assert res.base.price_yen and res.base.price_yen > 0
    assert res.conservative.price_yen and res.conservative.price_yen > 0


def test_bid_ranges_monotonicity(base_assumptions):
    res = bid_ranges(base_assumptions)
    assert res.conservative.price_yen <= res.base.price_yen <= res.aggressive.price_yen


def test_higher_rate_shock_lowers_price(base_assumptions):
    """金利ショックを上げると bid price が下がる (単調性)。"""
    low = _solve_one(
        base_assumptions, BidPolicy("only", 1.25, 0.08, 0.0, 0.0, 0.000, 0.0)
    )
    high = _solve_one(
        base_assumptions, BidPolicy("only", 1.25, 0.08, 0.0, 0.0, 0.015, 0.0)
    )
    assert low.price_yen is not None and high.price_yen is not None
    assert high.price_yen < low.price_yen


def test_lower_rent_shock_lowers_price(base_assumptions):
    """賃料ショックを下げ (gpi 縮小) ると bid price が下がる。"""
    a = _solve_one(
        base_assumptions, BidPolicy("only", 1.25, 0.08, 0.00, 0.0, 0.0, 0.0)
    )
    b = _solve_one(
        base_assumptions, BidPolicy("only", 1.25, 0.08, -0.10, 0.0, 0.0, 0.0)
    )
    assert a.price_yen is not None and b.price_yen is not None
    assert b.price_yen < a.price_yen


def test_infeasible_returns_none(base_assumptions):
    """極端な制約で成立不能になると price_yen=None。"""
    impossible = BidPolicy(
        name="impossible",
        min_dscr=3.0,  # 達成困難
        min_after_tax_irr=0.30,  # 30%
        rent_shock=-0.50,
        vacancy_shock=0.30,
        rate_shock=0.05,
        opex_shock=0.50,
    )
    entry = _solve_one(base_assumptions, impossible)
    assert entry.price_yen is None


def test_apply_shocks_zero_is_noop(base_assumptions):
    p = BidPolicy("noop", 1.25, 0.08, 0.0, 0.0, 0.0, 0.0)
    out = apply_shocks(base_assumptions, p)
    assert out.income.gpi_monthly_yen == base_assumptions.income.gpi_monthly_yen
    assert out.income.vacancy_rate == base_assumptions.income.vacancy_rate
    assert out.loan.interest_rate == base_assumptions.loan.interest_rate
    assert out.opex.building_mgmt_yen == base_assumptions.opex.building_mgmt_yen


def test_apply_shocks_clamps_vacancy(base_assumptions):
    p = BidPolicy("over", 1.25, 0.08, 0.0, 1.5, 0.0, 0.0)
    out = apply_shocks(base_assumptions, p)
    assert out.income.vacancy_rate == 1.0


def test_default_policies_have_three_levels():
    names = [p.name for p in DEFAULT_BID_POLICIES]
    assert names == ["aggressive", "base", "conservative"]
