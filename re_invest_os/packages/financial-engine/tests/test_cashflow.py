"""キャッシュフロー・プロジェクションのテスト。"""

from __future__ import annotations

import itertools

from re_engine.cashflow import project_cashflows
from re_engine.loan import amortized_schedule
from re_engine.models import Assumptions


def test_project_length_matches_hold_period(base_assumptions: Assumptions) -> None:
    sched = amortized_schedule(
        base_assumptions.loan.loan_amount_yen,
        base_assumptions.loan.interest_rate,
        base_assumptions.loan.term_years,
    )
    cfs = project_cashflows(base_assumptions, sched)
    assert len(cfs) == base_assumptions.exit_.hold_period_years == 10


def test_year1_gpi(base_assumptions: Assumptions) -> None:
    """初年度 GPI = 145,000 × 12 = 1,740,000。"""
    sched = amortized_schedule(
        base_assumptions.loan.loan_amount_yen,
        base_assumptions.loan.interest_rate,
        base_assumptions.loan.term_years,
    )
    cfs = project_cashflows(base_assumptions, sched)
    assert cfs[0].gpi_yen == 1_740_000


def test_year1_egi_after_vacancy(base_assumptions: Assumptions) -> None:
    """空室率5% → Vacancy = 87,000、EGI = 1,653,000。"""
    sched = amortized_schedule(
        base_assumptions.loan.loan_amount_yen,
        base_assumptions.loan.interest_rate,
        base_assumptions.loan.term_years,
    )
    cfs = project_cashflows(base_assumptions, sched)
    assert cfs[0].vacancy_loss_yen == 87_000
    assert cfs[0].egi_yen == 1_653_000


def test_noi_positive(base_assumptions: Assumptions) -> None:
    """この物件はNOIプラスのはず。"""
    sched = amortized_schedule(
        base_assumptions.loan.loan_amount_yen,
        base_assumptions.loan.interest_rate,
        base_assumptions.loan.term_years,
    )
    cfs = project_cashflows(base_assumptions, sched)
    assert cfs[0].noi_yen > 0


def test_btcf_consistency(base_assumptions: Assumptions) -> None:
    """BTCF = NOI - DS。"""
    sched = amortized_schedule(
        base_assumptions.loan.loan_amount_yen,
        base_assumptions.loan.interest_rate,
        base_assumptions.loan.term_years,
    )
    cfs = project_cashflows(base_assumptions, sched)
    for cf in cfs:
        assert cf.btcf_yen == cf.noi_yen - cf.debt_service_yen


def test_atcf_consistency(base_assumptions: Assumptions) -> None:
    """ATCF = BTCF - Tax。"""
    sched = amortized_schedule(
        base_assumptions.loan.loan_amount_yen,
        base_assumptions.loan.interest_rate,
        base_assumptions.loan.term_years,
    )
    cfs = project_cashflows(base_assumptions, sched)
    for cf in cfs:
        assert cf.atcf_yen == cf.btcf_yen - cf.tax_yen


def test_loan_balance_decreasing(base_assumptions: Assumptions) -> None:
    """残債は単調減少。"""
    sched = amortized_schedule(
        base_assumptions.loan.loan_amount_yen,
        base_assumptions.loan.interest_rate,
        base_assumptions.loan.term_years,
    )
    cfs = project_cashflows(base_assumptions, sched)
    balances = [cf.loan_balance_end_yen for cf in cfs]
    for a, b in itertools.pairwise(balances):
        assert b < a


def test_rent_decline_reduces_gpi(base_assumptions: Assumptions) -> None:
    """rent_growth = -0.005 → 10年目は1年目より低い。"""
    sched = amortized_schedule(
        base_assumptions.loan.loan_amount_yen,
        base_assumptions.loan.interest_rate,
        base_assumptions.loan.term_years,
    )
    cfs = project_cashflows(base_assumptions, sched)
    assert cfs[-1].gpi_yen < cfs[0].gpi_yen


def test_depreciation_present(base_assumptions: Assumptions) -> None:
    """RC築15年・建物3,180万円 → 年100万円弱の減価償却。"""
    sched = amortized_schedule(
        base_assumptions.loan.loan_amount_yen,
        base_assumptions.loan.interest_rate,
        base_assumptions.loan.term_years,
    )
    cfs = project_cashflows(base_assumptions, sched)
    # 残35年なら 31,800,000 / 35 ≒ 908,571
    assert 700_000 <= cfs[0].depreciation_yen <= 1_100_000


def test_interest_principal_sum_equals_debt_service(
    base_assumptions: Assumptions,
) -> None:
    """利息 + 元金 = 返済額 (端数は±12円)。"""
    sched = amortized_schedule(
        base_assumptions.loan.loan_amount_yen,
        base_assumptions.loan.interest_rate,
        base_assumptions.loan.term_years,
    )
    cfs = project_cashflows(base_assumptions, sched)
    for cf in cfs:
        diff = abs(cf.debt_service_yen - (cf.interest_expense_yen + cf.principal_payment_yen))
        assert diff <= 12
