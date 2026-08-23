# Ch.13 Binomial Trees

> **Source**: Hull 11e, Chapter 13 (pp. 288-315). Paraphrased summary for personal use.

## 1. 要点

- 株価が上下2方向にしか動かない1ステップのツリーでは、リスクフリー資産との裁定なしポートフォリオを構成することで、実際の株価の上昇確率を一切使わずにオプション価格が一意に定まる（§13.1）。
- 裁定なし価格とリスク中立評価は等価であり、リスク中立確率 $p$ のもとで期待ペイオフをリスクフリーレートで割り引くと同じ価格が得られる（§13.2）。
- 多ステップツリーでは後退帰納法（backward induction）を適用する。各ノードで eq.(13.5) を繰り返すことが本質であり、ステップ数を増やすと価格はBSM価格に収束する（§13.9, appendix）。
- CRR パラメータ化（$u=e^{\sigma\sqrt{\Delta t}}$, $d=1/u$）により、ツリーがボラティリティに整合するよう設定される（§13.7–13.8）。
- アメリカンオプションの評価では各ノードで継続価値と即時行使価値を比較し、大きい方を採用する（§13.5）。
- 指数・通貨・先物オプションへの拡張は $p$ の計算式の $a$ パラメータを変えるだけで対応できる（§13.11）。
- デルタ $\Delta$ はツリーの各ノードで定義され、時間とともに変化するため、ヘッジ比率の動的調整（デルタ・ヘッジ）が必要になる（§13.6）。

## 2. キー用語

- **binomial tree**: 各ステップで株価が $u$ 倍または $d$ 倍に動く格子状の価格ツリー
- **risk-neutral probability** ($p$): リスク中立世界における上昇確率。実世界の確率とは異なる
- **risk-neutral valuation**: 世界がリスク中立と仮定してオプションを評価する原理。全ての資産の期待収益率をリスクフリーレートとし、期待ペイオフをリスクフリーレートで割り引く
- **backward induction**: ツリーの末端から始まり、現在に向かって再帰的に価格を計算する手法
- **CRR parameterization**: Cox-Ross-Rubinstein (1979) が提案した $u=e^{\sigma\sqrt{\Delta t}}$, $d=1/u$ によるツリー構築法
- **delta** ($\Delta$): オプション価格の株価に対する感応度。1オプションにつき $\Delta$ 株保有でリスクレスポートフォリオを形成
- **delta hedging**: $\Delta$ 株を保有・調整し続けることでオプションポジションのリスクを消去する手法
- **early exercise**: アメリカンオプションを満期前に権利行使すること。プットでは有利な場合がある
- **intrinsic value**: 即時行使した場合の価値。コール: $\max(S-K,0)$、プット: $\max(K-S,0)$
- **continuation value**: 権利行使せず保有し続けた場合の現在価値（= eq.(13.5) によるバックワード計算値）
- **P-measure / Q-measure**: 実世界測度 / リスク中立測度。Girsanov の定理により、測度を変えても株価のボラティリティは変化しない（§13.7）

## 3. 主要公式

### 1ステップ裁定なし価格（一般形）

$$
f = e^{-rT}\bigl[p\, f_u + (1-p)\, f_d\bigr]
$$

<!-- Hull eq. (13.2) -->

- $f$: 現在のオプション価格
- $f_u, f_d$: 上昇・下落後のオプション価値
- $r$: 無リスク金利（連続複利）
- $T$: 満期までの時間（年）

### リスク中立確率（配当なし株式、1ステップ）

$$
p = \frac{e^{rT} - d}{u - d}
$$

<!-- Hull eq. (13.3) -->

### デルタ（ツリーのノードから）

$$
\Delta = \frac{f_u - f_d}{S_0 u - S_0 d}
$$

<!-- Hull eq. (13.1) -->

- $\Delta > 0$（コール）、$\Delta < 0$（プット）

### 多ステップ一般化（時間ステップ $\Delta t$）

$$
f = e^{-r\Delta t}\bigl[p\, f_u + (1-p)\, f_d\bigr]
$$

<!-- Hull eq. (13.5) -->

$$
p = \frac{e^{r\Delta t} - d}{u - d} = \frac{a - d}{u - d}, \quad a = e^{r\Delta t}
$$

<!-- Hull eq. (13.6), (13.17), (13.18) -->

### 2ステップツリーの閉形式（参考）

$$
f = e^{-2r\Delta t}\bigl[p^2 f_{uu} + 2p(1-p) f_{ud} + (1-p)^2 f_{dd}\bigr]
$$

