"""Build the ODE book chapter notebooks 01..07 (00 is built separately).

Usage: python build_ode_notebook.py [all|01|02|...|07]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nbkit import code, md, setup_cell, write  # noqa: E402

NB = Path(__file__).resolve().parent.parent / "ode-book" / "notebooks"
IMPORT = code("from ode_book import systems, solvers, plotting, datasets")


def _save(name, cells):
    write(cells, str(NB / name))
    print("wrote", NB / name)


# --------------------------------------------------------------------------- #
def overview():
    cells = [
        md(r"""
# 01. ODE の全体像 — 状態が時間とともにどう変わるか

> 本書の読み方: **微分積分(00 章) → ODE → PDE → 応用**。
> この章は ODE 全体の地図です。まず 00 章で微分=変化率・積分=蓄積の直感を作ってから戻ってくると、
> 以下がすべて「変化率をルールとして与える」一つの考えに見えてきます。

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture 〜 4. Visualization |
| Applied | 5. 解析解と数値解 〜 6. 読み方 |
| Advanced | 7. Advanced Notes |

## 1. Big Picture

**常微分方程式 (ODE)** は、たった一つのことを記述します。

> **状態が、時間とともにどう変わるか。**

未知関数 $y(t)$ そのものではなく、その **変化率** $dy/dt$ を、現在の状態と時刻の関数として与えます。

$$
\frac{dy}{dt} = f(t, y)
$$

「いまどこにいるか ($y$)」が決まれば「次にどちらへどれだけ動くか ($dy/dt$)」が決まる——
この **局所的なルール** を時間方向に積み上げると、未来の軌道が決まります。これが ODE の世界です。
"""),
        md(r"""
## 2. Problem / 3. Intuition — なぜ微分方程式なのか

現実の多くの法則は「量そのもの」ではなく「量の変化のしかた」で表されます。

- 放射性物質: 残量が多いほど速く減る → $dy/dt = -k y$
- 人口: 余裕があるほど増えるが、上限に近づくと頭打ち → $dy/dt = r y(1 - y/K)$
- 運動: 力 = 質量 × 加速度(加速度は位置の二階微分) → $m\,\ddot{x} = F$

いずれも **変化率を状態で表す** 形をしています。ODE はこの形を解いて(あるいは数値積分して)、
時間発展を再構成する道具です。
"""),
        setup_cell("ode_book"),
        IMPORT,
        md(r"""
## 4. Visualization — 同じ法則から、無数の未来

$dy/dt = f(t,y)$ は各点で「傾き」を定めます。これを矢印で敷き詰めたものが **方向場 (slope field)** です。
解は、初期条件という出発点を一つ選び、方向場に沿って流れていく曲線です。
初期条件を変えると別の未来になりますが、**ルール(方向場)は共通** であることに注目してください。
"""),
        code("""
# One rule, many futures: the slope field of dy/dt = y - t with several solutions.
f = lambda t, y: y - t
ax = plotting.direction_field(f, (0, 4), (-1, 4), n=20)
import numpy as np
t = np.linspace(0, 4, 200)
for y0 in (-0.5, 0.0, 0.5, 1.0, 1.5):
    Y = solvers.rk4(f, [y0], t)
    ax.plot(t, Y[:, 0], lw=1.8)
ax.set_ylim(-1, 4)
ax.set_title("dy/dt = y - t: one slope field, many solution curves")
plt.show()
"""),
        md(r"""
## 5. 解析解と数値解 (Applied)

ODE の解き方は二通りあります。

- **解析解**: 紙と鉛筆(または SymPy)で閉じた式を求める。可能なら最も理解が深い。
- **数値解**: 方向場に沿って小さく刻みながら前進する(Euler 法など)。ほとんどの実問題はこちら。

簡単な指数減衰 $dy/dt = -y$ で両者を比べます。解析解 $y = y_0 e^{-t}$ に、Euler 法と RK4 法が
どれだけ一致するかを見ます(詳しくは 06 章)。
"""),
        code("""
import numpy as np

# Analytic vs numerical on dy/dt = -y, y(0)=1  (exact: e^{-t}).
f = systems.exponential(-1.0)
t = np.linspace(0, 5, 21)
exact = np.exp(-t)
Y_euler = solvers.euler(f, [1.0], t)[:, 0]
Y_rk4 = solvers.rk4(f, [1.0], t)[:, 0]

fig, ax = plt.subplots(figsize=(6.5, 4))
ax.plot(t, exact, "k-", lw=2, label="analytic e^{-t}")
ax.plot(t, Y_euler, "o-", ms=4, color="#1f77b4", label="Euler")
ax.plot(t, Y_rk4, "s-", ms=4, color="#2ca02c", label="RK4")
ax.legend()
ax.grid(alpha=0.25)
ax.set_xlabel("t")
ax.set_title("analytic vs numerical (coarse dt to expose Euler error)")
plt.show()
print("max |Euler - exact| =", np.max(np.abs(Y_euler - exact)))
print("max |RK4   - exact| =", np.max(np.abs(Y_rk4 - exact)))
"""),
        md(r"""
## 6. この教材の読み方

各章は次の流れを踏みます: **現象 → 直感 → 可視化 → 数式 → Python 実験 → 応用 → 発展**。
また各章は 3 層に分かれます。

- **Basic**: 初学者が最低限つかむべき直感と定義
- **Applied**: Python による実装・実験・応用
- **Advanced**: 証明・発展理論・数値上の注意(`Advanced Notes` に分離)

### 章構成 (ODE Book)

| Notebook | 内容 |
|---|---|
| `00_calculus_foundations` | 前提編: 微分=変化率 / 積分=蓄積 / 偏微分・勾配・Hessian |
| `01_overview` | ODE の全体像(この章) |
| `02_first_order_odes` | 一階 ODE・変数分離・線形一階・ロジスティック・方向場 |
| `03_linear_odes_and_systems` | 高階線形・連立 ODE・行列形式・固有値・振動 |
| `04_phase_plane_and_stability` | 相図・固定点・線形化・安定性分類・ヌルクライン |
| `05_nonlinear_dynamics` | Lotka-Volterra・SIR・分岐・カオスの入口(Lorenz) |
| `06_numerical_methods` | Euler/Heun/RK4・誤差と次数・安定性・stiff・solve_ivp |
| `07_applications_physics_biology_finance` | 物理・生物・金融・機械学習・制御 |

### Python 環境の準備

```bash
# この workspace 内(推奨)
cd ~/projects && make install

# 単体で使う場合
cd analytics/differential_equation/ode-book
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
```

各 Notebook の最初のセルは、`ode_book` が未インストールでも `src/` を探して読み込む作りなので、
リポジトリを clone してそのまま実行できます。
"""),
        md(r"""
