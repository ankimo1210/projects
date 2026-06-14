"""
build_stochastic_calculus_notebook.py
=====================================
nbformat-dict pattern to generate stochastic_calculus.ipynb
(A1 deep-dive — graduate stochastic calculus behind Hull's pricing).

Plotly figures (``fig.show()``) instead of ipympl, so they render in the
static Jupyter Book HTML. Numerical-verification cells assert against closed
forms. References: Shreve, *Stochastic Calculus for Finance II*; Øksendal, *SDEs*.

Usage:
    uv run python build_stochastic_calculus_notebook.py
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
# Title
# ===========================================================================
cells.append(
    md(r"""# 確率解析 — 伊藤積分から Girsanov・Feynman-Kac へ（A1 深掘り）

`johnhull` 深掘りシリーズ第1巻。Hull が**道具として**使う確率解析を、
Shreve II / Øksendal の水準で基礎から組み立て直します。各節は
**図 → 直感 → 定理・導出 → コード検証** の順。図はすべて `hullkit` の
価格付け・確率関数をラップした `plotly_*` ビルダー、または同じ関数を使った
インライン plotly で、本文の数式と一致します。

| 節 | 内容 | 主参照 |
|---|---|---|
| 1 | ブラウン運動と二次変分 $[W]_t=t$ | Shreve II §3.2–3.4 |
| 2 | 伊藤積分の構成・伊藤等長・$\int W\,dW$ | Shreve II §4.2–4.3 |
| 3 | 伊藤の補題 | Shreve II §4.4 |
| 4 | SDE の存在一意・GBM・Euler–Maruyama | Øksendal §5.2；Kloeden–Platen |
| 5 | Girsanov（測度変換）→ リスク中立評価 | Shreve II §5.2–5.4 |
| 6 | Feynman–Kac：PDE ↔ 割引期待値 | Shreve II §6.4 |
| 7 | マルチンゲール表現と完備性 | Shreve II §5.3 |

> Hull 該当章: Ch.14（ウィーナー過程・伊藤の補題）。本巻はその先の厳密化。""")
)
cells.append(
    md(r"""> **核心** — 確率解析は『複製・測度変換・PDE 化』を厳密に支える言語。BSM の足場を組み直す。<br>
> **直感** — ブラウン運動の二次変分が消えない(=½σ² 項)ことが、決定論的微積との分かれ目。<br>
> **実務** — クオンツが新商品のモデルを導出・検証する共通言語。Girsanov と Feynman-Kac が実→Q と期待値↔PDE を繋ぐ。""")
)

# imports
cells.append(
    code(r"""# --- imports ---
import numpy as np
import plotly.graph_objects as go

from hullkit import bsm, fd, mc, sde
from hullkit import plotly_viz as pv

rng = np.random.default_rng(0)
np.set_printoptions(precision=4, suppress=True)""")
)

cells.append(
    md(r"""### 記号と単位

- $S$=原資産価格・$K$=ストライク(同一通貨単位)、$r$=無リスク金利(**連続複利・年率**)、$\sigma$=ボラティリティ(**年率**)、$T,t$=時間(**年**)。
- $W_t$=標準ブラウン運動、$[W]_t$=二次変分、$\mu$=実世界ドリフト(年率)、$\lambda=(\mu-r)/\sigma$=市場価格リスク、$Q$=リスク中立測度・$P$=実世界測度。
- コードの `S0,K,r,sigma,T,mu` は上記に対応(例: `r=0.05`→年率5%、`sigma=0.2`→年率20%、`T=1.0`→1年)。""")
)

# ===========================================================================
# 1. Brownian motion & quadratic variation
# ===========================================================================
cells.append(
    md(r"""## 1. ブラウン運動と二次変分

**定義（Shreve II §3.3）.** 標準ブラウン運動 $W=\{W_t\}_{t\ge 0}$ は
(i) $W_0=0$、(ii) 独立増分、(iii) $W_t-W_s\sim N(0,\,t-s)$ $(s<t)$、
(iv) 標本路が連続、を満たす確率過程。標本路は確率1で**いたるところ微分不可能**。

