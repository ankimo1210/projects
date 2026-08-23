# Ch.20 Volatility Smiles and Volatility Surfaces

> **Source**: Hull 11e, Chapter 20 (pp. 451-469). Paraphrased summary for personal use.

## 1. 要点

- BSMモデルは一定ボラティリティを前提とするが、実際の市場ではオプションの行使価格・満期ごとにインプライドボラティリティが異なる（ボラティリティ・スマイル）。
- プット・コール・パリティはモデル仮定に依存しない無裁定条件であり、同一 $K$・$T$ のコールとプットのインプライドボラティリティは必ず等しい。
- FX オプションのスマイルは「U 字形」（ATM が最低）、株式オプションのスマイルは「下向きスキュー（スマーク）」（低行使価格の IV が高い）という形状の違いがある。
- 株式スキューの主因はレバレッジ効果・ボラティリティ・フィードバック効果・1987年クラッシュ後の「クラッシュフォビア」。
- インプライドボラティリティを行使価格と満期の二次元関数 $\sigma(K,T)$ として整理したものがボラティリティ・サーフェス（Table 20.2 参照）。

## 2. キー用語

- **volatility smile**: 同一満期オプションの IV を行使価格の関数としてプロットした曲線
- **volatility skew / smirk**: 低行使価格ほど IV が高い一方向の傾き（株式市場に典型）
- **volatility surface**: IV を $(K, T)$ の二次元関数として表した曲面 $\sigma(K, T)$
- **volatility term structure**: 行使価格を ATM に固定したときの IV の満期依存性
- **implied distribution**: ボラティリティ・スマイルから逆算されるリスク中立確率分布
- **crashophobia**: 1987 年型暴落の再来を警戒するトレーダー心理が低行使価格プットを割高にする現象（M. Rubinstein による命名）
- **sticky-strike**: IV が行使価格 $K$ の関数として固定されたと仮定するヘッジ規約
- **sticky-delta**: IV が $\Delta$（マネーネス）の関数として固定されたと仮定するヘッジ規約
- **minimum variance delta**: 株価と IV の負の相関を考慮した修正デルタ $\Delta_{\text{MV}}$
- **Breeden-Litzenberger**: コール価格の $K$ に関する二階偏微分からリスク中立密度を抽出する手法

## 3. 主要公式

### Put-call parity（配当利回り $q$ 付き）

$$
p + S_0 e^{-qT} = c + K e^{-rT}
$$

<!-- Hull eq. (20.1) -->

- この関係はモデル非依存の無裁定条件であるため、同一 $(K, T)$ のコールとプットの BSM 価格誤差は等しく、インプライドボラティリティも一致する。

### BSM 価格誤差の一致

$$
p_{\text{BS}} - p_{\text{mkt}} = c_{\text{BS}} - c_{\text{mkt}}
$$

<!-- Hull eq. (20.2) -->

### FX ボラティリティ・スマイル（定性的）

ATM（$K/S_0 = 1$）で最低、両翼（深い OTM コール・プット）で高い対称的 U 字形。implied distribution は対数正規より**両裾が厚い**（超過尖度あり）。

### 株式ボラティリティ・スキュー（定性的）

行使価格が高いほど IV が低い下向き傾き（スマーク）。implied distribution は対数正規より**左裾が厚く右裾が薄い**（負の歪度）。

### Risk-reversal（25Δ）

$$
\text{RR}_{25} = \sigma_{25\Delta C} - \sigma_{25\Delta P}
$$

- 正値 → コール翼の方が高い（FX では通常小さい正または負）。
- 株式ではレバレッジ効果により RR は大きな負値。

### Butterfly spread（25Δ）

$$
\text{BF}_{25} = \frac{1}{2}\left(\sigma_{25\Delta C} + \sigma_{25\Delta P}\right) - \sigma_{\text{ATM}}
$$

<!-- FX vol quoting convention -->

- スマイルの曲率（凸性）を表す。正値 → 翼が ATM より高い（U 字形）。

