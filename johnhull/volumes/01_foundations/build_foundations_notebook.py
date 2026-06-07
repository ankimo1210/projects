"""
build_foundations_notebook.py
=============================
nbformat-dict pattern to generate foundations.ipynb (Hull 11e Ch.13-14).

Usage:
    uv run python build_foundations_notebook.py
"""

import json
import os

# ---------------------------------------------------------------------------
# Cell helpers (same pattern as build_ir_models_notebook.py)
# ---------------------------------------------------------------------------


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.split("\n")}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "source": source.split("\n"),
        "outputs": [],
        "execution_count": None,
    }


cells = []

# ===========================================================================
# Cell 00: title / intro
# ===========================================================================
cells.append(
    md(r"""# 基礎編: 二項ツリーと確率過程（Hull 11e Ch.13–14）

`johnhull/volumes` シリーズ第1冊。デリバティブ価格理論の2つの土台を扱います：

- **Ch.13 二項ツリー** — 裁定なし複製とリスク中立評価、CRRツリー、アメリカン早期行使、BSMへの収束
- **Ch.14 ウィーナー過程と伊藤の補題** — ブラウン運動、一般化ウィーナー過程、GBM、伊藤の補題と対数正規性

> 共通関数は `hullkit` パッケージ（`johnhull/hullkit`）から import します。
> 続編: `notebooks/bsm_chapter15.ipynb`（Ch.15 BSM モデル）""")
)

# Cell 01: matplotlib magic (standalone, ir_models convention)
cells.append(code(r"""%matplotlib widget"""))

# Cell 02: imports
cells.append(
    code(r"""# --- imports & 共通設定 ---
import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
from scipy.stats import lognorm, norm

from hullkit import bsm, mc, nbplot, trees

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()（comm_id エラー対策）""")
)

# ===========================================================================
# Section 1: Ch.13 binomial trees
# ===========================================================================

# Cell 03: §13.1-13.2 one-step tree & risk-neutral valuation
cells.append(
    md(r"""## 1. 1ステップ二項ツリーとリスク中立評価（§13.1–13.2）

株価が1期間で $u$ 倍か $d$ 倍にしか動かないとき、株式 $\Delta$ 株とオプション売り1単位の
ポートフォリオを **無リスク** にできる $\Delta$ が必ず存在します。裁定なし条件から：

$$\Delta = \frac{f_u - f_d}{S_0 u - S_0 d} \quad \text{(13.1)}$$

$$f = e^{-rT}\bigl[p f_u + (1-p) f_d\bigr], \qquad p = \frac{e^{rT} - d}{u - d} \quad \text{(13.2), (13.3)}$$

**重要**: 実世界の上昇確率は価格に一切現れません。$p$ は「全資産の期待収益率が
無リスク金利になる世界（リスク中立世界）」での上昇確率と解釈できます。""")
)

# Cell 04: one-step numeric check (Hull §13.1 example)
cells.append(
    code(r"""# Hull §13.1 の例: S0=20, u=1.1, d=0.9, K=21, r=12%, T=3ヶ月
S0, K, r, T = 20.0, 21.0, 0.12, 0.25
u, d = 1.1, 0.9
fu, fd = max(S0 * u - K, 0), max(S0 * d - K, 0)
p = (np.exp(r * T) - d) / (u - d)             # eq (13.3)
f = np.exp(-r * T) * (p * fu + (1 - p) * fd)  # eq (13.2)
delta = (fu - fd) / (S0 * u - S0 * d)         # eq (13.1)
print(f"リスク中立確率 p = {p:.4f}")
print(f"コール価格 f = {f:.4f}（Hull: 0.633）")
print(f"デルタ Δ = {delta:.4f}（株 {delta:.2f} 株保有でオプション1単位の売りをヘッジ）")""")
)

# Cell 05: replication intuition
cells.append(
    md(r"""### 複製ポートフォリオの直感

$\Delta$ 株ロング + オプション1単位ショートの価値は、上昇時 $S_0 u \Delta - f_u$、
下落時 $S_0 d \Delta - f_d$。eq (13.1) の $\Delta$ はこの2つを**等しく**します。
無リスクなポートフォリオはリスクフリーレートでしか増えない — これだけで価格が決まります。

下のスライダーで $u, d, K, r$ を動かして、$p$・$\Delta$・$f$ の関係を確認してください。""")
)

