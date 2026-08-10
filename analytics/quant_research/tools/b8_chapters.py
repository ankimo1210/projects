"""Deterministic cell definitions for the six B8 notebook builders."""

from __future__ import annotations

from nbkit import code, md
from stage2_nb import setup_cell, treasury_curve_cell

BAYES_SOURCES = """
- [Gelman et al., Bayesian Data Analysis, 3rd ed.](https://sites.stat.columbia.edu/gelman/book/)
- [Gelman et al., Bayesian Workflow](https://arxiv.org/abs/2011.01808)
- [Vehtari, Gelman, and Gabry, Practical Bayesian model evaluation](https://doi.org/10.1007/s11222-016-9696-4)
"""

LATENT_SOURCES = """
- [Rabiner (1989), A Tutorial on Hidden Markov Models](https://www.cs.cmu.edu/~durand/03-711/Readings/Rabiner89.pdf)
- [Vehtari et al., Rank-normalization, folding, and localization](https://arxiv.org/abs/1903.08008)
- [Stan Reference Manual — MCMC Sampling](https://mc-stan.org/docs/reference-manual/mcmc.html)
"""


def overview_cells():
    return [
        md(r"""
# 42. B8 — Bayesian inference and latent-state uncertainty

> B8はB7とは別のmarket storyを作らない。同じTreasury curve、同じ5公表日先target、同じouter testで、parameter・predictive・state uncertaintyを追加する。

## 学習目標

- prior、likelihood、posterior、posterior predictiveを分けられる
- partial poolingとno/complete poolingを比較できる
- DAG、mixture、HMMのconditional independenceを読める
- MCMCをacceptanceだけでなくESSとmulti-chain diagnosticで監査できる
- latent stateを観測された「真のregime」と呼ばず予測分布として評価できる

## 前提知識

- B2の条件付き確率とMarkov chain
- B3のlikelihoodとfinite-sample uncertainty
- B7のfactor dynamics、filtered/smoothed distinction
"""),
        setup_cell(42),
        treasury_curve_cell(),
        md(r"""
## 1. B8 evidence chain

| Week | Core | Treasury lab | 主な反証 |
|---|---|---|---|
| 29 | conjugacy、prior/posterior predictive | 5日先10年変化 | prior sensitivity |
| 30 | hierarchical shrinkage、WAIC boundary | tenor別5日変化 | exchangeability failure |
| 31 | DAG、mixture、HMM、EM | NS factor-change states | label/state truth claim |
| 32 | MH、ESS、split-(\hat R)、approximation boundary | predictive uncertainty | trace-only diagnosis |

CoreはNumPy/SciPyによる透明な共役計算、random-walk MH、Gaussian HMM。HMC/NUTS/VI/SMCは理論・診断のAdvanced範囲で、finite differenceをautomatic differentiationと呼ばない。
"""),
        code("""
horizon = 5
origins = np.arange(curve_yields.shape[0] - horizon)
target_changes_bp = (curve_yields[origins + horizon] - curve_yields[origins]) * 100.0
target_dates = curve_dates[origins + horizon]
training_targets = target_changes_bp[target_dates <= train_end_date]

prior_rng = task_rng(1)
prior_mean_draws = prior_rng.normal(loc=0.0, scale=5.0, size=4000)
prior_predictive = prior_mean_draws + prior_rng.normal(
    scale=training_targets[:, 3].std(ddof=1), size=4000
)
fig = go.Figure()
fig.add_histogram(x=training_targets[:, 3], name="observed training targets", histnorm="probability density", opacity=0.6)
fig.add_histogram(x=prior_predictive, name="prior predictive", histnorm="probability density", opacity=0.6)
fig.update_layout(
    title="Prior predictive scale check for five-publication 10y changes",
    xaxis_title="Change (bp)",
    barmode="overlay",
    template="plotly_white",
)
fig.show()
"""),
        md(
            r"""
## 2. Uncertainty contract

- Bayesian linear modelはparameter uncertaintyとobservation noiseを積分したposterior predictiveを返す。
- HMM EMはpoint-estimated parameterの下のpredictive distributionで、full Bayesian posterior predictiveではない。
- coverage、interval width、log predictive density、point RMSEを別々に報告する。
- HMM state probabilityはmodel内の条件付き確率で、外部の観測済みmarket regime labelではない。

## 3. 失敗モード

- priorを隠して「dataだけ」の結論と呼ぶ
- posterior intervalとfrequentist repeated-sampling CIを同義にする
- testを見てstate数やprior scaleを選ぶ
- EMのstate確率をparameter posterior uncertaintyと呼ぶ
- trace plotだけでMCMC convergenceを宣言する

## 4. 段階別演習

### 基礎

1. prior predictiveとposterior predictiveの条件付け集合を書け。
2. 5日先targetのtraining/validation/test件数を数えよ。

### 標準

3. prior standard deviation 1/5/20 bpの感応度を比較せよ。
4. coverageとwidthを同時に採用するgateを書け。

### 研究

5. full Bayesian switching state-space modelへ進む前のsimulation-based calibration計画を書け。

## 5. Exit Criteria

- [ ] B7と同じdata・target・outer testを使う
- [ ] posterior predictiveとHMM conditional predictiveを区別した
- [ ] point errorとcoverage/log scoreを分離した
- [ ] state labelを観測真値と呼ばない
- [ ] prior sensitivityとMCMC diagnosticsを必須にした

## 6. 出典

"""
            + BAYES_SOURCES
            + LATENT_SOURCES
        ),
    ]


