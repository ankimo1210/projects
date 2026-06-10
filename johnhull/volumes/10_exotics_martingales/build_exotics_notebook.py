"""
build_exotics_notebook.py
================================
nbformat-dict pattern to generate exotics.ipynb (Hull 11e Ch.26, 28).

Usage:
    uv run python build_exotics_notebook.py
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
    md(r"""# エキゾチック・オプションと測度（Hull 11e Ch.26, 28）

`johnhull/volumes` シリーズ第10冊。複雑なペイオフと、その背後の数学：

- **エキゾチック（Ch.26）** — バイナリ、バリア、ルックバック、アジアン、交換（Margrabe）、バリアンス・スワップ
- **マルチンゲールと測度（Ch.28）** — ニュメレール、市場リスクの価格 λ、フォワード測度

> 共通関数は `hullkit`（exotics / bsm / mc / nbplot）から import。
> 第6冊（数値解法）・第5冊（スマイル）の道具がここで効きます""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import math

import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
from scipy.stats import norm

from hullkit import bsm, exotics, mc, nbplot

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.26 exotics
# ===========================================================================

# Cell 03: taxonomy md
cells.append(
    md(r"""## 1. エキゾチックの分類（Ch.26）

OTC で取引される非標準ペイオフ。多くは GBM 仮定下で**解析解**を持ちます：

| 型 | 特徴 | 評価 |
|---|---|---|
| パッケージ | バニラの組み合わせ | バニラの和 |
| バイナリ | 不連続ペイオフ | cash/asset-or-nothing |
| バリア | 到達で発生/消滅 | 閉形式（in+out=vanilla） |
| ルックバック | 経路の最大/最小 | 閉形式 |
| アジアン | 平均価格 | 算術平均は近似/MC |
| 交換 | 資産を資産と交換 | Margrabe（r非依存） |
| バリアンス・スワップ | 実現分散 | ログ・コントラクト静的複製 |""")
)

# Cell 04: binary md
cells.append(
    md(r"""## 2. バイナリ・オプション（§26.10）

- **cash-or-nothing**: ITM なら固定額 $Q$ → $Q e^{-rT} N(d_2)$（コール）
- **asset-or-nothing**: ITM なら原資産 → $S_0 e^{-qT} N(d_1)$（コール）

バニラはこの2つに分解できます： $c = c_{\text{aon}}(K) - K\,c_{\text{con}}(K)$。
（第2冊のバタフライ＝建築ブロックの連続極限とも整合）""")
)

# Cell 05: binary demo
cells.append(
    code(r"""S_B, K_B, R_B, SIG_B, T_B = 100.0, 100.0, 0.05, 0.20, 1.0
aon = exotics.asset_or_nothing(S_B, K_B, R_B, SIG_B, T_B, kind="call")
con = exotics.cash_or_nothing(S_B, K_B, R_B, SIG_B, T_B, kind="call", payout=1.0)
van = bsm.call_price(S_B, K_B, R_B, SIG_B, T_B)
print(f"asset-or-nothing = {aon:.4f}")
print(f"cash-or-nothing（Q=1）= {con:.4f}")
print(f"分解 aon − K·con = {aon - K_B * con:.4f} ／ バニラ = {van:.4f}（恒等）")

s_grid = np.linspace(60.0, 140.0, 400)
fig1, ax1 = plt.subplots(figsize=(8, 4))
fig1.canvas.header_visible = False
ax1.plot(s_grid, np.where(s_grid > K_B, 1.0, 0.0), lw=2, label="cash-or-nothing（Q=1）満期ペイオフ")
ax1.plot(s_grid, np.where(s_grid > K_B, s_grid, 0.0) / 100.0, lw=2, ls="--",
         label="asset-or-nothing /100")
ax1.set_xlabel("満期株価 $S_T$")
ax1.set_ylabel("ペイオフ")
ax1.set_title("バイナリの不連続ペイオフ（K で跳ぶ）")
ax1.legend()
display(fig1.canvas)""")
)

