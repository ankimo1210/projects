# 国際不動産比較：取得しやすいデータから始める Implementation Plan

> 移管注記（2026-09-30）：この計画は `market-research/` への移管前に、物件DDリポジトリ（`re_invest_os`）内で書かれた。`data/market/...`、独立リポジトリ、独自の仮想環境といった記述は旧配置のもの。現在の配置と実行方法は[移管ガイド](../../../market-research/docs/REAL_ESTATE_BENCHMARK.md)を参照。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> 実行方法は最新のユーザー指示を優先する。エージェント委任は別途許可がある場合だけ行う。

**Goal:** 既存の福岡地価と公開CSVで取得できる香港の住宅価格・賃料から、原本・カバレッジ表・小さなHTMLを作り、英国などへ順番に広げる。

**Architecture:** 初回は研究用スクリプト1本で取得・集計・HTML生成を行う。原本と集計結果をrun別に保存し、処理を関数で分ける。都市・指標が増えてから全体計画のモジュール構成へ移行する。

**Tech Stack:** 当該リポジトリのPython、既存requests、標準ライブラリcsv/json/hashlib、pytest、既存HTMLテンプレート。

**Spec:** [参考案の検討ノート](../../../market-research/docs/data/global_city_real_estate_collection_notes_2026-09-28.md)、[ソース調査票](../../../market-research/docs/data/global_city_real_estate_sources_2026-09-28.md)、[全体計画](2026-09-28-global-city-real-estate-benchmark.md)。本書が直近の着手順と初回完了条件を定める。

更新: 2026-09-29。状態: **段階A/B、Cの英国・NSW月次履歴、Dのベルリン25年とシンガポール公開指数を実装・原本保存済み**。[A/B検証記録](../../../market-research/docs/data/validation/global_city_pilot_20260928T060018Z.md)、[C試験記録](../../../market-research/docs/data/validation/global_city_pilot_20260928T085744Z.md)、[NSW月次検証](../../../market-research/docs/data/validation/global_city_nsw_history_2026-09-28.md)、[ベルリン25年](../../../market-research/docs/data/validation/global_city_berlin_annual_2026-09-29.md)、[シンガポール指数](../../../market-research/docs/data/validation/global_city_singapore_indices_2026-09-29.md)を参照。NYCはAPI取得試験まで、NOI比較は未着手。

## Global Constraints

- 無認証で読めるCSVと既存の保存データを優先する。認証・取得制限に当たったソースは保留し、別の取得可能なソースを進める。
- 本番依存、API、収支エンジン、ライブDuckDB、日次ジョブは変更しない。有料データ契約や外部公開は含めない。
- 福岡は土地の評価、香港は建物込みの住宅指数として別パネルにする。両者の成長率を同じ資産の優劣ランキングにしない。
- 香港の価格指数/賃料指数は相対指標。表面利回りやNOIと表示しない。
- 出所・定義・対象期・取得日時・暫定値・件数を保存し、欠損を0や無断補間で埋めない。自動取得・ローカル利用・再配布の条件を分けて確認する。

## Review Focus

1. CSVのURLがHTMLを返すケースをTask 1で拒否する。
2. 香港CSVの2段見出し、四半期表記、各クラスのRemarks列をTask 2で検証する。
3. 非数値・欠損・改定・重複期をTask 2で識別し、観測行数と有効数を区別する。
4. 福岡の標準地と香港の住宅指数をTask 3で別表示し、利回りへの誤変換を防ぐ。
5. 英国の地理コード・改定版・不完全な直近四半期をTask 4で検証する。

## 1. 初回で見られるもの

- 香港: 価格と賃料の長期推移、2015Q1=100の比較、価格/家賃関係の変化、同じ四半期を使う1年・5年・10年変化率。
- 福岡: 既存の1983〜2026年の住宅地データ、7区の年次推移、地点数。各年の構成が変わる平均と既存の継続地点分析を区別する。
- カバレッジ: 何を、何年分、何行読めたか、何が未取得か。原本・取得日時・定義へ遡れる。