## 7. Advanced Notes

- **次元(状態の数)**: スカラー ODE は 1 次元の状態。$n$ 個連立させると $n$ 次元の状態ベクトル
  $\mathbf{x}\in\mathbb{R}^n$ になり、$d\mathbf{x}/dt = \mathbf{f}(t,\mathbf{x})$ と書けます(03 章)。
- **自励系 (autonomous)**: $f$ が $t$ に陽に依らない $dy/dt=f(y)$。方向場が時間で変わらないので相図が描けます(04 章)。
- **存在と一意性**: $f$ が $y$ について Lipschitz 連続なら、初期値問題の解は局所的に一意に存在します
  (Picard–Lindelöf)。これが「初期条件を決めれば未来が一つに決まる」ことの数学的保証です。
- **高階 = 連立一階**: $y^{(n)} = g(t, y, y', \dots)$ は補助変数を導入して必ず一階の連立系に直せます。
  だから本書のソルバは一階系だけ扱えば十分です。
"""),
    ]
    _save("01_overview.ipynb", cells)


# --------------------------------------------------------------------------- #
def first_order():
    cells = [
        md(r"""
# 02. 一階 ODE — 方向場・変数分離・線形・ロジスティック

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture 〜 5. Definition |
| Applied | 6. Computation 〜 9. Application |
| Advanced | 11. Advanced Notes |

## 1. Big Picture

一階 ODE は最も基本的な形

$$
\frac{dy}{dt} = f(t, y)
$$

です。右辺 $f$ が各点に傾きを与え、解はその **方向場に沿う曲線**。
本章では、解析的に解ける 2 つの型(**変数分離形**・**線形一階**)と、応用の主役 **ロジスティック方程式** を扱います。
"""),
        md(r"""
## 2. Problem / 3. Intuition

- 銀行口座: 利率が一定なら、残高が多いほど増える額も大きい → $dy/dt = r y$(指数成長)
- 池の藻: 増えるが、池の容量 $K$ に近づくと頭打ち → $dy/dt = r y(1 - y/K)$(ロジスティック)

「変化率が現在の状態に比例する」という素朴な仮定が、指数・ロジスティックという全く違う振る舞いを生みます。
"""),
        setup_cell("ode_book"),
        IMPORT,
        md(r"""
## 4. Visualization — 方向場と初期条件

同じ方程式でも初期条件で未来が変わります。ロジスティック方程式の方向場に、
複数の初期値からの解を重ねます。**どこから始めても $y=K$ に収束** するのが見どころです。
"""),
        code("""
import numpy as np

# Logistic slope field + a fan of initial conditions, all converging to K.
sc = datasets.logistic_scenario()
f = systems.logistic(**sc.params)
ax = plotting.direction_field(f, (0, 12), (0, 1.8), n=20)
t = sc.t
for y0 in sc.y0:
    Y = solvers.rk4(f, [y0], t)
    ax.plot(t, Y[:, 0], lw=1.8)
ax.axhline(sc.params["K"], color="#2ca02c", ls="--", lw=1, label="K")
ax.set_ylim(0, 1.8)
ax.legend()
ax.set_title("logistic dy/dt = r y(1 - y/K): every start flows to K")
plt.show()
"""),
        md(r"""
## 5. Definition / 6. Computation — 解析的に解ける 2 つの型 (Applied)

### 変数分離形

$\dfrac{dy}{dt} = g(t)\,h(y)$ の形なら、$\dfrac{dy}{h(y)} = g(t)\,dt$ と分離して両辺を積分できます。
最も単純な $dy/dt = r y$ は $y = y_0 e^{rt}$。SymPy で確認します。
"""),
        code("""
import sympy as sp

# Separable: dy/dt = r y  ->  y = y0 e^{r t}.
t, r, y0 = sp.symbols("t r y0", positive=True)
y = sp.Function("y")
sol = sp.dsolve(sp.Eq(y(t).diff(t), r * y(t)), y(t), ics={y(0): y0})
print("dy/dt = r y   =>  ", sol)
"""),
        md(r"""
### 線形一階

$\dfrac{dy}{dt} + p(t)\,y = q(t)$ は **積分因子** $\mu(t) = e^{\int p\,dt}$ を掛けると左辺が
$(\mu y)'$ にまとまり、積分で解けます。例として $dy/dt + y = t$ を解きます。
"""),
        code("""
import sympy as sp

# Linear first-order: dy/dt + y = t  (integrating factor mu = e^t).
t = sp.symbols("t")
y = sp.Function("y")
sol = sp.dsolve(sp.Eq(y(t).diff(t) + y(t), t), y(t))
print("dy/dt + y = t  =>  ", sol)
"""),
        md(r"""
### ロジスティック方程式

$dy/dt = r y(1 - y/K)$ も変数分離で解け、解は **シグモイド曲線**

$$
y(t) = \frac{K}{1 + \left(\frac{K - y_0}{y_0}\right) e^{-rt}}
$$

になります。解析解と数値解 (RK4) を重ねて一致を確認します。
"""),
        code("""
import numpy as np

# Logistic: analytic sigmoid vs RK4.
r, K, y_init = 0.9, 1.0, 0.1
t = np.linspace(0, 12, 200)
analytic = K / (1 + ((K - y_init) / y_init) * np.exp(-r * t))
Y = solvers.rk4(systems.logistic(r, K), [y_init], t)[:, 0]

fig, ax = plt.subplots(figsize=(6.5, 4))
ax.plot(t, analytic, "k-", lw=2, label="analytic sigmoid")
ax.plot(t[::8], Y[::8], "o", color="#d62728", ms=4, label="RK4")
ax.axhline(K, color="#2ca02c", ls="--", lw=1)
ax.legend()
ax.grid(alpha=0.25)
ax.set_xlabel("t")
ax.set_title("logistic: analytic vs numerical")
plt.show()
print("max |analytic - RK4| =", np.max(np.abs(analytic - Y)))
"""),
        md(r"""
### インタラクティブ: 成長率 $r$ を動かす(静的 HTML でも動く)

`ipywidgets` は JupyterLab 専用ですが、**Plotly のスライダーはエクスポートした HTML でも動きます**。
$r$ を大きくするほど収束が速くなり、平衡 $K$ は変わらないことを確かめてください。
"""),
        code("""
import plotly.io as pio
from ode_book import interactive

pio.renderers.default = "plotly_mimetype+notebook_connected"
fig = interactive.plotly_logistic_r()
fig.show()
"""),
        md(r"""
## 7. Invariant — 平衡点

$dy/dt = 0$ となる $y$ が **平衡点(定常解)**。ロジスティックでは $y=0$(不安定)と $y=K$(安定)。
平衡点とその安定性が、長時間後の振る舞いを決めます(04 章で深掘り)。

## 8. Failure Mode — 有限時間爆発

すべての解が永遠に存在するとは限りません。$dy/dt = y^2,\ y(0)=1$ の解は $y = 1/(1-t)$ で、
$t \to 1$ で **発散** します。数値解も $t=1$ 手前で破綻します。
"""),
        code("""
import numpy as np

# Finite-time blow-up: dy/dt = y^2, y(0)=1 -> y = 1/(1-t), diverges at t=1.
f = lambda t, y: y**2
t = np.linspace(0, 0.98, 200)
Y = solvers.rk4(f, [1.0], t)[:, 0]
fig, ax = plt.subplots(figsize=(6.5, 4))
ax.plot(t, Y, color="#d62728", lw=2, label="RK4")
ax.plot(t, 1 / (1 - t), "k--", lw=1, label="exact 1/(1-t)")
ax.axvline(1.0, color="gray", ls=":")
ax.set_ylim(0, 50)
ax.legend()
ax.grid(alpha=0.25)
ax.set_title("blow-up at t = 1: solutions need not exist for all time")
plt.show()
"""),
        md(r"""
## 9. Application — 放射性崩壊と冷却

- **放射性崩壊** $dy/dt = -k y$: 半減期 $t_{1/2} = \ln 2 / k$。
- **Newton の冷却法則** $dT/dt = -k(T - T_\text{env})$: 物体は環境温度へ指数的に近づく(線形一階の典型)。

## Exercises

1. $dy/dt = -k y$ を変数分離で解き、半減期が初期量によらないことを示せ。
2. $dy/dt + 2y = e^{-t}$ を積分因子で解き、SymPy の結果と一致させよ。
3. ロジスティックで $y_0 > K$ から始めたとき、解が上から $K$ に近づくことを数値で示せ。
4. $dy/dt = \sqrt{|y|},\ y(0)=0$ は解が一意でない(Lipschitz 条件の破れ)。複数解を構成せよ。

## Advanced Notes

- **積分因子の導出**: $(\mu y)' = \mu y' + \mu' y$ が $\mu(y' + p y)$ に一致する条件は $\mu' = p\mu$、すなわち $\mu = e^{\int p}$。
- **完全形と積分因子**: $M\,dt + N\,dy = 0$ が $\partial_y M = \partial_t N$ を満たせば完全形。満たさなくても積分因子で完全形にできる場合がある。
- **Lipschitz と一意性**: $f(t,y)=\sqrt{|y|}$ は $y=0$ で Lipschitz でなく、$y\equiv 0$ と $y=(t/2)^2$ の両方が初期値 0 の解になる。
"""),
    ]
    _save("02_first_order_odes.ipynb", cells)


# --------------------------------------------------------------------------- #
def linear_systems():
    cells = [
        md(r"""
