"""
sync_public_notice.py
全国（または都道府県別）の地価公示データをタイル走査で同期する。

CLI 使用例:
    python sync_public_notice.py --year 2026 --z 13
    python sync_public_notice.py --year 2026 --z 13 --pref 13
    python sync_public_notice.py --year 2025 --overwrite
"""

import argparse
import concurrent.futures
import json
import threading
import time
from pathlib import Path

import api_client
import db
import normalize
import pandas as pd
import tiles
from config import (
    DEFAULT_PRICE_CLASSIFICATION,
    DEFAULT_ZOOM,
    PROCESSED_DIR,
    RAW_DIR,
    REQUEST_INTERVAL_SEC,
    ensure_dirs,
    get_logger,
)

logger = get_logger(__name__)


# --------------------------------------------------------------------------
# 重複排除
# --------------------------------------------------------------------------


def merge_and_deduplicate_features(
    features: list[dict],
) -> list[dict]:
    """
    複数タイルから収集した GeoJSON Feature を point_id で重複排除する。

    Parameters
    ----------
    features : list[dict]
        GeoJSON Feature オブジェクトのリスト（タイル間で重複あり）。

    Returns
    -------
    list[dict]
        重複排除済みリスト。
    """
    seen: set[str] = set()
    deduped: list[dict] = []

    for f in features:
        props = f.get("properties") or {}
        # 実際のAPIレスポンスでは "point_id" フィールドが存在する
        pid = None
        for key in ["point_id", "standardLandNumber", "標準地番号", "L01_001"]:
            val = props.get(key)
            if val:
                pid = str(val)
                break

        # 座標フォールバック
        if pid is None:
            geom = f.get("geometry", {})
            if geom and geom.get("type") == "Point":
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    pid = f"coord_{coords[0]:.6f}_{coords[1]:.6f}"

        if pid is None or pid in seen:
            continue
        seen.add(pid)
        deduped.append(f)

    logger.debug(
        "重複排除: %d → %d features (重複 %d 件)",
        len(features),
        len(deduped),
        len(features) - len(deduped),
    )
    return deduped


# --------------------------------------------------------------------------
# 取得済みタイルの管理
# --------------------------------------------------------------------------


def _tile_cache_path(year: int, z: int, price_classification: int) -> Path:
    """取得済みタイルを記録するファイルパスを返す。"""
    return RAW_DIR / f"fetched_tiles_{year}_z{z}_pc{price_classification}.json"


def _load_fetched_tiles(year: int, z: int, price_classification: int) -> set[str]:
    """取得済みタイルのセットを読み込む。"""
    path = _tile_cache_path(year, z, price_classification)
    if not path.exists():
        return set()
    with open(path) as f:
        return set(json.load(f))


def _save_fetched_tiles(year: int, z: int, price_classification: int, fetched: set[str]) -> None:
    """取得済みタイルセットを保存する。"""
    path = _tile_cache_path(year, z, price_classification)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(list(fetched), f)


def _tile_key(z: int, x: int, y: int) -> str:
    return f"{z}/{x}/{y}"


# --------------------------------------------------------------------------
# raw GeoJSON 保存
# --------------------------------------------------------------------------


def _raw_geojson_path(year: int, z: int, price_classification: int) -> Path:
    return RAW_DIR / f"xpt002_y{year}_z{z}_pc{price_classification}.geojson"


def _save_raw_geojson(
    features: list[dict],
    year: int,
    z: int,
    price_classification: int,
) -> Path:
    """収集した全 Feature を raw GeoJSON として保存する。"""
    path = _raw_geojson_path(year, z, price_classification)
    path.parent.mkdir(parents=True, exist_ok=True)
    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "year": year,
            "z": z,
            "priceClassification": price_classification,
            "featureCount": len(features),
        },
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    logger.info("raw GeoJSON 保存: %s (%d features)", path, len(features))
    return path


# --------------------------------------------------------------------------
# Parquet 保存
# --------------------------------------------------------------------------


def _parquet_path(
    year: int,
    price_classification: int,
    prefecture_code: str | None = None,
) -> Path:
    if prefecture_code:
        return (
            PROCESSED_DIR
            / f"land_prices_y{year}_pref{prefecture_code}_pc{price_classification}.parquet"
        )
    return PROCESSED_DIR / f"land_prices_y{year}_pc{price_classification}.parquet"


