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
# Section 3: Ch.12 trading strategies
# ===========================================================================

# Cell 12: strategies overview
cells.append(
    md(r"""## 6. トレーディング戦略の全体像（Ch.12）

相場観 × ボラティリティ観で戦略を選びます：

| 相場観 | ボラ観 | 戦略 |
|---|---|---|
| 強気 | — | bull call spread（保守的）/ コール買い（積極的） |
| 弱気 | — | bear put spread / プット買い |
| 横ばい | 低下 | butterfly 買い / covered call |
| 方向不明 | 上昇 | straddle（コスト高）/ strangle（コスト低・大変動必要） |
| 方向不明・下落寄り | 上昇 | strip |
| 方向不明・上昇寄り | 上昇 | strap |

プレミアムは BSM（S₀=100, σ=25%, r=5%, T=0.5年）で算出します。""")
)

# Cell 13: strategy builder (interactive centerpiece)
cells.append(
    code(r"""# --- 戦略ビルダー（中核セル） ---
fig3, ax3 = plt.subplots(figsize=(9, 5))
fig3.canvas.header_visible = False

S0_B, R_B, SIG_B, T_B = 100.0, 0.05, 0.25, 0.5
S_GRID = np.linspace(50.0, 150.0, 601)

strat_dd = widgets.Dropdown(
    options=list(payoffs.STRATEGIES), value="bull_call_spread", description="戦略"
)
k1_sl = widgets.FloatSlider(value=95.0, min=70.0, max=130.0, step=1.0, description="K1")
k2_sl = widgets.FloatSlider(value=105.0, min=70.0, max=130.0, step=1.0, description="K2")
k3_sl = widgets.FloatSlider(value=115.0, min=70.0, max=130.0, step=1.0, description="K3")

_N_STRIKES = {
    "bull_call_spread": 2, "bear_put_spread": 2, "butterfly": 3,
    "straddle": 1, "strangle": 2, "strip": 1, "strap": 1,
    "covered_call": 1, "protective_put": 1,
}


def _leg_cost(qty, kind, K):
    if kind == "stock":
        return qty * S0_B
    if kind == "call":
        return qty * bsm.call_price(S0_B, K, R_B, SIG_B, T_B)
    return qty * bsm.put_price(S0_B, K, R_B, SIG_B, T_B)


def _upd_builder(change=None):
    ax3.clear()
    name = strat_dd.value
    n_k = _N_STRIKES[name]
    ks = sorted([k1_sl.value, k2_sl.value, k3_sl.value][:n_k])
    if name == "butterfly":
        ks = [ks[0], (ks[0] + ks[2]) / 2.0, ks[2]]  # K2は中点（Hullの対称形）
    legs = payoffs.STRATEGIES[name](*ks)
    cost = sum(_leg_cost(*leg) for leg in legs)
    profit = payoffs.strategy_payoff(S_GRID, legs) - cost
    ax3.plot(S_GRID, profit, lw=2)
    ax3.axhline(0.0, color="black", lw=0.8)
    ax3.axvline(S0_B, color="0.6", ls=":", lw=1)
    # 損益分岐点（線形補間でゼロ交差を検出）
    sgn = np.nonzero(np.diff(np.sign(profit)))[0]
    for idx in sgn:
        x0, x1 = S_GRID[idx], S_GRID[idx + 1]
        y0, y1 = profit[idx], profit[idx + 1]
        be = x0 - y0 * (x1 - x0) / (y1 - y0)
        ax3.plot(be, 0.0, "o", color="crimson", ms=6)
        ax3.annotate(f"BE {be:.1f}", (be, 0.0), textcoords="offset points",
                     xytext=(4, 7), fontsize=9, color="crimson")
    legs_str = " + ".join(f"{q:+d}×{k}" + (f"({K:.0f})" if K else "") for q, k, K in legs)
    ax3.set_title(
        f"{name}: {legs_str}\n"
        f"純コスト {cost:.2f} ／ 最大利益 {profit.max():.2f} ／ 最大損失 {profit.min():.2f}"
        f"（グリッド範囲内）", fontsize=10,
    )
    ax3.set_xlabel("満期株価 $S_T$")
    ax3.set_ylabel("損益")
    fig3.canvas.draw_idle()


for w in (strat_dd, k1_sl, k2_sl, k3_sl):
    w.observe(_upd_builder, "value")
_upd_builder()
display(widgets.VBox([strat_dd, widgets.HBox([k1_sl, k2_sl, k3_sl])]), fig3.canvas)""")
)