# 03. 線形 ODE と連立系 — 行列・固有値・振動

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture 〜 5. Definition |
| Applied | 6. Computation 〜 9. Application |
| Advanced | 11. Advanced Notes |

## 1. Big Picture

高階の線形 ODE や複数の量が絡む系は、補助変数を導入すると必ず **一階の連立線形系**

$$
\frac{d\mathbf{x}}{dt} = A\mathbf{x}
$$

に書けます。ここから先は **線形代数の言葉**——行列 $A$ の **固有値** が、解が「振動するか・減衰するか・発散するか」を決めます。
"""),
        md(r"""
## 2. Problem / 3. Intuition — 振り子とバネ

バネ・振り子・電気回路はどれも

$$
\ddot{x} + 2\gamma\,\dot{x} + \omega^2 x = F(t)
$$

の形(減衰 + 復元力 + 外力)。$x$ と速度 $v=\dot{x}$ を状態に取ると、二階方程式が一階の 2 次元系になります。

$$
\frac{d}{dt}\begin{pmatrix} x \\ v \end{pmatrix}
= \begin{pmatrix} 0 & 1 \\ -\omega^2 & -2\gamma \end{pmatrix}
\begin{pmatrix} x \\ v \end{pmatrix} + \begin{pmatrix} 0 \\ F(t) \end{pmatrix}
$$
"""),
        setup_cell("ode_book"),
        IMPORT,
        md(r"""
## 4. Visualization / 6. Computation — 減衰の 4 つの顔

$\omega = 1$ を固定し、減衰 $\gamma$ を変えると挙動が質的に変わります:
**無減衰(振動が続く)→ 弱減衰(振動しつつ収束)→ 臨界 → 過減衰(振動せず収束)**。
"""),
        code("""
# Four damping regimes of x'' + 2γ x' + ω^2 x = 0.
scen = datasets.harmonic_scenarios()
fig, ax = plt.subplots(figsize=(7.5, 4))
for name, sc in scen.items():
    f = systems.harmonic_oscillator(sc.params["omega"], sc.params["gamma"])
    Y = solvers.rk4(f, sc.y0, sc.t)
    ax.plot(sc.t, Y[:, 0], lw=2, label=f"{name} (gamma={sc.params['gamma']})")
ax.axhline(0, color="gray", lw=0.6)
ax.legend(fontsize=9)
ax.grid(alpha=0.25)
ax.set_xlabel("t")
ax.set_title("damped harmonic oscillator: position x(t)")
plt.show()
"""),
        md(r"""
## 5. Definition — 固有値が振る舞いを決める

$d\mathbf{x}/dt = A\mathbf{x}$ の解は $A$ の固有値 $\lambda$ と固有ベクトル $\mathbf{v}$ を使って
$\mathbf{x}(t) = \sum_k c_k e^{\lambda_k t}\mathbf{v}_k$ と書けます。

- $\mathrm{Re}\,\lambda < 0$ → 減衰、$> 0$ → 発散
- $\mathrm{Im}\,\lambda \ne 0$ → 振動(角振動数 $\approx |\mathrm{Im}\,\lambda|$)

振動子の行列の固有値を、減衰ごとに見てみます。
"""),
        code("""
import numpy as np

# Eigenvalues of the oscillator matrix explain each regime.
for name, sc in datasets.harmonic_scenarios().items():
    w, g = sc.params["omega"], sc.params["gamma"]
    A = np.array([[0.0, 1.0], [-(w**2), -2 * g]])
    eig = np.linalg.eigvals(A)
    print(f"{name:12s} gamma={g:.2f}  eigenvalues = {np.round(eig, 3)}")
"""),
        md(r"""
## 7. Invariant — エネルギー

