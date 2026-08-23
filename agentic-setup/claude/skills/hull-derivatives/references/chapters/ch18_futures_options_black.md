# Ch.18 Futures Options and Black's Model

> **Source**: Hull 11e, Chapter 18 (pp. 401-416). Paraphrased summary for personal use.

## 1. 要点

- 先物オプション（futures option）は、行使すると先物ポジション＋キャッシュを取得する権利。コールならロング先物＋ $(F-K)$、プットならショート先物＋ $(K-F)$。
- 先物価格はリスク中立世界でドリフトゼロ（配当利回り $q=r$ の株と同等）。これがBlack's Modelの核心的な直観。
- Black's Model（1976）はBSMに $q=r$（先物はゼロコスト資産）を代入した形で、ヨーロピアン先物オプション・現物オプション両方を同じ式で評価できる。
- プット・コール・パリティ：$c + Ke^{-rT} = p + F_0 e^{-rT}$（株式の式の $S_0$ が $F_0 e^{-rT}$ に置き換わる）。
- アメリカン先物オプションは正の金利下では早期行使の可能性があり、対応するヨーロピアンより高い。二項ツリーで評価するとき成長因子 $a=1$（先物はコストゼロ）。

## 2. キー用語

- **Futures option（先物オプション）**: 行使により先物ポジションとキャッシュフローを得る権利。満期前にいつでも行使可能（通常アメリカン）。
- **Black's model**: Fischer Black (1976) が提唱した先物オプション価格式。先物価格が対数正規分布に従うと仮定。
- **Risk-neutral drift of futures price**: リスク中立世界で先物価格の期待値は現在の先物価格と等しい（ドリフト＝0）。
- **Futures-style option**: オプションのペイオフ自体を先物化した契約。証拠金制で取引される。Put-call parity: $p + F_0 = c + K$。
- **Put-call parity for futures options**: $c + Ke^{-rT} = p + F_0 e^{-rT}$ （式 18.1）。
- **Lower bounds**: ヨーロピアン先物コール $c \geq \max((F_0-K)e^{-rT}, 0)$、プット $p \geq \max((K-F_0)e^{-rT}, 0)$。

## 3. 主要公式

### 先物オプションのペイオフ（満期時）

$$
\text{Call payoff} = \max(F_T - K,\; 0)
$$
$$
\text{Put payoff} = \max(K - F_T,\; 0)
$$

- $F_T$: 行使時点の先物価格
- $K$: 行使価格（strike）

<!-- Hull eq. (18.1 context) -->

---

### プット・コール・パリティ（先物オプション）

$$
c + K e^{-rT} = p + F_0 e^{-rT}
$$

<!-- Hull eq. (18.1) -->

- $c, p$: ヨーロピアン先物コール／プット価格
- $F_0$: 現在の先物価格
- $r$: 無リスク金利、$T$: 満期までの期間

---

### Black's Model — ヨーロピアン先物コール

$$
c = e^{-rT}\bigl[F_0\, N(d_1) - K\, N(d_2)\bigr]
$$

<!-- Hull eq. (18.7) -->

### Black's Model — ヨーロピアン先物プット

$$
p = e^{-rT}\bigl[K\, N(-d_2) - F_0\, N(-d_1)\bigr]
$$

<!-- Hull eq. (18.8) -->

### $d_1$, $d_2$ の定義

$$
d_1 = \frac{\ln(F_0/K) + \sigma^2 T/2}{\sigma\sqrt{T}}, \qquad d_2 = d_1 - \sigma\sqrt{T}
$$

- $\sigma$: 先物価格のボラティリティ（コスト・オブ・キャリーと便宜利回りが時間の関数のみなら原資産ボラティリティと一致）
- $N(\cdot)$: 標準正規分布の累積分布関数

**等価関係**: Black's model = BSM で配当利回り $q = r$ と設定した式。先物はゼロコスト資産（保有コスト＝金利収益で相殺）なので $q=r$ となる。

---

### 先物価格のSDE（リスク中立世界）

$$
dF = \sigma F\, dz
$$

<!-- Hull eq. (18.5) -->

ドリフト項がゼロ。これは先物が $q=r$ の配当支払い株と同様に振る舞うことを示す。

---

### American先物オプションの二項ツリー（リスク中立確率）

$$
p = \frac{1 - d}{u - d}
$$

<!-- Hull eq. (18.10) -->

- $u = e^{\sigma\sqrt{\Delta t}}$, $d = e^{-\sigma\sqrt{\Delta t}}$（または $d = 1/u$）
- 先物のグロースファクター $a=1$（先物ポジションはコストゼロ）→ $p = (1-d)/(u-d)$
- オプション価値: $f = e^{-rT}[p f_u + (1-p) f_d]$

<!-- Hull eq. (18.9) -->

---

### ヨーロピアン先物オプションの下限

$$
c \geq \max\!\bigl((F_0 - K)e^{-rT},\; 0\bigr), \quad p \geq \max\!\bigl((K - F_0)e^{-rT},\; 0\bigr)
$$

<!-- Hull eq. (18.3), (18.4) -->

## 4. アルゴリズム / 手順

### アルゴリズム1: Black's Modelによるヨーロピアン先物オプション（解析解）

