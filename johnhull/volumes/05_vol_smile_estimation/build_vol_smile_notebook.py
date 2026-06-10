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

- **sticky strike** / **sticky delta**（Derman 1999 の用語; Hull は脚注で言及）: σ(K) ないし σ(マネーネス) を固定とみなす規約
- **minimum variance delta**: 株価と IV の負相関を織り込む修正
  $\Delta_{MV} = \Delta_{BSM} + \mathcal{V}\,\partial E[\sigma_{imp}]/\partial S < \Delta_{BSM}$
- スマイルの**モデル化**（局所ボラ・確率ボラ）は第6冊（Ch.27）で扱います""")
)

# Cell 11b: vanna across strikes demo
cells.append(
    code(r"""# --- vanna = ∂Δ/∂σ: スマイル下で株価とσが連動するとデルタが動く量 ---
ks_v = np.linspace(80.0, 120.0, 41)
vanna_v = [bsm.vanna(S0_S, k, R_S, 0.22, T_S) for k in ks_v]
fig_va, ax_va = plt.subplots(figsize=(7.5, 4))
fig_va.canvas.header_visible = False
ax_va.plot(ks_v / S0_S, vanna_v, lw=2)
ax_va.axhline(0.0, color="black", lw=0.8)
ax_va.axvline(1.0, color="0.7", ls=":", lw=1)
ax_va.set_xlabel("K / S0")
ax_va.set_ylabel("vanna = ∂Δ/∂σ")
ax_va.set_title("vanna: 株価上昇でσが下がる（株式スキュー）と Δ_MV < Δ_BSM になる源")
display(fig_va.canvas)
print(f"ATM vanna = {bsm.vanna(S0_S, S0_S, R_S, 0.22, T_S):.4f}（符号がΔ補正の向きを決める）")""")
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
# Section 2: Ch.23 estimating volatilities
# ===========================================================================

# Cell 13: EWMA md
cells.append(
    md(r"""## 6. ヒストリカル・ボラティリティと EWMA（Ch.23、eq 23.3, 23.7）

日次リターン $u_i = \ln(S_i/S_{i-1})$ から：

$$\sigma_n^2 = \frac{1}{m}\sum_{i=1}^{m} u_{n-i}^2 \;(\text{等加重}), \qquad
\sigma_n^2 = \lambda\sigma_{n-1}^2 + (1-\lambda)u_{n-1}^2 \;(\text{EWMA, 23.7})$$

EWMA（RiskMetrics は $\lambda=0.94$）は直近を重視し、保持するのは前日の分散と
直近リターンだけ。等加重の移動窓は「古い大変動が窓から抜ける日」に
不自然なジャンプを起こします。""")
)

# Cell 14: EWMA tracking
cells.append(
    code(r"""# --- ボラティリティ・レジームシフトの追跡: EWMA vs 移動窓 ---
rng5 = np.random.default_rng(50)
N_DAYS = 500
true_sig = np.where(np.arange(N_DAYS) < 250, 0.01, 0.02)  # 1%/日 → 2%/日
u_series = true_sig * rng5.standard_normal(N_DAYS)
ewma_v = volatility.ewma_variance(u_series, lam=0.94, init=0.0001)
roll_v = pd.Series(u_series**2).rolling(50).mean().to_numpy()

fig5, ax5 = plt.subplots(figsize=(8.5, 4.5))
fig5.canvas.header_visible = False
ax5.plot(np.sqrt(ewma_v) * 100, lw=1.5, label="EWMA（λ=0.94）")
ax5.plot(np.sqrt(roll_v) * 100, lw=1.5, label="移動窓 50日（等加重）")
ax5.plot(true_sig * 100, "k--", lw=1, label="真のσ")
ax5.set_xlabel("日")
ax5.set_ylabel("日次ボラティリティ (%)")
ax5.set_title("レジームシフトへの追従")
ax5.legend()
display(fig5.canvas)

var_upd = volatility.ewma_variance([0.02, 0.0], lam=0.90, init=0.0001)
print(f"Hull Example 23.1（λ=0.90）: σ=1%/日, u=2% → 分散 {var_upd[1]:.6f}"
      f" → σ = {np.sqrt(var_upd[1]):.4%}/日（Hull: 1.14%）")""")
)

# Cell 15: GARCH md
cells.append(
    md(r"""## 7. GARCH(1,1)（Ch.23、eq 23.8–23.9）

$$\sigma_n^2 = \omega + \alpha u_{n-1}^2 + \beta\sigma_{n-1}^2, \qquad
V_L = \frac{\omega}{1-\alpha-\beta}$$

