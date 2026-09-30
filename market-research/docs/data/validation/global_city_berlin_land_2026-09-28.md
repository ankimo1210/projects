# ベルリン住宅用地価の公式データ試験

> 移管注記（2026-09-29）：現行の実行パスと原本配置は[移管ガイド](../../REAL_ESTATE_BENCHMARK.md)を参照。本文中の旧アプリのパスは取得当時の記録。

更新: 2026-09-28。対象: ベルリンのBodenrichtwert、2006年・2016年・2026年の各1月1日。

後続: 2026-09-29に[2002〜2026年の25年系列](global_city_berlin_annual_2026-09-29.md)を別原本で保存・照合した。本書は初回3時点の検証記録として保持する。

## 結果

[ベルリン市のBodenrichtwert](https://www.berlin.de/gutachterausschuss/marktinformationen/bodenrichtwerte/)を公式WFSから3年分取得した。`nutzung = W - Wohngebiet` で、再開発・修復に伴う特別な価額指定（`anwert` または `verfahrensart` が非空）のないゾーンに限定した。単位は土地1㎡当たりの名目EUR。**ゾーンを各1件として計算した中央値**であり、敷地面積や住宅戸数では重み付けしていない。

| 地域 | 2006年中央値（ゾーン） | 2016年中央値（ゾーン） | 2026年中央値（ゾーン） | 2026/2006 |
|---|---:|---:|---:|---:|
| ベルリン全体 | 190 (659) | 300 (699) | 605 (784) | 3.18倍 |
| Mitte | 375 (30) | 900 (31) | 2,200 (41) | 5.87倍 |
| Friedrichshain-Kreuzberg | 380 (17) | 1,000 (16) | 2,850 (20) | 7.50倍 |
| Charlottenburg-Wilmersdorf | 520 (42) | 940 (45) | 1,800 (55) | 3.46倍 |
| Pankow | 160 (85) | 300 (90) | 590 (94) | 3.69倍 |
| Spandau | 170 (92) | 245 (100) | 500 (110) | 2.94倍 |

残る7行政区を含む全12区の集計は `data/market/processed/global_city_pilot/berlin_history_20260928/zone_medians.csv` に保存。個別ゾーンは同所の `residential_zones.csv`、件数は `quality.json` に保存した。原本の全用途ゾーンは2006年1,064件、2016年1,136件、2026年1,623件。住宅用で通常扱いの採用数は上表のとおり。2006年・2016年・2026年すべてで公式WFSの `numberMatched`・`numberReturned`・実取得件数が一致し、住宅用ゾーンID重複と基準日不一致はなかった。

## 比較の限界

[市の定義](https://daten.berlin.de/datensaetze/bodenrichtwerte-01-01-2026-wms-fd3aa40c)ではBodenrichtwertは似た土地の**標準的な土地価額**で、個別取引の成約価格ではない。ゾーン数・境界・容積率・用途区分が時点間で変化する。したがって表の3.18倍等は「各年の公開ゾーン集合の中央値の比」であり、同じ土地の価格指数や投資リターンではない。インフレ調整、円換算、建物価格、家賃との対応もまだしていない。住宅用地の特別価額を除外したのは年次比較で別の価額定義を混ぜないため。

日本の公示地価・基準地価と同じ「土地」の指標として比較候補になるが、標準地1地点とベルリンの面積を持つゾーンでは観測単位が違う。まずはベルリン内の分布と定義確認に使い、福岡・東京との倍率比較は同じ用途・立地・容積率・通貨・インフレをそろえてから行う。NOIやCap Rateは原本にない。

## 再現方法・原本

- コード: `scripts/analysis/global_city_berlin_land.py`。
- 保存済み原本から: `.venv/bin/python scripts/analysis/global_city_berlin_land.py`。未保存の公式年次を取得する場合: `--download`。対象年は当面2006・2016・2026年に固定している。
- 原本: `data/market/raw/global_city_pilot/berlin_history_20260928/berlin_{year}.json`。同所 `manifest.json` に公式WFSの実際の要求URL、SHA-256、サイズ、保存日時を記録。原本はGit無視対象。
- worktree内の `data` は `/home/kazumasa/re_invest_os/data` へのシンボリックリンク。Windows側のCSVアクセスは実体側の `\\wsl.localhost\Ubuntu\home\kazumasa\re_invest_os\data\market\processed\global_city_pilot\berlin_history_20260928\zone_medians.csv` を使う。
- 元データの公開条件: [Berlin Open Data](https://daten.berlin.de/datensaetze/bodenrichtwerte-01-01-2026-wms-fd3aa40c)は2026年のデータを `dl-de-zero-2.0` と表示。過去年分の利用条件も公開に先立って個別確認する。
- 次の拡張: 2002〜2026年の年次取得、各年の通常住宅用ゾーンの定義検査、境界・容積率をそろえた地点追跡。ゾーンID一致だけで同一敷地と見なさない。