# Cell 06: barrier md
cells.append(
    md(r"""## 3. バリア・オプション（§26.9）

バリア $H$ への到達で**発生（in）**または**消滅（out）**。
up/down × in/out × call/put の8種に閉形式があります。鍵となる関係：

$$c_{\text{di}} + c_{\text{do}} = c \quad (\text{ノックイン} + \text{ノックアウト} = \text{バニラ})$$

「どちらかには必ずなる」ので、合計はバリアのないバニラに等しくなります。
ノックアウトはバニラより安く（消える可能性のぶん）、人気の理由です。""")
)

# Cell 07: barrier demo + chart
cells.append(
    code(r"""# down-and-in/out call（H≤K）と in+out=vanilla
cdi = exotics.barrier_call(S_B, K_B, 90.0, R_B, SIG_B, T_B, barrier="down-and-in")
cdo = exotics.barrier_call(S_B, K_B, 90.0, R_B, SIG_B, T_B, barrier="down-and-out")
print(f"down-and-in = {cdi:.4f} ／ down-and-out = {cdo:.4f}")
print(f"in + out = {cdi + cdo:.4f} ／ バニラ = {van:.4f}（恒等）")

h_grid = np.linspace(60.0, 99.0, 40)
fig2, ax2 = plt.subplots(figsize=(7.5, 4))
fig2.canvas.header_visible = False
ax2.plot(h_grid, [exotics.barrier_call(S_B, K_B, h, R_B, SIG_B, T_B, barrier="down-and-in")
                  for h in h_grid], lw=2, label="down-and-in")
ax2.plot(h_grid, [exotics.barrier_call(S_B, K_B, h, R_B, SIG_B, T_B, barrier="down-and-out")
                  for h in h_grid], lw=2, label="down-and-out")
ax2.axhline(van, color="0.6", ls=":", lw=1.5, label="バニラ")
ax2.set_xlabel("バリア H")
ax2.set_ylabel("価格")
ax2.set_title("H が K に近いほどノックインしやすく di↑・do↓（和は一定）")
ax2.legend()
display(fig2.canvas)""")
)

# Cell 08: lookback md + demo
cells.append(
    code(r"""# --- フローティング・ルックバック・コール（min を行使価格に） ---
lb = exotics.lookback_floating_call(S_B, S_B, R_B, SIG_B, T_B)
print(f"フローティング・ルックバック・コール = {lb:.4f} ／ ATM バニラ = {van:.4f}")
print("（経路最安値で買える権利 → 常にバニラより高い。「後知恵」のプレミアム）")

rng_lb = np.random.default_rng(26)
path = mc.simulate_gbm_paths(S_B, R_B, SIG_B, T_B, 252, 1, rng=rng_lb)[0]
t_lb = np.linspace(0.0, T_B, 253)
running_min = np.minimum.accumulate(path)
fig3, ax3 = plt.subplots(figsize=(8, 4))
fig3.canvas.header_visible = False
ax3.plot(t_lb, path, lw=1.5, label="株価パス")
ax3.plot(t_lb, running_min, lw=1.5, ls="--", label="経路最小値（実効行使価格）")
ax3.axhline(path[-1], color="0.6", ls=":", lw=1, label=f"満期 S_T={path[-1]:.1f}")
ax3.set_xlabel("t（年）")
ax3.set_ylabel("価格")
ax3.set_title(f"ルックバック・ペイオフ = S_T − min = {path[-1] - running_min[-1]:.2f}")
ax3.legend()
display(fig3.canvas)""")
)

# Cell 09: asian md
cells.append(
    md(r"""## 4. アジアン・オプション（§26.13）

平均価格型は満期スポットではなく**経路平均**でペイオフ。
平均は変動を均すので**ボラが下がり、バニラより安く**なります。
算術平均には厳密な閉形式がなく、**Turnbull-Wakeman モーメント整合**（平均の
1次・2次モーメントを合わせて Black-76 に入力）か MC を使います。""")
)

