# Ch.28 Martingales and Measures

> **Source**: Hull 11e, Chapter 28 (pp. 670-687). Paraphrased summary for personal use.

## 1. 要点

- **マーケット・プライス・オブ・リスク** $\lambda$ は、ある確率変数 $\theta$ に依存するすべてのデリバティブに共通して成立する無裁定条件 $(\mu - r)/\sigma = \lambda$ で定義される。
- **マルチンゲール**はドリフトゼロの確率過程であり、将来の期待値が現在値に等しい ($E[\theta_T] = \theta_0$)。
- **同値マルチンゲール測度結果**: トレーダブルな証券 $g$ を分子（ニュメレール）として選ぶと、すべての証券価格 $f$ について $f/g$ がその測度のもとでマルチンゲールになる測度が存在する。
- ニュメレールの選択によって便利な測度が得られる: マネーマーケット口座 → リスク中立測度 $\mathbb{Q}$、ゼロクーポン債 $P(t,T)$ → $T$-フォワード測度 $\mathbb{Q}^T$、アニュイティ → スワップ測度。
- **Black モデル（Black-76）** はフォワード測度の特殊ケースであり、確率的金利下でも $F_0$ をフォワード価格として Black 公式が成立することが正当化される。
- **Girsanov の定理**: 測度変換はドリフトを変えるが拡散係数（ボラティリティ）は保存する。

## 2. キー用語

- **マルチンゲール (Martingale)**: $d\theta = \sigma\,dz$ の形でドリフトがゼロの確率過程。将来期待値が現在値に等しい。
- **測度 (Measure)**: 確率の割り当て方（確率測度）。市場プライス・オブ・リスク $\lambda$ の選択に対応する。
- **市場リスクの価格 (Market Price of Risk)**: $\lambda = (\mu - r)/\sigma$。リスク1単位あたりの超過リターン。シャープ比に相当。
- **同値マルチンゲール測度 (Equivalent Martingale Measure)**: 元の測度と同じゼロ確率集合を持ち、ある分母証券 $g$ に対して $f/g$ がマルチンゲールになる測度。
- **ニュメレール (Numéraire)**: 価格の単位として使われるトレーダブルな証券 $g$。
- **リスク中立測度 $\mathbb{Q}$**: マネーマーケット口座をニュメレールとする測度。$\lambda = 0$ の世界。
- **$T$-フォワード測度 $\mathbb{Q}^T$**: 満期 $T$ のゼロクーポン債 $P(t,T)$ をニュメレールとする測度。
- **スワップ測度 (Swap Measure / Annuity Measure)**: アニュイティファクター $A(t)$ をニュメレールとする測度。スワップション評価に使用。
- **ニュメレール比 (Numeraire Ratio)**: $w = h/g$。測度変換時のドリフト調整に現れる比率。
- **Girsanov の定理**: 測度変換で Wiener 過程のドリフトが変わる（$dz^{\mathbb{Q}} = dz^{\mathbb{P}} + \lambda\,dt$）が、拡散係数は不変。

## 3. 主要公式

### 市場リスクの価格（1 因子）

$$
\frac{\mu - r}{\sigma} = \lambda
\quad \Longleftrightarrow \quad \mu - r = \lambda \sigma
$$

- $\mu$: 証券の期待リターン
- $r$: 瞬間リスクフリーレート
- $\sigma$: 証券のボラティリティ（$dz$ の係数）
- $\lambda$: $\theta$ のリスクの市場価格（$\theta$, $t$ にのみ依存、証券によらない）

<!-- Hull eq. (28.8), (28.9) -->

### 多因子拡張

$$
\mu - r = \sum_{i=1}^{n} \lambda_i \sigma_i
$$

- $\lambda_i$: 第 $i$ 確率変数のリスクの市場価格
- $\sigma_i$: 第 $i$ リスク要因に対する証券の感応度

<!-- Hull eq. (28.13) -->

### 同値マルチンゲール測度結果（基本定理）

$$
d\!\left(\frac{f}{g}\right) = (\sigma_f - \sigma_g)\frac{f}{g}\,dz
$$

$f/g$ はドリフトゼロ → ニュメレール $g$ の測度のもとでマルチンゲール。これより

$$
f_0 = g_0\,E_g\!\left[\frac{f_T}{g_T}\right]
$$

<!-- Hull eq. (28.14), (28.15) -->

### マネーマーケット口座ニュメレール → リスク中立測度

マネーマーケット口座 $g$: $dg = rg\,dt$（$\sigma_g = 0$）。$\lambda = 0$ の世界。

$$
f_0 = \hat{E}\!\left[e^{-\int_0^T r\,dt}\,f_T\right]
= \hat{E}\!\left[e^{-\bar{r}T} f_T\right]
$$

$\bar{r}$: パス平均短期金利。$r$ 一定なら $f_0 = e^{-rT}\hat{E}[f_T]$。