そのため通常の $\int f\,dW$ は各点では定義できず、$L^2$ の意味で構成する必要があります（§2）。
鍵となるのが**二次変分**です。

**定理（Shreve II §3.4）.** 区間 $[0,T]$ の分割 $\Pi=\{0=t_0<\dots<t_n=T\}$ に対し
$$[W]_T \;=\; \lim_{\|\Pi\|\to 0}\sum_{i} (W_{t_{i+1}}-W_{t_i})^2 \;=\; T \quad (\text{a.s.}).$$

**証明の骨子.** $Q_\Pi=\sum_i(\Delta W_i)^2$ とおくと $\mathbb E[Q_\Pi]=\sum_i\Delta t_i=T$、
$\operatorname{Var}(Q_\Pi)=\sum_i 2(\Delta t_i)^2\le 2\|\Pi\|\,T\to0$。
よって $Q_\Pi\to T$（$L^2$、したがって確率収束）。一様分割では $\operatorname{std}(Q_\Pi)=\sqrt{2/n}$。""")
)
cells.append(
    md(r"""> **核心** — [W]_t = t。ランダムな揺れの『二乗の累積』は確定的に t になる。<br>
> **直感** — 増分は独立で分散が時間に比例。だから (ΔW)² を足し上げると t に収束する。<br>
> **実務** — この一点が伊藤の補題の ½σ² 項の源。あらゆる価格 PDE の出発点。""")
)

cells.append(
    code(r"""# ブラウン運動の標本路（8本）
W = sde.brownian_paths(1.0, 500, 8, rng=np.random.default_rng(0))
tg = np.linspace(0.0, 1.0, 501)
figbm = go.Figure()
for k in range(W.shape[0]):
    figbm.add_trace(go.Scatter(x=tg, y=W[k], mode="lines", line={"width": 1}, showlegend=False))
figbm.update_layout(
    title="ブラウン運動の標本路（連続だが微分不可能）", xaxis_title="t", yaxis_title="W_t"
)
figbm.show()""")
)

cells.append(
    code(r"""# 二次変分 [W]_t → t（帯=±std, 分割を細かくすると y=t へ収縮）
pv.plotly_quadratic_variation().show()

# 数値確認: E[QV]≈T, std[QV]≈sqrt(2/n)
for n in (16, 256, 1024):
    qv = sde.quadratic_variation(sde.brownian_paths(1.0, n, 5000, rng=np.random.default_rng(7)))
    print(f"n={n:5d}  E[QV]={qv.mean():.4f}  std={qv.std():.4f}  (理論 sqrt(2/n)={np.sqrt(2/n):.4f})")""")
)

# ===========================================================================
# 2. Itô integral
# ===========================================================================
cells.append(
    md(r"""## 2. 伊藤積分と伊藤等長

可測な適合過程 $\Delta$ に対し、まず**単純過程**（区分定数）で
$I(\Delta)_T=\sum_i \Delta_{t_i}\,(W_{t_{i+1}}-W_{t_i})$ と定義します。**左端点** $\Delta_{t_i}$ で
評価するのが本質的で、これにより $I_t$ は**マルチンゲール**になります（$\mathbb E[\Delta_{t_i}\Delta W_i\mid\mathcal F_{t_i}]=0$）。

**伊藤等長（Itô isometry, Shreve II §4.2）.**
$$\mathbb E\!\left[\Big(\int_0^T \Delta_t\,dW_t\Big)^2\right] \;=\; \mathbb E\!\left[\int_0^T \Delta_t^2\,dt\right].$$
これは増分の独立性と $\mathbb E[(\Delta W_i)^2]=\Delta t_i$ から従い、単純過程で示したのち
$L^2$ の等長性で一般の $\Delta\in L^2$ へ拡張します（クロス項は左端点ゆえ期待値0）。

特に $\Delta_t=W_t$ のとき
$\mathbb E\big[(\int_0^T W\,dW)^2\big]=\int_0^T \mathbb E[W_t^2]\,dt=\int_0^T t\,dt=T^2/2$、
かつマルチンゲール性から $\mathbb E[\int_0^T W\,dW]=0$。""")
)
cells.append(
    md(r"""> **核心** — 確率積分は『左端点』で評価する(非予見的)。伊藤等長 E[(∫H dW)²]=E[∫H² dt]。<br>
