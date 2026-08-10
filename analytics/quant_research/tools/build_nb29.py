"""Builder for notebook 29: B5 real-data forecasting project."""

from nbkit import code, md
from stage2_nb import setup_cell, treasury_cell

cells = [
    md(r"""
# 29. B5 Project — Daily Treasury Curve Forecasting Baseline

> 最も価値のある結果が「複雑なmodelを採用しない」である場合を、failureではなく研究結論として残す。

## 学習目標

- real-data manifestからlocked testまで一つのpipelineを実行できる
- zero、mean、AR、ridge、lassoを同じ情報集合で比較できる
- direction logisticをBrierとreliabilityで評価できる
- aggregateとmethodology regimeの結果からclaimを制限できる
- 4成果物と75点gateを自己監査できる

## 前提知識

- Week 17–20の全Exit Criteria
- B1のnumerical stability、B3のclaim audit、B4のtested artifact
"""),
    setup_cell(29),
    treasury_cell(),
    md(r"""
## 1. Locked instructional Project contract

この固定snapshotは教材実装時に既に観察しているため、歴史的なpre-registrationとは呼ばない。
次の規約は、今後modelやhorizonを追加するときにtest結果へ合わせて変更しないinstructional lockである。

| Field | Locked value |
|---|---|
| Prediction origin | official day-$t$ curve publication後 |
| Target | next Treasury publication 10y CMT change |
| Unit | basis points |
| Features | current curve、lag changes、20-day volatility、day-of-week |
| Selection | chronological validation only |
| Final evaluation | last 20%、one use |
| Primary metric | RMSE; MAE and rank correlation are secondary |
| Adoption gate | zero RMSEを1%以上改善し、MAEも悪化せず、period sliceで重大劣化がない |
| Prohibited | PnL、liquidity、intraday、causal claim |
"""),
    code("""
split = qt.chronological_split(len(forecast.regression_target), gap=1)
features = forecast.features
target = forecast.regression_target
direction = forecast.direction_target

ridge_grid = [0.0, 0.01, 0.1, 1.0, 10.0, 100.0]
lasso_grid = [0.001, 0.01, 0.05, 0.1, 0.2]
selection_rows = []
for family, grid in [("ridge", ridge_grid), ("lasso", lasso_grid)]:
    for alpha in grid:
        model = (
            qt.fit_ridge(features[split.train], target[split.train], alpha=alpha)
            if family == "ridge"
            else qt.fit_lasso(features[split.train], target[split.train], alpha=alpha)
        )
        metrics = qt.regression_metrics(
            target[split.validation],
            model.predict(features[split.validation]),
        )
        selection_rows.append(
            {"family": family, "alpha": alpha, "validation_rmse_bp": metrics.rmse}
        )
selection_table = pd.DataFrame(selection_rows)
best_alpha = {
    family: float(group.loc[group["validation_rmse_bp"].idxmin(), "alpha"])
    for family, group in selection_table.groupby("family")
}
display(selection_table)
print("selected alpha:", best_alpha)
"""),
    md(r"""
## 2. Refit before the locked test

alpha選択後、test開始前までのrowsでmodelを一度refitする。test outcomeはこの時点まで参照しない。
"""),
    code("""
final_training = np.arange(0, split.test.min() - forecast.horizon_publications)
lag_column = forecast.feature_names.index("10y_change_lag1_bp")

models = {
    "lag1_ar": qt.fit_ridge(
        features[final_training][:, [lag_column]],
        target[final_training],
        alpha=0.0,
    ),
    "ridge": qt.fit_ridge(
        features[final_training],
        target[final_training],
        alpha=best_alpha["ridge"],
    ),
    "lasso": qt.fit_lasso(
        features[final_training],
        target[final_training],
        alpha=best_alpha["lasso"],
    ),
}

test_predictions = {
    "zero": np.zeros(split.test.size),
    "historical_mean": np.full(split.test.size, target[final_training].mean()),
    "lag1_ar": models["lag1_ar"].predict(features[split.test][:, [lag_column]]),
    "ridge": models["ridge"].predict(features[split.test]),
    "lasso": models["lasso"].predict(features[split.test]),
}
test_rows = []
for name, prediction in test_predictions.items():
    metrics = qt.regression_metrics(target[split.test], prediction)
    test_rows.append(
        {
            "model": name,
            "rmse_bp": metrics.rmse,
            "mae_bp": metrics.mae,
            "rank_corr": metrics.rank_correlation,
        }
    )
test_table = pd.DataFrame(test_rows).sort_values("rmse_bp")
display(test_table)
"""),
    code("""
fig = go.Figure()
fig.add_scatter(
    x=pd.to_datetime(forecast.prediction_dates[split.test]),
    y=target[split.test],
    name="actual",
    mode="lines",
    line={"color": "black", "width": 1},
)
for name in ["zero", "ridge", "lasso"]:
    fig.add_scatter(
        x=pd.to_datetime(forecast.prediction_dates[split.test]),
        y=test_predictions[name],
        name=name,
        mode="lines",
    )
fig.update_layout(
    title="Locked-test next-publication 10y CMT changes",
    xaxis_title="Prediction date",
    yaxis_title="Change (bp)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 3. Direction probability

regression modelのsignと確率modelを混同しない。logisticはdirection専用にfitし、constant prevalenceと比較する。
"""),
    code("""
logistic = qt.fit_logistic_ridge(
    features[final_training],
    direction[final_training],
    alpha=0.1,
)
direction_probability = logistic.predict_proba(features[split.test])
constant_probability = np.full(split.test.size, direction[final_training].mean())
direction_table = pd.DataFrame(
    [
        {
            "model": name,
            **qt.classification_metrics(direction[split.test], probability).__dict__,
        }
        for name, probability in [
            ("constant prevalence", constant_probability),
            ("logistic", direction_probability),
        ]
    ]
)
display(direction_table)

reliability = qt.calibration_table(direction_probability, direction[split.test], n_bins=8)
fig = go.Figure()
fig.add_scatter(
    x=reliability["mean_probability"],
    y=reliability["observed_frequency"],
    mode="lines+markers",
    text=reliability["count"],
    name="logistic",
)
fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", line={"dash": "dash"}, name="perfect")
fig.update_layout(
    title="Locked-test direction reliability",
    xaxis_title="Mean probability",
    yaxis_title="Observed frequency",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 4. Regime and claim audit

final testはmethodology change後だけである。そこで、selectionとは独立したexpanding foldsを使い、pre/post-breakのerrorも記録する。
"""),
    code("""
folds = qt.expanding_window_splits(
    len(target),
    initial_train_size=1000,
    test_size=250,
    step=250,
    gap=1,
)
regime_rows = []
for fold_number, (train_indices, test_indices) in enumerate(folds, start=1):
    model = qt.fit_ridge(features[train_indices], target[train_indices], alpha=best_alpha["ridge"])
    prediction = model.predict(features[test_indices])
    for regime in np.unique(forecast.methodology_regime[test_indices]):
        selected = forecast.methodology_regime[test_indices] == regime
        metrics = qt.regression_metrics(target[test_indices][selected], prediction[selected])
        zero_metrics = qt.regression_metrics(
            target[test_indices][selected],
            np.zeros(np.sum(selected)),
        )
        regime_rows.append(
            {
                "fold": fold_number,
                "regime": regime,
                "rows": int(np.sum(selected)),
                "ridge_rmse_bp": metrics.rmse,
                "zero_rmse_bp": zero_metrics.rmse,
            }
        )
regime_table = pd.DataFrame(regime_rows)
display(regime_table)

zero_row = test_table.loc[test_table["model"] == "zero"].iloc[0]
zero_rmse = float(zero_row["rmse_bp"])
zero_mae = float(zero_row["mae_bp"])
best_nonzero = test_table[test_table["model"] != "zero"].iloc[0]
relative_rmse_improvement = float(
    (zero_rmse - best_nonzero["rmse_bp"]) / zero_rmse
)
model_selected = bool(
    relative_rmse_improvement >= 0.01
    and best_nonzero["mae_bp"] <= zero_mae
)
claim = (
    f"candidate selected: {best_nonzero['model']}"
    if model_selected
    else "no model selected: no candidate clears the locked materiality gate"
)
print("best relative RMSE improvement:", relative_rmse_improvement)
print("primary claim:", claim)
"""),
    md(r"""
## 5. Block成果物と75点gate

| 成果物 | 必須内容 |
|---|---|
| Derivation note | empirical risk、ridge/lasso、logistic、Brier |
| Implementation + tests | snapshot loader、feature/target、split、regularized solver |
| Experiment | baseline、alpha selection、locked test、calibration、break audit |
| Technical memo | question、method、result、failure、no-selectionを含む結論 |

## 6. 失敗モード

- locked testを見てalpha、feature、horizonを再調整する
- zeroと統計的に同等の差を「改善」と強調する
- final testがpost-breakだけであることを隠す
- 1% gateを経済的materialityと呼ぶ（これは教材用の採用停止規則にすぎない）
- direction accuracyをprofitabilityへ読み替える
- modelが選ばれない結果を削除する

## 7. 段階別演習

### 基礎

1. manifest hashとrow countをmemoへ転記せよ。
2. test tableからzeroに対するRMSE差を計算せよ。

### 標準

3. 5公表観測先targetを別のlocked secondary experimentとして実行せよ。
4. bootstrapではなく時系列blockを保つ誤差差のuncertainty方法を設計せよ。

### 研究

5. methodology break後だけでtrainingを始める感度分析をsecondaryとして追加せよ。
6. executable instrumentとcost dataを追加する場合の新しいestimandを定義せよ。

## 8. Exit Criteria

- [ ] source、hash、grain、availabilityを保存した
- [ ] targetとfeature timestampのstrict orderingをtestした
- [ ] alpha selectionとlocked testを分離した
- [ ] zero、mean、AR、ridge、lassoを同じtestで比較した
- [ ] direction probabilityをBrierとreliabilityで評価した
- [ ] 1% RMSE・non-worse MAE gateを固定し、no model selectedを許容した
- [ ] 4成果物、75点、必須gateを別々に確認した

## 9. 出典

- [U.S. Treasury Daily Rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?page=1&type=daily_treasury_yield_curve)
- [U.S. Treasury Yield Curve Methodology](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology)
- [ISLP](https://www.statlearning.com/) — baseline、regularization、classification、validation
- [The Elements of Statistical Learning](https://hastie.su.domains/ElemStatLearn/) — statistical learningの理論
"""),
]
