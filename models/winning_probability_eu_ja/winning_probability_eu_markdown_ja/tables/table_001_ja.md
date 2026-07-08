# Table 1 - 日本語版

4ディーラーの単純なRFQ例で、Tradeweb APIが各ディーラーに返す情報と、MS内部での正規化状態を整理した表です。原表はページ8の回転表です。

![Table 1 rotated](../assets/derived/page_008_table_rotated.png)

## 読み方

- Dealer 1は各シナリオで勝者として描かれています。
- 勝者はExecutionReportを受け取り、自分のwinning priceとcover priceを知ります。
- 敗者はQuoteResponseを受け取りますが、tieやcoverに関する情報は限定的です。
- この情報の非対称性が、RFQデータをcensoredにする主因です。

| Scenario | 主な価格構造 | Dealer 1 | Dealer 2 | Dealer 3 | Dealer 4 | ポイント |
|---|---|---|---|---|---|---|
| 1 | Dealer 1/2/3がwinning priceでタイ、Dealer 4が低い価格 | Done / DoneTied | DoneAway / TiedTradedAway | DoneAway / TiedTradedAway | DoneAway / TradedAway | 勝者・タイ敗者はwinning=coverと推定できるが、Dealer 4はcoverを知らない。 |
| 2 | Dealer 1/2がwinning priceでタイ、Dealer 3/4が低い同価格 | Done / DoneTied | DoneAway / TiedTradedAway | DoneAway / TradedAway | DoneAway / TradedAway | Dealer 3/4はcoverやtie情報を十分に得ない。 |
| 3 | Dealer 1単独勝ち、Dealer 2/3がcoverでタイ、Dealer 4が低い価格 | Done | DoneAway / CoverTied | DoneAway / CoverTied | DoneAway / TradedAway | 勝者はcover priceを知り、Dealer 2/3はcover tieを知る。 |
| 4 | Dealer 1単独勝ち、Dealer 2単独cover、Dealer 3/4が低い価格 | Done | DoneAway / Covered | DoneAway / TradedAway | DoneAway / TradedAway | 最も単純なケース。勝者はcoverを知り、cover dealerだけがcoverであることを知る。 |
