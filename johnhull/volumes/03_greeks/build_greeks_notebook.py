"""
build_greeks_notebook.py
================================
nbformat-dict pattern to generate greeks.ipynb (Hull 11e Ch.19).

Usage:
    uv run python build_greeks_notebook.py
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
    md(r"""# ギリシャ文字編: 感応度とヘッジ（Hull 11e Ch.19）

`johnhull/volumes` シリーズ第3冊。オプションのリスク管理を扱います：

- **Δ・Γ・Θ・V・ρ** — 価格感応度の体系（`hullkit.bsm` に解析式を実装済み）
- **デルタヘッジシミュレーション**（中核）— Hull Tables 19.1–19.4 の再現
- **ガンマ＝曲率**、Θ-Γ トレードオフ、BSM PDE 恒等式
- **ガンマ・ベガ同時中立化**、合成プット（ポートフォリオ保険）

> 前提: 第1冊（BSM・CRR）、第2冊（オプション基礎）。共通関数は `hullkit` から import""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display

from hullkit import bsm, hedging, mc, nbplot

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Greeks tour
# ===========================================================================

# Cell 03: overview + Taylor
cells.append(
    md(r"""## 1. ギリシャ文字の体系（§19.1–19.9）

ポートフォリオ価値 $\Pi$ の変化はテイラー展開で近似できます：

$$\Delta\Pi \approx \underbrace{\Delta}_{\partial\Pi/\partial S}\Delta S
+ \underbrace{\Theta}_{\partial\Pi/\partial t}\Delta t
+ \tfrac{1}{2}\underbrace{\Gamma}_{\partial^2\Pi/\partial S^2}(\Delta S)^2
+ \underbrace{\mathcal{V}}_{\partial\Pi/\partial\sigma}\Delta\sigma + \cdots$$

| Greek | 定義 | 直感 |
|---|---|---|
| Δ デルタ | $\partial f/\partial S$ | 原資産1単位の変化に対する感応度。ヘッジ比率 |
| Γ ガンマ | $\partial^2 f/\partial S^2$ | デルタの変化率＝価格曲線の曲率 |
| Θ シータ | $\partial f/\partial t$ | 時間減価（通常マイナス） |
| V ベガ | $\partial f/\partial\sigma$ | ボラティリティ感応度（ギリシャ文字ではない！） |
| ρ ロー | $\partial f/\partial r$ | 金利感応度 |

単位の注意: Θ は**年率**（÷365 で1日あたり）、V は**ボラ1.0あたり**（÷100 で1%あたり）。""")
)

# Cell 04: interactive Greeks panel
cells.append(
    code(r"""# --- Δ Γ Θ V ρ の S 依存性（インタラクティブ） ---
fig1, axes1 = plt.subplots(2, 3, figsize=(11, 6), sharex=True)
fig1.canvas.header_visible = False
K_G, R_G, SIG_G = 100.0, 0.05, 0.25
S_AXIS = np.linspace(50.0, 150.0, 201)

t_sl = widgets.FloatSlider(value=0.5, min=0.05, max=2.0, step=0.05, description="T")
kind_dd = widgets.Dropdown(options=["call", "put"], value="call", description="種別")


def _upd_greeks(change=None):
    T = t_sl.value
    is_call = kind_dd.value == "call"
    price_f = bsm.call_price if is_call else bsm.put_price
    delta_f = bsm.call_delta if is_call else bsm.put_delta
    theta_f = bsm.call_theta if is_call else bsm.put_theta
    rho_f = bsm.call_rho if is_call else bsm.put_rho
    panels = [
        ("価格", [price_f(s, K_G, R_G, SIG_G, T) for s in S_AXIS]),
        ("Δ デルタ", [delta_f(s, K_G, R_G, SIG_G, T) for s in S_AXIS]),
        ("Γ ガンマ", [bsm.gamma(s, K_G, R_G, SIG_G, T) for s in S_AXIS]),
        ("Θ シータ（/年）", [theta_f(s, K_G, R_G, SIG_G, T) for s in S_AXIS]),
        ("V ベガ", [bsm.vega(s, K_G, R_G, SIG_G, T) for s in S_AXIS]),
        ("ρ ロー", [rho_f(s, K_G, R_G, SIG_G, T) for s in S_AXIS]),
    ]
    for ax, (title, ys) in zip(axes1.ravel(), panels):
        ax.clear()
        ax.plot(S_AXIS, ys, lw=2)
        ax.axvline(K_G, color="0.7", ls=":", lw=1)
        ax.set_title(title, fontsize=10)
    fig1.suptitle(f"{kind_dd.value}  K={K_G:.0f}, r={R_G:.0%}, σ={SIG_G:.0%}, T={T:.2f}年", fontsize=10)
    fig1.canvas.draw_idle()


t_sl.observe(_upd_greeks, "value")
kind_dd.observe(_upd_greeks, "value")
_upd_greeks()
display(widgets.HBox([t_sl, kind_dd]), fig1.canvas)
# T を小さくすると ATM の Γ がスパイクすることを確認""")
)

