"""Builder for notebook 21: first- and second-order optimization algorithms."""

from nbkit import code, md

cells = [
    md(r"""
# 21. Week 15 — 一次法、二次法、制約とnonsmoothness

> iterateが動かなくなったことではなく、objective gap、gradient mapping、feasibilityで収束を判定する。

## 学習目標

- smoothness、strong convexity、conditioningからgradient descentのstepを選ぶ
- backtracking line searchと固定stepの仮定・失敗を比較する
- Newton methodでHessianを逆行列にせず線形方程式として解く理由を説明する
- BFGSをanalytic gradient付きSciPy実装と照合する
- projected gradientのprojectionとgradient mappingを検査する
- proximal gradientとsoft-thresholdingでL1-regularized problemを解く
- raw / scaled problemでconvergence、objective gap、feasibilityを比較する

## 前提知識

- Week 13のconvex function、Lipschitz gradient、QP
- Week 14のKKT、stationarity、primal feasibility
- eigenvalue、condition number、gradient、Hessian

CoreはGD、backtracking、Newton、BFGSの役割、projected / proximal gradientである。coordinate descent、ADMM、SGD、momentum、accelerated proximal gradientはAdvancedに置く。
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from scipy.optimize import minimize

from quant_textbook.optimization import (
    backtracking_gradient_descent,
    gradient_descent,
    newton_method,
    projected_gradient,
    proximal_gradient,
)

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
NOTEBOOK_ID = 21
TASK_IDS = {
    "quadratic": 1,
    "projected": 2,
    "proximal": 3,
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
## 1. 停止判定をproblem structureへ合わせる

unconstrained smooth problemでは$\|\nabla f(x_k)\|$、reference optimumがある実験では$f(x_k)-f^*$を使える。closed convex set$C$へのprojected gradientでは

$$
G_\alpha(x)=\frac{1}{\alpha}
\left[x-\Pi_C\{x-\alpha\nabla f(x)\}\right]
$$

を使う。composite problem $F(x)=f(x)+g(x)$では

$$
G_\alpha(x)=\frac{1}{\alpha}
\left[x-\operatorname{prox}_{\alpha g}
\{x-\alpha\nabla f(x)\}\right]
$$

とする。$x_{k+1}-x_k$だけでは、stepが小さ過ぎて進まない状態と最適点を区別できない。制約付きproblemは全iterationのfeasibilityも保存する。

library traceは二つの量を分離する。raw mapping $g_k=\|G_\alpha(x_k)\|_2$はgradientと同じ単位を持ち、problem間でscaleが変わる。停止判定と`gradient_mapping_norms`は、$g_0>0$なら

$$
\widehat g_k=\frac{g_k}{g_0}
$$

という初期値正規化を使うため、objective全体を正の定数倍しても不変である。`raw_gradient_mapping_norms`と`gradient_mapping_scale=g_0`も保存し、物理単位の大きさを失わない。初期点がすでにstationaryならraw zeroをそのまま合格とし、zero除算はしない。

feasibilityもraw violation $v_k\ge0$とdimensionless traceを分ける。$v_0>0$なら`feasibility_values`は$v_k/v_0$、`raw_feasibility_values`は元のconstraint単位、`feasibility_scale`は$v_0$である。feasible startで$v_0=0$なら、以後のraw zeroだけをnormalized zeroとし、nonzero violationは無限大としてfailさせる。これによりzero除算を避けながら、feasible setから外れたiterateを見逃さない。
"""),
    md(r"""
## 2. ill-conditioned quadratic

$$
f(x)=\frac12x^\top Qx,
\qquad
Q=\operatorname{diag}(1,10^4)
$$

を考える。gradientは$Qx$、Lipschitz constantは$L=\lambda_{\max}(Q)=10^4$、strong-convexity constantは$\mu=1$、condition numberは$\kappa=L/\mu=10^4$である。

固定step GDはquadraticに対して$0<\alpha<2/L$で安定する。$\alpha=1/L$は高曲率方向を直ちに縮めるが、低曲率方向は一回ごとに$1-1/10^4$倍しか縮まない。
"""),
    code("""
quadratic_hessian = np.diag([1.0, 1.0e4])
quadratic_lipschitz = float(np.linalg.eigvalsh(quadratic_hessian).max())
quadratic_strong_convexity = float(np.linalg.eigvalsh(quadratic_hessian).min())
quadratic_condition = quadratic_lipschitz / quadratic_strong_convexity
quadratic_initial = np.array([8.0, 8.0])


def quadratic_objective(point):
    return float(0.5 * point @ quadratic_hessian @ point)


def quadratic_gradient(point):
    return quadratic_hessian @ point


def quadratic_second_derivative(point):
    return quadratic_hessian


stable_gd = gradient_descent(
    quadratic_objective,
    quadratic_gradient,
    quadratic_initial,
    step_size=1.0 / quadratic_lipschitz,
    tolerance=1.0e-10,
    max_iterations=2_500,
)
unstable_gd = gradient_descent(
    quadratic_objective,
    quadratic_gradient,
    quadratic_initial,
    step_size=2.05 / quadratic_lipschitz,
    tolerance=1.0e-10,
    max_iterations=80,
)

print("condition number:", quadratic_condition)
print("stable converged / iterations:", stable_gd.converged, stable_gd.iterations)
print("unstable converged / iterations:", unstable_gd.converged, unstable_gd.iterations)
print(
    "unstable objective first / last:",
    unstable_gd.trace.objective_values[0],
    unstable_gd.trace.objective_values[-1],
)
assert unstable_gd.trace.objective_values[-1] > unstable_gd.trace.objective_values[0]
"""),
    code("""
fig = go.Figure()
for result, label in (
    (stable_gd, "GD: alpha = 1/L"),
    (unstable_gd, "GD: alpha = 2.05/L"),
):
    objective_gap = np.maximum(
        np.asarray(result.trace.objective_values, dtype=float),
        np.finfo(float).tiny,
    )
    fig.add_scatter(
        x=np.arange(objective_gap.size),
        y=objective_gap,
        mode="lines",
        name=label,
    )
fig.update_yaxes(type="log")
fig.update_layout(
    title="A step just above 2/L diverges on the high-curvature direction",
    xaxis_title="Iteration",
    yaxis_title="Objective gap (log scale)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
`converged=False`は必ずしもimplementation failureではない。stable runはiteration budget内にlow-curvature方向を十分縮められず、unstable runはstep仮定を破った。message、gradient mapping、objective traceを一緒に読む。
"""),
    md(r"""
## 3. backtrackingとfeature scaling

Armijo backtrackingはdescent direction $p$に対し

$$
f(x+tp)\le f(x)+c_1t\nabla f(x)^\top p
$$

を満たすまでstepを縮める。未知の$L$に対する安全策になるが、conditioning自体を消さない。

変数変換$z=Q^{1/2}x$を使えば$f=\frac12\|z\|^2$となる。この例ではscaleが既知なので、scaled problemのcondition numberは1である。これは同じphysical pointへ戻せる同値変換であり、objectiveを変更するregularizationではない。
"""),
    code("""
backtracking_gd = backtracking_gradient_descent(
    quadratic_objective,
    quadratic_gradient,
    quadratic_initial,
    step_size=1.0,
    tolerance=1.0e-10,
    max_iterations=2_500,
)

scale_matrix = np.diag(np.sqrt(np.diag(quadratic_hessian)))
scaled_initial = scale_matrix @ quadratic_initial


def scaled_objective(point):
    return float(0.5 * point @ point)


def scaled_gradient(point):
    return point


scaled_gd = gradient_descent(
    scaled_objective,
    scaled_gradient,
    scaled_initial,
    step_size=1.0,
    tolerance=1.0e-10,
    max_iterations=20,
)
scaled_solution_in_physical_units = np.linalg.solve(scale_matrix, scaled_gd.x)

conditioning_table = pd.DataFrame(
    [
        {
            "method": "fixed-step raw",
            "condition_number": quadratic_condition,
            "iterations": stable_gd.iterations,
            "final_objective_gap": quadratic_objective(stable_gd.x),
            "final_normalized_mapping": stable_gd.gradient_mapping_norm,
            "final_raw_mapping": stable_gd.raw_gradient_mapping_norm,
            "initial_raw_mapping_scale": stable_gd.trace.gradient_mapping_scale,
        },
        {
            "method": "backtracking raw",
            "condition_number": quadratic_condition,
            "iterations": backtracking_gd.iterations,
            "final_objective_gap": quadratic_objective(backtracking_gd.x),
            "final_normalized_mapping": backtracking_gd.gradient_mapping_norm,
            "final_raw_mapping": backtracking_gd.raw_gradient_mapping_norm,
            "initial_raw_mapping_scale": backtracking_gd.trace.gradient_mapping_scale,
        },
        {
            "method": "fixed-step scaled",
            "condition_number": 1.0,
            "iterations": scaled_gd.iterations,
            "final_objective_gap": quadratic_objective(scaled_solution_in_physical_units),
            "final_normalized_mapping": scaled_gd.gradient_mapping_norm,
            "final_raw_mapping": scaled_gd.raw_gradient_mapping_norm,
            "initial_raw_mapping_scale": scaled_gd.trace.gradient_mapping_scale,
        },
    ]
)
display(conditioning_table)
for result in (stable_gd, backtracking_gd, scaled_gd):
    np.testing.assert_allclose(
        result.trace.gradient_mapping_norms,
        result.trace.raw_gradient_mapping_norms
        / result.trace.gradient_mapping_scale,
        rtol=1.0e-14,
        atol=0.0,
    )
"""),
    md(r"""
backtrackingのstep historyが小さい値へ落ちた後も、raw problemのlow-curvature方向は遅い。line searchとpreconditioning / scalingは答える問題が異なる。scaled rowのraw mappingは$z$座標のderivative単位であり、$x$座標のraw normと直接比較しない。初期値正規化はobjectiveの正のscalar倍には不変だが、variable metricを変える座標変換まで不変にするものではない。
"""),
    md(r"""
## 4. Newton methodとBFGS

Newton directionは

$$
\nabla^2f(x_k)p_k=-\nabla f(x_k)
$$

を解いて求める。`inv(H) @ g`を作らず`solve(H, -g)`を使う。正定値quadraticではexact arithmeticで一回のfull stepにより最適点へ到達する。一般の非quadratic problemではdomain、Hessian definiteness、line searchが必要である。

BFGSはgradient差からinverse Hessian approximationを更新するquasi-Newton法である。本章では自作NewtonとSciPy BFGSをanalytic gradient付きで比較する。
"""),
    code("""
newton_result = newton_method(
    quadratic_objective,
    quadratic_gradient,
    quadratic_second_derivative,
    quadratic_initial,
    tolerance=1.0e-10,
    max_iterations=20,
)

bfgs_objective_trace = [quadratic_objective(quadratic_initial)]


def record_bfgs(point):
    bfgs_objective_trace.append(quadratic_objective(point))


bfgs_result = minimize(
    quadratic_objective,
    quadratic_initial,
    jac=quadratic_gradient,
    method="BFGS",
    callback=record_bfgs,
    options={"gtol": 1.0e-10, "maxiter": 500},
)

second_order_table = pd.DataFrame(
    [
        {
            "method": "Newton with analytic Hessian",
            "success": newton_result.converged,
            "iterations": newton_result.iterations,
            "objective_gap": quadratic_objective(newton_result.x),
            "gradient_norm": np.linalg.norm(quadratic_gradient(newton_result.x)),
        },
        {
            "method": "SciPy BFGS with analytic gradient",
            "success": bfgs_result.success,
            "iterations": bfgs_result.nit,
            "objective_gap": quadratic_objective(bfgs_result.x),
            "gradient_norm": np.linalg.norm(quadratic_gradient(bfgs_result.x)),
        },
    ]
)
display(second_order_table)
np.testing.assert_allclose(newton_result.x, np.zeros(2), atol=1.0e-10, rtol=0.0)
np.testing.assert_allclose(bfgs_result.x, np.zeros(2), atol=1.0e-7, rtol=0.0)
"""),
    md(r"""
このquadraticでNewtonが速いことは、全問題で二次法が優れるという結論ではない。Hessian形成・factorizationはdenseな$n$変数でmemory $O(n^2)$、time $O(n^3)$になり得る。BFGSはexact Hessianを要求しないが、curvature condition、line search、memoryのtrade-offを持つ。
"""),
    md(r"""
## 5. projected gradient — raw gradientがzeroでない最適点

$$
\min_{x\ge0}\ \frac12\|x-c\|_2^2,
\qquad c=(-2,1.5)
$$

の解は$x^*=(0,1.5)$である。境界で$\nabla f(x^*)=(2,0)$はzeroではないが、feasibleな負方向へは進めない。したがってraw gradient normではなくprojected gradient mappingを使う。
"""),
    code("""
projected_center = np.array([-2.0, 1.5])
projected_initial = np.array([3.0, 4.0])


def projected_objective(point):
    residual = point - projected_center
    return float(0.5 * residual @ residual)


def projected_gradient_function(point):
    return point - projected_center


def nonnegative_projection(point):
    return np.maximum(point, 0.0)


def nonnegative_violation(point):
    return float(max(0.0, -np.min(point)))


projected_result = projected_gradient(
    projected_objective,
    projected_gradient_function,
    nonnegative_projection,
    projected_initial,
    step_size=0.8,
    feasibility=nonnegative_violation,
    tolerance=1.0e-10,
    max_iterations=200,
)
projected_exact = np.maximum(projected_center, 0.0)
mapping_at_solution = (
    projected_result.x
    - nonnegative_projection(
        projected_result.x - 0.8 * projected_gradient_function(projected_result.x)
    )
) / 0.8

print("solution:", projected_result.x)
print("raw gradient norm:", np.linalg.norm(projected_gradient_function(projected_result.x)))
print("raw projected mapping norm:", np.linalg.norm(mapping_at_solution))
print("trace raw projected mapping norm:", projected_result.raw_gradient_mapping_norm)
print("normalized projected mapping:", projected_result.gradient_mapping_norm)
print(
    "maximum normalized feasibility:",
    max(projected_result.trace.feasibility_values),
)
print(
    "maximum raw feasibility:",
    max(projected_result.trace.raw_feasibility_values),
)
print("initial raw feasibility scale:", projected_result.trace.feasibility_scale)
np.testing.assert_allclose(projected_result.x, projected_exact, atol=1.0e-9, rtol=0.0)
np.testing.assert_allclose(
    projected_result.raw_gradient_mapping_norm,
    np.linalg.norm(mapping_at_solution),
    rtol=1.0e-10,
    atol=1.0e-12,
)
np.testing.assert_array_equal(
    projected_result.trace.raw_feasibility_values,
    np.zeros_like(projected_result.trace.raw_feasibility_values),
)
np.testing.assert_array_equal(
    projected_result.trace.feasibility_values,
    np.zeros_like(projected_result.trace.feasibility_values),
)
assert projected_result.trace.feasibility_scale == 0.0
assert projected_result.raw_feasibility == 0.0
"""),
    md(r"""
projectionの実装も契約対象である。closed convex setへのEuclidean projectionは一意だが、nonconvex setや近似projectionへ同じ保証を移せない。この例はfeasible startなので`feasibility_scale=0`であり、全iterationのraw violationとnormalized feasibilityがともにexact zeroであることを別々に検査した。
"""),
    md(r"""
## 6. proximal gradient — ill-conditioned quadratic + L1

$$
F(x)=\frac12\sum_j q_j(x_j-b_j)^2+\lambda\|x\|_1
$$

を考える。smooth部分の$L=\max_jq_j$、L1項のproximal operatorはsoft-threshold

$$
S_{\alpha\lambda}(v)_j
=\operatorname{sign}(v_j)(|v_j|-\alpha\lambda)_+
$$

である。$Q$がdiagonalなのでreference solutionは

$$
x_j^*=S_{\lambda/q_j}(b_j)
$$

と解析的に得られる。これをobjective gapとcomposite gradient mappingのoracleにする。
"""),
    code("""
proximal_curvature = np.array([1.0, 4.0, 25.0, 100.0])
proximal_center = np.array([2.0, -0.35, 0.08, -1.0])
proximal_penalty = 0.3
proximal_initial = np.array([3.0, 2.0, -2.0, 2.5])
proximal_lipschitz = float(proximal_curvature.max())
PROXIMAL_NORMALIZED_TOLERANCE = 5.0e-10


def smooth_objective(point):
    residual = point - proximal_center
    return float(0.5 * np.sum(proximal_curvature * residual**2))


def smooth_gradient(point):
    return proximal_curvature * (point - proximal_center)


def nonsmooth_objective(point):
    return float(proximal_penalty * np.sum(np.abs(point)))


def soft_threshold(values, threshold):
    return np.sign(values) * np.maximum(np.abs(values) - threshold, 0.0)


def l1_proximal_operator(values, step_size):
    return soft_threshold(values, step_size * proximal_penalty)


proximal_result = proximal_gradient(
    smooth_objective,
    smooth_gradient,
    nonsmooth_objective,
    l1_proximal_operator,
    proximal_initial,
    step_size=1.0 / proximal_lipschitz,
    tolerance=PROXIMAL_NORMALIZED_TOLERANCE,
    max_iterations=5_000,
)
proximal_exact = soft_threshold(
    proximal_center,
    proximal_penalty / proximal_curvature,
)
exact_objective = smooth_objective(proximal_exact) + nonsmooth_objective(proximal_exact)
proximal_objective_gap = (
    smooth_objective(proximal_result.x)
    + nonsmooth_objective(proximal_result.x)
    - exact_objective
)

proximal_audit = pd.DataFrame(
    {
        "coordinate": np.arange(proximal_exact.size),
        "curvature": proximal_curvature,
        "reference": proximal_exact,
        "estimated": proximal_result.x,
        "absolute_error": np.abs(proximal_result.x - proximal_exact),
    }
)
display(proximal_audit)
print("objective gap:", proximal_objective_gap)
print("final normalized composite mapping:", proximal_result.gradient_mapping_norm)
print("final raw composite mapping norm:", proximal_result.raw_gradient_mapping_norm)
print("initial raw mapping scale:", proximal_result.trace.gradient_mapping_scale)
np.testing.assert_allclose(proximal_result.x, proximal_exact, atol=2.0e-7, rtol=0.0)
assert proximal_objective_gap < 1.0e-10
assert proximal_result.gradient_mapping_norm <= PROXIMAL_NORMALIZED_TOLERANCE
"""),
    code("""
proximal_trace_gap = np.maximum(
    np.asarray(proximal_result.trace.objective_values) - exact_objective,
    np.finfo(float).tiny,
)
proximal_normalized_mapping = np.maximum(
    np.asarray(proximal_result.trace.gradient_mapping_norms),
    np.finfo(float).tiny,
)
proximal_raw_mapping = np.maximum(
    np.asarray(proximal_result.trace.raw_gradient_mapping_norms),
    np.finfo(float).tiny,
)

fig = make_subplots(
    rows=1,
    cols=3,
    subplot_titles=(
        "Objective gap",
        "Normalized composite mapping",
        "Raw composite mapping",
    ),
)
fig.add_scatter(
    x=np.arange(proximal_trace_gap.size),
    y=proximal_trace_gap,
    mode="lines",
    name="Objective gap",
    row=1,
    col=1,
)
fig.add_scatter(
    x=np.arange(proximal_normalized_mapping.size),
    y=proximal_normalized_mapping,
    mode="lines",
    name="Normalized mapping",
    row=1,
    col=2,
)
fig.add_scatter(
    x=np.arange(proximal_raw_mapping.size),
    y=proximal_raw_mapping,
    mode="lines",
    name="Raw mapping",
    row=1,
    col=3,
)
fig.update_yaxes(type="log", row=1, col=1)
fig.update_yaxes(type="log", row=1, col=2)
fig.update_yaxes(type="log", row=1, col=3)
fig.update_layout(
    title="Value, dimensionless stopping evidence, and raw units stay separate",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
L1 objectiveはzeroでnondifferentiableなので、raw gradientを作ってBFGSへ渡す問題ではない。soft-thresholdはこの$nonsmooth$ termのstructureを使う。parameter differenceだけで止めず、objective gap、初期値で正規化したdimensionless composite mapping、gradient単位を保つraw mappingを別panelで示した。
"""),
    md(r"""
## 7. method選択の境界

| Structure | Core候補 | 主な診断 | 典型的failure |
|---|---|---|---|
| smooth、$L$既知 | fixed-step GD | normalized / raw gradient norm、gap | $\alpha\ge2/L$で発散 |
| smooth、$L$不明 | backtracking GD | accepted step、normalized / raw mapping | tiny stepで停滞 |
| modest dimension、PD Hessian | Newton | decrement、conditioning | singular / indefinite Hessian |
| smooth、Hessian形成が高価 | BFGS | gradient、line search | curvature / precision loss |
| simple convex constraint | projected gradient | normalized / raw mapping、feasibility | projectionの誤実装 |
| smooth + proximable nonsmooth | proximal gradient | normalized / raw composite mapping、gap | prox parameterのscale違い |

solverやalgorithmの名前だけでは選択理由にならない。derivative cost、matrix structure、constraint geometry、required accuracy、reference boundを一緒に記録する。
"""),
    md(r"""
## 8. Core / Advancedと75点gate

**Core**では本章の5 method family、step / scaling failure、reference optimum、traceを再現する。

**Advanced**はcoordinate descent、ADMM、SGD、momentum、accelerated proximal gradientである。Advanced methodを追加するときも、Coreと同じobjective、mapping、feasibility、budgetで比較する。

| Category | Points | 必須証拠 |
|---|---:|---|
| Mathematical understanding | 25 | step範囲、mapping、Newton systemの導出 |
| Implementation and testing | 30 | normalized / raw trace、projection、prox、SciPy照合 |
| Experimental design | 30 | ill-conditioning、failure、scaled comparison |
| Explanation and memo | 15 | method選択と限界 |

総合75点以上に加え、発散case、制約feasibility、proximal referenceの三つを必須gateにする。成功runだけを提出しても修了にならない。
"""),
    md(r"""
## 9. 失敗モード

- objective decreaseだけで最適性を結論する
- $x_{k+1}-x_k$だけで停止し、tiny stepによる停滞を見逃す
- $L$を確認せず固定stepを選ぶ
- line searchがconditioningを解消すると考える
- Hessian inverseを明示的に作る
- indefinite HessianでもNewton directionをdescentと仮定する
- boundary solutionへraw gradient norm zeroを要求する
- projection後のfeasibilityを再計算しない
- finite difference noiseをBFGSのalgorithm failureと混同する
- L1項をsmoothとして微分する
"""),
    md(r"""
## 10. 段階別演習

### 基礎

1. $Q=\operatorname{diag}(1,100)$に対するGDの安定step範囲を求めよ。
2. nonnegative orthantへのprojectionがcomponent-wise clippingになることを示せ。
3. L1 normのproximal operatorを一変数から導出せよ。

### 標準

4. condition numberを$10^1$から$10^6$まで変え、iteration数とgapをplotせよ。
5. backtrackingの初期stepと縮小率を変え、accepted step historyを比較せよ。
6. box constraintでprojected solutionのfeasibilityを全iteration検査せよ。
7. L1 penaltyをgridで変え、zero coefficient数とobjectiveを分離して報告せよ。

### 研究

8. Hessianがindefiniteな非凸例を作り、damped Newtonまたはtrust-regionが必要な理由を示せ。
9. **Advanced:** accelerated proximal gradientを同じoracle budgetとmappingでCoreと比較せよ。
"""),
    md(r"""
## 11. Exit Criteria

- [ ] smoothnessとconditioningからGD stepを選べる
- [ ] backtrackingとscalingの役割を区別できる
- [ ] Newton systemをinverseなしで解き、Hessian診断を説明できる
- [ ] BFGSをanalytic gradient付きreferenceと比較できる
- [ ] projected gradient mappingとfeasibilityを検査できる
- [ ] proximal gradientを解析的soft-threshold solutionと照合できる
- [ ] objective gap、mapping、feasibilityをparameter changeより優先できる
"""),
    md(r"""
## 12. 出典

- [Boyd and Vandenberghe, *Convex Optimization*, Chapter 9](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf) — gradient、backtracking、Newton methodの著者公開版
- [Stanford EE364a: Unconstrained Minimization](https://web.stanford.edu/class/ee364a/lectures/unconstrained.pdf) — conditioning、Newton decrement、line searchの公式講義資料
- [Parikh and Boyd, *Proximal Algorithms*](https://web.stanford.edu/~boyd/papers/prox_algs.html) — projection、soft-threshold、proximal gradientの原論文・著者資料
- [SciPy `minimize(method='BFGS')`](https://docs.scipy.org/doc/scipy-1.13.0/reference/optimize.minimize-bfgs.html) — BFGS、analytic `jac`、stopping optionsの1.13公式API

次章ではalgorithmをNotebook cellから数値契約を持つcomponentへ切り出し、gradient audit、test、benchmark、provenanceを分離する。
"""),
]
