"""
build_ir_models_notebook.py
============================
nbformat を使って ir_models.ipynb を生成するスクリプト。

Usage:
    /home/kazumasa/anaconda3/bin/python build_ir_models_notebook.py
"""

import json
import os

# ---------------------------------------------------------------------------
# Cell helpers (same pattern as build_bsm_notebook.py)
# ---------------------------------------------------------------------------


def md(source: str) -> dict:
    lines = source.split("\n")
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": lines,
    }


def code(source: str) -> dict:
    lines = source.split("\n")
    return {
        "cell_type": "code",
        "metadata": {},
        "source": lines,
        "outputs": [],
        "execution_count": None,
    }


# ---------------------------------------------------------------------------
# Build cell list
# ---------------------------------------------------------------------------
cells = []

# ===========================================================================
# Section 0: はじめに
# ===========================================================================

cells.append(
    md(r"""# 金利モデル比較・学習ノートブック

## なぜ金利モデルが必要か

金利モデルは以下の場面で不可欠です：
- **価格付け（Pricing）**: 金利スワップ・キャップ・スワップションなどの OTC デリバティブ評価
- **リスク管理**: DV01 / コンベクシティ / テール感応度の計算
- **ALM（資産負債管理）**: 保険・銀行の長期デュレーション管理

本ノートブックでは以下の **9 モデル** を共通のマーケットデータでクロス比較します。""")
)

cells.append(
    code(r"""%matplotlib widget
""")
)

cells.append(
    code(r"""# --- imports ---
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath("__file__")))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import japanize_matplotlib
import seaborn as sns
import plotly.graph_objects as go  # Treemap / Sankey のみ使用
import ipywidgets as widgets
from IPython.display import display
from scipy.optimize import minimize, brentq
from scipy.stats import gaussian_kde

from market_data import (
    TENORS, ZERO_RATES, CURVE_LABELS, CURVE_COLORS,
    discount_factors, instantaneous_forward, to_dataframe,
)

np.random.seed(42)

def _kde_xy(samples, n_pts=200):
    s = np.asarray(samples, dtype=float)
    s = s[np.isfinite(s)]
    if len(s) < 5:
        return np.zeros(n_pts), np.linspace(0, 1, n_pts)
    kde = gaussian_kde(s)
    x = np.linspace(s.min(), s.max(), n_pts)
    return kde(x), x

def _t_to_idx(T, T_total=10.0, N=252):
    return int(round(T / T_total * N))

def _redraw_dist(fig, ax_dist, dist_ln, smp, T, color):
    kd, kr = _kde_xy(smp)
    dist_ln.set_xdata(kd)
    dist_ln.set_ydata(kr)
    for coll in ax_dist.collections:
        coll.remove()
    ax_dist.fill_betweenx(kr, 0, kd, alpha=0.3, color=color)
    ax_dist.set_xlim(left=0)
    ax_dist.set_title(f'分布（T={T:.1f}年）', fontsize=9)

plt.ioff()  # prevent auto-display; figures shown via display() or plt.show()
print("Imports OK")
""")
)

cells.append(
    md(r"""## モデル分類図

金利モデルは大きく3ファミリーに分類されます：

```
金利モデル
├── 均衡ショートレートモデル (Equilibrium Short-rate)
│   ├── Vasicek (1977)          — mean reversion あり、負金利あり
│   ├── CIR (1985)              — mean reversion あり、負金利なし
│   └── Rendleman-Bartter       — mean reversion なし（GBM型）
│
├── 無裁定ショートレートモデル (Arbitrage-free Short-rate)
│   ├── Ho-Lee (1986)           — 初期カーブ完全フィット
│   ├── Hull-White (1990)       — 初期カーブ完全フィット + mean reversion
│   ├── Black-Derman-Toy (1990) — 対数正規、ボラティリティ TS
│   └── Black-Karasinski (1991) — 対数正規 + mean reversion
│
└── フォワードレートモデル (Forward-rate Model)
    ├── HJM (1992)              — 瞬間フォワードレート f(t,T)
    └── BGM/LMM (1997)         — 離散 LIBOR L_i(t)
```""")
)

cells.append(
    code(r"""# --- モデル分類ツリー（plotly Treemap） ---
labels = [
    "金利モデル",
    "均衡ショートレートモデル", "無裁定ショートレートモデル", "フォワードレートモデル",
    "Vasicek", "CIR", "Rendleman-Bartter",
    "Ho-Lee", "Hull-White", "BDT", "BK",
    "HJM", "BGM/LMM",
]
parents = [
    "",
    "金利モデル", "金利モデル", "金利モデル",
    "均衡ショートレートモデル", "均衡ショートレートモデル", "均衡ショートレートモデル",
    "無裁定ショートレートモデル", "無裁定ショートレートモデル",
    "無裁定ショートレートモデル", "無裁定ショートレートモデル",
    "フォワードレートモデル", "フォワードレートモデル",
]
fig_tree = go.Figure(go.Treemap(
    labels=labels,
    parents=parents,
    textinfo="label",
    marker_colorscale="Blues",
))
fig_tree.update_layout(title="金利モデル分類", height=500)
fig_tree.show()
""")
)

cells.append(
    md(r"""## 共通マーケットデータ（4 カーブパターン）

| パターン | 形状 | 想定局面 |
|---|---|---|
| `normal` | 右肩上がり | 景気拡大期 |
| `inverted` | 右肩下がり | 利上げ局面・景気後退懸念 |
| `flat` | ほぼフラット | QE 環境・転換期 |
| `humped` | 2-3Y でピーク | 不確実性の高い局面 |

4パターンすべてを同時に表示します。""")
)

cells.append(
    code(r"""# --- 4 カーブパターン表示（matplotlib） ---

fig_curves, ax_curves = plt.subplots(figsize=(8, 4))
for p, color in CURVE_COLORS.items():
    ax_curves.plot(TENORS, ZERO_RATES[p] * 100,
                   marker="o", markersize=5, linewidth=2,
                   color=color, label=CURVE_LABELS[p])

ax_curves.set_title("イールドカーブ（4パターン）")
ax_curves.set_xlabel("テナー（年）")
ax_curves.set_ylabel("ゼロレート（%）")
ax_curves.legend(loc="upper left")
ax_curves.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
""")
)

# ===========================================================================
# Section 1: 均衡ショートレートモデル
# ===========================================================================

cells.append(
    md(r"""---
# Section 1: 均衡ショートレートモデル（Equilibrium Short-rate Models）

均衡モデルは **外生的に決めたパラメータ** から金利の確率的振る舞いを記述します。
市場の初期カーブへの完全フィットは **保証しない** 代わりに、解析的な結果が多く得られます。""")
)

# --- 1.1 Vasicek ---
cells.append(
    md(r"""## 1.1 Vasicek モデル（1977）

### SDE

$$dr_t = \kappa(\theta - r_t)\,dt + \sigma\,dW_t$$

| パラメータ | 意味 |
|---|---|
| $\kappa > 0$ | 平均回帰速度（mean reversion speed） |
| $\theta$ | 長期均衡水準（long-run mean） |
| $\sigma$ | ボラティリティ |

### 特徴
- **解析的なゼロ債券価格**: $P(t,T) = A(t,T)\exp(-B(t,T)\,r_t)$（閉形式あり）
- **負金利が発生しうる**（拡散項が $r_t$ に依存しないため）
- **平均回帰あり**: $\kappa$ が大きいほど $\theta$ への回帰が速い""")
)

cells.append(
    code(r"""# --- Vasicek SDE: Euler-Maruyama シミュレーション ---

def simulate_vasicek(kappa, theta, sigma, r0, T=10.0, N=252, n_paths=100, seed=42):
    '''Simulate Vasicek short-rate paths via Euler-Maruyama.'''
    rng = np.random.default_rng(seed)
    dt = T / N
    r = np.zeros((n_paths, N + 1))
    r[:, 0] = r0
    for i in range(N):
        dW = rng.normal(0, np.sqrt(dt), n_paths)
        dr = kappa * (theta - r[:, i]) * dt + sigma * dW
        r[:, i + 1] = r[:, i] + dr
    return r


def vasicek_zero_curve(kappa, theta, sigma, r0, tenors):
    '''Vasicek analytical zero rate curve.'''
    B = (1 - np.exp(-kappa * tenors)) / kappa
    A_log = (
        (B - tenors) * (kappa ** 2 * theta - 0.5 * sigma ** 2) / kappa ** 2
        - sigma ** 2 * B ** 2 / (4 * kappa)
    )
    # P(0,T) = exp(A_log - B * r0) => zero rate = -log(P)/T
    log_P = A_log - B * r0
    return -log_P / tenors


t_grid = np.linspace(0, 10, 253)
_N_PATHS = 500

kappa_slider = widgets.FloatSlider(value=0.1, min=0.05, max=2.0, step=0.05,
                                   description="κ（回帰速度）:", style={"description_width": "initial"})
theta_slider = widgets.FloatSlider(value=0.05, min=0.01, max=0.15, step=0.005,
                                   description="θ（長期均衡）:", style={"description_width": "initial"},
                                   readout_format=".3f")
sigma_slider = widgets.FloatSlider(value=0.01, min=0.001, max=0.05, step=0.001,
                                   description="σ（ボラティリティ）:", style={"description_width": "initial"},
                                   readout_format=".3f")
t_vas_sl = widgets.FloatSlider(value=5.0, min=0.5, max=10.0, step=0.5,
                               description="T（分布表示時点）:", style={"description_width": "initial"})

fig_vas, (ax_vas_p, ax_vas_d) = plt.subplots(
    1, 2, figsize=(12, 5), gridspec_kw={'width_ratios': [3, 2]})
plt.subplots_adjust(wspace=0.08)

_vas_paths = [simulate_vasicek(0.1, 0.05, 0.01, 0.03, n_paths=_N_PATHS)]
_smp0 = _vas_paths[0][:, _t_to_idx(5.0)] * 100
_kd0, _kr0 = _kde_xy(_smp0)

path_lines_v = [ax_vas_p.plot(t_grid, _vas_paths[0][i]*100, color='steelblue', lw=0.8, alpha=0.5,
                     label='サンプルパス' if i==0 else '')[0] for i in range(10)]
mean_ln_v, = ax_vas_p.plot(t_grid, _vas_paths[0].mean(0)*100, color='navy', lw=2.5, label='平均パス')
ref_ln_v, = ax_vas_p.plot([0,10], [5.0,5.0], color='gray', ls='--', lw=1.2, label='θ（長期均衡）')
t_ln_v, = ax_vas_p.plot([5.0,5.0], [-4,22], color='black', ls=':', lw=1.2)
ax_vas_p.set_xlim(0, 10)
ax_vas_p.set_ylim(-4, 22)
ax_vas_p.set_xlabel('時間（年）')
ax_vas_p.set_ylabel('短期金利（%）')
ax_vas_p.set_title('サンプルパス（500パス中10本）', fontsize=9)
ax_vas_p.legend(loc='upper left', fontsize=8)
ax_vas_p.grid(True, alpha=0.3)

dist_ln_v, = ax_vas_d.plot(_kd0, _kr0, color='navy', lw=2)
ax_vas_d.fill_betweenx(_kr0, 0, _kd0, alpha=0.3, color='steelblue')
ax_vas_d.set_xlim(left=0)
ax_vas_d.set_ylim(-4, 22)
ax_vas_d.set_xlabel('確率密度')
ax_vas_d.set_title('分布（T=5.0年）', fontsize=9)
ax_vas_d.grid(True, alpha=0.3)
fig_vas.suptitle('Vasicek: κ=0.10, θ=0.050, σ=0.010')
fig_vas.tight_layout()


def update_vasicek(change):
    k, th, sig, T = kappa_slider.value, theta_slider.value, sigma_slider.value, t_vas_sl.value
    p = simulate_vasicek(k, th, sig, 0.03, n_paths=_N_PATHS)
    _vas_paths[0] = p
    tidx = _t_to_idx(T)
    for i, ln in enumerate(path_lines_v):
        ln.set_ydata(p[i]*100)
    mean_ln_v.set_ydata(p.mean(0)*100)
    ref_ln_v.set_ydata([th*100, th*100])
    t_ln_v.set_xdata([T, T])
    smp = p[:, tidx] * 100
    _redraw_dist(fig_vas, ax_vas_d, dist_ln_v, smp, T, 'steelblue')
    fig_vas.suptitle(f'Vasicek: κ={k:.2f}, θ={th:.3f}, σ={sig:.3f}')
    fig_vas.canvas.draw_idle()


def update_vas_t(change):
    T = t_vas_sl.value
    smp = _vas_paths[0][:, _t_to_idx(T)] * 100
    t_ln_v.set_xdata([T, T])
    _redraw_dist(fig_vas, ax_vas_d, dist_ln_v, smp, T, 'steelblue')
    fig_vas.canvas.draw_idle()


for _s in [kappa_slider, theta_slider, sigma_slider]:
    _s.observe(update_vasicek, names='value')
t_vas_sl.observe(update_vas_t, names='value')

display(widgets.VBox([
    widgets.HBox([kappa_slider, theta_slider, sigma_slider]),
    t_vas_sl,
    fig_vas.canvas,
]))
""")
)

# --- 1.2 CIR ---
cells.append(
    md(r"""## 1.2 CIR モデル（Cox-Ingersoll-Ross, 1985）

### SDE

$$dr_t = \kappa(\theta - r_t)\,dt + \sigma\sqrt{r_t}\,dW_t$$

### Feller 条件

$$2\kappa\theta > \sigma^2$$

この条件を満たすとき $r_t > 0$ が **確率 1 で保証** されます（負金利なし）。
拡散項が $\sqrt{r_t}$ なので金利が低いほどボラティリティも小さくなる。""")
)

