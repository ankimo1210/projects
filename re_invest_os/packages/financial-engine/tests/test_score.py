"""100点スコアのテスト。"""

from __future__ import annotations

from re_engine.analyze import run_full_analysis
from re_engine.models import Assumptions
from re_engine.score import DataQuality, MarketContext, total_score


def test_total_score_in_range(base_assumptions: Assumptions) -> None:
    result = run_full_analysis(base_assumptions)
    s = total_score(result)
    assert 0 <= s.total <= 100
    assert s.evaluation in ("健全", "中立", "要警戒")


def test_components_sum_equals_total(base_assumptions: Assumptions) -> None:
    result = run_full_analysis(base_assumptions)
    s = total_score(result)
    total = sum(c.score for c in s.components)
    assert abs(total - s.total) < 0.01


def test_market_cap_changes_price_score(base_assumptions: Assumptions) -> None:
    """市場Capに対する物件Capの位置で価格スコアが変わる。"""
    result = run_full_analysis(base_assumptions)
    cap = result.kpi.cap_rate
    # 物件Capより明確に高い市場 (物件は割高) → 減点
    ctx_high = MarketContext(market_cap_rate=cap + 0.03)
    # 物件Capより明確に低い市場 (物件は割安) → 満点
    ctx_low = MarketContext(market_cap_rate=cap - 0.01)
    s_high = total_score(result, market_context=ctx_high)
    s_low = total_score(result, market_context=ctx_low)
    price_h = next(c for c in s_high.components if c.name == "price")
    price_l = next(c for c in s_low.components if c.name == "price")
    assert price_h.score < price_l.score
    assert price_l.score == 20.0


def test_data_quality_low(base_assumptions: Assumptions) -> None:
    result = run_full_analysis(base_assumptions)
    dq = DataQuality(document_completeness=0.3, extraction_confidence=0.4)
    s = total_score(result, data_quality=dq)
    dq_comp = next(c for c in s.components if c.name == "data_quality")
    # max 5点だが 5 * (0.3*0.5 + 0.4*0.5) = 1.75
    assert 1.5 <= dq_comp.score <= 2.0


def test_evaluation_labels(base_assumptions: Assumptions) -> None:
    """スコア帯ごとに評価ラベルが付く。"""
    result = run_full_analysis(base_assumptions)
    s = total_score(result)
    if s.total >= 70:
        assert s.evaluation == "健全"
    elif s.total >= 50:
        assert s.evaluation == "中立"
    else:
        assert s.evaluation == "要警戒"
