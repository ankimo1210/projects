# Ch.16 Employee Stock Options

> **Source**: Hull 11e, Chapter 16 (pp. 371-383). Paraphrased summary for personal use.

## 1. 要点

- ESO（従業員ストック・オプション）は会社が従業員に付与するコール・オプションであり、通常は付与日にアット・ザ・マネーで設定され、満期は10〜15年程度。
- ESOは譲渡禁止のため早期行使が合理的になる場合があり、通常の上場オプションとは行使行動が大きく異なる。
- 2005年以降の会計基準（FAS 123R・IFRS 2）により、付与日公正価値での損益計算書計上が義務付けられた。これが普通株式ユニット（RSU）等への移行を促した。
- 評価方法は主に3つ：（1）期待寿命を使ったBSMの簡易適用、（2）離職率・早期行使確率を組み込んだ二項ツリー、（3）行使マルチプルMに基づくHull-Whiteモデル。
- バックデーティング（付与日の遡及操作）は不正会計として2002年以降に大量摘発され、CEOの刑事訴追に至った事例もある。

## 2. キー用語

- **ESO (Employee Stock Option)**: 会社が従業員に付与する非譲渡の株式コール・オプション
- **Vesting period**: 行使不可の待機期間。最長4年程度
- **Expected life**: 付与から行使または失効までの平均期間。BSM適用時に $T$ の代替として使う
- **Exercise multiple (M)**: 株価／行使価格が $M$ を超えた時点で行使するという経験則的な閾値（Hull-White モデル）
- **Exit rate ($\lambda$)**: 各期間に従業員が会社を辞める確率（二項ツリーで使用）
- **Restricted Stock Unit (RSU)**: 将来日付に株式を付与する報酬。オプションの非対称性を持たず損失も共有する
- **Market-Leveraged Stock Unit (MSU)**: 付与株数が $S_T/S_0$ に比例するRSUの変形
- **Backdating**: 付与日を実際より前の日付に遡及記載する不正行為
- **Agency costs**: 株主と経営者の利害不一致から生じる損失（オプションの非対称性が助長しうる）
- **Repricing**: 株価下落後に行使価格を再設定すること。インセンティブ設計の問題点

## 3. 主要公式

### BSM with expected life (shortened-T approximation)

$$
V_{\text{ESO}} = \text{BSM}(S_0, K, r, \sigma, q, T_{\text{exp}})
$$

- $S_0$: 付与日の株価（配当調整済みで $S_0 - \text{PV(div)}$ を使う場合あり）
- $K$: 行使価格（通常 $S_0$ と等しい）
- $T_{\text{exp}}$: 契約満期 $T$ ではなく、過去データから推定した期待寿命
- $r$: $T_{\text{exp}}$ に対応するゼロクーポン無リスク金利
- $\sigma$: 長期ヒストリカル・ボラティリティ

<!-- Hull §16.4, "Using the Black–Scholes–Merton Model" -->

### Dilution adjustment

$$
V_{\text{ESO}}^{\text{diluted}} = \frac{N}{N+M} \cdot V_{\text{BSM}}
$$

- $N$: 現在の発行済株数
- $M$: オプション行使時に新規発行される株数

ただし Hull は、市場が付与を既に織り込んでいる場合は通常この調整は不要と述べている（§16.4 Dilution）。

<!-- Hull §16.4, Dilution subsection -->

### Binomial tree node value with exit rate

各ノードで従業員が離職する確率を $\lambda$ とすると、保有継続確率は $1 - \lambda$。
行使判断ノードでの期待オプション価値：

$$
V_{\text{node}} = p_{\text{ex}} \cdot (S - K) + (1 - p_{\text{ex}}) \cdot \left[(1-\lambda) \cdot e^{-r\Delta t} \cdot \mathbb{E}[V_{\text{next}}] + \lambda \cdot \max(S-K,\,0)\right]
$$

- $p_{\text{ex}}$: 当該ノードで従業員が自発的に行使する確率（$S/K$ と残余満期の関数）
- $\lambda$: 1期間当たりの離職確率

<!-- Hull §16.4, "Binomial Tree Approach" and Figure 16.1 -->

### Hull-White exercise multiple rule

$$
\text{Exercise if } S \geq M \cdot K \text{ (option has vested)}
$$

- $M$: 行使マルチプル。過去の行使実績から行使時点の $S/K$ 平均として推定
- 満期・解雇による強制行使はこの平均の計算から除外する

<!-- Hull §16.4, "Exercise Multiple Approach" -->

