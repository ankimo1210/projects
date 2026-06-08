"""
build_numerical_notebook.py
================================
nbformat-dict pattern to generate numerical.ipynb (Hull 11e Ch.21, 27).

Usage:
    uv run python build_numerical_notebook.py
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
    md(r"""# 数値解法編（Hull 11e Ch.21, 27）

`johnhull/volumes` シリーズ第6冊。解析解がない商品を解く3大手法と発展モデル：

- **ツリーの拡張** — コントロール変量、三項ツリー（Ch.21）
- **モンテカルロ** — 標準誤差、分散削減（Ch.21）
- **有限差分法** — implicit / Crank-Nicolson、早期行使境界（Ch.21）
- **発展モデルと LSM** — Merton ジャンプ拡散が作るスマイル、Longstaff-Schwartz（Ch.27）

> 通し例: アメリカンプット S=50, K=50, r=10%, σ=40%, T=5/12（Hull Ch.21 のパラメータ）
> CRR（第1冊）・BSM・FD・MC の**相互整合**がこの冊の検証軸""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import math

import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display

from hullkit import bsm, fd, mc, nbplot, trees, volatility

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()

S_A, K_A, R_A, SIG_A, T_A = 50.0, 50.0, 0.10, 0.40, 5.0 / 12.0  # 通し例""")
)

# ===========================================================================
# Section 1: Ch.21 tree extensions
# ===========================================================================

# Cell 03: control variate md
cells.append(
    md(r"""## 1. ツリーの拡張とコントロール変量（Ch.21）

- 連続利回り $q$・時変パラメータは成長因子 $a = e^{(r-q)\Delta t}$（eq 21.4–21.7）の置換で対応
  （第1冊・第2冊で実装済み）
- **コントロール変量**: 同じツリーで欧州版も価格付けし、既知の BSM 解析値との誤差で補正

$$f^* = f_{\text{Am,tree}} + \left(f_{\text{Eu,BSM}} - f_{\text{Eu,tree}}\right)$$

ツリーの離散化誤差が Am/Eu 双方にほぼ同じ量だけ乗る、という観察を利用します。""")
)

# Cell 04: control variate demo
cells.append(
    code(r"""# --- コントロール変量: 少ないステップ数でも高精度 ---
ref_put = trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, 2000, kind="put", american=True)
eu_bsm = bsm.put_price(S_A, K_A, R_A, SIG_A, T_A)
rows = []
for n in (25, 50, 100, 200):
    am = trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, n, kind="put", american=True)
    eu_tree = trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, n, kind="put")
    cv = am + (eu_bsm - eu_tree)
    rows.append({"N": n, "plain": round(am, 4), "CV補正": round(cv, 4),
                 "|誤差| plain": round(abs(am - ref_put), 4),
                 "|誤差| CV": round(abs(cv - ref_put), 4)})
df_cv = pd.DataFrame(rows)
display(df_cv)
print(f"参照値（CRR N=2000）= {ref_put:.4f} ／ 欧州BSM = {eu_bsm:.4f}")""")
)

# Cell 05: trinomial md
cells.append(
    md(r"""## 2. 三項ツリー（Ch.21）

各ノードから上・中・下の3方向へ。$u = e^{\sigma\sqrt{3\Delta t}}$、

$$p_u = \sqrt{\frac{\Delta t}{12\sigma^2}}\left(r - q - \frac{\sigma^2}{2}\right) + \frac{1}{6}, \quad
p_m = \frac{2}{3}, \quad p_d = 1 - p_u - p_m$$

自由度が増えるぶん収束が滑らかで、**陽的有限差分法と等価**（後述）。
$\Delta t$ が大きすぎると $p_u, p_d$ が負になり得る点に注意。""")
)

# Cell 06: trinomial inline pricer
cells.append(
    code(r"""def trinomial_price(S0, K, r, sigma, T, n, q=0.0, kind="put", american=False):
    dt = T / n
    u = np.exp(sigma * np.sqrt(3.0 * dt))
    drift = r - q - 0.5 * sigma**2
    pu = np.sqrt(dt / (12.0 * sigma**2)) * drift + 1.0 / 6.0
    pd_ = -np.sqrt(dt / (12.0 * sigma**2)) * drift + 1.0 / 6.0
    pm = 2.0 / 3.0
    disc = np.exp(-r * dt)
    j = np.arange(-n, n + 1, dtype=float)
    s = S0 * u**j

    def payoff(x):
        return np.maximum(x - K, 0.0) if kind == "call" else np.maximum(K - x, 0.0)

    v = payoff(s)
    for _ in range(n):
        v = disc * (pu * v[2:] + pm * v[1:-1] + pd_ * v[:-2])
        s = s[1:-1]
        if american:
            v = np.maximum(v, payoff(s))
    return float(v[0])


tri_am = trinomial_price(S_A, K_A, R_A, SIG_A, T_A, 200, american=True)
crr_am = trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, 200, kind="put", american=True)
print(f"三項（N=200）= {tri_am:.4f} ／ CRR（N=200）= {crr_am:.4f} ／ 参照 {ref_put:.4f}")""")
)

