"""Builder for notebook 13: likelihood, estimands, and finite-sample MLE."""

from nbkit import code, md

cells = [
    md(r"""
# 13. Week 9 — likelihood、estimand、有限標本MLE

> optimizerの成功と、推定対象に対する統計的妥当性は別の判定である。

## 学習目標

- estimand、estimator、estimateをdata確認前に書き分けられる
- Gaussian、logistic、Poissonのlog-likelihood、score、Hessianを導出できる
- consistency・asymptotic normalityの条件とDelta methodの変換を説明できる
- analytic derivativeをcentral finite differenceで独立に照合できる
- model-based SE、empirical SD、finite-sample bias、coverageを比較できる
- logistic separationとPoisson overdispersionを検出し、optimizer statusと分けて報告できる
- misspecification下でinverse Hessianだけでは不十分な理由を説明できる

## 前提知識

- Week 6のCLT、delta method、coverage、Monte Carlo error
- B1のgradient、Hessian、conditioning、least squares
- Bernoulli、Gaussian、Poisson distributionの基本形
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy.special import expit

import quant_textbook.inference as inference

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
NOTEBOOK_ID = 13
TASK_IDS = {
    "derivative": 1,
    "coverage": 2,
    "overdispersion_example": 3,
}
MODEL_IDS = {
    "gaussian": 1,
    "logistic": 2,
    "poisson": 3,
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
## 1. dataより先にestimandを固定する

この章のsampling unitは独立な観測行 $i=1,\ldots,n$ とする。design rowを $x_i$、outcomeを $Y_i$ とし、次の三つのestimandを区別する。

| Model | Conditional estimand | Parameter interpretation | Scale |
|---|---|---|---|
| Gaussian | $\mathbb{E}[Y_i\mid x_i]=x_i^\top\beta$ | outcome平均の単位変化 | outcome unit |
| Logistic | $\operatorname{logit}\mathbb{P}(Y_i=1\mid x_i)=x_i^\top\beta$ | conditional log-odds差 | log-odds |
| Poisson | $\log\mathbb{E}[Y_i\mid x_i]=x_i^\top\beta$ | conditional log-rate差 | log-rate |

例えばlogisticのslope $\beta_1$ は、他のdesign列を固定したとき $x_1$ が1増えることに対応するlog-odds差である。これはrisk difference、予測精度、介入効果ではない。Poissonでexposure timeが異なる場合はoffsetを仕様へ含める必要があるが、この合成実験では全観測のexposureを1とする。

**Estimand**はpopulation modelのparameter、**estimator**はdataからparameterを選ぶ規則、**estimate**は今回得た数値である。MLEはlikelihoodを最大化するestimatorであり、modelそのものが正しいことを証明する手順ではない。
"""),
    md(r"""
## 2. likelihood、score、Hessian

独立観測のlog-likelihoodを

$$
\ell_n(\theta)=\sum_{i=1}^{n}\log p_\theta(Y_i\mid x_i)
$$

とする。scoreとobserved Hessianは

$$
U_n(\theta)=\nabla_\theta\ell_n(\theta),
\qquad
H_n(\theta)=\nabla_\theta^2\ell_n(\theta)
$$

である。interiorのMLEでは $U_n(\hat\theta)\approx0$ を期待し、observed information $-H_n(\hat\theta)$ の逆行列をmodel-based covarianceの近似に使う。

canonical linkを使うlogistic・Poisson regressionでは

$$
U_n(\beta)=X^\top(y-\mu),
\qquad
H_n(\beta)=-X^\top W X.
$$

logisticでは $\mu_i=p_i$、$W_{ii}=p_i(1-p_i)$、Poissonでは $\mu_i=\exp(x_i^\top\beta)$、$W_{ii}=\mu_i$ である。

Gaussianではscaleを正に保つため $\eta=\log\sigma$ をparameterとし、$\theta=(\beta^\top,\eta)^\top$ とする。実装が返すscale parameterとcoefficient covarianceのparameterizationを混同しない。
"""),
    md(r"""
### 2.1 三つのmodelを式に展開する

$z_i=x_i^\top\beta$、Gaussianでは $r=y-X\beta$ と置く。定数項を含むGaussian log-likelihoodは

$$
\ell_G(\beta,\eta)
=-\frac{n}{2}\log(2\pi)-n\eta
-\frac{1}{2}e^{-2\eta}r^\top r
$$

であり、derivativeは

$$
U_\beta=e^{-2\eta}X^\top r,
\qquad
U_\eta=-n+e^{-2\eta}r^\top r,
$$

$$
H_{\beta\beta}=-e^{-2\eta}X^\top X,
\quad
H_{\beta\eta}=-2e^{-2\eta}X^\top r,
\quad
H_{\eta\eta}=-2e^{-2\eta}r^\top r,
$$

となる。$H_{\eta\beta}=H_{\beta\eta}^\top$ である。

Logisticで $p_i=(1+e^{-z_i})^{-1}$ とすると

$$
\ell_L(\beta)=\sum_{i=1}^n
\left\{Y_i z_i-\log(1+e^{z_i})\right\},
$$

$$
U_L=X^\top(y-p),
\qquad
H_L=-X^\top\operatorname{diag}\{p_i(1-p_i)\}X.
$$

Poissonで $\mu_i=e^{z_i}$ とすると

$$
\ell_P(\beta)=\sum_{i=1}^n
\left\{Y_i z_i-\mu_i-\log(Y_i!)\right\},
$$

$$
U_P=X^\top(y-\mu),
\qquad
H_P=-X^\top\operatorname{diag}(\mu_i)X.
$$

実装では同じ式の数値overflowを避ける。安定化はestimandやlikelihoodを変えず、同じ数学的対象を浮動小数点で評価するために行う。

### 2.2 consistency、asymptotic normality、Delta methodの契約

MLEの漸近結果には、少なくとも次の条件が必要である。

1. sampling unitが定義され、想定する独立性または依存条件が成立する
2. $\theta_0$ がparameter spaceのinteriorにあり、population likelihoodの一意な最大化点としてidentifiedである
3. log-likelihoodが近傍で十分滑らかで、LLN・CLT・微分と期待値の交換に必要なmoment条件がある
4. 1観測あたりのFisher information

$$
I_1(\theta_0)
=\mathbb{E}\left[-\nabla_\theta^2
\log p_{\theta_0}(Y\mid X)\right]
$$

がfiniteかつnonsingularである

これらの条件とcorrect specificationの下で

$$
\hat\theta\xrightarrow{p}\theta_0,
\qquad
\sqrt{n}(\hat\theta-\theta_0)
\xrightarrow{d}
\mathcal{N}\left(0,I_1(\theta_0)^{-1}\right).
$$

滑らかなscalar transformation $g$にはDelta methodを適用し、

$$
\sqrt{n}\{g(\hat\theta)-g(\theta_0)\}
\xrightarrow{d}
\mathcal{N}\left(
0,
\nabla g(\theta_0)^\top I_1(\theta_0)^{-1}\nabla g(\theta_0)
\right).
$$

例えばlogisticのodds ratioやPoissonのrate ratioは $g(\beta_1)=e^{\beta_1}$ であり、$\operatorname{SE}\{g(\hat\beta_1)\}\approx e^{\hat\beta_1}\operatorname{SE}(\hat\beta_1)$ と変換する。

modelがmisspecifiedでも、per-observation criterion $m(Z_i,\theta)$ のpopulation maximizer

$$
\theta^*=\arg\max_\theta\mathbb{E}[m(Z_i,\theta)]
$$

がpseudo-true targetとしてidentifiedであれば、M-estimationの議論ができる。

$$
A=-\mathbb{E}[\nabla_\theta^2m(Z_i,\theta^*)],
\qquad
B=\mathbb{E}[\psi_i\psi_i^\top],
\qquad
\psi_i=\nabla_\theta m(Z_i,\theta^*),
$$

$$
\sqrt{n}(\hat\theta-\theta^*)
\xrightarrow{d}
\mathcal{N}(0,A^{-1}BA^{-1}),
\qquad
\widehat{\operatorname{Cov}}(\hat\theta)
=\frac{1}{n}\hat A^{-1}\hat B\hat A^{-1}.
$$

correctly specified likelihoodではinformation identityにより $A=B=I_1$となる。misspecification下では一般に一致せず、inverse Hessianだけではuncertaintyを表せない。
"""),
    md(r"""
## 3. analytic derivativeを独立に監査する

`evaluate_likelihood` は三modelのlog-likelihood、analytic score、analytic Hessianを返す。中央差分は同じ式をsymbolically変形したものではなく、近傍の関数値からderivativeを再構成する検査手段である。

finite differenceのstepが大きすぎるとtruncation error、小さすぎるとcancellationが支配する。完全一致ではなく、parameter scaleを反映したrelative errorを報告する。
"""),
    code("""
derivative_rows = []
derivative_examples = {}

for model in ("gaussian", "logistic", "poisson"):
    rng = task_rng("derivative", MODEL_IDS[model])
    sample_size = 90
    predictor = rng.normal(size=sample_size)
    X = np.column_stack((np.ones(sample_size), predictor))

    if model == "gaussian":
        parameters = np.array([0.25, -0.35, np.log(0.9)])
        y = X @ np.array([0.30, -0.40]) + rng.normal(scale=0.8, size=sample_size)
    elif model == "logistic":
        parameters = np.array([-0.10, 0.50])
        y = rng.binomial(1, expit(X @ np.array([-0.20, 0.60])))
    else:
        parameters = np.array([0.05, 0.20])
        y = rng.poisson(np.exp(X @ np.array([0.10, 0.25])))

    evaluation = inference.evaluate_likelihood(model, parameters, X, y)

    def log_likelihood_at(candidate, current_model=model, current_X=X, current_y=y):
        return inference.evaluate_likelihood(
            current_model,
            candidate,
            current_X,
            current_y,
        ).log_likelihood

    numerical_score = inference.finite_difference_gradient(
        log_likelihood_at,
        parameters,
    )
    numerical_hessian = inference.finite_difference_hessian(
        log_likelihood_at,
        parameters,
    )
    score_relative_error = np.linalg.norm(evaluation.score - numerical_score) / max(
        1.0,
        np.linalg.norm(evaluation.score),
    )
    hessian_relative_error = np.linalg.norm(
        evaluation.hessian - numerical_hessian,
        ord="fro",
    ) / max(1.0, np.linalg.norm(evaluation.hessian, ord="fro"))
    derivative_rows.append(
        {
            "model": model,
            "score_relative_error": score_relative_error,
            "hessian_relative_error": hessian_relative_error,
            "information_condition": np.linalg.cond(-evaluation.hessian),
        }
    )
    derivative_examples[model] = (X, y)

derivative_table = pd.DataFrame(derivative_rows)
display(derivative_table)

assert derivative_table["score_relative_error"].max() < 1e-6
assert derivative_table["hessian_relative_error"].max() < 1e-5
"""),
    md(r"""
小さいderivative errorはこの入力近傍で式と実装が整合する証拠である。しかし、signを共通に誤ったobjectiveとderivativeを同時に検査するなど、検査側が同じ誤りを共有する可能性は残る。既知のclosed-form Gaussian MLE、SciPy optimizer、finite-sample simulationという異なる検査も重ねる。
"""),
    md(r"""
## 4. fit結果では数値診断とmodel診断を分ける

共通結果objectはcoefficient、model-based covariance、fitted meanに加え、gradient norm、informationの条件数、separation、overdispersion、warningを返す。`optimizer_converged` とmodel診断の合否は意図的に別fieldである。ただし、後者は実装済み診断に通ったかだけを表し、model validityの証明ではない。そのためNotebookでは `implemented_diagnostics_passed` と表示する。
"""),
    code("""
fit_rows = []

for model, (X, y) in derivative_examples.items():
    if model == "gaussian":
        result = inference.fit_gaussian_mle(X, y)
    elif model == "logistic":
        result = inference.fit_logistic_mle(
            X,
            y,
            gradient_tolerance=1e-6,
        )
    else:
        result = inference.fit_poisson_mle(
            X,
            y,
            gradient_tolerance=1e-6,
        )
    fit_rows.append(
        {
            "model": model,
            "intercept": result.coefficients[0],
            "slope": result.coefficients[1],
            "slope_model_se": result.standard_errors[1],
            "optimizer_converged": result.diagnostics.optimizer_converged,
            "gradient_norm": result.diagnostics.gradient_norm,
            "information_condition": result.diagnostics.hessian_condition_number,
            "implemented_diagnostics_passed": (
                result.diagnostics.implemented_diagnostics_passed
            ),
        }
    )

fit_table = pd.DataFrame(fit_rows)
display(fit_table.round(7))
"""),
    code("""
transformed_effect_table = fit_table.loc[
    fit_table["model"].isin(["logistic", "poisson"]),
    ["model", "slope", "slope_model_se"],
].copy()
transformed_effect_table["transformed_estimand"] = [
    "conditional odds ratio",
    "conditional rate ratio",
]
transformed_effect_table["exp_slope"] = np.exp(
    transformed_effect_table["slope"]
)
transformed_effect_table["delta_method_se"] = (
    transformed_effect_table["exp_slope"]
    * transformed_effect_table["slope_model_se"]
)
display(transformed_effect_table.round(6))
"""),
    md(r"""
gradient normはstationarityの数値診断である。information conditionが大きければ、scoreが小さくてもparameterはdata perturbationへ敏感になり得る。Delta methodの表はlog-oddsとlog-rateをそれぞれodds ratioとrate ratioへ変換したものである。model-based SEは指定したconditional distributionと独立性が正しいときの近似であり、optimizerの停止条件からは導けない。
"""),
    md(r"""
## 5. finite-sample simulation — SEをcoverageで検査する

各replicationで新しいdesignとoutcomeを生成し、slopeを再推定する。次を別々に測る。

$$
\operatorname{Bias}(\hat\beta_1)
=\mathbb{E}[\hat\beta_1]-\beta_1,
$$

$$
\operatorname{SD}_{\mathrm{MC}}(\hat\beta_1),
\qquad
\overline{\operatorname{SE}}_{\mathrm{model}},
$$

および95% Wald intervalのempirical coverageである。coverage推定自体のMonte Carlo SEはindicatorを $R$ 回平均した

$$
\operatorname{MCSE}(\hat c)
=\sqrt{\frac{\hat c(1-\hat c)}{R}}
$$

で報告する。ここで $R$ はoptimizerが数値的に収束したreplication数である。primary ruleとして、非収束fitが返した見かけのintervalはcoverageに入れず、attempted数、coverageを評価できた数、optimizer failure rateを併記する。これにより、条件付きのstatistical coverageとalgorithmの信頼性を混ぜない。end-to-endの成功率を問う場合は、非収束をfailureとする別metricを事前指定する。
"""),
    code("""
def simulate_slope_coverage(
    model,
    sample_size,
    replications,
    *,
    overdispersed=False,
):
    rng = task_rng(
        "coverage",
        MODEL_IDS[model],
        sample_size,
        int(overdispersed),
    )
    true_coefficients = {
        "gaussian": np.array([0.20, 0.45]),
        "logistic": np.array([-0.20, 0.70]),
        "poisson": np.array([0.20, 0.45]),
    }[model]
    estimates = []
    standard_errors = []
    optimizer_converged = []
    implemented_diagnostics_passed = []
    separation_detected = []
    dispersion_ratios = []

    for _ in range(replications):
        predictor = rng.normal(size=sample_size)
        X = np.column_stack((np.ones(sample_size), predictor))
        linear_predictor = X @ true_coefficients

        if model == "gaussian":
            y = linear_predictor + rng.normal(size=sample_size)
            result = inference.fit_gaussian_mle(X, y)
        elif model == "logistic":
            y = rng.binomial(1, expit(linear_predictor))
            result = inference.fit_logistic_mle(
                X,
                y,
                gradient_tolerance=1e-6,
            )
        else:
            conditional_mean = np.exp(linear_predictor)
            if overdispersed:
                overdispersion_alpha = 0.8
                latent_rate = rng.gamma(
                    shape=1.0 / overdispersion_alpha,
                    scale=overdispersion_alpha * conditional_mean,
                )
                y = rng.poisson(latent_rate)
            else:
                y = rng.poisson(conditional_mean)
            result = inference.fit_poisson_mle(
                X,
                y,
                gradient_tolerance=1e-6,
            )
            dispersion_ratios.append(result.diagnostics.overdispersion_ratio)

        estimates.append(result.coefficients[1])
        standard_errors.append(result.standard_errors[1])
        optimizer_converged.append(result.diagnostics.optimizer_converged)
        implemented_diagnostics_passed.append(
            result.diagnostics.implemented_diagnostics_passed
        )
        separation_detected.append(result.diagnostics.separation_detected)

    estimates = np.asarray(estimates)
    standard_errors = np.asarray(standard_errors)
    optimizer_converged = np.asarray(optimizer_converged, dtype=bool)
    if np.count_nonzero(optimizer_converged) < 2:
        raise RuntimeError("fewer than two fits converged; coverage is undefined")
    summary = inference.summarize_coverage(
        estimates[optimizer_converged],
        standard_errors[optimizer_converged],
        true_coefficients[1],
    )
    return {
        "scenario": model + (" overdispersed" if overdispersed else ""),
        "sample_size": sample_size,
        "attempted_replications": replications,
        "coverage_replications": summary.n_replications,
        "bias": summary.empirical_bias,
        "empirical_sd": summary.empirical_standard_deviation,
        "mean_model_se": summary.mean_model_standard_error,
        "model_se_to_empirical_sd": summary.standard_error_ratio,
        "coverage": summary.coverage,
        "coverage_mc_se": summary.coverage_monte_carlo_error,
        "optimizer_convergence_rate": np.mean(optimizer_converged),
        "optimizer_failure_rate": np.mean(~optimizer_converged),
        "implemented_diagnostics_pass_rate": np.mean(
            implemented_diagnostics_passed
        ),
        "separation_rate": np.mean(separation_detected),
        "mean_dispersion_ratio": (
            np.mean(dispersion_ratios) if dispersion_ratios else np.nan
        ),
    }


replications = 1_200
coverage_rows = []
for model in ("gaussian", "logistic", "poisson"):
    for sample_size in (60, 240):
        coverage_rows.append(
            simulate_slope_coverage(
                model,
                sample_size,
                replications,
            )
        )

coverage_rows.append(
    simulate_slope_coverage(
        "poisson",
        240,
        replications,
        overdispersed=True,
    )
)
coverage_table = pd.DataFrame(coverage_rows)
display(coverage_table.round(4))
"""),
    code("""
fig = go.Figure()
for scenario, group in coverage_table.groupby("scenario", sort=False):
    fig.add_scatter(
        x=group["sample_size"],
        y=group["coverage"],
        error_y={
            "type": "data",
            "array": 1.96 * group["coverage_mc_se"],
            "visible": True,
        },
        mode="lines+markers",
        name=scenario,
    )
fig.add_hline(y=0.95, line_dash="dash", line_color="black")
fig.update_layout(
    title="Finite-sample Wald coverage with 95% Monte Carlo error bars",
    xaxis_title="Sample size",
    yaxis_title="Empirical coverage",
    yaxis_range=[0.65, 1.0],
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
Gaussian、logistic、正しく指定したPoissonでは、標本数とともにmodel SEとempirical SDが近づくことを期待する。ただし、nominal 0.95との差がcoverage MC intervalより小さい場合、seed固有の順位付けをしない。

`poisson overdispersed` はgamma-Poisson mixtureから生成している。fitは有限のcoefficientを返せても、Poisson model-based SEがempirical SDより小さく、coverageが低下する。表の `implemented_diagnostics_pass_rate` はdispersion診断も含む。これは試したreplication全体に対する実装済み診断の合格率であり、modelが正しい確率ではない。
"""),
    md(r"""
## 6. 失敗モード1 — logistic complete / quasi-complete separation

completeまたはquasi-complete separationでは、ある方向へcoefficientを大きくするほどlog-likelihoodが上限へ近づき、通常の有限MLEが存在しない。有限iterationのoptimizerは「十分平坦になった」と停止し、大きな有限値を返す場合がある。実装は両方の診断を `separation_detected` にまとめる。

次は $x<0$ なら0、$x>0$ なら1という完全分離と、境界付近でclassが重なるcaseを比較する。
"""),
    code("""
separation_predictor = np.concatenate((-np.arange(1, 9), np.arange(1, 9))).astype(float)
separation_X = np.column_stack(
    (np.ones(separation_predictor.size), separation_predictor)
)
separated_y = (separation_predictor > 0.0).astype(float)
overlap_y = separated_y.copy()
overlap_y[np.where(separation_predictor == -1.0)[0][0]] = 1.0
overlap_y[np.where(separation_predictor == 1.0)[0][0]] = 0.0

separated_fit = inference.fit_logistic_mle(
    separation_X,
    separated_y,
    gradient_tolerance=1e-6,
)
overlap_fit = inference.fit_logistic_mle(
    separation_X,
    overlap_y,
    gradient_tolerance=1e-6,
)

separation_table = pd.DataFrame(
    [
        {
            "case": "complete separation",
            "slope": separated_fit.coefficients[1],
            "slope_model_se": separated_fit.standard_errors[1],
            "optimizer_converged": separated_fit.diagnostics.optimizer_converged,
            "separation_detected": separated_fit.diagnostics.separation_detected,
            "implemented_diagnostics_passed": (
                separated_fit.diagnostics.implemented_diagnostics_passed
            ),
        },
        {
            "case": "overlap",
            "slope": overlap_fit.coefficients[1],
            "slope_model_se": overlap_fit.standard_errors[1],
            "optimizer_converged": overlap_fit.diagnostics.optimizer_converged,
            "separation_detected": overlap_fit.diagnostics.separation_detected,
            "implemented_diagnostics_passed": (
                overlap_fit.diagnostics.implemented_diagnostics_passed
            ),
        },
    ]
)
display(separation_table.round(5))
"""),
    code("""
prediction_grid = np.linspace(-8.0, 8.0, 300)
prediction_X = np.column_stack((np.ones(prediction_grid.size), prediction_grid))

fig = go.Figure()
fig.add_scatter(
    x=separation_predictor,
    y=separated_y,
    mode="markers",
    name="Separated observations",
)
fig.add_scatter(
    x=prediction_grid,
    y=expit(prediction_X @ separated_fit.coefficients),
    mode="lines",
    name="Separated fit",
)
fig.add_scatter(
    x=prediction_grid,
    y=expit(prediction_X @ overlap_fit.coefficients),
    mode="lines",
    name="Overlap fit",
    line={"dash": "dash"},
)
fig.update_layout(
    title="A finite optimizer output does not create a finite population MLE",
    xaxis_title="Predictor",
    yaxis_title="Fitted event probability",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
`optimizer_converged=True` でも `separation_detected=True` なら有限MLEとして合格させない。単にmaximum iterationを増やすとcoefficientがさらに大きくなるだけである。penalized likelihoodは別のestimatorとregularization contractを導入し、penaltyの設計とscalingによってはpseudo-true targetも変わる。したがって通常のMLEと黙って置き換えない。
"""),
    md(r"""
## 7. 失敗モード2 — Poisson overdispersionとmisspecification

Poisson modelはconditional meanとvarianceがともに $\mu_i$ であると仮定する。gamma-Poisson mixtureでは

$$
\mathbb{E}[Y_i\mid x_i]=\mu_i,
\qquad
\operatorname{Var}(Y_i\mid x_i)=\mu_i+\alpha\mu_i^2,
$$

となる。mean modelが正しくてもvariance modelは誤っている。Pearson dispersion

$$
\hat D
=\frac{1}{n-p}\sum_{i=1}^{n}
\frac{(Y_i-\hat\mu_i)^2}{\hat\mu_i}
$$

をPearson dispersion ratioと呼ぶ。$\hat D$ はvarianceとmeanのずれの診断であり、gamma-Poissonのheterogeneity parameter $\alpha$ 自体の推定量ではない。$\hat D$ が1から大きく離れるとき、Poisson inverse-information SEをそのまま信用しない。

別のboundary failureとして、interceptを含むdesignでcountがすべて0なら、interceptを $-\infty$ へ送るとlog-likelihoodが上限へ近づくため有限MLEは存在しない。実装はこれをoptimizerの成功とせず、boundary errorとして停止する。
"""),
    code("""
overdispersion_rng = task_rng("overdispersion_example")
overdispersion_sample_size = 400
overdispersion_predictor = overdispersion_rng.normal(
    size=overdispersion_sample_size
)
overdispersion_X = np.column_stack(
    (np.ones(overdispersion_sample_size), overdispersion_predictor)
)
overdispersion_mean = np.exp(overdispersion_X @ np.array([0.20, 0.45]))
gamma_poisson_alpha = 0.8
overdispersion_latent_rate = overdispersion_rng.gamma(
    shape=1.0 / gamma_poisson_alpha,
    scale=gamma_poisson_alpha * overdispersion_mean,
)
overdispersed_counts = overdispersion_rng.poisson(overdispersion_latent_rate)
overdispersed_fit = inference.fit_poisson_mle(
    overdispersion_X,
    overdispersed_counts,
    gradient_tolerance=1e-6,
)

print("optimizer converged:", overdispersed_fit.diagnostics.optimizer_converged)
print("Pearson dispersion ratio:", overdispersed_fit.diagnostics.overdispersion_ratio)
print("overdispersion detected:", overdispersed_fit.diagnostics.overdispersion_detected)
print(
    "implemented diagnostics passed:",
    overdispersed_fit.diagnostics.implemented_diagnostics_passed,
)
print("warnings:", overdispersed_fit.diagnostics.warnings)
"""),
    md(r"""
前半のM-estimation契約で示したように、misspecification下のasymptotic covarianceは一般にinverse Hessianだけでなく、score outer productを含むsandwich formになる。Week 11でHC/HAC/cluster covarianceへ進む。robust covarianceはvariance推定を変えるが、誤ったconditional mean、omitted variable、measurement errorを自動的に直さない。

### Advancedへの境界

- sufficient statisticとexponential familyの一般論
- profile likelihoodによるnuisance parameter除去
- quasi-likelihoodとGodambe information

これらはCoreのestimand、derivative照合、finite-sample coverage、separation・overdispersion診断を満たした後に扱う。
"""),
    md(r"""
## 8. 段階別演習

### 基礎

1. Bernoulli log-likelihoodからscoreとHessianを導出せよ。
2. Poisson log linkでcoefficientをrate ratioへ変換し、単位を説明せよ。
3. Gaussian scaleを $\log\sigma$ でparameter化する理由を書け。

### 標準

4. finite-difference stepを $10^{-2}$ から $10^{-8}$ まで変え、derivative errorのU字型を描け。
5. coverage replicationを4,000へ増やすか複数の独立root seedで繰り返し、0.95との差をMonte Carlo intervalで評価せよ。
6. separation exampleでiteration limitを変え、coefficient、gradient norm、log-likelihoodを記録せよ。
7. gamma-Poissonの $\alpha$ を0、0.2、0.8、1.5へ変え、Pearson $\hat D$、SE ratio、coverageを比較せよ。

### 研究

8. **Advanced:** scalar parameterのprofile likelihood intervalを実装し、Wald intervalと比較せよ。
9. **Advanced:** misspecified Poisson meanに対するsandwich covarianceを導出し、Week 11の実装へ接続せよ。
"""),
    md(r"""
## 9. Exit Criteria

- [ ] estimand、sampling unit、parameter scaleをdataより先に書ける
- [ ] Gaussian、logistic、PoissonのscoreとHessianを導出できる
- [ ] MLEのconsistency・asymptotic normalityの条件とDelta methodを説明できる
- [ ] analytic gradientとHessianを数値差分で照合できる
- [ ] optimizer convergenceと実装済みmodel診断の合否を別fieldで判定できる
- [ ] model-based SEとempirical SD、coverage、coverage MCSEを報告できる
- [ ] logistic separationを有限MLEとして受け入れない
- [ ] Poisson overdispersionでmodel-based SEが過小になり得ると説明できる
- [ ] misspecification下のpseudo-true targetとsandwich covarianceを式で書ける
"""),
    md(r"""
## 10. 出典

- [MIT OpenCourseWare 18.650: Lectures 4–5, Maximum Likelihood Estimation](https://ocw.mit.edu/courses/18-650-statistics-for-applications-fall-2016/resources/lecture-3-maximum-likelihood-estimation/) — likelihood、Fisher information、MLEの漸近正規性
- [MIT OpenCourseWare 18.655: Generalized Linear Models](https://ocw.mit.edu/courses/18-655-mathematical-statistics-spring-2016/e39da58d5b5f257bcd114210243f3510_MIT18_655S16_LecNote20_25.pdf) — canonical GLMのscore、Hessian、Fisher scoring、logistic、Poisson
- [SciPy `optimize.minimize`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html) — objective、Jacobian、Hessianとoptimizer resultの公式API
- [Albert and Anderson, *On the Existence of Maximum Likelihood Estimates in Logistic Regression Models*](https://doi.org/10.1093/biomet/71.1.1) — complete・quasi-complete separationと有限MLEの存在条件
- [White, *Maximum Likelihood Estimation of Misspecified Models*](https://doi.org/10.2307/1912526) — misspecification下のquasi-MLEとcovarianceの原論文
- [Wedderburn, *Quasi-likelihood Functions, Generalized Linear Models, and the Gauss–Newton Method*](https://doi.org/10.1093/biomet/61.3.439) — quasi-likelihoodの原論文

次章では、effect size・CI・powerをp-valueと分離し、resamplingとmultiple testingをsampling mechanismから監査する。
"""),
]