# Cell 10: asian demo
cells.append(
    code(r"""a_tw = exotics.asian_call_turnbull_wakeman(S_B, K_B, R_B, SIG_B, T_B)
# MC（算術平均）
rng_a = np.random.default_rng(1)
paths_a = mc.simulate_gbm_paths(S_B, R_B, SIG_B, T_B, 252, 100_000, rng=rng_a)
avg_a = paths_a[:, 1:].mean(axis=1)
a_mc = math.exp(-R_B * T_B) * np.maximum(avg_a - K_B, 0.0).mean()
print(f"Turnbull-Wakeman アジアン = {a_tw:.4f}")
print(f"MC（算術平均、10万パス）   = {a_mc:.4f}")
print(f"バニラ ATM コール          = {van:.4f}（アジアンは平均化でボラ低下 → 安い）")

fig4, ax4 = plt.subplots(figsize=(8, 4))
fig4.canvas.header_visible = False
for i in range(20):
    ax4.plot(np.linspace(0, T_B, 253), paths_a[i], lw=0.6, alpha=0.5)
ax4.axhline(K_B, color="crimson", ls=":", lw=1.5, label="K")
ax4.set_xlabel("t（年）")
ax4.set_ylabel("S")
ax4.set_title("アジアンは満期値でなく経路平均で決済（平均がボラを均す）")
ax4.legend()
display(fig4.canvas)""")
)

# Cell 11: exchange md + demo
cells.append(
    code(r"""# --- 交換オプション（Margrabe）: 資産Uを資産Vと交換 ---
print("Margrabe は r に依存しない（exchange_option の引数に r がない）:")
print(f"  交換オプション価値 = {exotics.exchange_option(100.0, 100.0, 0.2, 0.2, 0.5, 1.0):.6f}")
print("  （一方の資産をニュメレールに取ると成長率↑と割引率↑が相殺するため）")
print("σ̂ = √(σ_U²+σ_V²−2ρσ_Uσ_V)。ρ が高いほど2資産が連動し交換の価値は下がる")
rows = []
for rho in (-0.5, 0.0, 0.5, 0.9):
    rows.append({"相関ρ": rho,
                 "交換オプション": round(exotics.exchange_option(100.0, 100.0, 0.2, 0.2, rho, 1.0), 4)})
display(pd.DataFrame(rows))""")
)

# Cell 12: variance swap md + demo
cells.append(
    code(r"""# --- バリアンス・スワップ: OTM オプションのストリップで複製（VIX 流） ---
# 公正バリアンス ≈ (2/T) Σ ΔK/K² e^{rT} Q(K)（Q は OTM オプション価格）
F0 = S_B * math.exp(R_B * T_B)
strikes_vs = np.arange(60.0, 145.0, 5.0)
fair_var = 0.0
for k in strikes_vs:
    if k < F0:
        price = bsm.put_price(S_B, k, R_B, SIG_B, T_B)
    else:
        price = bsm.call_price(S_B, k, R_B, SIG_B, T_B)
    fair_var += 5.0 / k**2 * math.exp(R_B * T_B) * price
fair_var *= 2.0 / T_B
print(f"ストリップ複製の公正バリアンス・レート = {fair_var:.5f}")
print(f"→ 公正ボラティリティ = {math.sqrt(fair_var):.4%}（入力 σ={SIG_B:.0%} を概ね回復）")
print("VIX も同型: OTM SPX オプションのストリップで30日先のバリアンスを測る")""")
)

