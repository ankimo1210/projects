# Ch.10 Mechanics of Options Markets

> **Source**: Hull 11e, Chapter 10 (pp. 227-246). Paraphrased summary for personal use.

## 1. 要点
- コールは原資産を買う権利、プットは売る権利。オプション保有者は義務を負わず、行使するかどうかを自由に選べる点が先物・フォワードと根本的に異なる。
- 取引所上場の株式オプションは通常アメリカン型（100株単位）。満期日は満期月の第3金曜日。権利行使価格は株価水準に応じて$2.50/$5/$10刻みで列挙される。
- 株式分割・株式配当はオプション契約条件の調整対象（権利行使価格と株数を比例調整）。現金配当は通常調整されない（例外：配当が株価の10%超）。
- オプション売り手（ライター）は義務を負うためマージン提供が必要。OCC（Options Clearing Corporation）が清算機関として義務履行を保証する。
- OTC市場は取引所市場より規模が大きく、顧客ニーズに合わせてカスタマイズできる半面、デフォルトリスク（信用リスク）が生じる。

## 2. キー用語
- **call option**: 原資産を指定価格で買う権利
- **put option**: 原資産を指定価格で売る権利
- **strike price (exercise price)**: オプション契約に定められた売買価格 $K$
- **expiration date (maturity date)**: オプションの権利が消滅する日付
- **American option**: 満期日までの任意のタイミングで行使可能なオプション
- **European option**: 満期日のみ行使可能なオプション
- **in the money**: コールは $S > K$、プットは $S < K$ の状態
- **at the money**: $S = K$ の状態
- **out of the money**: コールは $S < K$、プットは $S > K$ の状態
- **intrinsic value**: オプションを今すぐ行使したときの価値。コール $\max(S-K,0)$、プット $\max(K-S,0)$
- **time value**: オプション価格から本質的価値を引いた残余価値（時間プレミアム）
- **option class**: 同一原資産に対する同種（コールまたはプット）のオプション全体
- **option series**: 同一クラス内で満期と権利行使価格が同じオプション群
- **FLEX option**: CBOE が提供する非標準条件（満期・権利行使価格・行使スタイル等を自由設定）オプション
- **naked option**: 原資産のオフセットポジションを持たずに書いたオプション
- **covered call**: 株式を保有した状態で書くコールオプション（最もリスクが低い）
- **LEAPS**: 満期最長39ヶ月の長期株式オプション（Long-term Equity AnticiPation Securities）
- **OCC (Options Clearing Corporation)**: 取引所オプション取引の清算機関。ライターの義務履行を保証
- **warrant**: 金融機関や事業会社が発行するオプション。行使時に発行体が新株を発行する点が取引所オプションと異なる
- **employee stock option (ESO)**: 会社が従業員に付与するコールオプション。公正価値で費用計上義務あり
- **convertible bond**: 株式に転換できる社債。株式コールオプションが内包されている
- **wash sale rule**: 損失確定後30日以内に同一（実質同一）証券を再取得すると損失が税務上不算入になる規則
- **constructive sale**: 実質的な売却とみなされる取引（1997年税制改正で規定）。ショートセール・先物等での完全ヘッジが対象

## 3. 主要公式

### コール・プット payoff（4式）

**Long call payoff**
$$ \max(S_T - K,\ 0) $$

**Short call payoff**
$$ -\max(S_T - K,\ 0) = \min(K - S_T,\ 0) $$

**Long put payoff**
$$ \max(K - S_T,\ 0) $$

**Short put payoff**
$$ -\max(K - S_T,\ 0) = \min(S_T - K,\ 0) $$

- $S_T$: 満期時の原資産価格
- $K$: 権利行使価格

<!-- Hull §10.2 (Fig. 10.5) -->

### 株式分割・株式配当後の契約条件調整

$n$-for-$m$ 株式分割後（$n > m$）:
$$ K_{\text{new}} = K_{\text{old}} \times \frac{m}{n}, \quad N_{\text{new}} = N_{\text{old}} \times \frac{n}{m} $$

- $K_{\text{old}},\, K_{\text{new}}$: 調整前後の権利行使価格
- $N_{\text{old}},\, N_{\text{new}}$: 調整前後の1契約当たり株数（通常 $N_{\text{old}} = 100$）

例: 3-for-2 分割 → $K_{\text{new}} = K \times \frac{2}{3}$、$N_{\text{new}} = 150$ 株

<!-- Hull §10.4 "Dividends and Stock Splits" -->

### Naked call ライターのマージン要件（CBOE）

$$\text{Margin} = \max\!\left(\text{proceeds} + 0.20\,S - \text{OTM amount},\quad \text{proceeds} + 0.10\,S\right)$$

- $S$: 原資産現在価格
- OTM amount: オプションが Out-of-the-money である金額（ITMなら0）
- 株価指数オプションは 20% → 15% に変更
- ネイキッドプットでも同様（プットの場合 OTM amount の計算が逆）

<!-- Hull §10.7 "Writing Naked Options" -->

## 4. アルゴリズム / 手順

