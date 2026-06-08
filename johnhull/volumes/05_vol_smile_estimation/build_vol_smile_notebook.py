"""
build_vol_smile_notebook.py
================================
nbformat-dict pattern to generate vol_smile.ipynb (Hull 11e Ch.20, 23).

Usage:
    uv run python build_vol_smile_notebook.py
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
    md(r"""# ボラティリティ・スマイルと推定（Hull 11e Ch.20, 23）

`johnhull/volumes` シリーズ第5冊。BSM の「σ 一定」前提を緩めます：

- **Ch.20 ボラティリティ・スマイル** — IV、株式スキュー vs FX スマイル、サーフェス、
  インプライド分布（Breeden-Litzenberger）
- **Ch.23 ボラティリティの推定** — EWMA（RiskMetrics）、GARCH(1,1)、MLE、予測

> 共通関数は `hullkit`（bsm / volatility / nbplot）から import。第3冊（Greeks）の V の前提を掘り下げる位置づけ""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
from scipy.stats import lognorm

from hullkit import bsm, nbplot, volatility

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.20 volatility smiles
# ===========================================================================

# Cell 03: IV + parity
cells.append(
    md(r"""## 1. インプライド・ボラティリティとパリティ（Ch.20、eq 20.1–20.2）

**IV** = 市場価格を BSM 式に代入して逆算した σ。プット・コール・パリティ

$$p + S_0 e^{-qT} = c + Ke^{-rT} \quad \text{(20.1)}$$

は**モデル非依存**なので、BSM 価格誤差はコールとプットで等しく（eq 20.2）、
**同一 $(K,T)$ のコールとプットの IV は必ず一致**します。
スマイルはコール/プットの区別なく1本の曲線です。""")
)

# Cell 04: implied vol demo
cells.append(
    code(r"""# 市場価格 → IV の逆算（hullkit.volatility.implied_vol、Brent法）
S0_S, R_S, T_S = 100.0, 0.03, 0.5
sigma_true = 0.27
c_mkt = bsm.call_price(S0_S, 105.0, R_S, sigma_true, T_S)
p_mkt = bsm.put_price(S0_S, 105.0, R_S, sigma_true, T_S)
iv_c = volatility.implied_vol(c_mkt, S0_S, 105.0, R_S, T_S, kind="call")
iv_p = volatility.implied_vol(p_mkt, S0_S, 105.0, R_S, T_S, kind="put")
print(f"コール市場価格 {c_mkt:.4f} → IV = {iv_c:.6f}")
print(f"プット市場価格 {p_mkt:.4f} → IV = {iv_p:.6f}")
print(f"差 = {abs(iv_c - iv_p):.2e}（パリティにより恒等的に一致）")""")
)

# Cell 05: skew vs smile md
cells.append(
    md(r"""## 2. 株式スキュー vs FX スマイル（Ch.20）

- **株式**: 低い行使価格ほど IV が高い「**スマーク**（下向きスキュー）」。
  要因はレバレッジ効果・ボラティリティフィードバック・**クラッシュフォビア**（1987年以降）
- **FX**: ATM が最低の「**U 字形**」。両方向のジャンプ（両裾の厚さ）を反映

インプライド分布で見ると、株式は**左裾が厚く**、FX は**両裾が厚い**。""")
)