def week29_cells():
    return [
        md(r"""
# 43. Week 29 — Conjugacy, prior predictive checks, and Bayesian regression

## 学習目標

- normal-normal conjugacyをprecisionで導出できる
- prior predictiveでscale mismatchを発見できる
- Normal–Inverse-Gamma regressionのposterior predictiveを作れる
- validation coverageとwidthをpoint errorから分けられる

## 前提知識

- Gaussian likelihood、linear regression
- B7の5公表日先target
"""),
        setup_cell(43),
        treasury_curve_cell(),
        md(r"""
## 1. Conjugate normal mean

既知観測分散 (sigma^2)、prior (mu\sim N(m_0,s_0^2)) なら

$$
s_n^{-2}=s_0^{-2}+n\sigma^{-2},\qquad
m_n=s_n^2\left(s_0^{-2}m_0+\sigma^{-2}\sum_i y_i\right).
$$
"""),
        code("""
horizon = 5
origins = np.arange(curve_yields.shape[0] - horizon)
targets = (curve_yields[origins + horizon] - curve_yields[origins]) * 100.0
target_dates = curve_dates[origins + horizon]
training_rows = target_dates <= train_end_date
validation_rows = (target_dates > train_end_date) & (target_dates <= validation_end_date)

ten_year_training = targets[training_rows, 3]
observation_variance = float(np.var(ten_year_training, ddof=1))
posterior_rows = []
for prior_sd in [1.0, 5.0, 20.0]:
    posterior = qt.normal_mean_posterior(
        ten_year_training,
        observation_variance=observation_variance,
        prior_mean=0.0,
        prior_variance=prior_sd**2,
    )
    lower, upper = posterior.predictive_interval(0.9)
    posterior_rows.append(
        {"prior_sd_bp": prior_sd, "posterior_mean_bp": posterior.mean, "posterior_sd_bp": np.sqrt(posterior.variance), "predictive_lower_bp": lower, "predictive_upper_bp": upper}
    )
display(pd.DataFrame(posterior_rows))
"""),
        md(r"""
## 2. Bayesian linear regression

$$
y\mid\beta,\sigma^2\sim N(X\beta,\sigma^2I),\quad
\beta\mid\sigma^2\sim N(0,\sigma^2\Lambda_0^{-1}),\quad
\sigma^2\sim \operatorname{InvGamma}(a_0,b_0).
$$

featuresはforecast originのcurve levelと直近1公表日のcurve change。標準化parameterはtrainingだけで固定する。
"""),
        code("""
raw_features = np.column_stack(
    [curve_yields[origins], np.vstack([np.zeros(5), np.diff(curve_yields, axis=0)])[origins] * 100.0]
)
feature_mean = raw_features[training_rows].mean(axis=0)
feature_scale = raw_features[training_rows].std(axis=0, ddof=1)
standardized = (raw_features - feature_mean) / feature_scale
design = np.column_stack([np.ones(standardized.shape[0]), standardized])

regression = qt.fit_bayesian_linear_regression(
    design[training_rows], targets[training_rows, 3], prior_precision=1.0, prior_shape=2.0, prior_scale=25.0
)
validation_predictive = qt.bayesian_linear_predictive(regression, design[validation_rows])
lower, upper = validation_predictive.interval(0.9)
actual = targets[validation_rows, 3]
coverage = np.mean((actual >= lower) & (actual <= upper))
display(
    pd.DataFrame(
        [
            {
                "validation_rmse_bp": np.sqrt(np.mean((actual - validation_predictive.mean) ** 2)),
                "validation_coverage_90": coverage,
                "mean_interval_width_bp": np.mean(upper - lower),
                "random_walk_rmse_bp": np.sqrt(np.mean(actual**2)),
            }
        ]
    )
)

fig = go.Figure()
validation_dates = target_dates[validation_rows]
fig.add_scatter(x=validation_dates, y=actual, name="actual", mode="lines")
fig.add_scatter(x=validation_dates, y=validation_predictive.mean, name="posterior predictive mean", mode="lines")
fig.add_scatter(x=validation_dates, y=upper, name="90% upper", mode="lines", line={"width": 0})
fig.add_scatter(x=validation_dates, y=lower, name="90% interval", mode="lines", fill="tonexty", line={"width": 0})
fig.update_layout(title="Validation posterior predictive: five-publication 10y change", yaxis_title="Change (bp)", template="plotly_white")
fig.show()
"""),
        md(
            r"""
## 3. 失敗モード

- prior predictiveを観測dataでfitしてからpriorと呼ぶ
- training外でfeature standardizationをfitする
- posterior meanのRMSEだけでBayesian modelを評価する
- nominal 90%だけを見て幅を隠す
- Gaussian predictive tailを保証されたtail riskと呼ぶ

## 4. 段階別演習

### 基礎

1. precision-weighted posterior meanを再計算せよ。
2. prior scaleごとのposterior sensitivityを説明せよ。

### 標準

3. tenorごとにBayesian regressionをfitしcoverageを比較せよ。
4. validationをmethodology break前後に分けよ。

### 研究

5. Student-t likelihoodへ拡張した場合のrobustness/estimand contractを書け。

## 5. Exit Criteria

- [ ] prior、likelihood、posterior、predictiveを分けた
- [ ] prior predictiveのscaleを実データ単位で監査した
- [ ] standardizationをtrainingに限定した
- [ ] validation RMSE、coverage、widthを報告した
- [ ] Gaussian tail assumptionを明記した

## 6. 出典

"""
            + BAYES_SOURCES
        ),
    ]


