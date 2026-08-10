"""Builder for notebook 23: the B4 constrained discount-curve project."""

from nbkit import code, md

cells = [
    md(r"""
# 23. B4 Project — Constrained Yield Curve Fitter

> coupon bondの価格をcash-flow node上のdiscount factorへ線形に写し、凸性、KKT、負金利境界、LOOを一つの監査memoへつなぐ。

## 学習目標

- `CouponBondUniverse`をbond-by-node cash-flow matrixへ変換する
- discount factorを変数とするbid–ask weighted smooth QPを導出する
- $D_j\ge10^{-8}$をhard constraintとして元の単位で検査する
- discount-factor monotonicityを非負forward rate仮定の任意制約に限定する
- primal / dual feasibility、stationarity、complementarity、duality gapを再計算する
- solver disagreement、objective scaling、leave-one-bond-out pricing errorを報告する
- B1のnonlinear basis calibrationとB4のdiscount-node QPのconvexity境界を説明する
- synthetic evidenceの範囲を2〜4ページmemoのclaim boundaryへ落とす

## 前提知識

- B1 Projectのzero rate、YTM、discount factor、dirty priceの区別
- Week 13のQP、scaling、feasibility
- Week 14のKKT sign conventionとduality gap
- Week 15–16のalgorithm trace、数値契約、再現性

## 重要な範囲制約

本章はseed固定の合成JGB-like universeだけを使う。settlement、day count、accrued interest、税、実quote timestampを省略しており、実務curveまたは投資推奨ではない。
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from quant_textbook.bonds import (
    CouponBondUniverse,
    fit_bond_price_curve,
    leave_one_bond_out_price_rmse,
    make_synthetic_jgb_universe,
    predict_bond_prices,
)
from quant_textbook.constrained_curves import (
    bond_cashflow_matrix,
    fit_constrained_bond_discount_curve,
    predict_prices_from_discounts,
    second_difference_matrix,
)
from quant_textbook.convex import (
    QuadraticProgram,
    solve_quadratic_program,
)

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
NOTEBOOK_ID = 23
TASK_IDS = {
    "universe": 1,
    "negative_rate": 2,
}
GENERALIZATION_SUPPORT_THRESHOLD_HALF_SPREADS = 2.0


def task_rng(task_name, *coordinates):
    entropy = [
        RANDOM_SEED,
        NOTEBOOK_ID,
        TASK_IDS[task_name],
        *(int(coordinate) for coordinate in coordinates),
    ]
    return np.random.default_rng(np.random.SeedSequence(entropy))
"""),
    md(r"""
## 1. Pre-analysis specification

結果を見る前にvariable、objective、constraint、selection ruleを固定する。

| Field | Primary specification |
|---|---|
| observations | 合成fixed-coupon bondのdirty mid price |
| decision variable | 全sampleのunique cash-flow time上の$D(t_j)$ |
| price map | $\widehat P=CD$ |
| price uncertainty proxy | 合成price half-spread $s_i$ |
| data fit | $\frac12\sum_i\{(C_iD-P_i)/s_i\}^2$ |
| smoothness | adjacent time-divided slope differenceのL2 penalty |
| required hard constraint | $D_j\ge\epsilon_D=10^{-8}$。数値floorでありeconomic boundではない |
| optional constraint | $D(0)=1$をanchorとして$D_1\le1$かつ$D_{j+1}\le D_j$。非負forward rateを仮定する場合のみ |
| primary monotonicity | off。正のdiscount factorだけを要求 |
| solver audit | SLSQPをprimary、trust-constr disagreementをsecondary |
| simple baseline | B1 fixed-decay Nelson–Siegelのleave-one-bond-out price RMSE |
| generalization metric | full-sample node grid固定LOOの$\sqrt{n^{-1}\sum_i(e_i/s_i)^2}$ |
| precommitted support gate | standardized LOO RMSE $\le 2.0$ half-spreads |
| in-sample claim | この合成universeに対する数値的に監査済みのpricing fit |
| out-of-sample claim | 上のsupport gateを満たすときだけ、この合成cross-sectionで支持 |
| disallowed claim | 実JGB curve、普遍的no-arbitrage、将来価格予測 |

smoothness ratioはfull sampleのoperator scaleから一度決める。LOO結果を見た後にprimary ratioを調整せず、各foldでもheld-out errorを使って選び直さない。support gateを先に固定するため、悪い結果もそのままclaimへ反映する。
"""),
    md(r"""
## 2. discount-node formulationとconvexity

bond $i$、cash-flow node $j$の金額を$C_{ij}$、dirty priceを$p_i$、half-spreadを$s_i>0$とする。$W=\operatorname{diag}(s_i^{-2})$とする。不等間隔nodeでは$L$のrowを

$$
(LD)_j=\frac{D_{j+1}-D_j}{t_{j+1}-t_j}
-\frac{D_j-D_{j-1}}{t_j-t_{j-1}}
$$

というadjacent divided-slope differenceにする。従ってtime-linearなdiscount curveはirregular gridでも$L$のnull spaceに入る。これを使って

$$
\min_D\quad
\frac12(CD-p)^\top W(CD-p)
+\frac{\rho}{2}\|LD\|_2^2
$$

を解く。定数$\frac12p^\top Wp$を除くと

$$
\frac12D^\top QD+q^\top D,
\qquad
Q=C^\top WC+\rho L^\top L\succeq0,
\quad q=-C^\top Wp.
$$

$C$、$W$、$L$が固定され、constraintがaffineなのでconvex QPである。$Q$がpositive definiteならprimal solutionは一意である。singularな場合、solver間の$D$差だけでfailにせず、price、objective、KKTを優先し、非一意性を報告する。

positive discount factorは将来cash flowの正のpresent-value weightを表す。しかし、この簡略QPの$D>0$だけを現実市場の全てのno-arbitrage conditionと呼ばない。
"""),
    md(r"""
## 3. 合成CouponBondUniverseとquote contract

B1と同じ10本のmaturityを使い、dirty priceへ小さな合成noiseを加える。quote幅が存在するため、price residualをhalf-spreadで標準化する。実dataではmid / bid / ask、timestamp、staleness、source licenseを別途監査する。
"""),
    code("""
universe = make_synthetic_jgb_universe(
    price_noise_std=0.006,
    seed=task_rng("universe"),
)
bond_table = universe.bonds.copy()
bond_table["price_half_spread"] = 0.014 + 0.0012 * bond_table["maturity_years"]
universe = CouponBondUniverse(
    bonds=bond_table,
    cashflows=universe.cashflows.copy(),
)

display(
    bond_table[
        [
            "bond_id",
            "maturity_years",
            "coupon_rate",
            "dirty_price",
            "price_half_spread",
        ]
    ].round(6)
)
assert (bond_table["dirty_price"] > 0.0).all()
assert (bond_table["price_half_spread"] > 0.0).all()
"""),
    md(r"""
## 4. cash-flow matrixを独立に監査する

library helperでmatrix contractを作る一方、Notebookでもlong-form cash flowから$C$を独立再構成する。各bond priceはcouponとprincipalを同じnode discount factorで評価し、YTMをcash-flowごとのzero rateとして使わない。
"""),
    code("""
cashflow_contract = bond_cashflow_matrix(
    universe,
    quote_width_column="price_half_spread",
)

bond_ids = tuple(bond_table["bond_id"])
node_times = np.sort(universe.cashflows["payment_time"].unique().astype(float))
manual_cashflow_matrix = np.zeros((len(bond_ids), node_times.size), dtype=float)
bond_index = {bond_id: index for index, bond_id in enumerate(bond_ids)}

for row in universe.cashflows.itertuples(index=False):
    node_index = int(np.searchsorted(node_times, float(row.payment_time)))
    if node_index == node_times.size or not np.isclose(
        node_times[node_index],
        float(row.payment_time),
        rtol=0.0,
        atol=1.0e-12,
    ):
        raise RuntimeError("cash-flow time did not map to a declared node")
    manual_cashflow_matrix[bond_index[row.bond_id], node_index] += float(row.cashflow)

np.testing.assert_allclose(
    cashflow_contract.cashflows,
    manual_cashflow_matrix,
    rtol=0.0,
    atol=0.0,
)
np.testing.assert_allclose(cashflow_contract.node_times, node_times, rtol=0.0, atol=0.0)

cashflow_audit = pd.DataFrame(
    {
        "bond_id": bond_ids,
        "nonzero_nodes": np.count_nonzero(manual_cashflow_matrix, axis=1),
        "final_cashflow": manual_cashflow_matrix.max(axis=1),
        "row_cashflow_total": manual_cashflow_matrix.sum(axis=1),
    }
)
display(cashflow_audit)
print("matrix shape:", manual_cashflow_matrix.shape)
print("node range (years):", node_times.min(), node_times.max())
"""),
    md(r"""
matrixのzeroはcash flowがないことを表し、missing quoteではない。LOOではfull-sample node gridを固定し、held-out bondのmaturity nodeがtraining dataに弱く識別される可能性もgeneralization errorへ含める。
"""),
    md(r"""
## 5. primary constrained fit

minimum discountを$10^{-8}$、monotonicityをoffにしてfitする。通常のdiscount factorが$O(1)$であるのに対し、$10^{-8}$は8桁小さく、`log(D)`とsolver domainを有限に保つための数値floorである。30年nodeでも$-\log(10^{-8})/30\approx61.4\%$の連続複利zero rateに相当する極端な下限であり、合理的な経済boundや完全なno-arbitrage conditionとは解釈しない。

smoothnessはdata Hessianとtime-aware divided-slope Hessianのoperator scaleを使って無次元の比率から固定する。primary ratioはこの後のLOO結果を見ても変更しない。
"""),
    code("""
price_half_spreads = bond_table["price_half_spread"].to_numpy()
price_weights = 1.0 / price_half_spreads**2
roughness_operator = second_difference_matrix(node_times)
weighted_design = np.sqrt(price_weights)[:, None] * manual_cashflow_matrix
data_hessian = weighted_design.T @ weighted_design
roughness_hessian = roughness_operator.T @ roughness_operator
SMOOTHNESS_RATIO = 2.0e-4
SMOOTHNESS_STRENGTH = SMOOTHNESS_RATIO * np.linalg.norm(
    data_hessian,
    ord=2,
) / max(np.linalg.norm(roughness_hessian, ord=2), 1.0)
MINIMUM_DISCOUNT = 1.0e-8
floor_implied_rate_at_longest_node = (
    -np.log(MINIMUM_DISCOUNT) / float(node_times.max())
)

# The operator must annihilate every discount curve linear in actual time,
# including on an irregular grid.
np.testing.assert_allclose(
    roughness_operator @ (1.0 - 0.01 * node_times),
    0.0,
    rtol=0.0,
    atol=5.0e-15,
)

primary_fit = fit_constrained_bond_discount_curve(
    universe,
    quote_width_column="price_half_spread",
    smoothness=SMOOTHNESS_STRENGTH,
    minimum_discount=MINIMUM_DISCOUNT,
    monotone=False,
    method="SLSQP",
)

recomputed_prices = predict_prices_from_discounts(
    cashflow_contract.cashflow_matrix,
    primary_fit.discount_factors,
)
np.testing.assert_allclose(
    recomputed_prices,
    primary_fit.fitted_prices,
    rtol=1.0e-12,
    atol=1.0e-10,
)

discount_table = pd.DataFrame(
    {
        "maturity_years": primary_fit.node_times,
        "discount_factor": primary_fit.discount_factors,
        "continuous_zero_rate_percent": -100.0
        * np.log(primary_fit.discount_factors)
        / primary_fit.node_times,
    }
)
display(discount_table.iloc[::6].round(8))
print("smoothness strength:", SMOOTHNESS_STRENGTH)
print("precommitted smoothness ratio:", SMOOTHNESS_RATIO)
print("minimum discount factor:", primary_fit.discount_factors.min())
print(
    "floor-implied rate at longest node (%):",
    100.0 * floor_implied_rate_at_longest_node,
)
print("optimizer and KKT accepted:", primary_fit.qp_solution.success)
"""),
    code("""
fig = go.Figure()
fig.add_scatter(
    x=primary_fit.node_times,
    y=primary_fit.discount_factors,
    mode="lines+markers",
    name="Constrained discount factors",
)
fig.add_hline(
    y=1.0,
    line_dash="dot",
    annotation_text="D = 1 reference",
)
fig.update_layout(
    title="Positive discount-factor nodes fitted in price space",
    xaxis_title="Cash-flow time (years)",
    yaxis_title="Discount factor",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
zero rateはdiscount factorから事後的に計算した表示値であり、QPのdecision variableではない。$t=0$はvariable gridに含めず、既知の$D(0)=1$を図のreferenceとして示す。
"""),
    md(r"""
## 6. raw feasibilityとKKT全residual

QPのcanonical signは

$$
\min_D\ \frac12D^\top QD+q^\top D,
\qquad GD\le h,
\qquad D\ge\epsilon_D
$$

である。positive boundのLagrangian termは$\mu_L^\top(\epsilon_D-D)$、$\mu_L\ge0$とする。solver statusと独立にfour KKT familiesを読む。
"""),
    code("""
kkt = primary_fit.qp_solution.diagnostics.kkt
curve_diagnostics = primary_fit.diagnostics
raw_positive_violation = curve_diagnostics.maximum_discount_floor_violation
hard_constraints_passed = curve_diagnostics.hard_constraints_passed

kkt_table = pd.DataFrame(
    [
        {"family": "primal inequality", "normalized_residual": kkt.primal_inequality},
        {"family": "primal equality", "normalized_residual": kkt.primal_equality},
        {"family": "primal bounds", "normalized_residual": kkt.primal_bounds},
        {"family": "dual feasibility", "normalized_residual": kkt.dual_feasibility},
        {"family": "stationarity", "normalized_residual": kkt.stationarity},
        {"family": "complementarity", "normalized_residual": kkt.complementarity},
        {"family": "duality gap", "normalized_residual": kkt.duality_gap},
    ]
)
hard_constraint_table = pd.DataFrame(
    [
        {
            "constraint": "minimum discount floor",
            "raw_violation": curve_diagnostics.maximum_discount_floor_violation,
        },
        {
            "constraint": "optional monotonicity",
            "raw_violation": curve_diagnostics.maximum_monotonicity_violation,
        },
        {
            "constraint": "optional D(0)=1 anchor",
            "raw_violation": curve_diagnostics.first_node_anchor_violation,
        },
    ]
)
display(kkt_table)
display(hard_constraint_table)
print("raw D lower-bound violation:", raw_positive_violation)
print(
    "conservative local hard-constraint tolerance summary:",
    curve_diagnostics.hard_constraint_tolerance,
)
print("local hard-constraint gates passed:", hard_constraints_passed)
print("primal / dual objective:", primary_fit.qp_solution.primal_objective, primary_fit.qp_solution.dual_objective)
assert hard_constraints_passed
assert kkt.passed
"""),
    md(r"""
dimensionless KKT toleranceとhard numerical-domain constraintのlocal raw gatesを分けた。floor、monotonicity、$D(0)=1$ anchorはそれぞれ自身のraw単位とscaleでlibraryが検査し、`hard_constraints_passed`へ集約する。表示した`hard_constraint_tolerance`はlocal tolerancesの保守的なsummaryであり、globalな最大discount scaleから手計算した一つの閾値を全constraintへ流用しない。この厳しい数値検査をeconomic lower boundの証拠には転用しない。
"""),
    md(r"""
## 7. price residual、solver disagreement、objective scaling

pricing errorは額面100あたりのraw単位とhalf-spread単位を分ける。次に同じQPをSLSQPとtrust-constrで解き、さらにobjective全体を$10^{-6}$倍した同値problemを解く。scalar objective scalingはargminを変えないが、absolute stopping ruleへ影響し得る。
"""),
    code("""
observed_prices = bond_table["dirty_price"].to_numpy()
price_residuals = observed_prices - primary_fit.fitted_prices
pricing_table = pd.DataFrame(
    {
        "bond_id": bond_ids,
        "maturity_years": bond_table["maturity_years"],
        "observed_price": observed_prices,
        "fitted_price": primary_fit.fitted_prices,
        "residual": price_residuals,
        "residual_in_half_spreads": price_residuals / price_half_spreads,
    }
)
display(pricing_table.round(6))

fig = go.Figure()
fig.add_bar(
    x=pricing_table["maturity_years"],
    y=pricing_table["residual_in_half_spreads"],
    name="Standardized price residual",
)
fig.add_hline(y=0.0, line_color="black")
fig.update_layout(
    title="Pricing residuals in quote-uncertainty units",
    xaxis_title="Bond maturity (years)",
    yaxis_title="Residual / price half-spread",
    template="plotly_white",
)
fig.show()
"""),
    code("""
primary_problem = primary_fit.problem
trust_solution = primary_fit.alternate_qp_solution
assert trust_solution is not None

# Construct one feasible start without reading either optimizer's solution.
# It is a regularized least-squares center plus a fixed, SeedSequence-derived
# perturbation.  Both raw and scaled problems receive the identical vector.
scale_audit_design = np.vstack(
    (
        weighted_design,
        np.sqrt(SMOOTHNESS_STRENGTH) * roughness_operator,
    )
)
scale_audit_target = np.concatenate(
    (
        np.sqrt(price_weights) * observed_prices,
        np.zeros(roughness_operator.shape[0]),
    )
)
scale_audit_center, *_ = np.linalg.lstsq(
    scale_audit_design,
    scale_audit_target,
    rcond=None,
)
scale_perturbation = task_rng("universe", 701).normal(size=node_times.size)
scale_perturbation /= np.max(np.abs(scale_perturbation))
INDEPENDENT_INITIAL_PERTURBATION = 1.0e-6
scale_audit_initial = np.maximum(
    scale_audit_center
    + INDEPENDENT_INITIAL_PERTURBATION * scale_perturbation,
    MINIMUM_DISCOUNT * (1.0 + 1.0e-4),
)
assert np.min(scale_audit_initial) >= MINIMUM_DISCOUNT

raw_restart_solution = solve_quadratic_program(
    primary_problem,
    initial=scale_audit_initial,
    method="SLSQP",
)

OBJECTIVE_SCALE_FACTOR = 1.0e-6
scaled_problem = QuadraticProgram(
    P=OBJECTIVE_SCALE_FACTOR * primary_problem.P,
    q=OBJECTIVE_SCALE_FACTOR * primary_problem.q,
    G=primary_problem.G,
    h=primary_problem.h,
    A=primary_problem.A,
    b=primary_problem.b,
    lower_bounds=primary_problem.lower_bounds,
    upper_bounds=primary_problem.upper_bounds,
    variable_units=primary_problem.variable_units,
    inequality_units=primary_problem.inequality_units,
    equality_units=primary_problem.equality_units,
    objective_unit=primary_problem.objective_unit,
    name="objective_scaled_discount_curve",
)
scaled_solution = solve_quadratic_program(
    scaled_problem,
    initial=scale_audit_initial,
    method="SLSQP",
)

solver_audit = pd.DataFrame(
    [
        {
            "comparison": "SLSQP vs trust-constr",
            "maximum_discount_difference": np.max(
                np.abs(primary_fit.discount_factors - trust_solution.x)
            ),
            "maximum_price_difference": np.max(
                np.abs(
                    manual_cashflow_matrix @ primary_fit.discount_factors
                    - manual_cashflow_matrix @ trust_solution.x
                )
            ),
            "both_KKT_pass": primary_fit.qp_solution.success and trust_solution.success,
        },
        {
            "comparison": "raw vs objective scaled",
            "maximum_discount_difference": np.max(
                np.abs(raw_restart_solution.x - scaled_solution.x)
            ),
            "maximum_price_difference": np.max(
                np.abs(
                    manual_cashflow_matrix @ raw_restart_solution.x
                    - manual_cashflow_matrix @ scaled_solution.x
                )
            ),
            "both_KKT_pass": raw_restart_solution.success and scaled_solution.success,
        },
    ]
)
display(solver_audit)
print(
    "independent start maximum perturbation:",
    np.max(np.abs(scale_audit_initial - scale_audit_center)),
)
print(
    "raw / scaled restart iterations:",
    raw_restart_solution.iterations,
    scaled_solution.iterations,
)
assert solver_audit["both_KKT_pass"].all()
"""),
    md(r"""
solver disagreementはsolution accuracyのstress testであり、二つが一致しただけでmodelが正しいとは言えない。objective-scale比較はprimary optimumをwarm startにせず、regularized least-squares centerから独立に作った同一のperturbed feasible initialをraw / scaled problemへ渡した。$Q$がsingularまたはnearly singularならdiscount node自体が違ってもprice mapが一致し得るため、factor差、price差、objective、KKTを同時に保存する。
"""),
    md(r"""
## 8. leave-one-bond-out evaluation

各foldでbondを一本だけ外し、残りのdirty pricesからfull-sample node grid上のdiscount factorsを再推定する。held-out priceはtrainingに使わない。smoothness strength、minimum discount、monotonicity ruleはfull sampleで固定したものを使う。

支持基準は結果を見る前に固定した

$$
\operatorname{LOO\text{-}RMSE}_{\rm std}
=\sqrt{\frac1n\sum_i\left(\frac{p_i-\widehat p_i^{(-i)}}{s_i}\right)^2}
\le 2.0
$$

である。B1 fixed-decay Nelson–Siegelをsimple baselineにし、packageの`leave_one_bond_out_price_rmse`でunweighted fitのraw RMSEとprecision-weighted fit / evaluationのweighted RMSEを別々に計算する。二つはloss weightingも異なるため、同一predictionに対する二種類の集計とは主張しない。

2.0は合成quote uncertaintyに対してRMS errorを2 half-spreads以内にするという教材上の事前基準であり、市場に普遍的な閾値でもstatistical confidence levelでもない。B4のraw / weighted RMSEは同じprecision-weighted fold predictionsを異なる集計で読んだ値である。
"""),
    code("""
loo_result = primary_fit.leave_one_out
assert loo_result is not None
loo_errors = cashflow_contract.dirty_prices - loo_result.predictions
loo_table = pd.DataFrame(
    {
        "bond_id": cashflow_contract.bond_ids,
        "observed_price": cashflow_contract.dirty_prices,
        "held_out_prediction": loo_result.predictions,
        "held_out_error": loo_errors,
        "held_out_error_in_half_spreads": loo_errors / price_half_spreads,
    }
)
display(loo_table.round(6))

b4_standardized_loo_rmse = float(
    np.sqrt(np.mean(loo_table["held_out_error_in_half_spreads"] ** 2))
)
b4_standardized_from_weighted_rmse = float(
    loo_result.weighted_rmse * np.sqrt(np.mean(price_weights))
)
np.testing.assert_allclose(
    b4_standardized_loo_rmse,
    b4_standardized_from_weighted_rmse,
    rtol=1.0e-12,
    atol=1.0e-12,
)

b1_raw_loo_rmse = leave_one_bond_out_price_rmse(
    universe,
    basis="nelson_siegel",
    decay=0.45,
    weights=None,
    ridge=1.0e-8,
)
b1_weighted_loo_rmse = leave_one_bond_out_price_rmse(
    universe,
    basis="nelson_siegel",
    decay=0.45,
    weights=price_weights,
    ridge=1.0e-8,
)
b1_standardized_loo_rmse = float(
    b1_weighted_loo_rmse * np.sqrt(np.mean(price_weights))
)
generalization_supported = bool(
    b4_standardized_loo_rmse
    <= GENERALIZATION_SUPPORT_THRESHOLD_HALF_SPREADS
)
worst_loo_index = int(
    np.argmax(np.abs(loo_table["held_out_error_in_half_spreads"].to_numpy()))
)
worst_loo_error_half_spreads = float(
    np.abs(loo_table.loc[worst_loo_index, "held_out_error_in_half_spreads"])
)

loo_model_comparison = pd.DataFrame(
    [
        {
            "model": "B1 fixed-decay NS simple baseline",
            "fit_contract": "raw=unweighted fit; weighted=precision-weighted fit",
            "raw_LOO_RMSE_price_units": b1_raw_loo_rmse,
            "weighted_LOO_RMSE_price_units": b1_weighted_loo_rmse,
            "standardized_LOO_RMSE_half_spreads": b1_standardized_loo_rmse,
            "support_threshold_half_spreads": GENERALIZATION_SUPPORT_THRESHOLD_HALF_SPREADS,
            "generalization_supported": (
                b1_standardized_loo_rmse
                <= GENERALIZATION_SUPPORT_THRESHOLD_HALF_SPREADS
            ),
        },
        {
            "model": "B4 discount-node QP",
            "fit_contract": "same precision-weighted fold predictions; two aggregations",
            "raw_LOO_RMSE_price_units": loo_result.rmse,
            "weighted_LOO_RMSE_price_units": loo_result.weighted_rmse,
            "standardized_LOO_RMSE_half_spreads": b4_standardized_loo_rmse,
            "support_threshold_half_spreads": GENERALIZATION_SUPPORT_THRESHOLD_HALF_SPREADS,
            "generalization_supported": generalization_supported,
        },
    ]
)
display(loo_model_comparison)
print("B4 generalization supported:", generalization_supported)
print(
    "worst B4 held-out bond / absolute standardized error:",
    cashflow_contract.bond_ids[worst_loo_index],
    worst_loo_error_half_spreads,
)
assert np.isfinite(loo_result.rmse)
assert loo_result.node_grid_fixed and loo_result.all_fits_accepted
assert loo_result.identified_fits == loo_result.total_fits
assert generalization_supported == (
    b4_standardized_loo_rmse
    <= GENERALIZATION_SUPPORT_THRESHOLD_HALF_SPREADS
)
"""),
    md(r"""
LOOは10本の合成cross-sectionに対するalgorithmic generalization checkであり、時系列out-of-sample testではない。`generalization_supported`はprecommitted thresholdから機械的に決まり、`False`ならin-sample KKT certificateが通っていてもout-of-sample pricing claimを支持しない。長期nodeの識別はheld-out maturityによって弱くなるため、平均だけでなくworst bondとfold別errorを残す。結果を良く見せるためprimary smoothnessを再調整しない。
"""),
    md(r"""
## 9. B1 nonlinear price fitとのconvex boundary

B1は固定decay Nelson–Siegel basisのzero rateを係数$\beta$で表し、各cash flowを

$$
D(t;\beta)=\exp\{-tB(t;\lambda)\beta\}
$$

でdiscountする。priceは$\beta$に対して一般に非線形であり、price residualの二乗和をconvex QPとはみなさない。さらにdecay $\lambda$と$\beta$の同時推定は非凸である。

B4は$D(t_j)$自体をvariableにするため、price map $CD$がlinearになる。node自由度とsmoothness依存が増えるtrade-offを持つ。
"""),
    code("""
b1_nonlinear_fit = fit_bond_price_curve(
    universe,
    basis="nelson_siegel",
    decay=0.45,
    weights=price_weights,
    ridge=1.0e-8,
)
b1_prices = predict_bond_prices(b1_nonlinear_fit, universe)

model_comparison = pd.DataFrame(
    [
        {
            "model": "B1 fixed-decay Nelson-Siegel price fit",
            "decision_variable": "zero-rate basis coefficients",
            "price_map": "nonlinear exponential",
            "convex_QP_certificate": False,
            "training_price_RMSE": np.sqrt(np.mean((observed_prices - b1_prices) ** 2)),
            "standardized_LOO_RMSE": b1_standardized_loo_rmse,
            "generalization_supported": (
                b1_standardized_loo_rmse
                <= GENERALIZATION_SUPPORT_THRESHOLD_HALF_SPREADS
            ),
        },
        {
            "model": "B4 discount-node fit",
            "decision_variable": "discount factors at cash-flow nodes",
            "price_map": "linear cash-flow matrix",
            "convex_QP_certificate": True,
            "training_price_RMSE": np.sqrt(
                np.mean((observed_prices - primary_fit.fitted_prices) ** 2)
            ),
            "standardized_LOO_RMSE": b4_standardized_loo_rmse,
            "generalization_supported": generalization_supported,
        },
    ]
)
display(model_comparison)
"""),
    md(r"""
training RMSEが小さい方を自動採用しない。basis dimension、smoothness、constraint、LOO error、経済的解釈が異なる。convexity certificateはglobal numerical structureの証拠であり、input model riskやgeneralizationの証拠ではない。
"""),
    md(r"""
## 10. negative-rate fixtureとmonotonicity境界

continuous zero rateが$-0.5\%$のとき

$$
D(T)=\exp(0.005T)>1
$$

となり、maturityとともに増加する。monotone optionは既知のanchor $D(0)=1$から

$$
D_1\le D(0)=1,
\qquad D_{j+1}\le D_j
$$

を同時に課す。first positive-time nodeだけにupper bound 1を置けば、後続nodeのupper boundはmonotonicityから従う。従ってこれは普遍的なno-arbitrage conditionではなく、nonnegative instantaneous forward rateを仮定するoptional restrictionである。

primary negative-rate fitは`monotone=False`とする。比較用にmonotoneを強制したfitをsecondary sensitivityとして作り、assumption mismatchのpricing costを測る。
"""),
    code("""
def negative_zero_curve(maturities):
    maturities = np.asarray(maturities, dtype=float)
    return np.full_like(maturities, -0.005)


negative_universe = make_synthetic_jgb_universe(
    zero_curve=negative_zero_curve,
    price_noise_std=0.0,
    seed=task_rng("negative_rate"),
)
negative_bonds = negative_universe.bonds.copy()
negative_bonds["price_half_spread"] = 0.014 + 0.0012 * negative_bonds["maturity_years"]
negative_universe = CouponBondUniverse(
    bonds=negative_bonds,
    cashflows=negative_universe.cashflows.copy(),
)

negative_free_fit = fit_constrained_bond_discount_curve(
    negative_universe,
    quote_width_column="price_half_spread",
    smoothness=SMOOTHNESS_STRENGTH,
    minimum_discount=MINIMUM_DISCOUNT,
    monotone=False,
    method="SLSQP",
    compute_loo=False,
    compare_solver=False,
)
negative_monotone_fit = fit_constrained_bond_discount_curve(
    negative_universe,
    quote_width_column="price_half_spread",
    smoothness=SMOOTHNESS_STRENGTH,
    minimum_discount=MINIMUM_DISCOUNT,
    monotone=True,
    method="SLSQP",
    compute_loo=False,
    compare_solver=False,
)

negative_observed = negative_bonds["dirty_price"].to_numpy()
negative_boundary_table = pd.DataFrame(
    [
        {
            "specification": "monotonicity off (primary for negative-rate fixture)",
            "first_discount": negative_free_fit.discount_factors[0],
            "maximum_discount": negative_free_fit.discount_factors.max(),
            "number_of_increasing_steps": int(
                np.sum(np.diff(negative_free_fit.discount_factors) > 1.0e-9)
            ),
            "price_RMSE": np.sqrt(
                np.mean((negative_observed - negative_free_fit.fitted_prices) ** 2)
            ),
            "KKT_passed": negative_free_fit.qp_solution.success,
        },
        {
            "specification": "monotone non-increasing (secondary assumption)",
            "first_discount": negative_monotone_fit.discount_factors[0],
            "maximum_discount": negative_monotone_fit.discount_factors.max(),
            "number_of_increasing_steps": int(
                np.sum(np.diff(negative_monotone_fit.discount_factors) > 1.0e-9)
            ),
            "price_RMSE": np.sqrt(
                np.mean((negative_observed - negative_monotone_fit.fitted_prices) ** 2)
            ),
            "KKT_passed": negative_monotone_fit.qp_solution.success,
        },
    ]
)
display(negative_boundary_table)
assert negative_free_fit.discount_factors.max() > 1.0
assert negative_monotone_fit.discount_factors[0] <= 1.0 + 1.0e-12
assert negative_monotone_fit.diagnostics.first_node_anchor_violation <= (
    negative_monotone_fit.diagnostics.hard_constraint_tolerance
)
assert negative_boundary_table["KKT_passed"].all()
"""),
    code("""
fig = go.Figure()
fig.add_scatter(
    x=negative_free_fit.node_times,
    y=negative_free_fit.discount_factors,
    mode="lines",
    name="Monotonicity off",
)
fig.add_scatter(
    x=negative_monotone_fit.node_times,
    y=negative_monotone_fit.discount_factors,
    mode="lines",
    name="Monotone non-increasing",
)
fig.add_hline(y=1.0, line_dash="dot")
fig.update_layout(
    title="A monotone discount constraint conflicts with the negative-rate fixture",
    xaxis_title="Cash-flow time (years)",
    yaxis_title="Discount factor",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
monotone fitがsolver上feasibleでも、negative-rate DGPと整合するとは限らない。feasibility、optimality、economic assumptionの妥当性は別のgateである。
"""),
    md(r"""
## 11. 2〜4ページ技術memoの骨格

### Question and data

- 合成fixed-coupon universeのdirty mid priceをcash-flow node discount factorで説明する
- quote half-spreadをprecision proxyとして使用する
- 全cash flow、price、unit、seed、configurationをartifactに保存する

### Method

- price-linear discount-node QP
- positive discount、second-difference smoothness
- primary monotonicity off、optional monotone sensitivity
- SLSQP primary、trust-constr disagreement、独立KKT audit

### Evidence

- raw / standardized price residual
- four KKT residual families、duality gap、hard-bound violation
- solver / objective-scale disagreement
- B1 fixed-decay baselineとのraw / weighted LOO比較
- precommitted 2 half-spread gate、`generalization_supported`、bond-level LOO error
- negative-rate fixture

### Claim boundary

- synthetic universeに対するannouncementでもcausal effectでもない数値演習
- in-sample numerical certificateとout-of-sample generalization supportを別判定にする
- `generalization_supported=False`なら、KKT合格でもLOO pricing claimは支持されないと明記する
- positive factorを完全なmarket no-arbitrage certificateと呼ばない
- monotone discountはnonnegative forwardを仮定した場合だけ
- B1 nonlinear basis fit、B4 convex node fit、joint decay estimationを分離
- 実JGBにはsettlement、calendar、accrued interest、quote timestamp、liquidity adapterが必要
"""),
    code("""
in_sample_numerical_certificate = bool(
    primary_fit.qp_solution.success
    and kkt.passed
    and primary_fit.diagnostics.hard_constraints_passed
    and primary_fit.diagnostics.penalized_design_full_column_rank
    and primary_fit.diagnostics.solver_comparison_passed
)
pipeline_diagnostics_accepted = bool(primary_fit.diagnostics.accepted)
if generalization_supported:
    out_of_sample_claim = (
        "supported for this fixed synthetic cross-section under the "
        "precommitted two-half-spread gate"
    )
else:
    out_of_sample_claim = (
        "not supported: standardized LOO RMSE exceeds the precommitted "
        "two-half-spread gate"
    )

memo_claim_audit = pd.DataFrame(
    [
        {
            "claim_family": "in-sample numerical certificate",
            "supported": in_sample_numerical_certificate,
            "evidence": "hard floor + rank + all KKT families + solver comparison",
        },
        {
            "claim_family": "numerical pipeline acceptance",
            "supported": pipeline_diagnostics_accepted,
            "evidence": "identified and accepted LOO solves; not a performance gate",
        },
        {
            "claim_family": "cross-sectional out-of-sample pricing",
            "supported": generalization_supported,
            "evidence": out_of_sample_claim,
        },
        {
            "claim_family": "real-JGB or future-price validity",
            "supported": False,
            "evidence": "synthetic fixture omits market-data and settlement contracts",
        },
    ]
)
display(memo_claim_audit)
print("memo OOS conclusion:", out_of_sample_claim)
assert in_sample_numerical_certificate
assert memo_claim_audit.loc[
    memo_claim_audit["claim_family"] == "cross-sectional out-of-sample pricing",
    "supported",
].item() == generalization_supported
"""),
    md(r"""
## 12. Core / Advancedと75点gate

**Core**はcash-flow matrix、positive discount、smoothness、bid–ask weighting、KKT、solver disagreement、LOO、negative-rate boundary、memoである。

**Advanced**はHuber等のconvex robust loss reformulation、形状制約のselection、multi-period portfolio optimizerである。Tukey等のnonconvex lossやNelson–Siegel decay同時推定をCore QPの保証で包まない。

| Category | Points | 必須証拠 |
|---|---:|---|
| Mathematical understanding | 25 | price-linear QPとconvex boundary |
| Implementation and testing | 30 | cash-flow adapter、KKT、constraint test |
| Experimental design | 30 | scaling、solver、LOO、negative-rate fixture |
| Explanation and memo | 15 | units、assumption、claim boundary |

総合75点以上に加え、positive bound、全KKT family、LOO、negative-rate monotonicity auditを必須gateにする。さらにout-of-sample pricingをclaimする場合はprecommitted standardized LOO gateも必須である。gateが落ちたmodelでも、memoが`generalization_supported=False`としてclaimをin-sample certificateへ制限すれば研究artifactのintegrity gateは満たせる。training RMSEだけでは合格しない。
"""),
    code("""
negative_rate_boundary_audited = bool(
    negative_free_fit.discount_factors.max() > 1.0
    and negative_monotone_fit.discount_factors[0] <= 1.0 + 1.0e-12
)
claim_boundary_truthful = bool(
    (generalization_supported and out_of_sample_claim.startswith("supported"))
    or (
        not generalization_supported
        and out_of_sample_claim.startswith("not supported")
    )
)
project_gate_table = pd.DataFrame(
    [
        {
            "gate": "in-sample numerical certificate",
            "observed": in_sample_numerical_certificate,
            "required_for_artifact": True,
            "passed": in_sample_numerical_certificate,
        },
        {
            "gate": "LOO executed on fixed identified grid",
            "observed": (
                loo_result.node_grid_fixed
                and loo_result.all_fits_accepted
                and loo_result.identified_fits == loo_result.total_fits
            ),
            "required_for_artifact": True,
            "passed": (
                loo_result.node_grid_fixed
                and loo_result.all_fits_accepted
                and loo_result.identified_fits == loo_result.total_fits
            ),
        },
        {
            "gate": "pipeline numerical diagnostics accepted",
            "observed": pipeline_diagnostics_accepted,
            "required_for_artifact": True,
            "passed": pipeline_diagnostics_accepted,
        },
        {
            "gate": "OOS generalization support",
            "observed": generalization_supported,
            "required_for_artifact": False,
            "passed": generalization_supported,
        },
        {
            "gate": "memo claim matches OOS result",
            "observed": claim_boundary_truthful,
            "required_for_artifact": True,
            "passed": claim_boundary_truthful,
        },
        {
            "gate": "negative-rate monotonicity boundary",
            "observed": negative_rate_boundary_audited,
            "required_for_artifact": True,
            "passed": negative_rate_boundary_audited,
        },
    ]
)
artifact_integrity_passed = bool(
    project_gate_table.loc[
        project_gate_table["required_for_artifact"],
        "passed",
    ].all()
)
oos_model_gate_passed = generalization_supported
display(project_gate_table)
print("artifact integrity passed:", artifact_integrity_passed)
print("OOS model gate passed:", oos_model_gate_passed)
assert artifact_integrity_passed
"""),
    md(r"""
## 13. 失敗モード

- YTMを各cash flowのzero rateとしてprice matrixへ入れる
- latent synthetic zero rateを実dataでも観測inputとして使う
- bid–ask widthとhalf-spread、priceとyieldの単位を混ぜる
- $Q$のPSD、rank、conditioningを検査しない
- constantを落としたQP objectiveとpricing lossを同じ値として比較する
- `success=True`だけでpositive boundやKKTを省略する
- objective scaling後のdualやtoleranceを元単位へ戻さない
- LOO foldのheld-out priceでsmoothnessを選ぶ
- nodeが非一意でもfactor差だけでsolver failureと断定する
- monotone discountを負金利下の普遍的no-arbitrage conditionと呼ぶ
- joint decay estimationをconvex QPと呼ぶ
"""),
    md(r"""
## 14. 段階別演習

### 基礎

1. 5年bondのcash-flow rowと$CD$ priceを手計算で照合せよ。
2. weighted least-squares objectiveから$Q,q$を導出せよ。
3. $D_j\ge\epsilon_D$のstationarityとcomplementarityを書け。

### 標準

4. smoothness ratioを$10^{-6}$から$10^{-1}$まで変え、training / LOO errorとroughnessをplotせよ。
5. objectiveとvariableのscaleを別々に変え、physical discountへ戻して比較せよ。
6. quote widthを一つだけ広げ、そのbondのstandardized residualとcurve shiftを測れ。
7. negative rateを$-0.1\%,-0.5\%,-1\%$へ変え、monotone constraintのcostを報告せよ。

### 研究

8. **Advanced:** Huber price lossをconvex epigraphまたは補助変数でformulateし、QPから変わるproblem classを示せ。
9. 実JGB adapterのsettlement / calendar / accrued-interest test planを書け。
"""),
    md(r"""
## 15. Exit Criteria

- [ ] CouponBondUniverseを監査可能なcash-flow matrixへ変換できる
- [ ] discount-node objectiveのconvexityとPSD Hessianを示せる
- [ ] positive discountのraw violationと全KKT residualを検査できる
- [ ] solver disagreementとobjective scalingをphysical priceで比較できる
- [ ] full-grid LOOをleakageなしで実行できる
- [ ] B1 nonlinear fitとB4 convex QPの境界を説明できる
- [ ] negative-rate regimeでmonotonicityをoffにすべきcaseを再現できる
- [ ] synthetic evidenceと実市場claimの境界をmemoにできる
"""),
    md(r"""
## 16. 出典

- [BIS Papers No. 25, *Zero-coupon yield curves: technical documentation*](https://www.bis.org/publ/bppdf/bispap25.pdf) — discount factor、spot / forward relation、中央銀行curve推定の一次資料
- [Boyd and Vandenberghe, *Convex Optimization*](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf) — convex quadratic objective、KKT、sensitivityの著者公開版
- [SciPy `LinearConstraint`](https://docs.scipy.org/doc/scipy-1.13.0/reference/generated/scipy.optimize.LinearConstraint.html) — `lb <= A @ x <= ub`の1.13公式sign contract
- [SciPy `minimize(method='trust-constr')`](https://docs.scipy.org/doc/scipy-1.13.0/reference/optimize.minimize-trustconstr.html) — constraint violation、Lagrangian gradient、multiplier signの公式API
- [Ministry of Finance Japan, Interest Rate Q&A](https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/qa.htm) — JGB prevailing yieldとconstant-maturity curveの公式説明

B4の結論は、solverを呼べることではなく、problem structure、数値誤差、economic assumption、generalization、claimを一つの再現可能なevidence chainで監査できることである。
"""),
]
