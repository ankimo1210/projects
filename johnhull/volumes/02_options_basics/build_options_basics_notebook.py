"""
build_options_basics_notebook.py
================================
nbformat-dict pattern to generate options_basics.ipynb (Hull 11e Ch.10-12, 17, 18).

Usage:
    uv run python build_options_basics_notebook.py
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
    md(r"""# オプション基礎編: 仕組み・性質・戦略（Hull 11e Ch.10–12, 17, 18）

`johnhull/volumes` シリーズ第2冊。オプションの基礎を5章まとめて扱います：

- **Ch.10 オプション市場の仕組み** — コール/プット、4つの基本ポジション
- **Ch.11 株式オプションの性質** — 上下限、プット・コール・パリティ、早期行使
- **Ch.12 トレーディング戦略**（中核）— スプレッド、コンビネーション、戦略ビルダー
- **Ch.17 指数・通貨オプション** — 連続配当利回り $q$、ポートフォリオ保険
- **Ch.18 先物オプションと Black-76** — $q=r$ の等価性

> 共通関数は `hullkit`（bsm / trees / payoffs / nbplot）から import。
> 前提: 第1冊 `volumes/01_foundations`（リスク中立評価・CRRツリー）""")
)

# Cell 01: matplotlib magic (standalone)
cells.append(code(r"""%matplotlib widget"""))

# Cell 02: imports
cells.append(
    code(r"""# --- imports & 共通設定 ---
import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
from scipy.stats import norm

from hullkit import bsm, nbplot, payoffs, trees

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.10 options mechanics
# ===========================================================================

# Cell 03: mechanics digest
cells.append(
    md(r"""## 1. オプション市場の仕組み（Ch.10 ダイジェスト）

- **コール**: 原資産を $K$ で**買う権利**。**プット**: $K$ で**売る権利**
- 4つの基本ポジション: コール買い / コール売り / プット買い / プット売り
- **本質的価値** intrinsic = $\max(S-K,0)$（コール）、**時間価値** = プレミアム − 本質的価値
- マネーネス: ITM / ATM / OTM。取引所オプションは通常アメリカン、現金決済の指数オプションはヨーロピアンが主流
- 売り手（writer）はプレミアムを受け取る代わりに無限大（コール売り）または $K$ まで（プット売り）の損失リスクを負う""")
)

# Cell 04: four basic positions (static 2x2)
cells.append(
    code(r"""# --- 4つの基本ポジションの損益図（プレミアム込み、BSMで算出） ---
S0_M, K_M, R_M, SIG_M, T_M = 100.0, 100.0, 0.05, 0.25, 0.5
prem_c = bsm.call_price(S0_M, K_M, R_M, SIG_M, T_M)
prem_p = bsm.put_price(S0_M, K_M, R_M, SIG_M, T_M)
s_t = np.linspace(60.0, 140.0, 401)

fig0, axes0 = plt.subplots(2, 2, figsize=(9, 6), sharex=True)
fig0.canvas.header_visible = False
cases = [
    ("コール買い", payoffs.leg_payoff(s_t, 1, "call", K_M) - prem_c, prem_c),
    ("コール売り", payoffs.leg_payoff(s_t, -1, "call", K_M) + prem_c, prem_c),
    ("プット買い", payoffs.leg_payoff(s_t, 1, "put", K_M) - prem_p, prem_p),
    ("プット売り", payoffs.leg_payoff(s_t, -1, "put", K_M) + prem_p, prem_p),
]
for ax, (title, prof, prem) in zip(axes0.ravel(), cases):
    ax.plot(s_t, prof, lw=2)
    ax.axhline(0.0, color="black", lw=0.8)
    ax.axvline(K_M, color="0.7", ls=":", lw=1)
    ax.set_title(f"{title}（プレミアム {prem:.2f}）", fontsize=10)
fig0.suptitle(f"K={K_M:.0f}, σ={SIG_M:.0%}, r={R_M:.0%}, T={T_M}年", fontsize=10)
fig0.supxlabel("満期株価 $S_T$")
fig0.supylabel("損益")
fig0.tight_layout()
display(fig0.canvas)
print(f"コール {prem_c:.4f} / プット {prem_p:.4f}（時間価値のみ＝ATMなので本質的価値0）")""")
)

