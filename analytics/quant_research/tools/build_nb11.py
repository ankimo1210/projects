"""Builder for notebook 11: the B2 Monte Carlo library project."""

from nbkit import code, md

cells = [
    md(r"""
# 11. B2 Project — Monte Carlo Library v0

> 再現できるseedだけでは足りない。乱数stream、path生成、payoff、estimand、interval、bias診断を別々の契約にする。

## 学習目標

- 注入可能な`numpy.random.Generator`を使うMonte Carlo APIを運用する
- path generationとpayoff evaluationを分離する
- point estimate、standard error、confidence intervalを同じ結果objectで管理する
- `SeedSequence`由来の独立streamをworkerへ固定的に割り当てる
- $N^{-1/2}$ scaling、analytic benchmark、Euler biasでlibraryを検証する
- **Advanced:** importance samplingのweightとESS、Brownian bridgeの条件付き分布を診断する

## 前提知識

- Week 5–6の条件付き分布、CLT、heavy tail、coverage
- Week 7のfiltrationとstopping time
- Week 8のBrownian motion、Euler–Maruyama、variance reduction
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy.stats import norm

import quant_textbook.monte_carlo as mc

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
TASK_IDS = {
    "euler_paths": 1,
    "exact_paths": 2,
    "mc_rate": 3,
    "plain_control": 4,
    "antithetic": 5,
    "euler_bias": 6,
    "importance_sampling": 7,
    "brownian_bridge": 8,
}


def task_rng(task_name, *coordinates):
    entropy = [
        RANDOM_SEED,
        TASK_IDS[task_name],
        *(int(coordinate) for coordinate in coordinates),
    ]
    return np.random.default_rng(np.random.SeedSequence(entropy))
"""),
    md(r"""
## 1. Project charterとAPI境界

### 問い

同じsimulation engineを、再現性を壊さず、複数payoff・複数worker・複数variance-reduction法へ再利用できるか。

### Core API

| 関数 | 責務 | 責務に含めないもの |
|---|---|---|
| `simulate_paths` | 時間gridと1-step更新からpathを作る | payoff、discount、CI |
| `estimate_expectation` | 標本平均、標本標準偏差、SE、CI | path生成 |
| `estimate_confidence_interval` | i.i.d.有限分散近似のCI | bias補正 |
| `antithetic_variates` | $Z,-Z$ の組を作る | payoff固有の有効性判断 |
| `control_variate` | 既知期待値で標本を調整する | control期待値の推定 |
| `spawn_generators` | root seedから子streamを作る | worker scheduling |

### Advanced API

- `importance_sampling`: standard normal upper tail専用の教材実装
- `brownian_bridge`: 両端を条件としたBrownian path

v0はCPU上のdense NumPy arrayを対象とする。automatic differentiation、GPU、quasi-Monte Carlo、multi-level Monte Carlo、production derivative conventionsは扱わない。
"""),
    md(r"""
## 2. Data contract — 乱数を隠さない

すべてのstochastic APIは呼び出し側が作った `Generator` を受け取る。module-level global RNGや、関数内の固定seedは使わない。

root seedから複数streamを作るときは `SeedSequence` のspawn機構を使う。seedへworker番号を足すだけの規約ではなく、生成されたchild sequenceをtask IDへ固定する。
"""),
    code("""
streams_first = mc.spawn_generators(RANDOM_SEED, n_streams=4)
streams_second = mc.spawn_generators(RANDOM_SEED, n_streams=4)

draws_first = np.vstack([stream.standard_normal(6) for stream in streams_first])
draws_second = np.vstack([stream.standard_normal(6) for stream in streams_second])

print("same root seed reproduces all streams:", np.array_equal(draws_first, draws_second))
print("distinct child streams give distinct prefixes:", len(np.unique(draws_first, axis=0)) == 4)
print(np.round(draws_first, 3))
"""),
    md(r"""
これはstream間の統計的独立性を有限標本から証明しているのではない。再現可能なspawn契約と、誤って同一streamを複製していないことを確認するsmoke testである。並列実行ではworker数ではなく論理task IDへchild streamを割り当てると、scheduler順序が変わっても結果を再現しやすい。
"""),
    md(r"""
## 3. Path generationとpayoffを分ける

generic simulatorは

$$
X_{k+1}=g(X_k,t_k,\Delta t_k,\xi_{k+1})
$$

というstep関数だけを知る。次のGBM Euler stepは状態を更新するが、strike、discount、payoffを知らない。同じpathへcall、put、digital、path statisticを後から適用できる。
"""),
    code("""
initial_price = 100.0
rate = 0.03
volatility = 0.22
horizon = 1.0
strike = 105.0


def gbm_euler_step(state, time, time_step, rng):
    del time
    normal_draws = rng.standard_normal(state.shape)
    return state + rate * state * time_step + volatility * state * np.sqrt(time_step) * normal_draws


def discounted_call_payoff(paths):
    terminal_values = paths[:, -1]
    return np.exp(-rate * horizon) * np.maximum(terminal_values - strike, 0.0)


time_grid = np.linspace(0.0, horizon, 253)
euler_paths = mc.simulate_paths(
    initial_price,
    time_grid,
    n_paths=60_000,
    step=gbm_euler_step,
    rng=task_rng("euler_paths"),
)
euler_payoffs = discounted_call_payoff(euler_paths)
euler_estimate = mc.estimate_expectation(euler_payoffs)
euler_interval = mc.estimate_confidence_interval(euler_payoffs)

print("path array shape:", euler_paths.shape)
print("Euler call estimate:", euler_estimate.estimate)
print("standard error:", euler_estimate.standard_error)
print("confidence interval:", euler_interval)
"""),
    md(r"""
pathを全保存するとpath-dependent payoffへ再利用できる一方、memoryは $O(Nm)$ で増える。terminal-only payoffならstreamingやterminal-only専用関数へ切り替える設計余地がある。v0では教育上の透明性を優先し、array shapeを明示する。
"""),
    md(r"""
## 4. Analytic benchmark — samplingとtime biasを切り分ける

risk-neutral GBMのEuropean callにはanalytic valueがある。

$$
C_0=S_0\Phi(d_1)-Ke^{-rT}\Phi(d_2),
$$

$$
d_1=\frac{\log(S_0/K)+(r+\sigma^2/2)T}{\sigma\sqrt{T}},
\qquad d_2=d_1-\sigma\sqrt{T}.
$$

exact transition estimatorはsampling errorだけを持つ。Euler estimatorはsampling errorにtime discretization biasが加わる。同じanalytic valueに対し、両方のCIと差を並べる。
"""),
    code("""
discount = np.exp(-rate * horizon)
d1 = (
    np.log(initial_price / strike)
    + (rate + 0.5 * volatility**2) * horizon
) / (volatility * np.sqrt(horizon))
d2 = d1 - volatility * np.sqrt(horizon)
analytic_value = initial_price * norm.cdf(d1) - strike * discount * norm.cdf(d2)

exact_paths = mc.simulate_gbm_exact(
    initial_price,
    rate,
    volatility,
    np.array([0.0, horizon]),
    n_paths=60_000,
    rng=task_rng("exact_paths"),
)
exact_payoffs = discounted_call_payoff(exact_paths)
exact_estimate = mc.estimate_expectation(exact_payoffs)

benchmark_table = pd.DataFrame(
    [
        {
            "method": "Euler, 252 steps",
            "estimate": euler_estimate.estimate,
            "standard_error": euler_estimate.standard_error,
            "error_vs_analytic": euler_estimate.estimate - analytic_value,
        },
        {
            "method": "exact terminal",
            "estimate": exact_estimate.estimate,
            "standard_error": exact_estimate.standard_error,
            "error_vs_analytic": exact_estimate.estimate - analytic_value,
        },
    ]
)
display(benchmark_table.round(6))
print("analytic value:", analytic_value)
"""),
    md(r"""
analytic valueが1回の95% CIに入らないだけで直ちにbugとは言えない。正しい手順でも約5%は外れる。複数seedでcoverageを検証し、Eulerではstepを変えてbias trendも調べる。CIはsampling uncertaintyであってmodel errorやdiscretization biasを覆わない。
"""),
    code("""
bias_step_counts = np.array([8, 32, 128, 512])
bias_path_count = 20_000
paired_bias_rows = []

for n_steps in bias_step_counts:
    time_step = horizon / int(n_steps)
    increments = task_rng("euler_bias", int(n_steps)).normal(
        scale=np.sqrt(time_step),
        size=(bias_path_count, int(n_steps)),
    )
    exact_terminal = initial_price * np.exp(
        (rate - 0.5 * volatility**2) * horizon
        + volatility * increments.sum(axis=1)
    )
    euler_terminal = initial_price * np.prod(
        1.0 + rate * time_step + volatility * increments,
        axis=1,
    )
    exact_discounted_payoff = discount * np.maximum(
        exact_terminal - strike,
        0.0,
    )
    euler_discounted_payoff = discount * np.maximum(
        euler_terminal - strike,
        0.0,
    )
    paired_difference = euler_discounted_payoff - exact_discounted_payoff
    paired_bias_rows.append(
        {
            "n_steps": int(n_steps),
            "estimated_discretization_bias": float(paired_difference.mean()),
            "paired_standard_error": float(
                paired_difference.std(ddof=1) / np.sqrt(bias_path_count)
            ),
        }
    )

paired_bias_table = pd.DataFrame(paired_bias_rows)
display(paired_bias_table.round(7))

fig = go.Figure()
fig.add_scatter(
    x=paired_bias_table["n_steps"],
    y=paired_bias_table["estimated_discretization_bias"],
    error_y={
        "type": "data",
        "array": 1.96 * paired_bias_table["paired_standard_error"],
        "visible": True,
    },
    mode="lines+markers",
    name="paired bias estimate with 95% interval",
)
fig.add_hline(y=0.0, line_dash="dash", line_color="black")
fig.update_layout(
    title="Euler call-payoff bias under common Brownian increments",
    xaxis_title="Number of time steps",
    xaxis_type="log",
    yaxis_title="Estimated discretization bias",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
同一Brownian incrementからexact payoffとEuler payoffを作り、その差をpathごとに取る。これにより、独立run同士の差より小さいpaired standard errorで $\mathbb{E}[Y_h-Y]$ を推定できる。表と図のintervalはbias推定のMonte Carlo uncertaintyである。coarse gridのbiasは0から識別できるが、細かいgridのintervalは0を跨ぐため、有限runから単調なtrendまで主張しない。
"""),
    md(r"""
## 5. $N^{-1/2}$ scalingをreplicationで検証する

1つの大標本で推定SEを見るだけでなく、各sample sizeを独立に複数回実行し、analytic valueに対するRMSEを測る。有限分散なら

$$
\operatorname{RMSE}(\hat\theta_N)\approx cN^{-1/2}
$$

を期待する。各replicationへ別child streamを割り当てる。
"""),
    code("""
sample_sizes = np.array([500, 2_000, 8_000, 32_000])
n_replications = 30
rmse_by_size = []

for sample_size in sample_sizes:
    estimates = []
    for replication_index in range(n_replications):
        replication_rng = task_rng(
            "mc_rate",
            int(sample_size),
            replication_index,
        )
        paths = mc.simulate_gbm_exact(
            initial_price,
            rate,
            volatility,
            np.array([0.0, horizon]),
            n_paths=int(sample_size),
            rng=replication_rng,
        )
        estimates.append(discounted_call_payoff(paths).mean())
    estimates = np.asarray(estimates)
    rmse_by_size.append(np.sqrt(np.mean((estimates - analytic_value) ** 2)))

rmse_by_size = np.asarray(rmse_by_size)
reference_curve = rmse_by_size[0] * np.sqrt(sample_sizes[0] / sample_sizes)
empirical_slope = np.polyfit(np.log(sample_sizes), np.log(rmse_by_size), deg=1)[0]

fig = go.Figure()
fig.add_scatter(
    x=sample_sizes,
    y=rmse_by_size,
    mode="lines+markers",
    name="empirical RMSE",
)
fig.add_scatter(
    x=sample_sizes,
    y=reference_curve,
    mode="lines",
    name="N^(-1/2) reference",
    line={"dash": "dash"},
)
fig.update_layout(
    title="Monte Carlo RMSE across independent replications",
    xaxis_title="Sample size N",
    xaxis_type="log",
    yaxis_title="RMSE",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()
print("log-log slope:", empirical_slope)
"""),
    md(r"""
30 replicationsではslopeそのものにも大きな標本変動がある。合格判定を「ちょうど $-1/2$」にせず、sample sizeとreplication数を増やしたときの安定性、外れreplication、乱数streamの割当を併記する。
"""),
    md(r"""
## 6. Variance reductionを共通harnessで比較する

plain、antithetic、control variateを同じanalytic benchmarkへ通す。ここではplainとcontrolが同じnormal drawsを共有する。antitheticは $N$ 個の独立normal drawsとその符号反転を使い、pair平均を $N$ 個の独立単位として扱う。したがってnormal draw数は揃うがpayoff評価数は2倍である。wall-clockとpayoff評価数もproduction benchmarkでは別列にする。
"""),
    code("""
n_independent_normals = 60_000
plain_normals = task_rng("plain_control").standard_normal(n_independent_normals)
plain_terminal = initial_price * np.exp(
    (rate - 0.5 * volatility**2) * horizon
    + volatility * np.sqrt(horizon) * plain_normals
)
plain_payoffs = discount * np.maximum(plain_terminal - strike, 0.0)
plain_result = mc.estimate_expectation(plain_payoffs)

paired_normals = mc.antithetic_variates(
    n_pairs=n_independent_normals,
    n_dimensions=1,
    rng=task_rng("antithetic"),
).ravel()
paired_terminal = initial_price * np.exp(
    (rate - 0.5 * volatility**2) * horizon
    + volatility * np.sqrt(horizon) * paired_normals
)
paired_payoffs = discount * np.maximum(paired_terminal - strike, 0.0)
pair_means = 0.5 * (
    paired_payoffs[:n_independent_normals]
    + paired_payoffs[n_independent_normals:]
)
antithetic_result = mc.estimate_expectation(pair_means)

control_result = mc.control_variate(
    plain_payoffs,
    discount * plain_terminal,
    known_control_mean=initial_price,
)
controlled_result = mc.estimate_expectation(control_result.adjusted_samples)

comparison = pd.DataFrame(
    [
        {
            "method": "plain",
            "estimate": plain_result.estimate,
            "standard_error": plain_result.standard_error,
            "normal_draws": n_independent_normals,
            "payoff_evaluations": n_independent_normals,
        },
        {
            "method": "antithetic pairs",
            "estimate": antithetic_result.estimate,
            "standard_error": antithetic_result.standard_error,
            "normal_draws": n_independent_normals,
            "payoff_evaluations": 2 * n_independent_normals,
        },
        {
            "method": "control variate",
            "estimate": controlled_result.estimate,
            "standard_error": controlled_result.standard_error,
            "normal_draws": n_independent_normals,
            "payoff_evaluations": n_independent_normals,
        },
    ]
)
comparison["variance_ratio_vs_plain"] = (
    plain_result.standard_error / comparison["standard_error"]
) ** 2
plain_variance_cost = plain_result.standard_error**2 * n_independent_normals
comparison["payoff_cost_efficiency_vs_plain"] = plain_variance_cost / (
    comparison["standard_error"] ** 2 * comparison["payoff_evaluations"]
)
display(comparison.round(5))
print("control coefficient:", control_result.coefficient)
"""),
    code("""
fig = go.Figure()
fig.add_bar(
    x=comparison["method"],
    y=comparison["standard_error"],
    name="estimated standard error",
)
fig.update_layout(
    title="Common estimator harness for variance reduction",
    xaxis_title="Method",
    yaxis_title="Standard error",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
variance ratioはnormal draw数を揃えた統計的比較、payoff cost efficiencyはvarianceとpayoff評価数の積を使う簡易な費用調整である。値が1より大きければplainより効率的である。実際の採用判断では、vectorization、memory、payoffの計算量を含むwall-clockも測る。
"""),
    md(r"""
## 7. Advanced — Importance samplingはESSまで報告する

rare event $p=\mathbb{P}(Z>a)$ をstandard normalから直接推定すると、多くの標本がindicator 0になる。proposal $q=\mathcal{N}(m,1)$ から $X_i$ を生成し、likelihood ratio

$$
w(x)=\frac{\phi(x)}{\phi(x-m)}
$$

を使えば

$$
\hat p_{\mathrm{IS}}=\frac{1}{N}\sum_{i=1}^N
\mathbf{1}\{X_i>a\}w(X_i)
$$

となる。ただしproposalが悪いとweightが集中する。estimateとSEだけでなく、

$$
\operatorname{ESS}=\frac{(\sum_iw_i)^2}{\sum_iw_i^2}
$$

や最大weight比、scale-freeな $CV^2=N/\mathrm{ESS}-1$ を診断する。極端なtailではraw weight varianceがunderflowし得るため、log varianceとunderflow flagも併記する。これはgeneral-purpose Girsanov engineではなく、1次元Gaussian tailに限定した教材APIである。
"""),
    code("""
threshold = 4.0
proposal_means = np.array([0.0, 1.5, 3.0, 4.0, 6.0])
importance_rows = []

for proposal_index, proposal_mean in enumerate(proposal_means):
    result = mc.importance_sampling(
        threshold,
        n_samples=120_000,
        proposal_mean=float(proposal_mean),
        rng=task_rng("importance_sampling", proposal_index),
    )
    importance_rows.append(
        {
            "proposal_mean": proposal_mean,
            "estimate": result.estimate,
            "standard_error": result.standard_error,
            "raw_weight_ess": result.effective_sample_size,
            "weight_cv_squared": result.weight_coefficient_of_variation_squared,
            "log_weight_variance": result.log_weight_variance,
            "weight_variance_underflow": result.weight_variance_underflow,
            "nonzero_contributions": result.nonzero_contributions,
            "max_contribution_share": result.max_contribution_share,
            "max_normalized_raw_weight": result.max_weight
            / (result.weight_mean * result.n_samples),
            "log_weight_range": result.log_weight_range,
            "normal_ci_warning": result.nonzero_contributions < 30,
        }
    )

importance_table = pd.DataFrame(importance_rows)
importance_table["absolute_error"] = np.abs(
    importance_table["estimate"] - norm.sf(threshold)
)
display(importance_table.round(8))
print("analytic tail probability:", norm.sf(threshold))
"""),
    code("""
fig = go.Figure()
fig.add_scatter(
    x=importance_table["proposal_mean"],
    y=importance_table["standard_error"],
    mode="lines+markers",
    name="standard error",
)
fig.add_scatter(
    x=importance_table["proposal_mean"],
    y=importance_table["raw_weight_ess"] / 120_000,
    mode="lines+markers",
    name="ESS fraction",
    yaxis="y2",
)
fig.update_layout(
    title="Proposal choice changes both precision and weight stability",
    xaxis_title="Proposal mean",
    yaxis={"title": "Standard error", "type": "log"},
    yaxis2={
        "title": "ESS / N",
        "overlaying": "y",
        "side": "right",
        "range": [0.0, 1.05],
    },
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
raw weightのESSはtargetとproposal全体のoverlap診断であり、indicator付きintegrandの推定varianceを完全には要約しない。rare-event estimatorではnonzero payoff率、weighted contributionの最大比、log-weight rangeも確認する。proposalをthresholdへ近づければ常に改善する、という単調な規則はない。

normal CI warningが真ならnonzero contributionが30未満であり、標本分散から作るnormal intervalは特に不安定である。これは普遍的な閾値ではなく、0やごく少数のhitから精度を主張しないための停止信号である。
"""),
    md(r"""
## 8. Advanced — Brownian bridge

$W_0=x_0$、$W_T=x_T$ を条件としたBrownian bridgeは、中間時刻 $t$ で

$$
\mathbb{E}[W_t\mid W_0=x_0,W_T=x_T]
=x_0+\frac{t}{T}(x_T-x_0),
$$

$$
\operatorname{Var}(W_t\mid W_0=x_0,W_T=x_T)
=\frac{t(T-t)}{T}
$$

を持つ。endpointを正確に固定し、経験的mean・varianceを式と比較する。
"""),
    code("""
bridge_times = np.linspace(0.0, 1.0, 101)
bridge_start = -0.4
bridge_end = 0.8
bridge_paths = mc.brownian_bridge(
    bridge_times,
    start=bridge_start,
    end=bridge_end,
    n_paths=12_000,
    rng=task_rng("brownian_bridge"),
)

bridge_mean = bridge_start + bridge_times * (bridge_end - bridge_start)
bridge_variance = bridge_times * (1.0 - bridge_times)
midpoint_index = len(bridge_times) // 2

print("maximum start error:", np.max(np.abs(bridge_paths[:, 0] - bridge_start)))
print("maximum end error:", np.max(np.abs(bridge_paths[:, -1] - bridge_end)))
print("midpoint empirical mean:", bridge_paths[:, midpoint_index].mean())
print("midpoint target mean:", bridge_mean[midpoint_index])
print("midpoint empirical variance:", bridge_paths[:, midpoint_index].var(ddof=1))
print("midpoint target variance:", bridge_variance[midpoint_index])

fig = go.Figure()
for path_index in range(16):
    fig.add_scatter(
        x=bridge_times,
        y=bridge_paths[path_index],
        mode="lines",
        name=f"bridge {path_index + 1}",
        showlegend=False,
        line={"width": 1},
    )
fig.add_scatter(
    x=bridge_times,
    y=bridge_mean,
    mode="lines",
    name="conditional mean",
    line={"color": "black", "width": 3},
)
fig.update_layout(
    title="Brownian bridges with fixed endpoints",
    xaxis_title="Time",
    yaxis_title="Bridge value",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
bridgeはunconditional Brownian motionの代用品ではない。endpointを条件とするsampling、path reconstruction、barrier crossing補正など、条件付きlawが対象のときに使う。粗いgridのbarrier optionでbridgeを使っても、model riskやvolatility discretizationまで自動的に解決しない。
"""),
    md(r"""
## 9. Validation matrix

| Contract | Oracle / invariant | v0 check |
|---|---|---|
| RNG injection | 同一root seedとtask map | exact replay |
| child streams | prefixを複製しない | distinct smoke test |
| path shape | $(N,m+1)$ または指定grid長 | explicit shape |
| estimator | constant sample | zero SE、degenerate CI |
| Gaussian mean | analytic mean | repeated coverage |
| Monte Carlo rate | finite-variance benchmark | RMSE slope near $-1/2$ |
| GBM exact | Black–Scholes value | analytic agreement |
| Euler | grid refinement | bias trend |
| antithetic | pair covariance | pair-level SE |
| control variate | known control mean | variance reduction and coefficient |
| Advanced: importance sampling | Gaussian survival function | estimate、SE、ESS、weight concentration |
| Advanced: Brownian bridge | endpoints、conditional moments | exact endpoints and moment tolerance |

unit testは単一seedのsnapshotだけにしない。algebraic invariant、analytic moment、複数seed coverage、収束trendを組み合わせる。
"""),
    md(r"""
## 10. 失敗モード

- stochastic function内部で `default_rng(固定値)` を作り、全callが同じpathになる
- 同じ `Generator` stateを複数workerへ複製する
- worker番号をseedへ足すだけで、task mappingと再現規約を残さない
- path生成器へstrikeやdiscountを埋め込み、payoffを再利用できなくする
- confidence intervalへEuler biasやmodel riskまで含まれると解釈する
- CIがanalytic valueを1回外れただけで実装を失格にする
- antithetic pairを独立な2観測としてSEを計算する
- controlの期待値を同じ標本から無検証で代用する
- importance samplingのestimateだけを見てweight concentrationとESSを捨てる
- Brownian bridgeをunconditional pathとして使う
"""),
    md(r"""
## 11. 段階別演習

### 基礎

1. constant sampleを`estimate_expectation`へ渡し、SEとCIを確認せよ。
2. 同じroot seedからspawnしたstreamを論理taskへ固定し、実行順を変えて再現せよ。
3. 同一pathへcall、put、digital payoffを適用し、path generatorを変更していないことを示せ。

### 標準

4. sample sizeを倍々にし、推定SEとreplication RMSEの両方で $N^{-1/2}$ を検証せよ。
5. GBM Eulerのstep数とpath数を2次元gridで変え、bias–variance–cost frontierを作れ。
6. antitheticとcontrol variateをwall-clock、normal draws、payoff評価数の3基準で比較せよ。

### 研究

7. rare-event thresholdごとにproposal meanを選び、ESSだけでは捉えないweighted contribution診断を設計せよ。
8. Brownian bridgeを用いたbarrier crossing probabilityを導出し、naive grid monitoringとのbiasを比較せよ。
"""),
    md(r"""
## 12. Exit Criteria

### Core必須

- [ ] すべてのstochastic APIへ`Generator`を注入できる
- [ ] root seed、child stream、task mappingを保存してrunを再現できる
- [ ] path generationとpayoff evaluationを別関数にできる
- [ ] estimate、SE、CIを同じ標本規約で報告できる
- [ ] independent replicationで $N^{-1/2}$ scalingを検証できる
- [ ] sampling errorとEuler discretization biasを別々に測れる
- [ ] antitheticをpair単位、control variateを既知期待値付きで評価できる
- [ ] analytic oracleがない場合のinvariant、refinement、coverage testを設計できる

### Advanced（任意）

- [ ] importance samplingでestimate、SE、ESS、weight concentrationを報告できる
- [ ] Brownian bridgeのendpointとconditional momentsを検証できる
"""),
    md(r"""
## 13. 出典

- [NumPy Random Sampling](https://numpy.org/doc/stable/reference/random/) — `Generator`とbit generatorを分離した公式乱数API
- [NumPy `Generator.spawn`](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.spawn.html) — child generatorの生成
- [NumPy `SeedSequence`](https://numpy.org/doc/stable/reference/random/bit_generators/generated/numpy.random.SeedSequence.html) — reproducible child streamのentropy mixing
- [Higham, An Algorithmic Introduction to Numerical Simulation of Stochastic Differential Equations](https://epubs.siam.org/doi/full/10.1137/S0036144500378302) — Euler–Maruyama、strong/weak convergence、Monte Carlo実験
- [MIT OpenCourseWare 15.070J: Advanced Stochastic Processes, Lecture Notes](https://ocw.mit.edu/courses/15-070j-advanced-stochastic-processes-fall-2013/pages/lecture-notes/) — Brownian motion、quadratic variation、martingale、Itô calculus
- [MIT OpenCourseWare 12.S990 Lecture 9: Importance Sampling](https://ocw.mit.edu/courses/12-s990-quantifying-uncertainty-fall-2012/ff0cab7501864a96a25c96796b36155a_MIT12_S990F12_lec9.pdf) — likelihood ratioとrare-event importance sampling
- [MIT OpenCourseWare 18.642 Lecture 14.1: Brownian Bridge](https://ocw.mit.edu/courses/18-642-topics-in-mathematics-with-applications-in-finance-fall-2024/mit18_642_f24_lec14_1.pdf) — endpointを条件としたBrownian bridge
- [Glynn, Efficiency Improvement Techniques](https://web.stanford.edu/~glynn/papers/1994/G94c.html) — variance reductionを計算費用込みで比較する基準

B2完了後は、B3で時系列依存、stationarity、forecast validationへ進む。Monte Carlo APIの独立streamとuncertainty contractは、その後のbootstrapやsimulation-based forecastにも引き継ぐ。
"""),
]
