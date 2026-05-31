"""ストレス（崩れ方）テスト — MVP 固定7シナリオ。"""

from __future__ import annotations

from re_engine.models import Assumptions
from re_engine.sensitivity import STRESS_SCENARIOS, sensitivity_grid


def test_fixed_seven_scenarios(base_assumptions: Assumptions) -> None:
    result = sensitivity_grid(base_assumptions)
    names = [s.scenario for s in result.scenarios]
    assert names == [
        "rate_up_100bp",
        "rent_down_5",
        "vacancy_up_5pt",
        "opex_up_10pct",
        "repair_up_20pct",
        "exit_down_10pct",
        "combined_stress",
    ]
    assert len(STRESS_SCENARIOS) == 7
    assert result.base.scenario == "base"


def test_rent_drop_reduces_atcf(base_assumptions: Assumptions) -> None:
    result = sensitivity_grid(base_assumptions)
    base_atcf = result.base.atcf_year1_yen
    rent5 = next(s for s in result.scenarios if s.scenario == "rent_down_5")
    assert rent5.atcf_year1_yen < base_atcf


def test_rate_up_reduces_atcf_and_dscr(base_assumptions: Assumptions) -> None:
    result = sensitivity_grid(base_assumptions)
    rate_up = next(s for s in result.scenarios if s.scenario == "rate_up_100bp")
    assert rate_up.atcf_year1_yen < result.base.atcf_year1_yen
    assert rate_up.dscr_min < result.base.dscr_min
    # Δ vs base が記録される
    assert rate_up.dscr_min_delta == round(rate_up.dscr_min - result.base.dscr_min, 4)
    assert rate_up.dscr_min_delta < 0


def test_exit_down_reduces_net_proceeds(base_assumptions: Assumptions) -> None:
    """売却価格 -10% (exit_cap を cap/0.9 に逆算) → net_proceeds↓。"""
    result = sensitivity_grid(base_assumptions)
    exit_down = next(s for s in result.scenarios if s.scenario == "exit_down_10pct")
    assert exit_down.net_proceeds_yen < result.base.net_proceeds_yen


def test_repair_up_present(base_assumptions: Assumptions) -> None:
    result = sensitivity_grid(base_assumptions)
    assert any(s.scenario == "repair_up_20pct" for s in result.scenarios)


def test_combined_is_worst_or_equal(base_assumptions: Assumptions) -> None:
    result = sensitivity_grid(base_assumptions)
    combined = next(s for s in result.scenarios if s.scenario == "combined_stress")
    rent5 = next(s for s in result.scenarios if s.scenario == "rent_down_5")
    rate_up = next(s for s in result.scenarios if s.scenario == "rate_up_100bp")
    assert combined.atcf_year1_yen <= rent5.atcf_year1_yen
    assert combined.atcf_year1_yen <= rate_up.atcf_year1_yen
    assert combined.dscr_min <= result.base.dscr_min


def test_judgment_assigned(base_assumptions: Assumptions) -> None:
    result = sensitivity_grid(base_assumptions)
    valid = {"good", "warn", "bad"}
    assert result.base.judgment in valid
    for s in result.scenarios:
        assert s.judgment in valid