無減衰($\gamma=0$)では **力学的エネルギー** $E = \tfrac12(v^2 + \omega^2 x^2)$ が保存します。
数値解でも(良いソルバなら)ほぼ一定に保たれることを確認します。
"""),
        code("""
import numpy as np

# Energy is conserved when undamped (a good check on the integrator).
f = systems.harmonic_oscillator(omega=1.0, gamma=0.0)
t = np.linspace(0, 20, 2001)
Y = solvers.rk4(f, [1.0, 0.0], t)
E = 0.5 * (Y[:, 1] ** 2 + Y[:, 0] ** 2)
print("energy drift over t in [0,20]:", np.max(np.abs(E - E[0])))
"""),
        md(r"""
## 8. Failure Mode / 9. Application — 共振

外力 $F(t) = F_0\cos(\Omega t)$ を加えると、駆動振動数 $\Omega$ が固有振動数 $\omega$ に近いとき
振幅が跳ね上がる **共振** が起きます。定常振幅は

$$
A(\Omega) = \frac{F_0}{\sqrt{(\omega^2 - \Omega^2)^2 + (2\gamma\Omega)^2}}
$$

減衰 $\gamma$ が小さいほど鋭いピーク。橋や建物の設計で避けるべき現象です。
"""),
        code("""
import numpy as np

# Resonance: steady-state amplitude vs driving frequency, several damping levels.
F0, w = 1.0, 1.0
Omega = np.linspace(0.2, 2.0, 400)
fig, ax = plt.subplots(figsize=(6.5, 4))
for g in (0.05, 0.1, 0.25, 0.5):
    A = F0 / np.sqrt((w**2 - Omega**2) ** 2 + (2 * g * Omega) ** 2)
    ax.plot(Omega, A, lw=2, label=f"gamma={g}")
ax.axvline(w, color="gray", ls=":")
ax.legend()
ax.grid(alpha=0.25)
ax.set_xlabel("driving frequency Omega")
ax.set_ylabel("amplitude")
ax.set_title("resonance peaks near Omega = omega")
plt.show()
"""),
        md(r"""
## Exercises

1. $\ddot{x} + 5\dot{x} + 6x = 0$ を一階系に直し、固有値 $-2, -3$ から過減衰であることを示せ。
2. 無減衰振動子のエネルギー保存を、Euler 法では破れること(エネルギーが増大)を数値で示せ。
3. 共振振幅 $A(\Omega)$ を $\Omega$ で微分し、ピーク位置 $\Omega^2 = \omega^2 - 2\gamma^2$ を導け。

## Advanced Notes

- **行列指数関数**: $d\mathbf{x}/dt = A\mathbf{x}$ の解は $\mathbf{x}(t) = e^{At}\mathbf{x}_0$。$e^{At}$ は固有分解 $A=V\Lambda V^{-1}$ で $V e^{\Lambda t} V^{-1}$。
- **重複固有値**: $A$ が対角化できないとき(Jordan ブロック)、解に $t e^{\lambda t}$ の項が現れる。臨界減衰がその例。
- **シンプレクティック積分**: 保存系では RK4 でも長時間でエネルギーがわずかに漂う。シンプレクティック法(leapfrog 等)は保存量をよく保つ。
"""),
    ]
    _save("03_linear_odes_and_systems.ipynb", cells)


# --------------------------------------------------------------------------- #
def phase_plane():
    cells = [
        md(r"""
# 04. 相図と安定性 — 固定点・線形化・分類

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture 〜 5. Definition |
| Applied | 6. Computation 〜 9. Application |
| Advanced | 11. Advanced Notes |

## 1. Big Picture

自励系 $d\mathbf{x}/dt = \mathbf{f}(\mathbf{x})$ では、時刻に依らず各点に速度ベクトルが定まります。
これを平面に描いたものが **相図 (phase portrait)**。解は時間軸を消して **軌道(オービット)** として見えます。
relevant な情報は **固定点(平衡点)とその安定性** に凝縮されます。
"""),
        md(r"""
## 2. Problem / 3. Intuition / 5. Definition — 固定点を分類する

$\mathbf{f}(\mathbf{x}^\*)=\mathbf{0}$ となる点が **固定点**。その近くで $\mathbf{f}$ を線形化すると、
ヤコビ行列 $J = D\mathbf{f}(\mathbf{x}^\*)$ の固有値が局所的な振る舞いを決めます。

- 実・同符号負 → **stable node (sink)**、実・同符号正 → **unstable node (source)**
- 実・異符号 → **saddle**
- 複素・実部負 → **stable spiral**、実部正 → **unstable spiral**、実部 0 → **center**
"""),
        setup_cell("ode_book"),
        IMPORT,
        md(r"""
## 4. Visualization / 6. Computation — 5 つの典型を一望する (Applied)

線形系 $d\mathbf{x}/dt = A\mathbf{x}$ の相図を、行列 $A$ を変えて並べます。
`systems.classify_fixed_point` が固有値から型を自動判定します。
"""),
        code("""
import numpy as np

# The canonical 2-D linear phase portraits, auto-classified from eigenvalues.
mats = {
    "stable node":     [[-1.0, 0.0], [0.0, -2.0]],
    "saddle":          [[1.0, 0.0], [0.0, -1.0]],
    "unstable node":   [[1.0, 0.0], [0.0, 2.0]],
    "stable spiral":   [[-0.3, 1.0], [-1.0, -0.3]],
    "center":          [[0.0, 1.0], [-1.0, 0.0]],
    "unstable spiral": [[0.3, 1.0], [-1.0, 0.3]],
}
fig, axes = plt.subplots(2, 3, figsize=(13, 8))
for ax, (name, A) in zip(axes.ravel(), mats.items()):
    A = np.array(A)
    f = systems.linear_system(A)
    plotting.phase_portrait(f, (-3, 3), (-3, 3), fixed_points=[(0, 0)], ax=ax)
    kind = systems.classify_fixed_point(A)
    ax.set_title(f"{name}  ->  {kind}")
fig.tight_layout()
plt.show()
"""),
        md(r"""
## 7. Invariant / 8. Failure Mode — 線形化が効かないとき

線形化は **固有値の実部がゼロでない(双曲型)** 固定点でのみ確実です(Hartman–Grobman)。
center のように実部 0 のときは、非線形項が安定/不安定を左右し、線形化だけでは判定できません。
"""),
        md(r"""
## 9. Application — ヌルクラインと非線形系

**ヌルクライン** は $\dot{x}=0$ や $\dot{y}=0$ となる曲線。その交点が固定点で、
ヌルクラインは平面を「どちらへ流れるか」の領域に分けます。
競合 2 種モデル $\dot{x}=x(3-x-2y),\ \dot{y}=y(2-x-y)$ で描いてみます。
"""),
        code("""
