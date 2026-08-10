"""Builder for notebook 18: B4 orientation and optimization-audit contract."""

from nbkit import code, md

cells = [
    md(r"""
# 18. B4の地図 — 最適化を研究成果へ変える

> solverが値を返したことではなく、問題、単位、最適性、再現性を監査できることを成果物にする。

## 学習目標

- Week 13–16の依存関係とB4 Projectへ集約する証拠を説明できる
- mathematical problem、formulation、algorithm、solver resultを区別できる
- convexity、feasibility、optimality、numerical accuracyを別々に診断できる
- CoreとAdvancedの境界を守り、LP・QP・SOCPを優先して学べる
- B4の4成果物、75点、必須Exit Criteriaを満たす実行計画を作れる

## 前提知識

- B1のleast squares、conditioning、curve fitting、solver disagreement
- B2のMonte Carlo errorとseed contract
- B3のestimand、diagnostic、claim boundary
- 多変数微分、線形代数、NumPy・SciPy・Plotlyの基本操作

凸最適化の基礎をplacementで圧縮しても、成果物、KKT監査、再現性要件は免除しない。
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
NOTEBOOK_ID = 18
TASK_IDS = {
    "feasible_geometry": 1,
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
## 1. 4週間の問い

| 週 | 中心となる問い | Coreの証拠 | Advancedの境界 |
|---|---|---|---|
| Week 13 | 問題を凸なformulationとして記述できるか | domain、units、LP/QP/SOCP、feasibility | SDP、一般conic duality |
| Week 14 | solverとは独立に最適性を監査できるか | 4種類のKKT residual、gap、感度 | Fenchel duality、nonsmooth KKT |
| Week 15 | 構造とconditioningからalgorithmを選べるか | GD、Newton、projected/proximal gradient | ADMM、SGD、accelerated method |
| Week 16 | Notebookの探索を検証可能なcomponentへ移せるか | numerical contract、test、benchmark、provenance | differentiable optimization、継続benchmark |
| Project | B1 Curve Fitterを制約付きで頑健化できるか | positive discount、smoothness、KKT、LOBO | multi-period portfolio optimizer |

**Core**はLP・QP・SOCP、projected/proximal gradient、small tested APIに絞る。高度なalgorithm名を増やすより、objective、constraint、optimality certificate、計算予算を一つのevidence chainへ接続する。

**Advanced**はCoreのExit Criteriaを通過した後に選ぶ。ADMMやSDPを実行できても、残差の尺度やtermination ruleを説明できなければB4修了とはしない。
"""),
    md(r"""
## 2. 4成果物と75点gate

B4も導出ノート、実装とtest、実験、2〜4ページの技術メモをすべて提出する。総合点が75点以上でも、欠けた成果物または未達のExit Criteriaがあれば未修了である。
"""),
    code("""
rubric = pd.DataFrame(
    {
        "category": [
            "Mathematical understanding",
            "Implementation and testing",
            "Experimental design",
            "Explanation and memo",
        ],
        "points": [25, 30, 30, 15],
    }
)

fig = go.Figure()
for row in rubric.itertuples(index=False):
    fig.add_bar(
        y=["B4 assessment"],
        x=[row.points],
        name=row.category,
        orientation="h",
        text=[row.points],
        textposition="inside",
    )
fig.add_vline(x=75, line_dash="dash", annotation_text="Pass mark")
fig.update_layout(
    title="B4 assessment weights",
    xaxis_title="Total points",
    xaxis_range=[0, 105],
    barmode="stack",
    template="plotly_white",
)
fig.show()

print("rubric total:", int(rubric["points"].sum()))
print("pass mark:", 75)
"""),
    md(r"""
75点線は総合点の参照線であり、feasibilityを検査しないcodeを合格へ変える線ではない。B4では特に、solver statusとは独立した数値証拠を必須gateにする。
"""),
    md(r"""
## 3. optimization problemを先に書く

標準的な制約付き問題を

$$
\begin{aligned}
\text{minimize}_{x\in\mathcal{D}}\quad & f_0(x)\\
\text{subject to}\quad & f_i(x)\le 0,\quad i=1,\ldots,m,\\
& Ax=b
\end{aligned}
$$

と書く。solverへ渡す前に次を固定する。

1. **Decision variable:** shape、domain、経済的意味、単位
2. **Objective:** 値の単位、各termのscale、regularizationの役割
3. **Constraints:** 等式・不等式の向き、各boundの単位、許容誤差
4. **Information set:** fit時点で利用可能な入力と将来情報の除外
5. **Acceptance rule:** statusではなく、どのresidualを何の尺度で判定するか

数学上の問題とcode上のformulationは同じではない。同じproblemをepigraph、slack variable、variable scalingで複数のformulationへ写せる。さらに、同じformulationでもalgorithmとsolver設定によって停止点は変わり得る。
"""),
    md(r"""
## 4. convexity、DCP、solver statusは別の判定

凸最適化問題では、domainが凸、目的関数が凸、各不等式関数が凸、等式がaffineであることを確認する。局所最適解が大域最適解になる保証は、この数学的構造に由来する。

Disciplined Convex Programming（DCP）は式木にcomposition ruleを適用する**十分条件ベースのgrammar**である。

| 判定 | 意味 | 次の行動 |
|---|---|---|
| DCP accepted | grammarがconvexityを証明した | domainとsolver精度をさらに検査する |
| DCP unknown | grammarでは符号・曲率を証明できない | 非凸と断定せず、同値変形または独立証明を探す |
| mathematically nonconvex | domainを含む反例またはHessian等で非凸 | Coreの凸solver保証を主張しない |

例えば $\sqrt{1+x^2}$ は凸だが、`sqrt(1 + square(x))` という構文は単純なDCP composition ruleではunknownになり得る。同じ関数を $\lVert(1,x)\rVert_2$ と書けばnorm atomとしてacceptedになる。DCP acceptedも、data scale、feasibility、solution accuracyを保証しない。
"""),
    md(r"""
## 5. feasible geometryを先に見る

次の小問題では、quadratic objectiveの等高線とlinear constraintsの交わりを描く。

$$
\min_x\ \frac12\lVert x-c\rVert_2^2
\quad\text{s.t.}\quad
x_1+x_2\ge 1,\ x_1\ge0,\ x_2\ge0.
$$

目的関数を評価できる点が存在しても、制約を満たすとは限らない。図の色はobjectiveであり、白抜き領域だけがfeasible setである。
"""),
    code("""
geometry_rng = task_rng("feasible_geometry")
grid = np.linspace(-0.25, 1.75, 121)
x1_grid, x2_grid = np.meshgrid(grid, grid)
center = np.array([0.25, 0.45])
objective_grid = 0.5 * (
    (x1_grid - center[0]) ** 2 + (x2_grid - center[1]) ** 2
)
feasible_mask = (
    (x1_grid + x2_grid >= 1.0)
    & (x1_grid >= 0.0)
    & (x2_grid >= 0.0)
)
masked_objective = np.where(feasible_mask, objective_grid, np.nan)

candidate_points = geometry_rng.uniform(0.0, 1.5, size=(30, 2))
candidate_violation = np.maximum(
    1.0 - candidate_points[:, 0] - candidate_points[:, 1],
    0.0,
)

fig = go.Figure(
    go.Contour(
        x=grid,
        y=grid,
        z=masked_objective,
        contours={"showlabels": True},
        colorbar={"title": "Objective"},
        name="Feasible objective",
    )
)
fig.add_scatter(
    x=candidate_points[:, 0],
    y=candidate_points[:, 1],
    mode="markers",
    marker={"color": candidate_violation, "colorscale": "Reds", "size": 7},
    name="Candidate points",
)
fig.add_scatter(
    x=[0.4],
    y=[0.6],
    mode="markers",
    marker={"symbol": "x", "size": 13, "color": "black"},
    name="Constrained optimum",
)
fig.update_layout(
    title="Objective values are meaningful only after feasibility is checked",
    xaxis_title="x1",
    yaxis_title="x2",
    template="plotly_white",
)
fig.show()

print("largest sampled violation:", float(candidate_violation.max()))
"""),
    md(r"""
unconstrained optimum $c=(0.25,0.45)$ は $x_1+x_2\ge1$ を満たさない。制約付き最適解は境界上の $(0.4,0.6)$ であり、図示点はその位置である。低いobjectiveだけを選ぶとinfeasibleな候補を採用し得る。

各constraint residualは元の単位で残し、判定にはabsolute toleranceだけでなくrepresentative scaleを使う。異なる単位の制約を一つの無次元maximumへまとめる場合、各行を何で正規化したかを記録する。
"""),
    md(r"""
## 6. B4 evidence chain

```text
economic question and information set
    -> variable, units, objective, constraints
        -> convexity argument and formulation
            -> algorithm, scaling, termination
                -> feasibility and KKT audit
                    -> perturbation, benchmark, reproducible artifact
```

| 層 | 必須の問い |
|---|---|
| Specification | 変数・目的・制約は元の問いと同じか |
| Structure | domainを含めてconvexか、DCP判定の範囲はどこか |
| Numerics | scale、conditioning、初期点、iteration budgetは何か |
| Feasibility | 等式・不等式・boundを元データから再計算したか |
| Optimality | stationarity、dual feasibility、complementarity、gapは小さいか |
| Sensitivity | boundやdataの微小変更にshadow priceと整合するか |
| Software | clean processから同じartifactを生成できるか |

`success=True`、`optimal`、`optimal_inaccurate`はevidence chainの入力であり、結論ではない。
"""),
    md(r"""
## 7. B4 Project — Constrained Yield Curve Fitter

B1のbond price mode

$$
P_i=\sum_j C_{ij}D(t_{ij})
$$

を、discount-factor grid $D$ に対する制約付きconvex problemへ拡張する。Coreでは少なくとも次を実装する。

- quote widthがある場合のbid–ask weighting
- $D_i\ge\epsilon_D$ とそのscale-aware violation
- smoothness penaltyまたはbound
- primal / dual feasibility、stationarity、complementarity
- scalingとsolver disagreement
- leave-one-bond-out pricing error

discount factorの単調非増加は、nonnegative instantaneous forward rateを仮定するときの**任意制約**である。負金利では $D(T)>1$ や局所的増加があり得るため、普遍的no-arbitrage条件として強制しない。

Nelson–Siegelのdecayは固定または事前gridとする。decayとlinear coefficientの同時推定は一般に非凸であり、Coreの凸問題へ混ぜない。
"""),
    md(r"""
## 8. 失敗モード

- variable、objective、constraintの単位を書かずにsolverへ渡す
- DCP unknownを数学的nonconvexと断定する
- DCP acceptedをfeasible・accurate・well-scaledの証明として扱う
- `success`または`optimal_inaccurate`だけで候補解を採用する
- objectiveだけを比較し、constraint residualとKKT residualを捨てる
- absolute toleranceを全問題へ固定し、行scaleやfloating-point errorを無視する
- penaltyとhard constraintが答える問いを混同する
- discount factor monotonicityを負金利下でも普遍条件と呼ぶ
- Notebookの隠れたstate、実行順、未記録solver optionに依存する
"""),
    md(r"""
## 9. 段階別演習

### 基礎

1. quadratic objectiveとlinear inequalityを持つ問題について、variable、単位、domainを書け。
2. LP、QP、SOCPのobjectiveとconstraint構造を対照表にせよ。
3. solver status、primal feasibility、optimalityの違いを各1文で説明せよ。

### 標準

4. 図のconstraint boundを0.5、1.0、1.5へ変え、solutionとvalueを比較せよ。
5. $\sqrt{1+x^2}$ をnormで表し、mathematical convexityとDCP grammarを分けて説明せよ。
6. B1 Curve Fitterのinput、decision variable、objective、constraints、acceptance ruleを1ページに固定せよ。

### 研究

7. solver-independentなsolution artifact schemaを設計し、raw status、options、4 KKT residual、data fingerprintを含めよ。
8. **Advanced:** SDPで書ける問題を一つ選び、なぜB4 Coreへ含めないかを計算量とcertificateから説明せよ。
"""),
    md(r"""
## 10. Exit Criteria

- [ ] B4のCoreとAdvanced、4週間の依存関係を説明できる
- [ ] variable、domain、units、objective、constraintsをsolverより先に書ける
- [ ] mathematical convexity、DCP判定、solver statusを区別できる
- [ ] objectiveだけでなくfeasibilityとoptimalityを独立に検査できる
- [ ] 4成果物、75点、必須Exit Criteriaの三つの修了条件を説明できる
- [ ] 負金利下のdiscount-factor monotonicityを任意仮定として限定できる
"""),
    md(r"""
## 11. 出典

- [Boyd and Vandenberghe, *Convex Optimization*](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf) — convex set・function、problem form、duality、numerical implementationを通した著者公開版
- [Stanford EE364a, Convex Optimization I](https://web.stanford.edu/class/ee364a/) — lecture slides、notes、homeworkを含む公式course page
- [CVXPY: Disciplined Convex Programming](https://www.cvxpy.org/tutorial/dcp/) — accepted / unknownと同値表現の境界を示す公式tutorial
- [SciPy: Constrained minimization](https://docs.scipy.org/doc/scipy/reference/optimize.html#constrained-minimization-of-multivariate-scalar-functions-minimize) — 本教材で比較対象にする制約付きsolverの公式documentation

次章では、LP・QP・SOCPのformulationを作り、scaleを変えた同値問題とinfeasible problemをobjective・residualの両方から監査する。
"""),
]
