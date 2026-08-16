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
from .report_static import TOP_COMPANIES as STATIC_TOP_COMPANIES

DEFAULT_OUT = Path("reports/labor_ai_quadrant.html")

#: これを超えたら J-Quants の財務は日付一括で取る。提出日1日あたり約280件返るので、
#: 銘柄数がこの規模を超えると1銘柄1リクエストより速く、レート制限にも当たりにくい。
BULK_SUMMARY_THRESHOLD = 400


def _align_sector_names(universe: pd.DataFrame, ref: ReferenceData) -> pd.DataFrame:
    """Restate J-Quants' 33-sector labels in the reference table's spelling.

    Matching on the name alone loses six sectors — J-Quants writes 情報･通信業 /
    ガラス･土石製品 / 倉庫･運輸関連業 / 石油･石炭製品 / 電気･ガス業 with a
    half-width middle dot and 証券･商品先物取引業 with a middle dot where JPX's
    own name has a comma. Those would be dropped as "unknown sectors", taking
    the top-right quadrant's leading sector (情報・通信業) with them. The
    four-digit sector code is stable on both sides, so join on that.
    """
    if "sector33_code" not in universe.columns:
        return universe
    by_code = pd.Series(ref.shortage.index.to_numpy(), index=ref.shortage["code"].astype(str))
    mapped = universe["sector33_code"].map(by_code)
    universe = universe.copy()
    universe["sector33"] = mapped.fillna(universe["sector33"])
    return universe


def _resolve_reference(args: argparse.Namespace) -> ReferenceData:
    ref = load_reference()
    if args.universe == "curated":
        return ref

    from .providers.jquants import fetch_listed_universe

    universe = fetch_listed_universe(scale=args.scale)
    universe = _align_sector_names(universe, ref)
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

        financials = load_financials(args.financials) if args.financials else None
        out = build_static_report(
            args.out, cfg=cfg, ref=ref, fragment=args.fragment,
            financials=financials, top_companies=args.top,
        )
    else:
        from .report import build_report

        financials = load_financials(args.financials) if args.financials else None
        out = build_report(args.out, cfg=cfg, financials=financials, ref=ref)

    print(f"レポートを書き出しました: {out} ({out.stat().st_size / 1024:.0f} KB)")
    return 0


def cmd_fetch_financials(args: argparse.Namespace) -> int:
    """Assemble the company-level financial table from J-Quants + EDINET.

    Written to disk rather than used inline: the EDINET sweep walks a year of
    filing calendar and is far too slow to repeat on every report build.
    """
    from .company import estimate_labor_cost
    from .providers.edinet import build_financials
    from .providers.jquants import fetch_summaries, fetch_summaries_by_date

    ref = _resolve_reference(args)
    codes = list(ref.universe.index)
    print(f"対象 {len(codes)} 銘柄", file=sys.stderr)

    print("EDINET から従業員数・平均年間給与・単体P/Lを取得中…", file=sys.stderr)
    edinet = build_financials(lookback_days=args.lookback_days, codes=set(codes))

    print("J-Quants から連結の売上高・営業利益を取得中…", file=sys.stderr)
    try:
        # 銘柄ごとに引くと1銘柄1リクエストで、J-Quants は50件ほど連続で叩くと
        # 429 を返す。日付一括は提出日1日あたり1リクエストで全上場企業が返るので、
        # ユニバースが大きいほど有利になる（TOPIX 全体で 1,642 → 400 リクエスト）。
        summaries = (
            fetch_summaries_by_date(lookback_days=args.lookback_days)
            if len(codes) > BULK_SUMMARY_THRESHOLD
            else fetch_summaries(codes)
        )
    except Exception as exc:
        print(f"J-Quants の取得に失敗しました（連結の参考列は空になります）: {exc}", file=sys.stderr)
        summaries = pd.DataFrame(index=pd.Index([], name="code"))

    merged = edinet.copy()
    # J-Quants は決算短信＝**連結**、EDINET から取っているのは提出会社＝**単体**。
    # 人件費は平均年間給与が単体でしか開示されないため単体でしか組めないので、
    # 比率の分母も単体で揃える。連結の値は別列に置いて混ざらないようにする
    # （NTT は単体従業員 2,606人 / 連結 344,196人。連結営業利益で割ると押上げ余地が
    #   一桁以上小さく出る）。
    for column in ("revenue", "operating_profit"):
        if column in summaries.columns:
            merged[f"{column}_consolidated"] = summaries[column].reindex(merged.index)

    merged["labor_cost"] = estimate_labor_cost(
        merged["employees"], merged["average_salary"], args.benefits_multiplier
    )
    # 単体が企業グループのどれだけを覆っているか。純粋持株会社では数%になり、
    # 単体で組んだ人件費率も押上げ余地もグループの実態を表さない。
    if "employees_consolidated" in merged.columns:
        merged["parent_employee_share"] = merged["employees"] / merged["employees_consolidated"]

    required = ["revenue", "operating_profit", "labor_cost", "employees"]
    complete = merged.dropna(subset=required)
    print(
        f"{len(complete)}/{len(merged)} 銘柄で4項目すべてが揃いました",
        file=sys.stderr,
    )
    share = merged.get("parent_employee_share")
    if share is not None:
        thin = int((share < 0.2).sum())
        print(
            f"単体従業員が連結の2割未満（純粋持株会社など）: {len(merged)} 銘柄中 {thin} 銘柄。"
            "この銘柄群では単体ベースの人件費率・押上げ余地がグループ実態を表しません。",
            file=sys.stderr,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    merged.reset_index().to_csv(args.out, index=False)
    print(f"財務データを書き出しました: {args.out}")
    return 0


def cmd_verify_universe(args: argparse.Namespace) -> int:
    """Check the curated universe against J-Quants (codes, names, sector33)."""
    from .providers.jquants import fetch_listed_universe

    ref = load_reference()
    # 表記揺れ（半角中黒など）を先に吸収しないと、実際には一致している数十件が
    # 業種不一致として並び、本当の再分類が埋もれる。
    live = _align_sector_names(fetch_listed_universe(scale="all"), ref)

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
            p.add_argument("--scale",
                           choices=("topix100", "topix500", "topix1000", "topix", "all"),
                           default="topix500",
                           help="--universe jquants のときの範囲。topix = TOPIX 全構成銘柄、"
                                "all = 規模区分の無い銘柄も含む上場全銘柄")

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
                         help="code/revenue/operating_profit/labor_cost/employees を持つ CSV/Parquet/JSON")
    p_build.add_argument("--top", type=int, default=STATIC_TOP_COMPANIES,
                         help=f"static レポートの銘柄表に載せる件数 (default: {STATIC_TOP_COMPANIES})")
    p_build.set_defaults(func=cmd_build)

    p_fin = sub.add_parser(
        "fetch-financials",
        help="J-Quants + EDINET から財務・従業員データを取得して CSV に保存（要ネットワーク）",
    )
    add_common(p_fin)
    p_fin.add_argument("--out", type=Path, default=Path("_data/financials.csv"))
    p_fin.add_argument("--lookback-days", type=int, default=400,
                       help="EDINET の提出日を何日分さかのぼるか（既定400日＝決算期を問わず1周分）")
    p_fin.add_argument("--benefits-multiplier", type=float, default=1.25,
                       help="平均年間給与から会計上の人件費に直す係数（法定福利費・賞与引当等）")
    p_fin.set_defaults(func=cmd_fetch_financials)

    p_verify = sub.add_parser("verify-universe", help="キュレーション済みユニバースを J-Quants で検証")
    p_verify.set_defaults(func=cmd_verify_universe)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
