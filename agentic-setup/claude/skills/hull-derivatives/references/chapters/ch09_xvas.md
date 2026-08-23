# Ch.09 XVAs

> **Source**: Hull 11e, Chapter 9 (pp. 216-226). Paraphrased summary for personal use.

## 1. 要点

- デリバティブのノーデフォルト価値には、相手方デフォルトリスク（CVA）・自行デフォルトリスク（DVA）・資金調達コスト（FVA）・初期証拠金コスト（MVA）・資本コスト（KVA）を表す調整項（XVAs）を加味する必要がある。
- CVA はカウンターパーティのデフォルト確率と期待エクスポージャーの積の現在価値の和として計算され、ポートフォリオ価値を減少させる。DVA は自行デフォルトによる利益で価値を増加させる。
- FVA と MVA については、金融工学実務家（平均調達コストで算定）と金融経済学者（マージンのリスクに見合ったリスクフリーに近いコストを使うべき）の間で根本的な意見の相違がある。
- CVA・DVA はネッティングの影響を受けるためポートフォリオ単位で計算しなければならないが、FVA は取引単位で計算できる。
- XVAs の計算はモンテカルロシミュレーションを必要とし計算コストが高く、機械学習（ニューラルネットワーク）による高速近似が実務で活用されている。

## 2. キー用語

- **CVA (Credit Valuation Adjustment)**: カウンターパーティのデフォルトリスクによる損失期待値の現在価値。ポートフォリオ価値を減少させる。
- **DVA (Debit/Debt Valuation Adjustment)**: 自行がデフォルトした場合に得られる利得の期待値の現在価値。ポートフォリオ価値を増加させる。
- **FVA (Funding Valuation Adjustment)**: アンコラテラライズドのデリバティブポジションに必要な資金調達コスト（または便益）の現在価値。
- **FCA (Funding Cost Adjustment)**: FVA の調達コスト部分の現在価値。
- **FBA (Funding Benefit Adjustment)**: FVA の調達便益部分の現在価値。FVA = FCA − FBA。
- **MVA (Margin Valuation Adjustment)**: 初期証拠金の資金調達コストの現在価値。
- **KVA (Capital Valuation Adjustment)**: 取引が発生させる増分的資本要件に対するコストの現在価値。
- **ネッティング**: 両者間の未決済デリバティブを一つの契約とみなし、デフォルト時に相殺計算する仕組み。マスター契約に基づく。
- **クレジット・サポート・アネックス (CSA)**: マスター契約の付属文書で担保の計算方法・形態を規定。
- **マージン期間 (Cure period / Margin period of risk)**: デフォルト前に担保提供が止まると想定される日数。
- **EPE (Expected Positive Exposure)**: 各時点における期待正エクスポージャー。CVA の計算に使用。
- **DVA2**: Hull-White が提唱する概念。銀行が発行する債務に対するデフォルトスプレッドの利益と同質のもので、FVA の一部はこれで説明できる。

## 3. 主要公式

### CVA（ノー・ウロング・ウェイ・リスク）

$$
\text{CVA} = \sum_{i=1}^{N} q_i \cdot v_i
$$

<!-- Hull eq. (9.1) -->

- $N$: 区間の総数（デリバティブ最長満期 $T$ 年を $N$ 分割）
- $q_i$: 第 $i$ 区間におけるカウンターパーティのデフォルト確率
- $v_i$: 第 $i$ 区間の中間時点でデフォルトが発生した場合の、デリバティブポートフォリオの期待損失の現在価値

より展開した表現として、$v_i = D_i \cdot E_i \cdot (1-R)$ と書けることが多い（$D_i$: リスクフリー割引係数、$E_i$: EPE、$R$: 回収率）。ただし Hull 本書では $v_i$ をまとめて定義している。

### DVA

$$
\text{DVA} = \sum_{i=1}^{N} q_i^* \cdot v_i^*
$$

<!-- Hull eq. (9.2) -->