> **直感** — 未来を見ずに今の情報で賭ける → マルチンゲール。等長は分散計算の道具。<br>
> **実務** — ヘッジ損益・複製誤差の分散評価、MC の収束解析の基礎。""")
)

cells.append(
    code(r"""# 伊藤積分のマルチンゲール性と伊藤等長を数値確認 (T=1)
W = sde.brownian_paths(1.0, 1000, 200_000, rng=np.random.default_rng(2))
I = sde.ito_riemann_sum(W, alpha=0.0)          # ∫_0^T W dW （左端点 = 伊藤）
print(f"E[I]   = {I.mean(): .4f}   (マルチンゲール → 0)")
print(f"E[I^2] = {(I**2).mean():.4f}   (伊藤等長 → ∫_0^T t dt = T^2/2 = 0.5)")""")
)

cells.append(
    md(r"""### $\int_0^T W\,dW$ と伊藤 vs Stratonovich

左端点和は**伸縮（telescoping）**で厳密に評価できます。$\sum_i W_{t_i}\Delta W_i
=\tfrac12\big(W_T^2-\sum_i(\Delta W_i)^2\big)=\tfrac12\big(W_T^2-[W]_T\big)$ なので
$$\int_0^T W\,dW \;=\; \tfrac12 W_T^2 - \tfrac12 T \qquad(\text{伊藤}).$$
通常の微積分の $\tfrac12 W_T^2$ と比べた **$-\tfrac12 T$ が伊藤補正**です。
一方、中点評価（Stratonovich）は $\sum_i \tfrac12(W_{t_i}+W_{t_{i+1}})\Delta W_i=\tfrac12 W_T^2$ と
**厳密に**なり、補正は現れません。両者の差はちょうど $\tfrac12[W]_T\to\tfrac12 T$。""")
)

cells.append(
    code(r"""# 伊藤補正 = (中点和 − 左点和) = ½[W]_t → ½T （n↑ で集中）
pv.plotly_ito_correction().show()

# telescoping 恒等式は乱数に依らず厳密に成立
W = sde.brownian_paths(1.0, 400, 3000, rng=np.random.default_rng(3))
left = sde.ito_riemann_sum(W, alpha=0.0)
mid = sde.ito_riemann_sum(W, alpha=0.5)
qv = sde.quadratic_variation(W)
assert np.allclose(left, 0.5 * (W[:, -1] ** 2 - qv))   # 伊藤  ≡ ½(W_T² − [W]_T)
assert np.allclose(mid, 0.5 * W[:, -1] ** 2)            # Strat ≡ ½W_T²
print("telescoping 恒等式 OK   E[mid−left] =", float((mid - left).mean()), "≈ ½T = 0.5")""")
)

# ===========================================================================
# 3. Itô's lemma
# ===========================================================================
cells.append(
    md(r"""## 3. 伊藤の補題

**定理（Shreve II §4.4）.** $dX_t=\mu_t\,dt+\sigma_t\,dW_t$、$f\in C^{1,2}$ のとき
$$df(t,X_t)=\Big(f_t+\mu_t f_x+\tfrac12\sigma_t^2 f_{xx}\Big)dt+\sigma_t f_x\,dW_t.$$
**直感.** テイラー展開で $(dX)^2=\sigma^2(dW)^2$ が現れ、$(dW)^2\to dt$（二次変分）のため
通常の連鎖律に **$\tfrac12\sigma^2 f_{xx}\,dt$** が追加されます。

**応用（GBM）.** $dS=\mu S\,dt+\sigma S\,dW$ に $f=\ln S$ を当てると
$f_x=1/S,\,f_{xx}=-1/S^2$ より
$$d\ln S=\Big(\mu-\tfrac12\sigma^2\Big)dt+\sigma\,dW
\;\Rightarrow\; \ln S_T\sim N\!\Big(\ln S_0+(\mu-\tfrac12\sigma^2)T,\ \sigma^2 T\Big).$$
ドリフトが $\mu$ ではなく $\mu-\tfrac12\sigma^2$ になるのが要点（Hull §14.7）。""")
)
cells.append(
    md(r"""> **核心** — dG=(G_t+aG_x+½b²G_xx)dt+bG_x dW。普通の連鎖律＋½b²G_xx の補正。<br>
