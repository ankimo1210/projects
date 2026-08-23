# Ch.05 Determination of Forward and Futures Prices

> **Source**: Hull 11e, Chapter 5 (pp. 124-151). Paraphrased summary for personal use.

## 1. 要点

- 投資資産（investment asset）のフォワード価格は裁定取引による無リスク条件から一意に決まる。消費資産（consumption asset）では等号は成立せず上界のみ。
- フォワード価格の基本式は $F_0 = S_0 e^{rT}$（収入・保管コストなし）。既知キャッシュ収入 $I$ や連続配当利回り $q$ を控除することで一般化される。
- 既存フォワード契約の価値は $f = (F_0 - K)e^{-rT}$：当初ゼロだが時間経過とともにプラス/マイナスになる。
- FX フォワードは「外貨＝連続利回り $r_f$ を生む資産」と見なせるため、$F_0 = S_0 e^{(r-r_f)T}$（カバー付き金利平価）が成立する。
- コスト・オブ・キャリー $c = r + u - q - r_f$ でまとめると投資資産は $F_0 = S_0 e^{cT}$、消費資産は $F_0 = S_0 e^{(c-y)T}$（$y$: コンビニエンス・イールド）。
- フューチャーズ価格と期待将来スポット価格の関係は資産の系統的リスクに依存：正の系統的リスクなら $F_0 < E(S_T)$（normal backwardation）、負なら $F_0 > E(S_T)$（contango）。

## 2. キー用語

- **investment asset**: 少なくとも一部の市場参加者が投資目的のみで保有する資産（株式・債券・金・銀）
- **consumption asset**: 主に消費・製造のために保有する資産（原油・銅・コーン）。フォワード価格の等号は導出不可
- **forward price** ($F_0$): 裁定がないもとで成立する現時点のデリバリー価格
- **delivery price** ($K$): 契約締結時に固定されたデリバリー価格。変化しない
- **value of forward contract** ($f$): 現時点でロング・フォワードを保有した場合の価値。締結時はゼロ
- **cost of carry** ($c$): 資産を保有するコスト純額 $= r + u - q$（為替は $r - r_f$）
- **convenience yield** ($y$): 物理的な現物保有から得られる非金銭的便益。消費資産固有
- **normal backwardation**: $F_0 < E(S_T)$。フューチャーズが期待スポットを下回る状態
- **contango**: $F_0 > E(S_T)$。フューチャーズが期待スポットを上回る状態
- **index arbitrage / program trading**: 株価指数フューチャーズとバスケット現物の価格乖離を利用する裁定戦略
- **short selling**: 資産を借りて売却し、後に買い戻してポジションを決済する取引

## 3. 主要公式

### 投資資産・収入なし

$$F_0 = S_0 e^{rT}$$

- $S_0$: 現時点のスポット価格
- $r$: 連続複利リスクフリー金利（満期 $T$ 年）
- $T$: 契約満期（年）

<!-- Hull eq. (5.1) -->

### 投資資産・既知キャッシュ収入 $I$

$$F_0 = (S_0 - I)\, e^{rT}$$

- $I$: 契約期間中に受け取るキャッシュ収入の現在価値（例：クーポン、配当）

<!-- Hull eq. (5.2) -->

### 投資資産・連続配当利回り $q$

$$F_0 = S_0\, e^{(r-q)T}$$

- $q$: 連続複利で表した配当利回り（株価指数フューチャーズに適用）

<!-- Hull eq. (5.3) / (5.8) -->

### ロング・フォワード契約の価値（一般形）

$$f = (F_0 - K)\, e^{-rT}$$

- $K$: 契約締結時に合意したデリバリー価格
- $F_0$: 現時点の（新規）フォワード価格

<!-- Hull eq. (5.4) -->

#### 資産タイプ別展開形

$$f = S_0 - K e^{-rT} \quad \text{（収入なし）}$$
$$f = S_0 - I - K e^{-rT} \quad \text{（既知収入）}$$
$$f = S_0 e^{-qT} - K e^{-rT} \quad \text{（連続利回り）}$$

<!-- Hull eq. (5.5), (5.6), (5.7) -->

### FX フォワード（カバー付き金利平価）

$$F_0 = S_0\, e^{(r - r_f)T}$$

- $r_f$: 外国通貨の連続複利リスクフリー金利
- $S_0$: 現時点のスポット為替レート（国内通貨建て外貨1単位）

<!-- Hull eq. (5.9) -->

### コモディティ・投資資産（保管コスト $U$ を現在価値で）

$$F_0 = (S_0 + U)\, e^{rT}$$

$$F_0 = S_0\, e^{(r+u)T} \quad \text{（$u$: スポット比率としての保管コスト）}$$

