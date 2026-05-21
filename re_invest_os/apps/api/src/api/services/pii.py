"""PII (個人情報) マスキング。

LLM に送る前に必ず通すこと。原則:
- 過剰マスクは許容、漏洩は許容しない
- マスク後のトークンは [REDACTED:KIND] 形式で、何が落とされたか追跡可能にする
- 数値 (価格・賃料・面積) は守る (これらは PII ではない)

検出対象 (v1):
- 電話番号 (固定・携帯・市外局番つき)
- メールアドレス
- 氏名 (姓+名 / 業者担当者の典型パターン)
- 個人名でよくある「●●様」「●●氏」
- 住所詳細 (丁目-番地-号 のうち号レベル)
- 仲介業者名 (有限会社/株式会社 + 不動産系キーワード)

注: 物件所在の市区町村レベルは PII ではないので残す。
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MaskResult:
    text: str
    counts: dict[str, int]  # {"PHONE": 2, "EMAIL": 1, ...}

    @property
    def total(self) -> int:
        return sum(self.counts.values())


# --- patterns ---

_PHONE = re.compile(
    r"(?<!\d)"
    r"(?:"
    r"0\d{1,4}-\d{1,4}-\d{3,4}"  # 03-1234-5678
    r"|0\d{9,10}"  # 0312345678
    r"|\+81[-\s]?\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4}"
    r")"
    r"(?!\d)"
)

_EMAIL = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# 〒 + 7桁
_POSTAL = re.compile(r"〒?\s*\d{3}-?\d{4}")

# 住所の「号」レベル: 丁目-番-号 / 丁目X-Y / X-Y-Z (連続数字3組以上)
_ADDR_DETAIL = re.compile(
    r"(?<![A-Za-z0-9])"
    r"\d{1,3}[-－‐]\d{1,3}[-－‐]\d{1,4}"
    r"(?:号|号室)?"
)

# 部屋番号: 「●●号室」「101号」「504号室」
_ROOM_NUMBER = re.compile(r"\d{2,4}号(?:室)?")

# 様 / 氏 / 殿 を伴う氏名候補 (姓 + 様)
_HONORIFIC_NAME = re.compile(r"[一-龥々ヶ]{1,4}(?:\s+)?[一-龥々ヶ]{0,4}\s*(?:様|氏|殿|さん)")

# 担当: ●● / お問い合わせ先 ●●
_CONTACT_PERSON = re.compile(
    r"(?:担当|担当者|お問い?合わせ先?)\s*[:：]?\s*"
    r"[一-龥ァ-ヶｦ-ﾟＡ-Ｚａ-ｚA-Za-z]{2,20}"
)

# 業者名: 株式会社XX / 有限会社XX / XX不動産 / XXハウジング
_COMPANY = re.compile(
    r"(?:"
    r"(?:株式会社|有限会社|合同会社|合資会社|（株）|\(株\))[一-龥ァ-ヶａ-ｚA-Za-z0-9・]{1,30}"
    r"|[一-龥ァ-ヶａ-ｚA-Za-z0-9・]{2,20}(?:不動産|ハウジング|エステート|リアルティ|ホーム)"
    r")"
)

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # 順序重要: 長いもの・特異なものを先に
    ("EMAIL", _EMAIL),
    ("PHONE", _PHONE),
    ("POSTAL", _POSTAL),
    ("COMPANY", _COMPANY),
    ("CONTACT", _CONTACT_PERSON),
    ("NAME", _HONORIFIC_NAME),
    ("ADDR_DETAIL", _ADDR_DETAIL),
    ("ROOM", _ROOM_NUMBER),
]


def mask(text: str) -> MaskResult:
    """テキストの PII をマスクし、検出数を返す。

    入力テキストは破壊しない。マスクは ``[REDACTED:KIND]`` トークンで置換。
    """
    counts: dict[str, int] = {}
    out = text
    for kind, pat in _PATTERNS:
        n = 0

        def _sub(_m: re.Match[str], _k: str = kind) -> str:
            nonlocal n
            n += 1
            return f"[REDACTED:{_k}]"

        out = pat.sub(_sub, out)
        if n:
            counts[kind] = n
    return MaskResult(text=out, counts=counts)


def mask_text(text: str) -> str:
    """マスク済みテキストだけ返す薄いヘルパー。"""
    return mask(text).text
