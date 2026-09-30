# 国際不動産データ先行調査：収集・照合記録

> 移管注記（2026-09-29）：現行の実行パスと原本配置は[移管ガイド](../../REAL_ESTATE_BENCHMARK.md)を参照。本文中の旧アプリのパスは取得当時の記録。

更新: 2026-09-28。対象は保存済みの2つのrun。実装は `scripts/analysis/global_city_pilot.py`、閲覧用の固定版は [HTMLレポート](global_city_pilot_2026-09-28.html)。

## 結果と読み方

段階A（福岡・香港）と段階B（英国の価格指数）を実行した。指数・地価の長期推移を原本とともに保存した。**都市間の期待利回りはまだ計算できない。** 福岡は土地の公示価格、香港・英国は建物込み住宅の指数であり、同じ資産の利回りや割安度を示す図ではない。

| 原本 | 期間・範囲 | 原本行 | 採用入力 | 出力上の注意 |
|---|---|---:|---:|---|
| `jp_fukuoka_land` | 1983–2026年、福岡市7区の公示地価 | 12,017 | 住宅地7,941地点年 | 市・7区の年次平均352行。独立物件数ではない |
| `hk_rent_q` | 1979Q4–2026Q2、民間住宅全クラス | 187 | 184四半期 | 1979Q4、1980Q1、1980Q2は欠損。2026Q2はP（暫定） |
| `hk_price_q` | 同上 | 187 | 187四半期 | 2026Q2はP（暫定） |
| `uk_hpi_index` | 1995Q1–2026Q2、ロンドン地域・マンチェスター市 | 151,920 | 対象2地域の月次758行 | 完全四半期252点へ集計。2026Q3は7月のみで除外 |

福岡の2026年住宅地は195地点、単純平均は **258,142.6円/土地㎡**。100円単位では **258,100円/土地㎡** となり、既存の[福岡地価検証](fukuoka_land_price_history_1983_2026.md)と一致する。平均は毎年の標準地の断面であり、地点が入れ替わる。地点数は独立した建物売買件数ではない。

香港の価格・賃料は原系列が1999年=100。図では双方を2015Q1=100に再基準化した。2026Q2の価格/賃料相対指数は **91.7375**。式は $100 (P_t/P_{2015Q1})/(R_t/R_{2015Q1})$ で、2015Q1より価格の伸びが賃料より弱いことを示す。家賃年数や表面・NOI利回りを表さない。英国はUK HPIの月次非季節調整指数を3か月平均してから、2015Q1=100に揃えた。英国の直近期は取引登録後の改定対象になり得る。

## 原本照合

CSVを実装の集計関数を使わずに読み、以下を別途確認した。

| 原本 | 初期 | 中期 | 最新 |
|---|---:|---:|---:|
| 香港賃料・All Classes | 1979Q4 `-` | 2015Q1 `168.5` | 2026Q2 `204`、P |
| 香港価格・All Classes | 1979Q4 `16.5` | 2015Q1 `289.2` | 2026Q2 `321.2`、P |
| UK HPI・London `E12000007` | 1995-01 `14.0` | 2015-01 `75.5` | 2026-07 `96.4` |
| UK HPI・Manchester `E08000003` | 1995-01 `14.6` | 2015-01 `55.7` | 2026-07 `109.1` |

英国の2026Q2は原本の4・5・6月平均がロンドン **96.4333**、マンチェスター **107.4**。ロンドンは広域のregion、マンチェスターはlocal authorityで、地理的粒度が違う。1995年以前のロンドン導出バックシリーズを本比較には入れていない。

## 再実行と保存場所

- A原本: `/home/kazumasa/re_invest_os/data/market/raw/global_city_pilot/20260928T060008Z/`
- A集計・HTML: `/home/kazumasa/re_invest_os/data/market/processed/global_city_pilot/20260928T060008Z/`
- B原本: `/home/kazumasa/re_invest_os/data/market/raw/global_city_pilot/20260928T060018Z/`
- B集計・HTML: `/home/kazumasa/re_invest_os/data/market/processed/global_city_pilot/20260928T060018Z/`
- Windowsから開くB版: `\\wsl.localhost\Ubuntu\home\kazumasa\re_invest_os\data\market\processed\global_city_pilot\20260928T060018Z\report.html`

`data/` はworktreeからmain側データへのシンボリックリンク。これらはローカルの無視対象で、ライブDuckDBや日次ジョブには入れていない。B版HTMLの固定コピーをこのノートと同じディレクトリに置いた。

```bash
# worktreeのルートから。--download を付けない再生成はネットワークを使わない。
.venv/bin/python scripts/analysis/global_city_pilot.py --run-id 20260928T060018Z
PYTHONPATH=scripts/analysis .venv/bin/python -m pytest scripts/analysis/tests/test_global_city_pilot.py -q
.venv/bin/ruff check scripts/analysis/global_city_pilot.py scripts/analysis/tests/test_global_city_pilot.py
```

同じ原本・コード・テンプレートでB版を2回生成し、`summary.json`・`coverage.csv`・`report.html`のSHA-256一致を確認。保存した原本・取得日時・元列・原単位・基準・版・URL・SHA-256・利用条件は各runの`manifest.json`にある。同じrun IDでの再取得・上書きは拒否する。HTTP 200のHTML本文、欠損、重複期、英国の地理コードと不完全四半期をテストした。HTMLはCSS・データ・SVGを内包し、ChromeでPCと狭幅の表示を確認した。

## 出所・利用条件

- 福岡：既存の地価公示CSV。[国土交通省 国土数値情報](https://nlftp.mlit.go.jp/ksj/)と[既存の検証](fukuoka_land_price_history_1983_2026.md)。住宅地は `code_group=000`。
- 香港：[香港政府 DATA.GOV.HK のRVD統計](https://data.gov.hk/en-data/dataset/hk-rvd-tsinfo_rvd-property-market-statistics)からRVDの`1.3Q.csv`と`1.4Q.csv`。データ出所を香港特別行政区政府・差餉物業估價署（RVD）・DATA.GOV.HKとして明記。[利用条件](https://data.gov.hk/en/terms-and-conditions)は出所・権利者表示を要求する。
- 英国：[HM Land Registry UK HPI 2026年7月公開版](https://www.gov.uk/government/statistical-data-sets/uk-house-price-index-data-downloads-july-2026)のIndex CSV（2026年9月16日公表）。[方法・再公表条件](https://www.gov.uk/government/publications/about-the-uk-house-price-index/about-the-uk-house-price-index)に従いHTML内にOGLの所定表示を含めた。指数は登録済み売買に基づき、後から改定される。

次に小さく試すのはONS家賃とNSW Rental Bond Data。地域コード、資産タイプ、成約と募集の違い、ライセンスを確認してから長期取得する。NOIとCap Rateの国際比較はその後の別段階。