# ===========================================================================
# Section 2: Ch.11 option properties
# ===========================================================================

# Cell 05: bounds
cells.append(
    md(r"""## 2. オプション価格の上下限（§11.3–11.4）

裁定なしから導かれるモデルフリーの不等式（無配当・ヨーロピアン）：

| | 下限 | 上限 |
|---|---|---|
| コール | $c \ge \max(S_0 - Ke^{-rT},\,0)$ (11.4) | $c \le S_0$ (11.1) |
| プット | $p \ge \max(Ke^{-rT} - S_0,\,0)$ (11.5) | $p \le Ke^{-rT}$ (11.3) |

BSM 価格は常にこのバンドの**内側**に収まります。下図で σ, r, T を動かして確認してください。""")
)

# Cell 06: interactive bounds chart
cells.append(
    code(r"""# --- 無裁定バンドと BSM 価格（インタラクティブ） ---
fig1, (ax1a, ax1b) = plt.subplots(1, 2, figsize=(10, 4), sharex=True)
fig1.canvas.header_visible = False
K_BND = 100.0
S_BND = np.linspace(40.0, 180.0, 141)

sig_b_sl = widgets.FloatSlider(value=0.25, min=0.05, max=0.6, step=0.05, description="σ")
r_b_sl = widgets.FloatSlider(value=0.05, min=0.0, max=0.15, step=0.01, description="r")
t_b_sl = widgets.FloatSlider(value=1.0, min=0.25, max=3.0, step=0.25, description="T")


def _upd_bounds(change=None):
    ax1a.clear()
    ax1b.clear()
    sig, r, T = sig_b_sl.value, r_b_sl.value, t_b_sl.value
    disc_k = K_BND * np.exp(-r * T)
    c = np.array([bsm.call_price(s, K_BND, r, sig, T) for s in S_BND])
    p = np.array([bsm.put_price(s, K_BND, r, sig, T) for s in S_BND])
    ax1a.fill_between(S_BND, np.maximum(S_BND - disc_k, 0.0), S_BND, alpha=0.15)
    ax1a.plot(S_BND, c, lw=2, label="BSM コール")
    ax1a.set_title("コール: 下限 max(S−Ke$^{-rT}$,0) 〜 上限 S")
    ax1b.fill_between(
        S_BND, np.maximum(disc_k - S_BND, 0.0), np.full_like(S_BND, disc_k),
        alpha=0.15, color="orange",
    )
    ax1b.plot(S_BND, p, lw=2, color="darkorange", label="BSM プット")
    ax1b.set_title("プット: 下限 max(Ke$^{-rT}$−S,0) 〜 上限 Ke$^{-rT}$")
    for ax in (ax1a, ax1b):
        ax.axvline(K_BND, color="0.7", ls=":", lw=1)
        ax.set_xlabel("株価 $S_0$")
        ax.legend(fontsize=9)
    fig1.canvas.draw_idle()


for w in (sig_b_sl, r_b_sl, t_b_sl):
    w.observe(_upd_bounds, "value")
_upd_bounds()
display(widgets.HBox([sig_b_sl, r_b_sl, t_b_sl]), fig1.canvas)""")
)

# Cell 07: put-call parity
cells.append(
    md(r"""## 3. プット・コール・パリティ（§11.5）

$$c + Ke^{-rT} = p + S_0 \quad \text{(11.6)}$$

両辺とも満期ペイオフが $\max(S_T, K)$ になるため（コール＋割引債 ＝ プット＋株）、
裁定なしで等価。**モデルに依存しない**関係式で、破れていれば裁定機会です。""")
)