cells.append(
    code(r"""# --- CIR simulation ---
def simulate_cir(kappa, theta, sigma, r0, T=10.0, N=252, n_paths=100, seed=42):
    # Reflected Euler-Maruyama: educational approximation.
    # Exact CIR sampling uses the non-central chi-squared distribution (Broadie-Kaya).
    rng = np.random.default_rng(seed)
    dt = T / N
    r = np.zeros((n_paths, N + 1))
    r[:, 0] = r0
    for i in range(N):
        dW = rng.normal(0, np.sqrt(dt), n_paths)
        dr = kappa * (theta - r[:, i]) * dt + sigma * np.sqrt(np.maximum(r[:, i], 0)) * dW
        r[:, i + 1] = np.maximum(r[:, i] + dr, 0.0)
    return r


kappa_cir_sl = widgets.FloatSlider(value=0.1, min=0.05, max=2.0, step=0.05,
                                   description="κ（回帰速度）:", style={"description_width": "initial"})
theta_cir_sl = widgets.FloatSlider(value=0.05, min=0.01, max=0.15, step=0.005,
                                   description="θ（長期均衡）:", style={"description_width": "initial"},
                                   readout_format=".3f")
sigma_cir_sl = widgets.FloatSlider(value=0.05, min=0.001, max=0.15, step=0.005,
                                   description="σ（ボラティリティ）:", style={"description_width": "initial"},
                                   readout_format=".3f")
t_cir_sl = widgets.FloatSlider(value=5.0, min=0.5, max=10.0, step=0.5,
                               description="T（分布表示時点）:", style={"description_width": "initial"})

fig_cir, (ax_cir_p, ax_cir_d) = plt.subplots(
    1, 2, figsize=(12, 5), gridspec_kw={'width_ratios': [3, 2]})
plt.subplots_adjust(wspace=0.08)

_cir_paths = [simulate_cir(0.1, 0.05, 0.05, 0.03, n_paths=_N_PATHS)]
_smp0 = _cir_paths[0][:, _t_to_idx(5.0)] * 100
_kd0, _kr0 = _kde_xy(_smp0)

path_lines_c = [ax_cir_p.plot(t_grid, _cir_paths[0][i]*100, color='salmon', lw=0.8, alpha=0.5,
                     label='サンプルパス' if i==0 else '')[0] for i in range(10)]
mean_ln_c, = ax_cir_p.plot(t_grid, _cir_paths[0].mean(0)*100, color='firebrick', lw=2.5, label='平均パス')
ref_ln_c, = ax_cir_p.plot([0,10], [5.0,5.0], color='gray', ls='--', lw=1.2, label='θ（長期均衡）')
t_ln_c, = ax_cir_p.plot([5.0,5.0], [0,22], color='black', ls=':', lw=1.2)
ax_cir_p.set_xlim(0, 10)
ax_cir_p.set_ylim(0, 22)
ax_cir_p.set_xlabel('時間（年）')
ax_cir_p.set_ylabel('短期金利（%）')
ax_cir_p.set_title('サンプルパス（500パス中10本）', fontsize=9)
ax_cir_p.legend(loc='upper left', fontsize=8)
ax_cir_p.grid(True, alpha=0.3)

dist_ln_c, = ax_cir_d.plot(_kd0, _kr0, color='firebrick', lw=2)
ax_cir_d.fill_betweenx(_kr0, 0, _kd0, alpha=0.3, color='salmon')
ax_cir_d.set_xlim(left=0)
ax_cir_d.set_ylim(0, 22)
ax_cir_d.set_xlabel('確率密度')
ax_cir_d.set_title('分布（T=5.0年）', fontsize=9)
ax_cir_d.grid(True, alpha=0.3)
fig_cir.suptitle('CIR: κ=0.10, θ=0.050, σ=0.050  (Feller ✓)')
fig_cir.tight_layout()


def update_cir(change):
    k, th, sig, T = kappa_cir_sl.value, theta_cir_sl.value, sigma_cir_sl.value, t_cir_sl.value
    p = simulate_cir(k, th, sig, 0.03, n_paths=_N_PATHS)
    _cir_paths[0] = p
    tidx = _t_to_idx(T)
    for i, ln in enumerate(path_lines_c):
        ln.set_ydata(p[i]*100)
    mean_ln_c.set_ydata(p.mean(0)*100)
    ref_ln_c.set_ydata([th*100, th*100])
    t_ln_c.set_xdata([T, T])
    smp = p[:, tidx] * 100
    _redraw_dist(fig_cir, ax_cir_d, dist_ln_c, smp, T, 'salmon')
    fig_cir.suptitle(f'CIR: κ={k:.2f}, θ={th:.3f}, σ={sig:.3f}  Feller {"✓" if 2*k*th>sig**2 else "✗"}')
    fig_cir.canvas.draw_idle()


def update_cir_t(change):
    T = t_cir_sl.value
    smp = _cir_paths[0][:, _t_to_idx(T)] * 100
    t_ln_c.set_xdata([T, T])
    _redraw_dist(fig_cir, ax_cir_d, dist_ln_c, smp, T, 'salmon')
    fig_cir.canvas.draw_idle()


for _s in [kappa_cir_sl, theta_cir_sl, sigma_cir_sl]:
    _s.observe(update_cir, names='value')
t_cir_sl.observe(update_cir_t, names='value')

display(widgets.VBox([
    widgets.HBox([kappa_cir_sl, theta_cir_sl, sigma_cir_sl]),
    t_cir_sl,
    fig_cir.canvas,
]))
""")
)

# --- 1.3 Rendleman-Bartter ---
cells.append(
    md(r"""## 1.3 Rendleman–Bartter モデル

### SDE（幾何ブラウン運動型）

$$dr_t = \mu\,r_t\,dt + \sigma\,r_t\,dW_t$$

- 株価の GBM と同形 → $r_t$ は対数正規分布（負金利なし）
- **mean reversion なし** → 長期的に金利が発散・崩壊する可能性
- 主に **教育目的**・CIR/Vasicek との対比用""")
)

cells.append(
    code(r"""# --- Rendleman-Bartter simulation ---
def simulate_rb(mu, sigma, r0, T=10.0, N=252, n_paths=100, seed=42):
    '''Simulate Rendleman-Bartter (GBM) short-rate paths.'''
    rng = np.random.default_rng(seed)
    dt = T / N
    r = np.zeros((n_paths, N + 1))
    r[:, 0] = r0
    for i in range(N):
        dW = rng.normal(0, np.sqrt(dt), n_paths)
        dr = mu * r[:, i] * dt + sigma * r[:, i] * dW
        r[:, i + 1] = r[:, i] + dr
    return r


mu_rb_sl = widgets.FloatSlider(value=0.02, min=-0.05, max=0.10, step=0.005,
                               description="μ（ドリフト）:", style={"description_width": "initial"},
                               readout_format=".3f")
sigma_rb_sl = widgets.FloatSlider(value=0.12, min=0.01, max=0.40, step=0.01,
                                  description="σ（ボラティリティ）:", style={"description_width": "initial"},
                                  readout_format=".2f")
t_rb_sl = widgets.FloatSlider(value=5.0, min=0.5, max=10.0, step=0.5,
                              description="T（分布表示時点）:", style={"description_width": "initial"})

fig_rb, (ax_rb_p, ax_rb_d) = plt.subplots(
    1, 2, figsize=(12, 5), gridspec_kw={'width_ratios': [3, 2]})
plt.subplots_adjust(wspace=0.08)

_rb_paths = [simulate_rb(0.02, 0.12, 0.03, n_paths=_N_PATHS)]
_smp0 = _rb_paths[0][:, _t_to_idx(5.0)] * 100
_kd0, _kr0 = _kde_xy(_smp0)

path_lines_rb = [ax_rb_p.plot(t_grid, _rb_paths[0][i]*100, color='seagreen', lw=0.8, alpha=0.5,
                     label='サンプルパス' if i==0 else '')[0] for i in range(10)]
mean_ln_rb, = ax_rb_p.plot(t_grid, _rb_paths[0].mean(0)*100, color='darkgreen', lw=2.5, label='平均パス')
ref_ln_rb, = ax_rb_p.plot([0,10], [3.0,3.0], color='gray', ls='--', lw=1.2, label='r₀=3%')
t_ln_rb, = ax_rb_p.plot([5.0,5.0], [0,30], color='black', ls=':', lw=1.2)
ax_rb_p.set_xlim(0, 10)
ax_rb_p.set_ylim(0, 30)
ax_rb_p.set_xlabel('時間（年）')
ax_rb_p.set_ylabel('短期金利（%）')
ax_rb_p.set_title('サンプルパス（500パス中10本）', fontsize=9)
ax_rb_p.legend(loc='upper left', fontsize=8)
ax_rb_p.grid(True, alpha=0.3)

dist_ln_rb, = ax_rb_d.plot(_kd0, _kr0, color='darkgreen', lw=2)
ax_rb_d.fill_betweenx(_kr0, 0, _kd0, alpha=0.3, color='seagreen')
ax_rb_d.set_xlim(left=0)
ax_rb_d.set_ylim(0, 30)
ax_rb_d.set_xlabel('確率密度')
ax_rb_d.set_title('分布（T=5.0年）', fontsize=9)
ax_rb_d.grid(True, alpha=0.3)
fig_rb.suptitle('Rendleman-Bartter: μ=0.020, σ=0.12 — mean reversion なし')
fig_rb.tight_layout()


def update_rb(change):
    mu, sig, T = mu_rb_sl.value, sigma_rb_sl.value, t_rb_sl.value
    p = simulate_rb(mu, sig, 0.03, n_paths=_N_PATHS)
    _rb_paths[0] = p
    tidx = _t_to_idx(T)
    for i, ln in enumerate(path_lines_rb):
        ln.set_ydata(p[i]*100)
    mean_ln_rb.set_ydata(p.mean(0)*100)
    ref_ln_rb.set_ydata([3.0, 3.0])
    t_ln_rb.set_xdata([T, T])
    smp = p[:, tidx] * 100
    _redraw_dist(fig_rb, ax_rb_d, dist_ln_rb, smp, T, 'seagreen')
    fig_rb.suptitle(f'Rendleman-Bartter: μ={mu:.3f}, σ={sig:.2f}')
    fig_rb.canvas.draw_idle()


def update_rb_t(change):
    T = t_rb_sl.value
    smp = _rb_paths[0][:, _t_to_idx(T)] * 100
    t_ln_rb.set_xdata([T, T])
    _redraw_dist(fig_rb, ax_rb_d, dist_ln_rb, smp, T, 'seagreen')
    fig_rb.canvas.draw_idle()


for _s in [mu_rb_sl, sigma_rb_sl]:
    _s.observe(update_rb, names='value')
t_rb_sl.observe(update_rb_t, names='value')

display(widgets.VBox([
    widgets.HBox([mu_rb_sl, sigma_rb_sl]),
    t_rb_sl,
    fig_rb.canvas,
]))
""")
)

# --- Section 1 まとめ: 均衡3モデル比較 ---
cells.append(
    md(r"""---
## Section 1 まとめ: 均衡3モデル比較

同一初期条件（r₀=3%, θ=5%, κ=0.1）で**解析的な平均パス ± 1σ** を重ね表示します。

- **Vasicek / CIR**: 平均パスは同一だが、σ バンドの形が異なる（CIR は低金利ほど幅が狭い）
- **Rendleman-Bartter**: mean reversion がないため長期で大きく乖離""")
)

