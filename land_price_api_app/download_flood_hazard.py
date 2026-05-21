"""
download_flood_hazard.py
国土数値情報「洪水浸水想定区域データ（A31a）」を shapefile から GeoJSON に変換し、
hazard_sources.py が読み込める形式で保存する。

== データ取得手順 ==
1. 以下のサイトから対象都道府県の「洪水浸水想定区域データ」を手動でダウンロードする。
   https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31a.html
   ※ サービス種別: A31a（洪水浸水想定区域）
   ※ 形式: shape（.zip）を選択

2. .zip を任意のフォルダに展開する（例: /tmp/A31a_13/）

3. このスクリプトを実行:
   python download_flood_hazard.py --shp /tmp/A31a_13/A31a-13_*.shp --pref 13

== 出力 ==
   ../_data/land_price/raw/hazard/flood_13.geojson
   （hazard_sources.py が自動検出する）

== 座標系 ==
国土数値情報 A31a は JGD2011 地理座標（EPSG:6668）。
WGS84 との差は最大 1cm 程度なので変換なしで使用する。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import RAW_DIR, get_logger

logger = get_logger(__name__)

HAZARD_DIR = RAW_DIR / "hazard"

# A31a shapefile の浸水深フィールド名候補（バージョンにより変化）
_DEPTH_FIELD_CANDIDATES = [
    "depth_rank",
    "A31a_503",  # 旧フォーマット
    "A31a_504",
    "rank",
    "level",
    "浸水深",
    "最大浸水深",
]


def convert_shp_to_geojson(shp_path: Path, pref_code: str, output_path: Path) -> int:
    """shapefile を読み込み、GeoJSON として保存する。変換したフィーチャ数を返す。"""
    try:
        import shapefile  # pyshp
    except ImportError:
        raise RuntimeError("pyshp が必要です。pip install pyshp でインストールしてください。")

    shp_path = Path(shp_path)
    if not shp_path.exists():
        raise FileNotFoundError(f"shapefile が見つかりません: {shp_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    reader = shapefile.Reader(str(shp_path))
    fields = [f[0] for f in reader.fields[1:]]  # fields[0] は削除フラグ
    logger.info("フィールド: %s", fields)

    depth_field = next((f for f in _DEPTH_FIELD_CANDIDATES if f in fields), None)
    if depth_field:
        logger.info("浸水深フィールド: %s", depth_field)
    else:
        logger.warning("浸水深フィールドが見つかりませんでした。フィールド一覧: %s", fields)

    features = []
    skipped = 0
    for sr in reader.shapeRecords():
        geom_dict = sr.shape.__geo_interface__
        if not geom_dict or geom_dict.get("type") is None:
            skipped += 1
            continue

        props = dict(zip(fields, sr.record))
        # 浸水深ランクを統一キー "depth_rank" で保持
        if depth_field:
            props["depth_rank"] = props.get(depth_field)

        features.append({
            "type": "Feature",
            "geometry": geom_dict,
            "properties": props,
        })

    geojson = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:6668"}},
        "features": features,
    }

    output_path.write_text(json.dumps(geojson, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    logger.info("保存: %s (%d フィーチャ, %d スキップ)", output_path, len(features), skipped)
    return len(features)


def inspect_shp(shp_path: Path) -> None:
    """shapefile のフィールド一覧と最初の数件を表示する（変換前の確認用）。"""
    try:
        import shapefile
    except ImportError:
        print("pyshp が必要です。pip install pyshp でインストールしてください。")
        return

    reader = shapefile.Reader(str(shp_path))
    fields = [f[0] for f in reader.fields[1:]]
    print(f"フィールド ({len(fields)}):")
    for f in fields:
        print(f"  {f}")
    print(f"\nフィーチャ数: {len(reader)}")
    print("\n最初の3件:")
    for sr in reader.shapeRecords()[:3]:
        props = dict(zip(fields, sr.record))
        print(f"  geometry type: {sr.shape.shapeType}")
        print(f"  props: {props}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="国土数値情報 A31a shapefile → hazard GeoJSON 変換")
    parser.add_argument("--shp", help="変換する .shp ファイルのパス（glob パターン可）")
    parser.add_argument("--pref", required=True, help="都道府県コード (例: 13)")
    parser.add_argument("--inspect", action="store_true", help="フィールド一覧を確認するだけ（変換しない）")
    parser.add_argument("--output", help="出力先 GeoJSON パス（省略時は自動設定）")
    args = parser.parse_args()

    if not args.shp:
        print("使い方: python download_flood_hazard.py --shp /path/to/A31a.shp --pref 13")
        print("データは https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31a.html からダウンロードしてください。")
        return

    # glob パターン対応
    shp_candidates = sorted(Path(".").glob(args.shp)) or [Path(args.shp)]
    if not shp_candidates:
        print(f"ファイルが見つかりません: {args.shp}")
        sys.exit(1)

    if args.inspect:
        inspect_shp(shp_candidates[0])
        return

    pref_code = args.pref.zfill(2)
    output_path = Path(args.output) if args.output else HAZARD_DIR / f"flood_{pref_code}.geojson"

    total = 0
    for shp_path in shp_candidates:
        n = convert_shp_to_geojson(shp_path, pref_code, output_path)
        total += n
        print(f"変換完了: {shp_path} → {output_path} ({n} フィーチャ)")

    print(f"\n合計 {total} フィーチャを保存しました。")
    print(f"hazard_sources.py が {output_path} を自動検出して判定に使用します。")


if __name__ == "__main__":
    main()