- $q_i^*$: 第 $i$ 区間における銀行自身のデフォルト確率
- $v_i^*$: 第 $i$ 区間の中間時点で銀行がデフォルトした場合の、銀行の期待利得（カウンターパーティの期待損失）の現在価値

### デフォルト調整後のポートフォリオ価値

$$
f_{\text{adj}} = f_{\text{nd}} - \text{CVA} + \text{DVA}
$$

- $f_{\text{nd}}$: ノーデフォルト前提でのポートフォリオ現在価値

### FVA（概念式）

$$
\text{FVA} = \text{FCA} - \text{FBA}
$$

- **FCA**: 将来の期待的資金調達コストの現在価値（アンコラテラライズドポジションがプラス価値の場合に発生）
- **FBA**: 将来の期待的資金調達便益の現在価値（アンコラテラライズドポジションがマイナス価値の場合に発生）

### KVA（概念）

$$
\text{KVA} = \text{PV}\bigl[\text{増分資本要件} \times \text{株主要求リターン}\bigr]
$$

実務家は株主要求リターン（例: 15%）を乗じた増分資本コストの現在価値を KVA とする。金融経済学者はモジリアーニ-ミラー定理に基づき、資本構成の変化がプロジェクト価値に影響しないと主張し、KVA の正当性に疑問を呈する。

## 4. アルゴリズム / 手順

### モンテカルロ法による CVA 計算手順

1. **タイムグリッド設定**: デリバティブ最長満期 $T$ を $N$ 等分し、各区間境界 $t_0=0, t_1, \ldots, t_N=T$ を定義する。
2. **エクスポージャー・シミュレーション**: 対象ポートフォリオ（例: IRS、オプション群）について複数のリスクファクターパスをモンテカルロで生成し、各時点 $t_i$ のポートフォリオ現在価値を計算する。ネッティングを考慮して、各シナリオで `max(portfolio_value, 0)` を取る（銀行にとってのエクスポージャーはプラス側のみ）。
3. **EPE 算出**: 各時点 $t_i$ における期待正エクスポージャー $E_i = E[\max(V_{t_i}, 0)]$ をシナリオ平均で推定する。
4. **デフォルト確率の取得**: カウンターパーティの CDS スプレッド（またはクレジットカーブ）からハザードレートを推定し、各区間のデフォルト確率 $q_i$ を計算する（例: $q_i \approx (e^{-\lambda t_{i-1}} - e^{-\lambda t_i})$）。
5. **回収率の設定**: 市場慣行に基づいて回収率 $R$（例: 0.40）を設定する。
6. **損失現在価値の計算**: 各区間について $v_i = D_i \cdot E_i \cdot (1-R)$ を計算する（$D_i$ は区間中間点 $\hat{t}_i = (t_{i-1}+t_i)/2$ のリスクフリー割引係数）。
7. **CVA 合計**: $\text{CVA} = \sum_{i=1}^{N} q_i \cdot v_i$
8. **DVA 計算（任意）**: 銀行自身のクレジットカーブから $q_i^*$ を取得し、同様の手順で DVA を算出。エクスポージャーはカウンターパーティから見たプラス側（銀行から見たマイナス側）を使う。
9. **コラテラル調整（担保あり場合）**: マージン期間（cure period）を考慮し、担保額を控除した純エクスポージャーで再計算する。

## 5. Python reference

