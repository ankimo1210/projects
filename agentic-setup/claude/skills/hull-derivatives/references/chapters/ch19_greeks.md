# Ch.19 The Greek Letters

> **Source**: Hull 11e, Chapter 19 (pp. 417-450). Paraphrased summary for personal use.

## 1. 要点

- 各ギリシャ文字はオプション価格の異なるリスク次元を定量化する。デルタは原資産価格への感応度、ガンマはデルタの曲率、ベガはボラティリティへの感応度、シータは時間経過による減価、ローは金利への感応度。
- **デルタヘッジ**は最も基本的なヘッジ手法であり、ポートフォリオのデルタをゼロに保つ（デルタニュートラル）ことで小さな価格変動を無力化するが、継続的なリバランス（動的ヘッジ）が必要。
- ガンマが大きいほどデルタ近似の誤差が拡大するため、**ガンマニュートラル化**（取引済みオプションによるデルタ＋ガンマ同時ヘッジ）によって曲率リスクを管理する。
- デルタニュートラルポートフォリオでは $\Theta + \tfrac{1}{2}\sigma^2 S^2 \Gamma = r\Pi$ が成立し、シータとガンマは互いにトレードオフの関係にある。
- 連続配当利回り $q$ を一般化パラメータとして用いると、株価指数・通貨・先物のギリシャ文字を統一的に記述できる（Table 19.6）。
- **ポートフォリオ保険**（合成プットオプション）は動的デルタヘッジの裏面であり、ポートフォリオ価値の低下に応じて株式比率を下げ続ける戦略だが、1987年クラッシュのように市場の流動性が枯渇すると機能しない。

## 2. キー用語

- **Delta (Δ)**: オプション価格の原資産価格に対する偏微分 $\partial f/\partial S$。
- **Delta neutral**: ポートフォリオのデルタが 0 の状態。小さな $\Delta S$ に対してポートフォリオ価値が不変。
- **Static hedging**: 初期にヘッジを設定し以後調整しない（"hedge-and-forget"）。
- **Dynamic hedging**: デルタが変化するたびに継続的にリバランスするヘッジ。
- **Gamma (Γ)**: デルタの原資産価格に対する偏微分 $\partial^2\Pi/\partial S^2$。オプション価格曲線の曲率。
- **Gamma scalping**: ガンマポジティブのポートフォリオが大きな $|\Delta S|$ で利益を得る現象。
- **Theta (Θ)**: 時間経過に対するポートフォリオ価値の変化率 $\partial\Pi/\partial t$（時間減価）。
- **Vega (V)**: ボラティリティに対するオプション価格の変化率 $\partial f/\partial\sigma$。ギリシャ文字ではないが慣用的に「ギリシャ文字」と呼ばれる。
- **Rho (ρ)**: 金利 $r$ に対する変化率 $\partial f/\partial r$。
- **Vanna**: $\partial\Delta/\partial\sigma = \partial^2 f/(\partial S\,\partial\sigma)$（デルタのボラティリティ感応度）。
- **Charm**: $\partial\Delta/\partial t$（デルタの時間感応度）。
- **Vomma / Volga**: $\partial^2 f/\partial\sigma^2$（ベガのボラティリティ感応度）。
- **Color**: $\partial\Gamma/\partial t$（ガンマの時間感応度）。
- **Portfolio insurance**: 合成プットオプションによる株式ポートフォリオの下落保護。
- **Stop-loss strategy**: 株価が $K$ を上回ったらカバードポジション、下回ったらネイキッドポジションに切り替える素朴な戦略。有効なヘッジにはならない（Table 19.1）。
- **Practitioner BSM model**: ボラティリティをインプライドボラティリティに固定してギリシャ文字を計算するアプローチ。

## 3. 主要公式

### $d_1$, $d_2$（連続配当利回り $q$ を含む一般形）

