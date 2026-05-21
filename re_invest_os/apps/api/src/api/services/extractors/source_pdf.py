"""PDF source: バイト列 → テキスト抽出。

v1:
- pypdf でテキスト層を抽出
- テキスト層が無いスキャン PDF は v1 では非対応 → 警告を返す
- ページ全部結合 (ページ境界は \\n\\n)
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import pypdf


@dataclass(frozen=True)
class PdfExtractionResult:
    text: str
    num_pages: int
    is_scanned: bool  # テキスト層なし
    warnings: list[str]


def extract_text(data: bytes) -> PdfExtractionResult:
    reader = pypdf.PdfReader(io.BytesIO(data))
    parts: list[str] = []
    warnings: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            txt = page.extract_text() or ""
        except Exception as e:
            txt = ""
            warnings.append(f"page {i + 1}: extraction error: {type(e).__name__}: {e}")
        parts.append(txt)
    text = "\n\n".join(parts).strip()
    is_scanned = len(text) < 30  # 殆ど取れない = スキャン
    if is_scanned:
        warnings.append("テキスト層がほぼ取れません。スキャン PDF の可能性 (v1 では OCR 非対応)")
    return PdfExtractionResult(
        text=text,
        num_pages=len(reader.pages),
        is_scanned=is_scanned,
        warnings=warnings,
    )
