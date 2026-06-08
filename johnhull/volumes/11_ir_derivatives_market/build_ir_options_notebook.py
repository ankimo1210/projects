"""
build_ir_options_notebook.py
================================
nbformat-dict pattern to generate ir_options.ipynb (Hull 11e Ch.29, 30).

Usage:
    uv run python build_ir_options_notebook.py
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
    md(r"""# 金利デリバティブ標準市場モデル（Hull 11e Ch.29, 30）

`johnhull/volumes` シリーズ第11冊。実務の金利オプション評価：

- **Black の標準市場モデル（Ch.29）** — 債券オプション、キャップ/フロア、スワプション
- **キャップ-フロア-スワップのパリティ**、ボラティリティ・ストリッピング
- **3つの調整（Ch.30）** — コンベクシティ、タイミング、クォント

> `hullkit`（ir_options / rates / swaps / nbplot）から import。
> 第4冊（カーブ）・第7冊（スワップ）・第10冊（測度）がここで合流します""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import math

import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
from scipy.optimize import brentq

from hullkit import ir_options, nbplot, rates, swaps

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.29 standard market models
# ===========================================================================

# Cell 03: why hard md
cells.append(
    md(r"""## 1. なぜ金利は難しいか（Ch.29）

株式・為替は単一変数だが、金利は**イールドカーブ全体**が動き、
割引率とペイオフの**両方**に影響します。実務の標準解は
「商品ごとに **Black モデル（Black-76）** を当てる」こと：

| 商品 | 対数正規と仮定するもの |
|---|---|
| 債券オプション | 将来の債券価格 |
| キャップレット | 将来の短期金利（フォワードレート） |
| スワプション | 将来のスワップレート |

3つは互いに整合しない（同時には正しくない）が、実務では独立に使われます。""")
)

# Cell 04: bond option md
cells.append(
    md(r"""## 2. 債券オプション（§29.1、eq 29.1/29.2）

$$c = P(0,T)[F_B N(d_1) - K N(d_2)], \qquad
d_1 = \frac{\ln(F_B/K) + \sigma_B^2 T/2}{\sigma_B\sqrt{T}}$$

- $F_B = (B_0 - I)/P(0,T)$: フォワード債券価格（キャッシュプライス）
- $\sigma_B$: フォワード債券価格のボラティリティ
- **利回りボラとの変換**: $\sigma_B \approx D\,y_0\,\sigma_y$（$D$=修正デュレーション）""")
)

# Cell 05: bond option demo
cells.append(
    code(r"""# 債券オプション: フォワード債券価格102, ストライク100, σ_B=8%, T=2, P(0,2)=0.90
P0T, F_B, K_bo, sig_B, T_bo = 0.90, 102.0, 100.0, 0.08, 2.0
c_bo = ir_options.bond_option_black(P0T, F_B, K_bo, sig_B, T_bo, kind="call")
p_bo = ir_options.bond_option_black(P0T, F_B, K_bo, sig_B, T_bo, kind="put")
print(f"コール = {c_bo:.4f} ／ プット = {p_bo:.4f}")
print(f"パリティ c−p = {c_bo - p_bo:.4f} ／ P(0,T)(F_B−K) = {P0T * (F_B - K_bo):.4f}")

# 利回りボラ → 価格ボラ
D_mod, y0, sig_y = 4.2, 0.05, 0.15
print(f"\n利回りボラ変換: σ_B ≈ D·y·σ_y = {D_mod}×{y0}×{sig_y} = {D_mod * y0 * sig_y:.4f}")""")
)

# Cell 06: caps md
cells.append(
    md(r"""## 3. キャップとフロア（§29.2、eq 29.7/29.8）

**キャップ** = 変動金利が上限 $R_K$ を超えた差額を受け取る金利コールの列。
1本（キャップレット）は Black モデルで：

$$\text{caplet} = L\delta_k P(0,t_{k+1})[F_k N(d_1) - R_K N(d_2)], \quad
d_1 = \frac{\ln(F_k/R_K) + \sigma_k^2 t_k/2}{\sigma_k\sqrt{t_k}}$$

ボラは**観測時点** $t_k$ で $\sqrt{t_k}$、割引は**支払時点** $t_{k+1}$ の $P(0,t_{k+1})$。
キャップ = キャップレットの和。""")
)

