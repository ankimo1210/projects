"""
build_stoch_vol_fourier_notebook.py
===================================
nbformat-dict pattern to generate stoch_vol_fourier.ipynb
(A2 deep-dive — stochastic volatility & Fourier pricing).

Plotly figures (``fig.show()``) so they render in the static Jupyter Book HTML.
Numerical-verification cells assert against closed forms / Monte-Carlo.
References: Gatheral, *The Volatility Surface*; Heston (1993); Fang & Oosterlee
(2008); Hagan et al. (2002).

Usage:
    uv run python build_stoch_vol_fourier_notebook.py
"""

import json
import os


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
cells.append(
    md(r"""# 確率ボラティリティと Fourier 価格付け（A2 深掘り）

`johnhull` 深掘りシリーズ第2巻。Hull は**フラット/局所ボラ**までだが、市場の
インプライド・ボラは満期・ストライクで動く**スマイル/サーフェス**を描く。本巻は
それを生む **Heston モデル**、閉形式が無いときの **Fourier（COS）価格付け**、
市場標準の **SABR スマイル補間** を、Gatheral / Fang-Oosterlee / Hagan の水準で扱う。

| 節 | 内容 | 主参照 |
|---|---|---|
| 1 | なぜ確率ボラか（フラット仮定の破れ） | Gatheral Ch.1 |
| 2 | Heston モデルの動学と Feller 条件 | Heston (1993) |
| 3 | 特性関数（little-trap 形） | Albrecher+ (2007) |
| 4 | COS 法による Fourier 価格付け | Fang & Oosterlee (2008) |
| 5 | Heston スマイルの形（ρ, ξ, κ の役割） | Gatheral Ch.3 |
| 6 | SABR と Hagan 公式 | Hagan+ (2002) |

> Hull 該当章: Ch.20（ボラティリティ・スマイル）。本巻はその生成メカニズムと価格付け。""")
)
cells.append(
    md(r"""> **核心** — ボラ自体を確率過程にするとスマイルが自然に出る。価格は Fourier で高速計算。<br>
> **直感** — σ が動く → 終端分布が裾を持つ → スマイル。特性関数があれば積分で値付け。<br>
> **実務** — Heston/SABR は株・FX のスマイル・モデルの業界標準。COS 法で高速カリブレーション。""")
)

cells.append(
    code(r"""# --- imports ---
import numpy as np
import plotly.graph_objects as go

from hullkit import bsm, fourier, heston, sabr, volatility
from hullkit import plotly_viz as pv

np.set_printoptions(precision=4, suppress=True)""")
)

cells.append(
    md(r"""### 記号と単位

- $S$=原資産価格・$K$=ストライク(同一通貨単位)、$r$=無リスク金利(**連続複利・年率**)、$T$=満期(**年**)、$y=\ln(S_T/S_0)$=対数収益率。
- Heston: $v_t$=**瞬間分散**(年率, ボラは $\sqrt{v_t}$)、$v_0$=初期分散、$\kappa$=平均回帰速度(/年)、$\theta$=長期分散、$\xi$=vol-of-vol、$\rho$=スポット-ボラ相関。
- Fourier: $\phi(u)$=特性関数・$N$=COS 項数。SABR: $\alpha$=初期ボラ・$\beta$=バックボーン・$\nu$=vol-of-vol・$\rho$=相関。""")
)

# 1. why stochastic vol
cells.append(
    md(r"""## 1. なぜ確率ボラティリティか

BSM は単一の $\sigma$ を仮定するが、市場の**インプライド・ボラ**はストライク $K$ で
一定でない（株式では下方で高い「スキュー」）。フラットなら下図は水平線になるはず。
確率ボラ（ボラ自身が確率過程）はこのスマイルを内生的に生む。局所ボラ（Dupire）は
スマイルに完全フィットできるが、**前方スマイルの動学が非現実的**で、確率ボラやその併用が要る。""")
)
cells.append(
    md(r"""> **核心** — BSM の一定 σ ではスマイルを説明できない。σ を確率過程にする。<br>
> **直感** — 現実のボラはクラスタリングし平均回帰する。一定 σ は強すぎる仮定。<br>
> **実務** — スマイル整合のエキゾチック値付け・ヘッジに不可欠。""")
)

