"""Build 08_exercise_solutions.ipynb for either book.

Usage: python build_exercise_solutions_notebook.py {ode|pde}
Worked solutions to the per-chapter Exercises. Chapter 00 (calculus) is shared;
chapters 02..07 are book-specific. Each solution pairs the reasoning (markdown,
math outside Japanese) with a numerical check (code) reusing the book package.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nbkit import code, md, setup_cell, write  # noqa: E402

HERE = Path(__file__).resolve().parent
BOOK_DIR = {"ode": HERE.parent / "ode-book", "pde": HERE.parent / "pde-book"}
PKG = {"ode": "ode_book", "pde": "pde_book"}


def header(book):
    which = "ODE" if book == "ode" else "PDE"
    return md(rf"""
# 08. 演習解答(付録)

本書({which} Book)の各章末 **Exercises** の解答集です。考え方(数式・理由)を述べ、
可能なものは `{PKG[book]}` の関数で数値的に検証します。**まず自力で解いてから**読むことを勧めます。

| 対象 | 章 |
|---|---|
| 00 | 微分積分の基礎(両書共通) |
| 02–07 | {which} 各章 |
""")


def calculus_solutions(pkg):
    """Chapter 00 solutions — identical across both books."""
    return [
        md(r"""
## 00. 微分積分の基礎
"""),
        code(f"from {pkg} import calculus\nimport sympy as sp"),
        md(r"""
**00-1 割線→接線**: $f(x)=x^2$ の差の商は $\dfrac{(2+h)^2-2^2}{h}=4+h \to 4$。$h\to0$ で接線の傾き $f'(2)=4$。
"""),
        code("""
for h in (1.0, 0.5, 0.1, 0.01):
    print(f"h={h:5.2f}  secant slope = {calculus.secant_slope(lambda x: x**2, 2.0, h):.4f}  (= 4 + h)")
"""),
        md(r"""
**00-2 Riemann 和の規則**: midpoint は誤差 $O(\Delta x^2)$、left/right は $O(\Delta x)$。よって midpoint が最速で $1/3$ に収束。
"""),
        code("""
f = lambda x: x**2
for n in (10, 100):
    row = {r: calculus.riemann_sum(f, 0, 1, n, r) for r in ("left", "mid", "right")}
    print(f"n={n:3d}  left={row['left']:.5f}  mid={row['mid']:.5f}  right={row['right']:.5f}  (exact 1/3={1/3:.5f})")
"""),
        md(r"""
**00-3 FTC**: $\int_0^x e^{-t}\,dt = 1-e^{-x}$。累積積分が解析解に一致する。
"""),
        code("""
import numpy as np
xs = np.linspace(0, 3, 400)
F = calculus.cumulative_integral(lambda t: np.exp(-t), xs)
print("max |F - (1 - e^-x)| =", float(np.max(np.abs(F - (1 - np.exp(-xs))))))
"""),
        md(r"""
**00-4 勾配**: $\nabla(\sin x\cos y)=(\cos x\cos y,\,-\sin x\sin y)$。$(\pi/4,\pi/4)$ では $(\tfrac12,-\tfrac12)$。
"""),
        code("""
import numpy as np
f = lambda p: np.sin(p[0]) * np.cos(p[1])
g = calculus.gradient(f, [np.pi / 4, np.pi / 4])
print("numerical grad =", g, " | analytic = (0.5, -0.5)")
"""),
        md(r"""
**00-5 Taylor**: $\ln(1+x)=x-\tfrac{x^2}{2}+\tfrac{x^3}{3}-\tfrac{x^4}{4}+\tfrac{x^5}{5}-\cdots$。$x=0.5$ で 5 次近似の誤差を評価。
"""),
        code("""
import numpy as np
x = sp.symbols("x")
poly = calculus.taylor_series(sp.log(1 + x), x, 0, 5)
print("Taylor(ln(1+x), order 5):", poly)
approx = calculus.taylor_approx(sp.log(1 + x), x, 0, 5)
print("error at x=0.5:", abs(float(approx(0.5)) - np.log(1.5)))
"""),
    ]


# --------------------------------------------------------------------------- #
def ode_solutions():
    pkg = PKG["ode"]
    cells = [header("ode"), *calculus_solutions(pkg)]
    cells += [
        setup_cell(pkg),
        code(f"from {pkg} import systems, solvers\nimport numpy as np"),
        md(r"""
