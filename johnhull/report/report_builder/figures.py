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

from . import frontier_figures as ff


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
    "ml_derivatives": BookMeta(
        key="ml_derivatives",
        title="MLとデリバティブ",
        subtitle="surrogate・surface・forecast・hedge",
        accent="#4f46e5",
        book_index="../../book/_build/html/index.html",
    ),
    "volatility_frontiers": BookMeta(
        key="volatility_frontiers",
        title="ボラ最前線",
        subtitle="joint SPX/VIX・0DTE",
        accent="#e11d48",
        book_index="../../book/_build/html/index.html",
    ),
    "crypto_market": BookMeta(
        key="crypto_market",
        title="Crypto市場構造",
        subtitle="perpetual・liquidation・AMM",
        accent="#f97316",
        book_index="../../book/_build/html/index.html",
    ),
    "climate_energy": BookMeta(
        key="climate_energy",
        title="気候とエネルギー",
        subtitle="carbon・weather・PPA",
        accent="#059669",
        book_index="../../book/_build/html/index.html",
    ),
    "risk_management": BookMeta(
        key="risk_management",
        title="リスク管理デスク",
        subtitle="バックテスト・EVT・配賦・PnL explain",
        accent="#dc2626",
        book_index="../../book/_build/html/index.html",
    ),
}


@dataclass(frozen=True)
class FigureSpec:
    id: str
    book: str
    title: str
    blurb: str  # 何が見えるか
    build: Callable
    is_new: bool = False
    tags: tuple = field(default_factory=tuple)
    practice: str = ""  # 実務での意味 — なぜ実社会で役立つか


