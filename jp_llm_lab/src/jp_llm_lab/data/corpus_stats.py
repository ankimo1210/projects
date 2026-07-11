"""Character-class statistics for Japanese corpora (spec §4.2).

Used both by the snapshot quality filter and by the corpus-exploration
notebook, so filtering criteria and reported statistics can never diverge.
"""

from __future__ import annotations

from collections import Counter

JP_PUNCT = set("。、「」『』・…—〜？！（）［］【】　")


def char_class(ch: str) -> str:
    o = ord(ch)
    if 0x3040 <= o <= 0x309F:
        return "hiragana"
    if 0x30A0 <= o <= 0x30FF or 0x31F0 <= o <= 0x31FF:
        return "katakana"
    if 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:
        return "kanji"
    if ch.isascii() and ch.isalnum():
        return "ascii_alnum"
    if ch in JP_PUNCT:
        return "jp_punct"
    if ch.isspace():
        return "whitespace"
    return "other"


def class_counts(text: str) -> Counter[str]:
    return Counter(char_class(c) for c in text)


def japanese_ratio(text: str, counts: Counter[str] | None = None) -> float:
    """(かな+漢字+和文記号) / 非空白文字数 — the snapshot quality filter."""
    counts = counts or class_counts(text)
    non_ws = sum(n for cls, n in counts.items() if cls != "whitespace")
    if non_ws == 0:
        return 0.0
    jp = counts["hiragana"] + counts["katakana"] + counts["kanji"] + counts["jp_punct"]
    return jp / non_ws


def doc_stats(text: str) -> dict:
    counts = class_counts(text)
    return {
        "n_chars": len(text),
        "n_lines": text.count("\n") + 1,
        "japanese_ratio": round(japanese_ratio(text, counts), 4),
        "class_counts": dict(counts),
    }
