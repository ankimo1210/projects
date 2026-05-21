"""感応度分析テスト。"""

from __future__ import annotations

from re_engine.models import Assumptions
from re_engine.sensitivity import sensitivity_grid


def test_grid_runs_all_scenarios(base_assumptions: Assumptions) -> None:
    result = sensitivity_grid(base_assumptions)
    # base + 11 scenarios
    assert len(result.scenarios) == 11
    assert result.base.scenario == "base"


def test_rent_drop_reduces_atcf(base_assumptions: Assumptions) -> None:
    result = sensitivity_grid(base_assumptions)
    base_atcf = result.base.atcf_year1_yen
    rent_10 = next(s for s in result.scenarios if s.scenario == "rent_down_10")
    assert rent_10.atcf_year1_yen < base_atcf


def test_rate_up_reduces_atcf(base_assumptions: Assumptions) -> None:
    result = sensitivity_grid(base_assumptions)
    base_atcf = result.base.atcf_year1_yen
    rate_up = next(s for s in result.scenarios if s.scenario == "rate_up_100bp")
    assert rate_up.atcf_year1_yen < base_atcf


def test_exit_cap_up_reduces_net_proceeds(base_assumptions: Assumptions) -> None:
    """出口Cap +0.5pt → 売却価格↓ → net_proceeds↓。"""
    result = sensitivity_grid(base_assumptions)
    base_net = result.base.net_proceeds_yen
    exit_up = next(s for s in result.scenarios if s.scenario == "exit_cap_up_50bp")
    assert exit_up.net_proceeds_yen < base_net


def test_combined_stress_is_worst_among_pieces(base_assumptions: Assumptions) -> None:
    """複合ストレスはどの単独ショックよりATCFが悪い、または同等。"""
    result = sensitivity_grid(base_assumptions)
    combined = next(s for s in result.scenarios if s.scenario == "combined_stress")
    rent5 = next(s for s in result.scenarios if s.scenario == "rent_down_5")
    rate50 = next(s for s in result.scenarios if s.scenario == "rate_up_50bp")
    assert combined.atcf_year1_yen <= rent5.atcf_year1_yen
    assert combined.atcf_year1_yen <= rate50.atcf_year1_yen


def test_judgment_assigned(base_assumptions: Assumptions) -> None:
    result = sensitivity_grid(base_assumptions)
    valid = {"good", "warn", "bad"}
    assert result.base.judgment in valid
    for s in result.scenarios:
        assert s.judgment in valid


def test_dscr_decreases_under_stress(base_assumptions: Assumptions) -> None:
    result = sensitivity_grid(base_assumptions)
    base_dscr = result.base.dscr_min
    rate_up = next(s for s in result.scenarios if s.scenario == "rate_up_100bp")
    assert rate_up.dscr_min < base_dscr