# Cell 07: caplet from curve
cells.append(
    code(r"""# --- 第4冊の bootstrap カーブからフォワードを出してキャップを価格付け ---
instruments = [
    (0.25, 0.0, 99.6), (0.50, 0.0, 99.0), (1.00, 0.0, 97.8),
    (1.50, 4.0, 102.5), (2.00, 5.0, 105.0),
]
bt_times, bt_zeros = rates.bootstrap_zero_curve(instruments)
CURVE = (bt_times, bt_zeros)


def fwd_simple(t0, t1):
    z0 = rates.zero_interp(t0, *CURVE) if t0 > 0 else 0.0
    z1 = rates.zero_interp(t1, *CURVE)
    f_cont = (z1 * t1 - z0 * t0) / (t1 - t0)
    return (math.exp(f_cont * (t1 - t0)) - 1.0) / (t1 - t0)


L_CAP, R_K, SIG_FLAT = 1e6, 0.025, 0.20
periods = [(0.5, 1.0), (1.0, 1.5), (1.5, 2.0)]
forwards = [fwd_simple(a, b) for a, b in periods]
accruals = [b - a for a, b in periods]
pay_disc = [swaps.discount(b, CURVE) for a, b in periods]
fix_times = [a for a, b in periods]
caplets = [ir_options.caplet_black(L_CAP, d, f, R_K, SIG_FLAT, t, p)
           for f, d, p, t in zip(forwards, accruals, pay_disc, fix_times)]
cap = sum(caplets)
display(pd.DataFrame({"観測t_k": fix_times, "フォワードF_k": [f"{f:.4%}" for f in forwards],
                     "キャップレット": [round(c, 2) for c in caplets]}))
print(f"キャップ（フラット vol {SIG_FLAT:.0%}, R_K={R_K:.1%}）= {cap:,.2f}")""")
)

# Cell 08: cap-floor parity
cells.append(
    code(r"""# --- キャップ − フロア = 固定 R_K 払いスワップ ---
cap_v = ir_options.cap_black(L_CAP, forwards, R_K, SIG_FLAT, accruals, pay_disc, fix_times, kind="cap")
floor_v = ir_options.cap_black(L_CAP, forwards, R_K, SIG_FLAT, accruals, pay_disc, fix_times, kind="floor")
swap_v = sum(L_CAP * d * p * (f - R_K) for f, d, p in zip(forwards, accruals, pay_disc))
print(f"キャップ = {cap_v:,.2f}")
print(f"フロア   = {floor_v:,.2f}")
print(f"キャップ − フロア = {cap_v - floor_v:,.2f}")
print(f"R_K 払いスワップの価値 = {swap_v:,.2f}（恒等）")
print("→ ATM（R_K = フォワードスワップレート）ではキャップ = フロア")""")
)

# Cell 09: vol stripping md
cells.append(
    md(r"""## 4. フラット vol とスポット vol のストリッピング（§29.2）

市場はキャップ1本に**フラットボラティリティ** $\hat\sigma$ を1つ呼びます。
でも各キャップレットの「真の」ボラ（**スポット vol** $\sigma_k$）は満期で異なる。
短いキャップから順に「キャップ価格 = 累積キャップレット + 新キャップレット」を
解いて $\sigma_k$ を**ストリッピング**します（brentq）。""")
)

# Cell 10: vol stripping demo
cells.append(
    code(r"""# 市場フラット vol（満期ごと）からスポット vol を逆算
market_flat = {1.0: 0.18, 1.5: 0.20, 2.0: 0.19}  # キャップ満期 → フラット vol
# 各満期キャップの市場価格 = フラット vol で全キャップレットを評価した値
spot_vols = []
cum_price = 0.0
for idx, (a, b) in enumerate(periods):
    mat = b
    flat = market_flat[mat]
    # この満期キャップの市場価格（フラット vol で全レット評価）
    mkt_price = sum(ir_options.caplet_black(L_CAP, accruals[j], forwards[j], R_K, flat,
                                            fix_times[j], pay_disc[j])
                    for j in range(idx + 1))
    target_caplet = mkt_price - cum_price  # 新キャップレットの価値

    def _obj(sig, j=idx):
        return ir_options.caplet_black(L_CAP, accruals[j], forwards[j], R_K, sig,
                                       fix_times[j], pay_disc[j]) - target_caplet

    sig_k = brentq(_obj, 1e-4, 2.0)
    spot_vols.append(sig_k)
    cum_price += ir_options.caplet_black(L_CAP, accruals[idx], forwards[idx], R_K, sig_k,
                                         fix_times[idx], pay_disc[idx])

fig1, ax1 = plt.subplots(figsize=(7.5, 4))
fig1.canvas.header_visible = False
ax1.plot(fix_times, [market_flat[b] * 100 for a, b in periods], "o--", label="フラット vol")
ax1.plot(fix_times, np.array(spot_vols) * 100, "s-", label="スポット vol（ストリップ）")
ax1.set_xlabel("キャップレット観測時点 t_k")
ax1.set_ylabel("ボラティリティ (%)")
ax1.set_title("フラット vol は平均、スポット vol が各レットの真の vol")
ax1.legend()
display(fig1.canvas)""")
)