import numpy as np

# Nullclines (dx/dt=0 in blue, dy/dt=0 in green) and fixed points of a competition model.
def f(t, s):
    x, y = s
    return np.array([x * (3 - x - 2 * y), y * (2 - x - y)])

ax = plotting.phase_portrait(f, (0, 3.5), (0, 2.5), n=24)
xs = np.linspace(0, 3.5, 200)
ys = np.linspace(0, 2.5, 200)
X, Y = np.meshgrid(xs, ys)
DX = X * (3 - X - 2 * Y)
DY = Y * (2 - X - Y)
ax.contour(X, Y, DX, levels=[0], colors="#1f77b4", linewidths=2)
ax.contour(X, Y, DY, levels=[0], colors="#2ca02c", linewidths=2)
for fp in [(0, 0), (3, 0), (0, 2), (1, 1)]:
    ax.plot(*fp, "*", color="#d62728", ms=14)
    print(f"fixed point {fp}: type =", systems.classify_fixed_point(systems.jacobian(f, fp)))
ax.set_title("competition model: nullclines (blue/green) and fixed points")
plt.show()
"""),
        md(r"""
## Exercises

1. $A = \begin{pmatrix} 2 & 1 \\ 1 & 2 \end{pmatrix}$ の固定点の型を、固有値を手計算して判定し、`classify_fixed_point` と一致させよ。
2. 減衰振動子 $(\gamma>0)$ の原点が stable spiral になることを、ヤコビ行列の固有値から示せ。
3. 上の競合モデルで内部固定点 $(1,1)$ が saddle になることを確かめ、生態学的な意味(共存できない)を述べよ。

## Advanced Notes

- **Hartman–Grobman 定理**: 双曲型固定点の近くでは、非線形系は線形化系と位相共役(定性的に同じ)。
- **trace–determinant 図**: 2×2 では $\mathrm{tr}\,A$ と $\det A$ の位置だけで型が決まる。判別式 $(\mathrm{tr})^2 - 4\det$ の符号が node/spiral を分ける。
- **Lyapunov 関数**: 線形化で決まらない場合でも、適切なエネルギー様関数 $V$ が減少すれば漸近安定を示せる。
- **Poincaré–Bendixson 定理**: 平面の有界軌道は、固定点か **閉軌道(リミットサイクル)** に収束する。平面ではカオスは起きない(→ 3 次元が必要、05 章)。
"""),
    ]
    _save("04_phase_plane_and_stability.ipynb", cells)


# --------------------------------------------------------------------------- #
def nonlinear():
    cells = [
        md(r"""
# 05. 非線形ダイナミクス — 捕食者・被食者・感染・分岐・カオス

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture 〜 4. Visualization |
| Applied | 5. Lotka-Volterra 〜 8. カオス |
| Advanced | 11. Advanced Notes |

## 1. Big Picture

非線形 ODE は、線形系にはない豊かな現象——**周期軌道・分岐・カオス**——を生みます。
本章は代表的な非線形モデルを通して、その入口を体験します。
"""),
        setup_cell("ode_book"),
        IMPORT,
        md(r"""
## 5. Lotka-Volterra — 捕食者と被食者 (Applied)

$$
\dot{x} = \alpha x - \beta x y, \qquad \dot{y} = \delta x y - \gamma y
$$

被食者 $x$ と捕食者 $y$ は互いに増減を引き起こし、**閉じた周期軌道** を描きます(個体数が周期的に振動)。
"""),
        code("""
import numpy as np

# Predator-prey: closed orbits in phase space + oscillating populations in time.
sc = datasets.lotka_volterra_scenario()
f = systems.lotka_volterra(**sc.params)
Y = solvers.rk4(f, sc.y0, sc.t)

fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.5))
for y0 in ([2, 1], [1.5, 1], [3, 1.5]):
    traj = solvers.rk4(f, y0, sc.t)
    a1.plot(traj[:, 0], traj[:, 1], lw=1.5)
a1.set_xlabel("prey x")
a1.set_ylabel("predator y")
a1.set_title("phase plane: closed (periodic) orbits")
a1.grid(alpha=0.25)
a2.plot(sc.t, Y[:, 0], label="prey x")
a2.plot(sc.t, Y[:, 1], label="predator y")
a2.legend()
a2.grid(alpha=0.25)
a2.set_xlabel("t")
a2.set_title("populations oscillate, predator lags prey")
fig.tight_layout()
plt.show()
"""),
        md(r"""
## 6. SIR — 感染症の流行

$$
\dot{S} = -\beta S I,\quad \dot{I} = \beta S I - \gamma I,\quad \dot{R} = \gamma I
$$

基本再生産数 $R_0 = \beta/\gamma$。$R_0 > 1$ なら感染は一度拡大してピークを作り、やがて終息します。
"""),
        code("""
# SIR outbreak: susceptible / infected / recovered over time.
sc = datasets.sir_scenario()
f = systems.sir(**sc.params)
Y = solvers.rk4(f, sc.y0, sc.t)
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(sc.t, Y[:, 0], label="S")
ax.plot(sc.t, Y[:, 1], label="I")
ax.plot(sc.t, Y[:, 2], label="R")
ax.legend()
ax.grid(alpha=0.25)
ax.set_xlabel("t")
ax.set_title(f"SIR, R0 = beta/gamma = {sc.params['beta'] / sc.params['gamma']:.1f}")
plt.show()
print("peak infected fraction =", round(float(Y[:, 1].max()), 3))
"""),
        md(r"""
## 7. 分岐 (bifurcation) — パラメータで質が変わる

パラメータをゆっくり変えると、固定点の **数や安定性が突然変わる** ことがあります。
$\dot{y} = r y - y^3$ の平衡点は、$r<0$ では $y=0$ のみ(安定)、$r>0$ で $y=\pm\sqrt{r}$ が現れる
**ピッチフォーク分岐** です。
"""),
        code("""
import numpy as np

# Pitchfork bifurcation of dy/dt = r y - y^3: equilibria branch at r=0.
r = np.linspace(-1, 1, 400)
fig, ax = plt.subplots(figsize=(6.5, 4))
ax.plot(r, np.zeros_like(r), "k--", lw=1)  # y=0 (dashed=unstable for r>0)
ax.plot(r[r >= 0], np.sqrt(r[r >= 0]), color="#d62728", lw=2)
ax.plot(r[r >= 0], -np.sqrt(r[r >= 0]), color="#d62728", lw=2)
ax.axvline(0, color="gray", ls=":")
ax.set_xlabel("parameter r")
ax.set_ylabel("equilibrium y*")
ax.set_title("pitchfork bifurcation: dy/dt = r y - y^3")
ax.grid(alpha=0.25)
plt.show()
"""),
        md(r"""