cells.append(
    code(r"""# --- 均衡3モデル比較: 解析的平均パス ± 1σ（インタラクティブ） ---

T_eq = np.linspace(0.01, 10, 300)
r0_eq_cmp = 0.03

kappa_eq_sl = widgets.FloatSlider(value=0.10, min=0.01, max=1.0,  step=0.01,
                                  description="κ（回帰速度）:",    style={"description_width": "initial"})
theta_eq_sl = widgets.FloatSlider(value=0.05, min=0.01, max=0.15, step=0.005,
                                  description="θ（長期均衡）:",    style={"description_width": "initial"},
                                  readout_format=".3f")
sig_v_sl    = widgets.FloatSlider(value=0.01, min=0.001, max=0.05, step=0.001,
                                  description="σ_V（Vasicek）:",  style={"description_width": "initial"},
                                  readout_format=".3f")
sig_c_sl    = widgets.FloatSlider(value=0.05, min=0.001, max=0.15, step=0.005,
                                  description="σ_C（CIR）:",  style={"description_width": "initial"},
                                  readout_format=".3f")
mu_rb_eq_sl = widgets.FloatSlider(value=0.0,  min=-0.05, max=0.10, step=0.005,
                                  description="μ_RB（ドリフト）:", style={"description_width": "initial"},
                                  readout_format=".3f")
sig_rb_eq_sl= widgets.FloatSlider(value=0.12, min=0.01, max=0.40, step=0.01,
                                  description="σ_RB（GBM vol）:", style={"description_width": "initial"},
                                  readout_format=".2f")

def _eq_bands(k, th, sv, sc, mu_r, sr):
    mean_v = th + (r0_eq_cmp - th) * np.exp(-k * T_eq)
    std_v  = np.sqrt(sv**2 / (2 * k) * (1 - np.exp(-2 * k * T_eq)))
    mean_c = th + (r0_eq_cmp - th) * np.exp(-k * T_eq)
    var_c  = (r0_eq_cmp * sc**2 / k * (np.exp(-k * T_eq) - np.exp(-2 * k * T_eq))
              + th * sc**2 / (2 * k) * (1 - np.exp(-k * T_eq))**2)
    std_c  = np.sqrt(np.maximum(var_c, 0))
    mean_r = r0_eq_cmp * np.exp(mu_r * T_eq)
    std_r  = r0_eq_cmp * np.exp(mu_r * T_eq) * np.sqrt(np.maximum(np.exp(sr**2 * T_eq) - 1, 0))
    return (mean_v, std_v), (mean_c, std_c), (mean_r, std_r)

t_eq_cmp_sl = widgets.FloatSlider(value=5.0, min=0.5, max=10.0, step=0.5,
                                  description="T（分布表示時点）:", style={"description_width": "initial"})
_N_EQ_CMP = 300
_EQ_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c"]
_EQ_LABELS = ["Vasicek", "CIR", "Rendleman-Bartter"]

def _eq_sim_samples(k, th, sv, sc, mu_r, sr, T):
    tidx = _t_to_idx(T)
    pv = simulate_vasicek(k, th, sv, r0_eq_cmp, n_paths=_N_EQ_CMP)
    pc = simulate_cir(k, th, sc, r0_eq_cmp, n_paths=_N_EQ_CMP)
    pr = simulate_rb(mu_r, sr, r0_eq_cmp, n_paths=_N_EQ_CMP)
    return pv[:, tidx] * 100, pc[:, tidx] * 100, pr[:, tidx] * 100

(mv0, sv0), (mc0, sc0), (mr0, sr0) = _eq_bands(0.1, 0.05, 0.01, 0.05, 0.0, 0.12)

fig_eq_cmp, (ax_eq_p, ax_eq_d) = plt.subplots(1, 2, figsize=(12, 5),
    gridspec_kw={"width_ratios": [3, 2]})
plt.subplots_adjust(wspace=0.1)

_eq_band_lines = []
_eq_fill_polys = []
for (mean, std, color, label) in [(mv0, sv0, "#1f77b4", "Vasicek"),
                                   (mc0, sc0, "#ff7f0e", "CIR"),
                                   (mr0, sr0, "#2ca02c", "Rendleman-Bartter")]:
    ln, = ax_eq_p.plot(T_eq, mean*100, color=color, lw=2.5, label=label)
    lo = np.maximum((mean-std)*100, 0.0) if label == "Rendleman-Bartter" else (mean-std)*100
    fill = ax_eq_p.fill_between(T_eq, lo, (mean+std)*100,
                                 color=color, alpha=0.12)
    _eq_band_lines.append(ln)
    _eq_fill_polys.append(fill)
theta_ref_eq, = ax_eq_p.plot([T_eq[0], T_eq[-1]], [5.0, 5.0],
                               color="gray", ls="--", lw=1.2, label="θ（長期均衡）")
t_ln_eq, = ax_eq_p.plot([5.0, 5.0], [-4, 22], color="black", ls=":", lw=1.2)
ax_eq_p.set_xlim(0, 10); ax_eq_p.set_ylim(-4, 22)
ax_eq_p.set_xlabel("時間（年）"); ax_eq_p.set_ylabel("短期金利（%）")
ax_eq_p.set_title("解析的平均パス ± 1σ", fontsize=9)
ax_eq_p.legend(loc="upper left", fontsize=8); ax_eq_p.grid(True, alpha=0.3)

_eq_dist_lns = []
smp_init = _eq_sim_samples(0.1, 0.05, 0.01, 0.05, 0.0, 0.12, 5.0)
for (smp, color) in zip(smp_init, _EQ_COLORS):
    kd, kr = _kde_xy(smp)
    ax_eq_d.fill_betweenx(kr, 0, kd, alpha=0.25, color=color)
    dl, = ax_eq_d.plot(kd, kr, color=color, lw=2)
    _eq_dist_lns.append(dl)
ax_eq_d.set_xlim(left=0); ax_eq_d.set_ylim(-4, 22)
ax_eq_d.set_xlabel("確率密度"); ax_eq_d.set_title("分布（T=5.0年）", fontsize=9)
ax_eq_d.grid(True, alpha=0.3)
fig_eq_cmp.suptitle("均衡3モデル比較: κ=0.10, θ=0.050")
fig_eq_cmp.tight_layout()


def _eq_redraw_dist(smps, T):
    ax_eq_d.cla()
    for (smp, color, ln) in zip(smps, _EQ_COLORS, _eq_dist_lns):
        kd, kr = _kde_xy(smp)
        ax_eq_d.fill_betweenx(kr, 0, kd, alpha=0.25, color=color)
        ln.set_xdata(kd); ln.set_ydata(kr)
        ax_eq_d.add_line(ln)
    ax_eq_d.set_xlim(left=0); ax_eq_d.set_ylim(-4, 22)
    ax_eq_d.set_xlabel("確率密度"); ax_eq_d.set_title(f"分布（T={T:.1f}年）", fontsize=9)
    ax_eq_d.grid(True, alpha=0.3)


def update_eq_cmp(change):
    k, th = kappa_eq_sl.value, theta_eq_sl.value
    sv, sc, mu_r, sr = sig_v_sl.value, sig_c_sl.value, mu_rb_eq_sl.value, sig_rb_eq_sl.value
    T = t_eq_cmp_sl.value
    (mv, sv_), (mc, sc_), (mr, sr_) = _eq_bands(k, th, sv, sc, mu_r, sr)
    smps = _eq_sim_samples(k, th, sv, sc, mu_r, sr, T)
    for fill in _eq_fill_polys:
        fill.remove()
    _eq_fill_polys.clear()
    for i, (ln, mean, std, color) in enumerate(
            zip(_eq_band_lines, [mv, mc, mr], [sv_, sc_, sr_], _EQ_COLORS)):
        ln.set_ydata(mean*100)
        lo = np.maximum((mean-std)*100, 0.0) if i == 2 else (mean-std)*100
        fill = ax_eq_p.fill_between(T_eq, lo, (mean+std)*100,
                                     color=color, alpha=0.12)
        _eq_fill_polys.append(fill)
    theta_ref_eq.set_ydata([th*100, th*100])
    t_ln_eq.set_xdata([T, T])
    _eq_redraw_dist(smps, T)
    fig_eq_cmp.suptitle(f"均衡3モデル比較: κ={k:.2f}, θ={th:.3f}")
    fig_eq_cmp.canvas.draw_idle()


def update_eq_cmp_t(change):
    T = t_eq_cmp_sl.value
    k, th = kappa_eq_sl.value, theta_eq_sl.value
    sv, sc, mu_r, sr = sig_v_sl.value, sig_c_sl.value, mu_rb_eq_sl.value, sig_rb_eq_sl.value
    smps = _eq_sim_samples(k, th, sv, sc, mu_r, sr, T)
    t_ln_eq.set_xdata([T, T])
    _eq_redraw_dist(smps, T)
    fig_eq_cmp.canvas.draw_idle()


for s in [kappa_eq_sl, theta_eq_sl, sig_v_sl, sig_c_sl, mu_rb_eq_sl, sig_rb_eq_sl]:
    s.observe(update_eq_cmp, names="value")
t_eq_cmp_sl.observe(update_eq_cmp_t, names="value")

display(widgets.VBox([
    widgets.HBox([kappa_eq_sl, theta_eq_sl]),
    widgets.HBox([sig_v_sl, sig_c_sl, mu_rb_eq_sl, sig_rb_eq_sl]),
    t_eq_cmp_sl,
    fig_eq_cmp.canvas,
]))
""")
)

# ===========================================================================
# Section 2: 無裁定ショートレートモデル
# ===========================================================================

cells.append(
    md(r"""---
# Section 2: 無裁定ショートレートモデル（Arbitrage-free Short-rate Models）

無裁定モデルは **時変ドリフト $\theta_t$** を市場の初期カーブから逆算し、
モデルが **現在の市場価格と完全に整合** するようキャリブレーションします。""")
)

# --- 2.1 Ho-Lee ---
cells.append(
    md(r"""## 2.1 Ho–Lee モデル（1986）

### SDE

$$dr_t = \theta_t\,dt + \sigma\,dW_t$$

$\theta_t$ を市場のフォワードレート $f^M(0,t)$ から決定：

$$\theta_t = \frac{\partial f^M(0,t)}{\partial t} + \sigma^2 t$$

- **初期カーブ完全フィット** ✓
- **mean reversion なし** → 長期で分散が $\sigma^2 t$ で増大
- **負金利あり**（Vasicek と同じ常数拡散項）""")
)

cells.append(
    code(r"""# --- Ho-Lee calibration ---

def _hl_theta_continuous(pattern, sigma=0.01):
    '''
    Compute theta(t) for Ho-Lee from market forward rates (continuous formula).
    theta(t) = df^M(0,t)/dt + sigma^2 * t
    '''
    f = instantaneous_forward(pattern)
    df_dt = np.gradient(f, TENORS)
    return df_dt + sigma ** 2 * TENORS


def ho_lee_zero_curve(pattern, sigma=0.01):
    return ZERO_RATES[pattern].copy()


sigma_hl_sl = widgets.FloatSlider(value=0.01, min=0.001, max=0.05, step=0.001,
                                  description="σ（ボラティリティ）:", style={"description_width": "initial"},
                                  readout_format=".3f")
drop_hl = widgets.Dropdown(
    options=[(CURVE_LABELS[p], p) for p in ZERO_RATES],
    description="パターン:", style={"description_width": "initial"},
    layout=widgets.Layout(width="300px"),
)

p_hl_init = "normal"
fig_hl, ax_hl = plt.subplots(figsize=(9, 4))
theta_hl_ln, = ax_hl.plot(TENORS, _hl_theta_continuous(p_hl_init, 0.01)*100,
                           color="firebrick", lw=2, marker="o", ms=5, label="θ_t (Ho-Lee)")
fwd_hl_ln, = ax_hl.plot(TENORS, instantaneous_forward(p_hl_init)*100,
                         color="steelblue", lw=2, ls="--", marker="s", ms=5,
                         label="f^M(0,T) 市場フォワード")
ax_hl.set_xlabel("テナー（年）"); ax_hl.set_ylabel("レート（%）")
ax_hl.set_title("Ho-Lee: θ_t vs 市場フォワード（σ が大きいほど θ_t が上方シフト）", fontsize=9)
ax_hl.legend(fontsize=8); ax_hl.grid(True, alpha=0.3)
fig_hl.tight_layout()


def update_hl(change):
    p = drop_hl.value
    sig = sigma_hl_sl.value
    theta_hl_ln.set_ydata(_hl_theta_continuous(p, sig)*100)
    fwd_hl_ln.set_ydata(instantaneous_forward(p)*100)
    ax_hl.set_title(f"Ho-Lee: θ_t (σ={sig:.3f}) vs 市場フォワード [{p}]", fontsize=9)
    ax_hl.relim(); ax_hl.autoscale_view()
    fig_hl.canvas.draw_idle()


for w in [sigma_hl_sl, drop_hl]:
    w.observe(update_hl, names="value")

display(widgets.VBox([
    widgets.HBox([drop_hl, sigma_hl_sl]),
    fig_hl.canvas,
]))
""")
)

# --- 2.2 Hull-White ---
cells.append(
    md(r"""## 2.2 Hull–White モデル（1990）

### SDE

$$dr_t = \big(\theta_t - a\,r_t\big)\,dt + \sigma\,dW_t$$

$\theta_t$ の解析式（Hull-White calibration condition）：

$$\theta_t = \frac{\partial f^M(0,t)}{\partial t} + a\,f^M(0,t) + \frac{\sigma^2}{2a}\left(1 - e^{-2at}\right)$$

- **初期カーブ完全フィット** ✓
- **mean reversion あり**（$a > 0$）
- **負金利あり**（Ho-Lee に mean reversion を加えた拡張）
- **金利デリバティブの業界標準**的モデル""")
)

cells.append(
    code(r"""# --- Hull-White calibration and zero curve ---

def calibrate_hull_white_theta(pattern, a=0.1, sigma=0.01):
    '''
    Compute theta(t) for Hull-White from market forward rates.
    theta(t) = df^M(0,t)/dt + a * f^M(0,t) + sigma^2/(2a) * (1 - exp(-2a*t))
    '''
    f = instantaneous_forward(pattern)
    df_dt = np.gradient(f, TENORS)
    theta_t = df_dt + a * f + sigma**2 / (2 * a) * (1 - np.exp(-2 * a * TENORS))
    return theta_t


def hull_white_zero_curve(pattern, a=0.1, sigma=0.01, r0=None):
    '''
    Hull-White zero rate curve. At t=0, the calibrated model exactly fits P^M(0,T).
    Returns market zero rates (exact fit by construction).
    '''
    return ZERO_RATES[pattern].copy()


# --- Interactive: a, sigma sliders → Hull-White theta_t ---
a_slider = widgets.FloatSlider(value=0.10, min=0.01, max=1.0, step=0.01,
                               description="a（回帰速度）:", style={"description_width": "initial"})
s_hw_slider = widgets.FloatSlider(value=0.01, min=0.001, max=0.05, step=0.001,
                                  description="σ（ボラティリティ）:", style={"description_width": "initial"},
                                  readout_format=".3f")
drop_hw = widgets.Dropdown(
    options=[(CURVE_LABELS[p], p) for p in ZERO_RATES],
    description="パターン:", style={"description_width":"initial"},
    layout=widgets.Layout(width="300px"),
)

pattern_init = "normal"
theta_init = calibrate_hull_white_theta(pattern_init, a_slider.value, s_hw_slider.value)
fig_hw, ax_hw = plt.subplots(figsize=(9, 4))
theta_hw_ln, = ax_hw.plot(TENORS, theta_init*100,
                           color="darkorange", lw=2, marker="o", ms=5, label="θ_t (Hull-White)")
fwd_hw_ln, = ax_hw.plot(TENORS, instantaneous_forward(pattern_init)*100,
                         color="steelblue", lw=2, ls="--", marker="s", ms=5,
                         label="f^M(0,T) 市場フォワード")
ax_hw.set_xlabel("テナー（年）"); ax_hw.set_ylabel("レート（%）")
ax_hw.set_title("Hull-White: θ_t vs 市場フォワードレート", fontsize=9)
ax_hw.legend(fontsize=8); ax_hw.grid(True, alpha=0.3)
fig_hw.tight_layout()


def update_hw(change):
    p = drop_hw.value
    a = a_slider.value
    s = s_hw_slider.value
    theta_hw_ln.set_ydata(calibrate_hull_white_theta(p, a, s)*100)
    fwd_hw_ln.set_ydata(instantaneous_forward(p)*100)
    ax_hw.set_title(f"Hull-White θ_t: a={a:.2f}, σ={s:.3f}, [{p}]", fontsize=9)
    ax_hw.relim(); ax_hw.autoscale_view()
    fig_hw.canvas.draw_idle()


for w in [a_slider, s_hw_slider, drop_hw]:
    w.observe(update_hw, names="value")

display(widgets.VBox([
    widgets.HBox([drop_hw, a_slider, s_hw_slider]),
    fig_hw.canvas,
]))
""")
)

