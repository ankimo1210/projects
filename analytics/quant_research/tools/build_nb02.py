"""Builder for notebook 02: factorizations and numerical stability."""

from nbkit import code, md

cells = [
    md(r"""
# 02. Week 2 — 分解と数値安定性

> 方程式を数学的に解けることと、浮動小数点で信頼できる答えを得ることは同じではない。

## 学習目標

- LU、Cholesky、QR、SVDが利用する構造を説明できる
- machine epsilon、条件数、forward error、backward errorを区別する
- normal equationsが2-norm条件数を二乗することを導出・実測する
- Vandermonde基底とGram–Schmidtの直交性喪失を実測する
- 残差、係数誤差、摂動感度を同時に比較する
- QRとSVDの精度・速度・rank診断のtrade-offを説明する

## 前提知識

- Week 1のnormal equationsと残差直交性
- 固有値、特異値を聞いたことがあること
- 相対誤差と対数軸の読み方
"""),
    code("""
import time

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

from quant_textbook import solve_least_squares

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260809
"""),
    md(r"""
## 1. 浮動小数点は有限である

IEEE 754の倍精度では、1の次に表現できる数との差はおよそ

$$
\varepsilon_{\mathrm{mach}}\approx 2.22\times 10^{-16}
$$

である。丸め誤差そのものは小さい。しかし、問題が入力誤差に敏感なら、その小ささは答えの正確さを保証しない。
"""),
    code("""
machine_epsilon = np.finfo(np.float64).eps
print("machine epsilon:", machine_epsilon)
print("1 + eps/2 equals 1:", 1.0 + machine_epsilon / 2.0 == 1.0)
print("1 + eps differs from 1:", 1.0 + machine_epsilon != 1.0)
"""),
    md(r"""
## 2. Conditioningとstability

線形系 $Ax=b$ に小さな $\delta b$ が入ったとき、2-normでは概ね

$$
\frac{\lVert\delta x\rVert_2}{\lVert x\rVert_2}
\lesssim
\kappa_2(A)
\frac{\lVert\delta b\rVert_2}{\lVert b\rVert_2}
$$

である。$\kappa_2(A)=\sigma_{\max}(A)/\sigma_{\min}(A)$ は問題そのものの感度を表す。

- **conditioning:** 問題が入力摂動にどれほど敏感か
- **stability:** algorithmが、近くの入力に対する正確な答えを返すか
- **forward error:** 計算解と真の解の距離
- **backward error:** 計算解を正解にするため、入力をどれだけ変えればよいか

安定なalgorithmでもill-conditionedな問題のforward errorは大きくなり得る。逆に、well-conditionedな問題を不安定なalgorithmで壊すこともある。
"""),
    md(r"""
## 3. なぜnormal equationsは条件数を二乗するか

$X=U\Sigma V^\top$ とする。すると

$$
X^\top X=V\Sigma^2V^\top
$$

なので、$X^\top X$ の最大・最小固有値は $X$ の最大・最小特異値の二乗である。full column rankなら

$$
\kappa_2(X^\top X)
=\frac{\sigma_{\max}(X)^2}{\sigma_{\min}(X)^2}
=\kappa_2(X)^2
$$

となる。normal equationsをCholeskyで正確に解いても、`X.T @ X` を作った時点で感度を悪化させる。Choleskyが悪いのではなく、適用する問題の作り方が悪い。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
left, _ = np.linalg.qr(rng.normal(size=(80, 6)))
right, _ = np.linalg.qr(rng.normal(size=(6, 6)))
singular_values = np.geomspace(1.0, 1e-6, 6)
design = left @ np.diag(singular_values) @ right.T

condition_x = np.linalg.cond(design)
condition_normal = np.linalg.cond(design.T @ design)
print("cond(X):", condition_x)
print("cond(X.T @ X):", condition_normal)
print("ratio to cond(X)^2:", condition_normal / condition_x**2)
"""),
    md(r"""
有限精度では比は厳密に1にならない。特に条件数が極端に大きいと、`X.T @ X` の最小固有値自体が丸め誤差に埋もれる。このずれも実験対象である。
"""),
    md(r"""
### Vandermonde行列 — 基底の選択がconditioningを作る

多項式回帰のraw monomial基底 $1,x,x^2,\ldots,x^d$ はVandermonde行列になる。次数を上げると列が似た形になり、同じ関数を表せても係数推定は急速にill-conditionedになる。これはWeek 4でsplineや正則化を導入する理由の一つである。
"""),
    code("""
sample_points = np.linspace(-1.0, 1.0, 80)
polynomial_degrees = np.arange(1, 19)
vandermonde_conditions = []
for degree in polynomial_degrees:
    vandermonde = np.vander(sample_points, N=degree + 1, increasing=True)
    vandermonde_conditions.append(np.linalg.cond(vandermonde))

fig = go.Figure(
    go.Scatter(
        x=polynomial_degrees,
        y=vandermonde_conditions,
        mode="lines+markers",
    )
)
fig.update_layout(
    title="Raw polynomial bases become ill-conditioned",
    xaxis_title="polynomial degree",
    yaxis_title="cond(V)",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()

for degree in [4, 8, 12, 16]:
    print(f"degree={degree:2d}  cond(V)={vandermonde_conditions[degree - 1]:.3e}")
"""),
    md(r"""
区間を変えたり列をscaleしたりすれば条件数は変わるが、raw係数の意味も変わる。「多項式だから悪い」のではなく、基底・座標・評価領域を含む表現が数値問題を決める。
"""),
    md(r"""
## 4. 分解の役割

| 分解 | 主な構造 | 最小二乗での位置づけ |
|---|---|---|
| LU | 一般の正方線形系 | normal equations以外の線形系で標準的 |
| Cholesky | 対称正定値 | 速いが、$X^\top X$ 経由は感度に注意 |
| QR | 直交基底と上三角 | full-rank最小二乗の第一候補 |
| SVD | 作用方向と特異値 | rank診断・最小norm・最も頑健、計算量は重い |

classical Gram–Schmidtは直感を得るには有用だが、近い列で直交性を失いやすい。実装ではHouseholder QRを標準と考える。
"""),
    md(r"""
### Classicalとmodified Gram–Schmidt

classical Gram–Schmidt（CGS）は、元の列に対する全射影をまとめて引く。modified Gram–Schmidt（MGS）は、更新したベクトルから射影を一方向ずつ引く。実数の厳密計算では同じでも、有限精度ではMGSの方が直交性を保ちやすい。
"""),
    code("""
def classical_gram_schmidt(matrix):
    q_matrix = np.zeros_like(matrix, dtype=float)
    for column in range(matrix.shape[1]):
        vector = matrix[:, column].copy()
        if column:
            coefficients = q_matrix[:, :column].T @ matrix[:, column]
            vector = vector - q_matrix[:, :column] @ coefficients
        q_matrix[:, column] = vector / np.linalg.norm(vector)
    return q_matrix


def modified_gram_schmidt(matrix):
    q_matrix = np.zeros_like(matrix, dtype=float)
    for column in range(matrix.shape[1]):
        vector = matrix[:, column].copy()
        for previous in range(column):
            coefficient = q_matrix[:, previous] @ vector
            vector = vector - coefficient * q_matrix[:, previous]
        q_matrix[:, column] = vector / np.linalg.norm(vector)
    return q_matrix


gram_schmidt_design = np.vander(sample_points, N=15, increasing=True)
gram_schmidt_design /= np.linalg.norm(gram_schmidt_design, axis=0)
q_classical = classical_gram_schmidt(gram_schmidt_design)
q_modified = modified_gram_schmidt(gram_schmidt_design)
q_householder, _ = np.linalg.qr(gram_schmidt_design, mode="reduced")

orthogonality_errors = {
    "classical GS": np.linalg.norm(
        q_classical.T @ q_classical - np.eye(q_classical.shape[1]), ord=2
    ),
    "modified GS": np.linalg.norm(
        q_modified.T @ q_modified - np.eye(q_modified.shape[1]), ord=2
    ),
    "Householder QR": np.linalg.norm(
        q_householder.T @ q_householder - np.eye(q_householder.shape[1]), ord=2
    ),
}

fig = go.Figure(
    go.Bar(
        x=list(orthogonality_errors),
        y=list(orthogonality_errors.values()),
    )
)
fig.update_layout(
    title="Loss of orthogonality on nearby polynomial columns",
    xaxis_title="orthogonalization method",
    yaxis_title="spectral norm of Q.T @ Q - I",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()

for method_name, error in orthogonality_errors.items():
    print(f"{method_name:>16s}: {error:.3e}")
"""),
    md(r"""
MGSはCGSを大幅に改善するが、Householder QRと同じ安定性を自動的に保証するわけではない。極端な問題では再直交化も選択肢になる。
"""),
    code("""
def make_design(n_rows, n_columns, condition_number, seed):
    rng = np.random.default_rng(seed)
    q_left, _ = np.linalg.qr(rng.normal(size=(n_rows, n_columns)))
    q_right, _ = np.linalg.qr(rng.normal(size=(n_columns, n_columns)))
    spectrum = np.geomspace(1.0, 1.0 / condition_number, n_columns)
    return q_left @ np.diag(spectrum) @ q_right.T


def solve_normal_cholesky(design, target):
    gram = design.T @ design
    right_hand_side = design.T @ target
    lower = np.linalg.cholesky(gram)
    return np.linalg.solve(lower.T, np.linalg.solve(lower, right_hand_side))


def normal_equation_backward_proxy(design, target, coefficients):
    gram = design.T @ design
    right_hand_side = design.T @ target
    equation_residual = right_hand_side - gram @ coefficients
    scale = (
        np.linalg.norm(gram, ord=2) * np.linalg.norm(coefficients)
        + np.linalg.norm(right_hand_side)
    )
    return np.linalg.norm(equation_residual) / scale if scale > 0.0 else 0.0


condition_grid = np.logspace(1, 12, 12)
methods = ["inverse", "normal", "cholesky", "qr", "svd"]
records = []
true_beta = np.linspace(0.5, 1.5, 8)

for grid_index, requested_condition in enumerate(condition_grid):
    design = make_design(120, 8, requested_condition, RANDOM_SEED + grid_index)
    target = design @ true_beta
    for method in methods:
        start = time.perf_counter()
        try:
            if method == "cholesky":
                coefficients = solve_normal_cholesky(design, target)
            else:
                result = solve_least_squares(design, target, method=method)
                coefficients = result.coefficients
            coefficient_error = np.linalg.norm(coefficients - true_beta) / np.linalg.norm(
                true_beta
            )
            relative_residual = np.linalg.norm(target - design @ coefficients) / np.linalg.norm(
                target
            )
            backward_proxy = normal_equation_backward_proxy(
                design, target, coefficients
            )
        except np.linalg.LinAlgError:
            coefficient_error = np.nan
            relative_residual = np.nan
            backward_proxy = np.nan
        records.append(
            {
                "condition": np.linalg.cond(design),
                "method": method,
                "coefficient_error": coefficient_error,
                "relative_residual": relative_residual,
                "backward_proxy": backward_proxy,
                "elapsed_ms": 1e3 * (time.perf_counter() - start),
            }
        )
"""),
    code("""
fig = go.Figure()
for method in methods:
    selected = [record for record in records if record["method"] == method]
    fig.add_scatter(
        x=[record["condition"] for record in selected],
        y=[record["coefficient_error"] for record in selected],
        mode="lines+markers",
        name=method,
    )
fig.update_layout(
    title="Coefficient error as conditioning worsens",
    xaxis_title="cond(X)",
    yaxis_title="relative coefficient error",
    xaxis_type="log",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
Choleskyの行は $X^\top X$ を明示的に作り、二回の三角solveを行う。Cholesky自体は対称正定値系に適した安定な分解だが、Gram行列を作る経路はQRやSVDと違って条件数を二乗する。極端なcaseで分解が失敗することも重要な診断である。

normal equationsという正方線形系に対するbackward-error proxyを

$$
\eta_{\mathrm{NE}}
=\frac{\lVert X^\top y-X^\top X\hat\beta\rVert_2}
{\lVert X^\top X\rVert_2\lVert\hat\beta\rVert_2+\lVert X^\top y\rVert_2}
$$

とする。これはnormal equationsをどれだけ正確に解いたかを見るscale-aware指標であり、元の最小二乗問題の係数が正しいことを保証しない。ill-conditioned問題では $\eta_{\mathrm{NE}}$ が小さくてもforward errorが大きくなり得る。
"""),
    code("""
comparison_index = 7
comparison_condition = condition_grid[comparison_index]
comparison_records = [
    [record for record in records if record["method"] == method][comparison_index]
    for method in methods
]

print(f"requested cond(X): {comparison_condition:.1e}")
print(
    f"{'method':>10s} {'forward error':>15s} {'rel residual':>15s} "
    f"{'backward proxy':>16s} {'runtime (ms)':>14s}"
)
for record in comparison_records:
    print(
        f"{record['method']:>10s} {record['coefficient_error']:15.3e} "
        f"{record['relative_residual']:15.3e} "
        f"{record['backward_proxy']:16.3e} {record['elapsed_ms']:14.3f}"
    )

median_runtime = [
    np.median([record["elapsed_ms"] for record in records if record["method"] == method])
    for method in methods
]
fig = go.Figure(go.Bar(x=methods, y=median_runtime))
fig.update_layout(
    title="Illustrative median API runtime across the condition grid",
    xaxis_title="solver",
    yaxis_title="elapsed milliseconds",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
表示時間には、この教材APIが毎回行うrank・condition診断も含まれる。小さい行列の単発測定から性能順位を一般化しない。十分なwarm-up、反復、行列sizeの系列、同じ診断範囲を揃えたbenchmarkが必要である。

| Solver | 選ぶ場面 | 得られる診断 | 主な注意 / fallback |
|---|---|---|---|
| Cholesky on normal equations | 小さく十分well-conditionedで、Gram行列を使う理由がある | SPDでないと失敗 | 条件数二乗。迷えばQR |
| QR (Householder) | full column rankの通常の最小二乗 | rank境界の詳細は弱い | rank不明・欠損ならSVD |
| SVD | rank不明、underdetermined、最小norm、診断重視 | 特異値と有効rank | 通常はQRより高コスト |
| explicit inverse | 教材上の失敗baselineのみ | 追加情報なし | 本番採用しない |

比較では「どのsolverが常に勝つか」ではなく、問題構造、必要な診断、どの条件数から結果が分岐するかを先に見る。
"""),
    md(r"""
## 5. 小さい残差は小さい係数誤差を意味しない

最小特異値に対応する右特異ベクトル $v_{\min}$ の方向へ係数を動かすと、係数は大きく変わっても予測は $\sigma_{\min}$ 倍しか変わらない。

$$
X(\beta+c v_{\min})-X\beta=c\sigma_{\min}u_{\min}
$$

したがってill-conditionedな問題では、fitがほぼ同じ複数の係数が存在する。curve fitの係数を経済的factorとして解釈するときに、この不識別が重要になる。
"""),
    code("""
ill_conditioned = make_design(100, 6, 1e10, RANDOM_SEED)
_, singular_values, right_vectors_t = np.linalg.svd(ill_conditioned, full_matrices=False)
weak_direction = right_vectors_t[-1]
base_beta = np.ones(6)
shifted_beta = base_beta + 1_000.0 * weak_direction

coefficient_change = np.linalg.norm(shifted_beta - base_beta)
prediction_change = np.linalg.norm(
    ill_conditioned @ shifted_beta - ill_conditioned @ base_beta
)

print("smallest singular value:", singular_values[-1])
print("coefficient change:", coefficient_change)
print("prediction change:", prediction_change)
"""),
    md(r"""
## 6. 摂動実験

forward errorは真の係数を知る合成データでしか直接測れない。実データでは、入力へ意味のある小さな摂動を加えて係数・予測・採用判断がどれだけ変わるかを測る。
"""),
    code("""
design = make_design(100, 6, 1e8, RANDOM_SEED)
target = design @ np.arange(1.0, 7.0)
rng = np.random.default_rng(RANDOM_SEED)
perturbation_scale = 1e-9 * np.linalg.norm(target) / np.sqrt(target.size)

base = solve_least_squares(design, target, method="svd")
coefficient_changes = []
prediction_changes = []
for _ in range(200):
    perturbed_target = target + rng.normal(scale=perturbation_scale, size=target.size)
    perturbed = solve_least_squares(design, perturbed_target, method="svd")
    coefficient_changes.append(np.linalg.norm(perturbed.coefficients - base.coefficients))
    prediction_changes.append(np.linalg.norm(perturbed.fitted_values - base.fitted_values))

fig = go.Figure()
fig.add_histogram(x=np.log10(coefficient_changes), name="coefficient change", opacity=0.7)
fig.add_histogram(x=np.log10(prediction_changes), name="prediction change", opacity=0.7)
fig.update_layout(
    title="Sensitivity to tiny target perturbations",
    xaxis_title="log10 change norm",
    yaxis_title="count",
    barmode="overlay",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 7. 失敗モード — residualだけでsolverを採用する

ill-conditioned問題では、normal equations、QR、SVDが似た残差を返しても係数は大きく異なり得る。次を同時に記録する。

- relative residual
- 既知ならrelative coefficient error
- rankと特異値gap
- condition number
- 入力摂動への係数・予測感度
- solver間のprediction disagreement

条件数を小さく見せるために列を標準化しても、元の単位へ戻した係数の感度が消えるとは限らない。scale変更前後の問いを明示する。
"""),
    md(r"""
## 8. 段階別演習

### 基礎

1. SVDから $\kappa_2(X^\top X)=\kappa_2(X)^2$ を導出せよ。
2. `float32` と `float64` でcondition grid実験を繰り返せ。
3. residual、forward error、backward errorを1文ずつ定義せよ。

### 標準

4. classical Gram–Schmidtとmodified Gram–Schmidtを実装し、近接列で $\lVert Q^\top Q-I\rVert_2$ を比較せよ。
5. QRとSVDの結果が分岐する条件数を、複数seedで区間推定せよ。
6. 摂動を $X$ と $y$ の両方へ加え、係数・予測感度を分けて可視化せよ。

### 研究

7. LAPACK driverの異なるSciPy `lstsq` を比較し、rank判定thresholdの影響を論じよ。
8. 実務で使う「solver採用カード」を作り、速さ、rank診断、安定性、失敗時のfallbackを定義せよ。
"""),
    md(r"""
## 9. Exit Criteria

- [ ] conditioningとalgorithmic stabilityを区別できる
- [ ] normal equationsの条件数二乗を導出・数値確認できる
- [ ] Choleskyを使ってもGram行列の条件数二乗は消えないと説明できる
- [ ] $\lVert Q^\top Q-I\rVert_2$ とbackward-error proxyを計算できる
- [ ] 小さい残差が正しい係数を保証しない例を作れる
- [ ] QRを通常のfull-rank最小二乗、SVDをrank診断・最小normへ使う理由を説明できる
- [ ] 摂動実験に単位と現実的なscaleを与えられる
"""),
    md(r"""
## 10. 出典

- [MIT OpenCourseWare 18.335J: Introduction to Numerical Methods](https://ocw.mit.edu/courses/18-335j-introduction-to-numerical-methods-spring-2019/) — floating-point、backward error、conditioning、QR/SVD
- [NumPy `linalg.cond`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.cond.html) — condition numberの定義とnorm選択
- [NumPy `linalg.qr`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.qr.html) — LAPACKベースQRの仕様
- [NumPy `linalg.cholesky`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.cholesky.html) — 対称正定値行列のCholesky分解
- [NumPy `linalg.svd`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.svd.html) — SVDの形状と計算規約
- [SciPy `linalg.lstsq`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.lstsq.html) — `gelsd`、`gelsy`、`gelss` driverの仕様

次章ではSVDを誤差診断から情報圧縮へ転じ、yield changeのPCAを構成する。
"""),
]