> **直感** — 二次変分が消えないので2次項が生き残る。これが確率版の連鎖律。<br>
> **実務** — 新しいペイオフ/モデルの SDE 導出の主力。BSM 偏微分方程式もこれ1本から出る。""")
)

cells.append(
    code(r"""# d(ln S) のドリフトが μ−σ²/2 になることを GBM サンプルで確認
S0, mu, sigma, T = 100.0, 0.12, 0.25, 1.0  # S0=100, μ=12%/年, σ=25%/年, T=1年
paths = mc.simulate_gbm_paths(S0, mu, sigma, T, 1, 200_000, rng=np.random.default_rng(1))
logret = np.log(paths[:, -1] / S0)
print(f"E[ln(S_T/S0)]: sim={logret.mean(): .4f}  理論 (μ−σ²/2)T={(mu - 0.5 * sigma**2) * T: .4f}")
print(f"Var[ln(S_T/S0)]: sim={logret.var(): .4f}  理論 σ²T={sigma**2 * T: .4f}")
assert abs(logret.mean() - (mu - 0.5 * sigma**2) * T) < 5e-3""")
)

# ===========================================================================
# 4. SDEs, GBM, Euler-Maruyama
# ===========================================================================
cells.append(
    md(r"""## 4. 確率微分方程式と数値解法

**存在一意（Øksendal Thm 5.2.1）.** $dX_t=b(t,X_t)\,dt+\sigma(t,X_t)\,dW_t,\ X_0=x$ について
$b,\sigma$ が**リプシッツ連続**かつ**線形増大**なら、強解が一意に存在。

**GBM の閉形式.** 伊藤の補題（§3）から $S_t=S_0\exp\!\big((\mu-\tfrac12\sigma^2)t+\sigma W_t\big)$。

**Euler–Maruyama.** $X_{k+1}=X_k+b\,\Delta t+\sigma\,\Delta W_k$。
**強収束**位数 $1/2$（経路ごとの $L^2$ 誤差 $\sim\sqrt{\Delta t}$）、**弱収束**位数 $1$
（モーメント誤差 $\sim\Delta t$）。拡散が状態依存だと Milstein で強位数1に上げられる（A3 で扱う）。""")
)
cells.append(
    md(r"""> **核心** — Euler–丸山と対数オイラー。離散化には強収束・弱収束の概念がある。<br>
> **直感** — ナイーブな離散化は誤差が蓄積。GBM は対数で厳密にシミュできる。<br>
> **実務** — MC エンジンの心臓部。離散化スキームの選択が価格バイアスを左右する。""")
)

cells.append(
    code(r"""# Euler–Maruyama を GBM に適用し、終端モーメントが厳密 GBM に一致するか確認
S0, mu, sigma, T = 100.0, 0.10, 0.20, 1.0
em = sde.euler_maruyama(
    lambda x, t: mu * x, lambda x, t: sigma * x, S0, T, 300, 100_000, rng=np.random.default_rng(3)
)
e_st, var_st = mc.gbm_theory(S0, mu, sigma, T)
print(f"E[S_T]:  EM={em[:, -1].mean():.3f}  理論 S0·e^(μT)={e_st:.3f}")
assert abs(em[:, -1].mean() - e_st) / e_st < 0.01   # 弱位数1

