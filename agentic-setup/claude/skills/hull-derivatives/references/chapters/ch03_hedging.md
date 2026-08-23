# Ch.03 Hedging Strategies Using Futures

> **Source**: Hull 11e, Chapter 3 (pp. 70-97). Paraphrased summary for personal use.

## 1. 要点

- **Short hedge / Long hedge**: 将来の売却予定資産にはショートヘッジ、購入予定資産にはロングヘッジを使う。ヘッジにより価格を先物価格近辺にロックインできる。
- **Basis risk**: ヘッジ対象資産と先物原資産が異なる（クロスヘッジ）場合や、先物を満期前に決済する場合、ベーシス（スポット価格 − 先物価格）の不確実性が残る。
- **Optimal hedge ratio** $h^*$: 最小分散ヘッジ比率は $h^* = \rho\,\sigma_S/\sigma_F$（スポット・先物の価格変化の回帰係数）。ヘッジの効果は $R^2 = \rho^2$ で測られる。
- **株価指数先物によるベータヘッジ**: ポートフォリオのベータに比例した枚数の先物を売ることで系統的リスクを除去できる。$N^* = \beta\,V_A/V_F$。また先物でベータを任意の値 $\beta^*$ に変更できる。
- **Stack and roll**: 希望するヘッジ満期より手前にしか流動性のある先物がない場合、短期先物を繰り返しロールして長期ヘッジを合成する。現金フロータイミングのミスマッチに注意（Metallgesellschaft の事例）。

## 2. キー用語

- **Short hedge**: ショート先物ポジションによるヘッジ。資産を将来売却する側が使う。
- **Long hedge**: ロング先物ポジションによるヘッジ。資産を将来購入する側が使う。
- **Perfect hedge**: リスクを完全に消去するヘッジ。実際にはほぼ存在しない。
- **Basis**: ヘッジ対象資産のスポット価格 − ヘッジに使う先物価格。$b = S - F$。
- **Basis risk**: 満期時点でのベーシスが現時点と異なるリスク。スポットと先物の原資産が異なるクロスヘッジで拡大する。
- **Cross hedging**: ヘッジ対象資産と先物の原資産が異なるヘッジ（例: ジェット燃料 → 灯油先物）。
- **Hedge ratio** $h$: 先物ポジションのサイズとエクスポージャーのサイズの比。
- **Minimum variance hedge ratio** $h^*$: ヘッジ後ポジションの分散を最小化するヘッジ比率。
- **Hedge effectiveness**: ヘッジが除去できる分散の割合 $= \rho^2$。
- **Tailing the hedge**: 日次決済を考慮し、名目の $N^*$ を $(1 + r\cdot T)$ で割り引く調整。
- **Beta** ($\beta$): CAPMにおける市場リスク感応度。株価指数先物ヘッジの枚数計算に使う。
- **Stack and roll**: 短期先物を繰り返しロールして長期エクスポージャーをヘッジする戦略。
- **CAPM**: 期待リターン $= R_F + \beta(R_M - R_F)$。系統的リスクのみが補償される。

## 3. 主要公式

### ベーシスの定義

$$b = S - F$$

- $S$: ヘッジ対象資産のスポット価格
- $F$: ヘッジに使う先物価格

<!-- Hull eq. (implicit, Section 3.3) -->

### ショートヘッジの実現価格

$$S_2 + F_1 - F_2 = F_1 + b_2$$

- $F_1$: ヘッジ設定時の先物価格（既知）
- $b_2$: ヘッジ決済時のベーシス（不確実 = basis risk の源泉）

<!-- Hull eq. (implicit, Section 3.3) -->

### クロスヘッジ時の実現価格（分解）

$$F_1 + (S_2^* - F_2) + (S_2 - S_2^*)$$

- $S_2^*$: ヘッジ決済時の先物原資産のスポット価格
- 第1項: ベーシス（先物原資産が同じ場合）
- 第2項: 原資産の違いによるベーシス

<!-- Hull eq. (implicit, Section 3.3) -->

### 最小分散ヘッジ比率 (Optimal Hedge Ratio)

$$h^* = \rho\,\frac{\sigma_S}{\sigma_F}$$

- $\rho$: $\Delta S$ と $\Delta F$ の相関係数
- $\sigma_S$: $\Delta S$（スポット価格変化）の標準偏差
- $\sigma_F$: $\Delta F$（先物価格変化）の標準偏差

