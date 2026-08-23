# Ch.06 Interest Rate Futures

> **Source**: Hull 11e, Chapter 6 (pp. 152-171). Paraphrased summary for personal use.

## 1. 要点

- 債券の**クリーン価格**（クォート価格）と**ダーティ価格**（現金価格）は異なる。現金価格 = クォート価格 + 経過利息。デイカウント規則（actual/actual、30/360、actual/360）が経過利息の計算方法を決める。
- T-bondフューチャーズでは、ショートポジションが複数の**デリバラブル銘柄**から選択でき、**コンバージョン・ファクター**（CF）が各銘柄の受取価格を決定する。受取額 = 決済価格 × CF + 経過利息。
- **最安値デリバリー（CTD）債**はクォート価格 − 決済価格 × CF を最小にする銘柄。利回りが6%超では低クーポン長期債が有利、6%未満では高クーポン短期債が有利。
- **ユーロドル先物**（および後継のSOFRフューチャーズ）は短期金利に対するエクスポージャーをヘッジする。クォートが0.01動くと1契約あたり$25の損益。先物レートから前向きレートを得るには**コンベクシティ調整**が必要（先物レート > フォワードレート）。
- **デュレーション・ベースのヘッジ比率** $N^* = P D_P / (V_F D_F)$ を使うことで、ポートフォリオの金利リスクを先物で中和できる。ヘッジの有効性はイールドカーブが平行シフトするという仮定に依存する。

## 2. キー用語

- **クリーン価格（Quoted/Clean Price）**: 経過利息を含まない債券のクォート価格
- **ダーティ価格（Cash/Dirty Price）**: 実際に支払われる現金価格；クリーン価格 + 経過利息
- **デイカウント規則（Day Count Convention）**: 利息計算期間の日数カウント方法。actual/actual（米国債）、30/360（社債・地方債）、actual/360（マネーマーケット）
- **コンバージョン・ファクター（Conversion Factor, CF）**: T-bondフューチャーズで各デリバラブル銘柄に付与される係数。6%クーポン・6%割引率での額面当たり価格として定義
- **最安値デリバリー債（CTD: Cheapest-to-Deliver Bond）**: ショートが選ぶデリバリー銘柄のうち、純コストが最も低い銘柄
- **ワイルドカード・プレイ（Wild Card Play）**: CMEのT-bondフューチャーズで2時以降に通知を出せる短ポジションのオプション
- **ユーロドル先物（Eurodollar Futures）**: 3ヶ月USDLIBORに連動するCME先物。LIBORフェーズアウト後はSOFR先物に移行中
- **SOFRフューチャーズ**: 担保付翌日物調達金利（SOFR）の3ヶ月複利に基づくCME先物
- **コンベクシティ調整（Convexity Adjustment）**: 先物レートからフォワードレートを求める際の補正項；日次決済とFRAの決済タイミング差から生じる
- **デュレーション・ベースのヘッジ比率（Duration-Based Hedge Ratio）**: 先物を使ってポートフォリオの金利感応度を中和するための契約数
- **ポートフォリオ・イミュニゼーション（Portfolio Immunization）**: 資産と負債のデュレーションを一致させて金利リスクを軽減する戦略

## 3. 主要公式

### クリーン価格とダーティ価格

$$
\text{Cash Price} = \text{Quoted Price} + \text{Accrued Interest}
$$

$$
\text{Accrued Interest} = \frac{\text{Days since last coupon}}{\text{Days in coupon period}} \times \text{Coupon payment}
$$

- 米国T-bondにはactual/actual（in period）を使用
- 米国社債・地方債には30/360を使用

<!-- Hull eq. (6.1 context, p.154) -->

### Tビルのクォート価格と現金価格

$$
P = \frac{360}{n}(100 - Y)
$$

- $P$: ディスカウントレートとして表されたクォート価格
- $Y$: 現金価格（額面$100に対して）
- $n$: 残存日数（暦日）

<!-- Hull p.154 -->

### T-bondフューチャーズの受取現金（Invoice Price）

$$
\text{Cash received} = (\text{Settlement price} \times \text{CF}) + \text{Accrued interest}
$$

- CF: コンバージョン・ファクター（各デリバラブル債に固有）

<!-- Hull §6.2, p.155 -->

### 最安値デリバリー債の選択基準

$$
\text{Minimize:} \quad \text{Quoted bond price} - (\text{Settlement price} \times \text{CF})
$$

<!-- Hull §6.2, p.158 -->

### T-bondフューチャーズ価格（CTDが既知の場合）

$$
F_0 = (S_0 - I)\,e^{rT}
$$

- $S_0$: CTD債の現金価格（スポット）
- $I$: 先物期間中のクーポン現在価値
- $r$: リスクフリーレート（連続複利）
- $T$: 先物満期までの年数

<!-- Hull eq. (6.1), p.159 -->

### クォート先物価格（CTD既知）