def week30_cells():
    return [
        md(r"""
# 44. Week 30 — Hierarchical shrinkage and model-evaluation boundaries

## 学習目標

- no pooling、complete pooling、partial poolingを比較できる
- sampling standard errorに応じたshrinkageを説明できる
- tenor exchangeabilityの仮定を監査できる
- WAICのpointwise-i.i.d.近似を時系列へ無批判に適用しない

## 前提知識

- Week 29のconjugacyとposterior predictive
- B3のestimandとdependence-aware inference
"""),
        setup_cell(44),
        treasury_curve_cell(),
        md(r"""
## 1. Normal-normal partial pooling

$$
\hat\theta_j\mid\theta_j\sim N(\theta_j,s_j^2),\qquad
\theta_j\mid\mu,\tau^2\sim N(\mu,\tau^2).
$$

posterior meanは (w_j\hat\theta_j+(1-w_j)\mu)、(w_j=\tau^2/(\tau^2+s_j^2))。本章は (mu,\tau) をpredeclared sensitivity parameterとして固定し、empirical Bayes推定と取り違えない。
"""),
        code("""
horizon = 5
origins = np.arange(curve_yields.shape[0] - horizon)
targets = (curve_yields[origins + horizon] - curve_yields[origins]) * 100.0
target_dates = curve_dates[origins + horizon]
training_rows = target_dates <= train_end_date
training_targets = targets[training_rows]
raw_means = training_targets.mean(axis=0)
standard_errors = training_targets.std(axis=0, ddof=1) / np.sqrt(training_targets.shape[0])
pooled = qt.hierarchical_normal_posterior(
    raw_means,
    standard_errors,
    population_mean=0.0,
    population_standard_deviation=1.0,
)
pooling_table = pd.DataFrame(
    {
        "tenor": qt.DEFAULT_TENORS,
        "no_pooling_mean_bp": raw_means,
        "standard_error_bp": standard_errors,
        "partial_pooling_mean_bp": pooled.means,
        "shrinkage_weight": pooled.shrinkage_weights,
        "complete_pooling_mean_bp": np.average(raw_means, weights=1.0 / standard_errors**2),
    }
)
display(pooling_table)

fig = go.Figure()
fig.add_scatter(x=pooling_table["tenor"], y=pooling_table["no_pooling_mean_bp"], name="no pooling", mode="markers")
fig.add_scatter(x=pooling_table["tenor"], y=pooling_table["partial_pooling_mean_bp"], name="partial pooling", mode="markers")
fig.update_layout(title="Five-publication mean changes before and after partial pooling", yaxis_title="Mean change (bp)", template="plotly_white")
fig.show()
"""),
        md(r"""
## 2. Tenor-specific predictive coverage
"""),
        code("""
raw_features = np.column_stack(
    [curve_yields[origins], np.vstack([np.zeros(5), np.diff(curve_yields, axis=0)])[origins] * 100.0]
)
feature_mean = raw_features[training_rows].mean(axis=0)
feature_scale = raw_features[training_rows].std(axis=0, ddof=1)
design = np.column_stack([np.ones(raw_features.shape[0]), (raw_features - feature_mean) / feature_scale])
validation_rows = (target_dates > train_end_date) & (target_dates <= validation_end_date)
predictive_rows = []
models = []
for tenor_index, tenor in enumerate(qt.DEFAULT_TENORS):
    model = qt.fit_bayesian_linear_regression(
        design[training_rows], targets[training_rows, tenor_index], prior_precision=1.0, prior_shape=2.0, prior_scale=25.0
    )
    models.append(model)
    predictive = qt.bayesian_linear_predictive(model, design[validation_rows])
    lower, upper = predictive.interval(0.9)
    actual = targets[validation_rows, tenor_index]
    predictive_rows.append(
        {
            "tenor": tenor,
            "rmse_bp": np.sqrt(np.mean((actual - predictive.mean) ** 2)),
            "coverage_90": np.mean((actual >= lower) & (actual <= upper)),
            "mean_width_bp": np.mean(upper - lower),
        }
    )
display(pd.DataFrame(predictive_rows))
"""),
        md(r"""
## 3. WAIC diagnostic and dependence boundary

WAICはdraw-by-observation log likelihoodから

$$
\operatorname{WAIC}=-2\left(\sum_i\log E_s[p(y_i\mid\theta_s)]-\sum_i\operatorname{Var}_s[\log p(y_i\mid\theta_s)]\right)
$$

を計算する。ただしoverlapping 5公表日targetは独立でないため、naive pointwise WAICを最終model selectorにしない。
"""),
        code("""
waic_rng = task_rng(2)
model = models[3]
precision_inverse = np.linalg.solve(model.precision, np.eye(model.precision.shape[0]))
draw_count = 500
sigma_squared = model.scale / waic_rng.gamma(model.shape, 1.0, size=draw_count)
beta_draws = np.vstack(
    [waic_rng.multivariate_normal(model.mean, sigma_squared[index] * precision_inverse) for index in range(draw_count)]
)
audit_design = design[training_rows][-400:]
audit_target = targets[training_rows, 3][-400:]
log_likelihood_draws = np.empty((draw_count, audit_target.size))
for draw in range(draw_count):
    residual = audit_target - audit_design @ beta_draws[draw]
    log_likelihood_draws[draw] = -0.5 * (
        np.log(2.0 * np.pi * sigma_squared[draw]) + residual**2 / sigma_squared[draw]
    )
waic_value, effective_parameters = qt.waic(log_likelihood_draws)
print("naive pointwise WAIC diagnostic:", waic_value)
print("effective parameter diagnostic:", effective_parameters)
print("used for time-series model selection:", False)
"""),
        md(
            r"""
## 4. 失敗モード

- tenorがexchangeableかを確認せずpoolingする
- (mu,	au) をdataから選んでfixed priorと呼ぶ
- shrinkageをbias-freeと表現する
- overlapping targetsへnaive i.i.d. WAICをmodel selectorとして使う
- interval widthを隠してcoverageだけを比較する

## 5. 段階別演習

### 基礎

1. shrinkage weightの極限 (s_j\to0,\infty) を説明せよ。
2. no/complete/partial poolingを図示せよ。

### 標準

3. (	au=0.25,1,5) bpの感応度を比較せよ。
4. tenor階層ではなくmaturity spline priorを設計せよ。

### 研究

5. leave-future-block-out predictive evaluationを設計せよ。

## 6. Exit Criteria

- [ ] three pooling regimesを区別した
- [ ] hyperparameterの固定/推定を明記した
- [ ] tenor exchangeabilityを仮定として書いた
- [ ] RMSE、coverage、widthをtenor別に報告した
- [ ] WAICのtime-series dependence boundaryを明記した

## 7. 出典

"""
            + BAYES_SOURCES
        ),
    ]