## 8. カオスの入口 — Lorenz 系 (Advanced)

平面ではカオスは起きません(Poincaré–Bendixson)。3 次元になると話が変わります。**Lorenz 系**

$$
\dot{x} = \sigma(y-x),\quad \dot{y} = x(\rho - z) - y,\quad \dot{z} = xy - \beta z
$$

は有名な蝶形アトラクタを描き、**初期値鋭敏性**(わずかな差が指数的に拡大)を示します。
"""),
        code("""
import numpy as np

# Lorenz attractor + sensitive dependence on initial conditions.
f = systems.lorenz()
t = np.linspace(0, 40, 8000)
A = solvers.solve(f, [1.0, 1.0, 1.0], t, rtol=1e-9, atol=1e-9)
B = solvers.solve(f, [1.0, 1.0, 1.0 + 1e-8], t, rtol=1e-9, atol=1e-9)  # tiny perturbation

fig = plt.figure(figsize=(12, 4.5))
ax1 = fig.add_subplot(1, 2, 1, projection="3d")
ax1.plot(A[:, 0], A[:, 1], A[:, 2], lw=0.4, color="#1f77b4")
ax1.set_title("Lorenz attractor (butterfly)")
ax2 = fig.add_subplot(1, 2, 2)
ax2.semilogy(t, np.abs(A[:, 0] - B[:, 0]) + 1e-16, color="#d62728")
ax2.set_xlabel("t")
ax2.set_ylabel("|x_A - x_B|")
ax2.set_title("1e-8 initial gap grows exponentially (chaos)")
ax2.grid(alpha=0.3, which="both")
fig.tight_layout()
plt.show()
"""),
        md(r"""
## Exercises

1. Lotka-Volterra には保存量 $V = \delta x - \gamma\ln x + \beta y - \alpha\ln y$ がある。軌道上で $V$ がほぼ一定になることを数値で確かめよ。
2. SIR で、感染がピークに達する条件が $S = \gamma/\beta$($\dot I = 0$)であることを示せ。
3. ピッチフォーク分岐で $r>0$ のとき $y=0$ が不安定、$y=\pm\sqrt{r}$ が安定であることを線形化で示せ。
4. Lorenz 系で初期差を $10^{-6}$ に変えると、軌道が分かれ始める時刻がどう変わるか観察せよ。

## Advanced Notes

- **保存系 vs 散逸系**: Lotka-Volterra は保存量を持つ(周期軌道)。現実的な修正(ロジスティック項)を入れると軌道は固定点へ巻き込む。
- **リミットサイクル**: Van der Pol 振動子 `systems.van_der_pol(mu)` は孤立した安定周期軌道を持つ。初期値によらず同じ周期運動へ収束する。
- **Lyapunov 指数**: 初期値鋭敏性の定量化。正の最大 Lyapunov 指数がカオスの指標。
- **分岐の種類**: saddle-node / transcritical / pitchfork / Hopf(固定点から周期軌道が生まれる)など。
"""),
    ]
    _save("05_nonlinear_dynamics.ipynb", cells)


# --------------------------------------------------------------------------- #
def numerical():
    cells = [
        md(r"""
# 06. 数値解法 — Euler・Heun・RK4・安定性・stiff

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture 〜 4. Visualization |
| Applied | 5. 誤差と次数 〜 8. solve_ivp |
| Advanced | 11. Advanced Notes |

## 1. Big Picture

ほとんどの ODE は閉じた式で解けません。そこで **方向場に沿って小さく前進** します。
刻み幅 $\Delta t$ をどう使うかで精度と安定性が決まります。本章は Euler / Heun / RK4 を比較し、
**「刻み方を間違えると数値解は壊れる」** ことを体験します。
"""),
        md(r"""
## 2. Definition — 3 つのステッパ

1 ステップ $t_k \to t_{k+1}=t_k+\Delta t$ の進め方:

- **Euler(1 次)**: $y_{k+1} = y_k + \Delta t\, f(t_k, y_k)$
- **Heun(2 次)**: 予測子 + 修正子(台形)
- **RK4(4 次)**: 区間内 4 点の傾きを加重平均(精度の定番)

次数 $p$ が高いほど、$\Delta t$ を半分にしたときの誤差の減りが速い($\propto \Delta t^p$)。
"""),
        setup_cell("ode_book"),
        IMPORT,
        md(r"""
## 4. Visualization — 同じ $\Delta t$ でどれだけ違うか
"""),
        code("""
import numpy as np

# Same coarse dt, three methods, against the exact decay.
f = systems.exponential(-1.0)
t = np.linspace(0, 5, 16)
exact = np.exp(-t)
fig, ax = plt.subplots(figsize=(6.5, 4))
ax.plot(t, exact, "k-", lw=2, label="exact")
for name, Y in [("euler", solvers.euler(f, [1.0], t)),
                ("heun", solvers.heun(f, [1.0], t)),
                ("rk4", solvers.rk4(f, [1.0], t))]:
    ax.plot(t, Y[:, 0], "o-", ms=4, label=name)
ax.legend()
ax.grid(alpha=0.25)
ax.set_xlabel("t")
ax.set_title(f"dt = {t[1] - t[0]:.3f}: accuracy by method")
plt.show()
"""),
        md(r"""
## 5. 誤差と収束次数 (Applied)

刻み幅 $\Delta t$ に対する最大誤差を両対数で見ると、傾きが **収束次数** を表します
(Euler ≈ 1、Heun ≈ 2、RK4 ≈ 4)。
"""),
        code("""
import numpy as np

# Convergence order: error vs dt on log-log; slope = method order.
f = systems.exponential(-1.0)
ns = np.array([8, 16, 32, 64, 128, 256])
dts, errs = [], {"euler": [], "heun": [], "rk4": []}
for n in ns:
    t = np.linspace(0, 2, n + 1)
    dts.append(t[1] - t[0])
    exact = np.exp(-t)
    for name, fn in [("euler", solvers.euler), ("heun", solvers.heun), ("rk4", solvers.rk4)]:
        errs[name].append(solvers.global_error(fn(f, [1.0], t)[:, 0], exact))

fig, ax = plt.subplots(figsize=(6.5, 4))
for name in errs:
    ax.loglog(dts, errs[name], "o-", label=name)
for p, c in [(1, "1"), (2, "2"), (4, "4")]:
    ref = np.array(dts) ** p
    ax.loglog(dts, ref / ref[0] * errs["euler" if p == 1 else "heun" if p == 2 else "rk4"][0],
              "--", color="gray", lw=0.8)
