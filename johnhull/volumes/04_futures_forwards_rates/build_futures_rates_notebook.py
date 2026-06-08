"""
build_futures_rates_notebook.py
================================
nbformat-dict pattern to generate futures_rates.ipynb (Hull 11e Ch.2-6).

Usage:
    uv run python build_futures_rates_notebook.py
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
    md(r"""# 先物・フォワード・金利編（Hull 11e Ch.2–6）

`johnhull/volumes` シリーズ第4冊。デリバティブの土台となる現物・先物・金利を扱います：

- **Ch.2 先物市場の仕組み** — 日次値洗い・証拠金・CCP
- **Ch.3 先物によるヘッジ** — ベーシスリスク、最小分散ヘッジ比率、ベータヘッジ
- **Ch.4 金利**（中核）— 複利変換、ゼロカーブ bootstrap、FRA、デュレーション（`hullkit.rates` を実装）
- **Ch.5 フォワード・先物価格の決定** — コストオブキャリー
- **Ch.6 金利先物** — デイカウント、CTD、デュレーションヘッジ

> 共通関数は `hullkit`（rates / mc / nbplot）から import""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display

from hullkit import nbplot, rates

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.2 futures markets
# ===========================================================================

# Cell 03: mechanics digest
cells.append(
    md(r"""## 1. 先物市場の仕組み（Ch.2 ダイジェスト）

- 取引所で標準化（原資産・サイズ・受渡月）。ほとんどは受渡し前に**反対売買で決済**
- **日次値洗い（marking to market）**: 毎日清算価格で損益を証拠金口座に反映。
  残高が**維持証拠金**を下回ると**マージンコール**（当初証拠金水準まで補充）
- クリアリングハウス/CCP が全取引の相手方となり信用リスクを吸収
- 満期接近で先物価格はスポットに収束（乖離は裁定で消える）

| | フォワード | 先物 |
|---|---|---|
| 取引 | OTC・相対 | 取引所・標準化 |
| 決済 | 満期一括 | 日次値洗い |
| 信用リスク | 相手方 | CCP が吸収 |""")
)

# Cell 04: margin account simulation
cells.append(
    code(r"""# --- 証拠金口座の日次決済シミュレーション（Hull Table 2.1 形式） ---
# 金先物 2枚 × 100オンス、当初証拠金 $6,000/枚、維持証拠金 $4,500/枚
N_OZ = 200
F0_M, INIT_M, MAINT_M = 1250.0, 12_000.0, 9_000.0
rng_m = np.random.default_rng(21)
moves = np.round(rng_m.normal(0.0, 9.0, 10), 1)
futures_path = F0_M + np.cumsum(moves)

rows, balance, total_calls = [], INIT_M, 0.0
prev = F0_M
for day, f in enumerate(futures_path, start=1):
    gain = (f - prev) * N_OZ
    balance += gain
    call = 0.0
    if balance < MAINT_M:
        call = INIT_M - balance
        balance = INIT_M
        total_calls += call
    rows.append({"日": day, "先物価格": round(f, 1), "日次損益": round(gain, 0),
                 "口座残高": round(balance, 0), "マージンコール": round(call, 0)})
    prev = f
df_margin = pd.DataFrame(rows)
display(df_margin)
total_gain = (futures_path[-1] - F0_M) * N_OZ
print(f"累積損益 = (F_最終 − F_0) × {N_OZ} = {total_gain:,.0f}"
      f" ／ 日次損益の合計 = {df_margin['日次損益'].sum():,.0f}（一致が値洗いの本質）")
print(f"マージンコール総額 = {total_calls:,.0f}")""")
)

# ===========================================================================
# Section 2: Ch.3 hedging with futures
# ===========================================================================

# Cell 05: hedge basics
cells.append(
    md(r"""## 2. 先物によるヘッジとベーシスリスク（§3.1–3.3）

- **ショートヘッジ**: 将来売る資産を持つ側（実現価格 $= F_1 + b_2$）
- **ロングヘッジ**: 将来買う予定の側
- **ベーシス** $b = S - F$。満期前決済やクロスヘッジ（対象資産 ≠ 先物原資産）では
  $b_2$ が不確実 — これが**ベーシスリスク**""")
)

