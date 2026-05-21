"""
sync_trade_prices.py
不動産取引価格情報 (XIT001) を都道府県・年・四半期単位で同期する。

CLI 使用例:
    python sync_trade_prices.py --pref 47 --year 2024
    python sync_trade_prices.py --pref 13 --year 2024 --quarter 1
    python sync_trade_prices.py --pref 47 --year 2023 --overwrite
"""

import argparse
import time
from pathlib import Path

import api_client
import db
import normalize
import pandas as pd
from config import (
    PROCESSED_DIR,
    RAW_DIR,
    REQUEST_INTERVAL_SEC,
    ensure_dirs,
    get_logger,
)

logger = get_logger(__name__)


# --------------------------------------------------------------------------
# ファイル保存
# --------------------------------------------------------------------------


def _raw_path(pref: str, year: int, quarter: int) -> Path:
    return RAW_DIR / f"xit001_pref{pref}_y{year}q{quarter}.geojson"


def _parquet_path(pref: str, year: int, quarter: int) -> Path:
    return PROCESSED_DIR / f"trade_prices_pref{pref}_y{year}q{quarter}.parquet"


# --------------------------------------------------------------------------
# 1四半期同期
# --------------------------------------------------------------------------


def sync_trade_quarter(
    pref: str,
    year: int,
    quarter: int,
    overwrite: bool = False,
    conn=None,
    skip_db_write: bool = False,
) -> pd.DataFrame:
    """指定都道府県・年・四半期の取引価格データを同期する。"""
    pref = str(pref).zfill(2)
    parquet = _parquet_path(pref, year, quarter)

    if not overwrite and parquet.exists():
        logger.info("スキップ (既存): pref=%s year=%d Q%d", pref, year, quarter)
        return pd.read_parquet(parquet)

    logger.info("取得開始: pref=%s year=%d Q%d", pref, year, quarter)
    try:
        records = api_client.fetch_trade_prices_xit001(pref, year, quarter)
    except Exception as exc:
        logger.error("XIT001 取得失敗 pref=%s year=%d Q%d: %s", pref, year, quarter, exc)
        return pd.DataFrame()

    if not records:
        logger.warning("データなし: pref=%s year=%d Q%d", pref, year, quarter)
        return pd.DataFrame()

    # raw 保存
    raw = _raw_path(pref, year, quarter)
    raw.parent.mkdir(parents=True, exist_ok=True)
    import json

    with open(raw, "w", encoding="utf-8") as f:
        json.dump(
            {"year": year, "quarter": quarter, "pref": pref, "data": records}, f, ensure_ascii=False
        )

    # 正規化
    df = normalize.normalize_xit001_features_to_dataframe(records, year, quarter)
    logger.info("正規化完了: %d 件 (pref=%s year=%d Q%d)", len(df), pref, year, quarter)

    # Parquet 保存
    parquet.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(parquet, index=False)

    # DB 保存
    if not skip_db_write and not df.empty:
        _own_conn = conn is None
        _write_conn = None
        try:
            _write_conn = db.get_connection() if _own_conn else conn
            db.create_tables_if_needed(_write_conn)
            inserted = db.upsert_trade_prices(_write_conn, df)
            logger.info("DB 保存完了: %d 件 (pref=%s year=%d Q%d)", inserted, pref, year, quarter)
        except Exception as exc:
            logger.warning("DB 保存スキップ (Parquet 保存済み): %s", exc)
        finally:
            if _own_conn and _write_conn is not None:
                try:
                    _write_conn.close()
                except Exception:
                    pass

    return df


# --------------------------------------------------------------------------
# 年全体同期（全四半期ループ）
# --------------------------------------------------------------------------


def sync_trade_year(
    pref: str,
    year: int,
    quarters: list[int] | None = None,
    overwrite: bool = False,
    conn=None,
) -> pd.DataFrame:
    """指定年の全四半期（または指定四半期）を順に同期する。"""
    qs = quarters or [1, 2, 3, 4]
    all_dfs: list[pd.DataFrame] = []

    for q in qs:
        df = sync_trade_quarter(pref, year, q, overwrite=overwrite, conn=conn)
        if not df.empty:
            all_dfs.append(df)
        time.sleep(REQUEST_INTERVAL_SEC)

    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="不動産取引価格情報 (XIT001) を取得・保存する")
    p.add_argument("--pref", type=str, required=True, help="都道府県コード 2桁 (例: 47)")
    p.add_argument("--year", type=int, required=True, help="取得対象年 (例: 2024)")
    p.add_argument(
        "--quarter",
        type=int,
        default=None,
        choices=[1, 2, 3, 4],
        help="四半期 1-4 (省略時は全四半期)",
    )
    p.add_argument("--overwrite", action="store_true", help="既存 Parquet を再取得して上書き")
    p.add_argument(
        "--skip-db", action="store_true", help="DB 書き込みをスキップし Parquet のみ保存"
    )
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    ensure_dirs()

    if args.quarter:
        df = sync_trade_quarter(
            args.pref,
            args.year,
            args.quarter,
            overwrite=args.overwrite,
            skip_db_write=args.skip_db,
        )
    else:
        df = sync_trade_year(
            args.pref,
            args.year,
            overwrite=args.overwrite,
        )

    if df.empty:
        print(f"[警告] pref={args.pref} year={args.year} でデータが取得できませんでした。")
    else:
        print(f"同期完了: {len(df)} 件 (pref={args.pref} year={args.year})")


if __name__ == "__main__":
    main()
