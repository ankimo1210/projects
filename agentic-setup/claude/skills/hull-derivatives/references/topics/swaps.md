# Topic: Swaps — Vanilla & Exotic

## 対応章
- Ch.7 Swaps — [chapters/ch07_swaps.md](../chapters/ch07_swaps.md)
- Ch.34 Swaps Revisited — [chapters/ch34_swaps_revisited.md](../chapters/ch34_swaps_revisited.md)

## クイック公式

### パースワップレート（アット・マーケット固定レート）
$$s = \frac{1 - P(0, t_n)}{\displaystyle\sum_{i=1}^{n} \tau_i\,P(0, t_i)}$$
- $P(0, t_i) = e^{-r_i t_i}$: OIS ゼロカーブから計算したディスカウント因子
- $\tau_i$: 第 $i$ 決済期間の日数分数（actual/360 等）
- See: ch7 §3

### IRS 評価：債券分解アプローチ
$$V_{\text{swap}} = B_{\text{fix}} - B_{\text{fl}}$$
$$B_{\text{fl}} = (L + L r^* \tau_1)\,P(0, t_1)$$
- receive-fixed の場合; pay-fixed は符号を逆転する
- 変動利付債は次の支払直後に額面に戻る（LIBOR 型, 期首固定）
- See: ch7 §3

### IRS 評価：FRA ポートフォリオ・アプローチ（Hull 推奨）
$$V = \sum_{i=1}^{n} \bigl(f_i - s\bigr)\,\tau_i\,L\,e^{-r_i t_i}$$
- $f_i$: 期間 $i$ のフォワードレート（OIS/SOFR カーブから）
- See: ch7 §3

### 通貨スワップ評価
$$V = B_D - S_0\,B_F \quad \text{(receive domestic)}$$
- $B_D$: ドルキャッシュフローの PV, $B_F$: 外貨キャッシュフローの PV（外貨単位）
- $S_0$: スポット為替（国内通貨/外貨1単位）
- See: ch7 §3

### LIBOR-in-arrears 凸性調整
$$\hat{F} = F + \frac{F^2 \sigma^2 T \tau}{1 + F \tau}$$
- $F$: 標準フォワードLIBOR, $T$: レート観測・支払時点, $\tau$: 利払い期間
- See: ch34 §3

