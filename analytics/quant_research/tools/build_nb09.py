"""Builder for notebook 09: Markov chains, martingales, and stopping times."""

from nbkit import code, md

cells = [
    md(r"""
# 09. Week 7 — Markov連鎖・マルチンゲール・停止時刻

> 「未来の条件付き平均」を扱うには、確率変数だけでなく、その時点までに何を知っているかを固定する。

## 学習目標

- 有限状態Markov連鎖をrow-stochastic遷移行列として実装する
- 定常分布、既約性、非周期性と長期分布の関係を区別する
- filtration、adapted process、martingale、stopping timeを定義する
- 有界停止時刻でoptional stoppingを数値確認する
- 条件を破る反例から、停止定理を機械的に使えない理由を説明する

## 前提知識

- 条件付き期待値と全期待値の法則
- 行列積、固有値、確率分布
- 独立同分布なBernoulli変数と大数の法則
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810


def task_rng(task_id):
    return np.random.default_rng(
        np.random.SeedSequence([RANDOM_SEED, int(task_id)])
    )
"""),
    md(r"""
## 1. 有限状態Markov連鎖のデータ契約

状態を $X_t\in\{1,\ldots,K\}$ とし、遷移行列を

$$
P_{ij}=\mathbb{P}(X_{t+1}=j\mid X_t=i)
$$

と定義する。本章では分布をrow vectorとして右から掛けるため、$P$ の各行が非負で和が1の **row-stochastic** 規約を使う。

Markov性は

$$
\mathbb{P}(X_{t+1}=j\mid X_0,\ldots,X_t)
=\mathbb{P}(X_{t+1}=j\mid X_t)
$$

というモデル仮定である。観測データから自動的に保証される性質ではない。
"""),
    code("""
state_names = np.array(["calm", "volatile", "stressed"])
transition = np.array(
    [
        [0.90, 0.09, 0.01],
        [0.18, 0.72, 0.10],
        [0.08, 0.27, 0.65],
    ],
    dtype=float,
)

if np.any(transition < 0.0) or not np.allclose(transition.sum(axis=1), 1.0):
    raise ValueError("transition must be row-stochastic")

initial_distribution = np.array([0.0, 0.0, 1.0])
distributions = np.vstack(
    [initial_distribution @ np.linalg.matrix_power(transition, step) for step in range(41)]
)

fig = go.Figure()
for state_index, state_name in enumerate(state_names):
    fig.add_scatter(
        x=np.arange(len(distributions)),
        y=distributions[:, state_index],
        mode="lines",
        name=state_name,
    )
fig.update_layout(
    title="Distribution dynamics from a stressed initial state",
    xaxis_title="Step",
    yaxis_title="Probability",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 2. 定常分布と収束条件

定常分布 $\pi$ は

$$
\pi=\pi P,
\qquad
\sum_{i=1}^K\pi_i=1
$$

を満たす。固有値1に対応する左固有ベクトルを正規化して計算できるが、存在する定常分布へ任意の初期分布から収束するとは限らない。

- **既約:** 任意の状態から任意の状態へ有限stepで正の確率で到達できる
- **周期 $d(i)$:** $i$ へ戻れるstep数集合の最大公約数
- **非周期:** 各状態の周期が1

有限状態で既約なら定常分布は一意である。さらに非周期なら $\mu P^t\to\pi$ が成り立つ。定常分布の方程式と、分布の収束は別の主張である。
"""),
    code("""
eigenvalues, left_eigenvectors = np.linalg.eig(transition.T)
stationary_index = np.argmin(np.abs(eigenvalues - 1.0))
stationary = np.real(left_eigenvectors[:, stationary_index])
stationary = stationary / stationary.sum()

stationarity_error = np.max(np.abs(stationary @ transition - stationary))
print(pd.Series(stationary, index=state_names, name="stationary"))
print("stationarity error:", stationarity_error)

positive_reachability = (transition > 0.0) | np.eye(len(state_names), dtype=bool)
for intermediate_state in range(len(state_names)):
    positive_reachability |= (
        positive_reachability[:, intermediate_state, None]
        & positive_reachability[None, intermediate_state, :]
    )
print("all states mutually reachable:", bool(np.all(positive_reachability)))
print("positive self-transition in every state:", bool(np.all(np.diag(transition) > 0.0)))
"""),
    md(r"""
正のself-transitionがあれば、その状態の周期は1である。既約連鎖では全状態が同じ周期を持つため、この例は非周期である。一般の疎な大規模行列では、行列べきの値を眺めるだけでなく、強連結成分とreturn-timeの最大公約数を検査する。

次の2状態連鎖は既約だが周期2である。

$$
P_{\mathrm{cycle}}=
\begin{pmatrix}0&1\\1&0\end{pmatrix},
\qquad
\pi=(1/2,1/2).
$$

$\pi$ は存在する一方、初期分布 $(1,0)$ は2点を往復して収束しない。
"""),
    code("""
periodic_transition = np.array([[0.0, 1.0], [1.0, 0.0]])
periodic_initial = np.array([1.0, 0.0])
periodic_probabilities = np.array(
    [
        (periodic_initial @ np.linalg.matrix_power(periodic_transition, step))[0]
        for step in range(13)
    ]
)

fig = go.Figure()
fig.add_scatter(
    x=np.arange(len(periodic_probabilities)),
    y=periodic_probabilities,
    mode="lines+markers",
    name="P(X_t = 0)",
)
fig.add_hline(y=0.5, line_dash="dash", annotation_text="stationary mass")
fig.update_layout(
    title="A stationary distribution does not imply convergence",
    xaxis_title="Step",
    yaxis_title="Probability",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 3. 1本のpathとensemble分布を混同しない

ensemble分布 $\mu P^t$ は多数の独立な実験を時刻 $t$ で観測した分布である。occupation frequencyは1本の長いpathが各状態に滞在した割合である。有限既約連鎖ではergodic theoremにより後者も定常分布へ近づくが、有限標本ではserial dependenceが残る。
"""),
    code("""
def simulate_chain(matrix, initial_state, n_steps, rng):
    path = np.empty(n_steps + 1, dtype=int)
    path[0] = initial_state
    for step in range(n_steps):
        path[step + 1] = rng.choice(matrix.shape[0], p=matrix[path[step]])
    return path


rng = task_rng(0)
chain_path = simulate_chain(transition, initial_state=2, n_steps=20_000, rng=rng)
checkpoints = np.unique(np.geomspace(20, len(chain_path), 90).astype(int))
occupation = np.vstack(
    [np.bincount(chain_path[:checkpoint], minlength=3) / checkpoint for checkpoint in checkpoints]
)

fig = go.Figure()
for state_index, state_name in enumerate(state_names):
    fig.add_scatter(
        x=checkpoints,
        y=occupation[:, state_index],
        mode="lines",
        name=f"occupation: {state_name}",
    )
    fig.add_hline(y=stationary[state_index], line_dash="dot", line_color="gray")
fig.update_layout(
    title="Occupation frequencies along one dependent path",
    xaxis_title="Observed steps",
    xaxis_type="log",
    yaxis_title="Frequency",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 4. Filtrationとmartingale

filtration $\{\mathcal{F}_t\}$ は情報の増加列

$$
\mathcal{F}_0\subseteq\mathcal{F}_1\subseteq\cdots
$$

である。process $M_t$ が $\mathcal{F}_t$ にadapted、integrableであり、

$$
\mathbb{E}[M_{t+1}\mid\mathcal{F}_t]=M_t
$$

を満たすときmartingaleという。独立なfair sign $\xi_t\in\{-1,+1\}$ の部分和

$$
S_t=\sum_{k=1}^t\xi_k
$$

は自然なfiltration $\mathcal{F}_t=\sigma(\xi_1,\ldots,\xi_t)$ に関するmartingaleである。「平均が一定」だけでは不十分で、条件付き期待値と情報集合が定義の中心になる。

stopping time $\tau$ は、時刻 $t$ までの情報だけで $\{\tau\le t\}$ を判定できる時刻である。未来のpath全体を見て選んだ最良売却日はstopping timeではない。
"""),
    md(r"""
## 5. 有界停止時刻 — 成立する例

上下barrierの初回到達を最大時刻 $T$ で打ち切り、

$$
\tau=\min\{t:S_t\in\{-a,b\}\}\wedge T
$$

とする。$\tau\le T$ なので有界であり、simple random walkのoptional stoppingに必要な十分条件を満たす。このとき

$$
\mathbb{E}[S_\tau]=\mathbb{E}[S_0]=0.
$$

Monte Carloは定理の証明ではない。実装、符号、停止規則が理論と整合するかを調べるtestとして使う。
"""),
    code("""
def bounded_stopped_walk(n_paths, lower, upper, horizon, rng):
    positions = np.zeros(n_paths, dtype=int)
    active = np.ones(n_paths, dtype=bool)
    stopping_times = np.full(n_paths, horizon, dtype=int)
    for step in range(1, horizon + 1):
        active_indices = np.flatnonzero(active)
        if active_indices.size == 0:
            break
        increments = rng.choice(np.array([-1, 1]), size=active_indices.size)
        positions[active_indices] += increments
        newly_stopped = active_indices[
            (positions[active_indices] <= lower) | (positions[active_indices] >= upper)
        ]
        stopping_times[newly_stopped] = step
        active[newly_stopped] = False
    return positions, stopping_times


bounded_rng = task_rng(1)
stopped_values, stopping_times = bounded_stopped_walk(
    n_paths=80_000,
    lower=-7,
    upper=7,
    horizon=120,
    rng=bounded_rng,
)
mean_stopped = stopped_values.mean()
standard_error = stopped_values.std(ddof=1) / np.sqrt(len(stopped_values))

print("mean stopped value:", mean_stopped)
print("Monte Carlo standard error:", standard_error)
print("within two standard errors of zero:", abs(mean_stopped) <= 2.0 * standard_error)
print("fraction stopped by a barrier:", np.mean(stopping_times < 120))
"""),
    md(r"""
## 6. 条件を破る反例 — 打ち切り近似との違い

fair random walkについて

$$
\tau=\inf\{t\ge0:S_t=1\}
$$

を考える。$\tau<\infty$ は確率1である一方、$\mathbb{E}[\tau]=\infty$ で、停止processに必要な一様可積分性も満たさない。$S_\tau=1$ だから、条件を確認せず $\mathbb{E}[S_\tau]=0$ とするのは誤りである。

有限計算で観測できるのは $\tau_T=\tau\wedge T$ である。各 $T$ について $\tau_T$ は有界なので $\mathbb{E}[S_{\tau_T}]=0$ である。$T$ が増えるとhit済みpathの値は1へ集まるが、ごく少数の未到達pathの大きな負値が平均を相殺する。確率収束だけで期待値と極限を交換できない例になっている。
"""),
    code("""
counter_rng = task_rng(2)
n_paths = 50_000
max_horizon = 2_000
horizons = np.unique(np.geomspace(4, max_horizon, 55).astype(int))
positions = np.zeros(n_paths, dtype=int)
hit = np.zeros(n_paths, dtype=bool)
hit_probabilities = []
stopped_means = []
horizon_cursor = 0

for step in range(1, max_horizon + 1):
    active_indices = np.flatnonzero(~hit)
    positions[active_indices] += counter_rng.choice(
        np.array([-1, 1]),
        size=active_indices.size,
    )
    hit_now = (~hit) & (positions == 1)
    hit[hit_now] = True
    positions[hit_now] = 1
    if horizon_cursor < len(horizons) and step == horizons[horizon_cursor]:
        hit_probabilities.append(hit.mean())
        stopped_means.append(positions.mean())
        horizon_cursor += 1

fig = go.Figure()
fig.add_scatter(
    x=horizons,
    y=hit_probabilities,
    mode="lines",
    name="P(tau <= T)",
)
fig.add_scatter(
    x=horizons,
    y=stopped_means,
    mode="lines",
    name="mean S_(tau capped at T)",
)
fig.add_hline(y=0.0, line_dash="dot", line_color="black")
fig.update_layout(
    title="Unbounded stopping: probability mass and expectation behave differently",
    xaxis_title="Cap T",
    xaxis_type="log",
    yaxis_title="Estimate",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
simulation horizonを伸ばしてhit率が1へ近づいても、unbounded $\tau$ の期待値を有限標本が検証したことにはならない。rare pathの寄与、tail bound、一様可積分性を別に調べる必要がある。
"""),
    md(r"""
## 7. 失敗モード

- row vector規約とcolumn vector規約を混ぜ、$\pi P=\pi$ と $P\pi=\pi$ を取り違える
- 定常分布が存在するだけで、任意の初期分布から収束すると主張する
- 既約性、非周期性を数値固有値だけから断定する
- ensemble分布と、1本のserially dependent pathのoccupation frequencyを同一視する
- $\mathbb{E}[M_t]$ が一定という周辺的性質だけでmartingaleと呼ぶ
- future informationを使う時刻をstopping timeとして扱う
- optional stoppingの結論だけを記憶し、有界性・可積分性・一様可積分性などの十分条件を確認しない
- $\tau\wedge T$ のsimulation結果を、unbounded $\tau$ の期待値へ無条件に外挿する
"""),
    md(r"""
## 8. 段階別演習

### 基礎

1. 3状態遷移行列の各行を検査し、$\mu P^t$ を手計算とcodeで照合せよ。
2. $P_{\mathrm{cycle}}$ の定常分布を求め、分布が収束しないことを説明せよ。
3. fair random walkが自然なfiltrationに関するmartingaleであることを示せ。

### 標準

4. 遷移回数から遷移行列を推定し、各行のeffective sample sizeを報告せよ。
5. burn-inを変えたoccupation frequencyとbatch-means標準誤差を比較せよ。
6. 非対称barrier $(-a,b)$ でbounded stoppingをsimulationし、hitting probabilityを導出値と比較せよ。

### 研究

7. 同じ定常分布を持つ複数の遷移行列を作り、spectral gapとmixingの差を比較せよ。
8. stopped process $M_{t\wedge\tau}$ の一様可積分性が期待値極限の交換にどう関係するか、反例とともに説明せよ。
"""),
    md(r"""
## 9. Exit Criteria

- [ ] row-stochastic規約を明示して有限Markov連鎖を実装できる
- [ ] 定常性、一意性、分布収束を別々の命題として説明できる
- [ ] 既約だが周期的な反例を作れる
- [ ] filtration、adapted、martingale、stopping timeを数式で定義できる
- [ ] 有界停止時刻でoptional stoppingの前提を確認できる
- [ ] unbounded stoppingの反例で、確率極限と期待値極限を交換できない理由を説明できる
- [ ] Monte Carlo結果を定理の証明と呼ばず、finite-horizon診断として解釈できる
"""),
    md(r"""
## 10. 出典

- [MIT OpenCourseWare 18.445, Lecture 16: Stopping Times and Martingales](https://ocw.mit.edu/courses/18-445-introduction-to-stochastic-processes-spring-2015/resources/mit18_445s15_lecture16/) — stopping time、martingale、optional stopping
- [MIT OpenCourseWare 15.070J: Advanced Stochastic Processes, Lecture Notes](https://ocw.mit.edu/courses/15-070j-advanced-stochastic-processes-fall-2013/pages/lecture-notes/) — Markov chains、filtration、martingales、stopping
- [MIT OpenCourseWare 18.600, Lecture 34: Martingales and the Optional Stopping Theorem](https://ocw.mit.edu/courses/18-600-probability-and-random-variables-fall-2019/3ce8cee748c630414deebc968bd375e1_MIT18_600F19_lec34.pdf) — optional stoppingの十分条件と例

次章では、離散時間のrandom walkを連続時間Brownian motionへ移し、Itô補正、Euler–Maruyama、Monte Carlo誤差を分解する。
"""),
]
