# Ch.17 Options on Stock Indices and Currencies

> **Source**: Hull 11e, Chapter 17 (pp. 384-400). Paraphrased summary for personal use.

## 1. 要点

- 株価指数オプションは通常「指数×100」単位で現金決済される。CBOE ではS&P 500 (SPX/OEX/XEO)、Dow Jones (DJX)、Nasdaq 100 (NDX) などが取引される。
- 連続配当利回り $q$ を支払う株式に対してBSMを適用するには、現在株価 $S_0$ を割引後の $S_0 e^{-qT}$ に置き換えるだけでよい（Merton の拡張）。
- 株価指数は指数構成銘柄の配当利回りを $q$ として扱える。外国通貨は外国無リスク金利 $r_f$ を $q$ として扱える（Garman-Kohlhagen）。
- ポートフォリオ保険では、ベータ $\beta$ のポートフォリオを守るために買う指数プットの枚数は $\beta \times P / (S \times \text{multiplier})$ で決まる（ベータ1.0なら $P/(100 S_0)$ 枚）。
- レンジ・フォワード（FXカラー）は、プット買い＋コール売りのゼロコスト組み合わせで為替レートを一定レンジに固定するヘッジ手法。
- 米国オプション（インデックス・通貨）は二項ツリーで評価する。高配当指数のコール・低配当指数のプット、高金利通貨のコール・低金利通貨のプットは早期行使が最適になりやすい。

## 2. キー用語

- **連続配当利回り (continuous dividend yield)** $q$: 株価成長率を $r-q$ に押し下げる連続複利での年率配当。指数・外国通貨いずれにも適用。
- **Garman-Kohlhagen モデル**: 外国通貨オプションの評価式。$q = r_f$（外国無リスク金利）として Merton 拡張 BSM を適用したもの（1983年）。
- **ポートフォリオ保険 (portfolio insurance)**: 指数プットを購入し、ポートフォリオ価値の下限を設定するヘッジ戦略。
- **レンジ・フォワード (range forward contract)**: プット買い＋コール売り（または逆）でゼロコストの為替レンジを設定する OTC 契約。FX カラーとも呼ばれる。
- **フォワード価格利用評価 (forward-price formulation)**: $F_0 = S_0 e^{(r-q)T}$ を使うことで配当利回りを直接推定せずに欧州オプションを評価できる形式。
- **LEAPS**: 長期（1年超）の株式・指数オプション。CBOE が提供。

## 3. 主要公式

### 連続配当利回り株の欧州コール・プット（Merton）

$$
c = S_0 e^{-qT} N(d_1) - K e^{-rT} N(d_2)
$$

$$
p = K e^{-rT} N(-d_2) - S_0 e^{-qT} N(-d_1)
$$

$$
d_1 = \frac{\ln(S_0/K) + (r - q + \sigma^2/2)T}{\sigma\sqrt{T}}, \quad
d_2 = d_1 - \sigma\sqrt{T}
$$

<!-- Hull eq. (17.4), (17.5) -->

- $S_0$: 現在の株価（または指数値、スポット為替レート）
- $K$: 行使価格
- $r$: 国内（または国内）無リスク金利（連続複利）
- $q$: 連続配当利回り（指数オプション）または外国無リスク金利 $r_f$（FX オプション）
- $\sigma$: 原資産のボラティリティ
- $T$: 満期（年）

### プット・コール・パリティ（配当利回りあり）

$$
c + K e^{-rT} = p + S_0 e^{-qT}
$$

<!-- Hull eq. (17.3) -->

米国オプションの場合：

$$
S_0 e^{-qT} - K \leq C - P \leq S_0 - K e^{-rT}
$$

### 下限（欧州オプション）

$$
c \geq \max(S_0 e^{-qT} - K e^{-rT},\ 0)
$$

$$
p \geq \max(K e^{-rT} - S_0 e^{-qT},\ 0)
$$

<!-- Hull eq. (17.1), (17.2) -->

### 通貨オプション（Garman-Kohlhagen）

$q = r_f$（外国無リスク金利）として式 (17.4)/(17.5) をそのまま適用：

$$
c = S_0 e^{-r_f T} N(d_1) - K e^{-rT} N(d_2)
$$

$$
d_1 = \frac{\ln(S_0/K) + (r - r_f + \sigma^2/2)T}{\sigma\sqrt{T}}
$$

<!-- Hull eq. (17.11), (17.12) -->

### フォワード価格を使った欧州オプション評価

$$
c = F_0 e^{-rT} N(d_1) - K e^{-rT} N(d_2), \quad
p = K e^{-rT} N(-d_2) - F_0 e^{-rT} N(-d_1)
$$

$$
d_1 = \frac{\ln(F_0/K) + \sigma^2 T/2}{\sigma\sqrt{T}}, \quad d_2 = d_1 - \sigma\sqrt{T}
$$

<!-- Hull eq. (17.8), (17.9) / (17.13), (17.14) -->

### ポートフォリオ保険の必要枚数

$$
N^* = \beta \cdot \frac{P}{S \cdot \text{multiplier}}
$$

- $\beta$: ポートフォリオのベータ（CAPM）
- $P$: ポートフォリオの現在価値
- $S$: 指数の現在値
- multiplier: 通常 100（1 契約 = 指数 × 100）

<!-- Hull §17.1 Portfolio Insurance, Table 17.1–17.2 -->

### 二項ツリーのパラメータ（米国オプション）

指数オプション：$a = e^{(r-q)\Delta t}$、通貨オプション：$a = e^{(r-r_f)\Delta t}$

<!-- Hull eq. (17.15), (17.16) -->

## 4. アルゴリズム / 手順

### ポートフォリオ保険の手順