def week31_cells():
    return [
        md(r"""
# 45. Week 31 — Graphical models, mixtures, HMMs, and EM

## 学習目標

- DAGのfactorizationとd-separationを読める
- iid mixtureとHMMの依存構造を区別できる
- forward-backward、Viterbi、Baum–Welchの役割を分けられる
- label switchingとstate occupancy/durationを監査できる

## 前提知識

- B2のMarkov chain
- B7のNS factor changes
"""),
        setup_cell(45),
        treasury_curve_cell(),
        md(r"""
## 1. Conditional independence graph

HMMは

$$
p(z_{1:T},y_{1:T})=p(z_1)p(y_1\mid z_1)\prod_{t=2}^T p(z_t\mid z_{t-1})p(y_t\mid z_t)
$$

とfactorizeする。(y_t\perp y_{1:t-1}\mid z_t) はmodel仮定であり、市場の真の生成過程がそうだという観測事実ではない。iid Gaussian mixtureはtransitionを持たず、duration情報を表現しない。
"""),
        code("""
decay = 0.5
factors = qt.extract_nelson_siegel_factors(curve_yields, maturity_years, decay)
factor_changes_bp = np.diff(factors, axis=0) * 100.0
factor_change_dates = curve_dates[1:]
training_rows = factor_change_dates <= train_end_date
audit_rows = factor_change_dates <= validation_end_date

hmm = qt.fit_gaussian_hmm(factor_changes_bp[training_rows], 2)
filtered_probability = qt.hmm_filtered_probabilities(hmm, factor_changes_bp[audit_rows])
smoothed_probability = qt.hmm_smoothed_probabilities(hmm, factor_changes_bp[audit_rows])
diagnostics = qt.hmm_state_diagnostics(hmm, factor_changes_bp[training_rows])
display(
    pd.DataFrame(
        {
            "state": np.arange(2),
            "level_change_mean_bp": hmm.means[:, 0],
            "slope_change_mean_bp": hmm.means[:, 1],
            "curvature_change_mean_bp": hmm.means[:, 2],
            "occupancy": diagnostics.occupancy,
            "mean_viterbi_duration": diagnostics.mean_duration,
        }
    )
)
display(pd.DataFrame(hmm.transition_matrix, index=["from 0", "from 1"], columns=["to 0", "to 1"]))
"""),
        code("""
fig = go.Figure()
dates = factor_change_dates[audit_rows]
fig.add_scatter(x=dates, y=filtered_probability[:, 1], name="filtered P(state 1)", mode="lines")
fig.add_scatter(x=dates, y=smoothed_probability[:, 1], name="smoothed P(state 1)", mode="lines")
fig.update_layout(
    title="HMM state probabilities: online filtering versus retrospective smoothing",
    xaxis_title="Treasury publication date",
    yaxis_title="Conditional probability",
    template="plotly_white",
)
fig.show()
"""),
        md(r"""
## 2. EM monotonicity and label audit

Baum–WelchはEMであり、観測log likelihoodを減らさない局所更新を行うがglobal optimumは保証しない。実装はlevel-factor change meanでlabelをcanonicalizeする。別initializationでlabelが反転してもlikelihoodは同じになり得る。
"""),
        code("""
assert np.all(np.diff(hmm.log_likelihood_trace) >= -1e-6)
assert np.all(np.diff(hmm.means[:, 0]) >= 0.0)
em_table = pd.DataFrame(
    {
        "iteration": np.arange(1, len(hmm.log_likelihood_trace) + 1),
        "log_likelihood": hmm.log_likelihood_trace,
    }
)
display(em_table.tail())
print("converged:", hmm.converged)
print("labels are observed truth:", False)
"""),
        md(
            r"""
## 3. 失敗モード

- smoothed probabilityをforecast-origin stateへ使う
- EM convergenceをglobal optimumやBayesian posteriorと呼ぶ
- state 0/1の番号に経済的意味を固定する
- occupancyが極小のstateを説明せず残す
- state数をouter test likelihoodで選ぶ

## 4. 段階別演習

### 基礎

1. forward recursionをlog-sum-expで書け。
2. filtered/smoothed/Viterbiの目的を比較せよ。

### 標準

3. 2/3/4 stateをtraining fit、validation log scoreで比較せよ。
4. state durationとgeometric distributionの関係を導出せよ。

### 研究

5. switching VARまたはswitching Kalman modelの識別条件を書け。

## 5. Exit Criteria

- [ ] HMM factorizationを書ける
- [ ] iid mixtureとMarkov mixtureを区別した
- [ ] EM log likelihoodの単調性を検査した
- [ ] label canonicalizationとstate数感応度を計画した
- [ ] filtered stateだけがforecast originで利用可能と説明した

## 6. 出典

"""
            + LATENT_SOURCES
        ),
    ]


