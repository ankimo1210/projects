"""
build_numerical_notebook.py
================================
nbformat-dict pattern to generate numerical.ipynb (Hull 11e Ch.21, 27).

Usage:
    uv run python build_numerical_notebook.py
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
    md(r"""# 数値解法編（Hull 11e Ch.21, 27）

`johnhull/volumes` シリーズ第6冊。解析解がない商品を解く3大手法と発展モデル：

- **ツリーの拡張** — コントロール変量、三項ツリー（Ch.21）
- **モンテカルロ** — 標準誤差、分散削減（Ch.21）
- **有限差分法** — implicit / Crank-Nicolson、早期行使境界（Ch.21）
- **発展モデルと LSM** — Merton ジャンプ拡散が作るスマイル、Longstaff-Schwartz（Ch.27）

> 通し例: アメリカンプット S=50, K=50, r=10%, σ=40%, T=5/12（Hull Ch.21 のパラメータ）
> CRR（第1冊）・BSM・FD・MC の**相互整合**がこの冊の検証軸""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import math

import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display

from hullkit import bsm, fd, mc, nbplot, trees, volatility

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()

S_A, K_A, R_A, SIG_A, T_A = 50.0, 50.0, 0.10, 0.40, 5.0 / 12.0  # 通し例""")
)

# ===========================================================================
# Section 1: Ch.21 tree extensions
# ===========================================================================

# Cell 03: control variate md
cells.append(
    md(r"""## 1. ツリーの拡張とコントロール変量（Ch.21）

- 連続利回り $q$ は成長因子 $a = e^{(r-q)\Delta t}$（eq 21.4–21.7）、時変 $r(t), q(t)$ は $a = e^{[f(t)-g(t)]\Delta t}$（eq 21.11）で対応
  （第1冊・第2冊で実装済み）
- **コントロール変量**: 同じツリーで欧州版も価格付けし、既知の BSM 解析値との誤差で補正

$$f^* = f_{\text{Am,tree}} + \left(f_{\text{Eu,BSM}} - f_{\text{Eu,tree}}\right)$$

ツリーの離散化誤差が Am/Eu 双方にほぼ同じ量だけ乗る、という観察を利用します。""")
)

# Cell 04: control variate demo
cells.append(
    code(r"""# --- コントロール変量: 少ないステップ数でも高精度 ---
ref_put = trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, 2000, kind="put", american=True)
eu_bsm = bsm.put_price(S_A, K_A, R_A, SIG_A, T_A)
rows = []
for n in (25, 51, 101, 201):
    am = trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, n, kind="put", american=True)
    eu_tree = trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, n, kind="put")
    cv = am + (eu_bsm - eu_tree)
    rows.append({"N": n, "plain": round(am, 4), "CV補正": round(cv, 4),
                 "|誤差| plain": round(abs(am - ref_put), 4),
                 "|誤差| CV": round(abs(cv - ref_put), 4)})
df_cv = pd.DataFrame(rows)
display(df_cv)
print(f"参照値（CRR N=2000）= {ref_put:.4f} ／ 欧州BSM = {eu_bsm:.4f}")
print("※ CV の利得は粗い N で劇的（N=25 で約10倍）。N が増えると plain 自身が収束して差は消える")""")
)

# Cell 05: trinomial md
cells.append(
    md(r"""## 2. 三項ツリー（Ch.21）

各ノードから上・中・下の3方向へ。$u = e^{\sigma\sqrt{3\Delta t}}$、

$$p_u = \sqrt{\frac{\Delta t}{12\sigma^2}}\left(r - q - \frac{\sigma^2}{2}\right) + \frac{1}{6}, \quad
p_m = \frac{2}{3}, \quad p_d = 1 - p_u - p_m$$

自由度が増えるぶん収束が滑らかで、**陽的有限差分法と等価**（後述）。
$\Delta t$ が大きすぎると $p_u, p_d$ が負になり得る点に注意。""")
)

