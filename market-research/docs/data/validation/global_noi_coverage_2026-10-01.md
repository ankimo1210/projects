# 海外住宅NOI参照値の取得状況

確認日: 2026-10-01（日本時間）。値と定義は[参照JSON](../global_noi_references_2026-10-01.json)に保存。

| 対象 | 時点・公表日 | 指標・対象資産 | 一次資料で確認した値 | 国内実績NOIとの一致 |
|---|---|---|---|---|
| NY | 2025年12月上旬調査、2026-02-10公表 | CBRE、Class A・市街地集合住宅・安定稼働の想定取得Cap Rate | 4.50–5.00% | 想定安定稼働NOI／取得価格。実績NOI、個別取引平均、鑑定額分母とは異なる |
| NY 最新資料 | 2026年6月下旬調査、2026-08-12公表 | CBRE 2026年上期調査 | 都市表未照合 | 数値を空欄にし、二次記事で埋めない |
| London Zone 1 | 2026-04-30 | Knight Frank、プライム安定稼働BTRのNIY | 3.90–4.00% | NOI控除項目と価格分母の詳細は未開示 |
| London Zone 2 | 同上 | 同上 | 4.00–4.15% | 同上 |
| London Zones 3–4 | 同上 | 同上 | 4.15–4.30% | 同上 |
| Greater London | 同上 | 同上。前の3行の平均ではない | 4.25–4.50% | 同上 |
| UK全体 | 2025年9月–2026年3月、記事2026-07-14 | CBRE Multifamily指数、半年間の保有収益 | インカム2.2%、資本変化−2.2%、総収益0.0% | London単独でも年間取得Cap Rateでもない。年率Cap Rateへの換算をしない |

NYの[CBRE一次PDF](https://mediaassets.cbre.com/-/media/project/cbre/shared-site/teams/united-states/ft-lauderdale/calum-weaver/cbre-us-cap-rate-survey-h2-2025.pdf)のp9とp7を読み取った。調査は専門家推計で、家賃規制物件全体や市5区平均の実績収益を表さない。下期版のNOI式は「net income less operating expenses」と表記され、[上期版](https://www.cbre.com/insights/reports/us-cap-rate-survey-h1-2026)とは収入の記載に差がある。推計NOI金額や個別費用は復元できない。

Londonの[Knight Frank一次PDF](https://www.knightfrank.co.uk/site-assets/research/report-pdfs/uk-living-sectors-yield-guide/kf-april-2026-prime-yield-guide2.pdf)のp1は、市場賃料まで賃貸された機関投資家向け資産のNIYを示す。保存PDFのテキストとページ画像で4月列を確認した。取得諸費用、地代、修繕、CAPEX、NCFの詳細がなく、これを日本の実績NOI／鑑定額と同一計算とみなせない。確認できた版の時点を表示し、2026年10月の最新値とは主張しない。

[CBRE UK記事のFigure 1](https://www.cbre.co.uk/insights/articles/business-insights-robust-occupier-demand-drives-multifamily-housing-investment)は半年間のUK全体のリターンである。この2.2%を2倍して一棟の年間取得利回りにしない。

融資の補助資料として[Grainger HY26 p11](https://corporate.graingerplc.co.uk/sites/graingerplc-corp/files/2026-05/HY26-announcement.pdf)で、全社既存調達コスト3.2%、LTV40.2%、94%ヘッジを確認した。Londonの新規物件融資金利や為替ヘッジ費用には代用できない。

[Equity Residential Q2 2026の定義](https://investors.equityapartments.com/news-events/press-releases-news/news-details/2026/Equity-Residential-Reports-Second-Quarter-2026-Results/default.aspx)では、取得Cap Rateの分子から管理費（収入の3–4%）と住戸内更新CAPEX（100–450 USD/戸）も控除する。名称が同じでも、日本のNOI、海外のNIY、NCFの定義を一致させるには費用項目の確認が必要。

原本の保存・アクセス結果はリポジトリ内 `_data/market-research/market/raw/noi_expansion_20261001/global/manifest.json` に記録した。Knight FrankはHTTP 200で430,061 bytes、SHA-256 `8c014885c586475a5cf5fc2ff4fd525e0689f24b14e2b8d75699fe17b8463db6`。CBRE、Grainger、EQRの直接取得はHTTP 403で保存できず、拒否後の再試行や迂回を行っていない。

NY・Londonの同期間実績NOI・NCF・成約価格、費用と権利の内訳、同条件融資・CAPEX実績・為替ヘッジを取得するまで、海外との割安順位や円ベースIRRの実績比較は保留する。