# Cell 06: interactive one-step tree
cells.append(
    code(r"""# --- 1ステップツリー（インタラクティブ） ---
fig1, ax1 = plt.subplots(figsize=(7, 4))
fig1.canvas.header_visible = False
ax1.set_xlim(-0.35, 1.45)
ax1.set_ylim(-1.6, 1.6)
ax1.axis("off")
ax1.plot([0, 1], [0, 1], "k-", lw=1)
ax1.plot([0, 1], [0, -1], "k-", lw=1)
txt_root = ax1.text(-0.05, 0, "", ha="right", va="center", fontsize=11)
txt_up = ax1.text(1.05, 1, "", ha="left", va="center", fontsize=11)
txt_dn = ax1.text(1.05, -1, "", ha="left", va="center", fontsize=11)

u_sl = widgets.FloatSlider(value=1.1, min=1.01, max=1.5, step=0.01, description="u")
d_sl = widgets.FloatSlider(value=0.9, min=0.5, max=0.99, step=0.01, description="d")
k_sl = widgets.FloatSlider(value=21.0, min=15.0, max=25.0, step=0.5, description="K")
r_sl = widgets.FloatSlider(value=0.12, min=0.0, max=0.3, step=0.01, description="r")

S0_1, T_1 = 20.0, 0.25


def _upd_onestep(change=None):
    u, d, K, r = u_sl.value, d_sl.value, k_sl.value, r_sl.value
    Su, Sd = S0_1 * u, S0_1 * d
    fu, fd = max(Su - K, 0.0), max(Sd - K, 0.0)
    p = (np.exp(r * T_1) - d) / (u - d)
    f = np.exp(-r * T_1) * (p * fu + (1 - p) * fd)
    delta = (fu - fd) / (Su - Sd)
    txt_root.set_text(f"S0={S0_1:.0f}\nf={f:.3f}")
    txt_up.set_text(f"Su={Su:.1f}\nfu={fu:.2f}")
    txt_dn.set_text(f"Sd={Sd:.1f}\nfd={fd:.2f}")
    ax1.set_title(f"コール（T={T_1}年）   p={p:.4f},  Δ={delta:.4f}")
    fig1.canvas.draw_idle()


for w in (u_sl, d_sl, k_sl, r_sl):
    w.observe(_upd_onestep, "value")
_upd_onestep()
display(widgets.VBox([widgets.HBox([u_sl, d_sl]), widgets.HBox([k_sl, r_sl])]), fig1.canvas)""")
)

# Cell 07: §13.3-13.4, 13.7-13.8 multi-step & CRR
cells.append(
    md(r"""## 2. 多ステップツリーと CRR パラメータ化（§13.3–13.4, 13.7–13.8）

多ステップでは各ノードで eq (13.5) を末端から繰り返します（**後退帰納法**）：

$$f = e^{-r\Delta t}\bigl[p f_u + (1-p) f_d\bigr], \qquad p = \frac{a - d}{u - d}, \quad a = e^{(r-q)\Delta t}$$

ツリーをボラティリティ $\sigma$ に整合させる標準的な方法が **CRR パラメータ化**：

$$u = e^{\sigma\sqrt{\Delta t}}, \qquad d = \frac{1}{u} \quad \text{(13.15), (13.16)}$$

測度を実世界からリスク中立に変えても $\sigma$ は変わりません（ギルサノフの定理、§13.7）。""")
)

# Cell 08: two-step & American examples
cells.append(
    code(r"""# Hull Fig 13.3: 2ステップ ヨーロピアンコール（S0=20, K=21, u=1.1, d=0.9, r=12%, Δt=0.25）
_, opt = trees.binomial_tree(20.0, 21.0, 0.12, 0.5, 2, u=1.1, d=0.9)
print(f"2ステップ コール = {opt[0][0]:.4f}（Hull Fig 13.3: 1.2823）")

# Hull Fig 13.5: 2ステップ プット（S0=50, K=52, u=1.2, d=0.8, r=5%, Δt=1年）
_, opt_eu = trees.binomial_tree(50.0, 52.0, 0.05, 2.0, 2, u=1.2, d=0.8, kind="put")
_, opt_am = trees.binomial_tree(50.0, 52.0, 0.05, 2.0, 2, u=1.2, d=0.8, kind="put", american=True)
print(f"ヨーロピアンプット = {opt_eu[0][0]:.4f}（Hull: 4.1923）")
print(f"アメリカンプット   = {opt_am[0][0]:.4f}（Hull Fig 13.5: 5.0894）")
print(f"早期行使プレミアム = {opt_am[0][0] - opt_eu[0][0]:.4f}")
print("※ 本文の値は p を4桁に丸めた計算。丸めなしでは 4.1927 / 5.0896")""")
)