<!-- Hull eq. (5.11), (5.12) -->

### 消費資産とコンビニエンス・イールド $y$

$$F_0 \le (S_0 + U)\, e^{rT}$$

$$F_0 = S_0\, e^{(r+u-y)T}$$

- $y \ge 0$: コンビニエンス・イールド。$y > r + u$ のとき市場はバックワーデーション

<!-- Hull eq. (5.15), (5.17) -->

### コスト・オブ・キャリー（統合形）

$$F_0 = S_0\, e^{cT} \quad \text{（投資資産）}, \qquad F_0 = S_0\, e^{(c-y)T} \quad \text{（消費資産）}$$

| 資産タイプ | $c$ |
|---|---|
| 無配当株 | $r$ |
| 株価指数 | $r - q$ |
| 外貨 | $r - r_f$ |
| 保管コスト付きコモディティ | $r + u$ |

<!-- Hull eq. (5.18), (5.19) -->

### フューチャーズ価格と期待将来スポット価格

$$F_0 = E(S_T)\, e^{(r-k)T}$$

- $k$: 投資家が資産に要求するリターン（CAPM ベースの割引率）
- $k = r$ のとき $F_0 = E(S_T)$（系統的リスクなし）
- $k > r$（正の系統的リスク）$\Rightarrow F_0 < E(S_T)$（normal backwardation）
- $k < r$（負の系統的リスク）$\Rightarrow F_0 > E(S_T)$（contango）

<!-- Hull eq. (5.20) -->

## 4. アルゴリズム / 手順

### 無裁定フォワード価格の導出（キャリー論法）

対象: 収入・保管コストのない投資資産（スポット価格 $S_0$、金利 $r$、満期 $T$）

1. **ケース A: $F_0 > S_0 e^{rT}$ の場合**
   1. $S_0$ を金利 $r$ で $T$ 年借入
   2. 資産1単位を現物購入
   3. フォワード契約でショット（$F_0$ で売り約定）
   4. 満期に資産を $F_0$ で引き渡し、借入残高 $S_0 e^{rT}$ を返済
   5. 利益: $F_0 - S_0 e^{rT} > 0$ → 無リスク利益が発生 → 裁定が消滅するまで $F_0$ が低下

2. **ケース B: $F_0 < S_0 e^{rT}$ の場合**
   1. 資産を空売りして $S_0$ の収入を得る
   2. $S_0$ を金利 $r$ で $T$ 年投資
   3. フォワード契約でロング（$F_0$ で買い約定）
   4. 満期に $F_0$ を払って資産を受け取り、空売りポジションをクローズ
   5. 利益: $S_0 e^{rT} - F_0 > 0$ → 裁定が消滅するまで $F_0$ が上昇

3. **均衡**: 両方向の裁定が消えるのは $F_0 = S_0 e^{rT}$ のときのみ

### 既知収入がある場合の修正

- $I$ は将来収入の現在価値。資産の「実効スポット価格」を $S_0 - I$ に置き換えてステップ 1-5 を繰り返す
- 直感: 収入はホルダーが受け取るため、フォワードの買い手はその分を差し引いた価格でしか合意しない

### FX フォワードの導出（金利平価論法）

1. 外貨 1 単位を保有し、外国レート $r_f$ で $T$ 年投資 → $e^{r_f T}$ 単位
2. 同時に $e^{r_f T}$ 単位をフォワード売り（レート $F_0$）
3. 国内通貨スポット投資では $S_0 e^{rT}$ を得る
4. 裁定なし条件: $e^{r_f T} \cdot F_0 = S_0 e^{rT}$ → $F_0 = S_0 e^{(r-r_f)T}$

## 5. Python reference

