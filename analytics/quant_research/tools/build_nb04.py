"""Builder for notebook 04: regularization and curve fitting."""

from nbkit import code, md

cells = [
    md(r"""
# 04. Week 4 — 正則化と金利カーブfit

> 点を通る曲線ではなく、目的と制約が説明できる曲線を作る。

## 学習目標

- ridge/Tikhonov正則化を幾何・固有方向・matrix calculusで説明する
- polynomial、truncated-power spline、Nelson–Siegel basisを比較する
- 固定decayならNelson–Siegelが係数に線形な最小二乗になることを示す
- 学習内RMSE、weighted RMSE、leave-one-out RMSEを区別する
- yield curve fitとcoupon bond price fitを区別する

## 前提知識

- Week 1のleast squaresとWLS
- Week 2の条件数とSVD
- Week 3のlevel-like、slope-like、curvature-like loading
"""),
    code("""
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from scipy.optimize import LinearConstraint, minimize

from quant_textbook import (
    fit_curve,
    leave_one_out_predictions,
    leave_one_out_rmse,
    polynomial_basis,
    predict_curve,
    price_coupon_bond,
    truncated_power_cubic_spline_basis,
    weighted_rmse,
)

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260809
"""),
    md(r"""
## 1. 直感と導出 — Ridgeは弱い方向を抑える

ridge目的関数を

$$
L(\beta)=\lVert y-X\beta\rVert_2^2+\alpha\lVert\beta\rVert_2^2,
\qquad \alpha\ge 0
$$

とする。勾配とHessianは

$$
\nabla_\beta L=-2X^\top y+2X^\top X\beta+2\alpha\beta,
\qquad
\nabla_\beta^2L=2(X^\top X+\alpha I)
$$

で、解は

$$
(X^\top X+\alpha I)\hat\beta_\alpha=X^\top y
$$

を満たす。SVD方向で見ると第 $j$ 成分は

$$
\frac{\sigma_j}{\sigma_j^2+\alpha}u_j^\top y
$$

となる。$\sigma_j$ が小さい不安定方向ほど強く縮む。ridgeはvarianceを減らす代わりにbiasを入れる。
"""),
    md(r"""
## 2. Curve basisという設計選択

満期 $\tau$ のzero yieldをbasisの線形結合で表す。

$$
\hat y(\tau)=\sum_{j=1}^{p}\beta_j\phi_j(\tau)
$$

- polynomial: 単純だが高次数・長い満期範囲でill-conditionedになりやすい
- truncated-power cubic spline: localな曲率を表現しやすいがknotとpenaltyが必要
- Nelson–Siegel: level、slope、curvature-likeな3 basisで低次元

どのbasisも市場の真理ではない。補間、平滑化、価格評価、factor解釈のどれが目的かで比較基準が変わる。
"""),
    md(r"""
## 3. 固定decayのNelson–Siegel

decayを $\lambda>0$ とし、loadingを

$$
\begin{aligned}
\phi_0(\tau)&=1,\\
\phi_1(\tau)&=\frac{1-e^{-\lambda\tau}}{\lambda\tau},\\
\phi_2(\tau)&=\frac{1-e^{-\lambda\tau}}{\lambda\tau}-e^{-\lambda\tau}
\end{aligned}
$$

と置く。curveは

$$
y(\tau)=\beta_0\phi_0(\tau)+\beta_1\phi_1(\tau)+\beta_2\phi_2(\tau)
$$

である。$\lambda$ を固定すれば未知なのは $\beta$ だけなので線形最小二乗になる。$\lambda$ まで同時推定すると非線形・一般に非凸で、初期値やlocal minimumの診断が必要になる。本章では固定値または事前に定めたgridだけを使う。
"""),
    code("""
def nelson_siegel_curve(maturities, coefficients, decay):
    maturities = np.asarray(maturities, dtype=float)
    scaled = decay * maturities
    slope_loading = -np.expm1(-scaled) / scaled
    curvature_loading = slope_loading - np.exp(-scaled)
    basis = np.column_stack([np.ones_like(maturities), slope_loading, curvature_loading])
    return basis @ np.asarray(coefficients, dtype=float)


rng = np.random.default_rng(RANDOM_SEED)
maturities = np.array([0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30], dtype=float)
true_coefficients = np.array([0.0120, -0.0100, 0.0180])
fixed_decay = 0.45
true_yields = nelson_siegel_curve(maturities, true_coefficients, fixed_decay)
bid_ask_spreads = np.array([1.0, 0.8, 0.7, 0.7, 0.8, 1.0, 1.2, 1.8, 2.4, 3.0]) * 1e-4
observed_yields = true_yields + rng.normal(scale=0.35 * bid_ask_spreads)
precision_weights = 1.0 / bid_ask_spreads**2

print("yield range (%):", 100 * observed_yields.min(), 100 * observed_yields.max())
"""),
    md(r"""
spreadはyield単位で合成した不確実性proxyである。実際のbond bid–ask priceをyield spreadへ変換するにはdurationが効くため、単純な同一視はしない。
"""),
    code("""
models = {
    "Polynomial degree 5": fit_curve(
        maturities,
        observed_yields,
        basis="polynomial",
        degree=5,
        method="svd",
    ),
    "Cubic spline": fit_curve(
        maturities,
        observed_yields,
        basis="spline",
        knots=(2.0, 5.0, 10.0, 20.0),
        ridge=1e-5,
        method="svd",
    ),
    "Nelson-Siegel": fit_curve(
        maturities,
        observed_yields,
        basis="nelson_siegel",
        decay=fixed_decay,
        weights=precision_weights,
        method="svd",
    ),
}

evaluation_grid = np.linspace(0.25, 30.0, 240)
fig = go.Figure()
fig.add_scatter(
    x=maturities,
    y=100 * observed_yields,
    mode="markers",
    name="Observed synthetic yields",
    marker={"size": 10, "color": "black"},
)
fig.add_scatter(
    x=evaluation_grid,
    y=100 * nelson_siegel_curve(evaluation_grid, true_coefficients, fixed_decay),
    mode="lines",
    name="Latent curve",
    line={"dash": "dash", "color": "gray"},
)
for name, model in models.items():
    fig.add_scatter(
        x=evaluation_grid,
        y=100 * predict_curve(model, evaluation_grid),
        mode="lines",
        name=name,
    )
fig.update_layout(
    title="Basis choice changes interpolation between observations",
    xaxis_title="Maturity (years)",
    yaxis_title="Zero yield (%)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
観測点の近くで3モデルが似ていても、短端・長端・点の間で曲線は異なる。in-sampleの点だけではbasis選択を識別できないことがある。
"""),
    md(r"""
## 4. Fit指標とvalidation指標を分ける

通常のRMSEは

$$
\operatorname{RMSE}=\sqrt{\frac{1}{n}\sum_{i=1}^n(y_i-\hat y_i)^2}
$$

である。重み $w_i>0$ を使うなら

$$
\operatorname{WRMSE}
=\sqrt{\frac{\sum_iw_i(y_i-\hat y_i)^2}{\sum_iw_i}}
$$

と正規化を明示する。leave-one-outでは1点を除いてfitし、その点を予測する操作を全点で繰り返す。学習内RMSEとLOO RMSEは同じ表の別列に置く。
"""),
    code("""
for name, model in models.items():
    fitted = predict_curve(model, maturities)
    in_sample_rmse_bp = 1e4 * np.sqrt(np.mean((observed_yields - fitted) ** 2))
    weighted_rmse_bp = 1e4 * weighted_rmse(
        observed_yields,
        fitted,
        precision_weights,
    )
    if name == "Polynomial degree 5":
        loo = leave_one_out_rmse(
            maturities,
            observed_yields,
            basis="polynomial",
            degree=5,
            method="svd",
        )
    elif name == "Cubic spline":
        loo = leave_one_out_rmse(
            maturities,
            observed_yields,
            basis="spline",
            knots=(2.0, 5.0, 10.0, 20.0),
            ridge=1e-5,
            method="svd",
        )
    else:
        loo = leave_one_out_rmse(
            maturities,
            observed_yields,
            basis="nelson_siegel",
            decay=fixed_decay,
            weights=precision_weights,
            method="svd",
        )
    print(
        f"{name:>20s} | in-sample={in_sample_rmse_bp:6.3f} bp "
        f"weighted={weighted_rmse_bp:6.3f} bp LOO={1e4 * loo:6.3f} bp"
    )
"""),
    md(r"""
### 4.1 高次数多項式のLOO失敗を数値化する

点をよく通ることと、除外した満期を予測できることは別である。degree 7の無正則化modelについて、学習内RMSE、LOO RMSE、その比、最悪のheld-out tenorを同時に出す。端点を除いたfitから端点を予測する操作は外挿になるため、長端の誤差が支配し得る。
"""),
    code("""
high_degree_model = fit_curve(
    maturities,
    observed_yields,
    basis="polynomial",
    degree=7,
    method="svd",
)
high_degree_training_rmse_bp = 1e4 * np.sqrt(
    np.mean((observed_yields - predict_curve(high_degree_model, maturities)) ** 2)
)
high_degree_loo_predictions = leave_one_out_predictions(
    maturities,
    observed_yields,
    basis="polynomial",
    degree=7,
    method="svd",
)
absolute_holdout_errors_bp = 1e4 * np.abs(
    observed_yields - high_degree_loo_predictions
)
high_degree_loo_rmse_bp = np.sqrt(np.mean(absolute_holdout_errors_bp**2))
worst_holdout = int(np.argmax(absolute_holdout_errors_bp))

print("training RMSE (bp):", high_degree_training_rmse_bp)
print("LOO RMSE (bp):", high_degree_loo_rmse_bp)
print("LOO / training ratio:", high_degree_loo_rmse_bp / high_degree_training_rmse_bp)
print(
    "worst held-out maturity and absolute error:",
    maturities[worst_holdout],
    "years,",
    absolute_holdout_errors_bp[worst_holdout],
    "bp",
)

fig = go.Figure(
    go.Bar(
        x=maturities,
        y=absolute_holdout_errors_bp,
        name="Absolute held-out error",
    )
)
fig.update_layout(
    title="Degree-7 polynomial leave-one-out errors by maturity",
    xaxis_title="Held-out maturity (years)",
    yaxis_title="Absolute error (bp, log scale)",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
LOOでもmodel specificationをデータ全体から選んだ後なら、完全な学習外評価ではない。degree、knot、decay、ridgeを比較する場合は、選択手順までvalidation loopの内側へ入れる。

上の比率と満期別誤差が大きいとき、低い学習内RMSEは過適合の証拠になる。とくに端点LOOは補間ではなく外挿を含むため、「どの満期を予測する評価か」までmetricの定義に含める。
"""),
    md(r"""
## 5. Ridge path

正則化強度を1点だけ試して採用しない。係数norm、学習内誤差、LOO誤差、曲線形状がどこで安定するかを見る。
"""),
    code("""
ridge_grid = np.logspace(-10, -1, 16)
coefficient_norms = []
training_errors = []
loo_errors = []

for ridge_value in ridge_grid:
    model = fit_curve(
        maturities,
        observed_yields,
        basis="polynomial",
        degree=7,
        ridge=ridge_value,
        method="svd",
    )
    coefficient_norms.append(np.linalg.norm(model.coefficients))
    training_errors.append(
        1e4 * np.sqrt(np.mean((observed_yields - predict_curve(model, maturities)) ** 2))
    )
    loo_errors.append(
        1e4
        * leave_one_out_rmse(
            maturities,
            observed_yields,
            basis="polynomial",
            degree=7,
            ridge=ridge_value,
            method="svd",
        )
    )

fig = go.Figure()
fig.add_scatter(x=ridge_grid, y=training_errors, mode="lines+markers", name="Training RMSE")
fig.add_scatter(x=ridge_grid, y=loo_errors, mode="lines+markers", name="LOO RMSE")
fig.add_scatter(
    x=ridge_grid,
    y=coefficient_norms,
    mode="lines+markers",
    name="Coefficient norm",
    yaxis="y2",
)
fig.update_layout(
    title="Regularization path for a high-degree polynomial",
    xaxis_title="Ridge penalty",
    yaxis={"title": "Error (bp)", "type": "log"},
    yaxis2={
        "title": "Coefficient norm",
        "type": "log",
        "overlaying": "y",
        "side": "right",
    },
    xaxis_type="log",
    template="plotly_white",
)
fig.show()

best_ridge_index = int(np.argmin(loo_errors))
print("minimum-LOO ridge:", ridge_grid[best_ridge_index])
print("minimum LOO RMSE (bp):", loo_errors[best_ridge_index])
print("coefficient norm at minimum LOO:", coefficient_norms[best_ridge_index])
print("path endpoint norm ratio:", coefficient_norms[-1] / coefficient_norms[0])
"""),
    md(r"""
係数normは正則化に伴うstabilityの診断であり、小さければ自動的に良いわけではない。LOO誤差と曲線形状を同じpath上で見て、biasを増やしすぎていないか確認する。
"""),
    md(r"""
## 6. 実務的な平滑化penalty

係数ridgeはbasis係数を一様に縮める。一方、曲線のroughnessを直接抑えたいなら、密なgrid上の二階差分を使って

$$
\min_\beta \lVert y-X\beta\rVert_2^2
+\lambda_s\lVert R\beta\rVert_2^2,
\qquad
R=\sqrt{h}D_2B_g
$$

を解ける。$B_g$ はgrid上のbasis、$D_2$ は刻み $h$ でscaleした二階差分operatorである。これは曲率二乗積分の離散近似で、levelとslopeを直接縮めずにwiggleを罰する。
"""),
    code("""
spline_knots = (2.0, 5.0, 10.0, 20.0)
basis_location = float(maturities.min())
basis_scale = float(np.ptp(maturities))
spline_design = truncated_power_cubic_spline_basis(
    maturities,
    spline_knots,
    location=basis_location,
    scale=basis_scale,
)
smoothness_grid = np.linspace(maturities.min(), maturities.max(), 240)
spline_grid_design = truncated_power_cubic_spline_basis(
    smoothness_grid,
    spline_knots,
    location=basis_location,
    scale=basis_scale,
)

normalized_step = (smoothness_grid[1] - smoothness_grid[0]) / basis_scale
second_difference = np.zeros((smoothness_grid.size - 2, smoothness_grid.size))
row_indices = np.arange(smoothness_grid.size - 2)
second_difference[row_indices, row_indices] = 1.0
second_difference[row_indices, row_indices + 1] = -2.0
second_difference[row_indices, row_indices + 2] = 1.0
second_difference /= normalized_step**2
roughness_operator = np.sqrt(normalized_step) * second_difference @ spline_grid_design

unpenalized_coefficients = np.linalg.lstsq(
    spline_design,
    observed_yields,
    rcond=None,
)[0]
smoothness_penalty = 1e-6
augmented_design = np.vstack(
    [spline_design, np.sqrt(smoothness_penalty) * roughness_operator]
)
augmented_target = np.concatenate(
    [observed_yields, np.zeros(roughness_operator.shape[0])]
)
smoothed_coefficients = np.linalg.lstsq(
    augmented_design,
    augmented_target,
    rcond=None,
)[0]

unpenalized_curve = spline_grid_design @ unpenalized_coefficients
smoothed_curve = spline_grid_design @ smoothed_coefficients
for label, coefficients, curve in (
    ("Unpenalized", unpenalized_coefficients, unpenalized_curve),
    ("Smoothness-penalized", smoothed_coefficients, smoothed_curve),
):
    training_rmse_bp = 1e4 * np.sqrt(
        np.mean((observed_yields - spline_design @ coefficients) ** 2)
    )
    curvature_rms = np.sqrt(np.mean((second_difference @ curve) ** 2))
    print(label, "training RMSE (bp):", training_rmse_bp, "curvature RMS:", curvature_rms)

fig = go.Figure()
fig.add_scatter(
    x=maturities,
    y=100 * observed_yields,
    mode="markers",
    name="Observed synthetic yields",
    marker={"size": 10, "color": "black"},
)
fig.add_scatter(
    x=smoothness_grid,
    y=100 * unpenalized_curve,
    mode="lines",
    name="Unpenalized spline",
)
fig.add_scatter(
    x=smoothness_grid,
    y=100 * smoothed_curve,
    mode="lines",
    name="Second-difference penalty",
)
fig.update_layout(
    title="Spline fit with a direct smoothness penalty",
    xaxis_title="Maturity (years)",
    yaxis_title="Zero yield (%)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
上の $\lambda_s$ は説明用の固定値であり、表示結果から都合よく採用しない。実際には候補値、評価指標、許容roughnessを事前に定め、選択手順をvalidationの内側へ入れる。

### 6.1 線形不等式付きleast squares

正のrate regimeでnon-negative forward rateをguardrailにするなら、continuous compoundingの

$$
D(\tau)=\exp[-\tau y(\tau)]
$$

が満期とともに増えない条件を、grid上で

$$
\Delta[\tau\hat y(\tau)]=A\beta\ge 0
$$

と書ける。basis係数に対する線形制約なので、least-squares目的と一緒に解ける。ここではwiggleしやすいdegree 8 polynomialへ適用し、solver status、制約違反数、fit誤差のtrade-offを記録する。
"""),
    code("""
constraint_degree = 8
polynomial_design = polynomial_basis(
    maturities,
    constraint_degree,
    location=basis_location,
    scale=basis_scale,
)
polynomial_grid_design = polynomial_basis(
    smoothness_grid,
    constraint_degree,
    location=basis_location,
    scale=basis_scale,
)
target_yields_bp = 1e4 * observed_yields
unconstrained_coefficients_bp = np.linalg.lstsq(
    polynomial_design,
    target_yields_bp,
    rcond=None,
)[0]

forward_constraint_matrix = np.diff(
    smoothness_grid[:, None] * polynomial_grid_design,
    axis=0,
)

def constrained_objective(coefficients):
    residuals = polynomial_design @ coefficients - target_yields_bp
    return 0.5 * residuals @ residuals


def constrained_gradient(coefficients):
    residuals = polynomial_design @ coefficients - target_yields_bp
    return polynomial_design.T @ residuals


feasible_start = np.zeros(constraint_degree + 1)
feasible_start[0] = target_yields_bp.mean()
constrained_result = minimize(
    constrained_objective,
    feasible_start,
    jac=constrained_gradient,
    constraints=[LinearConstraint(forward_constraint_matrix, 0.0, np.inf)],
    method="SLSQP",
    options={"ftol": 1e-12, "maxiter": 2000},
)
if not constrained_result.success:
    raise RuntimeError(constrained_result.message)

unconstrained_curve_bp = polynomial_grid_design @ unconstrained_coefficients_bp
constrained_curve_bp = polynomial_grid_design @ constrained_result.x
unconstrained_forward_steps = np.diff(smoothness_grid * unconstrained_curve_bp)
constrained_forward_steps = np.diff(smoothness_grid * constrained_curve_bp)
constraint_tolerance = -1e-7

print("solver success:", constrained_result.success)
print(
    "negative forward steps before / after:",
    np.sum(unconstrained_forward_steps < constraint_tolerance),
    "/",
    np.sum(constrained_forward_steps < constraint_tolerance),
)
print(
    "training RMSE before / after (bp):",
    np.sqrt(
        np.mean(
            (target_yields_bp - polynomial_design @ unconstrained_coefficients_bp) ** 2
        )
    ),
    "/",
    np.sqrt(
        np.mean((target_yields_bp - polynomial_design @ constrained_result.x) ** 2)
    ),
)
print("minimum constrained forward step:", constrained_forward_steps.min())

fig = go.Figure()
fig.add_scatter(
    x=maturities,
    y=100 * observed_yields,
    mode="markers",
    name="Observed synthetic yields",
    marker={"size": 10, "color": "black"},
)
fig.add_scatter(
    x=smoothness_grid,
    y=unconstrained_curve_bp / 100.0,
    mode="lines",
    name="Unconstrained degree 8",
)
fig.add_scatter(
    x=smoothness_grid,
    y=constrained_curve_bp / 100.0,
    mode="lines",
    name="Non-negative-forward constraint",
)
fig.update_layout(
    title="Linear inequality constraints suppress polynomial arbitrage wiggles",
    xaxis_title="Maturity (years)",
    yaxis_title="Zero yield (%)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
この制約は「常に正しい金融法則」ではない。negative-rate regimeではdiscount factorが局所的に増えることがあり、non-negative forwardを無条件に課すと観測を歪める。制約は対象regimeとestimandから選び、solver successだけでなく最大違反量とfit劣化を検査する。制約法の一般論はB4で扱う。
"""),
    md(r"""
## 7. Yield fitとprice fitは別問題

coupon bond価格は、満期yieldを1回割り引けば得られるわけではない。各cash flowを対応する時点のzero rateで割り引く。

$$
P_i=\sum_{j}C_{ij}D(t_{ij}),
\qquad
D(t)=e^{-t z(t)}
$$

ここで $z(t)$ はcontinuous-compounded zero rateである。yield-to-maturityは、1つの内部収益率で複数cash flowをまとめたquoteであり、zero curveとは異なる。
"""),
    code("""
nelson_siegel_model = models["Nelson-Siegel"]
cashflow_times = np.arange(0.5, 5.0 + 0.5, 0.5)
cashflows = np.full(cashflow_times.shape, 100.0 * 0.012 / 2.0)
cashflows[-1] += 100.0

zero_curve = lambda times: predict_curve(nelson_siegel_model, np.asarray(times, dtype=float))
dirty_price = price_coupon_bond(cashflow_times, cashflows, zero_curve)

print("educational dirty price per 100 face:", dirty_price)
"""),
    md(r"""
この価格はcontinuous compounding、半年ごとの規則的cash flow、経過利息なしという教材規約に基づく。実際のJGB評価にはsettlement、day count、coupon schedule、clean/dirty price、丸めなどが必要である。
"""),
    md(r"""
## 8. 失敗モード — decayまで一度に最適化する

固定 $\lambda$ ならNelson–Siegelは線形だが、$\lambda$ も未知にすると非線形になる。最適化が1つの答えを返してもglobal optimumとは限らない。

- 初期値を変えていない
- decayと係数の識別を確認していない
- 学習内RMSEだけでdecayを選ぶ
- 長端外挿を図示していない
- yield RMSEをpricing RMSEと呼ぶ
- 負のrateがあり得るのにdiscount factorの単調減少を無条件に課す

B1ではdecayを固定し、grid比較は候補生成として扱う。連続最適化と制約診断はB4で扱う。
"""),
    md(r"""
## 9. 段階別演習

### 基礎

1. ridgeの勾配・Hessian・normal equationsを導出せよ。
2. Nelson–Siegelの3 loadingを $\tau\to0$ と $\tau\to\infty$ で評価せよ。
3. 同じcurveをyieldとdiscount factorで可視化せよ。

### 標準

4. polynomial degreeとridgeの2次元gridを作り、nested LOOで選択せよ。
5. bid–ask weightを外した場合に短端・長端のfitがどう変わるか比較せよ。
6. fixed decayを0.2–1.5でgrid searchし、係数安定性とLOO誤差を同時に描け。

### 研究

7. smoothness penaltyをgrid比較し、学習誤差、LOO誤差、curvature RMSのtrade-offを論じよ。
8. negative-rate curveでdiscount factor単調制約が不適切になる反例を作れ。
"""),
    md(r"""
## 10. Exit Criteria

- [ ] ridgeをbias–varianceと特異方向の両方から説明できる
- [ ] fixed-decay Nelson–Siegelが線形最小二乗であることを説明できる
- [ ] training、weighted、LOO RMSEを区別できる
- [ ] ridge pathで係数normとLOO誤差を併せて診断できる
- [ ] 二階差分penaltyと係数ridgeの違いを説明できる
- [ ] 制約付きfitでsolver status、違反量、fit劣化を検査できる
- [ ] yield curveからcoupon cash flowを価格評価できる
- [ ] 合成価格規約を実務JGB規約と呼ばない
"""),
    md(r"""
## 11. 出典

- [BIS Papers No. 25: Zero-coupon yield curves](https://www.bis.org/publ/bppdf/bispap25.htm) — discount factor、spot/forward rate、Nelson–Siegel系手法
- [BIS: Technical note on Japanese government securities](https://www.bis.org/publ/bppdf/bispap25h.pdf) — JGB cash flowとcurve推定の入力・慣行
- [Federal Reserve: Supervisory Stress Test Methodology, Market Risk Models](https://www.federalreserve.gov/supervisionreg/files/market-risk-models.pdf) — fixed-shape Nelson–Siegelのlevel/slope/curvature loading
- [財務省 Interest Rate Q&A](https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/qa.htm) — prevailing yieldとconstant-maturity yield curve
- [SciPy optimize.LinearConstraint](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.LinearConstraint.html) — 線形上下限制約の公式API
- [SciPy SLSQP](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html) — 制約付き最適化のsolver規約とstatus
- [SciPy `interpolate.LSQUnivariateSpline`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.LSQUnivariateSpline.html) — least-squares splineの公式API

次章では、yield教育モードとcoupon bond価格モードを分け、B1の診断を1つのJGB-like projectへ統合する。
"""),
]