cells.append(
    code(r"""# Heston が生むスマイル vs BSM のフラット仮定
S0, r, T = 100.0, 0.05, 1.0  # S0=100, r=年率5%(連続複利), T=1年
v0, kappa, theta, xi, rho = 0.04, 1.5, 0.04, 0.6, -0.7  # 初期分散0.04(≈20%ボラ)/κ=1.5(/年)/θ=0.04/ξ=0.6/ρ=-0.7
def cf(u):
    return heston.heston_cf(u, r, T, v0, kappa, theta, xi, rho)
Ks = np.linspace(80, 120, 21)
iv = np.array([volatility.implied_vol(fourier.cos_price(cf, S0, K, r, T), S0, K, r, T) for K in Ks])
fig = go.Figure()
fig.add_trace(go.Scatter(x=Ks, y=iv, mode="lines+markers", name="Heston IV", line={"color": "#d62728"}))
fig.add_trace(go.Scatter(x=Ks, y=np.full_like(Ks, np.sqrt(v0)), mode="lines",
                         name="BSM フラット (√v0)", line={"color": "#1f77b4", "dash": "dash"}))
fig.update_layout(title="市場はフラットでない: Heston スマイル vs BSM", xaxis_title="ストライク K",
                  yaxis_title="インプライド・ボラティリティ")
fig.show()""")
)

# 2. Heston dynamics
cells.append(
    md(r"""## 2. Heston モデル

$$dS_t = r S_t\,dt + \sqrt{v_t}\,S_t\,dW_t^1,\qquad
dv_t = \kappa(\theta - v_t)\,dt + \xi\sqrt{v_t}\,dW_t^2,\qquad d\langle W^1,W^2\rangle=\rho\,dt.$$

- $v_t$: 瞬間分散(年率, $\sqrt{v_t}$=瞬間ボラ)、$v_0$: 初期分散、$\kappa$: 分散の平均回帰速度(/年)、$\theta$: 長期分散、$\xi$: vol-of-vol、$\rho$: スポット-ボラ相関。
- **Feller 条件** $2\kappa\theta\ge\xi^2$ で $v_t>0$ がほぼ保証される（破れると 0 に触れる）。
- $\rho<0$ は「価格下落↔ボラ上昇」を表し、**下方スキュー**を生む（株式の典型）。

下図は $(S_t, v_t)$ の標本路。ボラ自身が動く（フルトランケーション・オイラー）。""")
)
cells.append(
    md(r"""> **核心** — 分散 v_t が CIR 過程で平均回帰。株とボラに相関 ρ。<br>
> **直感** — ρ<0 で下落時にボラ上昇 → 左スキュー。ξ(vol-of-vol)が曲率。<br>
> **実務** — 株・指数オプションのデファクト。半解析解があり高速。""")
)

cells.append(
    code(r"""# Heston の標本路 (S と √v)
def heston_paths(S0, r, T, v0, kappa, theta, xi, rho, n_steps, n_paths, seed):
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    corr = np.sqrt(1 - rho**2)
    S = np.empty((n_paths, n_steps + 1)); S[:, 0] = S0
    V = np.empty((n_paths, n_steps + 1)); V[:, 0] = v0
    s = np.full(n_paths, float(S0)); v = np.full(n_paths, float(v0))
    for k in range(1, n_steps + 1):
        z = rng.standard_normal((n_paths, 2))
        dw1 = z[:, 0] * np.sqrt(dt)
        dw2 = (rho * z[:, 0] + corr * z[:, 1]) * np.sqrt(dt)
        vp = np.maximum(v, 0.0)
        s = s * np.exp((r - 0.5 * vp) * dt + np.sqrt(vp) * dw1)
        v = v + kappa * (theta - vp) * dt + xi * np.sqrt(vp) * dw2
        S[:, k] = s; V[:, k] = v
    return S, V

S, V = heston_paths(100, 0.05, 1.0, 0.04, 1.5, 0.04, 0.6, -0.7, 250, 6, seed=1)
tg = np.linspace(0, 1, 251)
figp = go.Figure()
for k in range(S.shape[0]):
    figp.add_trace(go.Scatter(x=tg, y=S[k], mode="lines", line={"width": 1}, showlegend=False))
figp.update_layout(title="Heston: 株価 S_t の標本路", xaxis_title="t", yaxis_title="S_t")
figp.show()
figv = go.Figure()
for k in range(V.shape[0]):
    figv.add_trace(go.Scatter(x=tg, y=np.sqrt(np.maximum(V[k], 0)), mode="lines", line={"width": 1}, showlegend=False))
figv.update_layout(title="Heston: ボラティリティ √v_t の標本路（平均回帰）", xaxis_title="t", yaxis_title="√v_t")
figv.show()""")
)

