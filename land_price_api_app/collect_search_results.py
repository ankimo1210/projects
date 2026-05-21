"""
collect_search_results.py
検索結果URLから掲載物件詳細URLを収集し、既存の取込パイプラインへ流す。
"""

from __future__ import annotations

import argparse
import hashlib
import time
from collections.abc import Callable
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit

import db
import requests
from bs4 import BeautifulSoup
from collect_listings_batch import import_urls_with_connection
from config import get_logger
from recompute_listing_features import run_recompute

logger = get_logger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class SearchResultCollectionError(Exception):
    pass


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(_HEADERS)
    return session


def fetch_search_result_html(
    url: str, timeout: int = 15, session: requests.Session | None = None
) -> str:
    if session is None:
        session = _make_session()
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
    except requests.exceptions.RequestException as exc:
        raise SearchResultCollectionError(f"検索結果ページ取得失敗: {exc}") from exc
    if resp.status_code == 403:
        raise SearchResultCollectionError("検索結果ページで 403 が返りました。")
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        raise SearchResultCollectionError(f"検索結果ページ HTTP {resp.status_code}: {exc}") from exc
    return resp.text


def normalize_detail_url(base_url: str, href: str) -> str | None:
    absolute = urljoin(base_url, href)
    parsed = urlsplit(absolute)
    if "rakumachi.jp" not in parsed.netloc:
        return None
    if "/syuuekibukken/" not in parsed.path or not parsed.path.endswith("/show.html"):
        return None
    return urlunsplit((parsed.scheme or "https", parsed.netloc, parsed.path, "", ""))


