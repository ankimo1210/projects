"""NormalizedProperty: 物件の正規化表現 + フィールド出所追跡。

Assumptions が「計算に必要な値の集合」であるのに対し、
NormalizedProperty は「その値が何由来か (PDF/URL/ユーザー/デフォルト)」を保持する。

risk_engine, evidence_cards, checklist などが confidence (A/B/C/D) を判定するために使う。

Assumptions は変更しない (純粋関数の入力契約を維持)。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["pdf", "url", "user_input", "default", "derived"]
Confidence = Literal["A", "B", "C", "D"]


_SOURCE_TO_CONFIDENCE: dict[Source, Confidence] = {
    "pdf": "B",
    "url": "B",
    "user_input": "C",
    "derived": "C",
    "default": "D",
}


def source_to_confidence(source: Source) -> Confidence:
    """source から confidence への既定マッピング。

    A (一次資料・実データ確認) は外部データ照合で別途昇格させる前提。
    """
    return _SOURCE_TO_CONFIDENCE[source]


class FieldSource(BaseModel):
    source: Source
    confidence: Confidence
    raw_value: Any | None = None  # 元データ (LLM 抽出の生値など)
    note: str | None = None

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_source(cls, source: Source, *, raw_value: Any | None = None, note: str | None = None) -> FieldSource:
        return cls(
            source=source,
            confidence=source_to_confidence(source),
            raw_value=raw_value,
            note=note,
        )


class NormalizedProperty(BaseModel):
    """物件正規化データ + 各フィールドの出所マップ。

    field_sources のキーは Assumptions の dotted path に揃える。例:
      - "property.purchase_price_yen"
      - "income.gpi_monthly_yen"
      - "income.vacancy_rate"
      - "loan.interest_rate"
      - "opex.repair_reserve_monthly_yen"
      - "exit.exit_cap_rate"
    """

    field_sources: dict[str, FieldSource] = Field(default_factory=dict)
    # 補足情報 (相場照合・チェックリストに使う)
    rent_per_sqm_monthly_yen: float | None = None
    building_age_years: int | None = None
    has_rent_roll: bool = False
    is_leasehold: bool = False
    is_non_rebuildable: bool = False
    is_old_seismic: bool = False  # 旧耐震 (1981年以前)

    model_config = ConfigDict(extra="forbid")

    def confidence_for(self, field_path: str, default: Confidence = "C") -> Confidence:
        fs = self.field_sources.get(field_path)
        return fs.confidence if fs else default

    def source_for(self, field_path: str, default: Source = "user_input") -> Source:
        fs = self.field_sources.get(field_path)
        return fs.source if fs else default

    @classmethod
    def all_user_input(cls) -> NormalizedProperty:
        """テスト用: すべて user_input としてマークした空 NormalizedProperty を返す。"""
        return cls(field_sources={})
