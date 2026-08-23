# Ch.15 The Black-Scholes-Merton Model

> **Source**: Hull 11e, Chapter 15 (pp. 338-370). Paraphrased summary for personal use.

## 1. 要点

- 株価の対数リターンが正規分布に従うという仮定（対数正規モデル）から出発し、European オプションの解析的な価格公式を導く。
- Black-Scholes-Merton の微分方程式は、デルタヘッジによるリスクフリーポートフォリオの構築から導かれる。BSM PDEの解に必要なのは境界条件のみであり、投資家の危険選好は現れない。
- リスク中立評価原理：BSM PDE が $\mu$（期待リターン）を含まないことを利用し、仮想的な「リスク中立世界」で期待ペイオフを計算してリスクフリーレートで割り引くことで、正しいオプション価格が得られる。
- ボラティリティは **ヒストリカル法**（過去の日次対数リターンの標本標準偏差）または **インプライドボラティリティ**（市場価格をBSM式に逆代入して得る）の2通りで推定できる。
- 配当がある場合、欧州オプションは $S_0' = S_0 - \text{PV(div)}$ で代替し、アメリカンコールに対しては Black's approximation（満期 $T$ と最終配当落ち前日 $t_n$ のいずれかを行使期日とした欧州コール2本の価格の大きい方）を用いる。

## 2. キー用語

- **対数正規分布 (Lognormal distribution)**: $S_T > 0$ で右裾が厚い。$S_T$ が対数正規 ⟺ $\ln S_T$ が正規分布。
- **ボラティリティ $\sigma$**: 株価変化率の年率連続複利標準偏差。GBM の拡散係数として現れる。
- **BSM PDE**: オプション価格 $f$ が満たすべき偏微分方程式。リスクフリーポートフォリオの無裁定条件から導かれる。
- **リスク中立評価 (Risk-neutral valuation)**: 全ての資産の期待リターンを $r$ と置き換えて期待ペイオフを計算し、$e^{-rT}$ で割り引く手続き。実世界では成立しないが、正しいオプション価格を与える。
- **デルタ $\Delta = \partial f / \partial S$**: オプション価格の株価に対する感応度。BSM PDE 導出で用いるヘッジ比率。
- **ヒストリカルボラティリティ**: 過去の対数リターン $u_i = \ln(S_i/S_{i-1})$ の標本標準偏差 $s$ から $\hat\sigma = s/\sqrt\tau$ で推定した年率ボラティリティ。
- **インプライドボラティリティ (Implied volatility)**: BSM 式が市場価格に一致するような $\sigma$ の値。市場参加者が実質的にやり取りする量。
- **VIX指数**: CBOE が S&P 500 の30日オプション価格群から算出する30日インプライドボラティリティ指数。
- **Black's approximation**: 配当付きアメリカンコールを2本の欧州コールの価格の最大値で近似する手法。
- **$N(x)$**: 標準正規分布の累積分布関数。$d_1$, $d_2$ に適用してオプション価格を求める。

## 3. 主要公式

### 対数正規株価モデル

$$
\ln S_T \sim N\!\left(\ln S_0 + \left(\mu - \frac{\sigma^2}{2}\right)T,\; \sigma^2 T\right)
$$

<!-- Hull eq. (15.3) -->

- $S_0$: 現在株価、$\mu$: 期待リターン（年率）、$\sigma$: ボラティリティ（年率）、$T$: 年単位の満期

### 対数正規モーメント

$$
E(S_T) = S_0 e^{\mu T}
$$
<!-- Hull eq. (15.4) -->

$$
\mathrm{Var}(S_T) = S_0^2 e^{2\mu T}\!\left(e^{\sigma^2 T} - 1\right)
$$
<!-- Hull eq. (15.5) -->

### 連続複利リターンの分布

$$
x = \frac{1}{T}\ln\frac{S_T}{S_0} \;\sim\; N\!\left(\mu - \frac{\sigma^2}{2},\; \frac{\sigma^2}{T}\right)
$$

<!-- Hull eq. (15.7) -->

- 平均は $\mu - \sigma^2/2$（期待リターン $\mu$ より低い）、分散は $T$ とともに縮小する。

### BSM 偏微分方程式

$$
\frac{\partial f}{\partial t} + r S \frac{\partial f}{\partial S} + \frac{1}{2}\sigma^2 S^2 \frac{\partial^2 f}{\partial S^2} = r f
$$

<!-- Hull eq. (15.16) -->

- $f$: 株式を原資産とする任意の派生商品の価格、$r$: リスクフリーレート（連続複利）。

### BS 欧州コールおよびプット（配当なし）

$$
c = S_0 N(d_1) - K e^{-rT} N(d_2)
$$
<!-- Hull eq. (15.20) -->

$$
p = K e^{-rT} N(-d_2) - S_0 N(-d_1)
$$
<!-- Hull eq. (15.21) -->