$$
\text{Quoted futures price} = \frac{(F_0 - \text{Accrued interest at delivery})}{\text{CF}}
$$

<!-- Hull §6.2 Example 6.2, p.160 -->

### ユーロドル先物の損益（1 basis point = $25）

$$
\Delta \text{PnL} = \$1{,}000{,}000 \times 0.0001 \times 0.25 = \$25 \text{ per bp per contract}
$$

<!-- Hull §6.3, p.161 -->

### コンベクシティ調整（Eurodollar / SOFR先物）

$$
\text{Forward Rate} = \text{Futures Rate} - \tfrac{1}{2}\sigma^2 t_1 t_2
$$

- $\sigma$: 短期金利の年次ボラティリティ
- $t_1$: 先物満期までの年数
- $t_2$: 先物レートが適用される期間の終了時点（年）
- 調整項は正なので、フォワードレート < 先物レート

<!-- Hull §6.3 Convexity Adjustments, pp.163-164 -->

### ゼロカーブのブートストラップ（先物利用）

$$
R_2 = \frac{R_F(T_2 - T_1) + R_1 T_1}{T_2}
$$

- $R_F$: $T_1$ から $T_2$ 期間のフォワードレート（連続複利）
- $R_1, R_2$: 満期 $T_1, T_2$ のゼロレート

<!-- Hull eq. (6.2), p.164 -->

### デュレーション・ベースのヘッジ比率

$$
N^* = \frac{P\, D_P}{V_F\, D_F}
$$

- $P$: ヘッジ対象ポートフォリオの（将来時点の）価値
- $D_P$: ヘッジ満期時のポートフォリオのデュレーション
- $V_F$: 先物1契約あたりの価格（= 決済価格 × 契約倍率）
- $D_F$: 先物満期時点でのCTD債デュレーション

<!-- Hull eq. (6.3), p.166 -->

## 4. アルゴリズム / 手順

### 最安値デリバリー債の特定手順

1. デリバリー月において、各デリバラブル債 $i$ のクォート価格 $Q_i$ とCF $c_i$ を取得する。
2. 直近決済価格 $F$ を記録する。
3. 各債券について純コストを計算する：
   $$\text{Net cost}_i = Q_i - F \times c_i$$
4. 純コストが最小の債券がCTD債となる。
5. 利回りが6%超なら低クーポン長期債が有利になる傾向、6%未満なら高クーポン短期債が有利になる傾向。イールドカーブの傾きも影響する（右上がりなら長期、右下がりなら短期が有利）。

### コンバージョン・ファクターの計算手順（CBOTルール）

1. 対象債券の満期と直近クーポン日を最寄りの3ヶ月単位に切り捨てる（T-bond/T-note先物の場合）。
2. 切り捨て後の残存期間が6ヶ月の整数倍かどうかを確認する。
   - 整数倍の場合：最初のクーポンを6ヶ月後に支払うと仮定。
   - 整数倍でない（端数3ヶ月あり）場合：最初のクーポンを3ヶ月後に支払うと仮定し、最終的に経過利息を差し引く。
3. 全クーポンと元本を年率6%（半年複利、つまり3%/半年）で現在価値に割り引く。
4. 額面$100で割ってCFを求める。

**例（10%クーポン、残存20年2ヶ月 → 20年に切り捨て）**:
$$
\sum_{i=1}^{40} \frac{5}{1.03^i} + \frac{100}{1.03^{40}} = 146.23 \implies \text{CF} = 1.4623
$$

### デュレーション・ベースのヘッジ実施手順

1. ポートフォリオ価値 $P$ とヘッジ満期時のデュレーション $D_P$ を推定する。
2. ヘッジに使う先物を選定し、CTD債とそのデュレーション $D_F$ を特定する。
3. 先物価格から1契約あたりの価値 $V_F$ を算出する。
4. $N^* = P D_P / (V_F D_F)$ で契約数を計算し、最寄り整数に丸める。
5. 金利上昇リスク（ポートフォリオ価値低下リスク）→ショートポジション；金利低下リスク → ロングポジション。
6. ヘッジ中にCTD債が変わった場合はポジションを調整する。

## 5. Python reference