# ===========================================================================
# Section 2: Ch.21 Monte Carlo
# ===========================================================================

# Cell 07: MC md
cells.append(
    md(r"""## 3. モンテカルロ法（Ch.21、eq 21.16）

リスク中立世界でパスを生成し、割引期待ペイオフを平均：

$$S_T = S_0\exp\left[\left(r - q - \frac{\sigma^2}{2}\right)T + \sigma\epsilon\sqrt{T}\right], \qquad
\hat f = e^{-rT}\frac{1}{N}\sum f_T^{(i)}, \quad \text{SE} = \frac{s}{\sqrt{N}}$$

強み: パス依存・多資産。弱み: 収束が $1/\sqrt{N}$、アメリカンは工夫（LSM、後述）が必要。""")
)

# Cell 08: MC demo
cells.append(
    code(r"""price_mc, se_mc = mc.price_european_mc(100.0, 100.0, 0.05, 0.2, 1.0, n_paths=200_000)
target_bsm = bsm.call_price(100.0, 100.0, 0.05, 0.2, 1.0)
print(f"MC = {price_mc:.4f} ± {1.96 * se_mc:.4f}（95%CI） ／ BSM = {target_bsm:.4f}")
print(f"|誤差| = {abs(price_mc - target_bsm):.4f}（{abs(price_mc - target_bsm) / se_mc:.2f} SE）")""")
)

# Cell 09: variance reduction md
cells.append(
    md(r"""## 4. 分散削減（Ch.21）

- **対称変量**: $\epsilon$ と $-\epsilon$ をペアにし、ペア平均の分散で評価
- **コントロール変量**: 解析解既知の類似商品 B で $f_A = f_A^* - f_B^* + f_B$
- **重点サンプリング** / **層化** / **準乱数列**（Sobol 等、誤差 $O(1/N)$ 近く）

Greeks の MC 計算はバンプ&再評価（共通乱数）か pathwise 微分（第3冊の Δ なら
$e^{-rT}\mathbf{1}_{S_T>K}\,S_T/S_0$）で行います — 詳細は省略。""")
)

# Cell 10: antithetic chart
cells.append(
    code(r"""# --- 対称変量の効果: SE vs パス数 ---
ns_mc = [1_000, 4_000, 16_000, 64_000, 256_000]
se_plain, se_anti = [], []
for i, n in enumerate(ns_mc):
    _, sp = mc.price_european_mc(100.0, 100.0, 0.05, 0.2, 1.0, n_paths=n,
                                 rng=np.random.default_rng(100 + i))
    _, sa = mc.price_european_mc(100.0, 100.0, 0.05, 0.2, 1.0, n_paths=n,
                                 antithetic=True, rng=np.random.default_rng(100 + i))
    se_plain.append(sp)
    se_anti.append(sa)

fig1, ax1 = plt.subplots(figsize=(7.5, 4))
fig1.canvas.header_visible = False
ax1.loglog(ns_mc, se_plain, "o-", label="プレーン")
ax1.loglog(ns_mc, se_anti, "s-", label="対称変量")
ax1.set_xlabel("パス数 N")
ax1.set_ylabel("標準誤差")
ax1.set_title("どちらも 1/√N で減少、対称変量は定数倍の改善")
ax1.legend()
display(fig1.canvas)""")
)

# Cell 11: MC misc md
cells.append(
    md(r"""### MC が得意な商品・苦手な商品

| 得意 | 苦手 |
|---|---|
| パス依存（アジアン・ルックバック） | 早期行使（→ LSM で対応、§7） |
| 多資産バスケット（次元の呪いに強い） | 高精度が必要な Greeks |
| 複雑なペイオフの追加が容易 | 収束 1/√N の遅さ |

ツリー・FD は低次元・早期行使に強く、MC と相補的です。""")
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "numerical.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