$$
d_1 = \frac{\ln(S_0/K) + (r + \sigma^2/2)\,T}{\sigma\sqrt{T}}, \qquad d_2 = d_1 - \sigma\sqrt{T}
$$

- $N(d_2)$: リスク中立確率でコールが行使される確率。
- $S_0 N(d_1) e^{rT}$: 行使された場合の期待株価（リスク中立世界）。

### 連続配当利回り $q$ ありの場合

$$
c = S_0 e^{-qT} N(d_1) - K e^{-rT} N(d_2)
$$

$$
d_1 = \frac{\ln(S_0/K) + (r - q + \sigma^2/2)\,T}{\sigma\sqrt{T}}, \qquad d_2 = d_1 - \sigma\sqrt{T}
$$

<!-- Hull Ch.17 の Merton (1973) 拡張。Ch.15 で導入される連続配当扱いの一般化 -->

### 離散配当ありの欧州オプション

$$
S_0' = S_0 - \mathrm{PV(div)} = S_0 - \sum_i D_i e^{-r t_i}
$$

- $S_0'$ を配当なし BSM 式の $S_0$ に代入する。ストライクからは引かない点に注意。

### ヒストリカルボラティリティ推定量

$$
u_i = \ln\frac{S_i}{S_{i-1}}, \qquad
s = \sqrt{\frac{1}{n-1}\sum_{i=1}^{n}(u_i - \bar{u})^2}, \qquad
\hat\sigma = \frac{s}{\sqrt{\tau}}
$$

- $\tau$: 観測間隔（年単位）、$n$: 観測数、標準誤差 $\approx \hat\sigma/\sqrt{2n}$。
- 実務では $\bar{u} \approx 0$ と置くことが多い。取引日ベースで計算し、252日/年換算。

### インプライドボラティリティの定義

$$
c_{\mathrm{BS}}(\sigma_{\mathrm{impl}}) = c_{\mathrm{mkt}}
$$

- $c_{\mathrm{BS}}$ は $\sigma$ の単調増加関数なので、一意解が存在する。反復法（二分法・Newton-Raphson）で解く。

### リスク中立評価原理

$$
f = e^{-rT}\, \hat{E}[f_T]
$$

- $\hat{E}[\cdot]$: リスク中立確率測度下での期待値。$\mu \to r$ と置換して期待ペイオフを計算し、$e^{-rT}$ で割り引く。

### Black's approximation（配当付きアメリカンコール）