### CMS 凸性調整
$$\hat{s} = s_0 + \tfrac{1}{2}\,s_0^2\,\sigma^2 T\,\frac{G''(s_0)}{G'(s_0)}, \qquad G(s) = \sum_{i=1}^{n} \tau(1+s\tau)^{-i}$$
- $s_0$: フォワードスワップレート, $\sigma$: スワップレートのボラティリティ
- See: ch34 §3

### クアント（diff swap）調整
$$\hat{F}_f = F_f - \rho\,\sigma_f\,\sigma_X\,T$$
- $\rho$: 外国金利と為替（外貨/国内通貨）の相関; $\rho > 0$ → 調整は下方向
- See: ch34 §3

## 実装スニペット

```python
import numpy as np


def par_swap_rate(payment_times, discount_factors) -> float:
    """At-market IRS fixed rate: s = (1 - P(T_n)) / annuity.

    Args:
        payment_times: array of payment dates (years)
        discount_factors: OIS discount factors P(0, t_i)
    """
    ts  = np.asarray(payment_times)
    dfs = np.asarray(discount_factors)
    dt  = np.diff(np.concatenate([[0.0], ts]))
    return float((1.0 - dfs[-1]) / np.dot(dt, dfs))


def swap_value_fra(notional, fixed_rate,
                   payment_times, forward_rates, zero_rates) -> float:
    """Receive-fixed IRS via FRA portfolio (Hull §7.6).

    Args:
        forward_rates: forward rates for each period (continuous, p.a.)
        zero_rates:    OIS zero rates for discounting (continuous)
    """
    ts  = np.asarray(payment_times)
    dt  = np.diff(np.concatenate([[0.0], ts]))
    dfs = np.exp(-np.asarray(zero_rates) * ts)
    net = notional * (np.asarray(forward_rates) - fixed_rate) * dt
    return float(np.dot(net, dfs))


def cms_convexity_adjusted_rate(s0: float, sigma: float, T: float,
                                 payment_freq: int, swap_tenor: int) -> float:
    """CMS convexity-adjusted expected swap rate paid at T.

    Args:
        s0: forward swap rate (e.g. 0.04 for 4%)
        sigma: swap rate lognormal vol
        T: observation/payment time (years)
        payment_freq: coupon frequency of reference swap (e.g. 2=semiannual)
        swap_tenor: tenor of reference swap in years
    """
    m, n = payment_freq, swap_tenor * payment_freq
    tau  = 1.0 / m

    def G(s):
        return sum(tau * (1.0 + s * tau) ** (-i) for i in range(1, n + 1))

    ds = 1e-5
    g1 = (G(s0 + ds) - G(s0 - ds)) / (2 * ds)
    g2 = (G(s0 + ds) - 2 * G(s0) + G(s0 - ds)) / ds ** 2
    return s0 + 0.5 * s0 ** 2 * sigma ** 2 * T * (g2 / g1)


def libor_in_arrears_rate(F: float, sigma: float, T: float, tau: float) -> float:
    """Convexity-adjusted LIBOR for in-arrears payment.

    Adjusted rate = F + F^2*sigma^2*T*tau / (1 + F*tau)
    """
    return F + (F ** 2 * sigma ** 2 * T * tau) / (1.0 + F * tau)


# --- Quick checks ---
if __name__ == "__main__":
    # par swap rate: 3 semi-annual periods with flat 3% zero curve
    ts  = np.array([0.5, 1.0, 1.5])
    dfs = np.exp(-0.03 * ts)
    print(f"Par rate = {par_swap_rate(ts, dfs)*100:.4f}%")  # ~3.00%

    # LIBOR-in-arrears: F=4%, sigma=20%, T=1y, tau=0.25
    print(f"In-arrears adj = {libor_in_arrears_rate(0.04, 0.20, 1.0, 0.25)*100:.4f}%")

    # CMS 10Y rate, T=1y, semiannual, s0=4%, sigma=20%
    print(f"CMS adj = {cms_convexity_adjusted_rate(0.04, 0.20, 1.0, 2, 10)*100:.4f}%")
```

## デシジョンガイド

- **債券分解 vs FRA アプローチ**: Hull は FRA アプローチを推奨。どちらも同じ結果を出すが FRA アプローチはキャッシュフロー単位で調整しやすく、SOFR のような期末確定型変動レートへの拡張が明示的。変動利付債が「次の支払直後に額面に等しい」という性質は LIBOR（期首確定）のみ厳密に成立する。
- **OIS ディスカウント vs LIBOR/SOFR フォワード（Dual Curve）**: 2010年以降の市場標準は OIS（SOFR/SONIA 等）でディスカウント、SOFR 先物/OIS スワップでフォワードレートを推計する dual-curve。単一カーブ（LIBOR のみ）は旧慣行。
- **通常スワップで十分 vs 調整が必要な場面**: フォワードレート実現仮定（FRA アプローチ）は通常の IRS、step-up/amortizing swap、コンパウンディングスワップに有効。LIBOR-in-arrears（支払いが期首）、CMS（スワップレート参照）、diff/quanto swap（外貨建てレートを国内元本に適用）には凸性・タイミング・クアント調整が必要。
- **キャンセラブルスワップ → バミューダン・スワプション**: 単一キャンセル日ならブラックモデルのヨーロピアンスワプション価値を加算/減算。複数キャンセル日（バミューダン）は金利ツリーまたは LMM + Longstaff-Schwartz で評価。
- **クアント調整の符号確認**: $\rho > 0$（外国金利上昇時に外貨高）→ 調整はマイナス方向（$\hat{F}_f < F_f$）。符号を逆にすると系統的な過大評価になる。
