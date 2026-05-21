"""
sync_rent_market.py
e-Stat API から住宅・土地統計調査の「延べ面積1m²当たり家賃」を取得し
rent_market テーブルに保存する。

使い方:
    python sync_rent_market.py           # 2023年（最新）のみ
    python sync_rent_market.py --year 2018
"""

import argparse

import db
import pandas as pd
import requests
from config import ESTAT_APP_ID, get_logger

logger = get_logger(__name__)

_ESTAT_BASE = "https://api.e-stat.go.jp/rest/3.0/app/json"

# 統計表ID: 所有の関係(4区分)別 延べ面積1m²当たり家賃 — 全国・都道府県・市区町村
_STATS_ID: dict[int, str] = {
    2023: "0004021492",
    2018: "0003356459",  # 2018年版の市区町村別家賃テーブル
}

# cat01 所有関係コード → 名称
_OWNERSHIP: dict[str, str] = {
    "0": "total",
    "1": "public",
    "2": "kiko",
    "3": "private",
    "4": "company",
}


def _fetch_estat(stats_id: str, app_id: str) -> list[dict]:
    """e-Stat getStatsData を全件取得して VALUE リストを返す。"""
    url = f"{_ESTAT_BASE}/getStatsData"
    params = {
        "appId": app_id,
        "statsDataId": stats_id,
        "limit": 100000,
    }
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    try:
        values = data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
    except KeyError as e:
        raise RuntimeError(f"e-Stat レスポンス構造が予期しない形式です: {e}") from e

    return values if isinstance(values, list) else [values]


def fetch_rent_market(year: int, app_id: str) -> pd.DataFrame:
    """指定年の賃貸相場データを DataFrame で返す。"""
    stats_id = _STATS_ID.get(year)
    if not stats_id:
        raise ValueError(f"未対応の調査年: {year}。対応年: {list(_STATS_ID)}")

    print(f"[e-Stat] {year}年データ取得中 (statsDataId={stats_id})...")
    values = _fetch_estat(stats_id, app_id)
    print(f"  → {len(values)} 件取得")

    records = []
    for v in values:
        area = v.get("@area", "")
        cat01 = v.get("@cat01", "")
        raw_val = v.get("$", "")

        # 市区町村コードは5桁。00000=全国、末尾000=都道府県集計なので除外。
        if not area or len(area) != 5 or area == "00000" or area.endswith("000"):
            continue
        # 数値以外（"-", "***" など）はスキップ
        try:
            rent = float(raw_val)
        except (ValueError, TypeError):
            continue

        ownership = _OWNERSHIP.get(str(cat01))
        if ownership is None:
            continue

        records.append(
            {
                "city_code": area,
                "survey_year": year,
                "ownership_type": ownership,
                "rent_per_sqm": rent,
            }
        )

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.groupby(["city_code", "survey_year", "ownership_type"], as_index=False)[
            "rent_per_sqm"
        ].mean()
    print(f"  → 市区町村データ: {len(df)} 件（{df['city_code'].nunique()} 市区町村）")
    return df


def sync(year: int) -> None:
    app_id = ESTAT_APP_ID
    if not app_id:
        raise OSError("ESTAT_APP_ID が未設定です。.env を確認してください。")

    df = fetch_rent_market(year, app_id)
    if df.empty:
        print(f"[{year}] データが空のため保存をスキップします。")
        return

    conn = db.get_connection()
    db.create_tables_if_needed(conn)
    n = db.upsert_rent_market(conn, df)
    conn.close()
    print(f"[{year}] 保存完了: {n} 件")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, choices=list(_STATS_ID), default=2023)
    args = parser.parse_args()
    sync(args.year)