# Cell 14: spreads
cells.append(
    md(r"""### スプレッド（§12.3）

- **bull call spread**: $K_1$ コール買い + $K_2$ コール売り（$K_1<K_2$）。上昇益を $K_2-K_1$ に限定する代わりにコスト減
- **bear put spread**: $K_2$ プット買い + $K_1$ プット売り。下落で利益
- **butterfly**: $K_1, K_3$ 買い + $K_2$ 2枚売り（$K_2$ 中点）。±小動きで利益の「スパイク」
- **box spread**: bull call + bear put。ペイオフは常に $K_2-K_1$ → 価値は $(K_2-K_1)e^{-rT}$（**ヨーロピアン限定**の裁定関係。アメリカンで組むと早期行使リスクで崩れる — Business Snapshot 12.1）""")
)

# Cell 15: spreads panel (static)
cells.append(
    code(r"""# --- スプレッド4種の損益（BSMプレミアム込み） ---
K1_S, K2_S, K3_S = 90.0, 100.0, 110.0
panels = [
    ("bull call spread", payoffs.STRATEGIES["bull_call_spread"](K1_S, K3_S)),
    ("bear put spread", payoffs.STRATEGIES["bear_put_spread"](K1_S, K3_S)),
    ("butterfly", payoffs.STRATEGIES["butterfly"](K1_S, K2_S, K3_S)),
    ("box spread", payoffs.STRATEGIES["bull_call_spread"](K1_S, K3_S)
     + payoffs.STRATEGIES["bear_put_spread"](K1_S, K3_S)),
]
fig4, axes4 = plt.subplots(2, 2, figsize=(9, 6), sharex=True)
fig4.canvas.header_visible = False
for ax, (name, legs) in zip(axes4.ravel(), panels):
    cost = sum(_leg_cost(*leg) for leg in legs)
    prof = payoffs.strategy_payoff(S_GRID, legs) - cost
    ax.plot(S_GRID, prof, lw=2)
    ax.axhline(0.0, color="black", lw=0.8)
    ax.set_title(f"{name}（コスト {cost:.2f}）", fontsize=10)
fig4.supxlabel("満期株価 $S_T$")
fig4.supylabel("損益")
fig4.tight_layout()
display(fig4.canvas)
box_cost = sum(_leg_cost(*leg) for leg in panels[3][1])
print(f"box: コスト {box_cost:.4f} ≒ 理論値 (K3−K1)e^(-rT) = "
      f"{payoffs.box_spread_value(K1_S, K3_S, R_B, T_B):.4f} → 損益は常にほぼ0（裁定なし）")""")
)

# Cell 16: combinations
cells.append(
    md(r"""### コンビネーション（§12.4）

- **straddle**: 同一 $K$ のコール＋プット買い。ペイオフ $|S_T - K|$。大変動を予想するが方向不明のとき
- **strangle**: OTM プット（$K_1$）＋ OTM コール（$K_2$）。コスト安いがより大きな変動が必要
- **strip**: コール1 + プット2 — 下落寄りの大変動予想
- **strap**: コール2 + プット1 — 上昇寄りの大変動予想

注意: 決算・イベント前は IV が既に上がっており、straddle は見た目ほど儲からないことが多い（市場は同じ情報を織り込み済み）。""")
)

# Cell 17: combinations panel (static)
cells.append(
    code(r"""# --- コンビネーション4種の損益 ---
panels_c = [
    ("straddle", payoffs.STRATEGIES["straddle"](100.0)),
    ("strangle", payoffs.STRATEGIES["strangle"](90.0, 110.0)),
    ("strip", payoffs.STRATEGIES["strip"](100.0)),
    ("strap", payoffs.STRATEGIES["strap"](100.0)),
]
fig5, axes5 = plt.subplots(2, 2, figsize=(9, 6), sharex=True)
fig5.canvas.header_visible = False
for ax, (name, legs) in zip(axes5.ravel(), panels_c):
    cost = sum(_leg_cost(*leg) for leg in legs)
    prof = payoffs.strategy_payoff(S_GRID, legs) - cost
    ax.plot(S_GRID, prof, lw=2)
    ax.axhline(0.0, color="black", lw=0.8)
    ax.set_title(f"{name}（コスト {cost:.2f}）", fontsize=10)
fig5.supxlabel("満期株価 $S_T$")
fig5.supylabel("損益")
fig5.tight_layout()
display(fig5.canvas)""")
)

