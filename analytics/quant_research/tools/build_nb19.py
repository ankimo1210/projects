"""Builder for notebook 19: convex modeling, scaling, and feasibility."""

from nbkit import code, md

cells = [
    md(r"""
# 19. Week 13 — 凸問題、formulation、feasibility

> DCP acceptedやsolver successでは止まらず、元の単位で制約を再計算する。

## 学習目標

- domainを含めてconvex set・convex functionを判定できる
- LP、QP、SOCPを標準形へ写し、金融・回帰問題と対応づけられる
- mathematical convexity、DCP accepted / unknown、実装済みvalidatorの範囲を区別できる
- 同値なvariable scalingがconditioningとsolver diagnosticsへ与える影響を測れる
- objective valueとprimal feasibilityを独立に検査できる
- infeasible problemで値を捏造せず、statusとcertificateの限界を報告できる

## 前提知識

- B1のleast squares、quadratic form、condition number
- Week 18のproblem contractとB4 evidence chain
- gradient、Hessian、affine map、NumPy・SciPyの基本操作
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy.optimize import NonlinearConstraint, linprog, minimize

from quant_textbook.convex import (
    QuadraticProgram,
    quadratic_objective,
    solve_quadratic_program,
    validate_quadratic_program,
)

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
NOTEBOOK_ID = 19
TASK_IDS = {
    "scaled_regression": 1,
    "socp_regression": 2,
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
## 1. convex set、function、epigraph

集合 $C$ が凸であるとは、任意の $x,y\in C$ と $\theta\in[0,1]$ に対して

$$
\theta x+(1-\theta)y\in C
$$

が成り立つことである。関数 $f:\mathbb{R}^n\to\mathbb{R}\cup\{+\infty\}$ が凸であるとは、domainが凸で、

$$
f(\theta x+(1-\theta)y)
\le \theta f(x)+(1-\theta)f(y)
$$

を満たすことである。extended-value表現でdomain外を $+\infty$ とすれば、domainと目的を同時に扱える。

epigraph

$$
\operatorname{epi}f=\{(x,t):f(x)\le t\}
$$

が凸であることと$f$が凸であることは同値である。この事実が、absolute valueやnormを補助変数$t$を使うlinear / conic constraintへ変える基礎になる。

Hessian test $\nabla^2f(x)\succeq0$ は、open convex domain上で二階微分可能な関数に使える十分必要条件である。nonsmooth functionやdomain boundaryにはそのまま適用しない。
"""),
    md(r"""
## 2. LP、QP、SOCPの標準形

| Class | 代表的な形 | 研究での例 | Coreで残すcertificate |
|---|---|---|---|
| LP | $\min c^\top x$ s.t. $Gx\le h, Ax=b$ | absolute-deviation regression、cash allocation | primal/dual feasibility、gap |
| QP | $\min \frac12x^\top Px+q^\top x$ s.t. affine constraints、$P\succeq0$ | constrained least squares、mean-variance portfolio | PSD check、4 KKT residual、gap |
| SOCP | $\min f^\top x$ s.t. $\lVert A_ix+b_i\rVert_2\le c_i^\top x+d_i$ | norm regression、tracking-error / risk bound | cone feasibility、primal/dual certificate |

### LPへのepigraph変換

$\ell_1$ regression $\min_\beta\sum_i|y_i-x_i^\top\beta|$ は、$t_i\ge0$ を導入して

$$
\begin{aligned}
\min_{\beta,t}\quad & \mathbf{1}^\top t\\
\text{s.t.}\quad & X\beta-y\le t,\\
& -(X\beta-y)\le t
\end{aligned}
$$

と書ける。補助変数を増やすが、objectiveとconstraintsはaffineである。

### QPとしてのportfolio

covariance $\Sigma\succeq0$、expected-return estimate $\mu$、risk-return weight $\gamma$ に対して

$$
\min_w\ \frac12w^\top\Sigma w-\gamma\mu^\top w
\quad\text{s.t.}\quad
\mathbf1^\top w=1,\quad \ell\le w\le u
$$

はconvex QPである。$\mu$の推定誤差はQPのconvexityとは別のmodel riskである。

### SOCPとしてのleast squares

$$
\min_{\beta,t}\ t
\quad\text{s.t.}\quad
\lVert X\beta-y\rVert_2\le t
$$

はsecond-order cone constraintを一つ持つ。SciPyの一般非線形constraintで小例を解けても、専用conic solverのdual cone certificateを得たことにはならない。
"""),
    md(r"""
## 3. convexityとDCPの判定境界

DCPはatomのcurvature、sign、monotonicityを式木へ伝播する十分条件であり、数学的凸性の必要条件ではない。本教材はCVXPYを依存関係へ追加しないため、自動DCP checkerは利用しない。次の表のstatusは公式composition rulesを手でtraceした教材上の判定である。
"""),
    code("""
dcp_boundary = pd.DataFrame(
    [
        {
            "expression": "square(a @ x - b)",
            "mathematical_curvature": "convex",
            "manual_dcp_trace": "accepted",
            "reason": "convex square applied to an affine expression",
        },
        {
            "expression": "sqrt(1 + square(x))",
            "mathematical_curvature": "convex",
            "manual_dcp_trace": "unknown",
            "reason": "concave increasing sqrt applied to a convex expression",
        },
        {
            "expression": "norm(hstack([1, x]), 2)",
            "mathematical_curvature": "convex",
            "manual_dcp_trace": "accepted",
            "reason": "norm atom applied to an affine vector",
        },
        {
            "expression": "x * y",
            "mathematical_curvature": "nonconvex on R2",
            "manual_dcp_trace": "unknown",
            "reason": "product of two variables",
        },
    ]
)
display(dcp_boundary)
"""),
    md(r"""
`unknown`には「convexだがgrammarが証明できない」と「実際にnonconvex」の両方が入る。したがってunknownからnonconvexを結論しない。$\sqrt{1+x^2}=\lVert(1,x)\rVert_2$ のように同値なaccepted表現へ直すか、domainを含む独立証明を残す。

`validate_quadratic_program`が証明する範囲も限定される。対称な$P$の最小固有値とaffine constraintのshape・有限性を検査し、$P\succeq0$のQPをcertifyする。しかし一般のexpression tree、SOCP、SDPのDCP checkerではない。SciPyが`success=True`を返すこともconvexity proofではない。
"""),
    md(r"""
## 4. QP contractをcodeへ固定する

共通APIは

$$
\min_x\ \frac12x^\top Px+q^\top x
\quad\text{s.t.}\quad
Gx\le h,\ Ax=b,\ \ell\le x\le u
$$

を採用する。$P$、$q$、$G$、$h$のscaleとunitsは別々に記録する。`quadratic_objective`は候補点を評価し、`solve_quadratic_program`はsolver出力に加えてKKT diagnosticsを返す。
"""),
    code("""
portfolio_covariance = np.array(
    [
        [0.040, 0.012, 0.008],
        [0.012, 0.025, 0.006],
        [0.008, 0.006, 0.016],
    ]
)
expected_returns = np.array([0.035, 0.024, 0.017])
risk_return_weight = 0.8

portfolio_problem = QuadraticProgram(
    P=portfolio_covariance,
    q=-risk_return_weight * expected_returns,
    A=np.ones((1, 3)),
    b=np.array([1.0]),
    lower_bounds=np.zeros(3),
    upper_bounds=np.full(3, 0.8),
    variable_units=("weight", "weight", "weight"),
    equality_units=("weight",),
    name="long_only_portfolio",
)
portfolio_validation = validate_quadratic_program(portfolio_problem)
portfolio_solution = solve_quadratic_program(
    portfolio_problem,
    initial=np.full(3, 1.0 / 3.0),
    method="SLSQP",
)

portfolio_table = pd.DataFrame(
    {
        "asset": ["A", "B", "C"],
        "weight": portfolio_solution.x,
    }
)
display(portfolio_table.round(6))
print("objective:", portfolio_solution.primal_objective)
print("KKT passed:", portfolio_solution.diagnostics.kkt.passed)
print("validation:", portfolio_validation)
"""),
    md(r"""
このsolutionは合成入力に対するmodel outputであり、実運用推奨ではない。expected return推定、covariance安定性、transaction cost、情報時点は最適化外の入力契約として別途検証する。
"""),
    md(r"""
## 5. 同じleast squares、異なるvariable scale

二列目が$10^6$倍のunitを持つdesign matrixを作る。physical coefficientを$\beta=(\beta_0,\beta_1)$とし、scaled variable $z$を

$$
\beta=Sz,
\qquad
S=\operatorname{diag}(1,10^{-6})
$$

で定義する。二つのformulationは同じpredictionを表すが、Hessianは

$$
P_z=S^\top P_\beta S
$$

へ変わる。objectiveを比較するときは定数$y^\top y$を両方で落としているため、同じ候補なら差が一致する。
"""),
    code("""
regression_rng = task_rng("scaled_regression")
sample_size = 120
raw_feature = regression_rng.uniform(-1.0, 1.0, size=sample_size)
design_unscaled = np.column_stack(
    [np.ones(sample_size), 1.0e6 * raw_feature]
)
true_coefficients = np.array([0.7, 0.8e-6])
outcome = design_unscaled @ true_coefficients + regression_rng.normal(
    scale=0.03,
    size=sample_size,
)

P_unscaled = 2.0 * design_unscaled.T @ design_unscaled / sample_size
q_unscaled = -2.0 * design_unscaled.T @ outcome / sample_size
variable_transform = np.diag([1.0, 1.0e-6])
P_scaled = variable_transform.T @ P_unscaled @ variable_transform
q_scaled = variable_transform.T @ q_unscaled

unscaled_problem = QuadraticProgram(
    P=P_unscaled,
    q=q_unscaled,
    lower_bounds=np.array([-np.inf, 0.0]),
    variable_units=("outcome", "outcome_per_raw_unit"),
    name="unscaled_regression",
)
scaled_problem = QuadraticProgram(
    P=P_scaled,
    q=q_scaled,
    lower_bounds=np.array([-np.inf, 0.0]),
    variable_units=("outcome", "outcome_per_scaled_unit"),
    name="scaled_regression",
)

formulation_solutions = {
    (formulation, method): solve_quadratic_program(
        problem,
        initial=np.zeros(2),
        method=method,
    )
    for formulation, problem in (
        ("Raw physical variables", unscaled_problem),
        ("Scaled variables", scaled_problem),
    )
    for method in ("SLSQP", "trust-constr")
}
unscaled_solution = formulation_solutions[("Raw physical variables", "SLSQP")]
scaled_solution = formulation_solutions[("Scaled variables", "SLSQP")]
scaled_coefficients_in_physical_units = variable_transform @ scaled_solution.x

scaling_rows = []
for (label, method), solution in formulation_solutions.items():
    problem = unscaled_problem if label == "Raw physical variables" else scaled_problem
    physical_coefficients = (
        solution.x if label == "Raw physical variables" else variable_transform @ solution.x
    )
    prediction = design_unscaled @ physical_coefficients
    scaling_rows.append(
        {
            "formulation": label,
            "method": method,
            "hessian_condition_number": np.linalg.cond(problem.P),
            "prediction_rmse": np.sqrt(np.mean((outcome - prediction) ** 2)),
            "slope_in_physical_units": physical_coefficients[1],
            "primal_objective": quadratic_objective(problem, solution.x),
            "iterations": solution.iterations,
            "optimizer_success": solution.diagnostics.optimizer_success,
            "raw_stationarity": solution.diagnostics.kkt.raw_stationarity,
            "stationarity_residual": solution.diagnostics.kkt.stationarity,
            "primal_bound_residual": solution.diagnostics.kkt.primal_bounds,
            "raw_complementarity": solution.diagnostics.kkt.raw_complementarity,
            "complementarity_residual": solution.diagnostics.kkt.complementarity,
            "duality_gap": solution.diagnostics.kkt.duality_gap,
            "KKT_passed": solution.diagnostics.kkt.passed,
        }
    )

scaling_table = pd.DataFrame(scaling_rows)
display(
    scaling_table[
        [
            "formulation",
            "method",
            "hessian_condition_number",
            "prediction_rmse",
            "slope_in_physical_units",
            "iterations",
            "optimizer_success",
            "KKT_passed",
        ]
    ]
)
display(
    scaling_table[
        [
            "formulation",
            "method",
            "raw_stationarity",
            "stationarity_residual",
            "primal_bound_residual",
            "raw_complementarity",
            "complementarity_residual",
            "duality_gap",
        ]
    ]
)
"""),
    code("""
fig = go.Figure()
for method, method_rows in scaling_table.groupby("method", sort=False):
    fig.add_bar(
        x=method_rows["formulation"],
        y=method_rows["hessian_condition_number"],
        name=method,
    )
fig.update_yaxes(type="log")
fig.update_layout(
    title="Equivalent predictions can have very different conditioning",
    xaxis_title="Formulation",
    yaxis_title="Condition number (log scale)",
    barmode="group",
    template="plotly_white",
)
fig.show()

prediction_disagreement = np.max(
    np.abs(
        design_unscaled @ unscaled_solution.x
        - design_unscaled @ scaled_coefficients_in_physical_units
    )
)
print("maximum prediction disagreement:", prediction_disagreement)
"""),
    md(r"""
variable scalingはestimandを変えない同値変換である。比較すべきなのは、solver内部のraw objectiveだけでなく、physical unitsへ戻したprediction、constraint residual、stationarity、conditioningである。大きなcondition numberでも解ける場合はあるが、それはscaleを無視してよい理由ではない。

この決定的runでは四つの組合せすべてでoptimizer statusはsuccessだが、strictなKKT gateは同じ判定にならない。特にtrust-constrのunscaled runは近いpredictionを返してもstationarity監査に失敗し、scaled runではresidualが大幅に小さくなる。これは「予測が近い」「solverが停止した」「指定toleranceで最適性を証明した」を分離すべき具体例である。

`KKTResiduals`のdimensionless判定はproblem scaleを含むdenominatorを使い、raw residualも元の単位で保存する。well-scaledなfloat64小問題では$100\sqrt{\epsilon_{\rm mach}}\approx1.5\times10^{-6}$が一つのgate候補になるが、普遍定数ではない。conditioning、solver tolerance、data uncertaintyを根拠に設定する。
"""),
    md(r"""
## 6. SOCP formulationを一般solverで照合する

least-squares epigraphをSciPy `NonlinearConstraint`で解き、`numpy.linalg.lstsq`と照合する。これはformulationの数値確認であり、SciPyをSOCP専用solverまたはDCP checkerとして扱う例ではない。
"""),
    code("""
socp_rng = task_rng("socp_regression")
socp_design = np.column_stack(
    [np.ones(40), socp_rng.normal(size=40)]
)
socp_outcome = (
    socp_design @ np.array([0.4, -0.25])
    + socp_rng.normal(scale=0.08, size=40)
)


def socp_objective(candidate):
    return float(candidate[-1])


def cone_residual(candidate):
    coefficients = candidate[:-1]
    epigraph_variable = candidate[-1]
    return np.linalg.norm(socp_design @ coefficients - socp_outcome) - epigraph_variable


ols_coefficients = np.linalg.lstsq(
    socp_design,
    socp_outcome,
    rcond=None,
)[0]
initial_socp = np.r_[
    ols_coefficients,
    1.1 * np.linalg.norm(socp_design @ ols_coefficients - socp_outcome),
]
socp_result = minimize(
    socp_objective,
    initial_socp,
    method="SLSQP",
    bounds=[(None, None), (None, None), (0.0, None)],
    constraints=[NonlinearConstraint(cone_residual, -np.inf, 0.0)],
    options={"ftol": 1.0e-12, "maxiter": 500},
)

socp_coefficient_error = np.linalg.norm(socp_result.x[:-1] - ols_coefficients)
socp_cone_violation = max(cone_residual(socp_result.x), 0.0)
print("general solver success:", socp_result.success)
print("coefficient disagreement:", socp_coefficient_error)
print("raw cone violation:", socp_cone_violation)
assert socp_result.success
assert socp_coefficient_error < 1.0e-6
assert socp_cone_violation < 1.0e-8
"""),
    md(r"""
objective $t$ とcone violationを別々に検査した。SLSQPのsuccessは、この小例で停止条件を満たしたという情報である。SOCPの強双対性やcone dual certificateを主張するには、constraint qualificationと対応するprimal / dual情報を持つconic solverが必要である。
"""),
    md(r"""
## 7. LPのfeasible、infeasible、unboundedを区別する

次のfeasibility problemを考える。

$$
x_1+x_2=1,
\qquad x_1\ge1,
\qquad x_2\ge1.
$$

lower boundsだけで$x_1+x_2\ge2$なので、等式と同時には満たせない。zero objectiveのLPとして`linprog`へ渡し、statusを保存する。同時にbounded feasible caseとunbounded caseを作り、三つのstatusを区別する。SciPy `linprog`の既定boundsは$x\ge0$だが、hidden domainを避けるためすべて明示する。
"""),
    code("""
feasible_result = linprog(
    c=np.array([1.0, 2.0]),
    A_ub=np.array([[-1.0, -1.0]]),
    b_ub=np.array([-1.0]),
    bounds=[(0.0, None), (0.0, None)],
    method="highs",
)
infeasible_result = linprog(
    c=np.zeros(2),
    A_eq=np.ones((1, 2)),
    b_eq=np.array([1.0]),
    bounds=[(1.0, None), (1.0, None)],
    method="highs",
)
unbounded_result = linprog(
    c=np.array([-1.0]),
    bounds=[(0.0, None)],
    method="highs",
)

lp_status_table = pd.DataFrame(
    [
        {
            "case": label,
            "solver_success": result.success,
            "solver_status": result.status,
            "objective_available": result.fun is not None,
            "candidate_available": result.x is not None,
        }
        for label, result in (
            ("bounded feasible", feasible_result),
            ("infeasible", infeasible_result),
            ("unbounded", unbounded_result),
        )
    ]
)
display(lp_status_table)
print("feasible objective:", feasible_result.fun)
print("solver message:", infeasible_result.message)
print("unbounded message:", unbounded_result.message)
assert feasible_result.success
assert not infeasible_result.success and infeasible_result.status == 2
assert not unbounded_result.success and unbounded_result.status == 3
"""),
    md(r"""
infeasibleはfeasible pointがなく、unboundedはfeasible directionに沿ってobjectiveを有限の下限なく改善できる。どちらも`success=False`だけで一括しない。infeasible statusのとき、存在しない$x$やobjectiveを前回runから流用しない。solver certificateの種類はmethod依存なので、この例ではlower boundから得る解析的矛盾も残す。

presolveは高速化と早期診断に有用だが、statusが疑わしいcaseではpresolve設定を変えた再実行と独立certificateを追加する。実務ではirreducible infeasible subsystem、bound relaxation、入力単位の誤りを調べ、元のproblemと緩和problemを別artifactにする。
"""),
    md(r"""
## 8. 失敗モード

### Core / Advancedの境界

CoreはLP・QP・SOCPのformulation、manual DCP rule trace、scale-aware feasibilityまでである。SDP、一般conic duality、composition ruleの証明は**Advanced**とし、Coreのcertificateを完成させた後に扱う。

- functionのdomainを無視してHessianだけでconvexityを判定する
- DCP unknownをnonconvex、DCP acceptedをaccurate solutionと読む
- NumPy / SciPyに存在しないDCP checkerやconic certificateを暗黙に仮定する
- $P$が非対称またはindefiniteでもQPとして同じ保証を主張する
- variable scalingでphysical meaningを変え、同値問題と呼ぶ
- raw objectiveだけを比較し、constant termとunitsを記録しない
- infeasible statusでも最後のiterateをsolutionとして報告する
- cone violationを検査せず一般非線形solverのsuccessをSOCP certificateと呼ぶ
"""),
    md(r"""
## 9. 段階別演習

### 基礎

1. affine set、Euclidean ball、二点集合のconvexityを定義から判定せよ。
2. $\ell_1$ regressionのepigraph LPで各blockのshapeを記せ。
3. constrained least squaresとportfolio QPの$P,q,G,h,A,b$を作れ。

### 標準

4. regressionのscale factorを$10^2,10^4,10^6,10^8$へ変え、conditioningとKKT residualを比較せよ。
5. $\sqrt{1+x^2}$についてHessian proofとDCP rule traceを別々に書け。
6. feasible QPのconstraintを矛盾させ、status、raw residual、入力単位を記録せよ。
7. SOCP epigraph solutionのnorm residualを元データから再計算せよ。

### 研究

8. **Advanced:** semidefinite constraintを含む問題を一つformulateし、QP/SOCP validatorがunsupportedとすべき理由を示せ。
9. portfolio QPでexpected returnを摂動し、convex optimization errorとinput estimation errorを分離せよ。
"""),
    md(r"""
## 10. Exit Criteria

- [ ] domainを含めてset・function・problemのconvexityを説明できる
- [ ] LP、QP、SOCPを代表的な回帰・portfolio問題へ対応づけられる
- [ ] DCP accepted / unknownとmathematical convexityを区別できる
- [ ] QP validatorと一般DCP / conic certificateの範囲を区別できる
- [ ] variable scaling後にphysical unitsへ戻してsolutionを比較できる
- [ ] objective、primal feasibility、statusを別々に報告できる
- [ ] infeasible caseを候補解の成功として報告しない
"""),
    md(r"""
## 11. 出典

- [Boyd and Vandenberghe, *Convex Optimization*](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf) — convex analysis、LP/QP/SOCP、problem transformationsの著者公開版
- [Grant, Boyd, and Ye, *Disciplined Convex Programming*](https://web.stanford.edu/~boyd/papers/pdf/disc_cvx_prog.pdf) — DCPをcomposition ruleによる十分条件として定式化した原論文
- [CVXPY: Disciplined Convex Programming](https://www.cvxpy.org/tutorial/dcp/) — unknownと同値なaccepted formulationを示す公式tutorial
- [SciPy `minimize`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html) — SLSQP・trust-constrを含む一般optimization interface
- [SciPy `linprog`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html) — LP status、HiGHS method、marginalを含む公式API
- [MOSEK Modeling Cookbook: Conic Quadratic Optimization](https://docs.mosek.com/modeling-cookbook/cqo.html) — second-order cone formulationの公式modeling guide

次章では、同じQPにdual variableを導入し、4種類のKKT residual、duality gap、shadow-price finite differenceでsolverを独立監査する。
"""),
]
