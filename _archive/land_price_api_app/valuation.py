"""
valuation.py
掲載物件の簡易スコアリングと割安・割高判定。
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from utils import safe_float as _num


def score_location_features(features: dict[str, Any]) -> dict[str, float]:
    """周辺施設・地形から簡易スコアを算出する。"""
    life = 50.0
    family = 50.0
    negative = 20.0
    terrain = 20.0

    life += min(_num(features.get("convenience_count_500m")) * 6.0, 18.0)
    life += min(_num(features.get("supermarket_count_1000m")) * 5.0, 15.0)
    life += (
        8.0
        if _nearest(features.get("transit_nearest_m"))
        and _nearest(features.get("transit_nearest_m")) <= 800
        else 0.0
    )
    life -= (
        5.0
        if _nearest(features.get("transit_nearest_m"))
        and _nearest(features.get("transit_nearest_m")) > 1500
        else 0.0
    )

    family += min(_num(features.get("school_count_1000m")) * 6.0, 18.0)
    family += min(_num(features.get("medical_count_1000m")) * 4.0, 12.0)
    family += min(_num(features.get("park_count_1000m")) * 4.0, 12.0)

    negative += min(_num(features.get("pachinko_count_1000m")) * 12.0, 36.0)
    if (
        _nearest(features.get("pachinko_nearest_m"))
        and _nearest(features.get("pachinko_nearest_m")) <= 300
    ):
        negative += 12.0

    elevation_m = _nearest(features.get("elevation_m"))
    if elevation_m is not None and elevation_m < 3:
        terrain += 35.0
    elif elevation_m is not None and elevation_m < 10:
        terrain += 15.0
    if (
        _nearest(features.get("nearest_water_m"))
        and _nearest(features.get("nearest_water_m")) <= 300
    ):
        terrain += 20.0
    elif (
        _nearest(features.get("nearest_water_m"))
        and _nearest(features.get("nearest_water_m")) <= 800
    ):
        terrain += 8.0
    if features.get("flood_risk_flag") is True:
        terrain += 25.0
    if features.get("landslide_risk_flag") is True:
        terrain += 15.0

    return {
        "life_convenience_score": round(_clip(life, 0, 100), 1),
        "family_score": round(_clip(family, 0, 100), 1),
        "negative_facility_score": round(_clip(negative, 0, 100), 1),
        "terrain_caution_score": round(_clip(terrain, 0, 100), 1),
    }


def build_valuation_result(
    listing_row: dict[str, Any],
    snapshot_row: dict[str, Any] | None,
    feature_row: dict[str, Any] | None,
    *,
    valuation_version: int = 1,
) -> dict[str, Any]:
    """ルールベースの割安・割高判定結果を返す。"""
    snapshot_row = snapshot_row or {}
    feature_row = feature_row or {}
    scores = score_location_features(feature_row)

    asking_price = _num(listing_row.get("asking_price_yen"))
    public_gap = _num(snapshot_row.get("public_notice_gap_pct"))
    trade_gap = _num(snapshot_row.get("trade_gap_pct"))

    base_gap_values = [v for v in (public_gap, trade_gap) if v is not None]
    gap_pct = round(sum(base_gap_values) / len(base_gap_values), 2) if base_gap_values else None
    fair_value_yen = None
    if asking_price is not None and gap_pct is not None:
        fair_value_yen = asking_price / (1 + gap_pct / 100.0) if gap_pct > -99 else None

    adjustment = 0.0
    reasons: list[dict[str, Any]] = []
    if public_gap is not None:
        reasons.append({"factor": "public_notice_gap_pct", "value": round(public_gap, 2)})
    if trade_gap is not None:
        reasons.append({"factor": "trade_gap_pct", "value": round(trade_gap, 2)})

    life = scores["life_convenience_score"]
    family = scores["family_score"]
    negative = scores["negative_facility_score"]
    terrain = scores["terrain_caution_score"]

    if life >= 70:
        adjustment -= 2.0
        reasons.append({"factor": "life_convenience", "direction": "supportive", "value": life})
    elif life <= 35:
        adjustment += 2.0
        reasons.append({"factor": "life_convenience", "direction": "weak", "value": life})

    if family >= 70:
        adjustment -= 1.5
        reasons.append({"factor": "family_score", "direction": "supportive", "value": family})

    if negative >= 45:
        adjustment += 3.0
        reasons.append({"factor": "negative_facility", "direction": "risk", "value": negative})

    if terrain >= 40:
        adjustment += 4.0
        reasons.append({"factor": "terrain_caution", "direction": "risk", "value": terrain})

    adjusted_gap_pct = round(gap_pct + adjustment, 2) if gap_pct is not None else None
    label = _gap_label(adjusted_gap_pct)
    confidence = _confidence(snapshot_row, feature_row)

    return {
        "listing_id": listing_row["listing_id"],
        "valuation_date": date.today(),
        "valuation_version": valuation_version,
        "model_name": "rules_v1",
        "fair_value_yen": fair_value_yen,
        "gap_pct": gap_pct,
        "adjusted_gap_pct": adjusted_gap_pct,
        "cheap_or_expensive": label,
        "confidence": confidence,
        "life_convenience_score": life,
        "family_score": family,
        "negative_facility_score": negative,
        "terrain_caution_score": terrain,
        "reasons_json": reasons,
    }


def render_reason_texts(reasons_json: str | list[dict[str, Any]] | None) -> list[str]:
    """UI表示用の理由文リストへ変換する。"""
    if reasons_json is None:
        return []
    if isinstance(reasons_json, str):
        try:
            reasons = json.loads(reasons_json)
        except Exception:
            return []
    else:
        reasons = reasons_json
    if not isinstance(reasons, list):
        return []

    lines: list[str] = []
    for reason in reasons:
        factor = reason.get("factor")
        value = reason.get("value")
        direction = reason.get("direction")
        if factor == "public_notice_gap_pct":
            lines.append(f"公示地価比 {value:+.1f}%")
        elif factor == "trade_gap_pct":
            lines.append(f"取引価格比 {value:+.1f}%")
        elif factor == "life_convenience":
            lines.append(f"生活利便 {direction} ({value:.0f})")
        elif factor == "family_score":
            lines.append(f"ファミリー適性 {direction} ({value:.0f})")
        elif factor == "negative_facility":
            lines.append(f"嫌悪施設リスク {direction} ({value:.0f})")
        elif factor == "terrain_caution":
            lines.append(f"地形注意 {direction} ({value:.0f})")
    return lines


def _confidence(snapshot_row: dict[str, Any], feature_row: dict[str, Any]) -> str:
    signal_count = 0
    if snapshot_row.get("public_notice_gap_pct") is not None:
        signal_count += 1
    if snapshot_row.get("trade_gap_pct") is not None:
        signal_count += 1
    if feature_row.get("elevation_m") is not None:
        signal_count += 1
    if feature_row.get("transit_nearest_m") is not None:
        signal_count += 1
    if signal_count >= 4:
        return "high"
    if signal_count >= 2:
        return "medium"
    return "low"


def _gap_label(gap_pct: float | None) -> str | None:
    if gap_pct is None:
        return None
    if gap_pct <= -10:
        return "割安"
    if gap_pct <= -3:
        return "やや割安"
    if gap_pct < 3:
        return "中立"
    if gap_pct < 10:
        return "やや割高"
    return "割高"


def _nearest(value: Any) -> float | None:
    return _num(value)


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