# Cell 18: principal-protected note
cells.append(
    md(r"""### 元本保護ノート（§12.1）

割引債（満期に元本を返す）＋ 残額でコール買い、の組み合わせ。
元本 $P$ のうち $Pe^{-rT}$ を債券に、残り $P(1-e^{-rT})$ をオプションに充てます。
金利が高く・ボラが低く・配当が高いほど多くのコールを買え、参加率が上がります。""")
)

# Cell 19: PPN demo
cells.append(
    code(r"""# --- 元本保護ノート: 1000 = 割引債 + ATMコール（3年） ---
P_NOTE, R_N, Q_N, SIG_N, T_N, S0_N = 1000.0, 0.06, 0.015, 0.20, 3.0, 100.0
bond_cost = P_NOTE * np.exp(-R_N * T_N)
budget = P_NOTE - bond_cost
call_unit = bsm.call_price(S0_N, S0_N, R_N, SIG_N, T_N, q=Q_N)
eta = budget / call_unit  # 買えるコールの「株数」
participation = eta * S0_N / P_NOTE

s_t3 = np.linspace(40.0, 220.0, 301)
note = P_NOTE + eta * np.maximum(s_t3 - S0_N, 0.0)
index_inv = P_NOTE / S0_N * s_t3

fig6, ax6 = plt.subplots(figsize=(8, 4.5))
fig6.canvas.header_visible = False
ax6.plot(s_t3, note, lw=2, label="元本保護ノート")
ax6.plot(s_t3, index_inv, lw=1.5, ls="--", label="株式100%投資")
ax6.axhline(P_NOTE, color="0.6", ls=":", lw=1)
ax6.set_xlabel("満期株価 $S_T$")
ax6.set_ylabel("満期受取額")
ax6.set_title(f"債券 {bond_cost:.1f} + コール予算 {budget:.1f}（{eta:.2f}株分, 参加率 {participation:.0%}）")
ax6.legend()
display(fig6.canvas)""")
)

# Cell 20: butterfly as building block
cells.append(
    md(r"""### バタフライ＝ペイオフの「建築ブロック」（§12.5の含意）

幅 $h$ のバタフライは $K$ にだけ高さ $h$ の「スパイク」を立てます。
ストライク格子 $\{K_i\}$ 上のバタフライを $\text{target}(K_i)/h$ 枚ずつ重ねれば、
**任意のペイオフ関数を区分線形近似**できます。
（これは「ヨーロピアンオプション価格 ⇔ リスク中立密度」（Breeden-Litzenberger）の離散版です）""")
)

# Cell 21: replication demo
cells.append(
    code(r"""# --- 任意ペイオフ（ガウシアン・バンプ）をバタフライ束で複製 ---
def target_payoff(s):
    return 8.0 * np.exp(-((s - 100.0) ** 2) / 50.0)


H_BF = 5.0
strikes_bf = np.arange(70.0, 131.0, H_BF)
s_fine = np.linspace(60.0, 140.0, 801)
approx = np.zeros_like(s_fine)
for k in strikes_bf:
    legs = payoffs.STRATEGIES["butterfly"](k - H_BF, k, k + H_BF)
    approx += (target_payoff(k) / H_BF) * payoffs.strategy_payoff(s_fine, legs)

fig7, ax7 = plt.subplots(figsize=(8, 4.5))
fig7.canvas.header_visible = False
ax7.plot(s_fine, target_payoff(s_fine), lw=2, label="ターゲットペイオフ")
ax7.plot(s_fine, approx, lw=1.5, ls="--", label=f"バタフライ近似（格子幅 {H_BF:.0f}）")
ax7.set_xlabel("満期株価 $S_T$")
ax7.set_ylabel("ペイオフ")
ax7.set_title("バタフライの線形結合による静的複製")
ax7.legend()
display(fig7.canvas)
err = np.max(np.abs(target_payoff(strikes_bf) - approx[np.searchsorted(s_fine, strikes_bf)]))
print(f"格子点上の最大誤差 = {err:.2e}（格子点では厳密に一致）")""")
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