cells.append(
    code(r"""# --- Hull-White: simulated short-rate paths ---

def simulate_hull_white(theta_const, a, sigma, r0, T=10.0, N=252, n_paths=100, seed=42):
    '''Simulate Hull-White paths with constant theta (illustrative).'''
    rng = np.random.default_rng(seed)
    dt = T / N
    r = np.zeros((n_paths, N + 1))
    r[:, 0] = r0
    for i in range(N):
        dW = rng.normal(0, np.sqrt(dt), n_paths)
        dr = (theta_const - a * r[:, i]) * dt + sigma * dW
        r[:, i + 1] = r[:, i] + dr
    return r


_theta_hw_const = 0.05 * 0.10  # a * θ_long_run ≈ mean level

a_hw_path_sl = widgets.FloatSlider(value=0.10, min=0.01, max=1.0, step=0.01,
                                   description="a（回帰速度）:", style={"description_width": "initial"})
s_hw_path_sl = widgets.FloatSlider(value=0.01, min=0.001, max=0.05, step=0.001,
                                   description="σ（ボラティリティ）:", style={"description_width": "initial"},
                                   readout_format=".3f")
t_hw_sl = widgets.FloatSlider(value=5.0, min=0.5, max=10.0, step=0.5,
                              description="T（分布表示時点）:", style={"description_width": "initial"})

_hw_paths = [simulate_hull_white(_theta_hw_const, 0.10, 0.01, 0.03, n_paths=_N_PATHS)]
_smp_hw0 = _hw_paths[0][:, _t_to_idx(5.0)] * 100
_kd_hw0, _kr_hw0 = _kde_xy(_smp_hw0)

fig_hw_paths, (ax_hw_p, ax_hw_d) = plt.subplots(
    1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [3, 2]})
plt.subplots_adjust(wspace=0.08)

path_lines_hw = [ax_hw_p.plot(t_grid, _hw_paths[0][i]*100, color="purple", lw=0.8, alpha=0.5,
                               label="サンプルパス" if i==0 else "")[0] for i in range(10)]
mean_ln_hw, = ax_hw_p.plot(t_grid, _hw_paths[0].mean(0)*100, color="darkviolet", lw=2.5, label="平均パス")
ref_ln_hw, = ax_hw_p.plot([0, 10], [3.0, 3.0], color="gray", ls="--", lw=1.2, label="r₀=3%")
t_ln_hw, = ax_hw_p.plot([5.0, 5.0], [-3, 15], color="black", ls=":", lw=1.2)
ax_hw_p.set_xlim(0, 10); ax_hw_p.set_ylim(-3, 15)
ax_hw_p.set_xlabel("時間（年）"); ax_hw_p.set_ylabel("短期金利（%）")
ax_hw_p.set_title("サンプルパス（500パス中10本）", fontsize=9)
ax_hw_p.legend(loc="upper left", fontsize=8); ax_hw_p.grid(True, alpha=0.3)

dist_ln_hw, = ax_hw_d.plot(_kd_hw0, _kr_hw0, color="darkviolet", lw=2)
ax_hw_d.fill_betweenx(_kr_hw0, 0, _kd_hw0, alpha=0.3, color="purple")
ax_hw_d.set_xlim(left=0); ax_hw_d.set_ylim(-3, 15)
ax_hw_d.set_xlabel("確率密度"); ax_hw_d.set_title("分布（T=5.0年）", fontsize=9)
ax_hw_d.grid(True, alpha=0.3)
fig_hw_paths.suptitle("Hull-White パスシミュレーション: a=0.10, σ=0.010")
fig_hw_paths.tight_layout()


def update_hw_paths(change):
    a, sig, T = a_hw_path_sl.value, s_hw_path_sl.value, t_hw_sl.value
    p = simulate_hull_white(_theta_hw_const, a, sig, 0.03, n_paths=_N_PATHS)
    _hw_paths[0] = p
    for i, ln in enumerate(path_lines_hw): ln.set_ydata(p[i]*100)
    mean_ln_hw.set_ydata(p.mean(0)*100)
    t_ln_hw.set_xdata([T, T])
    smp = p[:, _t_to_idx(T)] * 100
    _redraw_dist(fig_hw_paths, ax_hw_d, dist_ln_hw, smp, T, "purple")
    fig_hw_paths.suptitle(f"Hull-White パスシミュレーション: a={a:.2f}, σ={sig:.3f}")
    fig_hw_paths.canvas.draw_idle()


def update_hw_t(change):
    T = t_hw_sl.value
    smp = _hw_paths[0][:, _t_to_idx(T)] * 100
    t_ln_hw.set_xdata([T, T])
    _redraw_dist(fig_hw_paths, ax_hw_d, dist_ln_hw, smp, T, "purple")
    fig_hw_paths.canvas.draw_idle()


for s in [a_hw_path_sl, s_hw_path_sl]:
    s.observe(update_hw_paths, names="value")
t_hw_sl.observe(update_hw_t, names="value")

display(widgets.VBox([
    widgets.HBox([a_hw_path_sl, s_hw_path_sl]),
    t_hw_sl,
    fig_hw_paths.canvas,
]))
""")
)

# --- 2.3 BDT ---
cells.append(
    md(r"""## 2.3 Black–Derman–Toy モデル（1990）

### SDE（対数正規ショートレート）

$$d(\ln r_t) = \theta_t\,dt + \sigma_t\,dW_t$$

つまり $\ln r_t$ が Ho-Lee 型の SDE に従います。

### 特徴
- **負金利なし**（$r_t > 0$ 常に保証）
- **ボラティリティ term structure** $\sigma_t$ をキャリブレーション可能
- 離散バイナリー**ツリー**として実装されることが多い（後述Section 4でブートストラップ実装）

### BDT ツリー概念図

下記は簡略概念図です（実際は dt ステップごとに分岐）：
```
                        r_uuu
              r_uu
    r_u                 r_uud
r_0
    r_d                 r_udd
              r_dd
                        r_ddd
```
各ノードで $r_{up} = r_{down} \cdot e^{2\sigma_t\sqrt{\Delta t}}$""")
)

cells.append(
    code(r"""# --- BDT ツリー（σ スライダーでノードレートが変化） ---
import plotly.graph_objects as go

nodes_pos = {
    (0, 0): (0, 0),
    (1, 0): (1, -1), (1, 1): (1, 1),
    (2, 0): (2, -2), (2, 1): (2, 0), (2, 2): (2, 2),
    (3, 0): (3, -3), (3, 1): (3, -1), (3, 2): (3, 1), (3, 3): (3, 3),
}
edges_x, edges_y = [], []
for step in range(3):
    for lev in range(step + 1):
        for next_lev in [lev, lev + 1]:
            x0, y0 = nodes_pos[(step, lev)]
            x1, y1 = nodes_pos[(step + 1, next_lev)]
            edges_x += [x0, x1, None]
            edges_y += [y0, y1, None]

_bdt_bases = [0.030, 0.025, 0.021, 0.018]  # lowest-node base rates per step

def bdt_node_rates(sigma):
    '''r[step][lev] = base[step] * exp(2 * lev * sigma)'''
    rates = {}
    for step in range(4):
        for lev in range(step + 1):
            rates[(step, lev)] = _bdt_bases[step] * np.exp(2 * lev * sigma)
    return rates

def make_bdt_labels(sigma):
    rates = bdt_node_rates(sigma)
    return {k: f"{v*100:.2f}%" for k, v in rates.items()}


sigma_bdt_sl = widgets.FloatSlider(value=0.15, min=0.01, max=0.50, step=0.01,
                                   description="σ（対数正規vol）:", style={"description_width": "initial"},
                                   readout_format=".2f")

labels_init = make_bdt_labels(0.15)
node_keys = list(nodes_pos.keys())

fig_bdt, ax_bdt = plt.subplots(figsize=(8, 4))
for step in range(3):
    for lev in range(step + 1):
        for next_lev in [lev, lev + 1]:
            x0, y0 = nodes_pos[(step, lev)]
            x1, y1 = nodes_pos[(step + 1, next_lev)]
            ax_bdt.plot([x0, x1], [y0, y1], color="gray", lw=1.2, zorder=1)
_bdt_texts = {}
for key, (x, y) in nodes_pos.items():
    ax_bdt.scatter([x], [y], s=120, color="steelblue", zorder=3)
    _bdt_texts[key] = ax_bdt.text(x, y + 0.3, labels_init[key], ha="center", fontsize=8)
ax_bdt.set_xlim(-0.5, 3.5); ax_bdt.set_ylim(-4, 4)
ax_bdt.set_xticks([0, 1, 2, 3]); ax_bdt.set_xticklabels(["t=0","t=1","t=2","t=3"])
ax_bdt.set_yticks([]); ax_bdt.grid(False)
ax_bdt.set_title("BDT ツリー（σ=0.15）— r_up = r_down × exp(2σ)", fontsize=9)
fig_bdt.tight_layout()


def update_bdt(change):
    sig = sigma_bdt_sl.value
    new_labels = make_bdt_labels(sig)
    for key, txt in _bdt_texts.items():
        txt.set_text(new_labels[key])
    ax_bdt.set_title(f"BDT ツリー（σ={sig:.2f}）— r_up = r_down × exp(2σ)", fontsize=9)
    fig_bdt.canvas.draw_idle()


sigma_bdt_sl.observe(update_bdt, names="value")
display(widgets.VBox([sigma_bdt_sl, fig_bdt.canvas]))
""")
)

# --- 2.4 BK ---
cells.append(
    md(r"""## 2.4 Black–Karasinski モデル（1991）

### SDE

$$d(\ln r_t) = \big(\theta_t - a\,\ln r_t\big)\,dt + \sigma_t\,dW_t$$

### BDT との違い

| 比較軸 | BDT | BK |
|---|---|---|
| Mean reversion | なし（$\sigma_t$ 一定なら）| **あり**（$a > 0$ で明示的に） |
| ボラティリティ | $\sigma_t$ で term structure | $\sigma_t$ + mean reversion $a$ |
| 解析解 | なし | なし |
| キャリブレーション | $\theta_t$ のみ or $(\theta_t, \sigma_t)$ | $\theta_t$ を逐次決定（$a, \sigma$ 固定） |

**BK は BDT に Hull-White の mean reversion を組み合わせた形** と解釈できます。""")
)

cells.append(
    code(r"""# --- Black-Karasinski: simulated short-rate paths ---

def simulate_bk(theta_const, a, sigma, r0, T=10.0, N=252, n_paths=100, seed=42):
    '''Simulate BK: d(ln r) = (theta - a * ln r) dt + sigma dW'''
    rng = np.random.default_rng(seed)
    dt = T / N
    x = np.zeros((n_paths, N + 1))
    x[:, 0] = np.log(r0)
    for i in range(N):
        dW = rng.normal(0, np.sqrt(dt), n_paths)
        dx = (theta_const - a * x[:, i]) * dt + sigma * dW
        x[:, i + 1] = x[:, i] + dx
    return np.exp(x)


_theta_bk_const = np.log(0.05)  # log-space long-run level ≈ 5%

a_bk_sl = widgets.FloatSlider(value=0.10, min=0.01, max=1.0, step=0.01,
                               description="a（回帰速度）:", style={"description_width": "initial"})
sigma_bk_sl = widgets.FloatSlider(value=0.15, min=0.01, max=0.50, step=0.01,
                                  description="σ（対数正規vol）:", style={"description_width": "initial"},
                                  readout_format=".2f")
t_bk_sl = widgets.FloatSlider(value=5.0, min=0.5, max=10.0, step=0.5,
                              description="T（分布表示時点）:", style={"description_width": "initial"})

_bk_paths = [simulate_bk(_theta_bk_const, 0.10, 0.15, 0.03, n_paths=_N_PATHS)]
_smp_bk0 = _bk_paths[0][:, _t_to_idx(5.0)] * 100
_kd_bk0, _kr_bk0 = _kde_xy(_smp_bk0)

fig_bk, (ax_bk_p, ax_bk_d) = plt.subplots(
    1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [3, 2]})
plt.subplots_adjust(wspace=0.08)

path_lines_bk = [ax_bk_p.plot(t_grid, _bk_paths[0][i]*100, color="hotpink", lw=0.8, alpha=0.5,
                               label="サンプルパス" if i==0 else "")[0] for i in range(10)]
mean_ln_bk, = ax_bk_p.plot(t_grid, _bk_paths[0].mean(0)*100, color="deeppink", lw=2.5, label="平均パス")
ref_ln_bk, = ax_bk_p.plot([0, 10], [3.0, 3.0], color="gray", ls="--", lw=1.2, label="r₀=3%")
t_ln_bk, = ax_bk_p.plot([5.0, 5.0], [0, 30], color="black", ls=":", lw=1.2)
ax_bk_p.set_xlim(0, 10); ax_bk_p.set_ylim(0, 30)
ax_bk_p.set_xlabel("時間（年）"); ax_bk_p.set_ylabel("短期金利（%）")
ax_bk_p.set_title("サンプルパス（500パス中10本）", fontsize=9)
ax_bk_p.legend(loc="upper left", fontsize=8); ax_bk_p.grid(True, alpha=0.3)

dist_ln_bk, = ax_bk_d.plot(_kd_bk0, _kr_bk0, color="deeppink", lw=2)
ax_bk_d.fill_betweenx(_kr_bk0, 0, _kd_bk0, alpha=0.3, color="hotpink")
ax_bk_d.set_xlim(left=0); ax_bk_d.set_ylim(0, 30)
ax_bk_d.set_xlabel("確率密度"); ax_bk_d.set_title("分布（T=5.0年）", fontsize=9)
ax_bk_d.grid(True, alpha=0.3)
fig_bk.suptitle("Black-Karasinski: a=0.10, σ=0.15（対数正規 → 負金利なし）")
fig_bk.tight_layout()


def update_bk(change):
    a, sig, T = a_bk_sl.value, sigma_bk_sl.value, t_bk_sl.value
    p = simulate_bk(_theta_bk_const, a, sig, 0.03, n_paths=_N_PATHS)
    _bk_paths[0] = p
    for i, ln in enumerate(path_lines_bk): ln.set_ydata(p[i]*100)
    mean_ln_bk.set_ydata(p.mean(0)*100)
    t_ln_bk.set_xdata([T, T])
    smp = p[:, _t_to_idx(T)] * 100
    _redraw_dist(fig_bk, ax_bk_d, dist_ln_bk, smp, T, "hotpink")
    fig_bk.suptitle(f"Black-Karasinski: a={a:.2f}, σ={sig:.2f}")
    fig_bk.canvas.draw_idle()


def update_bk_t(change):
    T = t_bk_sl.value
    smp = _bk_paths[0][:, _t_to_idx(T)] * 100
    t_ln_bk.set_xdata([T, T])
    _redraw_dist(fig_bk, ax_bk_d, dist_ln_bk, smp, T, "hotpink")
    fig_bk.canvas.draw_idle()


for s in [a_bk_sl, sigma_bk_sl]:
    s.observe(update_bk, names="value")
t_bk_sl.observe(update_bk_t, names="value")

display(widgets.VBox([
    widgets.HBox([a_bk_sl, sigma_bk_sl]),
    t_bk_sl,
    fig_bk.canvas,
]))
""")
)

# --- Section 2 まとめ: 無裁定4モデル比較 ---
cells.append(
    md(r"""---
## Section 2 まとめ: 無裁定4モデル比較

全モデルは初期カーブに完全フィット。ここでは**簡略定数パラメータ**でパス動態を比較します。

| モデル | 分布 | Mean reversion |
|---|---|---|
| Ho-Lee | 正規（additive） | なし |
| Hull-White | 正規（additive） | **あり** |
| BDT | 対数正規（multiplicative） | なし（簡略形） |
| BK | 対数正規（multiplicative） | **あり** |""")
)

