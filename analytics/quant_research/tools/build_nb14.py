"""Builder for notebook 14: testing, resampling, and multiple comparisons."""

from nbkit import code, md

cells = [
    md(r"""
# 14. Week 10 — 検定、resampling、多重比較

> p-valueを単独で報告せず、effect size、interval、power、選択規則、family全体の誤りへ戻す。

## 学習目標

- effect size、confidence interval、p-value、powerを別々に定義・報告できる
- likelihood-ratio、Wald、score testの評価点と必要なfitを比較できる
- parametric / nonparametric bootstrapとpermutation testが近似するsampling mechanismを説明できる
- BonferroniのFWER制御とBenjamini–HochbergのFDR制御を使い分けられる
- selection-induced biasとdata snoopingをsimulationで再現できる
- iid bootstrapをdependent time seriesへ適用した失敗を診断できる
- type-I error、FDR、powerをMonte Carlo SE付きで報告できる

## 前提知識

- Week 9のestimand、likelihood、model-based SE、finite-sample coverage
- Week 6のCLT、confidence interval、Monte Carlo error
- B2の明示的な `numpy.random.Generator` とnamed stream
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy import stats

import quant_textbook.inference as inference
import quant_textbook.resampling as resampling

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
NOTEBOOK_ID = 14
TASK_IDS = {
    "effect_example": 1,
    "power": 2,
    "bernoulli_tests": 3,
    "bootstrap_sample": 4,
    "bootstrap_nonparametric": 5,
    "bootstrap_parametric": 6,
    "bootstrap_scipy": 7,
    "permutation_sample": 8,
    "permutation_custom": 9,
    "permutation_scipy": 10,
    "multiple_testing": 11,
    "fdr_audit": 12,
    "selection_bias": 13,
    "ar_observed": 14,
    "ar_sampling": 15,
    "ar_iid_bootstrap": 16,
}


def task_rng(task_name, *coordinates):
    entropy = [
        RANDOM_SEED,
        NOTEBOOK_ID,
        TASK_IDS[task_name],
        *(int(coordinate) for coordinate in coordinates),
    ]
    return np.random.default_rng(np.random.SeedSequence(entropy))
"""),
    md(r"""
## 1. primary estimandとhypothesis familyを先に固定する

この章のprimary analysisは、独立な二群のpopulation mean difference

$$
\Delta=\mathbb{E}[Y\mid G=1]-\mathbb{E}[Y\mid G=0]
$$

をoutcome単位で推定することとする。null hypothesisは $H_0:\Delta=0$、two-sided alternativeを使う。group assignmentがrandomizedでない場合、この差は介入の因果効果ではない。

多重比較実験では、dataを見る前にfamily sizeを100、うちsignalを先頭10個、significance levelを0.05と固定する。primary familyへ含める仮説を結果確認後に変えない。

| Quantity | 答える問い | 単位 |
|---|---|---|
| effect size | 差はどれくらい大きいか | outcome unitまたは標準化単位 |
| confidence interval | estimatorの不確実性と整合する範囲は何か | effectと同じ単位 |
| p-value | 指定したnull model下で同等以上に極端な統計量はどれほどか | probability scale |
| power | 指定したalternativeで事前のtestがrejectする確率はどれほどか | probability scale |

p-valueはeffect sizeでも、nullが真である確率でも、結果の再現確率でもない。
"""),
    md(r"""
## 2. effect size、interval、p-valueを併記する

合成データで群1と群0の平均差を推定する。95% Welch intervalは

$$
\hat\Delta\pm t_{1-\alpha/2,\nu}
\sqrt{\frac{s_1^2}{n_1}+\frac{s_0^2}{n_0}}
$$

で作る。標準化effectも補助的に示すが、経済的な解釈には元のoutcome単位の差を残す。
"""),
    code("""
effect_rng = task_rng("effect_example")
group_size = 60
true_effect = 0.35
control_sample = effect_rng.normal(loc=0.0, scale=1.0, size=group_size)
treated_sample = effect_rng.normal(loc=true_effect, scale=1.0, size=group_size)

effect_estimate = treated_sample.mean() - control_sample.mean()
effect_standard_error = np.sqrt(
    treated_sample.var(ddof=1) / group_size
    + control_sample.var(ddof=1) / group_size
)
welch_result = stats.ttest_ind(treated_sample, control_sample, equal_var=False)
welch_df = float(welch_result.df)
critical_value = stats.t.ppf(0.975, welch_df)
effect_interval = (
    effect_estimate - critical_value * effect_standard_error,
    effect_estimate + critical_value * effect_standard_error,
)
pooled_standard_deviation = np.sqrt(
    (
        (group_size - 1) * treated_sample.var(ddof=1)
        + (group_size - 1) * control_sample.var(ddof=1)
    )
    / (2 * group_size - 2)
)
standardized_effect = effect_estimate / pooled_standard_deviation

effect_table = pd.DataFrame(
    [
        {
            "estimand": "treated minus control mean",
            "estimate": effect_estimate,
            "ci_lower": effect_interval[0],
            "ci_upper": effect_interval[1],
            "standardized_effect": standardized_effect,
            "p_value": welch_result.pvalue,
            "sample_size_per_group": group_size,
        }
    ]
)
display(effect_table.round(4))
"""),
    md(r"""
同じeffectでも標本数が増えるとp-valueは小さくなりやすい。したがって、実質的重要性の閾値をp-valueから逆算しない。outcome単位のeffect、interval、事前に意味を定めたminimum relevant effectを比較する。
"""),
    md(r"""
## 3. powerはalternativeとsample sizeの関数である

既知のpopulation SDを1とする二群z-testで、真のmean differenceを0.35に固定する。各sample sizeを4,000回独立に生成し、empirical powerとそのMonte Carlo SEを計算する。

$$
\widehat{\operatorname{MCSE}}(\widehat{\operatorname{Power}})
=\sqrt{\frac{\hat\pi(1-\hat\pi)}{R}}.
$$

analytic powerはnormal referenceによる独立した照合に使う。
"""),
    code("""
power_sample_sizes = np.array([25, 50, 100, 200, 400])
power_replications = 4_000
power_effect = 0.35
power_rows = []
z_critical = stats.norm.ppf(0.975)

for sample_size in power_sample_sizes:
    rng = task_rng("power", int(sample_size))
    control_means = rng.normal(
        loc=0.0,
        scale=1.0 / np.sqrt(sample_size),
        size=power_replications,
    )
    treated_means = rng.normal(
        loc=power_effect,
        scale=1.0 / np.sqrt(sample_size),
        size=power_replications,
    )
    z_statistics = (treated_means - control_means) / np.sqrt(2.0 / sample_size)
    rejected = np.abs(z_statistics) > z_critical
    empirical_power = rejected.mean()
    noncentral_shift = power_effect * np.sqrt(sample_size / 2.0)
    analytic_power = stats.norm.cdf(-z_critical - noncentral_shift) + stats.norm.sf(
        z_critical - noncentral_shift
    )
    power_rows.append(
        {
            "sample_size_per_group": int(sample_size),
            "effect": power_effect,
            "empirical_power": empirical_power,
            "power_mc_se": np.sqrt(
                empirical_power * (1.0 - empirical_power) / power_replications
            ),
            "analytic_power": analytic_power,
        }
    )

power_table = pd.DataFrame(power_rows)
display(power_table.round(4))
"""),
    code("""
fig = go.Figure()
fig.add_scatter(
    x=power_table["sample_size_per_group"],
    y=power_table["empirical_power"],
    error_y={
        "type": "data",
        "array": 1.96 * power_table["power_mc_se"],
        "visible": True,
    },
    mode="lines+markers",
    name="Empirical power",
)
fig.add_scatter(
    x=power_table["sample_size_per_group"],
    y=power_table["analytic_power"],
    mode="lines",
    name="Normal-reference power",
    line={"dash": "dash"},
)
fig.update_layout(
    title="Power is indexed by a pre-specified effect and sample size",
    xaxis_title="Sample size per group",
    yaxis_title="Power",
    yaxis_range=[0.0, 1.0],
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
simulationとanalytic curveの差はMonte Carlo errorと数値誤差の範囲で評価する。observed effectをそのままpower calculationへ戻す「post hoc power」は、intervalより新しい情報をほとんど加えない。設計時には科学的に意味のあるalternativeを先に置く。
"""),
    md(r"""
## 4. likelihood-ratio、Wald、score test

三つのtestは同じnullを異なる位置で評価する。

| Test | 主に必要なfit | 評価する情報 |
|---|---|---|
| Likelihood-ratio | restrictedとunrestricted | 最大log-likelihoodの差 |
| Wald | unrestricted | unrestricted estimateとcovariance |
| Score | restricted | null点のscoreとinformation |

正則条件の下では漸近的に同じchi-squared referenceへ近づくが、有限標本では数値が一致する必要はない。Bernoulli probabilityについて $H_0:p=0.5$ を検査する。
"""),
    code("""
test_rng = task_rng("bernoulli_tests")
test_sample_size = 120
null_probability = 0.5
bernoulli_sample = test_rng.binomial(1, 0.62, size=test_sample_size)
successes = int(bernoulli_sample.sum())
probability_estimate = bernoulli_sample.mean()


def bernoulli_log_likelihood(probability):
    return successes * np.log(probability) + (
        test_sample_size - successes
    ) * np.log1p(-probability)


lr_result = inference.likelihood_ratio_test(
    bernoulli_log_likelihood(probability_estimate),
    bernoulli_log_likelihood(null_probability),
    degrees_of_freedom=1,
)
wald_result = inference.wald_test(
    np.array([probability_estimate]),
    np.array(
        [[probability_estimate * (1.0 - probability_estimate) / test_sample_size]]
    ),
    np.array([1.0]),
    null=null_probability,
)
restricted_score = np.array([successes - test_sample_size * null_probability])
restricted_information = np.array(
    [[test_sample_size * null_probability * (1.0 - null_probability)]]
)
score_result = inference.score_test(
    restricted_score,
    restricted_information,
)

test_table = pd.DataFrame(
    [
        {
            "method": result.method,
            "statistic": result.statistic,
            "degrees_of_freedom": result.degrees_of_freedom,
            "p_value": result.p_value,
        }
        for result in (lr_result, wald_result, score_result)
    ]
)
display(test_table.round(5))
print("sample proportion:", probability_estimate)
"""),
    md(r"""
testの選択は「最も小さいp-valueを返したもの」では決めない。null・alternative、parameter boundary、small-sample挙動、restricted fitの可用性を先に定める。Week 9のseparationのようにregularity conditionが壊れると、通常のchi-squared referenceも無条件には使えない。
"""),
    md(r"""
## 5. bootstrap — 何から再標本化するか

nonparametric bootstrapは観測sampleのempirical distributionからreplacement付きで再標本化する。parametric bootstrapはfitしたdistributionから新しいsampleを生成する。前者はi.i.d. sampling、後者はi.i.d.に加えてparametric modelを仮定する。

右に歪んだlognormal sampleのpopulation meanをestimandとし、percentile intervalを比較する。これはpercentile intervalが常に最良という主張ではなく、sampling mechanismを見える形にする最小実装である。
"""),
    code("""
bootstrap_sample_rng = task_rng("bootstrap_sample")
bootstrap_sample = bootstrap_sample_rng.lognormal(
    mean=0.15,
    sigma=0.75,
    size=80,
)
bootstrap_resamples = 3_000
sample_log_mean = np.log(bootstrap_sample).mean()
sample_log_scale = np.log(bootstrap_sample).std(ddof=0)

nonparametric_result = resampling.bootstrap_statistic(
    bootstrap_sample,
    np.mean,
    bootstrap_resamples,
    rng=task_rng("bootstrap_nonparametric"),
)
parametric_result = resampling.parametric_bootstrap_statistic(
    bootstrap_sample,
    lambda rng, size: rng.lognormal(
        mean=sample_log_mean,
        sigma=sample_log_scale,
        size=size,
    ),
    np.mean,
    bootstrap_resamples,
    rng=task_rng("bootstrap_parametric"),
)
scipy_bootstrap = stats.bootstrap(
    (bootstrap_sample,),
    np.mean,
    n_resamples=bootstrap_resamples,
    method="percentile",
    random_state=task_rng("bootstrap_scipy"),
)

bootstrap_table = pd.DataFrame(
    [
        {
            "method": "custom nonparametric percentile",
            "estimate": nonparametric_result.estimate,
            "bootstrap_se": nonparametric_result.bootstrap_standard_error,
            "ci_lower": nonparametric_result.confidence_interval[0],
            "ci_upper": nonparametric_result.confidence_interval[1],
        },
        {
            "method": "custom parametric lognormal percentile",
            "estimate": parametric_result.estimate,
            "bootstrap_se": parametric_result.bootstrap_standard_error,
            "ci_lower": parametric_result.confidence_interval[0],
            "ci_upper": parametric_result.confidence_interval[1],
        },
        {
            "method": "SciPy nonparametric percentile",
            "estimate": bootstrap_sample.mean(),
            "bootstrap_se": scipy_bootstrap.standard_error,
            "ci_lower": scipy_bootstrap.confidence_interval.low,
            "ci_upper": scipy_bootstrap.confidence_interval.high,
        },
    ]
)
display(bootstrap_table.round(4))
"""),
    md(r"""
custom nonparametricとSciPyは独立なresampling streamを使うため、intervalがbyte単位で一致する必要はない。この単一runは実装と大きさの照合であり、resampling Monte Carlo errorを完全に定量化していない。細かい差を比較するときは、複数の独立streamとresample数への感度を追加する。parametric resultとの差は、lognormal modelを追加した影響も含む。

**Advanced:** maximum、boundary parameter、非滑らかなstatisticでは通常bootstrapがconsistentでない場合がある。method名だけで妥当性を判断せず、statisticとsampling lawの条件を確認する。
"""),
    md(r"""
## 6. permutation test — exchangeabilityをnullとして実装する

独立二群で「null下ではlabelを入れ替えられる」と仮定し、mean differenceのrandomization distributionを作る。randomized p-valueにはplus-one correctionを使い、有限回のpermutationで0を返さない。
"""),
    code("""
permutation_sample_rng = task_rng("permutation_sample")
permutation_first = permutation_sample_rng.normal(loc=0.0, size=45)
permutation_second = permutation_sample_rng.normal(loc=0.45, size=50)


def mean_difference(first, second):
    return second.mean() - first.mean()


permutation_resamples = 3_999
custom_permutation = resampling.permutation_test_two_sample(
    permutation_first,
    permutation_second,
    mean_difference,
    permutation_resamples,
    rng=task_rng("permutation_custom"),
)
scipy_permutation = stats.permutation_test(
    (permutation_first, permutation_second),
    mean_difference,
    permutation_type="independent",
    vectorized=False,
    n_resamples=permutation_resamples,
    alternative="two-sided",
    random_state=task_rng("permutation_scipy"),
)
permutation_tolerance = 100.0 * np.finfo(float).eps * max(
    1.0,
    abs(custom_permutation.observed_statistic),
)
greater_tail_probability = (
    np.count_nonzero(
        custom_permutation.null_distribution
        >= custom_permutation.observed_statistic - permutation_tolerance
    )
    + 1.0
) / (permutation_resamples + 1.0)
less_tail_probability = (
    np.count_nonzero(
        custom_permutation.null_distribution
        <= custom_permutation.observed_statistic + permutation_tolerance
    )
    + 1.0
) / (permutation_resamples + 1.0)
smaller_tail_probability = min(
    greater_tail_probability,
    less_tail_probability,
)
permutation_mc_se = 2.0 * np.sqrt(
    smaller_tail_probability
    * (1.0 - smaller_tail_probability)
    / (permutation_resamples + 1.0)
)

permutation_table = pd.DataFrame(
    [
        {
            "implementation": "custom plus-one",
            "effect": custom_permutation.observed_statistic,
            "p_value": custom_permutation.p_value,
            "randomization_mc_se": permutation_mc_se,
        },
        {
            "implementation": "SciPy",
            "effect": scipy_permutation.statistic,
            "p_value": scipy_permutation.pvalue,
            "randomization_mc_se": np.nan,
        },
    ]
)
display(permutation_table.round(5))
"""),
    md(r"""
異なるrandom permutationを使う二実装のp-valueは完全には一致しない。表のMonte Carlo SEは、小さい片側tailが固定される近似の下で、そのplus-one比率のSEを2倍している。tailが切り替わる場合やtiesが多い場合は、独立なrandomization runで安定性を検査する。さらにtwo-sided p-valueの定義には規約差があるため、statistic、alternative、permutation type、plus-one ruleを記録する。

観測がpairedならpairを保つ交換、時系列なら一般に個別時点の自由な交換は許されない。exchangeabilityは「distribution-freeだから仮定がない」という意味ではない。
"""),
    md(r"""
## 7. multiple comparisons — FWERとFDRは異なるestimand

$m$ 個の仮説でfalse rejection数を $V$、全rejection数を $R$ とする。

$$
\operatorname{FWER}=\mathbb{P}(V\ge1),
\qquad
\operatorname{FDR}=\mathbb{E}\left[\frac{V}{\max(R,1)}\right].
$$

Bonferroniは各raw p-valueを $m$ 倍し、任意の依存下でFWERを制御する保守的なbaselineである。Benjamini–Hochbergはordered p-valueへstep-up ruleを適用し、独立または所定のpositive dependence条件でFDRを制御する。

次のresearch factoryでは100仮説中10個に標準化effect 0.55を置く。unadjusted、Bonferroni、BHを800回比較する。marginal type-I error、FWER、FDR、powerはreplicationごとのmetricを平均し、その標準誤差をMonte Carlo SEとして報告する。
"""),
    code("""
multiple_testing_rng = task_rng("multiple_testing")
family_size = 100
signal_count = 10
multiple_testing_sample_size = 40
multiple_testing_replications = 800
alpha = 0.05
true_effects = np.zeros(family_size)
true_effects[:signal_count] = 0.55
null_mask = true_effects == 0.0
signal_mask = ~null_mask
method_metrics = {
    "unadjusted": [],
    "bonferroni": [],
    "benjamini-hochberg": [],
}

for _ in range(multiple_testing_replications):
    estimates = true_effects + multiple_testing_rng.normal(
        scale=1.0 / np.sqrt(multiple_testing_sample_size),
        size=family_size,
    )
    z_statistics = estimates * np.sqrt(multiple_testing_sample_size)
    p_values = 2.0 * stats.norm.sf(np.abs(z_statistics))
    decisions = {
        "unadjusted": p_values <= alpha,
        "bonferroni": resampling.bonferroni_adjust(
            p_values,
            alpha=alpha,
        ).rejected,
        "benjamini-hochberg": resampling.benjamini_hochberg(
            p_values,
            alpha=alpha,
        ).rejected,
    }
    for method, rejected in decisions.items():
        false_positives = np.count_nonzero(rejected & null_mask)
        true_positives = np.count_nonzero(rejected & signal_mask)
        total_rejections = np.count_nonzero(rejected)
        method_metrics[method].append(
            [
                false_positives / np.count_nonzero(null_mask),
                float(false_positives > 0),
                false_positives / max(total_rejections, 1),
                true_positives / signal_count,
            ]
        )

multiple_testing_rows = []
metric_names = ("type_i_error", "fwer", "fdr", "power")
for method, values in method_metrics.items():
    metric_array = np.asarray(values)
    row = {"method": method}
    for column, metric_name in enumerate(metric_names):
        row[metric_name] = metric_array[:, column].mean()
        row[f"{metric_name}_mc_se"] = metric_array[:, column].std(
            ddof=1
        ) / np.sqrt(multiple_testing_replications)
    multiple_testing_rows.append(row)

multiple_testing_table = pd.DataFrame(multiple_testing_rows)
display(multiple_testing_table.round(4))
"""),
    code("""
fig = go.Figure()
for metric_name in ("fwer", "fdr", "power"):
    fig.add_bar(
        x=multiple_testing_table["method"],
        y=multiple_testing_table[metric_name],
        error_y={
            "type": "data",
            "array": 1.96 * multiple_testing_table[f"{metric_name}_mc_se"],
            "visible": True,
        },
        name=metric_name.upper(),
    )
fig.update_layout(
    title="Error control and power answer different operating questions",
    xaxis_title="Reporting rule",
    yaxis_title="Empirical rate",
    barmode="group",
    template="plotly_white",
)
fig.show()
"""),
    code("""
fdr_audit_rng = task_rng("fdr_audit")
audit_z_statistics = fdr_audit_rng.normal(size=family_size)
audit_p_values = 2.0 * stats.norm.sf(np.abs(audit_z_statistics))
custom_bh = resampling.benjamini_hochberg(audit_p_values, alpha=alpha)
scipy_bh_adjusted = stats.false_discovery_control(audit_p_values, method="bh")
bh_maximum_difference = np.max(
    np.abs(custom_bh.adjusted_p_values - scipy_bh_adjusted)
)

print("family size:", custom_bh.family_size)
print("maximum adjusted-p difference vs SciPy:", bh_maximum_difference)
assert bh_maximum_difference < 1e-12
"""),
    md(r"""
このsimulationでBHがBonferroniより高いpowerを持つのは、制御対象がFWERではなくFDRだからである。どちらが常に優れるのではない。false positiveが1件でも重大ならFWER、発見集合の誤り割合を管理したい探索familyならFDRというように、decision costから選ぶ。

empirical FDRが0.05を少し上下しても、まずFDR MCSEを見る。このcaseでは独立なtestを生成している。実際のwindowやmaturityを並べた金融仮説は強く依存し得るため、BHの条件を無条件に仮定しない。
"""),
    md(r"""
## 8. selection-induced bias — winnerだけを報告する

すべてnullのfamilyから絶対値最大のestimateを選ぶと、選択されたestimateの絶対値は事前指定した1個より系統的に大きい。これはestimatorのsampling distributionをselection ruleが変えた結果である。
"""),
    code("""
selection_rng = task_rng("selection_bias")
selection_replications = 2_000
selection_family_size = 100
selection_sample_size = 50
null_estimates = selection_rng.normal(
    scale=1.0 / np.sqrt(selection_sample_size),
    size=(selection_replications, selection_family_size),
)
pre_specified_absolute = np.abs(null_estimates[:, 0])
selected_absolute = np.max(np.abs(null_estimates), axis=1)
naive_half_width = 1.96 / np.sqrt(selection_sample_size)

selection_table = pd.DataFrame(
    [
        {
            "rule": "pre-specified first",
            "mean_absolute_estimate": pre_specified_absolute.mean(),
            "naive_interval_coverage": np.mean(
                pre_specified_absolute <= naive_half_width
            ),
        },
        {
            "rule": "largest absolute after looking",
            "mean_absolute_estimate": selected_absolute.mean(),
            "naive_interval_coverage": np.mean(selected_absolute <= naive_half_width),
        },
    ]
)
display(selection_table.round(4))
"""),
    code("""
selection_edges = np.linspace(0.0, selected_absolute.max(), 34)
pre_counts, _ = np.histogram(pre_specified_absolute, bins=selection_edges)
selected_counts, _ = np.histogram(selected_absolute, bins=selection_edges)
selection_centers = 0.5 * (selection_edges[:-1] + selection_edges[1:])

fig = go.Figure()
fig.add_bar(
    x=selection_centers,
    y=pre_counts / selection_replications,
    name="Pre-specified",
    opacity=0.65,
)
fig.add_bar(
    x=selection_centers,
    y=selected_counts / selection_replications,
    name="Selected maximum",
    opacity=0.65,
)
fig.add_vline(x=naive_half_width, line_dash="dash")
fig.update_layout(
    title="Selection changes the target distribution before any p-value adjustment",
    xaxis_title="Absolute estimate",
    yaxis_title="Fraction of research runs",
    barmode="overlay",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
multiple-testing adjustmentはdecision errorを制御するが、選択されたeffect estimateのwinner's curseを自動的に除かない。primary hypothesisをpre-specifyし、探索で選んだsignalは独立sampleでvalidationする。
"""),
    md(r"""
## 9. 失敗モード — iid bootstrapを時系列へ使う

iid bootstrapは観測時点を個別に再標本化し、serial dependenceを壊す。stationary AR(1)

$$
X_t=\rho X_{t-1}+\varepsilon_t,
\qquad
\operatorname{Var}(X_t)=1
$$

のsample meanでは、正のautocorrelationがlong-run varianceを増やす。有限標本で

$$
\operatorname{Var}(\bar X)
=\frac{1}{n}\left[
1+2\sum_{k=1}^{n-1}\left(1-\frac{k}{n}\right)\rho^k
\right]
$$

である。以下ではpackageのiid bootstrapを意図的に誤適用し、独立pathから測ったempirical sampling SDと比較する。
"""),
    code("""
def simulate_stationary_ar1(rng, n_paths, n_times, autoregressive_coefficient):
    paths = np.empty((n_paths, n_times), dtype=float)
    paths[:, 0] = rng.normal(size=n_paths)
    innovation_scale = np.sqrt(1.0 - autoregressive_coefficient**2)
    innovations = rng.normal(
        scale=innovation_scale,
        size=(n_paths, n_times - 1),
    )
    for time_index in range(1, n_times):
        paths[:, time_index] = (
            autoregressive_coefficient * paths[:, time_index - 1]
            + innovations[:, time_index - 1]
        )
    return paths


ar_coefficient = 0.8
ar_sample_size = 240
observed_ar_series = simulate_stationary_ar1(
    task_rng("ar_observed"),
    1,
    ar_sample_size,
    ar_coefficient,
)[0]
iid_bootstrap_for_ar = resampling.bootstrap_statistic(
    observed_ar_series,
    np.mean,
    4_000,
    rng=task_rng("ar_iid_bootstrap"),
)

sampling_replications = 5_000
ar_sampling_paths = simulate_stationary_ar1(
    task_rng("ar_sampling"),
    sampling_replications,
    ar_sample_size,
    ar_coefficient,
)
ar_mean_sampling_sd = ar_sampling_paths.mean(axis=1).std(ddof=1)
lags = np.arange(1, ar_sample_size)
ar_mean_theoretical_variance = (
    1.0
    + 2.0
    * np.sum((1.0 - lags / ar_sample_size) * ar_coefficient**lags)
) / ar_sample_size
ar_mean_theoretical_se = np.sqrt(ar_mean_theoretical_variance)
sampling_sd_mc_se = ar_mean_sampling_sd / np.sqrt(
    2.0 * (sampling_replications - 1)
)

ar_bootstrap_table = pd.DataFrame(
    [
        {
            "uncertainty_estimator": "iid bootstrap applied to one AR series",
            "standard_error": iid_bootstrap_for_ar.bootstrap_standard_error,
            "monte_carlo_se": np.nan,
        },
        {
            "uncertainty_estimator": "empirical SD across independent AR paths",
            "standard_error": ar_mean_sampling_sd,
            "monte_carlo_se": sampling_sd_mc_se,
        },
        {
            "uncertainty_estimator": "finite-sample AR(1) formula",
            "standard_error": ar_mean_theoretical_se,
            "monte_carlo_se": np.nan,
        },
    ]
)
display(ar_bootstrap_table.round(5))
"""),
    code("""
fig = go.Figure(
    go.Bar(
        x=ar_bootstrap_table["uncertainty_estimator"],
        y=ar_bootstrap_table["standard_error"],
    )
)
fig.update_layout(
    title="I.i.d. resampling destroys positive serial dependence",
    xaxis_title="Uncertainty estimator",
    yaxis_title="Standard error of the sample mean",
    template="plotly_white",
)
fig.show()

print(
    "iid bootstrap to empirical SD ratio:",
    iid_bootstrap_for_ar.bootstrap_standard_error / ar_mean_sampling_sd,
)
"""),
    md(r"""
iid bootstrap SEがempirical sampling SDとAR(1)公式より小さいのは、resample内のlag correlationを0へ壊したためである。bootstrap codeは正常に実行されているが、近似したsampling mechanismが問いと一致しない。

**Advanced:** stationary dependenceに対するblock bootstrapは連続blockを再標本化する。block lengthも新しいtuning parameterであり、1にすればiid bootstrapへ戻り、長すぎれば有効なresample数が減る。dependent wild bootstrapも含め、適用前にstationarity、dependence range、sampling unitを定義する。
"""),
    md(r"""
## 10. 段階別演習

### 基礎

1. effect size、CI、p-value、powerをそれぞれ1文で定義せよ。
2. Bernoulli exampleのLR、Wald、score statisticを手計算で導出せよ。
3. bootstrapとpermutationが再標本化する対象を対照表にせよ。

### 標準

4. power effectを0.1、0.35、0.8へ変え、MCSE付きのcurveを作れ。
5. family sizeを20、100、500へ変え、unadjusted FWERを比較せよ。
6. signal countとeffectを変え、BonferroniとBHのFDR・power trade-offを測れ。
7. AR coefficientを0、0.4、0.8へ変え、iid bootstrap SEの比を描け。

### 研究

8. **Advanced:** circular block bootstrapを実装し、block lengthごとのbiasとcoverageを測れ。
9. **Advanced:** maximum statisticのordinary bootstrapが失敗するcaseを調べ、subsamplingと比較せよ。
10. exploratory familyで選んだsignalを独立holdoutで再推定し、winner's curseを測れ。
"""),
    md(r"""
## 11. Exit Criteria

- [ ] effect size、CI、p-value、powerを同じ表で別columnとして報告できる
- [ ] LR、Wald、score testが評価するfit位置を説明できる
- [ ] resamplingのexchangeability・independence・parametric modelを明記できる
- [ ] hypothesis familyとselection ruleをdataより先に固定できる
- [ ] BonferroniのFWERとBHのFDRを区別して選べる
- [ ] type-I error、FWER、FDR、powerをMonte Carlo SE付きで報告できる
- [ ] iid bootstrapをdependent seriesへ適用した過小SEを診断できる
"""),
    md(r"""
## 12. 出典

- [MIT OpenCourseWare 18.650: Parametric Hypothesis Testing](https://ocw.mit.edu/courses/18-650-statistics-for-applications-fall-2016/11b4116aa55b4e0288141bd40a39104f_MIT18_650F16_Parametric_HT.pdf) — type-I error、power、Wald、likelihood-ratio test
- [SciPy `stats.bootstrap`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html) — bootstrap interval、paired option、明示的RNGの公式API
- [SciPy `stats.permutation_test`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html) — permutation type、plus-one規約、randomized null distribution
- [SciPy `stats.false_discovery_control`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.false_discovery_control.html) — BH/BY adjusted p-valueの公式参照実装
- [Efron, *Bootstrap Methods: Another Look at the Jackknife*](https://doi.org/10.1214/aos/1176344552) — nonparametric bootstrapの原論文
- [Benjamini and Hochberg, *Controlling the False Discovery Rate*](https://www.math.tau.ac.il/~ybenja/MyPapers/benjamini_hochberg1995.pdf) — FDRとstep-up procedureの原論文
- [Künsch, *The Jackknife and the Bootstrap for General Stationary Observations*](https://doi.org/10.1214/aos/1176347265) — dependent stationary seriesに対するblock resamplingの原論文

次章では、同じcoefficient estimateへHC、HAC、cluster covarianceを適用し、依存構造とcoverageから選択する。
"""),
]
