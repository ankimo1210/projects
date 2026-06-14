"""Build the PDE book chapter notebooks 01..07 (00 is built separately).

Usage: python build_pde_notebook.py [all|01|02|...|07]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nbkit import code, md, setup_cell, write  # noqa: E402

NB = Path(__file__).resolve().parent.parent / "pde-book" / "notebooks"
IMPORT = code("from pde_book import grids, solvers, plotting, datasets")


def _save(name, cells):
    write(cells, str(NB / name))
    print("wrote", NB / name)


# --------------------------------------------------------------------------- #
def overview():
    cells = [
        md(r"""
# 01. PDE の全体像 — 空間と時間の中で、場がどう変わるか

> 本書の読み方: **微分積分(00 章) → ODE → PDE → 応用**。
> この章は PDE 全体の地図です。ODE(時間方向の変化)を踏まえ、ここからは **空間方向の変化** が加わります。

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture 〜 4. Visualization |
| Applied | 5. 問題の種類 〜 6. 読み方 |
| Advanced | 7. Advanced Notes |

## 1. Big Picture

**偏微分方程式 (PDE)** が記述するのは、ただ一つ。

> **空間と時間の中で、場がどう変化するか。**

未知関数は、場所 $x$(や $x,y,z$)と時刻 $t$ の両方に依存する **場** $u(x, t)$ です。
PDE は、その場の **時間変化率** $\partial u/\partial t$ や **空間的な曲がり方** $\partial^2 u/\partial x^2$ の間の関係を、
局所的なルールとして与えます。たとえば熱方程式

$$
\frac{\partial u}{\partial t} = \alpha \frac{\partial^2 u}{\partial x^2}
$$

は「各点の時間変化率 = その点の空間的な曲がり方に比例」というルールです。
"""),
        md(r"""
## 2. ODE との違い / 3. 場とは何か

- **ODE**: 状態は有限個の数($y(t)$ や $\mathbf{x}(t)$)。変化は **時間** の 1 方向だけ。
- **PDE**: 状態は **場**($u(x,t)$)= 各点に値が乗った連続体。変化は **時間 + 空間** の複数方向。

「場」とは、空間の各点に量が割り当てられたもの——棒の各点の温度、弦の各点の変位、平面の各点の電位、など。
PDE は、その無限自由度の場を支配する局所ルールです。
"""),
        setup_cell("pde_book"),
        IMPORT,
        md(r"""
## 4. Visualization — 拡散(なめらかにする)と伝播(伝える)

PDE の二大挙動を一目で。**熱方程式は場をなめらかにし**、**波動方程式は形を保って伝える**。
まず初期の段差(でこぼこ)が熱方程式でどう平滑化されるかを、時間スナップショットで見ます。
"""),
        code("""
import numpy as np

# Heat equation smooths an initial bump over time (Dirichlet ends).
g = grids.Grid1D(0.0, 1.0, 101)
x, dx = g.x, g.dx
alpha = 1.0
dt = 0.4 * dx**2 / alpha
U = solvers.solve_heat_explicit(datasets.bump(x, 0.5, 0.15), alpha, dx, dt, steps=400)
ax = plotting.plot_field_snapshots(x, U, [0, 20, 80, 400], dt=dt,
                                   title="heat equation: an initial bump smooths out")
ax.set_ylim(-0.1, 1.2)
plt.show()
"""),
        md(r"""
PDE には「時刻 $t$ ごとの場のスナップショット」という見方のほかに、
**横軸=空間・縦軸=時間** の **時空間ヒートマップ** という見方があります。拡散の広がりが見えます。
"""),
        code("""
import numpy as np

# Same evolution as a space-time heatmap: the bump diffuses outward.
t = np.arange(U.shape[0]) * dt
plotting.space_time_heatmap(U, x, t, title="u(x, t): diffusion in space-time")
plt.show()
"""),
        md(r"""
## 5. 問題の種類 — 時間発展問題と境界値問題 (Applied)

PDE は大きく 2 種類に分かれます。

- **時間発展問題**(放物型・双曲型): 初期条件から時間を前へ進める。**熱・移流・波動**(02 章)。
  → 必要なのは **初期条件** + **境界条件**。
- **境界値問題**(楕円型): 時間がなく、領域の縁の値から内部の定常状態を決める。**Laplace・Poisson**(03 章)。
  → 必要なのは **境界条件** のみ。

### 初期条件と境界条件

- **初期条件**: $t=0$ での場の形 $u(x, 0)$。
- **境界条件**: 領域の縁での約束。値を指定する **Dirichlet**、傾き(流量)を指定する **Neumann** など。

これらを取り違えると、解は一意に決まりません。
"""),
        md(r"""
## 6. この教材の読み方

各章は **現象 → 直感 → 可視化 → 数式 → Python 実験 → 応用 → 発展** の流れ、
そして **Basic / Applied / Advanced** の 3 層構成です。

### 章構成 (PDE Book)

| Notebook | 内容 |
|---|---|
| `00_calculus_foundations` | 前提編: 微分=変化率 / 積分=蓄積 / 偏微分・勾配・Hessian |
| `01_overview` | PDE の全体像(この章) |
| `02_transport_heat_wave` | 移流・熱・波動 — 拡散と伝播 |
| `03_laplace_poisson_boundary_value` | Laplace・Poisson・境界条件・調和関数 |
| `04_fourier_series_and_transform` | Fourier 級数/変換 — 関数を波に分解 |
| `05_separation_of_variables` | 変数分離・固有関数・解析解 |
| `06_numerical_pde_fdm` | 有限差分法・安定性・CFL・数値拡散 |
| `07_applications_physics_finance_ml` | 物理・金融(Black-Scholes)・画像・拡散モデル |

### Python 環境の準備

```bash
cd ~/projects && make install                 # workspace 内(推奨)
# or standalone:
cd analytics/differential_equation/pde-book
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
```

各 Notebook の最初のセルは、`pde_book` が未インストールでも `src/` を探して読み込みます。
"""),
        md(r"""
## 7. Advanced Notes

- **PDE の分類**: 2 階線形 PDE $A u_{xx} + B u_{xy} + C u_{yy} + \dots$ は判別式 $B^2 - 4AC$ の符号で
  **楕円型**(<0; Laplace)・**放物型**(=0; 熱)・**双曲型**(>0; 波動)に分かれ、解の性質が大きく異なる。
- **適切性 (well-posedness)**: 解が「存在し・一意で・データに連続依存する」こと。境界/初期条件の付け方で決まる。
- **特性曲線**: 双曲型では情報が有限速度で特性に沿って伝わる(波動の伝播速度 $c$)。放物型では無限速度で瞬時に拡散する。
"""),
    ]
    _save("01_overview.ipynb", cells)


# --------------------------------------------------------------------------- #
def transport_heat_wave():
    cells = [
        md(r"""
# 02. 移流・熱・波動 — 拡散と伝播の違い

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture 〜 4. Visualization |
| Applied | 5. 熱 〜 7. 波動 |
| Advanced | 11. Advanced Notes |

