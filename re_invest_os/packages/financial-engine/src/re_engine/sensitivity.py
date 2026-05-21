"""感応度分析: 主要前提に対するKPIの感度。

仕様: docs/architecture/calculation_engine_spec.md §5.8

シナリオセット (固定):
- 賃料 -5%, -10%
- 空室率 +5pt, +10pt
- 金利 +0.5pt, +1.0pt
- OPEX x1.5, x2.0
- 出口Cap +0.25pt, +0.5pt
- 売却価格 -5%, -10%  (出口Capの逆算で実現)
- 複合ストレス (rent-5% + vacancy+5pt + rate+0.5pt)
"""

from __future__ import annotations

import copy
from typing import Literal

from pydantic import BaseModel, ConfigDict

from re_engine.analyze import run_full_analysis
from re_engine.models import Assumptions

ScenarioName = Literal[
    "base",
    "rent_down_5",
    "rent_down_10",
    "vacancy_up_5pt",
    "vacancy_up_10pt",
    "rate_up_50bp",
    "rate_up_100bp",
    "opex_15x",
    "opex_20x",
    "exit_cap_up_25bp",
    "exit_cap_up_50bp",
    "combined_stress",
]


class ScenarioResult(BaseModel):
    scenario: ScenarioName
    atcf_year1_yen: int
    irr: float | None
    dscr_min: float
    net_proceeds_yen: int
    judgment: Literal["good", "warn", "bad"]
    model_config = ConfigDict(extra="forbid")


class SensitivityResult(BaseModel):
    base: ScenarioResult
    scenarios: list[ScenarioResult]
    model_config = ConfigDict(extra="forbid")


def _apply_scenario(a: Assumptions, name: ScenarioName) -> Assumptions:
    """シナリオを適用した新しい Assumptions を返す。"""
    s = copy.deepcopy(a)
    if name == "base":
        return s
    elif name == "rent_down_5":
        s.income.gpi_monthly_yen = round(s.income.gpi_monthly_yen * 0.95)
    elif name == "rent_down_10":
        s.income.gpi_monthly_yen = round(s.income.gpi_monthly_yen * 0.90)
    elif name == "vacancy_up_5pt":
        s.income.vacancy_rate = min(1.0, s.income.vacancy_rate + 0.05)
    elif name == "vacancy_up_10pt":
        s.income.vacancy_rate = min(1.0, s.income.vacancy_rate + 0.10)
    elif name == "rate_up_50bp":
        s.loan.interest_rate = min(1.0, s.loan.interest_rate + 0.005)
    elif name == "rate_up_100bp":
        s.loan.interest_rate = min(1.0, s.loan.interest_rate + 0.010)
    elif name == "opex_15x":
        s.opex.fixed_property_tax_yen = int(s.opex.fixed_property_tax_yen * 1.5)
        s.opex.insurance_yen = int(s.opex.insurance_yen * 1.5)
        s.opex.building_mgmt_yen = int(s.opex.building_mgmt_yen * 1.5)
        s.opex.other_opex_yen = int(s.opex.other_opex_yen * 1.5)
        s.opex.repair_reserve_monthly_yen = int(s.opex.repair_reserve_monthly_yen * 1.5)
    elif name == "opex_20x":
        s.opex.fixed_property_tax_yen = int(s.opex.fixed_property_tax_yen * 2.0)
        s.opex.insurance_yen = int(s.opex.insurance_yen * 2.0)
        s.opex.building_mgmt_yen = int(s.opex.building_mgmt_yen * 2.0)
        s.opex.other_opex_yen = int(s.opex.other_opex_yen * 2.0)
        s.opex.repair_reserve_monthly_yen = int(s.opex.repair_reserve_monthly_yen * 2.0)
    elif name == "exit_cap_up_25bp":
        s.exit_.exit_cap_rate = min(1.0, s.exit_.exit_cap_rate + 0.0025)
    elif name == "exit_cap_up_50bp":
        s.exit_.exit_cap_rate = min(1.0, s.exit_.exit_cap_rate + 0.005)
    elif name == "combined_stress":
        s.income.gpi_monthly_yen = round(s.income.gpi_monthly_yen * 0.95)
        s.income.vacancy_rate = min(1.0, s.income.vacancy_rate + 0.05)
        s.loan.interest_rate = min(1.0, s.loan.interest_rate + 0.005)
    return s


def _judge(atcf_y1: int, irr: float | None, dscr_min: float) -> Literal["good", "warn", "bad"]:
    """シナリオ結果の三段階判定。"""
    irr_ok = irr is not None and irr >= 0.06
    if atcf_y1 < 0 or dscr_min < 1.0:
        return "bad"
    if not irr_ok or dscr_min < 1.25:
        return "warn"
    return "good"


def _run_scenario(a: Assumptions, name: ScenarioName) -> ScenarioResult:
    scen_a = _apply_scenario(a, name)
    r = run_full_analysis(scen_a)
    return ScenarioResult(
        scenario=name,
        atcf_year1_yen=r.kpi.atcf_first_year_yen,
        irr=r.kpi.equity_irr,
        dscr_min=r.kpi.dscr_min,
        net_proceeds_yen=r.exit_.net_proceeds_yen,
        judgment=_judge(r.kpi.atcf_first_year_yen, r.kpi.equity_irr, r.kpi.dscr_min),
    )


def sensitivity_grid(a: Assumptions) -> SensitivityResult:
    """すべての標準シナリオを実行。"""
    scenarios: list[ScenarioName] = [
        "rent_down_5",
        "rent_down_10",
        "vacancy_up_5pt",
        "vacancy_up_10pt",
        "rate_up_50bp",
        "rate_up_100bp",
        "opex_15x",
        "opex_20x",
        "exit_cap_up_25bp",
        "exit_cap_up_50bp",
        "combined_stress",
    ]
    base = _run_scenario(a, "base")
    others = [_run_scenario(a, s) for s in scenarios]
    return SensitivityResult(base=base, scenarios=others)
