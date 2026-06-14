"""Figure registry for the analytics portal.

Every entry is a :class:`FigureSpec` whose ``build`` callable returns a Plotly
``go.Figure`` by calling one of the textbooks' ``plotly_*`` helpers with small,
seed-fixed demo inputs (no downloads). The same builders power the notebooks, so
the gallery shows exactly what readers meet in the books.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class BookMeta:
    key: str
    title: str
    subtitle: str
    accent: str
    book_index: str  # relative path from site/ to the Jupyter Book index
    nav: str = ""  # short label for the top nav (falls back to title)


# Books with portal figures: drive the gallery, per-book showcase pages, and nav.
BOOKS: dict[str, BookMeta] = {
    "linear_algebra": BookMeta(
        key="linear_algebra",
        title="線形代数の風景",
        subtitle="空間・情報・変換の言語",
        accent="#2563eb",
        book_index="../../linear_algebra/book/_build/html/index.html",
        nav="線形代数",
    ),
    "neural_net": BookMeta(
        key="neural_net",
        title="ニューラルネットの中身",
        subtitle="関数近似から Transformer まで",
        accent="#db2777",
        book_index="../../neural_net/book/_build/html/index.html",
        nav="NN",
    ),
    "bayesian": BookMeta(
        key="bayesian",
        title="ベイズ推定の体験",
        subtitle="信念の更新装置としての統計",
        accent="#16a34a",
        book_index="../../bayesian/book/_build/html/index.html",
        nav="ベイズ",
    ),
    "laplace": BookMeta(
        key="laplace",
        title="ラプラス変換の風景",
        subtitle="時間・複素周波数・システムの言語",
        accent="#7c3aed",
        book_index="../../laplace/book/_build/html/index.html",
        nav="ラプラス",
    ),
    "machine_learning": BookMeta(
        key="machine_learning",
        title="機械学習の実践",
        subtitle="定式化・検証・解釈",
        accent="#ea580c",
        book_index="../../machine_learning/book/_build/html/index.html",
        nav="ML",
    ),
}

# Textbooks without portal figure builders yet: shown as landing cards + book
# links only (no gallery section / showcase page).
LINK_BOOKS: list[BookMeta] = [
    BookMeta(
        "fourier",
        "フーリエ解析の風景",
        "波・周波数・分解の言語",
        "#0891b2",
        "../../fourier/book/_build/html/index.html",
        nav="フーリエ",
    ),
    BookMeta(
        "diffeq_ode",
        "微分方程式 (ODE)",
        "常微分方程式 — 変化と流れ",
        "#ca8a04",
        "../../differential_equation/ode-book/book/_build/html/index.html",
        nav="ODE",
    ),
    BookMeta(
        "diffeq_pde",
        "微分方程式 (PDE)",
        "偏微分方程式 — 場と波",
        "#0d9488",
        "../../differential_equation/pde-book/book/_build/html/index.html",
        nav="PDE",
    ),
]


@dataclass(frozen=True)
class FigureSpec:
    id: str
    book: str
    title: str
    blurb: str
    build: Callable
    is_new: bool = False
    tags: tuple = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# linear_algebra
# ---------------------------------------------------------------------------


def _la_grid_transform():
    import numpy as np
    from la_book import plotting as lviz

    mats = [
        np.eye(2),
        [[1.6, 0.0], [0.0, 0.6]],
        [[1.0, 0.8], [0.0, 1.0]],
        [[0.0, -1.0], [1.0, 0.0]],
        [[1.2, 0.5], [0.3, 1.1]],
    ]
    labels = ["identity", "scale", "shear", "rotate 90", "general"]
    return lviz.plotly_grid_transform(mats, labels, title="Linear maps deform the grid")


def _la_eigen_sweep():
    import numpy as np
    from la_book import plotting as lviz

    return lviz.plotly_eigen_sweep(
        np.array([[2.0, 1.0], [1.0, 2.0]]), title="Au vs u: eigen-directions"
    )


def _la_image_ranks():
    from la_book import plotting as lviz
    from la_book.datasets import make_test_image

    return lviz.plotly_image_ranks(make_test_image(96), [1, 2, 5, 10, 20, 40, 96])


def _la_svd_spectrum():
    from la_book import plotting as lviz
    from la_book.datasets import make_test_image

    return lviz.plotly_svd_spectrum(make_test_image(96), max_k=40)


def _la_yield_curves():
    from la_book import plotting as lviz
    from la_book.datasets import make_yield_curves

    mats, df = make_yield_curves()
    return lviz.plotly_yield_curves(mats, df.values)


def _la_pca_loadings():
    from la_book import plotting as lviz
    from la_book.datasets import make_yield_curves
    from la_book.decompositions import pca_fit

    mats, df = make_yield_curves()
    pca = pca_fit(df.values, n_components=3)
    return lviz.plotly_pca_loadings(mats, pca.components)


def _la_iterative_convergence():
    from la_book import plotting as lviz

    return lviz.plotly_iterative_convergence()


def _la_pagerank():
    from la_book import plotting as lviz

    return lviz.plotly_pagerank()


def _la_gd_quadratic():
    from la_book import plotting as lviz

    return lviz.plotly_gradient_descent_quadratic()


# ---------------------------------------------------------------------------
# neural_net
# ---------------------------------------------------------------------------


def _nn_decision_boundary():
    from nn_textbook import datasets
    from nn_textbook import plotting as nviz

    X, y = datasets.make_moons_dataset(n=240, seed=0)
    return nviz.plotly_decision_boundary(
        X, y, epochs=150, n_frames=12, grid_steps=60, title="MLP decision boundary over training"
    )


def _nn_attention():
    import numpy as np
    from nn_textbook import plotting as nviz

    tokens = ["the", "cat", "sat", "on", "the", "mat"]
    i = np.arange(len(tokens))
    scores = 2.0 * np.exp(-0.5 * (i[:, None] - i[None, :]) ** 2)
    scores[:, 0] += 0.5
    temps = [0.25, 0.5, 1.0, 2.0, 4.0]
    return nviz.plotly_attention_slider(
        tokens, scores, temps, title="Attention sharpness vs temperature"
    )


def _nn_training_curves():
    from nn_textbook import datasets
    from nn_textbook import plotting as nviz
    from nn_textbook.models import MLP
    from nn_textbook.training import train_numpy_mlp

    X, y = datasets.make_moons_dataset(n=300, seed=0)
    configs = [
        ("he, lr=0.3", "he", 0.3),
        ("he, lr=0.05", "he", 0.05),
        ("small init, lr=0.3", "small", 0.3),
    ]
    histories, labels = [], []
    for lab, init, lr in configs:
        model = MLP([2, 32, 32, 2], activation="relu", seed=0, init=init)
        histories.append(train_numpy_mlp(model, X, y, lr=lr, epochs=120, batch_size=32, seed=0))
        labels.append(lab)
    return nviz.plotly_training_curves(
        histories, labels, title="Training loss: init & learning rate"
    )


def _nn_image_slider():
    import numpy as np
    from nn_textbook import plotting as nviz

    rng = np.random.default_rng(0)
    n = 28
    yy, xx = np.mgrid[0:n, 0:n]
    clean = np.exp(-(((xx - 14) / 6) ** 2 + ((yy - 14) / 6) ** 2))
    clean = clean + 0.6 * np.exp(-(((xx - 8) / 2) ** 2 + ((yy - 20) / 2) ** 2))
    noise = rng.standard_normal((n, n))
    betas = np.linspace(0.0, 1.0, 8)
    images = [np.sqrt(1 - b) * clean + np.sqrt(b) * noise for b in betas]
    labels = [f"{b:.2f}" for b in betas]
    return nviz.plotly_image_slider(
        images, labels, title="Forward diffusion: signal -> noise", slider_name="noise level"
    )


def _nn_activations():
    from nn_textbook import plotting as nviz

    return nviz.plotly_activations()


def _nn_hidden_unfolding():
    from nn_textbook import plotting as nviz

    return nviz.plotly_hidden_unfolding()


def _nn_ssm_impulse():
    from nn_textbook import plotting as nviz

    return nviz.plotly_ssm_impulse()


# ---------------------------------------------------------------------------
# bayesian
# ---------------------------------------------------------------------------


def _bayes_posterior_update():
    import numpy as np
    from bayes_textbook import visualization as bviz
    from bayes_textbook.conjugacy import BetaBinomial

    rng = np.random.default_rng(0)
    flips = (rng.random(40) < 0.63).astype(int)
    return bviz.plotly_posterior_update(BetaBinomial(2, 2), flips)


def _bayes_mcmc_trace():
    from bayes_textbook import visualization as bviz
    from bayes_textbook.models import metropolis_hastings

    samples, _rate = metropolis_hastings(
        lambda t: -0.5 * t**2, x0=3.0, n_steps=600, proposal_sd=1.0, seed=0
    )
    return bviz.plotly_mcmc_trace(samples, target=0.0)


def _bayes_posterior_predictive():
    import numpy as np
    from bayes_textbook import visualization as bviz

    rng = np.random.default_rng(1)
    x = np.linspace(-3, 3, 50)
    y = 0.4 * x**3 - x + 0.5 * rng.standard_normal(50)
    return bviz.plotly_posterior_predictive(x, y, degree=3, n_frames=10)


def _bayes_gp_regression():
    from bayes_textbook import visualization as bviz

    return bviz.plotly_gp_regression()


def _bayes_bandit_regret():
    from bayes_textbook import visualization as bviz

    return bviz.plotly_bandit_regret()


def _bayes_gibbs_path():
    from bayes_textbook import visualization as bviz

    return bviz.plotly_gibbs_path()


# ---------------------------------------------------------------------------
# laplace
# ---------------------------------------------------------------------------


def _lap_pole_response():
    from laplace_book import plotting as lp

    return lp.plotly_pole_response_slider()


def _lap_step_zeta():
    from laplace_book import plotting as lp

    return lp.plotly_step_response_slider()


def _lap_pole_zero():
    from laplace_book import plotting as lp

    return lp.plotly_pole_zero()


def _lap_abs_f_surface():
    from laplace_book import plotting as lp

    return lp.plotly_abs_F_surface()


def _lap_root_locus():
    from laplace_book import plotting as lp

    return lp.plotly_root_locus()


def _lap_rlc_step():
    from laplace_book import plotting as lp

    return lp.plotly_rlc_step_slider()


# ---------------------------------------------------------------------------
# machine_learning
# ---------------------------------------------------------------------------


def _ml_model_complexity():
    import numpy as np
    from ml_textbook import plotting as mviz

    rng = np.random.default_rng(0)
    x = np.linspace(-3, 3, 80)
    y = np.sin(1.2 * x) + 0.3 * rng.standard_normal(80)
    return mviz.plotly_model_complexity(x, y)


def _ml_threshold_explorer():
    import numpy as np
    from ml_textbook import plotting as mviz

    rng = np.random.default_rng(0)
    n = 300
    y_true = rng.integers(0, 2, n)
    y_score = np.clip(0.5 + 0.32 * (y_true * 2 - 1) + 0.25 * rng.standard_normal(n), 0.0, 1.0)
    return mviz.plotly_threshold_explorer(y_true, y_score)


FIGURES: list[FigureSpec] = [
    # linear_algebra
    FigureSpec(
        "la_grid_transform",
        "linear_algebra",
        "行列はグリッドを変形する",
        "2x2 行列を切り替えると単位グリッドがどう曲がるかを見る。スケール・せん断・回転・一般の写像。",
        _la_grid_transform,
        tags=("slider",),
    ),
    FigureSpec(
        "la_eigen_sweep",
        "linear_algebra",
        "固有方向を探す",
        "単位ベクトル u を回しながら Au を観察。Au が u と平行になる向き = 固有方向。",
        _la_eigen_sweep,
        tags=("slider",),
    ),
    FigureSpec(
        "la_image_ranks",
        "linear_algebra",
        "低ランク画像近似",
        "SVD による rank-k 近似。少ない k でも画像がどこまで復元できるか(圧縮率つき)。",
        _la_image_ranks,
        tags=("slider", "svd"),
    ),
    FigureSpec(
        "la_svd_spectrum",
        "linear_algebra",
        "特異値スペクトルと累積エネルギー",
        "各特異値のエネルギー寄与と累積。なぜ小さな k で十分かを定量的に示す。",
        _la_svd_spectrum,
        is_new=True,
        tags=("slider", "svd"),
    ),
    FigureSpec(
        "la_yield_curves",
        "linear_algebra",
        "金利カーブのパネル",
        "合成イールドカーブの時系列。3つの潜在因子(Level/Slope/Curvature)が動かしている。",
        _la_yield_curves,
        tags=("finance",),
    ),
    FigureSpec(
        "la_pca_loadings",
        "linear_algebra",
        "PCA ローディング(金利)",
        "カーブ群の主成分。第1=水準、第2=傾き、第3=曲率という古典的分解。",
        _la_pca_loadings,
        tags=("finance", "pca"),
    ),
    FigureSpec(
        "la_iterative_convergence",
        "linear_algebra",
        "反復ソルバの収束比較",
        "Jacobi・Gauss-Seidel・共役勾配の残差を反復ごとに対数で。CG が桁違いに速い。",
        _la_iterative_convergence,
        is_new=True,
        tags=("convergence",),
    ),
    FigureSpec(
        "la_pagerank",
        "linear_algebra",
        "PageRank のべき乗反復",
        "Web グラフの PageRank が反復で各ページの重要度に収束する様子(合計 1)。",
        _la_pagerank,
        is_new=True,
        tags=("slider", "graph"),
    ),
    FigureSpec(
        "la_gd_quadratic",
        "linear_algebra",
        "二次形式上の勾配降下",
        "異方的な谷の等高線上を勾配降下が最小へジグザグ進む(スライダーで 1 歩ずつ)。",
        _la_gd_quadratic,
        is_new=True,
        tags=("slider", "optimization"),
    ),
    # neural_net
    FigureSpec(
        "nn_decision_boundary",
        "neural_net",
        "学習が進むと決定境界が育つ",
        "NumPy MLP を学習させ、エポックごとの P(class 1) をヒートマップで。境界が moons を包む様子。",
        _nn_decision_boundary,
        is_new=True,
        tags=("slider", "training"),
    ),
    FigureSpec(
        "nn_attention",
        "neural_net",
        "注意の鋭さ ∝ 1/温度",
        "softmax(scores / T) を温度 T で掃引。低温で鋭く一点集中、高温で一様に。",
        _nn_attention,
        tags=("slider", "attention"),
    ),
    FigureSpec(
        "nn_training_curves",
        "neural_net",
        "初期化と学習率で収束が変わる",
        "He/小初期化・学習率違いの loss 曲線。スライダーがエポック窓を広げ、降下の速さを比較。",
        _nn_training_curves,
        is_new=True,
        tags=("slider", "training"),
    ),
    FigureSpec(
        "nn_image_slider",
        "neural_net",
        "前向き拡散:信号→ノイズ",
        "クリーン画像に少しずつノイズを足す拡散過程。生成モデルが逆向きに辿る道。",
        _nn_image_slider,
        tags=("slider", "diffusion"),
    ),
    FigureSpec(
        "nn_activations",
        "neural_net",
        "活性化関数とその微分",
        "ReLU/LeakyReLU/sigmoid/tanh を切替。sigmoid・tanh は端で微分が消える(勾配消失)。",
        _nn_activations,
        is_new=True,
        tags=("slider", "activations"),
    ),
    FigureSpec(
        "nn_hidden_unfolding",
        "neural_net",
        "ネットがクラスを解きほぐす",
        "入力では分離不能な同心円を、学習が進むと出力空間で線形分離可能に変える様子。",
        _nn_hidden_unfolding,
        is_new=True,
        tags=("slider", "representation"),
    ),
    FigureSpec(
        "nn_ssm_impulse",
        "neural_net",
        "線形 SSM の記憶長 ∝ 減衰",
        "対角線形 SSM のインパルス応答 A_diag**t。値が大きいほど長い記憶(S4/Mamba の核)。",
        _nn_ssm_impulse,
        is_new=True,
        tags=("slider", "ssm"),
    ),
    # bayesian
    FigureSpec(
        "bayes_posterior_update",
        "bayesian",
        "信念の更新:事前→尤度→事後",
        "コイン投げを足すたびに事後分布が立ち上がり鋭くなる。ベータ二項の閉形式。",
        _bayes_posterior_update,
        is_new=True,
        tags=("slider",),
    ),
    FigureSpec(
        "bayes_mcmc_trace",
        "bayesian",
        "MCMC の収束:トレース+移動平均",
        "鎖を一歩ずつ見せると、生の軌跡は揺れ続けるのに移動平均は真値へ落ち着く。",
        _bayes_mcmc_trace,
        is_new=True,
        tags=("slider", "mcmc"),
    ),
    FigureSpec(
        "bayes_posterior_predictive",
        "bayesian",
        "事後予測:データで帯が締まる",
        "ベイズ多項式回帰。データ点を増やすと信頼帯・予測帯が目に見えて細くなる。",
        _bayes_posterior_predictive,
        is_new=True,
        tags=("slider", "regression"),
    ),
    FigureSpec(
        "bayes_gp_regression",
        "bayesian",
        "ガウス過程:データ付近で帯が縮む",
        "GP 事後の平均と ±2σ 帯。観測を増やすと点の近くで不確実性が締まり、空白では広いまま。",
        _bayes_gp_regression,
        is_new=True,
        tags=("slider", "gp"),
    ),
    FigureSpec(
        "bayes_bandit_regret",
        "bayesian",
        "累積リグレット:Thompson vs ε-greedy",
        "Thompson サンプリングは事後から賢く探索し、ε-greedy より累積後悔が低い。",
        _bayes_bandit_regret,
        is_new=True,
        tags=("bandit",),
    ),
    FigureSpec(
        "bayes_gibbs_path",
        "bayesian",
        "Gibbs が相関ガウスを探索",
        "1 座標ずつ更新する Gibbs サンプラが、相関の尾根に沿ってジグザグに分布を埋める。",
        _bayes_gibbs_path,
        is_new=True,
        tags=("slider", "mcmc"),
    ),
    # laplace
    FigureSpec(
        "lap_pole_response",
        "laplace",
        "σ が極を虚軸の向こうへ運ぶ",
        "複素周波数 s=σ+iω の実部 σ をスライダーで動かすと、応答 e^{σt}cos(ωt) が減衰→持続→発散と変わる。",
        _lap_pole_response,
        is_new=True,
        tags=("slider",),
    ),
    FigureSpec(
        "lap_step_zeta",
        "laplace",
        "2次系ステップ応答 vs 減衰比 ζ",
        "ζ を掃引。<1 で行き過ぎて振動、=1 で最速、>1 でゆっくり。すべて極の位置が決める。",
        _lap_step_zeta,
        is_new=True,
        tags=("slider",),
    ),
    FigureSpec(
        "lap_pole_zero",
        "laplace",
        "極・零点と s 平面",
        "H(s) の極(×)と零点(○)。極が左半面にあれば安定、虚軸を越えると不安定。",
        _lap_pole_zero,
        is_new=True,
        tags=("poles",),
    ),
    FigureSpec(
        "lap_abs_f_surface",
        "laplace",
        "|F(s)| は極で尖る地形",
        "s 平面上の |F(s)| を高さとして描くと、極が山のように尖る(回して確認)。",
        _lap_abs_f_surface,
        is_new=True,
        tags=("surface",),
    ),
    FigureSpec(
        "lap_root_locus",
        "laplace",
        "根軌跡:ゲインで極が動く",
        "ループゲイン k を上げると閉ループ極が軌跡を描く。虚軸を越えるゲインで不安定化する。",
        _lap_root_locus,
        is_new=True,
        tags=("locus",),
    ),
    FigureSpec(
        "lap_rlc_step",
        "laplace",
        "RLC のステップ応答 vs R",
        "直列 RLC の抵抗 R を変えると、underdamped → critical → overdamped と過渡が切り替わる。",
        _lap_rlc_step,
        is_new=True,
        tags=("slider", "circuit"),
    ),
    # machine_learning
    FigureSpec(
        "ml_model_complexity",
        "machine_learning",
        "モデル複雑度と過適合",
        "多項式の次数を上げると訓練誤差は下がり続けるが、テスト誤差は U 字。バイアス-分散トレードオフ。",
        _ml_model_complexity,
        is_new=True,
        tags=("slider", "overfitting"),
    ),
    FigureSpec(
        "ml_threshold_explorer",
        "machine_learning",
        "閾値で動く適合率・再現率",
        "分類の判定閾値を動かすと、適合率・再現率・F1 がトレードオフしながら変化する。",
        _ml_threshold_explorer,
        is_new=True,
        tags=("slider", "classification"),
    ),
]


def figures_for(book: str) -> list[FigureSpec]:
    return [f for f in FIGURES if f.book == book]