## 4. アルゴリズム / 手順

**方法A: BSM期待寿命法（最も一般的）**

1. 過去の行使・失効データから期待寿命 $T_{\text{exp}}$ を推定する。
2. 配当現在価値を $S_0$ から差し引き調整済み株価を求める（または連続配当利回り $q$ を使う）。
3. $T_{\text{exp}}$ に対応する無リスク金利 $r$ とヒストリカル・ボラティリティ $\sigma$ を設定。
4. 通常のBSMコール価値を計算し、付与オプション数を乗じて損益計算書費用を得る。

**方法B: 二項ツリー法（より精緻）**

1. 各期 $\Delta t$ ごとに離職率 $\lambda$ を設定（年率離職率から変換）。
2. ベスティング期間前のノードでは行使不可とし、離職時はアウト・オブ・ザ・マネーなら失効、インザマネーなら即時行使。
3. ベスティング後のノードでは、$S/K$ と残余満期から推定した行使確率 $p_{\text{ex}}$ を適用。
4. ツリーを満期から現在に向かってロールバックし初期ノード価値を取得（Example 16.2 参照）。

**方法C: 行使マルチプル法（Hull-White）**

1. 過去データから行使マルチプル $M$ を推定。
2. ノードが $S \geq MK$ かつベスティング済みなら即時行使とみなすツリーを構築。
3. Section 27.6 の要領でノードが行使境界に乗るようにツリーを調整する。
4. 離職率も同様に取り込んで価値を計算。

## 5. Python reference

```python
import math
from scipy.stats import norm


def eso_bsm_shortened(
    S: float,
    K: float,
    r: float,
    sigma: float,
    expected_life: float,
    q: float = 0.0,
    N_shares: int = 1,
    M_new: int = 0,
) -> float:
    """
    Dilution-adjusted ESO value using BSM with shortened time-to-exercise.

    Parameters
    ----------
    S            : current stock price (net of PV of dividends, or use q)
    K            : strike price
    r            : risk-free rate (zero-coupon, matching expected_life)
    sigma        : annualised volatility
    expected_life: estimated average time to exercise/expiry (years)
    q            : continuous dividend yield (alternative to pre-deducting dividends)
    N_shares     : shares currently outstanding (for dilution adjustment)
    M_new        : new shares issued on exercise (0 = no dilution adjustment)
    """
    T = expected_life
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    bsm_value = (
        S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    )
    # Dilution factor: N / (N + M)  — only apply if surprise grant
    if M_new > 0 and N_shares > 0:
        bsm_value *= N_shares / (N_shares + M_new)
    return bsm_value


# Example 16.1 (Hull p. 376)
# S0=30, PV(div)=4 => adjusted S=26; K=30, r=5%, sigma=25%, T_exp=4.5
value = eso_bsm_shortened(S=26, K=30, r=0.05, sigma=0.25, expected_life=4.5)
print(f"ESO value per option: ${value:.2f}")   # expect ~$6.31
```

## 6. 注意点 / 典型的なミス

- **期待寿命 ≠ 契約満期**: BSM に $T = 10$ 年をそのまま渡すと過大評価になる。必ず期待寿命を使う。
- **理論的妥当性の欠如**: 期待寿命法はヒューリスティックであり、理論的厳密性はない（Hull §16.4 で明言）。
- **希薄化の二重計上**: 付与が市場に既知なら株価は既に希薄化を織り込んでいる。サプライズ付与以外では希薄化調整は不要。
- **バックデーティングのリスク**: 付与日を遡及操作すると行使価格が有利になるが、不正会計・刑事罰の対象。再評価制度があれば誘因は大幅に低下する。
- **RSUとの混同**: RSUは株価下落でも損失を共有する。ESOの非対称ペイオフとは本質的に異なる。
- **二項ツリーでの離職タイミング**: Hull の例では従業員は期末に離職すると仮定。前提を変えると結果が変わる点に注意。
- **行使マルチプルの推定**: 満期到来・解雇時の行使はサンプルから除外しないと $M$ が過小推定される。

## 7. 関連トピック

- See: Ch.11 (オプションの性質・早期行使条件), Ch.13 (二項ツリーの構築), Ch.15 (BSMモデル詳細)
- See: Ch.27 §27.6 (行使境界ノードを持つツリー構築)
- See: Ch.15 §15.10 (希薄化の扱い、Business Snapshot 15.3)
- See: [topics/employee_stock_options.md](../topics/employee_stock_options.md) (未作成)
