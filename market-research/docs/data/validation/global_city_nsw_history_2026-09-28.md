# NSW・Greater Sydney新規賃貸家賃の月次履歴

> 移管注記（2026-09-29）：現行の実行パスと原本配置は[移管ガイド](../../REAL_ESTATE_BENCHMARK.md)を参照。本文中の旧アプリのパスは取得当時の記録。

更新: 2026-09-28。対象: 2021年1月〜2026年8月、68か月。

## 結果

NSW政府の賃貸保証金登録データから、住宅種類F（フラット／ユニット）、1寝室または2寝室、週額家賃が正の新規契約を集計した。単位は名目AUD/週、指標は各月の登録中央値。既存入居者の賃料や同一住戸の改定率ではない。

| Greater Sydney近似 | 2021年8月 | 2026年8月 | 同月比 | 直近登録件数 |
|---|---:|---:|---:|---:|
| 1寝室 | AUD 440/週 | AUD 710/週 | +61.4% | 3,845 |
| 2寝室 | AUD 507.5/週 | AUD 845/週 | +66.5% | 5,799 |

全68か月に1寝室・2寝室・両者合算の3分類を、NSW州、Greater Sydney近似、postcode 2000の3地域で保存した（計612セル）。寝室数の構成変化を避けるため、上表の増加率は1寝室と2寝室を別々に比較した。2026年8月の州全体1〜2寝室中央値AUD 750/週（10,931件）とpostcode 2000のAUD 1,150/週（362件）は、先行の単月試験と一致。

## 都市圏境界

[ABS ASGS Edition 3の2021年Mesh Block・Postal Area配分表](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-3-july-2021-june-2026/access-and-downloads/allocation-files)を用い、NSWの住宅用Mesh Block 73,887件をPOAに対応させた。POAごとにGreater Sydney GCCSA（`1GSYD`）に属する住宅用Mesh Blockが**過半**なら都市圏近似に採用。611 POAのうち257件を採用し、境界をまたぐPOAは3件。全73,887件にPOAが付いた。

[ABSの説明](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-3-july-2021-june-2026/non-abs-structures/postal-areas)によればPOAはAustralia Postの郵便番号を近似する地域で、完全には一致しない。加えて過半判定は境界POA内の全住戸や全契約を正確に都市圏へ割り当てるものではない。そのため系列名を「Greater Sydney近似」とし、NSW州全体やpostcode 2000と明確に分けた。固定した割当は `postcode_membership.csv` に住宅用Mesh Block件数・都市圏内件数・比率を記録。

## データ品質と再現

- [NSW Fair Tradingの配布ページ](https://www.nsw.gov.au/housing-and-construction/rental-forms-surveys-and-data/rental-bond-data)から年次2021〜2025年、月次2026年1〜8月の13 XLSXを保存。原本1,856,904登録。家賃が正の行1,828,714、家賃不明28,091（1.51%）、0円99。種類コード異常64。上記の対象条件に合うNSW州登録808,127件、Greater Sydney近似703,248件。条件に合うがPOA対応がない登録は26件。
- `data/market/raw/global_city_pilot/nsw_history_20260928/manifest.json` に13原本とABS 2原本のURL、取得日時、SHA-256、サイズを保存。原本はローカルの無視対象ディレクトリにあり、Gitには含めない。
- 集計は `data/market/processed/global_city_pilot/nsw_history_20260928/monthly_rents.csv`、割当は同ディレクトリの `postcode_membership.csv`、検査件数は `quality.json`。月次CSVのSHA-256は `c22c57cb20604d0298468717fd22afb7b57ddc3498e01f875d17659c3fba5e5f`。
- worktree内の `data` は `/home/kazumasa/re_invest_os/data` へのシンボリックリンク。Windows側でCSVを開く場合は実体側の `\\wsl.localhost\Ubuntu\home\kazumasa\re_invest_os\data\market\processed\global_city_pilot\nsw_history_20260928\monthly_rents.csv` を使う。
- コードは `scripts/analysis/global_city_nsw_history.py`。保存済み原本だけで `.venv/bin/python scripts/analysis/global_city_nsw_history.py` を実行できる。新規取得時のみ `--download` を付ける。
- [HTML表示](global_city_nsw_history_2026-09-28.html)には1寝室・2寝室の月次チャート、件数、境界・指標の注意を含む。HTML構造と自己完結性を検査。ローカル `file:` URLはアプリ内ブラウザーのポリシーで開けず、目視による描画確認は未実施。

賃貸保証金データには購入価格、運営費、空室、NOI、Cap Rateは入っていない。この家賃系列だけから一棟住宅の期待利回りは算定しない。UKのPIPRや香港の賃料指数とも指標定義を揃える前に水準や騰落率を順位付けしない。