EWMA に**長期平均分散 $V_L$ への平均回帰**を加えた形（EWMA は $\gamma=0$ の特殊ケース）。
定常条件は $\alpha + \beta < 1$。回帰速度は $1-\alpha-\beta$。""")
)

# Cell 16: GARCH filter
cells.append(
    code(r"""# Hull の例: ω=0.000002, α=0.13, β=0.86
OMEGA_H, ALPHA_H, BETA_H = 2e-6, 0.13, 0.86
v_l = volatility.garch11_long_run(OMEGA_H, ALPHA_H, BETA_H)
print(f"V_L = {v_l:.6f} → σ_L = {np.sqrt(v_l):.4%}/日（Hull: 1.4%）")
var_g = volatility.garch11_variance([-0.01, 0.0], OMEGA_H, ALPHA_H, BETA_H, init=0.016**2)
print(f"更新例: σ=1.6%/日, u=−1% → 分散 {var_g[1]:.8f} → σ = {np.sqrt(var_g[1]):.4%}/日（Hull: 1.53%）")

garch_v = volatility.garch11_variance(u_series, OMEGA_H, ALPHA_H, BETA_H)
fig6, ax6 = plt.subplots(figsize=(8.5, 4))
fig6.canvas.header_visible = False
ax6.plot(np.sqrt(garch_v) * 100, lw=1.5, label="GARCH(1,1) 条件付きσ")
ax6.plot(true_sig * 100, "k--", lw=1, label="真のσ")
ax6.axhline(np.sqrt(v_l) * 100, color="crimson", ls=":", lw=1.5, label="σ_L（長期水準）")
ax6.set_xlabel("日")
ax6.set_ylabel("日次ボラティリティ (%)")
ax6.set_title("GARCH(1,1) 条件付きボラティリティ")
ax6.legend()
display(fig6.canvas)""")
)

# Cell 17: MLE md
cells.append(
    md(r"""## 8. 最尤法によるパラメータ推定（Ch.23、eq 23.12）

$$\max_{\omega,\alpha,\beta} \sum_i \left[-\ln \sigma_i^2 - \frac{u_i^2}{\sigma_i^2}\right]$$

GARCH 漸化式で $\sigma_i^2$ を逐次計算しながら対数尤度を最大化します
（`hullkit.volatility.garch11_fit`、Nelder-Mead）。
実務では $V_L$ をサンプル分散に固定する**バリアンス・ターゲティング**も使われます。""")
)

# Cell 18: fit demo
cells.append(
    code(r"""# --- 合成 GARCH 系列でパラメータ復元 ---
rng6 = np.random.default_rng(0)
OMEGA_T, ALPHA_T, BETA_T = 2e-6, 0.10, 0.85
n_fit = 4000
u_fit = np.empty(n_fit)
var_t = OMEGA_T / (1.0 - ALPHA_T - BETA_T)
for i in range(n_fit):
    u_fit[i] = np.sqrt(var_t) * rng6.standard_normal()
    var_t = OMEGA_T + ALPHA_T * u_fit[i] ** 2 + BETA_T * var_t

omega_e, alpha_e, beta_e = volatility.garch11_fit(u_fit)
display(pd.DataFrame([
    {"パラメータ": "ω", "真値": OMEGA_T, "推定値": round(omega_e, 8)},
    {"パラメータ": "α", "真値": ALPHA_T, "推定値": round(alpha_e, 4)},
    {"パラメータ": "β", "真値": BETA_T, "推定値": round(beta_e, 4)},
    {"パラメータ": "α+β（持続性）", "真値": ALPHA_T + BETA_T, "推定値": round(alpha_e + beta_e, 4)},
]))
print(f"推定 V_L = {volatility.garch11_long_run(omega_e, alpha_e, beta_e):.6f}"
      f"（真値 {OMEGA_T / (1 - ALPHA_T - BETA_T):.6f}）")""")
)

# Cell 19: forecast md
cells.append(
    md(r"""## 9. ボラティリティ予測とタームストラクチャー（Ch.23、eq 23.13–23.14）

$$E[\sigma_{n+t}^2] = V_L + (\alpha+\beta)^t(\sigma_n^2 - V_L) \quad \text{(23.13)}$$

現在の分散は $(\alpha+\beta)^t$ の速度で $V_L$ へ回帰。年率換算のタームストラクチャーは

