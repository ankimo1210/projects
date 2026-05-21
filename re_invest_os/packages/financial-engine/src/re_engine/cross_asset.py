"""クロスアセット比較 (純粋関数)。

仕様: docs/architecture/calculation_engine_spec.md §5.9
法務注意: docs/architecture/calculation_engine_spec.md §9 (避ける表現)

**重要**:
- 個別銘柄推奨はしない
- 資産クラス・指数レベルの参考比較に留める
- "買うべき/売るべき" の表現は出さない
- すべて参考リターン (名目)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AssetClass = Literal[
    "real_estate",
    "world_equity",
    "us_equity",
    "japan_equity",
    "jreit",
    "jp_bonds",
    "us_bonds",
    "jpy_deposit",
    "mmf",
]


class AssetBenchmark(BaseModel):
    asset_class: AssetClass
    label_jp: str
    expected_return_annual: float  # 名目年率
    liquidity: Literal["high", "medium", "low"]
    diversification: Literal["high", "medium", "low"]
    effort: Literal["high", "medium", "low"]
    leverage_risk: bool
    fx_risk: bool
    note: str = ""
    model_config = ConfigDict(extra="forbid")


# 初期固定値 (青写真9.3 + spec §5.9)
DEFAULT_BENCHMARKS: list[AssetBenchmark] = [
    AssetBenchmark(
        asset_class="world_equity",
        label_jp="全世界株インデックス",
        expected_return_annual=0.050,
        liquidity="high",
        diversification="high",
        effort="low",
        leverage_risk=False,
        fx_risk=True,
        note="MSCI ACWI / VT 等。長期名目リターン",
    ),
    AssetBenchmark(
        asset_class="us_equity",
        label_jp="米国株インデックス",
        expected_return_annual=0.060,
        liquidity="high",
        diversification="high",
        effort="low",
        leverage_risk=False,
        fx_risk=True,
        note="S&P500 / VTI 等。長期名目リターン",
    ),
    AssetBenchmark(
        asset_class="japan_equity",
        label_jp="日本株インデックス",
        expected_return_annual=0.040,
        liquidity="high",
        diversification="high",
        effort="low",
        leverage_risk=False,
        fx_risk=False,
        note="TOPIX / Nikkei225 等",
    ),
    AssetBenchmark(
        asset_class="jreit",
        label_jp="J-REIT指数",
        expected_return_annual=0.045,
        liquidity="high",
        diversification="medium",
        effort="low",
        leverage_risk=False,
        fx_risk=False,
        note="東証REIT指数。配当込み",
    ),
    AssetBenchmark(
        asset_class="jp_bonds",
        label_jp="国内債券",
        expected_return_annual=0.010,
        liquidity="high",
        diversification="medium",
        effort="low",
        leverage_risk=False,
        fx_risk=False,
        note="10年国債周辺",
    ),
    AssetBenchmark(
        asset_class="us_bonds",
        label_jp="米国債",
        expected_return_annual=0.040,
        liquidity="high",
        diversification="medium",
        effort="low",
        leverage_risk=False,
        fx_risk=True,
        note="10年米国債。為替リスク別",
    ),
    AssetBenchmark(
        asset_class="jpy_deposit",
        label_jp="円定期預金",
        expected_return_annual=0.003,
        liquidity="high",
        diversification="low",
        effort="low",
        leverage_risk=False,
        fx_risk=False,
        note="メガバンク定期",
    ),
    AssetBenchmark(
        asset_class="mmf",
        label_jp="MMF / 短期金融商品",
        expected_return_annual=0.005,
        liquidity="high",
        diversification="medium",
        effort="low",
        leverage_risk=False,
        fx_risk=False,
    ),
]


class ComparisonRow(BaseModel):
    asset_class: AssetClass
    label_jp: str
    expected_return: float
    premium_over_re_pt: float  # 不動産税後IRRとの差 (pt)
    liquidity: Literal["high", "medium", "low"]
    effort: Literal["high", "medium", "low"]
    note: str
    model_config = ConfigDict(extra="forbid")


class CrossAssetResult(BaseModel):
    re_label_jp: str = "本物件 (税後)"
    re_after_tax_irr: float | None
    rows: list[ComparisonRow]
    disclaimer: str = (
        "資産クラス間の参考シナリオ比較です。特定金融商品の売買を推奨するものではありません。"
        "過去データ・仮定に基づく試算であり、将来のリターンを保証するものではありません。"
        "最終的な投資判断はユーザー自身の責任で行ってください。"
    )
    model_config = ConfigDict(extra="forbid")


class CrossAssetRequest(BaseModel):
    re_after_tax_irr: float | None
    benchmarks: list[AssetBenchmark] = Field(default_factory=lambda: DEFAULT_BENCHMARKS)
    model_config = ConfigDict(extra="forbid")


def cross_asset_comparison(req: CrossAssetRequest) -> CrossAssetResult:
    """不動産税後IRRに対する各資産クラスの参考プレミアムを算出。

    注意:
    - リターンは名目年率
    - 個別銘柄推奨を含まない
    - 為替リスク・流動性差は別途付記
    """
    irr = req.re_after_tax_irr if req.re_after_tax_irr is not None else 0.0
    rows: list[ComparisonRow] = []
    for b in req.benchmarks:
        premium_pt = (b.expected_return_annual - irr) * 100
        rows.append(
            ComparisonRow(
                asset_class=b.asset_class,
                label_jp=b.label_jp,
                expected_return=b.expected_return_annual,
                premium_over_re_pt=round(premium_pt, 2),
                liquidity=b.liquidity,
                effort=b.effort,
                note=b.note,
            )
        )
    return CrossAssetResult(re_after_tax_irr=req.re_after_tax_irr, rows=rows)