FIGURES: list[FigureSpec] = [
    # options_core -------------------------------------------------------
    FigureSpec(
        "strategy_payoffs",
        "options_core",
        "オプション戦略のペイオフ",
        "ブル/ストラドル/バタフライ…をドロップダウンで切替。脚の足し合わせが戦略の形を作る(Hull Ch.12)。",
        pv.plotly_strategy_payoffs,
        practice="セールスが顧客の相場観を『形』に翻訳する道具。脚の組み合わせで損益図を設計する。",
        tags=("dropdown",),
    ),
    FigureSpec(
        "delta_vs_spot",
        "options_core",
        "デルタは満期で鋭くなる",
        "残存 T を縮めるとコールデルタが滑らかな S 字 → ストライクでの段差へ。ガンマ急増の理由(Hull Ch.19)。",
        pv.plotly_delta_vs_spot,
        practice="満期が近いほどデルタが段差化＝ガンマ急騰。決算跨ぎ短期 ATM のヘッジが最難関な理由。",
        is_new=True,
        tags=("slider", "greeks"),
    ),
    FigureSpec(
        "delta_hedge_cost",
        "options_core",
        "デルタヘッジ費用が BSM 価格へ締まる",
        "リヘッジ回数を増やすとヘッジ費用の分布が BSM 価格(破線)の周りに収束。実ドリフトに依らない(Hull §19.4)。",
        pv.plotly_delta_hedge_cost,
        practice="マーケットメイカーの損益分布そのもの。建値(BSM)へ締まる＝方向観に依らず鞘を取れる。",
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
        practice="閉形式の無い商品を木で値付ける際の必要ステップ数の目安。木と BSM の一致は実装の検算。",
        tags=("convergence",),
    ),
    # numerics (A3) ------------------------------------------------------
    FigureSpec(
        "mc_variance_reduction",
        "numerics",
        "分散減少と QMC の収束",
        "価格誤差 vs N を手法別に両対数で。制御変量は水準を下げ、Sobol QMC は傾きを N⁻¹ へ近づける。",
        pv.plotly_mc_variance_reduction,
        practice="XVA 等の重い MC を実用化する鍵。同じ精度を桁違いに少ない計算で得る。",
        is_new=True,
        tags=("convergence", "mc"),
    ),
    FigureSpec(
        "qmc_vs_pseudo",
        "numerics",
        "擬似乱数 vs Sobol 列",
        "単位正方形上の点。擬似乱数はむら・隙間、Sobol は一様に空間を埋める(低食い違い)。",
        pv.plotly_qmc_vs_pseudo,
        practice="高次元の値付けを速くする低食い違い列。実務 MC が QMC を使う理由が目で分かる。",
        is_new=True,
        tags=("qmc",),
    ),
    FigureSpec(
        "american_boundary",
        "numerics",
        "アメリカンプットの早期行使境界",
        "Crank-Nicolson から読む S*(τ)。境界より下で行使。σ を上げると境界は下がる(待つ価値)。",
        pv.plotly_american_boundary,
        practice="『いつ行使・解約すべきか』の境界。コーラブル債・期前償還の実務判断に直結。",
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
        practice="銀行の規制資本・リスク限度の根幹。Basel が VaR から ES へ移った理由を体感できる。",
        is_new=True,
        tags=("slider", "risk"),
    ),
    FigureSpec(
        "credit_survival",
        "risk_credit",
        "生存確率と CDS スプレッド",
        "ハザード率 λ を上げると生存曲線が速く減衰し、5Y CDS パースプレッドが拡大する(Hull Ch.24-25)。",
        pv.plotly_credit_survival,
        practice="CDS スプレッドから読む信用の市場評価。ハザード率と価格の対応。",
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
        practice="CVA を駆動する EE と限度枠の PFE。カウンターパーティ・リスク管理の基礎量。",
        is_new=True,
        tags=("slider", "xva"),
    ),
    FigureSpec(
        "cva_sensitivity",
        "risk_credit",
        "CVA の時間分解とハザード感応度",
        "CVA 被積分項 (1−R)·DF·EE·ΔPD を時間軸に展開。λ を上げると総額(タイトル、bp 表示)が増え、重みが手前に移る。",
        pv.plotly_cva_sensitivity,
        practice="CVA は『エクスポージャが大きい時期』と『デフォルトしやすい時期』の重なり。CVA デスクのプライシングの直感。",
        is_new=True,
        tags=("slider", "xva", "cva"),
    ),
    FigureSpec(
        "portfolio_loss",
        "risk_credit",
        "ポートフォリオ損失 vs 相関",
        "1ファクター・ガウシアンコピュラ。平均は pd 不変、相関 ρ↑ で損失分布のテールが肥大(2008年の本質)。",
        pv.plotly_portfolio_loss_correlation,
        practice="相関こそシステミックリスク。平均は不変でテールだけ肥大＝2008年の本質。",
        is_new=True,
        tags=("slider", "copula"),
    ),
    FigureSpec(
        "copula_scatter",
        "risk_credit",
        "コピュラ散布とテール依存",
        "ガウシアンコピュラ標本。ρ↑ で点が対角に集まり、名柄が同時にデフォルトしやすくなる。",
        pv.plotly_copula_scatter,
        practice="相関↑ で名柄が同時にデフォルトしやすくなる様子。CDO が崩れた仕組み。",
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
        practice="二次変分 → t が伊藤の ½σ² 項の源。あらゆる価格 PDE の出発点。",
        is_new=True,
        tags=("slider", "brownian"),
    ),
    FigureSpec(
        "ito_correction",
        "stochastic",
        "伊藤 vs Stratonovich",
        "∫W dW の左点和(伊藤)と中点和(Stratonovich)の差 ½[W]_T → ½T が伊藤の補正項(Shreve II §4.3)。",
        pv.plotly_ito_correction,
        practice="伊藤 vs Stratonovich の差＝½T。確率版の連鎖律がなぜ要るか。",
        is_new=True,
        tags=("slider", "ito"),
    ),
    FigureSpec(
        "girsanov",
        "stochastic",
        "Girsanov: 実世界 μ を変えても Q は不変",
        "実世界ドリフト μ を動かしても、測度変換後のリスク中立分布と Q コール価格は動かない(Shreve II §5.2-5.4)。",
        pv.plotly_girsanov,
        practice="実世界 μ を動かしても Q 価格は不変。リスク中立評価が成り立つ理由の可視化。",
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
        practice="ρ で傾き・ξ で曲率。市場スマイルへのカリブレーションのパラメータ感覚。",
        is_new=True,
        tags=("slider", "smile"),
    ),
    FigureSpec(
        "cos_convergence",
        "volatility",
        "COS 法の密度収束",
        "特性関数から復元した密度が項数 N を増やすと基準へ収束。少数項で十分(Fang-Oosterlee)。",
        pv.plotly_cos_density_convergence,
        practice="特性関数 → 密度を少数項で復元。Heston 高速値付けの心臓部。",
        is_new=True,
        tags=("slider", "fourier"),
    ),
    FigureSpec(
        "sabr_smile",
        "volatility",
        "SABR スマイルと vol-of-vol",
        "Hagan 公式の IV スマイル。ν で曲率、ρ<0 で傾き、ATM を揃えた β 比較でバックボーンのスキューも見える。",
        pv.plotly_sabr_smile,
        practice="金利スマイルの市場標準。ブローカー画面が SABR パラメータで気配を出す理由。",
        is_new=True,
        tags=("slider", "smile", "sabr"),
    ),
    FigureSpec(
        "iv_surface",
        "volatility",
        "Heston IV サーフェス IV(K, T)",
        "COS 価格を逆算した IV をストライク×満期の曲面に。ρ<0 が全満期を株式スキューへ傾け、満期とともにスマイルが平坦化。",
        pv.plotly_iv_surface,
        practice="デスクが毎朝見るボラサーフェスそのもの。スマイルと期間構造を1枚で掴むカリブレーションの出発点。",
        is_new=True,
        tags=("slider", "surface", "smile"),
    ),
    FigureSpec(
        "smile_model_risk",
        "volatility",
        "同じスマイル、違う Greeks — β のモデルリスク",
        "同一の市場スマイルに β=0/0.5/1 の SABR を再校正。フィットは市場点に重なり区別不能なのに、Δ・Γ・ベガが揃って乖離する。",
        pv.plotly_smile_model_risk,
        practice="市場価格が決めてくれない選択(β)がヘッジ全体を決める — Hagan (2002) の中心命題。モデル検証・リザーブの根拠。",
        is_new=True,
        tags=("smile", "sabr", "greeks"),
    ),
    FigureSpec(
        "sabr_greeks_by_param",
        "volatility",
        "SABR パラメータを動かすと Greeks はどう変わるか",
        "α/β/ρ/ν をドロップダウンで選び、5値スイープの Δ・Γ・V・Θ 曲線。全スイープが基準線(accent)を通り、各ノブが Greeks をどう引き剥がすかが見える。",
        pv.plotly_sabr_greeks_by_param,
        practice="どのパラメータを動かすと、どの Greek が・どのストライクで動くか。β 以外(α・ρ・ν)も含めたヘッジの依存構造を一望する。",
        is_new=True,
        tags=("dropdown", "sabr", "greeks"),
    ),
    FigureSpec(
        "sabr_rho_nu_smile_greeks",
        "volatility",
        "ρ と ν はスマイルをどう変え、Greeks がどう追随するか",
        "行=ρ/ν、列=スマイル IV・Δ・Γ の 5値スイープ。ρ はスマイルを傾けΔを歪め、ν は翼を持ち上げΓを膨らませる — スマイル変化→ヘッジ変化の連鎖。",
        pv.plotly_sabr_rho_nu_smile_greeks,
        practice="β の影に隠れがちな ρ・ν の役割。スマイルの傾き・曲率を動かすと、ヘッジのどこがどう崩れるかを左右に並べて読む。",
        is_new=True,
        tags=("sabr", "smile", "greeks"),
    ),
    FigureSpec(
        "sabr_param_greeks",
        "volatility",
        "どのパラメータがどの Greek に効くか",
        "標準化バンプ(α+1volpt/β+0.1 ATM揃え/ρ+0.1/ν+0.1)× Δ・Γ・V・Θ の変化率ヒートマップ。行内の赤青混在＝トレードオフ。K スライダー。",
        pv.plotly_sabr_param_greeks,
        practice="キャリブレーションの自由度はヘッジの自由度。あるGreekを合わせると別のGreekがずれる構造を、バンプ前に地図で知る。",
        is_new=True,
        tags=("slider", "sabr", "greeks"),
    ),
    # extra coverage -----------------------------------------------------
    FigureSpec(
        "gamma_surface",
        "options_core",
        "ガンマ曲面 Γ(S, T)",
        "ガンマはストライク近傍・満期直前で尖る。ATM オプションが満期間際に最もヘッジしにくい理由。",
        pv.plotly_gamma_surface,
        practice="ATM・満期直前で最もヘッジしにくい領域が一目で分かる。在庫の危険ゾーンの地図。",
        is_new=True,
        tags=("surface", "greeks"),
    ),
    FigureSpec(
        "greeks_map",
        "options_core",
        "グリークスの地図(ベガ・セータ・バンナ・ボンマ)",
        "S×残存 T のヒートマップをドロップダウンで切替。ベガ/ボンマは長期に、セータは満期直前 ATM に、バンナは翼に住む。",
        pv.plotly_greeks_map,
        practice="スマイルリスク(バンナ・ボンマ)がブックのどこに溜まるかの地図。ボラデスクのリスクレポートの縮図。",
        is_new=True,
        tags=("dropdown", "greeks"),
    ),
    FigureSpec(
        "bsm_greeks_sensitivity",
        "options_core",
        "Greeks はボラ入力にどう依存するか",
        "Δ・Γ・Θ・V の4面 vs S。ヘッジ入力 σ を動かすと、同じ点 S=K(点線)での Greeks がすべて動く — 入力リスク。",
        pv.plotly_bsm_greeks_sensitivity,
        practice="古い・誤ったボラマークを入れると全ヘッジ比率が狂う。EODマークとリアルタイムヘッジの乖離という日常的リスク。",
        is_new=True,
        tags=("slider", "greeks"),
    ),
    FigureSpec(
        "stop_loss_vs_delta",
        "options_core",
        "ストップロス vs デルタヘッジ",
        "素朴なストップロスは偏り・分散が大きい。デルタヘッジは BSM 価格に締まる(Hull §19.2)。",
        pv.plotly_stop_loss_vs_delta_hedge,
        practice="『直感的に正しそうな』ストップロスが破綻する反面教師。複製の規律がなぜ要るか。",
        is_new=True,
        tags=("slider", "hedging"),
    ),
    FigureSpec(
        "binomial_lattice",
        "numerics",
        "二項木格子と後ろ向き帰納",
        "CRR 格子そのもの。ノードの色がオプション価値、アメリカンの早期行使域が見える(Hull Ch.13)。",
        pv.plotly_binomial_lattice,
        practice="後退帰納とアメリカンの早期行使域を格子上で。エキゾチック評価器の基礎。",
        is_new=True,
        tags=("tree",),
    ),
    FigureSpec(
        "garch_volatility",
        "volatility",
        "ボラのクラスタリング(EWMA/GARCH)",
        "EWMA と GARCH(1,1) の年率ボラ。荒れた時期が固まり、GARCH は長期水準へ平均回帰(Hull Ch.23)。",
        pv.plotly_garch_volatility,
        practice="ボラのクラスタリングと平均回帰。危機時の VaR 過小評価を防ぐ動学。",
        is_new=True,
        tags=("garch",),
    ),
    FigureSpec(
        "garch_term_structure",
        "volatility",
        "GARCH 予測の期間構造",
        "出発が高ボラでも低ボラでも、予測は長期ボラへ平均回帰。ボラの期間構造の素。",
        pv.plotly_garch_term_structure,
        practice="高/低ボラから長期水準への回帰。ボラの期間構造＝満期別オプション値付けの素。",
        is_new=True,
        tags=("garch",),
    ),
    FigureSpec(
        "merton_structural",
        "risk_credit",
        "Merton 構造模型",
        "株式 = 資産のコール。負債・資産ボラを上げるとデフォルト確率が上がる(Hull §24.6)。",
        pv.plotly_merton_structural,
        practice="株価から信用を読む(KMV の distance-to-default)。資産ボラ・レバレッジと PD の関係。",
        is_new=True,
        tags=("slider", "credit"),
    ),
    FigureSpec(
        "portfolio_diversification",
        "risk_credit",
        "分散投資と相関の床",
        "独立なら 1/√N で減るが、相関 ρ があると √ρ·σ の床が残る(分散しきれないリスク)。",
        pv.plotly_portfolio_diversification,
        practice="分散しきれないリスクの『床』。相関がある限り 1/√N では消えない。",
        is_new=True,
        tags=("risk",),
    ),
    FigureSpec(
        "yield_curve",
        "rates_swaps",
        "イールドカーブとフォワード",
        "順イールドではフォワードがゼロ金利の上、逆イールドでは下に来る(Hull Ch.4)。",
        pv.plotly_yield_curve,
        practice="順/逆イールドとフォワードの関係。将来金利の市場予想の読み取り。",
        is_new=True,
        tags=("slider", "rates"),
    ),
    FigureSpec(
        "bond_convexity",
        "rates_swaps",
        "債券の価格-利回りとコンベクシティ",
        "価格-利回り曲線は凸。デュレーション(接線)が捉え損なう曲率がコンベクシティ(Hull Ch.4)。",
        pv.plotly_bond_convexity,
        practice="デュレーション(接線)が捉え損なう曲率。債券リスク管理の基本量。",
        is_new=True,
        tags=("rates",),
    ),
    FigureSpec(
        "swap_value",
        "rates_swaps",
        "金利スワップの価値と par レート",
        "受取固定スワップ価値は固定金利に対して線形で、par スワップレートでちょうど 0(Hull Ch.7)。",
        pv.plotly_swap_value,
        practice="受取固定スワップ価値は固定金利に線形、par で 0。世界最大級のデリバ市場の評価。",
        is_new=True,
        tags=("rates", "swap"),
    ),
    FigureSpec(
        "barrier_knockout",
        "exotics",
        "ノックアウト・バリアコール",
        "バリア H が原資産に近づくほどノックアウトしやすく、価値が 0 へ崩れる(Hull §26.9)。",
        pv.plotly_barrier_knockout,
        practice="バリアが近いほど価値が 0 へ。為替仕組商品の定番、ヘッジ難所の可視化。",
        is_new=True,
        tags=("slider", "exotic"),
    ),
    FigureSpec(
        "asian_vs_european",
        "exotics",
        "アジアン vs ヨーロピアン",
        "平均価格は終端価格よりボラが低い → アジアンはヨーロピアンより割安(Hull §26.12)。",
        pv.plotly_asian_vs_european,
        practice="平均はブレが小さい → アジアンは割安。商品・為替の実需に合う構造。",
        is_new=True,
        tags=("exotic",),
    ),
]


