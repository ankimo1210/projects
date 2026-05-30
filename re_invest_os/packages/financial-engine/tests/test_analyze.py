"""フル分析オーケストレーターのテスト。"""

from __future__ import annotations

from re_engine import ENGINE_VERSION
from re_engine.analyze import first_dead_cross_year, run_full_analysis
from re_engine.models import Assumptions, YearlyCashflow


def test_run_full_analysis_returns_consistent_result(
    base_assumptions: Assumptions,
) -> None:
    result = run_full_analysis(base_assumptions)
    assert result.engine_version == "0.2.0"
    assert len(result.yearly_cashflows) == 10
    assert len(result.loan_schedule) == 360  # 30年×12
    assert result.exit_.sale_price_yen > 0
    assert result.kpi.cap_rate > 0
    assert result.kpi.dscr_min > 0


def test_run_full_analysis_idempotent(base_assumptions: Assumptions) -> None:
    """同じ入力で同じ出力 (純粋関数)。"""
    r1 = run_full_analysis(base_assumptions)
    r2 = run_full_analysis(base_assumptions)
    assert r1 == r2


def test_kpi_ranges(base_assumptions: Assumptions) -> None:
    result = run_full_analysis(base_assumptions)
    k = result.kpi
    # LTV 70%
    assert abs(k.ltv - 0.70) < 0.005
    # Cap Rate は 2-7% 程度のはず
    assert 0.02 <= k.cap_rate <= 0.08
    # DSCR は 1.0前後 (この物件はギリギリ)
    assert 0.5 <= k.dscr_min <= 2.0


def _row(year: int, depreciation: int, principal: int) -> YearlyCashflow:
    return YearlyCashflow(
        year=year, gpi_yen=0, vacancy_loss_yen=0, bad_debt_yen=0, egi_yen=0,
        opex_yen=0, noi_yen=0, debt_service_yen=0, btcf_yen=0,
        depreciation_yen=depreciation, interest_expense_yen=0,
        principal_payment_yen=principal, taxable_income_yen=0, tax_yen=0,
        atcf_yen=0, loan_balance_end_yen=0,
    )


def test_first_dead_cross_year_detects_crossover() -> None:
    # dep > principal in y1-2, dep < principal from y3
    rows = [_row(1, 100, 50), _row(2, 100, 90), _row(3, 100, 110), _row(4, 100, 130)]
    assert first_dead_cross_year(rows) == 3


def test_first_dead_cross_year_none_when_never_crosses() -> None:
    rows = [_row(1, 100, 50), _row(2, 100, 60)]
    assert first_dead_cross_year(rows) is None


def test_analysis_populates_dead_cross_year_consistently(
    base_assumptions: Assumptions,
) -> None:
    result = run_full_analysis(base_assumptions)
    expected = first_dead_cross_year(result.yearly_cashflows)
    assert result.kpi.dead_cross_year == expected
    assert result.kpi.dead_cross_year is None or isinstance(result.kpi.dead_cross_year, int)


def test_engine_version_bumped() -> None:
    assert ENGINE_VERSION == "0.2.0"
