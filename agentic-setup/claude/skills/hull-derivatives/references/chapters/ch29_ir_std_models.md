# Ch.29 Interest Rate Derivatives: The Standard Market Models

> **Source**: Hull 11e, Chapter 29 (pp. 688-706). Paraphrased summary for personal use.

## 1. 要点

- 金利デリバティブは株式・為替より困難：金利は単一変数ではなく利回り曲線全体が動き、割引率と payoff の両方に影響する。
- 実務の標準は **Black のモデル**（Black-76）を各商品ごとに適用する手法。債券オプションは将来の債券価格が対数正規、キャップレットは将来の短期金利が対数正規、スワップションは将来のスワップレートが対数正規と仮定する。
- **キャップ（Cap）**は一連のキャップレットの和；キャップレット 1 本は「前払・後受」構造の金利コールオプションであり、フラットボラティリティ 1 本または個別スポットボラティリティで価格付けされる。
- **スワップション（Swaption）**は将来時点 $T$ に入る $n$ 年スワップの European オプション；ペイヤー（固定払い権）は $LA[s_F N(d_1) - s_K N(d_2)]$ で表される。
- 3 つのモデル（債券オプション・キャップ・スワップション）は互いに矛盾しており、理論的には両立しないが、実務ではそれぞれ独立に使われる。

## 2. キー用語

- **Bond option**: 将来の特定日に特定価格でボンドを売買する権利。Callable/Putable bond に埋め込まれた形でも存在。
- **Callable bond**: 発行体が所定のコールプライスで買い戻せる条項を持つ債券。
- **Putable bond (retractable bond)**: 保有者が早期償還を要求できる条項を持つ債券。
- **Clean price / Dirty price**: クリーンプライスは経過利子を除いた公表価格、ダーティプライスは経過利子込みの実際の決済価格。
- **Cap**: 変動金利が上限を超えた場合に差額を受け取る一連のコールオプション。
- **Floor**: 変動金利が下限を下回った場合に差額を受け取る一連のプットオプション。
- **Caplet / Floorlet**: キャップ（フロア）を構成する個々の金利オプション。
- **Collar**: キャップのロングとフロアのショートの組み合わせ（コストゼロ設計も可）。
- **Flat volatility**: キャップ全体に一律に当てはめるボラティリティ；市場での標準的な呼び値。
- **Spot volatility (caplet vol)**: 各キャップレットに個別に適用するボラティリティ；ストリッピングで得る。
- **Swaption (swap option)**: 将来時点に特定レートでスワップに入る権利。ペイヤー／レシーバーの 2 種類。
- **Forward swap rate ($s_F$)**: 現時点で合意するスワップの均衡固定レート（=$s_0$）。
- **Swap annuity ($A$)**: スワップのキャッシュフロー $1/m$ を各支払日に割引いた現在価値の合計 $A = \frac{1}{m}\sum_{i=1}^{mn} P(0,T_i)$。
- **Volatility cube**: スワップション vol の (ストライク × オプション満期 × スワップテナー) の 3 次元曲面。
- **Shifted lognormal model**: 金利 $+\alpha$（シフト）を対数正規と仮定し、負金利に対応する拡張モデル。
- **Bachelier (normal) model**: 金利を正規分布と仮定；負金利環境でも適用可能。DV01 は dollar value of 1 basis point。

## 3. 主要公式

### Bond Option — Black's model (European)

$$
c = P(0,T)\bigl[F_B N(d_1) - K N(d_2)\bigr]
$$
$$
p = P(0,T)\bigl[K N(-d_2) - F_B N(-d_1)\bigr]
$$

$$
d_1 = \frac{\ln(F_B/K) + \sigma_B^2 T/2}{\sigma_B \sqrt{T}}, \quad d_2 = d_1 - \sigma_B\sqrt{T}
$$

- $F_B$: 現時点でのフォワード債券価格（キャッシュプライス）$= (B_0 - I)/P(0,T)$
- $K$: ストライク（キャッシュプライス）
- $\sigma_B$: フォワード債券価格のボラティリティ
- $T$: オプション満期