## 02. 一階 ODE

**02-1**: $dy/dt=-ky$ は変数分離で $y=y_0e^{-kt}$。半減期は $y(t_{1/2})=y_0/2 \Rightarrow e^{-kt_{1/2}}=1/2 \Rightarrow t_{1/2}=\ln 2/k$、
$y_0$ に依らない。
"""),
        code("""
k = 0.7
t_half = np.log(2) / k
for y0 in (1.0, 5.0, 100.0):
    print(f"y0={y0:6.1f}  y(t_half)/y0 = {np.exp(-k * t_half):.4f}  (= 1/2 for any y0)")
print("half-life =", t_half, "(independent of y0)")
"""),
        md(r"""
**02-2**: $y'+2y=e^{-t}$。積分因子 $\mu=e^{2t}$ で $(e^{2t}y)'=e^{t}$、よって $y=e^{-t}+Ce^{-2t}$。
"""),
        code("""
import sympy as sp
t = sp.symbols("t")
y = sp.Function("y")
print(sp.dsolve(sp.Eq(y(t).diff(t) + 2 * y(t), sp.exp(-t)), y(t)))
"""),
        md(r"""
**02-3**: ロジスティックで $y_0>K$ から始めると $dy/dt=ry(1-y/K)<0$ なので **上から単調減少** して $K$ に収束。
"""),
        code("""
f = systems.logistic(r=0.9, K=1.0)
t = np.linspace(0, 12, 300)
Y = solvers.rk4(f, [1.7], t)[:, 0]
print("monotone decreasing:", bool(np.all(np.diff(Y) < 0)), "| final ->", round(float(Y[-1]), 4), "(K=1)")
"""),
        md(r"""
**02-4**: $dy/dt=\sqrt{|y|},\,y(0)=0$ は Lipschitz でない。$y\equiv 0$ と $y=(t/2)^2$ がともに解
($\dot y=t/2=\sqrt{(t/2)^2}=\sqrt{y}$)。一意性が破れる。
"""),
        code("""
t = np.linspace(0, 4, 200)
y_a = np.zeros_like(t)
y_b = (t / 2) ** 2
# both satisfy dy/dt = sqrt(|y|)
res_b = np.max(np.abs(np.gradient(y_b, t)[1:-1] - np.sqrt(np.abs(y_b))[1:-1]))
print("y=0 is a solution; y=(t/2)^2 residual ~", round(float(res_b), 4), "-> two solutions from y(0)=0")
"""),
        md(r"""
## 03. 線形 ODE と連立系

**03-1**: $\ddot x+5\dot x+6x=0 \Rightarrow \begin{pmatrix}0&1\\-6&-5\end{pmatrix}$。固有値 $-2,-3$(実・相異・負)→ 振動しない **過減衰**。
"""),
        code("""
A = np.array([[0.0, 1.0], [-6.0, -5.0]])
print("eigenvalues:", np.linalg.eigvals(A), "->", systems.classify_fixed_point(A), "(overdamped: real, distinct, negative)")
"""),
        md(r"""
**03-2**: 無減衰調和振動子のエネルギー $E=\tfrac12(v^2+\omega^2x^2)$。Euler 法は増幅率 $>1$ で **エネルギーが増大**(RK4 はほぼ保存)。
"""),
        code("""
f = systems.harmonic_oscillator(omega=1.0, gamma=0.0)
t = np.linspace(0, 20, 400)
for name, Y in [("Euler", solvers.euler(f, [1.0, 0.0], t)), ("RK4", solvers.rk4(f, [1.0, 0.0], t))]:
    E = 0.5 * (Y[:, 1] ** 2 + Y[:, 0] ** 2)
    print(f"{name:5s}: energy E(0)={E[0]:.3f} -> E(T)={E[-1]:.3f}  (drift {E[-1] - E[0]:+.3f})")