1. 入力: $F_0, K, r, \sigma, T$
2. $d_1 = [\ln(F_0/K) + \sigma^2 T/2] / (\sigma\sqrt{T})$ を計算
3. $d_2 = d_1 - \sigma\sqrt{T}$ を計算
4. コール: $c = e^{-rT}[F_0 N(d_1) - K N(d_2)]$
5. プット: $p = e^{-rT}[K N(-d_2) - F_0 N(-d_1)]$
6. 検証: プット・コール・パリティ $c + Ke^{-rT} = p + F_0 e^{-rT}$ が成立するか確認

### アルゴリズム2: 二項ツリーによるアメリカン先物オプション

1. 入力: $F_0, K, r, \sigma, T$, ステップ数 $n$
2. $\Delta t = T/n$, $u = e^{\sigma\sqrt{\Delta t}}$, $d = 1/u$ を計算
3. リスク中立確率: $p = (1-d)/(u-d)$ （先物の成長因子 $a=1$）
4. 先物価格ツリーを構築: $F_{i,j} = F_0 \cdot u^j \cdot d^{i-j}$（$i$: ステップ, $j$: アップ回数）
5. 満期ペイオフを計算: コール $\max(F_{n,j}-K, 0)$、プット $\max(K-F_{n,j}, 0)$
6. 後ろ向き帰納法でオプション価値を計算。各ノードで継続価値と即時行使価値の大きい方を選択（アメリカン早期行使条件）
7. ルートノードの値が現在のオプション価格

## 5. Python reference

```python
import math
from scipy.stats import norm


def black_futures_call(F, K, r, sigma, T):
    """Black's model: European call on futures."""
    d1 = (math.log(F / K) + 0.5 * sigma**2 * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return math.exp(-r * T) * (F * norm.cdf(d1) - K * norm.cdf(d2))


def black_futures_put(F, K, r, sigma, T):
    """Black's model: European put on futures."""
    d1 = (math.log(F / K) + 0.5 * sigma**2 * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return math.exp(-r * T) * (K * norm.cdf(-d2) - F * norm.cdf(-d1))


def american_futures_option_binomial(F, K, r, sigma, T, n, option_type="call"):
    """American futures option via binomial tree (a=1, so p=(1-d)/(u-d))."""
    dt = T / n
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (1.0 - d) / (u - d)          # growth factor a=1 for futures
    disc = math.exp(-r * dt)

    # Terminal futures prices and payoffs
    futures = [F * u**j * d**(n - j) for j in range(n + 1)]
    if option_type == "call":
        vals = [max(f - K, 0.0) for f in futures]
    else:
        vals = [max(K - f, 0.0) for f in futures]

    # Backward induction with early exercise
    for i in range(n - 1, -1, -1):
        for j in range(i + 1):
            f_node = F * u**j * d**(i - j)
            hold = disc * (p * vals[j + 1] + (1 - p) * vals[j])
            if option_type == "call":
                exercise = max(f_node - K, 0.0)
            else:
                exercise = max(K - f_node, 0.0)
            vals[j] = max(hold, exercise)
    return vals[0]


# Example (Hull Example 18.6: European put, F=20, K=20, r=9%, sigma=25%, T=4/12)
print(black_futures_call(F=100, K=100, r=0.05, sigma=0.20, T=0.5))  # ~5.573
print(black_futures_put(F=100, K=100, r=0.05, sigma=0.20, T=0.5))   # ~5.573
print(black_futures_put(F=20, K=20, r=0.09, sigma=0.25, T=4/12))    # ~1.12
```

## 6. 注意点 / 典型的なミス

- **早期行使とアメリカン価値**: 正の金利下ではアメリカン先物オプション（コール・プット両方）に早期行使の可能性がある。スポットオプションとは異なりコールも早期行使され得る点に注意。
- **$F_0$ vs $S_0$ の混同**: Black's modelの $F_0$ は先物価格（割引不要）であり、BSMの $S_0$ ではない。先物価格が既にキャリーを反映している。
- **二項ツリーで $a=1$**: 先物はポジション開始コストがゼロのため成長因子 $a=1$（株式の $a=e^{r\Delta t}$ とは異なる）。
- **先物・スポット同時満期の場合のみ等価**: ヨーロピアン先物オプション＝スポットオプションは先物契約とオプションが同時に満期を迎える場合のみ成立する。
- **現物オプションへの応用**: Black's modelは通貨・株価指数・金利デリバティブの現物オプション評価にも広く使われる。その際 $F_0$ には先物価格の代わりに先渡価格を使うことが多い（金利が確定的なら等価）。
- **ボラティリティの解釈**: Black's modelの $\sigma$ は先物価格のボラティリティ。コスト・オブ・キャリーと便宜利回りが時間の関数のみであれば原資産のボラティリティと等しい。

## 7. 関連トピック

- See: [topics/options_basics.md](../topics/options_basics.md) — オプションの基本構造・ペイオフ
- See: [topics/bsm.md](../topics/bsm.md) — Black-Scholes-Merton モデル（Black's modelの親）
- See: [ch15_bsm.md](ch15_bsm.md) — BSM導出（Ch.18はそのq=r特殊ケース）
- See: Ch.29 — 金利デリバティブ（キャップ、フロア）にもBlack-like modelsが使用される
- See: Ch.13 ([ch13_binomial_trees.md](ch13_binomial_trees.md)) — 二項ツリーの基礎（Section 13.9が先物ツリーの出典）