<!-- Hull eq. (29.1), (29.2), (29.3) -->

**Yield volatility との変換**:
$$
\sigma_B \approx D y_0 \sigma_y
$$
ここで $D$ は修正デュレーション、$y_0$ は初期フォワード利回り、$\sigma_y$ はフォワード利回りのボラティリティ。

<!-- Hull eq. (29.4) -->

---

### Caplet — Black's model

$$
\text{caplet} = L \delta_k P(0, t_{k+1})\bigl[F_k N(d_1) - R_K N(d_2)\bigr]
$$

$$
d_1 = \frac{\ln(F_k/R_K) + \sigma_k^2 t_k/2}{\sigma_k \sqrt{t_k}}, \quad d_2 = d_1 - \sigma_k\sqrt{t_k}
$$

- $L$: 想定元本
- $\delta_k = t_{k+1} - t_k$: テナー（年率）
- $F_k$: 期間 $[t_k, t_{k+1}]$ のフォワード金利（スポットボラティリティ $\sigma_k$ に対応）
- $R_K$: キャップレート（ストライク）
- $P(0, t_{k+1})$: 満期 $t_{k+1}$ までの割引ファクター
- ボラティリティは $\sqrt{t_k}$ で掛けることに注意（金利は $t_k$ 時点観測、payoff は $t_{k+1}$）

<!-- Hull eq. (29.7) -->

**Floorlet** (analogous put):
$$
\text{floorlet} = L \delta_k P(0, t_{k+1})\bigl[R_K N(-d_2) - F_k N(-d_1)\bigr]
$$

<!-- Hull eq. (29.8) -->

**Cap = sum of caplets**:
$$
\text{cap} = \sum_{k=1}^{n} \text{caplet}_k
$$

**Flat vol vs Spot vol**: 市場はキャップ 1 本につきフラットボラティリティ $\hat{\sigma}$ を 1 つ呼ぶ。個別キャップレット vol（スポット vol $\sigma_k$）はストリッピングで逆算する。

---

### Cap-Floor Parity

$$
\text{cap} - \text{floor} = \text{IRS (pay fixed } R_K\text{)}
$$

同一ストライク・同一満期のキャップとフロアの差は、$R_K$ 払い固定スワップに等しい。ATM のキャップとフロアは等価（コールペリティ）で、ATM ストライクは現在のフォワードスワップレートに一致する。

<!-- Hull Business Snapshot 29.1 -->

---

### Swaption (European Payer) — Black's model

$$
V_{\text{payer}} = L \cdot A(0)\bigl[s_F N(d_1) - s_K N(d_2)\bigr]
$$

$$
V_{\text{receiver}} = L \cdot A(0)\bigl[s_K N(-d_2) - s_F N(-d_1)\bigr]
$$

$$
d_1 = \frac{\ln(s_F/s_K) + \sigma_s^2 T/2}{\sigma_s\sqrt{T}}, \quad d_2 = d_1 - \sigma_s\sqrt{T}
$$

$$
A(0) = \frac{1}{m}\sum_{i=1}^{mn} P(0, T_i)
$$

- $s_F$ ($=s_0$): フォワードスワップレート（現時点の均衡固定レート）
- $s_K$: ストライク固定レート
- $\sigma_s$: フォワードスワップレートのボラティリティ
- $T$: スワップション満期、$n$: スワップ年数、$m$: 支払頻度
- $A(0)$: スワップアニュイティ（$1/m$ を各支払日に割引いた合計）

<!-- Hull eq. (29.10), (29.11) -->

**Volatility cube**: スワップション vol は (ストライク $s_K$, オプション満期 $T$, スワップテナー $n$) の 3 次元曲面で管理される。

## 4. アルゴリズム / 手順

1. **Cap pricing（フラットボラティリティ）**
   1. 割引カーブからフォワードレート $F_k$ を bootstrap。
   2. 各キャップレットを Black's 式（eq. 29.7）で計算（全キャップレット共通のフラット vol $\hat\sigma$ を使用）。
   3. キャップレットを合計してキャップ価格を得る。