cells.append(
    code(r"""# --- 無裁定4モデル比較: パス動態の違い（インタラクティブ） ---

N_cmp2 = 300
r0_arb = 0.03

def simulate_ho_lee_cmp(sigma, r0, T=10.0, N=252, n_paths=300, seed=42):
    rng = np.random.default_rng(seed)
    dt = T / N
    r = np.zeros((n_paths, N + 1))
    r[:, 0] = r0
    for i in range(N):
        r[:, i + 1] = r[:, i] + sigma * rng.normal(0, np.sqrt(dt), n_paths)
    return r

def simulate_bdt_cmp(sigma, r0, T=10.0, N=252, n_paths=300, seed=42):
    rng = np.random.default_rng(seed)
    dt = T / N
    x = np.zeros((n_paths, N + 1))
    x[:, 0] = np.log(r0)
    for i in range(N):
        x[:, i + 1] = x[:, i] + sigma * rng.normal(0, np.sqrt(dt), n_paths)
    return np.exp(x)

sig_add_sl = widgets.FloatSlider(value=0.01, min=0.001, max=0.05, step=0.001,
                                 description="σ_add（加法vol）:", style={"description_width": "initial"},
                                 readout_format=".3f")
sig_log_sl = widgets.FloatSlider(value=0.15, min=0.01,  max=0.50, step=0.01,
                                 description="σ_log（対数正規vol）:", style={"description_width": "initial"},
                                 readout_format=".2f")
a_mr_sl    = widgets.FloatSlider(value=0.10, min=0.01,  max=1.0,  step=0.01,
                                 description="a（回帰速度）:", style={"description_width": "initial"})

def _run_arb_sims(sa, sl, a):
    hl  = simulate_ho_lee_cmp(sa, r0_arb, n_paths=N_cmp2)
    hw  = simulate_hull_white(_theta_hw_const, a, sa, r0_arb, n_paths=N_cmp2)
    bdt = simulate_bdt_cmp(sl, r0_arb, n_paths=N_cmp2)
    bk  = simulate_bk(_theta_bk_const, a, sl, r0_arb, n_paths=N_cmp2)
    return hl, hw, bdt, bk

t_arb_cmp_sl = widgets.FloatSlider(value=5.0, min=0.5, max=10.0, step=0.5,
                                   description="T（分布表示時点）:", style={"description_width": "initial"})

hl0, hw0, bdt0, bk0 = _run_arb_sims(0.01, 0.15, 0.10)
_arb_paths = [hl0, hw0, bdt0, bk0]
_ARB_COLORS = ["#d62728", "#9467bd", "#8c564b", "#e377c2"]
_ARB_LABELS = ["Ho-Lee", "Hull-White", "BDT", "BK"]

fig_arb_cmp, (ax_arb_p, ax_arb_d) = plt.subplots(1, 2, figsize=(12, 5),
    gridspec_kw={"width_ratios": [3, 2]})
plt.subplots_adjust(wspace=0.1)

_arb_mean_lns = []; _arb_fill_polys = []; _arb_dist_lns = []
for (paths, color, label) in zip(_arb_paths, _ARB_COLORS, _ARB_LABELS):
    mean = paths.mean(0); std = paths.std(0)
    ln, = ax_arb_p.plot(t_grid, mean*100, color=color, lw=2.5, label=label)
    fill = ax_arb_p.fill_between(t_grid, (mean-std)*100, (mean+std)*100, color=color, alpha=0.12)
    _arb_mean_lns.append(ln); _arb_fill_polys.append(fill)
    kd, kr = _kde_xy(paths[:, _t_to_idx(5.0)]*100)
    ax_arb_d.fill_betweenx(kr, 0, kd, alpha=0.25, color=color)
    dl, = ax_arb_d.plot(kd, kr, color=color, lw=2)
    _arb_dist_lns.append(dl)
t_ln_arb, = ax_arb_p.plot([5.0, 5.0], [-4, 22], color="black", ls=":", lw=1.2)
ax_arb_p.set_xlim(0, 10); ax_arb_p.set_ylim(-4, 22)
ax_arb_p.set_xlabel("時間（年）"); ax_arb_p.set_ylabel("短期金利（%）")
ax_arb_p.set_title("平均パス ± 1σ", fontsize=9)
ax_arb_p.legend(loc="upper left", fontsize=8); ax_arb_p.grid(True, alpha=0.3)
ax_arb_d.set_xlim(left=0); ax_arb_d.set_ylim(-4, 22)
ax_arb_d.set_xlabel("確率密度"); ax_arb_d.set_title("分布（T=5.0年）", fontsize=9)
ax_arb_d.grid(True, alpha=0.3)
fig_arb_cmp.suptitle("無裁定4モデル比較: σ_add=0.010, σ_log=0.15, a=0.10")
fig_arb_cmp.tight_layout()


def _arb_redraw_dist(T):
    tidx = _t_to_idx(T)
    ax_arb_d.cla()
    for (paths, color, ln) in zip(_arb_paths, _ARB_COLORS, _arb_dist_lns):
        smp = paths[:, tidx] * 100
        kd, kr = _kde_xy(smp)
        ax_arb_d.fill_betweenx(kr, 0, kd, alpha=0.25, color=color)
        ln.set_xdata(kd); ln.set_ydata(kr)
        ax_arb_d.add_line(ln)
    ax_arb_d.set_xlim(left=0); ax_arb_d.set_ylim(-4, 22)
    ax_arb_d.set_xlabel("確率密度"); ax_arb_d.set_title(f"分布（T={T:.1f}年）", fontsize=9)
    ax_arb_d.grid(True, alpha=0.3)


def update_arb_cmp(change):
    sa, sl, a, T = sig_add_sl.value, sig_log_sl.value, a_mr_sl.value, t_arb_cmp_sl.value
    hl, hw, bdt, bk = _run_arb_sims(sa, sl, a)
    _arb_paths[:] = [hl, hw, bdt, bk]
    for fill in _arb_fill_polys: fill.remove()
    _arb_fill_polys.clear()
    for i, (ln, paths, color) in enumerate(zip(_arb_mean_lns, _arb_paths, _ARB_COLORS)):
        mean = paths.mean(0); std = paths.std(0)
        ln.set_ydata(mean*100)
        fill = ax_arb_p.fill_between(t_grid, (mean-std)*100, (mean+std)*100, color=color, alpha=0.12)
        _arb_fill_polys.append(fill)
    t_ln_arb.set_xdata([T, T])
    _arb_redraw_dist(T)
    fig_arb_cmp.suptitle(f"無裁定4モデル比較: σ_add={sa:.3f}, σ_log={sl:.2f}, a={a:.2f}")
    fig_arb_cmp.canvas.draw_idle()


def update_arb_cmp_t(change):
    T = t_arb_cmp_sl.value
    t_ln_arb.set_xdata([T, T])
    _arb_redraw_dist(T)
    fig_arb_cmp.canvas.draw_idle()


for s in [sig_add_sl, sig_log_sl, a_mr_sl]:
    s.observe(update_arb_cmp, names="value")
t_arb_cmp_sl.observe(update_arb_cmp_t, names="value")

display(widgets.VBox([
    widgets.HBox([sig_add_sl, sig_log_sl, a_mr_sl]),
    t_arb_cmp_sl,
    fig_arb_cmp.canvas,
]))
""")
)

# ===========================================================================
# Section 3: フォワードレートモデル
# ===========================================================================

cells.append(
    md(r"""---
# Section 3: フォワードレートモデル（Forward-rate Models）

Short-rate モデルが **$r_t$（1点）** を状態変数とするのに対し、
Forward-rate モデルは **カーブ全体**を状態変数として直接モデル化します。""")
)

cells.append(
    md(r"""## 3.1 HJM フレームワーク（Heath-Jarrow-Morton, 1992）

### モデル化対象

瞬間フォワードレート $f(t, T)$ の確率微分方程式：

$$df(t,T) = \alpha(t,T)\,dt + \sigma(t,T)\,dW_t$$

### HJM ドリフト条件（無裁定の必要十分条件）

$$\alpha(t,T) = \sigma(t,T)\int_t^T \sigma(t,s)\,ds$$

ドリフト $\alpha$ は **ボラティリティだけで決まる** — ボラティリティ関数 $\sigma(t,T)$ を一度決めればモデルが確定します。

### Hull-White は HJM の特殊ケース

$\sigma(t,T) = \sigma\,e^{-a(T-t)}$（指数型ボラティリティ）を選ぶと Hull-White と等価になります：

$$\alpha(t,T) = \sigma e^{-a(T-t)} \cdot \frac{\sigma}{a}\left(1 - e^{-a(T-t)}\right)$$

### HJM の課題
- **一般的には非マルコフ** → 状態変数の次元が増え、木・PDE が非常に複雑
- 指数型ボラティリティ（Hull-White）はマルコフ性を回復する特殊形""")
)

cells.append(
    code(r"""# --- HJM: Exponential volatility → Hull-White equivalence (interactive) ---

T_values = np.linspace(0.01, 20, 200)

a_hjm_sl = widgets.FloatSlider(value=0.10, min=0.01, max=0.50, step=0.01,
                               description="a（回帰速度）:", style={"description_width": "initial"})
sigma_hjm_sl = widgets.FloatSlider(value=0.01, min=0.001, max=0.05, step=0.001,
                                   description="σ（ボラティリティ）:", style={"description_width": "initial"},
                                   readout_format=".3f")

def hjm_curves(a, sigma):
    vol = sigma * np.exp(-a * T_values)
    alpha = sigma * np.exp(-a * T_values) * (sigma / a) * (1 - np.exp(-a * T_values))
    return vol, alpha

vol_init, alpha_init = hjm_curves(0.10, 0.01)

fig_hjm, (ax_hjm_vol, ax_hjm_drift) = plt.subplots(1, 2, figsize=(12, 4))
hjm_vol_ln, = ax_hjm_vol.plot(T_values, vol_init*100, color="steelblue", lw=2)
ax_hjm_vol.set_xlabel("T（年）"); ax_hjm_vol.set_ylabel("vol (%)")
ax_hjm_vol.set_title("HJM ボラティリティ σ(0,T)  a=0.10, σ=0.010", fontsize=9)
ax_hjm_vol.grid(True, alpha=0.3)
hjm_drift_ln, = ax_hjm_drift.plot(T_values, alpha_init*100, color="darkorange", lw=2)
ax_hjm_drift.set_xlabel("T（年）"); ax_hjm_drift.set_ylabel("drift (%)")
ax_hjm_drift.set_title("HJM ドリフト α(0,T)  a=0.10, σ=0.010", fontsize=9)
ax_hjm_drift.grid(True, alpha=0.3)
fig_hjm.tight_layout()


def update_hjm(change):
    a = a_hjm_sl.value
    sig = sigma_hjm_sl.value
    vol, alpha = hjm_curves(a, sig)
    hjm_vol_ln.set_ydata(vol*100)
    hjm_drift_ln.set_ydata(alpha*100)
    ax_hjm_vol.set_title(f"HJM ボラティリティ σ(0,T)  a={a:.2f}, σ={sig:.3f}", fontsize=9)
    ax_hjm_drift.set_title(f"HJM ドリフト α(0,T)  a={a:.2f}, σ={sig:.3f}", fontsize=9)
    ax_hjm_vol.relim(); ax_hjm_vol.autoscale_view()
    ax_hjm_drift.relim(); ax_hjm_drift.autoscale_view()
    fig_hjm.canvas.draw_idle()


for s in [a_hjm_sl, sigma_hjm_sl]:
    s.observe(update_hjm, names="value")

display(widgets.VBox([
    widgets.HBox([a_hjm_sl, sigma_hjm_sl]),
    fig_hjm.canvas,
]))
""")
)

cells.append(
    md(r"""## 3.2 BGM / LIBOR Market Model（Brace-Gatarek-Musiela, 1997）

### モデル化対象

離散 LIBOR レート $L_i(t)$（期間 $[T_i, T_{i+1}]$）の SDE：

$$\frac{dL_i(t)}{L_i(t)} = \mu_i(t)\,dt + \sigma_i(t)\,dW_t$$

### Black 式との整合性

Forward measure $Q^{T_{i+1}}$ の下で：

$$\frac{dL_i(t)}{L_i(t)} = \sigma_i(t)\,dW_t^{T_{i+1}}$$

→ $L_i(T_i) \sim \text{Log-Normal}$ → **市場標準の Black キャップレット式と完全整合**

### HJM との比較

| 比較軸 | HJM | BGM/LMM |
|---|---|---|
| 状態変数 | 連続 $f(t,T)$ | 離散 $\{L_i(t)\}$ |
| 市場商品 | キャップ・スワップション間接的 | キャップ直接キャリブレーション |
| マルコフ性 | 一般になし | なし（相関行列で高次元） |
| 複雑さ | 中 | **高**（蒙地卡羅が主） |""")
)

cells.append(
    code(r"""# --- BGM: Black caplet formula (interactive σ slider) ---
from scipy.stats import norm

def black_caplet(F, K, sigma, T, delta=0.5, disc=None):
    # Black caplet PV = delta * P(0,T+delta) * [F*N(d1) - K*N(d2)]
    # disc: discount factor P(0,T+delta); default: approx exp(-F*(T+delta))
    if disc is None:
        disc = np.exp(-F * (T + delta))
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return delta * disc * (F * norm.cdf(d1) - K * norm.cdf(d2))


strikes = np.linspace(0.01, 0.08, 80)
F_libor = 0.035
T_cap = 1.0

sigma_lmm_sl = widgets.FloatSlider(value=0.25, min=0.05, max=0.60, step=0.01,
                                   description="σ（キャップレットvol）:", style={"description_width": "initial"},
                                   readout_format=".2f")

prices_init = [black_caplet(F_libor, K, 0.25, T_cap) * 10000 for K in strikes]

fig_lmm, ax_lmm = plt.subplots(figsize=(9, 4))
lmm_ln, = ax_lmm.plot(strikes*100, prices_init, color="steelblue", lw=2.5, label="キャップレット価格")
ax_lmm.axvline(x=F_libor*100, color="gray", ls="--", lw=1.2, label="ATM")
ax_lmm.set_xlabel("行使レート（%）"); ax_lmm.set_ylabel("価値（bps）")
ax_lmm.set_title(f"Black キャップレット価格（F={F_libor:.1%}, T={T_cap}Y, σ=0.25）", fontsize=9)
ax_lmm.legend(fontsize=8); ax_lmm.grid(True, alpha=0.3)
fig_lmm.tight_layout()


def update_lmm(change):
    sig = sigma_lmm_sl.value
    prices = [black_caplet(F_libor, K, sig, T_cap) * 10000 for K in strikes]
    lmm_ln.set_ydata(prices)
    ax_lmm.set_title(f"Black キャップレット価格（F={F_libor:.1%}, T={T_cap}Y, σ={sig:.2f}）", fontsize=9)
    ax_lmm.relim(); ax_lmm.autoscale_view()
    fig_lmm.canvas.draw_idle()


sigma_lmm_sl.observe(update_lmm, names="value")
display(widgets.VBox([sigma_lmm_sl, fig_lmm.canvas]))
""")
)