# Cell 06: trinomial inline pricer
cells.append(
    code(r"""def trinomial_price(S0, K, r, sigma, T, n, q=0.0, kind="put", american=False):
    dt = T / n
    u = np.exp(sigma * np.sqrt(3.0 * dt))
    drift = r - q - 0.5 * sigma**2
    pu = np.sqrt(dt / (12.0 * sigma**2)) * drift + 1.0 / 6.0
    pd_ = -np.sqrt(dt / (12.0 * sigma**2)) * drift + 1.0 / 6.0
    pm = 2.0 / 3.0
    disc = np.exp(-r * dt)
    j = np.arange(-n, n + 1, dtype=float)
    s = S0 * u**j

    def payoff(x):
        return np.maximum(x - K, 0.0) if kind == "call" else np.maximum(K - x, 0.0)

    v = payoff(s)
    for _ in range(n):
        v = disc * (pu * v[2:] + pm * v[1:-1] + pd_ * v[:-2])
        s = s[1:-1]
        if american:
            v = np.maximum(v, payoff(s))
    return float(v[0])


tri_am = trinomial_price(S_A, K_A, R_A, SIG_A, T_A, 200, american=True)
crr_am = trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, 200, kind="put", american=True)
print(f"三項（N=200）= {tri_am:.4f} ／ CRR（N=200）= {crr_am:.4f} ／ 参照 {ref_put:.4f}")""")
)

# ===========================================================================
# Section 2: Ch.21 Monte Carlo
# ===========================================================================

# Cell 07: MC md
cells.append(
    md(r"""## 3. モンテカルロ法（Ch.21、eq 21.16）

リスク中立世界でパスを生成し、割引期待ペイオフを平均：

$$S_T = S_0\exp\left[\left(r - q - \frac{\sigma^2}{2}\right)T + \sigma\epsilon\sqrt{T}\right], \qquad
\hat f = e^{-rT}\frac{1}{N}\sum f_T^{(i)}, \quad \text{SE} = \frac{s}{\sqrt{N}}$$

強み: パス依存・多資産。弱み: 収束が $1/\sqrt{N}$、アメリカンは工夫（LSM、後述）が必要。""")
)

# Cell 08: MC demo
cells.append(
    code(r"""price_mc, se_mc = mc.price_european_mc(100.0, 100.0, 0.05, 0.2, 1.0, n_paths=200_000)
target_bsm = bsm.call_price(100.0, 100.0, 0.05, 0.2, 1.0)
print(f"MC = {price_mc:.4f} ± {1.96 * se_mc:.4f}（95%CI） ／ BSM = {target_bsm:.4f}")
print(f"|誤差| = {abs(price_mc - target_bsm):.4f}（{abs(price_mc - target_bsm) / se_mc:.2f} SE）")""")
)

# Cell 09: variance reduction md
cells.append(
    md(r"""## 4. 分散削減（Ch.21）

- **対称変量**: $\epsilon$ と $-\epsilon$ をペアにし、ペア平均の分散で評価
- **コントロール変量**: 解析解既知の類似商品 B で $f_A = f_A^* - f_B^* + f_B$
- **重点サンプリング** / **層化** / **準乱数列**（Sobol 等、誤差 $O(1/N)$ 近く）

Greeks の MC 計算はバンプ&再評価（共通乱数）か pathwise 微分（第3冊の Δ なら
$e^{-rT}\mathbf{1}_{S_T>K}\,S_T/S_0$）で行います — 詳細は省略。""")
)

# Cell 10: antithetic chart
cells.append(
    code(r"""# --- 対称変量の効果: SE vs パス数 ---
ns_mc = [1_000, 4_000, 16_000, 64_000, 256_000]
se_plain, se_anti = [], []
for i, n in enumerate(ns_mc):
    _, sp = mc.price_european_mc(100.0, 100.0, 0.05, 0.2, 1.0, n_paths=n,
                                 rng=np.random.default_rng(100 + i))
    _, sa = mc.price_european_mc(100.0, 100.0, 0.05, 0.2, 1.0, n_paths=n,
                                 antithetic=True, rng=np.random.default_rng(100 + i))
    se_plain.append(sp)
    se_anti.append(sa)

fig1, ax1 = plt.subplots(figsize=(7.5, 4))
fig1.canvas.header_visible = False
ax1.loglog(ns_mc, se_plain, "o-", label="プレーン")
ax1.loglog(ns_mc, se_anti, "s-", label="対称変量")
ax1.set_xlabel("パス数 N")
ax1.set_ylabel("標準誤差")
ax1.set_title("どちらも 1/√N で減少、対称変量は定数倍の改善")
ax1.legend()
display(fig1.canvas)""")
)

