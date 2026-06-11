"""sync_market_lake.py — 市場データレイク同期 CLI。

re_invest_os の市場エビデンス分析向けに、reinfolib タイル API
（XPT001 取引ポイント / XKT002 用途地域 / XKT026・028・029 ハザード /
XKT013 将来推計人口メッシュ）を対象エリアへ一括ダンプする。

使い方:
    # スモーク（沖縄本島・取引2024のみ・タイル20枚まで）
    python sync_market_lake.py --areas okinawa --layers xpt001 --years 2024 --limit-tiles 20

    # フル（関東+関西+域外政令市+沖縄本島、取引 2016-2025 + 全 GIS レイヤー）
    python sync_market_lake.py --areas kanto,kansai,cities,okinawa --years 2016-2025

    # 中断後の再開（既定で resume 有効 — 完了タイルはスキップ）
    python sync_market_lake.py --areas kanto,kansai,cities,okinawa --years 2016-2025

    # 件数サマリ
    python sync_market_lake.py --stats
"""

from __future__ import annotations

import argparse
import sys

import db
from config import get_logger
from market_lake import ALL_LAYERS, build_worklist, run_sync, target_tiles

logger = get_logger(__name__)


def _parse_years(spec: str) -> list[int]:
    """"2016-2025" または "2024" / "2022,2024"。"""
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.extend(range(int(lo), int(hi) + 1))
        elif part:
            out.append(int(part))
    return sorted(set(out))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--areas",
        type=str,
        default="kanto,kansai,cities,okinawa",
        help="エリアグループ (カンマ区切り: kanto/kansai/cities/okinawa)",
    )
    p.add_argument(
        "--layers",
        type=str,
        default=",".join(ALL_LAYERS),
        help=f"レイヤー (カンマ区切り、既定: {','.join(ALL_LAYERS)})",
    )
    p.add_argument("--years", type=str, default="2016-2025", help="xpt001 の対象年 (例: 2016-2025)")
    p.add_argument("--z", type=int, default=13, help="タイルズームレベル (既定 13)")
    p.add_argument("--workers", type=int, default=6, help="並列フェッチ数 (既定 6)")
    p.add_argument("--limit-tiles", type=int, default=None, help="リクエスト上限 (スモーク用)")
    p.add_argument("--no-resume", action="store_true", help="同期済みタイルもやり直す")
    p.add_argument("--plan", action="store_true", help="リクエスト数の見積りだけ表示して終了")
    p.add_argument("--stats", action="store_true", help="レイクの件数サマリを表示して終了")
    args = p.parse_args()

    if args.stats:
        conn = db.get_connection(read_only=True)
        for k, v in db.lake_stats(conn).items():
            print(f"{k}: {v}")
        return

    groups = [g.strip() for g in args.areas.split(",") if g.strip()]
    layers = [layer.strip().lower() for layer in args.layers.split(",") if layer.strip()]
    unknown = [layer for layer in layers if layer not in ALL_LAYERS]
    if unknown:
        print(f"unknown layers: {unknown} (choices: {ALL_LAYERS})", file=sys.stderr)
        sys.exit(2)
    years = _parse_years(args.years)

    tiles = target_tiles(groups, args.z)
    work = build_worklist(layers, groups, years, args.z)
    print(f"対象タイル: {len(tiles)} 枚 / 総リクエスト(全量): {len(work)} 件")
    if args.plan:
        for layer in layers:
            n = len([w for w in work if w.layer == layer])
            print(f"  {layer}: {n}")
        return

    conn = db.get_connection()
    stats = run_sync(
        conn,
        layers,
        groups,
        years,
        z=args.z,
        workers=args.workers,
        resume=not args.no_resume,
        limit_tiles=args.limit_tiles,
    )
    print(stats)
    print("--- lake stats ---")
    for k, v in db.lake_stats(conn).items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