# Cell 13: interactive barrier
cells.append(
    code(r"""# --- バリア・エクスプローラ（インタラクティブ） ---
fig5, ax5 = plt.subplots(figsize=(7.5, 4))
fig5.canvas.header_visible = False
h_sl = widgets.FloatSlider(value=90.0, min=70.0, max=99.0, step=1.0, description="H")
sig_b_sl = widgets.FloatSlider(value=0.20, min=0.10, max=0.50, step=0.02, description="σ")


def _upd_barrier(change=None):
    ax5.clear()
    ss = np.linspace(70.0, 140.0, 60)
    do = [exotics.barrier_call(s, K_B, h_sl.value, R_B, sig_b_sl.value, T_B,
                               barrier="down-and-out") if s > h_sl.value else 0.0
          for s in ss]
    van_curve = [bsm.call_price(s, K_B, R_B, sig_b_sl.value, T_B) for s in ss]
    ax5.plot(ss, van_curve, lw=1.5, ls=":", label="バニラ")
    ax5.plot(ss, do, lw=2, label="down-and-out")
    ax5.axvline(h_sl.value, color="crimson", ls="--", lw=1, label=f"H={h_sl.value:.0f}")
    # ノックアウト確率（GBM 初通過確率）
    bdrift = R_B - 0.5 * sig_b_sl.value**2
    lam_ko = math.log(h_sl.value / 100.0)
    sqT = sig_b_sl.value * math.sqrt(T_B)
    prob_ko = (norm.cdf((lam_ko - bdrift * T_B) / sqT)
               + math.exp(2 * bdrift * lam_ko / sig_b_sl.value**2) * norm.cdf((lam_ko + bdrift * T_B) / sqT))
    ax5.set_xlabel("現在株価 S")
    ax5.set_ylabel("価格")
    ax5.set_title(f"down-and-out（H={h_sl.value:.0f}, σ={sig_b_sl.value:.0%}）: "
                  f"S=100 でのノックアウト確率 ≈ {prob_ko:.1%}")
    ax5.legend()
    fig5.canvas.draw_idle()


h_sl.observe(_upd_barrier, "value")
sig_b_sl.observe(_upd_barrier, "value")
_upd_barrier()
display(widgets.HBox([h_sl, sig_b_sl]), fig5.canvas)""")
)

# ===========================================================================
# Section 2: Ch.28 martingales and measures
# ===========================================================================

# Cell 14: numeraire md
cells.append(
    md(r"""## 5. マルチンゲールと測度（Ch.28）

**マルチンゲール** = ドリフトゼロの過程（$E[\theta_T] = \theta_0$）。
**同値マルチンゲール測度の定理**: トレーダブル証券 $g$（ニュメレール）を選ぶと、
任意の証券価格 $f$ について $f/g$ がマルチンゲールになる測度が存在し：

$$f_0 = g_0\,E_g\!\left[\frac{f_T}{g_T}\right] \quad \text{(28.15)}$$

ニュメレールの選び方で「便利な測度」が得られます：
マネーマーケット口座 → リスク中立測度、ゼロクーポン債 → フォワード測度。""")
)

# Cell 15: market price of risk md
cells.append(
    md(r"""## 6. 市場リスクの価格 λ（§28.1）

ある確率変数 $\theta$ に依存する**すべての**デリバティブで、無裁定なら

$$\frac{\mu - r}{\sigma} = \lambda \quad \text{(28.8)}$$

が共通に成立（$\lambda$ は $\theta, t$ のみに依存、商品によらない）。
$\lambda$ はシャープ比に相当。リスク中立測度は $\lambda$ を 0 に「移す」測度です。""")
)

# Cell 16: market price of risk demo
cells.append(
    code(r"""# --- λ が2つのデリバティブで一致することの数値確認 ---
# 原資産 θ: dθ/θ = m dt + s dz。θに依存する2つのデリバティブ f1, f2 の (μ-r)/σ を比較
# BSM 世界では任意のオプションについて (μ_opt - r)/σ_opt = (μ_S - r)/σ_S = λ
S0_m, mu_S, sig_S, r_m = 100.0, 0.12, 0.20, 0.05
lam_underlying = (mu_S - r_m) / sig_S
# コールのリターン・ボラはデルタ弾性 Ω = (S/c)·Δ でスケール
for K_m, T_m in [(100.0, 0.5), (110.0, 1.0)]:
    c = bsm.call_price(S0_m, K_m, r_m, sig_S, T_m)
    delta = bsm.call_delta(S0_m, K_m, r_m, sig_S, T_m)
    omega = S0_m / c * delta  # 弾性
    sig_opt = omega * sig_S
    mu_opt = r_m + omega * (mu_S - r_m)  # CAPM 風
    lam_opt = (mu_opt - r_m) / sig_opt
    print(f"K={K_m}, T={T_m}: σ_opt={sig_opt:.3f}, (μ−r)/σ = {lam_opt:.4f}")
print(f"原資産の λ = (μ−r)/σ = {lam_underlying:.4f} ← すべて一致（無裁定）")""")
)

