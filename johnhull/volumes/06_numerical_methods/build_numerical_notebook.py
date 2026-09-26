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
cells.append(
    md(r"""> **核心** — 閉形式が無い商品は、木・モンテカルロ・有限差分で数値的に解く。<br>
> **直感** — どれも『リスク中立の割引期待値』を別の近似で計算しているだけ。互いに一致すべき。<br>
> **実務** — エキゾチック・アメリカン・多資産の値付けは数値手法が主力。相互整合が検算になる。""")
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

- 連続利回り $q$ は成長因子 $a = e^{(r-q)\Delta t}$（eq 21.4–21.7）、時変 $r(t), q(t)$ は $a = e^{[f(t)-g(t)]\Delta t}$（eq 21.11）だが、hullkit のツリーは定数 $r, q$ のみ
  （第1冊・第2冊で実装済み）
- **コントロール変量**: 同じツリーで欧州版も価格付けし、既知の BSM 解析値との誤差で補正

$$f^* = f_{\text{Am,tree}} + \left(f_{\text{Eu,BSM}} - f_{\text{Eu,tree}}\right)$$

ツリーの離散化誤差が Am/Eu 双方にほぼ同じ量だけ乗る、という観察を利用します。""")
)
cells.append(
    md(r"""> **核心** — ツリーの誤差は、解析解のある類似商品で補正できる(コントロール変量)。<br>
> **直感** — Am と Eu の木の誤差はほぼ同じ → Am_tree+(Eu_exact−Eu_tree) で誤差を相殺。<br>
> **実務** — 少ない計算量で精度を上げる定番テク。実装の高速化に効く。""")
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
cells.append(
    md(r"""> **核心** — 上・横・下の3分岐。二項より自由度が高く安定。<br>
> **直感** — Δt が大きすぎると分岐確率が負になり得る点に注意。<br>
> **実務** — 有限差分(陽解法)と等価で、バリア等の扱いが二項より素直。""")
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
cells.append(
    md(r"""> **核心** — パスを大量生成し、ペイオフ平均を割引く。誤差は 1/√N。<br>
> **直感** — 大数の法則。パス依存・多資産が得意、アメリカンは工夫が要る。<br>
> **実務** — エキゾチック・XVA・多資産の主力。収束の遅さを分散削減で補う。""")
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
cells.append(
    md(r"""> **核心** — 同じ精度を少ないパスで——対称変量・制御変量・重点サンプリング。<br>
> **直感** — 推定量の分散を構造的に下げる。乱数をただ増やすより賢い。<br>
> **実務** — MC の計算コストを桁で下げる。実務の MC はほぼ必ず分散削減付き。

> **実務での出番 — なぜ 1/√N が問題なのか**
>
> MC 誤差は 1/√N でしか縮まない——精度を10倍にするにはパスを100倍必要。XVA のように『全取引×多数シナリオ×多数時点』を回す計算では、これが現実的な壁になる。分散削減(制御変量・重点サンプリング)と準モンテカルロ(Sobol 列、第15巻)は、この壁を破る実務必須技術。""")
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
cells.append(
    md(r"""> **核心** — 価格 PDE を格子上で差分近似して解く。<br>
> **直感** — 陽解法は単純だが条件付き安定、陰解法/CN は無条件安定。<br>
> **実務** — 低次元・早期行使(アメリカン)に強い。バリアも境界条件で自然に扱える。""")
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
cells.append(
    md(r"""> **核心** — 各時点で継続価値と即時行使を比較し、早期行使境界 S* を得る。<br>
> **直感** — 境界より下(プット)で行使。満期に近づくと S* → K。<br>
> **実務** — アメリカン商品の行使戦略・値付け。FD/ツリーが MC より素直。""")
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
# Section 4: Hull §27.1 alternative models & later LSM
# ===========================================================================

# Cell 18: §27.1 model map
cells.append(
    md(r"""## 7. Black–Scholes–Merton 以外のモデル（§27.1）

この節は Hull 11e Global Edition pp.641–646 の3モデルを追う。記号の時間は年、金額は通貨、
ボラティリティは年率。次節以降に現れる Heston・SABR は第14巻で扱う。

| モデル | ランダム性 | 主な形状 |
|---|---|---|
| CEV | 株価依存の局所ボラ | β<1 で下側のボラが高い |
| Merton ジャンプ拡散 | 正規拡散＋ポアソンジャンプ | 下向きジャンプで左尾が厚い |
| 分散ガンマ（VG） | ガンマ時計で進むブラウン運動 | 時計のばらつきで厚い裾、θで歪み |

以下の図は独立参照の保存値を Book と portal で共用する。価格の一致は数値検証であり、
市場較正やヘッジ成績の検証ではない。""")
)
cells.append(
    md(r"""### 7.1 CEV：株価が変わると局所ボラも変わる

$$dS_t=(r-q)S_t\,dt+\sigma S_t^{\beta}\,dW_t,\qquad
\sigma_{\mathrm{loc}}(S)=\sigma S^{\beta-1}.$$

$\beta=1$ なら BSM。$\beta<1$ なら株価低下で局所ボラが上がり、$\beta>1$ なら逆。
異なる $\beta$ を比較するときは $S_0=100$ における局所ボラを20%に固定し、
$\sigma=0.2S_0^{1-\beta}$ とする。$\sigma$ の単位は $\beta$ に応じて変わる。
欧州価格は非心カイ二乗分布の閉形式で計算できる。ここでは $0<\beta<1$ の
価格を独立した局所ボラ PDE（Crank–Nicolson）とも照合した。""")
)

cells.append(
    code(r"""from hullkit import alternative_models
from hullkit._alternative_models_lesson import _figures, _load_reference

am_reference = _load_reference()
am_figures = _figures()
display(am_figures["alternative_cev"])
for strike, pde_price in am_reference["cev"]["pde_beta_0_8_calls"].items():
    closed = alternative_models.cev_price(
        100.0, float(strike), 0.05, 0.2 * 100**0.2, 0.5, beta=0.8)
    print(f"CEV K={strike}: 非心χ² {closed:.6f}, 独立PDE {pde_price:.6f}, 差 {closed-pde_price:+.6f}")""")
)

cells.append(
    md(r"""### 7.2 Merton：ジャンプ補償と欧州価格

ジャンプ回数 $N_T\sim\mathrm{Poisson}(\lambda T)$、各ジャンプの倍率の対数を
$\log(1+J_i)\sim N(\gamma,\delta^2)$ とする。平均ジャンプ率
$k=E[J]=e^{\gamma+\delta^2/2}-1$ を引き、リスク中立ドリフトを $r-q-\lambda k$ にする。
そうしないと割引後の期待株価が $S_0e^{-qT}$ と一致しない。

$$\log(S_T/S_0)=(r-q-\lambda k-\sigma^2/2)T+\sigma W_T+
\sum_{i=1}^{N_T}\log(1+J_i).$$

Hull の BSM 級数は $\lambda'=\lambda(1+k)$ でポアソン重みを変え、
$\sigma_n^2=\sigma^2+n\delta^2/T$、
$r_n=r-\lambda k+n(\gamma+\delta^2/2)/T$ を用いる。
下図の価格は別経路（元の $\mathrm{Poisson}(\lambda T)$ ごとに条件付き対数正規給付を積分）と照合した。""")
)
cells.append(
    code(r"""S_J, R_J, T_J = 100.0, 0.05, 0.25
LAM_J, GAM_J, DEL_J, SIG_J = 1.0, -0.10, 0.15, 0.20

def merton_jump_call(S, K, r, sigma, T, lam, gamma_j, delta_j, q=0.0):
    return alternative_models.merton_jump_price(S, K, r, sigma, T, lam, gamma_j, delta_j, q)

display(am_figures["alternative_merton"])
for strike in (75.0, 100.0, 125.0):
    print(f"K={strike:.0f}: Merton call={merton_jump_call(S_J, strike, R_J, SIG_J, T_J, LAM_J, GAM_J, DEL_J):.6f}")""")
)

cells.append(
    md(r"""### 7.3 Table 27.1：ジャンプ回数を実際に数える

原典の $\lambda=0.5$/年、$T=2$ 年では $E[N_T]=1$。$m=0$ と $m=1$ は共に約0.3679、
$m\le2$ の累積確率は約0.9197。1回以上のジャンプ確率は $1-e^{-1}\approx0.6321$。
個々のジャンプの大きさも標本抽出する。複数回の対数ジャンプを合計した分布は
$N\gamma+\sqrt N\delta Z$ と等価で、下の経路例はこの表現を使う。""")
)
cells.append(
    code(r"""display(am_figures["alternative_poisson"])
print("m / P(N=m) / P(N≤m)")
for m, p, cumulative in zip(
    am_reference["poisson_table"]["counts"],
    am_reference["poisson_table"]["probability"],
    am_reference["poisson_table"]["cumulative"], strict=True):
    print(f"{m} / {p:.4f} / {cumulative:.4f}")""")
)

cells.append(
    md(r"""### 7.4 ジャンプの経路と短期スマイル

- $\gamma < 0$（下向きジャンプ）→ 左裾が厚い → **株式型スキュー**（第5冊のスマイル再現）
- ジャンプ回数と各サイズが偶然に決まるため、経路は連続ではない
- 短期でジャンプ由来の裾・スマイルが目立ち得る。形状は $\lambda,\gamma,\delta,\sigma,T$ に依存する""")
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

cells.append(
    md(r"""### 7.5 分散ガンマ：ランダムな時計

$G_T\sim\mathrm{Gamma}(T/\nu,\text{scale}=\nu)$ なので $E[G_T]=T$、
$\operatorname{Var}(G_T)=\nu T$。独立なブラウン運動をこの時計で動かす：

$$\log S_T=\log S_0+(r-q+\omega)T+\theta G_T+\sigma W_{G_T},\quad
\omega=\nu^{-1}\log(1-\theta\nu-\sigma^2\nu/2).$$

$1-\theta\nu-\sigma^2\nu/2>0$ は株価の指数モーメントに必要。
$\omega$ が $E[S_T]=S_0e^{(r-q)T}$ を保つ。原典 Figure 27.1 と同じ
$S_0=100,T=0.5,\nu=0.5,\theta=0.1,\sigma=0.2,r=q=0$ の満期株価を、
40万標本の VG 密度と GBM の対数正規密度で比較する。密度図は標本誤差を持つ。
欧州価格は独立にガンマ密度積分で照合する。""")
)
cells.append(
    code(r"""display(am_figures["alternative_vg"])
for strike in (75.0, 100.0, 125.0):
    vg_call = alternative_models.variance_gamma_price(100.0, strike, 0.0, 0.2, 0.5, 0.5, 0.1)
    print(f"VG K={strike:.0f}: call={vg_call:.6f}")""")
)
cells.append(
    md(r"""### 7.6 使い分けと限界

CEV は **株価水準と瞬時ボラの結び付き**、Merton は **まれな大きい変化**、
VG は **価格変動が進む時計そのもののばらつき**を表す。どれも BSM の一定ボラ正規対数収益から
外れるが、パラメータだけで市場スマイル全体に自動で一致するわけではない。

ここでの価格は欧州バニラ・定数パラメータ・連続利回りの合成例。
CEV の $\beta>1$ には無限遠境界の扱いに注意が要り、教材の独立 PDE 照合は $\beta=0.8$ のみ。
ジャンプや VG での動的ヘッジは連続拡散のデルタだけでは完結しない。
モデル選択・較正・尾部リスク・ヘッジ費用は別の検証を要する。""")
)

# ===========================================================================
# Section 8: §27.2 stochastic volatility models
# ===========================================================================

cells.append(
    md(r"""## 8. 確率ボラティリティ・モデル（§27.2）

この節は Hull 11e Global Edition pp.646–649 を追う。時間は年、金額は通貨、金利とボラは年率。
BSM は一定のボラを仮定するが、実際のボラは時間とともに変わる（第23章）。§27.2 は次の順で一定ボラを外す。

| 小節 | ボラの扱い | 原典の要点 |
|---|---|---|
| 8.1 | 時間の既知関数 $\sigma(t)$ | 式27.1。BSM に平均分散率を入れれば正しい |
| 8.2–8.3 | 株価と無相関な確率変数 | Hull–White：BSM 価格を平均分散率の分布で平均する |
| 8.4 | 株価と相関 | 負の相関で株式型スキュー。$\alpha=0.5$ は Heston |
| 8.5 | SABR | Hagan らの近似 IV。$\sigma_0,\rho,\nu$ の役割 |
| 8.6 | GARCH・rough volatility | 位置付けと限界 |

図は独立参照（本冊の関数を使わない数値計算）の保存値を Book と portal で共用する。
Heston の特性関数と COS 法、SABR の Greeks は第14巻で深掘りする。""")
)
cells.append(
    md(r"""### 8.1 時間で決まるボラと平均分散率（式27.1）

ボラが時間の既知関数なら、リスク中立過程は

$$dS=(r-q)S\,dt+\sigma(t)S\,dz. \tag{27.1}$$

$\ln S_T$ は平均 $\ln S_0+(r-q)T-\tfrac12\int_0^T\sigma(t)^2dt$、分散 $\int_0^T\sigma(t)^2dt$ の正規分布。
したがって BSM に**平均分散率** $\bar V=\frac1T\int_0^T\sigma(t)^2dt$ を入れれば正確な価格になる。
分散率はボラの2乗である。

原典の例：1年のうち前半6か月は20%、後半6か月は30%。平均分散率は
$0.5\times0.20^2+0.5\times0.30^2=0.065$ で、BSM のボラは $\sqrt{0.065}=25.5\%$。
ボラの単純平均25%を入れるのは誤り。下の赤線は、時刻 $t$ に残る期間の平均分散率の平方根で、
$t$ が進むと前半の低いボラが抜けて30%へ近づく。価格は $\sigma(t)$ を直接使う独立の
Crank–Nicolson PDE と照合した。""")
)
cells.append(
    code(r"""from hullkit import stochastic_volatility as sv
from hullkit._stochastic_volatility_lesson import _figures as sv_lesson_figures
from hullkit._stochastic_volatility_lesson import _load_reference as sv_load_reference

sv_reference = sv_load_reference()
sv_figures = sv_lesson_figures()
display(sv_figures["stochvol_term"])
sv_term = sv_reference["term_structure"]
sv_avg = sv.average_variance_rate(sv_term["durations"], sv_term["volatilities"])
print(f"平均分散率 = {sv_avg:.4f}, BSMのボラ = {math.sqrt(sv_avg):.4f}（原典 0.065, 25.5%）")
for strike, row in sv_term["prices"].items():
    price = sv.time_dependent_bsm_price(
        100.0, float(strike), 0.05, sv_term["durations"], sv_term["volatilities"])
    print(f"K={float(strike):.0f}: 平均分散のBSM {price:.5f}, 独立PDE {row['pde']:.5f}, "
          f"差 {price - row['pde']:+.1e} / 単純平均25%のBSM {row['arithmetic_vol_bsm']:.5f}")""")
)
cells.append(
    md(r"""### 8.2 確率ボラ（式27.2–27.3）と Hull–White の混合公式

ボラ自体が確率的に動くモデルとして、原典は分散率 $V$ の過程を明示する：

$$\frac{dS}{S}=(r-q)\,dt+\sqrt V\,dz_S, \tag{27.2}$$
$$dV=a(V_L-V)\,dt+\xi V^{\alpha}\,dz_V. \tag{27.3}$$

$V$ は率 $a$ で水準 $V_L$ に引き戻される。$\alpha=0.5$ が Heston モデル。

**Hull–White の結果。** ボラが株価と**無相関**なら、分散の経路を条件にすると $\ln S_T$ は
分散 $\bar V T$ の正規分布になる（$\bar V$ は満期までの平均分散率）。よって欧州コールは

$$c=\int_0^\infty c_{\mathrm{BSM}}(\bar V)\,g(\bar V)\,d\bar V,$$

$c_{\mathrm{BSM}}(\bar V)$ は分散率 $\bar V$ の BSM 価格、$g$ はリスク中立世界での $\bar V$ の密度。
$g$ は $V$ の過程によらず、この式が成り立つ。以下は $S_0=100,r=5\%,T=1$、$V_0=V_L=0.04$、
$a=1.5$、$\xi=0.6$、$\alpha=0.5$。$V$ の各ステップを厳密な平方根過程の遷移（非心カイ二乗）で
抽出し、$\bar V$ の標本で BSM 価格を平均する。独立参照は Heston 特性関数の Gil-Pelaez 積分。""")
)
cells.append(
    code(r"""sv_h = sv_reference["heston"]
sv_vbar = sv.simulate_average_variance(
    sv_h["v0"], sv_h["reversion"], sv_h["long_run"], sv_h["vol_of_variance"], sv_h["expiry"],
    n_steps=250, n_paths=50_000, seed=2702)
sv_ev = sv.expected_average_variance(sv_h["v0"], sv_h["reversion"], sv_h["long_run"], sv_h["expiry"])
print(f"E[V̄] = {sv_ev:.4f}（標本平均 {sv_vbar.mean():.4f}）, √E[V̄] = {math.sqrt(sv_ev):.4f}")
for strike in (80.0, 100.0, 120.0):
    mixed, se = sv.mixing_price(sv_h["spot"], strike, sv_h["rate"], sv_h["expiry"], sv_vbar)
    fourier_price = sv_h["smiles"]["+0.0"]["prices"][sv_h["strikes"].index(strike)]
    print(f"K={strike:.0f}: 混合公式 {mixed:.4f} ± {se:.4f}, 独立Fourier {fourier_price:.4f}, "
          f"差 {(mixed - fourier_price) / se:+.2f} SE")""")
)
cells.append(
    md(r"""### 8.3 無相関なら ATM は過大、裾は過小

原典は、この結果から BSM が**ATM 付近を過大評価し、深い ITM・OTM を過小評価する**と述べる。
比較の BSM は同じ期待分散 $E[\bar V]$ を使う。理由は $c_{\mathrm{BSM}}$ の $\bar V$ に関する曲がり方にある。
ATM 付近では $c_{\mathrm{BSM}}\approx 0.4S_0\sqrt{\bar V T}$ が $\bar V$ の凹関数なので、
Jensen の不等式から $E[c(\bar V)]<c(E[\bar V])$。深い OTM では凸なので逆になる。

逆算 IV にすると U 字のスマイルで、通貨オプションのスマイルに近い（§20.2）。$\rho=0$ では
IV が対数フォワード・マネネス $\ln(K/F_0)$ について左右対称になる。""")
)
cells.append(
    code(r"""display(sv_figures["stochvol_mixing"])
sv_gap = [p - f for p, f in zip(sv_h["smiles"]["+0.0"]["prices"], sv_h["flat_prices"], strict=True)]
sv_over = [k for k, g in zip(sv_h["strikes"], sv_gap, strict=True) if g < 0]
print(f"BSM(√E[V̄]) が過大評価する行使価格: {min(sv_over):.0f}–{max(sv_over):.0f}（それ以外は過小評価）")
for strike in (60.0, 100.0, 160.0):
    print(f"K={strike:.0f}: 確率ボラ − BSM = {sv_gap[sv_h['strikes'].index(strike)]:+.4f}")
sv_sym = max(abs(r["upper_vol"] - r["lower_vol"]) for r in sv_h["rho_zero_symmetry"])
print(f"ρ=0 の IV の左右差（ln K/F = ±0.1〜±0.4）: 最大 {sv_sym:.1e}")""")
)
cells.append(
    md(r"""### 8.4 相関と Heston：株式型スキュー

株価とボラが相関すると計算は難しくなり、一般にはモンテカルロを使う。$\alpha=0.5$ なら
Heston の解析解がある。原典 p.649 の書き方では

$$\frac{dS_t}{S_t}=(r-q)\,dt+\sqrt{V_t}\left(\rho\,dz_t+\sqrt{1-\rho^2}\,dw_t\right),\qquad
dV_t=a(V_L-V_t)\,dt+\xi\sqrt{V_t}\,dz_t,$$

$dz_t,dw_t$ は無相関、$\rho$ は株価とボラの相関。**負の相関**では株価下落時にボラが上がり、
左の裾が厚くなって、株式のような右下がりのスキューになる（§20.3）。

下図は他のパラメータを 8.2 と同じにして $\rho$ だけを変える。公開関数は COS 法、
独立参照は特性関数の Gil-Pelaez 積分で、78価格の差は保存記録にある。""")
)
cells.append(
    code(r"""display(sv_figures["stochvol_correlation"])
for label in ("-0.7", "+0.0", "+0.7"):
    row = sv_h["smiles"][label]
    cos_100 = sv.heston_price(sv_h["spot"], 100.0, sv_h["rate"], sv_h["expiry"], sv_h["v0"],
                              sv_h["reversion"], sv_h["long_run"], sv_h["vol_of_variance"], float(label))
    reference_100 = row["prices"][sv_h["strikes"].index(100.0)]
    iv = dict(zip(sv_h["strikes"], row["implied_vol"], strict=True))
    print(f"ρ={float(label):+.1f}: K=100 COS {cos_100:.6f} / Gil-Pelaez {reference_100:.6f}, "
          f"IV(K=80) {iv[80.0]:.2%}, IV(K=120) {iv[120.0]:.2%}")""")
)
cells.append(
    md(r"""### 8.5 SABR：Hull の近似式と $\sigma_0,\rho,\nu$

SABR は満期 $T$ ごとの欧州オプション（特に金利オプション）のスマイルに使われる：

$$dF=\sigma F^{\beta}\,dz,\qquad \frac{d\sigma}{\sigma}=\nu\,dw,$$

$F$ はフォワード（ドリフト0の世界）、$\sigma$ は確率ボラ、$\rho$ は $dz,dw$ の相関、
$\sigma_0,F_0$ は初期値。原典の Hagan らの近似 IV は、
$x=(F_0K)^{(1-\beta)/2}$、$y=(1-\beta)\ln(F_0/K)$ として

$$A=\frac{\sigma_0}{x\left(1+y^2/24+y^4/1920\right)},\quad
B=1+\left(\frac{(1-\beta)^2\sigma_0^2}{24x^2}+\frac{\rho\beta\nu\sigma_0}{4x}+\frac{2-3\rho^2}{24}\nu^2\right)T,$$
$$\phi=\frac{\nu x}{\sigma_0}\ln\frac{F_0}{K},\qquad
\chi=\ln\left(\frac{\sqrt{1-2\rho\phi+\phi^2}+\phi-\rho}{1-\rho}\right),$$

IV は $AB\phi/\chi$、$F_0=K$ では $\sigma_0B/F_0^{1-\beta}$。$\sigma_0$ は水準を決め、
BSM 型のボラに $F_0^{1-\beta}$ を掛けたものに近い。$\rho$ が大きく正なら右上がり、大きく負なら
右下がり、中間ではU字。$\nu$ が大きいほどスマイルが強まる。金利では $\beta=0.5$ がよく使われる。

例は $F_0=3\%$、$T=1$、$\beta=0.5$、$\sigma_0=0.2F_0^{0.5}$。`hullkit.sabr.sabr_implied_vol` は
原典の式の独立転記と一致し（保存記録）、点は Euler 法 SABR のモンテカルロ（40万経路）の逆算 IV。
メニューで $\rho$ と $\nu$ を切り替えられる。""")
)
cells.append(
    code(r"""from hullkit import sabr as sabr_model

display(sv_figures["stochvol_sabr"])
sv_s = sv_reference["sabr"]
print(f"σ0 = {sv_s['sigma0']:.6f}（= 0.2 × F0^0.5）")
print("K / Hull式IV / MC逆算IV ± SE / 差")
for row in sv_s["monte_carlo"]["rows"]:
    formula = sabr_model.sabr_implied_vol(
        sv_s["forward"], row["strike"], sv_s["expiry"], sv_s["sigma0"], sv_s["beta"], 0.0, 0.4)
    print(f"{row['strike']:.3f} / {formula:.4%} / {row['implied_vol']:.4%} ± "
          f"{row['implied_vol_standard_error']:.4%} / {formula - row['implied_vol']:+.4%}")""")
)
cells.append(
    md(r"""### 8.6 GARCH・rough volatility と限界

**GARCH。** 第23章の EWMA・GARCH(1,1) も確率ボラの別の表し方で、Duan は GARCH(1,1) を
内部整合的なオプション価格モデルの基礎にできることを示した（推定は第5巻）。

**Rough volatility。** Gatheral・Jaisson・Rosenbaum（2018）は、ボラの振る舞いは通常のブラウン運動より
分数ブラウン運動（§14.8）でよく表せると論じ、高頻度データから株価指数のハースト指数 $H$ を
0.06–0.20 と推定した（通常のブラウン運動は $H=0.5$）。解析的に扱える rough Heston、
通常のブラウン運動だけで rough Heston を模倣する lifted Heston（Jaber 2019）がある。
本リポジトリでは rough Heston の核を第21巻、rBergomi の教師データを第18–19巻で扱う。本節では数値検証していない。

**限界。** 本節の価格は一定パラメータ・欧州バニラ・合成市場の例。Hull–White の混合公式は
無相関のときだけ成り立つ。SABR 式は近似で、誤差は深い OTM と長い満期で大きくなり得る
（ここでは7行使価格で MC との差を実測した）。市場への較正、ヘッジ成績、ジャンプは扱わない。
$\xi\to0$ では確率ボラの効果が消え、BSM（$\sqrt{E[\bar V]}$）に戻る。

1. ボラが20%→30%と変わるとき、BSM に25%を入れるとどちらに偏るか。
2. 混合公式で平均しているのは何の分布か。相関があるとなぜ使えないか。
3. ATM では確率ボラが価格を下げ、深い OTM では上げるのはなぜか。
4. 株式市場で $\rho<0$ が選ばれるのは、どんな株価とボラの動きを表すためか。
5. SABR の $\rho$ と $\nu$ を変えると、スマイルのどこがどう変わるか。

**回答の手掛かり：** 分散の加法性、条件付き対数正規、BSM 価格の凹凸、下落時のボラ上昇、傾きと曲がり。""")
)

# Cell 22: LSM md
cells.append(
    md(r"""## 9. Longstaff-Schwartz（LSM）— MC でアメリカン（Ch.27）

後ろ向きに各行使時点で:
1. ITM パスについて「継続価値」を**将来キャッシュフローの回帰**（基底: $1, S, S^2$）で推定
2. 即時行使価値 > 推定継続価値 のパスはそこで行使
3. 全パスの割引キャッシュフローを平均

回帰がツリーの後退帰納を代替するため、パス依存・多資産でも早期行使を扱えます。""")
)
cells.append(
    md(r"""> **核心** — 回帰でアメリカンの継続価値を推定し、MC で早期行使を扱う(LSM)。<br>
> **直感** — 後退帰納を回帰で代替する。だからパス依存・多資産でもアメリカンが解ける。<br>
> **実務** — バミューダ・スワプション、CVA の wrong-way risk など実務の重い計算で主力。""")
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
- CEV の閉形式（非心 χ²）はポインタのみ。Heston / SABR の半解析解は第14冊で実装""")
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
    md(r"""## 10. 練習問題

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
