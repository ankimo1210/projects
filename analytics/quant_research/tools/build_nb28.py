"""Builder for notebook 28: Week 20 temporal validation."""

from nbkit import code, md
from stage2_nb import setup_cell, treasury_cell

cells = [
    md(r"""
# 28. Week 20 — Temporal validationとleakage-resistant pipeline

> 時系列pipelineでは、各foldのfit対象期間がmodelの一部である。

## 学習目標

- expanding-window validationを実装できる
- target horizonに合わせてsplit boundaryをpurgeできる
- preprocessingとhyperparameter selectionのfit範囲を監査できる
- methodology break前後のerrorを分けられる

## 前提知識

- Week 17のprediction contract
- Week 18のregularized model
- 時系列indexとrolling window
"""),
    setup_cell(28),
    treasury_cell(),
    md(r"""
## 1. Expanding-window folds

fold $k$ ではtraining終端より後の連続blockだけを評価する。1公表観測先targetなのでboundaryを1行purgeする。
"""),
    code("""
folds = qt.expanding_window_splits(
    len(forecast.regression_target),
    initial_train_size=1000,
    test_size=250,
    step=250,
    gap=forecast.horizon_publications,
)

fold_rows = []
for fold_number, (train_indices, test_indices) in enumerate(folds, start=1):
    model = qt.fit_ridge(
        forecast.features[train_indices],
        forecast.regression_target[train_indices],
        alpha=10.0,
    )
    prediction = model.predict(forecast.features[test_indices])
    metrics = qt.regression_metrics(forecast.regression_target[test_indices], prediction)
    fold_rows.append(
        {
            "fold": fold_number,
            "train_end": pd.Timestamp(forecast.prediction_dates[train_indices[-1]]),
            "test_start": pd.Timestamp(forecast.prediction_dates[test_indices[0]]),
            "test_end": pd.Timestamp(forecast.prediction_dates[test_indices[-1]]),
            "rmse_bp": metrics.rmse,
            "mae_bp": metrics.mae,
            "monotone_convex_share": np.mean(
                forecast.methodology_regime[test_indices] == "monotone-convex"
            ),
        }
    )
fold_table = pd.DataFrame(fold_rows)
display(fold_table)
"""),
    code("""
fig = go.Figure()
fig.add_bar(x=fold_table["fold"], y=fold_table["rmse_bp"], name="RMSE")
fig.add_scatter(
    x=fold_table["fold"],
    y=fold_table["monotone_convex_share"] * fold_table["rmse_bp"].max(),
    name="Post-break share (scaled)",
    mode="lines+markers",
)
fig.update_layout(
    title="Forecast error changes across expanding validation folds",
    xaxis_title="Fold",
    yaxis_title="RMSE (bp); share scaled for display",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 2. Pipeline fit boundary

各foldでfeature mean/stdとmodel parameterをtraining rowsだけから推定する。`fit_ridge`はそのmean/stdをmodel内へ保存し、test rowsにはtransformだけを適用する。
"""),
    code("""
boundary_rows = []
for fold_number, (train_indices, test_indices) in enumerate(folds, start=1):
    model = qt.fit_ridge(
        forecast.features[train_indices],
        forecast.regression_target[train_indices],
        alpha=10.0,
    )
    boundary_rows.append(
        {
            "fold": fold_number,
            "scaler_fit_last_row": int(train_indices[-1]),
            "first_target_row": int(test_indices[0]),
            "purged_rows": int(test_indices[0] - train_indices[-1] - 1),
            "stored_mean_matches_train": bool(
                np.allclose(model.feature_mean, forecast.features[train_indices].mean(axis=0))
            ),
        }
    )
boundary_table = pd.DataFrame(boundary_rows)
display(boundary_table)
assert boundary_table["stored_mean_matches_train"].all()
assert (boundary_table["purged_rows"] == forecast.horizon_publications).all()
"""),
    md(r"""
## 3. Random splitは別の問い

random splitは過去と未来のregimeを混ぜ、deploymentを模倣しない。数値が良くなるかどうかに関係なく、翌日予測のevaluation designとして不採用にする。
"""),
    code("""
rng = task_rng(1)
permutation = rng.permutation(len(forecast.regression_target))
random_train = permutation[:1000]
random_test = permutation[1000:1250]
random_model = qt.fit_ridge(
    forecast.features[random_train],
    forecast.regression_target[random_train],
    alpha=10.0,
)
random_metric = qt.regression_metrics(
    forecast.regression_target[random_test],
    random_model.predict(forecast.features[random_test]),
)
print("random-split RMSE (not an admissible deployment estimate):", random_metric.rmse)
print(
    "random training date range:",
    pd.Timestamp(forecast.prediction_dates[random_train].min()),
    "to",
    pd.Timestamp(forecast.prediction_dates[random_train].max()),
)
"""),
    md(r"""
## 4. 失敗モード

- random splitのscoreをdeployment estimateと呼ぶ
- scaler、imputer、feature selectorをfull sampleでfitする
- target horizon分のpurgeを置かない
- inner validationとfinal outer testを同じrowsにする
- fold errorの分散を隠してaggregate scoreだけを報告する

## 5. 段階別演習

### 基礎

1. 各foldのtraining end、test start、gapを表にせよ。
2. horizon 5日へ変更してpurge testを書け。

### 標準

3. rolling-windowとexpanding-windowを比較せよ。
4. alpha gridをinner expanding foldsだけで選べ。

### 研究

5. methodology breakを跨がないevaluationと跨ぐevaluationを分けよ。
6. hyperparameter search数を増やしたときのselection optimismをsimulationで測れ。

## 6. Exit Criteria

- [ ] chronological expanding foldを構築できる
- [ ] target horizonに合わせてboundaryをpurgeできる
- [ ] transformのfit範囲を監査できる
- [ ] random splitを不採用にする理由を時点で説明できる
- [ ] final testをmodel selectionから隔離できる

## 7. 出典

- [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) — 時系列splitの公式API契約。教材は依存せず同じ境界を明示実装する
- [scikit-learn Nested CV Example](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html) — selectionとevaluationの分離
- [ISLP, Resampling Methods](https://www.statlearning.com/) — validationとcross-validation
"""),
]