def week32_cells():
    return [
        md(r"""
# 46. Week 32 — MCMC, ESS, split-Rhat, and approximation boundaries

## 学習目標

- random-walk Metropolisのdetailed balanceを説明できる
- acceptance rate、ESS、multi-chain split-(\hat R)を併用できる
- proposal scale failureを実験で示せる
- Gibbs、HMC/NUTS、VI、SMCの適用条件と本Coreの境界を説明できる

## 前提知識

- Week 29のposterior
- B2のMarkov chainとMonte Carlo error
"""),
        setup_cell(46),
        treasury_curve_cell(),
        md(r"""
## 1. Random-walk Metropolis

対称proposal (q(\theta'\mid\theta)=q(\theta\mid\theta')) ならacceptanceは

$$
\alpha(\theta,\theta')=\min\left\{1,\frac{p(\theta'\mid y)}{p(\theta\mid y)}\right\}.
$$

高いacceptanceだけでは良いmixingを意味しない。小さすぎるstepはほぼ全てacceptされてもESSが低い。
"""),
        code("""
horizon = 5
origins = np.arange(curve_yields.shape[0] - horizon)
target = (curve_yields[origins + horizon, 3] - curve_yields[origins, 3]) * 100.0
target_dates = curve_dates[origins + horizon]
training_target = target[target_dates <= train_end_date]
known_variance = float(np.var(training_target, ddof=1))
prior_variance = 25.0

def log_posterior(parameter):
    mean = parameter[0]
    return float(
        -0.5 * mean**2 / prior_variance
        -0.5 * np.sum((training_target - mean) ** 2) / known_variance
    )

chains = []
chain_rows = []
for chain_index, initial in enumerate([-5.0, -1.0, 1.0, 5.0]):
    result = qt.metropolis_hastings(
        log_posterior,
        [initial],
        3000,
        proposal_scale=[0.25],
        burn_in=1000,
        rng=task_rng(1, chain_index),
    )
    chains.append(result.samples[:, 0])
    chain_rows.append(
        {"chain": chain_index, "acceptance_rate": result.acceptance_rate, "ess": result.effective_sample_size[0], "mean": result.samples[:, 0].mean()}
    )
chain_array = np.asarray(chains)[:, :, None]
display(pd.DataFrame(chain_rows))
print("classical split-Rhat:", qt.split_rhat(chain_array)[0])
"""),
        code("""
fig = go.Figure()
for chain_index in range(chain_array.shape[0]):
    fig.add_scatter(x=np.arange(500), y=chain_array[chain_index, :500, 0], name=f"chain {chain_index}", mode="lines")
fig.update_layout(title="Multiple-chain trace audit", xaxis_title="Retained draw", yaxis_title="Mean change (bp)", template="plotly_white")
fig.show()
"""),
        md(r"""
## 2. Proposal-scale failure
"""),
        code("""
proposal_rows = []
for index, proposal_scale in enumerate([0.002, 0.25, 10.0]):
    result = qt.metropolis_hastings(
        log_posterior,
        [0.0],
        3000,
        proposal_scale=[proposal_scale],
        burn_in=500,
        rng=task_rng(2, index),
    )
    proposal_rows.append(
        {"proposal_scale": proposal_scale, "acceptance_rate": result.acceptance_rate, "ess": result.effective_sample_size[0], "posterior_mean": result.samples[:, 0].mean()}
    )
display(pd.DataFrame(proposal_rows))
"""),
        md(
            r"""
## 3. Algorithm boundary

| Method | Strength | Required audit |
|---|---|---|
| Gibbs | conjugate full conditionals | autocorrelation、blocking |
| MH | generic ratio | proposal scale、ESS、multi-chain |
| HMC/NUTS | continuous differentiable high dimension | divergences、energy、rank-normalized (\hat R)/ESS |
| VI | fast approximation | under-dispersion、objective gap、predictive calibration |
| SMC | sequence/multimodality | particle ESS、resampling、path degeneracy |

本Core helperのsplit-(\hat R)はclassical variance versionであり、Vehtari et al.のrank-normalized/folded/localized diagnosticを実装していない。production HMC/NUTSの代替としない。

## 4. 失敗モード

- 一つのchainとtrace plotだけでconvergenceを宣言する
- acceptance rateだけを最適化する
- burn-in後もinitialization差が残るのに平均を統合する
- classical split-(\hat R)をrank-normalized (\hat R)と呼ぶ
- finite differenceをautomatic differentiationと呼ぶ

## 5. 段階別演習

### 基礎

1. three proposal scalesのacceptance/ESS trade-offを説明せよ。
2. Monte Carlo SEをposterior SDとESSから計算せよ。

### 標準

3. rank normalizationを実装しclassical split-(\hat R)と比較せよ。
4. independent conjugate drawsをoracleとしてMH meanを検証せよ。

### 研究

5. HMC/NUTS導入時のdependency、AD、divergence test計画を書け。

## 6. Exit Criteria

- [ ] explicit RNGと複数chainを使った
- [ ] acceptance、ESS、split-(\hat R)を報告した
- [ ] proposal-scale failureを再現した
- [ ] classicalとrank-normalized diagnosticを区別した
- [ ] HMC/NUTS/VI/SMCを未実装のAdvanced範囲と明記した

## 7. 出典

"""
            + BAYES_SOURCES
            + LATENT_SOURCES
        ),
    ]