def extract_rakumachi_listing_urls(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    seen: set[str] = set()

    for anchor in soup.select("a[href]"):
        normalized = normalize_detail_url(base_url, anchor.get("href", ""))
        if normalized and normalized not in seen:
            seen.add(normalized)
            urls.append(normalized)
    return urls


def _normalized_search_url(base_url: str, href: str) -> str | None:
    absolute = urljoin(base_url, href)
    parsed = urlsplit(absolute)
    base_parsed = urlsplit(base_url)
    if "rakumachi.jp" not in parsed.netloc:
        return None
    if parsed.path != base_parsed.path:
        return None
    if normalize_detail_url(base_url, href):
        return None
    return urlunsplit((parsed.scheme or "https", parsed.netloc, parsed.path, parsed.query, ""))


def extract_rakumachi_next_page_url(html: str, current_url: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    current_page = int(parse_qs(urlsplit(current_url).query).get("page", ["1"])[0] or "1")

    for anchor in soup.select("a[rel='next'][href]"):
        candidate = _normalized_search_url(current_url, anchor.get("href", ""))
        if candidate:
            return candidate

    candidates: list[tuple[int, str]] = []
    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "")
        candidate = _normalized_search_url(current_url, href)
        if not candidate:
            continue
        text = anchor.get_text(" ", strip=True)
        page = int(parse_qs(urlsplit(candidate).query).get("page", ["0"])[0] or "0")
        if page > current_page:
            candidates.append((page, candidate))
            continue
        if any(token in text for token in ("次へ", "次の", "›", "≫", ">")):
            candidates.append((current_page + 1, candidate))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def collect_rakumachi_search_result_urls(
    search_url: str,
    *,
    max_pages: int = 3,
    max_listings: int = 60,
    sleep_sec: float = 0.5,
    progress_cb: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, object]:
    session = _make_session()
    current_url = search_url
    visited_pages: list[str] = []
    collected_urls: list[str] = []
    collected_rows: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    seen_pages: set[str] = set()
    page_no = 1

    while current_url and len(visited_pages) < max_pages and len(collected_urls) < max_listings:
        if current_url in seen_pages:
            break
        seen_pages.add(current_url)
        visited_pages.append(current_url)
        if progress_cb:
            progress_cb(
                {
                    "stage": "collect",
                    "event": "page_start",
                    "page_no": page_no,
                    "max_pages": max_pages,
                    "current_url": current_url,
                    "collected_urls": len(collected_urls),
                    "max_listings": max_listings,
                }
            )
        html = fetch_search_result_html(current_url, session=session)
        page_urls = extract_rakumachi_listing_urls(html, current_url)
        page_new = 0
        for position, detail_url in enumerate(page_urls, start=1):
            if detail_url in seen_urls:
                continue
            seen_urls.add(detail_url)
            collected_urls.append(detail_url)
            page_new += 1
            collected_rows.append(
                {
                    "detail_url": detail_url,
                    "page_no": page_no,
                    "position": position,
                }
            )
            if len(collected_urls) >= max_listings:
                break
        if progress_cb:
            progress_cb(
                {
                    "stage": "collect",
                    "event": "page_done",
                    "page_no": page_no,
                    "max_pages": max_pages,
                    "current_url": current_url,
                    "page_new": page_new,
                    "collected_urls": len(collected_urls),
                    "max_listings": max_listings,
                }
            )
        if len(collected_urls) >= max_listings:
            break
        next_url = extract_rakumachi_next_page_url(html, current_url)
        if not next_url:
            break
        current_url = next_url
        page_no += 1
        if sleep_sec > 0:
            time.sleep(float(sleep_sec))

    return {
        "visited_pages": visited_pages,
        "detail_urls": collected_urls,
        "detail_rows": collected_rows,
        "session": session,
    }


def run_search_import(
    search_url: str,
    *,
    region_label: str | None = None,
    max_pages: int = 3,
    max_listings: int = 60,
    sleep_sec: float = 0.5,
    compute_features: bool = True,
    progress_cb: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, object]:
    if "rakumachi.jp" not in search_url:
        raise SearchResultCollectionError("現時点では楽待の検索結果URLのみ対応しています。")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    job_id = f"rakumachi_search:{hashlib.sha1((search_url + timestamp).encode('utf-8')).hexdigest()[:16]}"
    conn = db.get_connection()
    db.create_tables_if_needed(conn)
    db.upsert_search_job(
        conn,
        {
            "job_id": job_id,
            "source": "rakumachi",
            "search_url": search_url,
            "region_label": region_label,
            "status": "running",
            "max_pages": max_pages,
            "max_listings": max_listings,
            "started_at": datetime.now(),
            "finished_at": None,
        },
    )

    try:
        collected = collect_rakumachi_search_result_urls(
            search_url,
            max_pages=max_pages,
            max_listings=max_listings,
            sleep_sec=sleep_sec,
            progress_cb=progress_cb,
        )
        detail_urls = collected["detail_urls"]
        detail_rows = [{"job_id": job_id, **row} for row in collected["detail_rows"]]
        db.replace_search_job_urls(conn, job_id, detail_rows)

        if progress_cb:
            progress_cb(
                {
                    "stage": "import",
                    "event": "phase_start",
                    "total": len(detail_urls),
                }
            )
        import_result = import_urls_with_connection(
            conn,
            detail_urls,
            region_label=region_label,
            sleep_sec=sleep_sec,
            session=collected.get("session"),
            referer=search_url,
            progress_cb=progress_cb,
        )
        feature_result = {"done": 0, "failed": 0}
        listing_ids = list(import_result.get("listing_ids", []))
        if compute_features and listing_ids:
            conn.close()
            conn = None
            if progress_cb:
                progress_cb(
                    {
                        "stage": "features",
                        "event": "phase_start",
                        "total": len(listing_ids),
                    }
                )
            feature_result = run_recompute(
                listing_ids=listing_ids,
                stale_days=0,
                sleep_sec=0.0,
                progress_cb=lambda done, total, listing_id: (
                    progress_cb(
                        {
                            "stage": "features",
                            "event": "progress",
                            "done": done,
                            "total": total,
                            "listing_id": listing_id,
                        }
                    )
                    if progress_cb
                    else None
                ),
            )
            conn = db.get_connection()
            db.create_tables_if_needed(conn)

        db.upsert_search_job(
            conn,
            {
                "job_id": job_id,
                "source": "rakumachi",
                "search_url": search_url,
                "region_label": region_label,
                "status": "completed",
                "max_pages": max_pages,
                "max_listings": max_listings,
                "collected_pages": len(collected["visited_pages"]),
                "collected_urls": len(detail_urls),
                "imported_done": int(import_result["done"]),
                "imported_failed": int(import_result["failed"]),
                "feature_done": int(feature_result["done"]),
                "feature_failed": int(feature_result["failed"]),
                "error_message": None,
                "finished_at": datetime.now(),
            },
        )
        return {
            "job_id": job_id,
            "pages": len(collected["visited_pages"]),
            "collected_urls": len(detail_urls),
            "imported_done": int(import_result["done"]),
            "imported_failed": int(import_result["failed"]),
            "feature_done": int(feature_result["done"]),
            "feature_failed": int(feature_result["failed"]),
            "detail_urls": detail_urls,
        }
    except Exception as exc:
        if conn is None:
            conn = db.get_connection()
            db.create_tables_if_needed(conn)
        db.upsert_search_job(
            conn,
            {
                "job_id": job_id,
                "source": "rakumachi",
                "search_url": search_url,
                "region_label": region_label,
                "status": "failed",
                "max_pages": max_pages,
                "max_listings": max_listings,
                "error_message": str(exc),
                "finished_at": datetime.now(),
            },
        )
        raise
    finally:
        if conn is not None:
            conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--search-url", required=True)
    parser.add_argument("--region-label", default=None)
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--max-listings", type=int, default=60)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--no-features", action="store_true")
    args = parser.parse_args()
    result = run_search_import(
        args.search_url,
        region_label=args.region_label,
        max_pages=args.max_pages,
        max_listings=args.max_listings,
        sleep_sec=args.sleep,
        compute_features=not args.no_features,
    )
    print(result)


if __name__ == "__main__":
    main()