# Cell 06: optimal hedge ratio
cells.append(
    code(r"""# --- 最小分散ヘッジ比率（ジェット燃料を灯油先物でクロスヘッジ、Hull §3.4） ---
RHO_H, SIG_S, SIG_F = 0.928, 0.0263, 0.0313
h_star = RHO_H * SIG_S / SIG_F  # eq (3.1)

rng_h = np.random.default_rng(31)
z1 = rng_h.standard_normal(5000)
z2 = rng_h.standard_normal(5000)
d_f = SIG_F * z1
d_s = SIG_S * (RHO_H * z1 + np.sqrt(1.0 - RHO_H**2) * z2)
h_grid = np.linspace(0.0, 1.6, 81)
var_h = [float(np.var(d_s - h * d_f)) for h in h_grid]
h_hat = float(np.polyfit(d_f, d_s, 1)[0])  # ΔS を ΔF に回帰 → 傾き ≈ h*

fig1, ax1 = plt.subplots(figsize=(7.5, 4))
fig1.canvas.header_visible = False
ax1.plot(h_grid, var_h, lw=2)
ax1.axvline(h_star, color="crimson", ls="--", lw=1.5, label=f"h* = ρσ_S/σ_F = {h_star:.3f}")
ax1.set_xlabel("ヘッジ比率 h")
ax1.set_ylabel("ヘッジ後ポジションの分散")
ax1.set_title("分散は h = h* で最小（ヘッジ効果 = ρ² = "
              f"{RHO_H**2:.3f}）")
ax1.legend()
display(fig1.canvas)
print(f"回帰推定 ĥ = {h_hat:.4f}（理論値 {h_star:.4f}）")
n_star = h_star * 2_000_000 / 42_000
print(f"ジェット燃料200万ガロンを 42,000ガロン/枚 の灯油先物で → N* = {n_star:.2f} ≈ {round(n_star)} 枚")""")
)

# Cell 07: beta hedging md
cells.append(
    md(r"""### 株価指数先物によるベータヘッジ（§3.5）

$$N^* = \beta\,\frac{V_A}{V_F} \quad \text{(eq 3.5)}, \qquad
\beta \to \beta^*: \; (\beta - \beta^*)\frac{V_A}{V_F}\ \text{枚ショート}$$

ヘッジで消えるのは**システマティックリスク**のみ。β を 0 にすればリスクフリー相当、
β を任意の目標値に調整することもできます。""")
)

# Cell 08: beta hedge demo
cells.append(
    code(r"""V_A, F_IDX, MULT, BETA = 5_050_000.0, 1_010.0, 250.0, 1.5
V_F = F_IDX * MULT
n_beta = BETA * V_A / V_F
print(f"ポートフォリオ ${V_A:,.0f}（β={BETA}）、先物1枚 = {F_IDX:.0f}×{MULT:.0f} = ${V_F:,.0f}")
print(f"完全ヘッジ: N* = β·V_A/V_F = {n_beta:.1f} 枚ショート\n")
rows = []
for b_target in (0.0, 0.75, 1.5, 2.0):
    k = (BETA - b_target) * V_A / V_F
    rows.append({"目標β*": b_target, "取引枚数": round(abs(k), 1),
                 "方向": "ショート" if k > 0 else ("ロング" if k < 0 else "—")})
display(pd.DataFrame(rows))""")
)

# ===========================================================================
# Section 3: Ch.4 interest rates (centerpiece)
# ===========================================================================

# Cell 09: compounding
cells.append(
    md(r"""## 3. 複利の単位（§4.2）

金利は複利頻度が決まって初めて意味を持ちます。本書（とこのシリーズ）の標準は**連続複利**：

$$R_c = m \ln\!\left(1 + \frac{R_m}{m}\right), \qquad R_m = m\left(e^{R_c/m} - 1\right) \quad \text{(4.3), (4.4)}$$""")
)