### Delta バケット表記

標準的な FX ボラティリティ・クォートは 5 点：10Δ Put / 25Δ Put / ATM / 25Δ Call / 10Δ Call。

### Breeden-Litzenberger（リスク中立密度の抽出）

$$
g(K) = e^{rT} \frac{\partial^2 c}{\partial K^2}
$$

<!-- Hull eq. (20A.1) -->

有限差分近似（間隔 $\delta$）：

$$
g(K) \approx e^{rT} \frac{c_1 + c_3 - 2c_2}{\delta^2}
$$

ここで $c_1, c_2, c_3$ は行使価格 $K-\delta, K, K+\delta$ のコール価格。

<!-- Hull eq. (20A.2) -->

### ボラティリティ・サーフェス

$$
\sigma = \sigma(K, T) \quad \text{（2 次元関数）}
$$

標準化表記では $K/S_0$（または $K/F_0$、あるいは $\frac{1}{\sqrt{T}}\ln(K/F_0)$）を横軸に用いる。後者は満期依存性を大幅に緩和する。

### Minimum variance delta

$$
\Delta_{\text{MV}} = \Delta_{\text{BSM}} + \mathcal{V}_{\text{BSM}} \frac{\partial E(\sigma_{\text{imp}})}{\partial S}
$$

株価上昇時に IV が低下する（$\partial E(\sigma_{\text{imp}})/\partial S < 0$、$\mathcal{V}_{\text{BSM}} > 0$）ため、$\Delta_{\text{MV}} < \Delta_{\text{BSM}}$。

## 4. アルゴリズム / 手順

### 1. ボラティリティ・スマイルの構築（市場オプション価格からの逆算）

1. 対象満期の各行使価格 $K_i$ について市場コール（またはプット）価格 $c_i^{\text{mkt}}$ を収集する。
2. 各 $(K_i, c_i^{\text{mkt}})$ に対して BSM 式を $\sigma$ について数値逆算（Brent 法など）し、$\sigma_i^{\text{imp}}$ を求める。
3. $(K_i/S_0,\ \sigma_i^{\text{imp}})$ をプロットしてスマイル曲線を得る。

### 2. スマイルの補間・外挿

1. 市場クォートが存在する格子点以外は補間が必要：スプライン、多項式、または SVI（Stochastic Volatility Inspired）パラメトリック形式を使用。
2. 外挿は翼部分の振る舞いに注意（ゼロ以下や急激な発散を防ぐ）。
3. 補間後の IV から再計算したコール価格が単調減少・凸であることを確認（バタフライ無裁定条件）。

### 3. ボラティリティ・サーフェスの構築（無裁定条件の保証）

1. 複数満期 $T_1 < T_2 < \cdots$ について各スマイルを構築する。
2. **カレンダー無裁定**：総分散 $\sigma^2(K,T) \cdot T$ が $T$ について単調非減少であることを確認。
3. **バタフライ無裁定**：各 $T$ でコール価格の $K$ に関する二階差分が非負（密度が非負）。
4. 違反箇所は補正または SVI パラメータ再フィット。

### 4. Breeden-Litzenberger によるリスク中立密度の抽出

1. ボラティリティ・サーフェスから密なグリッドでコール価格を計算（BSM に各スマイル IV を代入）。
2. 中心差分 $g(K) \approx e^{rT}(c(K+\delta)-2c(K)+c(K-\delta))/\delta^2$ を適用。
3. 得られた $g(K)$ が積分して 1 になることを確認（数値積分で検証）。

## 5. Python reference