# 終端分布 vs 理論対数正規（インライン plotly）
st = em[:, -1]
edges = np.linspace(st.min(), st.max(), 60)
ctr = 0.5 * (edges[:-1] + edges[1:])
m_log, s_log = np.log(S0) + (mu - 0.5 * sigma**2) * T, sigma * np.sqrt(T)
pdf = np.exp(-((np.log(ctr) - m_log) ** 2) / (2 * s_log**2)) / (ctr * s_log * np.sqrt(2 * np.pi))
dens, _ = np.histogram(st, bins=edges, density=True)
figem = go.Figure()
figem.add_trace(go.Bar(x=ctr, y=dens, name="EM 終端 S_T", marker={"color": "#c7c7c7"}))
figem.add_trace(go.Scatter(x=ctr, y=pdf, mode="lines", name="理論 対数正規", line={"color": "#d62728"}))
figem.update_layout(title="Euler–Maruyama 終端分布 vs 対数正規", xaxis_title="S_T", yaxis_title="密度")
figem.show()""")
)

# ===========================================================================
# 5. Girsanov
# ===========================================================================
cells.append(
    md(r"""## 5. Girsanov の定理 — 測度変換とリスク中立評価

実世界 $P$ で $dS=\mu S\,dt+\sigma S\,dW^P$。**市場価格リスク** $\lambda=(\mu-r)/\sigma$ を用いて
$$\left.\frac{dQ}{dP}\right|_T=\exp\!\Big(-\lambda W^P_T-\tfrac12\lambda^2 T\Big),\qquad
W^Q_t=W^P_t+\lambda t.$$
**Girsanov（Shreve II §5.2–5.4）** により $W^Q$ は $Q$ のもとでブラウン運動で、$S$ のドリフトは
$\mu\to r$ に変わります。$\mathbb E^P[dQ/dP]=1$ かつ
$\mathbb E^P[\,(dQ/dP)\,g(S_T)\,]=\mathbb E^Q[g(S_T)]$。

**含意.** ドリフト $\mu$（実世界の期待リターン）は価格に現れず、割引期待値
$e^{-rT}\mathbb E^Q[\text{payoff}]$ がBSM価格を与えます。下図は $\mu$ を変えても
再重み付け後の $Q$ 分布と $Q$ コール価格が**不変**であることを示します。""")
)
cells.append(
    md(r"""> **核心** — 測度を変えるとドリフトが変わり、ボラは不変。実→リスク中立の橋。<br>
> **直感** — 確率の重みを付け替えるだけ。揺れ幅(σ)は測度に依らない。<br>
> **実務** — リスク中立評価の正当化そのもの。σ が実測でも Q でも同じ、が成り立つ理由。

> **実務での出番 — Girsanov がリスク中立評価を支える**
>
> オプション価格は『リスク中立測度 Q の下での割引期待値』。だが現実のデータは実世界測度 P で観測される。Girsanov の定理は、P から Q への移行がドリフトだけを変えボラを変えないことを保証する。だからヒストリカルに推定した σ をそのまま Q の価格付けに使える——理論と実データを繋ぐ要石。""")
)

cells.append(
    code(r"""# Girsanov: 実世界ドリフト μ を変えても Q（リスク中立）は不変
pv.plotly_girsanov().show()

# P（ドリフト μ）でサンプリング → dQ/dP で再重み付け → BSM 価格に一致
S0, K, r, sigma, T, muP = 100.0, 100.0, 0.05, 0.20, 1.0, 0.15
s_t = mc.simulate_gbm_paths(S0, muP, sigma, T, 1, 400_000, rng=np.random.default_rng(5))[:, -1]
w = sde.girsanov_weights(s_t, S0, sigma, T, mu_from=muP, mu_to=r)
price = float(np.exp(-r * T) * np.sum(w * np.maximum(s_t - K, 0.0)) / np.sum(w))
print(f"E^P[dQ/dP] = {w.mean():.4f}  (=1)")
print(f"Girsanov 再重み付け価格 = {price:.4f}   BSM = {bsm.call_price(S0, K, r, sigma, T):.4f}")
assert abs(price - bsm.call_price(S0, K, r, sigma, T)) < 0.1""")
)

# ===========================================================================
# 6. Feynman-Kac
# ===========================================================================
cells.append(
    md(r"""## 6. Feynman–Kac — PDE と割引期待値の橋