"""),
        md(r"""
**03-3**: $A(\Omega)=F_0/\sqrt{(\omega^2-\Omega^2)^2+(2\gamma\Omega)^2}$。分母 $g(u)=(\omega^2-u)^2+4\gamma^2u$($u=\Omega^2$)を最小化:
$g'(u)=-2(\omega^2-u)+4\gamma^2=0 \Rightarrow u=\omega^2-2\gamma^2$。よって $\Omega^2=\omega^2-2\gamma^2$。
"""),
        code("""
w, g = 1.0, 0.2
Om = np.linspace(0.2, 1.5, 4000)
A = 1.0 / np.sqrt((w**2 - Om**2) ** 2 + (2 * g * Om) ** 2)
print("numerical peak Omega^2 =", round(float(Om[np.argmax(A)] ** 2), 4),
      " | formula w^2-2gamma^2 =", round(w**2 - 2 * g**2, 4))
"""),
        md(r"""
## 04. 相図と安定性

**04-1**: $A=\begin{pmatrix}2&1\\1&2\end{pmatrix}$。固有値 $\lambda=2\pm1=\{3,1\}$(実・正)→ **unstable node**。
"""),
        code("""
A = np.array([[2.0, 1.0], [1.0, 2.0]])
print("eigenvalues:", np.linalg.eigvals(A), "->", systems.classify_fixed_point(A))
"""),
        md(r"""
**04-2**: 減衰振動子 $\begin{pmatrix}0&1\\-\omega^2&-2\gamma\end{pmatrix}$。$0<\gamma<\omega$ で固有値は実部 $-\gamma$ の複素共役 → **stable spiral**。
"""),
        code("""
w, g = 1.0, 0.3
J = np.array([[0.0, 1.0], [-(w**2), -2 * g]])
print("eigenvalues:", np.round(np.linalg.eigvals(J), 3), "->", systems.classify_fixed_point(J))
"""),
        md(r"""
**04-3**: 競合系の内部固定点 $(1,1)$ のヤコビ行列は $\begin{pmatrix}-1&-2\\-1&-1\end{pmatrix}$。$\det=-1<0$ → **saddle**。
鞍点は不安定なので 2 種は安定共存できない(**競争排除**)。
"""),
        code("""
def fcomp(t, s):
    x, y = s
    return np.array([x * (3 - x - 2 * y), y * (2 - x - y)])

J = systems.jacobian(fcomp, [1.0, 1.0])
print("Jacobian at (1,1):\\n", np.round(J, 3))
print("det =", round(float(np.linalg.det(J)), 3), "->", systems.classify_fixed_point(J), "(no stable coexistence)")
"""),
        md(r"""
## 05. 非線形ダイナミクス

**05-1**: Lotka-Volterra の保存量 $V=\delta x-\gamma\ln x+\beta y-\alpha\ln y$ は軌道上で一定。
"""),
        code("""
al, be, de, ga = 1.1, 0.4, 0.1, 0.4
f = systems.lotka_volterra(al, be, de, ga)
t = np.linspace(0, 24, 4000)
Y = solvers.rk4(f, [2.0, 1.0], t)
V = de * Y[:, 0] - ga * np.log(Y[:, 0]) + be * Y[:, 1] - al * np.log(Y[:, 1])
print("V range over the orbit:", round(float(V.max() - V.min()), 6), "(~0 => conserved)")
"""),
        md(r"""
**05-2**: SIR の $\dot I=\beta SI-\gamma I=I(\beta S-\gamma)$。ピーク($\dot I=0,\,I>0$)は $S=\gamma/\beta$。
"""),
        code("""
beta, gamma = 0.5, 0.2
f = systems.sir(beta, gamma, 1.0)
t = np.linspace(0, 60, 4000)
Y = solvers.rk4(f, [0.99, 0.01, 0.0], t)
S_at_peak = Y[np.argmax(Y[:, 1]), 0]
print("S at infection peak =", round(float(S_at_peak), 4), " | gamma/beta =", gamma / beta)
"""),
        md(r"""
