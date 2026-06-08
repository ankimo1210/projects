"""
build_swaps_notebook.py
================================
nbformat-dict pattern to generate swaps.ipynb (Hull 11e Ch.7, 34).

Usage:
    uv run python build_swaps_notebook.py
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
    md(r"""# スワップ編（Hull 11e Ch.7, 34）

`johnhull/volumes` シリーズ第7冊。OTC デリバティブの主役：

- **金利スワップ（IRS）** — 仕組み、比較優位論とその批判（Ch.7）
- **2つの評価法** — 債券分解 vs FRA 分解（**恒等的に一致** — `hullkit.swaps` で確認）
- **通貨スワップ** — B_D − S₀·B_F（Ch.7）
- **非標準スワップの動物園** — コンパウンディング、LIBOR-in-arrears、CMS、キャンセラブル（Ch.34）

> 第4冊の `rates.py`（bootstrap カーブ）を本格活用します""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import math

import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display

from hullkit import nbplot, rates, swaps

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.7 mechanics
# ===========================================================================

# Cell 03: IRS mechanics md
cells.append(
    md(r"""## 1. 金利スワップの仕組み（Ch.7）

プレーン・バニラ IRS: 同一名目元本 $L$ に対して**固定**と**変動**（SOFR 等）を周期交換。
元本は交換しない。市場では固定側のレート（スワップレート）がクォートされ、
LIBOR 廃止後は割引・参照とも **OIS/SOFR** が標準。

| 用語 | 意味 |
|---|---|
| 固定払い側 | 固定を払い変動を受ける（金利上昇にロング） |
| スワップレート | 開始時に価値ゼロになる固定レート＝パー債券クーポン |
| ベーシススワップ | 変動 vs 変動（異なる参照レート） |""")
)

# Cell 04: cashflow table demo
cells.append(
    code(r"""# --- キャッシュフロー表（名目1億、固定3%受取、半年毎、実現変動レートはシナリオ） ---
L_SW = 100_000_000.0
S_FIX = 0.03
float_scenario = [0.024, 0.027, 0.031, 0.034]  # 実現した6ヶ月レート（年率、シナリオ）
rows = []
for i, rf in enumerate(float_scenario, start=1):
    cf_fix = L_SW * S_FIX * 0.5
    cf_fl = L_SW * rf * 0.5
    rows.append({"支払時点 t（年）": 0.5 * i, "固定受取": f"{cf_fix:,.0f}",
                 "変動支払": f"{cf_fl:,.0f}", "ネット": f"{cf_fix - cf_fl:,.0f}"})
df_cf = pd.DataFrame(rows)
display(df_cf)
print("変動レートが固定3%を超える期間はネット支払いに転じる")""")
)

# Cell 05: comparative advantage md
cells.append(
    md(r"""## 2. 比較優位論とその批判（Ch.7）

| | 固定市場 | 変動市場 |
|---|---|---|
| AAA社 | 4.0% | SOFR + 0.3% |
| BBB社 | 5.2% | SOFR + 1.0% |
| スプレッド差 | a = 1.2% | b = 0.7% |

総利得 $= a - b = 0.5\%$ を両社（と仲介銀行）で分配できる。

**批判**: 固定市場のスプレッド差が大きいのは、固定で長期に貸す方が
信用リスクの期間が長いから。BBB 社の「変動での優位」は
ロールオーバーリスクを抱え込んでいるだけ、という面がある。""")
)

# ===========================================================================
# Section 2: Ch.7 valuation
# ===========================================================================

# Cell 06: valuation approaches md
cells.append(
    md(r"""## 3. IRS の評価 — 2つの分解（Ch.7）

**債券分解**: 固定受取スワップ = 固定債ロング + 変動債ショート

$$V = B_{\text{fix}} - B_{\text{fl}}, \qquad B_{\text{fl}} = (L + L r^* \tau_1) P(0, t_1)$$

（変動債は次回支払直後に額面 — これが評価を簡単にする鍵）

**FRA 分解**（Hull 推奨）: スワップ = FRA の列。各期間の変動を
カーブのフォワードレートが実現すると仮定して

$$V = \sum_i L (s - f_i) \tau_i P(0, t_i)$$

**両者は恒等的に同じ値**になります（下で数値確認）。""")
)

# Cell 07: swap rate from bootstrap curve
cells.append(
    code(r"""# --- 第4冊の bootstrap カーブからスワップレートを計算 ---
instruments = [
    (0.25, 0.0, 99.6), (0.50, 0.0, 99.0), (1.00, 0.0, 97.8),
    (1.50, 4.0, 102.5), (2.00, 5.0, 105.0),
]
bt_times, bt_zeros = rates.bootstrap_zero_curve(instruments)
CURVE = (bt_times, bt_zeros)
PAY_T = [0.5, 1.0, 1.5, 2.0]
s_par = swaps.swap_rate(PAY_T, CURVE)
print(f"2年・半年払いのパー・スワップレート = {s_par:.4%}")
print("（カーブのゼロレート 2.0–2.4% に整合する水準）")

# 次回変動レート（カーブ整合のリセット済みレート）
r_next = (math.exp(rates.zero_interp(0.5, *CURVE) * 0.5) - 1.0) / 0.5
print(f"設定済みの次回6ヶ月レート（単利） = {r_next:.4%}")""")
)