# Cell 10: conversion table
cells.append(
    code(r"""# 年率10%を各複利頻度から連続複利へ（hullkit.rates）
rows = []
for m, label in [(1, "年1回"), (2, "半年"), (4, "四半期"), (12, "月次"), (365, "日次")]:
    rc = rates.to_continuous(0.10, m)
    rows.append({"複利頻度": label, "m": m, "連続複利換算": f"{rc:.5%}",
                 "逆変換チェック": f"{rates.from_continuous(rc, m):.5%}"})
display(pd.DataFrame(rows))
print(f"半年複利10% → 連続複利 {rates.to_continuous(0.10, 2):.4%}（Hull: 9.758%）")""")
)

# Cell 11: bonds md
cells.append(
    md(r"""## 4. ゼロレート・債券価格・YTM・パーイールド（§4.4–4.6）

- **ゼロレート** $R(t)$: 満期 $t$ の一括払い投資に適用される金利
- **債券価格**: 各キャッシュフローを対応するゼロレートで個別に割引いた合計
- **YTM**: 全キャッシュフローを単一レート $y$ で割引いて価格に一致させる解
- **パーイールド**: 価格が額面に等しくなるクーポンレート""")
)

# Cell 12: Table 4.2 bond
cells.append(
    code(r"""# Hull Table 4.2: ゼロレート 5.0/5.8/6.4/6.8%（連続複利）、2年 6% 半年払い債
times_b = [0.5, 1.0, 1.5, 2.0]
cfs_b = [3.0, 3.0, 3.0, 103.0]
zeros_b = [0.050, 0.058, 0.064, 0.068]
price_b = rates.bond_price(times_b, cfs_b, zeros_b)
ytm_b = rates.bond_yield(times_b, cfs_b, price_b)
print(f"債券価格 = {price_b:.3f}（Hull: 98.39）")
print(f"YTM（連続複利）= {ytm_b:.4%}（Hull: 6.76%）")

# パーイールド: c·A/m + 100·d = 100 を解く（m=2）
d_factor = np.exp(-zeros_b[-1] * times_b[-1])
a_factor = sum(np.exp(-z * t) for z, t in zip(zeros_b, times_b))
par_c = (100.0 - 100.0 * d_factor) * 2.0 / a_factor
print(f"パーイールド = {par_c:.3f}%（年率、半年複利）")""")
)

# Cell 13: bootstrap md
cells.append(
    md(r"""## 5. ブートストラップ法によるゼロカーブ構築（§4.7）

市場で観測できるのは債券**価格**。短期のゼロクーポン債から順に、
クーポン債の既知キャッシュフローを既決ゼロレートで割引き、
残った最終キャッシュフローから未知のゼロレートを逐次的に解きます（Table 4.3）。""")
)

# Cell 14: bootstrap demo
cells.append(
    code(r"""# Hull Table 4.3 の5銘柄から bootstrap（hullkit.rates.bootstrap_zero_curve）
instruments = [
    (0.25, 0.0, 99.6),
    (0.50, 0.0, 99.0),
    (1.00, 0.0, 97.8),
    (1.50, 4.0, 102.5),
    (2.00, 5.0, 105.0),
]
bt_times, bt_zeros = rates.bootstrap_zero_curve(instruments)
df_bt = pd.DataFrame({"満期": bt_times, "ゼロレート": [f"{z:.4%}" for z in bt_zeros]})
display(df_bt)
print("Hull: 1.603% / 2.010% / 2.225% / 2.284% / 2.416%")

fig2, ax2 = plt.subplots(figsize=(7.5, 4))
fig2.canvas.header_visible = False
t_fine = np.linspace(0.25, 2.0, 200)
ax2.plot(t_fine, [rates.zero_interp(t, bt_times, bt_zeros) * 100 for t in t_fine],
         lw=1.5, label="線形補間")
ax2.plot(bt_times, np.array(bt_zeros) * 100, "o", ms=7, label="bootstrap 点")
ax2.set_xlabel("満期（年）")
ax2.set_ylabel("ゼロレート（%）")
ax2.set_title("Table 4.3 から構築したゼロカーブ")
ax2.legend()
display(fig2.canvas)""")
)

