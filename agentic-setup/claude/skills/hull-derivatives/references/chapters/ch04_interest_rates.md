# Ch.04 Interest Rates

> **Source**: Hull 11e, Chapter 4 (pp. 98-123). Paraphrased summary for personal use.

## 1. 要点

- 金利は複利計算頻度によって「単位」が決まる。年1回複利と半年複利は同じ数値でも異なる意味を持ち、連続複利（continuous compounding）はデリバティブ解析の標準形。
- ゼロレート（スポットレート）はn年後に一括で全リターンを受け取る投資に適用される金利。クーポン付き債券の価格は各キャッシュフローを対応するゼロレートで個別に割り引いた現在価値の合計。
- フォワードレートは現在のゼロレート曲線から無裁定条件で導出される将来期間の金利。FRA（Forward Rate Agreement）はこのフォワードレートと固定レートの差額を交換する契約。
- ブートストラップ法は短期のゼロクーポン債から順に長期のクーポン付き債券の価格を使って、整合的なゼロレート曲線を逐次的に構築する手法。
- デュレーションは金利（イールド）の小さな並行シフトに対する債券価格の感応度を測る加重平均残存期間。コンベクシティは2次の補正項で、大きなイールド変化に対する精度を高める。
- イールドカーブの形状を説明する主要理論：期待理論（forward rate = expected future spot rate）、流動性選好理論（long-term rates > expected future short-term rates due to liquidity premium）、市場分断理論（各満期が独立した需給で決定）。

## 2. キー用語

- **Treasury rate**: 政府が自国通貨で借り入れる際の金利。信用リスクなしとみなされる（税制・規制上の理由でリスクフリーレートとしては使わない）
- **Overnight rate / RFR**: 翌日物無担保（または担保付き）金利。SOFR（米）、SONIA（英）、TONAR（日）。LIBORの後継リファレンスレート
- **SOFR**: Secured Overnight Financing Rate。米国オーバーナイトレポ取引の出来高加重中央値。担保付きのため実質リスクフリー
- **Repo rate**: レポ（現先）取引の金利。証券担保の短期借入。信用リスクが極めて小さい
- **Credit spread**: リスクフリーレートへの上乗せ金利。借り手の信用リスクを反映
- **Zero rate (spot rate)**: n年ゼロクーポン金利。今日投資しn年後に元利一括受取の場合の年率
- **Par yield**: 債券価格が額面（par）に等しくなるクーポンレート
- **Yield to maturity (YTM)**: 全キャッシュフローを現在価値に等しくする単一割引率
- **Forward rate**: 現在のゼロレート曲線から算出される将来期間t1〜t2の金利
- **FRA (Forward Rate Agreement)**: 将来の特定期間に固定レートと変動レートを元本に適用して差額決済するOTC契約
- **Duration (Macaulay duration)**: イールド変化に対する債券価格変化の加重平均残存期間（連続複利ベース）
- **Modified duration**: 離散複利表示のイールドに対応したデュレーション調整値 $D^* = D/(1+y/m)$
- **DV01**: 全レートが1ベーシスポイント上昇したときの価格変化（dollar value of 1 bp）
- **Convexity**: デュレーション近似の2次補正項。大きなイールド変化に対して精度向上
- **Bootstrap method**: 短期ゼロレートから逐次的に長期ゼロレートを計算する手法
- **Liquidity preference theory**: 長期投資には流動性プレミアムが必要 → 順イールドカーブが標準的

## 3. 主要公式

### 複利計算（m回/年）

$$A\!\left(1+\frac{R}{m}\right)^{mn}$$

- $A$: 投資元本、$R$: 年率、$m$: 年間複利回数、$n$: 年数

<!-- Hull eq. (4.1) -->

### 連続複利の終価

$$A e^{R_c n}$$

- $R_c$: 連続複利レート

<!-- Hull eq. (4.2) -->

### 複利変換：m回/年 ↔ 連続複利

$$R_c = m \ln\!\left(1 + \frac{R_m}{m}\right), \qquad R_m = m\!\left(e^{R_c/m} - 1\right)$$

- $R_m$: m回複利の年率

<!-- Hull eq. (4.3), (4.4) -->

### 債券価格（連続複利ゼロレート使用）

$$B = \sum_{i=1}^{n} c_i \, e^{-R(t_i)\, t_i}$$

- $c_i$: 時刻 $t_i$ のキャッシュフロー（最終回は額面＋クーポン）
- $R(t_i)$: 満期 $t_i$ の連続複利ゼロレート

