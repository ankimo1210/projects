# 世界主要都市の不動産比較：データソース調査

> 移管注記（2026-09-29）：現行の実行パスと原本配置は[移管ガイド](../REAL_ESTATE_BENCHMARK.md)を参照。本文中の旧アプリのパスは取得当時の記録。

調査日: 2026-09-28。目的は、日本の各都市を海外都市と比較するために、地価・住宅価格・賃料・利回り・需要供給の取得可能性と比較上の制約を確認すること。分析結果や将来収益率の予測ではない。

対応する[分析計画](../../../docs/superpowers/plans/2026-09-28-global-city-real-estate-benchmark.md)。既存の[福岡地価分析](validation/fukuoka_land_price_history_1983_2026.md)と[市場データ基盤](market-data.md)を出発点とする。

2026-09-28追記: [参考案の検討と取得試験ノート](global_city_real_estate_collection_notes_2026-09-28.md)を追加。ユーザー方針に従い、直近の順序は[取得しやすいデータから始めるプラン](../../../docs/superpowers/plans/2026-09-28-global-city-data-pilot.md)とする。

2026-09-29追記: [ベルリン25年の公式WFS検証](validation/global_city_berlin_annual_2026-09-29.md)、[シンガポールの公開価格・賃料指数](validation/global_city_singapore_indices_2026-09-29.md)、[NYC売買個票APIの取得試験](validation/global_city_nyc_access_2026-09-29.md)を追加。シンガポールの公開集計指数はURA個別契約APIのAccessKeyなしで取得できるが、取引水準・NOIを含まない。NYCの現行売買APIは取得可能だが、0ドル移転と区分/一棟の判別が残る。

## 調査で分かったこと

- 都市別の土地価格、建物込み住宅価格、一棟賃貸NOI利回りを一つの世界共通データセットで揃えることはできない。指標ごとにソースを選び、比較できる都市の組を作る。
- 香港・英国・フランス・米国には公開データがある。シンガポール・韓国には公式APIがあるが、利用登録と実データ接続の確認が必要。
- 日本不動産研究所（JREI）の国際比較は有用だが、公開される都市間マンション価格水準は高級住宅の比較。NOI利回りの詳細は有料版。標準的な中古賃貸一棟の直接比較に置き換えない。
- 公開閲覧、ダウンロード、社内分析、加工物公開、再配布は別の利用条件。無料という理由だけでアプリへの組込みが可能と判定しない。

## 確認状態の意味

| 状態 | この調査で確認した範囲 |
|---|---|
| 実取得 | データファイルを取得し、列と期間を読めた |
| 公開確認 | 発行元のページ・PDF・データカタログを確認。完全な取得・全期間の品質検証は未実施 |
| 仕様確認 | APIの説明と認証方法を確認。利用者のキーを使った取得は未実施 |
| 候補 | 発行元の存在・製品を確認。対象都市、契約、項目の詳細確認が必要 |

## 共通の基礎データ