# Cell 17: risk-neutral & forward measure md
cells.append(
    md(r"""## 7. ニュメレールの選択（§28.4）

| ニュメレール $g$ | 測度 | 公式 |
|---|---|---|
| マネーマーケット口座 $e^{rt}$ | リスク中立 $\mathbb{Q}$ | $f_0 = \hat E[e^{-rT}f_T]$ |
| ゼロクーポン債 $P(t,T)$ | $T$-フォワード $\mathbb{Q}^T$ | $f_0 = P(0,T)E^T[f_T]$ |
| アニュイティ $A(t)$ | スワップ測度 | スワプション評価（→第11冊） |

**フォワード測度の効用**: $F(t,T) = E^T[S_T]$ — フォワード価格はフォワード測度下の
期待スポット。これが**確率的金利下でも Black-76 が成り立つ**理由です（第2冊の $q=r$ の正当化）。""")
)

# Cell 18: numeraire invariance demo
cells.append(
    code(r"""# --- ニュメレール不変性: 同じコールを2つの測度で独立評価 → MC 誤差内で一致 ---
S0_n, K_n, r_n, sig_n, T_n = 100.0, 100.0, 0.05, 0.25, 1.0
rng_n = np.random.default_rng(28)
n_paths = 400_000
# (a) リスク中立測度 Q（ニュメレール=マネーマーケット口座、ドリフト r）
z_q = rng_n.standard_normal(n_paths)
ST_q = S0_n * np.exp((r_n - 0.5 * sig_n**2) * T_n + sig_n * math.sqrt(T_n) * z_q)
price_q = math.exp(-r_n * T_n) * np.maximum(ST_q - K_n, 0.0).mean()
# (b) 株価ニュメレール（測度 S、ドリフト r+σ²）: c = S0 E^S[(S_T-K)^+ / S_T]
z_s = rng_n.standard_normal(n_paths)
ST_s = S0_n * np.exp((r_n + 0.5 * sig_n**2) * T_n + sig_n * math.sqrt(T_n) * z_s)
price_s = S0_n * (np.maximum(ST_s - K_n, 0.0) / ST_s).mean()
print(f"(a) リスク中立測度 Q の MC 価格 = {price_q:.4f}")
print(f"(b) 株価ニュメレールの MC 価格 = {price_s:.4f}（別測度・別サンプリング）")
print(f"BSM 解析値                     = {bsm.call_price(S0_n, K_n, r_n, sig_n, T_n):.4f}")
print("→ 異なる測度・異なるドリフトで独立にサンプリングしても同じ価格（測度変換の不変性）")""")
)

# Cell 19: Girsanov md + demo
cells.append(
    md(r"""## 8. ギルサノフの定理（§28.1）

測度変換は**ドリフトを変えるがボラティリティは保存**する：

$$dz^{\mathbb{Q}} = dz^{\mathbb{P}} + \lambda\,dt$$

実世界 $\mathbb{P}$（ドリフト $\mu$）からリスク中立 $\mathbb{Q}$（ドリフト $r$）へ移っても、
$\sigma$ は不変。これは第1冊で見た「二項ツリーで測度を変えても σ が変わらない」の
連続版です。下で同じ σ・異なるドリフトのパスを比較します。""")
)

# Cell 20: Girsanov path demo
cells.append(
    code(r"""rng_g = np.random.default_rng(280)
z_common = rng_g.standard_normal((30, 252))
t_g = np.linspace(0.0, 1.0, 253)
dt_g = 1.0 / 252
fig6, (ax6a, ax6b) = plt.subplots(1, 2, figsize=(10.5, 4), sharey=True)
fig6.canvas.header_visible = False
for ax, mu_g, title in ((ax6a, 0.12, "実世界 P（μ=12%）"),
                        (ax6b, 0.05, "リスク中立 Q（μ=r=5%）")):
    lp = np.cumsum((mu_g - 0.5 * 0.2**2) * dt_g + 0.2 * math.sqrt(dt_g) * z_common, axis=1)
    paths_g = 100.0 * np.exp(np.column_stack([np.zeros(30), lp]))
    ax.plot(t_g, paths_g.T, lw=0.6, alpha=0.6)
    ax.plot(t_g, 100.0 * np.exp(mu_g * t_g), "k--", lw=2)
    ax.set_title(title)
    ax.set_xlabel("t")
ax6a.set_ylabel("S")
fig6.suptitle("同じ乱数・同じ σ=20%、ドリフトだけ違う（ギルサノフ）", fontsize=10)
display(fig6.canvas)
print("拡散の広がり（σ）は両測度で同一。期待成長率（点線）だけが異なる")""")
)

