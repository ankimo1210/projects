# ニューヨーク市の売買個票：取得試験

> 移管注記（2026-09-29）：現行の実行パスと原本配置は[移管ガイド](../../REAL_ESTATE_BENCHMARK.md)を参照。本文中の旧アプリのパスは取得当時の記録。

更新: 2026-09-29。今回は機械取得と定義の確認まで。個票の価格分析は未実施。

[NYC Department of FinanceのRolling Sales](https://www.nyc.gov/site/finance/taxes/property-rolling-sales-data.page)は過去12か月の売買を公開し、2003年以降の年次ファイルも案内している。[NYC Open Dataの現行API](https://data.cityofnewyork.us/dataset/NYC-Citywide-Rolling-Calendar-Sales/usep-8jbt)へ認証なしでGETでき、5行の標本、件数・日付の集計、用途カテゴリー集計をHTTP 200で確認した。

件数・期間・用途集計の原本応答と要求URL・取得時刻・SHA-256は `data/market/raw/global_city_pilot/nyc_access_20260929/` に保存。これは日々更新される直近12か月のスナップショットで、後日の同じAPI要求は別の期間・件数になり得る。

| 確認項目 | 取得結果 |
|---|---|
| 現行API | `https://data.cityofnewyork.us/resource/usep-8jbt.json` |
| 対象期間 | 2025-09-01〜2026-08-31 |
| 登録行 | 82,345件 |
| `07 RENTALS - WALKUP APARTMENTS` | 2,829件 |
| `08 RENTALS - ELEVATOR APARTMENTS` | 525件 |
| 読めた主な列 | 売買日・売買価格・borough・neighborhood・建物用途・住宅戸数・土地/延床面積・築年 |

[市の用語集](https://www.nyc.gov/site/finance/property/glossary-property-sales.page)によれば売買価格0ドルは対価を伴わない所有権移転を表し得るため、市場価格の統計から無条件に使えない。用途07/08にも物件・権利の扱いを確認すべき行がある。建物の住宅戸数が載っていても、各行が「賃貸一棟の丸ごと取引」とは限らない。まず売買クラス、block/lot、住所、正の対価、面積の有効性を絞り、標本で取引単位を照合する必要がある。売買原本にはNOI・運営費・入居率がなく、ここから実績Cap Rateは直接計算できない。

次は市の年次ファイル2003年以降との列・取引単位の整合を確認し、現行12か月の賃貸用建物候補を限定して価格/㎡または価格/戸を試算する。現時点では価格・利回りの都市間ランキングに使わない。
