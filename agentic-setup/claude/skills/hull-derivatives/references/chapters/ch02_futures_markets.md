# Ch.02 Futures Markets and Central Counterparties

> **Source**: Hull 11e, Chapter 2 (pp. 46-69). Paraphrased summary for personal use.

## 1. 要点

- 先物契約は取引所で標準化されており、原資産・契約サイズ・受渡し場所・受渡し月が取引所によって規定される。大多数の契約は受渡し前にポジションを反対売買（close out）することで決済される。
- **マージン制度（daily settlement / marking to market）** が先物の中核。毎営業日末に損益がマージン口座に反映され、維持マージンを下回るとマージンコールが発生し、初期マージン水準まで補充が求められる。
- 取引所のクリアリングハウスが全取引の相手方となり、デフォルトリスクを吸収する。CCPはOTC市場にも同様の機能を提供し、2010年ドッド＝フランク法以降、金融機関間の標準的OTCデリバティブはCCPを通じた清算が義務付けられた。
- 先物価格は受渡し期間が近づくにつれ現物（スポット）価格に収束する。この収束が保証されるのは、価格乖離があれば裁定取引が成立するためである。
- 先物契約とフォワード契約の主要な違いは、標準化・取引所上場・日次決済の有無にある（Table 2.3）。

## 2. キー用語

- **Futures price**: 先物契約で合意された将来の売買価格。需給により決定される。
- **Long / Short futures position**: 買い先物（ロング）は将来受取り側、売り先物（ショート）は将来引渡し側。
- **Closing out**: 元の先物ポジションと反対の取引を行ってポジションを解消すること。
- **Initial margin**: 契約締結時にマージン口座へ預け入れる必要最低額。
- **Maintenance margin**: マージン口座残高の最低維持水準（通常は初期マージンの約75%）。
- **Margin call**: 口座残高が維持マージンを下回った際、初期マージン水準まで補充するよう要求されること。
- **Variation margin**: 日次決済に伴うマージン口座の損益変動額。ロングとショートの間で資金が移動する。
- **Daily settlement (marking to market)**: 毎日の清算価格に基づき損益をマージン口座に反映する仕組み。
- **Settlement price**: 取引日の終値付近で算出され、日次損益計算およびマージン要件算定に使用される価格。
- **Open interest**: 未決済のロングポジション（またはショートポジション）数。取引高（volume）とは別概念。
- **Clearing house**: 取引所の全先物取引の法的相手方となり、履行を保証する機関。
- **Central Counterparty (CCP)**: OTC市場においてクリアリングハウスと同等の機能を果たす中央清算機関。
- **Bilateral clearing**: CCP非経由のOTC取引清算。Credit Support Annex (CSA) / ISDA Master Agreement を通じた担保（collateral）管理が伴う。
- **Haircut**: 担保として差し入れる有価証券の市場価値に適用される割引率。マージン目的での評価額を減額する。
- **Normal market / Inverted market**: 先物価格が満期に向けて上昇するのがnormal、下落するのがinverted。
- **Limit up / Limit down**: 前日比で日次価格変動制限幅に達した状態。
- **Position limit**: 投機筋が保有できる契約数の上限。市場への過度な影響を防ぐ目的。
- **First notice day**: ショートポジション保有者が取引所に受渡し意思通知を提出できる最初の日。
- **Last trading day**: 取引最終日。一般に最終通知日の数日前。
- **Cash settlement**: 実物受渡しに代えてスポット価格と先物価格の差額を現金決済する方式（株価指数先物など）。
- **FCM (Futures Commission Merchant)**: 顧客の注文を執行し手数料を受取るブローカー。
- **Scalper / Day trader / Position trader**: 超短期・1日以内・長期の各時間軸で取引する投機筋の分類。
- **Hedge accounting**: ヘッジ目的の先物損益を、ヘッジ対象の損益と同期間に認識する会計処理。
- **60/40 rule**: 米国税制上、先物ポジションを期末に清算とみなし、損益の60%を長期・40%を短期キャピタルゲインとして扱うルール。

## 3. 主要公式

### 日次損益（Daily P&L）

$$
\Delta V_t = (F_t - F_{t-1}) \times N
$$

- $F_t$: $t$ 日の清算価格（settlement price）
- $F_{t-1}$: 前日の清算価格
- $N$: 保有契約数 × 契約サイズ（ロングの場合は正、ショートは符号反転）

<!-- Hull narrative, pp. 51-52 (Table 2.1 の数値例から導出) -->

### マージンコール発生条件

$$
B_t < M_{\text{maintenance}} \implies \text{Margin call} = M_{\text{initial}} - B_t
$$

- $B_t$: $t$ 日末のマージン口座残高
- $M_{\text{maintenance}}$: 維持マージン水準
- $M_{\text{initial}}$: 初期マージン水準

<!-- Hull narrative, p. 52 -->

## 4. アルゴリズム / 手順

### マージン口座の日次決済手順

