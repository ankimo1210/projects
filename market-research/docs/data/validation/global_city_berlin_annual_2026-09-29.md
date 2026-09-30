# ベルリン住宅用地価ゾーン：2002〜2026年

> 移管注記（2026-09-29）：現行の実行パスと原本配置は[移管ガイド](../../REAL_ESTATE_BENCHMARK.md)を参照。本文中の旧アプリのパスは取得当時の記録。

更新: 2026-09-29。対象は毎年1月1日の[Bodenrichtwert](https://www.berlin.de/gutachterausschuss/marktinformationen/bodenrichtwerte/)で、単位は土地1㎡当たり名目EUR。公式WFSの25年分を保存した。

## 結果

`nutzung = W - Wohngebiet`、かつ特別な価額指定のない通常ゾーンの**件数等重み中央値**。ゾーンの面積や住宅戸数では重み付けしていない。

| 年 | ベルリン全体の中央値（EUR/㎡） | 採用ゾーン数 |
|---:|---:|---:|
| 2002 | 240 | 641 |
| 2008 | 180 | 674 |
| 2013 | 200 | 688 |
| 2016 | 300 | 699 |
| 2019 | 650 | 710 |
| 2022 | 850 | 774 |
| 2023 | 750 | 779 |
| 2024 | 650 | 784 |
| 2025 | 630 | 783 |
| 2026 | 605 | 784 |

全25年と12行政区の325地域・年セルは `zone_medians_annual.csv` に保存。**2022→2026年は同じゾーンID・同じ容積率の764ゾーンで変化率中央値▲19.5%**。一方、各年に公表されたゾーン集合の中央値どうしの比は▲28.8%であり、こちらを同一ゾーンの変化率としては扱わない。後者では12区すべての断面中央値が下がる。ゾーン数・境界・用途・基準は変化し、特に2021→2022年の採用数は722→774へ増加した。2002年と2026年の断面中央値比2.52倍も同一地点の上昇率ではない。変化の原因をこの表だけで金利等に帰属させない。

原本は全用途ゾーン計30,693件、対象の通常住宅用は計17,565件。再開発・修復等の特別指定がある住宅用606件を除外した。25年すべてで公式応答の全件数と取得件数が一致し、住宅用ゾーンは全12区を含む。基準日が一部の年で `YYYY-MM-DDT00:00:00+01:00` と表現されるため、ベルリン現地の1月1日午前0時として検証した。3時点試験の2006・2016・2026年、39地域・年セルの集計値と一致。

## 比較上の扱い

[市の定義](https://daten.berlin.de/datensaetze/bodenrichtwerte-01-01-2026-wms-fd3aa40c)では、Bodenrichtwertは類似した土地の標準的な価額であり、個別の成約価格ではない。日本の地価と比較する際は住宅用途、立地、容積率、土地面積、通貨・物価を揃える必要がある。建物価格、運営費、NOI、Cap Rateはこの原本にない。行政区中央値をそのまま一棟住宅の取得価格や収益率にしない。

## 再現

- コード: `scripts/analysis/global_city_berlin_history.py`。`.venv/bin/python scripts/analysis/global_city_berlin_history.py` で保存済み原本だけから再生成。初回のみ `--download`。
- 原本: `data/market/raw/global_city_pilot/berlin_history_20260929/` に25年分JSON、取得URL・日時・SHA-256を記録した `manifest.json`。前日の3年試験原本は別ディレクトリに保持した。
- 集計: `data/market/processed/global_city_pilot/berlin_history_20260929/zone_medians_annual.csv`、個別ゾーンCSV、`quality.json`（同一ゾーン・同一容積率の変化率も記録）。年次CSVのSHA-256: `6e887fafefe5f7fce7918e16f7dbf313bd228a9d9316d450c63f9fe58dfd0861`。
- worktree内の `data` は `/home/kazumasa/re_invest_os/data` へのシンボリックリンク。WindowsからCSVを開く場合は `\\wsl.localhost\Ubuntu\home\kazumasa\re_invest_os\data\market\processed\global_city_pilot\berlin_history_20260929\zone_medians_annual.csv`。