# Cell 08: parity arbitrage demo
cells.append(
    code(r"""# Hull §11.5 の例: S=31, K=30, r=10%, T=3ヶ月, コール=3
S_p, K_p, R_p, T_p, c_p = 31.0, 30.0, 0.10, 0.25, 3.0
p_fair = c_p + K_p * np.exp(-R_p * T_p) - S_p
print(f"パリティ含意プット価格 = {p_fair:.4f}（Hull: 1.26）")

p_mkt = 2.25  # 市場プットが割高なケース
print(f"\n市場プット {p_mkt} > {p_fair:.2f} → 割高。裁定: プット売り + コール買い + 株ショート")
inflow = p_mkt - c_p + S_p
fv = inflow * np.exp(R_p * T_p)
print(f"当初受取り = {p_mkt} − {c_p} + {S_p} = {inflow:.2f} → 満期FV {fv:.4f}")
for s_T in (25.0, 35.0):
    # どちらの分岐でも株は K=30 で買い戻せる（S_T<K: プット行使される / S_T>K: コール行使）
    print(f"  S_T={s_T:>5.1f}: 株買戻し K={K_p:.0f} → 裁定利益 {fv - K_p:.4f}")""")
)

# Cell 09: early exercise
cells.append(
    md(r"""## 4. 早期行使（§11.6–11.7）

- **無配当株のアメリカンコール**: 早期行使は最適でない → $C = c$。
  行使すると本質的価値 $S-K$ のみ。待てば $K$ 支払いの繰延べ金利＋下方プロテクションが残る
- **アメリカンプット**: 深い ITM では即時行使が最適になり得る → $P > p$。
  $K - S$ をいま受け取って金利運用する価値が時間価値を上回る

下図は CRR ツリー（N=200、第1冊の `hullkit.trees`）で測った早期行使プレミアム $P - p$。""")
)

# Cell 10: early-exercise premium chart (static)
cells.append(
    code(r"""# --- 早期行使プレミアム（アメリカン − ヨーロピアン、CRR N=200） ---
S_EE = np.linspace(60.0, 140.0, 41)
K_EE, R_EE, SIG_EE, T_EE = 100.0, 0.05, 0.25, 1.0


def _ee_premium(s, kind):
    am = trees.crr_price(s, K_EE, R_EE, SIG_EE, T_EE, 200, kind=kind, american=True)
    eu = trees.crr_price(s, K_EE, R_EE, SIG_EE, T_EE, 200, kind=kind)
    return am - eu


prem_put = np.array([_ee_premium(s, "put") for s in S_EE])
prem_call = np.array([_ee_premium(s, "call") for s in S_EE])

fig2, ax2 = plt.subplots(figsize=(8, 4))
fig2.canvas.header_visible = False
ax2.plot(S_EE, prem_put, lw=2, label="プット P − p（深いITMで増大）")
ax2.plot(S_EE, prem_call, lw=2, ls="--", label="コール C − c（無配当 → 常に0）")
ax2.axvline(K_EE, color="0.7", ls=":", lw=1)
ax2.set_xlabel("株価 $S_0$")
ax2.set_ylabel("早期行使プレミアム")
ax2.set_title(f"K={K_EE:.0f}, r={R_EE:.0%}, σ={SIG_EE:.0%}, T={T_EE}年")
ax2.legend()
display(fig2.canvas)
print(f"コール側プレミアムの最大値 = {prem_call.max():.2e}（= 0、C=c の数値確認）")""")
)

# Cell 11: six factors table
cells.append(
    md(r"""## 5. オプション価格の6要因（Table 11.1）

| 変数が増加 | 欧州コール $c$ | 欧州プット $p$ | 米国コール $C$ | 米国プット $P$ |
|---|---|---|---|---|
| 株価 $S_0$ | + | − | + | − |
| 行使価格 $K$ | − | + | − | + |
| 満期 $T$ | ? | ? | + | + |
| ボラティリティ $\sigma$ | + | + | + | + |
| 無リスク金利 $r$ | + | − | + | − |
| 配当 | − | + | − | + |

注意: 欧州オプションの満期 $T$ は「?」— 配当の大きい株では長い満期が不利になり得ます。""")
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "options_basics.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
