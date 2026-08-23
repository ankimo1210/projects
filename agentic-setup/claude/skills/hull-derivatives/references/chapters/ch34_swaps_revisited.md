# Ch.34 Swaps Revisited

> **Source**: Hull 11e, Chapter 34 (pp. 773-784). Paraphrased summary for personal use.

## 1. 要点

- 大半の非標準スワップは「フォワードレートが実現すると仮定する」アプローチで評価できる。元本変動スワップ（step-up / amortizing）、両サイドで元本・頻度が異なるスワップ、コンパウンディングスワップがこれに該当する。
- フォワードレート実現仮定が使えない場合は Ch.30 の **凸性・タイミング・クアント調整**を適用する。ペイメントタイミングが自然でない（LIBOR-in-arrears）・レートが別通貨建て（diff swap）・スワップレートそのものを参照（CMS）する場合が典型。
- **エクイティスワップ**はインデックスのリターンを固定または浮動レートと交換する。ペイメント直後の価値はゼロ; 期中はインデックスと浮動レートの現在価値差として評価する。
- **アクルアルスワップ**は参照レートが一定レンジ内にある日数のみ固定クーポンが発生する構造で、バイナリキャップレットの集合として評価できる。
- **キャンセラブルスワップ**は普通スワップ＋レシーバー/ペイヤー・スワプションと等価。複数キャンセル日がある場合はバミューダン型スワプション（LSM またはツリー）で評価する。

## 2. キー用語

- **Step-up swap**: 元本が時間とともに増加する金利スワップ。
- **Amortizing swap**: 元本が時間とともに減少する金利スワップ。
- **Basis swap**: 二つの浮動参照レートを交換するスワップ。
- **Compounding swap**: 途中のクーポンを再投資・複利積算し、満期一括で支払うスワップ。
- **LIBOR-in-arrears swap**: 金利の観測と支払いが同じ期末に行われるスワップ（標準では観測は期首）。凸性調整が必要。
- **CMS (Constant Maturity Swap)**: 浮動レグが特定年限のスワップレート（例: 10年スワップレート）を参照するスワップ。CMS凸性調整が必要。
- **CMS spread swap**: 二つのCMSレート（例: 10Y − 2Y）の差を参照するスワップ。
- **Differential (diff/quanto) swap**: 外国通貨建ての浮動レートを国内通貨の元本に適用するスワップ。クアント調整が必要。
- **Equity swap**: 株式インデックスのトータルリターンを固定または浮動レートと交換するスワップ。
- **Accrual swap**: 参照レートが指定レンジ内の日のみ固定クーポンが発生するスワップ。バイナリキャップレットの集合と見なせる。
- **Cancellable swap**: 一方に指定日に解約するオプションを与えたスワップ。スワプション内包。
- **Index amortizing rate swap**: 金利水準に依存して元本が減少する。低金利ほど元本減少が大きい。
- **Commodity swap**: 商品の固定価格と変動市場価格を交換するスワップ。

## 3. 主要公式

### コンパウンディングスワップの価値（例示）

$$
V = \frac{C_{\text{float, compounded}} - C_{\text{fixed, compounded}}}{P(0, T)}
$$

- フォワードレートを全期間に適用して浮動側を積算し、割引率（OIS）で現在価値化する。

<!-- Hull eq. Example 34.1 -->

### LIBOR-in-arrears 凸性調整

$$
\hat{F} = F + \frac{F^2 \sigma^2 \tau T}{1 + F \tau}
$$

- $F$: フォワードLIBOR
- $\sigma$: LIBORのボラティリティ
- $T$: レート観測時点（= 支払時点）
- $\tau$: 利払い期間（例: 0.25 for 3M）

<!-- Hull Ch.30 convexity adjustment, applied in Ch.34 -->

### CMS 凸性調整（簡略）

