from __future__ import annotations

import re
import unicodedata

from .parsers import detect_language
from .utils import stable_id

TRANSLATION = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "–": "-",
        "—": "-",
        "…": "...",
        " ": " ",
    }
)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).translate(TRANSLATION)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return re.sub(r"\s*\n\s*", "\n", normalized).strip()


def question_id(
    source_id: str, normalized_text: str, position: int, source_url: str = ""
) -> str:
    return stable_id(source_id, source_url, normalized_text, position, prefix="q_")


def normalized_language(text: str) -> str:
    return detect_language(normalize_text(text))