# Cell 11: MC misc md
cells.append(
    md(r"""### MC が得意な商品・苦手な商品

| 得意 | 苦手 |
|---|---|
| パス依存（アジアン・ルックバック） | 早期行使（→ LSM で対応、§8） |
| 多資産バスケット（次元の呪いに強い） | 高精度が必要な Greeks |
| 複雑なペイオフの追加が容易 | 収束 1/√N の遅さ |

ツリー・FD は低次元・早期行使に強く、MC と相補的です。""")
)

# ===========================================================================
# Section 3: Ch.21 finite differences
# ===========================================================================

# Cell 12: FD md
cells.append(
    md(r"""## 5. 有限差分法（Ch.21）

BSM PDE を $(S, t)$（ここでは $x=\ln S$）のグリッド上の差分方程式に変換して
満期から後ろ向きに解きます：

- **陽的（explicit）**: 三項ツリーと等価。条件付き安定
- **陰的（implicit）**: 三重対角連立を各ステップで解く。無条件安定・1次精度
- **Crank-Nicolson**: 両者の平均。無条件安定・**2次精度**

`hullkit.fd.fd_vanilla` は $\ln S$ 等間隔グリッド＋θスキームの実装です。""")
)

# Cell 13: European convergence
cells.append(
    code(r"""# --- 欧州コール: グリッド細分化での収束（CN vs implicit） ---
target_c = bsm.call_price(100.0, 100.0, 0.05, 0.25, 1.0)
grids = [(50, 50), (100, 100), (200, 200), (400, 400)]
err_cn, err_im = [], []
for n_s, n_t in grids:
    err_cn.append(abs(fd.fd_vanilla(100.0, 100.0, 0.05, 0.25, 1.0,
                                    method="cn", n_s=n_s, n_t=n_t) - target_c))
    err_im.append(abs(fd.fd_vanilla(100.0, 100.0, 0.05, 0.25, 1.0,
                                    method="implicit", n_s=n_s, n_t=n_t) - target_c))
labels = [f"{a}×{b}" for a, b in grids]
fig2, ax2 = plt.subplots(figsize=(7.5, 4))
fig2.canvas.header_visible = False
ax2.semilogy(labels, err_cn, "o-", label="Crank-Nicolson")
ax2.semilogy(labels, err_im, "s-", label="implicit")
ax2.set_xlabel("グリッド（空間×時間）")
ax2.set_ylabel("|誤差| vs BSM")
ax2.set_title("CN は2次精度で速く収束")
ax2.legend()
display(fig2.canvas)""")
)

# Cell 14: American FD md
cells.append(
    md(r"""## 6. アメリカンオプションと早期行使境界（Ch.21）

FD では各時間ステップの後に $f \leftarrow \max(f, \text{本質的価値})$ と射影するだけで
アメリカンに対応できます。さらに「$f = $ 本質的価値」となる領域の端を読み取れば、
**早期行使境界 $S^*(\tau)$** がグリッドから直接得られます
（プット: $S < S^*$ で行使。満期に近づくと $S^* \to K$）。""")
)

# Cell 15: American FD + boundary
cells.append(
    code(r"""price_fd, taus_b, bound_s = fd.fd_vanilla(
    S_A, K_A, R_A, SIG_A, T_A, kind="put", american=True, method="cn",
    n_s=300, n_t=300, return_boundary=True,
)
print(f"アメリカンプット: FD(CN) = {price_fd:.4f} ／ CRR(N=500) = "
      f"{trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, 500, kind='put', american=True):.4f}")

fig3, ax3 = plt.subplots(figsize=(7.5, 4))
fig3.canvas.header_visible = False
ax3.plot(taus_b, bound_s, lw=2)
ax3.axhline(K_A, color="0.6", ls=":", lw=1, label="K")
ax3.set_xlabel("残存期間 τ（年）")
ax3.set_ylabel("早期行使境界 S*(τ)")
ax3.set_title("τ→0 で S*→K（満期直前はわずかな ITM でも行使）")
ax3.invert_xaxis()
ax3.legend()
display(fig3.canvas)""")
)

