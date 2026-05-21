"""フル分析オーケストレーターのテスト。"""

from __future__ import annotations

from re_engine.analyze import run_full_analysis
from re_engine.models import Assumptions


def test_run_full_analysis_returns_consistent_result(
    base_assumptions: Assumptions,
) -> None:
    result = run_full_analysis(base_assumptions)
    assert result.engine_version == "0.1.0"
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