# 3. characteristic function
cells.append(
    md(r"""## 3. 特性関数

Heston では密度の閉形式は無いが、対数収益率 $y=\ln(S_T/S_0)$ の**特性関数**
$\phi(u)=\mathbb E^Q[e^{iuy}]$ は閉形式で書ける（数値的に安定な little-trap 形, Albrecher+ 2007）：
$$d=\sqrt{(\rho\xi iu-\kappa)^2+\xi^2(iu+u^2)},\quad g=\frac{\kappa-\rho\xi iu-d}{\kappa-\rho\xi iu+d},$$
$$\phi(u)=\exp\!\Big(iur T+\tfrac{\kappa\theta}{\xi^2}\big[(\kappa-\rho\xi iu-d)T-2\ln\tfrac{1-ge^{-dT}}{1-g}\big]
+\tfrac{v_0}{\xi^2}(\kappa-\rho\xi iu-d)\tfrac{1-e^{-dT}}{1-ge^{-dT}}\Big).$$
特性関数があれば、Fourier 反転で**密度**も**価格**も得られる（§4）。""")
)
cells.append(
    md(r"""> **核心** — Heston は密度が解析的でなくても特性関数は閉形式。<br>
> **直感** — Fourier 空間では難しい分布も扱いやすい形になる。<br>
> **実務** — 特性関数さえあれば価格が積分1本で出る——モデル選択の幅が広がる。""")
)

cells.append(
    code(r"""# CF(0)=1 を確認し、CF から密度を復元（∫=1）
print("φ(0) =", heston.heston_cf(np.array([0.0]), r, T, v0, kappa, theta, xi, rho)[0], " (=1)")
y, f = fourier.cos_density(cf, N=256, L=12.0, n_grid=2000)
print("∫ density dy =", float(np.trapezoid(f, y)), " (=1)")
figd = go.Figure(go.Scatter(x=y, y=f, mode="lines", line={"color": "#d62728"}))
figd.update_layout(title="特性関数から復元した対数収益率の密度（COS）",
                   xaxis_title="y = ln(S_T/S0)", yaxis_title="密度")
figd.show()""")
)

# 4. COS method
cells.append(
    md(r"""## 4. COS 法による Fourier 価格付け

切断区間 $[a,b]$ 上で密度を**Fourier-余弦級数**で近似する（Fang & Oosterlee 2008）。
$$f(y)\approx\sum_{k=0}^{N-1}{}' A_k\cos\!\Big(k\pi\tfrac{y-a}{b-a}\Big),\quad
A_k=\tfrac{2}{b-a}\,\mathrm{Re}\Big\{\phi\!\big(\tfrac{k\pi}{b-a}\big)e^{-ik\pi a/(b-a)}\Big\},$$
（$\sum'$ は初項を半分に）。ペイオフの余弦係数 $U_k$（コール/プットは $\chi_k,\psi_k$ の
閉形式）と組み合わせ、
$$V=e^{-rT}\sum_{k=0}^{N-1}{}' \mathrm{Re}\Big\{\phi\big(\tfrac{k\pi}{b-a}\big)e^{-ik\pi a/(b-a)}\Big\}U_k.$$
**指数収束**するので少数項（$N\!\sim\!100$）で高精度。Carr-Madan（FFT）も同系統。""")
)
cells.append(
    md(r"""> **核心** — 特性関数からコサイン級数で密度・価格を復元。少数項で高精度。<br>
> **直感** — フーリエ–コサイン展開で積分を有限和に。収束が速い。<br>
> **実務** — Heston カリブレーションの実用的高速化。実務の値付けエンジンに採用。""")
)

cells.append(
    code(r"""# COS の検証: GBM-CF で BSM と一致、Heston で独立な MC と一致
S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0
cos_bsm = fourier.cos_price(fourier.lognormal_cf(r, T, sigma), S0, K, r, T)
print(f"COS(GBM)  = {cos_bsm:.4f}   BSM = {bsm.call_price(S0, K, r, sigma, T):.4f}")

p_cos = fourier.cos_price(cf, S0, K, r, T)
p_mc, se = heston.heston_mc_price(S0, K, r, T, v0, kappa, theta, xi, rho,
                                  n_steps=200, n_paths=200_000, rng=np.random.default_rng(0))
print(f"Heston COS = {p_cos:.4f}   MC = {p_mc:.4f} ± {se:.4f}   ({abs(p_cos - p_mc) / se:.1f} SE)")""")
)

cells.append(
    code(r"""# COS の項数 N に対する密度収束（少数項で十分・低 N は Gibbs 振動）
pv.plotly_cos_density_convergence().show()""")
)