<!-- Hull eq. (3.1) -->

### ヘッジ効果 (Hedge Effectiveness)

$$\text{Hedge effectiveness} = \rho^2$$

回帰 $\Delta S$ on $\Delta F$ の決定係数 $R^2$ に等しい。

<!-- Hull eq. (implicit, Section 3.4) -->

### 最適先物枚数（量ベース）

$$N^* = \frac{h^* Q_A}{Q_F}$$

- $Q_A$: ヘッジ対象ポジションのサイズ（単位数）
- $Q_F$: 先物1枚あたりの単位数

<!-- Hull eq. (3.2) -->

### 最適先物枚数（日次決済調整・価値ベース）

$$N^* = \hat{h}\,\frac{V_A}{V_F}$$

ここで $\hat{h} = \hat{\rho}\,\hat{\sigma}_S / \hat{\sigma}_F$（日次変化率の回帰より推定）、$V_A = S\,Q_A$、$V_F = F\,Q_F$。

<!-- Hull eq. (3.3) -->

### 株式ポートフォリオのヘッジ（インデックス mirror の場合）

$$N^* = \frac{V_A}{V_F}$$

<!-- Hull eq. (3.4) -->

### 株式ポートフォリオのヘッジ（ベータ考慮）

$$N^* = \beta\,\frac{V_A}{V_F}$$

- $\beta$: ポートフォリオのベータ
- $V_A$: ポートフォリオの現在価値
- $V_F$: 先物価格 × コントラクト乗数（1枚あたりの価値）

<!-- Hull eq. (3.5) -->

### ベータ変更（$\beta \to \beta^*$）

$$\text{Short } (\beta - \beta^*)\frac{V_A}{V_F} \text{ contracts} \quad (\beta > \beta^*)$$
$$\text{Long } (\beta^* - \beta)\frac{V_A}{V_F} \text{ contracts} \quad (\beta < \beta^*)$$

<!-- Hull eq. (implicit, Section 3.5) -->

### CAPM（付録 3A）

$$E(R) = R_F + \beta\bigl(E(R_M) - R_F\bigr)$$

- $R_F$: リスクフリーレート
- $R_M$: 市場ポートフォリオのリターン
- $\beta$: 系統的リスクの尺度（市場超過リターンへの感応度）

<!-- Hull eq. (3A.1) -->

## 4. アルゴリズム / 手順

### クロスヘッジの手順

1. **データ収集**: ヘッジ期間と同じ長さの重複しない時間区間について $\Delta S$（ヘッジ対象のスポット価格変化）と $\Delta F$（使用先物の価格変化）を収集する。
2. **回帰推定**: $\Delta S = a + h\,\Delta F + \epsilon$ を OLS で推定し、$\hat{h}^* = \hat{b}$（傾き係数）、$\rho$（相関係数）を得る。
3. **最適ヘッジ比率計算**: $h^* = \rho\,\sigma_S / \sigma_F$（または回帰の傾き）。
4. **枚数計算**: $N^* = h^* \cdot Q_A / Q_F$（量ベース）または $N^* = \hat{h}\,V_A/V_F$（日次決済考慮・価値ベース）を四捨五入。
5. **ヘッジ設定**: 計算した枚数の先物ポジションを設定（ショートまたはロング）。
6. **モニタリング**: スポット・先物価格の動向を追跡し、ベーシスの変化を確認。
7. **決済**: 保有資産の売買と同時に先物をクローズアウト。実現価格 $\approx F_1 + b_2$ を確認。

### ベータヘッジの手順

1. ポートフォリオのベータ $\beta$、現在価値 $V_A$ を確認。
2. 使用する指数先物1枚の価値 $V_F =$ 先物価格 × コントラクト乗数 を計算。
3. 売り枚数 $N^* = \beta \cdot V_A / V_F$ を計算（端数切捨て/四捨五入）。
4. ショートポジションを設定。ヘッジ後のベータはゼロ（または $\beta^*$）に近づく。

## 5. Python reference

