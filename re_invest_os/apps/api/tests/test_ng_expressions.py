"""NG 表現エンフォースメント。

- NG 語彙が新フレーズを検出すること。
- 正当な「買付/買い手」系を誤検出しないこと。
- ユーザー表示面 (web UI ラベル) に NG 表現が無いこと。

注: docs/prompts は LLM への「禁止語を使うな」という指示で禁止語自体を含むため、
このソース走査の対象外。LLM 実出力の NG は summarizer のランタイム has_ng で担保する。
"""

from __future__ import annotations

from pathlib import Path

from api.constants import DISCLAIMERS
from api.services.ng_filter import find_ng_ui, has_ng, has_ng_ui

_REPO = Path(__file__).resolve().parents[3]  # re_invest_os/


def test_ng_detects_new_phrases() -> None:
    assert has_ng("推奨買付価格は3300万円です")
    assert has_ng("この物件は良いです")
    assert has_ng("購入すべきです")
    assert has_ng("見送り推奨")
    assert has_ng("健全性スコア")


def test_ng_allows_legitimate_buy_terms() -> None:
    # 裸の「買い」は誤検出しない (買付/買い手/買い増しは正当)
    assert not has_ng("買い手側のDDツール")
    assert not has_ng("買付前の収支耐性を検証")
    assert not has_ng("買い増しの検討")


def test_disclaimers_have_no_value_judgment() -> None:
    # 免責文は 推奨/購入 を正当に含むが、価値判断の断定は含まない。
    for d in DISCLAIMERS.values():
        assert "この物件は良い" not in d
        assert "この物件は悪い" not in d


def test_ui_surfaces_have_no_ng() -> None:
    disclaimer_texts = set(DISCLAIMERS.values())
    root = _REPO / "apps/web/src"
    offenders: list[str] = []
    for path in list(root.rglob("*.tsx")) + list(root.rglob("*.ts")):
        if "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for d in disclaimer_texts:
            text = text.replace(d, "")
        if has_ng_ui(text):
            offenders.append(f"{path.relative_to(_REPO)}: {find_ng_ui(text)}")
    assert not offenders, "NG expressions found in UI:\n" + "\n".join(offenders)
