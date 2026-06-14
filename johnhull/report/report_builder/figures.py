"""Figure registry for the johnhull portal.

Mirrors ``analytics/report``: every entry is a :class:`FigureSpec` whose
``build`` callable returns a Plotly ``go.Figure`` by calling a
:mod:`hullkit.plotly_viz` builder. Those builders wrap the same pricing/risk
functions the notebooks use, so the gallery can never drift from the maths.

Adding a figure = append one ``FigureSpec``. Adding a theme = one ``BookMeta``.
New deep-dive volumes (A1 stochastic calculus, A2 stoch-vol/Fourier, A3 advanced
numerics, A4 XVA) register their figures here as they land.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from hullkit import plotly_viz as pv


@dataclass(frozen=True)
class BookMeta:
    key: str
    title: str
    subtitle: str
    accent: str
    book_index: str  # relative path from site/ to the Jupyter Book index


BOOKS: dict[str, BookMeta] = {
    "options_core": BookMeta(
        key="options_core",
        title="オプションの設計図",
        subtitle="ペイオフ・グリークス・ヘッジ",
        accent="#2563eb",
        book_index="../../book/_build/html/index.html",
    ),
    "numerics": BookMeta(
        key="numerics",
        title="数値手法の収束",
        subtitle="格子・モンテカルロ・有限差分",
        accent="#7c3aed",
        book_index="../../book/_build/html/index.html",
    ),
    "risk_credit": BookMeta(
        key="risk_credit",
        title="リスクと信用",
        subtitle="VaR・ES・デフォルト",
        accent="#16a34a",
        book_index="../../book/_build/html/index.html",
    ),
    "stochastic": BookMeta(
        key="stochastic",
        title="確率解析",
        subtitle="伊藤・Girsanov・Feynman-Kac",
        accent="#0891b2",
        book_index="../../book/_build/html/index.html",
    ),
    "volatility": BookMeta(
        key="volatility",
        title="確率ボラティリティ",
        subtitle="Heston・Fourier・SABR",
        accent="#db2777",
        book_index="../../book/_build/html/index.html",
    ),
    "rates_swaps": BookMeta(
        key="rates_swaps",
        title="金利とスワップ",
        subtitle="カーブ・デュレーション・スワップ",
        accent="#ca8a04",
        book_index="../../book/_build/html/index.html",
    ),
    "exotics": BookMeta(
        key="exotics",
        title="エキゾチック",
        subtitle="バリア・アジアン",
        accent="#0d9488",
        book_index="../../book/_build/html/index.html",
    ),
}


@dataclass(frozen=True)
class FigureSpec:
    id: str
    book: str
    title: str
    blurb: str
    build: Callable
    is_new: bool = False
    tags: tuple = field(default_factory=tuple)


FIGURES: list[FigureSpec] = [
    # options_core -------------------------------------------------------
    FigureSpec(
        "strategy_payoffs",
        "options_core",
        "オプション戦略のペイオフ",
        "ブル/ストラドル/バタフライ…をドロップダウンで切替。脚の足し合わせが戦略の形を作る(Hull Ch.12)。",
        pv.plotly_strategy_payoffs,
        tags=("dropdown",),
    ),
    FigureSpec(
        "delta_vs_spot",
        "options_core",
        "デルタは満期で鋭くなる",
        "残存 T を縮めるとコールデルタが滑らかな S 字 → ストライクでの段差へ。ガンマ急増の理由(Hull Ch.19)。",
        pv.plotly_delta_vs_spot,
        is_new=True,
        tags=("slider", "greeks"),
    ),
    FigureSpec(
        "delta_hedge_cost",
        "options_core",
        "デルタヘッジ費用が BSM 価格へ締まる",
        "リヘッジ回数を増やすとヘッジ費用の分布が BSM 価格(破線)の周りに収束。実ドリフトに依らない(Hull §19.4)。",
        pv.plotly_delta_hedge_cost,
        is_new=True,
        tags=("slider", "hedging", "mc"),
    ),
    # numerics -----------------------------------------------------------
    FigureSpec(
        "tree_convergence",
        "numerics",
        "二項木 → BSM 収束",
        "ステップ数 N を上げると CRR 価格が鋸歯状に振動しながら閉形式へ収束する(Hull Ch.13)。",
        pv.plotly_tree_convergence,
        tags=("convergence",),
    ),
    # numerics (A3) ------------------------------------------------------
    FigureSpec(
        "mc_variance_reduction",
        "numerics",
        "分散減少と QMC の収束",
        "価格誤差 vs N を手法別に両対数で。制御変量は水準を下げ、Sobol QMC は傾きを N⁻¹ へ近づける。",
        pv.plotly_mc_variance_reduction,
        is_new=True,
        tags=("convergence", "mc"),
    ),
    FigureSpec(
        "qmc_vs_pseudo",
        "numerics",
        "擬似乱数 vs Sobol 列",
        "単位正方形上の点。擬似乱数はむら・隙間、Sobol は一様に空間を埋める(低食い違い)。",
        pv.plotly_qmc_vs_pseudo,
        is_new=True,
        tags=("qmc",),
    ),
    FigureSpec(
        "american_boundary",
        "numerics",
        "アメリカンプットの早期行使境界",
        "Crank-Nicolson から読む S*(τ)。境界より下で行使。σ を上げると境界は下がる(待つ価値)。",
        pv.plotly_american_boundary,
        is_new=True,
        tags=("slider", "fd", "american"),
    ),
    # risk_credit --------------------------------------------------------
    FigureSpec(
        "var_es",
        "risk_credit",
        "VaR と ES を信頼水準で動かす",
        "信頼水準を上げると VaR(とその外側の ES)が損失テールへ深く移動。ヒストリカル法(Hull Ch.22)。",
        pv.plotly_var_es,
        is_new=True,
        tags=("slider", "risk"),
    ),
    FigureSpec(
        "credit_survival",
        "risk_credit",
        "生存確率と CDS スプレッド",
        "ハザード率 λ を上げると生存曲線が速く減衰し、5Y CDS パースプレッドが拡大する(Hull Ch.24-25)。",
        pv.plotly_credit_survival,
        is_new=True,
        tags=("slider", "credit"),
    ),
    # XVA & counterparty credit (A4) -------------------------------------
    FigureSpec(
        "exposure_profile",
        "risk_credit",
        "エクスポージャ EE / PFE",
        "フォワードの期待エクスポージャ EE(CVA を駆動)と PFE(限度枠)。σ で両者が広がる。",
        pv.plotly_exposure_profile,
        is_new=True,
        tags=("slider", "xva"),
    ),
    FigureSpec(
        "portfolio_loss",
        "risk_credit",
        "ポートフォリオ損失 vs 相関",
        "1ファクター・ガウシアンコピュラ。平均は pd 不変、相関 ρ↑ で損失分布のテールが肥大(2008年の本質)。",
        pv.plotly_portfolio_loss_correlation,
        is_new=True,
        tags=("slider", "copula"),
    ),
    FigureSpec(
        "copula_scatter",
        "risk_credit",
        "コピュラ散布とテール依存",
        "ガウシアンコピュラ標本。ρ↑ で点が対角に集まり、名柄が同時にデフォルトしやすくなる。",
        pv.plotly_copula_scatter,
        is_new=True,
        tags=("slider", "copula"),
    ),
    # stochastic (A1) ----------------------------------------------------
    FigureSpec(
        "quadratic_variation",
        "stochastic",
        "二次変分 [W]_t → t",
        "ブラウン運動の累積 Σ(ΔW)² が、分割を細かくするほど直線 y=t に張り付く(Shreve II §3.4)。",
        pv.plotly_quadratic_variation,
        is_new=True,
        tags=("slider", "brownian"),
    ),
    FigureSpec(
        "ito_correction",
        "stochastic",
        "伊藤 vs Stratonovich",
        "∫W dW の左点和(伊藤)と中点和(Stratonovich)の差 ½[W]_T → ½T が伊藤の補正項(Shreve II §4.3)。",
        pv.plotly_ito_correction,
        is_new=True,
        tags=("slider", "ito"),
    ),
    FigureSpec(
        "girsanov",
        "stochastic",
        "Girsanov: 実世界 μ を変えても Q は不変",
        "実世界ドリフト μ を動かしても、測度変換後のリスク中立分布と Q コール価格は動かない(Shreve II §5.2-5.4)。",
        pv.plotly_girsanov,
        is_new=True,
        tags=("slider", "measure-change"),
    ),
    # volatility (A2) ----------------------------------------------------
    FigureSpec(
        "heston_smile",
        "volatility",
        "Heston スマイルと ρ",
        "Heston 価格(COS)を逆算した IV スマイル。ρ<0 で下方スキュー、ξ で曲率(Gatheral Ch.3)。",
        pv.plotly_heston_smile,
        is_new=True,
        tags=("slider", "smile"),
    ),
    FigureSpec(
        "cos_convergence",
        "volatility",
        "COS 法の密度収束",
        "特性関数から復元した密度が項数 N を増やすと基準へ収束。少数項で十分(Fang-Oosterlee)。",
        pv.plotly_cos_density_convergence,
        is_new=True,
        tags=("slider", "fourier"),
    ),
    FigureSpec(
        "sabr_smile",
        "volatility",
        "SABR スマイルと vol-of-vol",
        "Hagan 公式の IV スマイル。ν を上げると曲率が増し、ρ<0 で傾く(市場標準の補間)。",
        pv.plotly_sabr_smile,
        is_new=True,
        tags=("slider", "smile", "sabr"),
    ),
    # extra coverage -----------------------------------------------------
    FigureSpec(
        "gamma_surface",
        "options_core",
        "ガンマ曲面 Γ(S, T)",
        "ガンマはストライク近傍・満期直前で尖る。ATM オプションが満期間際に最もヘッジしにくい理由。",
        pv.plotly_gamma_surface,
        is_new=True,
        tags=("surface", "greeks"),
    ),
    FigureSpec(
        "stop_loss_vs_delta",
        "options_core",
        "ストップロス vs デルタヘッジ",
        "素朴なストップロスは偏り・分散が大きい。デルタヘッジは BSM 価格に締まる(Hull §19.2)。",
        pv.plotly_stop_loss_vs_delta_hedge,
        is_new=True,
        tags=("slider", "hedging"),
    ),
    FigureSpec(
        "binomial_lattice",
        "numerics",
        "二項木格子と後ろ向き帰納",
        "CRR 格子そのもの。ノードの色がオプション価値、アメリカンの早期行使域が見える(Hull Ch.13)。",
        pv.plotly_binomial_lattice,
        is_new=True,
        tags=("tree",),
    ),
    FigureSpec(
        "garch_volatility",
        "volatility",
        "ボラのクラスタリング(EWMA/GARCH)",
        "EWMA と GARCH(1,1) の年率ボラ。荒れた時期が固まり、GARCH は長期水準へ平均回帰(Hull Ch.23)。",
        pv.plotly_garch_volatility,
        is_new=True,
        tags=("garch",),
    ),
    FigureSpec(
        "garch_term_structure",
        "volatility",
        "GARCH 予測の期間構造",
        "出発が高ボラでも低ボラでも、予測は長期ボラへ平均回帰。ボラの期間構造の素。",
        pv.plotly_garch_term_structure,
        is_new=True,
        tags=("garch",),
    ),
    FigureSpec(
        "merton_structural",
        "risk_credit",
        "Merton 構造模型",
        "株式 = 資産のコール。負債・資産ボラを上げるとデフォルト確率が上がる(Hull §24.6)。",
        pv.plotly_merton_structural,
        is_new=True,
        tags=("slider", "credit"),
    ),
    FigureSpec(
        "portfolio_diversification",
        "risk_credit",
        "分散投資と相関の床",
        "独立なら 1/√N で減るが、相関 ρ があると √ρ·σ の床が残る(分散しきれないリスク)。",
        pv.plotly_portfolio_diversification,
        is_new=True,
        tags=("risk",),
    ),
    FigureSpec(
        "yield_curve",
        "rates_swaps",
        "イールドカーブとフォワード",
        "順イールドではフォワードがゼロ金利の上、逆イールドでは下に来る(Hull Ch.4)。",
        pv.plotly_yield_curve,
        is_new=True,
        tags=("slider", "rates"),
    ),
    FigureSpec(
        "bond_convexity",
        "rates_swaps",
        "債券の価格-利回りとコンベクシティ",
        "価格-利回り曲線は凸。デュレーション(接線)が捉え損なう曲率がコンベクシティ(Hull Ch.4)。",
        pv.plotly_bond_convexity,
        is_new=True,
        tags=("rates",),
    ),
    FigureSpec(
        "swap_value",
        "rates_swaps",
        "金利スワップの価値と par レート",
        "受取固定スワップ価値は固定金利に対して線形で、par スワップレートでちょうど 0(Hull Ch.7)。",
        pv.plotly_swap_value,
        is_new=True,
        tags=("rates", "swap"),
    ),
    FigureSpec(
        "barrier_knockout",
        "exotics",
        "ノックアウト・バリアコール",
        "バリア H が原資産に近づくほどノックアウトしやすく、価値が 0 へ崩れる(Hull §26.9)。",
        pv.plotly_barrier_knockout,
        is_new=True,
        tags=("slider", "exotic"),
    ),
    FigureSpec(
        "asian_vs_european",
        "exotics",
        "アジアン vs ヨーロピアン",
        "平均価格は終端価格よりボラが低い → アジアンはヨーロピアンより割安(Hull §26.12)。",
        pv.plotly_asian_vs_european,
        is_new=True,
        tags=("exotic",),
    ),
]


def figures_for(book: str) -> list[FigureSpec]:
    return [f for f in FIGURES if f.book == book]
