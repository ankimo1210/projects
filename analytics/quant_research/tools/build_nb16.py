"""Builder for notebook 16: causal foundations and event-study boundaries."""

from nbkit import code, md

cells = [
    md(r"""
# 16. Week 12 — 因果推論の基礎とevent-studyの境界

> event前後に価格が動いたことと、政策がその価格変化を因果的に生んだことは、同じestimandではない。

## 学習目標

- potential outcomesでATE、counterfactual、識別仮定を定義する
- DAG上のconfounderとcolliderを区別し、調整がbiasを生む反例を作る
- overlapを可視化し、matching、IPW、outcome regression、doubly robust推定の役割を説明する
- DiDのparallel trendsとno anticipationを別々に検査する
- financial announcement studyとcausal panel event studyをestimand単位で分離する
- primary event window、timezone、timestamp precision、placebo計画を結果を見る前に指定する

## 前提知識

- 条件付き期待値、回帰、confidence interval
- Week 10の多重比較とpre-specification
- Week 11のsampling unitと依存に対応したcovariance
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy.special import expit
from scipy.stats import t as student_t

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
NOTEBOOK_ID = 16
TASK_IDS = {
    "potential_outcomes": 1,
    "dag": 2,
    "did_valid": 3,
    "did_anticipation": 4,
    "announcement": 5,
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
## 1. Potential outcomesと識別

binary treatmentを $A\in\{0,1\}$、potential outcomesを $Y(1),Y(0)$ とする。個体ごとのcausal effect $Y(1)-Y(0)$ は両方を同時に観測できない。母集団平均効果は

$$
\operatorname{ATE}=\mathbb{E}[Y(1)-Y(0)]
$$

である。観測outcomeはconsistencyの下で

$$
Y=AY(1)+(1-A)Y(0)
$$

と結ばれる。observational dataからATEを識別する代表的な条件は次の三つである。

1. **Consistency / well-defined intervention:** treatmentのversionとoutcome時点が明確
2. **Conditional exchangeability:** $(Y(1),Y(0))\perp A\mid X$
3. **Positivity / overlap:** 対象populationで $0<P(A=1\mid X)<1$

モデルのfitが良いことは、これらの識別仮定を保証しない。
"""),
    md(r"""
## 2. Confoundingとoverlapの合成実験

ここではcovariate $X$ がtreatment assignmentとpotential outcomesの両方を動かすDGPを作る。真のpotential outcomesを保持するため、simulation内ではsample ATEをoracleとして計算できる。実データではこのoracleは観測できない。
"""),
    code("""
def add_intercept(*columns):
    arrays = [np.asarray(column, dtype=float) for column in columns]
    return np.column_stack([np.ones(len(arrays[0])), *arrays])


def fit_logistic_newton(design, treatment, max_iterations=60, tolerance=1e-10):
    coefficients = np.zeros(design.shape[1])
    for _ in range(max_iterations):
        probabilities = expit(design @ coefficients)
        weights = np.clip(probabilities * (1.0 - probabilities), 1e-10, None)
        information = design.T @ (weights[:, None] * design)
        score = design.T @ (treatment - probabilities)
        step = np.linalg.solve(information, score)
        coefficients = coefficients + step
        if np.max(np.abs(step)) < tolerance:
            break
    return coefficients


def fit_group_outcomes(design, treatment, outcome):
    control_coefficients = np.linalg.lstsq(
        design[treatment == 0],
        outcome[treatment == 0],
        rcond=None,
    )[0]
    treated_coefficients = np.linalg.lstsq(
        design[treatment == 1],
        outcome[treatment == 1],
        rcond=None,
    )[0]
    return design @ control_coefficients, design @ treated_coefficients


def normalized_ipw_ate(treatment, outcome, propensity):
    treated_weights = treatment / propensity
    control_weights = (1.0 - treatment) / (1.0 - propensity)
    treated_mean = np.sum(treated_weights * outcome) / np.sum(treated_weights)
    control_mean = np.sum(control_weights * outcome) / np.sum(control_weights)
    return treated_mean - control_mean


def augmented_ipw_ate(treatment, outcome, propensity, outcome_zero, outcome_one):
    correction_one = treatment * (outcome - outcome_one) / propensity
    correction_zero = (1.0 - treatment) * (outcome - outcome_zero) / (1.0 - propensity)
    return np.mean(outcome_one - outcome_zero + correction_one - correction_zero)


def nearest_donor_outcomes(scores, outcomes, donor_mask, query_mask):
    donor_scores = scores[donor_mask]
    donor_outcomes = outcomes[donor_mask]
    order = np.argsort(donor_scores)
    donor_scores = donor_scores[order]
    donor_outcomes = donor_outcomes[order]
    query_scores = scores[query_mask]
    upper = np.searchsorted(donor_scores, query_scores, side="left")
    upper = np.clip(upper, 0, len(donor_scores) - 1)
    lower = np.clip(upper - 1, 0, len(donor_scores) - 1)
    choose_upper = np.abs(donor_scores[upper] - query_scores) < np.abs(
        donor_scores[lower] - query_scores
    )
    selected = np.where(choose_upper, upper, lower)
    return donor_outcomes[selected]


def matching_ate(treatment, outcome, scores):
    treated = treatment == 1
    control = ~treated
    imputed_zero = outcome.copy()
    imputed_one = outcome.copy()
    imputed_zero[treated] = nearest_donor_outcomes(scores, outcome, control, treated)
    imputed_one[control] = nearest_donor_outcomes(scores, outcome, treated, control)
    return np.mean(imputed_one - imputed_zero)
"""),
    code("""
po_rng = task_rng("potential_outcomes")
n_units = 6_000
covariate = po_rng.normal(size=n_units)
true_propensity = expit(-0.15 + 1.00 * covariate)
treatment = po_rng.binomial(1, true_propensity)
outcome_noise = po_rng.normal(scale=1.0, size=n_units)
potential_zero = 0.4 + 0.65 * covariate + 0.80 * covariate**2 + outcome_noise
individual_effect = 1.0 + 0.25 * covariate
potential_one = potential_zero + individual_effect
outcome = treatment * potential_one + (1 - treatment) * potential_zero
sample_ate = np.mean(individual_effect)

propensity_design = add_intercept(covariate)
propensity_coefficients = fit_logistic_newton(propensity_design, treatment)
estimated_propensity = np.clip(expit(propensity_design @ propensity_coefficients), 0.005, 0.995)

correct_outcome_design = add_intercept(covariate, covariate**2)
linear_outcome_design = add_intercept(covariate)
correct_zero, correct_one = fit_group_outcomes(correct_outcome_design, treatment, outcome)
linear_zero, linear_one = fit_group_outcomes(linear_outcome_design, treatment, outcome)

naive_difference = outcome[treatment == 1].mean() - outcome[treatment == 0].mean()
outcome_regression_ate = np.mean(correct_one - correct_zero)
ipw_ate = normalized_ipw_ate(treatment, outcome, estimated_propensity)
aipw_ate = augmented_ipw_ate(
    treatment,
    outcome,
    estimated_propensity,
    correct_zero,
    correct_one,
)
matched_ate = matching_ate(treatment, outcome, estimated_propensity)

estimate_table = pd.DataFrame(
    {
        "method": [
            "oracle sample ATE",
            "unadjusted difference",
            "outcome regression",
            "normalized IPW",
            "AIPW",
            "nearest-neighbor matching",
        ],
        "estimate": [
            sample_ate,
            naive_difference,
            outcome_regression_ate,
            ipw_ate,
            aipw_ate,
            matched_ate,
        ],
    }
)
estimate_table["error_vs_oracle"] = estimate_table["estimate"] - sample_ate
display(estimate_table.round(4))
"""),
    md(r"""
unadjusted differenceは、treatedとcontrolのcovariate分布の差をcausal effectへ混ぜる。adjustment後の推定値がoracleへ近いのは、この合成DGPで必要なconfounderとfunctional formを知っているからである。近さだけを見て実データのexchangeabilityを証明したことにはならない。
"""),
    code("""
histogram_edges = np.linspace(0.0, 1.0, 41)
fig = go.Figure()
for group_value, group_name in [(0, "control"), (1, "treated")]:
    counts, edges = np.histogram(
        estimated_propensity[treatment == group_value],
        bins=histogram_edges,
        density=True,
    )
    centers = 0.5 * (edges[1:] + edges[:-1])
    fig.add_bar(
        x=centers,
        y=counts,
        width=np.diff(edges),
        opacity=0.55,
        name=group_name,
    )
fig.update_layout(
    title="Propensity overlap is an identification diagnostic",
    xaxis_title="Estimated propensity score",
    yaxis_title="Density",
    barmode="overlay",
    template="plotly_white",
)
fig.show()

analysis_weights = treatment / estimated_propensity + (1.0 - treatment) / (1.0 - estimated_propensity)
weight_ess = analysis_weights.sum() ** 2 / np.sum(analysis_weights**2)
overlap_diagnostics = pd.Series(
    {
        "treated_fraction": treatment.mean(),
        "fraction_below_0.05_or_above_0.95": np.mean(
            (estimated_propensity < 0.05) | (estimated_propensity > 0.95)
        ),
        "maximum_analysis_weight": analysis_weights.max(),
        "weight_effective_sample_size": weight_ess,
        "raw_sample_size": n_units,
    },
    name="value",
)
display(overlap_diagnostics.to_frame().round(3))
"""),
    md(r"""
overlapが乏しい領域では、matchingは遠い相手を選び、IPWは少数観測へ大きなweightを置き、outcome regressionは外挿へ依存する。trimmingはvarianceを下げうるが、対象populationとestimandを変えるためsecondary analysisとして明記する。

| 方法 | 主な役割 | 必要な確認 | 自動的には解決しないもの |
|---|---|---|---|
| randomization | assignmentを設計してexchangeabilityを作る | noncompliance、attrition、interference | ill-defined treatment |
| matching | covariate supportとbalanceを設計段階で近づける | distance、caliper、残差balance | unmeasured confounding |
| IPW | propensityでpseudo-populationを作る | positivity、weight concentration、model | extreme weights |
| outcome regression | conditional outcomeを標準化する | functional form、extrapolation | assignment model failure |
| doubly robust | treatmentまたはoutcome nuisanceの一方が正しい場合に保護する | positivity、少なくとも一方の正しいmodel、regularity | 両方のmisspecification、hidden bias |
"""),
    md(r"""
## 3. Doubly robustは「二つとも間違ってよい」ではない

同じ標本で、propensity modelとoutcome modelの仕様だけを変える。真のassignmentはlinear logit、真のconditional outcomeはquadraticなので、intercept-only propensityとlinear outcomeをmisspecifiedとする。
"""),
    code("""
constant_propensity = np.full(n_units, treatment.mean())
dr_specifications = [
    ("correct PS + correct OR", estimated_propensity, correct_zero, correct_one),
    ("correct PS + linear OR", estimated_propensity, linear_zero, linear_one),
    ("constant PS + correct OR", constant_propensity, correct_zero, correct_one),
    ("constant PS + linear OR", constant_propensity, linear_zero, linear_one),
]
dr_rows = []
for label, propensity, outcome_zero, outcome_one in dr_specifications:
    estimate = augmented_ipw_ate(
        treatment,
        outcome,
        propensity,
        outcome_zero,
        outcome_one,
    )
    dr_rows.append(
        {
            "specification": label,
            "AIPW_estimate": estimate,
            "error_vs_oracle": estimate - sample_ate,
            "absolute_error_vs_oracle": abs(estimate - sample_ate),
        }
    )
display(pd.DataFrame(dr_rows).round(4))
"""),
    md(r"""
この1標本はdouble robustnessの証明ではない。少なくとも一方のnuisance modelが正しく、positivityなどの条件が成立する場合の整合性を有限標本でsmoke testしている。両方が誤る仕様では保護を期待できない。この固定seedでは、両方を誤指定したestimateが一部の正しい仕様よりoracleへ近く見えるが、これは有限標本の偶然であって頑健性ではない。replication間のbias、RMSE、coverageで性質を判定する。
"""),
    md(r"""
## 4. DAG — confounderを閉じ、colliderを開かない

DAGは統計的相関から自動生成する答えではなく、変数の時間順序と因果仮定を記述する設計図である。

| 構造 | 矢印 | 調整 |
|---|---|---|
| confounding path | `C -> A`, `C -> Y`, `A -> Y` | `C` を調整してback-door pathを閉じる候補 |
| collider path | `A -> S <- Y` | `S` を調整すると元は閉じたpathを開きうる |

次のlinear structural equationsでは真のdirect effectを知っている。confounderを落とす場合と、confounderに加えてcolliderを入れる場合を比較する。
"""),
    code("""
dag_rng = task_rng("dag")
n_dag = 30_000
confounder = dag_rng.normal(size=n_dag)
continuous_treatment = 0.85 * confounder + dag_rng.normal(size=n_dag)
TRUE_DIRECT_EFFECT = 0.70
dag_outcome = (
    TRUE_DIRECT_EFFECT * continuous_treatment
    + 0.90 * confounder
    + dag_rng.normal(size=n_dag)
)
collider = continuous_treatment + dag_outcome + 0.60 * dag_rng.normal(size=n_dag)

dag_specifications = {
    "unadjusted": add_intercept(continuous_treatment),
    "adjust confounder": add_intercept(continuous_treatment, confounder),
    "adjust confounder and collider": add_intercept(
        continuous_treatment,
        confounder,
        collider,
    ),
}
dag_rows = []
for label, design in dag_specifications.items():
    coefficients = np.linalg.lstsq(design, dag_outcome, rcond=None)[0]
    dag_rows.append(
        {
            "specification": label,
            "treatment_slope": coefficients[1],
            "bias_vs_structural_effect": coefficients[1] - TRUE_DIRECT_EFFECT,
        }
    )
display(pd.DataFrame(dag_rows).round(4))
"""),
    md(r"""
「利用できる変数をすべてcontrolする」は安全な規則ではない。confounder、mediator、collider、post-treatment variableはDAGとtimingで役割が変わる。collider biasをrobust SEで直すこともできない。
"""),
    md(r"""
## 5. DiD — parallel trendsとanticipation

2群2期間のATTを考える。treated groupを $G=1$、postを $T=1$ とすると、DiD estimandは

$$
\operatorname{DiD}
=\{\mathbb{E}[Y\mid G=1,T=1]-\mathbb{E}[Y\mid G=1,T=0]\}
-\{\mathbb{E}[Y\mid G=0,T=1]-\mathbb{E}[Y\mid G=0,T=0]\}.
$$

causal ATTとして読むには、少なくともuntreated potential outcomeのparallel trends、no anticipation、stable compositionなどが必要になる。pre-trendが平坦に見えることは有用な診断だが、反実仮想のparallel trendsを証明しない。
"""),
    code("""
def simulate_panel(rng, anticipation=False, n_units=500):
    event_times = np.arange(-5, 6)
    unit = np.repeat(np.arange(n_units), len(event_times))
    event_time = np.tile(event_times, n_units)
    treated_by_unit = np.zeros(n_units, dtype=int)
    treated_by_unit[n_units // 2 :] = 1
    treated = treated_by_unit[unit]
    unit_effect = rng.normal(scale=1.0, size=n_units)
    common_time = 0.10 * event_time + 0.08 * np.sin(event_time)
    untreated_outcome = unit_effect[unit] + common_time + rng.normal(scale=0.65, size=len(unit))
    post_effect = treated * (event_time >= 0) * (0.55 + 0.06 * event_time)
    anticipation_effect = treated * (event_time == -1) * 0.35 if anticipation else 0.0
    outcome = untreated_outcome + post_effect + anticipation_effect
    return pd.DataFrame(
        {
            "unit": unit,
            "event_time": event_time,
            "treated": treated,
            "outcome": outcome,
            "post_effect": post_effect,
            "anticipation_effect": anticipation_effect,
        }
    )


def group_time_summary(panel):
    summary = (
        panel.groupby(["event_time", "treated"], as_index=False)["outcome"]
        .mean()
        .pivot(index="event_time", columns="treated", values="outcome")
        .rename(columns={0: "control", 1: "treated"})
        .reset_index()
    )
    summary["gap"] = summary["treated"] - summary["control"]
    reference_gap = summary.loc[summary["event_time"] == -1, "gap"].iloc[0]
    summary["event_coefficient"] = summary["gap"] - reference_gap
    return summary


def simple_did(panel, pre_times=(-2, -1), post_times=(0, 1)):
    pre = panel[panel["event_time"].isin(pre_times)]
    post = panel[panel["event_time"].isin(post_times)]
    pre_gap = pre.loc[pre["treated"] == 1, "outcome"].mean() - pre.loc[
        pre["treated"] == 0, "outcome"
    ].mean()
    post_gap = post.loc[post["treated"] == 1, "outcome"].mean() - post.loc[
        post["treated"] == 0, "outcome"
    ].mean()
    return post_gap - pre_gap


valid_panel = simulate_panel(task_rng("did_valid"), anticipation=False)
anticipation_panel = simulate_panel(task_rng("did_anticipation"), anticipation=True)
valid_summary = group_time_summary(valid_panel)
anticipation_summary = group_time_summary(anticipation_panel)

did_comparison = pd.DataFrame(
    {
        "design": ["parallel trends + no anticipation", "anticipation at t=-1"],
        "DiD_estimate": [simple_did(valid_panel), simple_did(anticipation_panel)],
        "oracle_post_ATT": [
            valid_panel.loc[
                (valid_panel["treated"] == 1) & valid_panel["event_time"].isin([0, 1]),
                "post_effect",
            ].mean(),
            anticipation_panel.loc[
                (anticipation_panel["treated"] == 1)
                & anticipation_panel["event_time"].isin([0, 1]),
                "post_effect",
            ].mean(),
        ],
    }
)
did_comparison["error_vs_oracle"] = did_comparison["DiD_estimate"] - did_comparison["oracle_post_ATT"]
display(did_comparison.round(4))
"""),
    code("""
fig = go.Figure()
for label, summary, dash in [
    ("no anticipation", valid_summary, "solid"),
    ("anticipation at -1", anticipation_summary, "dash"),
]:
    fig.add_scatter(
        x=summary["event_time"],
        y=summary["event_coefficient"],
        mode="lines+markers",
        name=label,
        line={"dash": dash},
    )
fig.add_hline(y=0.0, line_dash="dot", line_color="black")
fig.add_vline(x=0.0, line_dash="dot", line_color="gray")
fig.update_layout(
    title="A contaminated reference period distorts an event-time path",
    xaxis_title="Event time",
    yaxis_title="Treated-control gap relative to t=-1",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
anticipationがあるとreference period自体が処置の影響を受け、post estimateが減衰し、より早いpre-periodまで見かけ上ずれる。lead coefficientが有意でないことだけをparallel trendsの証明にせず、政策情報がいつ漏れうるかを制度とtimestampから検討する。

staggered adoptionではtwo-way fixed-effectsのlead/lagがcohort・時点間のheterogeneous effectを不透明なweightで混ぜる場合がある。本章ではAdvancedとし、cohort-time ATTを明示するmodern DiDへ進む前に、2群設計のcounterfactualを固定する。
"""),
    md(r"""
## 6. 同じevent studyという語が指す二つの設計

| 項目 | Financial announcement study | Causal panel event study |
|---|---|---|
| typical data | 高頻度price / return | unit-by-time panel outcome |
| primary estimand | 事前指定windowのabnormal returnまたはprice response | event time $k$ のATT |
| counterfactual | eventがない短時間のnormal return | treated unitのuntreated potential outcome |
| central timing | 公表timestamp、market clock、同時news | adoption date、anticipation、cohort |
| central assumptions | timestamp精度、normal-return model、event isolation | parallel trends、no anticipation、valid comparison group |
| default claim | announcement周辺の市場反応 | 仮定下のdynamic causal effect |
| causal extension | surprise measureやcontrol designを追加 | cohort-time identificationと適切な推論 |

短いwindowはconfoundingの機会を減らしうるが、同時news、予想形成、情報漏洩、内生的な政策決定を自動的に消さない。
"""),
    md(r"""
## 7. 合成intraday announcement response

次のlabは実BOJデータではない。48件の合成eventを作り、publication timeをAsia/Tokyo、precisionを1分、primary response windowを $[0,5]$ 分、anticipation windowを $[-5,-1]$ 分と**結果生成前に固定**する。

timestamp precisionが1分なら、秒単位のprice discovery順序は識別できない。minute barのlabelがopenかcloseか、event時刻をどちらのbarへ含めるかもadapter契約に必要である。
"""),
    code("""
announcement_rng = task_rng("announcement")
n_events = 48
relative_minutes = np.arange(-15, 16)
event_timestamps = pd.date_range(
    "2024-01-23 12:30",
    periods=n_events,
    freq="14D",
    tz="Asia/Tokyo",
)
event_surprise = announcement_rng.normal(size=n_events)
intraday_returns = announcement_rng.normal(
    scale=0.18,
    size=(n_events, len(relative_minutes)),
)
response_mask = (relative_minutes >= 0) & (relative_minutes <= 5)
response_profile = np.array([0.30, 0.22, 0.15, 0.10, 0.06, 0.03])
intraday_returns[:, response_mask] += (
    0.40 + 0.18 * event_surprise[:, None]
) * response_profile[None, :]

anticipation_mask = (relative_minutes >= -5) & (relative_minutes <= -1)
event_response = intraday_returns[:, response_mask].sum(axis=1)
event_anticipation = intraday_returns[:, anticipation_mask].sum(axis=1)
response_standard_error = event_response.std(ddof=1) / np.sqrt(n_events)
anticipation_standard_error = event_anticipation.std(ddof=1) / np.sqrt(n_events)
announcement_critical_value = student_t.ppf(0.975, n_events - 1)

announcement_summary = pd.DataFrame(
    {
        "estimand": ["primary response [0, 5]", "anticipation [-5, -1]"],
        "mean_return_bps": [event_response.mean(), event_anticipation.mean()],
        "standard_error_bps": [response_standard_error, anticipation_standard_error],
        "ci_lower_bps": [
            event_response.mean() - announcement_critical_value * response_standard_error,
            event_anticipation.mean() - announcement_critical_value * anticipation_standard_error,
        ],
        "ci_upper_bps": [
            event_response.mean() + announcement_critical_value * response_standard_error,
            event_anticipation.mean() + announcement_critical_value * anticipation_standard_error,
        ],
    }
)
display(announcement_summary.round(4))

metadata_preview = pd.DataFrame(
    {
        "event_timestamp": event_timestamps[:4],
        "timezone": ["Asia/Tokyo"] * 4,
        "timestamp_precision_seconds": [60] * 4,
        "source_class": ["synthetic teaching event"] * 4,
    }
)
display(metadata_preview)
"""),
    code("""
mean_path = intraday_returns.mean(axis=0)
path_standard_error = intraday_returns.std(axis=0, ddof=1) / np.sqrt(n_events)
fig = go.Figure()
fig.add_scatter(
    x=relative_minutes,
    y=mean_path,
    mode="lines+markers",
    name="mean one-minute return",
)
fig.add_scatter(
    x=np.concatenate([relative_minutes, relative_minutes[::-1]]),
    y=np.concatenate(
        [
            mean_path + announcement_critical_value * path_standard_error,
            (mean_path - announcement_critical_value * path_standard_error)[::-1],
        ]
    ),
    fill="toself",
    fillcolor="rgba(31, 119, 180, 0.18)",
    line={"color": "rgba(255,255,255,0)"},
    hoverinfo="skip",
    name="pointwise Student-t 95% interval",
)
fig.add_vrect(x0=0, x1=5, fillcolor="orange", opacity=0.12, line_width=0)
fig.add_vline(x=0, line_dash="dash", line_color="black")
fig.update_layout(
    title="Synthetic announcement response with a pre-specified window",
    xaxis_title="Minutes relative to publication",
    yaxis_title="Return (basis points)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
この図の各minute intervalはpointwiseであり、31時点を同時に探索したfamily-wise uncertaintyではない。primary inferenceは事前指定した累積windowへ限定する。時点別profile、別window、surprise interactionはsecondary familyとして多重比較を管理する。

ここで許される結論は「この合成DGPで、指定windowに平均responseが観測された」である。実BOJ announcement responseでもなく、金融政策の因果効果でもない。
"""),
    md(r"""
## 8. BOJ Announcement Studyのpre-analysis specification

| 項目 | Coreで事前指定する内容 |
|---|---|
| event source | 個別の公式statement URLと取得時点。calendarだけを正確な公表時刻の代用にしない |
| timestamp | publication time、Asia/TokyoとUTC、precision、revision履歴 |
| primary windows | anticipationとresponseの境界、bar endpoint規約 |
| estimand | 対象instrument、return unit、event population、集計関数 |
| expectation / surprise | 市場予想のsource、cutoff、revision、欠損rule |
| contamination | overlapping eventとsimultaneous newsのdrop / flag / sensitivity rule |
| seasonality | event外の日から推定するminute-of-day adjustment |
| uncertainty | eventをsampling unitとし、依存に対応したSEまたはresampling |
| falsification | placebo date、far-pre window、negative-control asset / outcome |
| multiplicity | primary familyとsecondary family、FWERまたはFDR rule |
| claim class | announcement response。causal extensionは追加識別を要求 |

BOJのmeeting scheduleではstatement時刻が未定とされる場合がある。実データadapterでは個別statementのrelease metadataと保存時刻を照合し、market dataのfrequencyよりtimestampが粗い場合はwindowを広げるか分析を停止する。
"""),
    md(r"""
## 9. 失敗モード

- prediction accuracyやoptimizer successをconditional exchangeabilityの根拠にする
- measured covariateをすべてcontrolし、colliderやpost-treatment variableを開く
- propensity scoreの極端値とweight concentrationを報告しない
- matching、IPW、DRをunmeasured confoundingの自動修正とみなす
- pre-trend testが有意でないことをparallel trendsの証明とする
- anticipationで汚染された時点をevent-time referenceに使う
- financial announcement studyを識別戦略なしにcausal event studyと呼ぶ
- event windowを結果を見てから選び、primaryとsensitivityを混ぜる
- release dateだけを使い、timezone、時刻精度、bar規約を残さない
"""),
    md(r"""
## 10. 段階別演習

### 基礎

1. ATE、ATT、observed differenceをpotential outcomesで別々に定義せよ。
2. confounderとcolliderのDAGを描き、調整集合を説明せよ。
3. propensity分布とweight ESSをtreated / control別に報告せよ。

### 標準

4. outcome modelまたはpropensity modelだけを誤指定し、AIPWの有限標本挙動をreplicationで測れ。
5. anticipationの開始時点を変え、DiD estimateとevent-time pathの歪みを比較せよ。
6. financial announcementとcausal panel event studyのestimand、counterfactual、assumption、failure modeを対照表にせよ。

### 研究

7. hidden confoundingに対するsensitivity parameterを導入し、どの強さで結論が反転するか報告せよ。
8. staggered adoptionとheterogeneous treatment effectを生成し、naive TWFEとcohort-time ATTを比較せよ。
"""),
    md(r"""
## 11. Exit Criteria

- [ ] potential outcomes、ATE、consistency、exchangeability、overlapを定義できる
- [ ] associationからcausalityへ進むための識別仮定を列挙できる
- [ ] confounder conditioningとcollider conditioningの違いをDAGと反例で説明できる
- [ ] matching、IPW、outcome regression、doubly robust推定の役割と限界を説明できる
- [ ] parallel trendsとno anticipationを別々に検討できる
- [ ] financial announcement responseとcausal panel effectを区別できる
- [ ] timestamp、timezone、precision、primary windowを結果確認前に指定できる
- [ ] placebo、negative control、多重比較をpre-analysis planへ含められる
"""),
    md(r"""
## 12. 出典

- [Hernán and Robins, Causal Inference: What If](https://www.hsph.harvard.edu/miguel-hernan/wp-content/uploads/sites/1268/2024/04/hernanrobins_WhatIf_26apr24.pdf) — potential outcomes、exchangeability、positivity、IP weighting、standardization
- [Rosenbaum and Rubin, The Central Role of the Propensity Score in Observational Studies for Causal Effects](https://doi.org/10.1093/biomet/70.1.41) — propensity score、matching、observed covariate balance
- [Sant'Anna and Zhao, Doubly Robust Difference-in-Differences Estimators](https://arxiv.org/abs/1812.01723) — doubly robust DiDの原著論文
- [Callaway and Sant'Anna, Difference-in-Differences with Multiple Time Periods](https://arxiv.org/abs/1803.09015) — cohort-time ATTと複数時点DiD
- [Sun and Abraham, Estimating Dynamic Treatment Effects in Event Studies with Heterogeneous Treatment Effects](https://arxiv.org/abs/1804.05785) — staggered timingでのlead / lag contamination
- [MacKinlay, Event Studies in Economics and Finance](https://www.bu.edu/econ/files/2011/01/MacKinlay-1996-Event-Studies-in-Economics-and-Finance.pdf) — financial event studyの設計とabnormal return
- [Bank of Japan, Monetary Policy Meetings](https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm) — meeting、statement、minutesの公式索引
- [Bank of Japan, Release Schedule](https://www.boj.or.jp/en/about/calendar/index.htm) — 公式公表予定。個別eventの正確なtimestampは各release metadataで別途確認する

次章では、この境界をproject contractへ落とし、合成BOJ-like intraday dataでprimary analysis、seasonality、contamination rule、placebo、negative control、多重比較、claim auditを一体化する。
"""),
]
