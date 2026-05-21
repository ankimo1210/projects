"""売却シナリオのテスト。"""

from __future__ import annotations

from re_engine.cashflow import project_cashflows
from re_engine.exit import compute_exit
from re_engine.loan import amortized_schedule
from re_engine.models import Assumptions


def _full(a: Assumptions):
    sched = amortized_schedule(a.loan.loan_amount_yen, a.loan.interest_rate, a.loan.term_years)
    cfs = project_cashflows(a, sched)
    return compute_exit(a, cfs, sched), sched, cfs


def test_sale_price_uses_exit_cap(base_assumptions: Assumptions) -> None:
    res, _, cfs = _full(base_assumptions)
    expected = round(cfs[-1].noi_yen / base_assumptions.exit_.exit_cap_rate)
    assert res.sale_price_yen == expected


def test_selling_costs(base_assumptions: Assumptions) -> None:
    res, _, _ = _full(base_assumptions)
    assert res.selling_costs_yen == round(
        res.sale_price_yen * base_assumptions.exit_.selling_cost_rate
    )


def test_remaining_loan_present(base_assumptions: Assumptions) -> None:
    """10年保有・30年ローンなので残債は元本の50-70%程度残るはず。"""
    res, _, _ = _full(base_assumptions)
    loan = base_assumptions.loan.loan_amount_yen
    assert loan * 0.50 < res.remaining_loan_yen < loan * 0.80


def test_book_value_floor_is_land(base_assumptions: Assumptions) -> None:
    """簿価は土地分以下にはならない。"""
    res, _, _ = _full(base_assumptions)
    assert res.book_value_yen >= base_assumptions.property.land_value_yen


def test_long_term_gain_rate(base_assumptions: Assumptions) -> None:
    """10年保有 → 長期譲渡。譲渡所得が正なら税率20%が適用される。"""
    res, _, _ = _full(base_assumptions)
    if res.capital_gain_yen > 0:
        expected = round(res.capital_gain_yen * 0.20)
        assert res.capital_gain_tax_yen == expected


def test_net_proceeds_consistency(base_assumptions: Assumptions) -> None:
    """net_proceeds = sale - selling_costs - loan - tax。"""
    res, _, _ = _full(base_assumptions)
    expected = (
        res.sale_price_yen
        - res.selling_costs_yen
        - res.remaining_loan_yen
        - res.capital_gain_tax_yen
    )
    assert res.net_proceeds_yen == expected
