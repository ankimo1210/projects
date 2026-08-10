"""Builder for notebook 25: Week 17 real-data baselines."""

from nbkit import code, md
from stage2_nb import setup_cell, treasury_cell

cells = [
    md(r"""
# 25. Week 17 — 実データ、予測問題、baseline

> modelを作る前に、dataが何を表し、いつ利用でき、何を予測するかを固定する。

## 学習目標

- Treasury snapshotのdate × tenor grainを監査できる
- prediction originとfuture targetをcode上で分離できる
- zero、historical mean、lag-1 baselineを同一holdoutで比較できる
- loss、metric、utilityを区別できる

## 前提知識

- 時系列のlagとdifference
- 平均、分散、RMSE、MAE
- B3のestimandとB4のdata contract
"""),
    setup_cell(25),
    treasury_cell(),
    md(r"""
## 1. Data-quality profile

Sourceの表が表示できるだけでは足りない。date key、tenor completeness、range、calendar gap、methodology breakを検査する。
"""),
    code("""
profile = pd.DataFrame(
    {
        "tenor": treasury.metadata.tenors,
        "missing": [treasury.quality.missing_by_tenor[name] for name in treasury.metadata.tenors],
        "minimum_pct": [float(rates[name].min()) for name in treasury.metadata.tenors],
        "maximum_pct": [float(rates[name].max()) for name in treasury.metadata.tenors],
    }
)
display(profile)

quality_summary = pd.DataFrame(
    {
        "check": [
            "rows",
            "duplicate dates",
            "maximum calendar gap days",
            "methodology-crossing targets retained",
            "snapshot sha256",
            "terms reviewed at",
        ],
        "value": [
            treasury.quality.row_count,
            treasury.quality.duplicate_dates,
            treasury.quality.maximum_calendar_gap_days,
            int(crosses_methodology_break.sum()),
            treasury.metadata.snapshot_sha256,
            treasury.metadata.terms_reviewed_at,
        ],
    }
)
display(quality_summary)

annual_rows = rates.groupby(rates["date"].dt.year).size()
fig = go.Figure(go.Bar(x=annual_rows.index, y=annual_rows.values))
fig.update_layout(
    title="Observation count by calendar year",
    xaxis_title="Year",
    yaxis_title="Treasury trading dates",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 2. Prediction contract

10年CMTを $y_t$ とし、day-$t$の公式公表後に、次のTreasury公表観測を$t+1$として

$$
Y_{t+1}=100(y_{t+1}-y_t)
$$

を予測する。sourceはpercent表示なので100倍した差がbasis pointsである。featureにはday-$t$までのyield、curve factor、lagged change、20日volatilityだけを入れる。
"""),
    code("""
split = qt.chronological_split(
    len(forecast.regression_target),
    gap=forecast.horizon_publications,
)

split_table = pd.DataFrame(
    [
        {
            "partition": name,
            "rows": len(indices),
            "first_prediction": pd.Timestamp(forecast.prediction_dates[indices[0]]),
            "last_prediction": pd.Timestamp(forecast.prediction_dates[indices[-1]]),
            "last_target": pd.Timestamp(forecast.target_dates[indices[-1]]),
        }
        for name, indices in [
            ("train", split.train),
            ("validation", split.validation),
            ("test_locked", split.test),
        ]
    ]
)
display(split_table)
assert split.train.max() + forecast.horizon_publications < split.validation.min()
assert split.validation.max() + forecast.horizon_publications < split.test.min()
"""),
    md(r"""
## 3. Baselines

- **Zero:** $\hat Y_{t+1}=0$
- **Historical mean:** training targetの平均
- **Lag-1 AR:** 当日までに観測済みの直近変化だけを使うlinear model

baselineは弱い飾りではない。日次yield changeではno-changeが強い基準になり得る。
"""),
    code("""
target = forecast.regression_target
lag_column = forecast.feature_names.index("10y_change_lag1_bp")
train_lag = forecast.features[split.train][:, [lag_column]]
validation_lag = forecast.features[split.validation][:, [lag_column]]

ar_model = qt.fit_ridge(train_lag, target[split.train], alpha=0.0)
baseline_predictions = {
    "zero": np.zeros(split.validation.size),
    "historical_mean": np.full(split.validation.size, target[split.train].mean()),
    "lag1_ar": ar_model.predict(validation_lag),
}

baseline_rows = []
for name, prediction in baseline_predictions.items():
    metrics = qt.regression_metrics(target[split.validation], prediction)
    baseline_rows.append(
        {"model": name, "rmse_bp": metrics.rmse, "mae_bp": metrics.mae, "rank_corr": metrics.rank_correlation}
    )
baseline_table = pd.DataFrame(baseline_rows).sort_values("rmse_bp")
display(baseline_table)

fig = go.Figure()
for name, prediction in baseline_predictions.items():
    fig.add_scatter(
        x=pd.to_datetime(forecast.prediction_dates[split.validation]),
        y=prediction,
        name=name,
        mode="lines",
    )
fig.add_scatter(
    x=pd.to_datetime(forecast.prediction_dates[split.validation]),
    y=target[split.validation],
    name="actual next-publication change",
    mode="lines",
    line={"color": "black", "width": 1},
)
fig.update_layout(
    title="Validation-period next-publication 10y CMT change forecasts",
    xaxis_title="Prediction date",
    yaxis_title="Change (bp)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 4. Loss、metric、utility

training lossはparameterを選ぶ数式、metricはholdoutでmodelを比較する要約、utilityは意思決定の価値である。RMSEが小さくても取引instrument、price、position、costが無ければPnL utilityは定義できない。

## 5. 失敗モード

- targetを作ってからrandom shuffleする
- full sampleの平均や標準偏差でfeatureを変換する
- no-changeを比較表から外す
- day-$t$ curveが3:30 PM時点のindicative bidから作られ、通常6:00 PMまでに公表されることを無視する
- CMT forecastを取引可能なTreasury securityのreturn forecastと呼ぶ

## 6. 段階別演習

### 基礎

1. date重複、tenor欠損、maximum gapを再計算せよ。
2. targetを5公表観測先へ変更し、purge gapも5行へ変更せよ。

### 標準

3. 2年・5年・30年をtargetに同じbaselineを比較せよ。
4. methodology break前後でtarget volatilityを比較せよ。

### 研究

5. publication delayを考慮したconservative prediction timestamp schemaを設計せよ。
6. no-changeを上回るために必要なRMSE差のuncertainty評価を提案せよ。

## 7. Exit Criteria

- [ ] date × tenor grain、unit、availabilityを説明できる
- [ ] target dateがprediction dateより後であることをtestできる
- [ ] three baselinesを同じchronological holdoutで比較できる
- [ ] loss、metric、utilityを区別できる
- [ ] model改善が実取引改善を意味しないと説明できる

## 8. 出典

- [U.S. Treasury Daily Rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?page=1&type=daily_treasury_yield_curve) — official source
- [U.S. Treasury Yield Curve Methodology](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology) — observationとpublication contract
- [ISLP, Chapter 2](https://www.statlearning.com/) — prediction、loss、train/test、baselineの基礎
"""),
]