# --- Section 3 まとめ: フォワードレートモデル比較 ---
cells.append(
    md(r"""---
## Section 3 まとめ: HJM vs BGM/LMM 比較

**Implied caplet vol のテナー構造**で比較します。

- **HJM（指数型 vol）**: mean reversion $a$ により長期ほど vol が減衰 → 右肩下がり
- **BGM/LMM（フラット vol）**: 全テナーで同一 vol（市場直接キャリブレーション）→ 水平""")
)

cells.append(
    code(r"""# --- HJM vs BGM/LMM: implied caplet vol テナー構造比較（インタラクティブ） ---

T_fwd = np.linspace(0.25, 15, 200)

def hjm_implied_vol(a, sigma, T):
    '''HJM (Hull-White kernel) implied Black caplet vol at expiry T.'''
    integral = sigma**2 / (2 * a) * (1 - np.exp(-2 * a * T))
    return np.sqrt(integral / T)

a_hjm_c_sl = widgets.FloatSlider(value=0.10, min=0.01, max=0.50, step=0.01,
                                 description="a（HJM回帰速度）:", style={"description_width": "initial"})
sigma_hjm_c_sl = widgets.FloatSlider(value=0.20, min=0.001, max=0.60, step=0.001,
                                     description="σ（HJMボラティリティ）:", style={"description_width": "initial"},
                                     readout_format=".3f")
sigma_bgm_c_sl = widgets.FloatSlider(value=0.25, min=0.05, max=0.60, step=0.01,
                                     description="σ（BGMフラットvol）:", style={"description_width": "initial"},
                                     readout_format=".2f")

fig_fwd_cmp, ax_fwd_cmp = plt.subplots(figsize=(9, 4))
hjm_fwd_ln, = ax_fwd_cmp.plot(T_fwd, hjm_implied_vol(0.10, 0.01, T_fwd)*100,
                                color="#7f7f7f", lw=2.5, label="HJM（指数型 vol, 右肩下がり）")
bgm_fwd_ln, = ax_fwd_cmp.plot(T_fwd, np.full_like(T_fwd, 25.0),
                                color="#17becf", lw=2.5, ls="--", label="BGM/LMM（フラット vol）")
ax_fwd_cmp.set_xlabel("テナー T（年）"); ax_fwd_cmp.set_ylabel("Implied vol (%)")
ax_fwd_cmp.set_title("HJM vs BGM/LMM: Implied Caplet Vol のテナー構造", fontsize=9)
ax_fwd_cmp.legend(loc="upper right", fontsize=8); ax_fwd_cmp.grid(True, alpha=0.3)
fig_fwd_cmp.tight_layout()


def update_fwd_cmp(change):
    a = a_hjm_c_sl.value
    sig_h = sigma_hjm_c_sl.value
    sig_b = sigma_bgm_c_sl.value
    hjm_fwd_ln.set_ydata(hjm_implied_vol(a, sig_h, T_fwd)*100)
    bgm_fwd_ln.set_ydata(np.full_like(T_fwd, sig_b*100))
    ax_fwd_cmp.relim(); ax_fwd_cmp.autoscale_view()
    fig_fwd_cmp.canvas.draw_idle()


for s in [a_hjm_c_sl, sigma_hjm_c_sl, sigma_bgm_c_sl]:
    s.observe(update_fwd_cmp, names="value")

display(widgets.VBox([
    widgets.HBox([a_hjm_c_sl, sigma_hjm_c_sl, sigma_bgm_c_sl]),
    fig_fwd_cmp.canvas,
]))
""")
)

# ===========================================================================
# Section 4: 全モデル比較（核心）
# ===========================================================================

cells.append(
    md(r"""---
# Section 4: 【核心】全モデルで共通カーブへのフィット比較

Dropdown でカーブパターンを選択すると、9モデルのフィット結果が一括更新されます。

- **均衡モデル**（Vasicek / CIR / Rendleman-Bartter）: 最小二乗でパラメータ推定 → 近似フィット
- **無裁定モデル**（Ho-Lee / Hull-White / BDT / BK）: θ_t を解析的・数値的に決定 → 完全フィット""")
)

cells.append(
    code(r"""# ===================================================================
# Section 4: Model calibration functions
# ===================================================================

# ---------------------------------------------------------------
# 4.1 Equilibrium models: least-squares calibration
# ---------------------------------------------------------------

# vasicek_zero_curve is defined once above (Section 1 analytical helper).

def cir_zero_curve(kappa, theta, sigma, r0, tenors):
    '''CIR closed-form zero curve.'''
    gamma = np.sqrt(kappa**2 + 2 * sigma**2)
    num = 2 * gamma * np.exp(0.5 * (kappa + gamma) * tenors)
    den = (kappa + gamma) * (np.exp(gamma * tenors) - 1) + 2 * gamma
    A = (num / den) ** (2 * kappa * theta / sigma**2)
    B = 2 * (np.exp(gamma * tenors) - 1) / den
    log_P = np.log(A) - B * r0
    return -log_P / tenors


def rb_zero_curve(mu, sigma, r0, tenors):
    # Rendleman-Bartter (GBM): dr = mu*r dt + sigma*r dW
    # Mean-path zero rate: z0(T) = r0*(exp(mu*T)-1)/(mu*T)
    # Jensen convexity correction (small-sigma, 2nd-order cumulant):
    #   -log P(0,T) ≈ E[integral r dt] - (1/2)*Var[integral r dt]
    #   Var ≈ sigma^2 * z0^2 * T^3/3  =>  correction = sigma^2*z0^2*T^2/6
    with np.errstate(divide="ignore", invalid="ignore"):
        z0 = r0 * np.where(
            np.abs(mu) < 1e-10,
            np.ones_like(tenors),
            (np.exp(mu * tenors) - 1) / (mu * tenors),
        )
    convexity = sigma**2 * z0**2 * tenors**2 / 6.0
    return np.maximum(z0 - convexity, 0.0)


def fit_vasicek(market_zr, tenors, r0_guess=None):
    '''Least-squares calibration of Vasicek to market zero rates.'''
    r0 = market_zr[0] if r0_guess is None else r0_guess
    def obj(params):
        kappa, theta, sigma = params
        if kappa <= 0 or sigma <= 0:
            return 1e9
        model_zr = vasicek_zero_curve(kappa, theta, sigma, r0, tenors)
        return np.sum((model_zr - market_zr) ** 2)
    res = minimize(obj, x0=[0.3, market_zr[-1], 0.015],
                   method="Nelder-Mead",
                   options={"maxiter": 5000, "xatol": 1e-8, "fatol": 1e-10})
    k, th, sig = np.abs(res.x)
    return k, th, sig, r0


def fit_cir(market_zr, tenors, r0_guess=None):
    '''Least-squares calibration of CIR to market zero rates.'''
    r0 = market_zr[0] if r0_guess is None else r0_guess
    def obj(params):
        kappa, theta, sigma = params
        if kappa <= 0 or theta <= 0 or sigma <= 0:
            return 1e9
        if 2 * kappa * theta <= sigma**2:   # Feller violated
            return 1e9
        model_zr = cir_zero_curve(kappa, theta, sigma, r0, tenors)
        if np.any(np.isnan(model_zr)) or np.any(np.isinf(model_zr)):
            return 1e9
        return np.sum((model_zr - market_zr) ** 2)
    res = minimize(obj, x0=[0.3, market_zr[-1], 0.01],
                   method="Nelder-Mead",
                   options={"maxiter": 5000, "xatol": 1e-8, "fatol": 1e-10})
    k, th, sig = np.abs(res.x)
    return k, th, sig, r0


def fit_rb(market_zr, tenors, r0_guess=None):
    '''Least-squares calibration of Rendleman-Bartter to market zero rates.'''
    r0 = market_zr[0] if r0_guess is None else r0_guess
    def obj(params):
        mu, sigma = params
        model_zr = rb_zero_curve(mu, sigma, r0, tenors)
        if np.any(np.isnan(model_zr)) or np.any(np.isinf(model_zr)):
            return 1e9
        return np.sum((model_zr - market_zr) ** 2)
    res = minimize(obj, x0=[0.02, 0.05], method="Nelder-Mead",
                   options={"maxiter": 5000})
    mu, sig = res.x
    return mu, sig, r0


# ---------------------------------------------------------------
# 4.2 Arbitrage-free models: theta calibration
# ---------------------------------------------------------------

def calibrate_ho_lee(market_zr, tenors, sigma=0.01):
    # Piecewise-constant θ bootstrap → evaluate log P at calibration nodes.
    # RMSE ≈ 0 by construction (numerical precision ~1e-12), not by copy.
    theta = calibrate_hl_theta(market_zr, tenors, sigma)
    r0 = market_zr[0]
    return np.array([-hl_logP(theta, tenors, r0, sigma, T) / T for T in tenors])


def calibrate_hull_white(market_zr, tenors, a=0.10, sigma=0.01):
    # Piecewise-constant θ bootstrap → evaluate log P at calibration nodes.
    # RMSE ≈ 0 by construction (numerical precision ~1e-12), not by copy.
    theta = calibrate_hw_theta(market_zr, tenors, a, sigma)
    r0 = market_zr[0]
    return np.array([-hw_logP(theta, tenors, r0, a, sigma, T) / T for T in tenors])


def bdt_bootstrap(market_zr, tenors, sigma_const=0.15):
    '''
    BDT bootstrap: calibrate theta_i at each tenor to match market zero bond price.

    We use a simplified 1-factor continuous BDT approximation:
        ln r_t = x_t, where dx_t = theta_t dt + sigma dW
        => r_t = exp(x_t)  [log-normal]

    For each tenor T_i, we find theta_i such that:
        E^Q[exp(-integral_0^{T_i} r_s ds)] = P^M(0, T_i)

    Monte Carlo approximation with N_paths paths, using previously calibrated theta values.
    We use a simple step-by-step bootstrap in the log-space.
    '''
    rng = np.random.default_rng(0)
    N_paths = 2000
    N_steps_per_year = 50

    # Discretize to fine grid
    T_max = tenors[-1]
    N_total = int(T_max * N_steps_per_year)
    dt = T_max / N_total
    t_grid = np.linspace(0, T_max, N_total + 1)

    # Theta piecewise-constant on tenor intervals
    theta_vals = np.zeros(len(tenors))
    x0 = np.log(market_zr[0])  # initial log-rate

    # Pre-allocate paths (log-rates)
    x_paths = np.full((N_paths, N_total + 1), x0)

    target_idx = 0   # which tenor we're currently calibrating

    def simulate_forward(theta_arr, up_to_step):
        '''Simulate x paths up to given step index using theta_arr (one per tenor segment).'''
        rng2 = np.random.default_rng(0)
        x = np.full(N_paths, x0)
        for step in range(up_to_step):
            t_now = step * dt
            # Find which tenor segment we're in
            seg = np.searchsorted(tenors, t_now, side="right") - 1
            seg = np.clip(seg, 0, len(tenors) - 1)
            th = theta_arr[seg]
            dW = rng2.normal(0, np.sqrt(dt), N_paths)
            x = x + th * dt + sigma_const * dW
        return x

    def price_bond(theta_arr, tenor_target):
        '''Monte Carlo price of zero bond to tenor_target.'''
        rng3 = np.random.default_rng(0)
        N_steps = int(tenor_target * N_steps_per_year)
        dt_loc = tenor_target / N_steps
        x = np.full(N_paths, x0)
        log_disc = np.zeros(N_paths)
        for step in range(N_steps):
            t_now = step * dt_loc
            seg = np.searchsorted(tenors, t_now, side="right") - 1
            seg = np.clip(seg, 0, len(tenors) - 1)
            th = theta_arr[seg]
            dW = rng3.normal(0, np.sqrt(dt_loc), N_paths)
            r_cur = np.exp(x)
            log_disc -= r_cur * dt_loc
            x = x + th * dt_loc + sigma_const * dW
        return np.mean(np.exp(log_disc))

    P_market = np.exp(-market_zr * tenors)

    for i, T_i in enumerate(tenors):
        P_target = P_market[i]
        def obj_bdt(theta_i_val):
            theta_try = theta_vals.copy()
            theta_try[i] = theta_i_val[0]
            P_model = price_bond(theta_try, T_i)
            return (P_model - P_target) ** 2

        from scipy.optimize import minimize as sp_min
        res = sp_min(obj_bdt, x0=[0.0], method="Nelder-Mead",
                     options={"xatol": 1e-5, "fatol": 1e-8, "maxiter": 200})
        theta_vals[i] = res.x[0]

    # Compute model zero rates: P(0,Ti) → r(Ti)
    model_zr = np.zeros(len(tenors))
    for i, T_i in enumerate(tenors):
        P_model = price_bond(theta_vals, T_i)
        model_zr[i] = -np.log(max(P_model, 1e-10)) / T_i

    return model_zr


def bk_bootstrap(market_zr, tenors, a_bk=0.1, sigma_bk=0.15):
    '''
    BK bootstrap: same as BDT but with mean reversion in log-rate.
    dx = (theta(t) - a * x) dt + sigma dW  where x = ln r
    '''
    rng = np.random.default_rng(0)
    N_paths = 2000
    N_steps_per_year = 50

    T_max = tenors[-1]
    x0 = np.log(market_zr[0])
    theta_vals = np.zeros(len(tenors))
    P_market = np.exp(-market_zr * tenors)

    def price_bond_bk(theta_arr, tenor_target):
        rng3 = np.random.default_rng(0)
        N_steps = int(tenor_target * N_steps_per_year)
        dt_loc = tenor_target / N_steps
        x = np.full(N_paths, x0)
        log_disc = np.zeros(N_paths)
        for step in range(N_steps):
            t_now = step * dt_loc
            seg = np.searchsorted(tenors, t_now, side="right") - 1
            seg = np.clip(seg, 0, len(tenors) - 1)
            th = theta_arr[seg]
            dW = rng3.normal(0, np.sqrt(dt_loc), N_paths)
            r_cur = np.exp(x)
            log_disc -= r_cur * dt_loc
            x = x + (th - a_bk * x) * dt_loc + sigma_bk * dW
        return np.mean(np.exp(log_disc))

    for i, T_i in enumerate(tenors):
        P_target = P_market[i]
        def obj_bk(theta_i_val):
            theta_try = theta_vals.copy()
            theta_try[i] = theta_i_val[0]
            P_model = price_bond_bk(theta_try, T_i)
            return (P_model - P_target) ** 2
        from scipy.optimize import minimize as sp_min
        res = sp_min(obj_bk, x0=[0.0], method="Nelder-Mead",
                     options={"xatol": 1e-5, "fatol": 1e-8, "maxiter": 200})
        theta_vals[i] = res.x[0]

    model_zr = np.zeros(len(tenors))
    for i, T_i in enumerate(tenors):
        P_model = price_bond_bk(theta_vals, T_i)
        model_zr[i] = -np.log(max(P_model, 1e-10)) / T_i

    return model_zr


# ---------------------------------------------------------------
# 4.5 Piecewise-θ bootstrap for Ho-Lee and Hull-White
#     Enables dense-grid forward curve computation in Section 4.2
# ---------------------------------------------------------------

def calibrate_hl_theta(market_zr, tenors, sigma=0.01):
    # Ho-Lee piecewise-constant θ bootstrap.
    # log P(0,T) = -r0*T - integral_0^T (T-s)*theta(s) ds + sigma^2*T^3/6
    r0 = market_zr[0]
    log_P_mkt = -market_zr * tenors
    theta = np.zeros(len(tenors))
    for n in range(len(tenors)):
        Tn = tenors[n]
        prev = 0.0
        for i in range(n):
            t_lo = tenors[i-1] if i > 0 else 0.0
            t_hi = tenors[i]
            prev += theta[i] * (t_hi - t_lo) * (Tn - 0.5*(t_lo + t_hi))
        t_lo_n = tenors[n-1] if n > 0 else 0.0
        dt_n = Tn - t_lo_n
        rhs = -log_P_mkt[n] - r0 * Tn - prev + sigma**2 * Tn**3 / 6.0
        theta[n] = rhs / (dt_n**2 / 2.0)
    return theta


def hl_logP(theta, tenors, r0, sigma, T):
    # log P^{HL}(0,T) at arbitrary T using piecewise-constant theta
    if T <= 1e-12:
        return 0.0
    idx = max(0, min(int(np.searchsorted(tenors, T, side='right')) - 1, len(tenors)-1))
    integral = 0.0
    for i in range(idx):
        t_lo = tenors[i-1] if i > 0 else 0.0
        t_hi = tenors[i]
        integral += theta[i] * (t_hi - t_lo) * (T - 0.5*(t_lo + t_hi))
    t_lo_m = tenors[idx-1] if idx > 0 else 0.0
    integral += theta[idx] * (T - t_lo_m)**2 / 2.0
    return -r0 * T - integral + sigma**2 * T**3 / 6.0


def _hw_int_B(t_lo, t_hi, T, a):
    # integral_{t_lo}^{t_hi} B(s,T; a) ds,  B(s,T) = (1-exp(-a(T-s)))/a
    # = (t_hi-t_lo)/a + (exp(-a(T-t_lo)) - exp(-a(T-t_hi))) / a^2
    return (t_hi - t_lo) / a + (np.exp(-a*(T - t_lo)) - np.exp(-a*(T - t_hi))) / a**2


def _hw_var(T, a, sigma):
    # (sigma^2/2) * integral_0^T B(s,T)^2 ds  (convexity correction)
    return (sigma**2 / (2*a**2)) * (T - 2*(1 - np.exp(-a*T))/a + (1 - np.exp(-2*a*T))/(2*a))


def calibrate_hw_theta(market_zr, tenors, a=0.10, sigma=0.01):
    # Hull-White piecewise-constant θ bootstrap.
    # log P(0,T) = integral_0^T theta(s)*B(s,T) ds + Var(T) - B(T)*r0
    r0 = market_zr[0]
    log_P_mkt = -market_zr * tenors
    theta = np.zeros(len(tenors))
    def Bfn(T_): return (1 - np.exp(-a*T_)) / a
    for n in range(len(tenors)):
        Tn = tenors[n]
        prev = 0.0
        for i in range(n):
            t_lo = tenors[i-1] if i > 0 else 0.0
            t_hi = tenors[i]
            prev += theta[i] * _hw_int_B(t_lo, t_hi, Tn, a)
        t_lo_n = tenors[n-1] if n > 0 else 0.0
        coeff = _hw_int_B(t_lo_n, Tn, Tn, a)
        rhs = log_P_mkt[n] + r0 * Bfn(Tn) - prev - _hw_var(Tn, a, sigma)
        theta[n] = rhs / coeff
    return theta


def hw_logP(theta, tenors, r0, a, sigma, T):
    # log P^{HW}(0,T) at arbitrary T using piecewise-constant theta
    if T <= 1e-12:
        return 0.0
    def Bfn(T_): return (1 - np.exp(-a*T_)) / a
    idx = max(0, min(int(np.searchsorted(tenors, T, side='right')) - 1, len(tenors)-1))
    integral = 0.0
    for i in range(idx):
        t_lo = tenors[i-1] if i > 0 else 0.0
        t_hi = tenors[i]
        integral += theta[i] * _hw_int_B(t_lo, t_hi, T, a)
    t_lo_m = tenors[idx-1] if idx > 0 else 0.0
    integral += theta[idx] * _hw_int_B(t_lo_m, T, T, a)
    return integral + _hw_var(T, a, sigma) - Bfn(T) * r0


print("Section 4 calibration functions defined.")
print("Note: BDT/BK Monte Carlo bootstrap may take ~1-2 minutes per curve pattern.")
""")
)

