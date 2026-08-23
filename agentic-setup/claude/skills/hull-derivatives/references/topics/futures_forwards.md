# Topic: Futures & Forwards Pricing

## 対応章
- Ch.2 Futures Markets and Central Counterparties — [chapters/ch02_futures_markets.md](../chapters/ch02_futures_markets.md)
- Ch.5 Determination of Forward and Futures Prices — [chapters/ch05_forward_futures_pricing.md](../chapters/ch05_forward_futures_pricing.md)
- Ch.6 Interest Rate Futures — [chapters/ch06_ir_futures.md](../chapters/ch06_ir_futures.md)

## クイック公式

### 基本フォワード価格（収入なし）
$$F_0 = S_0 e^{rT}$$
- $S_0$: 現在スポット価格, $r$: 連続複利リスクフリー金利, $T$: 満期（年）
- See: ch5 §3

### 既知現金収入・連続利回りあり
$$F_0 = (S_0 - I)\,e^{rT}, \qquad F_0 = S_0\,e^{(r-q)T}$$
- $I$: 期間中キャッシュ収入の現在価値, $q$: 連続配当利回り
- 株価指数先物では $I=0$ で $q$ を使う; クーポン付き債券では $q=0$ で $I$ を使う
- See: ch5 §3

### FX フォワード（カバー付き金利平価）
$$F_0 = S_0\,e^{(r - r_f)T}$$
- $r_f$: 外国通貨の連続複利リスクフリー金利; $S_0$: 国内通貨 / 外貨1単位
- See: ch5 §3

### コスト・オブ・キャリー統合形
$$c = r + u - q - r_f, \qquad F_0 = S_0\,e^{cT} \; (\text{投資資産}), \qquad F_0 = S_0\,e^{(c-y)T} \; (\text{消費資産})$$
- $u$: 保管コスト（比率）, $y$: コンビニエンス・イールド（消費資産のみ）
- See: ch5 §3

### ロング・フォワード契約の価値
$$f = (F_0 - K)\,e^{-rT}$$
- $K$: 契約締結時の固定デリバリー価格（変化しない）
- See: ch5 §3

### T-bond フューチャーズ インボイス価格
$$\text{Cash received} = (\text{Settlement price} \times \text{CF}) + \text{Accrued interest}$$
- CF: コンバージョン・ファクター（6%クーポン・6%利回りで評価した額面比）
- See: ch6 §3

### ユーロドル先物 凸性調整
$$\text{Forward Rate} = \text{Futures Rate} - \tfrac{1}{2}\sigma^2 t_1 t_2$$
- $\sigma$: 短期金利の年次ボラティリティ, $t_1$: 先物満期, $t_2$: レート適用期間終了
- 調整は必ず正 → フォワードレート < 先物レート
- See: ch6 §3

## 実装スニペット

```python
import numpy as np


def forward_price(S0: float, r: float, T: float,
                  q: float = 0.0, I: float = 0.0) -> float:
    """Forward/futures price for an investment asset.

    Usage:
    - No income:        forward_price(S0, r, T)
    - Known cash I:     forward_price(S0, r, T, I=I)
    - Continuous yield: forward_price(S0, r, T, q=q)
    - FX forward:       forward_price(S0, r_dom, T, q=r_for)
    """
    return (S0 - I) * np.exp((r - q) * T)


def fx_forward(S0: float, r_dom: float, r_for: float, T: float) -> float:
    """FX forward rate via covered interest rate parity.

    S0: spot (domestic per 1 unit of foreign).
    """
    return S0 * np.exp((r_dom - r_for) * T)


def forward_value(F0: float, K: float, r: float, T: float) -> float:
    """Current value of a long forward contract: (F0 - K)*exp(-rT)."""
    return (F0 - K) * np.exp(-r * T)


def eurodollar_convexity_adj(futures_rate: float, sigma: float,
                             t1: float, t2: float) -> float:
    """Convexity-adjusted forward rate from Eurodollar/SOFR futures.

    forward_rate = futures_rate - 0.5*sigma^2*t1*t2

    Args:
        futures_rate: quoted rate (e.g. 0.033 for 3.3%)
        sigma: annual volatility of short rate
        t1: futures expiry (years)
        t2: end of rate application period (years)
    """
    return futures_rate - 0.5 * sigma**2 * t1 * t2


# --- Quick verification (Hull Ch.5 examples) ---
if __name__ == "__main__":
    # Ex5.5 index: S0=1300, r=5%, q=1%, T=0.25 -> 1313.07
    print(f"Index F0 = {forward_price(1300, 0.05, 0.25, q=0.01):.2f}")
    # Ex5.6 FX: S0=0.75 AUD, r_dom=1%, r_for=3%, T=2 -> 0.7206
    print(f"FX F0 = {fx_forward(0.75, 0.01, 0.03, 2):.4f}")
    # Convexity adj: sigma=1.2%, t1=5, t2=5.25
    print(f"Fwd after adj = {eurodollar_convexity_adj(0.065, 0.012, 5.0, 5.25)*100:.4f}%")
```

## デシジョンガイド

- **フォワード vs 先物**: 先物は日次決済（marking-to-market）があるため中間的な現金流出入が発生する。金利と先物原資産価格が正相関なら先物価格 > フォワード価格（実務上の短期では差は小）。デフォルトリスクは先物のほうが低い（CCPが保証）。
- **インデックス形 vs FX形**: 株価指数は連続利回り $q$ を使う（$F_0 = S_0 e^{(r-q)T}$）。FX も同形だが $q = r_f$（外国金利）と解釈する。既知の現金収入（クーポン等）がある場合は $I$ を使う形を選ぶ。
- **消費資産への等号適用は不可**: 原油・コーンなどの消費資産は $F_0 \leq (S_0+U)e^{rT}$ の不等号のみ。コンビニエンス・イールド $y$ はフォワードから逆算する内生変数。
- **凸性調整が重要な場面**: 満期が長い（2年超）ユーロドル/SOFR先物からフォワードレートを推計するときは必ず調整する。短期（3ヶ月以内）では無視できる。
- **T-bond フューチャーズの CTD 変化**: イールドが6%を超えると低クーポン長期債がCTDになりやすい。ヘッジ期間中にイールドが変動するとCTDが変わり、ヘッジ比率を再調整が必要。