# 5. Heston smile shaping
cells.append(
    md(r"""## 5. Heston スマイルの形

- **$\rho$（相関）**: 符号がスキューの向き。$\rho<0$ で下方が高い（株式）、$\rho>0$ で上方。
- **$\xi$（vol-of-vol）**: スマイルの**曲率**。大きいほど両翼が持ち上がる。
- **$\kappa,\theta$**: 満期方向（期間構造）。$\kappa$ 大で速くフラットへ、$\theta$ が遠期の水準。

下のスライダーで $\rho$ を動かし、スキューが反転する様子を確認。""")
)
cells.append(
    md(r"""> **核心** — ρ で傾き、ξ で曲率、平均回帰でタームストラクチャーが決まる。<br>
> **直感** — パラメータと『スマイルの形』が直感的に対応する。<br>
> **実務** — 市場スマイルへのカリブレーション。パラメータの市場的意味を理解して使う。""")
)

cells.append(
    code(r"""# Heston スマイル: ρ でスキューが反転（スライダー）
pv.plotly_heston_smile().show()

# ATM の IV は概ね √(瞬間分散) 付近、ρ がスキュー（傾き）を作る
atm_iv = volatility.implied_vol(fourier.cos_price(cf, 100, 100, r, T), 100, 100, r, T)
skew = (volatility.implied_vol(fourier.cos_price(cf, 100, 95, r, T), 100, 95, r, T)
        - volatility.implied_vol(fourier.cos_price(cf, 100, 105, r, T), 100, 105, r, T))
print(f"ATM IV ≈ {atm_iv:.4f}（√v0={np.sqrt(v0):.4f}）   95-105 スキュー = {skew:+.4f}（ρ<0 で正）")""")
)

# 6. SABR
cells.append(
    md(r"""## 6. SABR と Hagan 公式

$$dF=\alpha F^\beta dW^1,\quad d\alpha=\nu\,\alpha\,dW^2,\quad d\langle W^1,W^2\rangle=\rho\,dt.$$
Hagan ら(2002)は**特異摂動**で Black インプライド・ボラの近似閉形式を導いた。市場では
$(\alpha,\rho,\nu)$ を日々キャリブレーション、$\beta$ は「バックボーン」を決める（株式 $\beta\!\approx\!1$、
金利 $\beta\!\approx\!0.5$）。$\nu\to0,\ \beta=1$ で**フラット $=\alpha$**、$\nu$ 増で曲率、$\rho<0$ で傾き。""")
)
cells.append(
    md(r"""> **核心** — フォワードと確率ボラの2因子。Hagan の漸近 IV 公式で即スマイル。<br>
> **直感** — β で分布形、ν で曲率、ρ で傾き。閉形式で速い。<br>
> **実務** — 金利(スワプション)スマイルの市場標準。気配補間に日常的に使われる。

> **実務での出番 — なぜ市場は SABR で気配を出すか**
>
> スワプションやキャップのブローカー画面は、各行使価格の価格でなく SABR パラメータ(α,β,ρ,ν)で気配が回る。Hagan の閉形式 IV 公式が一瞬でスマイル全体を返すため、少数のパラメータで面を補間・無裁定チェックできるからだ。トレーダーは『この通貨の ρ が下がった』のように、パラメータ自体を相場観の言葉として使う。""")
)

cells.append(
    code(r"""# SABR スマイル: vol-of-vol ν で曲率（スライダー）
pv.plotly_sabr_smile().show()

# 極限/ATM の健全性
flat = [round(float(sabr.sabr_implied_vol(100, K, 1.0, 0.3, 1.0, 0.0, 1e-8)), 4) for K in (80, 100, 120)]
print("β=1, ν→0 はフラット ≈ α=0.3:", flat)
atm = sabr.sabr_implied_vol(100, 100, 1.0, 0.3, 1.0, -0.3, 0.4)
near = sabr.sabr_implied_vol(100, 100.0001, 1.0, 0.3, 1.0, -0.3, 0.4)
print(f"ATM 連続性: atm={atm:.6f} ≈ near={near:.6f}")""")
)