**05-3**: $\dot y=ry-y^3=g(y)$、$g'(y)=r-3y^2$。$r>0$ で $g'(0)=r>0$ → $y=0$ 不安定;
$g'(\pm\sqrt r)=r-3r=-2r<0$ → $y=\pm\sqrt r$ 安定。
"""),
        code("""
r = 0.5
gp = lambda y: r - 3 * y**2
print("g'(0) =", gp(0), "(>0 unstable)   g'(+/-sqrt r) =", round(gp(np.sqrt(r)), 3), "(<0 stable)")
"""),
        md(r"""
**05-4**: Lorenz の初期差を $10^{-6}$ にすると、$10^{-8}$ より **早く** 分岐する(分離時刻 $\approx \frac1\lambda\ln(\text{閾値}/\text{初期差})$、初期差が大きいほど早い)。
"""),
        code("""
f = systems.lorenz()
t = np.linspace(0, 40, 8000)
base = solvers.solve(f, [1.0, 1.0, 1.0], t, rtol=1e-9, atol=1e-9)
for gap in (1e-6, 1e-8):
    pert = solvers.solve(f, [1.0, 1.0, 1.0 + gap], t, rtol=1e-9, atol=1e-9)
    d = np.abs(base[:, 0] - pert[:, 0])
    t_sep = t[np.argmax(d > 1.0)]
    print(f"gap={gap:.0e}: trajectories separate (|dx|>1) at t ~ {t_sep:.1f}")
"""),
        md(r"""
## 06. 数値解法

**06-1**: Heun の収束次数(log-log の傾き)を測ると $\approx 2$。
"""),
        code("""
f = systems.exponential(-1.0)
dts, errs = [], []
for n in (16, 32, 64, 128, 256):
    t = np.linspace(0, 2, n + 1)
    dts.append(t[1] - t[0])
    errs.append(solvers.global_error(solvers.heun(f, [1.0], t)[:, 0], np.exp(-t)))
print("measured Heun order (slope) =", round(float(np.polyfit(np.log(dts), np.log(errs), 1)[0]), 3))
"""),
        md(r"""
**06-2**: 陽的 Euler を $\dot y=\lambda y$ に使うと $y_{k+1}=(1+\lambda\Delta t)y_k$。安定は $|1+\lambda\Delta t|<1$。
$\lambda<0$(実)では $-1<1+\lambda\Delta t \Rightarrow \lambda\Delta t>-2 \Rightarrow \Delta t<2/|\lambda|$。
"""),
        code("""
lam = -50.0
print("stability bound dt < 2/|lambda| =", 2 / abs(lam))
for dt in (0.039, 0.041):
    print(f"  amplification |1+lambda*dt| at dt={dt}: {abs(1 + lam * dt):.3f} ({'stable' if abs(1 + lam * dt) < 1 else 'UNSTABLE'})")
"""),
        md(r"""
**06-3**: stiff 系では陽的 RK45 は安定性のため小刻みを強いられ `nfev` が爆発、陰的 Radau は大刻みで安定。
"""),
        code("""
from scipy.integrate import solve_ivp
A = np.array([[-1.0, 0.0], [0.0, -1000.0]])
f = systems.linear_system(A)
nfev = {m: solve_ivp(f, (0, 5), [1.0, 1.0], method=m, rtol=1e-6, atol=1e-9).nfev for m in ("RK45", "Radau")}
print(nfev, "-> RK45/Radau nfev ratio =", round(nfev["RK45"] / nfev["Radau"], 1))
"""),
        md(r"""
## 07. 応用

**07-1**: 強制振動子の定常振幅は $\Omega\approx\omega$ でピーク(弱減衰なら $\Omega^2=\omega^2-2\gamma^2\approx\omega^2$)。
"""),
        code("""
w, g, F0 = 1.0, 0.1, 0.5
Om = np.linspace(0.2, 2.0, 4000)
A = F0 / np.sqrt((w**2 - Om**2) ** 2 + (2 * g * Om) ** 2)
print("peak near Omega =", round(float(Om[np.argmax(A)]), 3), "(omega = 1)")
"""),
        md(r"""