$$
C_{\mathrm{American}} \approx \max\bigl(c(S_0,\, K,\, r,\, \sigma,\, T),\; c(S_0',\, K,\, r,\, \sigma,\, t_n)\bigr)
$$

- 第1項：満期 $T$、$S_0' = S_0 - \mathrm{PV(div)}$ の欧州コール。
- 第2項：最終配当落ち日直前 $t_n$、$S_0$ の欧州コール（その時点で全株価を使う）。
- 近似理由：ホルダーが時刻 0 に「$T$ まで保有」か「$t_n$ 直前に行使」かを決める仮定に相当。

<!-- Hull §15.12, eq. (15.23)-(15.25) より派生 -->

## 4. アルゴリズム / 手順

### 4.1 デルタヘッジによるBSM PDE の導出（Hull §15.6）

1. 株価過程を GBM と仮定：$dS = \mu S\, dt + \sigma S\, dz$。
2. Itô の補題を $f(S, t)$ に適用：
   $$df = \left(\frac{\partial f}{\partial S}\mu S + \frac{\partial f}{\partial t} + \frac{1}{2}\frac{\partial^2 f}{\partial S^2}\sigma^2 S^2\right)dt + \frac{\partial f}{\partial S}\sigma S\, dz$$
3. ポートフォリオを構築：$\Pi = -f + \dfrac{\partial f}{\partial S}\cdot S$（デリバティブ1単位ショート、株式 $\partial f/\partial S$ 単位ロング）。
4. $\Delta\Pi$ を計算すると、$\Delta z$ 項が消去され確定的変化になる：
   $$\Delta\Pi = \left(-\frac{\partial f}{\partial t} - \frac{1}{2}\frac{\partial^2 f}{\partial S^2}\sigma^2 S^2\right)\Delta t$$
5. 無裁定条件より $\Delta\Pi = r\Pi\,\Delta t$ を代入。$\Pi = -f + (\partial f/\partial S)S$ を用いて整理すると BSM PDE が得られる。

### 4.2 リスク中立評価による価格計算手順

1. $\mu = r$ と置換（リスク中立世界へ移行）。
2. $S_T$ の分布：$\ln S_T \sim N\!\left(\ln S_0 + (r - \sigma^2/2)T,\; \sigma^2 T\right)$。
3. ペイオフの期待値を計算（コールなら $\hat{E}[\max(S_T - K, 0)]$）。
4. $e^{-rT}$ を掛けて現在価値化。$\Rightarrow$ 付録の積分計算により $d_1$, $d_2$ の式が出る。

### 4.3 インプライドボラティリティのソルバー（Newton-Raphson 法）

1. 初期値 $\sigma^{(0)}$ を設定（例：0.2）。
2. 残差 $F(\sigma) = c_{\mathrm{BS}}(\sigma) - c_{\mathrm{mkt}}$、ヤコビアン $F'(\sigma) = \mathrm{Vega} = S_0\sqrt{T}\,N'(d_1)e^{-qT}$。
3. 更新：$\sigma^{(k+1)} = \sigma^{(k)} - F(\sigma^{(k)}) / F'(\sigma^{(k)})$。
4. 収束まで繰り返す（通常 3-5 回）。
5. 収束しない場合（深い ITM/OTM）は Brent 法（二分法ベース）に切り替える。

## 5. Python reference

```python
import math
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq


def bs_call(S, K, r, q, sigma, T):
    """European call on continuous-dividend lognormal stock."""
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)


def bs_put(S, K, r, q, sigma, T):
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)


def implied_vol_call(price, S, K, r, q, T, lo=1e-6, hi=5.0):
    """Solve bs_call(sigma) = price for sigma in [lo, hi]."""
    f = lambda s: bs_call(S, K, r, q, s, T) - price
    return brentq(f, lo, hi)


# Examples
c = bs_call(100, 100, 0.05, 0.0, 0.20, 1.0)
p = bs_put(100, 100, 0.05, 0.0, 0.20, 1.0)
print(f"C={c:.4f}  P={p:.4f}  C-P={c-p:.4f}  S-Ke^-rT={100 - 100*math.exp(-0.05):.4f}")
iv = implied_vol_call(c, 100, 100, 0.05, 0.0, 1.0)
print(f"implied vol: {iv:.4f}")
```

期待出力（プットコールパリティ確認）:
```
C=10.4506  P=5.5735  C-P=4.8771  S-Ke^-rT=4.8771
implied vol: 0.2000
```

### ヒストリカルボラティリティの計算例

```python
import numpy as np

def hist_vol(prices, tau=1/252):
    """Annualized historical volatility from a price series."""
    u = np.log(prices[1:] / prices[:-1])
    s = np.std(u, ddof=1)
    return s / np.sqrt(tau)

# Example: 21 trading days → ~19.3% pa (replicates Hull Table 15.1)
prices = [20.00, 20.10, 19.90, 20.00, 20.50, 20.25, 20.90, 20.90,
          20.90, 20.75, 20.75, 21.00, 21.10, 20.90, 20.90, 21.25,
          21.40, 21.40, 21.25, 21.75, 22.00]
print(f"hist vol: {hist_vol(prices):.4f}")  # ≈ 0.193
```

## 6. 注意点 / 典型的なミス

- **$\sigma$ の単位**：Hull の $\sigma$ は連続複利年率。単純リターンの標準偏差でも、日次標準偏差でもない。$\sqrt{252}$ スケーリングで年率化する。
- **$q$ と $r$, $T$ の統一**：連続配当利回り $q$、リスクフリーレート $r$ はいずれも連続複利年率で揃えること。期間 $T$ も同一の年数単位を使う。
- **離散配当の扱い**：$S_0' = S_0 - \text{PV(div)}$ を使う。ストライク $K$ からは引かない（よくある間違い）。
- **BSM は定数ボラティリティを仮定**：実市場では vol smile / skew が存在するため、BSM をそのまま使うのはベースライン。Ch.20 でスマイルを扱う。
- **インプライドボラティリティの根探し**：探索区間を有界に設定しないと失敗する。深い OTM オプションはインプライドボラティリティが高い場合があり、上限を広めに取る（`hi=5.0` 程度）。
- **アメリカンコールと配当**：配当がなければアメリカンコールは早期行使しない（BSM = 欧州コールと等価）。配当がある場合のみ早期行使が起こりうる。Black's approximation は近似であり、厳密解ではない。
- **時間の測り方**：ボラティリティ計算では取引日ベース（252日/年）、オプション満期 $T$ も取引日数/252 で計算することが実務標準。カレンダー日数との混同に注意。
- **$\mu$ の非出現**：BSM 式は期待リターン $\mu$ を含まない。これは BSM PDE の本質的な特徴であり、リスク中立評価の根拠となる。

## 7. 関連トピック

- 前提：[topics/stochastic_calculus.md](../topics/stochastic_calculus.md) (Ch.14 — GBM, Itô's Lemma)、[topics/binomial.md](../topics/binomial.md) (Ch.13 — 離散近似→BSM収束)
- 後続：[topics/greeks.md](../topics/greeks.md) (Ch.19 — $\Delta$, $\Gamma$, $\Theta$, $\mathcal{V}$, $\rho$)、Ch.20 (Vol smile)、Ch.21 (数値手法)
- 拡張：Ch.17 (株価指数・通貨オプション、Merton の連続配当モデル)、Ch.18 (Black's model for futures)
- 参照：[topics/bsm.md](../topics/bsm.md)