**定理（Shreve II §6.4）.** $dX=rX\,dt+\sigma X\,dW^Q$（リスク中立）とし、$v(t,x)$ が終端条件
$v(T,x)=h(x)$ のもとで
$$v_t+rx\,v_x+\tfrac12\sigma^2x^2 v_{xx}-r\,v=0$$
を満たすなら、
$$v(t,x)=\mathbb E^Q\!\big[e^{-r(T-t)}h(X_T)\,\big|\,X_t=x\big].$$
これが **BSM の PDE = 割引期待値** である理由。したがって同じコール価格は3通りで一致します：
**閉形式（BSM）= PDE 数値解（有限差分）= モンテカルロ期待値**。""")
)
cells.append(
    md(r"""> **核心** — 割引期待値は放物型 PDE の解。期待値↔PDE は同一物の二つの顔。<br>
> **直感** — 価格を SDE の期待値でも PDE の境界値問題でも書ける。<br>
> **実務** — MC(期待値)と有限差分(PDE)が同じ価格を出す理論的根拠。手法選択の自由。""")
)

cells.append(
    code(r"""# Feynman–Kac の三者一致: 閉形式 == 有限差分(PDE) == モンテカルロ(期待値)
S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0
closed = bsm.call_price(S0, K, r, sigma, T)
pde = fd.fd_vanilla(S0, K, r, sigma, T, method="cn", n_s=300, n_t=300)
mc_price, se = mc.price_european_mc(S0, K, r, sigma, T, n_paths=400_000, rng=np.random.default_rng(6))
print(f"閉形式 BSM      = {closed:.4f}")
print(f"PDE 有限差分(CN) = {pde:.4f}")
print(f"モンテカルロ     = {mc_price:.4f} ± {se:.4f}")
assert abs(pde - closed) < 0.02 and abs(mc_price - closed) < 3 * se

figfk = go.Figure(
    go.Bar(
        x=["閉形式", "PDE(CN)", "MC"], y=[closed, pde, mc_price],
        marker={"color": ["#d62728", "#1f77b4", "#7f7f7f"]},
    )
)
figfk.update_layout(
    title=f"Feynman–Kac: 3手法が一致 (≈{closed:.3f})", yaxis_title="コール価格"
)
figfk.show()""")
)

# ===========================================================================
# 7. Martingale representation & completeness
# ===========================================================================
cells.append(
    md(r"""## 7. マルチンゲール表現と完備性

**マルチンゲール表現定理（Shreve II §5.3）.** ブラウン・フィルトレーション上の任意の
（自乗可積分）マルチンゲール $M_t$ は、ある適合過程 $\Gamma$ により
$M_t=M_0+\int_0^t \Gamma_s\,dW_s$ と表せる。

**含意.** 割引ペイオフのリスク中立期待値 $V_t=\mathbb E^Q[e^{-r(T-t)}h(S_T)\mid\mathcal F_t]$ は
$Q$-マルチンゲール（割引後）であり、上式の $\Gamma$ が**複製ポートフォリオのデルタ**を与えます。
よって BSM の世界は**完備**：すべての請求権が複製可能で、価格は一意。
これが §5 の「割引期待値が価格」を**ヘッジ可能性**から正当化します
（Hull のデルタヘッジ＝この $\Gamma$ の離散近似）。""")
)
cells.append(
    md(r"""> **核心** — 完備市場ではどんなペイオフも自己充足的に複製できる。<br>
> **直感** — マルチンゲール表現定理＝『複製ポートフォリオが必ず存在する』の数学版。<br>
> **実務** — 複製＝ヘッジが可能、という前提の根拠。不完備だと一意価格が消える(確率ボラ等)。""")
)

# ===========================================================================
# Validation
# ===========================================================================
cells.append(
    code(r"""# === 検証: 本巻の主張を参照値に対して固定 ===