cells.append(
    code(r"""# ===================================================================
# Section 4: Pre-compute all model fits for all patterns
# (Run once; results cached in dicts for interactive display)
# ===================================================================

import warnings
warnings.filterwarnings("ignore")

ALL_PATTERNS = list(ZERO_RATES.keys())

# Storage
fit_results = {p: {} for p in ALL_PATTERNS}
fit_params  = {p: {} for p in ALL_PATTERNS}   # calibrated parameters for dense-grid eval
rmse_table  = {p: {} for p in ALL_PATTERNS}

def rmse(market, model):
    return np.sqrt(np.mean((market - model)**2)) * 10000  # in bps

def mad(market, model):
    return np.mean(np.abs(market - model)) * 10000  # in bps

for pattern in ALL_PATTERNS:
    mzr = ZERO_RATES[pattern]
    r0 = mzr[0]
    print(f"\n--- Fitting pattern: {pattern} ---")

    # Vasicek
    k, th, sig, r0v = fit_vasicek(mzr, TENORS)
    zr_v = vasicek_zero_curve(k, th, sig, r0v, TENORS)
    fit_results[pattern]["Vasicek"] = zr_v
    fit_params[pattern]["Vasicek"]  = (k, th, sig, r0v)
    rmse_table[pattern]["Vasicek"] = rmse(mzr, zr_v)
    print(f"  Vasicek RMSE={rmse(mzr,zr_v):.2f} bps  (κ={k:.3f}, θ={th:.4f}, σ={sig:.4f})")

    # CIR
    k, th, sig, r0c = fit_cir(mzr, TENORS)
    zr_c = cir_zero_curve(k, th, sig, r0c, TENORS)
    fit_results[pattern]["CIR"] = zr_c
    fit_params[pattern]["CIR"]  = (k, th, sig, r0c)
    rmse_table[pattern]["CIR"] = rmse(mzr, zr_c)
    print(f"  CIR    RMSE={rmse(mzr,zr_c):.2f} bps  (κ={k:.3f}, θ={th:.4f}, σ={sig:.4f})")

    # Rendleman-Bartter
    mu, sig_rb, r0rb = fit_rb(mzr, TENORS)
    zr_rb = rb_zero_curve(mu, sig_rb, r0rb, TENORS)
    fit_results[pattern]["RB"] = zr_rb
    fit_params[pattern]["RB"]  = (mu, sig_rb, r0rb)
    rmse_table[pattern]["RB"] = rmse(mzr, zr_rb)
    print(f"  RB     RMSE={rmse(mzr,zr_rb):.2f} bps  (μ={mu:.4f}, σ={sig_rb:.4f})")

    # Ho-Lee (piecewise-θ bootstrap: exact fit, RMSE ≈ 0 by model construction)
    zr_hl = calibrate_ho_lee(mzr, TENORS)
    fit_results[pattern]["Ho-Lee"] = zr_hl
    rmse_table[pattern]["Ho-Lee"] = rmse(mzr, zr_hl)
    print(f"  Ho-Lee RMSE={rmse_table[pattern]['Ho-Lee']:.2e} bps  (numerical precision)")

    # Hull-White (piecewise-θ bootstrap: exact fit, RMSE ≈ 0 by model construction)
    zr_hw = calibrate_hull_white(mzr, TENORS)
    fit_results[pattern]["Hull-White"] = zr_hw
    rmse_table[pattern]["Hull-White"] = rmse(mzr, zr_hw)
    print(f"  HW     RMSE={rmse_table[pattern]['Hull-White']:.2e} bps  (numerical precision)")

    # BDT (MC bootstrap)
    print(f"  BDT    calibrating... (MC bootstrap, may take ~30s)")
    zr_bdt = bdt_bootstrap(mzr, TENORS)
    fit_results[pattern]["BDT"] = zr_bdt
    rmse_table[pattern]["BDT"] = rmse(mzr, zr_bdt)
    print(f"  BDT    RMSE={rmse_table[pattern]['BDT']:.2f} bps")

    # BK (MC bootstrap with mean reversion)
    print(f"  BK     calibrating... (MC bootstrap with mean reversion, may take ~30s)")
    zr_bk = bk_bootstrap(mzr, TENORS)
    fit_results[pattern]["BK"] = zr_bk
    rmse_table[pattern]["BK"] = rmse(mzr, zr_bk)
    print(f"  BK     RMSE={rmse_table[pattern]['BK']:.2f} bps")

    # HJM / BGM: exact fit (calibrated by construction)
    fit_results[pattern]["HJM"] = mzr.copy()
    fit_results[pattern]["BGM/LMM"] = mzr.copy()
    rmse_table[pattern]["HJM"] = 0.0
    rmse_table[pattern]["BGM/LMM"] = 0.0

print("\nAll calibrations complete.")

# θ arrays for dense-grid forward curve (Section 4.2)
# Note: calibrate_ho_lee / calibrate_hull_white above already call these internally;
# here we store the θ arrays explicitly for the forward curve chart.
hl_theta_store = {p: calibrate_hl_theta(ZERO_RATES[p], TENORS, sigma=0.01) for p in ALL_PATTERNS}
hw_theta_store = {p: calibrate_hw_theta(ZERO_RATES[p], TENORS, a=0.10, sigma=0.01) for p in ALL_PATTERNS}
print("HL / HW θ arrays stored for Section 4.2.")
""")
)

cells.append(
    code(r"""# ===================================================================
# Section 4: All model fits — 4 curve patterns simultaneously
# ===================================================================

_MDL_STYLES = {
    "Vasicek":    ("#1f77b4", "-",   2),
    "CIR":        ("#ff7f0e", "-",   2),
    "RB":         ("#2ca02c", "-",   2),
    "Ho-Lee":     ("#d62728", "--",  2),
    "Hull-White": ("#9467bd", "--",  2),
    "BDT":        ("#8c564b", ":",   2),
    "BK":         ("#e377c2", ":",   2),
    "HJM":        ("#7f7f7f", "-.",  2),
    "BGM/LMM":    ("#17becf", "-.",  2),
}

fig_sec4, axes_sec4 = plt.subplots(2, 2, figsize=(14, 10))
axes_sec4 = axes_sec4.flatten()

for idx, p in enumerate(ALL_PATTERNS):
    ax = axes_sec4[idx]
    mzr = ZERO_RATES[p] * 100
    y_lo = mzr.min() - 0.5
    y_hi = mzr.max() + 1.5

    ax.plot(TENORS, mzr, color="black", lw=3, marker="D", ms=6,
            label="Market", zorder=10)
    for mn, (color, ls, lw) in _MDL_STYLES.items():
        yzr = np.clip(fit_results[p][mn] * 100, y_lo - 1, y_hi + 1)
        ax.plot(TENORS, yzr, color=color, ls=ls, lw=lw, marker="o", ms=3, label=mn)

    ax.set_ylim(y_lo, y_hi)
    ax.set_title(CURVE_LABELS[p], fontsize=10)
    ax.set_xlabel("テナー（年）")
    ax.set_ylabel("ゼロレート（%）")
    ax.grid(True, alpha=0.3)

handles, labels = axes_sec4[0].get_legend_handles_labels()
fig_sec4.legend(handles, labels, loc="lower center", ncol=5, fontsize=8,
                bbox_to_anchor=(0.5, 0.0))
fig_sec4.suptitle("全モデルフィット比較（4カーブパターン）", fontsize=13)
fig_sec4.tight_layout(rect=[0, 0.06, 1, 0.97])
plt.show()
""")
)

cells.append(
    code(r"""# ===================================================================
# Section 4.1: Residual bar chart for equilibrium models — 4 patterns
# ===================================================================

eq_models = ["Vasicek", "CIR", "RB"]
eq_colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
_x = np.arange(len(TENORS))
_bar_w = 0.25

fig_res, axes_res = plt.subplots(2, 2, figsize=(14, 8), sharey=False)
axes_res = axes_res.flatten()

for idx, p in enumerate(ALL_PATTERNS):
    ax = axes_res[idx]
    mzr = ZERO_RATES[p]
    for k, (model, color) in enumerate(zip(eq_models, eq_colors)):
        res_bps = (fit_results[p][model] - mzr) * 10000
        ax.bar(_x + k*_bar_w - _bar_w, res_bps, _bar_w,
               color=color, alpha=0.75, label=model)
    ax.axhline(0, color="black", lw=1)
    ax.set_xticks(_x)
    ax.set_xticklabels([f"{t:.2f}" for t in TENORS], rotation=45, fontsize=8)
    ax.set_xlabel("テナー（年）")
    ax.set_ylabel("残差（bps）")
    ax.set_title(f"均衡モデル フィット残差（{CURVE_LABELS[p]}）", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")

fig_res.suptitle("均衡モデル フィット残差（4カーブパターン）", fontsize=13)
fig_res.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()
""")
)

