"""NG 表現フィルタ (法務制約)。

LLM 生成テキストに以下の表現が含まれていないかを検出する。
含まれていた場合、呼び出し側が再生成・自動修正・拒否を判断する。

このリストは投資助言・誇張表現に該当しうるもの。
- summarizer.py (3行サマリー)
- memo builder (投資メモ)
- checklist refine (LLM 整形)
で共通利用する。
"""

from __future__ import annotations

import re

NG_WORDS: list[str] = [
    # 投資判断の断定
    "買うべき",
    "売るべき",
    "買い推奨",
    "売り推奨",
    "投資推奨",
    "購入をおすすめ",
    "売却をおすすめ",
    "見送りを推奨",
    "見送るべき",
    # 価値判断
    "お得です",
    "狙い目",
    "割安",
    "おすすめ",
    "推奨",
    # 収益保証・誇張
    "儲かります",
    "儲かる物件",
    "儲かる",
    "絶対に",
    "確実に",
    "確実",
    "保証します",
    "保証できます",
    "保証",
    # 買付・価格判断 (裸の「買い」は買付/買い手/買い増しと衝突するため句で登録)
    "推奨買付価格",
    "買いです",
    "買いだ",
    "買いと判断",
    "購入すべき",
    "見送り推奨",
    # 物件価値の断定・価値判断ラベル
    "この物件は良い",
    "この物件は悪い",
    "健全性スコア",
]

_NG_RE = re.compile("|".join(re.escape(w) for w in NG_WORDS))


def has_ng(text: str) -> bool:
    """text に NG 表現が含まれていれば True (LLM 出力フィルタ用、アグレッシブ)。"""
    return bool(_NG_RE.search(text))


def find_ng(text: str) -> list[str]:
    """text に含まれる NG 表現を抽出 (重複あり、出現順)。"""
    return _NG_RE.findall(text)


# 静的ソース (UI ラベル) 走査用。法務・技術文の正当な「推奨環境」「保証しません」等を
# 誤検出しないよう、投資助言・価値判断として明確な句のみに限定する。
UI_NG_WORDS: list[str] = [
    "買うべき",
    "売るべき",
    "買い推奨",
    "売り推奨",
    "投資推奨",
    "購入をおすすめ",
    "売却をおすすめ",
    "見送りを推奨",
    "見送り推奨",
    "見送るべき",
    "推奨買付価格",
    "買いです",
    "買いだ",
    "買いと判断",
    "購入すべき",
    "おすすめ物件",
    "狙い目",
    "お得です",
    "割安",
    "儲かります",
    "儲かる物件",
    "儲かる",
    "この物件は良い",
    "この物件は悪い",
    "健全性スコア",
]

_UI_NG_RE = re.compile("|".join(re.escape(w) for w in UI_NG_WORDS))


def has_ng_ui(text: str) -> bool:
    """静的 UI ラベルに価値判断/投資助言の断定が含まれていれば True。"""
    return bool(_UI_NG_RE.search(text))


def find_ng_ui(text: str) -> list[str]:
    return _UI_NG_RE.findall(text)