**07-2**: Vasicek の決定論部分 $\dot r=\kappa(\theta-r)$。$z=r-\theta$ とおくと $\dot z=-\kappa z \Rightarrow z=z_0e^{-\kappa t}$、
よって $r(t)=\theta+(r_0-\theta)e^{-\kappa t}$。$\kappa$ が大きいほど速く $\theta$ へ回帰。
"""),
        code("""
theta, r0 = 0.03, 0.09
t = np.linspace(0, 10, 200)
for kappa in (0.3, 1.5):
    r = theta + (r0 - theta) * np.exp(-kappa * t)
    half = t[np.argmax(np.abs(r - theta) < 0.5 * abs(r0 - theta))]
    print(f"kappa={kappa}: half-way-to-theta time ~ {half:.2f}  (larger kappa -> faster)")
"""),
        md(r"""
**07-3**: フィードバック $\dot x=(a-k)x$ は $a-k<0 \Leftrightarrow k>a$ で安定。$a=2$ なら **最小ゲイン $k=2$**(厳密には $k>2$)。
"""),
        code("""
a = 2.0
print("stabilizing requires k > a =", a, "-> minimal gain k_min =", a)
"""),
    ]
    write(cells, str(BOOK_DIR["ode"] / "notebooks" / "08_exercise_solutions.ipynb"))
    print("wrote ode 08_exercise_solutions.ipynb")


# --------------------------------------------------------------------------- #
def pde_solutions():
    pkg = PKG["pde"]
    cells = [header("pde"), *calculus_solutions(pkg)]
    cells += [
        setup_cell(pkg),
        code(f"from {pkg} import grids, solvers, datasets\nimport numpy as np"),
        md(r"""
## 02. 移流・熱・波動

**02-1**: $c<0$ では情報が右から来るので upwind は **右隣** $u_{i+1}$ を使う。波形は左へ動く。
"""),
        code("""
g = grids.Grid1D(0, 1, 201)
x, dx = g.x, g.dx
c = -1.0
U = solvers.solve_transport(datasets.gaussian(x, 0.7, 0.05), c, dx, 0.8 * dx / abs(c), 100, "upwind")
print("peak moved from 0.70 to", round(float(x[np.argmax(U[-1])]), 3), "(leftward, since c<0)")
"""),
        md(r"""
**02-2**: 熱方程式はガウス分布を **広がるガウス分布** に保つ(分散 $\sigma^2(t)=\sigma_0^2+2\alpha t$)。標準偏差が増える。
"""),
        code("""
g = grids.Grid1D(0, 1, 401)
x, dx = g.x, g.dx
u0 = datasets.gaussian(x, 0.5, 0.04, height=1.0)
U = solvers.solve_heat_explicit(u0, 1.0, dx, 0.4 * dx**2, 800)
def width(u):  # std of the (normalized) profile
    w = u / u.sum()
    return np.sqrt(np.sum(w * (x - np.sum(w * x)) ** 2))
print("std grows:", round(width(U[0]), 4), "->", round(width(U[-1]), 4), "(diffusion widens the Gaussian)")
"""),
        md(r"""
**02-3**: 「はじく」(初期変位 $u_0\ne0,\,v_0=0$)は左右に分裂して伝播。「たたく」($u_0=0,\,v_0\ne0$)は速度から変位が立ち上がる。
"""),
        code("""
g = grids.Grid1D(0, 1, 401)
x, dx = g.x, g.dx
c = 1.0
dt = 0.8 * dx / c
pluck = solvers.solve_wave(datasets.gaussian(x, 0.5, 0.04), np.zeros_like(x), c, dx, dt, 200)
hammer = solvers.solve_wave(np.zeros_like(x), datasets.gaussian(x, 0.5, 0.04), c, dx, dt, 200)
print("pluck max displacement:", round(float(np.abs(pluck).max()), 3),
      "| hammer builds displacement from velocity:", round(float(np.abs(hammer[-1]).max()), 3))