**初回の完了は福岡＋香港の2市場。** 東京・大阪や海外6都市の完成、有料NOI、条件を揃えた売買/賃貸個票、DCFは初回の条件に含めない。既存福岡物件の採点は変えない。

## 2. 収集順

| 段階 | 対象・入力 | 成果物 | 次へ進む条件 |
|---|---|---|---|
| A 初回 | 福岡保存済みCSV＋香港RVDのCSV2本 | 原本、カバレッジCSV、長期チャートの小さなHTML | 同じ原本で再生成でき、原典と数字が合う |
| B 次回 | UK HPIのIndex CSV。ロンドンとマンチェスター | 住宅価格指数の比較を追加 | 地域コード・範囲・期間を確認。家賃取得を待たず価格を掲載可能 |
| C 追加 | ONS家賃、NSW Rental Bond Data | 英国家賃、シドニーの新規契約家賃 | 1ファイルで列・定義・件数・利用方法を確認してから履歴取得 |
| D 条件整備後 | ベルリン地価、URA、米国CSV等 | 土地・売買・家賃の対象を拡張 | 機械取得、必要キー、利用条件の確認 |
| E 分析拡張 | JREI/CBRE、必要に応じ有料RCA等 | 一棟利回り・買値・CFシナリオ | 比較可能な資産と収益定義、価格帯の被覆を確認 |

初回Aは実装・照合・表示確認を含め1〜2人日を目安とする。取得形式変更や利用条件確認の待ち時間は別。まずAの成果物を見てからB以降へ進み、20都市分の取得基盤を先に作り込まない。

## 3. 初回の入力を固定する

| ID | 入力 | 確認済み範囲 |
|---|---|---|
| `jp_fukuoka_land` | `data/market/processed/fukuoka_land_price_history_1983_2026.csv` | 存在と列を確認。集計定義は[既存検証ノート](../../../market-research/docs/data/validation/fukuoka_land_price_history_1983_2026.md) |
| `hk_rent_q` | `https://www.rvd.gov.hk/datagovhk/1.3Q.csv` | 1979Q4〜2026Q2、187観測行＋見出し2行を読取確認 |
| `hk_price_q` | `https://www.rvd.gov.hk/datagovhk/1.4Q.csv` | 同じ期間と行数、各面積クラス・All Classes列を読取確認 |

