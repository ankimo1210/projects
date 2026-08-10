"""Builder for notebook 17: the B3 honest announcement-study project."""

from nbkit import code, md

cells = [
    md(r"""
# 17. B3 Project — BOJ Announcement Study with Honest Inference

> primary window、event eligibility、timestamp精度、contamination ruleを先に固定し、支持されないcausal claimをclaim auditで止める。

## 学習目標

- seed固定の合成BOJ-like intraday dataから再現可能なevent-level datasetを作る
- publication timestamp、timezone、precision、bar endpointをdata contractにする
- intraday seasonalityをevent外の日だけから推定する
- overlap、simultaneous news、missing data、liquidityのprimary除外ruleを適用する
- effect sizeとevent-level intervalをprimary windowで報告する
- anticipation、placebo date、negative-control assetでfalsificationを行う
- secondary window familyへ多重比較補正を適用する
- announcement responseとcausal effectをclaim auditで分離する

## 前提知識

- Week 9のestimand、有限標本interval、model diagnostic
- Week 10のplacebo、permutation、多重比較とpre-specification
- Week 11のsampling unitとdependence-aware covariance
- Week 12のfinancial announcement studyとcausal event studyの境界
- pandasのtimezone-aware index、NumPy、SciPy、Plotly

## 重要な範囲制約

このNotebookは**実際のBOJ公表資料、実市場data、実政策surpriseを使用しない**。日付、return、news flag、liquidityはすべて教育用の合成値である。`BOJ-like`は分析契約を模したという意味であり、BOJの実証結果を表さない。
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy.stats import t as student_t

from quant_textbook.events import (
    ClaimMetadata,
    EventWindowSpecification,
    announcement_event_study,
    placebo_event_study,
)
from quant_textbook.resampling import benjamini_hochberg

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
NOTEBOOK_ID = 17
TASK_IDS = {
    "metadata": 1,
    "market_data": 2,
    "placebo_groups": 3,
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
## 1. Pre-analysis specification

data生成前に、primary estimandとanalysis ruleを固定する。

| Field | Primary specification |
|---|---|
| event source | synthetic registryのみ。実adapterは個別BOJ statement URLを要求 |
| event population | 合成eventのうちtimestamp・market coverage・quality ruleを満たすもの |
| instrument | 合成market instrumentのadditive log return、単位はbasis point |
| publication timezone | `Asia/Tokyo` |
| timestamp precision | 1分。1-minute barより細かい順序は主張しない |
| expected cadence | 1分。局所gapまたはwindow端の欠落はanalysis gateで除外 |
| anticipation window | $[-10,-1]$ 分、両端を含む |
| response window | $[0,5]$ 分、両端を含む |
| bar convention | timestampは1-minute intervalのstart label、event minuteから始まるbarをresponseへ含める |
| estimand | eligible eventにおけるseasonality-adjusted累積responseの平均 |
| expectation / surprise | primary平均では使わない。合成surpriseとの条件付き分析はsecondary。実adapterはsourceとcutoffを要求 |
| overlap rule | windowが重なるeventはerror。外部macro overlap flagはprimaryから除外 |
| simultaneous news | known simultaneous market-moving newsをprimaryから除外 |
| missing / liquidity | response欠損0、low-liquidity flagなしを要求 |
| uncertainty | eventをsampling unitとするStudent-$t$ interval |
| primary claim | 合成eventで観測されたannouncement response |
| disallowed claim | 実BOJ response、金融政策のcausal effect |

responseの6本のminute returnを独立な6観測としてSEへ入れない。window内をeventごとに先に集計し、独立性を仮定する単位をeventにする。
"""),
    code("""
PRIMARY_SPECIFICATION = EventWindowSpecification(
    anticipation_start="-10min",
    anticipation_end="-1min",
    response_start="0min",
    response_end="5min",
    timezone="Asia/Tokyo",
    timestamp_precision="1min",
    overlap_policy="error",
    simultaneous_news_rule="exclude known simultaneous market-moving news",
    estimand="mean seasonality-adjusted additive return in [0, 5] minutes among eligible synthetic events",
    claim_class="announcement-response",
    return_aggregation="sum",
    minimum_observations_per_window=6,
    expected_cadence="1min",
)

CLAIM_CONTRACT = ClaimMetadata(
    estimand=PRIMARY_SPECIFICATION.estimand,
    claim_class="announcement-response",
    counterfactual=None,
    identification_assumptions=(),
    causal_claim_supported=False,
    limitations=(
        "synthetic data only",
        "no exogenous policy-surprise design",
        "no causal counterfactual or control design",
        "event-level independence is an analysis approximation",
    ),
)
"""),
    md(r"""
## 2. 合成event registry

48件の合成announcement、120件のseasonality-training day、120件のplacebo-evaluation dayを別期間に作る。placebo自身のnoiseをseasonality fitへ入れてreference varianceを縮めないよう、trainingとevaluationを分割する。event timestampはtz-awareで、各eventは公式資料の代わりに`synthetic-event` IDを持つ。flagは互いに重ならないよう割り当て、除外理由を監査できるようにする。

実adapterでmeeting dateをpublication timestampとして代用してはいけない。BOJのmeeting一覧やrelease scheduleは候補eventの索引であり、正確な時刻は個別statementのrelease metadata、保存済み文書、market clockと照合する。
"""),
    code("""
metadata_rng = task_rng("metadata")
n_events = 48
event_times = pd.date_range(
    "2022-01-18 12:30",
    periods=n_events,
    freq="21D",
    tz="Asia/Tokyo",
)
seasonality_training_times = pd.date_range(
    "2017-01-10 12:30",
    periods=120,
    freq="7D",
    tz="Asia/Tokyo",
)
placebo_times = pd.date_range(
    "2019-07-09 12:30",
    periods=120,
    freq="7D",
    tz="Asia/Tokyo",
)

event_order = metadata_rng.permutation(n_events)
macro_overlap_flag = np.zeros(n_events, dtype=bool)
simultaneous_news_flag = np.zeros(n_events, dtype=bool)
low_liquidity_flag = np.zeros(n_events, dtype=bool)
missing_data_flag = np.zeros(n_events, dtype=bool)
macro_overlap_flag[event_order[:6]] = True
simultaneous_news_flag[event_order[6:11]] = True
low_liquidity_flag[event_order[11:15]] = True
missing_data_flag[event_order[15:18]] = True

event_metadata = pd.DataFrame(
    {
        "event_id": [f"SYN-MPM-{index + 1:03d}" for index in range(n_events)],
        "event_time": event_times,
        "source_class": "synthetic teaching event",
        "source_locator": [f"synthetic-event:{index + 1:03d}" for index in range(n_events)],
        "timestamp_precision_seconds": 60,
        "macro_overlap_flag": macro_overlap_flag,
        "simultaneous_news_flag": simultaneous_news_flag,
        "low_liquidity_flag": low_liquidity_flag,
        "missing_data_flag": missing_data_flag,
        "synthetic_surprise": metadata_rng.normal(size=n_events),
        "median_spread_bps": np.where(
            low_liquidity_flag,
            metadata_rng.uniform(2.8, 4.2, size=n_events),
            metadata_rng.uniform(0.5, 1.2, size=n_events),
        ),
    }
)
display(event_metadata.head(6))
"""),
    md(r"""
`synthetic_surprise`はDGPを作るlatent valueであり、実際の市場予想dataではない。primary analysisはresponseの平均だけを対象とし、surprise slopeは推定しない。実adapterでsurpriseを追加するなら、survey / futures等のsource、collection cutoff、revision、単位、missing ruleを別途事前指定する。
"""),
    md(r"""
## 3. Intraday data generatorとseasonality

各dayにrelative minute $-30$ から $30$ までの1-minute additive log returnを作る。seasonality-training dayとplacebo-evaluation dayは独立集合にし、announcement dayだけにresponse profileを加える。simultaneous-news、macro-overlap、low-liquidity eventには別のcontaminationを加える。

seasonalityは

$$
\widehat m(j)=\frac{1}{D_0}\sum_{d\in\text{control days}}r_{d,j},
\qquad
\widetilde r_{d,j}=r_{d,j}-\widehat m(j)
$$

とevent外の日だけで推定する。event responseをseasonalityのfitへ混ぜない。
"""),
    code("""
relative_minutes = np.arange(-30, 31)
response_mask = (relative_minutes >= 0) & (relative_minutes <= 5)
anticipation_mask = (relative_minutes >= -10) & (relative_minutes <= -1)
response_profile = np.array([0.34, 0.24, 0.17, 0.12, 0.08, 0.05])


def deterministic_seasonality(minutes):
    scaled = np.asarray(minutes, dtype=float) / 30.0
    return 0.025 + 0.030 * scaled**2 + 0.010 * np.sin(np.pi * scaled)


def ar_noise(rng, n_observations, scale, rho=0.28):
    innovations = rng.normal(scale=scale, size=n_observations)
    values = np.empty(n_observations)
    values[0] = innovations[0]
    for index in range(1, n_observations):
        values[index] = rho * values[index - 1] + innovations[index]
    return values


def day_frame(event_time, day_type, rng, metadata=None):
    timestamps = event_time + pd.to_timedelta(relative_minutes, unit="min")
    base = deterministic_seasonality(relative_minutes)
    main_scale = 0.22
    if metadata is not None and metadata["low_liquidity_flag"]:
        main_scale = 0.55
    main_return = base + ar_noise(rng, len(relative_minutes), main_scale)
    control_return = 0.5 * base + ar_noise(rng, len(relative_minutes), 0.18)

    if day_type == "announcement":
        response_size = 1.10 + 0.35 * metadata["synthetic_surprise"]
        main_return[response_mask] += response_size * response_profile
        if metadata["simultaneous_news_flag"]:
            main_return[response_mask] += 1.50 * response_profile[::-1]
            control_return[response_mask] += 0.80 * response_profile
        if metadata["macro_overlap_flag"]:
            main_return[anticipation_mask] += 0.08
            main_return[response_mask] -= 0.90 * response_profile
        if metadata["missing_data_flag"]:
            missing_positions = np.flatnonzero(response_mask)[[1, 4]]
            main_return[missing_positions] = np.nan

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "relative_minute": relative_minutes,
            "day_type": day_type,
            "event_id": metadata["event_id"] if metadata is not None else None,
            "main_return_bps": main_return,
            "negative_control_return_bps": control_return,
        }
    )


MARKET_DAY_CLASS_IDS = {
    "seasonality_training": 1,
    "placebo_evaluation": 2,
    "announcement": 3,
}
day_frames = []
for day_index, training_time in enumerate(seasonality_training_times):
    day_frames.append(
        day_frame(
            training_time,
            "seasonality_training",
            task_rng("market_data", MARKET_DAY_CLASS_IDS["seasonality_training"], day_index),
        )
    )
for day_index, placebo_time in enumerate(placebo_times):
    day_frames.append(
        day_frame(
            placebo_time,
            "placebo_evaluation",
            task_rng("market_data", MARKET_DAY_CLASS_IDS["placebo_evaluation"], day_index),
        )
    )
for day_index, (_, metadata) in enumerate(event_metadata.iterrows()):
    day_frames.append(
        day_frame(
            metadata["event_time"],
            "announcement",
            task_rng("market_data", MARKET_DAY_CLASS_IDS["announcement"], day_index),
            metadata,
        )
    )

intraday_data = (
    pd.concat(day_frames, ignore_index=True)
    .sort_values("timestamp")
    .reset_index(drop=True)
)

control_days = intraday_data["day_type"] == "seasonality_training"
main_seasonality = (
    intraday_data.loc[control_days]
    .groupby("relative_minute")["main_return_bps"]
    .mean()
)
negative_control_seasonality = (
    intraday_data.loc[control_days]
    .groupby("relative_minute")["negative_control_return_bps"]
    .mean()
)
intraday_data["main_adjusted_bps"] = (
    intraday_data["main_return_bps"]
    - intraday_data["relative_minute"].map(main_seasonality)
)
intraday_data["negative_control_adjusted_bps"] = (
    intraday_data["negative_control_return_bps"]
    - intraday_data["relative_minute"].map(negative_control_seasonality)
)
"""),
    code("""
fig = go.Figure()
fig.add_scatter(
    x=relative_minutes,
    y=deterministic_seasonality(relative_minutes),
    mode="lines",
    name="DGP seasonality oracle",
)
fig.add_scatter(
    x=main_seasonality.index,
    y=main_seasonality.values,
    mode="lines+markers",
    name="control-day estimate",
)
fig.update_layout(
    title="Seasonality is estimated without announcement days",
    xaxis_title="Minutes relative to the synthetic publication clock",
    yaxis_title="Mean one-minute return (basis points)",
    template="plotly_white",
)
fig.show()

seasonality_error = np.max(
    np.abs(main_seasonality.to_numpy() - deterministic_seasonality(relative_minutes))
)
print("maximum seasonality estimation error:", seasonality_error)
print("training days used for seasonality:", len(seasonality_training_times))
print("placebo evaluation days used for seasonality: 0")
print("announcement days used for seasonality: 0")
"""),
    md(r"""
oracleとの差はcontrol-day sampling errorである。実データではoracleは存在しないため、曜日、month-end、market regime、bar constructionを変えたsensitivityが必要になる。event dayを使わないことはlook-aheadとsignal leakageを防ぐ基本contractである。
"""),
    md(r"""
## 4. Data qualityとprimary eligibility

eventごとにresponse windowのmissing shareを実dataから計算し、metadata flagと照合する。primary ruleは次のすべてを要求する。

1. external macro overlapなし
2. known simultaneous market-moving newsなし
3. response window missing shareが0
4. low-liquidity flagなし

除外は結果の大きさを見て決めず、flagとquality thresholdだけで行う。
"""),
    code("""
response_rows = intraday_data[
    (intraday_data["day_type"] == "announcement")
    & intraday_data["relative_minute"].between(0, 5)
]
missing_share = (
    response_rows.groupby("event_id")["main_return_bps"]
    .apply(lambda values: values.isna().mean())
    .rename("response_missing_share")
)
event_metadata = event_metadata.merge(missing_share, on="event_id", how="left")
event_metadata["primary_eligible"] = ~(
    event_metadata["macro_overlap_flag"]
    | event_metadata["simultaneous_news_flag"]
    | event_metadata["low_liquidity_flag"]
    | (event_metadata["response_missing_share"] > 0.0)
)

eligibility_audit = pd.DataFrame(
    {
        "rule": [
            "total synthetic events",
            "macro overlap",
            "simultaneous news",
            "low liquidity",
            "response missingness",
            "primary eligible",
        ],
        "count": [
            len(event_metadata),
            event_metadata["macro_overlap_flag"].sum(),
            event_metadata["simultaneous_news_flag"].sum(),
            event_metadata["low_liquidity_flag"].sum(),
            (event_metadata["response_missing_share"] > 0.0).sum(),
            event_metadata["primary_eligible"].sum(),
        ],
    }
)
display(eligibility_audit)
"""),
    md(r"""
disjoint flagを使ったため、除外数の和とeligible数を照合できる。実registryでは複数理由が重なるため、reason別countとunique excluded event数を分けて報告する。
"""),
    md(r"""
## 5. Primary event study — effect sizeとinterval

共通APIはtz-awareでunique、sortedなreturn seriesを要求し、window endpoint、overlap、timestamp precisionを検査する。欠損eventはprimary event listへ入れない一方、除外履歴はregistryに残す。
"""),
    code("""
main_return_series = (
    intraday_data.dropna(subset=["main_adjusted_bps"])
    .set_index("timestamp")["main_adjusted_bps"]
    .sort_index()
)
negative_control_series = (
    intraday_data.set_index("timestamp")["negative_control_adjusted_bps"]
    .sort_index()
)
primary_event_times = pd.DatetimeIndex(
    event_metadata.loc[event_metadata["primary_eligible"], "event_time"]
)

primary_result = announcement_event_study(
    main_return_series,
    primary_event_times,
    PRIMARY_SPECIFICATION,
)
primary_event_responses = primary_result.event_responses.loc[
    primary_result.event_responses["included"].astype(bool)
]
response_standard_deviation = primary_event_responses["response"].std(ddof=1)
standardized_effect = primary_result.mean_response / response_standard_deviation
economic_threshold_bps = 0.50

primary_summary = pd.Series(
    {
        "eligible_events": primary_result.n_events,
        "mean_response_bps": primary_result.mean_response,
        "event_level_standard_error_bps": primary_result.response_standard_error,
        "ci_lower_bps": primary_result.confidence_interval[0],
        "ci_upper_bps": primary_result.confidence_interval[1],
        "standardized_mean_effect": standardized_effect,
        "mean_anticipation_bps": primary_result.mean_anticipation_response,
        "ci_excludes_zero": primary_result.confidence_interval[0] > 0.0
        or primary_result.confidence_interval[1] < 0.0,
        "economic_threshold_bps": economic_threshold_bps,
        "mean_exceeds_economic_threshold": primary_result.mean_response >= economic_threshold_bps,
        "ci_entirely_above_economic_threshold": primary_result.confidence_interval[0]
        >= economic_threshold_bps,
        "timestamp_precision_sufficient": primary_result.diagnostics.timestamp_precision_sufficient,
    },
    name="primary analysis",
)
display(primary_summary.to_frame())
"""),
    code("""
response_values = primary_event_responses["response"].to_numpy(dtype=float)
counts, edges = np.histogram(response_values, bins=18)
centers = 0.5 * (edges[1:] + edges[:-1])
fig = go.Figure()
fig.add_bar(
    x=centers,
    y=counts,
    width=np.diff(edges),
    name="eligible event responses",
)
fig.add_vline(
    x=primary_result.mean_response,
    line_color="black",
    line_width=3,
    annotation_text="mean",
)
fig.add_vrect(
    x0=primary_result.confidence_interval[0],
    x1=primary_result.confidence_interval[1],
    fillcolor="orange",
    opacity=0.18,
    line_width=0,
    annotation_text="95% interval for mean",
)
fig.update_layout(
    title="Primary response is summarized at the event level",
    xaxis_title="Cumulative adjusted response (basis points)",
    yaxis_title="Event count",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
intervalはeligible event populationからのsampling approximationだけを表す。timestamp error、source omission、seasonality model、simultaneous-news misclassification、policy endogeneity、instrument selectionを含まない。statistical significanceとeconomic thresholdの判定も別々に報告する。
"""),
    md(r"""
## 6. Timestamp precision stress test

primary precisionは1分でmedian data frequencyと同じである。仮にsourceが「数分程度」しか分からず5分精度なら、1-minute barを使えてもevent alignmentは5分より細かく識別できない。
"""),
    code("""
coarse_timestamp_specification = EventWindowSpecification(
    anticipation_start="-10min",
    anticipation_end="-1min",
    response_start="0min",
    response_end="5min",
    timezone="Asia/Tokyo",
    timestamp_precision="5min",
    overlap_policy="error",
    simultaneous_news_rule="exclude known simultaneous market-moving news",
    estimand="precision stress test only",
    claim_class="announcement-response",
    return_aggregation="sum",
    minimum_observations_per_window=6,
    expected_cadence="1min",
)
coarse_precision_result = announcement_event_study(
    main_return_series,
    primary_event_times,
    coarse_timestamp_specification,
)
precision_audit = pd.DataFrame(
    {
        "specification": ["primary 1-minute precision", "coarse 5-minute precision"],
        "timestamp_precision": [
            PRIMARY_SPECIFICATION.timestamp_precision,
            coarse_timestamp_specification.timestamp_precision,
        ],
        "median_data_frequency": [
            primary_result.diagnostics.median_data_frequency,
            coarse_precision_result.diagnostics.median_data_frequency,
        ],
        "precision_sufficient": [
            primary_result.diagnostics.timestamp_precision_sufficient,
            coarse_precision_result.diagnostics.timestamp_precision_sufficient,
        ],
    }
)
display(precision_audit)
"""),
    md(r"""
coarse caseのestimateが数値上同じでも、解釈可能な時間分解能は同じではない。precision warningはestimateを機械的に補正するものではなく、window変更または分析停止を促すgateである。
"""),
    md(r"""
## 7. Contamination sensitivity

primaryから除外したmacro overlapとsimultaneous newsを段階的に戻す。これはprimaryの定義変更ではなく、除外ruleが結果へ与える感度を示すsecondary analysisである。missingとlow-liquidity eventは全仕様で除外する。
"""),
    code("""
base_quality = ~(
    event_metadata["low_liquidity_flag"]
    | (event_metadata["response_missing_share"] > 0.0)
)
contamination_contracts = {
    "primary: exclude both": {
        "mask": event_metadata["primary_eligible"],
        "specification": PRIMARY_SPECIFICATION,
        "claim": CLAIM_CONTRACT,
    },
    "secondary: include macro overlap": {
        "mask": base_quality & ~event_metadata["simultaneous_news_flag"],
        "simultaneous_news_rule": (
            "exclude simultaneous news; include macro overlaps only for secondary sensitivity"
        ),
        "estimand": (
            "secondary mean adjusted return including pre-labeled macro-overlap events"
        ),
    },
    "secondary: include all known contamination": {
        "mask": base_quality,
        "simultaneous_news_rule": (
            "include simultaneous news and macro overlaps only for secondary sensitivity"
        ),
        "estimand": (
            "secondary mean adjusted return including all pre-labeled contamination"
        ),
    },
}
contamination_rows = []
for label, contract in contamination_contracts.items():
    if "specification" in contract:
        specification = contract["specification"]
        claim = contract["claim"]
    else:
        specification = EventWindowSpecification(
            anticipation_start="-10min",
            anticipation_end="-1min",
            response_start="0min",
            response_end="5min",
            timezone="Asia/Tokyo",
            timestamp_precision="1min",
            overlap_policy="error",
            simultaneous_news_rule=contract["simultaneous_news_rule"],
            estimand=contract["estimand"],
            claim_class="announcement-response",
            return_aggregation="sum",
            minimum_observations_per_window=6,
            expected_cadence="1min",
        )
        claim = ClaimMetadata(
            estimand=specification.estimand,
            claim_class="announcement-response",
            counterfactual=None,
            identification_assumptions=(),
            causal_claim_supported=False,
            limitations=(
                "secondary contamination sensitivity",
                "not the primary event population",
                "synthetic data only",
                "no causal identification",
            ),
        )
    analysis_times = pd.DatetimeIndex(event_metadata.loc[contract["mask"], "event_time"])
    result = announcement_event_study(
        main_return_series,
        analysis_times,
        specification,
    )
    contamination_rows.append(
        {
            "analysis": label,
            "n_events": result.n_events,
            "mean_response_bps": result.mean_response,
            "ci_lower_bps": result.confidence_interval[0],
            "ci_upper_bps": result.confidence_interval[1],
            "estimand": result.estimand,
            "simultaneous_news_rule": result.specification.simultaneous_news_rule,
            "claim_class": claim.claim_class,
            "causal_claim_supported": claim.causal_claim_supported,
        }
    )
contamination_sensitivity = pd.DataFrame(contamination_rows)
display(contamination_sensitivity.round(4))
"""),
    md(r"""
contaminated eventを含めた推定値が変わることは、どちらが「真の政策効果」かを教えない。primary ruleを守り、除外した母集団へのresponseとして解釈する。除外が多い場合はexternal validityとselectionもfailure modeとして残す。
"""),
    md(r"""
## 8. Placebo datesとnegative control

placebo dateには同じtimezone、同じclock time、同じwindow、同じseasonality adjustmentを適用する。negative-control assetは合成DGPでpolicy responseを入れていない別seriesである。

placeboのvalidityは「eventがない」だけでなく、曜日、market regime、volatility、他のannouncementの分布がprimary eventと比較可能かに依存する。ここでは合成control dayなので、その設計も既知である。
"""),
    code("""
placebo_result = placebo_event_study(
    main_return_series,
    placebo_times,
    PRIMARY_SPECIFICATION,
    observed_response=primary_result.mean_response,
)
negative_control_result = announcement_event_study(
    negative_control_series,
    primary_event_times,
    PRIMARY_SPECIFICATION,
)

placebo_event_values = placebo_result.event_study.event_responses.loc[
    placebo_result.event_study.event_responses["included"].astype(bool),
    "response",
].to_numpy(dtype=float)
placebo_group_rng = task_rng("placebo_groups")
n_placebo_replications = 2_000
placebo_group_means = np.empty(n_placebo_replications)
for replication in range(n_placebo_replications):
    sampled = placebo_group_rng.choice(
        placebo_event_values,
        size=primary_result.n_events,
        replace=False,
    )
    placebo_group_means[replication] = sampled.mean()
group_exceedances = np.count_nonzero(
    np.abs(placebo_group_means) >= abs(primary_result.mean_response)
)
group_placebo_p_value = (group_exceedances + 1.0) / (n_placebo_replications + 1.0)

anticipation_values = primary_event_responses["anticipation_response"].to_numpy(dtype=float)
anticipation_standard_error = anticipation_values.std(ddof=1) / np.sqrt(anticipation_values.size)
anticipation_critical_value = student_t.ppf(0.975, anticipation_values.size - 1)
anticipation_half_width = anticipation_critical_value * anticipation_standard_error
anticipation_interval = (
    primary_result.mean_anticipation_response - anticipation_half_width,
    primary_result.mean_anticipation_response + anticipation_half_width,
)
timing_isolation_warning = not (
    anticipation_interval[0] <= 0.0 <= anticipation_interval[1]
)
placebo_group_interval = np.quantile(placebo_group_means, [0.025, 0.975])

falsification_summary = pd.DataFrame(
    {
        "diagnostic": [
            "anticipation window",
            "individual placebo-window reference",
            "matched-size placebo-group reference",
            "negative-control asset response",
        ],
        "estimate_bps": [
            primary_result.mean_anticipation_response,
            placebo_result.event_study.mean_response,
            placebo_group_means.mean(),
            negative_control_result.mean_response,
        ],
        "reference_lower_bps": [
            anticipation_interval[0],
            placebo_result.event_study.confidence_interval[0],
            placebo_group_interval[0],
            negative_control_result.confidence_interval[0],
        ],
        "reference_upper_bps": [
            anticipation_interval[1],
            placebo_result.event_study.confidence_interval[1],
            placebo_group_interval[1],
            negative_control_result.confidence_interval[1],
        ],
        "reference_p_value": [
            np.nan,
            placebo_result.empirical_two_sided_p_value,
            group_placebo_p_value,
            np.nan,
        ],
        "design_flag": [
            "warning: interval excludes zero" if timing_isolation_warning else "no interval flag",
            "reference diagnostic",
            "reference diagnostic",
            "reference diagnostic",
        ],
    }
)
display(falsification_summary.round(4))
"""),
    code("""
placebo_counts, placebo_edges = np.histogram(placebo_group_means, bins=36, density=True)
placebo_centers = 0.5 * (placebo_edges[1:] + placebo_edges[:-1])
fig = go.Figure()
fig.add_bar(
    x=placebo_centers,
    y=placebo_counts,
    width=np.diff(placebo_edges),
    name="matched-size placebo group means",
)
fig.add_vline(
    x=primary_result.mean_response,
    line_color="red",
    line_width=3,
    annotation_text="primary mean",
)
fig.update_layout(
    title="Placebo comparison preserves the number of event-level units",
    xaxis_title="Mean adjusted response (basis points)",
    yaxis_title="Density",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
共通APIのplus-one p-valueはprimary meanを**個々の**placebo window分布と比較する監査値である。追加したmatched-size distributionはprimaryと同じevent数の平均を比較する。reference statisticとsampling ruleを明記せず、どちらか都合のよいp-valueだけを選ばない。

表のintervalも対象が異なる。anticipation、個別placebo平均、negative-control平均はevent-level Student-$t$ interval、matched-size placeboはgroup mean reference distributionの2.5% / 97.5% quantileである。

placeboやnegative controlが通ってもcausal identificationの証明にはならない。失敗すればdesignの警告になり、通れば検出できた特定のfailure modeを弱めるだけである。anticipation intervalが0を含まない場合もprimary windowのdescriptive responseは計算できるが、発表後だけに分離されたresponseという解釈はqualifiedとし、claim auditへ引き継ぐ。
"""),
    md(r"""
## 9. Secondary windowsと多重比較

primary $[0,5]$ は単一の事前指定testとして保持する。次のalternative windowsはすべてsecondary familyとし、unadjusted p-valueとBenjamini–Hochberg FDR-adjusted p-valueを併記する。windowを増やした後でprimaryへ昇格させない。

共通APIのminimum observationはanticipation / responseに共通のscalarなので、短い方をAPI gateへ渡した後、tableの実観測本数がanticipationで10、responseで2 / 4 / 11 / 16 / 31に完全一致することを明示的に検査する。不完全windowを黙って許さない。
"""),
    code("""
secondary_windows = [
    ("secondary [0, 1]", "0min", "1min", 2),
    ("secondary [0, 3]", "0min", "3min", 4),
    ("secondary [0, 10]", "0min", "10min", 11),
    ("secondary [0, 15]", "0min", "15min", 16),
    ("secondary [0, 30]", "0min", "30min", 31),
]
secondary_rows = []
for label, response_start, response_end, minimum_observations in secondary_windows:
    specification = EventWindowSpecification(
        anticipation_start="-10min",
        anticipation_end="-1min",
        response_start=response_start,
        response_end=response_end,
        timezone="Asia/Tokyo",
        timestamp_precision="1min",
        overlap_policy="error",
        simultaneous_news_rule="exclude known simultaneous market-moving news",
        estimand=f"secondary mean adjusted return in [{response_start}, {response_end}]",
        claim_class="announcement-response",
        return_aggregation="sum",
        minimum_observations_per_window=min(minimum_observations, 10),
        expected_cadence="1min",
    )
    result = announcement_event_study(
        main_return_series,
        primary_event_times,
        specification,
    )
    included_responses = result.event_responses.loc[
        result.event_responses["included"].astype(bool)
    ]
    if not included_responses["response_observations"].eq(minimum_observations).all():
        raise RuntimeError("secondary response window has incomplete market coverage")
    if not included_responses["anticipation_observations"].eq(10).all():
        raise RuntimeError("secondary anticipation window has incomplete market coverage")
    t_statistic = result.mean_response / result.response_standard_error
    p_value = 2.0 * student_t.sf(abs(t_statistic), result.confidence_degrees_of_freedom)
    confidence_half_width = result.confidence_interval[1] - result.mean_response
    secondary_rows.append(
        {
            "analysis": label,
            "anticipation_window": "[-10, -1]",
            "required_observations_per_window": minimum_observations,
            "mean_response_bps": result.mean_response,
            "standard_error_bps": result.response_standard_error,
            "student_t_confidence_half_width_bps": confidence_half_width,
            "unadjusted_p_value": p_value,
        }
    )

secondary_results = pd.DataFrame(secondary_rows)
fdr_result = benjamini_hochberg(
    secondary_results["unadjusted_p_value"].to_numpy(),
    alpha=0.05,
)
secondary_results["BH_adjusted_p_value"] = fdr_result.adjusted_p_values
secondary_results["BH_reject"] = fdr_result.rejected
display(secondary_results.round(5))
"""),
    code("""
fig = go.Figure()
fig.add_scatter(
    x=secondary_results["analysis"],
    y=secondary_results["mean_response_bps"],
    error_y={
        "type": "data",
        "array": secondary_results["student_t_confidence_half_width_bps"],
        "visible": True,
    },
    mode="markers",
    name="secondary estimates with pointwise Student-t intervals",
)
fig.add_hline(y=0.0, line_dash="dash", line_color="black")
fig.update_layout(
    title="Alternative windows remain a labeled secondary family",
    xaxis_title="Window",
    yaxis_title="Mean adjusted response (basis points)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
図のintervalはpointwiseで、family-wide intervalではない。BHはFDRを対象とし、effect sizeやeconomic significanceを作る手続きではない。confirmatory familyでFWERが必要ならHolm / Bonferroni等を事前指定する。
"""),
    md(r"""
## 10. Claim audit

数値結果と主張の強さを分離する。`ClaimMetadata`はcausal counterfactualと識別仮定がない状態でcausal supportを`True`にできない。
"""),
    code("""
primary_response_supported = primary_result.confidence_interval[0] > 0.0
claim_audit = pd.DataFrame(
    [
        {
            "candidate_claim": "Eligible synthetic events have a positive mean response in the primary window",
            "status": (
                "not supported by the primary interval"
                if not primary_response_supported
                else (
                    "supported descriptively; timing interpretation qualified"
                    if timing_isolation_warning
                    else "supported within the synthetic experiment"
                )
            ),
            "reason": (
                "the pre-specified primary interval does not establish a positive response"
                if not primary_response_supported
                else (
                    "primary interval excludes zero, but the anticipation interval also excludes zero"
                    if timing_isolation_warning
                    else "pre-specified event-level estimate and interval"
                )
            ),
        },
        {
            "candidate_claim": "The response is isolated to the post-publication window",
            "status": (
                "not supported by the anticipation diagnostic"
                if timing_isolation_warning
                else "not contradicted by the anticipation diagnostic"
            ),
            "reason": (
                "the anticipation interval excludes zero"
                if timing_isolation_warning
                else "the anticipation interval includes zero; this is not proof of isolation"
            ),
        },
        {
            "candidate_claim": "The result is economically material under the pre-specified 0.50 bp threshold",
            "status": "evaluate from reported effect size",
            "reason": "economic threshold is separate from statistical significance",
        },
        {
            "candidate_claim": "Actual BOJ announcements produced this response",
            "status": "not supported",
            "reason": "no real BOJ or market data were used",
        },
        {
            "candidate_claim": "Monetary policy causally changed market prices",
            "status": "not supported",
            "reason": "no causal counterfactual, exogenous surprise, or valid control design",
        },
        {
            "candidate_claim": "Placebos prove causal identification",
            "status": "not supported",
            "reason": "falsification checks address selected failure modes only",
        },
    ]
)
display(claim_audit)
print("claim class:", CLAIM_CONTRACT.claim_class)
print("causal claim supported:", CLAIM_CONTRACT.causal_claim_supported)
print("limitations:", CLAIM_CONTRACT.limitations)
"""),
    md(r"""
causal extensionはAdvancedである。実施するなら、policy surpriseが事前予想に対して外生とみなせる根拠、surprise測定誤差、同時information、instrumentのexclusion、または妥当なcontrol designとcounterfactualを明示する。windowを短くしただけではcausal identificationにならない。
"""),
    md(r"""
## 11. 実BOJ data adapter requirements

このMVPはdownloadを行わない。実adapterを追加するときは、少なくとも次のschemaとvalidationを満たす。

| Field | Required validation |
|---|---|
| `event_id` | meetingとstatement versionに対してstable、重複なし |
| `official_document_url` | BOJの個別statement / release。calendar indexだけにしない |
| `publication_time_local` | tz-aware `Asia/Tokyo`、日付だけは禁止 |
| `publication_time_utc` | local timestampとの一意な変換を照合 |
| `timestamp_precision` | second / minute / unknownを明示。market frequencyとのcompatibility gate |
| `release_version` | correction、replacement、retrieved-at、content hash |
| `meeting_start_end` | publication timeと混同しない |
| `market_source` | vendor、license、instrument、venue、timezone、trading calendar |
| `bar_contract` | open / close label、interval境界、quote / trade、stale-price rule |
| `expectation_source` | survey / futures等、cutoff、revision、unit、missing rule |
| `other_news` | macro calendar、speech、disaster等の同時news classification |
| `liquidity` | spread、volume、stale bar、halt、missingness |

ライセンスが再配布を許さないmarket dataはrepositoryへ含めず、取得手順、hash、local path contractだけを残す。timestamp precisionがprimary frequencyより粗い場合は、windowを事前規則で広げるか分析を停止する。
"""),
    md(r"""
## 12. Reproducibilityとvalidation matrix

| Contract | Check |
|---|---|
| RNG | root seed、Notebook ID、named task ID、day class、indexを保存 |
| source class | 全eventがsyntheticと明記 |
| timestamp | tz-aware、unique、sorted、precision gate |
| seasonality | control dayだけでfit |
| primary eligibility | flagとmissingnessから決定、response値を使わない |
| sampling unit | event-level response数とeligible event数が一致 |
| window | inclusive endpointと観測本数を検査 |
| falsification | anticipation、placebo date、negative-control asset |
| multiplicity | primary単独、secondary familyへ補正 |
| claim | announcement-response、causal supportはFalse |
"""),
    code("""
assert event_metadata["source_class"].eq("synthetic teaching event").all()
assert len(seasonality_training_times.intersection(placebo_times)) == 0
assert event_metadata.loc[event_metadata["primary_eligible"], "macro_overlap_flag"].sum() == 0
assert event_metadata.loc[event_metadata["primary_eligible"], "simultaneous_news_flag"].sum() == 0
assert event_metadata.loc[event_metadata["primary_eligible"], "low_liquidity_flag"].sum() == 0
assert event_metadata.loc[event_metadata["primary_eligible"], "response_missing_share"].sum() == 0.0
assert primary_result.n_events == int(event_metadata["primary_eligible"].sum())
assert primary_event_responses["response_observations"].eq(6).all()
assert primary_event_responses["anticipation_observations"].eq(10).all()
assert primary_result.diagnostics.timestamp_precision_sufficient
assert not coarse_precision_result.diagnostics.timestamp_precision_sufficient
assert not CLAIM_CONTRACT.causal_claim_supported
assert CLAIM_CONTRACT.claim_class == "announcement-response"
print("all project contract checks passed")
"""),
    md(r"""
## 13. Block成果物と採点check

| 成果物 | このNotebookでの対応 | 提出時の追加物 |
|---|---|---|
| derivation note | event estimand、seasonality、event-level interval | 仮定と式を独立した短いnoteへ整理 |
| implementation + tests | events API、timestamp / overlap / claim contract | unit testとedge-case test |
| experiment | baseline、contamination、placebo、negative control、multiplicity | run manifestとenvironment lock |
| technical memo | claim auditとfailure modes | 2〜4ページでquestion、method、result、failure、conclusion |

B3の配点は数学25、実装・test 30、実験設計30、説明・memo 15、合格点75/100である。4成果物と必須Exit Criteriaの両方を満たす必要がある。
"""),
    md(r"""
## 14. 失敗モード

- synthetic resultを実BOJ empirical resultとして記述する
- meeting date、statement publication、press conferenceを同じevent timeにする
- timezone-naive timestampをmarket seriesへ暗黙にmergeする
- timestamp precisionより細かいbarでprice discovery順序を主張する
- event returnを使ってintraday seasonalityをfitする
- overlapやsimultaneous newsをresponseの符号を見て除外する
- minute barを独立sampleとしてevent-level SEを過小評価する
- alternative windowから最も有意なものをprimaryと呼び直す
- placeboやnegative controlの成功をcausal proofと呼ぶ
- effect size、interval、economic thresholdをp-valueだけで置き換える
- excluded eventとmissing / liquidity diagnosticを報告しない
"""),
    md(r"""
## 15. 段階別演習

### 基礎

1. primary specificationをYAMLへ保存し、Notebook内の値と照合せよ。
2. event-level responseを手計算し、共通APIのinclusive endpointと一致させよ。
3. timestampをUTCへ変換して再実行し、同じeventを指すことを確認せよ。

### 標準

4. seasonality fitを曜日別にし、primary estimateの変化をsecondaryとして報告せよ。
5. simultaneous-news classifierにmisclassificationを加え、claimの頑健性を調べよ。
6. placebo dateをweekday・volatility regimeでmatchし、無条件placeboと比較せよ。

### 研究

7. 事前に定義したmarket-expectation proxyを追加し、surprise-response slopeのmeasurement errorを評価せよ。
8. 秒精度sourceと複数instrumentを持つ場合だけ、明示的なidentification strategyを立ててcausal extensionを提案せよ。
"""),
    md(r"""
## 16. Exit Criteria

### Core必須

- [ ] official source URL、publication timestamp、timezone、precisionのadapter contractを定義できる
- [ ] primary anticipation / response windowとbar endpointを結果確認前に固定できる
- [ ] overlap、simultaneous news、missing、liquidityのruleを監査表で示せる
- [ ] intraday seasonalityをevent外dataだけから推定できる
- [ ] eventをsampling unitとしてeffect size、SE、intervalを報告できる
- [ ] primaryとsecondary sensitivityを分離できる
- [ ] placebo date、negative control、多重比較補正を実装できる
- [ ] timestamp precisionがdata frequencyに十分かgateを作れる
- [ ] synthetic result、actual BOJ response、causal policy effectを区別できる
- [ ] 2〜4ページmemoでfailure modeとclaim auditを説明できる

### Advanced（任意）

- [ ] 明示的なsurprise measureとcounterfactualを追加し、追加識別仮定を監査できる
- [ ] dependent event、multi-instrument family、microstructure noiseに対応した推論を設計できる
"""),
    md(r"""
## 17. 出典

- [Bank of Japan, Monetary Policy Meetings](https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm) — meeting、statement、Summary of Opinions、minutesの公式索引
- [Bank of Japan, Release Schedule](https://www.boj.or.jp/en/about/calendar/index.htm) — 公式公表予定。実adapterでは個別release metadataでtimestampを確定する
- [Bank of Japan, Outline of Monetary Policy](https://www.boj.or.jp/en/mopo/outline/index.htm) — MPM decisionと公表の制度的背景
- [MacKinlay, Event Studies in Economics and Finance](https://www.bu.edu/econ/files/2011/01/MacKinlay-1996-Event-Studies-in-Economics-and-Finance.pdf) — financial event study、event window、abnormal return
- [Hernán and Robins, Causal Inference: What If](https://www.hsph.harvard.edu/miguel-hernan/wp-content/uploads/sites/1268/2024/04/hernanrobins_WhatIf_26apr24.pdf) — counterfactual、識別、causal claimの条件
- [Callaway and Sant'Anna, Difference-in-Differences with Multiple Time Periods](https://arxiv.org/abs/1803.09015) — causal panel event studyでのcohort-time ATT
- [Sun and Abraham, Estimating Dynamic Treatment Effects in Event Studies with Heterogeneous Treatment Effects](https://arxiv.org/abs/1804.05785) — staggered adoptionとheterogeneous effectsの注意
- [Bertrand, Duflo, and Mullainathan, How Much Should We Trust Differences-In-Differences Estimates?](https://economics.mit.edu/sites/default/files/2022-08/How%20Much%20Should%20We%20Trust%20Differences%20in%20Difference.pdf) — serial dependenceと推論

B3の既定結論はannouncement responseまでである。追加識別なしに金融政策のcausal effectとは呼ばない。この境界を守ることが、手法の複雑さより先に満たすべきprojectの品質基準になる。
"""),
]
