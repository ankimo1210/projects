"""
collect_listings_batch.py
URL リストから掲載物件を一括取り込み、listing_raw / listing_master に保存する。
"""

from __future__ import annotations

import argparse
import hashlib
import time
from collections.abc import Callable
from pathlib import Path

import db
import requests
from config import get_logger
from geocoder import GeocodingError, geocode_address
from property_scraper import (
    ScrapingError,
    extract_property_data,
    extract_source_property_id,
    fetch_property_html,
)

logger = get_logger(__name__)

# 403 バックオフ設定
_BLOCK_BACKOFF_SEC = 25.0  # 403 検知後に待機する秒数 (Cloudflare レート制限ウィンドウ対応)
_BLOCK_WARMUP_SEC = 3.0  # 検索ページ再取得後の追加待機
_MAX_RETRIES = 1  # 403 時のリトライ回数


def run_import(
    url_file: Path, *, region_label: str | None = None, compute_features: bool = False
) -> dict[str, object]:
    urls = [
        line.strip() for line in url_file.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    return run_import_urls(urls, region_label=region_label)


def run_import_urls(urls: list[str], *, region_label: str | None = None) -> dict[str, object]:
    conn = db.get_connection()
    db.create_tables_if_needed(conn)
    result = import_urls_with_connection(conn, urls, region_label=region_label)
    conn.close()
    return result


def _rewarm_session(session: requests.Session, referer: str) -> None:
    """403 後のクールダウン: 検索ページを再取得してクッキーを更新する。"""
    try:
        logger.info("セッション再ウォームアップ: %s", referer)
        session.get(referer, timeout=15)
        time.sleep(_BLOCK_WARMUP_SEC)
    except Exception as exc:
        logger.warning("再ウォームアップ失敗: %s", exc)


def import_urls_with_connection(
    conn,
    urls: list[str],
    *,
    region_label: str | None = None,
    sleep_sec: float = 1.5,
    session: requests.Session | None = None,
    referer: str | None = None,
    progress_cb: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, object]:
    done = 0
    failed = 0
    consecutive_403 = 0
    listing_ids: list[str] = []
    imported_rows: list[dict[str, object]] = []
    total = len(urls)
    batch_start = time.monotonic()
    for idx, url in enumerate(urls, start=1):
        batch_elapsed = time.monotonic() - batch_start
        if progress_cb:
            progress_cb(
                {
                    "stage": "import",
                    "event": "start",
                    "done": done,
                    "failed": failed,
                    "total": total,
                    "url": url,
                    "batch_elapsed_sec": batch_elapsed,
                }
            )
        # 連続 403 が 3 件続いたらバッチ全体を一時停止して再ウォーム
        if consecutive_403 >= 3 and session is not None and referer:
            logger.warning("連続 403 × %d: 60秒バッチ停止後に再試行", consecutive_403)
            time.sleep(60.0)
            _rewarm_session(session, referer)
            consecutive_403 = 0
        url_start = time.monotonic()
        try:
            imported = _import_one_with_retry(
                conn,
                url,
                region_label=region_label,
                session=session,
                referer=referer,
            )
            url_elapsed = time.monotonic() - url_start
            listing_id = str(imported["listing_id"])
            listing_ids.append(listing_id)
            imported_rows.append(imported)
            done += 1
            consecutive_403 = 0
            if progress_cb:
                progress_cb(
                    {
                        "stage": "import",
                        "event": "success",
                        "done": done,
                        "failed": failed,
                        "total": total,
                        "url": url,
                        "listing_id": listing_id,
                        "property_name": imported.get("property_name") or "—",
                        "url_elapsed_sec": url_elapsed,
                        "batch_elapsed_sec": time.monotonic() - batch_start,
                    }
                )
        except Exception as exc:
            url_elapsed = time.monotonic() - url_start
            failed += 1
            error_msg = f"{type(exc).__name__}: {exc}"
            if "403" in error_msg:
                consecutive_403 += 1
            else:
                consecutive_403 = 0
            logger.warning("取込失敗 [%s] %s", url, error_msg)
            if progress_cb:
                progress_cb(
                    {
                        "stage": "import",
                        "event": "failed",
                        "done": done,
                        "failed": failed,
                        "total": total,
                        "url": url,
                        "error": error_msg,
                        "url_elapsed_sec": url_elapsed,
                        "batch_elapsed_sec": time.monotonic() - batch_start,
                    }
                )
        if idx < total and sleep_sec > 0:
            time.sleep(sleep_sec)
    return {
        "done": done,
        "failed": failed,
        "listing_ids": listing_ids,
        "imported_rows": imported_rows,
    }


def _import_one_with_retry(
    conn,
    url: str,
    *,
    region_label: str | None = None,
    session: requests.Session | None = None,
    referer: str | None = None,
) -> dict[str, object]:
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return _import_one(
                conn, url, region_label=region_label, session=session, referer=referer
            )
        except ScrapingError as exc:
            is_blocked = "403" in str(exc)
            if is_blocked and attempt < _MAX_RETRIES and session is not None and referer:
                logger.warning(
                    "403 検知 (attempt %d/%d)。%s秒待機後リトライ: %s",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    _BLOCK_BACKOFF_SEC,
                    url,
                )
                time.sleep(_BLOCK_BACKOFF_SEC)
                _rewarm_session(session, referer)
            else:
                raise


def _import_one(
    conn,
    url: str,
    *,
    region_label: str | None = None,
    session: requests.Session | None = None,
    referer: str | None = None,
) -> dict[str, object]:
    html = fetch_property_html(url, session=session, referer=referer)
    html_hash = hashlib.sha1(html.encode("utf-8")).hexdigest()
    prop = extract_property_data(html, url)

    source = prop.platform or "unknown"
    source_property_id = extract_source_property_id(url)
    raw_id = f"{source}:{source_property_id or html_hash[:16]}"
    db.upsert_listing_raw(
        conn,
        {
            "raw_id": raw_id,
            "source": source,
            "source_property_id": source_property_id,
            "source_url": url,
            "region_label": region_label,
            "html_hash": html_hash,
            "html_text": html,
            "extraction_json": prop.raw_extraction,
            "status": "fetched",
            "error_message": None,
        },
    )

    city_code = None
    lat = None
    lon = None
    if prop.address:
        try:
            geo = geocode_address(prop.address)
            city_code = geo.city_code
            lat = round(float(geo.lat), 5)
            lon = round(float(geo.lon), 5)
        except GeocodingError:
            pass

    listing_id = (
        f"{source}:{source_property_id or hashlib.sha1(url.encode('utf-8')).hexdigest()[:16]}"
    )
    db.upsert_listing_master(
        conn,
        {
            "listing_id": listing_id,
            "source": source,
            "source_property_id": source_property_id,
            "source_url": url,
            "region_label": region_label,
            "property_name": prop.property_name,
            "address": prop.address,
            "city_code": city_code,
            "lat": lat,
            "lon": lon,
            "asking_price_yen": prop.asking_price_yen,
            "gross_rent_monthly_yen": prop.gross_rent_monthly_yen,
            "gross_rent_annual_yen": prop.gross_rent_annual_yen,
            "gross_yield_pct": prop.gross_yield_pct,
            "build_year_month": prop.build_year_month,
            "age_years": prop.age_years,
            "structure": prop.structure,
            "property_type": prop.property_type,
            "building_area_sqm": prop.building_area_sqm,
            "land_area_sqm": prop.land_area_sqm,
            "land_rights": prop.land_rights,
            "legal_far_pct": prop.legal_far_pct,
            "bcr_pct": prop.bcr_pct,
            "num_units": prop.num_units,
            "road_frontage": prop.road_frontage,
            "nearest_station": prop.nearest_station,
            "station_walk_min": prop.station_walk_min,
            "floor_plan": prop.floor_plan,
            "num_floors": prop.num_floors,
            "land_category": prop.land_category,
            "city_planning_area": prop.city_planning_area,
            "updated_date": prop.updated_date,
            "transaction_type": prop.transaction_type,
            "listing_date": prop.listing_date,
            "platform": prop.platform,
            "extraction_confidence": prop.extraction_confidence,
            "raw_extraction_json": prop.raw_extraction,
            "llm_filled_fields_json": sorted(prop.llm_filled_fields),
        },
    )
    return {
        "listing_id": listing_id,
        "property_name": prop.property_name,
        "url": url,
        "source": source,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url_file", type=Path)
    parser.add_argument("--region-label", default=None)
    args = parser.parse_args()
    print(run_import(args.url_file, region_label=args.region_label))


if __name__ == "__main__":
    main()