ax.legend()
ax.set_xlabel("dt")
ax.set_ylabel("max error")
ax.set_title("convergence order (slopes ~ 1, 2, 4)")
ax.grid(alpha=0.3, which="both")
plt.show()
for name in errs:
    rate = np.log(errs[name][0] / errs[name][-1]) / np.log(dts[0] / dts[-1])
    print(f"{name:6s} measured order ~ {rate:.2f}")
"""),
        md(r"""
## 6. 安定性 — 大きすぎる $\Delta t$ で爆発する

精度とは別に **安定性** の問題があります。$dy/dt=\lambda y$($\lambda<0$)に陽的 Euler を使うと、
増幅率は $|1+\lambda\Delta t|$。これが 1 を超える($\Delta t > 2/|\lambda|$)と、真の解は減衰するのに
**数値解は振動しながら発散** します。
"""),
        code("""
import numpy as np

# Explicit Euler on dy/dt = -50 y: stable only if dt < 2/50 = 0.04.
lam = -50.0
f = systems.exponential(lam)
fig, ax = plt.subplots(figsize=(6.5, 4))
for dt in (0.01, 0.039, 0.041, 0.05):
    t = np.arange(0, 1 + dt, dt)
    Y = solvers.euler(f, [1.0], t)[:, 0]
    style = "-" if dt < 2 / abs(lam) else "--"
    ax.plot(t, Y, style, lw=1.8, label=f"dt={dt} ({'stable' if dt < 0.04 else 'UNSTABLE'})")
ax.axhline(0, color="gray", lw=0.6)
ax.set_ylim(-2, 2)
ax.legend(fontsize=9)
ax.grid(alpha=0.25)
ax.set_xlabel("t")
ax.set_title("explicit Euler stability threshold dt = 2/|lambda| = 0.04")
plt.show()
"""),
        md(r"""
## 7. stiff 方程式 — 陰解法の出番

**stiff** な系は、速い成分と遅い成分の時間スケールが極端に違う系です。
陽的解法は安定性のために極小の $\Delta t$ を強いられ、非効率。**陰的解法**(Radau, BDF)は
大きな刻みでも安定です。固有値 $-1$ と $-1000$ を持つ線形系で、関数評価回数 (`nfev`) を比べます。
"""),
        code("""
import numpy as np
from scipy.integrate import solve_ivp

# Stiff linear system: eigenvalues -1 and -1000. Compare explicit RK45 vs implicit Radau.
A = np.array([[-1.0, 0.0], [0.0, -1000.0]])
f = systems.linear_system(A)
span = (0.0, 5.0)
y0 = [1.0, 1.0]
for method in ("RK45", "Radau", "BDF"):
    sol = solve_ivp(f, span, y0, method=method, rtol=1e-6, atol=1e-9)
    print(f"{method:6s}  steps(nfev) = {sol.nfev:6d}   success = {sol.success}")
"""),
        md(r"""
## 8. `scipy.integrate.solve_ivp` — 実務の道具

手作りステッパは学習用。実務では適応刻み幅・誤差制御つきの `solve_ivp` を使います。
`solvers.solve` はその薄いラッパで、グリッド上の解を返します(stiff なら `method="Radau"`)。

## Exercises

1. Heun 法の収束次数が 2 であることを、上の収束プロットの傾きから読み取れ。
2. 陽的 Euler の安定限界 $\Delta t < 2/|\lambda|$ を、増幅率 $|1+\lambda\Delta t|<1$ から導け。
3. stiff 系で RK45 と Radau の `nfev` 比を確かめ、なぜ陰解法が有利か説明せよ。

## Advanced Notes

- **絶対安定領域**: 各解法には複素平面上の安定領域がある。陽的法は有界、陰的法(A-安定)は左半平面全体を含む。
- **適応刻み**: RK45(Dormand–Prince)は 4 次と 5 次の差で誤差を推定し $\Delta t$ を自動調整する。
- **保存系の長時間積分**: シンプレクティック法は位相空間体積を保ち、エネルギー誤差が増えない。
- **DAE / イベント検出**: `solve_ivp` の `events` で「地面に着いた瞬間」などを検出できる。
"""),
    ]
    _save("06_numerical_methods.ipynb", cells)


# --------------------------------------------------------------------------- #
def applications():
    cells = [
        md(r"""
# 07. 応用 — 物理・生物・金融・機械学習・制御

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture |
| Applied | 2. 物理 〜 6. 制御 |
| Advanced | 11. Advanced Notes |

## 1. Big Picture

ODE は分野を越えた共通言語です。本章は、これまでの道具を各分野の代表問題に当てはめます。
同じ「変化率をルールとして与える」枠組みが、振動・感染・金利・深層学習・制御に現れます。
"""),
        setup_cell("ode_book"),
        IMPORT,
        md(r"""
## 2. 物理 — 強制減衰振動と共振 (Applied)

外力つき振動子 $\ddot{x} + 2\gamma\dot{x} + \omega^2 x = F_0\cos(\Omega t)$ を時間積分し、
駆動振動数 $\Omega$ を固有 $\omega$ に合わせると振幅が育つ(共振)様子を見ます。
"""),
        code("""
import numpy as np

# Forced damped oscillator: transient + steady oscillation; near-resonant drive.
w, g, F0 = 1.0, 0.1, 0.5
for Omega, label in [(0.6, "off-resonance"), (1.0, "resonance")]:
    f = systems.harmonic_oscillator(w, g, forcing=lambda t, Om=Omega: F0 * np.cos(Om * t))
    t = np.linspace(0, 80, 4000)
    Y = solvers.rk4(f, [0.0, 0.0], t)
    plt.plot(t, Y[:, 0], lw=1, label=f"Omega={Omega} ({label})")
plt.legend()
plt.grid(alpha=0.25)
plt.xlabel("t")
plt.title("forced damped oscillator: resonance builds a larger amplitude")
plt.show()
"""),
        md(r"""
## 3. 生物 — 感染症の介入効果

SIR を使い、接触率 $\beta$ を下げる(隔離・ワクチン)とピークがどう変わるかを比べます
(いわゆる「流行曲線を平らにする」)。
"""),
        code("""
# Flattening the curve: lowering beta reduces and delays the infection peak.
sc = datasets.sir_scenario()
t = sc.t
fig, ax = plt.subplots(figsize=(7, 4))
for beta in (0.5, 0.35, 0.25):
    f = systems.sir(beta=beta, gamma=sc.params["gamma"], N=1.0)
    Y = solvers.rk4(f, sc.y0, t)
    ax.plot(t, Y[:, 1], lw=2, label=f"beta={beta}, R0={beta / sc.params['gamma']:.2f}")
