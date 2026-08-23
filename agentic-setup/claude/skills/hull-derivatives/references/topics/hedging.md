# Topic: Hedging Strategies Using Futures

## 対応章
- Ch.3 Hedging Strategies Using Futures — [chapters/ch03_hedging.md](../chapters/ch03_hedging.md)

## クイック公式

### 最小分散ヘッジ比率
$$h^* = \rho\,\frac{\sigma_S}{\sigma_F}$$
- $\rho$: $\Delta S$（スポット価格変化）と $\Delta F$（先物価格変化）の相関係数
- $\sigma_S$, $\sigma_F$: それぞれの標準偏差（同一期間・同一単位で計測）
- See: ch3 §3

### 最適先物枚数（量ベース）
$$N^* = h^* \frac{Q_A}{Q_F}$$
- $Q_A$: ヘッジ対象ポジションのサイズ（単位数）, $Q_F$: 先物1枚あたりの単位数
- See: ch3 §3

### 株式ポートフォリオのベータヘッジ
$$N^* = \beta\,\frac{V_A}{V_F}$$
- $\beta$: ポートフォリオの市場ベータ, $V_A$: ポートフォリオ時価, $V_F$: 先物1枚の時価（= 先物価格 × 乗数）
- See: ch3 §3

### ベータ変更（$\beta \to \beta^*$）
$$N^* = (\beta^* - \beta)\,\frac{V_A}{V_F}$$
- $N^* > 0$（ロング）: ベータを引き上げる。$N^* < 0$（ショート）: ベータを引き下げる
- 完全ヘッジは $\beta^* = 0$、すなわち $N^* = -\beta\, V_A / V_F$ 枚のショート
- See: ch3 §3

### ヘッジ効果
$$\text{Hedge effectiveness} = \rho^2 = R^2$$
- 回帰 $\Delta S \sim \Delta F$ の決定係数に等しい。除去できない分散比率 = $1 - \rho^2$
- See: ch3 §3

## 実装スニペット

```python
import numpy as np


def optimal_hedge_n(rho: float, sigma_S: float, sigma_F: float,
                    Q_A: float, Q_F: float) -> dict:
    """Minimum-variance hedge ratio and optimal contract count.

    Args:
        rho: correlation between spot and futures price changes
        sigma_S: std dev of spot price changes
        sigma_F: std dev of futures price changes
        Q_A: size of exposure (units)
        Q_F: size of one futures contract (units)

    Returns:
        {'h_star': float, 'N_star': float, 'effectiveness': float}
    """
    h_star = rho * sigma_S / sigma_F         # Hull eq. (3.1)
    N_star = h_star * Q_A / Q_F              # Hull eq. (3.2)
    return {"h_star": h_star, "N_star": N_star, "effectiveness": rho**2}


def beta_hedge_n(beta: float, V_A: float, F: float, multiplier: float) -> dict:
    """Contracts needed for full beta hedge (target beta = 0).

    Args:
        beta: current portfolio beta
        V_A: portfolio value ($)
        F: index futures price (index points)
        multiplier: $ per index point (e.g. 250 for S&P 500)

    Returns:
        {'V_F': float, 'N_star': float}  N_star > 0 means short
    """
    V_F = F * multiplier
    N_star = beta * V_A / V_F               # Hull eq. (3.5)
    return {"V_F": V_F, "N_star": N_star}


def change_beta_n(beta: float, beta_target: float,
                  V_A: float, F: float, multiplier: float) -> dict:
    """Contracts needed to shift portfolio beta to beta_target.

    Positive N_star -> buy (go long). Negative -> sell (go short).
    """
    V_F = F * multiplier
    N_star = (beta_target - beta) * V_A / V_F
    return {"V_F": V_F, "N_star": N_star}


# --- Examples (Hull Ch.3) ---
if __name__ == "__main__":
    # Cross hedge: jet fuel with heating oil futures
    result = optimal_hedge_n(rho=0.928, sigma_S=0.0263, sigma_F=0.0313,
                              Q_A=2_000_000, Q_F=42_000)
    print(f"h* = {result['h_star']:.4f}, N* = {result['N_star']:.1f}")  # 0.7800, 37.1

    # S&P 500 beta hedge: beta=1.5, V_A=$5.05M, F=1010, mult=250
    bh = beta_hedge_n(beta=1.5, V_A=5_050_000, F=1010, multiplier=250)
    print(f"N* (short) = {bh['N_star']:.1f}")  # 30.0

    # Change beta from 1.5 to 0.75
    cb = change_beta_n(beta=1.5, beta_target=0.75, V_A=5_050_000, F=1010, multiplier=250)
    print(f"N* (change beta) = {cb['N_star']:.1f}")  # -15.0 (short 15)
```

## デシジョンガイド

- **クロスヘッジのベーシスリスク**: ヘッジ対象と先物原資産が異なると $\rho^2 < 1$ となり残留リスクが残る。ヘッジ効果 $\rho^2$ が低い（例: 0.5以下）場合は先物ヘッジの意義を再検討する。
- **ヘッジ比率の推定期間**: $\rho$, $\sigma_S$, $\sigma_F$ は想定ヘッジ期間と同じ長さの区間で計測する。日次データで四半期ヘッジを推定すると雑音が増える。
- **Stack-and-roll のキャッシュフロー・ミスマッチ**: 短期先物を繰り返しロールして長期エクスポージャーをヘッジすると、先物損益は即時現金化されるがヘッジ対象は将来キャッシュフロー。価格下落時に即時マージンコールが流動性危機につながる（Metallgesellschaft 1993年事例）。長期ヘッジには長期先物か固定価格契約を優先する。
- **ヘッジしない選択肢**: 業界全体がヘッジしない場合、1社だけヘッジすると原材料価格低下時に競合より高コストになるリスクがある（Tailing the hedge は日次決済の小さな調整であり、上記とは別問題）。
- **デュレーションヘッジ（金利）との使い分け**: 株式ポートフォリオにはベータヘッジ、債券ポートフォリオには Ch.6 のデュレーション・ベースのヘッジ比率 $N^* = P D_P / (V_F D_F)$ を使う。どちらも「ポートフォリオ価値 × 感応度 / 先物1枚価値 × 先物感応度」という同一構造。