```python
from datetime import date
import numpy as np


def day_count_fraction(t1: date, t2: date, basis: str = "actual/actual",
                       coupon_start: date = None, coupon_end: date = None) -> float:
    """Compute day count fraction between t1 and t2.

    basis: 'actual/actual' | '30/360' | 'actual/360'
    For actual/actual, coupon_start and coupon_end define the reference period.
    """
    if basis == "actual/actual":
        if coupon_start is None or coupon_end is None:
            raise ValueError("actual/actual requires coupon_start and coupon_end")
        num = (t2 - t1).days
        denom = (coupon_end - coupon_start).days
        return num / denom
    elif basis == "30/360":
        d1, m1, y1 = t1.day, t1.month, t1.year
        d2, m2, y2 = t2.day, t2.month, t2.year
        d1 = min(d1, 30)
        d2 = min(d2, 30) if d1 == 30 else d2
        return (360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)) / 360
    elif basis == "actual/360":
        return (t2 - t1).days / 360
    else:
        raise ValueError(f"Unknown basis: {basis}")


def accrued_interest(face: float, coupon_rate: float, t1: date, t2: date,
                     coupon_start: date, coupon_end: date,
                     basis: str = "actual/actual", freq: int = 2) -> float:
    """Accrued interest from t1 to t2 (semiannual coupon by default)."""
    coupon = face * coupon_rate / freq
    dcf = day_count_fraction(t1, t2, basis, coupon_start, coupon_end)
    return coupon * dcf


def convexity_adjustment(futures_rate: float, sigma: float,
                         t1: float, t2: float) -> float:
    """Convexity adjustment: forward_rate = futures_rate - 0.5*sigma^2*t1*t2.

    Args:
        futures_rate: quoted futures rate (e.g. 0.033 for 3.3%)
        sigma:        annual volatility of short rate
        t1:           futures contract expiry (years from now)
        t2:           end of the rate application period (years from now)
    Returns:
        forward_rate
    """
    adj = 0.5 * sigma**2 * t1 * t2
    return futures_rate - adj


def n_futures(P: float, DP: float, VF: float, DF: float) -> float:
    """Duration-based hedge ratio (Hull eq. 6.3).

    Args:
        P:  forward value of portfolio being hedged ($)
        DP: duration of portfolio at hedge maturity (years)
        VF: price of one futures contract ($)
        DF: duration of CTD bond at futures maturity (years)
    Returns:
        Number of futures contracts to short (positive = short).
    """
    return (P * DP) / (VF * DF)


# --- Example usage ---
if __name__ == "__main__":
    # Accrued interest: T-bond, coupon Mar 1 – Sep 1, settle Jul 3
    ai = accrued_interest(
        face=100, coupon_rate=0.08,
        t1=date(2018, 3, 1), t2=date(2018, 7, 3),
        coupon_start=date(2018, 3, 1), coupon_end=date(2018, 9, 1),
        basis="actual/actual"
    )
    print(f"Accrued interest (T-bond example): ${ai:.4f}")  # ~2.6957

    # Convexity adjustment: sigma=1.2%, t1=5yr, t2=5.25yr
    fwd = convexity_adjustment(futures_rate=0.065, sigma=0.012, t1=5.0, t2=5.25)
    print(f"Forward rate after convexity adj: {fwd*100:.4f}%")

    # Duration hedge: $10M portfolio, DP=6.8yr, VF=$93,062.50, DF=9.2yr
    n = n_futures(P=10_000_000, DP=6.80, VF=93_062.50, DF=9.20)
    print(f"Contracts to short: {n:.2f} → round to {round(n)}")  # ~79
```

## 6. 注意点 / 典型的なミス

- **クリーン/ダーティ価格の混同**: 市場クォートはクリーン価格。先物のインボイス計算や現金決済にはダーティ価格を使う。T-bondとコーポレート債でデイカウント規則が異なることに注意（actual/actual vs 30/360）。
- **CFの定義忘れ**: CFは「その債券を6%クーポン・6%利回りの標準債券に換算したときの額面比」。利回り環境が変わっても基準は常に6%固定。
- **CTD債は固定ではない**: ヘッジ期間中に利回り水準が変化すると、CTD債が変わりヘッジ比率の再調整が必要になる。
- **コンベクシティ調整の符号**: フォワードレート = 先物レート − 正の調整項。調整を忘れると、長期先物から推定したフォワードレートが過大評価される。
- **ユーロドル先物の決済タイミング**: 先物は期間開始時に決済（FRAに相当）するが、実際の利息支払いは期間末。この非対称性がコンベクシティ調整の第二の理由。
- **デュレーション・ヘッジの限界**: 平行シフト仮定に基づくため、ツイスト（長短金利の独立した動き）に対しては機能しない。GAP管理（バケット別管理）が補完手段。
- **先物価格の符号方向**: 金利が上がると先物価格は下がる。「金利上昇リスクをヘッジ」= 先物ショート。
- **30/360のカウント**: 月末調整ルールに注意。31日は30日に丸めるが、すでに $d_1=30$ の場合のみ $d_2=31$ も30に丸める。

## 7. 関連トピック

- See: Ch.04 (デュレーション・金利の基礎), Ch.05 (先物価格の決定、コスト・オブ・キャリー)
- See: Ch.07 (金利スワップ：FRAとの関係)
- See: Ch.29 (金利デリバティブ：キャップ・フロアのBlackモデル)
- See: Ch.30 (コンベクシティ・タイミング・クワント調整の詳細)
- See: [topics/interest_rates.md](../topics/interest_rates.md), [topics/futures_forwards.md](../topics/futures_forwards.md), [topics/hedging.md](../topics/hedging.md)
