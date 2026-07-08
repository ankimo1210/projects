# 用語集 - 日本語版

| Term | 日本語メモ |
|---|---|
| RFQ | Request for Quotation。顧客が複数ディーラーに見積もりを依頼する取引プロセス。 |
| EUGV | European Government bonds。欧州政府債。 |
| UKGV | UK Government bonds。英国政府債。 |
| UK inflation | 英国インフレ連動債の文脈。 |
| AQ | Autoquoting。自動クォート。 |
| Hit-rate curve | 提示marginと取引に勝つ確率の関係を表す曲線。Probability curveとほぼ同義。 |
| Probability curve | 勝率曲線。RFQの候補価格・marginに対する勝率を返す。 |
| Margin | midとquote priceの差をsideで補正した量。ディーラーがどれだけスプレッドを取ろうとしているかを表す。 |
| Market spread captured | 市場スプレッドのうち、quoteにどれだけ反映して獲得しようとしたかを示す量。 |
| Dealer count | RFQに参加するディーラー数。 |
| Cover price | 負けたディーラーの中で最良の価格。勝者から見ると次点価格。 |
| Done | MS正規化上、RFQに勝って取引成立した状態。 |
| DoneAway | 負けた状態。 |
| TiedTradedAway | 最良価格にタイしたが、顧客が他ディーラーを選んだ状態。 |
| CoverTied | cover priceでタイした状態。 |
| Censored information | RFQ結果の情報が参加者ごとに部分的にしか開示されない状態。 |
| Logistic regression | ロジスティック回帰。0/1ターゲットの確率を推定する標準的モデル。 |
| Segmentation | 国、顧客tier、notional bucketなどでデータを分割し、別々の曲線を推定する設計。 |
| One-hot categorical value | カテゴリ変数を0/1ベクトルとして表す形式。 |
| GLM | Global Limit Manager。リスク制限をQuote Managerに供給する。 |
| MCS | Model Control System。モデル管理システム。 |
| BMET | Business Metrics database。自動クォートサイクルの記録先。 |
| Algo Pricer | Winning-Probability Modelを内包し、model-based candidate priceを生成するコンポーネント。 |
| Quote Manager | 最終的にmarketへ返すquote priceを生成するコンポーネント。 |
| Inquiry Manager | RFQ orderの状態を管理し、Algo PricerとQuote Managerへ問い合わせを転送する。 |
| Mid Service | 市場情報からmid quoteを提供するサービス。 |
| Risk HQ | ポジション情報を使ってリスクコストを提供するコンポーネント。 |
| Reliability plot | 予測確率バケットごとに予測hit rateと実現hit rateを比較する診断図。 |
| Backtesting | 過去データを使い、モデル予測と実際の結果を比較する評価。 |
| Stress testing | ボラティリティ上昇や低流動性などのシナリオ下でモデル挙動を確認する検証。 |