ax.legend()
ax.grid(alpha=0.25)
ax.set_xlabel("t")
ax.set_ylabel("infected fraction I")
ax.set_title("lowering beta flattens the epidemic peak")
plt.show()
"""),
        md(r"""
## 4. 金融 — 平均回帰 (Ornstein–Uhlenbeck / Vasicek の決定論部分)

短期金利モデル(Vasicek)は確率微分方程式

$$
dr_t = \kappa(\theta - r_t)\,dt + \sigma\,dW_t
$$

です。$\sigma\,dW_t$ はランダムな揺らぎ(ブラウン運動)。これを取り除いた **決定論部分**

$$
\frac{dr}{dt} = \kappa(\theta - r)
$$

は線形一階 ODE で、解は $r(t) = \theta + (r_0-\theta)e^{-\kappa t}$。
どの初期値からも長期平均 $\theta$ へ **平均回帰** します。ODE は SDE の「骨格(ドリフト)」を与えます。
"""),
        code("""
import numpy as np

# Deterministic skeleton of Vasicek: mean reversion to theta. Plus one noisy sample path.
kappa, theta, sigma = 0.8, 0.03, 0.015
t = np.linspace(0, 10, 600)
f = lambda tt, r: kappa * (theta - r)
fig, ax = plt.subplots(figsize=(7, 4))
for r0 in (0.0, 0.06, 0.09):
    r_det = solvers.rk4(f, [r0], t)[:, 0]
    ax.plot(t, r_det, lw=2, label=f"deterministic, r0={r0}")
# one Euler-Maruyama path on top (noise illustration only, seed fixed)
rng = np.random.default_rng(0)
dt = t[1] - t[0]
r = np.empty_like(t)
r[0] = 0.06
for k in range(t.size - 1):
    r[k + 1] = r[k] + kappa * (theta - r[k]) * dt + sigma * np.sqrt(dt) * rng.standard_normal()
ax.plot(t, r, color="gray", lw=0.8, alpha=0.8, label="one SDE sample path")
ax.axhline(theta, color="#2ca02c", ls="--", lw=1, label="theta (long-run mean)")
ax.legend(fontsize=8)
ax.grid(alpha=0.25)
ax.set_xlabel("t")
ax.set_title("mean reversion: ODE drift is the skeleton of the SDE")
plt.show()
"""),
        md(r"""
## 5. 機械学習 — Neural ODE の概念的導入

残差ネット $z_{k+1} = z_k + \Delta t\, f_\theta(z_k)$ は、Euler 1 ステップそのもの。
層を無限に細かくした極限が **Neural ODE** $dz/dt = f_\theta(z)$ です。
ここでは学習は行わず、固定した $f_\theta(z)=Az$ の **流れ** が点群をどう変形するかだけを見ます
(「深さ = 時間」のイメージ)。
"""),
        code("""
import numpy as np

# Neural-ODE intuition: a fixed vector field f(z)=Az transforms a point cloud as "depth" t grows.
A = np.array([[-0.2, -1.0], [1.0, -0.2]])  # spiral-in flow
f = systems.linear_system(A)
theta = np.linspace(0, 2 * np.pi, 60)
cloud = np.c_[np.cos(theta), np.sin(theta)] * 2.0  # initial ring
t = np.linspace(0, 3, 50)
fig, ax = plt.subplots(figsize=(5.5, 5.5))
for snap, col in [(0, "#1f77b4"), (20, "#9467bd"), (49, "#d62728")]:
    pts = np.array([solvers.rk4(f, p, t)[snap] for p in cloud])
    ax.plot(np.r_[pts[:, 0], pts[0, 0]], np.r_[pts[:, 1], pts[0, 1]], color=col,
            label=f"t={t[snap]:.1f}")
ax.set_aspect("equal")
ax.legend()
ax.grid(alpha=0.25)
ax.set_title("a learned vector field as a flow (Neural ODE intuition)")
plt.show()
"""),
        md(r"""
## 6. 制御 — フィードバックで安定化

不安定な系 $\dot{x} = a x$($a>0$ は発散)に、状態フィードバック $u = -k x$ を加えると
$\dot{x} = (a-k)x$。ゲイン $k>a$ で **安定化** できます。制御の最も基本的なアイデアです。
"""),
        code("""
import numpy as np

# Feedback stabilization: unstable dx/dt = a x becomes stable with u = -k x (k > a).
a = 1.0
t = np.linspace(0, 6, 300)
fig, ax = plt.subplots(figsize=(6.5, 4))
for k in (0.0, 0.5, 1.5, 3.0):
    f = lambda tt, x, kk=k: (a - kk) * x
    Y = solvers.rk4(f, [1.0], t)[:, 0]
    ax.plot(t, Y, lw=2, label=f"k={k} ({'stable' if k > a else 'unstable'})")
ax.axhline(0, color="gray", lw=0.6)
ax.set_ylim(-1, 8)
ax.legend()
ax.grid(alpha=0.25)
ax.set_xlabel("t")
ax.set_title("state feedback u = -k x stabilizes when k > a")
plt.show()
"""),
        md(r"""
## Exercises

1. 強制振動子で $\Omega$ を 0.2〜2.0 と変え、定常振幅のピークが $\omega$ 付近に来ることを数値で確かめよ。
2. Vasicek の決定論解 $r(t)=\theta+(r_0-\theta)e^{-\kappa t}$ を導き、$\kappa$ が大きいほど速く回帰することを示せ。
3. 制御の例で、$a=2$ のとき安定化に必要な最小ゲイン $k$ を求めよ。

## Advanced Notes

- **SDE と Fokker–Planck**: $dr=\kappa(\theta-r)dt+\sigma dW$ の確率分布は Fokker–Planck 方程式(PDE!)に従う。ODE/PDE/確率が交わる地点。
- **Neural ODE の学習**: 随伴感度法 (adjoint) で勾配をメモリ効率よく計算する。`torchdiffeq` などが有名。
- **最適制御と Pontryagin**: コスト最小化のための最適入力は、状態と随伴変数の連立 ODE(ハミルトン系)で特徴づけられる。
- **線形制御理論**: $\dot{\mathbf{x}}=A\mathbf{x}+B\mathbf{u}$ の安定化は、$A-BK$ の固有値を左半平面に置く極配置問題になる。
"""),
    ]
    _save("07_applications_physics_biology_finance.ipynb", cells)


BUILDERS = {
    "01": overview,
    "02": first_order,
    "03": linear_systems,
    "04": phase_plane,
    "05": nonlinear,
    "06": numerical,
    "07": applications,
}

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    todo = BUILDERS.keys() if arg == "all" else [arg]
    for key in todo:
        BUILDERS[key]()