_FRONTIER_SPECS = (
    (
        "ml_price_error",
        "ml_derivatives",
        "ML価格誤差サーフェス",
        "moneyness×maturityで平均値に隠れる局所誤差を確認。",
        "surrogateの危険領域を配置前に特定する。",
    ),
    (
        "ml_greek_error",
        "ml_derivatives",
        "Differential MLのGreek誤差",
        "Delta/Gammaの誤差を同じsplitで比較。",
        "価格精度だけでなくhedge入力の品質を検証する。",
    ),
    (
        "ml_hard_violations",
        "ml_derivatives",
        "soft lossとhard無裁定検査",
        "penalty前後の違反件数をhard checkで測る。",
        "soft lossをarbitrage-freeの証明と取り違えない。",
    ),
    (
        "ml_speed",
        "ml_derivatives",
        "teacherとsurrogateのbreak-even",
        "batch size別のCPU latency。",
        "較正内の反復呼出しで近似器が効く規模を判断する。",
    ),
    (
        "surface_fit",
        "ml_derivatives",
        "hard-constrained IV fit",
        "市場surfaceと制約付きfitを満期別に重ねる。",
        "repricingとsurface shapeを同時に監視する。",
    ),
    (
        "surface_identifiability",
        "ml_derivatives",
        "識別性とrepricing誤差",
        "同じ価格誤差でもparameter errorが異なる。",
        "parameter解釈よりrepricing riskを優先すべき場面を示す。",
    ),
    (
        "surface_arbitrage",
        "ml_derivatives",
        "fitと無裁定のtrade-off",
        "unconstrained/hard surfaceの形状診断。",
        "見かけのfit改善が静的裁定を生まないか検査する。",
    ),
    (
        "variance_consistency",
        "ml_derivatives",
        "IVとvariance termの同時較正",
        "IV-onlyとjoint lossの期間構造。",
        "VIX系商品とSPX smileの整合を確認する。",
    ),
    (
        "forecast_paths",
        "ml_derivatives",
        "leakage-free RV forecast",
        "Log-HARと小型Transformerを同じwalk-forward窓で比較。",
        "複雑モデルを単純baselineより先に採用しない。",
    ),
    (
        "forecast_metrics",
        "ml_derivatives",
        "forecast metricと不確実性",
        "RMSEとQLIKEをモデル別に比較。",
        "metric選択で順位が変わるmodel riskを可視化する。",
    ),
    (
        "hedge_pnl",
        "ml_derivatives",
        "common-path hedge P&L",
        "同じscenarioでstrategy別P&L分布を比較。",
        "予測改善が実際のhedging errorへ届くか確認する。",
    ),
    (
        "hedge_economics",
        "ml_derivatives",
        "CVaRとturnover",
        "tail riskと取引量を同時表示。",
        "低誤差でも過剰売買なら採用しない。",
    ),
    (
        "spx_joint_fit",
        "volatility_frontiers",
        "SPX IV joint fit",
        "PDV/AFVのSPX smile fit。",
        "VIXも同時に合う状態モデルを選ぶ。",
    ),
    (
        "vix_joint_fit",
        "volatility_frontiers",
        "VIX term structure joint fit",
        "VIX futures proxyの期間構造。",
        "SPXだけの過学習をVIX側から検査する。",
    ),
    (
        "joint_model_error",
        "volatility_frontiers",
        "PDV・AFV・rough・quintic比較",
        "SPX/VIX誤差を同じ表で比較。",
        "単一市場のfitだけでモデルを決めない。",
    ),
    (
        "nested_mc_speed",
        "volatility_frontiers",
        "nested MCとsurrogate",
        "batch size別のteacher/surrogate速度。",
        "joint calibrationの計算予算を見積もる。",
    ),
    (
        "zero_dte_clock",
        "volatility_frontiers",
        "0DTE variance clock",
        "暦時間と異なる日中varianceの進み方。",
        "open/closeへ集中するriskを正しい時計で測る。",
    ),
    (
        "zero_dte_jump",
        "volatility_frontiers",
        "scheduled jump intensity",
        "event日と非event日を分離。",
        "FOMC等の既知時刻riskを通常拡散へ混ぜない。",
    ),
    (
        "zero_dte_expiry",
        "volatility_frontiers",
        "隣接expiryのtotal variance",
        "満期を跨ぐtotal variance consistency。",
        "0DTE quoteのcalendar arbitrageを検査する。",
    ),
    (
        "zero_dte_ood",
        "volatility_frontiers",
        "時刻別price/Greek OOD",
        "open/midday/event/closeの誤差。",
        "平均誤差が隠すevent windowを監視する。",
    ),
    (
        "rfr_compounding",
        "rates_swaps",
        "RFR離散複利と連続極限",
        "daily compoundingとcontinuous limitを比較。",
        "lookback/lockout等の規約実装を手計算で検査する。",
    ),
    (
        "rfr_convexity",
        "rates_swaps",
        "futures-forward convexity",
        "満期別convexity adjustment。",
        "futures quoteをforwardと同一視しない。",
    ),
    (
        "rfr_smile",
        "rates_swaps",
        "Bachelierとshifted SABR",
        "負金利を含むnormal/shifted smile。",
        "近似式のwing・long maturity model riskを見る。",
    ),
    (
        "rfr_delta",
        "rates_swaps",
        "sticky-strikeとBartlett delta",
        "二つのhedge conventionの誤差。",
        "smile moveを含むdelta選択を経済損失で比べる。",
    ),
    (
        "perpetual_prices",
        "crypto_market",
        "index・mark・last price",
        "三つの価格stateをstress pathで分離。",
        "清算とfundingの参照価格混同を防ぐ。",
    ),
    (
        "liquidation_waterfall",
        "crypto_market",
        "insurance fundとADL",
        "清算損失のwaterfallを追跡。",
        "fund枯渇後のsocialized lossを可視化する。",
    ),
    (
        "crypto_solvency",
        "crypto_market",
        "solvency ledger",
        "equity/liabilityのstress推移。",
        "全cash flowが保存則に合うか確認する。",
    ),
    (
        "amm_lvr",
        "crypto_market",
        "AMM LVRとfee補償",
        "LVR・固定fee・dynamic feeを分離。",
        "fee収益をLVR削減と取り違えない。",
    ),
    (
        "carbon_smile",
        "climate_energy",
        "carbon GBMとSV+jump",
        "jump riskがcarbon option smileへ与える影響。",
        "return/variance/jump premiumを分けて感応度管理する。",
    ),
    (
        "weather_paths",
        "climate_energy",
        "temperature OUとfOU",
        "seasonality・短期平均回帰・long memory。",
        "weather payoffの期間依存をモデル別に見る。",
    ),
    (
        "weather_basis",
        "climate_energy",
        "station/location basis risk",
        "距離とindex mismatchの誤差。",
        "非取引可能な現地weather riskの残差を測る。",
    ),
    (
        "ppa_risk",
        "climate_energy",
        "PPA shape・volume・profile risk",
        "CVaRとhedge residualをrisk別に比較。",
        "fair valueとcash-flow-at-riskを別々に報告する。",
    ),
)