| ID・発行元 | 取得できるもの・単位 | 期間・粒度・更新 | 利用方法と注意 | 状態 |
|---|---|---|---|---|
| X01 [BIS Residential Property Prices](https://data.bis.org/topics/RPP) | 名目・実質住宅価格指数、前年比。国・一部都市/地域 | 約60経済、詳細300超系列。選抜系列の一部23か国は1970年前後まで。頻度は系列別 | [SDMX API案内](https://data.bis.org/help/tools)。全国系列を都市の代用にしない。詳細系列も戸建て/共同住宅、新築/中古、推計手法が異なる | 公開確認 |
| X02 [OECD Housing Prices / House Price Tracker](https://www.oecd.org/en/data/tools/oecd-house-price-tracker.html) | 住宅価格・賃料・所得比などの国/地域指標 | 系列別。長期の市場環境を比較 | price-to-rent指数は基準年からの相対値。指数の逆数から絶対利回りは作れない。都市別収録は採用前に確認 | 公開確認 |
| X03 [BIS Bilateral Exchange Rates](https://data.bis.org/topics/XRU) | 対USD二国間為替、期中平均/期末 | 日・月・四半期・年 | JPY/現地通貨のクロスを作る。実効為替指数を換算レートに使わない。USDペッグでも対JPY変動は残る | 公開確認 |
| X04 [OECD Long-term Interest Rates](https://www.oecd.org/en/data/indicators/long-term-interest-rates.html) | 原則10年国債利回り | 国別・時系列 | NOI利回りとの差の基準。日本の金利を外国物件に適用しない。住宅ローン・非居住者向け融資金利とは別 | 公開確認 |
| X05 [OECD 都市・FUA定義](https://www.oecd.org/en/data/datasets/oecd-definition-of-cities-and-functional-urban-areas.html)、[Regions and Cities Atlas](https://www.oecd.org/en/data/tools/oecd-regions-and-cities-atlas.html) | 都市圏境界、人口、雇用、所得等 | 都市/機能的都市圏、概ね年次・項目別 | 行政市と通勤圏を別IDで保存。統計公表年と対象年を区別。住宅系列を無理にFUAへ割り振らない | 公開確認 |
| X06 [Eurostat HICP Manual](https://ec.europa.eu/eurostat/documents/3859598/18594110/KS-GQ-24-003-EN-N.pdf) | CPI・家賃指数の定義確認 | 主に国別、月次の指標設計 | 家賃には新規契約だけでなく既存契約や公的住宅も含まれ得る。CPI家賃指数を募集家賃水準と混ぜない | 公開確認 |
| X07 [OECD CPI](https://www.oecd.org/en/data/indicators/inflation-cpi.html)、[香港C&SD](https://www.censtatd.gov.hk/en/wbr.html?ecode=B10600012025MM12)、[SingStat APIカタログ](https://tablebuilder.singstat.gov.sg/view-api/find-apis)、[台湾DGBAS](https://estatdb.dgbas.gov.tw/) | 物価指数の水準・前年比、総合/内訳 | 主に月次。採用系列の開始年・基準改定を取得時に確認 | 実質化には前年比だけでなく指数水準を使う。OECDで対象外の地域は現地統計へ。香港リンクは取得形式の確認用で最新刊ではない。既に実質化済みのBIS系列を再度CPIで割らない | 公開確認、各系列の一括取得は未実施 |
| X08 [HKMA政府債API](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/gov-bond/instit-bond-price-yield-daily/)、[新プログラムのHKD政府債API](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/ibpgsbp/instit-bond-price-yield-daily-ibpgsbp-hkd/)、[MAS SGS](https://eservices.mas.gov.sg/statistics/fdanet/BenchmarkPricesAndYields.aspx) | 香港・シンガポールの10年等の政府債利回り | 日次等。HKMAはJSON APIに10年の指標/終値参照利回りの定義あり | OECD未収録時の候補。HKMAのプログラム・通貨・指標種別を区別。旧Exchange Fund Notesは2015年以降3年以上の新規発行停止のため、古い10年値を現在値として延長しない | HKMA仕様確認、MAS公開確認 |

## 日本と都市間の橋渡し

| ID・発行元 | 取得できるもの | 期間・粒度・方法 | 注意・権利・用途 | 状態 |
|---|---|---|---|---|
| J01 [国土数値情報・地価公示](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L01-2026.html) | 標準地の土地価格、用途、駅距離、容積率、価格履歴 | 年次GML。福岡県1983–2026年は既存収集済み | 日本の土地比較の中核。標準地番号の再利用、選定替え、分類変更に対応。建物価格を含まない | 既存実取得 |
| J02 [不動産情報ライブラリAPI](https://www.reinfolib.mlit.go.jp/help/apiManual/) | 取引・成約価格、土地/建物面積、築年、地理情報等 | XIT001の取引情報は2005Q3以降、成約情報は2021Q1以降。APIキー必要 | 既存レイク/取得コードを再利用。取引情報と成約情報の出所フラグ、欠損、面積上限表現を維持 | 仕様確認・国内基盤あり |
| J03 [JREI 不動産投資家調査・2026年4月](https://www.reinet.or.jp/pdf/REIS/published-document_main_the-japanese-real-estate-investor-survey_202604.pdf) | 国内の賃貸住宅一棟等の期待利回り | 半年ごと、都市・標準物件条件別の投資家アンケート | 実取引利回りやIRRではない。原文の収益定義・物件条件とセットで記録。転載・データ利用条件確認が必要 | 公開確認 |
| J04 [JREI 国際不動産価格賃料指数・2026年4月](https://www.reinet.or.jp/pdf/kokusai/published-document_jrei-global-property-value-rent-indices-ja_202604.pdf) | 東京・大阪を含む16都市のオフィス/マンション価格・賃料指数 | 半年ごと。鑑定士による調査対象物件の評価。都市間住宅水準は元麻布の高級マンション基準 | 有料詳細版にNOI利回りと国債比較がある。公開版は市場全体の代表価格ではない。図表再利用・DB化の許諾範囲と価格は購入前確認。今回未購入 | 公開確認 |
| J05 [JREI 公表資料](https://www.reinet.or.jp/visitors-report.html) | 国内賃料指数、中古マンション価格指数、市街地価格指数 | 不動研住宅価格指数は首都圏中古マンション・1993年6月からの系列案内あり | 「住宅マーケットインデックス」は終了の告知あり、最新供給源として採用しない。不動研住宅価格指数と別製品 | 公開確認 |
| J06 既存SUUMO・楽待・健美家収集、J-REIT各投資法人IR | 募集賃料、売出価格、物件別実績収支/鑑定NOI | 地域・掲載時点・投資法人決算ごと | 募集/実績を分離。REITの分配金利回りを現物利回りにしない。過去の取得価格で割ったNOIは現在価値ベースの利回りと別。各原本へ遡る | 国内既存基盤・個別確認 |

J04の16都市は東京、大阪、ソウル、北京、上海、香港、台北、シンガポール、クアラルンプール、バンコク、ジャカルタ、ホーチミン、ムンバイ、シドニー、ニューヨーク、ロンドン。福岡を元麻布基準の指数へ直接接続しない。元麻布→東京全体→福岡という比率の連鎖も、物件条件が違えば成立しない。

## 海外の価格・賃料・土地

| ID・都市 | 主な一次データ | 履歴・頻度・取得 | 比較上の制約と初版での使い方 | 状態 |
|---|---|---|---|---|
| O01 香港 | [RVD Property Market Statistics](https://data.gov.hk/en-data/dataset/hk-rvd-tsinfo_rvd-property-market-statistics) | CSV/XLS/API。住宅価格・賃料指数は1979年から、平均価格/賃料は1982年から、利回り系列も提供。開始年は系列で異なる | 面積クラス、地域、専有面積基準が使える。公表yieldの費用控除定義を確認するまでNOIと呼ばない。価格と賃料は同一住戸標本ではない | 価格・賃料の四半期CSV読取試験済み、永続保存は未実施 |
| O02 ロンドン・マンチェスター | [HM Land Registry PPD](https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads)、[UK HPI](https://www.gov.uk/government/statistical-data-sets/uk-house-price-index-data-downloads-may-2026)、[ONS PIPR](https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/priceindexofprivaterentsukmonthlypricestatistics) | PPDは1995年からCSV・月次。HPIのEngland/Walesも1995年から。PIPRは2015年からの月次統計 | PPDに床面積がないため単純に㎡単価を作れない。必要ならEPC等の面積データとの住所照合を別工程で評価。PIPRとHPIは標本・構成が違い、単純比は参考値 | 公開確認 |
| O03 パリ | [DGFiP DVF](https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres)、[OLL賃料](https://www.data.gouv.fr/datasets/resultats-des-observatoires-locaux-des-loyers-par-agglomeration) | DVFは現行5年分・半期更新、原本パイプ区切り。OLLは都市圏・築年・部屋数・入居期間別の公表集計 | 取引単位と複数物件行を区別。駐車場、複数住戸一括売買を処理。DVF面積と専有面積の定義差あり。OLLは掲載市場全体ではない。DVFは再識別/検索エンジン索引制約を維持 | 公開確認 |
| O04 ニューヨーク・ダラス | [Zillow Research](https://www.zillow.com/research/data/)、[FHFA HPI](https://www.fhfa.gov/data/hpi/datasets) | ZHVI/ZORIはCSV、月次。FHFAは都市圏・郡等の長期指数。開始日は系列別 | ZHVIは推計住宅価値、ZORIは賃貸在庫を考慮した募集賃料指標。condo/co-opと5戸以上の賃貸MFRは違う。FHFAは主にsingle-familyの指標で一棟賃貸価格の代用不可 | 公開確認。Zillow入口は当環境のrequestsで403、CSV直取得は未試験 |
| O05 ニューヨーク | [NYC DOF Rolling Sales](https://www.nyc.gov/site/finance/taxes/property-rolling-sales-data.page)、[RGB Research](https://rentguidelinesboard.cityofnewyork.us/research/) | 売買データには用途、面積等。RGBは収入・運営費の年次調査 | ゼロ/名目的売買、建物全体と区分、総床面積と専有面積を区別。RGBの家賃規制対象の収支を自由賃料物件へ転用しない | 公開確認 |
| O06 米国の土地 | [FHFA住宅地価研究データ](https://www.fhfa.gov/blog/statistics/land-price-appreciation-during-the-covid-19-pandemic) | 確認できた更新は2012–2022年、郡・ZIP・census tract、Excel | 戸建て鑑定から推計した土地価格。土地の実売価格ではない。時点の古さを明示し、都心高容積マンション用地には使わない | 公開確認 |
| O07 シンガポール | [URA API仕様](https://eservice.ura.gov.sg/maps/api/)、[物件統計](https://www.ura.gov.sg/property-data/private-residential-properties/)、[GLS](https://www.ura.gov.sg/land-sales/current-ura-gls-sites/) | APIはAccessKeyと日次Token。売買/賃貸契約は直近5年。プロジェクト名、面積、tenure等。指数・供給統計、土地入札は別系列 | Private non-landedを採用しHDB/landedを分離。賃貸面積は範囲値があり、中央値への変換には上下限感応度を付す。GLSは土地面積/GFAと借地期間を区別 | 仕様確認 |
| O08 ソウル | [MOLITマンション実売API](https://www.data.go.kr/data/15126469/openapi.do)、[REB R-ONE](https://www.reb.or.kr/r-one/portal/openapi/openApiDevPage.do) | 行政コード×契約年月のAPI、住宅価格・地価変動統計。登録キー/採用系列の履歴を取得時確認 | 売買と月額賃貸、チョンセの返還保証金を分離。保証金を年間賃料に算入しない。REBは標本再設計による価格水準の断絶を記録 | 仕様確認 |
| O09 台北 | [内政部実価登録](https://plvr.land.moi.gov.tw/Index)、[公式カタログ](https://data.gov.tw/dataset/77051) | 売買・賃貸・予約販売のバッチ、原則毎月1/11/21日更新 | 登記面積に共用部/駐車場が含まれることを確認。棟/階/住戸を識別。賃貸登録の対象範囲を精査し全賃貸市場と呼ばない | 公開確認 |
| O10 シドニー | [NSW土地・売買サービス](https://www.nsw.gov.au/housing-and-construction/land-values-nsw/services-and-tools)、[売買データ案内](https://www.nsw.gov.au/housing-and-construction/land-values-nsw/how-to-find-property-sales-information)、[賃料・売買統計](https://bocsar.nsw.gov.au/content/dcj/dcj-website/dcj/about-us/families-and-communities-statistics/housing-rent-and-sales/rent-and-sales-report.html)、[Rental Bond Data](https://www.nsw.gov.au/housing-and-construction/rental-forms-surveys-and-data/rental-bond-data) | 評価地価、売買、LGA別賃料。保証金登録は郵便番号・週額家賃・寝室数・住宅種類の月次XLSX。土地バルクは2017年以降の申請案内あり | 保証金登録は契約開始時の申告で全入居者の現在家賃とは異なる。商用PSIは許諾確認対象。[バルクPSI](https://www.valuergeneral.nsw.gov.au/design/bulk_psi_content/bulk_psi)の検索結果にCC BY-NC-ND表記あり、現行条件は未検証。土地評価と実売は別。週額賃料×52。ABS旧8都市価格指数は2021Q4終了 | 公開確認、XLSX読取と利用条件の確認は取得時に実施 |
| O11 ベルリン | [地価・BORIS](https://www.berlin.de/gutachterausschuss/marktinformationen/bodenrichtwerte/)、[成約個票のアクセス条件](https://www.berlin.de/gutachterausschuss/service/informationen-zur-aks-online/artikel.180099.php)、[Mietspiegel 2026](https://mietspiegel.berlin.de/wp-content/uploads/2026/05/mietspiegel2026.pdf) | 土地基準値、年次市場報告、住宅条件別比較賃料。BORISは2002〜2026年の無料閲覧を確認 | 基準地価は用途・容積条件を伴う区域評価。Mietspiegelは新規募集家賃と異なる。地価の一括取得は未確認。AKSの個別成約情報には資格・申請等の制約があり、一般向け集計と区別 | 公開確認 |
| O12 トロント（拡張: バンクーバー） | [CMHC Rental Market Data](https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/rental-market)、[CREA HPI](https://www.crea.ca/housing-market-stats/mls-home-price-index/hpi-tool)、[利用条件](https://www.crea.ca/legal/) | CMHCは年次賃料/空室/供給、Excel。CREAは指数・benchmark価格、Excel | purpose-built賃貸と分譲賃貸を分離。売買benchmarkと家賃母集団を一致させる。CREAの再利用条件を記録 | 公開確認 |
| O13 拡張: ドバイ | [DLD不動産データ](https://dubailand.gov.ae/ar/open-data/real-estate-data/) | 売買・賃貸・土地の公式データ入口 | off-plan/完成物件、所有形態、契約更新を分離。API/バルク、登録、期間、ライセンスは未検証。初期完了条件に含めない | 候補 |

## 一棟賃貸利回り・運営収益を補う情報

| ID | ソース | 用途 | 限界・費用 |
|---|---|---|---|
| Y01 | [CBRE U.S. Cap Rate Survey H1 2026](https://www.cbre.com/insights/reports/us-cap-rate-survey-h1-2026) | 米国市場×用途×グレード×stabilized/value-addのcap rate目線 | 50超市場の専門家推計。取引個票の実績NOIではない。都市別表の入手範囲、定義、再利用条件を確認して採用 |
| Y02 | [Savills World Cities Prime Residential Index H1 2025](https://pdf.savills.com/documents/World-Research-World-Cities-H1-2025-full.pdf) | 高級住宅の価格・賃料・保有売買費用の比較設計の参考 | 今回読めた版は2025H1。2026年の現況値として使わない。prime市場を一般賃貸と混ぜない。最新刊とデータ利用権を別確認 |
| Y03 | [MSCI Property Indexes方法論](https://www.msci.com/indexes/private-asset-indexes/real-estate-methodology-documents)、[Performance & Risk API](https://developer.msci.com/apis/real-estate-performance-risk-data-api-v3-0) | 直接不動産のincome return、capital growth、total return、NOI/空室等 | 実データ/API利用は契約・都市/セクター範囲確認が必要。費用未確認。鑑定評価の平滑化とファンド選択偏りに注意 |
| Y04 | J04の有料詳細版、各国の住宅REIT/住宅会社IR | 都市別NOI利回りの橋渡し、費用項目の定義確認 | 有料版未購入。REITは保有物件偏りと取得時点差を記録。free公開資料でも自動再配布可とは限らない |
| Y05 | [MSCI Real Capital Analytics](https://www.msci.com/data-and-analytics/real-estate/real-capital-analytics)、[データカタログ](https://dataexplorer.msci.com/ui/products) | 一棟取引、価格、物件、投資家・貸し手・資金動向 | Y03の運用収益データとは別に調査。カタログにはアジア500万ドル以上等の地域別収録条件。契約時の現行条件、福岡の価格帯に近い取引件数、NOI/Cap Rate入力率、権利・料金を確認。未契約 |

一棟NOI利回りがない都市では、住宅の表面利回りから一律の経費率を引いて「市場NOI」とはしない。経費率を置く場合は、出所・幅を持つモデルシナリオとして表示する。

## 税・規制の参照先

これらは資産価格の比較から、日本居住投資家の実行可能性を評価する段階で必要になる。現在の規則を将来まで固定せず、effective_from / effective_to / checked_atを保存する。

- [シンガポールIRAS ABSD](https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/additional-buyer%27s-stamp-duty-%28absd%29): 追加取得税は居住資格・国籍・保有数・取得主体で異なる。通常の購入者と外国人の費用を混ぜない。
- [豪州外国投資規則](https://foreigninvestment.gov.au/guidance/conditions-and-reporting/residential-compliance): 2025-04-01〜2027-03-31の既存住宅取得制限と例外を確認。都市比較への掲載と、実際に取得できることは別。
- [カナダCMHC FAQ](https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-research/consultations/prohibition-purchase-residential-property-non-canadians-act/faq)、[政府の延長説明](https://www.canada.ca/en/department-finance/corporate/transparency/2024/nffn-part-3.html): 非カナダ人による住宅購入制限・期限・例外を確認。
- [ベルリン賃料規制案内](https://www.berlin.de/sen/wohnen/wissen-fuer-mieter/berliner-mietratgeber/miete/): 既存契約・新規契約・新築等の適用差を収支に反映する。

## 今回の実取得・照合結果

| 対象 | 結果 | この結果で証明できないこと |
|---|---|---|
| 香港RVD [1.3Q.csv](https://www.rvd.gov.hk/datagovhk/1.3Q.csv) | HTTP 200、text/csv、11,837 bytes。見出し2行＋観測187行。1979Q4〜2026Q2。A〜Eクラス、全クラス等の列。2026Q2はP（暫定）付き | 他の価格・yield系列との完全整合、全都市データ取得 |
| 香港RVD [1.4Q.csv](https://www.rvd.gov.hk/datagovhk/1.4Q.csv) | HTTP 200、11,684 bytes。価格指数の見出し2行＋観測187行。1979Q4〜2026Q2。クラス列と期間を読取確認 | 原本の永続保存、一棟NOIの取得、価格/家賃の同一住戸対応 |
| 英国HPI Index CSV | 2026年5月版の公式リンクからHTTP 200、text/csv。`Date,Region_Name,Area_Code,Index` の先頭列を確認 | 全行数、地域・履歴の網羅、最新版取得 |
| URA API | 公開仕様でAccessKey、日次Token、5年売買/賃貸、面積範囲を確認。未認証HTTPのHTML応答だけでは実API接続成功と判定しない | ユーザーの利用権、API実データ取得、全期間取得 |
| FHFA | カタログHTTP 200、取得形式・データ製品の説明を確認 | HPI各系列や土地Excelの全行検証 |
| JREI | 国際指数10ページ、国内投資家調査23ページの公開PDFを読んだ。国際版の有料NOI情報と転載制約を確認 | 有料データへのアクセス、公開図表の再配布許諾 |

## 着手時の取得順と費用方針

1. 初回: 既存福岡地価＋香港の価格/賃料CSV2本。原本保存と小さなHTMLまで完了する。
2. 次回: 英国HPIのCSV。ONS家賃、NSWのXLSXは1ファイルの読取・定義確認後に追加する。
3. 拡張: ベルリンの機械取得、URA等の登録API、米国CSVの正規導線、BIS等のマクロ系列を確認できたものから追加。キーが必要なソースは未取得として残す。
4. 有料オプション: JREI国際指数詳細版の都市別NOI・標準条件・履歴・二次利用権を確認。MSCIの運用収益とRCA取引データは別製品として評価し、公開データだけでは満たせない具体的な欠損が分かってから検討する。

初期は新規有料契約なしで成立する範囲を分析する。料金が公開資料から確定しない製品は「要見積り」とし、金額や利用権を仮定しない。自動更新は月次の取得確認、四半期の比較更新を候補とするが、この調査でジョブは作成していない。
