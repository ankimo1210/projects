"""
run_backfill.py
DB クリア → 既存 Parquet 再インポート → 過去データ取得。

使い方:
    python run_backfill.py                        # 2010-2026 全取得（DB クリア）
    python run_backfill.py --from 2000 --to 2009  # 2000-2009 追加取得（DB クリアなし）
    python run_backfill.py --no-clear             # DB クリアをスキップして追記
    python run_backfill.py --skip-fetch           # 取得スキップ、Parquet→DB インポートのみ
"""
import argparse
import os
import sys
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_ROOT = Path(__file__).parent
os.chdir(_ROOT)
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd
import sync_public_notice as sync
import db
from config import PROCESSED_DIR

# ── 設定 ─────────────────────────────────────────────────────────────────────
TARGET_PREFS = ["47", "13", "14", "27", "01", "23", "40"]
PREF_NAMES = {
    "01": "北海道", "13": "東京都", "14": "神奈川県",
    "23": "愛知県", "27": "大阪府", "40": "福岡県", "47": "沖縄県",
}
TILE_WORKERS = 8
PREF_WORKERS = 5
processed_dir = PROCESSED_DIR

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="year_from", type=int, default=2010)
    p.add_argument("--to",   dest="year_to",   type=int, default=2026)
    p.add_argument("--skip-fetch", action="store_true", help="API取得をスキップしParquet→DBインポートのみ")
    p.add_argument("--no-clear", action="store_true", help="DB クリアをスキップして既存データに追記する")
    return p.parse_args()

def clear_and_reimport(conn, reimport_years, skip_clear=False):
    """DB を全削除して指定年の既存 Parquet を再インポートする。"""
    if not skip_clear:
        print("=== DB クリア ===")
        before = conn.execute("SELECT COUNT(*) FROM land_prices_public_notice").fetchone()[0]
        conn.execute("DELETE FROM land_prices_public_notice")
        conn.commit()
        print(f"  削除完了: {before:,} 件")

    print("\n=== 既存 Parquet → DB 再インポート ===")
    total = 0
    for year in reimport_years:
        for pref in TARGET_PREFS:
            p = processed_dir / f"land_prices_y{year}_pref{pref}_pc0.parquet"
            if p.exists():
                df = pd.read_parquet(p)
                if not df.empty:
                    n = db.upsert_land_prices(conn, df)
                    total += n
                    print(f"  ✓ {PREF_NAMES.get(pref,pref)} {year}年: {len(df):,} 件", flush=True)
    print(f"  再インポート計: {total:,} 件\n")
    return total