$$
d_1 = \frac{\ln(S/K) + (r - q + \tfrac{1}{2}\sigma^2)T}{\sigma\sqrt{T}}, \qquad d_2 = d_1 - \sigma\sqrt{T}
$$

<!-- Hull eq. (17.4)-(17.5), referenced in §19.12 -->

---

### Delta

$$
\Delta_c = e^{-qT} N(d_1)
\qquad \text{(call)}
$$

$$
\Delta_p = e^{-qT}\bigl(N(d_1) - 1\bigr)
\qquad \text{(put)}
$$

<!-- Hull Table 19.6; non-dividend case (q=0): Δ(call)=N(d₁), Δ(put)=N(d₁)−1 -->

- $\Delta \in (0,1)$ for calls, $\Delta \in (-1,0)$ for puts.
- Delta of a **long forward contract** on an asset with yield $q$:

$$
\Delta_{\mathrm{fwd}} = e^{-qT}
$$

- Delta of a **futures contract** (non-dividend): $e^{rT}$; with yield $q$: $e^{(r-q)T}$.

**Portfolio delta** (weighted sum):

$$
\Delta_{\Pi} = \sum_{i=1}^{n} w_i \Delta_i
$$

<!-- Hull §19.4 -->

---

### Gamma

$$
\Gamma = \frac{e^{-qT} N'(d_1)}{S\,\sigma\sqrt{T}}
$$

where $N'(x) = \phi(x) = \dfrac{1}{\sqrt{2\pi}} e^{-x^2/2}$ is the standard normal PDF.

<!-- Hull §19.6, Table 19.6 -->

- Gamma is identical for calls and puts (same $d_1$).
- A long option position always has positive gamma.
- Gamma peaks at-the-money and spikes sharply for short-dated options.

To make a delta-neutral portfolio gamma-neutral, add $w_T = -\Gamma/\Gamma_T$ units of a traded option with gamma $\Gamma_T$, then re-adjust the underlying position to restore delta neutrality.

---

### Theta

$$
\Theta_c = -\frac{S e^{-qT} N'(d_1)\,\sigma}{2\sqrt{T}} - r K e^{-rT} N(d_2) + q S e^{-qT} N(d_1)
$$

$$
\Theta_p = -\frac{S e^{-qT} N'(d_1)\,\sigma}{2\sqrt{T}} + r K e^{-rT} N(-d_2) - q S e^{-qT} N(-d_1)
$$

<!-- Hull §19.5, Table 19.6 -->

- Theta is measured **per year**; divide by 365 for per-calendar-day, by 252 for per-trading-day.
- Theta is typically negative: options lose value as time passes.
- Exception: deep in-the-money European puts (or calls on high-yield currencies) can have positive theta.

---

### Vega

$$
\mathcal{V} = S e^{-qT} N'(d_1) \sqrt{T}
$$

<!-- Hull §19.8, Table 19.6 -->

- Vega is identical for calls and puts.
- Quoted **per unit of vol** (e.g., per 1.0); divide by 100 for per-1%-vol sensitivity.
- Vega is always positive for long options; peaks at-the-money.

To make a portfolio vega-neutral: add $-\mathcal{V}/\mathcal{V}_T$ units of a traded option with vega $\mathcal{V}_T$.

To achieve **both** gamma and vega neutrality simultaneously, two traded options are required. Solve the linear system:

$$
w_1 \Gamma_1 + w_2 \Gamma_2 = -\Gamma_{\Pi}, \qquad w_1 \mathcal{V}_1 + w_2 \mathcal{V}_2 = -\mathcal{V}_{\Pi}
$$

then restore delta neutrality via the underlying.

---

### Rho

$$
\rho_c = K T e^{-rT} N(d_2)
\qquad \text{(call)}
$$

$$
\rho_p = -K T e^{-rT} N(-d_2)
\qquad \text{(put)}
$$

<!-- Hull §19.9, Table 19.6 -->

- Rho is positive for calls and negative for puts.
- For **currency options**, there is a second rho with respect to the foreign risk-free rate $r_f$:
  - call: $-T e^{-r_f T} S N(d_1)$; put: $+T e^{-r_f T} S N(-d_1)$.

---

### Theta–Delta–Gamma relationship (BSM PDE)

For a portfolio $\Pi$ of derivatives on a non-dividend-paying stock:

$$
\Theta + r S \Delta + \tfrac{1}{2}\sigma^2 S^2 \Gamma = r\Pi
$$

<!-- Hull eq. (19.4) -->

For a **delta-neutral** portfolio ($\Delta = 0$):

$$
\Theta + \tfrac{1}{2}\sigma^2 S^2 \Gamma = r\Pi
$$

This shows that high positive theta tends to accompany negative gamma, and vice versa.

---

### Taylor expansion for portfolio P&L

Full expansion (Appendix, Hull eq. 19A.1):

$$
\Delta\Pi = \frac{\partial\Pi}{\partial S}\Delta S + \frac{\partial\Pi}{\partial t}\Delta t + \tfrac{1}{2}\frac{\partial^2\Pi}{\partial S^2}(\Delta S)^2 + \cdots
$$

For a **delta-neutral** portfolio (dropping $\Delta \cdot \Delta S$ term):

$$
\Delta\Pi \approx \Theta\,\Delta t + \tfrac{1}{2}\Gamma(\Delta S)^2
$$

<!-- Hull eq. (19.3) -->

Including vega (Practitioner BSM, §19 Appendix):

$$
\Delta f \approx \Delta\cdot\Delta S + \mathcal{V}\cdot\Delta\sigma_{\mathrm{imp}} + \tfrac{1}{2}\Gamma(\Delta S)^2 + \tfrac{1}{2}\,\mathrm{Vomma}\,(\Delta\sigma)^2 + \mathrm{Vanna}\cdot\Delta S\,\Delta\sigma + \cdots
$$

---

### Higher-order Greeks (mention)

| Name | Definition | Interpretation |
|---|---|---|
| Vanna | $\partial\Delta/\partial\sigma$ | Delta sensitivity to vol; relevant for vol-smile hedging |
| Charm | $\partial\Delta/\partial t$ | Delta time decay; important near expiry |
| Vomma / Volga | $\partial^2 f/\partial\sigma^2$ | Vega convexity; second-order vol risk |
| Color | $\partial\Gamma/\partial t$ | Gamma time decay |

In a vol-smile context, **vanna** ($\partial^2 f/\partial S\,\partial\sigma$) governs how delta shifts when implied vol moves, and **DvegaDvol** (= Vomma) measures second-order exposure to the vol surface.

---

### Futures contract delta adjustment

When using futures for delta hedging instead of the underlying asset:

$$
H_F = e^{-(r-q)T} H_A
$$

<!-- Hull eq. (19.6); for non-dividend stock: H_F = e^{-rT} H_A (eq. 19.5); for currency: q = r_f -->

## 4. アルゴリズム / 手順

### 1. Static delta hedge（初期設定のみ）

1. $\Delta$ を計算する（BSMまたはツリーモデル）。
2. 原資産を $-\Delta$ 単位保有してデルタニュートラルにする。
3. 以後調整しない（"hedge-and-forget"）。
4. 用途：為替フォワード等、デルタが安定している場合。

---

### 2. Dynamic delta hedge（リバランス手順）— Hull §19.4

1. **初期化**: $\Delta_0$ を計算し、$\Delta_0 \times \text{(オプション枚数)}$ 株を購入（または売却）してデルタニュートラルに設定。
2. **各リバランス時点** $t_k$（毎日または毎週）:
   a. 新しい $S_{t_k}$ でギリシャ文字を再計算する。
   b. 必要株数 $= \Delta_{t_k} \times N_{\mathrm{options}}$（現在保有株数との差分を取引）。
   c. 利息コストを累計に加算する。
3. **終了**: オプション満期時に最終精算。総ヘッジコストはBSM価格に近いが、リバランス頻度が低いほど分散が増える。

**パフォーマンス指標** = (ヘッジコストの標準偏差) / (オプションのBSM価格)。デルタヘッジは高頻度ほど改善する（Table 19.4）。

---

### 3. Delta-gamma hedge（線形連立方程式）

目標: $\Delta_\Pi = 0$、$\Gamma_\Pi = 0$ を同時に実現。

1. ポートフォリオの現在の $(\Delta_\Pi, \Gamma_\Pi)$ を計算。
2. 取引済みオプション（ガンマ $\Gamma_T$、デルタ $\Delta_T$）の追加量 $w_T$ を決定:
   $$w_T = -\Gamma_\Pi / \Gamma_T$$
3. 追加後のデルタ変化を補正: 原資産を $-(w_T \Delta_T)$ 単位売買してデルタを 0 に戻す。
4. ガンマニュートラルは瞬間的であり、時間経過とともに再調整が必要。

---

### 4. Delta-vega hedge（線形連立方程式）

目標: $\Delta_\Pi = 0$、$\mathcal{V}_\Pi = 0$ を同時に実現。

1. 取引済みオプション量: $w_T = -\mathcal{V}_\Pi / \mathcal{V}_T$。
2. 原資産でデルタを再調整。
3. ガンマニュートラルが達成されているとは限らない。ガンマとベガを同時にニュートラル化するには**2種類**のオプションが必要:
   $$\begin{pmatrix} \Gamma_1 & \Gamma_2 \\ \mathcal{V}_1 & \mathcal{V}_2 \end{pmatrix} \begin{pmatrix} w_1 \\ w_2 \end{pmatrix} = \begin{pmatrix} -\Gamma_\Pi \\ -\mathcal{V}_\Pi \end{pmatrix}$$
4. 解 $(w_1, w_2)$ を得たら、原資産でデルタを再調整。

---

### 5. Synthetic option creation — ポートフォリオ保険（Hull §19.13）

目標: 株式ポートフォリオ上の合成プットオプションを創出。

1. 合成プットのデルタ $\Delta_p = e^{-qT}[N(d_1) - 1]$ を計算（$S_0$ = ポートフォリオ現在価値、$K$ = 保護水準）。
2. 売却すべきポートフォリオ比率: $e^{-qT}[1 - N(d_1)]$。
3. 売却代金をリスクフリー資産に投資。
4. ポートフォリオ価値が下落 → $\Delta_p$ がより負になる → さらに株式を売却してリスクフリー資産へ。
5. ポートフォリオ価値が上昇 → $\Delta_p$ が 0 に近づく → 株式を買い戻す。
6. **先物を使う場合**: 必要先物ショート枚数 $= e^{q(T^*-T)} e^{-rT^*}[1 - N(d_1)] \times A_1/A_2$。
7. 注意: 市場が急落すると流動性が枯渇してリバランスが不可能になる（1987年クラッシュの教訓）。

## 5. Python reference

```python
import math
import numpy as np
from scipy.stats import norm


def _d1d2(S, K, r, q, sigma, T):
    """Compute d1 and d2 for BSM with continuous dividend yield q."""
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def bs_price(S, K, r, q, sigma, T, kind='call'):
    """Black-Scholes-Merton price with continuous yield q."""
    d1, d2 = _d1d2(S, K, r, q, sigma, T)
    if kind == 'call':
        return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)


def delta(S, K, r, q, sigma, T, kind='call'):
    """Delta: dV/dS."""
    d1, _ = _d1d2(S, K, r, q, sigma, T)
    if kind == 'call':
        return math.exp(-q * T) * norm.cdf(d1)
    return math.exp(-q * T) * (norm.cdf(d1) - 1.0)


def gamma(S, K, r, q, sigma, T):
    """Gamma: d²V/dS² — same for calls and puts."""
    d1, _ = _d1d2(S, K, r, q, sigma, T)
    return math.exp(-q * T) * norm.pdf(d1) / (S * sigma * math.sqrt(T))


def vega(S, K, r, q, sigma, T):
    """Vega: dV/dsigma — per 1.0 vol unit. Divide by 100 for per-1%-vol."""
    d1, _ = _d1d2(S, K, r, q, sigma, T)
    return S * math.exp(-q * T) * norm.pdf(d1) * math.sqrt(T)


def theta(S, K, r, q, sigma, T, kind='call'):
    """Theta: dV/dt — per year. Divide by 365 for per-calendar-day."""
    d1, d2 = _d1d2(S, K, r, q, sigma, T)
    term1 = -S * math.exp(-q * T) * norm.pdf(d1) * sigma / (2 * math.sqrt(T))
    if kind == 'call':
        term2 = -r * K * math.exp(-r * T) * norm.cdf(d2) + q * S * math.exp(-q * T) * norm.cdf(d1)
    else:
        term2 = r * K * math.exp(-r * T) * norm.cdf(-d2) - q * S * math.exp(-q * T) * norm.cdf(-d1)
    return term1 + term2


def rho(S, K, r, q, sigma, T, kind='call'):
    """Rho: dV/dr."""
    _, d2 = _d1d2(S, K, r, q, sigma, T)
    if kind == 'call':
        return K * T * math.exp(-r * T) * norm.cdf(d2)
    return -K * T * math.exp(-r * T) * norm.cdf(-d2)


def vanna(S, K, r, q, sigma, T):
    """Vanna: d²V/(dS dsigma) = dDelta/dsigma."""
    d1, d2 = _d1d2(S, K, r, q, sigma, T)
    return -math.exp(-q * T) * norm.pdf(d1) * d2 / sigma


def vomma(S, K, r, q, sigma, T):
    """Vomma/Volga: d²V/dsigma² — second-order vol risk."""
    d1, d2 = _d1d2(S, K, r, q, sigma, T)
    return vega(S, K, r, q, sigma, T) * d1 * d2 / sigma


def portfolio_greeks(positions):
    """
    Sum Greeks across a portfolio.
    positions: list of dicts with keys 'quantity' and 'greeks' dict.
    Returns aggregated greeks dict.
    """
    total = {}
    for pos in positions:
        for key, val in pos['greeks'].items():
            total[key] = total.get(key, 0.0) + pos['quantity'] * val
    return total


def delta_gamma_hedge(port_delta, port_gamma, opt_delta, opt_gamma):
    """
    Compute option quantity w and underlying adjustment h to achieve
    delta-gamma neutrality.
      w  = -port_gamma / opt_gamma
      h  = -(port_delta + w * opt_delta)   (units of underlying to buy)
    """
    w = -port_gamma / opt_gamma
    h = -(port_delta + w * opt_delta)
    return w, h


def delta_vega_gamma_hedge(port_delta, port_gamma, port_vega,
                           g1, v1, d1_opt, g2, v2, d2_opt):
    """
    Two-option hedge for simultaneous gamma and vega neutrality.
    Solves: [[g1,g2],[v1,v2]] @ [w1,w2] = [-port_gamma, -port_vega]
    Then adjusts underlying to restore delta neutrality.
    """
    A = np.array([[g1, g2], [v1, v2]])
    b = np.array([-port_gamma, -port_vega])
    w1, w2 = np.linalg.solve(A, b)
    h = -(port_delta + w1 * d1_opt + w2 * d2_opt)
    return w1, w2, h


# --- Example: ATM 1Y call with continuous dividend yield ---
S, K, r, q, sigma, T = 100, 100, 0.05, 0.02, 0.20, 1.0
print(f"price = {bs_price(S, K, r, q, sigma, T):.4f}")
print(f"Δ     = {delta(S, K, r, q, sigma, T):.4f}  "
      f"Γ = {gamma(S, K, r, q, sigma, T):.4f}")
print(f"V     = {vega(S, K, r, q, sigma, T):.4f}  "
      f"Θ = {theta(S, K, r, q, sigma, T):.4f}  "
      f"ρ = {rho(S, K, r, q, sigma, T):.4f}")
print(f"vanna = {vanna(S, K, r, q, sigma, T):.4f}  "
      f"vomma = {vomma(S, K, r, q, sigma, T):.4f}")

# Verify BSM Theta–Gamma identity (delta-neutral approximation)
# For a single option: Θ + r*S*Δ + 0.5*σ²*S²*Γ ≈ r * price
price = bs_price(S, K, r, q, sigma, T)
lhs = (theta(S, K, r, q, sigma, T)
       + r * S * delta(S, K, r, q, sigma, T)
       + 0.5 * sigma**2 * S**2 * gamma(S, K, r, q, sigma, T))
print(f"\nBSM PDE check: LHS={lhs:.4f}  r*price={r * price:.4f}  diff={abs(lhs - r*price):.2e}")
```

## 6. 注意点 / 典型的なミス

- **Vega はギリシャ文字ではない**: Vega はギリシャアルファベットに存在しない。kappa（κ）や lambda（λ）と呼ばれることもあるが、業界標準は "Vega"。混乱を避けるため記号は $\mathcal{V}$ または $\nu$ で表記することが多い。
- **シータのスケール変換を忘れる**: BSM式のシータは「年率」。「1日あたり」に換算するには÷365（カレンダー日）または÷252（取引日）が必要。報告書やツールによって単位が異なるため、常に確認する。
- **ベガのスケール変換を忘れる**: `vega()` の戻り値は「ボラティリティ1.0（= 100%）あたり」の変化量。「1%あたり」に換算するには÷100。
- **ストップロス戦略の誤解**: 一見合理的に見えるが、株価が $K$ 付近を頻繁に行き来するほどコストが増大し、有効なヘッジにならない（Table 19.1 参照）。
- **ガンマニュートラルの誤解**: ガンマは瞬間的にのみ 0 にできる。時間が経てば再調整が必要。
- **BSM前提とベガリスク**: BSM モデルはボラティリティ一定を前提とするため、ベガの計算はモデルの仮定が成立しないことへのリスクを測っている。真のボラティリティリスクにはボラティリティ曲面全体の変化を考慮する必要がある（Ch.20）。
- **離散リバランスのP&L分散**: 連続ヘッジならヘッジコストはBSM価格と一致するが、現実は離散リバランスのためコストにばらつきが生じる（高頻度ほど減少）。この分散はガンマスカルピングの利益/損失と等価。
- **デルタとガンマの同時中立化**: 原資産（デルタ=1, ガンマ=0）では gamma を変えられない。ガンマ中立化には必ず他のオプション（非線形商品）が必要。
- **先物デルタと現物デルタの相違**: 先物のデルタは $e^{rT}$（または $e^{(r-q)T}$）であり、現物の1.0 とは異なる。先物でヘッジする場合は $H_F = e^{-(r-q)T} H_A$ で換算する。

## 7. 関連トピック

- 参照: [topics/greeks.md](../topics/greeks.md), [topics/bsm.md](../topics/bsm.md)
- **Ch.15** (BSM モデル): $d_1, d_2$ の定義と基本式、ギリシャ文字の導出基礎。
- **Ch.17** (株価指数・通貨オプション): 連続配当利回り $q$ の一般化。Table 19.6 の出発点。
- **Ch.18** (先物オプション): $q = r$ とすると先物オプションのギリシャ文字が得られる。
- **Ch.20** (ボラティリティスマイル): スティッキー・デルタ解釈、スマイル下でのデルタ修正、ボラティリティ曲面変化への Vanna/Vomma の応用。
- **Ch.21** (数値手法): アメリカンオプションのギリシャ文字計算（有限差分・ツリー法）。
- **Ch.27** (数値ギリシャ文字): PDE・モンテカルロによる数値微分。Bumped-delta, pathwise, likelihood-ratio 法。
