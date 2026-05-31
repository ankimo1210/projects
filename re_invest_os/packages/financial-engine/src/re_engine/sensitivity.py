"""ストレス（崩れ方）: 標準条件に対する KPI の崩れ方 — MVP 固定7シナリオ。

仕様: docs/architecture/calculation_engine_spec.md §5.8 / MVP §8

固定7シナリオ:
- rate_up_100bp     金利 +1.0pt
- rent_down_5       賃料 -5%
- vacancy_up_5pt    空室率 +5pt
- opex_up_10pct     円建てOPEX ×1.10
- repair_up_20pct   修繕積立 ×1.20 のみ
- exit_down_10pct   売却価格 -10% (exit_cap を cap/0.9 で逆算)
- combined_stress   上記6つ同時

各シナリオは標準条件 (base) に対する DSCR・税後IRR の Δ を持つ。
判定 (good/warn/bad) は投資助言ではなく、入力条件に対する感応度の三段表示。
"""

from __future__ import annotations

import copy
from typing import Literal

from pydantic import BaseModel, ConfigDict

from re_engine.analyze import run_full_analysis
from re_engine.models import Assumptions

ScenarioName = Literal[
    "base",
    "rate_up_100bp",
    "rent_down_5",
    "vacancy_up_5pt",
    "opex_up_10pct",
    "repair_up_20pct",
    "exit_down_10pct",
    "combined_stress",
]

STRESS_SCENARIOS: list[ScenarioName] = [
    "rate_up_100bp",
    "rent_down_5",
    "vacancy_up_5pt",
    "opex_up_10pct",
    "repair_up_20pct",
    "exit_down_10pct",
    "combined_stress",
]

# 円建て OPEX フィールド (management_fee_rate は % なので非対象)
_OPEX_FIELDS = (
    "fixed_property_tax_yen",
    "insurance_yen",
    "building_mgmt_yen",
    "other_opex_yen",
    "repair_reserve_monthly_yen",
)


class ScenarioResult(BaseModel):
    scenario: ScenarioName
    atcf_year1_yen: int
    irr: float | None  # 税後 equity IRR
    dscr_min: float
    net_proceeds_yen: int
    dscr_min_delta: float = 0.0  # vs base
    irr_delta: float | None = None  # vs base
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
    if name == "rate_up_100bp":
        s.loan.interest_rate = min(1.0, s.loan.interest_rate + 0.010)
    elif name == "rent_down_5":
        s.income.gpi_monthly_yen = round(s.income.gpi_monthly_yen * 0.95)
    elif name == "vacancy_up_5pt":
        s.income.vacancy_rate = min(1.0, s.income.vacancy_rate + 0.05)
    elif name == "opex_up_10pct":
        for f in _OPEX_FIELDS:
            setattr(s.opex, f, round(getattr(s.opex, f) * 1.10))
    elif name == "repair_up_20pct":
        s.opex.repair_reserve_monthly_yen = round(s.opex.repair_reserve_monthly_yen * 1.20)
    elif name == "exit_down_10pct":
        # 売却価格 -10% ≒ 出口Cap を cap/0.9 に引き上げ (price = NOI / cap)
        s.exit_.exit_cap_rate = min(1.0, s.exit_.exit_cap_rate / 0.90)
    elif name == "combined_stress":
        s.loan.interest_rate = min(1.0, s.loan.interest_rate + 0.010)
        s.income.gpi_monthly_yen = round(s.income.gpi_monthly_yen * 0.95)
        s.income.vacancy_rate = min(1.0, s.income.vacancy_rate + 0.05)
        for f in _OPEX_FIELDS:
            setattr(s.opex, f, round(getattr(s.opex, f) * 1.10))
        s.opex.repair_reserve_monthly_yen = round(s.opex.repair_reserve_monthly_yen * 1.20)
        s.exit_.exit_cap_rate = min(1.0, s.exit_.exit_cap_rate / 0.90)
    return s


def _judge(atcf_y1: int, irr: float | None, dscr_min: float) -> Literal["good", "warn", "bad"]:
    """シナリオ結果の三段階判定。"""
    irr_ok = irr is not None and irr >= 0.06
    if atcf_y1 < 0 or dscr_min < 1.0:
        return "bad"
    if not irr_ok or dscr_min < 1.25:
        return "warn"
    return "good"


def _run_scenario(
    a: Assumptions, name: ScenarioName, base: ScenarioResult | None = None
) -> ScenarioResult:
    scen_a = _apply_scenario(a, name)
    r = run_full_analysis(scen_a)
    dscr_delta = 0.0 if base is None else round(r.kpi.dscr_min - base.dscr_min, 4)
    irr_delta = (
        None
        if base is None or r.kpi.equity_irr is None or base.irr is None
        else round(r.kpi.equity_irr - base.irr, 4)
    )
    return ScenarioResult(
        scenario=name,
        atcf_year1_yen=r.kpi.atcf_first_year_yen,
        irr=r.kpi.equity_irr,
        dscr_min=r.kpi.dscr_min,
        net_proceeds_yen=r.exit_.net_proceeds_yen,
        dscr_min_delta=dscr_delta,
        irr_delta=irr_delta,
        judgment=_judge(r.kpi.atcf_first_year_yen, r.kpi.equity_irr, r.kpi.dscr_min),
    )


def sensitivity_grid(a: Assumptions) -> SensitivityResult:
    """標準条件 + 固定7ストレスを実行し、各ストレスに base との Δ を付す。"""
    base = _run_scenario(a, "base")
    others = [_run_scenario(a, s, base=base) for s in STRESS_SCENARIOS]
    return SensitivityResult(base=base, scenarios=others)