## 1. Big Picture

時間発展する 1 次元 PDE の三役(順に **移流(伝播)**・**熱(拡散)**・**波動(両方向伝播)**):

$$
\underbrace{\frac{\partial u}{\partial t} + c\frac{\partial u}{\partial x} = 0}_{\text{transport}}
\qquad
\underbrace{\frac{\partial u}{\partial t} = \alpha\frac{\partial^2 u}{\partial x^2}}_{\text{heat}}
\qquad
\underbrace{\frac{\partial^2 u}{\partial t^2} = c^2\frac{\partial^2 u}{\partial x^2}}_{\text{wave}}
$$

一階の空間微分は **流れ**、二階の空間微分は **拡散** を生みます。同じ「場のルール」でも挙動は対照的です。
"""),
        setup_cell("pde_book"),
        IMPORT,
        md(r"""
## 4. 移流方程式 — 形を保って右へ流れる

$\partial_t u + c\,\partial_x u = 0$ の解は $u(x,t) = u_0(x - ct)$、つまり **初期波形がそのまま速度 $c$ で平行移動**。
数値的には風上差分(upwind)で解きます(わずかに数値拡散でなまります)。
"""),
        code("""
import numpy as np

# Advection: the initial profile translates to the right at speed c.
g = grids.Grid1D(0.0, 1.0, 401)
x, dx = g.x, g.dx
c = 1.0
dt = 0.8 * dx / c                      # CFL = 0.8
steps = 250
u0 = datasets.gaussian(x, 0.25, 0.05)
U = solvers.solve_transport(u0, c, dx, dt, steps, scheme="upwind")
ax = plotting.plot_field_snapshots(x, U, [0, 80, 160, 250], dt=dt,
                                   title="transport: waveform moves right at speed c")
plt.show()
"""),
        md(r"""
## 5. 熱方程式 — でこぼこをならす

$\partial_t u = \alpha\,\partial_{xx} u$。二階微分(曲がり方)が正(谷)の点は温まり、負(山)の点は冷める。
結果として **鋭い構造は急速に消え、場はなめらかに** なります。段差の初期条件で確認します。
"""),
        code("""
import numpy as np

# Heat: sharp features vanish fast; the field relaxes toward smooth.
g = grids.Grid1D(0.0, 1.0, 201)
x, dx = g.x, g.dx
alpha = 1.0
dt = 0.4 * dx**2 / alpha
steps = 1500
U = solvers.solve_heat_explicit(datasets.step(x, 0.5, 1.0, 0.0), alpha, dx, dt, steps)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4))
plotting.plot_field_snapshots(x, U, [0, 100, 500, 1500], dt=dt, ax=a1,
                              title="heat: a step diffuses into a smooth ramp")
t = np.arange(U.shape[0]) * dt
plotting.space_time_heatmap(U, x, t, ax=a2, title="u(x, t)")
fig.tight_layout()
plt.show()
"""),
        md(r"""
**アニメーション**(Play で再生、静的 HTML でも動く):段差がなめらかに均されていく様子を時間発展で。
"""),
        code("""
import plotly.io as pio
from pde_book import interactive

pio.renderers.default = "plotly_mimetype+notebook_connected"
gA = grids.Grid1D(0.0, 1.0, 101)
xA, dxA = gA.x, gA.dx
UA = solvers.solve_heat_explicit(datasets.bump(xA, 0.5, 0.15), 1.0, dxA, 0.4 * dxA**2, 300)
interactive.plotly_field_evolution(xA, UA, step=6, dt=0.4 * dxA**2,
                                   title="heat equation: press Play to watch a bump diffuse").show()
"""),
        md(r"""
### 拡散と伝播の違い

- **熱(拡散)**: 情報は **瞬時に** 全体へにじむ(無限の伝播速度)。エネルギーは散逸し、時間反転できない。
- **移流・波動(伝播)**: 情報は **有限速度** $c$ で運ばれる。形(エネルギー)は保たれ、時間反転できる。
"""),
        md(r"""
## 7. 波動方程式 — 弦をはじく (Applied)

$\partial_{tt} u = c^2 \partial_{xx} u$。弦の各点の加速度が曲がり方に比例。初期変位を与えて手を離すと、
波が **左右に分かれて伝播** し、端で反射します。両端固定(Dirichlet)の弦をはじきます。
"""),
        code("""
import numpy as np

# Wave: a plucked string splits into left/right travelling waves and reflects.
g = grids.Grid1D(0.0, 1.0, 401)
x, dx = g.x, g.dx
c = 1.0
dt = 0.8 * dx / c
steps = 400
u0 = datasets.gaussian(x, 0.5, 0.04)   # initial pluck
v0 = np.zeros_like(x)
U = solvers.solve_wave(u0, v0, c, dx, dt, steps)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4))
plotting.plot_field_snapshots(x, U, [0, 80, 160, 320], dt=dt, ax=a1,
                              title="wave: pluck splits into two travelling pulses")
t = np.arange(U.shape[0]) * dt
plotting.space_time_heatmap(U, x, t, ax=a2, cmap="seismic", title="u(x, t): X-shaped characteristics")
fig.tight_layout()
plt.show()
"""),
        md(r"""
**アニメーション**(matplotlib の `line_animation` ヘルパ→ `to_jshtml` で HTML 埋め込み):
弾いた波が左右に分裂し、端で反射して戻ってくる様子。
"""),
        code("""
from IPython.display import HTML

# Matplotlib animation embedded as self-contained HTML (works offline in the book).
# Subsampled to keep the embedded frames light.
anim = plotting.line_animation(x, U[::13], interval=80,
                               title="wave: a pluck splits and reflects (matplotlib)")
HTML(anim.to_jshtml())
"""),
        md(r"""
時空間ヒートマップの **X 字** は、波が速度 $\pm c$ の **特性線** $x \pm ct = \text{const}$ に沿って伝わることを示します。

## Exercises

1. 移流方程式で $c<0$(左へ流れる)場合に upwind の風上側が変わることを確認し、解いてみよ。
2. 熱方程式で初期条件をガウス分布にすると、解が「広がるガウス分布」になることを数値で確かめよ。
3. 波動方程式で初期速度 $v_0 \ne 0$(たたく)場合と初期変位(はじく)場合の違いを比べよ。

## Advanced Notes

- **d'Alembert の公式**: 1 次元波動の一般解は $u(x,t) = \tfrac12[u_0(x-ct)+u_0(x+ct)] + \tfrac{1}{2c}\int_{x-ct}^{x+ct} v_0$。
- **熱核**: 熱方程式の基本解は正規分布 $\frac{1}{\sqrt{4\pi\alpha t}}e^{-x^2/4\alpha t}$。畳み込みで一般の初期条件の解が書ける。
- **数値拡散**: upwind は一次精度で、移流を解くと余分な拡散(波形のなまり)が入る。高次スキーム(Lax-Wendroff 等)で軽減できる(06 章)。
"""),
    ]
    _save("02_transport_heat_wave.ipynb", cells)


# --------------------------------------------------------------------------- #
def laplace_poisson():
    cells = [
        md(r"""
