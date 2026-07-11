from __future__ import annotations

import csv
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from .utils import ROOT, stable_id

SEARCH_QUERIES = [
    '"WSET Level 3" sample questions',
    '"WSET Level 3" mock exam',
    '"WSET Level 3" short written answer',
    '"WSET Level 3" practice questions PDF',
    '"WSET Level 3" exam questions',
    '"WSET Level 3" study questions',
    '"WSET Level 3" tasting exam practice',
    '"WSET Level 3" 25 mark question',
    '"WSET Level 3" multiple choice questions',
    '"WSET Level 3" quiz',
    '"WSET Level 3" flashcards',
    '"WSET Level 3" questions Japanese',
    "WSET Level 3 練習問題",
    "WSET Level 3 記述式",
    "WSET Level 3 模擬試験",
    "WSET Level 3 問題集",
    "WSET Level 3 テイスティング 試験",
    "WSET Level 3 勉強法 記述",
]


class SearchProvider(Protocol):
    def search(self, query: str) -> list[dict[str, str]]: ...


class GenericSearchAPI:
    """Minimal provider-neutral JSON search adapter.

    The endpoint should accept a `q` parameter and return either a list or a
    `{results: [...]}` object containing title/url/snippet fields.
    """

    def __init__(self, endpoint: str, api_key: str) -> None:
        self.endpoint = endpoint
        self.api_key = api_key

    def search(self, query: str) -> list[dict[str, str]]:
        response = httpx.get(
            self.endpoint,
            params={"q": query},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30,
        )
        response.raise_for_status()
        payload: Any = response.json()
        values = payload.get("results", []) if isinstance(payload, dict) else payload
        return [
            {
                "title": str(item.get("title", "")),
                "url": str(item.get("url", "")),
                "snippet": str(item.get("snippet", "")),
            }
            for item in values
            if isinstance(item, dict) and item.get("url")
        ]


def _candidate_row(query: str, item: dict[str, str] | None = None) -> dict[str, str]:
    item = item or {}
    url = item.get("url", "")
    return {
        "candidate_id": stable_id(query, url, prefix="cand_"),
        "query": query,
        "title": item.get("title", ""),
        "url": url,
        "domain": urlparse(url).netloc,
        "snippet": item.get("snippet", ""),
        "language": "ja" if any("\u3040" <= char <= "\u9fff" for char in query) else "en",
        "likely_source_type": "unknown",
        "discovered_at": datetime.now(UTC).isoformat(),
        "review_status": "unreviewed",
        "review_notes": "",
    }


def discover(output: Path | None = None, use_api: bool = False) -> Path:
    output = output or ROOT / "data" / "exports" / "source_candidates.csv"
    provider: SearchProvider | None = None
    if use_api:
        endpoint = os.getenv("WSET_SEARCH_API_URL")
        api_key = os.getenv("WSET_SEARCH_API_KEY")
        if not endpoint or not api_key:
            raise RuntimeError("WSET_SEARCH_API_URL and WSET_SEARCH_API_KEY are required")
        provider = GenericSearchAPI(endpoint, api_key)

    rows: list[dict[str, str]] = []
    for query in SEARCH_QUERIES:
        results = provider.search(query) if provider else []
        rows.extend(_candidate_row(query, item) for item in results)
        if not results:
            rows.append(_candidate_row(query))

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return output