def _save_parquet(
    df: pd.DataFrame,
    year: int,
    price_classification: int,
    prefecture_code: str | None = None,
) -> Path:
    path = _parquet_path(year, price_classification, prefecture_code)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    logger.info("Parquet 保存: %s (%d rows)", path, len(df))
    return path


# --------------------------------------------------------------------------
# メイン同期関数
# --------------------------------------------------------------------------


def sync_public_notice_year(
    year: int,
    z: int = DEFAULT_ZOOM,
    price_classification: int = DEFAULT_PRICE_CLASSIFICATION,
    use_category_codes: list[str] | None = None,
    overwrite: bool = False,
    prefecture_code: str | None = None,
    max_empty_streak: int = 0,  # 0 = 無制限
    conn=None,  # 既存の DuckDB 接続を渡すと競合を回避できる
    max_workers: int = 1,  # タイル並列取得数。1=逐次、4程度が目安
    skip_db_write: bool = False,  # True=Parquetのみ保存、DB書き込みをスキップ
) -> pd.DataFrame:
    """
    指定年の地価公示データを API から取得し、DB へ保存する。

    Parameters
    ----------
    year : int
        取得対象年 (例: 2026)。
    z : int
        ズームレベル。デフォルト 13。
    price_classification : int
        0=地価公示, 1=地価調査。
    use_category_codes : list[str], optional
        用途区分コードで絞り込む (例: ["01"])。
    overwrite : bool
        True の場合、取得済みタイル記録を無視して再取得する。
    prefecture_code : str, optional
        指定時は該当都道府県のみ走査する。
    max_empty_streak : int
        空タイルが連続した場合の打ち切り（デバッグ用）。0 = 打ち切りなし。
    max_workers : int
        タイル並列取得数。1=逐次（デフォルト）。4程度で約4倍高速化。
    skip_db_write : bool
        True の場合 Parquet のみ保存、DB 書き込みをスキップ。
        並列処理でDB競合を避けたい場合に使用し、後でまとめてインポートする。

    Returns
    -------
    pd.DataFrame
        正規化済みの全データ。
    """
    ensure_dirs()

    fetched_tiles = set() if overwrite else _load_fetched_tiles(year, z, price_classification)

    all_features: list[dict] = []
    tile_count = 0
    error_count = 0

    # タイル走査イテレータの選択
    if prefecture_code:
        tile_iter = tiles.iter_prefecture_tiles(prefecture_code, z)
        logger.info("都道府県別同期開始: year=%d, z=%d, pref=%s", year, z, prefecture_code)
    else:
        tile_iter = tiles.iter_japan_tiles(z)
        logger.info("全国同期開始: year=%d, z=%d", year, z)

    # 取得済みを除外したタイルリストを作成（generatorを消費）
    pending_tiles = [
        (tz, x, y) for tz, x, y in tile_iter if _tile_key(tz, x, y) not in fetched_tiles
    ]

    if max_workers > 1 and pending_tiles:
        # ── 並列取得 ──────────────────────────────────────────────
        _lock = threading.Lock()
        _stats = [0, 0]  # [tile_count, error_count]

        def _fetch_one(args: tuple[int, int, int]) -> None:
            tz, x, y = args
            key = _tile_key(tz, x, y)
            try:
                data = api_client.fetch_geojson_tile_xpt002(
                    z=tz,
                    x=x,
                    y=y,
                    year=year,
                    price_classification=price_classification,
                    use_category_codes=use_category_codes,
                )
                feats = data.get("features", [])
                with _lock:
                    all_features.extend(feats)
                    fetched_tiles.add(key)
                    _stats[0] += 1
                    if _stats[0] % 200 == 0:
                        logger.info("進捗: %d タイル, %d features", _stats[0], len(all_features))
                        _save_fetched_tiles(year, z, price_classification, fetched_tiles)
            except Exception as exc:
                with _lock:
                    _stats[1] += 1
                logger.warning("タイル %s 取得失敗 (%d): %s", key, _stats[1], exc)
            finally:
                time.sleep(REQUEST_INTERVAL_SEC)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            pool.map(_fetch_one, pending_tiles)

        tile_count, error_count = _stats
    else:
        # ── 逐次取得（デフォルト・互換モード） ───────────────────
        for tile_z, x, y in pending_tiles:
            key = _tile_key(tile_z, x, y)
            try:
                data = api_client.fetch_geojson_tile_xpt002(
                    z=tile_z,
                    x=x,
                    y=y,
                    year=year,
                    price_classification=price_classification,
                    use_category_codes=use_category_codes,
                )
                features = data.get("features", [])
                all_features.extend(features)
                fetched_tiles.add(key)
                tile_count += 1
                if tile_count % 500 == 0:
                    logger.info(
                        "進捗: %d タイル処理済み, 累積 %d features", tile_count, len(all_features)
                    )
                    _save_fetched_tiles(year, z, price_classification, fetched_tiles)
            except Exception as exc:
                error_count += 1
                logger.warning("タイル %s 取得失敗 (%d 件目): %s", key, error_count, exc)
                if error_count > 100:
                    logger.error("エラーが多すぎるため中断します (error_count=%d)", error_count)
                    break
            time.sleep(REQUEST_INTERVAL_SEC)

    # 取得完了後の保存
    _save_fetched_tiles(year, z, price_classification, fetched_tiles)

    logger.info(
        "タイル走査完了: %d タイル, %d features (重複排除前), エラー %d 件",
        tile_count,
        len(all_features),
        error_count,
    )

    if not all_features:
        logger.warning(
            "year=%d のデータが 0 件でした。"
            "年度が未公開の場合や API 仕様変更の可能性があります。"
            "year=%d を試してみてください。",
            year,
            year - 1,
        )
        return pd.DataFrame()

    # 重複排除
    deduped = merge_and_deduplicate_features(all_features)

    # raw 保存
    _save_raw_geojson(deduped, year, z, price_classification)

    # 正規化
    df = normalize.normalize_features_to_dataframe(deduped, year, price_classification)
    logger.info("正規化完了: %d レコード", len(df))

    # Parquet 保存（都道府県コード付きファイル名）
    _save_parquet(df, year, price_classification, prefecture_code)

    # DuckDB 保存（skip_db_write=True の場合はスキップ）
    if not skip_db_write:
        _own_conn = conn is None
        _write_conn = None
        try:
            _write_conn = db.get_connection() if _own_conn else conn
            db.create_tables_if_needed(_write_conn)
            inserted = db.upsert_land_prices(_write_conn, df)
            logger.info("DuckDB 保存完了: %d 件 upsert", inserted)
        except Exception as exc:
            logger.warning(
                "DuckDB 保存スキップ (Parquet は保存済み): %s — "
                "別カーネルや Streamlit が DB を開いている場合はそちらを終了してください。",
                exc,
            )
        finally:
            if _own_conn and _write_conn is not None:
                try:
                    _write_conn.close()
                except Exception:
                    pass

    return df


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="地価公示データを不動産情報ライブラリ API から取得・保存する"
    )
    p.add_argument("--year", type=int, required=True, help="取得対象年 (例: 2026)")
    p.add_argument(
        "--z", type=int, default=DEFAULT_ZOOM, help=f"ズームレベル (デフォルト: {DEFAULT_ZOOM})"
    )
    p.add_argument(
        "--pref",
        type=str,
        default=None,
        help="都道府県コード 2 桁 (省略時は全国)",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="取得済みタイル記録を無視して再取得する",
    )
    p.add_argument(
        "--price-class",
        type=int,
        default=0,
        help="価格区分 (0=地価公示, 1=地価調査; デフォルト: 0)",
    )
    p.add_argument(
        "--smoke-test",
        action="store_true",
        help="APIとDB の疎通確認のみ行う",
    )
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.smoke_test:
        ok_key = api_client.smoke_test_api_key()
        ok_xit = api_client.smoke_test_xit002()
        ok_xpt = api_client.smoke_test_xpt002(year=args.year)
        ok_db = db.smoke_test_db()
        print(f"API key:  {'OK' if ok_key else 'NG'}")
        print(f"XIT002:   {'OK' if ok_xit else 'NG'}")
        print(f"XPT002:   {'OK' if ok_xpt else 'NG'}")
        print(f"DB:       {'OK' if ok_db else 'NG'}")
        return

    df = sync_public_notice_year(
        year=args.year,
        z=args.z,
        price_classification=args.price_class,
        overwrite=args.overwrite,
        prefecture_code=args.pref,
    )

    if df.empty:
        print(f"[警告] year={args.year} でデータが取得できませんでした。")
        print(
            f"  → year={args.year - 1} を試す場合: python sync_public_notice.py --year {args.year - 1}"
        )
    else:
        print(f"同期完了: {len(df)} 件 (year={args.year})")


if __name__ == "__main__":
    main()