2. **Cap vol stripping（スポット vol の逆算）**
   1. 最短期キャップ（通常 1 年）の市場価格からキャップレット 1 本の価格を直接読み取る → $\sigma_1$ を brentq 等で解く。
   2. 次のキャップの市場価格 = 前の累積キャップレット価値 + 新キャップレット価値 → $\sigma_2$ を解く。
   3. 以降 incremental に繰り返す。

3. **Swaption pricing（Black's model）**
   1. 割引カーブから $A(0) = \frac{1}{m}\sum P(0,T_i)$ を計算。
   2. フォワードスワップレート $s_F$ を計算（$A \cdot s_F = \sum [P(0,t_k) - P(0,t_{k+1})]$ のパー条件より）。
   3. Black's 式（eq. 29.10 or 29.11）にボラティリティ $\sigma_s$ を代入して価格算出。

4. **Convexity check（測度の確認）**
   - キャップレット：$F_k$ は $\mathbb{Q}^{t_{k+1}}$（$P(0,t_{k+1})$ をニュメレールとする測度）でマルチンゲール → Black's formula は exact（eq. 28.22）。
   - スワップション：$s_F$ はスワップアニュイティ $A$ をニュメレールとする測度でマルチンゲール → Black's formula は exact（eq. 28.24-25）。
   - この測度整合性が崩れる商品（CMS, Libor in arrears 等）では凸性調整が必要（Ch.30）。

## 5. Python reference

```python
import math
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq


def caplet_black(F, K, sigma, tau, P_pay, T):
    """Black-76 caplet. F: fwd rate over [T, T+tau]. P_pay: discount factor to T+tau."""
    d1 = (math.log(F / K) + 0.5 * sigma**2 * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return tau * P_pay * (F * norm.cdf(d1) - K * norm.cdf(d2))


def floorlet_black(F, K, sigma, tau, P_pay, T):
    """Black-76 floorlet."""
    d1 = (math.log(F / K) + 0.5 * sigma**2 * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return tau * P_pay * (K * norm.cdf(-d2) - F * norm.cdf(-d1))


def cap_price_flat_vol(fwd_rates, K, vol_flat, taus, P_pays, T_starts):
    """Price a cap as sum of caplets sharing a single flat vol."""
    return sum(
        caplet_black(F, K, vol_flat, tau, P, T)
        for F, tau, P, T in zip(fwd_rates, taus, P_pays, T_starts)
        if T > 0
    )


def swaption_black(F_swap, K, sigma, T_exp, annuity, kind='payer'):
    """European swaption via Black's model on forward swap rate.

    annuity = (1/m) * sum of P(0, T_i) over all swap payment dates.
    kind: 'payer' (right to pay fixed) or 'receiver' (right to receive fixed).
    """
    d1 = (math.log(F_swap / K) + 0.5 * sigma**2 * T_exp) / (sigma * math.sqrt(T_exp))
    d2 = d1 - sigma * math.sqrt(T_exp)
    if kind == 'payer':
        return annuity * (F_swap * norm.cdf(d1) - K * norm.cdf(d2))
    return annuity * (K * norm.cdf(-d2) - F_swap * norm.cdf(-d1))


def cap_flat_to_spot_vols(cap_quotes, fwd_rates, K, taus, P_pays, T_starts):
    """Strip caplet (spot) vols by solving cap-cap difference equations.

    cap_quotes: list of cumulative cap prices at each maturity.
    Returns list of per-caplet (spot) volatilities.
    """
    spot_vols = []
    cum_caplet_value = 0.0
    for i, cap_price in enumerate(cap_quotes):
        F, tau, P, T = fwd_rates[i], taus[i], P_pays[i], T_starts[i]
        target_caplet = cap_price - cum_caplet_value
        if T <= 0:
            spot_vols.append(0.0)
            continue
        sigma_i = brentq(
            lambda s: caplet_black(F, K, s, tau, P, T) - target_caplet, 1e-4, 5.0
        )
        spot_vols.append(sigma_i)
        cum_caplet_value += caplet_black(F, K, sigma_i, tau, P, T)
    return spot_vols


# --- Example: 2y cap with 4 semi-annual caplets, K=4%, flat vol 20% ---
fwd_rates = [0.04, 0.04, 0.04, 0.04]
taus      = [0.5,  0.5,  0.5,  0.5]
T_starts  = [0.5,  1.0,  1.5,  2.0]
P_pays    = [math.exp(-0.04 * t) for t in T_starts]

cap = cap_price_flat_vol(fwd_rates, K=0.04, vol_flat=0.20, taus=taus,
                         P_pays=P_pays, T_starts=T_starts)
print(f"Cap price (flat vol 20%): {cap:.6f}")

# --- Example: 3y swaption, payer ---
m = 2  # semi-annual payments
T_exp = 5.0
r = 0.06
pay_dates = [T_exp + i / m for i in range(1, 3 * m + 1)]
P_swap = [math.exp(-r * t) for t in pay_dates]
annuity = (1 / m) * sum(P_swap)
s_F = 0.06194  # forward swap rate (semiannual compounding)
print(f"Swaption (payer): {100 * swaption_black(s_F, K=0.062, sigma=0.20,
      T_exp=T_exp, annuity=annuity, kind='payer'):.4f} M")
```