$$\sigma(T)^2 = 252\left(V_L + \frac{1-e^{-aT}}{aT}\left[V(0) - V_L\right]\right), \quad a = \ln\frac{1}{\alpha+\beta} \quad \text{(23.14)}$$""")
)

# Cell 20: forecast chart
cells.append(
    code(r"""# 現在 σ=1.6%/日（> σ_L=1.41%）からの予測パス
sigma2_now = 0.016**2
days_fwd = np.arange(0, 252)
fcst = [volatility.garch11_forecast(sigma2_now, int(k), OMEGA_H, ALPHA_H, BETA_H)
        for k in days_fwd]

a_ts = np.log(1.0 / (ALPHA_H + BETA_H))
t_years = np.linspace(0.05, 2.0, 60)
term = np.sqrt(252.0 * (v_l + (1 - np.exp(-a_ts * 252.0 * t_years))
                        / (a_ts * 252.0 * t_years) * (sigma2_now - v_l)))

fig7, (ax7a, ax7b) = plt.subplots(1, 2, figsize=(10.5, 4))
fig7.canvas.header_visible = False
ax7a.plot(days_fwd, np.sqrt(fcst) * 100, lw=2)
ax7a.axhline(np.sqrt(v_l) * 100, color="crimson", ls=":", label="σ_L")
ax7a.set_xlabel("先日数 t")
ax7a.set_ylabel("E[σ] (%/日)")
ax7a.set_title("日次ボラの平均回帰（eq 23.13）")
ax7a.legend()
ax7b.plot(t_years, term * 100, lw=2)
ax7b.set_xlabel("満期 T（年）")
ax7b.set_ylabel("年率ボラ (%)")
ax7b.set_title("ボラのタームストラクチャー（eq 23.14）")
display(fig7.canvas)
print(f"10日先: E[σ²] = {volatility.garch11_forecast(sigma2_now, 10, OMEGA_H, ALPHA_H, BETA_H):.6e}")""")
)

# Cell 21: correlation md
cells.append(
    md(r"""## 10. 相関の推定（Ch.23）

共分散も同じ EWMA 更新で追跡できます：
$\mathrm{cov}_n = \lambda\,\mathrm{cov}_{n-1} + (1-\lambda)x_{n-1}y_{n-1}$、
$\rho_n = \mathrm{cov}_n/(\sigma_{x,n}\sigma_{y,n})$。

分散共分散行列は**正半定値**が必要（分散と共分散は同じ重みで計算）。
相関付き乱数の生成には **Cholesky 分解** $\Sigma = LL^\top$、$X = LZ$ を使います。""")
)

# Cell 22: EWMA correlation demo
cells.append(
    code(r"""# --- ρ=0.6 の相関付きリターンを Cholesky 生成 → EWMA 相関で追跡 ---
rng7 = np.random.default_rng(70)
RHO_T = 0.6
chol = np.linalg.cholesky(np.array([[1.0, RHO_T], [RHO_T, 1.0]]))
z_pair = rng7.standard_normal((2, N_DAYS))
x_r, y_r = 0.01 * (chol @ z_pair)

lam_c = 0.94
var_x = volatility.ewma_variance(x_r, lam=lam_c)
var_y = volatility.ewma_variance(y_r, lam=lam_c)
cov_xy = volatility.ewma_covariance(x_r, y_r, lam=lam_c)
rho_t = cov_xy / np.sqrt(var_x * var_y)

fig8, ax8 = plt.subplots(figsize=(8.5, 4))
fig8.canvas.header_visible = False
ax8.plot(rho_t, lw=1.5, label="EWMA 相関")
ax8.axhline(RHO_T, color="crimson", ls="--", lw=1.5, label=f"真の ρ = {RHO_T}")
ax8.set_xlabel("日")
ax8.set_ylabel("ρ")
ax8.set_ylim(-1.05, 1.05)
ax8.set_title("EWMA 相関の推定")
ax8.legend()
display(fig8.canvas)
print(f"後半250日の平均推定 ρ = {rho_t[250:].mean():.3f}")""")
)

# Cell 23: interactive lambda
cells.append(
    code(r"""# --- λ の感度（インタラクティブ）: 反応速度 vs 平滑性 ---
fig9, ax9 = plt.subplots(figsize=(8.5, 4))
fig9.canvas.header_visible = False
lam_sl = widgets.FloatSlider(value=0.94, min=0.86, max=0.99, step=0.01, description="λ")


