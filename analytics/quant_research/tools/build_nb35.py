"""Builder for notebook 35: B6 Treasury model tournament."""

from nbkit import code, md
from stage2_nb import setup_cell, treasury_cell

cells = [
    md(r"""
# 35. B6 Project — Treasury Forecast Model Tournament

> tournamentの成功条件はwinnerを必ず出すことではなく、比較不能な差とunsupported claimを排除することである。

## 学習目標

- B5のimmutable data・target・outer testを再利用できる
- ridge、boosting、kernel ridge、GPをpredeclared budgetで比較できる
- RMSE、MAE、rank、interval、drift、runtimeを同時に監査できる
- no model selectedを機械的なgateで結論にできる

## 前提知識

- B5 Projectのlocked protocol
- Week 21–24の全Exit Criteria
- B4のruntimeとartifact integrity
"""),
    setup_cell(35),
    treasury_cell(),
    md(r"""
## 1. Immutable tournament contract

| Item | Rule |
|---|---|
| Data / target / timestamp | B5から変更しない |
| Outer test | B5 final chronological 20% |
| Ridge fit rows | all pre-test rows |
| Boosting fit rows | all pre-test rows、20/40 stumpsをinner validation |
| Kernel ridge | latest 600 pre-test rows、length scale 0.5/1/2 |
| GP | latest 300 pre-test rows、fixed RBF/noise contract |
| MLP | B9完了後のAdvanced、Core tableへ入れない |
| Adoption | zero RMSEを1%以上改善 + non-worse MAE + failure/stability/runtime audit |
"""),
    code("""
split = qt.chronological_split(len(forecast.regression_target), gap=1)
features = forecast.features
target = forecast.regression_target
final_training = np.arange(0, split.test.min() - 1)

search_rows = []
for n_estimators in [20, 40]:
    model = qt.fit_gradient_boosting(
        features[split.train],
        target[split.train],
        n_estimators=n_estimators,
        learning_rate=0.05,
        min_leaf_size=40,
    )
    metric = qt.regression_metrics(
        target[split.validation],
        model.predict(features[split.validation]),
    )
    search_rows.append(
        {"family": "boosting", "setting": n_estimators, "validation_rmse_bp": metric.rmse}
    )

kernel_selection_train = split.train[-500:]
for length_scale in [0.5, 1.0, 2.0]:
    model = qt.fit_kernel_ridge(
        features[kernel_selection_train],
        target[kernel_selection_train],
        length_scale=length_scale,
        ridge=1.0,
    )
    metric = qt.regression_metrics(
        target[split.validation],
        model.predict(features[split.validation]),
    )
    search_rows.append(
        {"family": "kernel_ridge", "setting": length_scale, "validation_rmse_bp": metric.rmse}
    )

search_table = pd.DataFrame(search_rows)
selected_setting = {
    family: group.loc[group["validation_rmse_bp"].idxmin(), "setting"]
    for family, group in search_table.groupby("family")
}
display(search_table)
print("selected settings before outer test:", selected_setting)
"""),
    md(r"""
## 2. Final fits and runtime

各modelのfit rowsが異なることを表へ残す。これはdense kernelの計算量制約によるpredeclared contractであり、同じtraining sampleだと偽らない。
"""),
    code("""
predictions = {"zero": np.zeros(split.test.size)}
fit_records = [{"model": "zero", "fit_rows": 0, "fit_seconds": 0.0}]

start = time.perf_counter()
ridge = qt.fit_ridge(features[final_training], target[final_training], alpha=100.0)
fit_records.append(
    {"model": "ridge", "fit_rows": len(final_training), "fit_seconds": time.perf_counter() - start}
)
predictions["ridge"] = ridge.predict(features[split.test])

start = time.perf_counter()
boosting = qt.fit_gradient_boosting(
    features[final_training],
    target[final_training],
    n_estimators=int(selected_setting["boosting"]),
    learning_rate=0.05,
    min_leaf_size=40,
)
fit_records.append(
    {"model": "boosting", "fit_rows": len(final_training), "fit_seconds": time.perf_counter() - start}
)
predictions["boosting"] = boosting.predict(features[split.test])

kernel_training = final_training[-600:]
start = time.perf_counter()
kernel = qt.fit_kernel_ridge(
    features[kernel_training],
    target[kernel_training],
    length_scale=float(selected_setting["kernel_ridge"]),
    ridge=1.0,
)
fit_records.append(
    {"model": "kernel_ridge", "fit_rows": len(kernel_training), "fit_seconds": time.perf_counter() - start}
)
predictions["kernel_ridge"] = kernel.predict(features[split.test])

gp_training = final_training[-300:]
start = time.perf_counter()
gp = qt.fit_gaussian_process(
    features[gp_training],
    target[gp_training],
    length_scale=1.0,
    noise_variance=20.0,
)
fit_records.append(
    {"model": "gaussian_process", "fit_rows": len(gp_training), "fit_seconds": time.perf_counter() - start}
)
gp_prediction = gp.predict(features[split.test])
predictions["gaussian_process"] = gp_prediction.mean
runtime_table = pd.DataFrame(fit_records)
display(runtime_table)
"""),
    code("""
tournament_rows = []
for name, prediction in predictions.items():
    metrics = qt.regression_metrics(target[split.test], prediction)
    tournament_rows.append(
        {
            "model": name,
            "rmse_bp": metrics.rmse,
            "mae_bp": metrics.mae,
            "rank_corr": metrics.rank_correlation,
        }
    )
tournament = pd.DataFrame(tournament_rows).merge(runtime_table, on="model").sort_values("rmse_bp")
display(tournament)

fig = go.Figure()
fig.add_scatter(
    x=np.maximum(tournament["fit_seconds"], 1e-5),
    y=tournament["rmse_bp"],
    mode="markers+text",
    text=tournament["model"],
    textposition="top center",
)
fig.update_xaxes(type="log", title="Fit seconds (log scale)")
fig.update_layout(
    title="Locked-test error and fit cost",
    yaxis_title="RMSE (bp)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 3. GP interval and feature drift

GP intervalはmodel-basedであり、distribution-freeではない。coverageとwidthを実測し、train-to-test driftと並べる。
"""),
    code("""
z90 = 1.6448536269514722
gp_covered = (
    (target[split.test] >= gp_prediction.mean - z90 * gp_prediction.standard_deviation)
    & (target[split.test] <= gp_prediction.mean + z90 * gp_prediction.standard_deviation)
)
drift = qt.feature_drift_report(
    features[split.train],
    features[split.test],
    feature_names=forecast.feature_names,
)
diagnostic_table = pd.DataFrame(
    {
        "diagnostic": [
            "GP empirical 90% coverage",
            "GP mean interval width (bp)",
            "max abs standardized mean drift",
            "max PSI",
        ],
        "value": [
            gp_covered.mean(),
            np.mean(2.0 * z90 * gp_prediction.standard_deviation),
            drift.maximum_absolute_mean_difference,
            drift.maximum_population_stability_index,
        ],
    }
)
display(diagnostic_table)
"""),
    md(r"""
## 4. Direction calibration companion

B5 logisticはregression tournamentとは別taskである。同じlocked testでconstant prevalenceとBrierを比較するが、RMSE tableへ混ぜない。
"""),
    code("""
logistic = qt.fit_logistic_ridge(
    features[final_training],
    forecast.direction_target[final_training],
    alpha=0.1,
)
logistic_probability = logistic.predict_proba(features[split.test])
constant_probability = np.full(
    split.test.size,
    forecast.direction_target[final_training].mean(),
)
direction_audit = pd.DataFrame(
    [
        {
            "model": name,
            **qt.classification_metrics(
                forecast.direction_target[split.test], probability
            ).__dict__,
        }
        for name, probability in [
            ("constant", constant_probability),
            ("logistic", logistic_probability),
        ]
    ]
)
display(direction_audit)
"""),
    md(r"""
## 5. Locked instructional selection gate

Core候補はzeroよりlocked-test RMSEを1%以上改善し、MAEも悪化せず、diagnosticとruntimeが報告されて初めてcandidateになる。1%は教材用の停止規則であり、取引instrumentのない本データから経済的materialityを表すものではない。差のuncertainty評価をまだ行っていないため、gate通過後もcandidateに留める。
"""),
    code("""
zero_row = tournament.loc[tournament["model"] == "zero"].iloc[0]
zero_rmse = float(zero_row["rmse_bp"])
zero_mae = float(zero_row["mae_bp"])
eligible = tournament[
    (tournament["model"] != "zero")
    & ((zero_rmse - tournament["rmse_bp"]) / zero_rmse >= 0.01)
    & (tournament["mae_bp"] <= zero_mae)
]
if eligible.empty:
    selected_model = None
    tournament_claim = "no model selected: no Core candidate clears the materiality gate"
else:
    selected_model = str(eligible.iloc[0]["model"])
    tournament_claim = f"provisional candidate: {selected_model}; uncertainty audit still required"
print(tournament_claim)
"""),
    md(r"""
## 6. Block成果物と75点gate

| 成果物 | 必須内容 |
|---|---|
| Derivation note | stump/boosting、kernel/GP、drift、interval assumption |
| Implementation + tests | transparent B6 APIsとedge cases |
| Experiment | common test、inner budget、runtime、coverage、drift |
| Technical memo | winner/no-selection、failure、comparability、claim boundary |

## 7. 失敗モード

- testを見てsubset、length scale、stump数を変更する
- fit rowsの違いを隠す
- GP intervalをguaranteed coverageと呼ぶ
- RMSEだけでwinnerを決める
- no-selectionを失敗として削除する
- MLPを未履修のままblack boxでCoreへ追加する

## 8. 段階別演習

### 基礎

1. modelごとのfit rows、setting、runtimeをmanifestへ保存せよ。
2. zeroとの差をbp単位で計算せよ。

### 標準

3. expanding outer foldsでmodel順位の安定性を測れ。
4. GP coverageをtest前半・後半で分けよ。

### 研究

5. paired block bootstrapでRMSE差のuncertaintyを評価せよ。
6. B9後にMLPを同じbudgetで追加するpre-analysis planを書け。

## 9. Exit Criteria

- [ ] B5のdata・target・timestamp・outer testを変更していない
- [ ] inner search budgetとfit rowsをmodel別に保存した
- [ ] RMSE、MAE、rank、runtime、drift、intervalを報告した
- [ ] GP uncertaintyのmodel dependenceを説明した
- [ ] direction taskをregression tournamentと分離した
- [ ] no model selectedを機械的gateで許容した
- [ ] 4成果物、75点、必須gateを別々に確認した

## 10. 出典

- [The Elements of Statistical Learning](https://hastie.su.domains/ElemStatLearn/)
- [Gaussian Processes for Machine Learning](https://gaussianprocess.org/gpml/)
- [Lei et al., Distribution-Free Predictive Inference](https://doi.org/10.1080/01621459.2017.1307116)
- [Gibbs & Candès, Adaptive Conformal Inference Under Distribution Shift](https://papers.neurips.cc/paper_files/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html)
- [U.S. Treasury Yield Curve Methodology](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology)
"""),
]
