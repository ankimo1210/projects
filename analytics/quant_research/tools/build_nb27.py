"""Builder for notebook 27: Week 19 classification and calibration."""

from nbkit import code, md
from stage2_nb import setup_cell, treasury_cell

cells = [
    md(r"""
# 27. Week 19 — 方向分類と確率calibration

> 方向を当てることと、0.7と出した事象が約70%起きることは別の性質である。

## 学習目標

- generative classifierとdiscriminative classifierを区別できる
- logistic、LDA、QDA、naive Bayes、kNNを同じ時系列splitで比較できる
- log loss、Brier score、accuracy、reliabilityを別々に診断できる
- probabilityのoverconfidenceを検出できる

## 前提知識

- Gaussian distributionとBayes rule
- logistic likelihood
- Week 17のchronological splitとWeek 18のstandardization
"""),
    setup_cell(27),
    treasury_cell(),
    md(r"""
## 1. Targetとclass prevalence

次のTreasury公表日の10年CMT変化がstrictly positiveなら1、zeroまたはnegativeなら0とする。これは取引signではなく、公表yield変化のdirectionである。
"""),
    code("""
split = qt.chronological_split(len(forecast.direction_target), gap=1)
features = forecast.features
direction = forecast.direction_target

prevalence = pd.DataFrame(
    [
        {"partition": name, "rows": len(indices), "up_rate": direction[indices].mean()}
        for name, indices in [
            ("train", split.train),
            ("validation", split.validation),
            ("test_locked", split.test),
        ]
    ]
)
display(prevalence)
"""),
    md(r"""
## 2. Generativeとdiscriminative

LDA/QDA/naive Bayesは $p(X\mid Y)$ とpriorからposteriorを作る。logisticは $p(Y=1\mid X)$ を直接model化する。kNNは近傍のempirical class rateである。仮定が異なるため、accuracyだけでなく確率品質を比較する。

$$
p(Y=k\mid x)=\frac{\pi_k p(x\mid Y=k)}{\sum_j \pi_j p(x\mid Y=j)},
\qquad
p(Y=1\mid x)=\frac{1}{1+\exp[-(\beta_0+x^\top\beta)]}.
$$

LDAはclass間でcovarianceを共有し、QDAはclass別covarianceを使う。naive Bayesはclass内covarianceを
diagonalへ制限する。教材APIはすべてtraining rowsでstandardizeしてからfitする。
"""),
    code("""
train_x = features[split.train]
validation_x = features[split.validation]
train_y = direction[split.train]
validation_y = direction[split.validation]

probabilities = {
    "constant": np.full(validation_y.size, train_y.mean()),
    "logistic": qt.fit_logistic_ridge(train_x, train_y, alpha=0.1).predict_proba(validation_x),
}
for kind in ["lda", "qda", "naive_bayes"]:
    model = qt.fit_gaussian_classifier(train_x, train_y, kind=kind, regularization=1e-3)
    probabilities[kind] = qt.predict_gaussian_proba(model, validation_x)
probabilities["knn"] = qt.knn_predict_proba(
    train_x,
    train_y,
    validation_x,
    n_neighbors=41,
)

metric_rows = []
for name, probability in probabilities.items():
    metrics = qt.classification_metrics(validation_y, probability)
    metric_rows.append(
        {
            "model": name,
            "log_loss": metrics.log_loss,
            "brier": metrics.brier_score,
            "accuracy": metrics.accuracy,
            "ece": metrics.expected_calibration_error,
        }
    )
classification_table = pd.DataFrame(metric_rows).sort_values("brier")
display(classification_table)
"""),
    md(r"""
## 3. Reliability diagram

bin内のmean forecast probabilityとobserved frequencyを比較する。binの標本数を隠さない。
"""),
    code("""
fig = go.Figure()
for name in ["constant", "logistic", "lda", "qda", "naive_bayes", "knn"]:
    table = qt.calibration_table(probabilities[name], validation_y, n_bins=8)
    fig.add_scatter(
        x=table["mean_probability"],
        y=table["observed_frequency"],
        mode="lines+markers",
        name=name,
        text=table["count"],
        hovertemplate="p=%{x:.3f}<br>freq=%{y:.3f}<br>n=%{text}<extra></extra>",
    )
fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="perfect calibration", line={"dash": "dash"})
fig.update_layout(
    title="Validation reliability diagram",
    xaxis_title="Mean predicted probability",
    yaxis_title="Observed up frequency",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 4. Overconfidence破壊実験

logitを2倍するとclass rankは保ちやすいが、確率は0/1側へ押される。discriminationが同じでもBrierとlog lossは悪化し得る。
"""),
    code("""
logistic_probability = np.clip(probabilities["logistic"], 1e-8, 1 - 1e-8)
logit = np.log(logistic_probability / (1.0 - logistic_probability))
overconfident_probability = 1.0 / (1.0 + np.exp(-2.0 * logit))

confidence_audit = pd.DataFrame(
    [
        {
            "version": name,
            **qt.classification_metrics(validation_y, probability).__dict__,
        }
        for name, probability in [
            ("original logistic", logistic_probability),
            ("overconfident logits", overconfident_probability),
        ]
    ]
)
display(confidence_audit)
"""),
    md(r"""
## 5. 失敗モード

- 0.5 threshold accuracyだけでprobability modelを選ぶ
- final testでcalibration methodを選ぶ
- reliability binの標本数を表示しない
- QDA covarianceが不安定でもregularizationを記録しない
- yield-up probabilityをtrade-profit probabilityと呼ぶ

## 6. 段階別演習

### 基礎

1. Brier scoreをmean squared probability errorとして計算せよ。
2. LDAとQDAが共有する仮定・異なる仮定を表にせよ。

### 標準

3. bin数を5、10、20に変え、reliabilityの分散を比較せよ。
4. kNNのneighbor数をvalidationで選べ。

### 研究

5. rolling calibration errorを作り、methodology break前後で比較せよ。
6. probability recalibration専用partitionを設計せよ。

## 7. Exit Criteria

- [ ] generative / discriminativeの違いを説明できる
- [ ] log loss、Brier、accuracy、ECEを計算できる
- [ ] reliability diagramへbin countを載せられる
- [ ] overconfidenceとdiscriminationを分離できる
- [ ] classification targetの市場上の限界を説明できる

## 8. 出典

- [ISLP, Classification](https://www.statlearning.com/) — logistic、LDA/QDA、naive Bayes、kNN
- [scikit-learn Calibration Guide](https://scikit-learn.org/stable/modules/calibration.html) — reliability diagramとcalibrationの公式解説。教材実装はNumPy/SciPyで独立に行う
- [Brier, Verification of forecasts expressed in terms of probability](https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2) — probability score原論文
"""),
]
