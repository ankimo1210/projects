"""企業レベルへの展開と、人件費を通じた P/L 換算。

象限上の位置は業種で決まる部分が大きい。企業固有の差分は2つの属性だけで表現する:

  labor_intensity  労働集約度  → 人手不足の「痛み」の大きさ（X軸）
  knowledge_tilt   知的労働比率 → LLM の効く面積（Y軸）

いずれも業種平均からの乖離を low/mid/high の3値で持ち、``Config.tilt_points``
の幅でスコアを動かす。企業内差分が業種間差分を上書きしないよう幅は小さく取る。

財務データ（人件費・営業利益・売上・従業員数）を渡すと、象限上の位置を
「営業利益が何%押し上がりうるか」に翻訳する。渡さなければ象限マップだけを返す。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .axes import rescale_0_100, sector_frame
from .config import Config
from .quadrant import assign_quadrants, escape_potential
from .reference import TILT_LEVELS, ReferenceData, load_reference

#: 財務レイヤに必要な列。単位は任意だが revenue / operating_profit /
#: labor_cost は同一単位（例: 百万円）で揃っていること。
FINANCIAL_COLUMNS = ("revenue", "operating_profit", "labor_cost", "employees")


def _tilt(series: pd.Series) -> pd.Series:
    return series.map(TILT_LEVELS).astype(float)


def _span(series: pd.Series) -> float:
    """Max-min, falling back to 1.0 so a degenerate column cannot zero out the tilts."""
    span = float(series.max() - series.min())
    return span if span > 0 else 1.0


def company_frame(
    cfg: Config | None = None,
    ref: ReferenceData | None = None,
    financials: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Company-level quadrant map.

    Parameters
    ----------
    financials:
        Optional frame indexed by securities code with the columns in
        :data:`FINANCIAL_COLUMNS`. Rows missing from it simply get NaN in the
        P/L columns — partial coverage is expected and supported.
    """
    cfg = cfg or Config()
    cfg.validate()
    ref = ref or load_reference()

    sectors = sector_frame(cfg, ref)
    joined = ref.universe.copy().join(
        sectors[["shortage_composite", "ai_substitutable_share_pct", "shortage_score", "ai_score"]],
        on="sector33",
    )
    joined = joined.rename(columns={"shortage_score": "sector_shortage_score", "ai_score": "sector_ai_score"})

    # Tilts are applied to the *raw* quantities and the 0-100 rescale is then
    # redone across the company universe. Applying them to the already-rescaled
    # sector score would pile every company in the leading sector onto the 100
    # ceiling, erasing exactly the within-sector differences the tilts encode.
    # One tilt point is defined as 1% of the sector-level spread, so the two
    # scales stay comparable without introducing another free parameter.
    shortage_step = _span(sectors["shortage_composite"]) / 100.0
    ai_step = _span(sectors["ai_substitutable_share_pct"]) / 100.0

    labor_tilt = _tilt(joined["labor_intensity"])
    knowledge_tilt = _tilt(joined["knowledge_tilt"])

    joined["shortage_composite"] = joined["shortage_composite"] + labor_tilt * cfg.tilt_points * shortage_step
    joined["ai_substitutable_share_pct"] = (
        joined["ai_substitutable_share_pct"] + knowledge_tilt * cfg.tilt_points * ai_step
    ).clip(0, 100)

    joined["shortage_score"] = rescale_0_100(joined["shortage_composite"])
    joined["ai_score"] = rescale_0_100(joined["ai_substitutable_share_pct"])

    joined["escape_potential"] = escape_potential(joined["shortage_score"], joined["ai_score"])
    joined["quadrant"] = assign_quadrants(joined["shortage_score"], joined["ai_score"], cfg)

    if financials is not None:
        joined = joined.join(_pnl_layer(joined, financials, cfg))

    return joined.sort_values("escape_potential", ascending=False)


def _pnl_layer(companies: pd.DataFrame, financials: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Translate the AI-substitutable share into an operating-profit sensitivity."""
    missing = [c for c in FINANCIAL_COLUMNS if c not in financials.columns]
    if missing:
        raise ValueError(f"financials is missing required columns {missing}")

    fin = financials.copy()
    fin.index = fin.index.astype(str)
    fin = fin.reindex(companies.index)

    share = companies["ai_substitutable_share_pct"] / 100.0
    addressable = fin["labor_cost"] * share
    savings = addressable * cfg.realization_rate

    out = pd.DataFrame(index=companies.index)
    out["revenue"] = fin["revenue"]
    out["operating_profit"] = fin["operating_profit"]
    out["labor_cost"] = fin["labor_cost"]
    out["employees"] = fin["employees"]
    out["labor_cost_ratio"] = _safe_div(fin["labor_cost"], fin["revenue"])
    out["revenue_per_employee"] = _safe_div(fin["revenue"], fin["employees"])
    out["ai_addressable_labor_cost"] = addressable
    out["expected_labor_savings"] = savings
    # 営業利益に対する感応度。人件費率が高く、かつAI代替余地が大きいほど大きい。
    out["op_uplift_pct"] = _safe_div(savings, fin["operating_profit"]) * 100.0
    return out


def _safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Element-wise division that yields NaN (not inf) on a zero or negative denominator.

    Operating profit can legitimately be zero or negative; an uplift ratio is
    meaningless there and must not be reported as a huge positive number.
    """
    denom = denominator.where(denominator > 0)
    return numerator / denom


#: 法定福利費・賞与・退職給付を上乗せする係数。平均年間給与は現金給与のみなので、
#: 会計上の人件費に直すには社会保険料の事業主負担などを足す必要がある。
#: 健保・厚年・雇用・労災の事業主負担がおおむね給与の15%、これに賞与引当と
#: 退職給付費用を加えて 1.25 を既定とした。感応度を見たい場合は引数で振ること。
DEFAULT_BENEFITS_MULTIPLIER = 1.25


def estimate_labor_cost(
    employees: pd.Series,
    average_salary: pd.Series,
    benefits_multiplier: float = DEFAULT_BENEFITS_MULTIPLIER,
) -> pd.Series:
    """人件費 ≈ 従業員数 × 平均年間給与 × 福利厚生係数。

    多くの日本企業は損益計算書で人件費を単独開示しない（販管費に埋まる）一方、
    有価証券報告書は従業員数と平均年間給与を必ず載せる。したがってこの積が
    実務上いちばん入手しやすい人件費の推計になる。

    **スコープを揃えるのは呼び出し側の責任。** 従業員数・平均年間給与・売上高・
    営業利益がすべて単体なら単体の人件費率が出る。連結従業員数に単体の平均年収を
    掛けると、海外従業員の賃金水準を日本と同じとみなすことになり過大推計になる。
    ``providers.edinet`` は既定で提出会社（単体）の値を揃えて返す。
    """
    return employees * average_salary * benefits_multiplier


def load_financials(path: str | Path) -> pd.DataFrame:
    """Read a user-supplied financial table, indexed by securities code.

    Supports ``.csv``, ``.parquet`` and ``.json``. The file must contain a
    ``code`` column plus the columns in :data:`FINANCIAL_COLUMNS`.
    """
    path = Path(path)
    if path.suffix == ".csv":
        df = pd.read_csv(path, dtype={"code": str})
    elif path.suffix == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix == ".json":
        df = pd.read_json(path, dtype={"code": str})
    else:
        raise ValueError(f"unsupported financials format: {path.suffix} (use .csv/.parquet/.json)")

    if "code" not in df.columns:
        raise ValueError(f"{path.name}: a 'code' column is required")
    df["code"] = df["code"].astype(str).str.zfill(4)
    return df.set_index("code")
