"""Command line entry point: ``python -m labor_ai_quadrant <command>``."""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

import pandas as pd

from .axes import sector_frame
from .company import company_frame, load_financials
from .config import SCENARIOS, Config
from .quadrant import quadrant_summary, top_right
from .reference import ReferenceData, load_reference

DEFAULT_OUT = Path("reports/labor_ai_quadrant.html")


def _resolve_reference(args: argparse.Namespace) -> ReferenceData:
    ref = load_reference()
    if args.universe == "curated":
        return ref

    from .providers.jquants import fetch_listed_universe

    universe = fetch_listed_universe(scale=args.scale)
    known = set(ref.shortage.index)
    unknown = sorted(set(universe["sector33"]) - known)
    if unknown:
        print(
            f"警告: 33業種マスタに無い業種名を {len(unknown)} 件検出したため除外します: {unknown}",
            file=sys.stderr,
        )
        universe = universe[universe["sector33"].isin(known)]
    print(f"J-Quants から {len(universe)} 銘柄を取得しました (scale={args.scale})", file=sys.stderr)
    return dataclasses.replace(ref, universe=universe)


def _config_from_args(args: argparse.Namespace) -> Config:
    cfg = SCENARIOS.get(getattr(args, "scenario", "base"), Config())
    overrides: dict[str, float | str] = {}
    if getattr(args, "robotics_weight", None) is not None:
        overrides["robotics_weight"] = args.robotics_weight
    if getattr(args, "realization_rate", None) is not None:
        overrides["realization_rate"] = args.realization_rate
    if getattr(args, "threshold", None) is not None:
        overrides["threshold_method"] = args.threshold
    cfg = cfg.replace(**overrides) if overrides else cfg
    cfg.validate()
    return cfg


def _show(df: pd.DataFrame, columns: list[str]) -> None:
    with pd.option_context("display.max_rows", 400, "display.width", 200, "display.unicode.east_asian_width", True):
        print(df[columns].round(1).to_string())


def cmd_sectors(args: argparse.Namespace) -> int:
    ref = load_reference()
    cfg = _config_from_args(args)
    df = sector_frame(cfg, ref)
    _show(df, ["shortage_score", "ai_score", "ai_substitutable_share_pct", "escape_potential", "quadrant"])
    print("\n--- 象限別サマリー ---")
    print(quadrant_summary(df).to_string())
    return 0


def cmd_top(args: argparse.Namespace) -> int:
    ref = _resolve_reference(args)
    cfg = _config_from_args(args)
    level = args.level
    if level == "sector":
        df = sector_frame(cfg, ref)
        cols = ["shortage_score", "ai_score", "escape_potential", "top_ai_occupation"]
    else:
        df = company_frame(cfg, ref)
        cols = ["name", "sector33", "shortage_score", "ai_score", "escape_potential"]
    _show(top_right(df, args.n), cols)
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    ref = _resolve_reference(args)
    cfg = _config_from_args(args)

    if args.format == "static":
        from .report_static import build_static_report

        if args.financials:
            print(
                "注意: --financials は interactive レポートのみ対応です。無視します。",
                file=sys.stderr,
            )
        out = build_static_report(args.out, cfg=cfg, ref=ref, fragment=args.fragment)
    else:
        from .report import build_report

        financials = load_financials(args.financials) if args.financials else None
        out = build_report(args.out, cfg=cfg, financials=financials, ref=ref)

    print(f"レポートを書き出しました: {out} ({out.stat().st_size / 1024:.0f} KB)")
    return 0


def cmd_verify_universe(args: argparse.Namespace) -> int:
    """Check the curated universe against J-Quants (codes, names, sector33)."""
    from .providers.jquants import fetch_listed_universe

    ref = load_reference()
    live = fetch_listed_universe(scale="all")

    curated = ref.universe
    missing = sorted(set(curated.index) - set(live.index))
    problems = 0
    if missing:
        problems += len(missing)
        print(f"[非上場/コード不一致] {len(missing)} 件: {missing}")

    common = curated.index.intersection(live.index)
    mismatched = [
        (code, curated.loc[code, "sector33"], live.loc[code, "sector33"])
        for code in common
        if curated.loc[code, "sector33"] != live.loc[code, "sector33"]
    ]
    if mismatched:
        problems += len(mismatched)
        print(f"[33業種の不一致] {len(mismatched)} 件:")
        for code, got, expected in mismatched:
            print(f"  {code} {curated.loc[code, 'name']}: curated={got} / jquants={expected}")

    if not problems:
        print(f"OK: キュレーション済み {len(curated)} 銘柄はすべて J-Quants と一致しています")
    return 1 if problems else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="labor_ai_quadrant",
        description="人手不足の深刻度 × AI代替可能性 の4象限フレームワーク（日本の上場企業）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser, *, universe: bool = True) -> None:
        p.add_argument("--scenario", choices=sorted(SCENARIOS), default="base",
                       help="感応度シナリオのプリセット (default: base)")
        p.add_argument("--robotics-weight", type=float, default=None,
                       help="AI代替ポテンシャルにおけるロボ/自動運転成分の重み 0-1")
        p.add_argument("--realization-rate", type=float, default=None,
                       help="AI代替可能な労働が実際に削減される割合 0-1")
        p.add_argument("--threshold", choices=("median", "fixed"), default=None,
                       help="象限境界の決め方 (default: median)")
        if universe:
            p.add_argument("--universe", choices=("curated", "jquants"), default="curated",
                           help="銘柄ユニバース。jquants は要ネットワーク+認証")
            p.add_argument("--scale", choices=("topix100", "topix500", "topix1000", "all"),
                           default="topix500", help="--universe jquants のときの範囲")

    p_sectors = sub.add_parser("sectors", help="33業種のスコア一覧を表示")
    add_common(p_sectors, universe=False)
    p_sectors.set_defaults(func=cmd_sectors)

    p_top = sub.add_parser("top", help="右上象限（AI解放）のランキングを表示")
    add_common(p_top)
    p_top.add_argument("--level", choices=("sector", "company"), default="company")
    p_top.add_argument("-n", type=int, default=25)
    p_top.set_defaults(func=cmd_top)

    p_build = sub.add_parser("build", help="オフラインHTMLレポートを生成")
    add_common(p_build)
    p_build.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p_build.add_argument("--format", choices=("static", "interactive"), default="static",
                         help="static: 自己完結SVG 約30KB（既定） / interactive: Plotly 約5MB")
    p_build.add_argument("--fragment", action="store_true",
                         help="--format static で <html>/<head> を出さず本文断片のみ出力（埋め込み用）")
    p_build.add_argument("--financials", type=Path, default=None,
                         help="code/revenue/operating_profit/labor_cost/employees を持つ CSV/Parquet/JSON"
                              "（--format interactive のみ）")
    p_build.set_defaults(func=cmd_build)

    p_verify = sub.add_parser("verify-universe", help="キュレーション済みユニバースを J-Quants で検証")
    p_verify.set_defaults(func=cmd_verify_universe)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
