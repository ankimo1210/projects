# Ch.07 Swaps

> **Source**: Hull 11e, Chapter 7 (pp. 172-200). Paraphrased summary for personal use.

## 1. 要点

- スワップはOTCで二者間が将来のキャッシュフローを交換する契約。金利スワップは固定金利と変動金利（SOFR/LIBOR系）の交換が基本形（プレーン・バニラ IRS）。
- 金利スワップは「固定利付債と変動利付債のポートフォリオ」または「FRA のポートフォリオ」として価値評価できる（Hull 優先はFRAアプローチ）。
- スワップ開始時に価値をゼロにするレートが**スワップレート（par swap rate）**。市場では bid/ask スプレッドを挟んで提示される。
- 比較優位論はスワップが生まれる動機を説明するが、実際には固定・変動スプレッドの非対称は信用リスクの期間差に起因するため、「真の」比較優位は疑わしい。
- 通貨スワップは元本と利息を異なる通貨で交換。固定-固定、固定-変動、変動-変動の三形態があり、各種ポートフォリオ分解で評価できる。
- 2010年代以降、LIBOR から OIS（SOFR等）への移行が進み、スワップのディスカウントには OIS レートを使う慣行が定着。

## 2. キー用語

- **Interest Rate Swap (IRS)**: 同一名目元本に対し固定金利と変動金利を周期的に交換する契約。元本の交換はない。
- **Plain Vanilla IRS**: 固定 vs. 変動（LIBOR/SOFR）の最もシンプルな金利スワップ。
- **OIS (Overnight Indexed Swap)**: オーバーナイト金利（SOFR, SONIA 等）の実現値を参照する変動金利と固定金利を交換するスワップ。
- **SOFR**: Secured Overnight Financing Rate。米国でLIBORを代替するリスクフリー参照金利。
- **Notional Principal**: 名目元本。金利計算の基準額。金利スワップでは実際に交換されない。
- **Fixed-Rate Payer / Floating-Rate Payer**: 固定を払う側（変動を受ける）/ 変動を払う側（固定を受ける）。
- **Swap Rate**: 特定満期のスワップをゼロ価値にする固定レート。市場でクォートされ、ゼロカーブのブートストラップに使う。
- **Par Bond**: 価格が額面に等しい債券。スワップレートはパー債券のクーポンレートに相当。
- **FRA (Forward Rate Agreement)**: 将来の一期間について固定・変動金利を交換する単発の先渡し契約。スワップはFRAの列。
- **Currency Swap (Fixed-for-Fixed)**: 二通貨で元本と固定利息を交換。開始・終了時に元本を交換する。
- **Comparative Advantage**: 一方の企業が固定市場で、他方が変動市場で相対的に有利な場合、スワップで双方がコスト低減できる（ただし見かけ上の優位に過ぎないことが多い）。
- **CDS (Credit Default Swap)**: 参照エンティティのデフォルトリスクを移転する保険類似のスワップ。§7.12 で紹介、Ch.25 で詳述。
- **Swaption**: 将来スワップに入る権利（オプション）。
- **Basis Swap**: 変動-変動の金利スワップ（異なる変動指標間の交換）。
- **Equity Swap**: エクイティ指数のトータルリターンと固定/変動金利を交換。

## 3. 主要公式

### IRS 一期間の固定キャッシュフロー（固定払い側）

$$
CF_{\text{fix},i} = -L \cdot s \cdot \tau_i
$$

- $L$: 名目元本
- $s$: 固定スワップレート（年率）
- $\tau_i$: 第 $i$ 期間の日数分数（例: actual/360 または actual/365）

<!-- Hull §7.4, day-count discussion -->

### IRS 一期間の変動キャッシュフロー（LIBOR/SOFR ベース）

$$
CF_{\text{fl},i} = L \cdot R_i \cdot \frac{n_i}{360}
$$

ここで $R_i$ は期間 $i$ の浮動参照レート（SOFR 等 actual/360 基準）、$n_i$ は日数。

<!-- Hull eq. day count, p.179 -->

### スワップ評価：債券ポートフォリオ・アプローチ

固定受取・変動払いのスワップ価値（domestic 観点）:

$$
V_{\text{swap}} = B_{\text{fix}} - B_{\text{fl}}
$$

$$
B_{\text{fix}} = \sum_{i=1}^{n} L \cdot s \cdot \tau_i \cdot P(0,t_i) + L \cdot P(0,t_n)
$$

変動利付債は、次の変動支払が已知の場合（$r^*$ = 既観測の短期レート）:

$$
B_{\text{fl}} = (L + L \cdot r^* \cdot \tau_1) \cdot P(0, t_1)
$$

すなわち**変動利付債は次の支払直後に額面に等しい**ため、評価が簡単。

<!-- Hull §7.6, bond decomposition -->

### スワップ評価：FRA（フォワードレート合意）アプローチ（Hull 推奨）

スワップ = FRA の列。各 FRA をフォワードレート実現と仮定して評価:

1. 各期間のフォワードレート $f_i$ を OIS ゼロカーブから計算
2. 変動キャッシュフローを $CF_{\text{fl},i} = L \cdot f_i \cdot \tau_i$ とおく
3. ネットキャッシュフロー $\Delta_i = CF_{\text{fl},i} - CF_{\text{fix},i}$
4. スワップ価値 $V = \sum_{i} \Delta_i \cdot e^{-r_i t_i}$（連続複利割引）

<!-- Hull §7.6, FRA approach, Example 7.1 (p.184) -->

### アット・マーケット・スワップレート（$V_{\text{swap}}=0$ の条件）

$$
s = \frac{1 - P(0, t_n)}{\sum_{i=1}^{n} \tau_i \cdot P(0, t_i)}
$$

分子は「名目元本1単位の最終ディスカウント因子の補数」、分母は「アニュイティ因子」。

<!-- Hull §7.2, par bond interpretation -->

### 通貨スワップ評価：債券アプローチ

ドルを受取り、外貨（外国通貨）を払うスワップの価値（ドル建て）:

$$
V_{\text{swap}} = B_D - S_0 \cdot B_F
$$

ドルを払い、外貨を受取るスワップ:

$$
V_{\text{swap}} = S_0 \cdot B_F - B_D
$$

ここで $B_D$: ドルキャッシュフローの現在価値（ドルレートで割引）、$B_F$: 外貨キャッシュフローの現在価値（外貨レートで割引・外貨単位）、$S_0$: 現在スポットレート（ドル/外貨）。

<!-- Hull §7.9, p.191 -->

### 比較優位論の総利得

固定市場のスプレッド差を $a$、変動市場のスプレッド差を $b$ とすると:

$$
\text{総利得} = a - b
$$

ただし $a > b$ のとき正の利得が生じ、スワップ取引の動機となる。

<!-- Hull §7.5, p.182 -->

## 4. アルゴリズム / 手順

### OIS ゼロカーブのブートストラップ（post-2010 標準）

1. 満期1年以下の OIS レートは単一交換 → そのまま連続複利ゼロレートに変換:
   $$r_{\text{zero}} = m \cdot \ln\!\left(1 + \frac{R_{\text{OIS}}}{m}\right)$$
   ここで $m$ は複利頻度（月次、四半期等）。
2. 満期1年超の OIS スワップレート $s_k$ は「パー債券のクーポン = $s_k$」と解釈:
   $$\sum_{i=1}^{k-1} s_k \cdot \tau \cdot e^{-r_i t_i} + (1 + s_k \cdot \tau) \cdot e^{-r_k t_k} = 1$$
   既知の $r_1, \ldots, r_{k-1}$ を使って $r_k$ を反復（Solver / Newton 法）で求める。
3. 中間満期は線形補間（または cubic spline）。

### スワップレート曲線からフォワード SOFR/LIBOR カーブのブートストラップ

1. OIS ゼロカーブ $\{r_i\}$ からディスカウント因子 $P(0,t_i) = e^{-r_i t_i}$ を計算。
2. 各スワップ期間 $(t_{i-1}, t_i]$ のフォワードレート（連続複利）:
   $$f_i = \frac{r_i t_i - r_{i-1} t_{i-1}}{t_i - t_{i-1}}$$
3. 最初の変動レートは通常すでに確定済み（観測済みの直近 SOFR）。
4. スワップレートは方程式 $\sum_i (f_i - s) \tau P(0,t_i) = 0$ を満たすため、整合性確認に使用。

### FRA アプローチによるスワップ評価手順

1. OIS ゼロカーブからフォワードレート $\{f_i\}$ を計算（上記 §4.2 参照）。
2. 各決済日 $t_i$ の固定キャッシュフロー: $CF_{\text{fix},i} = -L \cdot s \cdot \tau_i$
3. 各決済日の推定変動キャッシュフロー: $CF_{\text{fl},i} = L \cdot f_i \cdot \tau_i$（フォワード実現仮定）
4. ネット: $\Delta_i = CF_{\text{fl},i} + CF_{\text{fix},i}$（受取正、払い負）
5. 割引: $V = \sum_i \Delta_i \cdot e^{-r_i t_i}$
6. 例（Ex.7.1）: $L=100M$, $s=3\%$ semiannual, 残存1.2年。
   フォワードレート 2.50%/3.36%/3.68%（連続複利）→ $V = +\$0.292M$。

## 5. Python reference

