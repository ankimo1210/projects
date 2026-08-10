"""Builder for notebook 20: duality, KKT diagnostics, and sensitivity."""

from nbkit import code, md

cells = [
    md(r"""
# 20. Week 14 — 双対性、KKT、shadow price

> statusを信頼する前に、primalとdualの両側から同じ解を監査する。

## 学習目標

- Lagrangian、dual function、weak / strong dualityを符号規約付きで導出できる
- Slater conditionが何を保証し、何を保証しないか説明できる
- stationarity、primal feasibility、dual feasibility、complementarityの4種類を計算できる
- raw residualとdimensionless residual、duality gapを区別できる
- inequality RHSのshadow priceをcentered finite differenceで照合できる
- optimal_inaccurateをKKT gateなしに合格させない

## 前提知識

- Week 13のconvexity、QP標準形、scaling、feasibility
- gradient、quadratic form、linear constraint
- B1のscale-aware numerical tolerance
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from quant_textbook.convex import (
    QuadraticProgram,
    check_inequality_sensitivity,
    evaluate_kkt,
    quadratic_objective,
    solve_quadratic_program,
)

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
NOTEBOOK_ID = 20
TASK_IDS = {
    "candidate_audit": 1,
}


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
## 1. canonical QPと符号規約

本章では

$$
\begin{aligned}
\text{minimize}_x\quad & f(x)=\frac12x^\top Px+q^\top x\\
\text{subject to}\quad & Gx\le h,\\
& Ax=b
\end{aligned}
$$

を使う。$P\succeq0$であればconvex QPである。Lagrangianを

$$
L(x,\lambda,\nu)
=f(x)+\lambda^\top(Gx-h)+\nu^\top(Ax-b),
\qquad \lambda\ge0
$$

と固定する。$\lambda$はinequality row、$\nu$はequality rowに対応し、$\nu$の符号制約はない。

bound $\ell\le x\le u$を含むlibrary APIでは、

$$
+\mu_\ell^\top(\ell-x)+\mu_u^\top(x-u),
\qquad \mu_\ell,\mu_u\ge0
$$

を加える。したがってstationarityへ $-\mu_\ell+\mu_u$ が入る。SciPy trust-constrのraw multiplierはupper-activeが正、lower-activeが負という規約を持つが、共通APIはlower / upperを別々の非負multiplierへ正規化する。solver間比較では必ずこの規約へ戻す。
"""),
    md(r"""
## 2. dual function、weak duality、strong duality

dual functionは

$$
g(\lambda,\nu)=\inf_x L(x,\lambda,\nu)
$$

である。任意のprimal feasible $x$ とdual feasible $\lambda\ge0$について

$$
g(\lambda,\nu)\le f(x)
$$

が成り立つ。これがweak dualityであり、$g$はprimal optimumのlower boundを与える。primal valueを$p^*$、dual valueを$d^*$とすれば $d^*\le p^*$ である。

convex problemで、例えばinequalityをすべてstrictに満たしequalityも満たすrelative-interior pointが存在するというSlater conditionが成立すれば、適切なclosednessの下でstrong duality $p^*=d^*$ とdual attainmentが得られる。

Slaterはdataが正しい、solutionが高精度、solverがcertificateを正しく返すことを保証しない。またaffine inequalityだけの問題ではより弱いconstraint qualificationでstrong dualityが成立する場合もある。Slaterは便利な十分条件であり、必要条件と断定しない。
"""),
    md(r"""
## 3. KKT conditionsと4 residual family

differentiable convex problemに対するKKT conditionsは次の四群である。

1. **Primal feasibility:** $Gx-h\le0$、$Ax-b=0$
2. **Dual feasibility:** $\lambda\ge0$
3. **Stationarity:** $Px+q+G^\top\lambda+A^\top\nu=0$
4. **Complementarity:** $\lambda_i(G_ix-h_i)=0$

boundがあればprimal / dual feasibility、stationarity、complementarityへ対応項を加える。convexityとconstraint qualificationの下では、KKT pointがglobal optimumのcertificateになる。

### raw residualとdimensionless residual

raw residualは元の単位を保持する。一方、異なるconstraint rowをgateへまとめるときはscaleを明示する。例えばinequality row $i$ のprimal violationを

$$
r_{{\rm pri},i}^{\rm raw}
=\max(G_ix-h_i,0),
$$

$$
r_{{\rm pri},i}^{\rm scaled}
=\frac{r_{{\rm pri},i}^{\rm raw}}
{\max\left\{
|h_i|,
\sum_j |G_{ij}x_j|,
\operatorname{tiny}
\right\}}
$$

とする。これはcodeでは`abs(G) @ abs(x)`で行別に計算する。$G_{ij}=0$の無関係な座標が巨大でも、そのrowのdenominatorを膨らませない。equality rowも同様に$\max\{|b_i|,\sum_j|A_{ij}x_j|,\operatorname{tiny}\}$を使う。$\lVert G_i\rVert_\infty\lVert x\rVert_\infty$では、rowに現れない巨大座標によって実際の違反を隠し得る。

stationarityのdenominatorは、KKT式へ入る各項の自然尺度

$$
\max\left\{
\lVert Px\rVert_\infty,
\lVert q\rVert_\infty,
\lVert G^\top\lambda\rVert_\infty,
\lVert A^\top\nu\rVert_\infty,
\lVert\mu_\ell\rVert_\infty,
\lVert\mu_u\rVert_\infty,
\operatorname{tiny}
\right\}
$$

とする。dual feasibilityはdual normで割る。complementarityとduality gapには、監査candidateにおけるobjective / Lagrangian各term、primal value、dual valueのabsolute maximumを使う。例えば

$$
\max\left\{
\frac12|x^\top Px|,
|q^\top x|,
|h^\top\lambda|,
|b^\top\nu|,
|\ell^\top\mu_\ell|,
|u^\top\mu_u|,
|p|,
|d|,
\operatorname{tiny}
\right\}
$$

である。boundの内積はfinite entryだけで作る。制約を無視したstationary pointが大きくても、監査candidateと無関係ならdenominatorへ入れない。そうしないと、infeasibleなreferenceが実際のcomplementarityとgapを隠し得る。

literalな1をdenominatorへ足すと、単位を暗黙に固定する。例えば同値なconstraint rowを$10^{-20}$倍したとき、自然尺度に対して100%の違反でもscaled residualが$10^{-20}$程度に隠れ得る。$\operatorname{tiny}$はzero divisionを避けるfloat64のguardであり、経済的なunit floorではない。denominatorの定義をartifactへ保存し、scaled値だけでraw unitsを隠さない。
"""),
    md(r"""
## 4. 小さなQPをprimalとdualから解く

required activityを$1$とし、

$$
\begin{aligned}
\min_x\quad & \frac12(x_1^2+4x_2^2)\\
\text{s.t.}\quad & x_1+x_2\ge1,\\
& x_1\ge0,\quad x_2\ge0
\end{aligned}
$$

を解く。標準形 $Gx\le h$ では各rowの符号を反転する。$x=(0.6,0.6)$ は全inequalityをstrictに満たすのでSlater pointである。

解析解は$x^*=(0.8,0.2)$、activity constraintのmultiplierは$\lambda_1^*=0.8$、他は0、valueは$0.4$である。
"""),
    code("""
P = np.diag([1.0, 4.0])
q = np.zeros(2)
required_activity = 1.0
G = np.array(
    [
        [-1.0, -1.0],
        [-1.0, 0.0],
        [0.0, -1.0],
    ]
)
h = np.array([-required_activity, 0.0, 0.0])

activity_problem = QuadraticProgram(
    P=P,
    q=q,
    G=G,
    h=h,
    variable_units=("activity", "activity"),
    inequality_units=("activity", "activity", "activity"),
    name="activity_allocation",
)

solutions = {
    method: solve_quadratic_program(
        activity_problem,
        initial=np.array([0.6, 0.6]),
        method=method,
    )
    for method in ("SLSQP", "trust-constr")
}

analytic_x = np.array([0.8, 0.2])
analytic_duals = np.array([0.8, 0.0, 0.0])
analytic_value = 0.4

solution_rows = []
for method, solution in solutions.items():
    solution_rows.append(
        {
            "method": method,
            "x1": solution.x[0],
            "x2": solution.x[1],
            "primal_value": solution.primal_objective,
            "dual_value": solution.dual_objective,
            "activity_dual": solution.inequality_duals[0],
            "solution_error": np.linalg.norm(solution.x - analytic_x, ord=np.inf),
            "optimizer_success": solution.diagnostics.optimizer_success,
            "KKT_passed": solution.diagnostics.kkt.passed,
        }
    )

solution_table = pd.DataFrame(solution_rows)
display(solution_table)
slsqp_row = solution_table.loc[solution_table["method"] == "SLSQP"].iloc[0]
assert abs(slsqp_row["primal_value"] - analytic_value) < 1.0e-8
assert abs(slsqp_row["activity_dual"] - analytic_duals[0]) < 1.0e-7
assert bool(slsqp_row["KKT_passed"])
assert np.max(np.abs(solution_table["primal_value"] - analytic_value)) < 5.0e-6
"""),
    md(r"""
二つのsolverが近いcandidateを返すことは有用な照合だが、独立certificateの代わりではない。表では`optimizer_success`と`KKT_passed`を別列にし、以降は解析解との一致とKKT gateを通ったSLSQP candidateを監査対象にする。もう一方のprimal candidateが近くても、dual reconstructionとstrict residual gateを通らなければ「最適」とは採用しない。両方が同じscale mistakeを共有する可能性もあるため、元の$P,q,G,h$からresidualを再計算する。
"""),
    md(r"""
### 4.1 同値なconstraint rowのscaleを変える

positive factor $s$ に対して $G_1x\le h_1$ と $sG_1x\le sh_1$ は同じfeasible setを表す。したがってprimal solutionとobjectiveは不変でなければならない。一方、scaled rowのmultiplier $\tilde\lambda_1$ は

$$
\tilde\lambda_1=\frac{\lambda_1}{s}
$$

と変わる。元のRHS unitへ戻した$s\tilde\lambda_1$を比較する。次のregression checkはactivity rowだけを$10^{-20}$、$1$、$10^{20}$倍し、二つのsolverで同じsolutionとKKT合格を要求する。
"""),
    code("""
row_scale_rows = []
for row_scale_factor in (1.0e-20, 1.0, 1.0e20):
    scaled_G = G.copy()
    scaled_h = h.copy()
    scaled_G[0] *= row_scale_factor
    scaled_h[0] *= row_scale_factor
    row_scaled_problem = QuadraticProgram(
        P=P,
        q=q,
        G=scaled_G,
        h=scaled_h,
        variable_units=("activity", "activity"),
        inequality_units=("scaled_activity", "activity", "activity"),
        name=f"activity_row_scaled_{row_scale_factor:.0e}",
    )
    for method in ("SLSQP", "trust-constr"):
        row_scaled_solution = solve_quadratic_program(
            row_scaled_problem,
            initial=np.array([0.6, 0.6]),
            method=method,
        )
        row_scale_rows.append(
            {
                "row_scale_factor": row_scale_factor,
                "method": method,
                "solution_error": np.linalg.norm(
                    row_scaled_solution.x - analytic_x,
                    ord=np.inf,
                ),
                "objective_error": abs(
                    row_scaled_solution.primal_objective - analytic_value
                ),
                "raw_activity_dual": row_scaled_solution.inequality_duals[0],
                "dual_in_base_rhs_units": (
                    row_scale_factor * row_scaled_solution.inequality_duals[0]
                ),
                "KKT_passed": row_scaled_solution.diagnostics.kkt.passed,
            }
        )

row_scale_table = pd.DataFrame(row_scale_rows)
display(row_scale_table)
assert row_scale_table["KKT_passed"].all()
assert row_scale_table["solution_error"].max() < 1.0e-6
assert row_scale_table["objective_error"].max() < 1.0e-6
assert np.max(
    np.abs(row_scale_table["dual_in_base_rhs_units"] - analytic_duals[0])
) < 1.0e-5

unrelated_coordinate_problem = QuadraticProgram(
    P=np.zeros((2, 2)),
    q=np.zeros(2),
    G=np.array([[1.0, 0.0]]),
    h=np.array([0.0]),
    name="unrelated_coordinate_regression",
)
unrelated_coordinate_kkt = evaluate_kkt(
    unrelated_coordinate_problem,
    point=np.array([1.0, 1.0e20]),
    inequality_duals=np.zeros(1),
    equality_duals=np.empty(0),
    lower_bound_duals=np.zeros(2),
    upper_bound_duals=np.zeros(2),
    dual_objective=0.0,
    tolerance=100.0 * np.sqrt(np.finfo(float).eps),
)
unrelated_coordinate_table = pd.DataFrame(
    [
        {
            "raw_primal_violation": (
                unrelated_coordinate_kkt.raw_primal_inequality
            ),
            "dimensionless_primal_violation": (
                unrelated_coordinate_kkt.primal_inequality
            ),
            "unrelated_coordinate": 1.0e20,
            "KKT_passed": unrelated_coordinate_kkt.passed,
        }
    ]
)
display(unrelated_coordinate_table)
assert unrelated_coordinate_kkt.raw_primal_inequality == 1.0
assert unrelated_coordinate_kkt.primal_inequality == 1.0
assert not unrelated_coordinate_kkt.passed
"""),
    md(r"""
raw multiplierはrow scaleの逆数で変わるため、そのままsolver間・formulation間で比較しない。primal解、元unitへ戻したdual、natural-scale residualが不変であることを同時に検査する。$10^{-20}$ rowでliteralな1をdenominatorへ足すと、この回帰検査が検出すべきrelative violationを隠す。さらに、係数0の座標を$10^{20}$にした回帰例でもrow scaleは変わらず、100%のprimal violationを100%として棄却する。
"""),
    md(r"""
## 5. dual lower boundを可視化する

nonnegativity constraintsのdualを0に固定し、activity rowのmultiplierを$\lambda\ge0$とする。$P\succ0$なので$x$についてinfimumを取ると

$$
g(\lambda)
=-\frac12(G_1^\top\lambda)^\top P^{-1}(G_1^\top\lambda)
-h_1\lambda
=-0.625\lambda^2+\lambda.
$$

$g(\lambda)$はすべてprimal optimum以下で、$\lambda=0.8$で$0.4$へ達する。
"""),
    code("""
dual_grid = np.linspace(0.0, 1.6, 161)
dual_values = -0.625 * dual_grid**2 + required_activity * dual_grid

fig = go.Figure()
fig.add_scatter(
    x=dual_grid,
    y=dual_values,
    mode="lines",
    name="Dual lower bound",
)
fig.add_hline(
    y=analytic_value,
    line_dash="dash",
    annotation_text="Primal optimum",
)
fig.add_scatter(
    x=[analytic_duals[0]],
    y=[analytic_value],
    mode="markers",
    marker={"size": 11},
    name="Strong-duality point",
)
fig.update_layout(
    title="Weak duality gives a lower bound; strong duality closes the gap",
    xaxis_title="Activity-constraint multiplier",
    yaxis_title="Objective value",
    template="plotly_white",
)
fig.show()

assert np.all(dual_values <= analytic_value + 1.0e-12)
"""),
    md(r"""
## 6. 4 residual familyを独立に再計算する

以下ではSLSQP solutionからraw residualとdimensionless residualを作る。library diagnosticsと同じ符号規約を用いるが、同じobjectの保存値をそのまま再表示せず、$P,q,G,h$から再計算する。
"""),
    code("""
audited_solution = solutions["SLSQP"]
audited_x = audited_solution.x
audited_lambda = audited_solution.inequality_duals
primal_value = quadratic_objective(activity_problem, audited_x)
dual_value = audited_solution.dual_objective

inequality_slack = h - G @ audited_x
primal_violation_by_row = np.maximum(-inequality_slack, 0.0)
floating_point_tiny = np.finfo(float).tiny
primal_denominator_by_row = np.maximum(
    np.maximum(
        np.abs(h),
        np.abs(G) @ np.abs(audited_x),
    ),
    floating_point_tiny,
)
primal_scaled = np.max(primal_violation_by_row / primal_denominator_by_row)

dual_feasibility_raw = float(np.max(np.maximum(-audited_lambda, 0.0)))
dual_feasibility_denominator = max(
    np.linalg.norm(audited_lambda, ord=np.inf),
    floating_point_tiny,
)
dual_feasibility_scaled = dual_feasibility_raw / dual_feasibility_denominator

objective_gradient = P @ audited_x + q
dual_gradient = G.T @ audited_lambda
stationarity_vector = objective_gradient + dual_gradient
stationarity_raw = float(np.linalg.norm(stationarity_vector, ord=np.inf))
stationarity_denominator = max(
    np.linalg.norm(objective_gradient, ord=np.inf),
    np.linalg.norm(dual_gradient, ord=np.inf),
    floating_point_tiny,
)
stationarity_scaled = stationarity_raw / stationarity_denominator

complementarity_by_row = audited_lambda * inequality_slack
complementarity_raw = float(np.max(np.abs(complementarity_by_row)))
value_denominator = max(
    0.5 * abs(float(audited_x @ P @ audited_x)),
    abs(float(q @ audited_x)),
    abs(float(h @ audited_lambda)),
    abs(primal_value),
    abs(dual_value),
    floating_point_tiny,
)
complementarity_scaled = complementarity_raw / value_denominator
duality_gap_raw = abs(primal_value - dual_value)
duality_gap_scaled = duality_gap_raw / value_denominator

manual_residuals = pd.DataFrame(
    [
        {
            "family": "Primal feasibility",
            "raw_residual": float(np.max(primal_violation_by_row)),
            "dimensionless_residual": primal_scaled,
        },
        {
            "family": "Dual feasibility",
            "raw_residual": dual_feasibility_raw,
            "dimensionless_residual": dual_feasibility_scaled,
        },
        {
            "family": "Stationarity",
            "raw_residual": stationarity_raw,
            "dimensionless_residual": stationarity_scaled,
        },
        {
            "family": "Complementarity",
            "raw_residual": complementarity_raw,
            "dimensionless_residual": complementarity_scaled,
        },
    ]
)
display(manual_residuals)
print("raw duality gap:", duality_gap_raw)
print("dimensionless duality gap:", duality_gap_scaled)
"""),
    md(r"""
4 residual familyとduality gapは役割が異なる。例えばprimal infeasibleな候補に形式的なdual valueを付けても、small gapをoptimality certificateとして解釈できない。逆にfeasibleでもstationarityが大きければ、よりよい候補が残る。

well-scaledなこのfloat64小問題では

$$
\tau=100\sqrt{\epsilon_{\rm mach}}
$$

を教材用gate候補とする。実務でこの定数をコピーせず、problem scale、conditioning、solver setting、downstream sensitivityから根拠を作る。

自然尺度も無制約解から機械的に借りない。例えば$\min\{\tfrac12 10^{-20}x^2-x:x\le0\}$の無制約解は$10^{20}$だが、制約付き最適解は0である。candidate $x=-1$、$\lambda=1$はraw complementarityとgapがともに1なので、大きな無制約解で割らず棄却する。
"""),
    code("""
dimensionless_gate = 100.0 * np.sqrt(np.finfo(float).eps)
largest_scaled_kkt_residual = float(
    manual_residuals["dimensionless_residual"].max()
)
manual_gate_passed = (
    largest_scaled_kkt_residual <= dimensionless_gate
    and duality_gap_scaled <= dimensionless_gate
)

print("dimensionless gate:", dimensionless_gate)
print("largest scaled KKT residual:", largest_scaled_kkt_residual)
print("manual gate passed:", manual_gate_passed)
assert manual_gate_passed

irrelevant_reference_problem = QuadraticProgram(
    P=np.array([[1.0e-20]]),
    q=np.array([-1.0]),
    G=np.array([[1.0]]),
    h=np.array([0.0]),
    name="irrelevant_unconstrained_reference_regression",
)
irrelevant_reference_kkt = evaluate_kkt(
    irrelevant_reference_problem,
    point=np.array([-1.0]),
    inequality_duals=np.array([1.0]),
    equality_duals=np.empty(0),
    lower_bound_duals=np.zeros(1),
    upper_bound_duals=np.zeros(1),
    dual_objective=0.0,
    tolerance=dimensionless_gate,
)
irrelevant_reference_table = pd.DataFrame(
    [
        {
            "raw_complementarity": (
                irrelevant_reference_kkt.raw_complementarity
            ),
            "dimensionless_complementarity": (
                irrelevant_reference_kkt.complementarity
            ),
            "raw_duality_gap": irrelevant_reference_kkt.raw_duality_gap,
            "dimensionless_duality_gap": irrelevant_reference_kkt.duality_gap,
            "KKT_passed": irrelevant_reference_kkt.passed,
        }
    ]
)
display(irrelevant_reference_table)
assert irrelevant_reference_kkt.raw_complementarity == 1.0
assert irrelevant_reference_kkt.raw_duality_gap == 1.0
assert irrelevant_reference_kkt.complementarity == 1.0
assert irrelevant_reference_kkt.duality_gap == 1.0
assert not irrelevant_reference_kkt.passed
"""),
    md(r"""
## 7. shadow priceをcentered finite differenceで照合する

標準形$Gx\le h$でactivity rowのRHS $h_1$を$\delta$だけ増やすとconstraintは緩む。value functionを$V(h)$とすれば、regularな点で

$$
\frac{\partial V}{\partial h_1}=-\lambda_1^*.
$$

一方、required activity $b=-h_1$を増やす操作はconstraintを厳しくし、$\partial V/\partial b=+\lambda_1^*$となる。符号を言葉だけで覚えず、実際に摂動したparameterを記録する。

library APIの`perturbation`入力はrow自然尺度に対するdimensionless fractionである。自然尺度は現在解と$x_{\rm stat}=P^\dagger(-q)$の大きい方を変数referenceとして、$\max\{|h_i|,\sum_j|G_{ij}|\max(|x_j|,|x_{{\rm stat},j}|),\operatorname{tiny}\}$とする。結果objectの`perturbation`は実現した$\delta$、`relative_perturbation`は入力率、`rhs_scale`はその自然尺度なので、三つをartifactへ残す。
"""),
    code("""
sensitivity_relative_step = 1.0e-4
sensitivity_check = check_inequality_sensitivity(
    activity_problem,
    solutions["SLSQP"],
    0,
    perturbation=sensitivity_relative_step,
    method="SLSQP",
    tolerance=dimensionless_gate,
)

shadow_price_table = pd.DataFrame(
    [
        {
            "quantity": "requested relative perturbation",
            "value": sensitivity_check.relative_perturbation,
        },
        {
            "quantity": "RHS natural scale",
            "value": sensitivity_check.rhs_scale,
        },
        {
            "quantity": "realized centered half-step in h units",
            "value": sensitivity_check.perturbation,
        },
        {
            "quantity": "dV/dh from multiplier",
            "value": -solutions["SLSQP"].inequality_duals[0],
        },
        {
            "quantity": "dV/dh centered finite difference",
            "value": sensitivity_check.finite_difference_derivative,
        },
        {
            "quantity": "absolute disagreement",
            "value": sensitivity_check.absolute_error,
        },
    ]
)
display(shadow_price_table)

assert sensitivity_check.relative_perturbation == sensitivity_relative_step
assert np.isclose(
    sensitivity_check.perturbation,
    sensitivity_relative_step * sensitivity_check.rhs_scale,
)
assert sensitivity_check.absolute_error < 1.0e-5
"""),
    md(r"""
finite differenceのstepを大きくすると非局所的なcurvatureやactive-set change、小さくするとcancellationとsolver toleranceが支配する。少なくとも複数stepで安定性を確認し、active setが変わった点では局所微分を単純に外挿しない。
"""),
    md(r"""
## 8. optimal_inaccurateをgateなしに採用しない

solverによっては、精度要件を満たせないが候補を返した状態をoptimal_inaccurateと表現する。このlabelは「optimal」と「inaccurate」の両方を含み、採用可否を自動決定しない。

次のillustrative candidateはconstraint boundary上でprimal feasibleだが、allocationが$(0.5,0.5)$でstationarityを満たさない。仮にstatus labelだけがoptimal_inaccurateでも、KKT gateではrejectする。
"""),
    code("""
candidate_rng = task_rng("candidate_audit")
candidate_shift = candidate_rng.uniform(-0.04, 0.04)
inaccurate_candidate = np.array([0.5 + candidate_shift, 0.5 - candidate_shift])
candidate_lambda = np.array([0.8, 0.0, 0.0])
candidate_objective = quadratic_objective(activity_problem, inaccurate_candidate)
candidate_kkt = evaluate_kkt(
    activity_problem,
    point=inaccurate_candidate,
    inequality_duals=candidate_lambda,
    equality_duals=np.empty(0),
    lower_bound_duals=np.zeros(2),
    upper_bound_duals=np.zeros(2),
    dual_objective=analytic_value,
    tolerance=dimensionless_gate,
)
audited_kkt = audited_solution.diagnostics.kkt

status_audit = pd.DataFrame(
    [
        {
            "reported_status": "optimal_inaccurate (illustrative)",
            "primal_feasibility": max(
                candidate_kkt.primal_inequality,
                candidate_kkt.primal_equality,
                candidate_kkt.primal_bounds,
            ),
            "dual_feasibility": candidate_kkt.dual_feasibility,
            "stationarity": candidate_kkt.stationarity,
            "complementarity": candidate_kkt.complementarity,
            "duality_gap": candidate_kkt.duality_gap,
            "objective": candidate_objective,
            "KKT_passed": candidate_kkt.passed,
            "accepted": candidate_kkt.passed,
        },
        {
            "reported_status": "solver candidate with audited KKT",
            "primal_feasibility": max(
                audited_kkt.primal_inequality,
                audited_kkt.primal_equality,
                audited_kkt.primal_bounds,
            ),
            "dual_feasibility": audited_kkt.dual_feasibility,
            "stationarity": audited_kkt.stationarity,
            "complementarity": audited_kkt.complementarity,
            "duality_gap": audited_kkt.duality_gap,
            "objective": primal_value,
            "KKT_passed": audited_kkt.passed,
            "accepted": (
                audited_solution.diagnostics.optimizer_success
                and audited_kkt.passed
            ),
        },
    ]
)
display(status_audit)
assert not candidate_kkt.passed
assert not bool(status_audit.loc[0, "accepted"])
assert audited_kkt.passed
assert bool(status_audit.loc[1, "accepted"])
"""),
    md(r"""
表の5 residual列はすべてdimensionlessであり、raw valuesも`KKTResiduals`に保持される。statusごとの固定accept / reject tableも不十分である。optimalでもresidual再計算が失敗すればrejectし、optimal_inaccurateでも用途に応じたresidual・gap・sensitivity gateをすべて通るか、限定用途として明示的に承認する。目的関数差が経済的に小さくても、大きなconstraint violationを相殺しない。
"""),
    md(r"""
## 9. duality gapとinfeasibilityを区別する

- **positive duality gap:** primal feasible pointとdual feasible pointの目的差。近似解のoptimality boundになり得る。
- **primal infeasibility:** constraintsを同時に満たす$x$がない。primal optimumの有限値を前提にgapを解釈しない。
- **dual infeasibility / unboundedness:** formulationとsolver certificateを確認し、一方のstatusだけから他方を即断しない。
- **numerical ambiguity:** residualとcertificateがtoleranceに対して不十分。単位、scaling、iteration budget、別solverを調べる。

「gapが計算された」というcode pathと「そのgapがvalid lower / upper boundを結ぶ」という数学的条件を分ける。

### Core / Advancedの境界

CoreはLagrangian、weak / strong duality、Slater、smooth convex problemのKKT、shadow-price監査までである。Fenchel conjugate、Fenchel duality、nonsmooth KKT、perturbation functionの一般的幾何は**Advanced**とし、4 residual familyを自力で検証した後に扱う。
"""),
    md(r"""
## 10. 失敗モード

- $Gx\le h$と$Gx\ge h$を混在させ、multiplierとshadow priceの符号を誤る
- lower-bound multiplierのsolver固有符号をそのまま共通APIへ流す
- weak dualityだけからgapが0になると仮定する
- Slaterを全問題の必要条件、またはnumerical accuracyの保証と呼ぶ
- stationarityだけを検査し、primal / dual feasibilityを捨てる
- complementarityを$\lambda_i(G_ix-h_i)$の符号付き和だけで相殺する
- dimensionless residualだけを残し、raw unitsを失う
- finite-difference stepを一つだけ試し、active-set changeを無視する
- optimal_inaccurateをstatus labelだけで採用する
"""),
    md(r"""
## 11. 段階別演習

### 基礎

1. canonical QPのLagrangianとstationarityを符号付きで導出せよ。
2. 小QPの解析解、multiplier、primal / dual valueを手計算せよ。
3. 4 residual familyを同じcandidateから計算せよ。

### 標準

4. required activityを0.5、1.0、2.0へ変え、shadow priceとvalue derivativeを比較せよ。
5. centered-difference stepを$10^{-2}$から$10^{-8}$へ変え、disagreementを描け。
6. inequality rowを$10^6$倍して同じfeasible setを表し、rawとscaled residualを比較せよ。
7. equality constraintを含むQPへ拡張し、free-sign multiplierを監査せよ。

### 研究

8. **Advanced:** nonsmooth objectiveのsubgradient KKTを導出し、smooth stationarity residualをそのまま使えない理由を示せ。
9. active-setが切り替わるbound周辺でvalue functionの片側微分とdualを比較せよ。
10. solver-specific multiplierをcanonical signへ正規化するadapter testを設計せよ。
"""),
    md(r"""
## 12. Exit Criteria

- [ ] Lagrangian、weak / strong duality、Slaterを符号規約付きで説明できる
- [ ] stationarity、primal feasibility、dual feasibility、complementarityを独立に計算できる
- [ ] raw residual、dimensionless residual、duality gapを別々に報告できる
- [ ] lower / upper boundを含むmultiplier conventionをsolver間で正規化できる
- [ ] $dV/dh=-\lambda$をcentered finite differenceで検査できる
- [ ] optimal_inaccurateをKKT・gap・sensitivityなしに合格させない
- [ ] duality gapとprimal infeasibilityを区別できる
"""),
    md(r"""
## 13. 出典

- [Boyd and Vandenberghe, *Convex Optimization*](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf) — Lagrangian duality、Slater、KKT、perturbation analysisの著者公開版
- [Stanford EE364a: Duality lecture slides](https://web.stanford.edu/class/ee364a/lectures/duality.pdf) — weak / strong duality、KKT、sensitivityの公式course material
- [SciPy 1.13: trust-constr](https://docs.scipy.org/doc/scipy-1.13.0/reference/optimize.minimize-trustconstr.html) — termination toleranceとconstraint handlingの公式reference
- [SciPy: LinearConstraint](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.LinearConstraint.html) — $\ell\le Ax\le u$というconstraint APIの公式reference
- [SciPy: linprog](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html) — inequality marginalのRHS sensitivityを含む公式reference

次章では、KKT residualをtermination ruleとして使い、gradient descent、Newton、projected gradient、proximal gradientの収束をconditioningと制約構造から比較する。
"""),
]
