"""Builder for notebook 32: Week 22 kernels and Gaussian processes."""

from nbkit import code, md
from stage2_nb import setup_cell, treasury_cell

cells = [
    md(r"""
# 32. Week 22 — Kernel ridgeとGaussian process

> smoothなnonlinearityとpredictive uncertaintyを得ても、仮定・計算量・coverageの監査は残る。

## 学習目標

- RBF kernelとkernel ridgeの式を説明できる
- GP posterior meanとvarianceをCholesky solveで計算できる
- length scaleとnoiseをvalidationで選べる
- cubic costのためのfit subsetを明記できる

## 前提知識

- B1のpositive-definite matrixとCholesky
- B5のridgeとtemporal validation
- Gaussian conditional distribution
"""),
    setup_cell(32),
    treasury_cell(),
    md(r"""
## 1. RBF kernelとrepresenter form

$$
k(x,x')=\exp\left(-\frac{\lVert x-x'\rVert_2^2}{2\ell^2}\right),
\qquad
\hat f(x)=k(x,X)(K+\lambda I)^{-1}(y-\bar y)+\bar y.
$$

列尺度はtraining subsetでstandardizeする。explicit inverseは作らずlinear solveを使う。
"""),
    code("""
split = qt.chronological_split(len(forecast.regression_target), gap=1)
features = forecast.features
target = forecast.regression_target

kernel_train = split.train[-500:]
kernel_validation = split.validation
length_scales = [0.5, 1.0, 2.0]
kernel_rows = []
kernel_models = {}
for length_scale in length_scales:
    start = time.perf_counter()
    model = qt.fit_kernel_ridge(
        features[kernel_train],
        target[kernel_train],
        length_scale=length_scale,
        ridge=1.0,
    )
    elapsed = time.perf_counter() - start
    metrics = qt.regression_metrics(
        target[kernel_validation],
        model.predict(features[kernel_validation]),
    )
    kernel_rows.append(
        {
            "length_scale": length_scale,
            "fit_rows": len(kernel_train),
            "validation_rmse_bp": metrics.rmse,
            "fit_seconds": elapsed,
        }
    )
    kernel_models[length_scale] = model
kernel_table = pd.DataFrame(kernel_rows)
display(kernel_table)
"""),
    code("""
fig = go.Figure(
    go.Scatter(
        x=kernel_table["length_scale"],
        y=kernel_table["validation_rmse_bp"],
        mode="lines+markers",
    )
)
fig.update_layout(
    title="Kernel length scale selected only on validation",
    xaxis_title="RBF length scale in standardized feature space",
    yaxis_title="Validation RMSE (bp)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 2. Gaussian process posterior

GPは同じkernelをcovarianceとして使う。training covarianceを $K+\sigma_n^2 I=LL^\top$ とCholesky分解し、posterior meanとvarianceをsolveで求める。

$$
m_*=\bar y+k_*^\top(K+\sigma_n^2I)^{-1}(y-\bar y),
\qquad
v_*=k(x_*,x_*)+\sigma_n^2-k_*^\top(K+\sigma_n^2I)^{-1}k_*.
$$

$\sigma_n^2$ はtargetのbp²単位で指定する。以下のgridはvalidation RMSEで選び、coverageは同じ
selection期間のdiagnosticなのでfinal保証とは呼ばない。
"""),
    code("""
z90 = 1.6448536269514722
gp_train = split.train[-300:]
gp_rows = []
gp_models = {}
for length_scale in [0.5, 1.0, 2.0]:
    for noise_variance in [10.0, 20.0, 40.0]:
        start = time.perf_counter()
        model = qt.fit_gaussian_process(
            features[gp_train],
            target[gp_train],
            length_scale=length_scale,
            noise_variance=noise_variance,
        )
        elapsed = time.perf_counter() - start
        prediction = model.predict(features[split.validation])
        metrics = qt.regression_metrics(target[split.validation], prediction.mean)
        coverage90 = np.mean(
            (
                target[split.validation]
                >= prediction.mean - z90 * prediction.standard_deviation
            )
            & (
                target[split.validation]
                <= prediction.mean + z90 * prediction.standard_deviation
            )
        )
        setting = (length_scale, noise_variance)
        gp_models[setting] = model
        gp_rows.append(
            {
                "length_scale": length_scale,
                "noise_variance_bp2": noise_variance,
                "validation_rmse_bp": metrics.rmse,
                "validation_coverage90": coverage90,
                "fit_seconds": elapsed,
            }
        )
gp_table = pd.DataFrame(gp_rows)
best_gp_row = gp_table.loc[gp_table["validation_rmse_bp"].idxmin()]
best_gp_setting = (
    float(best_gp_row["length_scale"]),
    float(best_gp_row["noise_variance_bp2"]),
)
gp_model = gp_models[best_gp_setting]
gp_prediction = gp_model.predict(features[split.validation])
display(gp_table)
print("selected GP setting:", best_gp_setting)
print("selection-period empirical 90% coverage:", best_gp_row["validation_coverage90"])
print("fit rows:", len(gp_train))
"""),
    code("""
display_rows = split.validation[:160]
display_prediction = gp_model.predict(features[display_rows])
display_dates = pd.to_datetime(forecast.prediction_dates[display_rows])
fig = go.Figure()
fig.add_scatter(
    x=np.r_[display_dates, display_dates[::-1]],
    y=np.r_[
        display_prediction.mean + z90 * display_prediction.standard_deviation,
        (display_prediction.mean - z90 * display_prediction.standard_deviation)[::-1],
    ],
    fill="toself",
    line={"color": "rgba(0,0,0,0)"},
    fillcolor="rgba(76,120,168,0.2)",
    name="model-based 90% interval",
)
fig.add_scatter(x=display_dates, y=display_prediction.mean, name="GP mean", mode="lines")
fig.add_scatter(
    x=display_dates,
    y=target[display_rows],
    name="actual",
    mode="lines",
    line={"color": "black", "width": 1},
)
fig.update_layout(
    title="GP uncertainty is model-based and must be coverage-audited",
    xaxis_title="Prediction date",
    yaxis_title="Next-day change (bp)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 3. Compute budget

dense kernel solveはfit rowsを $n$ としてmemory $O(n^2)$、time $O(n^3)$である。ridgeが全historyを使う一方、GPは固定300行subsetであることを比較表に残す。これは同じmodel capacityではない。

## 4. 失敗モード

- explicit matrix inverseを作る
- full history GPを暗黙に要求しruntimeを記録しない
- subsetを変えながらscoreだけ比較する
- posterior standard deviationをdistribution-free intervalと呼ぶ
- length scaleをtestで選ぶ

## 5. 段階別演習

### 基礎

1. kernel ridge dual solutionを導出せよ。
2. GP posterior meanとvarianceのsolve順序を書け。

### 標準

3. fit rowsを150、300、500へ変えruntimeを比較せよ。
4. noise varianceとcoverageの関係をvalidationで調べよ。

### 研究

5. inducing-point近似の計算量と誤差を設計せよ。
6. nonstationary kernelが必要な証拠をbreak前後で検討せよ。

## 6. Exit Criteria

- [ ] RBF kernelとkernel ridgeを説明できる
- [ ] Cholesky solveでGP predictionを計算できる
- [ ] fit subsetとruntimeを記録できる
- [ ] uncertaintyとempirical coverageを区別できる
- [ ] length scaleをvalidationだけで選べる

## 7. 出典

- [Gaussian Processes for Machine Learning](https://gaussianprocess.org/gpml/) — kernel、posterior、marginal likelihood、計算量
- [SciPy Cholesky](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.cholesky.html) — positive-definite solveの公式API
- [The Elements of Statistical Learning](https://hastie.su.domains/ElemStatLearn/) — kernel methodとregularization
"""),
]