```python
import numpy as np

def cva_montecarlo(
    exposure_paths: np.ndarray,   # shape (n_scenarios, n_steps)
    default_prob_curve: np.ndarray,  # shape (n_steps,) — PD for each interval
    discount_curve: np.ndarray,   # shape (n_steps,) — risk-free discount at midpoint
    recovery: float = 0.40,
) -> float:
    """Compute CVA via Monte Carlo for a single netting set.

    Parameters
    ----------
    exposure_paths : (n_scenarios, n_steps) array of portfolio mark-to-market values.
        Positive values represent exposure to the bank.
    default_prob_curve : (n_steps,) interval default probabilities q_i.
    discount_curve : (n_steps,) risk-free discount factors D_i at interval midpoints.
    recovery : Loss-given-default = 1 - recovery.

    Returns
    -------
    float : CVA (positive number, to be subtracted from no-default value).
    """
    # EPE: average positive exposure across scenarios at each time step
    positive_exposures = np.maximum(exposure_paths, 0.0)   # (n_scenarios, n_steps)
    epe = positive_exposures.mean(axis=0)                  # (n_steps,)

    # Expected loss per interval: q_i * D_i * EPE_i * (1 - R)
    lgd = 1.0 - recovery
    interval_loss = default_prob_curve * discount_curve * epe * lgd  # (n_steps,)

    cva = interval_loss.sum()
    return float(cva)


# --- Minimal usage example ---
if __name__ == "__main__":
    rng = np.random.default_rng(42)
    n_scenarios, n_steps = 5_000, 20
    # Simulated IRS mark-to-market values (centered near 0)
    paths = rng.normal(loc=0.5, scale=2.0, size=(n_scenarios, n_steps))

    # Flat hazard rate lambda = 0.02 → q_i per semi-annual step (dt = 0.5)
    dt = 0.5
    lam = 0.02
    t_mid = np.arange(1, n_steps + 1) * dt - dt / 2  # midpoints
    q = np.exp(-lam * (t_mid - dt / 2)) - np.exp(-lam * (t_mid + dt / 2))
    D = np.exp(-0.03 * t_mid)  # risk-free rate 3%

    print(f"CVA = {cva_montecarlo(paths, q, D, recovery=0.40):.6f}")
    # Example output: CVA = 0.xxxxxx  (positive, reduces portfolio value)
```

## 6. 注意点 / 典型的なミス

- **DVA の直感**: 銀行自身の信用力が低下すると DVA が増加してポートフォリオ価値が上がる。これは反直感的だが、デリバティブはゼロサムゲームであるため相手方の損失が自行の利得になる仕組みから論理的に導かれる。ただし DVA を実現益として計上することは多くの会計・規制上の場面で制限される。
- **ネッティングとポートフォリオ計算**: CVA・DVA はネッティングの影響を受けるためカウンターパーティ単位のポートフォリオ全体で計算しなければならない。取引単位での加算は誤り。一方 FVA はポートフォリオを横断して加算できる。
- **コラテラルとマージン期間**: 担保がある場合でも cure period 分のエクスポージャーが残る。CSA の詳細条件（担保形態・ヘアカット・閾値）を無視すると CVA を過小評価する。
- **FVA/MVA コスト率の選択**: 平均調達コストではなく、投資のリスクに見合ったマージナルコスト（リスクフリーに近い水準）を使うべきというのが金融経済学のコンセンサスだが、実務では平均調達コスト（例: FF+100bp）が使われることが多い。この差が FVA の過大計上につながる。
- **Wrong-way risk の無視**: Hull eq. (9.1) のシンプルな CVA 式は、カウンターパーティのデフォルト確率とエクスポージャーが独立であることを前提とする（ノー・ウロング・ウェイ・リスク）。実際には相関があり得る（例: 株式オプションで参照企業がカウンターパーティの場合）。詳細は Ch.24。
- **KVA の二重計上リスク**: DVA と KVA は経済的に重複する部分があるため、両方を調整するとカウンターパーティ信用リスクコストを二重に計上する可能性がある。
- **機械学習近似の限界**: ニューラルネット近似は学習データ外の市場環境やポートフォリオ構成には外挿精度が低下する。

## 7. 関連トピック

- See: Ch.07 Swaps — IRS のネッティング・コラテラル構造の基礎
- See: Ch.24 Credit Risk — CVA の詳細計算、ハザードレートモデル、ウロング・ウェイ・リスク
- See: Ch.25 Credit Derivatives — CDS スプレッドからのデフォルト確率推定
- See: [topics/credit.md](../topics/credit.md) — 信用リスク全般（Ch.8, 9, 24, 25 を横断）
- 参考: Hull & White (2012) "The FVA Debate," *Risk* — FVA の理論的根拠に関する議論
- 参考: Modigliani-Miller theorem — KVA/FVA の経済学的批判の基礎