# Cell 15: forward/FRA md
cells.append(
    md(r"""## 6. フォワードレートと FRA（§4.8–4.9）

$$R_F = \frac{R_2 T_2 - R_1 T_1}{T_2 - T_1} \quad \text{(4.5)}$$

**FRA** は将来期間 $[T_1, T_2]$ の金利を固定する OTC 契約。固定受取側の価値：

$$V_{\text{FRA}} = L\,(R_K - R_F)\,(T_2 - T_1)\,e^{-R_2 T_2}$$

順イールドではフォワードレートはゼロレートの上に位置します。""")
)

# Cell 16: forward/FRA demo
cells.append(
    code(r"""# bootstrap カーブからフォワードレートを計算
rows = []
for (t1, z1), (t2, z2) in zip(list(zip(bt_times, bt_zeros))[:-1],
                              list(zip(bt_times, bt_zeros))[1:]):
    rows.append({"期間": f"{t1}→{t2}年", "フォワードレート": f"{rates.forward_rate(z1, t1, z2, t2):.4%}"})
display(pd.DataFrame(rows))

rf_simple = rates.forward_rate(0.03, 1.0, 0.04, 2.0)
print(f"例: 1年3% / 2年4% → 1→2年フォワード = {rf_simple:.2%}（eq 4.5）")
fra = rates.fra_value(100e6, 0.058, 0.050, 1.5, 2.0, 0.040)
print(f"FRA（元本1億、固定5.8%受取、フォワード5.0%、1.5→2.0年、R2=4%）= {fra:,.0f}（Hull: ≈369,200）")""")
)

# Cell 17: duration md
cells.append(
    md(r"""## 7. デュレーションとコンベクシティ（§4.10–4.11）

$$D = \frac{\sum_i t_i c_i e^{-y t_i}}{B}, \qquad \frac{\Delta B}{B} \approx -D\,\Delta y \quad \text{(4.8), (4.12)}$$

$$\frac{\Delta B}{B} \approx -D\,\Delta y + \tfrac{1}{2} C (\Delta y)^2 \quad \text{(4.14)}$$

線形近似は**平行シフト・小変化**が前提。大きな変化はコンベクシティで2次補正します
（プレーン債券は $C>0$ → 「小さく損・大きく得」のバイアス）。""")
)

# Cell 18: duration demo + chart
cells.append(
    code(r"""# Hull Table 4.6: 3年・10%クーポン（半年5）・y=12%連続複利
times_d = np.arange(0.5, 3.01, 0.5)
cfs_d = [5.0] * 5 + [105.0]
y_d = 0.12
b_d = rates.bond_price(times_d, cfs_d, y_d)
dur_d = rates.macaulay_duration(times_d, cfs_d, y_d)
conv_d = rates.convexity(times_d, cfs_d, y_d)
print(f"B = {b_d:.3f}（Hull: 94.213） D = {dur_d:.3f}（Hull: 2.653） C = {conv_d:.3f}")
print(f"Δy=+10bp: 実際 {rates.bond_price(times_d, cfs_d, y_d + 0.001) - b_d:+.3f}"
      f" ／ −BDΔy = {-b_d * dur_d * 0.001:+.3f}")

dy_grid = np.linspace(-0.03, 0.03, 121)
actual = np.array([rates.bond_price(times_d, cfs_d, y_d + dy) - b_d for dy in dy_grid])
lin = -b_d * dur_d * dy_grid
quad = lin + 0.5 * conv_d * b_d * dy_grid**2

fig3, ax3 = plt.subplots(figsize=(8, 4.5))
fig3.canvas.header_visible = False
ax3.plot(dy_grid * 100, actual, lw=2, label="実際の価格変化")
ax3.plot(dy_grid * 100, lin, ls="--", lw=1.5, label="−BDΔy（線形）")
ax3.plot(dy_grid * 100, quad, ls=":", lw=2, label="＋½CB(Δy)²（2次）")
ax3.set_xlabel("Δy（%）")
ax3.set_ylabel("ΔB")
ax3.set_title("デュレーション近似とコンベクシティ補正")
ax3.legend()
display(fig3.canvas)""")
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "futures_rates.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