### 債券のYTM（Yield to Maturity）

$$B = \sum_{i=1}^{n} c_i \, e^{-y t_i}$$

- $y$: この方程式を $y$ について解いて得られるYTM（連続複利）

<!-- Hull eq. (4.7) -->

### パーイールド

$$c = \frac{(100 - 100\,d)\,m}{A}$$

- $d = e^{-R(T)\cdot T}$: 満期Tの割引ファクター
- $A = \sum_i e^{-R(t_i)\,t_i}$: クーポン支払日の割引ファクター合計
- $m$: 年間クーポン支払回数

### フォワードレート

$$R_F = \frac{R_2 T_2 - R_1 T_1}{T_2 - T_1}$$

- $R_1, R_2$: 満期 $T_1, T_2$ の連続複利ゼロレート（$T_2 > T_1$）
- $R_F$: 期間 $T_1$〜$T_2$ に適用されるフォワードレート

<!-- Hull eq. (4.5) -->

### FRAの価値（固定レート受取側）

$$V_{\text{FRA}} = L\,(R_K - R_F)\,(T_2 - T_1)\,e^{-R_2 T_2}$$

- $L$: 想定元本
- $R_K$: FRAで合意した固定レート
- $R_F$: 現在のフォワードレート（$T_1$〜$T_2$ 期間）
- $R_2$: 満期 $T_2$ の連続複利ゼロレート

### デュレーション（Macaulay）

$$D = \frac{\sum_{i=1}^{n} t_i\, c_i\, e^{-y t_i}}{B}$$

$$\frac{\Delta B}{B} \approx -D\,\Delta y \quad \Leftrightarrow \quad \Delta B \approx -B D\,\Delta y$$

<!-- Hull eq. (4.8), (4.12) -->

### 修正デュレーション（m回複利のyに対応）

$$D^* = \frac{D}{1 + y/m}, \qquad \Delta B = -B D^* \Delta y$$

<!-- Hull eq. (4.13) -->

### コンベクシティ

$$C = \frac{\sum_{i=1}^{n} c_i\, t_i^2\, e^{-y t_i}}{B}$$

$$\frac{\Delta B}{B} \approx -D\,\Delta y + \tfrac{1}{2}\,C\,(\Delta y)^2$$

<!-- Hull eq. (4.14) -->

## 4. アルゴリズム / 手順

### Bootstrap ゼロカーブ構築（Hull §4.7）

ゼロクーポン債とクーポン付き債券の市場価格からゼロレートを短期から順次計算する。

1. **短期ゼロクーポン債から直接計算する**
   - 満期 $T$ のゼロクーポン債（額面100、価格 $P$）に対して：
     $$R = -\frac{\ln(P/100)}{T}$$
   - 例：3ヶ月物（$T=0.25$）価格99.6 → $R = -\ln(99.6/100)/0.25 = 1.603\%$

2. **クーポン付き債券の最短満期を処理する**
   - すでに判明しているゼロレートで既知のクーポンを割り引く
   - 残余（最終キャッシュフロー）から未知ゼロレートを逆算する

3. **逐次外挿（ブートストラップ）**
   - 満期を短い順に並べ、前ステップで求めたゼロレートを使って次の満期のゼロレートを算出する
   - 例（1.5年物、価格102.5、クーポン半年2）：
     $$2 e^{-0.02010 \times 0.5} + 2 e^{-0.02225 \times 1.0} + 102\, e^{-R \times 1.5} = 102.5$$
     $$R = -\frac{\ln(0.96631)}{1.5} = 2.284\%$$

4. **ゼロカーブの補間**
   - 計算点間は線形補間（実務では区分線形またはスプライン関数）
   - 最短点以前は水平、最長点以降も水平と仮定することが多い

5. **完成したゼロレート表を使って債券価格・フォワードレートを計算する**

## 5. Python reference