```python
import numpy as np
from typing import Sequence


def swap_value_bond(
    notional: float, fixed_rate: float,
    payment_times: Sequence[float], floating_known_next: float,
    discount_factors: Sequence[float],
) -> float:
    """Receive-fixed IRS value via bond decomposition. V = B_fix - B_fl."""
    ts = np.asarray(payment_times)
    dfs = np.asarray(discount_factors)
    dt = np.diff(np.concatenate([[0.0], ts]))
    b_fix = np.sum(notional * fixed_rate * dt * dfs) + notional * dfs[-1]
    # floating bond resets to par after next coupon
    b_fl = (notional + notional * floating_known_next * dt[0]) * dfs[0]
    return float(b_fix - b_fl)


def swap_rate(
    payment_times: Sequence[float],
    discount_factors: Sequence[float],
) -> float:
    """At-market (par) swap rate: s = (1 - P(0,T)) / annuity_factor."""
    ts = np.asarray(payment_times)
    dfs = np.asarray(discount_factors)
    dt = np.diff(np.concatenate([[0.0], ts]))
    return float((1.0 - dfs[-1]) / np.dot(dt, dfs))


def swap_value_fra(
    notional: float, fixed_rate: float,
    payment_times: Sequence[float],
    forward_rates: Sequence[float],   # continuous, per period
    zero_rates: Sequence[float],       # continuous OIS zeros
) -> float:
    """Receive-fixed IRS value as portfolio of FRAs (Hull §7.6)."""
    ts = np.asarray(payment_times)
    dt = np.diff(np.concatenate([[0.0], ts]))
    dfs = np.exp(-np.asarray(zero_rates) * ts)
    net_cf = notional * (np.asarray(forward_rates) - fixed_rate) * dt
    return float(np.dot(net_cf, dfs))


def currency_swap_value(
    notional_d: float, coupon_d: float,
    notional_f: float, coupon_f: float,
    payment_times: Sequence[float],
    zero_d: Sequence[float], zero_f: Sequence[float],
    spot: float, receive_domestic: bool = True,
) -> float:
    """Fixed-for-fixed currency swap: V = B_D - S0*B_F (or reverse)."""
    ts = np.asarray(payment_times)
    dt = np.diff(np.concatenate([[0.0], ts]))
    dfs_d = np.exp(-np.asarray(zero_d) * ts)
    dfs_f = np.exp(-np.asarray(zero_f) * ts)
    b_d = float(np.dot(notional_d * coupon_d * dt, dfs_d) + notional_d * dfs_d[-1])
    b_f = float(np.dot(notional_f * coupon_f * dt, dfs_f) + notional_f * dfs_f[-1])
    return (b_d - spot * b_f) if receive_domestic else (spot * b_f - b_d)


# --- Verify: Hull Ex.7.1 (approximate) ---
if __name__ == "__main__":
    v = swap_value_fra(100.0, 0.03, [0.2, 0.7, 1.2],
                       [0.02516, 0.03388, 0.03714], [0.028, 0.032, 0.034])
    print(f"Ex7.1 swap value: ${v:.3f}M")  # expect ~+0.292M
```

## 6. 注意点 / 典型的なミス

- **デイカウントの混在**: 固定レートは actual/365 または 30/360、変動レートは actual/360 が多い。比較前に統一するか、各期間で正確に $\tau_i = n_i/\text{basis}$ を計算すること。
- **変動利付債の評価**: 「次の支払直後に額面に等しい」のは、変動レートが**当該期間開始時に確定**する LIBOR 型の場合。OIS（SOFR）は期間**終了時**に確定するため、最初のキャッシュフローの扱いが異なる（観測済み累積レートを使う）。
- **比較優位論の落とし穴**: 固定・変動スプレッドの非対称は信用リスクの満期差（固定は長期・変動は短期で更新）によるものが大半。スワップを組んでも「真の節約」にはならない可能性がある（Hull §7.5 批判を参照）。
- **通貨スワップの元本交換**: 金利スワップと異なり、通貨スワップでは開始・終了時に実際に元本を交換する。価値評価時に元本交換を含めた債券として扱うことが正しい。
- **OIS ディスカウント vs. LIBOR フォワード**: 2010年以降の市場慣行は「OIS でディスカウント、LIBOR/SOFR 先物でフォワードレートを推計」する dual-curve フレームワーク。単一カーブ（LIBOR でフォワードもディスカウントも計算）は古い手法。
- **スワップレート ≠ ゼロレート**: スワップレートはクーポン付き債券のパーレート（複数期間の平均的概念）。ゼロレート（スポットレート）とは異なる。ブートストラップで変換が必要。
- **符号規約**: receive-fixed 側は $V = B_{\text{fix}} - B_{\text{fl}}$、pay-fixed 側は逆符号。コードに渡す前に確認すること。

## 7. 関連トピック

- See: Ch.04 金利・ゼロカーブ・フォワードレート基礎 ([ch04_interest_rates.md](ch04_interest_rates.md))
- See: Ch.06 金利先物・ユーロドル先物・フォワードレート推定 ([ch06_ir_futures.md](ch06_ir_futures.md))
- See: Ch.09 XVA（CVA/DVA）— スワップの信用リスク調整
- See: Ch.25 Credit Derivatives（CDS 詳細）
- See: Ch.29 Interest Rate Derivatives: Standard Market Models（スワプション, Cap/Floor）
- See: Ch.34 Swaps Revisited（エキゾチックスワップ詳細）
- Topics: [topics/swaps.md](../topics/swaps.md)（未作成）, [topics/interest_rates.md](../topics/interest_rates.md)（未作成）