<!-- Hull eq. (13.10) -->

### CRR パラメータ化

$$
u = e^{\sigma\sqrt{\Delta t}}, \quad d = \frac{1}{u} = e^{-\sigma\sqrt{\Delta t}}
$$

<!-- Hull eq. (13.15), (13.16) -->

$\sigma$ はボラティリティ（年率）。$u$ と $d$ は $\Delta t^2$ 以上の項を無視した近似解。

### 連続配当利回り $q$ を持つ株式（株価指数を含む）

$$
p = \frac{e^{(r-q)\Delta t} - d}{u - d}, \quad a = e^{(r-q)\Delta t}
$$

<!-- Hull §13.11, Options on Stocks Paying a Continuous Dividend Yield -->

### 通貨オプション（外国リスクフリー金利 $r_f$）

$$
a = e^{(r - r_f)\Delta t}
$$

<!-- Hull §13.11, Options on Currencies -->

外国通貨を $r_f$ の配当を生む資産とみなし、$q \leftarrow r_f$ と置き換える。

### 先物オプション

$$
a = 1, \quad p = \frac{1 - d}{u - d}
$$

<!-- Hull §13.11, Options on Futures -->

先物ポジションのコストはゼロなのでリスク中立世界での先物価格の期待成長率はゼロ。

### 代替ツリー（等確率 $p=1/2$）

$$
p = \frac{1}{2}, \quad
u = e^{(r-q-\sigma^2/2)\Delta t + \sigma\sqrt{\Delta t}}, \quad
d = e^{(r-q-\sigma^2/2)\Delta t - \sigma\sqrt{\Delta t}}
$$

<!-- Hull §13.10 alternative tree (equal-probability parameterization) -->

$u \neq 1/d$ となるが、同様に価格はBSMに収束する。

### 収束：$\Delta t \to 0$ の極限

ステップ数 $n \to \infty$（$\Delta t = T/n \to 0$）の極限でバイノミアル価格はBSM公式に収束する（Appendix §13A）。付録では二項分布が正規分布に近づく性質を用いて：

$$
c = S_0 N(d_1) - K e^{-rT} N(d_2)
$$

$$
d_1 = \frac{\ln(S_0/K) + (r + \sigma^2/2)T}{\sigma\sqrt{T}}, \quad d_2 = d_1 - \sigma\sqrt{T}
$$

<!-- Hull eq. (13A.4), BSM derived from binomial appendix -->

## 4. アルゴリズム / 手順

### 手順1：$N$ ステップ ヨーロピアン・バイノミアル

1. **パラメータ計算**: $\Delta t = T/N$、$u = e^{\sigma\sqrt{\Delta t}}$、$d = 1/u$、$a = e^{(r-q)\Delta t}$、$p = (a-d)/(u-d)$、$\text{disc} = e^{-r\Delta t}$。
2. **末端株価配列**: ステップ $N$ の末端ノード $j = 0, 1, \ldots, N$ に対して $S_{N,j} = S_0 \cdot u^{N-j} \cdot d^{j}$。
3. **末端ペイオフ**: コールなら $V_j = \max(S_{N,j} - K, 0)$、プットなら $V_j = \max(K - S_{N,j}, 0)$。
4. **後退帰納**: $N$ 回ループし、$V_j \leftarrow \text{disc} \cdot (p \cdot V_j + (1-p) \cdot V_{j+1})$（$j=0,\ldots,\text{step}-1$）。
5. **結果**: $V_0$ が現在のオプション価格。

### 手順2：$N$ ステップ アメリカン・バイノミアル

手順1と同じだが、後退帰納の各ステップで各ノードの株価 $S_{\text{step},j}$ を復元し、継続価値と即時行使価値を比較する：

$$
V_j \leftarrow \max\!\bigl(\text{disc}\cdot(p\cdot V_j + (1-p)\cdot V_{j+1}),\; \max(K - S_{\text{step},j},\, 0)\bigr)
$$

プット以外のアメリカン（コール等）は $\max(S-K, 0)$ に変更。内部でフル株価ツリーを再構成する必要があるため、後退ループ内でステップごとの株価を計算する。

### 手順3：デルタの抽出

各ノードにおけるデルタは隣接する2ノードから直接得られる：

$$
\Delta_{\text{node}} = \frac{f_u - f_d}{S_0 u - S_0 d}
$$