```python
import numpy as np


def forward_price(S0: float, r: float, T: float,
                  q: float = 0.0, I: float = 0.0) -> float:
    """
    Forward/futures price for an investment asset.

    Parameters
    ----------
    S0 : spot price today
    r  : continuously compounded risk-free rate (p.a.)
    T  : time to maturity (years)
    q  : continuous dividend / foreign risk-free yield (p.a.)
    I  : present value of known cash income during [0, T]

    Returns
    -------
    F0 : forward price

    Notes
    -----
    - No income / no storage:  forward_price(S0, r, T)
    - Known cash income I:     forward_price(S0, r, T, I=I)
    - Continuous yield q:      forward_price(S0, r, T, q=q)
    - FX forward (r_f = q):    forward_price(S0, r, T, q=r_f)
    """
    return (S0 - I) * np.exp((r - q) * T)


def forward_value(F0: float, K: float, r: float, T: float) -> float:
    """
    Current value of a long forward contract.

    Parameters
    ----------
    F0 : current forward price (newly negotiated today)
    K  : delivery price fixed at contract inception
    r  : continuously compounded risk-free rate
    T  : remaining time to maturity (years)

    Returns
    -------
    f : value of long position  (negative => short position value = -f)
    """
    return (F0 - K) * np.exp(-r * T)


def fx_forward(S0: float, r_dom: float, r_for: float, T: float) -> float:
    """
    FX forward rate (covered interest rate parity).

    Parameters
    ----------
    S0    : spot exchange rate (domestic per 1 unit of foreign)
    r_dom : domestic continuously compounded risk-free rate
    r_for : foreign  continuously compounded risk-free rate
    T     : time to maturity (years)
    """
    return S0 * np.exp((r_dom - r_for) * T)


def commodity_forward(S0: float, r: float, T: float,
                      u: float = 0.0, y: float = 0.0) -> float:
    """
    Forward price for a commodity (upper bound for consumption assets).

    Parameters
    ----------
    u : storage cost as continuous proportion of spot price (p.a.)
    y : convenience yield as continuous proportion (p.a.)
      Set y=0 for investment commodities (gold, silver).
    """
    return S0 * np.exp((r + u - y) * T)


# --- Quick verification examples (Hull Ch.5) ---
if __name__ == "__main__":
    # Example 5.1: zero-coupon bond, S0=930, r=6%, T=4/12
    print(f"Ex5.1 F0 = {forward_price(930, 0.06, 4/12):.2f}")   # 948.79

    # Example 5.4: non-div stock, S0=25, r=10%, T=0.5, K=24
    F0 = forward_price(25, 0.10, 0.5)
    f  = forward_value(F0, 24, 0.10, 0.5)
    print(f"Ex5.4 F0 = {F0:.2f}, f = {f:.2f}")                   # 26.28, 2.17

    # Example 5.6: AUD/USD, S0=0.75, r_dom=1%, r_for=3%, T=2
    print(f"Ex5.6 FX F0 = {fx_forward(0.75, 0.01, 0.03, 2):.4f}") # 0.7206

    # Example 5.5: index, S0=1300, r=5%, q=1%, T=0.25
    print(f"Ex5.5 idx F0 = {forward_price(1300, 0.05, 0.25, q=0.01):.2f}") # 1313.07
```

## 6. 注意点 / 典型的なミス

- **$F_0$ と $K$ の混同**: 契約締結後は $K$ は固定。$F_0$ は市場で日々変化する「今日新規に結べばいくら」という値。$f = (F_0 - K)e^{-rT}$ の使い分けを誤らない。
- **消費資産への等号適用**: 消費資産では $F_0 = (S_0 + U)e^{rT}$ は成立しない（$\le$ のみ）。投資資産の公式をそのまま適用すると誤り。
- **Kidder Peabody の失敗例（Business Snapshot 5.1）**: フォワード価格が現物より高いのは収益ではなくファイナンスコストの反映。この差をシステムが「利益」として計上したため $350M の損失が隠蔽された。
- **インデックス裁定の限界（Black Monday 1987）**: 通常は program trading により eq. (5.8) が成立するが、市場パニック時には注文遅延で裁定不能となりフューチャーズが現物を 18% 下回った。
- **フォワードとフューチャーズの価格差**: 金利が確率的な場合、理論的には等しくない。資産価格と金利が正相関なら $F_{\text{fut}} > F_{\text{fwd}}$（先物の方がやや高い）。実務上は短期では無視できる。
- **FX フォワードの建値方向**: Hull の $S_0$ は「国内通貨/外貨1単位」。市場慣行（直接/間接表示）と混在しやすい。単位を常に確認する。
- **コンビニエンス・イールドの観察不可能性**: $y$ はフォワード価格から逆算する内生変数であり、独立して観察できない。バックワーデーション（先限が期近より安い）のときに $y > r + u$ と推定される。
- **保管コストの扱い**: 絶対額なら $U$（現在価値）として $S_0 - I$ と同様に処理。比率なら $u$ として $F_0 = S_0 e^{(r+u)T}$。混在すると計算誤差が生じる。

## 7. 関連トピック

- See: Ch.02 — フューチャーズ市場の仕組み（デイリー決済、証拠金）
- See: Ch.03 — ヘッジ戦略（ベーシスリスク、最小分散ヘッジ比率）
- See: Ch.04 — 金利（連続複利、ゼロレート、フォワードレート）
- See: Ch.06 — 金利フューチャーズ（T-Bond フューチャーズ、ユーロドル）
- See: Ch.17 — 株価指数・通貨オプション（同じ $q$, $r_f$ 調整が BSM に登場）
- See: Ch.30 — Quanto 調整（CME Nikkei 225 のような通貨ミスマッチ）
- See: [topics/futures_forwards.md](../topics/futures_forwards.md)