# Cell 21: swap measure pointer md
cells.append(
    md(r"""### スワップ測度へのポインタ（§28.6）

アニュイティ $A(t) = \sum (T_{i+1}-T_i)P(t,T_{i+1})$ をニュメレールにすると、
フォワード・スワップレート $s(t)$ がマルチンゲールになる「スワップ測度」が得られ、
**スワプションの Black 公式**が正当化されます。これは第11冊（Ch.29）で本格的に使います。""")
)

# ===========================================================================
# Section 3: verification / exercises / summary
# ===========================================================================

# Cell 22: assertion cell
cells.append(
    code(r"""# --- 検証（hullkit/tests/test_exotics.py にも同等の検証あり） ---
checks = []
checks.append(("バイナリ分解 = バニラ", aon - K_B * con, van, 1e-12))
checks.append(("バリア in+out = バニラ", cdi + cdo, van, 1e-12))
checks.append(("Margrabe 7.9656",
               exotics.exchange_option(100.0, 100.0, 0.2, 0.2, 0.5, 1.0), 7.965567, 1e-5))
checks.append(("gap call 13.1122",
               exotics.gap_call(100.0, 95.0, 100.0, 0.05, 0.20, 1.0), 13.112208, 1e-5))
checks.append(("アジアン < バニラ", float(a_tw < van), 1.0, 0.0))
checks.append(("ルックバック > ATM", float(lb > van), 1.0, 0.0))
checks.append(("ニュメレール不変（a≈b）", price_q, price_s, 3e-2))
checks.append(("λ 一致（原資産 vs オプション）", lam_opt, lam_underlying, 1e-9))

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.6g} want={want:.6g}")
    assert ok, name
print("\n全チェック合格")""")
)

# Cell 23: exercises
cells.append(
    md(r"""## 9. 練習問題

**Q1.** ダウン・アンド・アウト・コール（H=80）の価格が 9、対応するバニラが 10。
ダウン・アンド・イン・コールの価格は？

<details><summary>解答</summary>

in + out = vanilla より、di = 10 − 9 = 1。
</details>

**Q2.** 平均価格アジアン・コールがバニラ・コールより安いのはなぜ？

<details><summary>解答</summary>

平均は経路を均すので実効ボラティリティが下がる（σ_avg < σ）。
オプション価値はボラに単調増加なので安くなる。
</details>

**Q3.** 交換オプション（Margrabe）が金利 r に依存しないのはなぜ？

<details><summary>解答</summary>

一方の資産をニュメレールに取ると、両資産の成長率上昇と割引率上昇が相殺する。
価格は相対ボラ σ̂=√(σ_U²+σ_V²−2ρσ_Uσ_V) だけで決まる。
</details>""")
)

# Cell 24: summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 |
|---|---|
| バイナリ | aon − K·con = バニラ。不連続ペイオフ |
| バリア | in + out = バニラ。ノックアウトは安い |
| ルックバック | 経路最小で買える「後知恵」プレミアム |
| アジアン | 平均でボラ低下 → 安い。TW近似 or MC |
| Margrabe | 交換オプション。r 非依存、σ̂ だけで決まる |
| 測度 | f/g がマルチンゲール。ニュメレールで測度を選ぶ |
| λ | (μ−r)/σ は全商品共通。Q は λ=0 の測度 |
| ギルサノフ | 測度変換でドリフト変、σ 不変 |

**次へ**: `volumes/11_ir_derivatives_market`（Ch.29, 30 — Black モデルとスワプション）
**シリーズ**: `johnhull/ROADMAP.md` 参照""")
)

# Cell 25: closing md
cells.append(
    md(r"""---
*第10冊おわり。エキゾチックの閉形式と、その正当性を支える測度論を一巡しました。*""")
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exotics.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
