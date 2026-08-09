"""Builder for notebook 10: Brownian motion, Itô calculus, and Monte Carlo."""

from nbkit import code, md

cells = [
    md(r"""
# 10. Week 8 — Brownian motion・Itô・Euler–Maruyama・Monte Carlo

> pathを細かくすればMonte Carlo誤差が消えるわけではなく、path数を増やしても時間離散化biasは消えない。

## 学習目標

- Brownian increment、scaling、quadratic variationをsimulationで検証する
- Itô formulaの二次変動補正を離散和から説明する
- GBMのexact transitionとEuler–Maruyamaを同じBrownian incrementで比較する
- strong error、weak error、sampling error、discretization biasを分離する
- antithetic variatesとcontrol variateを公平な乱数予算で評価する

## 前提知識

- 条件付き期待値、正規分布、大数の法則、中心極限定理
- Week 7のfiltrationとmartingale
- 微分、Taylor展開、常微分方程式のEuler法
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy.stats import norm

from quant_textbook import (
    antithetic_variates,
    control_variate,
    estimate_expectation,
    quadratic_variation,
    simulate_brownian_motion,
    simulate_gbm_euler,
    simulate_gbm_exact,
)

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810


def task_rng(task_id, *coordinates):
    entropy = [
        RANDOM_SEED,
        int(task_id),
        *(int(coordinate) for coordinate in coordinates),
    ]
    return np.random.default_rng(np.random.SeedSequence(entropy))
"""),
    md(r"""
## 1. Brownian motionの契約

standard Brownian motion $W_t$ は $W_0=0$、連続path、独立定常incrementを持ち、$0\le s<t$ に対して

$$
W_t-W_s\sim\mathcal{N}(0,t-s)
$$

である。grid $0=t_0<\cdots<t_m=T$ では

$$
\Delta W_k=\sqrt{\Delta t_k}Z_k,
\qquad Z_k\overset{\mathrm{iid}}{\sim}\mathcal{N}(0,1)
$$

を累積してpathを作る。標準偏差は $\Delta t$ ではなく $\sqrt{\Delta t}$ でscalingする。
"""),
    code("""
times = np.linspace(0.0, 1.0, 501)
brownian_paths = simulate_brownian_motion(
    times,
    n_paths=8,
    rng=task_rng(0),
)

fig = go.Figure()
for path_index, path in enumerate(brownian_paths):
    fig.add_scatter(
        x=times,
        y=path,
        mode="lines",
        name=f"path {path_index + 1}",
    )
fig.update_layout(
    title="Brownian paths on a fixed time grid",
    xaxis_title="Time",
    yaxis_title="W_t",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 2. Quadratic variation — 二次項が消えない

partition $\Pi_n$ 上のquadratic variationを

$$
[W]_T^{(n)}=\sum_{k=0}^{n-1}(W_{t_{k+1}}-W_{t_k})^2
$$

と置く。meshが0へ近づくと $[W]_T^{(n)}\to T$ が確率収束する。一方、有限変動の滑らかなpathならquadratic variationは0へ向かう。Brownian pathに通常のchain ruleをそのまま使えない理由がここにある。
"""),
    code("""
partition_sizes = np.array([8, 16, 32, 64, 128, 256, 512, 1024])
qv_means = []
qv_standard_deviations = []

for partition_size in partition_sizes:
    partition = np.linspace(0.0, 1.0, partition_size + 1)
    paths = simulate_brownian_motion(
        partition,
        n_paths=2_500,
        rng=task_rng(1, partition_size),
    )
    qv_samples = quadratic_variation(paths)
    qv_means.append(qv_samples.mean())
    qv_standard_deviations.append(qv_samples.std(ddof=1))

fig = go.Figure()
fig.add_scatter(
    x=partition_sizes,
    y=qv_means,
    error_y={"type": "data", "array": qv_standard_deviations, "visible": True},
    mode="lines+markers",
    name="quadratic variation",
)
fig.add_hline(y=1.0, line_dash="dash", annotation_text="T")
fig.update_layout(
    title="Quadratic variation concentrates around the horizon",
    xaxis_title="Number of increments",
    xaxis_type="log",
    yaxis_title="Quadratic variation",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
error barはmeanのstandard errorではなくpath間のstandard deviationである。partitionを細かくすると分布自体が集中することを示している。
"""),
    md(r"""
## 3. Itô formula — $f(x)=x^2$ から理解する

$f\in C^{1,2}$ とItô process

$$
dX_t=\mu(t,X_t)dt+\sigma(t,X_t)dW_t
$$

に対し、Itô formulaは

$$
df(t,X_t)=
\left(f_t+\mu f_x+\frac{1}{2}\sigma^2f_{xx}\right)dt
+\sigma f_xdW_t
$$

である。$X_t=W_t$、$f(x)=x^2$ なら

$$
W_T^2=2\int_0^T W_t\,dW_t+T.
$$

通常のchain ruleが落とす $T$ は、離散和に残る $\sum(\Delta W)^2$ の極限である。
"""),
    code("""
ito_partition_sizes = np.array([16, 32, 64, 128, 256, 512, 1024])
mean_absolute_residuals = []

for partition_size in ito_partition_sizes:
    partition = np.linspace(0.0, 1.0, partition_size + 1)
    paths = simulate_brownian_motion(
        partition,
        n_paths=2_000,
        rng=task_rng(2, partition_size),
    )
    increments = np.diff(paths, axis=1)
    ito_integral = np.sum(paths[:, :-1] * increments, axis=1)
    residual = paths[:, -1] ** 2 - (2.0 * ito_integral + 1.0)
    mean_absolute_residuals.append(np.mean(np.abs(residual)))

fig = go.Figure()
fig.add_scatter(
    x=ito_partition_sizes,
    y=mean_absolute_residuals,
    mode="lines+markers",
    name="mean absolute residual",
)
fig.update_layout(
    title="Discrete Itô identity approaches the continuous identity",
    xaxis_title="Number of increments",
    xaxis_type="log",
    yaxis_title="Mean absolute residual",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 4. GBM — exact transitionとEuler–Maruyama

geometric Brownian motionを

$$
dS_t=\mu S_tdt+\sigma S_tdW_t,
\qquad S_0>0
$$

とする。exact solutionは

$$
S_t=S_0\exp\left((\mu-\tfrac12\sigma^2)t+\sigma W_t\right)
$$

である。Euler–Maruyamaは

$$
S_{k+1}^{\mathrm{EM}}
=S_k^{\mathrm{EM}}\left(1+\mu\Delta t_k+\sigma\Delta W_k\right)
$$

と更新する。exactとEMに同じ $\Delta W_k$ を使うcouplingにより、pathwise discretization errorをMonte Carloの独立noiseで汚さず比較できる。
"""),
    code("""
initial_price = 100.0
drift = 0.04
volatility = 0.25
horizon = 1.0
step_counts = np.array([4, 8, 16, 32, 64, 128, 256, 512])
strong_errors = []
weak_biases = []
weak_mc_errors = []
weak_mc_standard_errors = []

for n_steps in step_counts:
    grid = np.linspace(0.0, horizon, n_steps + 1)
    time_step = horizon / n_steps
    increment_rng = task_rng(3, n_steps)
    brownian_increments = increment_rng.normal(
        scale=np.sqrt(time_step),
        size=(8_000, int(n_steps)),
    )
    brownian_terminal = brownian_increments.sum(axis=1)
    exact_terminal = initial_price * np.exp(
        (drift - 0.5 * volatility**2) * horizon
        + volatility * brownian_terminal
    )
    euler_terminal = initial_price * np.prod(
        1.0 + drift * time_step + volatility * brownian_increments,
        axis=1,
    )
    strong_errors.append(np.mean(np.abs(euler_terminal - exact_terminal)))

    exact_mean = initial_price * np.exp(drift * horizon)
    euler_mean = initial_price * (1.0 + drift * horizon / n_steps) ** n_steps
    weak_biases.append(abs(euler_mean - exact_mean))
    weak_mc_errors.append(abs(euler_terminal.mean() - exact_mean))
    weak_mc_standard_errors.append(euler_terminal.std(ddof=1) / np.sqrt(len(euler_terminal)))

fig = go.Figure()
fig.add_scatter(
    x=step_counts,
    y=strong_errors,
    mode="lines+markers",
    name="strong error: coupled mean absolute error",
)
fig.add_scatter(
    x=step_counts,
    y=weak_biases,
    mode="lines+markers",
    name="weak bias: analytic expectation",
)
fig.add_scatter(
    x=step_counts,
    y=weak_mc_errors,
    mode="markers",
    name="weak error: one Monte Carlo run",
)
fig.update_layout(
    title="Strong and weak errors answer different questions",
    xaxis_title="Number of time steps",
    xaxis_type="log",
    yaxis_title="Absolute error",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
strong errorは同じBrownian path上の $\mathbb{E}|S_T^{\mathrm{EM}}-S_T|$ を測り、path-dependent payoffやpath再現に関係する。weak errorは $|\mathbb{E}[\phi(S_T^{\mathrm{EM}})]-\mathbb{E}[\phi(S_T)]|$ を測る。

図のanalytic weak biasは時間離散化だけを表す。一方、1回のMonte Carlo推定値にはstandard errorが重なるため、細かいgridでbiasが小さくなるとsampling noiseに隠れる。convergence orderを推定するときは、coupling、replication、confidence intervalを設計する。
"""),
    code("""
error_table = pd.DataFrame(
    {
        "n_steps": step_counts,
        "strong_mae": strong_errors,
        "analytic_weak_bias": weak_biases,
        "one_run_weak_error": weak_mc_errors,
        "one_run_mc_se": weak_mc_standard_errors,
    }
)
display(error_table.round(6))
"""),
    md(r"""
## 5. Sampling errorとdiscretization biasを分ける

Monte Carlo estimator $\hat\theta_N=N^{-1}\sum_iY_i$ のstandard errorは、有限分散なら概ね

$$
\operatorname{SE}(\hat\theta_N)=\frac{s_Y}{\sqrt{N}}
$$

で減る。一方、固定step幅 $h$ のEuler estimatorが狙うのは一般に $\theta_h$ であり、path数を増やしても $\theta_h-\theta$ は残る。

$$
\hat\theta_{N,h}-\theta
=\underbrace{(\hat\theta_{N,h}-\theta_h)}_{\text{sampling error}}
+\underbrace{(\theta_h-\theta)}_{\text{discretization bias}}.
$$

時間gridとpath数は別軸でvalidationする。
"""),
    md(r"""
## 6. Vanilla callとvariance reduction

risk-neutral GBMで $\mu=r$ とし、discounted call payoffを

$$
Y=e^{-rT}(S_T-K)^+
$$

とする。比較する方法は次の3つ。

1. plain Monte Carlo
2. $Z$ と $-Z$ を組にするantithetic estimator
3. 既知の $\mathbb{E}[e^{-rT}S_T]=S_0$ を使うcontrol variate

公平な比較のため、すべて同じ **normal draw予算** を使う。antitheticではpair平均を1観測としてstandard errorを計算し、相関した2 payoffを独立標本として数えない。
"""),
    code("""
rate = 0.03
strike = 105.0
n_normal_draws = 80_000
discount = np.exp(-rate * horizon)

plain_rng = task_rng(4)
plain_normals = plain_rng.standard_normal(n_normal_draws)
plain_terminal = initial_price * np.exp(
    (rate - 0.5 * volatility**2) * horizon
    + volatility * np.sqrt(horizon) * plain_normals
)
plain_payoffs = discount * np.maximum(plain_terminal - strike, 0.0)
plain_result = estimate_expectation(plain_payoffs)

paired_normals = antithetic_variates(
    n_pairs=n_normal_draws,
    n_dimensions=1,
    rng=task_rng(5),
).ravel()
paired_terminal = initial_price * np.exp(
    (rate - 0.5 * volatility**2) * horizon
    + volatility * np.sqrt(horizon) * paired_normals
)
paired_payoffs = discount * np.maximum(paired_terminal - strike, 0.0)
antithetic_pair_means = 0.5 * (
    paired_payoffs[:n_normal_draws] + paired_payoffs[n_normal_draws:]
)
antithetic_result = estimate_expectation(antithetic_pair_means)

discounted_terminal = discount * plain_terminal
control_result = control_variate(
    plain_payoffs,
    discounted_terminal,
    known_control_mean=initial_price,
)
control_estimate = estimate_expectation(control_result.adjusted_samples)

d1 = (
    np.log(initial_price / strike)
    + (rate + 0.5 * volatility**2) * horizon
) / (volatility * np.sqrt(horizon))
d2 = d1 - volatility * np.sqrt(horizon)
analytic_call = initial_price * norm.cdf(d1) - strike * discount * norm.cdf(d2)

variance_reduction_table = pd.DataFrame(
    [
        {
            "method": "plain",
            "estimate": plain_result.estimate,
            "standard_error": plain_result.standard_error,
            "normal_draws": n_normal_draws,
            "payoff_evaluations": n_normal_draws,
        },
        {
            "method": "antithetic pairs",
            "estimate": antithetic_result.estimate,
            "standard_error": antithetic_result.standard_error,
            "normal_draws": n_normal_draws,
            "payoff_evaluations": 2 * n_normal_draws,
        },
        {
            "method": "control variate",
            "estimate": control_estimate.estimate,
            "standard_error": control_estimate.standard_error,
            "normal_draws": n_normal_draws,
            "payoff_evaluations": n_normal_draws,
        },
    ]
)
variance_reduction_table["absolute_error"] = np.abs(
    variance_reduction_table["estimate"] - analytic_call
)
plain_variance_cost = plain_result.standard_error**2 * n_normal_draws
variance_reduction_table["payoff_cost_efficiency_vs_plain"] = (
    plain_variance_cost
    / (
        variance_reduction_table["standard_error"] ** 2
        * variance_reduction_table["payoff_evaluations"]
    )
)
display(variance_reduction_table.round(6))
print("analytic call value:", analytic_call)
print("control coefficient:", control_result.coefficient)
"""),
    code("""
fig = go.Figure()
fig.add_bar(
    x=variance_reduction_table["method"],
    y=variance_reduction_table["standard_error"],
    name="estimated standard error",
)
fig.update_layout(
    title="Variance reduction under a matched normal-draw budget",
    xaxis_title="Estimator",
    yaxis_title="Standard error",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
variance reductionは常に効くわけではない。antithetic pairのpayoff相関が十分に負か、controlとtargetの相関が強いかを実測する。表のpayoff cost efficiencyはvarianceとpayoff評価数の積による簡易比較であり、1より大きければplainより効率的である。係数を同じ標本で推定する小標本biasや、methodごとのwall-clockも最終比較では報告する。
"""),
    md(r"""
## 7. 失敗モード

- $\Delta W\sim\mathcal{N}(0,\Delta t)$ を実装するとき標準偏差へ $\Delta t$ を渡す
- Brownian pathを線形補間された滑らかな曲線として微分する
- Itô formulaの $\tfrac12\sigma^2f_{xx}$ を通常のchain ruleのように落とす
- strong errorを独立乱数の2本のpathで比較し、discretization errorをnoiseで覆う
- path数だけ増やして固定gridのEuler biasも消えたと考える
- time stepだけ細かくし、Monte Carlo confidence intervalを報告しない
- antithetic payoffを独立な $2N$ 標本としてstandard errorを過小評価する
- variance reductionを同じnormal draw数・計算時間で比較しない
- pricingでphysical driftとrisk-neutral driftを混ぜる
"""),
    md(r"""
## 8. 段階別演習

### 基礎

1. Brownian incrementの標本平均と分散を複数の $\Delta t$ で検証せよ。
2. $f(x)=e^x$ にItô formulaを適用し、補正項を導出せよ。
3. GBM exact transitionとEuler更新を1 stepで比較せよ。

### 標準

4. coupled strong errorをlog–log回帰し、Euler–Maruyamaのorderを推定せよ。
5. smooth payoffとdigital payoffでweak errorの収束を比較せよ。
6. path数とstep数の2次元gridを作り、sampling errorとbiasの支配領域を図示せよ。

### 研究

7. control係数をpilot sampleで推定し、本推定sampleと分離した場合のbiasとvarianceを調べよ。
8. barrier optionでBrownian bridge補正の有無を比較し、monitoring biasを測れ。
"""),
    md(r"""
## 9. Exit Criteria

- [ ] Brownian incrementのvariance scalingを実装・検証できる
- [ ] quadratic variationからItô補正を説明できる
- [ ] GBM exact transitionとEuler–Maruyamaを同じincrementでcoupleできる
- [ ] strong errorとweak errorのestimandを数式で区別できる
- [ ] sampling errorとdiscretization biasを別軸で報告できる
- [ ] antithetic pairを独立観測として数えずstandard errorを計算できる
- [ ] control variateの既知期待値と係数を記録できる
- [ ] analytic benchmarkとconfidence intervalでimplementationを検証できる
"""),
    md(r"""
## 10. 出典

- [Higham, An Algorithmic Introduction to Numerical Simulation of Stochastic Differential Equations](https://epubs.siam.org/doi/full/10.1137/S0036144500378302) — Brownian path、Euler–Maruyama、strong/weak convergenceの再現可能な導入
- [MIT OpenCourseWare 15.070J: Advanced Stochastic Processes, Lecture Notes](https://ocw.mit.edu/courses/15-070j-advanced-stochastic-processes-fall-2013/pages/lecture-notes/) — Brownian motion、quadratic variation、Itô calculus
- [NumPy Random Sampling](https://numpy.org/doc/stable/reference/random/) — `Generator`を中心とした乱数API
- [SciPy `stats.norm`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.norm.html) — analytic benchmarkで使う標準正規分布関数

次章では、乱数源、path生成、payoff、推定、confidence intervalを分離したB2 Monte Carlo libraryへ統合する。
"""),
]