# 03. Laplace・Poisson — 境界値問題と調和関数

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture 〜 4. Visualization |
| Applied | 5. Poisson 〜 6. 平均値性 |
| Advanced | 11. Advanced Notes |

## 1. Big Picture

時間を含まない **定常(平衡)** の世界です。

$$
\nabla^2 u = 0 \quad(\text{Laplace}) \qquad\qquad \nabla^2 u = f \quad(\text{Poisson})
$$

熱方程式を「時間が十分経って $\partial_t u = 0$」とした極限が Laplace 方程式。
内部に湧き出し $f$(熱源・電荷)があれば Poisson。解は **境界の値だけで決まり**、内部はそれを最も滑らかに補間します。
"""),
        md(r"""
## 2. Problem / 3. Intuition — 境界条件

- **Dirichlet 条件**: 縁での **値** を指定(縁の温度・電位を固定)。
- **Neumann 条件**: 縁での **法線方向の傾き** を指定(断熱 = 流出なし、など)。

直感: 縁の温度を固定した金属板を放置すると、内部の温度分布は Laplace 方程式の解(定常状態)に落ち着きます。
"""),
        setup_cell("pde_book"),
        IMPORT,
        md(r"""
## 4. Visualization — 熱い縁を持つ板の定常温度 (Laplace)

正方形の板の上辺だけを高温($u=1$)、他の三辺を $0$ に固定。内部の定常温度分布 $\nabla^2 u = 0$ を解きます。
等高線(等温線)が滑らかに分布し、**内部に極大・極小がない**(最大値原理)ことに注目。
"""),
        code("""
import numpy as np

# Steady temperature of a plate: top edge hot, others cold. Solve Laplace (rhs=0).
g = grids.Grid2D(0.0, 1.0, 0.0, 1.0, 61, 61)
boundary = datasets.hot_edge_boundary(g, value=1.0)
u = solvers.solve_poisson_2d(np.zeros((g.ny, g.nx)), g, boundary)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8))
plotting.heatmap_2d(u, grid=g, ax=a1, title="steady temperature (Laplace), hot top edge")
X, Y = g.meshgrid()
plotting.surface_2d(X, Y, u, ax=None)  # separate 3-D figure
cs = a2.contour(X, Y, u, levels=12, cmap="viridis")
a2.set_aspect("equal")
a2.set_title("isotherms: smooth, no interior extremum")
a2.set_xlabel("x")
a2.set_ylabel("y")
plt.show()
"""),
        md(r"""
## 5. Poisson 方程式 — 湧き出しがある場合 (Applied)

$\nabla^2 u = f$。$f$ は熱源(または電荷密度)。中央に点状の源(湧き出し)を置くと、
そこを頂点に場が盛り上がります。境界は $0$(接地)に固定します。
"""),
        code("""
import numpy as np