1. ポートフォリオのベータ $\beta$ を CAPM で推定する。
2. 保護したい下限価値と現在のポートフォリオ価値 $P$ から保険水準を決める。
3. 必要プット枚数 $N^* = \beta \times P / (S_0 \times 100)$ を計算する。
4. CAPMを使い、指数のどのレベルがポートフォリオの保護水準に対応するかを求め、その指数レベルを行使価格とするプットを購入する（Table 17.1/17.2 参照）。
5. ベータ増加に伴い必要枚数が増え行使価格も上昇するため、ヘッジコストはベータに対して増加する。

### レンジ・フォワード（FXカラー）の構築

**外貨受け取りのヘッジ（レート下落リスク回避）:**
1. ストライク $K_1$ の欧州プットを買う（下限レートを確保）。
2. ストライク $K_2 > K_1$ の欧州コールを売る（上昇の恩恵を放棄する代わりに費用を相殺）。
3. プットとコールのプレミアムが等しくなるよう $K_1, K_2$ を設定し、ゼロコストにする。

**外貨支払いのヘッジ（レート上昇リスク回避）:**
1. ストライク $K_1$ のプットを売り、ストライク $K_2$ のコールを買う（ロング・レンジ・フォワード）。
2. $K_1 = K_2$ とすれば通常の先物と同じになる。

### 指数配当利回りの推定

1. 先物価格 $F_0$ と現物 $S_0$ から $q = r - \frac{1}{T}\ln(F_0/S_0)$。
2. または、同一満期・同一ストライクのコール $c$ とプット $p$ から put-call parity を使い $q = -\frac{1}{T}\ln\frac{c-p+Ke^{-rT}}{S_0}$。
3. 複数の満期・ストライクの観測を組み合わせることで、配当利回りのタームストラクチャーを推定できる。

## 5. Python reference

```python
import math
from scipy.stats import norm


def bs_yield(S, K, r, q, sigma, T, kind='call'):
    """BSM with continuous yield (covers index, FX options).

    Parameters
    ----------
    S     : spot price (index value or exchange rate)
    K     : strike price
    r     : domestic risk-free rate (continuous, annual)
    q     : continuous dividend yield OR foreign risk-free rate r_f
    sigma : volatility (annual)
    T     : time to maturity (years)
    kind  : 'call' or 'put'
    """
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if kind == 'call':
        return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)


def fx_option(S0, K, r_dom, r_for, sigma, T, kind='call'):
    """Garman-Kohlhagen: FX option with foreign risk-free rate as yield."""
    return bs_yield(S0, K, r_dom, r_for, sigma, T, kind)


def portfolio_insurance_contracts(portfolio_value, index_level, beta=1.0, multiplier=100):
    """Number of index put contracts for portfolio insurance (Hull §17.1)."""
    return beta * portfolio_value / (index_level * multiplier)


# Example 17.1: S&P 500 European call, q=3%, r=8%, sigma=20%, T=2/12
call_idx = bs_yield(S=930, K=900, r=0.08, q=0.03, sigma=0.20, T=2/12, kind='call')
print(f"Index call price: {call_idx:.2f}")   # ~51.83

# Example 17.2: EUR/USD 4-month call (Garman-Kohlhagen)
# S0=1.60, K=1.60, r_dom=0.08, r_for=0.11, sigma=0.14, T=4/12
call_fx = fx_option(S0=1.60, K=1.60, r_dom=0.08, r_for=0.11, sigma=0.1414, T=4/12, kind='call')
print(f"FX call price: {call_fx:.4f}")       # ~0.0285

# Portfolio insurance: $500,000 portfolio, beta=2.0, index=1,000
n = portfolio_insurance_contracts(500_000, 1_000, beta=2.0)
print(f"Put contracts needed: {n:.0f}")      # 10
```

## 6. 注意点 / 典型的なミス

- **配当利回りの時間加重平均**: 指数オプション評価に使う $q$ は、オプション存続期間中のex配当日に対応する配当のみを使って計算した平均年率。将来の配当すべてを使わないこと。
- **ドル建て為替 vs 外貨建て**: $S_0$ は「1単位外貨の国内通貨価値（ドル/外貨）」として統一すること。プット/コールの対称性（式(17.12)は外貨でみたコールに等しい）に注意。
- **指数乗数（Dow Jones）**: CBOE の Dow Jones 指数オプションは通常表示される Dow Jones 指数の 0.01 倍を原資産として使う。1 契約 = 0.01 × DJI × 100。
- **米国オプションの早期行使**: 高配当指数コール・低配当指数プット、高金利通貨コール・低金利通貨プットは早期行使が有利になる場合がある。BSM では評価不可なので二項ツリーを使うこと。
- **レンジ・フォワードのコスト**: プット価格 ＝ コール価格 となるように $K_1 < F_0 < K_2$ を設定するとゼロコスト。フォワード価格の前後にストライクを対称に置くとほぼゼロコストになりやすい。
- **長期プット（Business Snapshot 17.1）**: 「長期では株は債券に勝つ」という保証の提供は見かけより非常に高価（例：10年プットは原資産の約17%相当）。長期オプションの時間価値を過小評価しないこと。

## 7. 関連トピック

- Ch.15 (BSM モデル基礎): $q=0$ のケース、put-call parity の導出
- Ch.13 / Ch.21 (二項ツリー): 米国指数・通貨オプションの数値評価
- Ch.05 (先物価格): $F_0 = S_0 e^{(r-q)T}$ の導出
- Ch.18 (先物オプション・Black モデル): 式 (17.13)/(17.14) は Black モデルと同形
- Ch.19 (Greeks): $\Delta$、$\Gamma$ の計算への $q$ の影響
- See: [topics/options_basics.md](../topics/options_basics.md), [topics/bsm.md](../topics/bsm.md)
