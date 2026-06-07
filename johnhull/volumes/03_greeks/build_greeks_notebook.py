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
- **デルタヘッジシミュレーション**（中核）— Hull Tables 19.1–19.4 と同形式の比較
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
BSM 理論価値は 1株あたり \$2.40（計24万ドル。Hull の例では 30万ドルで販売し、差額6万ドルがマージン）。
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
    md(r"""## 5. ストップロス戦略はなぜ失敗するか（§19.2）

「$S>K$ になったら1株買い、$S<K$ になったら売る」という素朴な戦略（Table 19.1）。
一見 $K$ で売買すればコストゼロに見えますが、実際は
**$K$ ちょうどでは取引できず**、上抜けでは $K+\epsilon$ で買い、下抜けでは $K-\epsilon$ で売る。
$S$ が $K$ 近傍を往復するたびにコストが嵩み、観測頻度を上げても性能が**収束しません**。""")
)

# Cell 11: frequency sweep comparison
cells.append(
    code(r"""# --- 性能指標 = std(コスト)/BSM価格 の頻度依存（Tables 19.1 vs 19.4 と同形式） ---
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
# Section 3: gamma, theta, PDE
# ===========================================================================

# Cell 14: gamma = curvature
cells.append(
    md(r"""## 7. ガンマ＝曲率（§19.6）

デルタだけの線形近似は $S$ が大きく動くと外れます。誤差の主因が曲率＝ガンマ：

$$f(S+\Delta S) \approx f(S) + \Delta\,\Delta S + \tfrac{1}{2}\Gamma\,(\Delta S)^2$$

ガンマは ATM で最大、満期直前に鋭くスパイクします（上のパネルで確認済み）。
ガンマ中立化には**オプションが必要**（原資産は Γ=0 なので使えない）。""")
)

# Cell 15: delta-approx error chart
cells.append(
    code(r"""# --- 線形近似 vs ガンマ補正（静的） ---
S0_C, K_C, R_C, SIG_C, T_C = 100.0, 100.0, 0.05, 0.25, 0.5
f0 = bsm.call_price(S0_C, K_C, R_C, SIG_C, T_C)
d0 = bsm.call_delta(S0_C, K_C, R_C, SIG_C, T_C)
g0 = bsm.gamma(S0_C, K_C, R_C, SIG_C, T_C)
s_axis = np.linspace(70.0, 130.0, 241)
exact = np.array([bsm.call_price(s, K_C, R_C, SIG_C, T_C) for s in s_axis])
linear = f0 + d0 * (s_axis - S0_C)
quad = linear + 0.5 * g0 * (s_axis - S0_C) ** 2

fig4, ax4 = plt.subplots(figsize=(8, 4.5))
fig4.canvas.header_visible = False
ax4.plot(s_axis, exact, lw=2, label="BSM 価格（厳密）")
ax4.plot(s_axis, linear, ls="--", lw=1.5, label="線形（Δのみ）")
ax4.plot(s_axis, quad, ls=":", lw=2, label="2次（Δ + ½Γ(ΔS)²）")
ax4.axvline(S0_C, color="0.7", ls=":", lw=1)
ax4.set_xlabel("株価 S")
ax4.set_ylabel("コール価格")
ax4.set_title(f"S0={S0_C:.0f} でのテイラー近似（Δ={d0:.3f}, Γ={g0:.4f}）")
ax4.legend()
display(fig4.canvas)""")
)

# Cell 16: theta and tradeoff
cells.append(
    md(r"""## 8. シータと Θ-Γ トレードオフ（§19.5, §19.7）

シータは時間減価。ATM 付近で最も負が深く、満期に向けて加速します。
デルタニュートラルなポートフォリオでは BSM PDE（eq 19.4）から：

$$\Theta + \tfrac{1}{2}\sigma^2 S^2 \Gamma = r\Pi$$

つまり **Γ を買えば（大きく動けば儲かる）Θ を払う**、Γ を売れば Θ を受け取る。
ガンマスカルピングの損益と時間減価は表裏一体です。""")
)

# Cell 17: theta charts + PDE check
cells.append(
    code(r"""# --- シータの形状と BSM PDE 恒等式 ---
fig5, (ax5a, ax5b) = plt.subplots(1, 2, figsize=(10, 4))
fig5.canvas.header_visible = False
for T_i in (0.1, 0.5, 1.0):
    ax5a.plot(s_axis, [bsm.call_theta(s, K_C, R_C, SIG_C, T_i) for s in s_axis],
              lw=1.5, label=f"T={T_i}")
ax5a.axvline(K_C, color="0.7", ls=":", lw=1)
ax5a.set_xlabel("株価 S")
ax5a.set_ylabel("Θ（/年）")
ax5a.set_title("シータ vs S（ATM が最も深い）")
ax5a.legend()
taus = np.linspace(0.02, 1.0, 100)
ax5b.plot(taus, [bsm.call_theta(K_C, K_C, R_C, SIG_C, t) for t in taus], lw=2)
ax5b.set_xlabel("残存期間 T（年）")
ax5b.set_ylabel("ATM の Θ（/年）")
ax5b.set_title("満期接近で時間減価が加速")
display(fig5.canvas)

lhs = (bsm.call_theta(S_H, K_H, R_H, SIG_H, T_H)
       + R_H * S_H * bsm.call_delta(S_H, K_H, R_H, SIG_H, T_H)
       + 0.5 * SIG_H**2 * S_H**2 * bsm.gamma(S_H, K_H, R_H, SIG_H, T_H))
rhs = R_H * bsm.call_price(S_H, K_H, R_H, SIG_H, T_H)
print(f"PDE 恒等式: Θ+rSΔ+½σ²S²Γ = {lhs:.6f} ／ r·c = {rhs:.6f} ／ 差 {abs(lhs - rhs):.2e}")""")
)

# Cell 18: delta-neutral P&L
cells.append(
    md(r"""### デルタニュートラル・ポートフォリオの P&L（eq 19.3）

デルタを消した後に残るのは：

$$\Delta\Pi \approx \Theta\,\Delta t + \tfrac{1}{2}\Gamma\,(\Delta S)^2$$

ロングガンマなら「動けば得・動かなければ Θ 分の損」の放物線になります。""")
)

# Cell 19: P&L parabola demo
cells.append(
    code(r"""# --- 1日後の P&L: 厳密再評価 vs Θdt + ½Γ(ΔS)²（デルタ消去済み） ---
dt_1d = 1.0 / 252.0
ds_grid = np.linspace(-8.0, 8.0, 81)
pnl_exact = np.array([
    bsm.call_price(S0_C + ds, K_C, R_C, SIG_C, T_C - dt_1d)
    - f0 - d0 * ds  # デルタヘッジ済み（株 -Δ 保有）
    for ds in ds_grid
])
pnl_approx = bsm.call_theta(S0_C, K_C, R_C, SIG_C, T_C) * dt_1d + 0.5 * g0 * ds_grid**2

fig6, ax6 = plt.subplots(figsize=(8, 4.5))
fig6.canvas.header_visible = False
ax6.plot(ds_grid, pnl_exact, lw=2, label="厳密（再評価）")
ax6.plot(ds_grid, pnl_approx, ls="--", lw=2, label="Θdt + ½Γ(ΔS)²")
ax6.axhline(0.0, color="black", lw=0.8)
ax6.set_xlabel("1日の株価変化 ΔS")
ax6.set_ylabel("デルタ中立 P&L（ロングコール+ヘッジ）")
ax6.set_title("ロングガンマの放物線: 動けば得、動かなければ Θ 分の損")
ax6.legend()
display(fig6.canvas)""")
)

# ===========================================================================
# Section 4: joint gamma-vega neutralization
# ===========================================================================

# Cell 20: md
cells.append(
    md(r"""## 9. ガンマ・ベガの同時中立化（§19.6, §19.8）

原資産はデルタしか動かせないので、Γ と V を消すには**取引可能なオプションが2本**必要：

$$\begin{pmatrix} \Gamma_1 & \Gamma_2 \\ \mathcal{V}_1 & \mathcal{V}_2 \end{pmatrix}
\begin{pmatrix} w_1 \\ w_2 \end{pmatrix} =
\begin{pmatrix} -\Gamma_\Pi \\ -\mathcal{V}_\Pi \end{pmatrix}$$

解いた後、原資産でデルタを 0 に戻します（中立化は**瞬間的** — 時間が経てば再調整）。""")
)

# Cell 21: two-option solve
cells.append(
    code(r"""# --- ポートフォリオ: ATMコール 1000枚のショート ---
S_P, R_P, SIG_P = 100.0, 0.05, 0.25
port = -1000.0
K_p, T_p = 100.0, 0.5
opt1 = dict(K=95.0, T=0.75)   # 取引オプション1
opt2 = dict(K=110.0, T=0.25)  # 取引オプション2

g_port = port * bsm.gamma(S_P, K_p, R_P, SIG_P, T_p)
v_port = port * bsm.vega(S_P, K_p, R_P, SIG_P, T_p)
d_port = port * bsm.call_delta(S_P, K_p, R_P, SIG_P, T_p)

A = np.array([
    [bsm.gamma(S_P, opt1["K"], R_P, SIG_P, opt1["T"]), bsm.gamma(S_P, opt2["K"], R_P, SIG_P, opt2["T"])],
    [bsm.vega(S_P, opt1["K"], R_P, SIG_P, opt1["T"]), bsm.vega(S_P, opt2["K"], R_P, SIG_P, opt2["T"])],
])
w1, w2 = np.linalg.solve(A, np.array([-g_port, -v_port]))
d_after = (d_port + w1 * bsm.call_delta(S_P, opt1["K"], R_P, SIG_P, opt1["T"])
           + w2 * bsm.call_delta(S_P, opt2["K"], R_P, SIG_P, opt2["T"]))
shares = -d_after  # 原資産でデルタを消す

g_res = g_port + w1 * A[0, 0] + w2 * A[0, 1]
v_res = v_port + w1 * A[1, 0] + w2 * A[1, 1]
display(pd.DataFrame([
    {"項目": "ヘッジ前", "Δ": round(d_port, 1), "Γ": round(g_port, 2), "V": round(v_port, 1)},
    {"項目": f"opt1 {w1:+.0f}枚 / opt2 {w2:+.0f}枚 / 株 {shares:+.0f}",
     "Δ": 0.0, "Γ": round(float(g_res), 10), "V": round(float(v_res), 10)},
]))
print("Γ・V の残差は数値誤差レベル（恒等的に0）。Θ は引き続き残る点に注意")""")
)

# ===========================================================================
# Section 5: rho
# ===========================================================================

# Cell 22: rho md
cells.append(
    md(r"""## 10. ロー（§19.9）

$$\rho_{\text{call}} = K T e^{-rT} N(d_2) > 0, \qquad \rho_{\text{put}} = -K T e^{-rT} N(-d_2) < 0$$

満期が長いほど金利感応度は大きくなります。
通貨オプションには外国金利 $r_f$ に対する**第2のロー**もあります（§19.12）
（コール: $-T e^{-r_f T} S N(d_1)$）。""")
)

# Cell 23: rho chart
cells.append(
    code(r"""fig7, ax7 = plt.subplots(figsize=(7, 4))
fig7.canvas.header_visible = False
taus7 = np.linspace(0.05, 3.0, 100)
ax7.plot(taus7, [bsm.call_rho(100.0, 100.0, 0.05, 0.25, t) for t in taus7], lw=2, label="コール ρ")
ax7.plot(taus7, [bsm.put_rho(100.0, 100.0, 0.05, 0.25, t) for t in taus7], lw=2, label="プット ρ")
ax7.axhline(0.0, color="black", lw=0.8)
ax7.set_xlabel("満期 T（年）")
ax7.set_ylabel("ρ")
ax7.set_title("金利感応度は満期にほぼ比例して拡大（ATM）")
ax7.legend()
display(fig7.canvas)""")
)

# ===========================================================================
# Section 6: portfolio insurance
# ===========================================================================

# Cell 24: synthetic put md
cells.append(
    md(r"""## 11. 合成プット＝ポートフォリオ保険（§19.13）

プットを買う代わりに、プットの**デルタを動的に複製**する：
ポートフォリオの比率 $e^{-qT}[1 - N(d_1)]$ を売却して無リスク資産へ移す
（残り＝株式で保有。$q=0$ なら保有比率は $N(d_1)$）。

価値が下がるほど株を売り、上がるほど買い戻す — この「下落で売る」群衆行動が
**1987年10月のクラッシュ**で流動性を枯渇させ、戦略は機能しませんでした。
（モデルの前提「摩擦なく連続取引できる」が、皆が同じ行動を取ると崩れる）""")
)

# Cell 25: synthetic put weights chart
cells.append(
    code(r"""# --- 合成プットの株式保有比率（保護水準 K=100, T=1, σ=15% ） ---
vals = np.linspace(60.0, 140.0, 161)
frac_keep = np.array([bsm.call_delta(v, 100.0, 0.05, 0.15, 1.0) for v in vals])  # N(d1)

fig8, ax8 = plt.subplots(figsize=(7.5, 4))
fig8.canvas.header_visible = False
ax8.plot(vals, frac_keep * 100, lw=2)
ax8.axvline(100.0, color="0.7", ls=":", lw=1)
ax8.set_xlabel("ポートフォリオ価値（保護水準=100）")
ax8.set_ylabel("株式で保有する比率 N(d1) [%]")
ax8.set_title("価値下落 → 株式比率を下げる（売る）/ 回復 → 買い戻す")
display(fig8.canvas)
print("60 まで下落すると株式比率は "
      f"{bsm.call_delta(60.0, 100.0, 0.05, 0.15, 1.0):.1%} まで縮小 — 下げ相場で売り続ける戦略")""")
)

# ===========================================================================
# Section 7: verification / exercises / summary
# ===========================================================================

# Cell 26: verification intro
cells.append(
    md(r"""## 12. 教科書例題との突合せ

Hull §19 の通し例（S=49, K=50, r=5%, σ=20%, T=0.3846）の全 Greeks、
BSM PDE 恒等式、ヘッジシミュレーションの収束性を assert します。
（`hullkit/tests/test_greeks.py`, `test_hedging.py` にも同じ検証あり）""")
)

# Cell 27: assertion cell
cells.append(
    code(r"""checks = []
c_ref = bsm.call_price(S_H, K_H, R_H, SIG_H, T_H)
checks.append(("Δ 0.5216 (Hull 0.522)", bsm.call_delta(S_H, K_H, R_H, SIG_H, T_H), 0.5216, 5e-4))
checks.append(("Γ 0.0655 (0.066)", bsm.gamma(S_H, K_H, R_H, SIG_H, T_H), 0.06555, 5e-4))
checks.append(("V 12.105 (12.1)", bsm.vega(S_H, K_H, R_H, SIG_H, T_H), 12.105, 2e-2))
checks.append(("Θ −4.3055 (−4.31)", bsm.call_theta(S_H, K_H, R_H, SIG_H, T_H), -4.3055, 5e-3))
checks.append(("ρ 8.9066 (8.91)", bsm.call_rho(S_H, K_H, R_H, SIG_H, T_H), 8.9066, 1e-2))
checks.append(("価格 2.4004 (2.40)", c_ref, 2.4004, 1e-3))

lhs = (bsm.call_theta(S_H, K_H, R_H, SIG_H, T_H)
       + R_H * S_H * bsm.call_delta(S_H, K_H, R_H, SIG_H, T_H)
       + 0.5 * SIG_H**2 * S_H**2 * bsm.gamma(S_H, K_H, R_H, SIG_H, T_H))
checks.append(("BSM PDE 恒等式", lhs, R_H * c_ref, 1e-9))

costs20 = hedging.simulate_delta_hedge(S_H, K_H, R_H, SIG_H, T_H, 20, 10_000, mu=0.13)
checks.append(("ヘッジコスト平均 ≈ BSM", float(costs20.mean()), c_ref, 0.08))

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.4f} want={want:.4f} (tol={tol})")
    assert ok, name

perf5 = float(hedging.simulate_delta_hedge(
    S_H, K_H, R_H, SIG_H, T_H, 5, 10_000, mu=0.13).std()) / c_ref
perf80 = float(hedging.simulate_delta_hedge(
    S_H, K_H, R_H, SIG_H, T_H, 80, 10_000, mu=0.13).std()) / c_ref
sl80 = float(hedging.simulate_stop_loss_hedge(
    S_H, K_H, R_H, SIG_H, T_H, 80, 10_000, mu=0.13).std()) / c_ref
print(f"[OK] 性能: delta n=5 {perf5:.3f} > n=80 {perf80:.3f}（高頻度化で改善）")
assert perf80 < perf5
print(f"[OK] ストップロス n=80 {sl80:.3f} > 2×デルタ {2 * perf80:.3f}（収束しない）")
assert sl80 > 2.0 * perf80
print("\n全チェック合格")""")
)

# Cell 28: exercises
cells.append(
    md(r"""## 13. 練習問題

**Q1.** Θ = −0.012/日 のデルタ中立ポートフォリオが1日「何も起きず」に終わった。P&L は？

<details><summary>解答</summary>

約 −0.012（Θ 分の減価）。ロングガンマならこの損失は (ΔS)² の利益で相殺されるはずだった。
</details>

**Q2.** ポートフォリオの Γ=−3000, V=−8000。取引オプション（Γ=0.5, V=10）1種類だけで両方消せるか？

<details><summary>解答</summary>

消せない。w·0.5=3000 → w=6000 だが、そのとき V 寄与は 60,000 ≠ 8000。
Γ と V を同時に消すには独立な2本目のオプションが必要（2×2連立）。
</details>

**Q3.** 先物（満期 T_F=0.5年、r=5%, q=0）でデルタヘッジする場合、現物換算 10,000株分に必要な先物は？

<details><summary>解答</summary>

H_F = e^{−rT_F} H_A = e^{−0.025} × 10,000 ≈ 9,753 株分（eq 19.5、q 一般形は eq 19.6）。
先物のデルタが e^{rT_F} > 1 のため、必要枚数は少なくなる。
</details>""")
)

# Cell 29: summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 |
|---|---|
| Δ | ヘッジ比率。動的リバランスが必須（ヘッジコスト平均=BSM価格、μ非依存） |
| ストップロス | 高頻度化しても性能が収束しない（Table 19.1） |
| Γ | 曲率。ATM・満期間際でスパイク。中立化にはオプションが必要 |
| Θ-Γ | Θ + ½σ²S²Γ = rΠ（デルタ中立時）。ガンマを買えばシータを払う |
| V | ボラ感応度。Γ と独立に消すには2本目のオプション |
| 合成プット | プットのΔを複製＝下落で売る。1987年に流動性前提が崩壊 |

**次へ**: `volumes/04_futures_forwards_rates`（Ch.2–6）または `volumes/05_vol_smile_estimation`（Ch.20, 23 — V の前提を緩める）
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
