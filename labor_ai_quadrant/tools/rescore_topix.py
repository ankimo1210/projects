"""Re-score the TOPIX universe from the cached snapshots (no network).

``--universe jquants --scale topix`` needs ~400 J-Quants requests and an EDINET
pass. Both were already run, so the銘柄リスト and the財務 are on disk. This
script reuses them so that a change to the reference tables can be re-scored
without touching the network — which also means the only thing that moved
between two runs is the framework, not the data vintage.

    uv run python labor_ai_quadrant/tools/rescore_topix.py
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd
from labor_ai_quadrant.axes import sector_frame
from labor_ai_quadrant.company import company_frame, load_financials
from labor_ai_quadrant.config import Config
from labor_ai_quadrant.quadrant import quadrant_summary
from labor_ai_quadrant.reference import load_reference

PKG = Path(__file__).resolve().parents[1]
DATA = PKG / "_data"

UNIVERSE_COLUMNS = ["code", "name", "sector33", "scale_category"]
#: company_frame が返さない開示の生値。ダンプを読む側の検算用に付け直す。
PASSTHROUGH_COLUMNS = [
    "filer_name", "average_salary", "average_age",
    "employees_consolidated", "revenue_consolidated", "operating_profit_consolidated",
]
OUT_COLUMNS = [
    "code", "name", "filer_name", "sector33", "scale_category", "quadrant",
    "shortage_score", "ai_score", "ai_substitutable_share_pct", "escape_potential",
    "employees", "average_salary", "average_age", "labor_cost", "revenue",
    "operating_profit", "labor_cost_ratio", "revenue_per_employee",
    "ai_addressable_labor_cost", "expected_labor_savings", "op_margin_uplift_pp",
    "op_uplift_pct", "employees_consolidated", "revenue_consolidated",
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


def main() -> None:
    prev_path = DATA / "topix_scored.csv"
    ref = dataclasses.replace(load_reference(), universe=cached_universe(prev_path))
    financials = load_financials(DATA / "financials_topix.csv")
    cfg = Config()

    previous = pd.read_csv(prev_path, dtype={"code": str}).set_index("code")
    companies = company_frame(cfg, ref, financials)
    # company_frame は P/L に使う列だけを返す。開示の生値（平均年収・平均年齢・
    # 連結の売上と営業利益）は、読む側が単体基準の数字を検算するのに要るので戻す。
    passthrough = [c for c in PASSTHROUGH_COLUMNS if c in financials.columns]
    companies = companies.join(financials[passthrough], rsuffix="_fin")
    companies = companies.reset_index().rename(columns={"index": "code"})
    if "code" not in companies.columns:
        companies = companies.rename(columns={companies.columns[0]: "code"})

    sectors = sector_frame(cfg, ref)
    sectors.to_csv(DATA / "topix_sectors.csv")
    companies[[c for c in OUT_COLUMNS if c in companies.columns]].to_csv(
        prev_path, index=False, float_format="%.6f"
    )

    print(f"companies: {len(companies)}   sectors: {len(sectors)}")
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
