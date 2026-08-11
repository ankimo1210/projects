"""Builder for notebook 34: Week 24 shift and conformal evaluation."""

from nbkit import code, md
from stage2_nb import setup_cell, treasury_cell

cells = [
    md(r"""
# 34. Week 24 — Distribution shift、nested evaluation、conformal境界

> intervalを計算できることと、そのcoverage theoremの仮定が成り立つことは別である。

## 学習目標

- inner selectionとouter evaluationを分離できる
- grouped split、purging、embargoの必要条件をdata grainとlabel intervalから判断できる
- feature driftとperformance driftを別々に測れる
- split-conformal intervalをfinite-sample rankで構成できる
- exchangeabilityを依存時系列へ無条件に仮定しない

## 前提知識

- B5のtemporal validation
- quantileとcoverage
- Week 21–23のmodel familyとregime diagnostic
"""),
    setup_cell(34),
    treasury_cell(),
    md(r"""
## 1. Nested temporal protocol

outer testを最後に固定する。alphaはproper-training候補期間のinner train/selectionだけで選び、
その後にproper trainingへfitする。外側のvalidation partitionはconformal calibration専用に残す。

### Group、purge、embargoは別の漏洩経路を閉じる

| guard | 閉じる経路 | このTreasury表での判断 |
|---|---|---|
| grouped split | 同じ企業・患者・instrument familyが両foldへ入る | 1日1本の公式curveでentity groupが無いため不適用 |
| purge | training labelの終了がselection prediction時点へ重なる | 1-publication先targetなので境界から1行を除外 |
| embargo | label終了後もfeature/反応が持続し隣接foldを汚す | 現Core targetでは追加0行。経済的持続を仮定するなら事前に正の幅を固定 |

grouped splitを日付splitの代わりにせず、panelならgroupとtimeの両方を守る。embargoを「念のため」の調整parameterにせず、holding period、label overlap、feature lookbackから単位付きで決める。
"""),
    code("""
split = qt.chronological_split(len(forecast.regression_target), gap=1)
features = forecast.features
target = forecast.regression_target

inner_boundary = int(np.floor(0.8 * split.train.size))
naive_inner_training = split.train[:inner_boundary]
inner_selection = split.train[inner_boundary:]
selection_information_start = forecast.prediction_dates[inner_selection[0]]
inner_training = naive_inner_training[
    forecast.target_dates[naive_inner_training] < selection_information_start
]
purged_rows = np.setdiff1d(naive_inner_training, inner_training)
embargo_publications = 0
assert (
    forecast.target_dates[inner_training[-1]]
    < forecast.prediction_dates[inner_selection[0]]
)
assert purged_rows.size == forecast.horizon_publications

split_guard_table = pd.DataFrame(
    [
        {
            "guard": "grouped split",
            "rows_removed": 0,
            "applied": False,
            "reason": "single official curve per date; no entity group",
        },
        {
            "guard": "target-horizon purge",
            "rows_removed": purged_rows.size,
            "applied": True,
            "reason": "training label must end before selection information time",
        },
        {
            "guard": "additional embargo",
            "rows_removed": embargo_publications,
            "applied": False,
            "reason": "no extra persistence assumed beyond one-publication label",
        },
    ]
)
display(split_guard_table)

alpha_grid = [0.1, 1.0, 10.0, 100.0]
inner_rows = []
for alpha in alpha_grid:
    model = qt.fit_ridge(features[inner_training], target[inner_training], alpha=alpha)
    metric = qt.regression_metrics(
        target[inner_selection],
        model.predict(features[inner_selection]),
    )
    inner_rows.append({"alpha": alpha, "inner_validation_rmse_bp": metric.rmse})
inner_table = pd.DataFrame(inner_rows)
selected_alpha = float(inner_table.loc[inner_table["inner_validation_rmse_bp"].idxmin(), "alpha"])
display(inner_table)
print("selected alpha before outer test:", selected_alpha)
print("inner train / selection rows:", len(inner_training), len(inner_selection))
print("purged boundary rows:", purged_rows.tolist())
"""),
    md(r"""
## 2. Feature drift

standardized mean differenceはlocation shift、population stability index（PSI）はreference quantile binのshare shiftを見る。閾値は普遍的な合否ではなく、追加診断のsignalである。
"""),
    code("""
drift = qt.feature_drift_report(
    features[split.train],
    features[split.test],
    feature_names=forecast.feature_names,
)
drift_table = pd.DataFrame(
    {
        "feature": drift.feature_names,
        "standardized_mean_difference": drift.standardized_mean_difference,
        "psi": drift.population_stability_index,
    }
).sort_values("psi", ascending=False)
display(drift_table.head(10))

fig = go.Figure(
    go.Scatter(
        x=drift_table["standardized_mean_difference"],
        y=drift_table["psi"],
        mode="markers+text",
        text=drift_table["feature"],
        textposition="top center",
    )
)
fig.update_layout(
    title="Train-to-test feature drift diagnostics",
    xaxis_title="Standardized mean difference",
    yaxis_title="Population stability index",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 3. Split conformal interval

calibration residual $R_i=|Y_i-\hat f(X_i)|$ の有限標本higher quantileを使う。
$\hat f$ はproper trainingだけで一度fitし、calibration outcomeをrefitへ戻さない。
calibration rowsとtest rowsがexchangeableならmarginal coverage保証が得られるが、金融時系列では依存とshiftがある。ここではintervalを計算し、保証ではなくperiod別empirical coverageとerror driftを報告する。

calibration sizeを $n$、miscoverageを $\alpha$ とすると、sorted residualの

$$
k=\min\left\{\left\lceil(n+1)(1-\alpha)\right\rceil,n\right\}
$$

番目をhalf-widthにする。このrank correctionもexchangeabilityを置いたときのものである。
"""),
    code("""
conformal_model = qt.fit_ridge(
    features[split.train],
    target[split.train],
    alpha=selected_alpha,
)
validation_prediction = conformal_model.predict(features[split.validation])
test_prediction = conformal_model.predict(features[split.test])
interval = qt.split_conformal_interval(
    target[split.validation],
    validation_prediction,
    test_prediction,
    miscoverage=0.1,
)
covered = (target[split.test] >= interval.lower) & (target[split.test] <= interval.upper)
interval_summary = pd.DataFrame(
    {
        "nominal_coverage": [interval.nominal_coverage],
        "empirical_coverage": [covered.mean()],
        "mean_width_bp": [np.mean(interval.upper - interval.lower)],
        "residual_quantile_bp": [interval.residual_quantile],
        "exchangeability_verified": [False],
    }
)
display(interval_summary)

period_rows = []
for period_name, period_indices in [
    ("test_first_half", split.test[: split.test.size // 2]),
    ("test_second_half", split.test[split.test.size // 2 :]),
]:
    local_prediction = conformal_model.predict(features[period_indices])
    local_position = np.searchsorted(split.test, period_indices)
    local_covered = (
        (target[period_indices] >= interval.lower[local_position])
        & (target[period_indices] <= interval.upper[local_position])
    )
    ridge_metric = qt.regression_metrics(target[period_indices], local_prediction)
    zero_metric = qt.regression_metrics(
        target[period_indices],
        np.zeros(period_indices.size),
    )
    period_rows.append(
        {
            "period": period_name,
            "rows": period_indices.size,
            "ridge_rmse_bp": ridge_metric.rmse,
            "zero_rmse_bp": zero_metric.rmse,
            "empirical_coverage": local_covered.mean(),
        }
    )
performance_drift_table = pd.DataFrame(period_rows)
display(performance_drift_table)
"""),
    code("""
display_indices = np.arange(min(120, split.test.size))
dates = pd.to_datetime(forecast.prediction_dates[split.test][display_indices])
fig = go.Figure()
fig.add_scatter(
    x=np.r_[dates, dates[::-1]],
    y=np.r_[interval.upper[display_indices], interval.lower[display_indices][::-1]],
    fill="toself",
    line={"color": "rgba(0,0,0,0)"},
    fillcolor="rgba(245,133,24,0.2)",
    name="split-conformal interval",
)
fig.add_scatter(x=dates, y=test_prediction[display_indices], name="ridge", mode="lines")
fig.add_scatter(
    x=dates,
    y=target[split.test][display_indices],
    name="actual",
    mode="lines",
    line={"color": "black", "width": 1},
)
fig.update_layout(
    title="Empirical interval audit under temporal dependence",
    xaxis_title="Prediction date",
    yaxis_title="Next-day change (bp)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 4. 失敗モード

- entity panelでgroupを無視し、同じentityをtrain/testへ置く
- label終了時点を見ず、行番号だけでgapを決める
- embargo幅をtest結果を見て調整する
- grouped split、purge、embargoを同じ操作だと考える
- outer testでalphaを選ぶ
- feature driftだけを見てperformance driftを推測する
- PSIの慣用thresholdを普遍的な統計検定と呼ぶ
- dependent time seriesにexchangeabilityを無条件に置く
- aggregate coverageだけを報告し、period別undercoverageを隠す

## 5. 段階別演習

### 基礎

1. split-conformalのfinite-sample rankを導出せよ。
2. prediction/target intervalを図示しpurgeされた行を説明せよ。

### 標準

3. SECのようなcompany panelでgroupとtimeを同時に守るsplitを設計せよ。
4. test前半・後半でcoverageを分けよ。

### 研究

5. holding periodが5 publication daysの場合のpurge/embargo単位を事前登録せよ。
6. rolling calibration windowでinterval幅を更新せよ。
7. block dependenceを考慮したcoverage診断を設計せよ。
8. adaptive conformalを実装する前に保証とestimandを定義せよ。

## 6. Exit Criteria

- [ ] inner selectionとouter evaluationを分離できる
- [ ] grouped split、purge、embargoが閉じる別々の経路を説明できる
- [ ] target intervalからpurge行を機械的に再計算できる
- [ ] embargoの幅と単位をoutcomeを見る前に固定できる
- [ ] feature driftとerror driftを別々に報告できる
- [ ] conformal quantile rankを実装できる
- [ ] exchangeability未検証を明記できる
- [ ] empirical coverageをperiod別に監査できる

## 7. 出典

- [Lei et al., Distribution-Free Predictive Inference](https://doi.org/10.1080/01621459.2017.1307116) — split conformalの理論
- [Gibbs & Candès, Adaptive Conformal Inference Under Distribution Shift](https://papers.neurips.cc/paper_files/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html) — shift下の拡張
- [scikit-learn Nested CV Example](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html) — selectionとevaluationの分離
"""),
]