```python
import math
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq


def bs_call(S, K, r, sigma, T, q=0.0):
    """Black-Scholes-Merton European call price."""
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)


def implied_vol(price, S, K, r, T, q=0.0, kind="call"):
    """Invert BSM to find implied volatility (Brent root-find)."""
    if kind == "call":
        f = lambda s: bs_call(S, K, r, s, T, q) - price
    else:
        # put via put-call parity: convert put price to call price first
        call_price = price + S * math.exp(-q * T) - K * math.exp(-r * T)
        f = lambda s: bs_call(S, K, r, s, T, q) - call_price
    return brentq(f, 1e-6, 5.0)


def smile_from_prices(strikes, prices, S, r, T, q=0.0, kind="call"):
    """Recover vol smile by inverting BSM at each strike."""
    return np.array(
        [implied_vol(p, S, K, r, T, q, kind) for K, p in zip(strikes, prices)]
    )


def implied_density_breeden_litzenberger(strikes, call_prices, r, T):
    """
    Estimate risk-neutral density f(K) = e^{rT} * d^2c/dK^2
    via central differences on a (roughly) uniform grid.
    """
    K = np.asarray(strikes, dtype=float)
    c = np.asarray(call_prices, dtype=float)
    d2c = np.zeros_like(c)
    # central difference for interior points; assumes roughly uniform spacing
    dK = np.diff(K)
    for i in range(1, len(K) - 1):
        h = 0.5 * (dK[i - 1] + dK[i])  # average spacing
        d2c[i] = (c[i + 1] - 2 * c[i] + c[i - 1]) / h**2
    return math.exp(r * T) * d2c


# ── Example: synthetic downward skew (equity-like) ──────────────────────────
S, r, T = 100.0, 0.02, 0.5
strikes = np.linspace(80, 120, 21)
# linearly declining vol: high IV for low strikes (skew)
true_vols = 0.20 + 0.10 * (S - strikes) / S
prices = np.array([bs_call(S, K, r, sv, T) for K, sv in zip(strikes, true_vols)])

recovered = smile_from_prices(strikes, prices, S, r, T)
print("max abs IV error:", float(np.max(np.abs(recovered - true_vols))))
# Expected: max abs IV error: ~0.0  (machine-precision)

density = implied_density_breeden_litzenberger(strikes, prices, r, T)
# Approximate integral to verify sums near 1 (only interior points used)
dK_uniform = strikes[1] - strikes[0]
print("approx density integral:", float(np.sum(density[1:-1]) * dK_uniform))
```

## 6. 注意点 / 典型的なミス

- **BSM インプライドボラティリティは「正しいボラティリティ」ではない**。誤ったモデル（BSM）が正しい市場価格を再現するための入力パラメータにすぎない。
- **株式スキューの根拠**：1987 年クラッシュ前は顕著なスキューが存在しなかった。ポスト・クラッシュ体制を前提とすること。レバレッジ効果（株価下落→ボラティリティ上昇）と「クラッシュフォビア」が主因。
- **Sticky-strike vs sticky-delta**：sticky-strike では株価変動後も同一 $K$ の IV が変わらないと仮定するためデルタ・ヘッジに誤差が生じやすい。sticky-delta は moneyness ベースなので方向性は改善するが、どちらも近似。
- **最小分散デルタ**：株式オプションでは BSM デルタをそのまま使うとオーバーヘッジになる。$\Delta_{\text{MV}}$ は常に $\Delta_{\text{BSM}}$ より小さい。
- **無裁定制約の見落とし**：スマイル補間でカレンダー無裁定（総分散単調性）またはバタフライ無裁定（密度非負性）を破ると裁定可能なサーフェスが生まれる。
- **モデルの役割**：BSM は市場の整合的補間ツール。異なるモデルに切り替えてもドル価格はほぼ不変だが、ギリシャ文字（特にデルタ）は変わる。

## 7. 関連トピック

- See: [topics/vol_smile_surface.md](../topics/vol_smile_surface.md), [topics/bsm.md](../topics/bsm.md) (Ch.15), [topics/greeks.md](../topics/greeks.md) (Ch.19)
- Ch.27: ローカル・ボラティリティ（Dupire）、Heston、SABR など、スマイルを内生的に生成するより柔軟なモデル群
- Ch.13/21: 二項木・数値手法（スマイル対応の実装）
- Ch.19: 最小分散デルタの前提となるギリシャ文字の定義