デルタは時間とともに変化するため、動的ヘッジには定期的な持ち高調整が必要。2ステップ例（Fig 13.4）では第1ステップの $\Delta = 0.4358$、第2ステップでは $0.7273$（上昇後）または $0$（下落後）に変わる。

## 5. Python reference

```python
import numpy as np
import math

def binomial_european_call(S, K, r, sigma, T, N, q=0.0):
    """N-step CRR binomial price of a European call."""
    dt = T / N
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp((r - q) * dt) - d) / (u - d)
    disc = math.exp(-r * dt)
    j = np.arange(N + 1)
    S_T = S * (u ** (N - j)) * (d ** j)
    V = np.maximum(S_T - K, 0.0)
    for _ in range(N):
        V = disc * (p * V[:-1] + (1 - p) * V[1:])
    return float(V[0])


def binomial_american_put(S, K, r, sigma, T, N, q=0.0):
    """N-step CRR binomial price of an American put."""
    dt = T / N
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp((r - q) * dt) - d) / (u - d)
    disc = math.exp(-r * dt)
    # build full tree as we need intrinsic at every node
    j = np.arange(N + 1)
    S_T = S * (u ** (N - j)) * (d ** j)
    V = np.maximum(K - S_T, 0.0)
    for step in range(N - 1, -1, -1):
        S_step = S * (u ** (np.arange(step + 1)[::-1])) * (d ** np.arange(step + 1))
        cont = disc * (p * V[:-1] + (1 - p) * V[1:])
        intrinsic = np.maximum(K - S_step, 0.0)
        V = np.maximum(cont, intrinsic)
    return float(V[0])


# Example
print(binomial_european_call(S=100, K=100, r=0.05, sigma=0.2, T=1.0, N=200))
print(binomial_american_put(S=100, K=100, r=0.05, sigma=0.2, T=1.0, N=200))
# Expected (approx BSM): European call ~10.45, American put ~10.47
```

先物オプション（$a=1$）や通貨オプション（$q=r_f$）への拡張は `q` 引数を変えるか `a` を直接指定する形に関数を改修することで対応できる。

## 6. 注意点 / 典型的なミス

- **実世界確率 $p^*$ とリスク中立確率 $p$ の混同**: 価格付けに使うのは常にリスク中立確率 $p$。実世界の上昇確率が変わってもオプション価格は変わらない（§13.1–13.2）。実世界では正しい割引率がわからないため、リスク中立評価の方が計算上はるかに便利。
- **$u > e^{r\Delta t}$ の要件**: リスク中立確率が $0 < p < 1$ になるためには $d < e^{r\Delta t} < u$ でなければならない。CRR パラメータ化ではこれが自動的に満たされるが、任意の $u,d$ を使う場合は確認が必要。
- **アメリカンオプションの誤差**: ヨーロピアンと同じ末端からの折り返し計算だけでは不十分。各内部ノードで intrinsic value との比較を忘れると American premium を見落とす。
- **ステップ数の選択**: ステップ数が少ないと価格が大きく変動する（奇数・偶数ステップで交互に振動することがある）。実務では30ステップ以上を使用。500ステップ程度でBSM価格にほぼ一致する（§13.9）。
- **配当処理**: 連続配当利回り $q$ では $a=e^{(r-q)\Delta t}$ を使えばよいが、離散配当の場合は株価から配当の現在価値を差し引くアプローチが必要（Ch.21 で詳述）。
- **デルタの動的変化**: デルタはノードごと・ステップごとに異なる。静的ヘッジは不可能であり、定期的な持ち高調整（dynamic rebalancing）が必要である（§13.6）。
- **先物ツリーの $a=1$**: 先物は証拠金の積み増しを除いてポジション取得コストがゼロなので、リスク中立世界での期待成長率はゼロ。うっかり $a=e^{r\Delta t}$ を使うと誤答になる。

## 7. 関連トピック

- See: Ch.15 (Black-Scholes-Merton model — バイノミアルの極限として導出)
- See: Ch.19 (The Greek Letters — デルタの詳細な議論とその他のGreeks)
- See: Ch.21 (Basic Numerical Procedures — 多ステップツリーの実務的実装、離散配当、バリア・オプションへの応用)
- See: Ch.10 (Mechanics of Options Markets — オプションの基本構造)
- See: Ch.11 (Properties of Stock Options — プット・コール・パリティ、上下限価格)
- See: Ch.17–18 (Options on Stock Indices/Currencies/Futures — §13.11の具体的展開)
- See: Ch.28 (Martingales and Measures — Q-measure / P-measure の理論的背景、Girsanov の定理)