<!-- Hull eq. (28.18), (28.19) -->

### ゼロクーポン債ニュメレール → $T$-フォワード測度

$g = P(t,T)$、$g_T = P(T,T) = 1$、$g_0 = P(0,T)$:

$$
f_0 = P(0,T)\,E_T[f_T]
$$

債券価格の整合性: $P(t,T) = E^T[1 \mid \mathcal{F}_t]$。

フォワード価格はフォワード測度のもとでの期待値:

$$
F(t,T) = E_T[S_T \mid \mathcal{F}_t]
\quad \text{（フォワード価格 = フォワード測度下の期待スポット価格）}
$$

<!-- Hull eq. (28.20), (28.21) -->

### アニュイティ・ニュメレール → スワップ測度

アニュイティファクター:

$$
A(t) = \sum_{i=0}^{N-1}(T_{i+1} - T_i)\,P(t,T_{i+1})
$$

フォワードスワップレート $s(t)$:

$$
s(t) = \frac{V(t)}{A(t)}, \qquad s(t) = E_A[s(T)]
$$

スワップション価格:

$$
V(0) = A(0)\,E_A\!\left[\frac{V(T)}{A(T)}\right]
$$

<!-- Hull eq. (28.23), (28.24), (28.25) -->

### Black のモデル（フォワード測度下）

$P(t,T)$ をニュメレールとし、$F_0$ をフォワード価格、$\sigma_F$ をフォワード価格のボラティリティとすると：

$$
c = P(0,T)\bigl[F_0 N(d_1) - K N(d_2)\bigr]
$$

$$
d_1 = \frac{\ln(F_0/K) + \tfrac{1}{2}\sigma_F^2 T}{\sigma_F\sqrt{T}},
\qquad d_2 = d_1 - \sigma_F\sqrt{T}
$$

<!-- Hull eq. (28.28) -->

### Girsanov の定理（測度変換とドリフトシフト）

市場リスクの価格を $\lambda_1$ から $\lambda_2$ へ変えると、$dz$ は不変のまま証券のドリフトが変わる:

$$
df = \bigl(\mu + (\lambda_2 - \lambda_1)\sigma\bigr)f\,dt + \sigma f\,dz
$$

一般に、ニュメレールを $g$ から $h$ へ変えると、変数 $v$ の期待成長率の調整は:

$$
\alpha_v = \rho\,\sigma_v\,\sigma_w, \qquad w = h/g
$$

$\rho$: $v$ と $w$ の瞬間相関。

<!-- Hull eq. (28.35) -->

## 4. アルゴリズム / 手順

### 手順 1: ニュメレール変換による価格計算

1. 対象デリバティブの満期ペイオフ $f_T$ を特定する。
2. 適切なニュメレール $g$ を選ぶ（満期一致ゼロクーポン債が通常最適）。
3. 対応する測度 $E_g$ のもとで $E_g[f_T/g_T]$ を計算する（対象変数のフォワード値を期待値として使える）。
4. $f_0 = g_0 \cdot E_g[f_T/g_T]$ で現在価格を得る。

### 手順 2: Girsanov 変換による Monte Carlo 重点サンプリング

1. 元の測度 $\mathbb{P}$ で $n$ パスをシミュレーション。
2. ドリフトを $\mu \to \mu + \lambda\sigma$ にシフトした別の測度 $\mathbb{Q}$ でサンプリング。
3. Radon-Nikodym 微分（尤度比）$dP/dQ = \exp(-\lambda Z - \tfrac{1}{2}\lambda^2 T)$ で各パスを重み付け。
4. 深くアウト・オブ・ザ・マネーなオプションの分散を大幅に削減できる。

### 手順 3: フォワード測度によるキャプレット価格計算（Ch.29 準備）

1. キャプレットのリセット日 $T_i$、支払日 $T_{i+1} = T_i + \tau$ を確認。
2. ニュメレールを $P(0, T_{i+1})$（支払日のゼロクーポン債）に設定。
3. $\mathbb{Q}^{T_{i+1}}$ 測度のもとで、フォワード LIBOR/SOFR レート $L$ はマルチンゲール → $E_{T_{i+1}}[L(T_i)] = L(0)$（現在フォワードレート）。
4. $L(T_i)$ が対数正規と仮定 → Black-76 公式を適用:
   $$\text{Caplet} = \tau \cdot P(0,T_{i+1})\bigl[L(0)\,N(d_1) - K\,N(d_2)\bigr]$$

## 5. Python reference