# Cell 08: both approaches agree
cells.append(
    code(r"""# --- パーで両分解ともゼロ、オフマーケットでも完全一致 ---
rows = []
for s_fix in (s_par, 0.02, 0.03, 0.04):
    vb = swaps.irs_value_bonds(L_SW, s_fix, PAY_T, CURVE, next_float_rate=r_next)
    vf = swaps.irs_value_fras(L_SW, s_fix, PAY_T, CURVE, next_float_rate=r_next)
    rows.append({"固定レート": f"{s_fix:.4%}", "債券分解": round(vb, 2),
                 "FRA分解": round(vf, 2), "差": f"{abs(vb - vf):.2e}"})
df_val = pd.DataFrame(rows)
display(df_val)
print("固定3%受取は現行カーブ（〜2.4%）より有利 → 正の価値")""")
)

# Cell 09: floating bond intuition md
cells.append(
    md(r"""### なぜ変動債は「パー」か

リセット直後の変動債を考える。次回クーポンは市場レートそのもの →
次回支払時点での価値は（クーポン＋元本の現在価値の合計が）ちょうど額面。
帰納的に、**リセットの瞬間の変動債は常に額面**。
期中は「確定済みの次回クーポン＋額面」を次回支払日まで割り引くだけでよい。""")
)

# Cell 10: DV01 / sensitivity chart
cells.append(
    code(r"""# --- 平行シフト感応度（受取固定の価値 vs シフト幅） ---
shifts = np.linspace(-0.02, 0.02, 41)
vals = []
for ds in shifts:
    crv = (CURVE[0], [z + ds for z in CURVE[1]])
    rn = (math.exp(rates.zero_interp(0.5, *crv) * 0.5) - 1.0) / 0.5
    vals.append(swaps.irs_value_bonds(L_SW, s_par, PAY_T, crv, next_float_rate=rn))
vals = np.array(vals)
dv01 = (vals[21] - vals[19]) / 2.0 / 10.0  # 10bp あたり→1bp

fig1, ax1 = plt.subplots(figsize=(7.5, 4))
fig1.canvas.header_visible = False
ax1.plot(shifts * 1e4, np.array(vals) / 1e6, lw=2)
ax1.axhline(0.0, color="black", lw=0.8)
ax1.set_xlabel("平行シフト（bp）")
ax1.set_ylabel("スワップ価値（百万）")
ax1.set_title(f"受取固定はデュレーション・ロング（DV01 ≈ {dv01:,.0f}/bp）")
display(fig1.canvas)""")
)

# Cell 11: interactive shift
cells.append(
    code(r"""# --- 金利シナリオ（インタラクティブ） ---
fig2, ax2 = plt.subplots(figsize=(7.5, 4))
fig2.canvas.header_visible = False
shift_sl = widgets.FloatSlider(value=0.0, min=-200.0, max=200.0, step=10.0,
                               description="シフト(bp)")
fix_sl = widgets.FloatSlider(value=round(s_par * 100, 2), min=1.0, max=5.0, step=0.05,
                             description="固定(%)")


def _upd_swap(change=None):
    ax2.clear()
    ds = shift_sl.value / 1e4
    s_fx = fix_sl.value / 100.0
    crv = (CURVE[0], [z + ds for z in CURVE[1]])
    rn = (math.exp(rates.zero_interp(0.5, *crv) * 0.5) - 1.0) / 0.5
    taus = np.diff(np.concatenate([[0.0], np.asarray(PAY_T)]))
    times_aug = np.concatenate([[0.0], np.asarray(PAY_T)])
    pvs = []
    for i, t in enumerate(PAY_T):
        t0, t1 = times_aug[i], times_aug[i + 1]
        if i == 0:
            f_simple = rn
        else:
            z0 = rates.zero_interp(t0, *crv)
            z1 = rates.zero_interp(t1, *crv)
            f_simple = (math.exp((z1 * t1 - z0 * t0)) - 1.0) / (t1 - t0)
        pvs.append(L_SW * (s_fx - f_simple) * taus[i] * swaps.discount(float(t1), crv) / 1e6)
    ax2.bar([str(t) for t in PAY_T], pvs)
    ax2.axhline(0.0, color="black", lw=0.8)
    total = swaps.irs_value_fras(L_SW, s_fx, PAY_T, crv, next_float_rate=rn) / 1e6
    ax2.set_xlabel("支払時点（年）")
    ax2.set_ylabel("ネットCFのPV（百万）")
    ax2.set_title(f"受取固定 {s_fx:.2%}, シフト {shift_sl.value:+.0f}bp → 合計 {total:+.2f} 百万")
    fig2.canvas.draw_idle()


shift_sl.observe(_upd_swap, "value")
fix_sl.observe(_upd_swap, "value")
_upd_swap()
display(widgets.HBox([shift_sl, fix_sl]), fig2.canvas)""")
)

# Cell 12: OIS note md
cells.append(
    md(r"""### OIS / SOFR 移行メモ（Ch.7）

- 2010年代以降、割引も参照も **OIS（SOFR/SONIA/TONAR）** が標準に
- LIBOR 時代の「LIBOR で割引・LIBOR を参照」から、
  クレジット・スプレッドをほぼ含まないレートへ移行
- 本シリーズでは単一カーブで簡略化（Hull 11e の扱いと同じ）""")
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "swaps.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