def _upd_lambda(change=None):
    ax9.clear()
    ev = volatility.ewma_variance(u_series, lam=lam_sl.value)
    ax9.plot(np.sqrt(ev) * 100, lw=1.5, label=f"EWMA（λ={lam_sl.value:.2f}）")
    ax9.plot(true_sig * 100, "k--", lw=1, label="真のσ")
    ax9.set_xlabel("日")
    ax9.set_ylabel("日次ボラ (%)")
    ax9.set_title("λ 小 → 機敏でノイジー ／ λ 大 → 滑らかで遅い")
    ax9.legend()
    fig9.canvas.draw_idle()


lam_sl.observe(_upd_lambda, "value")
_upd_lambda()
display(lam_sl, fig9.canvas)""")
)

# ===========================================================================
# Section 3: verification / exercises / summary
# ===========================================================================

# Cell 24: assertion cell
cells.append(
    code(r"""# --- 教科書例題との突合せ（hullkit/tests/test_volatility.py にも同等の検証あり） ---
checks = []
sigma_rt = 0.27
c_rt = bsm.call_price(100.0, 105.0, 0.04, sigma_rt, 0.75, q=0.01)
iv_rt = volatility.implied_vol(c_rt, 100.0, 105.0, 0.04, 0.75, q=0.01, kind="call")
checks.append(("IV ラウンドトリップ", iv_rt, sigma_rt, 1e-6))
p_rt = bsm.put_price(100.0, 105.0, 0.04, sigma_rt, 0.75, q=0.01)
iv_rt_p = volatility.implied_vol(p_rt, 100.0, 105.0, 0.04, 0.75, q=0.01, kind="put")
checks.append(("コール/プット IV 一致", iv_rt_p, iv_rt, 1e-6))

ew = volatility.ewma_variance([0.02, 0.0], lam=0.90, init=0.0001)
checks.append(("EWMA 更新例 0.00013（Hull Ex 23.1）", float(ew[1]), 0.00013, 1e-12))
gv = volatility.garch11_variance([0.01, 0.0], 2e-6, 0.13, 0.86, init=0.016**2)
checks.append(("GARCH 更新例 0.00023516", float(gv[1]), 0.00023516, 1e-10))
checks.append(("V_L = 0.0002", volatility.garch11_long_run(2e-6, 0.13, 0.86), 0.0002, 1e-12))
checks.append(("10日予測 2.50645e-4",
               volatility.garch11_forecast(0.016**2, 10, 2e-6, 0.13, 0.86), 2.50645e-4, 2e-8))
checks.append(("BL フラットσ ≈ 対数正規（相対誤差<1%）", bl_err, 0.0, 0.01))
checks.append(("GARCH fit 持続性", alpha_e + beta_e, ALPHA_T + BETA_T, 0.05))

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.6g} want={want:.6g}")
    assert ok, name
print("\n全チェック合格")""")
)

# Cell 25: exercises
cells.append(
    md(r"""## 11. 練習問題

**Q1.** 同一 (K, T) のコール IV が 25%、プット IV が 27% と観測された。何が起きている？

<details><summary>解答</summary>

パリティ違反＝裁定機会（または価格の同時性・流動性の問題）。
理論上は eq (20.2) により両者の IV は一致しなければならない。
</details>

**Q2.** λ=0.94 の EWMA で、σ=1.5%/日 のとき u=−3% が観測された。新しい σ は？

<details><summary>解答</summary>

σ² = 0.94×0.000225 + 0.06×0.0009 = 0.0002655 → σ = 1.629%/日。
</details>

**Q3.** GARCH で α+β=0.99、現在 σ が σ_L の2倍。約何日で乖離が半減する？

<details><summary>解答</summary>

分散の乖離は (0.99)^t 倍。0.99^t = 0.5 → t = ln0.5/ln0.99 ≈ 69日。
（ボラ自体なら分散ベースで考える点に注意）
</details>""")
)

# Cell 26: summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 |
|---|---|
| IV | パリティにより同一 (K,T) のコール/プットで一致。スマイルは1本 |
| スキュー/スマイル | 株式=左裾の恐怖（スマーク）、FX=両裾（U字） |
| BL 密度 | g(K)=e^{rT}∂²c/∂K²。スマイル ⇔ 非対数正規分布 |
| EWMA | λ=0.94。前日分散＋直近リターンだけで更新 |
| GARCH(1,1) | EWMA＋V_L への平均回帰。α+β が持続性 |
| 予測 | (α+β)^t で V_L へ回帰 → タームストラクチャー |

**次へ**: `volumes/06_numerical_methods`（Ch.21, 27 — スマイルを生むモデルの数値解法）
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vol_smile.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
