"""販売図面の構造化抽出。

役割: テキスト → PropertyBrochureExtraction (Pydantic)。
- 不明値は None
- 各フィールドに 0.0-1.0 の confidence
- LLM へは PII マスク済みテキストを渡す
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

from api.services import prompts
from api.services.llm_client import CallMeta, LLMError, chat_json
from api.services.pii import mask

Structure = Literal["wood", "rc", "src", "steel"]


def _coerce_list(v: Any) -> list[Any]:
    """LLM が dict や str で返してきても list に正規化。"""
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return list(v.keys())
    if isinstance(v, str):
        return [v] if v.strip() else []
    return [v]


def _coerce_dict(v: Any) -> dict[str, float]:
    """LLM が list で返してきても dict に正規化。"""
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, list):
        return {str(item): 1.0 for item in v}
    return {}


def _coerce_int(v: Any) -> int | None:
    """'39,800,000' / '3980万円' / 39800000.0 → int を許容。"""
    if v is None or v == "":
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        s = v.replace(",", "").replace("円", "").strip()
        try:
            return int(float(s))
        except ValueError:
            return None
    return None


def _coerce_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.replace(",", "").replace("%", "").strip()
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _coerce_structure(v: Any) -> str | None:
    """'RC造' / '鉄筋コンクリート' → 'rc' に正規化。"""
    if v is None:
        return None
    s = str(v).lower().strip()
    mapping = {
        "wood": "wood",
        "木造": "wood",
        "木": "wood",
        "rc": "rc",
        "rc造": "rc",
        "鉄筋コンクリート": "rc",
        "ｒｃ": "rc",
        "src": "src",
        "src造": "src",
        "鉄骨鉄筋コンクリート": "src",
        "steel": "steel",
        "鉄骨": "steel",
        "s造": "steel",
        "軽量鉄骨": "steel",
        "重量鉄骨": "steel",
    }
    for key, val in mapping.items():
        if key in s:
            return val
    return None


IntField = Annotated[int | None, BeforeValidator(_coerce_int)]
FloatField = Annotated[float | None, BeforeValidator(_coerce_float)]
ListField = Annotated[list[Any], BeforeValidator(_coerce_list)]
DictField = Annotated[dict[str, float], BeforeValidator(_coerce_dict)]
StructureField = Annotated[Structure | None, BeforeValidator(_coerce_structure)]


class PropertyBrochureExtraction(BaseModel):
    """販売図面から取れる主要 26 項目 (v1)。

    LLM の型ゆれを吸収するため Before validator で coerce。
    """

    property_name: str | None = None
    address: str | None = None
    asking_price_yen: IntField = None

    nearest_station: str | None = None
    station_walk_min: IntField = None

    land_area_sqm: FloatField = None
    building_area_sqm: FloatField = None
    exclusive_area_sqm: FloatField = None

    structure: StructureField = None
    floors_above: IntField = None
    num_units: IntField = None
    floor_plan: str | None = None
    build_year_month: str | None = None  # YYYY-MM

    zoning: str | None = None
    bcr_pct: FloatField = None
    far_pct: FloatField = None
    road_frontage: Annotated[
        str | None,
        BeforeValidator(lambda v: str(v) if v is not None and not isinstance(v, str) else v),
    ] = None

    gross_yield_pct: FloatField = None
    estimated_full_rent_monthly_yen: IntField = None

    management_fee_monthly_yen: IntField = None
    repair_reserve_monthly_yen: IntField = None

    notes: str | None = None
    field_confidences: DictField = Field(default_factory=dict)
    inferred_fields: ListField = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


def _output_schema() -> dict[str, Any]:
    """Ollama に渡す JSON Schema (PropertyBrochureExtraction)。"""
    schema = PropertyBrochureExtraction.model_json_schema()
    # Ollama の format=schema は必須キーをある程度尊重する。緩く全項目を許容。
    return schema


@dataclass(frozen=True)
class BrochureResult:
    data: PropertyBrochureExtraction
    meta: CallMeta
    pii_redactions: dict[str, int]
    warnings: list[str]


_MAX_TEXT = 8000


def _postprocess(d: PropertyBrochureExtraction) -> tuple[PropertyBrochureExtraction, list[str]]:
    """LLM の典型的なスケール誤りを補正。"""
    notes: list[str] = []
    updates: dict[str, Any] = {}

    # --- gross_yield_pct の段階的後処理 ---
    _y = d.gross_yield_pct

    # Step 1: 0-1 で来ている場合 → ×100 して % に正規化 (0.062 → 6.2)
    if _y is not None and 0 < _y < 1:
        _y = round(_y * 100, 6)
        notes.append(f"gross_yield_pct: 小数 → パーセントに変換 → {_y:.4f}")
        updates["gross_yield_pct"] = _y

    # Step 2: 正規化後の値で異常検出
    if _y is not None:
        if _y >= 100:
            updates["gross_yield_pct"] = None
            notes.append(f"gross_yield_pct={_y} は ≥100% → null")
            _y = None
        elif len(str(_y).rstrip("0").split(".")[-1]) > 2:
            # 小数点以下 3 桁以上: 賃料数値の誤認疑い (例: 5.649948)
            updates["gross_yield_pct"] = None
            notes.append(f"gross_yield_pct={_y} は有効桁数が多すぎる (賃料値の誤認疑い) → null")
            _y = None

    # bcr_pct / far_pct も 0-1 変換
    if d.bcr_pct is not None and 0 < d.bcr_pct < 1:
        updates["bcr_pct"] = d.bcr_pct * 100
    if d.far_pct is not None and 0 < d.far_pct < 1:
        updates["far_pct"] = d.far_pct * 100

    # build_year_month の YYYY/M → YYYY-MM 正規化
    if d.build_year_month:
        s = d.build_year_month.replace("年", "-").replace("月", "").replace("/", "-").strip("-")
        parts = s.split("-")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            normalized = f"{int(parts[0]):04d}-{int(parts[1]):02d}"
            if normalized != d.build_year_month:
                updates["build_year_month"] = normalized

    # nearest_station: "赤嶺" → "赤嶺駅" (駅サフィックス補完)
    if d.nearest_station and not d.nearest_station.endswith("駅"):
        updates["nearest_station"] = d.nearest_station + "駅"

    # gross_yield_pct が null で price + monthly_rent が揃っていれば計算補完
    current_yield = updates.get("gross_yield_pct", d.gross_yield_pct)
    price = d.asking_price_yen
    rent = d.estimated_full_rent_monthly_yen
    if current_yield is None and price and rent and price > 0:
        calc = round(rent * 12 / price * 100, 2)
        if 0.5 <= calc <= 30:  # 合理的な範囲のみ
            updates["gross_yield_pct"] = calc
            if "inferred_fields" not in updates:
                updates["inferred_fields"] = list(d.inferred_fields)
            updates["inferred_fields"] = [*updates["inferred_fields"], "gross_yield_pct"]
            notes.append(f"gross_yield_pct={calc}% を price×rent から計算補完")

    if updates:
        return d.model_copy(update=updates), notes
    return d, notes


def extract(text: str) -> BrochureResult:
    """販売図面テキスト → PropertyBrochureExtraction。

    注: ローカル LLM (qwen2.5:7b / gemma3:12b) は複雑な JSON Schema を渡すと
    一部フィールドを脱落させる傾向がある。v1 では prompt+few-shot+format=json で
    誘導し、Pydantic 側で検証 & 後処理する方針。
    """
    head = text[:_MAX_TEXT]
    masked = mask(head)
    prompt = prompts.load("property_brochure")
    r = chat_json(prompt, vars={"brochure_text": masked.text})
    try:
        validated = PropertyBrochureExtraction.model_validate(r.data)
    except ValidationError as e:
        raise LLMError(f"PropertyBrochureExtraction validation failed: {e}") from e
    fixed, notes = _postprocess(validated)
    return BrochureResult(
        data=fixed,
        meta=r.meta,
        pii_redactions=masked.counts,
        warnings=r.warnings + notes,
    )
