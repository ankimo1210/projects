"""資料分類: テキストから document_type を判定する。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from api.services import prompts
from api.services.llm_client import CallMeta, chat_json
from api.services.pii import mask

DocumentType = Literal[
    "property_brochure",
    "rent_roll",
    "income_statement",
    "fixed_asset_tax",
    "registry_certificate",
    "repair_history",
    "management_report",
    "lease_contract",
    "construction_cert",
    "long_term_repair",
    "important_matter",
    "unknown",
]


@dataclass(frozen=True)
class ClassifyResult:
    document_type: DocumentType
    confidence: float
    reason: str
    meta: CallMeta
    pii_redactions: dict[str, int]


_MAX_TEXT = 2000


def classify(text: str) -> ClassifyResult:
    """テキストの冒頭最大 2000 文字を見て分類する。PII は事前にマスク。"""
    head = text[:_MAX_TEXT]
    masked = mask(head)
    prompt = prompts.load("classify_document")
    r = chat_json(prompt, vars={"document_text": masked.text})
    return ClassifyResult(
        document_type=r.data.get("document_type", "unknown"),  # type: ignore[arg-type]
        confidence=float(r.data.get("confidence", 0.0)),
        reason=str(r.data.get("reason", "")),
        meta=r.meta,
        pii_redactions=masked.counts,
    )