# Cell 05: Hull running example
cells.append(
    md(r"""## 2. Hull の通し例（§19.1）

**100,000株分のコールを売った**ディーラーを考えます:
$S_0=49$, $K=50$, $r=5\%$, $\sigma=20\%$, $T=20$週（0.3846年）。
BSM 価格は 1株あたり \$2.40（=24万ドルの受取り）。
このネイキッドポジションをどうヘッジするかが本章のテーマです。""")
)

# Cell 06: example Greeks table
cells.append(
    code(r"""S_H, K_H, R_H, SIG_H, T_H = 49.0, 50.0, 0.05, 0.20, 0.3846
rows = [
    {"Greek": "価格", "値": round(bsm.call_price(S_H, K_H, R_H, SIG_H, T_H), 4), "Hull": 2.40},
    {"Greek": "Δ", "値": round(bsm.call_delta(S_H, K_H, R_H, SIG_H, T_H), 4), "Hull": 0.522},
    {"Greek": "Γ", "値": round(bsm.gamma(S_H, K_H, R_H, SIG_H, T_H), 4), "Hull": 0.066},
    {"Greek": "Θ（/年）", "値": round(bsm.call_theta(S_H, K_H, R_H, SIG_H, T_H), 4), "Hull": -4.31},
    {"Greek": "Θ（/日）", "値": round(bsm.call_theta(S_H, K_H, R_H, SIG_H, T_H) / 365, 4), "Hull": -0.0118},
    {"Greek": "V", "値": round(bsm.vega(S_H, K_H, R_H, SIG_H, T_H), 4), "Hull": 12.1},
    {"Greek": "ρ", "値": round(bsm.call_rho(S_H, K_H, R_H, SIG_H, T_H), 4), "Hull": 8.91},
]
display(pd.DataFrame(rows))
print("Vは「ボラ1.0あたり」→ σが1%動くと 12.1/100 ≈ 0.121 ドル動く")""")
)

# Cell 07: Table 19.6 generalization
cells.append(
    md(r"""## 3. q による統一（Table 19.6）と先物デルタ

第2冊と同じく、連続利回り $q$ で指数（$q$=配当利回り）・通貨（$q=r_f$）・
先物（$q=r$）の Greeks が統一的に得られます（`hullkit.bsm` は全関数 `q` 引数対応）。

- フォワードのデルタ: $e^{-qT}$（無配当なら 1）
- **先物のデルタ**: $e^{(r-q)T}$ — 現物1.0とは異なる！
  先物でデルタヘッジする場合の必要枚数は $H_F = e^{-(r-q)T} H_A$（eq 19.6）""")
)

# ===========================================================================
# Section 2: delta hedging (centerpiece)
# ===========================================================================

# Cell 08: dynamic hedging mechanics
cells.append(
    md(r"""## 4. 動的デルタヘッジ（§19.4）

コールの売り手は $\Delta \times 100{,}000$ 株を保有すればデルタニュートラル。
ただし $\Delta$ は $S$ と $t$ で変わるため**リバランスし続ける**必要があります。

手順（毎週）: ① 新しい $S$ で $\Delta$ を再計算 → ② 株数を $\Delta \times N$ に調整 →
③ 資金コストは金利 $r$ で累積。満期に ITM なら株を $K$ で引き渡し。

連続リバランスの極限でヘッジコストは**BSM 価格に一致**します（＝BSM の複製論法そのもの）。
離散リバランスではコストに分散が残ります。""")
)

# Cell 09: single-path hedge table (Table 19.2 format)
cells.append(
    code(r"""# --- 1パスのヘッジ表（Hull Table 19.2 形式、週次20回） ---
N_W = 20
rng_demo = np.random.default_rng(12)
path = mc.simulate_gbm_paths(S_H, 0.13, SIG_H, T_H, N_W, 1, rng=rng_demo)[0]
dt_w = T_H / N_W
growth_w = np.exp(R_H * dt_w)

rows, debt, holdings = [], 0.0, 0.0
for i in range(N_W + 1):
    tau = T_H - i * dt_w
    if i < N_W:
        delta_i = bsm.call_delta(path[i], K_H, R_H, SIG_H, tau)
    else:
        delta_i = 1.0 if path[i] > K_H else 0.0  # 満期: 行使されれば1株必要
    traded = delta_i - holdings
    debt = (debt * growth_w if i > 0 else 0.0) + traded * path[i]
    rows.append({
        "週": i, "S": round(path[i], 2), "Δ": round(delta_i, 3),
        "売買株数(/株)": round(traded, 3), "累積コスト": round(debt, 3),
    })
    holdings = delta_i
if path[-1] > K_H:
    debt -= K_H  # 1株を K で引き渡し
df_hedge = pd.DataFrame(rows)
display(df_hedge)
pv_cost = debt * np.exp(-R_H * T_H)
print(f"満期精算後の累積コストPV = {pv_cost:.4f} ／ BSM価格 = {bsm.call_price(S_H, K_H, R_H, SIG_H, T_H):.4f}")
print("（1パスでは一致しない。平均すると一致する — 下のセルで確認）")""")
)