# Cell 06: smile round-trip
cells.append(
    code(r"""# --- 合成スマイル: σ(K) で価格付け → IV を逆算して復元 ---
strikes = np.linspace(70.0, 130.0, 25)


def smile_equity(k):
    m = np.log(k / S0_S)
    return 0.22 - 0.25 * m + 0.20 * m**2  # 株式型スキュー


def smile_fx(k):
    m = np.log(k / S0_S)
    return 0.10 + 0.45 * m**2  # FX型 U字


fig1, axes1 = plt.subplots(1, 2, figsize=(10, 4))
fig1.canvas.header_visible = False
for ax, smile_fn, label in ((axes1[0], smile_equity, "株式型スキュー"),
                            (axes1[1], smile_fx, "FX型スマイル")):
    prices = [bsm.call_price(S0_S, k, R_S, smile_fn(k), T_S) for k in strikes]
    ivs = [volatility.implied_vol(c, S0_S, k, R_S, T_S, kind="call")
           for k, c in zip(strikes, prices)]
    ax.plot(strikes / S0_S, [smile_fn(k) * 100 for k in strikes],
            lw=1.5, color="0.6", label="真の σ(K)")
    ax.plot(strikes / S0_S, np.array(ivs) * 100, "o", ms=4, label="逆算 IV")
    ax.set_title(label, fontsize=10)
    ax.set_xlabel("K / S0")
    ax.set_ylabel("IV (%)")
    ax.legend(fontsize=9)
display(fig1.canvas)""")
)

# Cell 07: surface md
cells.append(
    md(r"""## 3. ボラティリティ・サーフェス（Ch.20）

IV を $(K, T)$ の2次元関数 $\sigma(K, T)$ として整理したもの。
典型的には**短期ほどスキューが急**（クラッシュは短期の恐怖）で、
満期とともにフラット化します。ATM の満期方向の断面が**タームストラクチャー**。""")
)

# Cell 08: surface heatmap
cells.append(
    code(r"""# --- 合成サーフェス: スキューが満期とともに減衰 ---
ts_grid = np.linspace(0.1, 2.0, 30)
ks_grid = np.linspace(70.0, 130.0, 31)
KK, TT = np.meshgrid(ks_grid, ts_grid)
MM = np.log(KK / S0_S)
SURF = 0.20 - 0.25 * MM * np.exp(-0.8 * TT) + 0.15 * MM**2 + 0.02 * (1 - np.exp(-TT))

fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(10.5, 4))
fig2.canvas.header_visible = False
pc = ax2a.pcolormesh(KK / S0_S, TT, SURF * 100, shading="auto", cmap="viridis")
fig2.colorbar(pc, ax=ax2a, label="IV (%)")
ax2a.set_xlabel("K / S0")
ax2a.set_ylabel("満期 T（年）")
ax2a.set_title("σ(K, T) サーフェス（スキューは短期で急）")
atm_idx = np.argmin(np.abs(ks_grid - S0_S))
ax2b.plot(ts_grid, SURF[:, atm_idx] * 100, lw=2)
ax2b.set_xlabel("満期 T（年）")
ax2b.set_ylabel("ATM IV (%)")
ax2b.set_title("ATM タームストラクチャー")
display(fig2.canvas)""")
)

# Cell 09: BL md
cells.append(
    md(r"""## 4. インプライド分布 — Breeden-Litzenberger（付録 20A）

コール価格の行使価格に関する2階微分がリスク中立密度を与えます：

$$g(K) = e^{rT}\frac{\partial^2 c}{\partial K^2} \quad \text{(20A.1)}, \qquad
g(K) \approx e^{rT}\frac{c_1 + c_3 - 2c_2}{\delta^2} \quad \text{(20A.2)}$$

第2冊の「バタフライ＝建築ブロック」の連続極限です。
フラットな σ なら対数正規分布が、スキューがあれば左裾の厚い分布が出てきます。""")
)