# Cell 09: §13.5 American early exercise
cells.append(
    md(r"""## 3. アメリカンオプションと早期行使（§13.5）

アメリカンオプションでは各ノードで **継続価値**（後退帰納の値）と
**本質的価値**（即時行使価値）を比較し、大きい方を採用します：

$$V = \max\bigl(e^{-r\Delta t}[p V_u + (1-p) V_d],\; \text{intrinsic}\bigr)$$

ディープ ITM のプットでは「いま $K-S$ を受け取って金利で運用する」方が有利になることがあり、
ツリー上では下方のノードで行使が発生します（下図の赤枠ノード）。""")
)

# Cell 10: interactive tree visualization
cells.append(
    code(r"""# --- 多ステップCRRツリーの可視化（赤枠=早期行使ノード） ---
fig2, ax2 = plt.subplots(figsize=(9, 5.5))
fig2.canvas.header_visible = False

n_sl = widgets.IntSlider(value=3, min=2, max=6, description="N")
sig2_sl = widgets.FloatSlider(value=0.3, min=0.1, max=0.6, step=0.05, description="σ")
k2_sl = widgets.FloatSlider(value=52.0, min=30.0, max=70.0, step=1.0, description="K")
kind_dd = widgets.Dropdown(options=["put", "call"], value="put", description="種別")
am_dd = widgets.Dropdown(
    options=[("American", True), ("European", False)], value=True, description="行使"
)

S0_2, R_2, T_2 = 50.0, 0.05, 2.0


def _upd_tree(change=None):
    ax2.clear()
    ax2.axis("off")
    N, sig, K = n_sl.value, sig2_sl.value, k2_sl.value
    u, d = trees.crr_params(sig, T_2 / N)
    stock, option = trees.binomial_tree(
        S0_2, K, R_2, T_2, N, u, d, kind=kind_dd.value, american=am_dd.value
    )

    def intrinsic(s):
        return np.maximum(s - K, 0.0) if kind_dd.value == "call" else np.maximum(K - s, 0.0)

    for i in range(N):
        for j in range(i + 1):
            ax2.plot([i, i + 1], [i - 2 * j, i + 1 - 2 * j], "-", color="0.8", lw=0.8, zorder=1)
            ax2.plot([i, i + 1], [i - 2 * j, i - 1 - 2 * j], "-", color="0.8", lw=0.8, zorder=1)
    for i in range(N + 1):
        exercised = (intrinsic(stock[i]) >= option[i] - 1e-12) & (intrinsic(stock[i]) > 0)
        for j in range(i + 1):
            hit = am_dd.value and i < N and bool(exercised[j])
            ec = "#d62728" if hit else "#1f77b4"
            ax2.text(
                i, i - 2 * j, f"S={stock[i][j]:.1f}\nV={option[i][j]:.2f}",
                ha="center", va="center", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=ec),
            )
    label = "アメリカン" if am_dd.value else "ヨーロピアン"
    ax2.set_title(
        f"CRR {N}ステップ {label}・{kind_dd.value}"
        f"（S0={S0_2:.0f}, r={R_2:.0%}, T={T_2}年, 赤枠=早期行使）"
    )
    ax2.set_xlim(-0.6, N + 0.6)
    fig2.canvas.draw_idle()


for w in (n_sl, sig2_sl, k2_sl, kind_dd, am_dd):
    w.observe(_upd_tree, "value")
_upd_tree()
display(
    widgets.VBox([widgets.HBox([n_sl, sig2_sl, k2_sl]), widgets.HBox([kind_dd, am_dd])]),
    fig2.canvas,
)""")
)

# Cell 11: §13.6 delta on the tree
cells.append(
    md(r"""## 4. ツリー上のデルタ（§13.6）

デルタはノードごとに定義され、時間とともに変化します：

$$\Delta_{i,j} = \frac{V_{i+1,j} - V_{i+1,j+1}}{S_{i+1,j} - S_{i+1,j+1}}$$

静的なヘッジは不可能で、**動的リバランス**が必要です。下表は Hull Fig 13.5 の
アメリカンプット例の各ノードのデルタ。下方ノード（行使域）では $\Delta = -1$ に張り付きます。""")
)

# Cell 12: node-delta table
cells.append(
    code(r"""stock, option = trees.binomial_tree(
    50.0, 52.0, 0.05, 2.0, 2, u=1.2, d=0.8, kind="put", american=True
)
rows = []
for i in range(2):
    for j in range(i + 1):
        delta_ij = (option[i + 1][j] - option[i + 1][j + 1]) / (
            stock[i + 1][j] - stock[i + 1][j + 1]
        )
        rows.append({"ステップ": i, "ノード": f"S={stock[i][j]:.0f}", "Δ": round(float(delta_ij), 4)})
display(pd.DataFrame(rows))
print(f"ルートのΔ（eq 13.1）: {trees.tree_delta(stock, option):.4f}")""")
)

