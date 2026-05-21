"""
sync_population.py
e-Stat 社会・人口統計体系（市区町村版）から人口・世帯データを取得し
population_stats テーブルに保存する。

使い方:
    python sync_population.py                # 最新年（2023）
    python sync_population.py --year 2020
    python sync_population.py --year 2023 --smoke-test
"""
import argparse
import time

import pandas as pd
import requests

import db
from config import ESTAT_APP_ID, get_logger

logger = get_logger(__name__)

_ESTAT_BASE = "https://api.e-stat.go.jp/rest/3.0/app/json"

# 社会・人口統計体系 市区町村版（国勢調査ベース、年次更新）
_STATS_ID = "0000020101"

# 取得する指標コード（住民基本台帳ベース - 毎年更新）
_CAT01_MAP = {
    "A2301":  "total_population",   # 住民基本台帳人口（総数）
    "A7103":  "households",         # 住民基本台帳世帯数
}

# @time フォーマット: YYYY100000（国勢調査は10月基準）
def _time_code(year: int) -> str:
    return f"{year}100000"


def _fetch_page(stats_id: str, app_id: str, cat01_codes: list[str], time_code: str,
                start: int, limit: int = 10000) -> tuple[list[dict], int]:
    """1ページ分のデータを取得して (VALUES, total_count) を返す。"""
    url = f"{_ESTAT_BASE}/getStatsData"
    params = {
        "appId": app_id,
        "statsDataId": stats_id,
        "cdCat01": ",".join(cat01_codes),
        "cdTime": time_code,
        "limit": limit,
        "startPosition": start,
    }
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    inner = data.get("GET_STATS_DATA", {})
    status = inner.get("RESULT", {}).get("STATUS", -1)
    if status != 0:
        err = inner.get("RESULT", {}).get("ERROR_MSG", "")
        raise RuntimeError(f"e-Stat エラー status={status}: {err}")

    sd = inner["STATISTICAL_DATA"]
    total = int(sd.get("TABLE_INF", {}).get("TOTAL_NUMBER", 0))
    vals = sd.get("DATA_INF", {}).get("VALUE", [])
    return (vals if isinstance(vals, list) else [vals]), total


def fetch_population_stats(year: int, app_id: str) -> pd.DataFrame:
    """指定年の市区町村別人口・世帯データを DataFrame で返す。"""
    time_code = _time_code(year)
    cat01_codes = list(_CAT01_MAP.keys())

    print(f"[e-Stat] {year}年 人口データ取得中 (statsDataId={_STATS_ID}, time={time_code})...")

    all_values: list[dict] = []
    start = 1
    limit = 10000
    total = None

    while True:
        vals, total_count = _fetch_page(_STATS_ID, app_id, cat01_codes, time_code, start, limit)
        all_values.extend(vals)
        if total is None:
            total = total_count
            print(f"  総件数: {total:,}")

        fetched = start + len(vals) - 1
        if not vals or fetched >= total:
            break
        start += limit
        time.sleep(0.3)

    print(f"  → {len(all_values):,} レコード取得")

    if not all_values:
        return pd.DataFrame()

    # pivot: city_code × indicator → 値
    records: dict[str, dict[str, float | None]] = {}
    for v in all_values:
        area = v.get("@area", "")
        cat = v.get("@cat01", "")
        raw = v.get("$", "")

        # 5桁市区町村コードのみ（都道府県集計・全国を除外）
        if not area or len(area) != 5 or area == "00000" or area.endswith("000"):
            continue

        indicator = _CAT01_MAP.get(cat)
        if indicator is None:
            continue

        try:
            val = int(float(raw))
        except (ValueError, TypeError):
            continue

        records.setdefault(area, {"city_code": area})
        records[area][indicator] = val

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(list(records.values()))
    df["survey_year"] = year

    # スキーマに揃える
    df["aging_rate"] = None
    for col in ["pop_change_pct", "households_change_pct", "net_migration"]:
        if col not in df.columns:
            df[col] = None

    print(f"  → 市区町村データ: {len(df):,} 件 ({df['city_code'].nunique():,} 市区町村)")
    return df


def _compute_yoy_changes(conn) -> None:
    """前年比変化率を計算して更新する。"""
    conn.execute(
        """
        UPDATE population_stats AS p
        SET pop_change_pct = (
            SELECT ROUND(
                (p.total_population - prev.total_population) * 100.0
                / NULLIF(prev.total_population, 0), 2
            )
            FROM population_stats prev
            WHERE prev.city_code = p.city_code
              AND prev.survey_year = p.survey_year - 5
        ),
        households_change_pct = (
            SELECT ROUND(
                (p.households - prev.households) * 100.0
                / NULLIF(prev.households, 0), 2
            )
            FROM population_stats prev
            WHERE prev.city_code = p.city_code
              AND prev.survey_year = p.survey_year - 5
        )
        WHERE EXISTS (
            SELECT 1 FROM population_stats prev
            WHERE prev.city_code = p.city_code
              AND prev.survey_year = p.survey_year - 5
        )
        """
    )
    logger.info("前年比変化率（5年比較）を更新しました")


def sync(year: int) -> None:
    app_id = ESTAT_APP_ID
    if not app_id:
        raise EnvironmentError("ESTAT_APP_ID が未設定です。.env を確認してください。")

    df = fetch_population_stats(year, app_id)
    if df.empty:
        print(f"[{year}] データが空のため保存をスキップします。")
        return

    conn = db.get_connection()
    db.create_tables_if_needed(conn)
    n = db.upsert_population_stats(conn, df)
    _compute_yoy_changes(conn)
    conn.close()
    print(f"[{year}] 保存完了: {n:,} 件")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2023, help="調査年（国勢調査年：2015/2020/2023等）")
    parser.add_argument("--smoke-test", action="store_true", help="API接続確認のみ（DB保存なし）")
    args = parser.parse_args()

    if args.smoke_test:
        app_id = ESTAT_APP_ID
        if not app_id:
            raise EnvironmentError("ESTAT_APP_ID が未設定です。")
        df = fetch_population_stats(args.year, app_id)
        print(f"スモークテスト完了: {len(df):,} 件取得")
    else:
        sync(args.year)