# Cell 16: FD Greeks demo
cells.append(
    code(
        "# --- FD はグリッドから Greeks も同時に得られる（バンプ不要） ---\n"
        "price_g, delta_g, gamma_g = fd.fd_vanilla(S_A, K_A, R_A, SIG_A, T_A, kind='put',\n"
        "                                          american=True, method='cn', n_s=300, n_t=300,\n"
        "                                          return_greeks=True)\n"
        'print(f"アメリカンプット: 価格 {price_g:.4f}, Δ {delta_g:.4f}, Γ {gamma_g:.5f}")\n'
        'print("（FD は満期から後退で解いた格子に Δ・Γ がそのまま埋まっている — 再評価バンプ不要）")'
    )
)

# Cell 17: interactive boundary explorer
cells.append(
    code(r"""# --- 早期行使境界の感応度（インタラクティブ） ---
fig4, ax4 = plt.subplots(figsize=(7.5, 4))
fig4.canvas.header_visible = False
sig_b_sl = widgets.FloatSlider(value=0.40, min=0.15, max=0.60, step=0.05, description="σ")
r_b_sl = widgets.FloatSlider(value=0.10, min=0.01, max=0.15, step=0.01, description="r")


def _upd_bound(change=None):
    ax4.clear()
    _, tb, bb = fd.fd_vanilla(S_A, K_A, r_b_sl.value, sig_b_sl.value, T_A,
                              kind="put", american=True, method="cn",
                              n_s=160, n_t=120, return_boundary=True)
    ax4.plot(tb, bb, lw=2)
    ax4.axhline(K_A, color="0.6", ls=":", lw=1)
    ax4.set_xlabel("残存期間 τ（年）")
    ax4.set_ylabel("S*(τ)")
    ax4.set_title(f"σ={sig_b_sl.value:.2f}, r={r_b_sl.value:.2f}: "
                  "σ↑で境界は下がり（待つ価値↑）、r↑で上がる（早期行使の金利メリット↑）")
    ax4.invert_xaxis()
    fig4.canvas.draw_idle()


sig_b_sl.observe(_upd_bound, "value")
r_b_sl.observe(_upd_bound, "value")
_upd_bound()
display(widgets.HBox([sig_b_sl, r_b_sl]), fig4.canvas)""")
)

# Cell 17: method comparison md
cells.append(
    md(r"""### 三項ツリー ＝ 陽的 FD

三項ツリーの後退帰納は、陽的有限差分の更新式そのもの（係数が $p_u, p_m, p_d$）。
ツリー＝「PDE を特定の差分で解いている」という統一的な見方ができます。
implicit / CN はこの構造を「連立を解く」ことで無条件安定にしたもの。""")
)

# ===========================================================================
# Section 4: Ch.27 alternative models & LSM
# ===========================================================================

# Cell 18: models map md
cells.append(
    md(r"""## 7. BSM を超えるモデルたち（Ch.27）

| モデル | アイデア | スマイルへの効き方 |
|---|---|---|
| CEV | σ ∝ S^{β−1} | β<1 で株式型スキュー |
| **Merton ジャンプ拡散** | 拡散＋ポアソンジャンプ | 裾を厚くする（短期で強い） |
| 分散ガンマ | ガンマ時間変換の純ジャンプ | 裾と歪みを独立に制御 |
| Heston | 分散が CIR 過程 | ρ<0 で株式型スキュー |
| SABR | フォワードとσの連立 SDE | 近似式でスマイルを直接表現 |
| 局所ボラ (IVF/Dupire) | σ(S,t) を市場に完全整合 | バニラは完全再現（エキゾチックは注意） |

このうち Merton は **BSM の重み付き級数**で書けるので、ここで実装して
「ジャンプ → スマイル」を直接見ます。""")
)