# Cell 13: §13.9 / Appendix 13A convergence
cells.append(
    md(r"""## 5. BSM への収束（§13.9, 付録13A）

ステップ数 $N \to \infty$ で CRR 価格は BSM 公式に収束します（二項分布 → 正規分布）。
誤差はおおむね $O(1/N)$ で、**奇数・偶数ステップで振動**するのが特徴です。
実務では30ステップ以上、500ステップでほぼ BSM に一致します。""")
)

# Cell 14: interactive convergence chart
cells.append(
    code(r"""# --- CRR → BSM 収束（インタラクティブ） ---
fig3, (ax3a, ax3b) = plt.subplots(1, 2, figsize=(10, 4))
fig3.canvas.header_visible = False
NS_CONV = np.arange(2, 201)

sig3_sl = widgets.FloatSlider(value=0.2, min=0.1, max=0.5, step=0.05, description="σ")
k3_sl = widgets.FloatSlider(value=100.0, min=70.0, max=130.0, step=5.0, description="K")

ln_crr, = ax3a.plot([], [], lw=0.9, label="CRR")
ln_bsm = ax3a.axhline(0.0, color="crimson", ls="--", label="BSM")
ln_err, = ax3b.semilogy([], [], lw=0.9)
ax3a.set_xlabel("ステップ数 N")
ax3a.set_ylabel("コール価格")
ax3a.legend()
ax3b.set_xlabel("ステップ数 N")
ax3b.set_ylabel("|CRR − BSM|（log）")


def _upd_conv(change=None):
    sig, K = sig3_sl.value, k3_sl.value
    prices = np.array([trees.crr_price(100.0, K, 0.05, sig, 1.0, int(n)) for n in NS_CONV])
    c_bsm = bsm.call_price(100.0, K, 0.05, sig, 1.0)
    ln_crr.set_data(NS_CONV, prices)
    ln_bsm.set_ydata([c_bsm, c_bsm])
    ln_err.set_data(NS_CONV, np.abs(prices - c_bsm))
    for ax in (ax3a, ax3b):
        ax.relim()
        ax.autoscale_view()
    ax3a.set_title(f"S0=100, r=5%, T=1年   BSM = {c_bsm:.4f}")
    fig3.canvas.draw_idle()


sig3_sl.observe(_upd_conv, "value")
k3_sl.observe(_upd_conv, "value")
_upd_conv()
display(widgets.HBox([sig3_sl, k3_sl]), fig3.canvas)""")
)

# Cell 15: §13.11 extensions
cells.append(
    md(r"""## 6. 指数・通貨・先物オプションへの拡張（§13.11）

リスク中立確率の $a$ パラメータを変えるだけで他の原資産に対応できます：

| 原資産 | $a$ | 意味 |
|---|---|---|
| 配当なし株式 | $e^{r\Delta t}$ | 標準形 |
| 株価指数（配当利回り $q$） | $e^{(r-q)\Delta t}$ | 保有中に配当を受け取る |
| 通貨（外国金利 $r_f$） | $e^{(r-r_f)\Delta t}$ | 外貨は $r_f$ の利回り資産 |
| 先物 | $1$ | 取得コストゼロ → リスク中立成長率ゼロ |

`hullkit` では `q` 引数で統一的に扱います（先物は $q = r$）。""")
)

# Cell 16: extension comparison table
cells.append(
    code(r"""S0_4, K_4, R_4, SIG_4, T_4 = 100.0, 100.0, 0.05, 0.2, 1.0
cases = {
    "非配当株 (q=0)": 0.0,
    "株価指数 (q=3%)": 0.03,
    "通貨 (rf=4%)": 0.04,
    "先物 (a=1 ⇔ q=r)": R_4,
}
rows = []
for name, q in cases.items():
    crr = trees.crr_price(S0_4, K_4, R_4, SIG_4, T_4, 200, q=q)
    ana = bsm.call_price(S0_4, K_4, R_4, SIG_4, T_4, q=q)
    rows.append(
        {"ケース": name, "q": q, "CRR (N=200)": round(crr, 4),
         "解析解": round(ana, 4), "|差|": round(abs(crr - ana), 4)}
    )
display(pd.DataFrame(rows))""")
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
        "language_info": {"name": "python", "version": "3.12.0"},
    },
    "cells": cells,
}

# Normalize cell sources: all lines except the last should end with \n
for cell in nb["cells"]:
    src = cell["source"]
    if isinstance(src, list) and len(src) > 1:
        for i in range(len(src) - 1):
            if not src[i].endswith("\n"):
                src[i] += "\n"
        if src[-1].endswith("\n"):
            src[-1] = src[-1].rstrip("\n")

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "foundations.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