# Cell 11: swaption md
cells.append(
    md(r"""## 5. スワプション（§29.3、eq 29.10/29.11）

将来 $T$ に $n$ 年スワップに入る権利。ペイヤー（固定払い権）は Black で：

$$V_{\text{payer}} = L\,A(0)[s_F N(d_1) - s_K N(d_2)], \qquad
A(0) = \frac{1}{m}\sum_{i=1}^{mn} P(0,T_i)$$

$s_F$ はフォワードスワップレート、$A(0)$ はスワップ・アニュイティ。
レシーバーはプット型。ATM（$s_K = s_F$）では payer = receiver。""")
)

# Cell 12: swaption demo
cells.append(
    code(r"""# 1年後にスタートする2年スワップのスワプション（半年払い）
swap_pays = [1.5, 2.0, 2.5, 3.0]  # スワップの支払時点
annuity = 0.5 * sum(swaps.discount(t, CURVE) for t in swap_pays)  # A(0) = (1/m)ΣP
# フォワードスワップレート s_F
s_F = (swaps.discount(1.0, CURVE) - swaps.discount(3.0, CURVE)) / annuity
print(f"フォワードスワップレート s_F = {s_F:.4%}, アニュイティ A(0) = {annuity:.4f}")

L_SW, SIG_SW, T_OPT = 1e6, 0.20, 1.0
for s_K in (s_F, 0.03, 0.04):
    pay = ir_options.swaption_black(L_SW, annuity, s_F, s_K, SIG_SW, T_OPT, kind="payer")
    rec = ir_options.swaption_black(L_SW, annuity, s_F, s_K, SIG_SW, T_OPT, kind="receiver")
    tag = " ← ATM（payer=receiver）" if abs(s_K - s_F) < 1e-9 else ""
    print(f"s_K={s_K:.4%}: ペイヤー {pay:,.2f} / レシーバー {rec:,.2f}{tag}")""")
)

# Cell 13: interactive vol cube slice
cells.append(
    code(r"""# --- ボラティリティ・キューブの断面（インタラクティブ） ---
fig2, ax2 = plt.subplots(figsize=(7.5, 4))
fig2.canvas.header_visible = False
sig_sl = widgets.FloatSlider(value=0.20, min=0.05, max=0.50, step=0.02, description="σ_swap")
t_sl = widgets.FloatSlider(value=1.0, min=0.25, max=3.0, step=0.25, description="オプション満期T")


def _upd_swaption(change=None):
    ax2.clear()
    sks = np.linspace(0.01, 0.06, 60)
    payers = [ir_options.swaption_black(L_SW, annuity, s_F, sk, sig_sl.value, t_sl.value,
                                        kind="payer") for sk in sks]
    recs = [ir_options.swaption_black(L_SW, annuity, s_F, sk, sig_sl.value, t_sl.value,
                                      kind="receiver") for sk in sks]
    ax2.plot(sks * 100, payers, lw=2, label="ペイヤー")
    ax2.plot(sks * 100, recs, lw=2, label="レシーバー")
    ax2.axvline(s_F * 100, color="crimson", ls="--", lw=1, label=f"ATM s_F={s_F:.2%}")
    ax2.set_xlabel("ストライク s_K (%)")
    ax2.set_ylabel("スワプション価値")
    ax2.set_title(f"σ={sig_sl.value:.0%}, T={t_sl.value}年（ストライク×満期×テナーがキューブ）")
    ax2.legend()
    fig2.canvas.draw_idle()


sig_sl.observe(_upd_swaption, "value")
t_sl.observe(_upd_swaption, "value")
_upd_swaption()
display(widgets.HBox([sig_sl, t_sl]), fig2.canvas)""")
)

# Cell 14: model inconsistency md
cells.append(
    md(r"""### 3モデルの非整合（§29.3）

債券価格・金利・スワップレートが**すべて同時に対数正規**ということはあり得ません
（一方が対数正規なら他方はそうでない）。それでも実務で並用されるのは、
各市場のクォート慣行に合っているから。負金利環境では
**シフト対数正規**や**正規（Bachelier）モデル**が使われます（本書では概念のみ）。""")
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ir_options.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
