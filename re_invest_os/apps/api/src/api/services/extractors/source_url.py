"""URL source: 楽待・SUUMO その他から HTML を取得 → 本文抽出。

v1 allowlist:
- rakumachi.jp / www.rakumachi.jp (楽待)
- suumo.jp / www.suumo.jp

設計:
- HTTP GET (User-Agent 明示)
- selectolax で main / article / 主要 div を抽出
- LLM へは「テキスト化済み」を渡す (HTML タグは送らない)
- 業者連絡先ブロック等は PII マスクが面倒なので、抽出前にざっくり捨てる
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from selectolax.parser import HTMLParser

ALLOWED_HOSTS = {
    "rakumachi.jp",
    "www.rakumachi.jp",
    "suumo.jp",
    "www.suumo.jp",
}

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; re-invest-os/0.1; +https://github.com/kazumasa1210/re_invest_os)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.9",
}


class UnsupportedHostError(ValueError):
    pass


@dataclass(frozen=True)
class FetchedPage:
    url: str
    host: str
    title: str | None
    text: str  # メインテキスト (PII マスク前)
    html_length: int


def _check_allowed(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host not in ALLOWED_HOSTS:
        raise UnsupportedHostError(
            f"host '{host}' は許可リストにありません。v1 allowlist: {sorted(ALLOWED_HOSTS)}"
        )
    return host


_SCRIPTS = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_WS = re.compile(r"[ \t]+")
_NEWLINES = re.compile(r"\n{3,}")


def _extract_main_text(html: str) -> tuple[str | None, str]:
    """HTML → (title, main_text)。selectolax で main/article 優先、なければ body 全体。"""
    cleaned = _SCRIPTS.sub("", html)
    tree = HTMLParser(cleaned)

    title_node = tree.css_first("title")
    title = title_node.text(strip=True) if title_node else None

    # サイト別の主要コンテンツセレクタ (優先順)
    main = (
        tree.css_first("main")
        or tree.css_first("article")
        or tree.css_first("#mainContents")  # SUUMO
        or tree.css_first(".l-mainContents")  # SUUMO
        or tree.css_first("#js-bukkenDetail")  # SUUMO 物件詳細
        or tree.body
    )

    if main is None:
        return title, ""

    # 不要 (連絡先/フォーム) を捨てる
    for sel in ("form", "footer", "nav", "iframe", "aside"):
        for node in main.css(sel):
            node.decompose()

    text = main.text(separator="\n", strip=True)
    text = _WS.sub(" ", text)
    text = _NEWLINES.sub("\n\n", text)
    return title, text


def fetch(url: str, *, timeout_s: float = 20.0) -> FetchedPage:
    """allowlist チェック + HTTP GET + 本文抽出。"""
    host = _check_allowed(url)
    with httpx.Client(headers=_DEFAULT_HEADERS, timeout=timeout_s, follow_redirects=True) as cli:
        resp = cli.get(url)
        resp.raise_for_status()
        html = resp.text
    title, text = _extract_main_text(html)
    return FetchedPage(url=url, host=host, title=title, text=text, html_length=len(html))