```python
import numpy as np
from scipy.optimize import brentq


def bond_price(times, cashflows, zero_rates):
    """連続複利ゼロレートで債券価格を計算する。"""
    return np.sum(cashflows * np.exp(-zero_rates * times))


def bond_yield(times, cashflows, price):
    """債券のYTM（連続複利）をbrentqで解く。"""
    def objective(y):
        return np.sum(cashflows * np.exp(-y * times)) - price
    return brentq(objective, -0.5, 5.0)


def duration(times, cashflows, ytm):
    """Macaulayデュレーション（連続複利YTM使用）。"""
    pv = cashflows * np.exp(-ytm * times)
    B = pv.sum()
    return np.dot(times, pv) / B


def convexity(times, cashflows, ytm):
    """コンベクシティ（連続複利YTM使用）。"""
    pv = cashflows * np.exp(-ytm * times)
    B = pv.sum()
    return np.dot(times**2, pv) / B


def forward_rate(R1, T1, R2, T2):
    """連続複利ゼロレートからフォワードレートを計算する。"""
    return (R2 * T2 - R1 * T1) / (T2 - T1)


def fra_value(L, R_K, R_F, T1, T2, R2):
    """FRAの価値（固定レート受取側）。R_K, R_F は連続複利。"""
    return L * (R_K - R_F) * (T2 - T1) * np.exp(-R2 * T2)


# --- Example (Hull Table 4.2 / 4.6) ---
times = np.array([0.5, 1.0, 1.5, 2.0])
zero_rates = np.array([0.050, 0.058, 0.064, 0.068])
cashflows = np.array([3.0, 3.0, 3.0, 103.0])

price = bond_price(times, cashflows, zero_rates)          # 98.39
ytm   = bond_yield(times, cashflows, price)               # 0.0676
D     = duration(times, cashflows, ytm)                   # ~1.91
C     = convexity(times, cashflows, ytm)
RF    = forward_rate(0.030, 1.0, 0.040, 2.0)             # 0.050
fra_v = fra_value(1e8, 0.058, 0.050, 1.5, 2.0, 0.040)   # 369,200

print(f"Bond price: {price:.2f}, YTM: {ytm:.4f}")
print(f"Duration: {D:.3f}, Convexity: {C:.3f}")
print(f"Forward rate: {RF:.4f}, FRA value: {fra_v:,.0f}")
```

## 6. 注意点 / 典型的なミス

- **複利単位の混同**: ゼロレートは「連続複利」で扱うのがHullの本書標準。債券イールドや市場慣行（半年複利など）との変換を忘れると計算が狂う。変換式 $R_c = m\ln(1+R_m/m)$ を常に確認すること。
- **デュレーションの前提**: $\Delta B \approx -BD\Delta y$ はイールドカーブが**並行シフト**（parallel shift）する場合の近似。非並行シフトには対応しない。
- **修正デュレーションとMacaulayデュレーションの取り違え**: 連続複利ベースのYTMを使う場合は $D^*=D$（修正不要）。離散複利の場合のみ $D^*=D/(1+y/m)$ が必要。
- **FRAのレート表示**: Hull §4.9のFRA公式は連続複利ベース。市場では四半期複利や半年複利で表示することが多いため、変換を事前に行うこと。例（Example 4.3）: 5.8%（半年複利）をそのまま使わず連続複利に変換してから差額計算する必要がある（公式自体は差額なので同じ複利表示であれば変換不要だが、混在する場合は注意）。
- **ブートストラップの順序エラー**: 長期のゼロレートを計算するとき、短期のゼロレートがすでに確定していることが前提。計算順序を逆にしたり、同時に解こうとするミスが起きやすい。
- **コンベクシティの符号**: $\Delta B/B \approx -D\Delta y + \tfrac{1}{2}C(\Delta y)^2$ の第2項は常に正（$C>0$ for plain bonds）。したがって、デュレーション単独の近似より実際の価格変化は「小さな損・大きな益」にバイアスがある（convexity is always favorable for long bond positions）。
- **ゼロレートとYTMの差異**: ゼロレートは特定満期のスポットレート。YTMは同一割引率で全キャッシュフローを割り引く仮定的な単一レート。順イールドカーブ下ではYTM < 最長ゼロレート。

## 7. 関連トピック

- See: Ch.06 Interest Rate Futures（デュレーションを使ったヘッジ、デイカウント慣行）
- See: Ch.07 Swaps（FRAの集合としての金利スワップ、ゼロカーブ構築への応用）
- See: Ch.29 Interest Rate Derivatives: The Standard Market Models（Black's model for caps/floors/swaptions）
- See: Ch.31-32 Short Rate Models（Vasicek, Hull-White: ゼロカーブのモデル化）
- See: Ch.33 Modeling Forward Rates（HJM framework）
- Topics: [interest_rates](../topics/interest_rates.md), [swaps](../topics/swaps.md), [ir_derivatives](../topics/ir_derivatives.md)