```python
import math
import numpy as np
from scipy.stats import norm


def black_caplet(L, K, sigma, T_pay, P0_T_pay, tau=0.25):
    """Caplet via Black-76 under T_pay forward measure.

    L: forward LIBOR/SOFR rate observed at T_reset, paid at T_pay
    K: strike
    sigma: forward rate vol
    T_pay: payment time (years)
    P0_T_pay: zero-coupon bond price discounting to T_pay
    tau: accrual fraction
    """
    d1 = (math.log(L / K) + 0.5 * sigma**2 * T_pay) / (sigma * math.sqrt(T_pay))
    d2 = d1 - sigma * math.sqrt(T_pay)
    return tau * P0_T_pay * (L * norm.cdf(d1) - K * norm.cdf(d2))


def importance_sample_european_call(S, K, r, sigma, T, n_paths, mu_shift, rng=None):
    """Importance-sampled MC: shift drift to r + mu_shift*sigma, reweight by Girsanov.

    mu_shift: drift shift in units of sigma (Girsanov lambda)
    Returns (price_estimate, std_error)
    """
    rng = rng or np.random.default_rng(0)
    drift = (r - 0.5 * sigma**2) * T + mu_shift * math.sqrt(T) * sigma
    Z = rng.standard_normal(n_paths)
    ST = S * np.exp(drift + sigma * math.sqrt(T) * Z)
    # Radon-Nikodym derivative (likelihood ratio)
    LR = np.exp(-mu_shift * Z - 0.5 * mu_shift**2)
    payoff = np.maximum(ST - K, 0.0) * LR
    price = float(math.exp(-r * T) * payoff.mean())
    se = float(payoff.std(ddof=1) * math.exp(-r * T) / math.sqrt(n_paths))
    return price, se


def black_swaption(s0, K, sigma, A0, T):
    """European payer swaption via Black-76 under annuity (swap) measure.

    s0: current forward swap rate
    K: fixed rate strike
    sigma: forward swap rate vol
    A0: annuity factor A(0) = sum_i tau_i * P(0, T_{i+1})
    T: option expiry
    """
    d1 = (math.log(s0 / K) + 0.5 * sigma**2 * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return A0 * (s0 * norm.cdf(d1) - K * norm.cdf(d2))


# --- Examples ---
# Caplet: L=4%, K=4%, vol=20%, 1y to pay, P(0,1)=0.95, tau=0.25
print("Caplet:", black_caplet(L=0.04, K=0.04, sigma=0.20, T_pay=1.0, P0_T_pay=0.95))

# Importance-sampled European call (OOM: K=120, S=100)
price, se = importance_sample_european_call(
    100, 120, 0.05, 0.20, 1.0, 50_000, mu_shift=1.0
)
print(f"IS Euro call (OOM K=120): price={price:.4f}, SE={se:.5f}")

# Payer swaption: s0=3%, K=3%, vol=25%, A0=4.0, T=1y
print("Payer swaption:", black_swaption(s0=0.03, K=0.03, sigma=0.25, A0=4.0, T=1.0))
```

## 6. 注意点 / 典型的なミス

- **リスク中立測度は特別な一つではない**: マネーマーケット口座をニュメレールとした場合の一測度に過ぎない。無数の等価マルチンゲール測度が存在し、ニュメレール選択次第でそれぞれ異なる「リスク中立」世界が得られる。
- **Black モデルは正しい測度のもとで使うこと**: 例えばキャプレットは支払日 $T_{i+1}$ のフォワード測度 $\mathbb{Q}^{T_{i+1}}$ のもとで導出される。誤った測度（例: $T_i$ の測度）で使うと凸性誤差（convexity error）が生じる（Ch.30 参照）。
- **測度変換はドリフトを変えるがボラティリティは変えない**: $dz$ の係数（$\sigma$）はどの測度でも同一。異なるのはドリフト項 $\mu$ のみで、差は $\lambda\sigma$。
- **多因子モデルのニュメレール変換にはベクトル $\lambda$ が必要**: 各 Wiener 過程に対応したリスクの市場価格 $\lambda_i$ が独立に必要になる。単一 $\lambda$ を使いまわすのは誤り。
- **現実測度 $\mathbb{P}$ と価格測度 $\mathbb{Q}$ は別物**: リスク管理・シナリオ分析では現実測度（正のリスクプレミアムあり）が重要だが、デリバティブ価格計算には $\mathbb{Q}$ を使う。混同しないこと。
- **フォワード価格と先物価格は異なる測度のもとでの期待値**: フォワード価格 → $T$-フォワード測度、先物価格 → リスク中立測度（伝統的）。金利確率的な場合は両者は一致しない（Section 18.6）。

## 7. 関連トピック

- See: [topics/stochastic_calculus.md](../topics/stochastic_calculus.md), Ch.14 (Itô の補題と Wiener 過程), Ch.15 (BSM とリスク中立評価), Ch.18 (Black-76 の導出), Ch.29 (IR デリバティブの標準市場モデル: フォワード測度の応用), Ch.30 (凸性・タイミング・クアント調整: 誤った測度使用による誤差).