"""),
        md(r"""
## 03. Laplace・Poisson

**03-1**: 4 辺を異なる温度に固定して定常分布を解く(各辺の値が内部へ滑らかに補間される)。
"""),
        code("""
g = grids.Grid2D(0, 1, 0, 1, 41, 41)
b = np.zeros((g.ny, g.nx))
b[-1, :], b[0, :], b[:, 0], b[:, -1] = 1.0, 0.0, 0.5, 0.25  # top, bottom, left, right
u = solvers.solve_poisson_2d(np.zeros_like(b), g, b)
print("interior temperature stays within the boundary range:",
      round(float(u[1:-1, 1:-1].min()), 3), "..", round(float(u[1:-1, 1:-1].max()), 3))
"""),
        md(r"""
**03-2**: Poisson は線形なので源 $f\to-f$ で解 $u\to-u$。湧き出しが吸い込みになり、場は **凹む**。
"""),
        code("""
g = grids.Grid2D(0, 1, 0, 1, 51, 51)
X, Y = g.meshgrid()
src = 50.0 * np.exp(-((X - 0.5) ** 2 + (Y - 0.5) ** 2) / 0.005)
up = solvers.solve_poisson_2d(-src, g, np.zeros_like(X))
dn = solvers.solve_poisson_2d(+src, g, np.zeros_like(X))
print("center value: +source ->", round(float(up[25, 25]), 3), " | -source ->", round(float(dn[25, 25]), 3), "(sign flips)")
"""),
        md(r"""
**03-3**: 線形 $u=ax+by+c$ は $\nabla^2u=0$(調和)。境界に線形値を与えると内部もその線形関数(5 点ステンシルは線形に厳密)。
"""),
        code("""
g = grids.Grid2D(0, 1, 0, 1, 21, 21)
X, Y = g.meshgrid()
u_lin = 2 * X + 3 * Y + 1
u = solvers.solve_poisson_2d(np.zeros_like(X), g, u_lin)
print("max |u - (2x+3y+1)| =", float(np.max(np.abs(u - u_lin))), "(~0: linear is harmonic)")
"""),
        md(r"""
## 04. Fourier 級数と変換

**04-1**: 三角波の係数は $\propto 1/k^2$(矩形波は $1/k$)。$1/k^2$ は速く減衰し、跳びが無いので **Gibbs が出ず速く収束**。
"""),
        code("""
x = np.linspace(0, 2 * np.pi, 1000)
tri = 2 / np.pi * np.arcsin(np.sin(x))  # triangle wave in [-1,1]
def tri_partial(n):
    s = np.zeros_like(x)
    for j in range(n):
        k = 2 * j + 1
        s += (-1) ** j / k**2 * np.sin(k * x)
    return 8 / np.pi**2 * s
for n in (1, 3, 10):
    print(f"triangle, {n:2d} terms: max error = {np.max(np.abs(tri_partial(n) - tri)):.4f}")
"""),
        md(r"""
**04-2**: Nyquist($f_s/2$)を超える正弦は **折り返し(エイリアシング)**。$f_s=10$ で $f=8$ を標本化すると $|8-10|=2$ Hz に化ける。
"""),
        code("""
fs = 10.0
n = np.arange(0, 4, 1 / fs)
hi = np.sin(2 * np.pi * 8 * n)
spec = np.abs(np.fft.rfft(hi)) / (len(n) / 2)
freq = np.fft.rfftfreq(len(n), 1 / fs)
print("8 Hz sampled at fs=10 appears at", round(float(freq[np.argmax(spec)]), 2), "Hz (alias = |8-10| = 2)")
"""),
        md(r"""
**04-3**: 熱方程式はモード $\sin(n\pi x)$ を固有値 $(n\pi)^2$ に応じて $e^{-\alpha(n\pi)^2 t}$ で減衰させる。
比 $a_1/a_4 \propto e^{-\alpha(1^2-4^2)\pi^2 t}=e^{15\alpha\pi^2 t}$ で **増大**(高次が速く消える)。
"""),
        code("""