# Cell 10: stop-loss strategy
cells.append(
    md(r"""## 5. ストップロス戦略はなぜ失敗するか（§19.3）

「$S>K$ になったら1株買い、$S<K$ になったら売る」という素朴な戦略（Table 19.1）。
一見 $K$ で売買すればコストゼロに見えますが、実際は
**$K$ ちょうどでは取引できず**、上抜けでは $K+\epsilon$ で買い、下抜けでは $K-\epsilon$ で売る。
$S$ が $K$ 近傍を往復するたびにコストが嵩み、観測頻度を上げても性能が**収束しません**。""")
)

# Cell 11: frequency sweep comparison
cells.append(
    code(r"""# --- 性能指標 = std(コスト)/BSM価格 の頻度依存（Tables 19.1 vs 19.4 の再現） ---
c_bsm = bsm.call_price(S_H, K_H, R_H, SIG_H, T_H)
n_rebs = [4, 5, 10, 20, 40, 80]
rows = []
for j, n in enumerate(n_rebs):
    dh = hedging.simulate_delta_hedge(
        S_H, K_H, R_H, SIG_H, T_H, n, 4000, mu=0.13, rng=np.random.default_rng(100 + j)
    )
    sl = hedging.simulate_stop_loss_hedge(
        S_H, K_H, R_H, SIG_H, T_H, n, 4000, mu=0.13, rng=np.random.default_rng(100 + j)
    )
    rows.append({
        "リバランス回数": n,
        "デルタヘッジ性能": round(float(dh.std()) / c_bsm, 3),
        "ストップロス性能": round(float(sl.std()) / c_bsm, 3),
    })
df_perf = pd.DataFrame(rows)
display(df_perf)

fig2, ax2 = plt.subplots(figsize=(7, 4))
fig2.canvas.header_visible = False
ax2.loglog(n_rebs, df_perf["デルタヘッジ性能"], "o-", label="デルタヘッジ")
ax2.loglog(n_rebs, df_perf["ストップロス性能"], "s-", label="ストップロス")
ref = df_perf["デルタヘッジ性能"].iloc[0] * np.sqrt(n_rebs[0] / np.array(n_rebs, dtype=float))
ax2.loglog(n_rebs, ref, "k:", lw=1, label="〜1/√n 参照線")
ax2.set_xlabel("リバランス回数 n")
ax2.set_ylabel("性能指標 std/BSM価格（小さいほど良い）")
ax2.legend()
display(fig2.canvas)""")
)

# Cell 12: distribution interpretation
cells.append(
    md(r"""## 6. ヘッジコストの分布（§19.4 の含意）

- **平均はドリフト $\mu$ に依存しない**（リスク中立評価の体感）— 下で $\mu$ を動かして確認
- 分散は離散リバランスの結果で、リバランス頻度 $n$ に対して $\propto 1/n$（性能指標は $1/\sqrt{n}$）
- この分散は「ガンマに対して $(\Delta S)^2$ が暴れる」ことから生じる（次節）""")
)

# Cell 13: interactive cost histogram
cells.append(
    code(r"""# --- ヘッジコスト分布（インタラクティブ: 頻度とμ） ---
fig3, ax3 = plt.subplots(figsize=(8, 4.5))
fig3.canvas.header_visible = False
n_dd = widgets.Dropdown(options=[5, 20, 80], value=20, description="リバランス")
mu_sl = widgets.FloatSlider(value=0.13, min=-0.05, max=0.30, step=0.01, description="μ")


def _upd_hist(change=None):
    ax3.clear()
    costs = hedging.simulate_delta_hedge(
        S_H, K_H, R_H, SIG_H, T_H, n_dd.value, 4000, mu=mu_sl.value,
        rng=np.random.default_rng(7),
    )
    ax3.hist(costs, bins=60, alpha=0.75)
    ax3.axvline(c_bsm, color="crimson", ls="--", lw=2, label=f"BSM価格 {c_bsm:.3f}")
    ax3.axvline(float(costs.mean()), color="black", lw=2,
                label=f"平均 {costs.mean():.3f}（μ={mu_sl.value:.2f}）")
    ax3.set_xlabel("割引後ヘッジコスト（/株）")
    ax3.set_title(f"n={n_dd.value}: std={costs.std():.3f}  性能={costs.std() / c_bsm:.3f}")
    ax3.legend()
    fig3.canvas.draw_idle()


n_dd.observe(_upd_hist, "value")
mu_sl.observe(_upd_hist, "value")
_upd_hist()
display(widgets.HBox([n_dd, mu_sl]), fig3.canvas)
# μ を動かしても平均は BSM 価格に張り付く（リスク中立評価の実演）""")
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "greeks.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