# Cell 10: BL density
cells.append(
    code(r"""# --- BL 密度: フラットσ → 対数正規と一致 ／ スキュー → 左裾が厚い ---
def bl_density(strike_grid, price_fn, r, T):
    c = np.array([price_fn(k) for k in strike_grid])
    dk = strike_grid[1] - strike_grid[0]
    g = np.exp(r * T) * (c[:-2] + c[2:] - 2.0 * c[1:-1]) / dk**2
    return strike_grid[1:-1], g


k_fine = np.linspace(40.0, 180.0, 281)
kk_f, g_flat = bl_density(k_fine, lambda k: bsm.call_price(S0_S, k, R_S, 0.22, T_S), R_S, T_S)
shape_ln = 0.22 * np.sqrt(T_S)
scale_ln = S0_S * np.exp((R_S - 0.5 * 0.22**2) * T_S)
g_ln = lognorm.pdf(kk_f, s=shape_ln, scale=scale_ln)
central = (kk_f > 70.0) & (kk_f < 140.0)
bl_err = float(np.max(np.abs(g_flat - g_ln)[central]) / g_ln.max())

kk_s, g_skew = bl_density(
    k_fine, lambda k: bsm.call_price(S0_S, k, R_S, smile_equity(k), T_S), R_S, T_S
)

fig3, ax3 = plt.subplots(figsize=(8, 4.5))
fig3.canvas.header_visible = False
ax3.plot(kk_f, g_ln, lw=1.5, color="0.6", label="対数正規（フラットσ理論値）")
ax3.plot(kk_f, g_flat, "--", lw=2, label="BL（フラットσ）")
ax3.plot(kk_s, g_skew, lw=2, label="BL（株式スキュー）→ 左裾が厚い")
ax3.set_xlabel("S_T")
ax3.set_ylabel("リスク中立密度")
ax3.legend()
display(fig3.canvas)
print(f"フラットσ: BL と対数正規の最大相対誤差 = {bl_err:.2e}（中央域）")""")
)

# Cell 11: sticky/MV delta md
cells.append(
    md(r"""## 5. スマイル下のヘッジ規約（Ch.20）

- **sticky strike**: σ(K) が固定とみなす ／ **sticky delta**: σ(マネーネス) が固定とみなす
- **minimum variance delta**: 株価と IV の負相関を織り込む修正
  $\Delta_{MV} = \Delta_{BSM} + \mathcal{V}\,\partial E[\sigma_{imp}]/\partial S < \Delta_{BSM}$
- スマイルの**モデル化**（局所ボラ・確率ボラ）は第6冊（Ch.27）で扱います""")
)

# Cell 12: interactive smile explorer
cells.append(
    code(r"""# --- スマイル・エクスプローラ（インタラクティブ） ---
fig4, (ax4a, ax4b) = plt.subplots(1, 2, figsize=(10.5, 4))
fig4.canvas.header_visible = False
atm_sl = widgets.FloatSlider(value=0.22, min=0.10, max=0.40, step=0.01, description="ATM σ")
slope_sl = widgets.FloatSlider(value=-0.25, min=-0.60, max=0.20, step=0.05, description="スキュー")
curv_sl = widgets.FloatSlider(value=0.20, min=0.0, max=0.80, step=0.05, description="曲率")


def _upd_smile(change=None):
    ax4a.clear()
    ax4b.clear()
    a0, sl, cv = atm_sl.value, slope_sl.value, curv_sl.value

    def sm(k):
        m = np.log(k / S0_S)
        return np.maximum(a0 + sl * m + cv * m**2, 0.01)

    ax4a.plot(strikes / S0_S, [sm(k) * 100 for k in strikes], lw=2)
    ax4a.set_xlabel("K / S0")
    ax4a.set_ylabel("IV (%)")
    ax4a.set_title("スマイル σ(K)")
    kk_i, g_i = bl_density(k_fine, lambda k: bsm.call_price(S0_S, k, R_S, sm(k), T_S), R_S, T_S)
    ax4b.plot(kk_f, g_ln, lw=1, color="0.7", label="対数正規（参考）")
    ax4b.plot(kk_i, g_i, lw=2, label="インプライド分布")
    ax4b.set_xlabel("S_T")
    ax4b.set_ylabel("密度")
    ax4b.legend(fontsize=9)
    fig4.canvas.draw_idle()


for w in (atm_sl, slope_sl, curv_sl):
    w.observe(_upd_smile, "value")
_upd_smile()
display(widgets.HBox([atm_sl, slope_sl, curv_sl]), fig4.canvas)
# スキューを深くすると左裾が厚くなるのを確認""")
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vol_smile.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