### 株式分割・株式配当後の契約条件調整手順
1. コーポレートアクション（分割比率 $n:m$ または株式配当率）を確認する。
2. 権利行使価格を $K_{\text{new}} = K_{\text{old}} \times m/n$ に変更する。
3. 1契約当たり株数を $N_{\text{new}} = N_{\text{old}} \times n/m$ に変更する。
4. 調整後、双方のポジション価値は不変であることを確認する（期待値保全の原則）。
5. 現金配当の場合は原則調整なし（例外: 配当が株価の 10% 超なら CBOE 委員会が判断）。

### 新規満期・権利行使価格の追加ルール
1. 各銘柄はJanuary / February / March サイクルのいずれかに属する。
2. 当月満期がまだ到来していない場合: 当月・翌月・サイクルの次の2ヶ月の計4満期を提供する。
3. 当月満期が過ぎた場合: 翌月・翌々月・サイクルの次の2ヶ月の計4満期に移行する。
4. 株価が既存の権利行使価格帯から外れたとき、取引所が新ストライクを追加設定する。
5. LEAPS は常に1月第3金曜日の満期で、最長39ヶ月先まで提供される。

### OCC による権利行使処理
1. 投資家がブローカーに行使指示を出す。
2. ブローカーが OCC メンバーに通知 → OCC が同一オプションのショートポジション保有メンバーをランダム選択。
3. 選ばれたメンバーが特定のライターを（事前ルールで）割り当てる（*assigned*）。
4. コールなら担当ライターが株式を権利行使価格で売却、プットなら購入。
5. 株式の受渡は行使の翌3営業日後。

## 5. Python reference

```python
import numpy as np
import matplotlib.pyplot as plt


def call_payoff(S_T: np.ndarray, K: float) -> np.ndarray:
    """Long call payoff at expiration."""
    return np.maximum(S_T - K, 0.0)


def put_payoff(S_T: np.ndarray, K: float) -> np.ndarray:
    """Long put payoff at expiration."""
    return np.maximum(K - S_T, 0.0)


def long_short_combinations(
    S_T: np.ndarray,
    K: float,
    option: str = "call",
    position: str = "long",
    premium: float = 0.0,
) -> np.ndarray:
    """
    Net profit for a single vanilla option position.

    Parameters
    ----------
    S_T      : array of terminal stock prices
    K        : strike price
    option   : 'call' or 'put'
    position : 'long' or 'short'
    premium  : option price paid (positive for buyer, i.e. cost)
    """
    if option == "call":
        payoff = call_payoff(S_T, K)
    else:
        payoff = put_payoff(S_T, K)

    if position == "long":
        return payoff - premium
    else:
        return -payoff + premium


# --- Example: payoff diagram for all four positions ---
S = np.linspace(60, 140, 500)
K, c, p = 100.0, 5.0, 5.0

fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
specs = [
    ("call", "long",  c, "Long Call"),
    ("call", "short", c, "Short Call"),
    ("put",  "long",  p, "Long Put"),
    ("put",  "short", p, "Short Put"),
]
for ax, (opt, pos, prem, title) in zip(axes.flat, specs):
    profit = long_short_combinations(S, K, opt, pos, prem)
    ax.plot(S, profit)
    ax.axhline(0, color="k", linewidth=0.8)
    ax.axvline(K, color="grey", linestyle="--", linewidth=0.8)
    ax.set_title(title)
    ax.set_xlabel("$S_T$")
    ax.set_ylabel("Profit ($)")

plt.tight_layout()
plt.show()
```

## 6. 注意点 / 典型的なミス
- **現金配当に契約調整はない**（原則）。「配当が出ればオプション条件が変わる」と誤解しやすい。変わるのは株式分割・株式配当の場合のみ。
- **アメリカン vs ヨーロピアン**の混同。取引所上場株式オプションの大半はアメリカン型。ITMのアメリカンでも、必ずしも早期行使が最適とは限らない（時間価値の喪失）。
- **Payoff と Profit の混同**。ペイオフはプレミアム無視の行使時受取額。利益（profit）はプレミアムのコストを差し引いた値。
- **Short callのマージン計算**。ネイキッドコールが OTM のとき「OTM amount を差し引く」が、ITM ではこの減額がゼロになるため計算が大きくなる（より多くのマージンが必要）。
- **ライター行使の流れ**。OCC はランダムにメンバーを選ぶが、メンバー内でのライター選定は「事前に確立した手続き」（通常はランダムまたは先入れ先出し）による。
- **Wash Sale Rule**：損失確定後30日前後（合計61日間）に同一証券や同種のオプションを取得すると損失が不算入。オプションでの再取得も対象になる点に注意。
- **ワラントとESO行使時は希薄化が生じる**。取引所オプション行使時には既発行株の転売であり、会社は関与しない。

## 7. 関連トピック
- See: Ch.11 (Properties of Stock Options — put-call parity, bounds)
- See: Ch.12 (Trading Strategies — spreads, straddles, covered calls)
- See: Ch.17 (Options on Stock Indices and Currencies)
- See: Ch.18 (Futures Options and Black's Model)
- See: Ch.16 (Employee Stock Options — ESO valuation, expensing)
- See: Ch.26 (Exotic Options — OTC non-standard structures)
