"""Builder for notebook 31: Week 21 trees and boosting."""

from nbkit import code, md
from stage2_nb import setup_cell, treasury_cell

cells = [
    md(r"""
# 31. Week 21 — Regression stumpとgradient boosting

> training lossを下げ続ける能力は、future errorを下げる保証ではない。

## 学習目標

- squared-error stumpのsplit ruleを導出できる
- boostingをresidualへの逐次fitとして実装できる
- learning rateとestimator数をvalidationで選べる
- split frequency、permutation importance、partial dependenceを因果効果と呼ばない

## 前提知識

- B5のempirical riskとlocked split
- squared errorとgradient
- basic recursion、array sorting
"""),
    setup_cell(31),
    treasury_cell(),
    md(r"""
## 1. Stump split

feature $j$ とthreshold $s$ に対して、左右のleaf meanを使うsquared error

$$
\sum_{i:x_{ij}\le s}(y_i-\bar y_L)^2+
\sum_{i:x_{ij}>s}(y_i-\bar y_R)^2
$$

を最小にする。threshold候補数とminimum leafを固定し、無制限なsearchを避ける。
"""),
    code("""
split = qt.chronological_split(len(forecast.regression_target), gap=1)
features = forecast.features
target = forecast.regression_target

stump = qt.fit_decision_stump(
    features[split.train],
    target[split.train],
    min_leaf_size=40,
)
stump_validation = qt.regression_metrics(
    target[split.validation],
    stump.predict(features[split.validation]),
)
print("split feature:", forecast.feature_names[stump.feature_index])
print("threshold:", stump.threshold)
print("validation RMSE (bp):", stump_validation.rmse)
"""),
    md(r"""
## 2. Gradient boosting

squared lossでは、現在のpredictionに対するnegative gradientはresidualである。各iterationでstumpをresidualへfitし、learning rate $\eta$ で加える。

$$
F_m(x)=F_{m-1}(x)+\eta h_m(x)
$$
"""),
    code("""
estimator_grid = [10, 25, 50]
boosting_rows = []
boosting_models = {}
for n_estimators in estimator_grid:
    start = time.perf_counter()
    model = qt.fit_gradient_boosting(
        features[split.train],
        target[split.train],
        n_estimators=n_estimators,
        learning_rate=0.05,
        min_leaf_size=40,
    )
    elapsed = time.perf_counter() - start
    metrics = qt.regression_metrics(
        target[split.validation],
        model.predict(features[split.validation]),
    )
    boosting_rows.append(
        {
            "n_estimators": n_estimators,
            "validation_rmse_bp": metrics.rmse,
            "fit_seconds": elapsed,
            "final_training_mse": model.training_loss[-1],
        }
    )
    boosting_models[n_estimators] = model
boosting_table = pd.DataFrame(boosting_rows)
display(boosting_table)
"""),
    code("""
fig = go.Figure()
for n_estimators, model in boosting_models.items():
    fig.add_scatter(
        x=np.arange(model.training_loss.size),
        y=model.training_loss,
        mode="lines",
        name=f"fit to {n_estimators}",
    )
fig.update_layout(
    title="Training loss decreases by construction",
    xaxis_title="Boosting iteration",
    yaxis_title="Training MSE (bp squared)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 3. Predictive importance and dependence are not causal

どのfeatureが何回stumpに選ばれたかを数える。さらにvalidation列を1列ずつshuffleしたRMSE増分と、
1 featureだけをgridへ置換したpartial dependenceを計算する。いずれもfit済みmodelの予測診断であり、
correlated feature間の代替やsupport外の組合せがあるため、経済的作用や因果効果とは解釈しない。
"""),
    code("""
selected_estimators = int(
    boosting_table.loc[boosting_table["validation_rmse_bp"].idxmin(), "n_estimators"]
)
selected_model = boosting_models[selected_estimators]
split_counts = pd.Series(
    [forecast.feature_names[stump.feature_index] for stump in selected_model.stumps]
).value_counts()

fig = go.Figure(go.Bar(x=split_counts.values, y=split_counts.index, orientation="h"))
fig.update_layout(
    title="Stump split frequency (predictive use only)",
    xaxis_title="Number of selected stumps",
    yaxis_title="Feature",
    template="plotly_white",
)
fig.show()
"""),
    code("""
validation_features = features[split.validation]
validation_target = target[split.validation]
baseline_prediction = selected_model.predict(validation_features)
baseline_rmse = qt.regression_metrics(validation_target, baseline_prediction).rmse

importance_rows = []
for feature_index, feature_name in enumerate(forecast.feature_names):
    permuted = validation_features.copy()
    order = task_rng(2, feature_index).permutation(validation_features.shape[0])
    permuted[:, feature_index] = permuted[order, feature_index]
    permuted_rmse = qt.regression_metrics(
        validation_target,
        selected_model.predict(permuted),
    ).rmse
    importance_rows.append(
        {
            "feature": feature_name,
            "permutation_rmse_increase_bp": permuted_rmse - baseline_rmse,
        }
    )
importance_table = pd.DataFrame(importance_rows).sort_values(
    "permutation_rmse_increase_bp",
    ascending=False,
)
display(importance_table.head(10))

fig = go.Figure(
    go.Bar(
        x=importance_table.head(10)["permutation_rmse_increase_bp"],
        y=importance_table.head(10)["feature"],
        orientation="h",
    )
)
fig.update_layout(
    title="Validation permutation importance (predictive only)",
    xaxis_title="RMSE increase after permutation (bp)",
    yaxis_title="Feature",
    template="plotly_white",
)
fig.show()

top_feature_name = str(importance_table.iloc[0]["feature"])
top_feature_index = forecast.feature_names.index(top_feature_name)
partial_grid = np.quantile(
    validation_features[:, top_feature_index],
    np.linspace(0.05, 0.95, 19),
)
partial_values = []
for value in partial_grid:
    counterfactual_features = validation_features.copy()
    counterfactual_features[:, top_feature_index] = value
    partial_values.append(selected_model.predict(counterfactual_features).mean())

fig = go.Figure(
    go.Scatter(x=partial_grid, y=partial_values, mode="lines+markers")
)
fig.update_layout(
    title=f"Partial dependence of {top_feature_name} (predictive only)",
    xaxis_title=top_feature_name,
    yaxis_title="Mean model prediction (bp)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 4. 失敗モード

- training lossの最小iterationを採用する
- estimator数、depth、learning rateをtestで選ぶ
- min leafとthreshold search budgetを報告しない
- split frequencyをcausal importanceと呼ぶ
- permutation importanceやpartial dependenceを介入効果と呼ぶ
- boostingがzero baselineを超えない結果を隠す

## 5. 段階別演習

### 基礎

1. cumulative sumでstump SSEを計算する式を導出せよ。
2. learning rateを0.02、0.1に変えtraining traceを比較せよ。

### 標準

3. estimator数とlearning rateの2次元validationを行え。
4. pre/post methodology breakでvalidation errorを分けよ。

### 研究

5. block bootstrapでbaselineとの差のuncertaintyを評価せよ。
6. partial dependenceがcorrelated feature下で壊れる例を作れ。

## 6. Exit Criteria

- [ ] stump splitを式とcodeで説明できる
- [ ] boosting updateとshrinkageを説明できる
- [ ] training traceとvalidation selectionを分離できる
- [ ] search budgetを保存できる
- [ ] predictive importanceとpartial dependenceを因果解釈しない

## 7. 出典

- [Friedman, Greedy Function Approximation](https://doi.org/10.1214/aos/1013203451) — gradient boosting原論文
- [The Elements of Statistical Learning](https://hastie.su.domains/ElemStatLearn/) — tree、boosting、regularization
- [Interpretable Machine Learning: Feature Importance](https://christophm.github.io/interpretable-ml-book/feature-importance.html) — predictive importanceの解釈
"""),
]