# 7. teaser
cells.append(
    md(r"""## 7. この先

- **rough volatility**: ボラの対数が粗い（Hurst $H\!\approx\!0.1$）分数ブラウン運動で駆動。
  短満期 ATM スキューの $T^{H-1/2}$ 挙動を説明（Gatheral-Jaisson-Rosenbaum 2018）。
- **分散スワップ**: $\mathbb E^Q[\int_0^T v_t\,dt]$ は OTM オプション帯の積分で複製（モデル非依存）。
- **キャリブレーション**: 市場スマイルへ $(\,v_0,\kappa,\theta,\xi,\rho)$ を最小二乗フィット（A3 の数値最適化）。""")
)
cells.append(
    md(r"""> **核心** — 確率ボラ＋ジャンプ、ラフ・ボラなど発展がある。<br>
> **直感** — 短期スキューの急峻さはジャンプ/ラフネスで説明できる。<br>
> **実務** — より精緻なスマイル再現への道。研究と実務のフロンティア。""")
)

# validation
cells.append(
    code(r"""# === 検証: 本巻の主張を参照値に対して固定 ===
checks = []
# COS(GBM) == BSM
checks.append(("COS(GBM) == BSM",
               fourier.cos_price(fourier.lognormal_cf(0.05, 1.0, 0.2), 100, 100, 0.05, 1.0),
               bsm.call_price(100, 100, 0.05, 0.2, 1.0), 1e-3))
# density integrates to 1
yv, fv = fourier.cos_density(cf, N=256, L=12.0, n_grid=4000)
checks.append(("Heston 密度 ∫=1", float(np.trapezoid(fv, yv)), 1.0, 1e-3))
# Heston COS within a few SE of MC
pc = fourier.cos_price(cf, 100, 100, 0.05, 1.0)
pm, sm = heston.heston_mc_price(100, 100, 0.05, 1.0, v0, kappa, theta, xi, rho,
                                n_steps=200, n_paths=200_000, rng=np.random.default_rng(1))
checks.append(("Heston COS ≈ MC", pc, pm, 4 * sm + 0.03))
# SABR flat limit
checks.append(("SABR β=1,ν→0 == α", sabr.sabr_implied_vol(100, 110, 1.0, 0.3, 1.0, 0.0, 1e-8), 0.3, 1e-4))
for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.4f} want={want:.4f} (tol={tol:.3g})")
    assert ok, name
print("\n全チェック合格")""")
)

# exercises
cells.append(
    md(r"""## 練習問題

**Q1.** Heston で $\rho=0$ のとき、スマイルのスキュー（傾き）はどうなるか。

<details><summary>解答</summary>

ほぼ対称な「スマイル」（両翼が持ち上がる）になり、スキュー（傾き）は消える。
$\rho$ が傾きを、$\xi$ が曲率を主に支配する。
</details>

**Q2.** COS 法で価格が項数 $N$ に対して**指数的**に収束するのはなぜか。

<details><summary>解答</summary>

密度が（切断区間上で）滑らかなら Fourier-余弦係数が指数的に減衰するため。
裾が重い/不連続だと収束は遅くなり、切断幅 $L$ を広げる必要がある。
</details>

**Q3.** SABR の $\beta$ を 1→0 に変えると ATM ボラの**水準**はなぜ変わるか。

<details><summary>解答</summary>

ATM $\approx \alpha/F^{1-\beta}$。$\beta$ を下げると $F^{1-\beta}$ が増え、同じ $\alpha$ でも
ログノーマル換算の ATM ボラが下がる（$\alpha$ は $F^\beta$ 単位の拡散係数のため）。
</details>""")
)

# summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 | Hull 巻への接続 |
|---|---|---|
| 確率ボラ | ボラ自身が過程 → スマイルを内生的に生成 | vol05（スマイル・推定） |
| Heston | 平均回帰分散 + 相関。Feller $2\kappa\theta\ge\xi^2$ | vol05 |
| 特性関数 | little-trap 形で安定。密度・価格を Fourier 反転 | — |
| COS 法 | 余弦級数で指数収束。閉形式なしでも高速高精度 | vol06（数値手法） |
| Heston smile | ρ=スキュー、ξ=曲率、κθ=期間構造 | vol05 |
| SABR | Hagan 近似。市場標準の補間。β=バックボーン | vol05・vol11（金利） |

**次巻**: A3 高度な数値（分散減少・準モンテカルロ・LSM・有限差分・AAD）。
**シリーズ**: `johnhull/ROADMAP.md`""")
)

# ===========================================================================
nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12.0"},
    },
    "cells": cells,
}

for idx, cell in enumerate(nb["cells"]):
    cell["id"] = f"cell-{idx:03d}"
    src = cell["source"]
    if isinstance(src, list) and len(src) > 1:
        for k in range(len(src) - 1):
            if not src[k].endswith("\n"):
                src[k] += "\n"
        if src[-1].endswith("\n"):
            src[-1] = src[-1].rstrip("\n")

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stoch_vol_fourier.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