def fetch_years(conn, years_to_fetch):
    """指定年度リストを並列取得してDBにインポートする（Parquet既存はスキップ）。"""
    _log_lock = threading.Lock()
    results: dict[tuple, int] = {}

    def _sync_one(pref, year):
        parquet = processed_dir / f"land_prices_y{year}_pref{pref}_pc0.parquet"
        # 既存 Parquet があればスキップ（再開可能）
        if parquet.exists():
            df_ex = pd.read_parquet(parquet)
            cnt = len(df_ex)
            if cnt > 0:
                with _log_lock:
                    print(f"  → {PREF_NAMES.get(pref,pref)} {year}年: スキップ（Parquet既存 {cnt:,}件）", flush=True)
                return pref, year, cnt, None

        t0 = time.time()
        try:
            df = sync.sync_public_notice_year(
                year=year, z=13,
                overwrite=False,          # キャッシュ活用（新規取得なので影響なし）
                prefecture_code=pref,
                conn=None,
                max_workers=TILE_WORKERS,
                skip_db_write=True,
            )
            elapsed = time.time() - t0
            cnt = len(df) if df is not None and not df.empty else 0
            with _log_lock:
                mark = "✓" if cnt > 0 else "⚠"
                print(f"  {mark} {PREF_NAMES.get(pref,pref)} ({pref}) {year}年: {cnt:,} 件  {elapsed:.0f}秒", flush=True)
            return pref, year, cnt, None
        except Exception as exc:
            elapsed = time.time() - t0
            with _log_lock:
                print(f"  ✗ {PREF_NAMES.get(pref,pref)} ({pref}) {year}年: {exc}  {elapsed:.0f}秒", flush=True)
            return pref, year, 0, exc

    tasks = [(p, y) for y in years_to_fetch for p in TARGET_PREFS]
    print(f"=== 並列取得 ===")
    print(f"対象: {len(years_to_fetch)} 年 × {len(TARGET_PREFS)} 都府県 = {len(tasks)} タスク")
    print(f"並列設定: TILE_WORKERS={TILE_WORKERS}, PREF_WORKERS={PREF_WORKERS}\n", flush=True)

    total_start = time.time()
    with ThreadPoolExecutor(max_workers=PREF_WORKERS) as executor:
        futures = {executor.submit(_sync_one, p, y): (p, y) for p, y in tasks}
        for fut in as_completed(futures):
            pref, year, cnt, exc = fut.result()
            results[(pref, year)] = cnt if exc is None else -1

    elapsed = time.time() - total_start
    print(f"\n取得完了: {elapsed:.0f}秒 ({elapsed/60:.1f}分)", flush=True)

    # Parquet → DB インポート
    print("\n=== 取得分 DB インポート ===")
    imported = 0
    for y in years_to_fetch:
        for pref in TARGET_PREFS:
            p = processed_dir / f"land_prices_y{y}_pref{pref}_pc0.parquet"
            if p.exists():
                df_p = pd.read_parquet(p)
                if not df_p.empty:
                    n = db.upsert_land_prices(conn, df_p)
                    imported += n
                    print(f"  ✓ {PREF_NAMES.get(pref,pref)} {y}年: {len(df_p):,} 件 → DB", flush=True)
    print(f"\nインポート計: {imported:,} 件", flush=True)
    return results

def main():
    args = parse_args()
    all_years = list(range(args.year_from, args.year_to + 1))

    conn = db.get_connection()
    db.create_tables_if_needed(conn)

    total_start = time.time()
    print(f"開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"対象年度: {all_years[0]}〜{all_years[-1]} ({len(all_years)}年分)\n")

    # 1. DB クリア + 既存 Parquet 再インポート（--no-clear 時はスキップ）
    existing_years = [y for y in all_years
                      if any((processed_dir / f"land_prices_y{y}_pref{p}_pc0.parquet").exists()
                             for p in TARGET_PREFS)]
    if args.no_clear:
        print("=== DB クリアをスキップ（追記モード）===")
        if existing_years:
            print(f"既存 Parquet を DB にインポート: {existing_years}")
            clear_and_reimport(conn, existing_years, skip_clear=True)
    else:
        clear_and_reimport(conn, existing_years)

    # 2. 未取得の年度を API から取得
    if not args.skip_fetch:
        new_years = [y for y in all_years if y not in existing_years]
        if new_years:
            print(f"新規取得年度: {new_years}\n")
            fetch_years(conn, new_years)
        else:
            print("新規取得年度なし（すべて Parquet 既存）")

    # 3. 派生テーブル再構築
    print("\n=== 派生テーブル再構築 ===")
    db.rebuild_derived_tables(conn)
    print("  完了")

    conn.close()

    total_elapsed = time.time() - total_start

    # 最終 DB 統計
    conn2 = db.get_connection()
    stats = db.get_stats(conn2)
    conn2.close()
    print(f"\n=== 最終DB統計 ===")
    print(f"総レコード: {stats['total_records']:,}")
    print(f"年度: {stats['available_years']}")
    for y, c in stats['year_counts'].items():
        print(f"  {y}年: {c:,}件")

    print(f"\n総所要時間: {total_elapsed:.0f}秒 ({total_elapsed/60:.1f}分)")
    print(f"終了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
