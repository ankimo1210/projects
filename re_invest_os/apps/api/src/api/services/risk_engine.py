"""前提リスク評価エンジン (純粋ロジック・LLM 不使用)。

入力:
- Assumptions: 計算前提
- AnalysisResult: full 分析結果
- NormalizedProperty: 各前提の出所マップ (任意。なければ全て user_input=C 扱い)
- MarketBenchmark: 相場レンジ (任意。なければ相場乖離判定はスキップ)

出力: list[AssumptionRisk]

各カテゴリ:
- rent / vacancy / opex / repair / interest_rate / exit_price / tax
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from re_engine.models import AnalysisResult, Assumptions
from re_engine.normalized import Confidence, NormalizedProperty

Category = Literal[
    "rent", "vacancy", "opex", "repair", "interest_rate", "exit_price", "tax"
]
RiskLevel = Literal["low", "medium", "high", "unknown"]


class MarketBenchmark(BaseModel):
    """相場ベンチマーク (任意)。

    値が None のフィールドはスキップ。
    """

    rent_per_sqm_monthly_p25: float | None = None
    rent_per_sqm_monthly_p50: float | None = None
    rent_per_sqm_monthly_p75: float | None = None
    area_vacancy_rate_p50: float | None = None
    market_cap_rate_p50: float | None = None
    model_config = ConfigDict(extra="forbid")


class AssumptionRisk(BaseModel):
    category: Category
    confidence: Confidence
    risk_level: RiskLevel
    reason: str
    source: str | None = None  # field_sources の note 等
    value_json: dict[str, Any] | None = None  # 評価対象の値・閾値
    model_config = ConfigDict(extra="forbid")


# ────────────────────────────────────────
# 個別カテゴリ判定
# ────────────────────────────────────────


def _bump_for_low_confidence(base: RiskLevel, confidence: Confidence) -> RiskLevel:
    """confidence が C/D なら medium 以上に底上げ。"""
    if base == "low" and confidence in ("C", "D"):
        return "medium"
    return base


def _rent_risk(
    a: Assumptions,
    norm: NormalizedProperty,
    market: MarketBenchmark | None,
) -> AssumptionRisk:
    conf = norm.confidence_for("income.gpi_monthly_yen", default="C")
    risk: RiskLevel = "low"
    reason_parts: list[str] = []

    # 相場乖離判定
    if (
        market is not None
        and market.rent_per_sqm_monthly_p75 is not None
        and a.property.building_area_sqm > 0
    ):
        rent_per_sqm = a.income.gpi_monthly_yen / a.property.building_area_sqm
        if rent_per_sqm > market.rent_per_sqm_monthly_p75:
            risk = "high"
            reason_parts.append(
                f"設定賃料 {rent_per_sqm:,.0f} 円/㎡ が相場上位 25% "
                f"({market.rent_per_sqm_monthly_p75:,.0f} 円/㎡) を上回る"
            )

    if not reason_parts:
        reason_parts.append(
            "実賃料の確認資料がない場合、賃料下振れリスクが大きい"
            if conf in ("C", "D")
            else "資料記載の賃料は将来更新時に変動する可能性がある"
        )
    risk = _bump_for_low_confidence(risk, conf)
    return AssumptionRisk(
        category="rent",
        confidence=conf,
        risk_level=risk,
        reason="; ".join(reason_parts),
        value_json={"gpi_monthly_yen": a.income.gpi_monthly_yen},
    )


def _vacancy_risk(
    a: Assumptions,
    norm: NormalizedProperty,
    market: MarketBenchmark | None,
) -> AssumptionRisk:
    conf = norm.confidence_for("income.vacancy_rate", default="D")
    risk: RiskLevel = "low"
    reasons: list[str] = []
    if market and market.area_vacancy_rate_p50 is not None:
        if a.income.vacancy_rate < market.area_vacancy_rate_p50 - 0.02:
            risk = "high"
            reasons.append(
                f"設定空室率 {a.income.vacancy_rate * 100:.1f}% がエリア中央値 "
                f"{market.area_vacancy_rate_p50 * 100:.1f}% を大きく下回る"
            )
    if not reasons:
        if conf in ("C", "D"):
            reasons.append("空室率はデフォルト/ユーザー入力のため、エリア実態と乖離する可能性")
        else:
            reasons.append("資料の空室率は時点情報。中長期では変動しうる")
    risk = _bump_for_low_confidence(risk, conf)
    return AssumptionRisk(
        category="vacancy",
        confidence=conf,
        risk_level=risk,
        reason="; ".join(reasons),
        value_json={"vacancy_rate": a.income.vacancy_rate},
    )


def _opex_risk(a: Assumptions, norm: NormalizedProperty) -> AssumptionRisk:
    conf = norm.confidence_for("opex.fixed_property_tax_yen", default="D")
    reasons: list[str] = []
    # 管理費・修繕積立金がゼロの区分は警戒
    if a.property.property_type == "kuubun" and a.opex.building_mgmt_yen == 0:
        return AssumptionRisk(
            category="opex",
            confidence=conf,
            risk_level="high",
            reason="区分マンションだが管理費・修繕積立金がゼロ。実費反映されていない可能性",
            value_json={"building_mgmt_yen": 0},
        )
    if a.opex.fixed_property_tax_yen == 0:
        reasons.append("固都税がゼロ。実額未反映の可能性")
        risk: RiskLevel = "high"
    else:
        risk = "low"
    risk = _bump_for_low_confidence(risk, conf)
    if not reasons:
        reasons.append("OPEX 実額は管理体制・修繕計画で変動。資料突合推奨")
    return AssumptionRisk(
        category="opex",
        confidence=conf,
        risk_level=risk,
        reason="; ".join(reasons),
        value_json={
            "fixed_property_tax_yen": a.opex.fixed_property_tax_yen,
            "building_mgmt_yen": a.opex.building_mgmt_yen,
        },
    )


def _repair_risk(a: Assumptions, norm: NormalizedProperty) -> AssumptionRisk:
    conf = norm.confidence_for("opex.repair_reserve_monthly_yen", default="D")
    # 築年数: building_completion_ym から
    try:
        y, _m = a.property.building_completion_ym.split("-")
        age = a.property.acquisition_year - int(y)
    except Exception:
        age = norm.building_age_years or 0
    reasons: list[str] = []
    if a.opex.repair_reserve_monthly_yen == 0:
        reasons.append("修繕積立月額がゼロ")
        risk: RiskLevel = "high"
    elif age >= 15:
        reasons.append(f"築 {age} 年で大規模修繕が近い/必要")
        risk = "high"
    elif age >= 10:
        reasons.append(f"築 {age} 年で短中期の修繕費上振れ余地")
        risk = "medium"
    else:
        reasons.append("修繕費は資料反映の有無で大きく変動")
        risk = "low"
    risk = _bump_for_low_confidence(risk, conf)
    return AssumptionRisk(
        category="repair",
        confidence=conf,
        risk_level=risk,
        reason="; ".join(reasons),
        value_json={
            "repair_reserve_monthly_yen": a.opex.repair_reserve_monthly_yen,
            "building_age_years": age,
        },
    )


def _interest_rate_risk(a: Assumptions, norm: NormalizedProperty) -> AssumptionRisk:
    conf = norm.confidence_for("loan.interest_rate", default="C")
    rate = a.loan.interest_rate
    reasons: list[str] = []
    if rate < 0.015:
        risk: RiskLevel = "high"
        reasons.append(f"金利 {rate * 100:.2f}% は楽観前提。+100bp ストレス耐性を要確認")
    elif rate < 0.025:
        risk = "medium"
        reasons.append(f"金利 {rate * 100:.2f}% は変動金利水準。上振れ余地あり")
    else:
        risk = "low"
        reasons.append(f"金利 {rate * 100:.2f}% は保守的")
    risk = _bump_for_low_confidence(risk, conf)
    return AssumptionRisk(
        category="interest_rate",
        confidence=conf,
        risk_level=risk,
        reason="; ".join(reasons),
        value_json={"interest_rate": rate},
    )


def _exit_price_risk(
    a: Assumptions,
    result: AnalysisResult,
    norm: NormalizedProperty,
    market: MarketBenchmark | None,
) -> AssumptionRisk:
    conf = norm.confidence_for("exit.exit_cap_rate", default="D")
    exit_cap = a.exit_.exit_cap_rate
    reasons: list[str] = []
    risk: RiskLevel = "medium"
    if market and market.market_cap_rate_p50 is not None:
        if exit_cap < market.market_cap_rate_p50 - 0.005:
            risk = "high"
            reasons.append(
                f"出口Cap {exit_cap * 100:.2f}% が相場 {market.market_cap_rate_p50 * 100:.2f}% を下回る"
            )
        else:
            risk = "low"
            reasons.append("出口Cap は相場圏内")
    else:
        reasons.append("出口Cap は将来推定。相場データ未照合のため不確実性が大きい")
    # 出口で損失なら一段悪化
    if result.exit_.net_proceeds_yen < a.acquisition.equity_yen:
        if risk != "high":
            risk = "high"
        reasons.append("出口手取りが当初自己資金を下回る試算")
    risk = _bump_for_low_confidence(risk, conf)
    return AssumptionRisk(
        category="exit_price",
        confidence=conf,
        risk_level=risk,
        reason="; ".join(reasons),
        value_json={
            "exit_cap_rate": exit_cap,
            "net_proceeds_yen": result.exit_.net_proceeds_yen,
        },
    )


def _tax_risk(a: Assumptions, norm: NormalizedProperty) -> AssumptionRisk:
    conf = norm.confidence_for("tax.income_tax_rate", default="D")
    rate = a.tax.income_tax_rate + a.tax.resident_tax_rate
    reasons: list[str] = []
    if rate < 0.20:
        risk: RiskLevel = "medium"
        reasons.append("低い実効税率を前提。所得増加で税負担増の余地")
    else:
        risk = "low"
        reasons.append("税率は標準的レンジ")
    risk = _bump_for_low_confidence(risk, conf)
    return AssumptionRisk(
        category="tax",
        confidence=conf,
        risk_level=risk,
        reason="; ".join(reasons),
        value_json={
            "income_tax_rate": a.tax.income_tax_rate,
            "resident_tax_rate": a.tax.resident_tax_rate,
        },
    )


# ────────────────────────────────────────
# Public entry
# ────────────────────────────────────────


def assess_assumption_risks(
    assumptions: Assumptions,
    result: AnalysisResult,
    normalized: NormalizedProperty | None = None,
    market: MarketBenchmark | None = None,
) -> list[AssumptionRisk]:
    """全カテゴリのリスクを評価して返す。market が無くても動く。"""
    norm = normalized or NormalizedProperty.all_user_input()
    return [
        _rent_risk(assumptions, norm, market),
        _vacancy_risk(assumptions, norm, market),
        _opex_risk(assumptions, norm),
        _repair_risk(assumptions, norm),
        _interest_rate_risk(assumptions, norm),
        _exit_price_risk(assumptions, result, norm, market),
        _tax_risk(assumptions, norm),
    ]


def summarize_risks(risks: list[AssumptionRisk]) -> str:
    """画面上部に出すための 1 行サマリ。"""
    highs = [r.category for r in risks if r.risk_level == "high"]
    if not highs:
        meds = [r.category for r in risks if r.risk_level == "medium"]
        if not meds:
            return "前提リスクは概ね低水準です。"
        return f"中リスク前提: {', '.join(meds)}。資料突合で確度を上げられます。"
    return f"この分析は {', '.join(highs)} の前提に強く依存しています。"
