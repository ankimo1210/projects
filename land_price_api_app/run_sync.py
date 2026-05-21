"""
run_sync.py
主要7都府県 × 直近3年分を並列取得してDuckDBに保存する。
"""

import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
_ROOT = Path(__file__).parent
os.chdir(_ROOT)
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import db
import pandas as pd
import sync_public_notice as sync
from config import PROCESSED_DIR

TARGET_PREFS = ["47", "13", "14", "27", "01", "23", "40"]
TARGET_YEARS = [2024, 2025, 2026]

PREF_NAMES = {
    "01": "北海道",
    "13": "東京都",
    "14": "神奈川県",
    "23": "愛知県",
    "27": "大阪府",
    "40": "福岡県",
    "47": "沖縄県",
}

TILE_WORKERS = 4
PREF_WORKERS = 3
processed_dir = PROCESSED_DIR

# DB接続
conn = db.get_connection()
db.create_tables_if_needed(conn)
stats = db.get_stats(conn)
print(f"DB接続OK: {stats['total_records']:,} レコード / 年度: {stats['available_years']}")

# Phase 1: 並列取得 (Parquetのみ保存)
_log_lock = threading.Lock()
results: dict[tuple, int] = {}


def _sync_one(pref: str, year: int) -> tuple:
    t0 = time.time()
    try:
        df = sync.sync_public_notice_year(
            year=year,
            z=13,
            overwrite=True,
            prefecture_code=pref,
            conn=None,
            max_workers=TILE_WORKERS,
            skip_db_write=True,
        )
        elapsed = time.time() - t0
        cnt = len(df) if df is not None and not df.empty else 0
        with _log_lock:
            mark = "✓" if cnt > 0 else "⚠"
            print(
                f"  {mark} {PREF_NAMES.get(pref, pref)} ({pref}) {year}年: {cnt:,} 件  {elapsed:.0f}秒",
                flush=True,
            )
        return pref, year, cnt, None
    except Exception as exc:
        elapsed = time.time() - t0
        with _log_lock:
            print(
                f"  ✗ {PREF_NAMES.get(pref, pref)} ({pref}) {year}年: エラー: {exc}  {elapsed:.0f}秒",
                flush=True,
            )
        return pref, year, 0, exc


total_start = time.time()
tasks = [(p, y) for p in TARGET_PREFS for y in TARGET_YEARS]
print("\n=== Phase 1: 並列取得 ===")
print(f"開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"対象: {len(TARGET_PREFS)} 都府県 × {len(TARGET_YEARS)} 年 = {len(tasks)} タスク")
print(f"並列設定: TILE_WORKERS={TILE_WORKERS}, PREF_WORKERS={PREF_WORKERS}\n", flush=True)

with ThreadPoolExecutor(max_workers=PREF_WORKERS) as executor:
    futures = {executor.submit(_sync_one, p, y): (p, y) for p, y in tasks}
    for fut in as_completed(futures):
        pref, year, cnt, exc = fut.result()
        results[(pref, year)] = cnt if exc is None else -1

phase1_elapsed = time.time() - total_start
print(f"\nPhase 1 完了: {phase1_elapsed:.0f}秒 ({phase1_elapsed / 60:.1f}分)", flush=True)

# Phase 2: Parquet → DuckDB 一括インポート
print("\n=== Phase 2: DB インポート ===", flush=True)
imported_total = 0
for pref in TARGET_PREFS:
    for year in TARGET_YEARS:
        p = processed_dir / f"land_prices_y{year}_pref{pref}_pc0.parquet"
        if p.exists():
            df_p = pd.read_parquet(p)
            if not df_p.empty:
                n = db.upsert_land_prices(conn, df_p)
                imported_total += n
                print(
                    f"  ✓ {PREF_NAMES.get(pref, pref)} {year}年: {len(df_p):,} 件 → DB", flush=True
                )
        else:
            print(f"  ⚠ {PREF_NAMES.get(pref, pref)} {year}年: Parquetなし", flush=True)

conn.close()

total_elapsed = time.time() - total_start
print(f"\n合計インポート: {imported_total:,} 件")
print(f"総所要時間: {total_elapsed:.0f}秒 ({total_elapsed / 60:.1f}分)")
print(f"終了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

print("\n=== 結果サマリー ===")
for pref in TARGET_PREFS:
    for year in TARGET_YEARS:
        cnt = results.get((pref, year), -1)
        mark = "✓" if cnt > 0 else ("⚠" if cnt == 0 else "✗")
        label = f"{cnt:,} 件" if cnt >= 0 else "エラー"
        print(f"  {mark} {PREF_NAMES.get(pref, pref)} ({pref}) {year}年: {label}")