$$
\hat{s} = s_0 + \frac{1}{2} s_0^2 \sigma^2 T \cdot \frac{G''(s_0)}{G'(s_0)}
$$

- $s_0$: フォワードスワップレート
- $G(s)$: スワップの annuity 関数
- $G''/ G'$: 曲率項（テナーと $s_0$ に依存）

<!-- Hull §34.3 / Ch.30 eq. (30.1) -->

### クアント（diff swap）調整

$$
\hat{F}_f = F_f - \rho \sigma_f \sigma_X T
$$

- $F_f$: 外国通貨のフォワードレート
- $\sigma_f$: 外国金利のボラティリティ
- $\sigma_X$: 為替レート（外貨/国内通貨）のボラティリティ
- $\rho$: 外国金利と為替の相関

<!-- Hull Ch.30 eq. (30.5) -->

### アクルアルスワップ — バイナリオプション分解

各日 $i$ に対応するバイナリオプション価値:

$$
V_i = \frac{QL}{n_2} P(0, s_i) N(d_2^*)
$$

$$
d_2 = \frac{\ln(F_i / R_K) - \sigma_i^2 t_i / 2}{\sigma_i \sqrt{t_i}}
$$

- $Q$: 固定レート, $L$: 元本, $n_2$: 年の日数
- $F_i$: 日 $i$ の参照レートのフォワード値
- $R_K$: カットオフレート
- $d_2^*$: タイミング調整済み $d_2$（通常近似的に $d_2$ と同値）

<!-- Hull §34.5 -->

### エクイティスワップの期中価値（receive-equity 側）

$$
V = L \cdot \frac{E - E_0}{E_0} - \text{PV(次回浮動払い)}
$$

- $L$: 元本, $E$: 現在のインデックス水準, $E_0$: 直前ペイメント日のインデックス水準

<!-- Hull §34.4 -->

## 4. アルゴリズム / 手順

### 1. LIBOR-in-arrears スワップ評価

1. 各期の標準フォワードレート $F_i$ を OIS/SOFR イールドカーブから計算する。
2. 凸性調整: $\hat{F}_i = F_i + F_i^2 \sigma_i^2 \tau T_i / (1 + F_i \tau)$。
3. 調整済みフォワードレートで現金フローを算出し、OIS割引率で現在価値化する。

### 2. CMS レート調整

1. フォワードスワップレート $s_0$ を現在のスワップカーブから計算する。
2. $G(s) = \sum_{i=1}^{n} \tau (1+s\tau)^{-i}$ を定義し、$G'(s_0)$, $G''(s_0)$ を計算する。
3. CMS調整: $\hat{s} = s_0 + \frac{1}{2} s_0^2 \sigma^2 T \cdot G''(s_0)/G'(s_0)$。
4. 調整済みレートで固定・浮動のキャッシュフローを計算し、OISで割引く。

### 3. クアント（diff）スワップ評価

1. 外国通貨のフォワードレート $F_f$ を外国カーブから計算する。
2. クアント調整: $\hat{F}_f = F_f - \rho \sigma_f \sigma_X T$。
3. 調整後レートを国内通貨元本に適用してキャッシュフローを算出し、国内OISで割引く。

### 4. アクルアルスワップ評価（バイナリキャップレット分解）

1. スワップ存続期間の各日 $i$ について、参照レートのフォワード $F_i$ とボラティリティ $\sigma_i$ を取得する。
2. $d_2 = [\ln(F_i/R_K) - \sigma_i^2 t_i/2] / (\sigma_i \sqrt{t_i})$ を計算する（$R_K$ はレンジ境界）。
3. 各日のバイナリ価値 $= (QL/n_2) P(0, s_i) N(d_2^*)$ を計算し合計する。
4. 浮動レグは通常の「フォワードレート実現仮定」で評価する。

### 5. キャンセラブルスワップ評価（バミューダンスワプション）

1. スワップを「普通スワップ ＋ スワプション」に分解する（レシーブ固定 → ペイヤースワプション内包）。
2. 単一キャンセル日の場合: ブラックモデルでヨーロピアンスワプションを評価（Ch.29）。
3. 複数キャンセル日の場合: Ch.32 の金利ツリーまたは Ch.33 の LMM + LSM（Longstaff-Schwartz, Ch.21）で評価する。
4. キャンセラブルコンパウンディングスワップ: OIS/SOFR フラット仮定で浮動側を debt に変換し、ツリーで固定側のみ評価する。

## 5. Python reference

```python
import math
import numpy as np
from scipy.stats import norm


def libor_in_arrears_adjustment(F: float, sigma: float, T: float, tau: float) -> float:
    """Adjust forward LIBOR for in-arrears payment.

    Standard caplet: rate set at T, paid at T+tau (T+tau-forward measure).
    In-arrears:      rate set at T, paid at T (same time) -> convexity adjustment.

    Adjusted rate ≈ F + F^2 * sigma^2 * T * tau / (1 + F*tau)
    """
    return F + (F**2 * sigma**2 * T * tau) / (1 + F * tau)


def cms_convexity_adjustment(
    s0: float, sigma: float, T: float, payment_freq: int, swap_tenor: int
) -> float:
    """First-order CMS convexity adjustment.

    CMS floats a swap rate (e.g., 10Y) observed at T and paid immediately.
    Adjustment depends on G''/G' of the annuity function G(s).
    """
    m = payment_freq
    n = swap_tenor * m
    tau = 1.0 / m

    def G(s: float) -> float:
        return sum(tau * (1 + s * tau) ** (-i) for i in range(1, n + 1))

    ds = 1e-5
    g0 = G(s0)
    g1 = (G(s0 + ds) - G(s0 - ds)) / (2 * ds)
    g2 = (G(s0 + ds) - 2 * g0 + G(s0 - ds)) / ds**2

    return s0 + 0.5 * s0**2 * sigma**2 * T * (g2 / g1)


def quanto_swap_adjustment(
    F_foreign: float, sigma_F: float, sigma_X: float, rho: float, T: float
) -> float:
    """Quanto-adjust a foreign forward rate for domestic-currency payment.

    Positive rho (rate rises when foreign currency strengthens) -> adjustment lowers rate.
    """
    return F_foreign - rho * sigma_F * sigma_X * T


def accrual_swap_binary_value(
    F_list: list, sigma_list: list, t_list: list, s_list: list,
    R_K: float, Q: float, L: float, n2: int,
    r: float
) -> float:
    """Value the fixed-side accrual of an accrual swap via binary caplet decomposition.

    Each day i the fixed coupon accrues only if reference rate < R_K.
    Binary caplet value for day i = (Q*L/n2) * P(0, s_i) * N(d2_star_i)
    """
    total = 0.0
    for F_i, sigma_i, t_i, s_i in zip(F_list, sigma_list, t_list, s_list):
        if sigma_i <= 0 or t_i <= 0:
            continue
        d2 = (math.log(F_i / R_K) - 0.5 * sigma_i**2 * t_i) / (sigma_i * math.sqrt(t_i))
        P_0_si = math.exp(-r * s_i)
        total += (Q * L / n2) * P_0_si * norm.cdf(-d2)  # accrues when R_i < R_K
    return total


# --- Examples ---
print("LIBOR-in-arrears adjustment:")
print(f"  F=4%, sigma=20%, T=1y, tau=0.25 -> {libor_in_arrears_adjustment(0.04, 0.20, 1.0, 0.25):.6f}")

print("CMS convexity adjustment (10Y swap rate, T=1y, semiannual):")
print(f"  s0=4%, sigma=20% -> {cms_convexity_adjustment(0.04, 0.20, 1.0, 2, 10):.6f}")

print("Quanto-adjusted AUD forward rate:")
print(f"  F_AUD=5%, sig_F=25%, sig_X=15%, rho=0.3, T=1y -> "
      f"{quanto_swap_adjustment(0.05, 0.25, 0.15, 0.3, 1.0):.6f}")
```

## 6. 注意点 / 典型的なミス

- **LIBOR-in-arrears**: レートの観測と支払いが同じ日のため、自然な T+τ 先渡し測度での期待値が標準フォワードと一致しない。調整を省略すると系統的に過小評価になる。
- **CMS調整**: CMSレートは単一クーポン日に「自然に」支払われる量ではない。調整量はスワップレートのボラティリティとスキューに依存するため、Black-Scholes的単純近似（平坦スマイル仮定）は誤差が大きくなることがある。精緻化にはスワップレートのスマイル（SABR等）が必要。
- **クアント調整の符号**: 外国金利と為替（外貨/国内）の相関が正（外国金利上昇時に外貨高）のとき、クアント調整はマイナス方向に働く（調整後フォワードが低下）。符号を逆にしやすい。
- **アクルアルスワップ**: ボラティリティスマイルが重要。参照レートが境界付近に分布しているとき、スマイルの形状が価値に大きく影響する。フラットボル仮定は過近似。
- **キャンセラブルスワップの分解**: レシーブ固定キャンセラブルスワップの保有者は固定受け取り方向なので、ペイヤースワプションを保有していると見なす（方向を間違えやすい）。バミューダン構造はヨーロピアン近似では過小評価になる。
- **コンパウンディングスワップ**: 「フォワードレート実現仮定」はスプレッド $s_x$ がゼロか、複利積算が $R+s_x$ で行われる場合のみ厳密に成立する。それ以外は小さな近似誤差が生じる（Hull Technical Note 18 参照）。
- **エクイティスワップの期中評価**: ペイメント直後は価値ゼロだが、期中は過去のインデックスリターン（$E/E_0 - 1$）の元本相当分と、次回浮動払いの現在価値の差として評価する必要がある。

## 7. 関連トピック

- See: [topics/swaps.md](../topics/swaps.md), [ch07_swaps.md](ch07_swaps.md) (基本スワップの評価), [ch30_convexity_timing_quanto.md](ch30_convexity_timing_quanto.md) (凸性・タイミング・クアント調整 — 本章全体の基盤), [ch29_ir_std_models.md](ch29_ir_std_models.md) (ブラックモデル — スワプション評価), [ch33_forward_rate_models.md](ch33_forward_rate_models.md) (LMM — パス依存評価), [ch21_basic_numerical.md](ch21_basic_numerical.md) (LSM — バミューダンスワプション).
