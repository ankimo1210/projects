# Topic: Interest Rates, Bond Pricing & Duration

## 対応章
- Ch.4 Interest Rates — [chapters/ch04_interest_rates.md](../chapters/ch04_interest_rates.md)
- Ch.6 Interest Rate Futures — [chapters/ch06_ir_futures.md](../chapters/ch06_ir_futures.md)

## クイック公式

### 複利変換：m回/年 ↔ 連続複利
$$R_c = m \ln\!\left(1 + \frac{R_m}{m}\right), \qquad R_m = m\!\left(e^{R_c/m} - 1\right)$$
- $R_m$: m回複利年率, $R_c$: 連続複利年率
- See: ch4 §3

### 債券価格（連続複利ゼロレート使用）
$$B = \sum_{i=1}^{n} c_i\,e^{-R(t_i)\,t_i}$$
- $c_i$: 時刻 $t_i$ のキャッシュフロー, $R(t_i)$: 満期 $t_i$ のゼロレート（連続複利）
- See: ch4 §3

### フォワードレート
$$R_F = \frac{R_2 T_2 - R_1 T_1}{T_2 - T_1}$$
- $R_1, R_2$: 満期 $T_1 < T_2$ の連続複利ゼロレート
- See: ch4 §3

### FRA の価値（固定受取側）
$$V_{\text{FRA}} = L\,(R_K - R_F)\,(T_2 - T_1)\,e^{-R_2 T_2}$$
- $L$: 想定元本, $R_K$: 合意固定レート, $R_F$: 現在のフォワードレート
- See: ch4 §3

### Macaulay デュレーションと価格感応度
$$D = \frac{\sum_{i} t_i\,c_i\,e^{-y t_i}}{B}, \qquad \Delta B \approx -B D\,\Delta y$$
- $y$: 連続複利 YTM。離散複利の場合は修正デュレーション $D^* = D/(1+y/m)$ を使う
- See: ch4 §3

### コンベクシティ（2次補正）
$$C = \frac{\sum_{i} c_i\,t_i^2\,e^{-y t_i}}{B}, \qquad \frac{\Delta B}{B} \approx -D\,\Delta y + \tfrac{1}{2}\,C\,(\Delta y)^2$$
- 通常債では $C > 0$ → デュレーション単独より実際の価格変化は有利（long bond に有益）
- See: ch4 §3

### T-bond フューチャーズ価格（CTD 既知）
$$F_0 = (S_0 - I)\,e^{rT}$$
- $S_0$: CTD 債の現金（ダーティ）価格, $I$: 期間中クーポンの現在価値
- デュレーション・ベースのヘッジ比率: $N^* = P D_P / (V_F D_F)$
- See: ch6 §3

## 実装スニペット

```python
import numpy as np
from scipy.optimize import brentq


def bond_price(times, cashflows, zero_rates):
    """Bond price using continuous zero rates."""
    return float(np.dot(cashflows, np.exp(-zero_rates * times)))


def bond_duration(times, cashflows, ytm):
    """Macaulay duration (continuous-compounding YTM)."""
    pv = cashflows * np.exp(-ytm * times)
    return float(np.dot(times, pv) / pv.sum())


def bond_convexity(times, cashflows, ytm):
    """Convexity (continuous-compounding YTM)."""
    pv = cashflows * np.exp(-ytm * times)
    return float(np.dot(times**2, pv) / pv.sum())


def forward_rate(R1: float, T1: float, R2: float, T2: float) -> float:
    """Instantaneous forward rate for (T1, T2) from zero rates."""
    return (R2 * T2 - R1 * T1) / (T2 - T1)


def bootstrap_zero_curve(maturities, par_rates, freq: int = 2):
    """Bootstrap zero curve from par/swap rates (discrete coupon, freq per year).

    Returns array of continuous zero rates matching each maturity.
    """
    zeros = np.zeros(len(maturities))
    dt = np.diff(np.concatenate([[0.0], maturities]))

    for k, (T, s) in enumerate(zip(maturities, par_rates)):
        coupon = s / freq
        # Coupon PV sum for periods 1..k-1 using already-known zeros
        coupon_pv = sum(
            coupon * dt[j] * np.exp(-zeros[j] * maturities[j])
            for j in range(k)
        )
        # Solve: coupon_pv + (1 + coupon*dt[k]) * exp(-z*T) = 1
        final_cf = 1.0 + coupon * dt[k]
        zeros[k] = -np.log((1.0 - coupon_pv) / final_cf) / T
    return zeros


# --- Verification (Hull Table 4.2) ---
if __name__ == "__main__":
    times = np.array([0.5, 1.0, 1.5, 2.0])
    zeros = np.array([0.050, 0.058, 0.064, 0.068])
    cfs   = np.array([3.0, 3.0, 3.0, 103.0])

    price = bond_price(times, cfs, zeros)      # ~98.39
    ytm   = brentq(lambda y: bond_price(times, cfs, np.full_like(times, y)) - price,
                   -0.5, 5.0)
    D = bond_duration(times, cfs, ytm)
    C = bond_convexity(times, cfs, ytm)
    RF = forward_rate(0.030, 1.0, 0.040, 2.0)  # 0.050

    print(f"Price={price:.2f}, YTM={ytm:.4f}, D={D:.3f}, C={C:.3f}")
    print(f"Forward rate(1,2)={RF:.4f}")
```

## デシジョンガイド

- **ゼロレート vs パーイールド vs YTM**: ゼロレートはスポットレートで割引に直結する。パーイールドはゼロレートから計算されるスワップ/クーポン設定の指標。YTMは単一割引率の便宜的概念であり、カーブがフラットでない限りゼロレートとは一致しない。
- **デュレーション vs コンベクシティの使い分け**: $|\Delta y| < 50$ bps ならデュレーション単独で十分な精度。100 bps を超える大幅シフト（ストレステスト等）ではコンベクシティ補正が必須。
- **デイカウント規則の選択**: 米国T-bond の経過利息は actual/actual (in period)。社債・地方債は 30/360。マネーマーケット商品（T-bill, LIBOR/SOFR, FRA）は actual/360（米）または actual/365（英）。混在するとダーティ価格計算が狂う。
- **連続複利 vs 離散複利**: Hull の公式群は連続複利が標準。市場クォート（半年複利、年複利）から変換してから計算すること。変換漏れはFRA評価や先物価格計算の誤りに直結する。
- **デュレーション・ヘッジの限界**: 平行シフト仮定に基づくため、ツイスト（長短独立シフト）には対応しない。キーレートデュレーション（バケット別）やDV01ヘッジが補完手段。ヘッジ期間中にCTD債が変わった場合は $N^*$ を再計算する。
