"""甘さスコア (AssumptionScore) のテスト。"""

from __future__ import annotations

import copy

from re_engine.analyze import run_full_analysis
from re_engine.models import Assumptions
from re_engine.normalized import NormalizedProperty

from api.services.risk_engine import (
    AssumptionScore,
    aggregate_overall_risk,
    assess_assumption_score,
)


def _score(assumptions: Assumptions) -> AssumptionScore:
    result = run_full_analysis(assumptions)
    return assess_assumption_score(assumptions, result, NormalizedProperty.all_user_input())


def test_aggregate_overall_risk_priority() -> None:
    assert aggregate_overall_risk(["low", "medium", "high"]) == "high"
    assert aggregate_overall_risk(["low", "medium", "low"]) == "medium"
    assert aggregate_overall_risk(["low", "low"]) == "low"
    assert aggregate_overall_risk(["unknown", "unknown"]) == "unknown"


def test_assumption_score_shape(base_assumptions: Assumptions) -> None:
    s = _score(base_assumptions)
    assert isinstance(s, AssumptionScore)
    assert s.overall_risk in ("low", "medium", "high", "unknown")
    assert s.items, "items must not be empty"
    assert isinstance(s.summary, str) and s.summary


def test_dscr_coupling_bumps_to_medium(base_assumptions: Assumptions) -> None:
    # DSCR最小を [1.00, 1.15] に入れるため借入と金利を上げる。
    a = copy.deepcopy(base_assumptions)
    a.loan.loan_amount_yen = 24_000_000
    a.loan.interest_rate = 0.020
    dscr_min = run_full_analysis(a).kpi.dscr_min
    assert 1.00 <= dscr_min <= 1.15, f"setup precondition; got {dscr_min}"
    s = _score(a)
    by_cat = {i.category: i.risk_level for i in s.items}
    order = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
    for cat in ("rent", "interest_rate", "opex"):
        assert order[by_cat[cat]] >= order["medium"], cat


def test_exit_share_marks_exit_price_high(base_assumptions: Assumptions) -> None:
    s = _score(base_assumptions)
    result = run_full_analysis(base_assumptions)
    net = result.exit_.net_proceeds_yen
    share = net / (sum(cf.atcf_yen for cf in result.yearly_cashflows) + net)
    exit_item = next(i for i in s.items if i.category == "exit_price")
    if share > 0.60:
        assert exit_item.risk_level == "high"


def test_new_categories_present(base_assumptions: Assumptions) -> None:
    s = _score(base_assumptions)
    cats = {i.category for i in s.items}
    assert "sale_year" in cats
    assert "acquisition_cost" in cats
    assert len(s.items) == 9
