"""最大買付価格 solver のテスト。"""

from __future__ import annotations

from re_engine.max_offer import InvestorTargets, max_offer_price
from re_engine.models import Assumptions


def test_loose_targets_yields_meaningful_price(base_assumptions: Assumptions) -> None:
    """十分に緩い基準なら、現在価格の半分以上は許容される (この物件は元々過大評価)。"""
    targets = InvestorTargets(min_dscr=0.5, min_irr=-0.50, min_first_year_atcf_yen=-5_000_000)
    result = max_offer_price(base_assumptions, targets)
    # 緩い基準なら少なくとも現在価格の50%以上は出る
    assert result.max_price_yen >= int(base_assumptions.property.purchase_price_yen * 0.50)
    assert result.converged


def test_strict_dscr_yields_lower_price(base_assumptions: Assumptions) -> None:
    """DSCR 1.5 基準は現価格では満たせない → max_price < current。"""
    targets = InvestorTargets(min_dscr=1.5, min_irr=-1.0, min_first_year_atcf_yen=-10_000_000)
    result = max_offer_price(base_assumptions, targets)
    assert result.max_price_yen < base_assumptions.property.purchase_price_yen
    # binding に dscr_min が含まれる
    assert any("dscr" in c for c in result.binding_constraints)


def test_max_lower_than_current_means_discount_needed(base_assumptions: Assumptions) -> None:
    targets = InvestorTargets(min_dscr=1.5, min_irr=-1.0, min_first_year_atcf_yen=-10_000_000)
    result = max_offer_price(base_assumptions, targets)
    assert result.required_discount_yen > 0
    assert result.safe_price_yen < result.max_price_yen


def test_impossible_targets_returns_zero(base_assumptions: Assumptions) -> None:
    """物理的に満たせない基準 (IRR 100% 等) → max_price = 0 / not converged。"""
    targets = InvestorTargets(min_dscr=10.0, min_irr=1.0, min_first_year_atcf_yen=10_000_000)
    result = max_offer_price(base_assumptions, targets)
    assert result.max_price_yen == 0
    assert not result.converged
    assert len(result.binding_constraints) > 0


def test_safe_price_is_5pct_below_max(base_assumptions: Assumptions) -> None:
    targets = InvestorTargets(min_dscr=1.0, min_irr=-1.0, min_first_year_atcf_yen=-10_000_000)
    result = max_offer_price(base_assumptions, targets)
    if result.max_price_yen > 0:
        assert result.safe_price_yen == int(result.max_price_yen * 0.95)


def test_stress_rate_lowers_max_price(base_assumptions: Assumptions) -> None:
    """金利+1%ストレス付き → 通常より厳しい価格になる。"""
    targets_no_stress = InvestorTargets(
        min_dscr=1.2, min_irr=-1.0, min_first_year_atcf_yen=-10_000_000
    )
    targets_stress = InvestorTargets(
        min_dscr=1.2,
        min_irr=-1.0,
        min_first_year_atcf_yen=-10_000_000,
        stress_interest_rate=0.030,
    )
    r1 = max_offer_price(base_assumptions, targets_no_stress)
    r2 = max_offer_price(base_assumptions, targets_stress)
    assert r2.max_price_yen <= r1.max_price_yen


def test_iterations_bounded(base_assumptions: Assumptions) -> None:
    """二分探索の反復回数は max_iterations 以下。"""
    result = max_offer_price(base_assumptions, max_iterations=20)
    assert result.iterations <= 20