# Poisson with a localized source in the middle (boundary grounded at 0).
g = grids.Grid2D(0.0, 1.0, 0.0, 1.0, 61, 61)
X, Y = g.meshgrid()
f = -50.0 * np.exp(-((X - 0.5) ** 2 + (Y - 0.5) ** 2) / 0.005)   # source term
u = solvers.solve_poisson_2d(f, g, boundary=np.zeros((g.ny, g.nx)))
ax = plotting.surface_2d(X, Y, u, title="Poisson: a central source lifts the field")
plt.show()
print("peak response at center:", round(float(u[g.ny // 2, g.nx // 2]), 4))
"""),
        md(r"""
## 6. 調和関数の直感 — 平均値性

Laplace 方程式の解(**調和関数**)には美しい性質があります: **各点の値は、その周りの平均に等しい**
(平均値性)。離散版では「各内部点 = 上下左右の隣の平均」。最初の板の解で数値的に確かめます。
"""),
        code("""
import numpy as np

# Mean-value property (discrete): interior value == average of its 4 neighbours.
g = grids.Grid2D(0.0, 1.0, 0.0, 1.0, 61, 61)
u = solvers.solve_poisson_2d(np.zeros((g.ny, g.nx)), g, datasets.hot_edge_boundary(g, 1.0))
nbr_avg = 0.25 * (u[2:, 1:-1] + u[:-2, 1:-1] + u[1:-1, 2:] + u[1:-1, :-2])
residual = np.max(np.abs(u[1:-1, 1:-1] - nbr_avg))
print("max |u_center - mean(4 neighbours)| =", residual, "(~0 confirms harmonicity)")
"""),
        md(r"""
## Exercises

1. 4 辺すべて異なる温度に固定し、定常分布を解いて等温線を描け。
2. Poisson 方程式で源 $f$ の符号を反転すると、場が凹む(谷になる)ことを確かめよ。
3. 線形関数 $u = ax + by + c$ が調和($\nabla^2 u = 0$)であることを示し、数値解と一致させよ。

## Advanced Notes

- **最大値原理**: 調和関数は領域内部で最大・最小を取らない(必ず境界で取る)。だから板の内部温度は縁の温度の範囲に収まる。
- **平均値性 ⇔ 調和性**: 連続版では「任意の球面平均 = 中心値」が調和性と同値。
- **Green 関数**: Poisson 方程式の解は $u = \int G(x, x') f(x')\,dx'$。点源応答 $G$ を重ね合わせれば任意の源に対応できる。
- **Neumann と適合条件**: 全周 Neumann では、源の総量と境界流量が釣り合わないと定常解が存在しない(解は定数分だけ不定)。
"""),
    ]
    _save("03_laplace_poisson_boundary_value.ipynb", cells)


# --------------------------------------------------------------------------- #
def fourier():
    cells = [
        md(r"""
# 04. Fourier 級数と変換 — 関数を波に分解する

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture 〜 4. Visualization |
| Applied | 5. 周波数 〜 6. 熱方程式との接続 |
| Advanced | 11. Advanced Notes |

## 1. Big Picture

**Fourier の考え**: どんな関数も、**いろいろな振動数の正弦波(サイン・コサイン)の重ね合わせ** で表せる。

$$
f(x) = \sum_{k} \big(a_k \cos kx + b_k \sin kx\big)
$$

これが PDE で決定的に効きます。なぜなら正弦波は熱方程式・波動方程式の **固有関数** で、
個々の波の時間発展が簡単に書けるからです(05 章へ)。
"""),
        setup_cell("pde_book"),
        IMPORT,
        md(r"""
## 4. Visualization — 矩形波を波で組み立てる

不連続な **矩形波** でさえ、サイン波の和で近似できます。項数を増やすほど近似が改善しますが、
跳びの近くでは行き過ぎ(**Gibbs 現象**)が残ります。
"""),
        code("""
import numpy as np

# Build a square wave from sine terms; more terms -> better fit (but Gibbs overshoot at jumps).
x = np.linspace(0, 2 * np.pi, 1000)
target = np.where((x % (2 * np.pi)) < np.pi, 1.0, -1.0)
fig, ax = plt.subplots(figsize=(7.5, 4))
ax.plot(x, target, "k--", lw=1, label="square wave")
for n in (1, 3, 9, 40):
    ax.plot(x, solvers.square_wave_partial_sum(x, n, L=np.pi), lw=1.5, label=f"{n} terms")
ax.legend(fontsize=8)
ax.grid(alpha=0.25)
ax.set_title("Fourier partial sums of a square wave (Gibbs overshoot near jumps)")
plt.show()
"""),
        md(r"""
### インタラクティブ: 項数を動かす(静的 HTML でも動く)

スライダーで項数を増やすと近似が改善し、跳びの近くに **Gibbs の行き過ぎ** が残る様子が見えます
(Plotly なのでエクスポート HTML でも動作)。
"""),
        code("""
import plotly.io as pio
from pde_book import interactive

pio.renderers.default = "plotly_mimetype+notebook_connected"
fig = interactive.plotly_fourier_square()
fig.show()
"""),
        md(r"""
## 5. 周波数 — 低周波と高周波 (Applied)

各サイン波の「振動数(周波数)」が、信号のどの成分を担うかを表します。
複数の周波数を混ぜた信号を作り、**FFT(高速 Fourier 変換)** で周波数成分を取り出します。
スパイクが立つ位置が、混ぜた周波数です。
"""),
        code("""
import numpy as np

# A signal = sum of a few pure tones; the FFT recovers their frequencies.
fs = 500                                  # samples per unit
x = np.arange(0, 2, 1 / fs)
freqs = [3, 12, 27]
amps = [1.0, 0.5, 0.3]
signal = sum(a * np.sin(2 * np.pi * f * x) for f, a in zip(freqs, amps))

spectrum = np.abs(np.fft.rfft(signal)) / (len(x) / 2)
freq_axis = np.fft.rfftfreq(len(x), 1 / fs)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4))
a1.plot(x[:200], signal[:200], color="#1f77b4")
a1.set_title("signal (3 tones mixed)")
a1.set_xlabel("x")
a1.grid(alpha=0.25)
a2.stem(freq_axis[:60], spectrum[:60])
a2.set_title("amplitude spectrum: peaks at 3, 12, 27")
a2.set_xlabel("frequency")
a2.grid(alpha=0.25)
fig.tight_layout()
plt.show()
"""),
        md(r"""
## 6. 熱方程式との接続 — 高周波は速く消える

熱方程式は、各 Fourier モード $\sin(kx)$ を **$e^{-\alpha k^2 t}$ で減衰** させます。
$k$(周波数)が大きいほど減衰が速い——だから熱方程式は **高周波(細かいでこぼこ)から先に消す** = 平滑化。
低周波 + 高周波を混ぜた初期条件を熱方程式で時間発展させ、高周波が先に消えることを見ます。
"""),
        code("""
import numpy as np

# Heat kills high modes first: mode k decays like e^{-alpha k^2 t}.
g = grids.Grid1D(0.0, 1.0, 201)
x, dx = g.x, g.dx
alpha = 1.0
u0 = datasets.sine_combo(x, modes=(1, 8), amps=(1.0, 0.5), L=1.0)  # low + high frequency
dt = 0.4 * dx**2 / alpha
U = solvers.solve_heat_explicit(u0, alpha, dx, dt, steps=800)
ax = plotting.plot_field_snapshots(x, U, [0, 30, 120, 800], dt=dt,
                                   title="heat smoothing: the high (k=8) mode vanishes first")
plt.show()
"""),
        md(r"""
## Exercises

1. 三角波の Fourier 級数を求め、矩形波より速く収束する(Gibbs が穏やか)ことを観察せよ。
2. FFT で、サンプリング周波数の半分(Nyquist)を超える周波数が折り返す(エイリアシング)様子を作れ。
3. 熱方程式で、モード $n=1$ と $n=4$($\sin(n\pi x)$, 固有値 $(n\pi)^2$)の振幅比が
   時間とともに $e^{-\alpha(1-16)\pi^2 t}=e^{15\alpha\pi^2 t}$ で変化することを数値で確かめよ。

## Advanced Notes

- **Fourier 変換**: 非周期関数には級数の代わりに変換 $\hat{f}(\omega)=\int f(x)e^{-i\omega x}dx$ を使う。微分が $i\omega$ 倍に化けるので PDE が代数方程式になる。
- **Parseval の定理**: 信号のエネルギーは時間領域でも周波数領域でも等しい($\int|f|^2 = \frac{1}{2\pi}\int|\hat f|^2$)。
- **Gibbs 現象**: 不連続点での行き過ぎ(約 9%)は項数を増やしても消えない(幅は狭まる)。Fejér 平均などで緩和できる。
- **スペクトル法**: 周期境界の PDE は FFT で空間微分を高精度に評価でき、有限差分より速く正確なことがある。
"""),
    ]
    _save("04_fourier_series_and_transform.ipynb", cells)


# --------------------------------------------------------------------------- #
def separation():
    cells = [
        md(r"""
# 05. 変数分離法 — 固有関数で解く

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture 〜 4. Visualization |
| Applied | 5. 熱の解析解 〜 6. 波動の解析解 |
| Advanced | 11. Advanced Notes |

## 1. Big Picture

**変数分離法** は、解を空間部分と時間部分の積

$$
u(x, t) = X(x)\,T(t)
$$

と仮定して PDE を 2 つの ODE に分解する手法です。境界条件が空間部分 $X(x)$ の許される形(**固有関数**)を選び、
時間部分 $T(t)$ がその時間発展を決めます。Fourier(04 章)はこの「固有関数で展開する」ことそのものです。
"""),
        md(r"""
## 2. Intuition / 3. Definition — 境界条件が固有関数を選ぶ

両端固定($u(0)=u(L)=0$)の棒や弦では、許される空間モードは

$$
X_n(x) = \sin\!\Big(\frac{n\pi x}{L}\Big), \qquad n = 1, 2, 3, \dots
$$

だけ(端でゼロになる正弦波)。これは行列の固有ベクトルの連続版で、$-\partial_{xx}$ という演算子の **固有関数** です。
固有値は $\lambda_n = (n\pi/L)^2$。
"""),
        setup_cell("pde_book"),
        IMPORT,
        md(r"""
## 4. Visualization — 固有関数(モード)
"""),
        code("""
import numpy as np

# The first few Dirichlet eigenfunctions sin(n pi x / L) on [0, 1].
g = grids.Grid1D(0.0, 1.0, 200)
x = g.x
fig, ax = plt.subplots(figsize=(7, 4))
for n in (1, 2, 3, 4):
    ax.plot(x, datasets.sine_mode(x, mode=n, L=1.0), lw=2, label=f"n={n}")
ax.axhline(0, color="gray", lw=0.6)
ax.legend()
ax.grid(alpha=0.25)
ax.set_title("eigenfunctions of -d^2/dx^2 with u(0)=u(1)=0")
plt.show()
"""),
        md(r"""
## 5. 熱方程式の解析解 (Applied)

熱方程式に変数分離を入れると、モード $n$ の時間部分は $T_n(t) = e^{-\alpha(n\pi/L)^2 t}$。
よって初期条件を固有関数で展開すれば、解は

$$
u(x, t) = \sum_n b_n\, e^{-\alpha (n\pi/L)^2 t}\,\sin\!\Big(\frac{n\pi x}{L}\Big)
$$

各モードが独立に減衰するだけ。この **解析解(級数和)** と、有限差分の **数値解** を重ねて一致を確認します。
"""),
        code("""
import numpy as np

# Analytic separation-of-variables series vs the numerical solver, for a 2-mode start.
g = grids.Grid1D(0.0, 1.0, 201)
x, dx = g.x, g.dx
alpha = 1.0
modes, amps = (1, 3), (1.0, 0.5)
u0 = datasets.sine_combo(x, modes, amps, L=1.0)

dt = 0.4 * dx**2 / alpha
steps = 300
U = solvers.solve_heat_explicit(u0, alpha, dx, dt, steps)
t_end = steps * dt
analytic = sum(
    a * np.exp(-alpha * (m * np.pi) ** 2 * t_end) * solvers.heat_mode_solution(x, 0, alpha, 1, m)
    for m, a in zip(modes, amps)
)

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(x, u0, "k--", lw=1, label="initial u(x,0)")
ax.plot(x, analytic, color="#1f77b4", lw=3, alpha=0.6, label="analytic series")
ax.plot(x[::8], U[-1][::8], "o", color="#d62728", ms=4, label="numerical FDM")
ax.legend()
ax.grid(alpha=0.25)
ax.set_title(f"heat at t={t_end:.4f}: separation-of-variables vs FDM")
plt.show()
print("max |analytic - numerical| =", float(np.max(np.abs(analytic - U[-1]))))
"""),
        md(r"""
## 6. 波動方程式の解析解

同じ分解を波動方程式に行うと、時間部分は減衰せず **振動** します: $T_n(t) = \cos(n\pi c\,t/L)$。

$$
u(x, t) = \sum_n b_n \cos\!\Big(\frac{n\pi c t}{L}\Big)\sin\!\Big(\frac{n\pi x}{L}\Big)
$$

各モードが固有振動数 $n\pi c/L$ で振動——これが弦の **倍音(harmonics)** です。
単一モードの数値解が解析解 $\sin(n\pi x)\cos(n\pi c t)$ と一致することを見ます。
"""),
        code("""
import numpy as np

# Wave: a single standing mode oscillates; numeric matches the analytic cos in time.
g = grids.Grid1D(0.0, 1.0, 301)
x, dx = g.x, g.dx
c, mode = 1.0, 2
dt = 0.8 * dx / c
steps = 120
u0 = solvers.wave_mode_solution(x, 0.0, c, L=1.0, mode=mode)
U = solvers.solve_wave(u0, np.zeros_like(x), c, dx, dt, steps)
t_end = steps * dt
analytic = solvers.wave_mode_solution(x, t_end, c, L=1.0, mode=mode)
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(x, u0, "k--", lw=1, label="initial (mode n=2)")
ax.plot(x, analytic, color="#1f77b4", lw=3, alpha=0.6, label="analytic")
ax.plot(x[::10], U[-1][::10], "o", color="#d62728", ms=4, label="numerical")
ax.legend()
ax.grid(alpha=0.25)
ax.set_title(f"standing wave mode n=2 at t={t_end:.3f}")
plt.show()
"""),
        md(r"""
## 7. 線形代数との接続

固有関数 $\sin(n\pi x/L)$ は演算子 $-\partial_{xx}$ の固有ベクトル、$\lambda_n=(n\pi/L)^2$ は固有値です。
これは行列の対角化と同じ構造:**演算子を固有基底で見ると、各モードが独立に簡単な ODE になる**。
線形代数(固有値分解)と Fourier(波への分解)と PDE(変数分離)は、同じ一つの考えの別の顔です。

## Exercises

1. Neumann 条件($u_x(0)=u_x(L)=0$, 断熱端)では固有関数が $\cos(n\pi x/L)$ になることを示せ。
2. 熱方程式で初期条件を 3 モード混合にし、最後に残るのが最低次モードであることを級数解で確かめよ。
3. 弦の基本振動数 $\pi c/L$ を導き、弦を短く($L$ 小)すると音が高くなることを説明せよ。

## Advanced Notes

- **Sturm-Liouville 理論**: 一般の境界条件下でも、固有関数は直交完全系を成す。これが「展開できる」ことの保証。
- **直交性**: $\int_0^L \sin(n\pi x/L)\sin(m\pi x/L)\,dx = 0\ (n\ne m)$。係数 $b_n$ は内積(投影)で決まる。
- **非斉次・非分離**: 係数が場所に依る、または領域が長方形でない場合、変数分離は使えず数値解(06 章)に頼る。
"""),
    ]
    _save("05_separation_of_variables.ipynb", cells)


# --------------------------------------------------------------------------- #
def numerical_pde():
    cells = [
        md(r"""
# 06. 有限差分法 — グリッド・安定性・CFL・数値拡散

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture 〜 3. グリッド |
| Applied | 4. 安定性 〜 7. 陰解法 |
| Advanced | 11. Advanced Notes |

## 1. Big Picture

解析解が無い PDE は **有限差分法 (FDM)** で解きます。空間を格子に切り、微分を差分で置き換える。

$$
\frac{\partial^2 u}{\partial x^2}\Big|_i \approx \frac{u_{i+1} - 2u_i + u_{i-1}}{\Delta x^2}
$$

本章の最重要メッセージ:

> **数値解は、刻み幅 $\Delta x$ と時間ステップ $\Delta t$ を間違えると壊れる。**
"""),
        setup_cell("pde_book"),
        IMPORT,
        md(r"""
## 3. グリッドと差分

格子点の上で場を表し、隣との差で微分を近似します。`grids` モジュールが格子と
安定性数(拡散数 $r$、CFL 数 $C$)を提供します。
"""),
        code("""
# Grids and the dimensionless numbers that govern explicit stability.
g = grids.Grid1D(0.0, 1.0, 11)
print("x =", g.x)
print("dx =", g.dx)
print("heat number r for (alpha=1, dt=0.004, dx=0.1):",
      grids.heat_number(1.0, 0.004, 0.1), "-> stable?", grids.heat_stable(1.0, 0.004, 0.1))
print("CFL number C for (c=1, dt=0.2, dx=0.1):",
      grids.courant_number(1.0, 0.2, 0.1), "-> ok?", grids.cfl_ok(1.0, 0.2, 0.1))
"""),
        md(r"""
## 4. 安定性 — 熱方程式の陽解法は $r \le 1/2$ (Applied)

陽的 FTCS 法は、拡散数 $r = \alpha\,\Delta t/\Delta x^2$ が $1/2$ を超えると **発散** します。
同じ初期条件・同じ最終時刻でも、$\Delta t$ を少し変えるだけで結果が天国と地獄です。
"""),
        code("""
import numpy as np

# Heat FTCS: r <= 1/2 smooths nicely; r > 1/2 explodes into sawtooth oscillations.
g = grids.Grid1D(0.0, 1.0, 81)
x, dx = g.x, g.dx
alpha = 1.0
u0 = datasets.bump(x, 0.5, 0.12)
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for ax, r in zip(axes, (0.4, 0.55)):
    dt = r * dx**2 / alpha
    U = solvers.solve_heat_explicit(u0, alpha, dx, dt, steps=120)
    ax.plot(x, U[0], "k--", lw=1, label="initial")
    ax.plot(x, U[-1], color="#d62728", lw=1.5, label=f"final (r={r})")
    ax.set_title(f"r = {r}  ->  {'STABLE' if r <= 0.5 else 'UNSTABLE'}")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
fig.tight_layout()
plt.show()
"""),
        md(r"""
## 5. CFL 条件 — 移流・波動は $C \le 1$

双曲型(移流・波動)では **CFL 条件** $C = c\,\Delta t/\Delta x \le 1$ が安定の鍵。
直感: **1 ステップで波が 1 格子以上進んではいけない**(情報の伝播速度を数値が追い越せない)。
"""),
        code("""
import numpy as np

# Advection upwind: CFL <= 1 transports cleanly; CFL > 1 blows up.
g = grids.Grid1D(0.0, 1.0, 201)
x, dx = g.x, g.dx
c = 1.0
u0 = datasets.gaussian(x, 0.3, 0.05)
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for ax, C in zip(axes, (0.9, 1.05)):
    dt = C * dx / c
    steps = int(0.3 / dt)
    U = solvers.solve_transport(u0, c, dx, dt, steps, scheme="upwind")
    ax.plot(x, U[0], "k--", lw=1, label="initial")
    ax.plot(x, U[-1], color="#d62728", lw=1.5, label=f"final (C={C})")
    ax.set_ylim(-0.5, 1.5)
    ax.set_title(f"CFL C = {C}  ->  {'OK' if C <= 1 else 'UNSTABLE'}")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
fig.tight_layout()
plt.show()
"""),
        md(r"""
### インタラクティブ: 安定数を動かして「壊れる瞬間」を見る(静的 HTML でも動く)

Plotly のスライダーで、熱方程式の拡散数 $r$ と移流の CFL 数 $C$ を動かします。
それぞれ $r>1/2$、$C>1$ を超えた瞬間に数値解が崩れる(振動・発散)ことを体感してください。
"""),
        code("""
import plotly.io as pio
from pde_book import interactive

pio.renderers.default = "plotly_mimetype+notebook_connected"
interactive.plotly_heat_stability().show()      # heat: stable iff r <= 1/2
"""),
        code("""
interactive.plotly_cfl_transport().show()        # advection: stable iff CFL C <= 1
"""),
        md(r"""
## 6. 数値拡散 — 安定でも「なまる」

風上差分は安定ですが、一次精度ゆえに余分な **数値拡散** が入り、移流させると波形がだんだん **なまり**ます
(本来は形が保たれるはず)。格子を細かくすると軽減します。
"""),
        code("""
import numpy as np

# Numerical diffusion: upwind preserves the bump's motion but smears its shape.
c = 1.0
fig, ax = plt.subplots(figsize=(7, 4))
for n in (101, 401):
    g = grids.Grid1D(0.0, 1.0, n)
    x, dx = g.x, g.dx
    dt = 0.9 * dx / c
    steps = int(0.5 / dt)
    u0 = datasets.gaussian(x, 0.25, 0.04)
    U = solvers.solve_transport(u0, c, dx, dt, steps, scheme="upwind")
    ax.plot(x, U[-1], lw=2, label=f"nx={n} (dx={dx:.4f})")
ax.plot(g.x, datasets.gaussian(g.x, 0.25 + c * steps * dt, 0.04), "k--", lw=1,
        label="exact (shape preserved)")
ax.legend(fontsize=8)
ax.grid(alpha=0.25)
ax.set_title("numerical diffusion shrinks with finer grids")
plt.show()
"""),
        md(r"""
## 7. 陰解法 — 大きな $\Delta t$ でも安定

陰的(後退 Euler)法は連立一次方程式を毎ステップ解く代わりに、**無条件安定**。
熱方程式を $r=5$($\gg 1/2$、陽解法なら即爆発)で解いても破綻しません。
"""),
        code("""
import numpy as np

# Implicit heat is stable even at r = 5 (explicit would explode instantly).
g = grids.Grid1D(0.0, 1.0, 81)
x, dx = g.x, g.dx
alpha = 1.0
dt = 5.0 * dx**2 / alpha
U = solvers.solve_heat_implicit(datasets.sine_combo(x, (1, 4), (1.0, 0.5)), alpha, dx, dt, steps=40)
ax = plotting.plot_field_snapshots(x, U, [0, 5, 15, 40], dt=dt,
                                   title="implicit heat at r=5: stable, smooth decay")
plt.show()
"""),
        md(r"""
## 8. 発展 — Crank-Nicolson・Neumann 境界・非線形 Burgers (Advanced)

3 つの発展ソルバを `solvers` に用意しています。

- **Crank-Nicolson**: 陽と陰の平均。**時間 2 次精度かつ無条件安定**(陽 FTCS の精度と陰の安定性の良いとこ取り)。
- **Neumann 境界**(断熱端 $u_x=0$): 流束 0 の保存形なので **総熱量が厳密保存** し、場は平均へ均される。
- **非線形 Burgers** $u_t + u u_x = \nu u_{xx}$: 移流の非線形性が波形を急峻化して **衝撃** を作り、粘性 $\nu$ が有限に保つ。
"""),
        code("""
import numpy as np

# Crank-Nicolson: 2nd-order in time, unconditionally stable. Here r=5 (FTCS would explode).
g = grids.Grid1D(0.0, 1.0, 81)
x, dx = g.x, g.dx
dt = 5.0 * dx**2
U = solvers.solve_heat_crank_nicolson(datasets.sine_combo(x, (1, 4), (1.0, 0.5)), 1.0, dx, dt, 40)
plotting.plot_field_snapshots(x, U, [0, 3, 10, 40], dt=dt,
                              title="Crank-Nicolson heat at r=5 (stable, 2nd-order in time)")
plt.show()
"""),
        code("""
import numpy as np

# Neumann (insulated) ends: total heat is conserved; the field relaxes to its mean.
g = grids.Grid1D(0.0, 1.0, 101)
x, dx = g.x, g.dx
u0 = datasets.gaussian(x, 0.35, 0.07) + 0.2
U = solvers.solve_heat_neumann(u0, 1.0, dx, 0.4 * dx**2, 3000)
ax = plotting.plot_field_snapshots(x, U, [0, 50, 300, 3000], dt=0.4 * dx**2,
                                   title="insulated (Neumann) ends: relaxes to the mean")
ax.axhline(u0.mean(), color="gray", ls="--", lw=1)
plt.show()
print("total heat  start =", round(float(U[0].sum() * dx), 6),
      " end =", round(float(U[-1].sum() * dx), 6), " (conserved)")
"""),
        code("""
import numpy as np

# Burgers: a smooth sine steepens into a shock; viscosity keeps it finite.
g = grids.Grid1D(0.0, 1.0, 201)
x, dx = g.x, g.dx
nu, dt = 2e-3, 0.002
U = solvers.solve_burgers(np.sin(2 * np.pi * x), nu, dx, dt, 150)
plotting.plot_field_snapshots(x, U, [0, 40, 90, 150], dt=dt,
                              title="viscous Burgers: nonlinear steepening into a shock")
plt.show()
print("momentum  start =", round(float(U[0].sum() * dx), 8),
      " end =", round(float(U[-1].sum() * dx), 8), " (conserved)")
"""),
        md(r"""
## Exercises

1. 熱方程式の安定限界 $r \le 1/2$ を、モード $\sin(kx)$ の増幅率 $1 - 4r\sin^2(k\Delta x/2)$ から導け。
2. CFL を 1 ちょうどにすると upwind が**数値拡散ゼロ**で正確に移流すること(偶然の一致)を確かめよ。
3. 陰解法の 1 ステップが三重対角系を解くことを確認し、`scipy` の `splu` がそれを高速化することを述べよ。

## Advanced Notes

- **von Neumann 安定性解析**: 解を $u_j^n = \xi^n e^{ikj\Delta x}$ と置き、増幅率 $|\xi|\le 1$ を要求する標準手法。
- **Lax の同値定理**: 適切な問題では「整合性 + 安定性 ⇔ 収束」。だから安定性が死活的。
- **Crank-Nicolson 法**: 陽と陰の中間(時間 2 次精度)で無条件安定。実務の定番。
- **高解像度スキーム**: 移流の数値拡散を抑えつつ振動を防ぐ TVD / WENO などがある。
"""),
    ]
    _save("06_numerical_pde_fdm.ipynb", cells)


# --------------------------------------------------------------------------- #
def applications():
    cells = [
        md(r"""
# 07. 応用 — 物理・金融(Black-Scholes)・画像・拡散モデル

| 層 | セクション |
|---|---|
| Basic | 1. Big Picture |
| Applied | 2. 物理 〜 5. 拡散モデル |
| Advanced | 11. Advanced Notes |

## 1. Big Picture

PDE は分野を越えた共通言語です。**同じ熱方程式** が、物理の熱伝導・金融の Black-Scholes・
画像の平滑化・生成 AI の拡散モデルに現れます。本章でその姿を確かめます。
"""),
        setup_cell("pde_book"),
        IMPORT,
        md(r"""
## 2. 物理 — 2 次元の熱伝導

これまでの 1 次元を 2 次元に拡張します。中央を熱したプレートの温度が、時間とともに
全体へ拡散していく様子を陽的 FDM(2 次元)で解きます。
"""),
        code("""
import numpy as np

# 2-D heat diffusion of a hot square on a cold plate (explicit, periodic-free Dirichlet 0).
n = 81
g = grids.Grid2D(0.0, 1.0, 0.0, 1.0, n, n)
dx = g.dx
alpha = 1.0
dt = 0.2 * dx**2 / alpha       # 2-D stability needs r <= 1/4; use 0.2 to be safe
u = np.zeros((n, n))
u[n // 3:2 * n // 3, n // 3:2 * n // 3] = 1.0   # hot square
snaps = {0: u.copy()}
for k in range(1, 1201):
    lap = (np.roll(u, 1, 0) + np.roll(u, -1, 0) + np.roll(u, 1, 1) + np.roll(u, -1, 1) - 4 * u)
    u = u + alpha * dt / dx**2 * lap
    u[0, :] = u[-1, :] = u[:, 0] = u[:, -1] = 0.0
    if k in (60, 300, 1200):
        snaps[k] = u.copy()
fig, axes = plt.subplots(1, 4, figsize=(15, 3.6))
for ax, (k, snap) in zip(axes, snaps.items()):
    plotting.heatmap_2d(snap, grid=g, ax=ax, title=f"step {k}")
fig.tight_layout()
plt.show()
"""),
        md(r"""
**アニメーション**(Play で再生):中央の熱い正方形が、時間とともに板全体へ拡散していく様子。
"""),
        code("""
from matplotlib import animation
from IPython.display import HTML

# 2-D heat diffusion as a movie (matplotlib imshow -> to_jshtml; works offline in the book).
na = 81
ga = grids.Grid2D(0.0, 1.0, 0.0, 1.0, na, na)
dxa = ga.dx
ua = np.zeros((na, na))
ua[na // 3:2 * na // 3, na // 3:2 * na // 3] = 1.0
frames2d = [ua.copy()]
for k in range(1, 601):
    lapa = np.roll(ua, 1, 0) + np.roll(ua, -1, 0) + np.roll(ua, 1, 1) + np.roll(ua, -1, 1) - 4 * ua
    ua = ua + 0.2 * lapa
    ua[0, :] = ua[-1, :] = ua[:, 0] = ua[:, -1] = 0.0
    if k % 30 == 0:
        frames2d.append(ua.copy())
figa, axa = plt.subplots(figsize=(4.5, 4))
ima = axa.imshow(frames2d[0], origin="lower", cmap="inferno", vmin=0, vmax=1)
axa.set_title("2-D heat diffusion")
axa.set_xticks([])
axa.set_yticks([])
anim2d = animation.FuncAnimation(figa, lambda i: (ima.set_data(frames2d[i]), (ima,))[1],
                                 frames=len(frames2d), interval=150, blit=True)
plt.close(figa)
HTML(anim2d.to_jshtml())
"""),
        md(r"""
## 3. 金融 — Black-Scholes 方程式 (Applied)

オプション価格 $V(S, t)$ は **Black-Scholes 方程式**

$$
\frac{\partial V}{\partial t} + \tfrac12\sigma^2 S^2 \frac{\partial^2 V}{\partial S^2} + rS\frac{\partial V}{\partial S} - rV = 0
$$

に従います。これは(変数変換すると)**熱方程式そのもの**。ヨーロピアン・コールには閉じた解(Black-Scholes 公式)があり、
ここでは解析解で価格曲面を描き、さらに **その曲面が PDE を満たす**(残差 ≈ 0)ことを数値微分で検証します。
"""),
        code("""
import numpy as np
from scipy.stats import norm

# Black-Scholes European call price surface (closed form).
def bs_call(S, t, K=1.0, r=0.05, sigma=0.2, T=1.0):
    tau = np.maximum(T - t, 1e-12)             # time to maturity
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * tau) / (sigma * np.sqrt(tau))
    d2 = d1 - sigma * np.sqrt(tau)
    return S * norm.cdf(d1) - K * np.exp(-r * tau) * norm.cdf(d2)

S = np.linspace(0.2, 2.0, 120)
tt = np.linspace(0.0, 0.95, 80)
SS, TT = np.meshgrid(S, tt)
V = bs_call(SS, TT)

fig = plt.figure(figsize=(12, 4.5))
ax1 = fig.add_subplot(1, 2, 1, projection="3d")
ax1.plot_surface(SS, TT, V, cmap="viridis")
ax1.set_xlabel("S (price)")
ax1.set_ylabel("t")
ax1.set_zlabel("V")
ax1.set_title("Black-Scholes call price surface")
ax2 = fig.add_subplot(1, 2, 2)
for t0 in (0.0, 0.5, 0.9):
    ax2.plot(S, bs_call(S, t0), label=f"t={t0}")
ax2.plot(S, np.maximum(S - 1.0, 0), "k--", lw=1, label="payoff at expiry")
ax2.legend()
ax2.grid(alpha=0.25)
ax2.set_xlabel("S")
ax2.set_title("call value vs price at several times")
fig.tight_layout()
plt.show()
"""),
        md(r"""
**インタラクティブ版**(ドラッグで回転・ズーム、静的 HTML でも動く):
"""),
        code("""
import plotly.io as pio
from pde_book import interactive

pio.renderers.default = "plotly_mimetype+notebook_connected"
interactive.plotly_bs_surface().show()
"""),
        code("""
import numpy as np
from scipy.stats import norm

# Verify the analytic surface satisfies the Black-Scholes PDE: residual ~ 0.
K, r, sigma, T = 1.0, 0.05, 0.2, 1.0
def bs_call(S, t):
    tau = max(T - t, 1e-9)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * tau) / (sigma * np.sqrt(tau))
    d2 = d1 - sigma * np.sqrt(tau)
    return S * norm.cdf(d1) - K * np.exp(-r * tau) * norm.cdf(d2)

S0, t0, h, dtau = 1.1, 0.4, 1e-4, 1e-5
V_t = (bs_call(S0, t0 + dtau) - bs_call(S0, t0 - dtau)) / (2 * dtau)
V_S = (bs_call(S0 + h, t0) - bs_call(S0 - h, t0)) / (2 * h)
V_SS = (bs_call(S0 + h, t0) - 2 * bs_call(S0, t0) + bs_call(S0 - h, t0)) / h**2
residual = V_t + 0.5 * sigma**2 * S0**2 * V_SS + r * S0 * V_S - r * bs_call(S0, t0)
print("Black-Scholes PDE residual at (S=1.1, t=0.4):", residual, " (~0 confirms it solves the PDE)")
"""),
        md(r"""
## 4. 画像処理 — 拡散による平滑化

2 次元の熱方程式を画像に適用すると、**ノイズや細部がぼけて** いきます(ガウシアンぼかしと同等)。
これは画像処理の基礎で、エッジ保存拡散(異方性拡散)などへ発展します。
"""),
        code("""
import numpy as np

# Image diffusion = 2-D heat equation. Noise blurs away as "time" advances.
img = datasets.make_test_image(96, seed=0)
u = img.copy()
r = 0.2  # diffusion number per step (<=1/4 for 2-D stability)
snaps = {0: u.copy()}
for k in range(1, 61):
    lap = (np.roll(u, 1, 0) + np.roll(u, -1, 0) + np.roll(u, 1, 1) + np.roll(u, -1, 1) - 4 * u)
    u = u + r * lap
    if k in (5, 20, 60):
        snaps[k] = u.copy()
fig, axes = plt.subplots(1, 4, figsize=(15, 3.8))
for ax, (k, snap) in zip(axes, snaps.items()):
    ax.imshow(snap, cmap="gray", vmin=0, vmax=1)
    ax.set_title(f"after {k} diffusion steps")
    ax.axis("off")
fig.tight_layout()
plt.show()
"""),
        md(r"""
## 5. 機械学習 — 拡散モデルとの概念的接続

生成 AI の **拡散モデル(diffusion models)** は、データに少しずつノイズを加えて壊す **前向き過程**
(熱方程式のように構造を拡散・破壊)と、それを逆にたどってノイズからデータを復元する **逆過程** から成ります。
ここでは 1 次元信号で「前向き = 拡散でなまる」過程だけを示します(逆過程の学習は本書の範囲外)。
"""),
        code("""
import numpy as np

# Forward (noising/diffusing) process intuition: structure is progressively destroyed.
g = grids.Grid1D(0.0, 1.0, 201)
x, dx = g.x, g.dx
rng = np.random.default_rng(0)
signal = datasets.sine_combo(x, (1, 3, 6), (1.0, 0.5, 0.3))
u = signal + 0.0
alpha, dt = 1.0, 0.4 * dx**2
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(x, signal, "k", lw=2, label="data (t=0)")
for steps, c in [(40, "#1f77b4"), (160, "#9467bd"), (600, "#d62728")]:
    U = solvers.solve_heat_explicit(signal, alpha, dx, dt, steps)
    ax.plot(x, U[-1], color=c, lw=1.5, label=f"diffused, {steps} steps")
ax.legend(fontsize=8)
ax.grid(alpha=0.25)
ax.set_title("forward diffusion destroys structure (diffusion-model intuition)")
plt.show()
"""),
        md(r"""
## Exercises

1. 2 次元熱伝導で安定条件が $r = \alpha\Delta t/\Delta x^2 \le 1/4$(1 次元の半分)になる理由を述べよ。
2. Black-Scholes 価格曲面の残差を別の $(S, t)$ でも評価し、満期 $t\to T$ 近くで数値誤差が増えることを観察せよ。
3. 画像拡散で、拡散ステップ数とぼけ具合(エッジの鈍り)の関係を調べよ。

## Advanced Notes

- **Black-Scholes ↔ 熱方程式**: 変数変換 $S = K e^{x},\ t = T - 2\tau/\sigma^2$ で BS 方程式は標準熱方程式に化ける。だから数値解も熱方程式の道具がそのまま使える。
- **異方性拡散 (Perona-Malik)**: 拡散係数を勾配の大きさで変え、エッジを保ちながら平坦部だけ平滑化する。
- **スコアベース生成モデル**: 拡散モデルの逆過程は確率微分方程式(SDE)で記述され、スコア関数 $\nabla\log p$ を学習する。PDE(Fokker-Planck)・SDE・最適輸送が交差する最前線。
- **有限要素法 (FEM)**: 複雑形状では差分より有限要素が標準。弱形式 + 基底関数で離散化する。
"""),
    ]
    _save("07_applications_physics_finance_ml.ipynb", cells)


BUILDERS = {
    "01": overview,
    "02": transport_heat_wave,
    "03": laplace_poisson,
    "04": fourier,
    "05": separation,
    "06": numerical_pde,
    "07": applications,
}

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    todo = BUILDERS.keys() if arg == "all" else [arg]
    for key in todo:
        BUILDERS[key]()
