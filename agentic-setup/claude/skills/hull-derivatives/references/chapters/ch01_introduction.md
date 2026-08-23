# Ch.01 Introduction

> **Source**: Hull 11e, Chapter 1 (pp. 23-45). Paraphrased summary for personal use.

## 1. 要点
- デリバティブとは、他の変数（原資産価格など）の値に依存する金融契約であり、取引所市場とOTC市場の両方で取引される。
- 主要な契約形態は forward、futures、options（call / put）の3種類。Forwardはカスタムのバイラテラル合意、futuresは取引所で標準化された契約。
- 市場参加者はヘッジャー（リスク削減）、スペキュレーター（レバレッジを利用した方向性ベット）、アービトラジャー（裁定利益の獲得）の3種類に分類される。
- Optionはforward/futuresと異なり、保有者に**権利**を与えるが**義務**を課さない。その非対称性の対価として、オプション購入にはプレミアムが必要。
- 2008年金融危機以降、OTC市場規制が強化され、標準化デリバティブはCCP（中央清算機関）経由の清算またはSEF（スワップ執行ファシリティ）での取引が義務付けられた。

## 2. キー用語
- **derivative**: 他の基礎変数（株価・金利・為替など）から価値が導出される金融契約
- **forward contract**: 将来の特定日時に特定価格で原資産を売買する相対（OTC）合意。取引所外で締結
- **futures contract**: forwardに類似するが取引所で標準化・清算機関を介して決済される契約
- **call option**: 原資産を満期までに（アメリカン型）または満期日に（ヨーロピアン型）特定価格で**買う**権利
- **put option**: 原資産を特定価格で**売る**権利
- **strike price (exercise price)**: オプション契約に定める行使価格
- **expiration date (maturity)**: オプション行使期限
- **long position**: 買い側ポジション（forward/futuresでは資産を買う義務、optionでは権利を保有）
- **short position**: 売り側ポジション；オプション売りは "writing the option" とも呼ぶ
- **hedger**: デリバティブを使ってリスクを軽減する参加者
- **speculator**: デリバティブのレバレッジを利用して市場方向性に賭ける参加者
- **arbitrageur**: 複数市場の価格乖離を同時取引で無リスク利益に変換する参加者
- **clearing house (CCP)**: 取引所取引またはOTC取引において買い手と売り手の間に介在し信用リスクを管理する機関
- **OTC market**: 取引所外で金融機関・事業法人間が相対で取引するデリバティブ市場
- **SEF (swap execution facility)**: 米国規制下で標準化OTCデリバティブを取引するための電子プラットフォーム
- **open outcry**: 取引所フロアでの立会い取引（現在は電子取引にほぼ置換）
- **systemic risk**: 一機関の破綻が連鎖的に金融システム全体へ波及するリスク
- **compression**: 複数カウンターパーティ間の取引を整理・相殺して想定元本を削減する手続き

## 3. 主要公式

### Forward payoff — long position
$$\text{Payoff} = S_T - K$$
- $S_T$: 満期時点の原資産スポット価格
- $K$: デリバリー価格（delivery price）

<!-- Hull eq. introduced in §1.3, p.29 -->

### Forward payoff — short position
$$\text{Payoff} = K - S_T$$

<!-- Hull eq. introduced in §1.3, p.29 -->

### No-arbitrage forward price (non-dividend-paying stock, preview)
$$F_0 = S_0 \, e^{rT} \approx S_0 (1 + r)^T$$
- $S_0$: 現在のスポット価格
- $r$: 無リスク金利（連続複利）
- $T$: 満期までの期間（年）

Hull illustrates this with the $60 stock / 5% / 1-year example (forward price = $63), noting that any deviation creates arbitrage. Detailed derivation is in Ch.5.

<!-- Hull narrative example, p.30 -->

## 4. アルゴリズム / 手順

N/A — conceptual chapter. No step-by-step procedure is presented; the forward pricing argument is a single-line no-arbitrage identity, not an algorithm.

## 5. Python reference

N/A — conceptual chapter. No central computation warrants a code snippet at this stage.

## 6. 注意点 / 典型的なミス
- **ForwardとFuturesを混同しない**: Forwardは相対契約で満期に一括決済、futuresは取引所標準で日次値洗い（marked-to-market）される。価格理論は近似的に同じだが実務上の違いは大きい（詳細はCh.2, Ch.5）。
- **OptionはForward/Futuresと異なり有償**: オプション買いにはプレミアムが必要。Forward/Futuresは（証拠金を除き）コストゼロで参入できる。ヘッジ手段の比較で混同しやすい。
- **アメリカン型とヨーロピアン型の地理的意味なし**: 名称は行使タイミングに関する慣習的区分であり、取引所の所在地とは無関係。
- **レバレッジの両刃性**: Futuresのレバレッジは利益・損失ともに拡大する（損失上限なし）。Optionのレバレッジは損失をプレミアム額に限定するが、正しく使わないと全額消失しうる。
- **ヘッジは必ずしも利益を改善しない**: ヘッジの目的はリスク削減であり、期待リターンの向上ではない。ヘッジしなかった方が結果的によかったケースも当然ある（§1.7の ImportCo / ExportCo 例参照）。
- **SocGen事例の教訓**: ヘッジやアービトラージの委任を受けた担当者が事実上の投機を行うリスクがある。明確なリスク上限の設定と日次モニタリングが不可欠。

## 7. 関連トピック
- See: Ch.2 (futures mechanics, margin, clearing), Ch.5 (forward/futures pricing theory), Ch.10–12 (options mechanics and trading strategies), Ch.3 (hedging strategies with futures), Ch.8 (2008 financial crisis and OTC regulation)
