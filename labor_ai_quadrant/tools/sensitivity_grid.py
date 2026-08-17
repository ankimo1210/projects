"""象限の所属が、判断の入る設定でどれだけ動くかを一枚の表にする。

interactive レポートの感応度は X軸6指標の leave-one-out だけで、レビュー（F-08）が
指摘したとおり **判断がいちばん入る箇所を振っていない**。ここでは4つを振る。

* `realization_rate` — 0.15 / 0.30 / 0.50
* 規制ドラッグ — 有効 / 0（analyst 判断値なので0にしたときの影響を見る）
* 象限の境界 — 33業種の中央値 / 絶対50 / 上位1/3
* 企業内の傾き — 既定8点 / 0点

出力は「AI解放に入る業種数と業種名」「右上の企業数」「右上の等ウェイト株価リターン」。
株価はキャッシュ（`_data/prices_monthly.json`）だけを読むのでネットワークに触らない。

    uv run python labor_ai_quadrant/tools/sensitivity_grid.py
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pandas as pd
from labor_ai_quadrant.axes import sector_frame
from labor_ai_quadrant.company import company_frame, company_quadrant_cuts
from labor_ai_quadrant.config import Q_ESCAPE, Config
from labor_ai_quadrant.quadrant import assign_quadrants
from labor_ai_quadrant.reference import load_reference

PKG = Path(__file__).resolve().parents[1]
DATA = PKG / "_data"

BASE = pd.Period("2022-11", freq="M")


def _prices(codes: list[str], as_of: pd.Period) -> pd.DataFrame:
    payload = json.loads((DATA / "prices_monthly.json").read_text())
    cached = payload.get("prices", payload)
    frame = pd.DataFrame({c: cached[c] for c in codes if c in cached}).sort_index()
    frame.index = pd.PeriodIndex(frame.index, freq="M")
    frame = frame.loc[frame.index <= as_of]
    ratio = frame / frame.shift(1)
    broken = frame.columns[(frame <= 0).any() | (ratio > 4.0).any() | (ratio < 0.25).any()]
    return frame.drop(columns=broken)


def _equal_weight(prices: pd.DataFrame, codes: list[str]) -> float:
    """Equal-weight total return (%) from BASE to the last month, for ``codes``."""
    live = [c for c in codes if c in prices.columns and pd.notna(prices.loc[BASE, c])]
    if not live:
        return float("nan")
    rel = prices[live].div(prices.loc[BASE, live], axis=1) * 100.0
    return float(rel.iloc[-1].mean() - 100.0)


def variants(ref) -> dict[str, tuple[Config, object]]:
    """name -> (config, reference). The drag variant needs a modified reference."""
    flat_drag = dataclasses.replace(ref, regulation_drag=ref.regulation_drag * 0.0)
    return {
        "base (実現率0.30)": (Config(), ref),
        "実現率 0.15": (Config(realization_rate=0.15), ref),
        "実現率 0.50": (Config(realization_rate=0.50), ref),
        "規制ドラッグ = 0": (Config(), flat_drag),
        "境界 = 絶対50": (Config(threshold_method="fixed"), ref),
        "企業の傾き = 0点": (Config(tilt_points=0.0), ref),
    }


def _top_third(sectors: pd.DataFrame, companies: pd.DataFrame) -> pd.Series:
    """Quadrants when the boundary is the sector 上位1/3 instead of the median."""
    x_cut = float(sectors["shortage_composite"].quantile(2 / 3))
    y_cut = float(sectors["ai_exposure_pct"].quantile(2 / 3))
    from labor_ai_quadrant.quadrant import project_cut

    return assign_quadrants(
        companies["shortage_score"],
        companies["ai_score"],
        Config(),
        cuts=(
            project_cut(x_cut, companies["shortage_composite"]),
            project_cut(y_cut, companies["ai_exposure_pct"]),
        ),
    )


def main() -> None:
    ref0 = load_reference()
    universe = pd.read_csv(DATA / "universe_topix.csv", dtype={"code": str}).set_index("code")
    universe["labor_intensity"] = "mid"
    universe["knowledge_tilt"] = "mid"
    ref0 = dataclasses.replace(ref0, universe=universe)

    as_of = pd.Period("2026-07", freq="M")
    prices = _prices(list(universe.index), as_of)

    rows = []
    for name, (cfg, ref) in variants(ref0).items():
        sectors = sector_frame(cfg, ref)
        companies = company_frame(cfg, ref)
        escape_sectors = sorted(sectors.index[sectors["quadrant"] == Q_ESCAPE])
        escape_codes = list(companies.index[companies["quadrant"] == Q_ESCAPE])
        rows.append(
            {
                "設定": name,
                "AI解放 業種数": len(escape_sectors),
                "AI解放 企業数": len(escape_codes),
                "右上 等ウェイト%": _equal_weight(prices, escape_codes),
                "ユニバース 等ウェイト%": _equal_weight(prices, list(universe.index)),
                "AI解放 業種": "、".join(escape_sectors),
            }
        )

    # 境界だけ差し替える追加ケース（33業種の上位1/3）
    sectors = sector_frame(Config(), ref0)
    companies = company_frame(Config(), ref0)
    q = _top_third(sectors, companies)
    codes = list(q.index[q == Q_ESCAPE])
    x_cut = float(sectors["shortage_composite"].quantile(2 / 3))
    y_cut = float(sectors["ai_exposure_pct"].quantile(2 / 3))
    sector_q = assign_quadrants(
        sectors["shortage_composite"], sectors["ai_exposure_pct"], Config(), cuts=(x_cut, y_cut)
    )
    escape_sectors = sorted(sectors.index[sector_q == Q_ESCAPE])
    rows.append(
        {
            "設定": "境界 = 33業種の上位1/3",
            "AI解放 業種数": len(escape_sectors),
            "AI解放 企業数": len(codes),
            "右上 等ウェイト%": _equal_weight(prices, codes),
            "ユニバース 等ウェイト%": _equal_weight(prices, list(universe.index)),
            "AI解放 業種": "、".join(escape_sectors),
        }
    )

    out = pd.DataFrame(rows)
    out.to_csv(DATA / "sensitivity_grid.csv", index=False, float_format="%.1f")
    cuts = company_quadrant_cuts(sectors, companies, Config())
    print(f"as-of {as_of}月末  価格のある銘柄 {prices.shape[1]}  既定の境界 {cuts[0]:.2f}/{cuts[1]:.2f}")
    print(out.drop(columns=["AI解放 業種"]).to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
    print()
    for r in rows:
        print(f"{r['設定']}: {r['AI解放 業種']}")


if __name__ == "__main__":
    main()
