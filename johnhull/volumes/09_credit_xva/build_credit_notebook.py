"""
build_credit_notebook.py
================================
nbformat-dict pattern to generate credit_xva.ipynb (Hull 11e Ch.24, 25, 9).

Usage:
    uv run python build_credit_notebook.py
"""

import json
import os

# ---------------------------------------------------------------------------
# Cell helpers (same pattern as build_foundations_notebook.py)
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
    md(r"""# 信用リスクと XVA（Hull 11e Ch.24, 25, 9）

`johnhull/volumes` シリーズ第9冊。デフォルトの確率と価格：

- **信用リスク（Ch.24）** — ハザードレート、Merton 構造モデル、ガウスコピュラ、信用 VaR
- **クレジット・デリバティブ（Ch.25）** — CDS、インデックス、CDO トランシェ
- **XVA（Ch.9）** — CVA / DVA / FVA / MVA / KVA

> 共通関数は `hullkit`（credit / bsm / nbplot）から import。第8冊の VaR を信用損失へ拡張""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import math

import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
from scipy.stats import norm

from hullkit import credit, nbplot

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.24 credit risk
# ===========================================================================

# Cell 03: hazard md
cells.append(
    md(r"""## 1. ハザードレートと生存確率（Ch.24）

ハザードレート（デフォルト強度）$\lambda(t)$ は「生存している条件で次の微小期間に
デフォルトする率」。生存確率と累積デフォルト確率は：

$$S(t) = e^{-\int_0^t \lambda(u)\,du}, \qquad Q(t) = 1 - S(t) \quad \text{(24.1)}$$

定数ハザードなら $Q(T) = 1 - e^{-\lambda T}$。""")
)

# Cell 04: survival curve
cells.append(
    code(r"""# --- 生存確率と累積デフォルト確率 ---
t_grid = np.linspace(0.0, 10.0, 200)
fig1, ax1 = plt.subplots(figsize=(8, 4))
fig1.canvas.header_visible = False
for lam in (0.01, 0.03, 0.06):
    ax1.plot(t_grid, [credit.default_prob(t, lam) for t in t_grid], lw=2,
             label=f"λ={lam:.0%} → 10年Q={credit.default_prob(10.0, lam):.1%}")
ax1.set_xlabel("年数 t")
ax1.set_ylabel("累積デフォルト確率 Q(t)")
ax1.set_title("定数ハザードの累積デフォルト確率")
ax1.legend()
display(fig1.canvas)""")
)

# Cell 05: real vs RN md
cells.append(
    md(r"""## 2. 実世界確率 vs リスク中立確率（Ch.24）

- **リスク中立確率**（CDS・債券スプレッドから逆算）は**実世界確率の 5〜10 倍**高い
- 理由: 信用リスクプレミアム、流動性、デフォルトの系統性（皆同時に困る）
- **使い分け**: デリバティブ価格付け → リスク中立 ／ 信用 VaR・資本 → 実世界

$$\bar\lambda(T) \approx \frac{s(T)}{1-R} \quad \text{(24.2)}, \qquad
s = -\frac{1}{T}\ln\frac{B^{\text{corp}}}{B^{\text{tsy}}}$$""")
)

# Cell 06: spread to hazard
cells.append(
    code(r"""# スプレッドからハザード、回収率の影響
rows = []
for s_bp in (50, 100, 200, 400):
    s = s_bp / 1e4
    for R in (0.2, 0.4, 0.6):
        lam = credit.hazard_from_spread(s, R)
        rows.append({"スプレッド(bp)": s_bp, "回収率R": R,
                     "ハザードλ": f"{lam:.4f}", "5年Q": f"{credit.default_prob(5.0, lam):.2%}"})
display(pd.DataFrame(rows))
print("同じスプレッドでも回収率が低いほどλは小さく見える（損失1単位あたりの強度）")""")
)

# Cell 07: Merton md
cells.append(
    md(r"""## 3. Merton 構造モデル（Ch.24）

企業の**株式 = 資産に対するコールオプション**（行使価格 = 負債額 $D$）と見なす：

$$E_0 = V_0 N(d_1) - D e^{-rT} N(d_2) \quad \text{(24.3)}, \qquad
\sigma_E E_0 = N(d_1)\sigma_V V_0 \quad \text{(24.4)}$$

観測できる $E_0, \sigma_E$ からこの2式を解いて $V_0, \sigma_V$ を求め、
**リスク中立デフォルト確率** $Q = N(-d_2)$ を得ます
（$d_2$ は KMV の「distance to default」）。""")
)

# Cell 08: Merton example
cells.append(
    code(r"""# Hull Example 24.3: 株式$3M, σ_E=80%, 負債$10M（1年）, r=5%
v0, sig_v, q = credit.merton_default_prob(3.0, 0.80, 10.0, 0.05, 1.0)
d2 = (math.log(v0 / 10.0) + (0.05 - 0.5 * sig_v**2) * 1.0) / (sig_v * 1.0)
print(f"資産価値 V0 = {v0:.4f}（百万）  資産ボラ σ_V = {sig_v:.4%}")
print(f"distance to default d2 = {d2:.4f}")
print(f"リスク中立デフォルト確率 Q = N(−d2) = {q:.4%}（Hull: 12.7%）")
print(f"参考: 信用スプレッド ≈ −ln(1−(1−0.4)·Q)/1 ≈ {-math.log(1 - 0.6 * q):.4%}")""")
)

# Cell 09: interactive Merton
cells.append(
    code(r"""# --- Merton エクスプローラ（インタラクティブ） ---
fig2, ax2 = plt.subplots(figsize=(7.5, 4))
fig2.canvas.header_visible = False
e_sl = widgets.FloatSlider(value=3.0, min=0.5, max=8.0, step=0.5, description="株式$M")
sige_sl = widgets.FloatSlider(value=0.80, min=0.3, max=1.5, step=0.05, description="σ_E")


def _upd_merton(change=None):
    ax2.clear()
    ds = np.linspace(5.0, 20.0, 40)
    qs = [credit.merton_default_prob(e_sl.value, sige_sl.value, d, 0.05, 1.0)[2] for d in ds]
    ax2.plot(ds, np.array(qs) * 100, lw=2)
    v0n, _, qn = credit.merton_default_prob(e_sl.value, sige_sl.value, 10.0, 0.05, 1.0)
    ax2.plot(10.0, qn * 100, "o", ms=9, color="crimson")
    ax2.set_xlabel("負債額 D（百万）")
    ax2.set_ylabel("デフォルト確率 Q (%)")
    ax2.set_title(f"株式{e_sl.value:.1f}M, σ_E={sige_sl.value:.0%}: D=10 で Q={qn:.1%}（レバレッジ↑・σ↑で Q↑）")
    fig2.canvas.draw_idle()


e_sl.observe(_upd_merton, "value")
sige_sl.observe(_upd_merton, "value")
_upd_merton()
display(widgets.HBox([e_sl, sige_sl]), fig2.canvas)""")
)

# Cell 10: copula md
cells.append(
    md(r"""## 4. デフォルト相関とガウスコピュラ（Ch.24）

複数企業の同時デフォルトは**1因子ガウスコピュラ**で表現：

$$x_i = a_i F + \sqrt{1-a_i^2}\,Z_i \quad \text{(24.7)}, \qquad
Q_i(T\mid F) = N\!\left(\frac{N^{-1}[Q_i(T)] - a_i F}{\sqrt{1-a_i^2}}\right) \quad \text{(24.8)}$$

共通因子 $F$ が悪い（負の）状態では全社のデフォルト確率が同時に上がる —
これがテールの厚さ（システミックリスク）の源です。""")
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credit_xva.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
