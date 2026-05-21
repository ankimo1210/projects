"""
geocode_trade_prices.py
trade_prices テーブルの lat/lon が NULL のレコードを
国土地理院API でジオコーディングして一括更新するバッチ。

使い方（CLI）:
    python geocode_trade_prices.py --limit 1000 --sleep 0.3

Admin タブからも呼び出せるよう run_geocoding() を公開している。
"""
import argparse
import time
from typing import Callable, Optional

import duckdb

import db
from config import DUCKDB_PATH, get_logger
from geocoder import GeocodingError, geocode_address

logger = get_logger(__name__)


def run_geocoding(
    limit: int = 1000,
    sleep_sec: float = 0.3,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> dict:
    """
    未ジオコーディングの (city_name, district_name) を処理して DB を更新する。

    Parameters
    ----------
    limit       : 処理する最大ユニーク地点数
    sleep_sec   : API 呼び出し間隔（秒）
    progress_cb : (done, total, message) を受け取るコールバック

    Returns
    -------
    {"done": int, "updated": int, "failed": int}
    """
    conn = duckdb.connect(str(DUCKDB_PATH))

    locations = db.get_trade_ungeocoded_locations(conn, limit=limit)
    total = len(locations)
    logger.info("未ジオコーディング地点: %d 件", total)

    done = 0
    failed = 0
    updates: list[dict] = []

    for _, row in locations.iterrows():
        city     = row["city_name"] or ""
        district = row.get("district_name") or ""
        pref     = row.get("prefecture_name") or ""

        # 住所文字列を組み立てる（都道府県 + 市区町村 + 地区）
        address_parts = [p for p in [pref, city, district] if p]
        address = "".join(address_parts)

        try:
            geo = geocode_address(address)
            updates.append({
                "prefecture_name": pref,
                "city_name":     city,
                "district_name": district or None,
                "lat":           geo.lat,
                "lon":           geo.lon,
            })
            done += 1
        except GeocodingError as e:
            logger.debug("ジオコーディング失敗: %s → %s", address, e)
            failed += 1

        if progress_cb:
            progress_cb(done + failed, total, address)

        time.sleep(sleep_sec)

        # 100件ごとにDBへコミット
        if len(updates) >= 100:
            db.update_trade_latlon(conn, updates)
            updates.clear()

    # 残りをコミット
    if updates:
        db.update_trade_latlon(conn, updates)

    conn.close()
    logger.info("ジオコーディング完了: 成功=%d 失敗=%d", done, failed)
    return {"done": done, "updated": done, "failed": failed}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",  type=int,   default=1000,  help="処理する最大件数")
    parser.add_argument("--sleep",  type=float, default=0.3,   help="API呼び出し間隔（秒）")
    args = parser.parse_args()

    result = run_geocoding(limit=args.limit, sleep_sec=args.sleep)
    print(f"完了: 成功={result['done']} 失敗={result['failed']}")
