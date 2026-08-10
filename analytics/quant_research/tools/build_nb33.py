"""Builder for notebook 33: Week 23 unsupervised regimes."""

from nbkit import code, md
from stage2_nb import setup_cell, treasury_cell

cells = [
    md(r"""
# 33. Week 23 — Unsupervised learningと記述的regime

> clusterはalgorithmが作るpartitionであり、市場状態の観測された真値ではない。

## 学習目標

- distance-based clusteringでstandardizationが必要な理由を説明できる
- explicit RNGでk-meansを実装できる
- seedを変えたcluster stabilityをlabel-invariantに測れる
- clusterをsupervised error sliceとして限定利用できる

## 前提知識

- B1のPCAと距離
- B2のRNG contract
- B5のcurve factor feature
"""),
    setup_cell(33),
    treasury_cell(),
    md(r"""
## 1. Features and fit period

targetそのものではなく、prediction時点で既知のcurve-change lagとrolling volatilityをclusterする。locked testはcluster fittingに使わない。

training-only standardization後のfeatureを $z_i$ とし、k-meansは

$$
\min_{C_1,\ldots,C_K}\sum_{k=1}^{K}\sum_{i\in C_k}\lVert z_i-\mu_k\rVert_2^2
$$

をassignmentとcenter updateで交互に減らす。local optimumなのでseed契約とstability監査が必要である。
"""),
    code("""
split = qt.chronological_split(len(forecast.regression_target), gap=1)
cluster_feature_names = (
    "10y_change_lag1_bp",
    "curve_level_change_lag1_bp",
    "curve_slope_change_lag1_bp",
    "curve_curvature_change_lag1_bp",
    "10y_rolling_vol_20d_bp",
)
cluster_columns = [forecast.feature_names.index(name) for name in cluster_feature_names]
cluster_train = np.arange(0, split.test.min() - 1)
cluster_features = forecast.features[:, cluster_columns]

cluster_model = qt.fit_kmeans(
    cluster_features[cluster_train],
    3,
    rng=task_rng(1),
)
test_labels = cluster_model.predict(cluster_features[split.test])
print("fit rows:", len(cluster_train))
print("converged / iterations:", cluster_model.converged, cluster_model.iterations)
print("test cluster counts:", np.bincount(test_labels, minlength=3))
"""),
    code("""
fig = go.Figure()
for label in range(3):
    selected = test_labels == label
    fig.add_scatter(
        x=cluster_features[split.test][selected, 0],
        y=cluster_features[split.test][selected, 4],
        mode="markers",
        name=f"cluster {label}",
    )
fig.update_layout(
    title="Descriptive clusters of known-at-prediction features",
    xaxis_title="Lagged 10y change (bp)",
    yaxis_title="20-day rolling volatility (bp)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 2. Label-invariant seed stability

cluster番号は任意なので、label文字列の一致率を使わない。標本pairが同じclusterかどうかのco-membershipを比較する。
"""),
    code("""
comparison_sample = np.linspace(0, len(cluster_train) - 1, 300).astype(int)
reference_labels = cluster_model.labels[comparison_sample]
reference_membership = reference_labels[:, None] == reference_labels[None, :]

stability_rows = []
for seed_coordinate in range(2, 8):
    alternative = qt.fit_kmeans(
        cluster_features[cluster_train],
        3,
        rng=task_rng(seed_coordinate),
    )
    labels = alternative.labels[comparison_sample]
    membership = labels[:, None] == labels[None, :]
    stability_rows.append(
        {
            "seed_coordinate": seed_coordinate,
            "pairwise_membership_agreement": np.mean(reference_membership == membership),
            "inertia": alternative.inertia,
        }
    )
stability_table = pd.DataFrame(stability_rows)
display(stability_table)
"""),
    md(r"""
## 3. Cluster-conditional supervised error

clusterは原因説明ではなく、modelがどのfeature shapeで失敗するかを切るdiagnosticとして使う。
"""),
    code("""
ridge = qt.fit_ridge(
    forecast.features[cluster_train],
    forecast.regression_target[cluster_train],
    alpha=100.0,
)
test_prediction = ridge.predict(forecast.features[split.test])
error_rows = []
for label in range(3):
    selected = test_labels == label
    metrics = qt.regression_metrics(
        forecast.regression_target[split.test][selected],
        test_prediction[selected],
    )
    error_rows.append(
        {
            "cluster": label,
            "rows": int(np.sum(selected)),
            "rmse_bp": metrics.rmse,
            "mae_bp": metrics.mae,
        }
    )
conditional_error = pd.DataFrame(error_rows)
display(conditional_error)

fig = go.Figure(go.Bar(x=conditional_error["cluster"], y=conditional_error["rmse_bp"]))
fig.update_layout(
    title="Ridge forecast error by descriptive test cluster",
    xaxis_title="Cluster label (arbitrary ID)",
    yaxis_title="RMSE (bp)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 4. 失敗モード

- scalerをfull sampleでfitする
- cluster ID 0を「normal regime」などと自動命名する
- seedを1つだけ使いstableと主張する
- targetをcluster featureへ入れてからprediction-time regimeと呼ぶ
- cluster別error差をcausal explanationと読む

## 5. 段階別演習

### 基礎

1. k-means objectiveとassignment/update stepを書け。
2. raw featureとstandardized featureのclusterを比較せよ。

### 標準

3. cluster数2–5でstabilityとinertiaを比較せよ。
4. rolling periodを変えconditional errorを再評価せよ。

### 研究

5. hierarchical clusteringとのco-membershipを比較せよ。
6. cluster uncertaintyを持つmixture modelへの拡張を設計せよ。

## 6. Exit Criteria

- [ ] explicit RNGでk-meansを再現できる
- [ ] scalingとdistanceの関係を説明できる
- [ ] label permutationに不変なstabilityを計算できる
- [ ] clusterをlatent truthと呼ばない
- [ ] supervised error sliceとしての用途を限定できる

## 7. 出典

- [Arthur & Vassilvitskii, k-means++](https://theory.stanford.edu/~sergei/papers/kMeansPP-soda.pdf) — initialization
- [The Elements of Statistical Learning](https://hastie.su.domains/ElemStatLearn/) — clustering、mixture、high-dimensional geometry
- [ISLP, Unsupervised Learning](https://www.statlearning.com/) — PCAとclusteringの実践
"""),
]