def project_cells():
    return [
        md(r"""
# 47. B8 Project — Treasury Predictive Uncertainty and Latent-State Audit

> latent stateは市場の隠れた真実ではない。観測系列を圧縮するmodel componentとして、外部予測と安定性で反証する。

## 学習目標

- B7と同じ5公表日先curve targetとouter testを再利用できる
- Bayesian regression posterior predictiveとHMM conditional predictiveを区別できる
- state数をtraining/validationだけで固定できる
- point RMSE、coverage、width、log score、occupancy、duration、transition stabilityを監査できる
- label switching、parameter uncertainty不足、no-selectionをclaimへ反映できる

## 前提知識

- Week 29–32の全Exit Criteria
- B7 Projectのlocked data/horizon/split
"""),
        setup_cell(47),
        treasury_curve_cell(),
        md(r"""
## 1. Locked contract

| Item | Rule |
|---|---|
| Target | five-publication change of all five Treasury tenors |
| Point baseline | zero change (random walk in levels) |
| Bayesian model | tenor-wise NIG regression posterior predictive |
| Latent model | diagonal-Gaussian HMM on fixed-decay NS factor changes |
| State count | 2/3/4 fit on training, select by validation log score |
| Outer test | unchanged B5/B6/B7 start, one use |
| HMM uncertainty | emission/state simulation conditional on point-estimated parameters |
| Prohibited | state=true regime、full Bayes claim、causality、PnL |
"""),
        code("""
decay = 0.5
loadings = qt.nelson_siegel_loadings(maturity_years, decay)
factors = qt.extract_nelson_siegel_factors(curve_yields, maturity_years, decay)
factor_changes_bp = np.diff(factors, axis=0) * 100.0
factor_change_dates = curve_dates[1:]
factor_training = factor_change_dates <= train_end_date
factor_validation = (factor_change_dates > train_end_date) & (factor_change_dates <= validation_end_date)

selection_rows = []
candidate_models = {}
for state_count in [2, 3, 4]:
    candidate = qt.fit_gaussian_hmm(factor_changes_bp[factor_training], state_count)
    candidate_models[state_count] = candidate
    validation_score = qt.hmm_log_likelihood(candidate, factor_changes_bp[factor_validation])
    selection_rows.append(
        {"states": state_count, "validation_log_score_per_observation": validation_score / np.sum(factor_validation), "converged": candidate.converged}
    )
selection_table = pd.DataFrame(selection_rows)
selected_states = int(selection_table.loc[selection_table["validation_log_score_per_observation"].idxmax(), "states"])
display(selection_table)
print("selected states before outer test:", selected_states)
"""),
        md(r"""
## 2. Pretest refit and filtered state audit
"""),
        code("""
pretest_changes = factor_change_dates < test_start_date
hmm = qt.fit_gaussian_hmm(factor_changes_bp[pretest_changes], selected_states)
filtered_probability = qt.hmm_filtered_probabilities(hmm, factor_changes_bp)
diagnostics = qt.hmm_state_diagnostics(hmm, factor_changes_bp[pretest_changes])
state_table = pd.DataFrame(
    {
        "state": np.arange(selected_states),
        "level_change_mean_bp": hmm.means[:, 0],
        "slope_change_mean_bp": hmm.means[:, 1],
        "curvature_change_mean_bp": hmm.means[:, 2],
        "occupancy": diagnostics.occupancy,
        "mean_duration": diagnostics.mean_duration,
    }
)
display(state_table)

fig = go.Figure()
for state in range(selected_states):
    fig.add_scatter(x=factor_change_dates, y=filtered_probability[:, state], name=f"state {state}", mode="lines")
fig.add_vline(x=pd.Timestamp(test_start_date).timestamp() * 1000, line_dash="dash", line_color="black")
fig.update_layout(title="Online HMM filtered probabilities under pretest parameters", yaxis_title="Probability", template="plotly_white")
fig.show()
"""),
        md(r"""
## 3. Same-target Bayesian and HMM predictive distributions

Bayesian regressionはparameterとobservation uncertaintyを積分する。HMM sampleはpoint-estimated transition/emission parametersを固定するためfull posterior predictiveではない。この差を結果表にも残す。
"""),
        code("""
horizon = 5
all_origins = np.arange(curve_yields.shape[0] - horizon)
all_targets_bp = (curve_yields[all_origins + horizon] - curve_yields[all_origins]) * 100.0
all_target_dates = curve_dates[all_origins + horizon]
training_rows = all_target_dates < test_start_date
test_rows = curve_dates[all_origins] >= test_start_date

raw_features = np.column_stack(
    [curve_yields[all_origins], np.vstack([np.zeros(5), np.diff(curve_yields, axis=0)])[all_origins] * 100.0]
)
feature_mean = raw_features[training_rows].mean(axis=0)
feature_scale = raw_features[training_rows].std(axis=0, ddof=1)
design = np.column_stack([np.ones(raw_features.shape[0]), (raw_features - feature_mean) / feature_scale])

bayesian_means = []
bayesian_lowers = []
bayesian_uppers = []
for tenor_index in range(5):
    model = qt.fit_bayesian_linear_regression(
        design[training_rows], all_targets_bp[training_rows, tenor_index], prior_precision=1.0, prior_shape=2.0, prior_scale=25.0
    )
    predictive = qt.bayesian_linear_predictive(model, design[test_rows])
    lower, upper = predictive.interval(0.9)
    bayesian_means.append(predictive.mean)
    bayesian_lowers.append(lower)
    bayesian_uppers.append(upper)
bayesian_mean = np.column_stack(bayesian_means)
bayesian_lower = np.column_stack(bayesian_lowers)
bayesian_upper = np.column_stack(bayesian_uppers)

test_origins = all_origins[test_rows]
hmm_mean = np.empty((test_origins.size, 5))
hmm_lower = np.empty_like(hmm_mean)
hmm_upper = np.empty_like(hmm_mean)
for row, origin in enumerate(test_origins):
    probability = filtered_probability[origin - 1]
    factor_draws = qt.simulate_hmm_forecast(
        hmm,
        probability,
        horizon,
        600,
        rng=task_rng(10, int(origin)),
    ).sum(axis=1)
    curve_draws = factor_draws @ loadings.T
    hmm_mean[row] = curve_draws.mean(axis=0)
    hmm_lower[row] = np.quantile(curve_draws, 0.05, axis=0)
    hmm_upper[row] = np.quantile(curve_draws, 0.95, axis=0)
"""),
        code("""
test_actual = all_targets_bp[test_rows]
evaluation_rows = []
for name, mean, lower, upper, uncertainty in [
    ("Bayesian regression", bayesian_mean, bayesian_lower, bayesian_upper, "posterior predictive"),
    ("HMM", hmm_mean, hmm_lower, hmm_upper, "parameter-conditional predictive"),
]:
    evaluation_rows.append(
        {
            "model": name,
            "uncertainty_contract": uncertainty,
            "aggregate_rmse_bp": np.sqrt(np.mean((test_actual - mean) ** 2)),
            "marginal_coverage_90": np.mean((test_actual >= lower) & (test_actual <= upper)),
            "mean_interval_width_bp": np.mean(upper - lower),
        }
    )
evaluation_rows.insert(
    0,
    {
        "model": "random walk",
        "uncertainty_contract": "point baseline only",
        "aggregate_rmse_bp": np.sqrt(np.mean(test_actual**2)),
        "marginal_coverage_90": np.nan,
        "mean_interval_width_bp": np.nan,
    },
)
evaluation_table = pd.DataFrame(evaluation_rows)
display(evaluation_table)
random_walk_rmse = float(evaluation_table.loc[evaluation_table["model"] == "random walk", "aggregate_rmse_bp"].iloc[0])
adoptable = evaluation_table[
    (evaluation_table["model"] != "random walk")
    & (evaluation_table["aggregate_rmse_bp"] < random_walk_rmse)
    & (evaluation_table["marginal_coverage_90"].between(0.85, 0.95))
]
print("project conclusion:", "no model selected" if adoptable.empty else adoptable["model"].tolist())

tenor_rows = []
for tenor_index, tenor in enumerate(qt.DEFAULT_TENORS):
    tenor_rows.append(
        {
            "tenor": tenor,
            "random_walk_rmse_bp": np.sqrt(np.mean(test_actual[:, tenor_index] ** 2)),
            "bayesian_rmse_bp": np.sqrt(np.mean((test_actual[:, tenor_index] - bayesian_mean[:, tenor_index]) ** 2)),
            "hmm_rmse_bp": np.sqrt(np.mean((test_actual[:, tenor_index] - hmm_mean[:, tenor_index]) ** 2)),
            "bayesian_coverage_90": np.mean((test_actual[:, tenor_index] >= bayesian_lower[:, tenor_index]) & (test_actual[:, tenor_index] <= bayesian_upper[:, tenor_index])),
            "hmm_coverage_90": np.mean((test_actual[:, tenor_index] >= hmm_lower[:, tenor_index]) & (test_actual[:, tenor_index] <= hmm_upper[:, tenor_index])),
        }
    )
display(pd.DataFrame(tenor_rows))
"""),
        md(r"""
## 4. Transition stability and label sensitivity
"""),
        code("""
pretest_values = factor_changes_bp[pretest_changes]
split_point = pretest_values.shape[0] // 2
early = qt.fit_gaussian_hmm(pretest_values[:split_point], selected_states)
late = qt.fit_gaussian_hmm(pretest_values[split_point:], selected_states)
stability_table = pd.DataFrame(
    [
        {
            "diagnostic": "transition Frobenius distance",
            "value": np.linalg.norm(early.transition_matrix - late.transition_matrix),
        },
        {
            "diagnostic": "emission-mean Frobenius distance",
            "value": np.linalg.norm(early.means - late.means),
        },
        {
            "diagnostic": "minimum full-pretest occupancy",
            "value": diagnostics.occupancy.min(),
        },
        {
            "diagnostic": "maximum classical state duration",
            "value": diagnostics.mean_duration.max(),
        },
    ]
)
display(stability_table)
print("labels canonicalized by level-factor change mean:", True)
print("labels are external observed regimes:", False)
print("HMM parameter posterior included:", False)
"""),
        md(
            r"""
## 5. Claim audit

評価可能なのは、固定snapshotと固定horizonにおけるhistorical point/predictive performance、state occupancy/duration、transition/emission stabilityである。stateに「risk-on」「crisis」等の名前を付けるには外部変数・事前定義・再現性検証が必要で、本Projectでは行わない。

HMM intervalはstate/emission randomnessだけでparameter uncertaintyを欠く。Bayesian regressionはfull posterior predictiveだがGaussian linear specificationに依存する。どちらもcoverageとwidthを満たさなければ採用しない。outer testを見た後のstate数変更には新しいholdoutが必要である。

## 6. 失敗モード

- outer testでstate数、prior、featureを選び直す
- smoothed stateをforecast originへ使う
- HMM conditional predictiveをfull Bayesian posterior predictiveと呼ぶ
- labelを市場の真のregimeと呼ぶ
- aggregate coverageだけを報告しtenor failureを隠す
- test log scoreを見てmodel storyを後付けする

## 7. 段階別演習

### 基礎

1. state selection tableとouter evaluationを再現せよ。
2. occupancy、duration、transitionをartifactへ保存せよ。

### 標準

3. horizon 1/20をsecondaryとして追加せよ。
4. filtered probabilityとsmoothed probabilityでpredictive leakage差を示せ。

### 研究

5. Bayesian HMMでtransition/emission parameter uncertaintyを積分する設計を書け。
6. switching Kalman DNSへ拡張する前のsimulation-based calibrationを設計せよ。

## 8. Exit Criteria

- [ ] B7と同じ5公表日targetとouter testを使った
- [ ] state数をtraining/validationだけで固定した
- [ ] forecast originではfiltered probabilityだけを使った
- [ ] random walk、Bayesian、HMMのRMSEを比較した
- [ ] coverage、width、uncertainty contractを分けた
- [ ] occupancy、duration、transition、state-count sensitivityを監査した
- [ ] label switchingとparameter uncertainty不足をclaimへ反映した
- [ ] stateを観測真値・causal regime・PnL signalと呼んでいない

## 9. 出典

"""
            + BAYES_SOURCES
            + LATENT_SOURCES
        ),
    ]


__all__ = [
    "overview_cells",
    "project_cells",
    "week29_cells",
    "week30_cells",
    "week31_cells",
    "week32_cells",
]
