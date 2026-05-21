"""
sync_suumo_rent_market.py
SUUMO 家賃相場ページから都道府県別の市区郡・間取り別賃料目安を取得する。

まずは相場ページ単位の低頻度取得に限定する。物件詳細の大量巡回は行わない。
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import date
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

import db


_PREFS: dict[str, tuple[str, str]] = {
    "hokkaido_": ("01", "北海道"),
    "aomori": ("02", "青森県"),
    "iwate": ("03", "岩手県"),
    "miyagi": ("04", "宮城県"),
    "akita": ("05", "秋田県"),
    "yamagata": ("06", "山形県"),
    "fukushima": ("07", "福島県"),
    "ibaraki": ("08", "茨城県"),
    "tochigi": ("09", "栃木県"),
    "gumma": ("10", "群馬県"),
    "saitama": ("11", "埼玉県"),
    "chiba": ("12", "千葉県"),
    "tokyo": ("13", "東京都"),
    "kanagawa": ("14", "神奈川県"),
    "niigata": ("15", "新潟県"),
    "toyama": ("16", "富山県"),
    "ishikawa": ("17", "石川県"),
    "fukui": ("18", "福井県"),
    "yamanashi": ("19", "山梨県"),
    "nagano": ("20", "長野県"),
    "gifu": ("21", "岐阜県"),
    "shizuoka": ("22", "静岡県"),
    "aichi": ("23", "愛知県"),
    "mie": ("24", "三重県"),
    "shiga": ("25", "滋賀県"),
    "kyoto": ("26", "京都府"),
    "osaka": ("27", "大阪府"),
    "hyogo": ("28", "兵庫県"),
    "nara": ("29", "奈良県"),
    "wakayama": ("30", "和歌山県"),
    "tottori": ("31", "鳥取県"),
    "shimane": ("32", "島根県"),
    "okayama": ("33", "岡山県"),
    "hiroshima": ("34", "広島県"),
    "yamaguchi": ("35", "山口県"),
    "tokushima": ("36", "徳島県"),
    "kagawa": ("37", "香川県"),
    "ehime": ("38", "愛媛県"),
    "kochi": ("39", "高知県"),
    "fukuoka": ("40", "福岡県"),
    "saga": ("41", "佐賀県"),
    "nagasaki": ("42", "長崎県"),
    "kumamoto": ("43", "熊本県"),
    "oita": ("44", "大分県"),
    "miyazaki": ("45", "宮崎県"),
    "kagoshima": ("46", "鹿児島県"),
    "okinawa": ("47", "沖縄県"),
}

_PROPERTY_TYPE_LABELS = {
    "mansion": "マンション",
    "apartment": "アパート",
    "ikkodate": "一戸建て・その他",
}


def fetch_suumo_prefecture_rents(prefecture_slug: str) -> pd.DataFrame:
    pref_code, pref_name = _PREFS[prefecture_slug]
    source_url = f"https://suumo.jp/chintai/soba/{prefecture_slug}/"
    html = _fetch_html(source_url)
    soup = BeautifulSoup(html, "html.parser")
    payload = _extract_sort_matrix_payload(soup)
    updated_date = _extract_updated_date(soup.get_text("\n"))

    rows: list[dict[str, Any]] = []
    for property_type, city_map in payload.items():
        property_type_label = _PROPERTY_TYPE_LABELS.get(property_type, property_type)
        if not isinstance(city_map, dict):
            continue
        for city_payload in city_map.values():
            if not isinstance(city_payload, dict):
                continue
            city_name = str(city_payload.get("name") or "").strip()
            if not city_name:
                continue
            for item in city_payload.get("data") or []:
                floor_plan = str(item.get("name") or "").strip()
                rent_man = _num(item.get("val"))
                if not floor_plan or rent_man is None:
                    continue
                rows.append(
                    {
                        "source": "suumo",
                        "prefecture_slug": prefecture_slug,
                        "prefecture_code": pref_code,
                        "prefecture_name": pref_name,
                        "city_name": city_name,
                        "property_type": property_type,
                        "property_type_label": property_type_label,
                        "floor_plan_bucket": floor_plan,
                        "monthly_rent_yen": rent_man * 10_000,
                        "updated_date": updated_date,
                        "source_url": source_url,
                    }
                )

    return pd.DataFrame(rows)


def _fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; local-rent-research/0.1; +https://localhost)",
        "Accept-Language": "ja,en;q=0.8",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def _extract_sort_matrix_payload(soup: BeautifulSoup) -> dict[str, Any]:
    tag = soup.find("script", id="js-sortMatrix-data")
    if tag is None or not tag.string:
        raise RuntimeError("SUUMO相場データJSONが見つかりませんでした。")
    return json.loads(tag.string)


def _extract_updated_date(text: str) -> date | None:
    match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日更新", text)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    return date(year, month, day)


def _num(value) -> float | None:
    if value in (None, "-", ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def sync(prefecture_slug: str) -> int:
    if prefecture_slug not in _PREFS:
        raise ValueError(f"未対応の都道府県: {prefecture_slug}. 対応: {', '.join(_PREFS)}")
    df = fetch_suumo_prefecture_rents(prefecture_slug)
    conn = db.get_connection()
    try:
        n = db.upsert_suumo_rent_market(conn, df, prefecture_slug=prefecture_slug)
    finally:
        conn.close()
    print(f"[SUUMO] {prefecture_slug}: {n} 件保存")
    return n


def sync_many(prefecture_slugs: list[str], *, sleep_sec: float = 1.0) -> None:
    total = 0
    failures: list[tuple[str, str]] = []
    for i, slug in enumerate(prefecture_slugs, start=1):
        try:
            print(f"[{i}/{len(prefecture_slugs)}] {slug} 取得中...")
            total += sync(slug)
        except Exception as exc:
            failures.append((slug, str(exc)))
            print(f"[SUUMO] {slug}: 失敗: {exc}")
        if i < len(prefecture_slugs):
            time.sleep(max(0.0, sleep_sec))
    print(f"[SUUMO] 合計保存: {total} 件")
    if failures:
        print("[SUUMO] 失敗:")
        for slug, message in failures:
            print(f"  - {slug}: {message}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pref", choices=["all", *sorted(_PREFS)], default="okinawa")
    parser.add_argument("--sleep", type=float, default=1.0, help="都道府県ごとの待機秒数")
    args = parser.parse_args()
    if args.pref == "all":
        sync_many(list(_PREFS.keys()), sleep_sec=args.sleep)
    else:
        sync(args.pref)
