# 2026-08-11 — B11 FINRA feasibility gate

## 結論

FINRA Treasury Daily Aggregate Statisticsは、データの意味と公開範囲はB11 Week 42の題材に
適合する。しかし、現時点ではB11 Coreの正式データ源としては**条件付き未承認**とする。

- 公式daily fileの公開URLと履歴範囲は確認できた。
- Web画面の自動取得・機械学習利用は利用規約上の制約があるため、スクレイピング経路は不採用。
- Query APIはdataset・field・履歴仕様が確認できたが、認証なしの実リクエストは401であった。
- API credentialを用いた、規約に沿うsnapshot取得と再現manifestがまだない。

したがって、Week 42の実データ分析はAPI access/permission gateが通るまで開始しない。Week 41、
Week 43、Week 44はTreasury公式curveとfixture中心で先行できる。API gateが通らない場合、Week 42は
aggregateから推測できないspread・impactを明示し、quote fixtureによる式・単位検証へ縮小する。

## Evidence

| Check | Result | Evidence |
|---|---|---|
| public daily file | pass | `ts-daily-aggregates-2026-08-10.xlsx` をHTTP 200で取得、7,513 bytes、XLSX |
| first available date | pass | FINRA pageはfirst dailyを2023-02-13と記載 |
| historical URL pattern | pass | 2023-02-13、2023-02-14、2024-03-25、2025-01-02のdirect fileをHTTP 200で取得 |
| semantic fields | pass | trade count、par value、ATS/interdealer、dealer-to-customer、total、on/off-the-run、remaining maturity、一部VWAP |
| data grain | pass | daily `Summary` workbook、2026-08-10 probeは43 rows × 8 columns |
| Query API dataset | conditional | `fixedIncomeMarket / treasuryDailyAggregates` と field schemaを確認 |
| unauthenticated API access | fail | production/mock GETともHTTP 401 `Failed to authenticate` |
| reproducible API snapshot | pending | credentials・API response・manifest/hash未取得 |

取得したXLSXは`/tmp`のprobeだけに置き、repositoryへ保存・commitしていない。API token、cookie、
個人連絡先も保存していない。

## Contract and terms boundary

FINRAのTreasury Aggregate pageは、daily dataが前日のTRACE報告を集計し、毎営業日20:00 ETに公開
されること、2023-02-13からdaily形式が始まったことを説明している。集計値はBills、FRNs、Nominal
Coupons、TIPS、ATS/interdealer、dealer-to-customer、total、remaining maturity、on/off-the-run、
trade count、par value、一部VWAPである。これはtrade-level quote、order book、individual impact、
implementation shortfallではない。

FINRA Fixed Income Data User Agreementはpersonal/non-commercial useを前提にし、Dataの重複・download、
robot/spider等の自動copy、distributionを制限している。FINRA Website TermsはWebサイト内容をML/AIや
predictive analyticsへ使うことも制限している。したがってdaily fileページを定期scrapeして教材へ
取り込む方式は採らない。

一方、FINRA Query APIのFixed Income Specific Termsは、valid Public/Firm/Organization API credentialsを
前提に、non-commercial internal useとderivative/resultant dataを認めるが、再配布にはattribution、
non-commercial、no-further-redistribution等の条件がある。B11 Coreで採用するには、このAPI経路と
credential/termsを明示したcontractが必要である。

## Next gate

1. 個人のFINRA API Console account / credentialを利用者が規約承諾のうえで準備する。tokenはchat、Git、
   repositoryへ渡さず、ローカル環境変数だけで扱う。
2. `treasuryDailyAggregates`へ最小limitのGET/POSTを実行し、401から200へ変わることを確認する。
3. 2023-02-13以降の指定日を複数取得し、schema、date coverage、duplicate、numeric range、correction
   semanticsを監査する。
4. API responseのcanonical JSON、request config、retrieval timestamp、content hash、schema hashを
   外部snapshot manifestへ記録する。raw API responseをrepositoryへcommitするかはterms確認後に決める。
5. access・semantics・sample・baseline・teaching-fitの5 gateを更新し、passならWeek 42 builderへ進む。
   failならfixture-only contractへ切り替え、FINRAの実データ主張を削除する。

## Official sources

- [FINRA Treasury Daily Aggregate Statistics](https://www.finra.org/finra-data/browse-catalog/about-treasury)
- [FINRA Treasury Daily Aggregate Statistics — Files](https://www.finra.org/finra-data/browse-catalog/about-treasury/daily-file)
- [FINRA Query API documentation](https://developer.finra.org/products/query-api)
- [FINRA Treasury Daily Aggregates API schema/example](https://developer.finra.org/docs)
- [FINRA Fixed Income API Specific Terms](https://developer.finra.org/specific-terms-fixed-income-data)
- [FINRA Fixed Income Data User Agreement](https://www.finra.org/finra-data/fixed-income/user-agreement)
- [FINRA Website Terms of Use](https://www.finra.org/terms-of-use)