# Cell 19: Merton series + smile
cells.append(
    code(r"""def merton_jump_call(S, K, r, sigma, T, lam, gamma_j, delta_j, q=0.0, n_terms=40):
    # Merton ジャンプ拡散のヨーロピアンコール（BSM 級数、Hull Ch.27）
    k_j = np.exp(gamma_j + 0.5 * delta_j**2) - 1.0
    lam_p = lam * (1.0 + k_j)
    total = 0.0
    for n in range(n_terms):
        sigma_n = np.sqrt(sigma**2 + n * delta_j**2 / T)
        r_n = r - lam * k_j + n * (gamma_j + 0.5 * delta_j**2) / T
        w = np.exp(-lam_p * T) * (lam_p * T) ** n / math.factorial(n)
        total += w * bsm.call_price(S, K, r_n, sigma_n, T, q)
    return total


# ジャンプが作るスマイル: Merton 価格 → BSM の IV を逆算
S_J, R_J, T_J = 100.0, 0.05, 0.25
LAM_J, GAM_J, DEL_J, SIG_J = 1.0, -0.10, 0.15, 0.20
ks_j = np.linspace(75.0, 125.0, 26)
ivs_j = []
for k in ks_j:
    c_j = merton_jump_call(S_J, k, R_J, SIG_J, T_J, LAM_J, GAM_J, DEL_J)
    ivs_j.append(volatility.implied_vol(c_j, S_J, k, R_J, T_J, kind="call"))

fig5, ax5 = plt.subplots(figsize=(7.5, 4))
fig5.canvas.header_visible = False
ax5.plot(ks_j / S_J, np.array(ivs_j) * 100, "o-", lw=1.5,
         label=f"Merton（λ={LAM_J}, γ={GAM_J}, δ={DEL_J}）")
ax5.axhline(SIG_J * 100, color="0.6", ls=":", lw=1.5, label="拡散部分 σ=20%")
ax5.set_xlabel("K / S0")
ax5.set_ylabel("インプライド・ボラティリティ (%)")
ax5.set_title("下向きジャンプ（γ<0）が株式型スキューを生む")
ax5.legend()
display(fig5.canvas)""")
)

# Cell 20: jump interpretation md
cells.append(
    md(r"""### ジャンプとスマイルの関係

- $\gamma < 0$（下向きジャンプ）→ 左裾が厚い → **株式型スキュー**（第5冊のスマイル再現）
- $\gamma = 0$ で対称ジャンプ → 両裾 → FX 型 U 字
- ジャンプの影響は **短満期で強烈**（拡散は √T、ジャンプ確率は T に比例）—
  実市場で短期スキューが急な理由の一つ""")
)

# Cell 21: jump path simulation
cells.append(
    code(r"""# --- ジャンプ付きパスと収益率分布 ---
rng_j = np.random.default_rng(60)
n_steps_j, n_paths_j = 252, 2000
dt_j = 1.0 / 252.0
k_jump = np.exp(GAM_J + 0.5 * DEL_J**2) - 1.0
log_paths = np.zeros((n_paths_j, n_steps_j + 1)) + np.log(S_J)
for i in range(n_steps_j):
    z = rng_j.standard_normal(n_paths_j)
    n_jumps = rng_j.poisson(LAM_J * dt_j, n_paths_j)
    jump_sizes = GAM_J * n_jumps + DEL_J * np.sqrt(n_jumps) * rng_j.standard_normal(n_paths_j)
    log_paths[:, i + 1] = (log_paths[:, i]
                           + (R_J - LAM_J * k_jump - 0.5 * SIG_J**2) * dt_j
                           + SIG_J * np.sqrt(dt_j) * z + jump_sizes)
paths_j = np.exp(log_paths)

fig6, (ax6a, ax6b) = plt.subplots(1, 2, figsize=(10.5, 4))
fig6.canvas.header_visible = False
t_j = np.linspace(0.0, 1.0, n_steps_j + 1)
ax6a.plot(t_j, paths_j[:30].T, lw=0.6, alpha=0.6)
ax6a.set_xlabel("t（年）")
ax6a.set_ylabel("S")
ax6a.set_title("ジャンプ拡散のパス（飛びが見える）")
rets = np.diff(log_paths[:, :22], axis=1).ravel()
ax6b.hist(rets, bins=80, density=True, alpha=0.7)
grid_r = np.linspace(rets.min(), rets.max(), 200)
ax6b.plot(grid_r, np.exp(-grid_r**2 / (2 * SIG_J**2 * dt_j)) / np.sqrt(2 * np.pi * SIG_J**2 * dt_j),
          "r--", lw=1.5, label="正規（拡散のみ）")
ax6b.set_title("日次対数収益: 裾が正規より厚い")
ax6b.legend()
display(fig6.canvas)""")
)

# Cell 22: LSM md
cells.append(
    md(r"""## 8. Longstaff-Schwartz（LSM）— MC でアメリカン（Ch.27）

後ろ向きに各行使時点で:
1. ITM パスについて「継続価値」を**将来キャッシュフローの回帰**（基底: $1, S, S^2$）で推定
2. 即時行使価値 > 推定継続価値 のパスはそこで行使
3. 全パスの割引キャッシュフローを平均

回帰がツリーの後退帰納を代替するため、パス依存・多資産でも早期行使を扱えます。""")
)