## 6. 注意点 / 典型的なミス

- **測度の一致**: Black's model がキャップレット・スワップションに適用できるのは、各フォワードレート（スワップレート）が正しい測度（$T_{k+1}$-フォワード測度・スワップアニュイティ測度）でマルチンゲールだからである（Jamshidian/Brace の証明）。この前提を確認せずに任意の金利商品に Black's を適用するのは誤り。
- **フラット vol とスポット vol の混同**: キャップは市場では 1 本のフラット vol で呼ばれる。スポット vol（キャップレット別 vol）はストリッピング後に初めて得られる。両者は一般に異なり、可算平均のような単純な関係ではない。
- **3 モデルの非整合性**: 「債券価格が対数正規」「短期金利が対数正規」「スワップレートが対数正規」は同時に成立しない。3 つの Black モデルは互いに矛盾しており、同じボラティリティを共有できない。モデル間の価格差は凸性調整（Ch.30）やよりリッチなモデル（Ch.32, 33）で扱う。
- **負金利環境での破綻**: 対数正規 Black は金利がゼロ以下になれないため、負金利では vol が定義不能になる。**シフト対数正規モデル**（金利 $+\alpha$ を対数正規と仮定）または **Bachelier 正規モデル**（正規分布を直接仮定）を使う。$\sigma_k$（Black vol）と $\sigma_k^*$（Bachelier vol）のスケールは大きく異なる（例: 金利 3% 付近で $\sigma_k \approx 33\%$, $\sigma_k^* \approx 1\%$）。
- **ストライクの cash vs quoted**: 債券オプションのストライクはクリーンプライスかダーティプライスかを明確に区別すること。満期が利払い日以外なら経過利子を加算する必要がある。
- **Day count conventions**: テナー $\delta_k$（実際の日数/360 または 365）が cap formula の $\delta_k$（年分数）に対応する accrual fraction $a_k$ に置き換わる。フォワードレートも同じ day count で定義すること。
- **Volatility cube**: スワップション vol は (ストライク, オプション満期, スワップテナー) の 3 次元で管理される。単一の vol surface ではなく cube であることを意識する。

## 7. 関連トピック

- See: [topics/ir_derivatives.md](../topics/ir_derivatives.md)
- **Ch.28** (Martingales and Measures) — $T$-フォワード測度とスワップアニュイティ測度の定式化；本章の理論的基盤。
- **Ch.30** (Convexity, Timing, and Quanto Adjustments) — CMS レート・LIBOR in arrears など、Black が exact でない商品の凸性調整。
- **Ch.32** (No-Arbitrage Models of the Short Rate) — Hull-White モデル；Jamshidian のスワップション分解により Black と整合的なスワップション価格が得られる。
- **Ch.33** (Modeling Forward Rates) — LIBOR Market Model (LMM / BGM)；全キャップレット vol を整合的に扱える一般フレームワーク。