checks = []
# QV → T
qv = sde.quadratic_variation(sde.brownian_paths(1.0, 2000, 4000, rng=np.random.default_rng(1)))
checks.append(("二次変分 [W]_T → T", float(qv.mean()), 1.0, 0.02))
# Itô isometry: E[(∫W dW)²]=T²/2
W = sde.brownian_paths(1.0, 1000, 200_000, rng=np.random.default_rng(2))
I = sde.ito_riemann_sum(W, 0.0)
checks.append(("伊藤等長 E[I²]=T²/2", float((I**2).mean()), 0.5, 0.02))
# Girsanov → BSM
s_t = mc.simulate_gbm_paths(100, 0.15, 0.2, 1.0, 1, 400_000, rng=np.random.default_rng(5))[:, -1]
w = sde.girsanov_weights(s_t, 100, 0.2, 1.0, 0.15, 0.05)
gp = float(np.exp(-0.05) * np.sum(w * np.maximum(s_t - 100, 0.0)) / np.sum(w))
checks.append(("Girsanov 再重み付け → BSM", gp, bsm.call_price(100, 100, 0.05, 0.2, 1.0), 0.1))
# Feynman-Kac: PDE == closed form
checks.append((
    "Feynman-Kac PDE == 閉形式",
    fd.fd_vanilla(100, 100, 0.05, 0.2, 1.0, method="cn", n_s=300, n_t=300),
    bsm.call_price(100, 100, 0.05, 0.2, 1.0),
    0.02,
))
for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.4f} want={want:.4f} (tol={tol})")
    assert ok, name
print("\n全チェック合格")""")
)

# ===========================================================================
# Exercises
# ===========================================================================
cells.append(
    md(r"""## 練習問題

**Q1.** $\int_0^T W_t\,dW_t$ の分散を求めよ。

<details><summary>解答</summary>

$\int_0^T W\,dW=\tfrac12(W_T^2-T)$。$W_T\sim N(0,T)$ より $W_T^2/T\sim\chi^2_1$、
$\operatorname{Var}(W_T^2)=2T^2$。よって $\operatorname{Var}=\tfrac14\cdot 2T^2=T^2/2$
（伊藤等長 $\mathbb E[I^2]=T^2/2$ と $\mathbb E[I]=0$ から直接でも同じ）。
</details>

**Q2.** $f(W_t)=e^{W_t}$ に伊藤の補題を適用し、$\mathbb E[e^{W_t}]$ を求めよ。

<details><summary>解答</summary>

$de^{W}=e^{W}dW+\tfrac12 e^{W}dt$。期待値を取ると $dm/dt=\tfrac12 m$、$m_0=1$ なので
$\mathbb E[e^{W_t}]=e^{t/2}$（モーメント母関数 $N(0,t)$ と一致）。
</details>

**Q3.** 実世界ドリフト $\mu$ を 2 倍にすると BSM コール価格はどう変わるか。

<details><summary>解答</summary>

変わらない。Girsanov により価格は $Q$（ドリフト $r$）の割引期待値で決まり、$\mu$ に依存しない。
$\mu$ は $dQ/dP$ の中で相殺される（§5 の図）。
</details>""")
)

# ===========================================================================
# Summary
# ===========================================================================
cells.append(
    md(r"""## まとめ

| 概念 | 要点 | Hull 巻への接続 |
|---|---|---|
| 二次変分 | $[W]_T=T$（std $\sqrt{2/n}$）。$\int dW$ を可能にする核 | vol01・bsm（Ch.14） |
| 伊藤等長 | $\mathbb E[(\int\Delta dW)^2]=\mathbb E[\int\Delta^2 dt]$、左端点でマルチンゲール | — |
| 伊藤の補題 | $(dW)^2=dt$ → $\tfrac12\sigma^2 f_{xx}$ 補正。$d\ln S$ のドリフト $\mu-\tfrac12\sigma^2$ | vol01・bsm |
| Euler–Maruyama | 強位数 $1/2$・弱位数 $1$。GBM は閉形式あり | vol06（数値手法） |
| Girsanov | $\mu\to r$ の測度変換。価格は実ドリフトに依らない | 全巻の価格付け |
| Feynman–Kac | PDE = 割引期待値。閉形式 = FD = MC | vol06・bsm |
| マルチンゲール表現 | $\Gamma$ = 複製デルタ → 完備・一意価格 | vol03（グリークス）・hedging |

**次巻**: A2 確率ボラティリティと Fourier 価格付け（Heston / SABR / COS）。
**シリーズ**: `johnhull/ROADMAP.md`""")
)

# ===========================================================================
# Notebook assembly (deterministic cell ids; same pattern as the Hull volumes)
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

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stochastic_calculus.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
