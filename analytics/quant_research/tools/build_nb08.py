"""Builder for notebook 08: convergence, concentration, and heavy tails."""

from nbkit import code, md

cells = [
    md(r"""
# 08. Week 6 — 収束、極限定理、heavy tail

> 「標本数を増やせば安定する」を、収束の種類・必要なmoment・coverageへ分解する。

## 学習目標

- almost sure、in probability、$L^p$、in distributionの収束を区別できる
- LLN、CLT、delta methodの仮定と結論をsimulationで検証できる
- Hoeffding boundの適用範囲をboundednessから判断できる
- Gaussian、Student $t$、Pareto、Gaussian mixtureのmoment存在条件を説明できる
- confidence intervalのcoverageを反復実験で測り、heavy-tailでの不安定性を診断できる

## 前提知識

- 期待値、分散、独立同分布
- 条件付き確率と `numpy.random.Generator`
- 標本平均、標本標準偏差、confidence intervalの初歩
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
    "distribution_counterexample",
    "path_counterexample",
    "lln_rate",
    "clt",
    "hoeffding",
    "delta",
    "coverage",
    "pareto_extremes",
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
## 1. 4種類の収束は同じ主張ではない

$X_n$ が $X$ へ近づくとき、何を0へ送るかで意味が変わる。

| 収束 | 定義 | 何を制御するか |
|---|---|---|
| almost surely | $\mathbb{P}(\lim_n X_n=X)=1$ | ほぼすべてのsample path |
| in probability | $\mathbb{P}(|X_n-X|>\varepsilon)\to0$ | 固定した誤差を外す確率 |
| in $L^p$ | $\mathbb{E}[|X_n-X|^p]\to0$ | $p$ 乗平均誤差 |
| in distribution | $F_{X_n}(x)\to F_X(x)$ | 分布関数の連続点 |

一般に

$$
X_n\xrightarrow{L^p}X
\Longrightarrow X_n\xrightarrow{P}X
\Longrightarrow X_n\xrightarrow{d}X,
$$

また

$$
X_n\xrightarrow{a.s.}X
\Longrightarrow X_n\xrightarrow{P}X.
$$

逆向きは追加条件なしには成り立たない。almost sure収束と $L^p$ 収束の間にも一般の含意はない。
"""),
    md(r"""
### Counterexample 1 — distributionは近づいても同じ確率空間上で近づかない

$X,X_1,X_2,\ldots$ を互いに独立な標準正規とする。すべて同じ分布なので $X_n\xrightarrow{d}X$ と書ける。一方、差は $X_n-X\sim\mathcal{N}(0,2)$ だから

$$
\mathbb{P}(|X_n-X|>\varepsilon)
$$

は $n$ とともに0へ行かない。分布収束は、確率変数同士がpathごとに近いとは述べない。
"""),
    code("""
rng = np.random.default_rng(STREAM_SEQUENCES["distribution_counterexample"])
replications = 100_000
limit_variable = rng.normal(size=replications)
epsilon = 0.5
exceedance_probabilities = []

for _ in range(8):
    candidate = rng.normal(size=replications)
    exceedance_probabilities.append(
        np.mean(np.abs(candidate - limit_variable) > epsilon)
    )

theoretical_exceedance = 2.0 * stats.norm.sf(epsilon / np.sqrt(2.0))
print("empirical exceedance probabilities:", np.round(exceedance_probabilities, 4))
print("theoretical constant:", round(float(theoretical_exceedance), 4))
"""),
    md(r"""
### Counterexample 2 — probability収束だけではeventualなpath安定性を言えない

独立な $X_n\sim\operatorname{Bernoulli}(1/n)$ なら

$$
\mathbb{P}(|X_n|>1/2)=1/n\to0
$$

なので $X_n\xrightarrow{P}0$ である。しかし $\sum_n 1/n=\infty$ で、独立性とBorel–Cantelli lemmaから $X_n=1$ はほぼ確実に無限回起こる。したがってalmost surelyには0へ収束しない。

有限simulationは「無限回」を証明できない。理論が主張するeventual behaviorと、有限horizonの図を区別する。
"""),
    code("""
path_rng = np.random.default_rng(STREAM_SEQUENCES["path_counterexample"])
probability_grid = np.unique(np.geomspace(2, 4000, 70).astype(int))
probability_trials = path_rng.random((30_000, probability_grid.size))
empirical_event_probability = (
    probability_trials < (1.0 / probability_grid)
).mean(axis=0)

n_grid = np.arange(1, 4001)
bernoulli_paths = path_rng.random((250, n_grid.size)) < (1.0 / n_grid)
late_event_fraction = bernoulli_paths[:, 2000:].any(axis=1).mean()

fig = go.Figure()
fig.add_scatter(
    x=probability_grid,
    y=empirical_event_probability,
    mode="lines+markers",
    name="Empirical P(X_n = 1)",
)
fig.add_scatter(
    x=probability_grid,
    y=1.0 / probability_grid,
    mode="lines",
    name="1 / n",
    line={"dash": "dash"},
)
fig.update_layout(
    title="Convergence in probability does not describe entire paths",
    xaxis_title="n",
    yaxis_title="Event probability",
    xaxis_type="log",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()

print("fraction of finite paths with an event after n=2000:", late_event_fraction)
"""),
    md(r"""
## 2. LLNとMonte Carlo rate

独立同分布で $\mathbb{E}[|X_1|]<\infty$ なら、標本平均 $\bar X_n$ は平均 $\mu$ へ収束する。weak lawはprobability収束、strong lawはalmost sure収束を与える。適用する定理の版により仮定は異なるため、「LLNより」とだけ書かず、使った版を明示する。

有限分散 $\sigma^2$ も存在すれば

$$
\mathbb{E}[(\bar X_n-\mu)^2]=\frac{\sigma^2}{n}
$$

であり、RMSEは $n^{-1/2}$ で減る。次の関数は、このbaselineを独立反復で測る。B2 Projectでは同じ入出力をpackageの `convergence_experiment` へ移し、distribution名、seed tree、実行時間も返す。
"""),
    code("""
def convergence_experiment(
    rng,
    sampler,
    true_mean,
    sample_sizes,
    replications,
):
    records = []
    for sample_size in sample_sizes:
        draws = sampler(rng, (replications, int(sample_size)))
        estimates = draws.mean(axis=1)
        errors = estimates - true_mean
        records.append(
            {
                "sample_size": int(sample_size),
                "bias": float(errors.mean()),
                "rmse": float(np.sqrt(np.mean(errors**2))),
                "median_absolute_error": float(np.median(np.abs(errors))),
            }
        )
    return records


sample_sizes = np.array([25, 100, 400, 1600, 6400])
normal_records = convergence_experiment(
    np.random.default_rng(STREAM_SEQUENCES["lln_rate"]),
    lambda generator, size: generator.normal(size=size),
    true_mean=0.0,
    sample_sizes=sample_sizes,
    replications=1_000,
)
normal_rmse = np.array([record["rmse"] for record in normal_records])
rmse_slope = np.polyfit(np.log(sample_sizes), np.log(normal_rmse), 1)[0]

fig = go.Figure()
fig.add_scatter(
    x=sample_sizes,
    y=normal_rmse,
    mode="lines+markers",
    name="Empirical RMSE",
)
fig.add_scatter(
    x=sample_sizes,
    y=1.0 / np.sqrt(sample_sizes),
    mode="lines",
    name="1 / sqrt(n)",
    line={"dash": "dash"},
)
fig.update_layout(
    title="LLN error rate for a finite-variance sample mean",
    xaxis_title="Sample size n",
    yaxis_title="RMSE",
    xaxis_type="log",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()

print("empirical log-log slope:", round(float(rmse_slope), 3))
"""),
    md(r"""
## 3. CLTとconfidence interval

$X_i$ が独立同分布で平均 $\mu$、有限で正の分散 $\sigma^2$ を持つとき、central limit theoremは

$$
\frac{\sqrt{n}(\bar X_n-\mu)}{\sigma}
\xrightarrow{d}\mathcal{N}(0,1)
$$

を与える。これは $\bar X_n$ 自体が正規分布になるという主張ではなく、中心化・scaleした誤差の分布収束である。

母標準偏差を標本標準偏差 $s$ へ置き換えた近似interval

$$
\bar X_n\pm z_{1-\alpha/2}\frac{s}{\sqrt n}
$$

は、反復実験で真値を含む割合coverageを測って初めて検証できる。1本のintervalが真値を含んだかどうかはcoverageではない。
"""),
    code("""
clt_rng = np.random.default_rng(STREAM_SEQUENCES["clt"])
clt_replications = 25_000
clt_sample_size = 40
bernoulli_probability = 0.2
bernoulli_draws = clt_rng.binomial(
    1,
    bernoulli_probability,
    size=(clt_replications, clt_sample_size),
)
standardized_means = np.sqrt(clt_sample_size) * (
    bernoulli_draws.mean(axis=1) - bernoulli_probability
) / np.sqrt(bernoulli_probability * (1.0 - bernoulli_probability))

x_grid = np.linspace(-4.0, 4.0, 300)
histogram_density, histogram_edges = np.histogram(
    standardized_means,
    bins=45,
    range=(-4.0, 4.0),
    density=True,
)
histogram_centers = 0.5 * (histogram_edges[:-1] + histogram_edges[1:])
fig = go.Figure()
fig.add_bar(
    x=histogram_centers,
    y=histogram_density,
    width=np.diff(histogram_edges),
    name="Standardized means",
    opacity=0.6,
)
fig.add_scatter(
    x=x_grid,
    y=stats.norm.pdf(x_grid),
    mode="lines",
    name="Standard normal",
)
fig.update_layout(
    title="CLT approximation for Bernoulli sample means",
    xaxis_title="Standardized error",
    yaxis_title="Density",
    barmode="overlay",
    template="plotly_white",
)
fig.show()

print("standardized mean:", round(float(standardized_means.mean()), 4))
print("standardized variance:", round(float(standardized_means.var()), 4))
"""),
    md(r"""
Bernoulli標本平均は離散的なので、有限 $n$ のhistogramには段差が残る。正規近似の見た目がよくても、tail probabilityやcoverageは別に確認する。
"""),
    md(r"""
## 4. Hoeffding bound — boundednessを使う

独立な $X_i\in[0,1]$ に対して、Hoeffding inequalityは

$$
\mathbb{P}(|\bar X_n-\mathbb{E}[\bar X_n]|\geq\varepsilon)
\leq 2\exp(-2n\varepsilon^2)
$$

を与える。分布の形や分散を知らなくても使えるが、boundednessが必要である。boundは保証であり、実際の確率と等しいとは限らない。
"""),
    code("""
hoeffding_rng = np.random.default_rng(STREAM_SEQUENCES["hoeffding"])
hoeffding_sizes = np.array([25, 50, 100, 200, 400])
hoeffding_epsilon = 0.06
hoeffding_replications = 30_000
empirical_probabilities = []
hoeffding_bounds = []

for sample_size in hoeffding_sizes:
    draws = hoeffding_rng.binomial(
        1,
        bernoulli_probability,
        size=(hoeffding_replications, int(sample_size)),
    )
    empirical_probabilities.append(
        np.mean(np.abs(draws.mean(axis=1) - bernoulli_probability) >= hoeffding_epsilon)
    )
    hoeffding_bounds.append(min(1.0, 2.0 * np.exp(-2.0 * sample_size * hoeffding_epsilon**2)))

fig = go.Figure()
fig.add_scatter(
    x=hoeffding_sizes,
    y=empirical_probabilities,
    mode="lines+markers",
    name="Empirical probability",
)
fig.add_scatter(
    x=hoeffding_sizes,
    y=hoeffding_bounds,
    mode="lines+markers",
    name="Hoeffding bound",
)
fig.update_layout(
    title="A distribution-free bound can be conservative",
    xaxis_title="Sample size n",
    yaxis_title="Tail probability",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
Gaussian、Student $t$、Paretoはboundedでないため、この形のHoeffding boundをそのまま適用できない。観測データのsample maximumを上限とみなすのも誤りである。clippingを使えばboundedになるが、estimandを変えるbiasとのtrade-offが生じる。
"""),
    md(r"""
## 5. Delta method

$\sqrt n(T_n-\theta)\xrightarrow{d}\mathcal{N}(0,\tau^2)$ で、$g$ が $\theta$ で微分可能なら

$$
\sqrt n\left(g(T_n)-g(\theta)\right)
\xrightarrow{d}\mathcal{N}\left(0,[g'(\theta)]^2\tau^2\right).
$$

$X_i\sim\operatorname{Exponential}(1)$、$T_n=\bar X_n$、$g(x)=\log x$ なら $\theta=1$、$\tau^2=1$、$g'(1)=1$ なので漸近分散は1である。非線形変換後の有限標本biasはdelta methodの一次近似からは消えない。
"""),
    code("""
delta_rng = np.random.default_rng(STREAM_SEQUENCES["delta"])
delta_replications = 30_000
delta_sample_size = 80
exponential_means = delta_rng.exponential(
    scale=1.0,
    size=(delta_replications, delta_sample_size),
).mean(axis=1)
delta_statistic = np.sqrt(delta_sample_size) * np.log(exponential_means)

delta_quantiles = np.quantile(delta_statistic, [0.025, 0.5, 0.975])
normal_quantiles = stats.norm.ppf([0.025, 0.5, 0.975])
print("delta-method quantiles:", np.round(delta_quantiles, 4))
print("normal reference quantiles:", np.round(normal_quantiles, 4))
print("finite-sample transformed bias:", round(float(delta_statistic.mean()), 4))
print("finite-sample transformed variance:", round(float(delta_statistic.var()), 4))
"""),
    md(r"""
## 6. Momentの存在を先に確認する

| Distribution | Mean | Variance | 注意点 |
|---|---|---|---|
| Gaussian | 常に有限 | 常に有限 | tailは比較的軽い |
| Student $t_\nu$ | $\nu>1$ で有限 | $\nu>2$ で有限 | $\nu$ が小さいと高次momentが消える |
| Pareto $\alpha$ | $\alpha>1$ で有限 | $\alpha>2$ で有限 | 最大値が標本平均を支配しやすい |
| finite Gaussian mixture | 有限 | 有限 | rare componentを有限標本で見落としやすい |

scale 1のParetoで $x\geq1$、密度 $f(x)=\alpha x^{-(\alpha+1)}$ とすると

$$
\mathbb{E}[X^k]
=\alpha\int_1^\infty x^{k-\alpha-1}\,dx
=\frac{\alpha}{\alpha-k}
$$

は $k<\alpha$ のときだけ有限である。$1<\alpha\leq2$ では平均は存在するが分散は存在しない。LLNを期待できても、有限分散を仮定する通常のCLTと $n^{-1/2}$ standard errorはそのまま使えない。
"""),
    code("""
def gaussian_sampler(rng, size):
    return rng.normal(size=size)


def student_t_sampler(rng, size):
    return rng.standard_t(df=3.0, size=size)


def pareto_sampler(rng, size):
    return rng.pareto(a=1.5, size=size) + 1.0


def gaussian_mixture_sampler(rng, size):
    rare_component = rng.random(size=size) < 0.01
    scales = np.where(rare_component, 20.0, 1.0)
    return rng.normal(scale=scales, size=size)


def wald_interval_experiment(
    rng,
    sampler,
    true_mean,
    sample_size,
    replications,
    confidence_level=0.95,
):
    draws = sampler(rng, (replications, sample_size))
    estimates = draws.mean(axis=1)
    standard_errors = draws.std(axis=1, ddof=1) / np.sqrt(sample_size)
    critical_value = stats.norm.ppf(0.5 + confidence_level / 2.0)
    lower = estimates - critical_value * standard_errors
    upper = estimates + critical_value * standard_errors
    coverage = float(np.mean((lower <= true_mean) & (true_mean <= upper)))
    coverage_mc_se = float(
        np.sqrt(coverage * (1.0 - coverage) / replications)
    )
    coverage_mc_half_width = 1.96 * coverage_mc_se
    return {
        "coverage": coverage,
        "coverage_mc_se": coverage_mc_se,
        "coverage_mc_lower": max(0.0, coverage - coverage_mc_half_width),
        "coverage_mc_upper": min(1.0, coverage + coverage_mc_half_width),
        "median_width": float(np.median(upper - lower)),
        "p95_width": float(np.quantile(upper - lower, 0.95)),
        "p95_absolute_error": float(np.quantile(np.abs(estimates - true_mean), 0.95)),
        "maximum_estimate": float(np.max(estimates)),
    }


distribution_specs = {
    "Gaussian": (gaussian_sampler, 0.0),
    "Student t(3)": (student_t_sampler, 0.0),
    "Pareto(1.5)": (pareto_sampler, 3.0),
    "Gaussian mixture": (gaussian_mixture_sampler, 0.0),
}
coverage_sizes = np.array([50, 200, 800])
coverage_records = []
child_sequences = iter(
    STREAM_SEQUENCES["coverage"].spawn(
        len(distribution_specs) * len(coverage_sizes)
    )
)

for distribution_name, (sampler, true_mean) in distribution_specs.items():
    for sample_size in coverage_sizes:
        result = wald_interval_experiment(
            np.random.default_rng(next(child_sequences)),
            sampler,
            true_mean=true_mean,
            sample_size=int(sample_size),
            replications=2_000,
        )
        coverage_records.append(
            {
                "distribution": distribution_name,
                "sample_size": int(sample_size),
                **result,
            }
        )

fig = go.Figure()
for distribution_name in distribution_specs:
    matching = [
        record
        for record in coverage_records
        if record["distribution"] == distribution_name
    ]
    fig.add_scatter(
        x=[record["sample_size"] for record in matching],
        y=[record["coverage"] for record in matching],
        mode="lines+markers",
        name=distribution_name,
        error_y={
            "type": "data",
            "array": [1.96 * record["coverage_mc_se"] for record in matching],
            "visible": True,
        },
    )
fig.add_hline(y=0.95, line_dash="dash", line_color="black")
fig.update_layout(
    title="Coverage of nominal 95% Gaussian Wald intervals",
    xaxis_title="Sample size n",
    yaxis_title="Empirical coverage",
    xaxis_type="log",
    yaxis_range=[0.60, 1.0],
    template="plotly_white",
)
fig.show()

coverage_table = pd.DataFrame(coverage_records)[
    [
        "distribution",
        "sample_size",
        "coverage",
        "coverage_mc_se",
        "coverage_mc_lower",
        "coverage_mc_upper",
        "median_width",
        "p95_width",
        "p95_absolute_error",
    ]
]
display(coverage_table.round(4))
"""),
    md(r"""
coverageのずれにはMonte Carlo errorもある。coverage推定値 $\hat c$ 自体のstandard errorは概ね

$$
\sqrt{\frac{\hat c(1-\hat c)}{R}}
$$

であり、$R$ は反復数である。図のerror barと表の `coverage_mc_lower` / `coverage_mc_upper` は、このstandard errorの1.96倍を使った95% Monte Carlo intervalである。0.950と0.947の差を解釈する前に、この誤差を計算する。

これは、各replicationで作るsample confidence intervalの幅ではない。`median_width` と `p95_width` は各sample intervalの幅を要約し、coverageのMonte Carlo intervalは「真値を含んだか」というindicatorを $R$ 回平均した推定精度を表す。二つのuncertaintyを混同しない。

ParetoのWald intervalは標本標準偏差を数値として返すが、母分散は存在しない。極端値を引かなかったreplicationはintervalを過度に狭くし、極端値を引いたreplicationは幅と中心を急変させる。この対称Gaussian mixtureではcoverage自体がnominalに近い場合もあるが、95%点のinterval幅と絶対誤差はmedianより不安定になる。coverageだけで安定性を判断しない。
"""),
    code("""
pareto_rng = np.random.default_rng(STREAM_SEQUENCES["pareto_extremes"])
pareto_sample_size = 400
pareto_replications = 1_500
pareto_draws = pareto_sampler(
    pareto_rng,
    (pareto_replications, pareto_sample_size),
)
pareto_estimates = pareto_draws.mean(axis=1)
pareto_maxima = pareto_draws.max(axis=1)
maximum_correlation = np.corrcoef(pareto_estimates, pareto_maxima)[0, 1]

fig = go.Figure(
    go.Scattergl(
        x=pareto_maxima,
        y=pareto_estimates,
        mode="markers",
        marker={"size": 5, "opacity": 0.4},
    )
)
fig.add_hline(y=3.0, line_dash="dash", line_color="black")
fig.update_layout(
    title="A single extreme observation can dominate a Pareto sample mean",
    xaxis_title="Sample maximum",
    yaxis_title="Sample mean",
    xaxis_type="log",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()

print("correlation between sample mean and sample maximum:", round(float(maximum_correlation), 4))
print("median estimate:", round(float(np.median(pareto_estimates)), 4))
print("largest estimate:", round(float(np.max(pareto_estimates)), 4))
"""),
    md(r"""
## 7. 失敗モード — finite sample varianceをfinite population varianceとみなす

どの有限標本にも有限な数値としての標本分散がある。しかし、それは母分散の存在を証明しない。

- distributionのmoment条件を確認せずCLTを引用する
- $t$ 分布のdegrees of freedomやParetoのtail indexを記録しない
- 1回のrunning meanが滑らかになったことを収束証明と呼ぶ
- confidence intervalを作るだけでcoverageを測らない
- Hoeffding boundをunboundedなreturnへ適用する
- 外れ値を削除した後も元の平均を推定していると主張する

clippingやwinsorizationは通常、元の平均とは異なるestimandを狙う。median-of-meansは元の母平均をtargetにできるrobust estimatorであり、bootstrapはestimandではなくsampling distributionを近似するresampling手順である。仮定と保証を一括りにしない。**Advanced**ではrobust estimatorとself-normalizedな推測を扱うが、まずcoreとしてmoment診断と反復coverageを必須にする。
"""),
    md(r"""
## 8. 段階別演習

### 基礎

1. 4種類の収束を定義し、既知の含意を矢印で描け。
2. finite varianceの標本平均でRMSEが $n^{-1/2}$ になることを導出せよ。
3. $t_\nu$ とPareto $\alpha$ について、平均・分散が存在するparameter領域を書け。

### 標準

4. BernoulliのCLT図を $n=10,40,160$ で比較し、離散性とtail近似を評価せよ。
5. Hoeffdingのempirical probabilityとboundの比を $\varepsilon$ ごとに比較せよ。
6. coverage反復数 $R$ に対するcoverage estimateのstandard errorを報告せよ。
7. `convergence_experiment` の入力に独立な `Generator` を要求し、同じspawn treeで結果が再現するtestを書け。

### 研究

8. Pareto tail indexを変え、sample meanのerror rateをlog-log図で推定せよ。
9. **Advanced:** percentile bootstrap intervalを実装し、SciPyの `stats.bootstrap` と照合せよ。
10. **Advanced:** median-of-meansを通常の平均と同じestimandで比較し、contamination率ごとのRMSEを測れ。
"""),
    md(r"""
## 9. Exit Criteria

- [ ] 4種類の収束を定義し、成立しない逆含意の例を挙げられる
- [ ] LLN、CLT、delta methodの仮定と結論を区別できる
- [ ] Hoeffding boundを使える範囲をboundednessから判定できる
- [ ] distribution parameterから平均・分散の存在を確認できる
- [ ] nominal confidence levelとempirical coverageを区別して検証できる
- [ ] 各sampleのconfidence intervalとcoverage反復推定のMonte Carlo intervalを区別できる
- [ ] heavy-tailで通常のWald intervalが不安定になる理由を説明できる
"""),
    md(r"""
## 10. 出典

- [MIT OpenCourseWare 18.600: Probability and Random Variables, Lecture Notes](https://ocw.mit.edu/courses/18-600-probability-and-random-variables-fall-2019/pages/lecture-notes/) — LLN、CLT、条件付き期待値、確率不等式
- [MIT OpenCourseWare 18.600: Readings](https://ocw.mit.edu/courses/18-600-probability-and-random-variables-fall-2019/pages/readings/) — 講義内容に対応する極限定理の読書順
- [NumPy `Generator`](https://numpy.org/doc/stable/reference/random/generator.html) — 固定seedと明示的なgeneratorによるsampling API
- [NumPy `Generator.pareto`](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.pareto.html) — Lomax出力をParetoへ変換するparameterization
- [SciPy `stats.t`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html) — Student $t$ 分布のdensity、moment、sampling API
- [SciPy `stats.bootstrap`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html) — paired/vectorizedを含むbootstrap confidence intervalの参照API

次章では、時間とともに情報が増える設定へ移り、Markov性、filtration、martingale、stopping ruleを区別する。
"""),
]