1. 取引開始時に $M_{\text{initial}}$ をマージン口座に預け入れる。
2. 各営業日の終値付近でクリアリングハウスが **settlement price** $F_t$ を決定する。
3. $\Delta V_t = (F_t - F_{t-1}) \times N$ を計算し、ロングの場合は口座残高に加算、ショートの場合は減算する（日次決済）。
4. 残高 $B_t$ を確認する。
   - $B_t \geq M_{\text{maintenance}}$: 翌営業日も保有継続。$B_t > M_{\text{initial}}$ の超過分は引出し可能。
   - $B_t < M_{\text{maintenance}}$: マージンコール発生。$M_{\text{initial}} - B_t$ を翌営業日の取引終了前までに補充する。
5. 補充がなければブローカーはポジションを強制決済（close out）する。
6. ポジションを反対売買で解消したい場合は、いつでも手順3を最終回として口座を清算できる。

### 受渡し（Delivery）手順（現物受渡しの場合）

1. ショートポジション保有者（trader A）が受渡しを決定し、ブローカーを通じて取引所に **notice of intention to deliver** を提出する。
2. 取引所は最も古いロングポジション保有者（trader B）に通知を転送する。
3. Trader B は倉荷証券（warehouse receipt）を受取り、即時の代金支払いを行う。
4. 価格は直近の清算価格を基準に、グレード・受渡し場所などに応じて調整される。

## 5. Python reference

```python
import numpy as np

def simulate_margin_account(
    entry_price: float,
    settlement_prices: list[float],
    contract_size: int,
    n_contracts: int,
    initial_margin: float,
    maintenance_margin: float,
    long: bool = True,
) -> dict:
    """
    Simulate daily mark-to-market for a futures position.

    Returns dict with daily balance, variation margin, and margin calls.
    """
    direction = 1 if long else -1
    balance = initial_margin
    prev_price = entry_price

    history = []
    for day, price in enumerate(settlement_prices, start=1):
        daily_pnl = direction * (price - prev_price) * contract_size * n_contracts
        balance += daily_pnl
        margin_call = 0.0
        if balance < maintenance_margin:
            margin_call = initial_margin - balance
            balance = initial_margin  # topped up
        history.append({
            "day": day,
            "settlement": price,
            "daily_pnl": daily_pnl,
            "margin_call": margin_call,
            "balance": balance,
        })
        prev_price = price
    return history


# --- Example: Hull Table 2.1 (2 gold contracts, long) ---
prices = [
    1741.00, 1738.30, 1744.60, 1741.30, 1740.10,
    1736.20, 1729.90, 1730.80, 1725.40, 1728.10,
    1711.00, 1711.00, 1714.30, 1716.10, 1723.00, 1726.90,
]

result = simulate_margin_account(
    entry_price=1750.00,
    settlement_prices=prices,
    contract_size=100,
    n_contracts=2,
    initial_margin=12_000,
    maintenance_margin=9_000,
    long=True,
)

for row in result:
    mc = f"  MARGIN CALL ${row['margin_call']:,.0f}" if row["margin_call"] else ""
    print(f"Day {row['day']:2d}: settle={row['settlement']:.2f}  "
          f"pnl={row['daily_pnl']:+,.0f}  bal={row['balance']:,.0f}{mc}")
```

## 6. 注意点 / 典型的なミス

- **マージンコール後の補充額を誤解しやすい**: 補充は「維持マージンとの差額」ではなく「**初期マージン**との差額」まで求められる。
- **変動マージン（variation margin）と初期マージンの混同**: OTCのCCP清算では変動マージンは日次決済（キャッシュのみ）であり利子が付かない。初期マージンは有価証券で代用可能で利子が付く。
- **先物 vs フォワードの損益タイミング**: 同じ原資産・同じ満期でも、先物は日次決済されるため損益実現のタイミングが異なる。金利水準と価格動向の相関次第で両者の価値は微妙にずれる（Hull §2.11）。
- **ロングを受渡し前に決済し忘れるリスク**: ショート側が受渡し通知を出せるのはfirst notice day以降。ロング保有者はfirst notice day**前**にポジションをclose outしないと思わぬ現物受渡しを受けることがある（Business Snapshot 2.1）。
- **Normalマーケットとinvertedの解釈**: Normal = 先物価格が期先ほど高い（コンタンゴ）。Inverted = 期先ほど低い（バックワーデーション）。金・原油・コーン等で具体例が異なることを確認すること。
- **外国為替の先物 vs フォワードのquote方向**: 先物はUSDが常に建値（USD per 1外貨）だが、フォワードはスポット慣行に合わせて逆になる通貨がある（例: CADはフォワード = 外貨 per USD）。

## 7. 関連トピック

- See: Ch.03 (Hedging Strategies Using Futures) — 先物を使ったヘッジの実践
- See: Ch.05 (Determination of Forward and Futures Prices) — 先物・フォワード価格の理論的決定、先物とフォワードの価格差
- See: Ch.06 (Interest Rate Futures) — T-Bond/T-Note先物の特殊な仕様（conversion factor等）
- See: Ch.24 (Credit Risk) — bilateral clearingとCSAの詳細、カウンターパーティーリスク
- Related concept: CCP / systemic risk (Ch.01 §1.2, Dodd-Frank Act)