FIGURES.extend(
    FigureSpec(
        figure_id,
        book,
        title,
        blurb,
        ff.FRONTIER_BUILDERS[figure_id],
        practice=practice,
        is_new=True,
        tags=("a5-a8", "artifact"),
    )
    for figure_id, book, title, blurb, practice in _FRONTIER_SPECS
)


# Beyond A5--A8: inflation/JGBi (vol 26) and the risk desk (vol 27), also
# artifact-backed and read via ``frontier_figures``.
_BEYOND_SPECS = (
    (
        "inflation_curves",
        "rates_swaps",
        "名目・実質割引カーブ",
        "名目と実質の割引factorを満期別に。両者の比がbreakeven inflationを決める。",
        "名目・実質カーブからBEIを読む。インフレ連動債値付けの出発点。",
    ),
    (
        "inflation_swaps",
        "rates_swaps",
        "ゼロクーポンインフレスワップの再評価",
        "committed ZCIS quoteと再評価値を満期別に比較。再評価誤差は恒等式でゼロ。",
        "市場ZCISからインフレカーブを較正した整合性の検算。",
    ),
    (
        "jgbi_floor",
        "rates_swaps",
        "JGBiデフレフロアとインフレボラ",
        "元本フロア価値をインフレボラ別に。analyticは単調増加、MCと標準誤差内で一致。",
        "デフレ時の元本保証(フロア)の価値。ボラが上がるほど厚くなるオプション価値。",
    ),
    (
        "jgbi_bei",
        "rates_swaps",
        "raw vs フロア調整後BEI",
        "生のbreakeven inflationと、デフレフロアを織り込んだ調整後BEIの差。",
        "フロア(オプション性)を無視した素朴なBEIが割高評価になる点の可視化。",
    ),
    (
        "var_traffic_light",
        "risk_management",
        "Baselトラフィックライトと資本乗数",
        "超過回数ごとの二項ゾーン(緑/黄/赤)と資本乗数のステップ。250日99%の枠組み。",
        "バックテスト超過が資本add-onへ翻訳される規制の仕組みを一望する。",
    ),
    (
        "fhs_vs_hs_coverage",
        "risk_management",
        "FHS vs 素朴HSのVaRカバレッジ",
        "ローリングVaR予測(HS/FHS)と違反日。FHSは条件付ボラで違反率を1%へ近づける。",
        "危機時のVaR過小評価をFHSが是正する様子。カバレッジ改善の実証。",
    ),
    (
        "gpd_tail_fit",
        "risk_management",
        "GPDテールフィットと平均超過",
        "経験VaR ladderとGPD(POT)フィット分位、横に平均超過プロット。",
        "希少テール(0.1%)の外挿。経験分位が尽きる領域をEVTで埋める。",
    ),
    (
        "risk_allocation_bars",
        "risk_management",
        "コンポーネントVaR/ESの配賦",
        "資産別のcomponent VaRとES。Euler配賦で合計はポート全体に厳密一致(加法性)。",
        "リスク限度をデスク別に割り当てる。合計がポート値に一致する配賦の実務。",
    ),
)

FIGURES.extend(
    FigureSpec(
        figure_id,
        book,
        title,
        blurb,
        ff.FRONTIER_BUILDERS[figure_id],
        practice=practice,
        is_new=True,
        tags=("beyond-hull", "artifact"),
    )
    for figure_id, book, title, blurb, practice in _BEYOND_SPECS
)


def figures_for(book: str) -> list[FigureSpec]:
    return [f for f in FIGURES if f.book == book]