cells.append(
    code(r"""# ===================================================================
# Section 4.2: 6M フォワードカーブ比較（dense grid）
# ===================================================================
# f(T, T+0.5) = [log P(0,T) - log P(0,T+0.5)] / 0.5
# Equilibrium : analytical log-P formula at any T
# Ho-Lee / HW : piecewise-θ bootstrap → exact log-P at any T
# BDT / BK    : cubic spline on 10 calibration points (MC noise baked in)
# HJM / BGM   : exact fit = market → omitted (identical to market spline)
# ===================================================================
from scipy.interpolate import CubicSpline

t_fwd = np.arange(0.25, 9.75, 0.25)   # T: 0.25 → 9.50 (step 0.25)

def _6m_fwd(logP_fn, t_arr):
    # f(T, T+0.5) array in %
    return np.array([(logP_fn(T) - logP_fn(T + 0.5)) / 0.5 for T in t_arr]) * 100

def _vas_logP(k, th, sig, r0, T):
    B = (1 - np.exp(-k*T)) / k
    A = (B - T)*(k**2*th - 0.5*sig**2)/k**2 - sig**2*B**2/(4*k)
    return A - B*r0

def _cir_logP(k, th, sig, r0, T):
    gam = np.sqrt(k**2 + 2*sig**2)
    num = 2*gam*np.exp(0.5*(k+gam)*T)
    den = (k+gam)*(np.exp(gam*T)-1) + 2*gam
    A   = (num/den)**(2*k*th/sig**2)
    B   = 2*(np.exp(gam*T)-1)/den
    return np.log(A) - B*r0

_fwd_styles = {
    "Market":     ("black",    "-",   3.0),
    "Vasicek":    ("#1f77b4",  "-",   1.8),
    "CIR":        ("#ff7f0e",  "-",   1.8),
    "RB":         ("#2ca02c",  "-",   1.8),
    "Ho-Lee":     ("#d62728",  "--",  1.8),
    "Hull-White": ("#9467bd",  "--",  1.8),
    "BDT":        ("#8c564b",  ":",   1.8),
    "BK":         ("#e377c2",  ":",   1.8),
}

fig_fwd, axes_fwd = plt.subplots(2, 2, figsize=(14, 10))
axes_fwd = axes_fwd.flatten()

for idx, p in enumerate(ALL_PATTERNS):
    ax   = axes_fwd[idx]
    mzr  = ZERO_RATES[p]
    r0_p = mzr[0]

    # --- Market spline ---
    cs_mkt   = CubicSpline(TENORS, mzr, extrapolate=True)
    fwd_mkt  = _6m_fwd(lambda T, cs=cs_mkt: -cs(T)*T, t_fwd)
    y_lo = fwd_mkt.min() - 0.5
    y_hi = fwd_mkt.max() + 1.0
    ax.plot(t_fwd, fwd_mkt, color="black", lw=3, label="Market (spline)", zorder=10)

    # --- Vasicek (analytical) ---
    kv, thv, sv, r0v = fit_params[p]["Vasicek"]
    fwd = _6m_fwd(lambda T, k=kv, th=thv, s=sv, r=r0v: _vas_logP(k, th, s, r, T), t_fwd)
    ax.plot(t_fwd, np.clip(fwd, y_lo-1, y_hi+1), color="#1f77b4", ls="-",  lw=1.8, label="Vasicek")

    # --- CIR (analytical) ---
    kc, thc, sc, r0c = fit_params[p]["CIR"]
    fwd = _6m_fwd(lambda T, k=kc, th=thc, s=sc, r=r0c: _cir_logP(k, th, s, r, T), t_fwd)
    ax.plot(t_fwd, np.clip(fwd, y_lo-1, y_hi+1), color="#ff7f0e", ls="-",  lw=1.8, label="CIR")

    # --- RB (spline on 10-pt fit; no closed-form log-P for GBM approximation) ---
    cs_rb = CubicSpline(TENORS, fit_results[p]["RB"], extrapolate=True)
    fwd   = _6m_fwd(lambda T, cs=cs_rb: -cs(T)*T, t_fwd)
    ax.plot(t_fwd, np.clip(fwd, y_lo-1, y_hi+1), color="#2ca02c", ls="-",  lw=1.8, label="RB")

    # --- Ho-Lee (piecewise-θ: shows kinks between calibration nodes) ---
    hl_th = hl_theta_store[p]
    fwd   = _6m_fwd(lambda T, th=hl_th, r=r0_p: hl_logP(th, TENORS, r, 0.01, T), t_fwd)
    ax.plot(t_fwd, np.clip(fwd, y_lo-1, y_hi+1), color="#d62728", ls="--", lw=1.8, label="Ho-Lee")

    # --- Hull-White (piecewise-θ: mean reversion smooths the kinks) ---
    hw_th = hw_theta_store[p]
    fwd   = _6m_fwd(lambda T, th=hw_th, r=r0_p: hw_logP(th, TENORS, r, 0.10, 0.01, T), t_fwd)
    ax.plot(t_fwd, np.clip(fwd, y_lo-1, y_hi+1), color="#9467bd", ls="--", lw=1.8, label="Hull-White")

    # --- BDT (spline on 10 MC-calibrated points) ---
    cs_bdt = CubicSpline(TENORS, fit_results[p]["BDT"], extrapolate=True)
    fwd    = _6m_fwd(lambda T, cs=cs_bdt: -cs(T)*T, t_fwd)
    ax.plot(t_fwd, np.clip(fwd, y_lo-1, y_hi+1), color="#8c564b", ls=":",  lw=1.8, label="BDT")

    # --- BK (spline on 10 MC-calibrated points) ---
    cs_bk = CubicSpline(TENORS, fit_results[p]["BK"], extrapolate=True)
    fwd   = _6m_fwd(lambda T, cs=cs_bk: -cs(T)*T, t_fwd)
    ax.plot(t_fwd, np.clip(fwd, y_lo-1, y_hi+1), color="#e377c2", ls=":",  lw=1.8, label="BK")

    ax.set_ylim(y_lo, y_hi)
    ax.set_title(CURVE_LABELS[p], fontsize=10)
    ax.set_xlabel("テナー T（年）")
    ax.set_ylabel("6M フォワードレート（%）")
    ax.axhline(0, color="gray", lw=0.5, ls="--")
    ax.grid(True, alpha=0.3)

handles, labels = axes_fwd[0].get_legend_handles_labels()
fig_fwd.legend(handles, labels, loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, 0.0))
fig_fwd.suptitle(
    "6M フォワードカーブ比較\n"
    "（Ho-Lee / HW は区分定数 θ → キャリブレーションノード間でキンクが出現、"
    "HJM・BGM は市場と完全一致のため省略）",
    fontsize=11)
fig_fwd.tight_layout(rect=[0, 0.06, 1, 0.95])
plt.show()
""")
)

cells.append(
    code(r"""# ===================================================================
# Section 4.3: RMSE / MAD heatmap（9 models × 4 patterns）
# ===================================================================

model_names_all = list(list(rmse_table[ALL_PATTERNS[0]].keys()))
pattern_labels = [CURVE_LABELS[p] for p in ALL_PATTERNS]

# Build RMSE matrix
rmse_matrix = []
for model in model_names_all:
    row = [rmse_table[p][model] for p in ALL_PATTERNS]
    rmse_matrix.append(row)

fig_heat, ax_heat = plt.subplots(figsize=(8, 6))
sns.heatmap(np.array(rmse_matrix), xticklabels=pattern_labels, yticklabels=model_names_all,
            annot=True, fmt=".1f", cmap="RdYlGn_r", vmin=0, ax=ax_heat,
            annot_kws={"size": 10})
ax_heat.set_xlabel("カーブパターン"); ax_heat.set_ylabel("モデル")
ax_heat.set_title("全モデル × 全カーブパターン: フィット誤差 RMSE（bps）\n（赤=大, 緑=小, 0=完全フィット）",
                  fontsize=9)
fig_heat.tight_layout()
plt.show()

df_err = pd.DataFrame(rmse_matrix, index=model_names_all, columns=ALL_PATTERNS)
df_err.columns = [CURVE_LABELS[p] for p in ALL_PATTERNS]
df_err = df_err.round(2)
print("\nRMSE 一覧（bps）:")
display(df_err.style.background_gradient(cmap="RdYlGn_r").format("{:.2f}"))
""")
)

# ===========================================================================
# Section 5: モデル間対比
# ===========================================================================

cells.append(
    md(r"""---
# Section 5: モデル間の対比解説""")
)

cells.append(
    code(r"""# --- Section 5: 5軸対比テーブル ---
comparison_data = {
    "比較軸": [
        "Vasicek vs CIR",
        "均衡 vs 無裁定",
        "Ho-Lee vs Hull-White",
        "Short-rate vs HJM",
        "HJM vs BGM/LMM",
    ],
    "観点1": [
        "拡散項: 定数 σ",
        "カーブフィット: ×",
        "Mean reversion: なし",
        "状態変数: r_t（1点）",
        "フォワードレート: 連続 f(t,T)",
    ],
    "観点2": [
        "拡散項: σ√r_t",
        "カーブフィット: ○（θ_t で完全フィット）",
        "Mean reversion: あり（a・r_t）",
        "状態変数: f(t,T)（カーブ全体）",
        "LIBOR: 離散 L_i(t)",
    ],
    "主な違い": [
        "負金利あり(V) vs なし(CIR), Feller 条件",
        "解析性・シンプルさ vs 市場整合性",
        "長期の金利分散: 無制限(HL) vs 制限あり(HW)",
        "マルコフ性: SR は通常○、HJM は一般に×",
        "キャリブレーション: HJM は間接的、BGM は直接",
    ],
}

df_cmp = pd.DataFrame(comparison_data)
display(df_cmp.style.set_caption("モデル間対比（5軸）")
              .set_properties(**{"text-align": "left"})
              .hide(axis="index"))
""")
)

# ===========================================================================
# Section 6: まとめ表
# ===========================================================================

cells.append(
    md(r"""---
# Section 6: まとめ表（9モデル × 9観点）""")
)

cells.append(
    code(r"""# --- Section 6: 9×9 summary table ---
summary_data = {
    "モデル":           ["Vasicek", "CIR", "Rendleman-Bartter",
                         "Ho-Lee", "Hull-White", "BDT", "BK", "HJM", "BGM/LMM"],
    "状態変数":         ["r_t", "r_t", "r_t",
                         "r_t", "r_t", "ln r_t", "ln r_t", "f(t,T)", "L_i(t)"],
    "分類":             ["均衡SR", "均衡SR", "均衡SR",
                         "無裁定SR", "無裁定SR", "無裁定SR", "無裁定SR",
                         "フォワード", "フォワード"],
    "初期カーブフィット": ["×", "×", "×", "○", "○", "○", "○", "○", "○"],
    "Mean reversion":   ["○", "○", "×", "×", "○", "△", "○", "依存", "×"],
    "負金利":           ["○", "×", "×", "○", "○", "×", "×", "依存", "×"],
    "解析しやすさ":     ["◎", "○", "○", "○", "◎", "△", "△", "△", "△"],
    "キャリブレーション": ["△", "△", "△", "○", "◎", "○", "○", "△", "◎"],
    "主な用途":         [
        "教育・シナリオ分析",
        "金利下限あり環境",
        "教育用",
        "シンプル無裁定",
        "金利デリバティブ全般",
        "債券オプション",
        "金利デリバティブ",
        "理論的フレームワーク",
        "キャップ・スワップション",
    ],
    "主な弱点":         [
        "カーブフィットなし",
        "カーブフィットなし",
        "Mean reversionなし",
        "Mean reversionなし",
        "負金利",
        "ツリーのみ・解析解なし",
        "解析解なし",
        "non-Markov",
        "高次元・複雑",
    ],
}

df_summary = pd.DataFrame(summary_data)
display(df_summary.style.set_caption("9モデル × 9観点 まとめ表")
              .set_properties(**{"text-align": "center"})
              .set_properties(subset=["モデル","主な用途","主な弱点"],
                              **{"text-align": "left"})
              .hide(axis="index"))
""")
)

# ===========================================================================
# Section 7: 実務ガイド
# ===========================================================================

cells.append(
    md(r"""---
# Section 7: 実務ガイド — どのモデルを選ぶか？

フローチャートに従ってモデルを選択しましょう。""")
)

cells.append(
    code(r"""# --- Section 7: Decision flowchart (Sankey diagram) ---
# Nodes: questions and model outcomes
node_labels = [
    # Questions (0-4)
    "モデル選択",                 # 0
    "初期カーブフィット必要?",    # 1
    "mean reversion 必要?",       # 2 (Yes branch of Q1=No)
    "負金利 排除したい?",         # 3 (Yes branch of Q1=Yes)
    "BGM/LMM or HJM?",           # 4 (No of Q3)
    # Outcomes (5-13)
    "Vasicek / CIR",             # 5  (Yes Q2, No Q1)
    "Rendleman-Bartter",         # 6  (No Q2, No Q1)
    "Hull-White / BK",           # 7  (No Q3, Yes Q1, Yes MR)
    "Ho-Lee",                    # 8  (No Q3, Yes Q1, No MR)
    "BDT / BK",                  # 9  (Yes Q3)
    "BGM/LMM",                   # 10 (Q4 = BGM)
    "HJM",                       # 11 (Q4 = HJM)
]
source = [0, 1, 1, 2, 2, 3, 3, 4, 4]
target = [1, 2, 3, 5, 6, 4, 9, 10, 11]
values = [10, 5, 5, 2, 3, 3, 2, 2, 1]
labels = ["→", "カーブフィット不要", "カーブフィット必要",
          "MR あり", "MR なし",
          "負金利 OK (HW系)", "負金利 NG (BDT/BK)",
          "汎用性重視 (BGM)", "理論重視 (HJM)"]

fig_flow = go.Figure(go.Sankey(
    arrangement="snap",
    node=dict(
        label=node_labels,
        pad=15,
        thickness=20,
        color=["#4472C4", "#4472C4", "#4472C4", "#4472C4", "#4472C4",
               "#70AD47", "#70AD47", "#ED7D31", "#ED7D31",
               "#FFC000", "#A5A5A5", "#A5A5A5"],
    ),
    link=dict(
        source=source,
        target=target,
        value=values,
        label=labels,
        color=["rgba(70,114,196,0.3)"] * len(source),
    ),
))
fig_flow.update_layout(
    title="実務モデル選択フロー",
    height=500,
    font_size=12,
)
fig_flow.show()
""")
)

cells.append(
    md(r"""## まとめ

| 場面 | 推奨モデル | 理由 |
|---|---|---|
| 教育・直感理解 | Vasicek | 解析解豊富、パラメータ直感的 |
| 負金利排除 | CIR / BDT | Feller 条件 / 対数正規 |
| 金利スワップ価格付け | Hull-White | 完全フィット + mean reversion + 解析解 |
| キャップ・スワップション | BGM/LMM | Black 式と整合、市場直接キャリブレーション |
| 理論研究 | HJM | 最も一般的なフレームワーク |
| ALM（保険・銀行） | Hull-White / CIR | 長期での安定性 |""")
)

# ===========================================================================
# Notebook assembly
# ===========================================================================

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0",
        },
    },
    "cells": cells,
}

# Normalize cell sources: all lines except the last should end with \n
for i, cell in enumerate(nb["cells"]):
    cell["id"] = f"cell-{i:03d}"
    src = cell["source"]
    if isinstance(src, list) and len(src) > 1:
        for i in range(len(src) - 1):
            if not src[i].endswith("\n"):
                src[i] += "\n"
        # Last line: no trailing newline
        if src[-1].endswith("\n"):
            src[-1] = src[-1].rstrip("\n")

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ir_models.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