# Cell 23: three-method comparison
cells.append(
    code(r"""# --- 同一オプションを3手法で: CRR / FD / LSM ---
import time

t0 = time.perf_counter()
v_crr = trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, 500, kind="put", american=True)
t_crr = time.perf_counter() - t0
t0 = time.perf_counter()
v_fd = fd.fd_vanilla(S_A, K_A, R_A, SIG_A, T_A, kind="put", american=True, method="cn",
                     n_s=300, n_t=300)
t_fd = time.perf_counter() - t0
t0 = time.perf_counter()
v_lsm = mc.price_american_lsm(S_A, K_A, R_A, SIG_A, T_A, kind="put",
                              n_steps=50, n_paths=100_000)
t_lsm = time.perf_counter() - t0
display(pd.DataFrame([
    {"手法": "CRR ツリー (N=500)", "価格": round(v_crr, 4), "計算時間(s)": round(t_crr, 3)},
    {"手法": "FD Crank-Nicolson (300×300)", "価格": round(v_fd, 4), "計算時間(s)": round(t_fd, 3)},
    {"手法": "LSM (50×100k)", "価格": round(v_lsm, 4), "計算時間(s)": round(t_lsm, 3)},
]))
print(f"欧州BSM = {eu_bsm:.4f}（早期行使プレミアム ≈ {v_crr - eu_bsm:.4f}）")""")
)

# Cell 24: pointers md
cells.append(
    md(r"""### その他のトピック（ポインタ）

- **転換社債**: ハザードレート入りツリーで、各ノードで転換/コール/継続を判定
- **バリアオプション**: ツリーのノードをバリア上に置く／**適応的メッシュ**で収束改善
- **パス依存 × 早期行使**: ツリーで代表値＋補間（ルックバック等）
- CEV の閉形式（非心 χ²）、Heston / SABR の半解析解は本シリーズではポインタのみ""")
)

# Cell 25: capstone convergence chart
cells.append(
    code(r"""# --- まとめ: 3手法の誤差 vs 計算量（アメリカンプット、参照=CRR N=4000） ---
ref_fine = trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, 4000, kind="put", american=True)
crr_ns = [25, 50, 100, 200, 400, 800]
crr_err = [abs(trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, n, kind="put", american=True)
               - ref_fine) for n in crr_ns]
fd_ns = [(40, 40), (80, 80), (160, 160), (320, 320)]
fd_err = [abs(fd.fd_vanilla(S_A, K_A, R_A, SIG_A, T_A, kind="put", american=True,
                            method="cn", n_s=a, n_t=b) - ref_fine) for a, b in fd_ns]
lsm_ns = [5_000, 20_000, 80_000]
lsm_err = [abs(mc.price_american_lsm(S_A, K_A, R_A, SIG_A, T_A, kind="put", n_steps=50,
                                     n_paths=n, rng=np.random.default_rng(7)) - ref_fine)
           for n in lsm_ns]

fig7, ax7 = plt.subplots(figsize=(8, 4.5))
fig7.canvas.header_visible = False
ax7.loglog(crr_ns, crr_err, "o-", label="CRR（ステップ数）")
ax7.loglog([a for a, _ in fd_ns], fd_err, "s-", label="FD CN（グリッド辺）")
ax7.loglog(lsm_ns, lsm_err, "^-", label="LSM（パス数）")
ax7.set_xlabel("計算量パラメータ（対数）")
ax7.set_ylabel("|誤差| vs CRR N=4000")
ax7.set_title("手法ごとの収束プロファイル")
ax7.legend()
ax7.text(0.02, 0.04, "注: LSM はパス数で誤差が減るが分散が大きい／CRR は参照と同族でやや有利",
         transform=ax7.transAxes, fontsize=8, color="0.4")
display(fig7.canvas)""")
)

# ===========================================================================
# Section 5: verification / exercises / summary
# ===========================================================================

