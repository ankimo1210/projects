"""Builder for notebook 07: conditional probability and multivariate systems."""

from nbkit import code, md

cells = [
    md(r"""
# 07. Week 5 — 条件付き確率と多変量系

> 相関行列を入力する前に、それが分布として存在し、観測後の更新が何を意味するかを確認する。

## 学習目標

- 条件付き期待値を情報に対する最良の二乗誤差予測として説明できる
- $\mathbb{E}[Y\mid\sigma(X)]$ を観測 $X$ が生む情報集合への条件付けとして説明できる
- 無相関と独立を反例で区別できる
- 多変量Gaussianの条件付き平均・共分散を導出してsimulationと照合できる
- 標本momentと条件付き分布の照合にMonte Carlo SEとintervalを付けられる
- affine変換と非線形変数変換で密度・momentがどう変わるか説明できる
- Choleskyと固有値分解による相関乱数生成を使い分けられる
- near-singular、positive semidefinite、indefiniteな共分散を診断できる

## 前提知識

- 確率変数、期待値、分散、共分散
- B1 Week 2の固有値、条件数、Cholesky分解
- 行列のblock分割と線形方程式
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy import stats

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
STREAM_NAMES = (
    "joint_gaussian",
    "lognormal_transform",
    "zero_covariance_dependence",
)
STREAM_SEQUENCES = dict(
    zip(
        STREAM_NAMES,
        np.random.SeedSequence(RANDOM_SEED).spawn(len(STREAM_NAMES)),
        strict=True,
    )
)
"""),
    md(r"""
## 1. 条件付き期待値は観測後の予測である

観測 $X$ から判定できるすべての事象は $\sigma(X)$ という情報集合（$\sigma$-algebra）を作る。一般に情報集合 $\mathcal{G}$ に対する可積分な $Y$ の条件付き期待値 $\mathbb{E}[Y\mid\mathcal{G}]$ は、$\mathcal{G}$-可測で、すべての $A\in\mathcal{G}$ に対して

$$
\mathbb{E}[Y\mathbf{1}_A]
=\mathbb{E}[\mathbb{E}[Y\mid\mathcal{G}]\mathbf{1}_A]
$$

を満たす確率変数である。通常の記法 $\mathbb{E}[Y\mid X]$ は $\mathbb{E}[Y\mid\sigma(X)]$ の略記であり、「$X$ の値」だけでなく「$X$ を観測して得られる情報」への射影を表す。

離散変数なら、事象 $X=x$ の確率が正のとき

$$
\mathbb{E}[Y\mid X=x]
=\sum_y y\,\mathbb{P}(Y=y\mid X=x)
$$

である。しかし $\mathbb{E}[Y\mid X]$ は数ではなく、$X$ が決まると値が決まる確率変数である。tower propertyは

$$
\mathbb{E}[\mathbb{E}[Y\mid X]]=\mathbb{E}[Y]
$$

を与える。また、$X$ から作れる任意の二乗可積分な予測 $g(X)$ に対して

$$
\mathbb{E}\left[(Y-\mathbb{E}[Y\mid X])^2\right]
\leq \mathbb{E}[(Y-g(X))^2]
$$

である。これはB1の直交射影を、確率変数の空間へ拡張した見方である。
"""),
    code("""
# Rows are regimes; columns are PnL outcomes -2, 0, and 3.
outcomes = np.array([-2.0, 0.0, 3.0])
regime_probability = np.array([0.65, 0.35])
conditional_probability = np.array(
    [
        [0.30, 0.50, 0.20],
        [0.10, 0.25, 0.65],
    ]
)
conditional_mean = conditional_probability @ outcomes
unconditional_mean = regime_probability @ conditional_mean
joint_probability = regime_probability[:, None] * conditional_probability
direct_mean = np.sum(joint_probability * outcomes[None, :])

print("conditional means:", np.round(conditional_mean, 3))
print("tower-property mean:", round(float(unconditional_mean), 6))
print("direct joint-distribution mean:", round(float(direct_mean), 6))
"""),
    md(r"""
条件付き平均の差を因果効果と呼んではいけない。regimeは観測情報であり、介入ではない。条件付けは分布を更新するが、因果方向を自動的に与えない。
"""),
    md(r"""
### Core反例: 共分散0でも従属し得る

$U\sim\mathcal{N}(0,1)$、$V=U^2$ とする。対称性から

$$
\operatorname{Cov}(U,V)
=\mathbb{E}[U^3]-\mathbb{E}[U]\mathbb{E}[U^2]=0
$$

だが、$V$ は $U$ の関数なので独立ではない。実際、

$$
\mathbb{E}[V\mid\sigma(U)]=U^2
\neq \mathbb{E}[V]=1,
\qquad |U|=\sqrt{V}.
$$

共分散は線形関係の一部しか捕まえない。無相関から独立を結論できるのは、joint Gaussianなど追加条件がある場合に限られる。
"""),
    code("""
dependence_rng = np.random.default_rng(
    STREAM_SEQUENCES["zero_covariance_dependence"]
)
dependence_sample_size = 30_000
u_samples = dependence_rng.standard_normal(dependence_sample_size)
v_samples = u_samples**2
dependence_batch_count = 30
u_batches = u_samples.reshape(dependence_batch_count, -1)
v_batches = v_samples.reshape(dependence_batch_count, -1)

dependence_estimates = np.array(
    [
        np.cov(u_samples, v_samples, ddof=1)[0, 1],
        np.corrcoef(u_samples, v_samples)[0, 1],
        np.corrcoef(np.abs(u_samples), v_samples)[0, 1],
        v_samples.mean(),
    ]
)
dependence_batch_estimates = np.array(
    [
        [
            np.cov(u_batch, v_batch, ddof=1)[0, 1],
            np.corrcoef(u_batch, v_batch)[0, 1],
            np.corrcoef(np.abs(u_batch), v_batch)[0, 1],
            v_batch.mean(),
        ]
        for u_batch, v_batch in zip(u_batches, v_batches, strict=True)
    ]
)
dependence_batch_standard_errors = dependence_batch_estimates.std(
    axis=0,
    ddof=1,
) / np.sqrt(dependence_batch_count)
absolute_u_v_squared_correlation = np.sqrt(2.0 / np.pi) / np.sqrt(
    2.0 * (1.0 - 2.0 / np.pi)
)

dependence_summary = pd.DataFrame(
    {
        "diagnostic": [
            "sample covariance Cov(U, V)",
            "sample correlation Corr(U, V)",
            "sample correlation Corr(|U|, V)",
            "mean of V",
        ],
        "estimate": dependence_estimates,
        "population_reference": [
            0.0,
            0.0,
            absolute_u_v_squared_correlation,
            1.0,
        ],
        "batch_mc_standard_error": dependence_batch_standard_errors,
    }
)
dependence_summary["ci_95_lower"] = (
    dependence_summary["estimate"]
    - stats.t.ppf(0.975, dependence_batch_count - 1)
    * dependence_summary["batch_mc_standard_error"]
)
dependence_summary["ci_95_upper"] = (
    dependence_summary["estimate"]
    + stats.t.ppf(0.975, dependence_batch_count - 1)
    * dependence_summary["batch_mc_standard_error"]
)
display(dependence_summary.round(6))

u_grid = np.linspace(-3.5, 3.5, 250)
fig = go.Figure()
fig.add_scattergl(
    x=u_samples[:4_000],
    y=v_samples[:4_000],
    mode="markers",
    name="seeded samples",
    marker={"size": 4, "opacity": 0.25},
)
fig.add_scatter(
    x=u_grid,
    y=u_grid**2,
    mode="lines",
    name="E[V | U = u] = u^2",
    line={"color": "black", "width": 3},
)
fig.update_layout(
    title="Zero covariance does not imply independence",
    xaxis_title="U",
    yaxis_title="V = U^2",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
有限標本の共分散は厳密な0にならない。表は同じseeded sampleを30個の独立batchに分け、batch間のばらつきからMonte Carlo SEと周辺的な95% intervalを作っている。一方、従属性の根拠は標本相関の大きさではなく、$V=U^2$ および $\mathbb{E}[V\mid\sigma(U)]=U^2$ という母集団の関係である。
"""),
    md(r"""
## 2. 多変量Gaussianと線形変換

$Z\sim\mathcal{N}(0,I_d)$ とし、$LL^\top=\Sigma$ を満たす $L$ を取ると

$$
X=\mu+LZ
$$

は

$$
\mathbb{E}[X]=\mu,\qquad
\operatorname{Cov}(X)=L I_d L^\top=\Sigma
$$

を満たす。$\Sigma$ がpositive definiteならCholesky分解が速く一意な下三角因子を返す。positive semidefiniteでrank欠損ならCholeskyは失敗するが、固有値分解

$$
\Sigma=Q\Lambda Q^\top,
\qquad L=Q\Lambda^{1/2}
$$

は利用できる。負の固有値が丸め誤差なのか、無効な入力なのかをscale-awareな閾値で分ける。
"""),
    code("""
def covariance_diagnostics(covariance, tolerance=None):
    covariance = np.asarray(covariance, dtype=float)
    if covariance.ndim != 2 or covariance.shape[0] != covariance.shape[1]:
        raise ValueError("covariance must be square")
    if covariance.shape[0] == 0 or not np.all(np.isfinite(covariance)):
        raise ValueError("covariance must be non-empty and finite")
    symmetry_error = np.linalg.norm(covariance - covariance.T, ord=np.inf)
    symmetric = 0.5 * (covariance + covariance.T)
    eigenvalues = np.linalg.eigvalsh(symmetric)
    scale = max(float(np.max(np.abs(eigenvalues))), np.finfo(float).tiny)
    symmetry_scale = max(
        float(np.linalg.norm(covariance, ord=np.inf)),
        np.finfo(float).tiny,
    )
    symmetry_tolerance = (
        100.0 * covariance.shape[0] * np.finfo(float).eps * symmetry_scale
    )
    if tolerance is None:
        tolerance = 100.0 * covariance.shape[0] * np.finfo(float).eps * scale
    if not np.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("tolerance must be finite and non-negative")
    numerical_rank = int(np.count_nonzero(eigenvalues > tolerance))
    positive_eigenvalues = eigenvalues[eigenvalues > tolerance]
    condition_number = (
        float(eigenvalues[-1] / positive_eigenvalues[0])
        if numerical_rank == covariance.shape[0]
        else np.inf
    )
    return {
        "symmetry_error": float(symmetry_error),
        "symmetry_tolerance": float(symmetry_tolerance),
        "min_eigenvalue": float(eigenvalues[0]),
        "max_eigenvalue": float(eigenvalues[-1]),
        "tolerance": float(tolerance),
        "rank": numerical_rank,
        "condition_number": condition_number,
    }


def covariance_factor(covariance, method="cholesky"):
    covariance = np.asarray(covariance, dtype=float)
    diagnostics = covariance_diagnostics(covariance)
    if diagnostics["symmetry_error"] > diagnostics["symmetry_tolerance"]:
        raise ValueError("covariance is not symmetric within tolerance")
    if diagnostics["min_eigenvalue"] < -diagnostics["tolerance"]:
        raise ValueError("covariance is indefinite")

    symmetric = 0.5 * (covariance + covariance.T)
    if method == "cholesky":
        factor = np.linalg.cholesky(symmetric)
    elif method == "eigh":
        eigenvalues, eigenvectors = np.linalg.eigh(symmetric)
        clipped = np.where(eigenvalues > diagnostics["tolerance"], eigenvalues, 0.0)
        factor = eigenvectors @ np.diag(np.sqrt(clipped))
    else:
        raise ValueError("method must be 'cholesky' or 'eigh'")
    return factor, diagnostics


def correlated_gaussian(rng, mean, covariance, sample_size, method="cholesky"):
    mean = np.asarray(mean, dtype=float)
    covariance = np.asarray(covariance, dtype=float)
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    if mean.ndim != 1 or mean.size == 0 or not np.all(np.isfinite(mean)):
        raise ValueError("mean must be a non-empty finite vector")
    if covariance.shape != (mean.size, mean.size):
        raise ValueError("covariance shape must match mean")
    if isinstance(sample_size, bool) or not isinstance(sample_size, (int, np.integer)):
        raise TypeError("sample_size must be an integer")
    if sample_size < 1:
        raise ValueError("sample_size must be positive")
    factor, diagnostics = covariance_factor(covariance, method=method)
    standard_normal = rng.normal(size=(sample_size, mean.size))
    samples = mean + standard_normal @ factor.T
    return samples, diagnostics
"""),
    md(r"""
この章では中間量を見せるため、教育用のlocal関数がsampleとdiagnosticsを同時に返す。B2 Projectではpackage APIを

```python
conditional = conditional_gaussian(mean, covariance, observed_indices, observed_values)
samples = correlated_gaussian(mean, covariance, n_samples, rng=rng, method="auto")
```

へ統一する。条件付き分布の `mean`、`covariance`、`gain` と共分散diagnosticsを結果objectに保存し、乱数生成関数はsampleだけを返す。この分離により、解析計算を乱数消費なしにtestできる。
"""),
    code("""
mean = np.array([0.02, -0.01, 0.15])
covariance = np.array(
    [
        [0.040, -0.012, -0.018],
        [-0.012, 0.0225, 0.009],
        [-0.018, 0.009, 0.0625],
    ]
)
rng = np.random.default_rng(STREAM_SEQUENCES["joint_gaussian"])
samples, diagnostics = correlated_gaussian(
    rng,
    mean,
    covariance,
    sample_size=30_000,
)
sample_covariance = np.cov(samples, rowvar=False, ddof=1)
sample_mean = samples.mean(axis=0)
sample_size = samples.shape[0]
normal_critical_value = stats.norm.ppf(0.975)

joint_moment_rows = []
for component_index in range(mean.size):
    standard_error = np.sqrt(covariance[component_index, component_index] / sample_size)
    joint_moment_rows.append(
        {
            "moment": f"E[X_{component_index + 1}]",
            "estimate": sample_mean[component_index],
            "target": mean[component_index],
            "mc_standard_error": standard_error,
        }
    )

for row_index in range(mean.size):
    for column_index in range(row_index, mean.size):
        standard_error = np.sqrt(
            (
                covariance[row_index, column_index] ** 2
                + covariance[row_index, row_index]
                * covariance[column_index, column_index]
            )
            / (sample_size - 1)
        )
        joint_moment_rows.append(
            {
                "moment": f"Cov(X_{row_index + 1}, X_{column_index + 1})",
                "estimate": sample_covariance[row_index, column_index],
                "target": covariance[row_index, column_index],
                "mc_standard_error": standard_error,
            }
        )

joint_moment_table = pd.DataFrame(joint_moment_rows)
joint_moment_table["ci_95_lower"] = (
    joint_moment_table["estimate"]
    - normal_critical_value * joint_moment_table["mc_standard_error"]
)
joint_moment_table["ci_95_upper"] = (
    joint_moment_table["estimate"]
    + normal_critical_value * joint_moment_table["mc_standard_error"]
)
joint_moment_table["standardized_error"] = (
    (joint_moment_table["estimate"] - joint_moment_table["target"])
    / joint_moment_table["mc_standard_error"]
)

print("covariance diagnostics:", diagnostics)
display(joint_moment_table.round(7))
print("max mean error:", float(np.max(np.abs(sample_mean - mean))))
print("max covariance error:", float(np.max(np.abs(sample_covariance - covariance))))

fig = go.Figure(
    go.Scattergl(
        x=samples[:4_000, 0],
        y=samples[:4_000, 2],
        mode="markers",
        marker={"size": 4, "opacity": 0.35},
    )
)
fig.update_layout(
    title="Correlated Gaussian draws from a Cholesky factor",
    xaxis_title="Component 1",
    yaxis_title="Component 3",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
sample covarianceは有限標本なので入力と完全一致しない。表の平均SEは $\sqrt{\Sigma_{jj}/N}$、Gaussian標本共分散のSEはWishartの関係

$$
\operatorname{Var}(S_{jk})
=\frac{\Sigma_{jk}^2+\Sigma_{jj}\Sigma_{kk}}{N-1}
$$

を使った理論上のMonte Carlo誤差である。95% intervalは各momentの周辺的なnormal近似であり、全行が同時に入ることを保証する同時intervalではない。照合では `np.allclose` の既定値を無批判に使わず、標本数に対して期待するMonte Carlo誤差を先に決める。
"""),
    md(r"""
## 3. Gaussianの条件付き分布

ベクトルをtarget $X_a$ とobserved $X_b$ に分ける。

$$
\begin{pmatrix}X_a\\X_b\end{pmatrix}
\sim\mathcal{N}\left(
\begin{pmatrix}\mu_a\\\mu_b\end{pmatrix},
\begin{pmatrix}
\Sigma_{aa}&\Sigma_{ab}\\
\Sigma_{ba}&\Sigma_{bb}
\end{pmatrix}
\right)
$$

$\Sigma_{bb}$ が可逆なら、$X_b=b$ の条件下で

$$
\begin{aligned}
\mathbb{E}[X_a\mid X_b=b]
&=\mu_a+\Sigma_{ab}\Sigma_{bb}^{-1}(b-\mu_b),\\
\operatorname{Cov}(X_a\mid X_b=b)
&=\Sigma_{aa}-\Sigma_{ab}\Sigma_{bb}^{-1}\Sigma_{ba}.
\end{aligned}
$$

実装では逆行列を作らず `solve` を使う。条件付き共分散は観測値 $b$ に依存しないが、条件付き平均は依存する。
"""),
    code("""
def conditional_gaussian(mean, covariance, observed_indices, observed_values):
    mean = np.asarray(mean, dtype=float)
    covariance = np.asarray(covariance, dtype=float)
    raw_indices = np.asarray(observed_indices)
    if mean.ndim != 1 or mean.size < 2 or not np.all(np.isfinite(mean)):
        raise ValueError("mean must be a finite vector with at least two entries")
    if covariance.shape != (mean.size, mean.size):
        raise ValueError("covariance shape must match mean")
    diagnostics = covariance_diagnostics(covariance)
    if diagnostics["symmetry_error"] > diagnostics["symmetry_tolerance"]:
        raise ValueError("covariance must be symmetric")
    if diagnostics["min_eigenvalue"] < -diagnostics["tolerance"]:
        raise ValueError("covariance must be positive semidefinite")
    if raw_indices.ndim != 1 or raw_indices.dtype.kind not in {"i", "u"}:
        raise TypeError("observed_indices must be a one-dimensional integer array")
    observed_indices = raw_indices.astype(int, copy=False)
    if (
        observed_indices.size == 0
        or np.unique(observed_indices).size != observed_indices.size
        or np.any(observed_indices < 0)
        or np.any(observed_indices >= mean.size)
        or observed_indices.size == mean.size
    ):
        raise ValueError("observed_indices must be unique, in bounds, and leave a target")
    observed_values = np.atleast_1d(np.asarray(observed_values, dtype=float))
    if (
        observed_indices.size != observed_values.size
        or not np.all(np.isfinite(observed_values))
    ):
        raise ValueError("observed values must be finite with one value per index")

    all_indices = np.arange(mean.size)
    target_indices = np.setdiff1d(all_indices, observed_indices, assume_unique=False)
    covariance_tt = covariance[np.ix_(target_indices, target_indices)]
    covariance_to = covariance[np.ix_(target_indices, observed_indices)]
    covariance_ot = covariance_to.T
    covariance_oo = covariance[np.ix_(observed_indices, observed_indices)]

    innovation = observed_values - mean[observed_indices]
    gain = np.linalg.solve(covariance_oo, covariance_ot).T
    conditional_mean = mean[target_indices] + gain @ innovation
    conditional_covariance = covariance_tt - gain @ covariance_ot
    conditional_covariance = 0.5 * (
        conditional_covariance + conditional_covariance.T
    )
    return target_indices, conditional_mean, conditional_covariance, gain


observed_value = np.array([0.45])
target_indices, analytic_mean, analytic_covariance, analytic_gain = conditional_gaussian(
    mean,
    covariance,
    observed_indices=[2],
    observed_values=observed_value,
)

# Validate the Schur-complement formula against the original joint draws.
joint_target = samples[:, target_indices]
joint_observed = samples[:, [2]]
regression_residuals = (
    joint_target
    - mean[target_indices]
    - (joint_observed - mean[[2]]) @ analytic_gain.T
)
residual_covariance = np.cov(regression_residuals, rowvar=False, ddof=1)
residual_observed_cross_covariance = np.cov(
    np.column_stack((regression_residuals, joint_observed)),
    rowvar=False,
    ddof=1,
)[: len(target_indices), len(target_indices) :]

# A narrow observed-value band gives a second, approximate empirical check.
conditioning_band = np.abs(samples[:, 2] - observed_value[0]) <= 0.015
band_target_mean = samples[conditioning_band][:, target_indices].mean(axis=0)
band_formula_mean = (
    mean[target_indices]
    + (samples[conditioning_band][:, [2]] - mean[[2]]) @ analytic_gain.T
).mean(axis=0)
band_count = int(conditioning_band.sum())
residual_mean = regression_residuals.mean(axis=0)
band_residual_mean = regression_residuals[conditioning_band].mean(axis=0)

conditional_validation_rows = []
for target_position, target_index in enumerate(target_indices):
    residual_mean_se = np.sqrt(
        analytic_covariance[target_position, target_position] / sample_size
    )
    conditional_validation_rows.append(
        {
            "diagnostic": f"E[residual X_{target_index + 1}]",
            "estimate": residual_mean[target_position],
            "target": 0.0,
            "mc_standard_error": residual_mean_se,
        }
    )
    band_mean_se = np.sqrt(
        analytic_covariance[target_position, target_position] / band_count
    )
    conditional_validation_rows.append(
        {
            "diagnostic": f"band mean residual X_{target_index + 1}",
            "estimate": band_residual_mean[target_position],
            "target": 0.0,
            "mc_standard_error": band_mean_se,
        }
    )

for row_position, row_index in enumerate(target_indices):
    for column_position in range(row_position, len(target_indices)):
        column_index = target_indices[column_position]
        covariance_se = np.sqrt(
            (
                analytic_covariance[row_position, column_position] ** 2
                + analytic_covariance[row_position, row_position]
                * analytic_covariance[column_position, column_position]
            )
            / (sample_size - 1)
        )
        conditional_validation_rows.append(
            {
                "diagnostic": (
                    f"Cov(residual X_{row_index + 1}, residual X_{column_index + 1})"
                ),
                "estimate": residual_covariance[row_position, column_position],
                "target": analytic_covariance[row_position, column_position],
                "mc_standard_error": covariance_se,
            }
        )

for target_position, target_index in enumerate(target_indices):
    cross_covariance_se = np.sqrt(
        analytic_covariance[target_position, target_position]
        * covariance[2, 2]
        / (sample_size - 1)
    )
    conditional_validation_rows.append(
        {
            "diagnostic": f"Cov(residual X_{target_index + 1}, observed X_3)",
            "estimate": residual_observed_cross_covariance[target_position, 0],
            "target": 0.0,
            "mc_standard_error": cross_covariance_se,
        }
    )

conditional_validation_table = pd.DataFrame(conditional_validation_rows)
conditional_validation_table["ci_95_lower"] = (
    conditional_validation_table["estimate"]
    - normal_critical_value
    * conditional_validation_table["mc_standard_error"]
)
conditional_validation_table["ci_95_upper"] = (
    conditional_validation_table["estimate"]
    + normal_critical_value
    * conditional_validation_table["mc_standard_error"]
)
conditional_validation_table["standardized_error"] = (
    (
        conditional_validation_table["estimate"]
        - conditional_validation_table["target"]
    )
    / conditional_validation_table["mc_standard_error"]
)

print("target indices:", target_indices)
print("analytic conditional mean:", np.round(analytic_mean, 6))
print("observations in conditioning band:", band_count)
print("band empirical target mean:", np.round(band_target_mean, 6))
print("band formula mean:", np.round(band_formula_mean, 6))
print("analytic gain:", np.round(analytic_gain, 6))
print("analytic conditional covariance:", np.round(analytic_covariance, 6))
print("joint-residual covariance:", np.round(residual_covariance, 6))
display(conditional_validation_table.round(7))
print(
    "max residual-observed cross-covariance:",
    float(np.max(np.abs(residual_observed_cross_covariance))),
)
"""),
    md(r"""
検証には、条件付き公式から再び乱数を作る循環的な照合を使っていない。元のjoint sampleから線形予測残差を作り、その共分散がSchur complementと一致し、observed座標とのcross-covarianceが0へ近いことを確認した。表は点推定だけでなく、Gaussianのmoment関係から得るMonte Carlo SE、95% interval、standardized errorを併記する。

narrow bandの比較は連続変数を幅のある区間へ近似した補助診断である。表のband mean residualは各観測値での公式からの差を測るため、固定幅のband自体が生む平滑化biasとMonte Carlo誤差を混同しない。band幅と標本数は必ず記録する。複数行の95% intervalはここでも同時intervalではない。

観測によって不確実性が減る方向は、cross-covarianceが運ぶ情報で決まる。条件付き共分散を元の共分散から単純に同じ割合で縮める実装は誤りである。また、$\Sigma_{bb}$ がill-conditionedなら条件付き平均も入力誤差に敏感になるため、solveを使うだけで診断は終わらない。
"""),
    md(r"""
## 4. 変数変換とJacobian

1対1の滑らかな変換 $Y=g(X)$ では

$$
f_Y(y)=f_X(g^{-1}(y))
\left|\frac{d}{dy}g^{-1}(y)\right|
$$

である。$Y=\exp(X)$、$X\sim\mathcal{N}(\mu,\sigma^2)$ なら

$$
f_Y(y)=\frac{1}{y\sigma\sqrt{2\pi}}
\exp\left(-\frac{(\log y-\mu)^2}{2\sigma^2}\right),
\qquad y>0,
$$

かつ

$$
\mathbb{E}[Y]=\exp(\mu+\sigma^2/2).
$$

Jacobianの $1/y$ を落とすと密度は1へ積分されない。simulationのhistogramだけでは正規化の誤りを見逃すことがあるため、解析密度とmomentの両方を照合する。
"""),
    code("""
log_mean = -0.15
log_std = 0.55
transform_rng = np.random.default_rng(STREAM_SEQUENCES["lognormal_transform"])
log_samples = transform_rng.normal(log_mean, log_std, size=80_000)
positive_samples = np.exp(log_samples)
analytic_lognormal_mean = np.exp(log_mean + 0.5 * log_std**2)

x_grid = np.linspace(0.02, np.quantile(positive_samples, 0.995), 250)
analytic_density = stats.lognorm.pdf(
    x_grid,
    s=log_std,
    scale=np.exp(log_mean),
)

fig = go.Figure()
histogram_density, histogram_edges = np.histogram(
    positive_samples,
    bins=100,
    density=True,
)
histogram_centers = 0.5 * (histogram_edges[:-1] + histogram_edges[1:])
fig.add_bar(
    x=histogram_centers,
    y=histogram_density,
    width=np.diff(histogram_edges),
    name="Simulation",
    opacity=0.55,
)
fig.add_scatter(
    x=x_grid,
    y=analytic_density,
    mode="lines",
    name="Analytic density",
)
fig.update_layout(
    title="Nonlinear change of variables: lognormal distribution",
    xaxis_title="Transformed value",
    yaxis_title="Density",
    barmode="overlay",
    template="plotly_white",
)
fig.show()

print("analytic mean:", round(float(analytic_lognormal_mean), 6))
print("simulated mean:", round(float(positive_samples.mean()), 6))
"""),
    md(r"""
## 5. Near-singular共分散を壊して調べる

2変量の相関行列

$$
R(\rho)=\begin{pmatrix}1&\rho\\\rho&1\end{pmatrix}
$$

の固有値は $1-\rho$ と $1+\rho$ である。$\rho\uparrow1$ では最小固有値が0へ近づき、条件数は発散する。$\rho=1$ は有効なpositive semidefinite行列だがrank 1であり、$\rho>1$ は共分散として無効である。
"""),
    code("""
correlations = np.array([0.9, 0.99, 0.999, 0.9999, 0.999999, 1.0])
minimum_eigenvalues = []
condition_numbers = []
for correlation in correlations:
    correlation_matrix = np.array([[1.0, correlation], [correlation, 1.0]])
    result = covariance_diagnostics(correlation_matrix)
    minimum_eigenvalues.append(result["min_eigenvalue"])
    condition_numbers.append(result["condition_number"])

finite_condition_numbers = np.where(
    np.isfinite(condition_numbers), condition_numbers, np.nan
)
plot_mask = (1.0 - correlations > 0.0) & np.isfinite(finite_condition_numbers)
fig = go.Figure()
fig.add_scatter(
    x=(1.0 - correlations)[plot_mask],
    y=finite_condition_numbers[plot_mask],
    mode="lines+markers",
    name="Condition number",
)
fig.update_layout(
    title="Correlation approaching a rank-one boundary",
    xaxis_title="1 - correlation",
    yaxis_title="Condition number",
    xaxis_type="log",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()

for correlation, eigenvalue, condition_number in zip(
    correlations, minimum_eigenvalues, condition_numbers, strict=True
):
    print(
        f"rho={correlation:.6f}  min_eigenvalue={eigenvalue:.3e}  "
        f"condition_number={condition_number:.3e}"
    )
"""),
    code("""
rank_one_covariance = np.array([[1.0, 1.0], [1.0, 1.0]])
invalid_covariance = np.array([[1.0, 1.00000001], [1.00000001, 1.0]])

for name, candidate in [
    ("rank-one PSD", rank_one_covariance),
    ("indefinite", invalid_covariance),
]:
    print(name, covariance_diagnostics(candidate))
    for method in ["cholesky", "eigh"]:
        try:
            factor, _ = covariance_factor(candidate, method=method)
            reconstruction_error = np.linalg.norm(factor @ factor.T - candidate)
            print(f"  {method}: reconstruction error={reconstruction_error:.3e}")
        except (ValueError, np.linalg.LinAlgError) as error:
            print(f"  {method}: rejected ({type(error).__name__})")

tiny_covariance = 1e-20 * np.array([[1.0, 0.3], [0.3, 2.0]])
tiny_factor, tiny_diagnostics = covariance_factor(tiny_covariance, method="cholesky")
print("tiny-scale rank:", tiny_diagnostics["rank"])
print(
    "tiny-scale relative reconstruction error:",
    np.linalg.norm(tiny_factor @ tiny_factor.T - tiny_covariance)
    / np.linalg.norm(tiny_covariance),
)
"""),
    md(r"""
rank-one行列を `eigh` で生成すると、標本は1本の直線上に乗る。これは失敗ではなく退化分布である。一方、明確な負の固有値を0へclipすると、入力とは別のモデルを黙って作る。repairが必要なら、変更前後の最小固有値、行列norm差、rankを記録し、モデル変更として承認する。

### 実装上の診断順序

1. shape、有限値、対称性を確認する
2. 固有値、scale-aware tolerance、numerical rankを記録する
3. positive definiteならCholeskyを使う
4. semidefiniteを意図した場合だけ固有値分解を使う
5. indefiniteなら停止し、共分散推定過程へ戻る
"""),
    md(r"""
## 6. 失敗モード — pairwise correlationをそのまま行列にする

各pairの相関が $[-1,1]$ に入っていても、行列全体がpositive semidefiniteとは限らない。欠損行がpairごとに異なる相関推定、丸めた相関、手作業のstress scenarioは特に危険である。

- Cholesky失敗を「数値の気まぐれ」として無条件にjitterで隠す
- `eigh` の全負固有値をclipし、変更量を報告しない
- 条件数を見ずにGaussian条件付き平均を計算する
- covarianceとcorrelation、varianceとstandard deviationを混同する
- 標本共分散が0に近いことから、追加条件なしに独立を結論する
- 観測による条件付けを因果的な介入と解釈する
- simulationの点推定だけをanalytic targetと比べ、Monte Carlo SEを報告しない

factorizationの成功は、入力行列の研究上の妥当性を保証しない。
"""),
    md(r"""
## 7. 段階別演習

### 基礎

1. tower propertyを離散例のjoint probability tableから確認せよ。
2. $U\sim\mathcal{N}(0,1)$、$V=U^2$ で共分散0と従属性をそれぞれ示せ。
3. $X=\mu+LZ$ の平均と共分散を導出せよ。
4. $R(\rho)$ の固有値と条件数を手計算せよ。

### 標準

5. 観測するcomponentを変え、条件付き平均と共分散をMonte Carlo SE付きで照合せよ。
6. Choleskyと `eigh` の標本moment誤差と実行時間を、well-conditioned行列で比較せよ。
7. lognormal変換でJacobianを落とした密度の数値積分を行い、1にならないことを示せ。

### 研究

8. 欠損patternが異なるpairwise covarianceからindefinite行列が生じる例を構成せよ。
9. covariance repair法を1つ調べ、元行列との差、rank、下流の条件付き平均への影響を報告せよ。
10. **Advanced:** Gaussianでないjoint distributionでは相関だけで条件付き分布が決まらない例を作れ。
"""),
    md(r"""
## 8. Exit Criteria

- [ ] $\mathbb{E}[Y\mid X]=\mathbb{E}[Y\mid\sigma(X)]$ を情報集合への条件付けとして説明できる
- [ ] 無相関だが従属する反例を作り、独立と区別できる
- [ ] 条件付き期待値が確率変数であることとtower propertyを説明できる
- [ ] Gaussian条件付き平均・共分散をblock行列から実装できる
- [ ] 標本平均・共分散・条件付き検証にMonte Carlo SEと95% intervalを付けられる
- [ ] Choleskyと固有値分解の適用条件を診断値とともに説明できる
- [ ] near-singular、semidefinite、indefiniteを区別できる
- [ ] 変数変換でJacobianとmomentを独立に照合できる
"""),
    md(r"""
## 9. 出典

- [MIT OpenCourseWare 18.600: Probability and Random Variables, Lecture Notes](https://ocw.mit.edu/courses/18-600-probability-and-random-variables-fall-2019/pages/lecture-notes/) — 条件付き確率、条件付き期待値、多変量分布
- [MIT OpenCourseWare 18.600: Readings](https://ocw.mit.edu/courses/18-600-probability-and-random-variables-fall-2019/pages/readings/) — 講義順に対応する教科書章
- [NumPy `Generator.multivariate_normal`](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.multivariate_normal.html) — 多変量正規乱数と共分散validity check
- [NumPy `linalg.cholesky`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.cholesky.html) — positive-definite行列のCholesky分解
- [NumPy `linalg.eigh`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.eigh.html) — 実対称行列の固有値分解
- [SciPy `stats.multivariate_normal`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.multivariate_normal.html) — positive semidefinite covarianceを含む多変量正規分布の参照API

次章では、標本数を増やす操作がどの収束を保証し、heavy-tailがその直感をどこで壊すかを調べる。
"""),
]
