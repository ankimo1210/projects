"""Builder for notebook 26: Week 18 regularized models."""

from nbkit import code, md
from stage2_nb import setup_cell, treasury_cell

cells = [
    md(r"""
# 26. Week 18 — Linear model、ridge、lasso

> regularizationは複雑さへの罰則であり、test scoreを見て調整する免許ではない。

## 学習目標

- OLS、ridge、lasso、elastic netの目的関数を比較できる
- standardized coordinateでcoordinate descentを実装・診断できる
- alphaをvalidationだけで選べる
- column unitを変えてもpredictionが変わらないことを検査できる

## 前提知識

- B1のleast squares、ridge、conditioning
- Week 17のprediction contractとchronological split
- subgradientとsoft thresholdの初歩
"""),
    setup_cell(26),
    treasury_cell(),
    md(r"""
## 1. 目的関数とgeometry

standardized feature $X$ とcentered target $y$ に対し、elastic netは

$$
\frac{1}{2n}\lVert y-X\beta\rVert_2^2
+\alpha\left[\rho\lVert\beta\rVert_1+\frac{1-\rho}{2}\lVert\beta\rVert_2^2\right]
$$

を最小化する。$\rho=0$がridge、$\rho=1$がlassoである。lassoのcoordinate updateはsoft thresholdを使う。
"""),
    code("""
split = qt.chronological_split(len(forecast.regression_target), gap=1)
features = forecast.features
target = forecast.regression_target

ridge_grid = np.array([0.0, 1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0])
lasso_grid = np.array([1e-3, 5e-3, 1e-2, 2e-2, 5e-2, 1e-1, 2e-1])

rows = []
models = {}
for family, grid in [("ridge", ridge_grid), ("lasso", lasso_grid)]:
    for alpha in grid:
        if family == "ridge":
            model = qt.fit_ridge(features[split.train], target[split.train], alpha=float(alpha))
        else:
            model = qt.fit_lasso(features[split.train], target[split.train], alpha=float(alpha))
        prediction = model.predict(features[split.validation])
        metrics = qt.regression_metrics(target[split.validation], prediction)
        rows.append(
            {
                "family": family,
                "alpha": alpha,
                "rmse_bp": metrics.rmse,
                "mae_bp": metrics.mae,
                "nonzero": int(np.sum(np.abs(model.coefficients) > 1e-10)),
                "converged": model.converged,
            }
        )
        models[(family, float(alpha))] = model
validation_table = pd.DataFrame(rows)
display(validation_table)
assert validation_table["converged"].all()
"""),
    code("""
fig = go.Figure()
for family in ["ridge", "lasso"]:
    selected = validation_table[validation_table["family"] == family]
    fig.add_scatter(
        x=selected["alpha"],
        y=selected["rmse_bp"],
        name=family,
        mode="lines+markers",
    )
fig.update_xaxes(type="log", title="Penalty alpha")
fig.update_layout(
    title="Validation error selects regularization before final test",
    yaxis_title="Validation RMSE (bp)",
    template="plotly_white",
)
fig.show()

best_rows = validation_table.loc[validation_table.groupby("family")["rmse_bp"].idxmin()]
display(best_rows)
"""),
    md(r"""
## 2. Coefficient pathとsparsity

係数の大きさはstandardized feature上で比較する。raw unitの係数を大きさだけで重要度と呼ばない。
"""),
    code("""
path_rows = []
for alpha in lasso_grid:
    model = models[("lasso", float(alpha))]
    for name, coefficient in zip(forecast.feature_names, model.coefficients, strict=True):
        path_rows.append({"alpha": alpha, "feature": name, "coefficient": coefficient})
path = pd.DataFrame(path_rows)

fig = go.Figure()
for feature_name, group in path.groupby("feature"):
    fig.add_scatter(x=group["alpha"], y=group["coefficient"], name=feature_name, mode="lines")
fig.update_xaxes(type="log", title="Lasso alpha")
fig.update_layout(
    title="Lasso coefficient path in training-standardized coordinates",
    yaxis_title="Coefficient (bp target per 1 training SD)",
    template="plotly_white",
    showlegend=False,
)
fig.show()
"""),
    md(r"""
## 3. Scale invariance audit

standardizationは各training partitionだけでfitする。列単位を変更しても同じalphaのstandardized model predictionは一致すべきである。
"""),
    code("""
column_scales = np.geomspace(1e-10, 1e10, features.shape[1])
reference = qt.fit_ridge(features[split.train], target[split.train], alpha=1.0)
rescaled = qt.fit_ridge(
    features[split.train] * column_scales,
    target[split.train],
    alpha=1.0,
)
reference_prediction = reference.predict(features[split.validation])
rescaled_prediction = rescaled.predict(features[split.validation] * column_scales)
maximum_difference = float(np.max(np.abs(reference_prediction - rescaled_prediction)))
print("maximum prediction difference after column rescaling:", maximum_difference)
assert maximum_difference < 1e-9
"""),
    md(r"""
## 4. 失敗モード

- alphaごとにtest scoreを見て最小値を選ぶ
- full-sample mean/stdでstandardizeする
- lassoのzero coefficientを「因果効果なし」と解釈する
- convergence未達を無視する
- raw-unit coefficientをそのままfeature importanceとして比較する

## 5. 段階別演習

### 基礎

1. ridgeのclosed-form normal equationをstandardized coordinateで導出せよ。
2. lasso coordinate updateのsoft-threshold式を書け。

### 標準

3. elastic netの`l1_ratio`を追加してvalidation surfaceを作れ。
4. horizon 5日でalpha selectionをやり直せ。

### 研究

5. alpha selectionのsampling uncertaintyをrolling foldで調べよ。
6. coefficient pathのsign stabilityを期間別に評価せよ。

## 6. Exit Criteria

- [ ] ridge、lasso、elastic netの目的関数を説明できる
- [ ] training-only standardizationを実装できる
- [ ] alphaをvalidationだけで選べる
- [ ] scale-invariance testを通せる
- [ ] sparse coefficientを因果解釈しない

## 7. 出典

- [ISLP, Linear Model Selection and Regularization](https://www.statlearning.com/) — ridge、lasso、validation
- [Stanford EE364a](https://web.stanford.edu/class/ee364a/) — convex regularizationとoptimality
- [SciPy `expit`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.expit.html) — 後続logistic実装で使う安定なsigmoid
"""),
]
