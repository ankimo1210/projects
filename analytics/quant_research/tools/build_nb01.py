"""Builder for notebook 01: projections and least squares."""

from nbkit import code, md

cells = [
    md(r"""
# 01. Week 1 — 射影としての最小二乗

> 回帰係数を計算する前に、どの空間へ何を射影しているかを見る。

## 学習目標

- 列空間、null space、rankを最小二乗と結びつける
- normal equationsと残差直交性を導出する
- OLS、weighted least squares、最小norm解を使い分ける
- overdetermined、underdetermined、rank欠損を診断する
- 明示的逆行列を教育上の悪いbaselineとして位置づける

## 前提知識

- 行列積、転置、ベクトルの2-norm
- 一変数・多変数の微分
- NumPy配列の基本操作
"""),
    code("""
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from scipy import linalg as scipy_linalg

from quant_textbook import make_regression_dataset, solve_least_squares

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260809
"""),
    md(r"""
## 1. 直感 — 観測を列空間へ落とす

$X\in\mathbb{R}^{n\times p}$ の列の線形結合で作れるベクトル全体が $\operatorname{col}(X)$ である。モデルが出せる予測 $X\beta$ は必ずこの空間にある。

観測 $y$ が列空間の外にあると完全一致はできない。そこで最も近い点 $\hat y=X\hat\beta$ を探す。残差 $r=y-\hat y$ が列空間に直交するとき、これ以上どの列方向へ動いても距離は短くならない。
"""),
    code("""
# A two-dimensional geometric example: project y onto span(x).
x_direction = np.array([2.0, 1.0])
observed = np.array([1.0, 2.5])
coefficient = (x_direction @ observed) / (x_direction @ x_direction)
fitted = coefficient * x_direction
residual = observed - fitted

fig = go.Figure()
for vector, name, color in [
    (observed, "observed y", "#1f77b4"),
    (fitted, "projection", "#2ca02c"),
    (residual, "residual", "#d62728"),
]:
    origin = fitted if name == "residual" else np.zeros(2)
    fig.add_scatter(
        x=[origin[0], origin[0] + vector[0]],
        y=[origin[1], origin[1] + vector[1]],
        mode="lines+markers",
        name=name,
        line={"width": 4, "color": color},
    )
line_scale = np.linspace(-0.3, 1.5, 50)
fig.add_scatter(
    x=line_scale * x_direction[0],
    y=line_scale * x_direction[1],
    mode="lines",
    name="col(X)",
    line={"dash": "dash", "color": "gray"},
)
fig.update_layout(
    title="Orthogonal projection onto a one-dimensional column space",
    xaxis_title="coordinate 1",
    yaxis_title="coordinate 2",
    yaxis_scaleanchor="x",
    template="plotly_white",
)
fig.show()

print("x.T @ residual:", float(x_direction @ residual))
"""),
    md(r"""
## 2. Normal equationsの導出

目的関数を

$$
L(\beta)=\lVert y-X\beta\rVert_2^2=(y-X\beta)^\top(y-X\beta)
$$

とする。展開して微分すると

$$
\nabla_\beta L(\beta)=-2X^\top y+2X^\top X\beta
$$

である。停留条件から

$$
X^\top X\hat\beta=X^\top y
$$

を得る。これがnormal equationsである。同じ式を $r=y-X\hat\beta$ へ戻せば

$$
X^\top r=0
$$

となり、幾何学的な直交性と解析的な一階条件が一致する。

$X$ がfull column rankなら $X^\top X$ は正定値で解は一意である。しかし式が書けることと、`inv(X.T @ X)` を計算すべきことは別である。Week 2で見るように、この経路は条件数を実質的に二乗する。
"""),
    md(r"""
## 3. APIでsolverを比較する

この教材の `solve_least_squares` は係数だけでなく、rank、条件数、残差normを返す。solverの結果を必ず診断値と一緒に読む。
"""),
    code("""
regression = make_regression_dataset(
    n_samples=100,
    n_features=4,
    noise_std=0.15,
    condition_number=20.0,
    seed=RANDOM_SEED,
)

results = {
    method: solve_least_squares(regression.X, regression.y, method=method)
    for method in ["inverse", "normal", "qr", "svd"]
}

for method, result in results.items():
    diagnostics = result.diagnostics
    print(
        f"{method:>7s} | rank={diagnostics.rank} "
        f"cond={diagnostics.condition_number:8.2f} "
        f"residual={diagnostics.residual_norm:.6f}"
    )
"""),
    code("""
reference = results["svd"]
orthogonality = regression.X.T @ reference.residuals
column_norms = np.linalg.norm(regression.X, axis=0)
residual_norm = np.linalg.norm(reference.residuals)
orthogonality_scale = column_norms * residual_norm
scale_aware_orthogonality = np.divide(
    np.abs(orthogonality),
    orthogonality_scale,
    out=np.zeros_like(orthogonality),
    where=orthogonality_scale > 0.0,
)

fig = go.Figure(
    go.Bar(
        x=[f"column {index}" for index in range(regression.X.shape[1])],
        y=np.abs(orthogonality),
    )
)
fig.update_layout(
    title="Least-squares residual orthogonality check",
    xaxis_title="Design column",
    yaxis_title="absolute inner product",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()

print("max |X.T @ residual|:", np.max(np.abs(orthogonality)))
print("max scale-aware orthogonality:", np.max(scale_aware_orthogonality))
"""),
    md(r"""
絶対値だけでは、列や目的変数の単位を変えると判定も変わる。そこで各列について

$$
\eta_{\perp,j}
=\frac{|x_j^\top r|}{\lVert x_j\rVert_2\lVert r\rVert_2}
$$

も記録する。これは列と残差が作る角度のcosineの絶対値で、列ごとのscale変更に不変である。分母が0の完全fitは別扱いにする。棒と $\eta_\perp$ が丸め誤差に照らして小さければ、残差は数値的に列空間と直交している。ただし、これだけでモデルが正しいとは言えない。欠落変数や目的変数の定義は線形代数の診断からは分からない。
"""),
    md(r"""
## 4. Weighted least squares

観測ごとの精度が異なるとき、対角重み $W=\operatorname{diag}(w_1,\ldots,w_n)$ を置き

$$
L_W(\beta)=(y-X\beta)^\top W(y-X\beta)
$$

を最小にする。微分すれば

$$
X^\top W X\hat\beta=X^\top W y
$$

となる。$W=C^\top C$ と分解できれば、$CX$ と $Cy$ の通常の最小二乗である。

bid–ask spreadを重みに使う場合、狭いspreadの観測ほど信頼するという**研究上の仮定**を置いている。数値手法がその仮定を正当化するわけではない。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
heteroskedastic_scale = np.linspace(0.05, 0.80, regression.X.shape[0])
noisy_y = regression.X @ regression.coefficients + rng.normal(
    scale=heteroskedastic_scale
)
precision_weights = 1.0 / heteroskedastic_scale**2

ols = solve_least_squares(regression.X, noisy_y, method="qr")
wls = solve_least_squares(
    regression.X,
    noisy_y,
    method="qr",
    weights=precision_weights,
)

print("OLS coefficient error:", np.linalg.norm(ols.coefficients - regression.coefficients))
print("WLS coefficient error:", np.linalg.norm(wls.coefficients - regression.coefficients))
print("WLS weighted residual norm:", wls.diagnostics.weighted_residual_norm)
"""),
    md(r"""
この1回の乱数実験でWLSが勝っても一般結論にはならない。重みが真の分散の逆数に比例するようデータ生成したため、WLSが有利になる設計である。複数seedで係数誤差の分布を比べるのが標準演習となる。
"""),
    md(r"""
## 5. Underdeterminedとrank欠損

$n<p$ では方程式を満たす係数が複数あり得る。SVDによるMoore–Penrose pseudoinverseは、その中から2-normが最小の解を選ぶ。

rank欠損でも同様に、null space方向 $z\in\operatorname{null}(X)$ を加えた

$$
X(\hat\beta+z)=X\hat\beta
$$

は同じ予測を返す。係数を「効果」として読む前に、解の一意性を確認しなければならない。

| Case | Shape / rank | Exact solution | Least-squares coefficient |
|---|---|---|---|
| full-rank square | $n=p=r$ | 存在すれば一意 | 一意 |
| overdetermined | $n>p$, $r=p$ | 通常は存在しない | 一意 |
| underdetermined | $n<p$, $r=n$ | 存在すれば無数 | 最小normなど選択規則が必要 |
| rank-deficient | $r<\min(n,p)$ | 0個または無数 | 係数は一意でない |

underdeterminedとrank欠損は同義ではない。前者はshape、後者は独立な方向の数を述べる。たとえば $n<p$ でもfull row rankにはなれるが、full column rankにはなれない。
"""),
    code("""
case_designs = {
    "full-rank square": (
        np.array([[2.0, 0.0], [0.0, 1.0]]),
        np.array([2.0, -1.0]),
    ),
    "overdetermined": (
        np.column_stack(
            (
                np.ones(8),
                np.linspace(-1.0, 1.0, 8),
                np.linspace(-1.0, 1.0, 8) ** 2,
            )
        ),
        np.linspace(-1.0, 1.0, 8) + 0.05 * np.arange(8),
    ),
    "underdetermined": (
        np.array([[1.0, 0.0, 1.0, 0.0], [0.0, 1.0, 0.0, 1.0]]),
        np.array([1.0, 2.0]),
    ),
    "rank-deficient": (
        np.array(
            [
                [1.0, 0.0, 1.0],
                [0.0, 1.0, 1.0],
                [1.0, 1.0, 2.0],
                [2.0, -1.0, 1.0],
            ]
        ),
        np.array([1.0, 2.0, 3.0, 0.0]),
    ),
}

print(f"{'case':<20s} {'shape':>9s} {'rank':>5s} {'nullity':>8s} {'residual':>12s}")
for case_name, (case_design, case_target) in case_designs.items():
    case_result = solve_least_squares(case_design, case_target, method="svd")
    case_rank = case_result.diagnostics.rank
    print(
        f"{case_name:<20s} {str(case_design.shape):>9s} {case_rank:5d} "
        f"{case_design.shape[1] - case_rank:8d} "
        f"{case_result.diagnostics.residual_norm:12.3e}"
    )
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
base_column = rng.normal(size=40)
rank_deficient_design = np.column_stack(
    [np.ones(40), base_column, 2.0 * base_column]
)
target = 1.0 + 3.0 * base_column + rng.normal(scale=0.05, size=40)

svd_solution = solve_least_squares(rank_deficient_design, target, method="svd")
print("shape:", rank_deficient_design.shape)
print("rank:", svd_solution.diagnostics.rank)
print("minimum-norm coefficients:", svd_solution.coefficients)

null_direction = np.array([0.0, -2.0, 1.0])
alternative = svd_solution.coefficients + 5.0 * null_direction
print(
    "same predictions after null-space shift:",
    np.allclose(
        rank_deficient_design @ svd_solution.coefficients,
        rank_deficient_design @ alternative,
    ),
)
"""),
    md(r"""
### NumPy / SciPyとの照合

自作SVD解だけを信用せず、独立したAPIとrank、係数norm、予測を照合する。underdetermined・rank欠損では係数ベクトルそのものより、最小norm規約が一致しているかと予測差を確認する。
"""),
    code("""
print(
    f"{'case':<20s} {'ranks':>9s} {'max prediction gap':>20s} "
    f"{'max coefficient gap':>21s}"
)
for case_name, (case_design, case_target) in case_designs.items():
    custom_result = solve_least_squares(case_design, case_target, method="svd")
    numpy_coefficients, _, numpy_rank, _ = np.linalg.lstsq(
        case_design, case_target, rcond=None
    )
    scipy_coefficients, _, scipy_rank, _ = scipy_linalg.lstsq(
        case_design, case_target, cond=None
    )

    coefficient_stack = np.vstack(
        (custom_result.coefficients, numpy_coefficients, scipy_coefficients)
    )
    prediction_stack = coefficient_stack @ case_design.T
    coefficient_gap = np.max(
        np.linalg.norm(coefficient_stack[:, None, :] - coefficient_stack[None, :, :], axis=2)
    )
    prediction_gap = np.max(
        np.linalg.norm(prediction_stack[:, None, :] - prediction_stack[None, :, :], axis=2)
    )
    ranks = f"{custom_result.diagnostics.rank}/{numpy_rank}/{scipy_rank}"
    print(
        f"{case_name:<20s} {ranks:>9s} {prediction_gap:20.3e} "
        f"{coefficient_gap:21.3e}"
    )
"""),
    md(r"""
## 6. 失敗モード — `inv(X.T @ X)`を実装と呼ぶ

明示的逆行列はnormal equationsを文字どおり書いた教育用baselineである。実務solverとして採用しない。

- 逆行列全体を作る必要がなく、`solve` やQRで十分である
- rank欠損では逆行列が存在しない
- ほぼ共線な列では丸め誤差を増幅する
- 残差が小さくても係数誤差が大きい場合を見落とす

このNotebookでは比較対象としてのみ `method="inverse"` を残す。Week 2で悪化させた行列へ適用し、壊れ方を観察する。
"""),
    md(r"""
## 7. 段階別演習

### 基礎

1. normal equationsを成分表示から導出せよ。
2. `X.T @ residuals` を計算し、許容誤差を自分で定義せよ。
3. overdeterminedとunderdeterminedの例を2×3または3×2行列で作れ。

### 標準

4. heteroskedastic実験を50 seedsで繰り返し、OLSとWLSの係数誤差分布をPlotlyで比較せよ。
5. rank欠損行列のnull space方向をSVDから求め、予測が不変であることを確かめよ。
6. QR解とSVD解の差、残差、rankを1つの診断表にまとめよ。

### 研究

7. bid–ask spreadの逆数、逆二乗、上限制約付き重みを比較し、外れ値に対する感度を論じよ。
8. 最小norm解が金融的に望ましい係数を選ぶとは限らない例を構成せよ。
"""),
    md(r"""
## 8. Exit Criteria

- [ ] $X^\top r=0$ を幾何と微分の両方から説明できる
- [ ] full rank、rank欠損、underdeterminedをrankで診断できる
- [ ] WLSの重みが研究上の仮定であることを説明できる
- [ ] 明示的逆行列を本番solverにしない理由を述べられる
- [ ] SVDの最小norm解と予測の一意性を区別できる
"""),
    md(r"""
## 9. 出典

- [MIT OpenCourseWare 18.065 Lecture 9: Four Ways to Solve Least Squares Problems](https://ocw.mit.edu/courses/18-065-matrix-methods-in-data-analysis-signal-processing-and-machine-learning-spring-2018/resources/lecture-9-four-ways-to-solve-least-squares-problems/) — 射影、normal equations、QR、pseudoinverse
- [MIT OpenCourseWare 18.06SC Linear Algebra](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/) — 列空間、null space、直交性
- [NumPy `linalg.lstsq`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html) — over/under-determined、rank欠損を含む最小二乗のAPI仕様
- [SciPy `linalg.lstsq`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.lstsq.html) — LAPACK driverを選べる参照実装

次章では、同じ問題をほぼ共線にして、残差だけでは見えない数値誤差を測る。
"""),
]
