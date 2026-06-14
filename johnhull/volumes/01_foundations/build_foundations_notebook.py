"""
build_foundations_notebook.py
=============================
nbformat-dict pattern to generate foundations.ipynb (Hull 11e Ch.13-14).

Usage:
    uv run python build_foundations_notebook.py
"""

import json
import os

from hullkit.teaching import caption, practice_box, scaffold

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

# Cell: volume-level scaffold
cells.append(
    md(
        scaffold(
            core="デリバティブ価格は「満期ペイオフを複製する費用」。将来予想（実確率）は要らない。",
            intuition="原資産と借入だけでオプションのペイオフを作れるなら、その複製コスト＝オプション価格"
            "（一物一価）。上昇確率は複製の中で相殺されて消える。",
            practice="この一点で投資銀行のデリバティブ・デスクが成立する。建値→動的ヘッジで方向観に依らず"
            "鞘を取る。Ch.14 の確率微分方程式は、その複製を連続時間で記述する言語。",
        )
    )
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
cells.append(
    md(
        scaffold(
            core="1 期間モデルでも、オプション価格は複製で一意に決まる：p=(a−d)/(u−d) で割引期待値。",
            intuition="Δ 株ロング＋オプション売りを無リスクにできる Δ が必ず存在する。"
            "無リスクなものは無リスク金利でしか増えない——これだけで価格が決まる。",
            practice="マーケットメイカーはこの値で建値し、Δ を売買して鞘を確定する。"
            "「上がる確率」を当てる必要が一切ない。",
        )
    )
)
cells.append(
    md(
        practice_box(
            "リスク中立確率は「予測」ではない",
            "p は「将来こう動く」という予想ではなく、複製コストを期待値の形に書き直したときに現れる"
            "人工的な重み。だからトレーダーは現実の上昇確率を見積もらずに値付けできる。"
            "価格が動くのは見通しが変わるからではなく $S,\\sigma,r$ が動くから——"
            "オプション・デスクの損益がギリシャ文字（Greeks）で管理される理由がここにある。",
        )
    )
)

# Cell 04: one-step numeric check (Hull §13.1 example)
cells.append(
    code(r"""# Hull §13.1 の例: S0=20, u=1.1, d=0.9, K=21, r=12%, T=3ヶ月
# ※ 11e Global Edition は r=4%（f=0.545）。本ノートは US 版の古典例 r=12% を採用
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
    if not 0.0 < p < 1.0:
        ax1.set_title(f"p={p:.3f} は (0,1) 外 — 裁定機会（d < e^(rT) < u を満たさない）")
        fig1.canvas.draw_idle()
        return
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
cells.append(
    md(
        caption(
            "スライダーで p が (0,1) を外れると「裁定機会」と表示され計算が止まる。"
            "これは d < e^{rT} < u（無裁定条件）が崩れた状態。価格が成立する範囲そのものが見える。"
        )
    )
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
cells.append(
    md(
        scaffold(
            core="多ステップは「1 期間の複製」を末端から巻き戻すだけ（後退帰納）。u=e^{σ√Δt} で σ に整合。",
            intuition="格子の各ノードで同じ無裁定論理を繰り返す。測度を変えても σ は不変（Girsanov）"
            "なので、ボラだけで木を組める。",
            practice="アメリカン・バリアなど閉形式の無い商品の標準評価器。エキゾチック・デスクの値付けの土台。",
        )
    )
)

# Cell 08: two-step & American examples
cells.append(
    code(r"""# Hull Fig 13.4: 2ステップ ヨーロピアンコール（S0=20, K=21, u=1.1, d=0.9, r=12%, Δt=0.25）
_, opt = trees.binomial_tree(20.0, 21.0, 0.12, 0.5, 2, u=1.1, d=0.9)
print(f"2ステップ コール = {opt[0][0]:.4f}（Hull Fig 13.4: 1.2823）")

# Hull Fig 13.7/13.8: 2ステップ プット（S0=50, K=52, u=1.2, d=0.8, r=5%, Δt=1年）
_, opt_eu = trees.binomial_tree(50.0, 52.0, 0.05, 2.0, 2, u=1.2, d=0.8, kind="put")
_, opt_am = trees.binomial_tree(50.0, 52.0, 0.05, 2.0, 2, u=1.2, d=0.8, kind="put", american=True)
print(f"ヨーロピアンプット = {opt_eu[0][0]:.4f}（Hull: 4.1923）")
print(f"アメリカンプット   = {opt_am[0][0]:.4f}（Hull Fig 13.8: 5.0894）")
print(f"早期行使プレミアム = {opt_am[0][0] - opt_eu[0][0]:.4f}")
print("※ 本文の値は p を4桁に丸めた計算。丸めなしでは 1.2822 / 4.1927 / 5.0896")""")
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
cells.append(
    md(
        scaffold(
            core="各ノードで max(継続価値, 即時行使価値) を取る。",
            intuition="「いま K−S を受け取り金利で運用する」方が得なら行使。ディープ ITM のプットで起きる。",
            practice="早期行使境界は「いつ解約・行使すべきか」の実務判断そのもの"
            "（転換社債のコール条項、住宅ローンの期前償還など同型の構造に効く）。",
        )
    )
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
    early_note = "、赤枠=早期行使" if am_dd.value else ""
    ax2.set_title(
        f"CRR {N}ステップ {label}・{kind_dd.value}"
        f"（S0={S0_2:.0f}, r={R_2:.0%}, T={T_2}年{early_note}）"
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
cells.append(
    md(
        caption(
            "赤枠＝即時行使が継続価値を上回るノード（早期行使域）。"
            "σ を上げると赤枠が縮む＝ボラが高いほど「待つ価値」が増え、早く行使しなくなる。"
        )
    )
)

# Cell 11: §13.6 delta on the tree
cells.append(
    md(r"""## 4. ツリー上のデルタ（§13.6）

デルタはノードごとに定義され、時間とともに変化します：

$$\Delta_{i,j} = \frac{V_{i+1,j} - V_{i+1,j+1}}{S_{i+1,j} - S_{i+1,j+1}}$$

静的なヘッジは不可能で、**動的リバランス**が必要です。下表は Hull Fig 13.8 の
アメリカンプット例の各ノードのデルタ。下方ノード（行使域）では $\Delta = -1$ に張り付きます。""")
)
cells.append(
    md(
        scaffold(
            core="Δ はノードごと・時刻ごとに変わる。静的なヘッジは不可能で、動的リバランスが要る。",
            intuition="ペイオフが曲がっている（凸）以上、複製比率も動く。だから一度組んだら終わりにできない。",
            practice="「リバランス頻度 vs 取引コスト」の最適化はヘッジ・デスクの日常。"
            "頻度を上げるほど複製誤差は減るがコストは増える。",
        )
    )
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
cells.append(
    md(
        scaffold(
            core="N→∞ で CRR は BSM に収束。誤差は O(1/N)、奇数・偶数で振動。",
            intuition="二項分布が正規分布へ近づく（中心極限）。離散の格子が連続の閉形式に化ける。",
            practice="木と BSM が一致することは実装の検算（リグレッションテスト）に使える。"
            "閉形式が無い商品は木に頼るので、この一致が信頼の根拠になる。",
        )
    )
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
cells.append(
    md(
        caption(
            "左：価格が鋸歯状に振動しながら BSM（破線）へ収束。右：誤差 |CRR−BSM| は両対数で"
            "ほぼ傾き −1（O(1/N)）の直線。実装で何ステップ取れば十分かの目安になる。"
        )
    )
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
cells.append(
    md(
        scaffold(
            core="リスク中立成長率の a を替えるだけで、指数・通貨・先物に同じ木が使える。",
            intuition="保有利回り（配当 q・外国金利 r_f）の分だけ成長率が下がる。先物は取得コスト 0 なので a=1。",
            practice="1 つのエンジンで株・指数・FX・先物オプションを値付け——プロダクトを跨ぐ共通基盤になる。",
        )
    )
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
# Section 2: Ch.14 Wiener processes & Ito's lemma
# ===========================================================================

# Cell 17: §14.1-14.2 Markov & Wiener processes
cells.append(
    md(r"""## 7. マルコフ性とウィーナー過程（§14.1–14.2）

株価過程の標準モデルは **マルコフ過程**：将来の分布は現在値のみで決まります。
最も基本的な連続時間マルコフ過程が **ウィーナー過程** $z$（ブラウン運動）：

$$\Delta z = \epsilon \sqrt{\Delta t}, \quad \epsilon \sim \phi(0,1) \quad \text{(14.1)}$$

$$z(T) - z(0) \sim \phi(0, T) \quad \text{(14.2)}$$

不確実性（標準偏差）は **時間の平方根** に比例して増えます。
分散は加法的（2年の分散=2）ですが標準偏差は非加法的（2年の標準偏差=$\sqrt{2}$）。""")
)
cells.append(
    md(
        scaffold(
            core="不確実性（標準偏差）は時間の平方根 √t で増える。",
            intuition="独立な増分を積み上げると分散が時間に比例。だから「2 年の散らばり」は 2 倍でなく √2 倍。",
            practice="日次ボラ→年率の換算（σ_day×√252）、VaR の √t スケーリングは、すべてこの性質が根拠。",
        )
    )
)

# Cell 18: interactive Wiener paths
cells.append(
    code(r"""# --- ウィーナー過程のパスと ±σ√t バンド ---
fig5, ax5 = plt.subplots(figsize=(8, 4.5))
fig5.canvas.header_visible = False
dt_sl = widgets.SelectionSlider(
    options=[("1.0", 1.0), ("0.25", 0.25), ("0.05", 0.05), ("0.01", 0.01)],
    value=0.05, description="Δt",
)
T_W = 5.0


def _upd_wiener(change=None):
    ax5.clear()
    dt = dt_sl.value
    n = int(T_W / dt)
    t = np.linspace(0.0, T_W, n + 1)
    rng = np.random.default_rng(0)
    dz = rng.standard_normal((30, n)) * np.sqrt(dt)
    z = np.column_stack([np.zeros(30), np.cumsum(dz, axis=1)])
    ax5.plot(t, z.T, lw=0.6, alpha=0.6)
    tt = np.linspace(0.0, T_W, 200)
    for k_sd, ls in [(1, "--"), (2, ":")]:
        ax5.plot(tt, k_sd * np.sqrt(tt), "k" + ls, lw=1.2)
        ax5.plot(tt, -k_sd * np.sqrt(tt), "k" + ls, lw=1.2)
    ax5.set_title(f"ウィーナー過程 30本（Δt={dt}）と ±√t / ±2√t バンド")
    ax5.set_xlabel("t（年）")
    ax5.set_ylabel("z(t)")
    fig5.canvas.draw_idle()


dt_sl.observe(_upd_wiener, "value")
_upd_wiener()
display(dt_sl, fig5.canvas)""")
)
cells.append(
    md(
        caption(
            "黒い帯は ±√t / ±2√t。Δt（刻み幅）を変えても帯は動かない＝"
            "不確実性の広がりは刻み幅でなく経過時間だけで決まる、を目で確認できる。"
        )
    )
)

# Cell 19: §14.3 generalized Wiener process
cells.append(
    md(r"""## 8. 一般化ウィーナー過程（§14.3）

ドリフト $a$・拡散係数 $b$ を加えた過程：

$$dx = a\,dt + b\,dz, \qquad x(T) - x(0) \sim \phi(aT,\; b^2 T) \quad \text{(14.3)}$$

期待値は $a$ に沿って直線的に進み、その周りに $b\sqrt{t}$ の不確実性が広がります。""")
)
cells.append(
    md(
        scaffold(
            core="dx = a·dt + b·dz：トレンド（ドリフト a）＋ノイズ（拡散 b）の最小モデル。",
            intuition="決定論的に a で進みながら、±b√t の帯で散らばる。これ以上単純な確率過程はない。",
            practice="金利・クレジットスプレッドなど「水準そのもの」がさまよう量のモデル化の出発点"
            "（負値を許すので株価には GBM を使う）。",
        )
    )
)

# Cell 20: interactive generalized Wiener + KDE
cells.append(
    code(r"""# --- 一般化ウィーナー過程: パス＋終端分布 ---
fig6, (ax6a, ax6b) = plt.subplots(
    1, 2, figsize=(10, 4), gridspec_kw={"width_ratios": [3, 1]}, sharey=True
)
fig6.canvas.header_visible = False
a_sl = widgets.FloatSlider(value=0.3, min=-1.0, max=1.0, step=0.1, description="a（ドリフト）")
b_sl = widgets.FloatSlider(value=0.5, min=0.1, max=2.0, step=0.1, description="b（拡散）")
T_G, N_G, M_G = 5.0, 250, 400


def _upd_gw(change=None):
    ax6a.clear()
    ax6b.clear()
    a, b = a_sl.value, b_sl.value
    dt = T_G / N_G
    t = np.linspace(0.0, T_G, N_G + 1)
    rng = np.random.default_rng(1)
    dx = a * dt + b * np.sqrt(dt) * rng.standard_normal((M_G, N_G))
    x = np.column_stack([np.zeros(M_G), np.cumsum(dx, axis=1)])
    ax6a.plot(t, x[:40].T, lw=0.5, alpha=0.5)
    ax6a.plot(t, a * t, "k--", lw=1.5, label="期待値 a·t")
    kx, ky = nbplot.kde_xy(x[:, -1])
    ax6b.plot(ky, kx, label="シミュ KDE")
    grid = np.linspace(x[:, -1].min(), x[:, -1].max(), 200)
    ax6b.plot(norm.pdf(grid, a * T_G, b * np.sqrt(T_G)), grid, "--", label="理論 φ(aT, b²T)")
    ax6a.set_title("dx = a·dt + b·dz")
    ax6a.set_xlabel("t（年）")
    ax6a.legend()
    ax6b.set_title("x(T) の分布")
    ax6b.legend(fontsize=8)
    fig6.canvas.draw_idle()


a_sl.observe(_upd_gw, "value")
b_sl.observe(_upd_gw, "value")
_upd_gw()
display(widgets.HBox([a_sl, b_sl]), fig6.canvas)""")
)

# Cell 21: §14.4-14.5 Ito process & GBM
cells.append(
    md(r"""## 9. 伊藤過程と幾何ブラウン運動（§14.4–14.5）

係数を状態依存にしたものが **伊藤過程** $dx = a(x,t)dt + b(x,t)dz$。
株価の標準モデルは **幾何ブラウン運動（GBM）**：

$$dS = \mu S\,dt + \sigma S\,dz \quad \text{(14.6)}$$

「期待収益率 $\mu$ と変動率 $\sigma$ が株価水準によらず一定」という仮定です。
シミュレーションには exact log-Euler 法（`hullkit.mc`）を使います —
naive Euler（$\Delta S = \mu S \Delta t + \sigma S \epsilon \sqrt{\Delta t}$）は離散化誤差が蓄積します。""")
)
cells.append(
    md(
        scaffold(
            core="dS = μS·dt + σS·dz。係数を株価に比例させると「%で動く」モデルになり、S_T は対数正規。",
            intuition="変化率が水準に比例するので株価は 0 を割らない。これが現実の株価と整合する最小の仮定。",
            practice="株式・FX・コモディティの業界標準モデル。BSM もモンテカルロも、この GBM の上に立っている。",
        )
    )
)

# Cell 22: interactive GBM + lognormal KDE
cells.append(
    code(r"""# --- GBM: パス＋終端分布（対数正規） ---
fig7, (ax7a, ax7b) = plt.subplots(
    1, 2, figsize=(10, 4), gridspec_kw={"width_ratios": [3, 1]}, sharey=True
)
fig7.canvas.header_visible = False
mu_sl = widgets.FloatSlider(value=0.10, min=-0.1, max=0.3, step=0.01, description="μ")
sig7_sl = widgets.FloatSlider(value=0.20, min=0.05, max=0.6, step=0.05, description="σ")
S0_7, T_7 = 100.0, 1.0


def _upd_gbm(change=None):
    ax7a.clear()
    ax7b.clear()
    mu, sig = mu_sl.value, sig7_sl.value
    paths = mc.simulate_gbm_paths(
        S0_7, mu, sig, T_7, n_steps=252, n_paths=2000, rng=np.random.default_rng(7)
    )
    t = np.linspace(0.0, T_7, 253)
    ax7a.plot(t, paths[:40].T, lw=0.5, alpha=0.5)
    ax7a.plot(t, S0_7 * np.exp(mu * t), "k--", lw=1.5, label="E[S_t] = S0·e^{μt}")
    st = paths[:, -1]
    kx, ky = nbplot.kde_xy(st)
    ax7b.plot(ky, kx, label="シミュ KDE")
    shape, scale = sig * np.sqrt(T_7), S0_7 * np.exp((mu - 0.5 * sig**2) * T_7)
    grid = np.linspace(st.min(), st.max(), 200)
    ax7b.plot(lognorm.pdf(grid, s=shape, scale=scale), grid, "--", label="理論 対数正規")
    ax7a.set_title("GBM: dS = μS·dt + σS·dz")
    ax7a.set_xlabel("t（年）")
    ax7a.legend()
    ax7b.set_title("S_T の分布")
    ax7b.legend(fontsize=8)
    fig7.canvas.draw_idle()


mu_sl.observe(_upd_gbm, "value")
sig7_sl.observe(_upd_gbm, "value")
_upd_gbm()
display(widgets.HBox([mu_sl, sig7_sl]), fig7.canvas)""")
)
cells.append(
    md(
        caption(
            "右の終端分布は対数正規（右に裾を引く非対称）。破線は期待値 E[S_t]=S0·e^{μt}。"
            "σ を上げると裾が伸び、中央値が期待値より下にずれる＝分散ドラッグの視覚化。"
        )
    )
)

# Cell 23: §14.6 Ito's lemma & ln S
cells.append(
    md(r"""## 10. 伊藤の補題と対数正規性（§14.6–14.7）

$x$ が伊藤過程に従うとき、$G(x,t)$ は：

$$dG = \left(\frac{\partial G}{\partial x}a + \frac{\partial G}{\partial t}
+ \frac{1}{2}\frac{\partial^2 G}{\partial x^2}b^2\right)dt
+ \frac{\partial G}{\partial x}\,b\,dz \quad \text{(14.12)}$$

核心は $(\Delta x)^2 \to b^2 \Delta t$（消えない！）。$G = \ln S$ に適用すると：

$$d(\ln S) = \left(\mu - \frac{\sigma^2}{2}\right)dt + \sigma\,dz \quad \text{(14.17)}$$

$$\ln S_T \sim \phi\!\left[\ln S_0 + \left(\mu - \tfrac{\sigma^2}{2}\right)T,\; \sigma^2 T\right] \quad \text{(14.19)}$$

通常の微分の感覚で $d(\ln S) = dS/S$ とすると $-\sigma^2/2$ の項が欠落します。
下のセルでこの差を数値で確認します。""")
)
cells.append(
    md(
        scaffold(
            core="伊藤の補題：$(\\Delta x)^2 \\to b^2\\Delta t$ が消えない。d(lnS) のドリフトは μ−σ²/2。",
            intuition="関数を確率変数で展開すると 2 次項が生き残る——ここが普通の微積と決定的に違う。",
            practice="BSM 偏微分方程式の導出そのもの。σ²/2 の項を落とすと価格も期待リターン推定も系統的にズレる。",
        )
    )
)
cells.append(
    md(
        practice_box(
            "分散ドラッグ——高ボラ資産の長期リターンが見かけより低い理由",
            "$E[S_T]=S_0 e^{\\mu T}$ なのに、対数リターンの期待は $\\mu-\\sigma^2/2$。"
            "σ が高いほど両者が開く（分散ドラッグ）。レバレッジ ETF やボラの高い銘柄を長期保有すると、"
            "平均リターンが高くても複利成長は $\\sigma^2/2$ だけ目減りする。"
            "ファンドのパフォーマンス評価やレバレッジ商品の設計で外せない事実。",
        )
    )
)

# Cell 24: Ito verification table
cells.append(
    code(r"""# d(lnS) のドリフトは μ−σ²/2、ΔS/S のドリフトは μ — 差が伊藤の ½σ² 項
mu_i, sig_i, S0_i, T_i = 0.15, 0.30, 100.0, 1.0
print(f"μ = {mu_i}, σ = {sig_i}  →  μ−σ²/2 = {mu_i - 0.5 * sig_i**2:.4f}（分散ドラッグ {0.5 * sig_i**2:.4f}）\n")
rows = []
for n_steps in [12, 52, 252]:
    dt = T_i / n_steps
    paths = mc.simulate_gbm_paths(
        S0_i, mu_i, sig_i, T_i, n_steps, 50_000, rng=np.random.default_rng(3)
    )
    dln = np.diff(np.log(paths), axis=1).ravel()
    ds_s = (np.diff(paths, axis=1) / paths[:, :-1]).ravel()
    rows.append(
        {"Δt": round(dt, 4),
         "mean d(lnS)/Δt": round(float(dln.mean() / dt), 4),
         "理論 μ−σ²/2": round(mu_i - 0.5 * sig_i**2, 4),
         "var d(lnS)/Δt": round(float(dln.var() / dt), 4),
         "理論 σ²": round(sig_i**2, 4),
         "mean (ΔS/S)/Δt": round(float(ds_s.mean() / dt), 4),
         "↑理論 μ": mu_i}
    )
display(pd.DataFrame(rows))""")
)

# Cell 25: mu vs mu - sigma^2/2
cells.append(
    md(r"""### $\mu$ と $\mu - \sigma^2/2$ の違い

- $\mu$: 短期間の期待収益率（算術平均的）。$E(S_T) = S_0 e^{\mu T}$
- $\mu - \sigma^2/2$: 対数収益率の期待値（連続複利・幾何平均的）

ボラティリティが高いほど両者の差（**分散ドラッグ**）が拡大します。
例：$\mu = 15\%,\ \sigma = 20\%$ → 対数収益率の期待値は $13\%$。""")
)

# Cell 26: E/Var sim vs theory
cells.append(
    code(r"""S0_e, mu_e, sig_e, T_e = 100.0, 0.10, 0.20, 1.0
paths = mc.simulate_gbm_paths(S0_e, mu_e, sig_e, T_e, 50, 100_000)
st = paths[:, -1]
e_th, v_th = mc.gbm_theory(S0_e, mu_e, sig_e, T_e)
ln_m_th = np.log(S0_e) + (mu_e - 0.5 * sig_e**2) * T_e
ln_v_th = sig_e**2 * T_e
display(pd.DataFrame([
    {"量": "E[S_T]", "シミュ": round(float(st.mean()), 3), "理論": round(e_th, 3)},
    {"量": "Var[S_T]", "シミュ": round(float(st.var()), 1), "理論": round(v_th, 1)},
    {"量": "E[ln S_T]", "シミュ": round(float(np.log(st).mean()), 4), "理論": round(ln_m_th, 4)},
    {"量": "Var[ln S_T]", "シミュ": round(float(np.log(st).var()), 4), "理論": round(ln_v_th, 4)},
]))""")
)

# ===========================================================================
# Section 3: verification / exercises / summary
# ===========================================================================

# Cell 27: verification intro
cells.append(
    md(r"""## 11. 教科書例題との突合せ

本ノートブックと `hullkit` の数値を Hull 11e の例題と突き合わせます。
（hullkit の pytest にも同じ検証があります: `johnhull/hullkit/tests/`）""")
)

# Cell 28: assertion cell
cells.append(
    code(r"""checks = []

# Hull §13.1 1ステップ: S0=20, u=1.1, d=0.9, K=21, r=12%, T=0.25
stock1, opt1 = trees.binomial_tree(20.0, 21.0, 0.12, 0.25, 1, u=1.1, d=0.9)
checks.append(("1ステップ コール 0.633", float(opt1[0][0]), 0.633, 5e-4))
checks.append(("1ステップ Δ = 0.25", trees.tree_delta(stock1, opt1), 0.25, 1e-9))

# Hull Fig 13.4 2ステップ コール
_, opt2 = trees.binomial_tree(20.0, 21.0, 0.12, 0.5, 2, u=1.1, d=0.9)
checks.append(("2ステップ コール 1.2823", float(opt2[0][0]), 1.2823, 5e-4))

# Hull Fig 13.8 アメリカンプット（丸めなし厳密値 5.0896）
_, opt3 = trees.binomial_tree(
    50.0, 52.0, 0.05, 2.0, 2, u=1.2, d=0.8, kind="put", american=True
)
checks.append(("アメリカンプット 5.0896", float(opt3[0][0]), 5.0896, 1e-3))

# Hull Example 15.6
checks.append(("BSM コール 4.76", bsm.call_price(42, 40, 0.10, 0.20, 0.5), 4.76, 1e-2))
checks.append(("BSM プット 0.81", bsm.put_price(42, 40, 0.10, 0.20, 0.5), 0.81, 1e-2))

# 収束: CRR(500) ≈ BSM (10.4506)
checks.append((
    "CRR(500) → BSM 10.4506",
    trees.crr_price(100.0, 100.0, 0.05, 0.2, 1.0, 500),
    bsm.call_price(100.0, 100.0, 0.05, 0.2, 1.0),
    1e-2,
))

# GBM モーメント（シード固定）
paths_v = mc.simulate_gbm_paths(100.0, 0.10, 0.20, 1.0, 50, 100_000)
e_v, _ = mc.gbm_theory(100.0, 0.10, 0.20, 1.0)
checks.append(("GBM E[S_T] ≈ 110.52", float(paths_v[:, -1].mean()), e_v, 0.5))

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.4f} want={want:.4f} (tol={tol})")
    assert ok, name
print("\n全チェック合格")""")
)

# Cell 29: exercises
cells.append(
    md(r"""## 12. 練習問題

**Q1.** S0=50, u=1.06, d=0.95, r=4%, T=0.5（1ステップ）の K=50 コールの価格とデルタは？

<details><summary>解答</summary>

p = (e^{0.02} − 0.95) / (1.06 − 0.95) = 0.6382。
f = e^{−0.02} × 0.6382 × 3 = 1.877。Δ = 3 / (53 − 47.5) = 0.5455。
</details>

**Q2.** アメリカンコール（配当なし株）は早期行使が最適にならない。なぜか？

<details><summary>解答</summary>

行使すると本質的価値 S−K しか得られないが、保有すれば時間価値＋K の支払い繰延べ
（金利分）＋下方プロテクションが残る。配当がなければ継続価値 > 本質的価値が常に成立（Ch.11 参照）。
</details>

**Q3.** μ=20%, σ=30% の株式の、1年後の対数収益率の期待値は？

<details><summary>解答</summary>

μ − σ²/2 = 0.20 − 0.045 = 15.5%。期待値 E[S_T]=S0·e^{0.20} と混同しないこと。
</details>""")
)

# Cell 30: summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 |
|---|---|
| リスク中立評価 | 実確率は不要。p=(a−d)/(u−d) で期待値→無リスク割引 |
| CRR ツリー | u=e^{σ√Δt}, d=1/u。N→∞ で BSM に収束（誤差 O(1/N), 奇偶振動） |
| アメリカン | 各ノードで max(継続価値, 本質的価値)。プットは行使域あり |
| ウィーナー過程 | Δz=ε√Δt。不確実性は √t で成長 |
| GBM | dS=μS dt+σS dz。S_T は対数正規 |
| 伊藤の補題 | (Δx)²→b²Δt。d(lnS) のドリフトは μ−σ²/2 |

**次へ**: `notebooks/bsm_chapter15.ipynb`（Ch.15 — GBM＋伊藤の補題から BSM 公式へ）
**シリーズ**: `johnhull/ROADMAP.md` 参照""")
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
for i, cell in enumerate(nb["cells"]):
    cell["id"] = f"cell-{i:03d}"
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
