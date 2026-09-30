# 国際不動産比較：参考案の検討と収集の優先順位

> 移管注記（2026-09-29）：現行の実行パスと原本配置は[移管ガイド](../REAL_ESTATE_BENCHMARK.md)を参照。本文中の旧アプリのパスは取得当時の記録。

更新: 2026-09-28。ユーザー方針: **まず簡単に集まるデータから進める**。

[先行収集プラン](../../../docs/superpowers/plans/2026-09-28-global-city-data-pilot.md)を直近の実行順とする。[全体計画](../../../docs/superpowers/plans/2026-09-28-global-city-real-estate-benchmark.md)は将来の分析範囲、[ソース調査票](global_city_real_estate_sources_2026-09-28.md)はデータ定義・出典の台帳。

## 参考案から取り入れる点

| 項目 | 確認結果 | 判断 |
|---|---|---|
| NSW Rental Bond Data | [公式ページ](https://www.nsw.gov.au/housing-and-construction/rental-forms-surveys-and-data/rental-bond-data)に契約開始時の週額家賃、寝室数、住宅種類、郵便番号を含む月次XLSX。2026年8月までのリンクを確認 | 募集家賃を補う候補。全入居者の現行家賃とは異なる。床面積と売買標本の整合確認後に利回りへ使う |
| ベルリンの地価履歴 | [BORIS公式案内](https://www.berlin.de/gutachterausschuss/marktinformationen/bodenrichtwerte/)に2002〜2026年の無料閲覧。古い年はラスター地図の案内 | 土地比較の優先候補。ただし閲覧・PDF出力と、時系列の一括取得は分ける |
| ベルリンの成約情報 | [AKS Online](https://www.berlin.de/gutachterausschuss/service/informationen-zur-aks-online/artikel.180099.php)は一般向け集計と個別取引でアクセス条件が異なる | 全成約個票を自由に一括取得できる市場として扱わない |
| MSCI RCA | [公式製品説明](https://www.msci.com/data-and-analytics/real-estate/real-capital-analytics)で物件・取引・投資家・資金を接続。[カタログ](https://dataexplorer.msci.com/ui/products)には地域別の取引金額条件がある | 運用収益データとは別製品として調べる。福岡の小中規模一棟を十分含むか、NOI/Cap Rateの入力率も契約前に確認。今回購入しない |
| 土地価格/建築可能延床面積 | 香港等の[政府土地売却](https://www.landsd.gov.hk/en/land-disposal-transaction/land-sale.html)やシンガポールGLSが候補 | 全体計画にある指標を維持。借地期間、開発義務、実際に利用可能な容積を併記する |

民間取引データ、投資家調査、公的住宅統計の三つを組み合わせる方向は採用する。ただし、最初の成果物を有料データや一棟NOIの取得待ちにしない。

## 比較方法で残す注意

- 都市の「◎/○」を総合評価には使わない。取得形式、認証、権利、履歴、欠損、比較可能な有効件数に分ける。
- 土地、建物込み住宅、賃貸一棟を分ける。指数の比率は基準年に対する価格/家賃関係の変化であり、絶対利回りではない。
- 需給は世帯数・住宅戸数・空室・賃貸比率を合わせて読む。人口人数と住宅戸数を直接差し引かない。
- 円換算と為替ヘッジ後収益は別。ヘッジには期間・比率・先物レート・更新費用が必要で、一定為替の試算では代用しない。[BISの説明](https://www.bis.org/publications/cip-fx-swaps-cross-currency-swaps-and-factors-move-basis)
- カバレッジ表は「行数」「系列数」「観測値数」「独立物件数」を分離する。集計指数187期を187件の物件と呼ばない。

## この環境での取得容易性の試験

以下は2026-09-28の着手前に行ったWSL上の接続試験の記録。原本保存と収集スクリプトは後に[段階A/B](validation/global_city_pilot_20260928T060018Z.md)と[段階C](validation/global_city_pilot_20260928T085744Z.md)で実装・照合した。定期ジョブは登録していない。

| 対象 | 実際に確認したこと | 次の扱い |
|---|---|---|
| 福岡の既存CSV | `data/market/processed/fukuoka_land_price_history_1983_2026.csv` が存在。年・区・標準地コード・円/㎡・住所・出典ZIPの列を確認 | 読取専用で再利用。地価であり住宅価格/NOIではない |
| 香港RVD賃料 | [1.3Q.csv](https://www.rvd.gov.hk/datagovhk/1.3Q.csv): HTTP 200、11,837 bytes、見出し2行＋観測187行。1979Q4〜2026Q2 | 初回の必須入力 |
| 香港RVD価格 | [1.4Q.csv](https://www.rvd.gov.hk/datagovhk/1.4Q.csv): HTTP 200、11,684 bytes、見出し2行＋観測187行。同じ期間・クラス列 | 初回の必須入力。賃料と同じクラスで指数比較 |
| 英国HPI | [2026年5月版案内](https://www.gov.uk/government/statistical-data-sets/uk-house-price-index-data-downloads-may-2026)のIndexリンクでHTTP 200、CSV見出し `Date,Region_Name,Area_Code,Index` を確認 | 第2段階。今回読んだのは先頭のみで、全行数・地域・履歴は未検証。この版を最新版とは呼ばない |
| Zillow | 公開入口 `https://www.zillow.com/research/data/` をrequestsで読むとHTTP 403 | この環境での入口取得の制約。公開CSV自体の取得不能を証明したものではない。初回の必須条件から外し、正規のCSV取得導線を別途確認 |
| NSW XLSX | 2026-08ファイルを取得し、標準ライブラリのストリーム読取で27,604行を確認 | 本番依存は追加せず、州全体とpostcode 2000を別集計。Greater Sydney境界と月次履歴は次段階 |

## 決めた順序

1. **福岡の既存データ＋香港の価格・賃料CSV**を原本付きで整理し、小さなHTMLとカバレッジ表を作る。
2. **英国HPIの公開CSV**でロンドン・マンチェスターを追加。ONS家賃も段階Cで追加済み。
3. **NSWの契約賃料**を1か月だけ試験取得済み。都市圏境界を定義してから履歴を追加。ベルリンは地価の機械取得可否を小さく調べる。
4. 登録API、米国の取得経路、有料NOI、一棟取引、為替ヘッジは、それぞれ条件が整った段階で拡張する。

初回の成功条件を6都市/20都市の完成から切り離す。長期の到達目標は維持し、最初は「確実に保存・再計算できる2市場の資料」を作る。取得の容易さは投資魅力の評価ではない。
