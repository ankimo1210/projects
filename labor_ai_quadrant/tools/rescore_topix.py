"""Re-score the TOPIX universe from the cached snapshots (no network).

``--universe jquants --scale topix`` needs ~400 J-Quants requests and an EDINET
pass. Both were already run, so the銘柄リスト and the財務 are on disk. This
script reuses them so that a change to the reference tables can be re-scored
without touching the network — which also means the only thing that moved
between two runs is the framework, not the data vintage.

    uv run python labor_ai_quadrant/tools/rescore_topix.py
"""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

import pandas as pd
from labor_ai_quadrant.axes import sector_frame
from labor_ai_quadrant.company import (
    DEFAULT_BENEFITS_MULTIPLIER,
    company_frame,
    company_quadrant_cuts,
    estimate_labor_cost,
    load_financials,
)
from labor_ai_quadrant.config import Config
from labor_ai_quadrant.quadrant import quadrant_summary
from labor_ai_quadrant.reference import load_reference

PKG = Path(__file__).resolve().parents[1]
DATA = PKG / "_data"

UNIVERSE_COLUMNS = ["code", "name", "sector33", "scale_category"]
#: 銘柄リストのスナップショット。**出力ファイルとは別にする。** 同じ CSV を読んで
#: 同じ CSV に書くと、途中で落ちたときに入力ごと壊れ、前回との比較も成立しなくなる。
UNIVERSE_SNAPSHOT = "universe_topix.csv"
#: company_frame が返さない開示の生値。ダンプを読む側の検算用に付け直す。
PASSTHROUGH_COLUMNS = [
    "filer_name", "average_salary", "average_age",
    "employees_consolidated", "revenue_consolidated", "operating_profit_consolidated",
]
OUT_COLUMNS = [
    "code", "name", "parent_scope", "parent_scope_flag", "filer_name", "sector33", "scale_category", "quadrant",
    "shortage_score", "ai_score", "ai_exposure_pct", "escape_potential",
    # 人手不足の緩和量（すべて従業員数に対する%）
    "vacancy_rate_pct", "ai_capacity_release_pct", "closable_gap_pct", "gap_coverage_x",
    "employees", "average_salary", "average_age", "labor_cost", "revenue",
    "operating_profit", "labor_cost_ratio", "revenue_per_employee",
    # 売上回復の経路（本線）
    "contribution_margin", "recovered_revenue", "scenario_profit_gain",
    "op_margin_uplift_pp", "op_uplift_pct",
    # 人件費削減の経路（比較用・前版のロジック）
    "cost_cut_savings", "cost_cut_margin_pp",
    "employees_consolidated", "revenue_consolidated",
    "operating_profit_consolidated", "parent_employee_share",
]


def cached_universe(path: Path) -> pd.DataFrame:
    """The 銘柄リスト as J-Quants returned it, from the previous scored snapshot.

    J-Quants carries no company-level attributes, so ``labor_intensity`` and
    ``knowledge_tilt`` are "mid" for every row — the same thing the live path
    does. Every company in a sector therefore gets that sector's scores.
    """
    df = pd.read_csv(path, dtype={"code": str})[UNIVERSE_COLUMNS].copy()
    df["labor_intensity"] = "mid"
    df["knowledge_tilt"] = "mid"
    return df.set_index("code")


def universe_path(seed_from: Path | None = None) -> Path:
    """The universe snapshot, seeded from the scored dump on first run."""
    path = DATA / UNIVERSE_SNAPSHOT
    if not path.exists():
        seed = pd.read_csv(seed_from or DATA / "topix_scored.csv", dtype={"code": str})
        seed[UNIVERSE_COLUMNS].to_csv(path, index=False)
        print(f"seeded {path.name} from {(seed_from or Path('topix_scored.csv')).name} ({len(seed)} rows)")
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--universe", type=Path, default=None,
                    help=f"銘柄リスト（既定 _data/{UNIVERSE_SNAPSHOT}、無ければ --compare-to から生成）")
    ap.add_argument("--financials", type=Path, default=DATA / "financials_topix.csv")
    ap.add_argument("--out", type=Path, default=DATA / "topix_scored.csv",
                    help="企業スコアの出力先。入力とは別ファイルにできる")
    ap.add_argument("--out-sectors", type=Path, default=DATA / "topix_sectors.csv")
    ap.add_argument("--compare-to", type=Path, default=DATA / "topix_scored.csv",
                    help="象限の移動を比べる相手（既定は前回の出力）")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    out_path = args.out
    universe = args.universe or universe_path(args.compare_to)
    ref = dataclasses.replace(load_reference(), universe=cached_universe(universe))
    financials = load_financials(args.financials)
    # 人件費はキャッシュの値を使わず、開示の従業員数×平均年間給与から毎回引き直す。
    # 係数を変えたときにキャッシュ側の古い人件費が残らないようにするため。
    if {"employees", "average_salary"} <= set(financials.columns):
        financials["labor_cost"] = estimate_labor_cost(
            financials["employees"], financials["average_salary"], DEFAULT_BENEFITS_MULTIPLIER
        )
        print(f"labor_cost recomputed with benefits_multiplier={DEFAULT_BENEFITS_MULTIPLIER}")
    cfg = Config()

    previous = pd.read_csv(args.compare_to, dtype={"code": str}).set_index("code")
    companies = company_frame(cfg, ref, financials)
    # company_frame は P/L に使う列だけを返す。開示の生値（平均年収・平均年齢・
    # 連結の売上と営業利益）は、読む側が単体基準の数字を検算するのに要るので戻す。
    passthrough = [c for c in PASSTHROUGH_COLUMNS if c in financials.columns]
    companies = companies.join(financials[passthrough], rsuffix="_fin")
    companies = companies.reset_index().rename(columns={"index": "code"})
    if "code" not in companies.columns:
        companies = companies.rename(columns={companies.columns[0]: "code"})

    sectors = sector_frame(cfg, ref)
    sectors.to_csv(args.out_sectors)
    companies[[c for c in OUT_COLUMNS if c in companies.columns]].to_csv(
        out_path, index=False, float_format="%.6f"
    )

    cuts = company_quadrant_cuts(sectors, companies.set_index("code"), cfg)
    print(f"companies: {len(companies)}   sectors: {len(sectors)}")
    if cuts:
        print(f"象限の境界（33業種の中央値を企業軸へ投影）: 人手不足 {cuts[0]:.2f} / AI {cuts[1]:.2f}")
    print("\n=== 象限サマリー ===")
    print(quadrant_summary(companies.set_index("code")).to_string())

    moved = companies.set_index("code")["quadrant"].rename("new").to_frame().join(
        previous["quadrant"].rename("old")
    )
    changed = moved[moved["new"] != moved["old"]]
    print(f"\n象限が変わった銘柄: {len(changed)} / {len(moved)}")
    print(changed.groupby(["old", "new"]).size().sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main()
