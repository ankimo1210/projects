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
]


def figures_for(book: str) -> list[FigureSpec]:
    return [f for f in FIGURES if f.book == book]
