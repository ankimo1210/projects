"""レントロール (家賃明細表) の構造化抽出。

rent_roll_v1.md プロンプトを使用。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from api.services import prompts
from api.services.llm_client import CallMeta, LLMError, chat_json
from api.services.pii import mask

# ---------- モデル ----------


def _coerce_int(v: Any) -> int | None:
    if v is None or v == "" or v == "-":
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        try:
            return int(float(v.replace(",", "").replace("円", "").strip()))
        except ValueError:
            return None
    return None


def _coerce_float(v: Any) -> float | None:
    if v is None or v == "" or v == "-":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", "").strip())
        except ValueError:
            return None
    return None


def _coerce_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() not in ("false", "0", "no", "空室", "vacant", "")
    return bool(v)


IntField = Annotated[int | None, BeforeValidator(_coerce_int)]
FloatField = Annotated[float | None, BeforeValidator(_coerce_float)]
BoolField = Annotated[bool, BeforeValidator(_coerce_bool)]


class RentRollUnit(BaseModel):
    unit_number: str | None = None
    floor: int | None = None
    floor_plan: str | None = None
    area_sqm: FloatField = None
    contract_rent_yen: IntField = None
    common_area_fee_yen: IntField = None
    parking_fee_yen: IntField = None
    deposit_months: FloatField = None
    key_money_months: FloatField = None
    renewal_fee_months: FloatField = None
    contract_start_date: str | None = None
    contract_end_date: str | None = None
    is_occupied: BoolField = True
    vacancy_period_months: FloatField = None
    arrears_status: str = "unknown"
    tenant_type: str = "unknown"
    free_rent_months: IntField = None

    model_config = ConfigDict(extra="ignore")


class RentRollExtraction(BaseModel):
    units: list[RentRollUnit] = Field(default_factory=list)
    rent_roll_date: str | None = None
    total_monthly_rent_yen: IntField = None
    total_annual_rent_yen: IntField = None
    occupancy_rate: FloatField = None
    raw_table_markdown: str | None = None
    field_confidences: dict[str, float] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")

    def with_computed_totals(self) -> RentRollExtraction:
        """units から total と occupancy_rate を補完した新しいインスタンスを返す。

        LLM が合計値を省略した場合の fallback。
        """
        occupied = [u for u in self.units if u.is_occupied]
        updates: dict = {}
        monthly = sum((u.contract_rent_yen or 0) + (u.common_area_fee_yen or 0) for u in occupied)
        if monthly > 0 and self.total_monthly_rent_yen is None:
            updates["total_monthly_rent_yen"] = monthly
            updates["total_annual_rent_yen"] = monthly * 12
        if self.units and self.occupancy_rate is None:
            updates["occupancy_rate"] = round(len(occupied) / len(self.units), 4)
        return self.model_copy(update=updates) if updates else self


# ---------- プロンプト v2 (テンプレート方式) ----------

_RENT_ROLL_USER_TEMPLATE = """\
レントロールテキスト:
---
{{rent_roll_text_or_image}}
---

変換ルール: 万円→×10000 / 空室はcontract_rent_yen=null,is_occupied=false / 個人名不要

以下のJSONテンプレートを埋めて返してください:
{
  "units": [
    {
      "unit_number": null,
      "floor": null,
      "floor_plan": null,
      "area_sqm": null,
      "contract_rent_yen": null,
      "common_area_fee_yen": null,
      "parking_fee_yen": null,
      "deposit_months": null,
      "key_money_months": null,
      "contract_start_date": null,
      "is_occupied": true,
      "arrears_status": "unknown",
      "tenant_type": "unknown"
    }
  ],
  "rent_roll_date": null,
  "total_monthly_rent_yen": null,
  "occupancy_rate": null,
  "raw_table_markdown": null,
  "field_confidences": {}
}
"""


# ---------- 抽出関数 ----------


@dataclass(frozen=True)
class RentRollResult:
    data: RentRollExtraction
    meta: CallMeta
    pii_redactions: dict[str, int]
    warnings: list[str]


_MAX_TEXT = 4000


def extract(text: str) -> RentRollResult:
    """レントロールテキスト → RentRollExtraction。"""
    head = text[:_MAX_TEXT]
    masked = mask(head)
    prompt = prompts.load("rent_roll")

    # v2 テンプレート方式
    from api.services.prompts import Prompt

    prompt_v2 = Prompt(
        name=prompt.name,
        version=prompt.version,
        system=prompt.system,
        user_template=_RENT_ROLL_USER_TEMPLATE,
        output_schema=None,
        raw_path=prompt.raw_path,
    )

    r = chat_json(prompt_v2, vars={"rent_roll_text_or_image": masked.text})
    try:
        validated = RentRollExtraction.model_validate(r.data)
    except Exception as e:
        raise LLMError(f"RentRollExtraction validation failed: {e}") from e

    validated = validated.with_computed_totals()
    return RentRollResult(
        data=validated,
        meta=r.meta,
        pii_redactions=masked.counts,
        warnings=r.warnings,
    )