香港は初回表示にAll Classesを使い、クラス別列と注記も原本に残す。全体指数の比較であって同一住戸価格と家賃の比率ではない。現行の指数方法・基準年・クラス定義を[公式カタログ](https://data.gov.hk/en-data/dataset/hk-rvd-tsinfo_rvd-property-market-statistics)とデータ辞書で確認して記録する。

福岡は住宅地 `code_group=000` を文字列で扱う。市の年平均は7区の全地点の単純平均、区平均の等重み平均にはしない。既存の継続地点159件の結果を再掲する場合は既存ノートへのリンクとし、全地点CSVから同じ母集団を復元できたと推測しない。

香港の価格/家賃関係は、同じ基準期bに対し次で表示する。

\[
R_t=100\times\frac{P_t/P_b}{Rent_t/Rent_b}
\]

100超なら基準期より価格が賃料に対して上昇したという意味。家賃の何年分で買えるか、利回り何%かはこの式から求めない。基準期・比較先が欠損なら当該指標を非表示にする。

## 4. ファイルと出力

作成予定:

```text
scripts/analysis/global_city_pilot.py
scripts/analysis/tests/test_global_city_pilot.py
data/market/raw/global_city_pilot/<run_id>/
  hk_rent_q.csv
  hk_price_q.csv
  jp_fukuoka_land.csv
  manifest.json
data/market/processed/global_city_pilot/<run_id>/
  observations.csv
  coverage.csv
  summary.json
  report.html
docs/data/validation/global_city_pilot_<run_id>.md
```

福岡の元CSVは読取専用で原本用コピーを保存する。`run_id` は取得日時を含む一意の名称とし、既存runを上書きしない。`manifest.json` に原URL/ローカル出所、取得日時、SHA-256、元列・単位・基準年、対象期、利用条件、コード版を保存する。

`observations.csv` は `source_id,geo_id,asset_type,metric,period,frequency,value,unit,remark`。`coverage.csv` は `source_id,status,period_start,period_end,raw_rows,valid_observations,series_count,unique_properties,missing_observations,reason`。集計統計の独立物件数は不明/非該当とし、行数で代用しない。

スクリプトのCLIは以下を予定する。`--download` なしでは保存原本だけから再生成し、ネットワークに接続しない。

```bash
.venv/bin/python scripts/analysis/global_city_pilot.py --run-id 20260928T120000Z --download
.venv/bin/python scripts/analysis/global_city_pilot.py --run-id 20260928T120000Z
PYTHONPATH=scripts/analysis .venv/bin/python -m pytest scripts/analysis/tests/test_global_city_pilot.py -q
.venv/bin/ruff check scripts/analysis/global_city_pilot.py scripts/analysis/tests/test_global_city_pilot.py
```

実行済みrun IDは段階Aが `20260928T060008Z`、段階Bが `20260928T060018Z`。コード・出力・実行結果は検証記録に残した。段階Bの新規取得には `--uk` を併用する。

## 5. 実行タスク

### Task 1 — 原本とカバレッジを保存する

**Files:** `global_city_pilot.py` と対象テスト、run別rawディレクトリ。

- [x] 公式ページの利用条件を記録し、香港2本を取得、福岡CSVをコピーする。
- [x] HTTP失敗、空応答、HTML応答を失敗として記録する。回避策を連続試行せず、失敗したソースは保留する。
- [x] ハッシュ・取得時刻・サイズを含むmanifestを保存する。同名runがあれば取得による上書きを拒否する。
- [x] HTTP 200でも本文がHTMLなら拒否するテスト、既存runを保護するテストを実行する。

**受入:** 3入力の原本が保存され、内容・取得状態を説明できる。取得できなかったものは0件の正常終了としない。

### Task 2 — 香港と福岡を別系列で集計する

**Files:** 同スクリプトとテスト、observations/coverage/summary。

内部の純粋関数 `quarter_label(text: str) -> str`、`rebase(points: dict[str, float], base_period: str) -> dict[str, float]`、`relative_price_rent(price_index: float, rent_index: float) -> float` を使う。非正の指数と存在しない基準期は `ValueError` を返す。

- [x] 香港の2段見出し・クラス列・Remarks列を読み、観測期間と数値の対応を確認する。
- [x] 非数値を欠損として保持し、重複期は原因が分かるまで集計を止める。暫定符号は保持する。
- [x] 福岡の住宅地と市/区を集計し、件数と単位を添える。
- [x] 下記の計算例と、ゼロ基準値・未知の基準期・重複四半期の拒否をテストする。

```python
from global_city_pilot import quarter_label, rebase, relative_price_rent


def test_quarter_label():
    assert quarter_label("04-06/2026") == "2026Q2"


def test_rebase():
    assert rebase({"2015Q1": 200.0, "2026Q2": 300.0}, "2015Q1") == {
        "2015Q1": 100.0,
        "2026Q2": 150.0,
    }


def test_relative_price_rent():
    assert relative_price_rent(150.0, 120.0) == 125.0
```

**受入:** 香港の初期・中期・最新の各3点を原本照合。福岡2026年住宅地195地点、市平均258,100円/㎡（100円単位丸め）が既存検証と一致。原本更新で期間・行数が変われば更新理由を記録し、187行へ無理に切らない。

### Task 3 — 最小HTMLを出して初回Aを完了する

**Files:** 同スクリプト、run内report.html、検証Markdown。

- [x] 香港の価格・賃料・相対比率、福岡の別パネル、カバレッジ表と出所を載せる。
- [x] `/home/kazumasa/projects/docs/templates/claude-report/` のテンプレートと色を使い、CSS・データ・SVGをHTMLに内包する。
- [x] 年次と四半期を区別し、欠損区間は線を接続しない。福岡と香港を同じ資産のランキングにしない。
- [x] ブラウザーで描画し、オフライン再生成、凡例・日本語・長いラベル、Windows側の実在パスを確認する。
- [x] 検証ノートへ取得済み/未取得、原典照合、計算結果、再生成コマンド、開けるパスを記録する。

**受入:** 保存済み原本だけで再生成でき、香港2系列と福岡地価の図を利用者が開ける。利回り未取得・資産種別の違いが図から分かる。

### Task 4 — 英国を1ソース追加する

**Files:** 同スクリプトとテスト、英国原本、既存出力の次run。

- [x] [HMLRのCSV案内](https://www.gov.uk/government/statistical-data-sets/uk-house-price-index-data-downloads-may-2026)を入口に、実行時点の公表版を確認する。試験済みの5月版は最新版と扱わない。
- [x] Index CSVの `Date,Region_Name,Area_Code,Index` を読んで、ロンドンとマンチェスターの候補コード・地理範囲を確認する。
- [x] 採用コードを設定に保存し、都市圏・中心市の別をラベルにする。名称の部分一致だけで選ばない。
- [x] 同一コード・月の重複、末尾の不完全な四半期を検証する。四半期比較では3か月揃った期だけ平均する。
- [x] 原典3点を照合して価格チャートを追加する。家賃未取得の欄はそのまま残し、価格だけから利回りを作らない。

**受入:** 国内土地と海外住宅価格の区分を維持しつつ、比較できる住宅価格指数の範囲が増える。英国の地理・物件種別が香港と同一条件とは主張しない。

### Task 5 — ONSとNSWの1ファイル試験（段階C）

- [x] ONS 2026年9月公表XLSXの列・地域コード・定義を確認し、ロンドン地域とマンチェスター市の2015年以降の家賃を保存する。
- [x] HPIとPIPRの完全四半期のみを2015Q1で指数化し、価格/家賃の相対変化を表示する。2026Q3は除く。
- [x] NSW 2026年8月XLSXを保存し、州全体とpostcode 2000を区別してフラット/ユニット1〜2寝室の正の週額家賃中央値を示す。
- [x] 家賃不明・0円・住宅種類コード異常の件数、原本ハッシュ、利用条件と再生成方法を記録する。
- [x] ABS 2021のGCCSA・POA配分からGreater Sydneyのpostcode**近似**集合を固定し、2021年1月〜2026年8月の月次履歴を収集する。POAと実郵便番号の差および境界をまたぐ3 POAを注記する。

**受入:** [段階C検証記録](../../../market-research/docs/data/validation/global_city_pilot_20260928T085744Z.md)の原本・件数・再生成結果を照合し、同一物件の利回りを推定しない。

## 6. 拡張時の判断

- NSWは1か月分の試験から68か月の履歴へ拡張した。ABSの住宅用Mesh Block配分による郵便番号近似を固定し、州全体・Greater Sydney近似・postcode 2000を別集計した。標準ライブラリの読取専用XLSXストリーム処理で本番依存を追加していない。
- Zillowは正規のCSV配布導線を確認できたら再評価する。今回の入口403を回避する仕組みは作らない。
- ベルリンは3年試験の原本を保持したまま、2002〜2026年の25年を別スナップショットで取得した。年別ゾーン中央値は同一地点の価格変化と呼ばない。シンガポールではキー不要のdata.gov.sg公開APIで同じ3地域・90四半期の価格/賃料指数を揃えたが、比率は絶対利回りではない。NYCは現行の売買個票APIが読めることを確認し、取引単位の精査前には価格統計に使わない。
- CPI・為替・国債、人口・供給、NOI、シナリオは順に追加する。最初の図は現地名目の指数と明記し、未取得の調整を済ませたように表示しない。
- 自動更新は手動で同じ処理を再実行できてから検討する。今回の計画作成ではジョブを作成しない。

初回Aの受入条件が満たされたら、その時点で一度成果物を提示する。全体計画の「6都市の比較完成」「20都市のカバレッジ」「NOI国際比較」は別の後続マイルストーンとして残す。