g = grids.Grid1D(0, 1, 201)
x, dx = g.x, g.dx
alpha = 1.0
u0 = datasets.sine_combo(x, (1, 4), (1.0, 1.0), L=1.0)
proj = lambda u, k: 2 * np.trapezoid(u * np.sin(k * np.pi * x), x)  # mode amplitude
U = solvers.solve_heat_explicit(u0, alpha, dx, 0.4 * dx**2, 400)
t_end = 400 * 0.4 * dx**2
r_num = proj(U[-1], 1) / proj(U[-1], 4)
r_th = (proj(u0, 1) / proj(u0, 4)) * np.exp(-alpha * (1 - 16) * np.pi**2 * t_end)
print("amplitude ratio a1/a4: numerical =", round(float(r_num), 2), " theory =", round(float(r_th), 2))
"""),
        md(r"""
## 05. 変数分離法

**05-1**: Neumann($u_x(0)=u_x(L)=0$)では $X''=-\lambda X$ の解で端の傾きが 0 になるのは $X_n=\cos(n\pi x/L)$。
($X_n'=-\tfrac{n\pi}{L}\sin(n\pi x/L)$ は $x=0,L$ で 0。)
"""),
        code("""
g = grids.Grid1D(0, 1, 201)
x = g.x
for n in (1, 2, 3):
    Xp = -n * np.pi * np.sin(n * np.pi * x)  # derivative of cos(n pi x)
    print(f"cos({n} pi x): |X'(0)|={abs(Xp[0]):.2e}, |X'(L)|={abs(Xp[-1]):.2e} (Neumann satisfied)")
"""),
        md(r"""
**05-2**: 3 モード混合の初期条件を熱方程式で時間発展させると、$e^{-\alpha k^2 t}$ により高次が先に消え、**最低次モードだけが残る**。
"""),
        code("""
g = grids.Grid1D(0, 1, 201)
x, dx = g.x, g.dx
U = solvers.solve_heat_explicit(datasets.sine_combo(x, (1, 3, 6), (1.0, 0.8, 0.6)), 1.0, dx, 0.4 * dx**2, 2000)
proj = lambda u, k: 2 * np.trapezoid(u * np.sin(k * np.pi * x), x)
amps = {k: round(float(abs(proj(U[-1], k))), 4) for k in (1, 3, 6)}
print("late-time mode amplitudes:", amps, "-> mode 1 dominates")
"""),
        md(r"""
**05-3**: 弦の固有振動数は $f_n=n c/(2L)$、基本($n=1$)は角振動数 $\pi c/L$。$L$ を小さくすると振動数が上がる(高い音)。
"""),
        code("""
c = 1.0
for L in (1.0, 0.5):
    print(f"L={L}: fundamental angular frequency = pi c / L = {np.pi * c / L:.3f}")
print("-> shorter string (smaller L) gives a higher pitch")
"""),
        md(r"""
## 06. 有限差分法

**06-1**: モード $\sin(kx)$ の FTCS 増幅率は $g=1-4r\sin^2(k\Delta x/2)$。$|g|\le1$ は最悪 $\sin^2=1$ で $1-4r\ge-1 \Rightarrow r\le1/2$。
"""),
        code("""
r = 0.5
worst = 1 - 4 * r * 1.0  # sin^2 = 1
print("at r=1/2 worst amplification =", worst, "(= -1, the stability edge)")
print("r=0.6 worst amplification =", 1 - 4 * 0.6, "(< -1 -> grows, unstable)")
"""),
        md(r"""
**06-2**: $C=1$ の upwind は $u_i^{n+1}=u_i-1\cdot(u_i-u_{i-1})=u_{i-1}$、すなわち **1 格子ぴったりの平行移動**=数値拡散ゼロの厳密移流。
"""),
        code("""
g = grids.Grid1D(0, 1, 201)
x, dx = g.x, g.dx
u0 = datasets.gaussian(x, 0.3, 0.05)
U = solvers.solve_transport(u0, 1.0, dx, 1.0 * dx, 50, "upwind")  # CFL = 1 exactly
shifted = np.roll(u0, 50)  # exact shift by 50 cells
print("max |upwind(C=1) - exact shift| =", float(np.max(np.abs(U[-1] - shifted))), "(~0: no numerical diffusion)")
"""),
        md(r"""
**06-3**: 陰解法 $(I-rL)u^{n+1}=u^n$ の行列は **三重対角**。`scipy` の `splu` で一度だけ LU 分解すれば毎ステップ前進・後退代入で速い。
"""),
        code("""
import scipy.sparse as sp
n, r = 8, 0.5
A = sp.diags([-r * np.ones(n - 1), (1 + 2 * r) * np.ones(n), -r * np.ones(n - 1)], [-1, 0, 1]).toarray()
band = np.count_nonzero(A) - np.count_nonzero(np.diag(A)) - np.count_nonzero(np.diag(A, 1)) - np.count_nonzero(np.diag(A, -1))
print("nonzeros off the three central diagonals:", band, "(0 => tridiagonal)")
"""),
        md(r"""
## 07. 応用

**07-1**: 2 次元 FTCS の増幅率は $g=1-4r(\sin^2\tfrac{k_x\Delta x}{2}+\sin^2\tfrac{k_y\Delta y}{2})$、最悪 $1-8r\ge-1 \Rightarrow r\le1/4$。
(1 次元 $1/2$ の半分。隣接点が 4 方向に増えるため。)
"""),
        code("""
print("2-D worst amplification at r=1/4:", 1 - 8 * 0.25, "(= -1, the 2-D stability edge)")
"""),
        md(r"""
**07-2**: Black-Scholes 価格は満期で折れ線(payoff)に近づき二階微分が鋭くなるので、$t\to T$ で有限差分の **残差(誤差)が増大**。
"""),
        code("""
from scipy.stats import norm
K, rr, sig, T = 1.0, 0.05, 0.2, 1.0
def bs(S, t):
    tau = max(T - t, 1e-9)
    d1 = (np.log(S / K) + (rr + 0.5 * sig**2) * tau) / (sig * np.sqrt(tau))
    return S * norm.cdf(d1) - K * np.exp(-rr * tau) * norm.cdf(d1 - sig * np.sqrt(tau))
S0, h, dtau = 1.0, 1e-4, 1e-5
for t0 in (0.4, 0.9, 0.99):
    Vt = (bs(S0, t0 + dtau) - bs(S0, t0 - dtau)) / (2 * dtau)
    Vss = (bs(S0 + h, t0) - 2 * bs(S0, t0) + bs(S0 - h, t0)) / h**2
    res = Vt + 0.5 * sig**2 * S0**2 * Vss + rr * S0 * (bs(S0 + h, t0) - bs(S0 - h, t0)) / (2 * h) - rr * bs(S0, t0)
    print(f"t={t0:.2f} (T-t={T - t0:.2f}): PDE residual = {res:.2e}")
"""),
        md(r"""
**07-3**: 画像拡散はステップが進むほどエッジが鈍る。勾配の大きさ(エッジの強さ)の総和が単調に減少する。
"""),
        code("""
img = datasets.make_test_image(96, seed=0)
u = img.copy()
def edge_strength(a):
    gx = np.diff(a, axis=1); gy = np.diff(a, axis=0)
    return float(np.abs(gx).sum() + np.abs(gy).sum())
print(f"step   0: edge strength = {edge_strength(u):.0f}")
for k in range(1, 41):
    lap = np.roll(u, 1, 0) + np.roll(u, -1, 0) + np.roll(u, 1, 1) + np.roll(u, -1, 1) - 4 * u
    u = u + 0.2 * lap
    if k in (10, 40):
        print(f"step {k:3d}: edge strength = {edge_strength(u):.0f}  (edges blur away)")
"""),
    ]
    write(cells, str(BOOK_DIR["pde"] / "notebooks" / "08_exercise_solutions.ipynb"))
    print("wrote pde 08_exercise_solutions.ipynb")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "ode"
    (ode_solutions if target == "ode" else pde_solutions)()