```python
import numpy as np


def optimal_hedge(rho: float, sigma_S: float, sigma_F: float,
                  Q_A: float, Q_F: float) -> dict:
    """Compute minimum-variance hedge ratio and optimal number of contracts.

    Args:
        rho: Correlation between changes in spot and futures prices.
        sigma_S: Std dev of spot price changes (same units as sigma_F).
        sigma_F: Std dev of futures price changes.
        Q_A: Size of position being hedged (units).
        Q_F: Size of one futures contract (units).

    Returns:
        dict with keys 'h_star' and 'N_star'.
    """
    h_star = rho * sigma_S / sigma_F          # Hull eq. (3.1)
    N_star = h_star * Q_A / Q_F               # Hull eq. (3.2)
    return {"h_star": h_star, "N_star": N_star}


def beta_hedge(beta: float, V_A: float, F: float, multiplier: float,
               beta_target: float = 0.0) -> dict:
    """Compute number of index futures contracts for beta hedging.

    Args:
        beta: Current portfolio beta.
        V_A: Current portfolio value ($).
        F: Current index futures price (index points).
        multiplier: Contract multiplier ($ per index point, e.g. 250 for S&P 500).
        beta_target: Desired beta after hedge (default 0 = full hedge).

    Returns:
        dict with 'V_F' (value of one contract) and 'N_star' (contracts,
        positive = short, negative = long).
    """
    V_F = F * multiplier                                  # Hull eq. (3.5) notation
    N_star = (beta - beta_target) * V_A / V_F             # Hull eq. (3.5) / change-beta
    return {"V_F": V_F, "N_star": N_star}


# --- Example: cross hedge (jet fuel with heating oil futures) ---
result = optimal_hedge(rho=0.928, sigma_S=0.0263, sigma_F=0.0313,
                       Q_A=2_000_000, Q_F=42_000)
print(f"h* = {result['h_star']:.4f}")   # => h* = 0.7800
print(f"N* = {result['N_star']:.1f}")   # => N* = 37.1  (round to 37)

# --- Example: S&P 500 beta hedge ---
bh = beta_hedge(beta=1.5, V_A=5_050_000, F=1010, multiplier=250)
print(f"V_F = {bh['V_F']:,.0f}")        # => V_F = 252,500
print(f"N* = {bh['N_star']:.2f}")       # => N* = 30.00  (short 30 contracts)
```

## 6. 注意点 / 典型的なミス

- **$h^* = 1$ は常に最適ではない**: 先物の価格変動率がスポットより大きい場合、$h^* < 1$ が最適。先物原資産とヘッジ対象が同じでも $\sigma_F \neq \sigma_S$ ならば 1.0 からずれる。
- **推定データの時間区間**: $\rho$, $\sigma_S$, $\sigma_F$ はヘッジ期間と同じ長さの区間で測定するのが理想。短すぎる区間は雑音が増加し、長すぎると古いデータが混入する。
- **日次決済の影響（tailing）**: 先物は日次決済されるため、フォワードとして扱うと枚数が若干過大になる。残存期間と金利で $N^*$ を割り引く（tailing the hedge）。
- **競合他社がヘッジしていない場合**: 業界全体がヘッジしない慣行の中で1社だけヘッジすると、原材料価格が下落したときに利益率が悪化する逆説（SafeandSure 事例）。ヘッジが必ずしも良い結果を生むとは限らない。
- **キャッシュフローのタイミング不一致（Stack and roll）**: 長期エクスポージャーを短期先物でヘッジすると、先物の損益は即座に現金化されるが、ヘッジ対象のキャッシュフローは将来に発生する。原材料価格が下落すると即時のマージンコールが発生し流動性危機に至る（Metallgesellschaft の教訓）。
- **ベータは安定しない**: ポートフォリオのベータは市場環境によって変化する。定期的に再推定が必要。
- **$\rho^2 < 1$ = cross hedge risk が残存**: ヘッジ効果 $\rho^2$ が示すとおり、完全ヘッジは達成されない。残るリスクはクロスヘッジのベーシスリスク。

## 7. 関連トピック

- See: [Ch.02 Futures Markets](ch02_futures_markets.md) — 先物の基本メカニズム、日次決済
- See: [Ch.05 Determination of Forward and Futures Prices](ch05_forward_futures_pricing.md) — ベーシスの理論値（cost-of-carry）
- See: [Ch.06 Interest Rate Futures](ch06_ir_futures.md) — 金利先物によるデュレーションヘッジ（ベータヘッジの金利版）
- See: [Ch.19 The Greek Letters](ch19_greeks.md) — デルタヘッジ（動的ヘッジ）
- See: [topics/hedging.md](../topics/hedging.md) — ヘッジ戦略の横断まとめ