# Cell 26: assertion cell
cells.append(
    code(r"""# --- 相互整合チェック（hullkit/tests にも同等の検証あり） ---
checks = []
checks.append(("FD CN 欧州 ≈ BSM", fd.fd_vanilla(100.0, 100.0, 0.05, 0.25, 1.0, method="cn"),
               bsm.call_price(100.0, 100.0, 0.05, 0.25, 1.0), 2e-2))
v_crr500 = trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, 500, kind="put", american=True)
checks.append(("FD アメリカン ≈ CRR500", v_fd, v_crr500, 2e-2))
checks.append(("LSM ≈ CRR500", v_lsm, v_crr500, 5e-2))
checks.append(("三項 ≈ CRR（N=200）", tri_am, crr_am, 5e-2))

cv_25 = (trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, 25, kind="put", american=True)
         + eu_bsm - trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, 25, kind="put"))
plain_25 = trees.crr_price(S_A, K_A, R_A, SIG_A, T_A, 25, kind="put", american=True)
assert abs(cv_25 - ref_put) < abs(plain_25 - ref_put), "CV が plain を改善していない"
print(f"[OK] CV(N=25) 誤差 {abs(cv_25 - ref_put):.5f} < plain 誤差 {abs(plain_25 - ref_put):.5f}")

p_mc, se_chk = mc.price_european_mc(100.0, 100.0, 0.05, 0.2, 1.0, n_paths=200_000)
assert abs(p_mc - bsm.call_price(100.0, 100.0, 0.05, 0.2, 1.0)) < 3.0 * se_chk
print(f"[OK] MC 3SE 以内（{abs(p_mc - bsm.call_price(100.0, 100.0, 0.05, 0.2, 1.0)) / se_chk:.2f} SE）")
_, se_p = mc.price_european_mc(100.0, 100.0, 0.05, 0.2, 1.0, n_paths=100_000,
                               rng=np.random.default_rng(1))
_, se_a = mc.price_european_mc(100.0, 100.0, 0.05, 0.2, 1.0, n_paths=100_000,
                               antithetic=True, rng=np.random.default_rng(1))
assert se_a < se_p
print(f"[OK] 対称変量 SE {se_a:.5f} < プレーン {se_p:.5f}")

c_m0 = merton_jump_call(100.0, 100.0, 0.05, 0.2, 1.0, lam=0.0, gamma_j=-0.1, delta_j=0.15)
checks.append(("Merton λ=0 ≡ BSM", c_m0, bsm.call_price(100.0, 100.0, 0.05, 0.2, 1.0), 1e-6))
c_m = merton_jump_call(S_J, 100.0, R_J, SIG_J, T_J, LAM_J, GAM_J, DEL_J)
p_m_parity = c_m - S_J + 100.0 * np.exp(-R_J * T_J)
assert p_m_parity > 0, "Merton put（パリティ経由）が負"
print(f"[OK] Merton パリティ経由プット = {p_m_parity:.4f} > 0")

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.6g} want={want:.6g}")
    assert ok, name
print("\n全チェック合格")""")
)

# Cell 27: exercises
cells.append(
    md(r"""## 9. 練習問題

**Q1.** CN と implicit、グリッドを倍に細かくしたとき誤差はそれぞれ何分の1になる？

<details><summary>解答</summary>

CN は2次精度 → 約 1/4。implicit は時間1次 → 時間方向は約 1/2（空間は2次）。
</details>

**Q2.** LSM の回帰を「全パス」で行うと何がまずい？

<details><summary>解答</summary>

OTM パス（行使しないことが自明）が回帰を汚し、継続価値の推定が歪む。
Longstaff-Schwartz は ITM パスのみで回帰するのが要点。
</details>

**Q3.** 三項ツリーで Δt を大きくしすぎると起こる問題は？

<details><summary>解答</summary>

p_u または p_d が負になる（確率の非負性が破れ、陽的スキームの不安定性に対応）。
σ√(3Δt) のグリッドでは |r−q−σ²/2|√(Δt/12σ²) < 1/6 が必要。
</details>""")
)

# Cell 28: summary
cells.append(
    md(r"""## まとめ

| 手法 | 強み | 弱み |
|---|---|---|
| ツリー（＋CV補正） | 早期行使が自然、実装簡単 | 多資産・パス依存に弱い |
| MC（＋分散削減） | パス依存・多資産 | 1/√N、早期行使は LSM 必要 |
| FD（implicit/CN） | 境界も Greeks も格子から読める | 高次元に弱い |
| Merton 級数 | ジャンプ→スマイルを解析的に | 較正は別問題 |

**次へ**: `volumes/07_swaps`（Ch.7, 34 — `rates.py` を本格活用）
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "numerical.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
