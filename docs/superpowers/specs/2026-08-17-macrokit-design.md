# macrokit — 日米マクロ経済指標のリサーチ基盤 設計書

- 日付: 2026-08-17
- 対象: `/home/kazumasa/projects/macrokit`（新規）
- 位置づけ: 日米の経済指標をポイントインタイムで蓄積し、マクロ計量モデルの土台にする

## 1. 動機

日米の経済指標を分析したいが、既存プロジェクトのどれもこの目的に合わない。

- `quantkit` は投資リサーチ基盤であり、マクロはシグナル生成のための一機能。
  ポイントインタイム基盤（`macro/store.py` の `as_of` / `latest` / `revisions`）は
  よくできているが、**指標カタログが薄い**（FRED の名前付きは 12 本のみ、
  それ以外は呼び出し側が生の series ID を知っている前提）。公表カレンダーも
  分析レイヤもない。
- `stockkit` / `market-viz` は価格中心。
- `labor_ai_quadrant` は EDINET 由来の企業データで、マクロ統計ではない。

本プロジェクトは「指標ユニバースの定義 + 公表カレンダー + ポイントインタイム蓄積」を
一次成果物とする。モデル（Nowcast・レジーム判定・反応関数）は次フェーズ。

### なぜ今すぐ始める必要があるか

**日本の統計には vintage（改定前の値）が存在しない。**e-Stat API 仕様 3.0 版を確認した
ところ、realtime / vintage / 公表時点を指定するパラメータはなく、提供されるのは
`OPEN_DATE`（公開日）と `UPDATED_DATE`（最終更新日）のみである。日銀・内閣府・財務省の
CSV も上書き公表。

したがって日本側の「速報 → 1 次改定 → 2 次改定」を追うには、**公表時点のファイルを
自分で保存し続けるしかなく、過去分は原理的に復元できない**。日本の GDP は改定幅が
大きく、これは飾りではなく本質的な制約である。1 日でも早く蓄積を始めた分だけ、
将来の分析可能性が増える。

米国は ALFRED があり全 vintage を遡って取得できる。**この非対称が本設計の最重要事実**
であり、データモデル・取得層・実装順序のすべてに反映されている。

## 2. スコープ

### 含めるもの

| 層 | 内容 |
|---|---|
| カタログ | 指標 1 本 = YAML 1 エントリ。ソース・ID・頻度・公表規則・因果連鎖・罠メモ |
| raw スナップショット | 生ファイルを日付付き immutable 保存。日本の vintage の唯一の源泉 |
| ストア | DuckDB。観測テーブル・内訳テーブル・PIT 関数（`as_of` / `latest` / `revisions`） |
| 取得層 | ソース別の薄いアダプタ 7 本 + 3 層の差分検出 |
| 公表カレンダー | 米国は FRED API から自動、日本は YAML の規則宣言 |
| 変換 | MoM / YoY / 3m・6m 年率 / 寄与度 / 裾野（保存せず都度計算） |
| 検証 | カタログ整合・パース・相互検証・PIT 不変条件・変換 |

対象は Sol 案の MVP をそのまま採用し、**日米各 15 リリース群・約 50 系列**（付録 A）。

### 含めないもの（YAGNI）

| 外すもの | 理由 |
|---|---|
| Consensus / SurpriseZ | 発表直前の市場予想中央値に無料 API が存在しない。Investing.com 等の スクレイピングは方針上行わない |
| 分足の市場反応（発表 5 分後 / 30 分後） | 無料で入手不能。USD/JPY の分足は直近しか遡れず、JGB・UST の分足は入手経路がない |
| Nowcast・レジーム判定・反応関数・サプライズβ | 基盤の次フェーズ。カタログのメタデータだけ先に用意する |
| ダッシュボード | 確認用 CLI と notebook 1 冊のみ |
| BLS / BEA / Census の直接 API | FRED がミラーしており、しかも直接 API と違って vintage が付く。キーを取る必要がない |

**サプライズ分析の代替**: Philadelphia Fed の Survey of Professional Forecasters と
NY Fed の Survey of Primary Dealers は無料・構造化データで公表されており、カタログに
指標として含める。日本側は日銀展望レポートの政策委員見通し（無料）が近い。ただし
いずれも四半期・会合単位であり、「発表直前のコンセンサス」ではない。高頻度サプライズは
作らず、四半期の予測 vs 実績にとどめる。

**市場反応の代替**: 当日引け・翌日引け・1 週間後の日次反応なら計算できる。市場データを
経済統計と同じ観測スキーマに同居させることで、結合なしに引ける（4.2 節）。

### 既存プロジェクトとの境界

`quantkit` には**一切依存しない**（`import quantkit` を行わない）。理由は目的が異なり、
マクロ計量向けに設計をやり直す必要があるため、および `~/projects` は複数セッションが
index/HEAD を共有するため依存方向を持つと壊れやすいため。

ただし `quantkit/src/quantkit/macro/connectors/` の実装は**読んで参考にする**。同じ API を
叩くので、e-Stat の期間コード解析や欠損表現（`-` `***` `X` `...` `－`）の扱いは既に
解かれた問題である。

## 3. 確認済みの制約

設計前に一次資料で裏取りした事実。

| 項目 | 確認結果 | 出典 |
|---|---|---|
| e-Stat の vintage | realtime / vintage / 公表時点のパラメータは**存在しない**。`UPDATED_DATE` のみ。改定時の旧データ保持についての記述もない | e-Stat API 仕様 3.0 版 / 2.1 版 |
| e-Stat の公表予定 | `getStatsList` / `getStatsData` のレスポンスに公表予定日に相当する項目は**ない** | 同上 |
| FRED の公表カレンダー | `fred/releases/dates` が全リリースの公表日を返す。`include_release_dates_with_no_data=true` で**将来の公表予定日も返る**（既定では除外） | FRED API docs |
| FRED の vintage | `fred/series/vintagedates` が改定日一覧を返す。**値が変わらなかった公表日は除外される**。観測は `date` / `realtime_start` / `realtime_end` を持つ | FRED API docs |
| 日銀 消費活動指数 | **公表継続中**。最新 2026-08-07、毎月第 5 営業日 14:00。2025-06-06 に遡及改定、2026-04-30 に見直し告知あり（vintage 蓄積の対象） | 日銀サイト |
| API キー | `FRED_API_KEY` / `ESTAT_API_KEY` は設定済み。BLS / BEA / Census は未取得だが**不要** | `stock/.env` |
| 依存パッケージ | httpx / requests / pyyaml / pydantic / duckdb / pandas / tenacity / click はインストール済み。**新規の本番依存はゼロ** | `uv pip list` |

日本の営業日計算は、内閣府が公式公開する「国民の祝日」CSV（1955 年〜翌年分）を
他のソースと同じくカタログの 1 系列として取得することで、依存を追加せずに解決する。

## 4. データモデル

### 4.1 カタログ YAML

```yaml
# catalog/jp/labor.yaml
- name: jp_scheduled_earnings          # 一意スラッグ
  country: JP
  block: labor                          # prices|labor|activity|demand|capex|external|policy|market
  title_ja: 所定内給与（一般労働者・共通事業所）
  source: estat
  source_ref:
    stats_id: "0003084821"
    cat_filter: {tab: "01", cat01: "020"}
  freq: M
  unit: yen
  sa: nsa                               # nsa | sa
  release_lag_days: 35
  release_rule:
    kind: nth_business_day              # nth_business_day|fixed_day|nth_weekday|manual
    n: 5
    time: "14:00"
    tz: Asia/Tokyo
    calendar: jp
  vintage: snapshot                     # alfred | snapshot | none
  chain:
    upstream: [jp_shunto_wage_hike]
    downstream: [jp_cash_earnings, jp_real_wage]
  caveats:
    - サンプル入替で断層が出る。前年比は「共通事業所」ベースを使う
```

`chain` によりカタログが因果グラフを兼ねる。「春闘 → 所定内給与 → 現金給与総額 →
実質賃金 → 個人消費 → サービス物価」のような連鎖は、可視化側でグラフを辿るだけで
1 枚に描ける。

### 4.2 実装状態（50 系列を捌く仕組み）

```
declared  →  fetching  →  parsed  →  validated
   │            │            │           │
 YAML に      raw が      観測レコードに  既知値・
 あるだけ     取れる      正規化できる    他ソースと突合済み
```

**`fetching` に到達した時点で日本の vintage 蓄積が始まる。**パースが 1 行も
書けていなくても生ファイルは貯まる。したがって作業順序を「全部パースしてから運用開始」
ではなく「50 本を最速で `fetching` にし、パースは後追い」にできる。50 系列という規模を
選んでもパースの泥沼で基盤設計が止まらないのは、この状態管理のためである。

**状態は YAML に手書きせず、実態から算出する。**手書きにすると「実装したのに `declared`
のまま」が必ず起きて腐るため。判定基準は以下。

| 状態 | 判定 |
|---|---|
| `declared` | カタログに存在する |
| `fetching` | アダプタに `fetch_raw()` があり、`manifest.jsonl` に取得実績がある |
| `parsed` | `parse()` があり、`observations` に当該 `indicator` の行がある |
| `validated` | その指標の検証テストが存在し、直近の実行で通っている |

テストは状態に連動する。`validated` のみ値の突合を要求し、`declared` は YAML スキーマ
検証のみ。進捗は `macrokit status` で一覧表示する。

### 4.3 観測テーブル

```sql
CREATE TABLE observations (
  indicator     VARCHAR,     -- カタログの name
  period_start  DATE,
  period_end    DATE,
  release_date  TIMESTAMP,
  vintage_seq   INTEGER,     -- 何回目の公表か（1 = 速報）
  value         DOUBLE,
  unit          VARCHAR,
  sa            VARCHAR,
  freq          VARCHAR,
  source        VARCHAR,
  source_url    VARCHAR,
  ingested_at   TIMESTAMP,   -- 自分が取得した時刻
  vintage_kind  VARCHAR      -- 'actual' | 'estimated' | 'snapshot'
);
```

`vintage_kind` を 3 値にするのが要点。`release_date` が本物かどうかを混ぜない。

| 値 | 意味 | 該当 |
|---|---|---|
| `actual` | ソースが公表日を明示 | 米 ALFRED、US Treasury |
| `snapshot` | 自分が取得した時刻から復元 | 日本の全指標 |
| `estimated` | 公表ラグからの推定 | 公表日不明の系列 |

日本の系列で `release_date` を本当の公表日のように見せると、分析が静かに壊れる。
ここは正直に持つ。

**変換値は保存しない。**vintage ごとに計算し直す必要があり、保存すると組み合わせが
爆発する。関数で都度計算する（50 系列規模で速度は問題にならない）。

内訳は別テーブル。CPI の品目別、GDP の需要項目別が入り、寄与度分解と裾野
（上昇品目比率）の計算源になる。

```sql
CREATE TABLE components (
  indicator, component_code, component_name, weight,
  period_start, release_date, value
);
```

市場データ（UST / JGB カーブ、USD/JPY、BEI、OAS、株価指数）は**別テーブルにせず
`observations` に同居**させる。こうすると「指標公表日の翌営業日の 10 年金利変化」が
結合なしで引ける。コモディティ・CDX・MOVE は無料入手性が不確かなので、カタログに
宣言だけ置き `declared` のまま保持する。

### 4.4 raw スナップショット層

```
data/raw/{source}/{indicator}/{ingested_date}/{filename}
data/raw/manifest.jsonl
```

immutable、上書きしない。**内容ハッシュで重複排除**する。

```jsonl
{"ingested_at":"2026-08-17T08:31:02+09:00","source":"estat",
 "indicator":"jp_cpi_core","sha256":"3f2a…","bytes":2841002,
 "changed":true,"http_status":200}
```

毎日取得しても中身が同じ日は保存しない。**中身が変わった日 = 改定があった日**なので、
`RevisionShock = RevisedPrevious − PreviousAsPublished` の検出が副産物として得られる。

保存量は 50 系列の日次取得・重複排除ありで年間数百 MB〜数 GB を見込む。
`macrokit/data/` は `.gitignore` と `.agentignore` の両方に追加する。

## 5. 取得層

### 5.1 ソースアダプタ

```
sources/
├── alfred.py     FRED/ALFRED   キー: FRED_API_KEY   vintage: actual
├── estat.py      e-Stat        キー: ESTAT_API_KEY  vintage: snapshot
├── boj.py        日銀          キー不要（CSV）       vintage: snapshot
├── mof.py        財務省        キー不要（CSV）       vintage: snapshot
├── cabinet.py    内閣府        キー不要（CSV/Excel） vintage: snapshot
├── meti.py       経産省        キー不要（CSV）       vintage: snapshot
└── treasury.py   US Treasury   キー不要（JSON API）  vintage: actual
```

各アダプタが実装するのは 3 つのみ。

- `probe()` — 本体を取らずに更新有無を判定（第 2 層）
- `fetch_raw()` — 生ファイル取得
- `parse()` — 観測レコード化

`parse()` が未実装でも `fetch_raw()` があれば状態は `fetching` に到達し、スナップショット
蓄積が始まる。

### 5.2 公表カレンダー

| 国 | 方式 |
|---|---|
| 米国 | `fred/releases/dates` から自動生成。実装コストほぼゼロ |
| 日本 | カタログ YAML の `release_rule` で規則宣言。規則で書けないものは `kind: manual` |

日本の統計は概ね規則的（日銀 消費活動指数 = 毎月第 5 営業日 14:00 など）。HTML
スクレイピングを避け、規則が変わったら YAML を直す方針とする。

### 5.3 差分検出（3 層）

毎日 50 系列をフル取得するのは重く、レート制限にも当たる。軽い順に確かめる。

```
第1層  カレンダー      次回公表日を過ぎたか？                    → コスト 0
   ↓ 過ぎている
第2層  メタ問い合わせ  UPDATED_DATE / vintagedates が変わったか？ → 軽い1リクエスト
   ↓ 変わった
第3層  本体取得        フル取得 → ハッシュ照合 → 変化あれば保存   → 重い
```

第 2 層が効く。日本は `getStatsList` の `UPDATED_DATE` だけ見れば本体を取らずに改定の
有無が分かる。米国は `series/vintagedates` が同じ役割。第 3 層のハッシュ照合を残すのは、
`UPDATED_DATE` が動いたのに中身が同じ（表の体裁のみ変更等）ケースを弾くため。

### 5.4 レート制限と実行

FRED は 120 req/min とされるが 30 req/min に抑える。e-Stat と静的 CSV は 1 req/sec、
失敗時は指数バックオフ（`tenacity`）。日次実行なら第 1・2 層で大半が止まるため、実際の
リクエストは 1 日数十本。

```bash
macrokit ingest --country jp      # 第1〜3層を通して取得
macrokit ingest --due-only        # 公表予定を過ぎたものだけ
macrokit status                   # 50系列の実装状態と最終取得
macrokit calendar --next 14       # 今後2週間の公表予定
```

**定期実行（cron）の登録は行わない。**まず手動で `--due-only` を回して挙動を確認し、
レート制限で問題が出ないこと・取得漏れがないことを確かめてから、別途相談して登録する。

## 6. 検証・テスト戦略

50 系列規模では「動いているつもりで静かに間違っている」が最大のリスク。5 段構成とする。

| 段 | 内容 | ネットワーク |
|---|---|---|
| カタログ整合 | pydantic スキーマ、`name` 一意性、`chain` の参照先実在、循環なし、`release_rule` が解決可能 | 不要 |
| パース | 記録済みフィクスチャに対するパーステスト。ライブは `-m live` で分離 | 不要 |
| 相互検証 | 同一指標を 2 ソースから取得して突合 | ライブのみ |
| PIT 不変条件 | 下記の性質テスト | 不要 |
| 変換 | 寄与度合計 == 全体変化、裾野 ∈ [0,1]、3m 年率が手計算と一致、`sa` フラグの取り違え検査 | 不要 |

**相互検証が最も効く。**日本の主要指標は e-Stat と FRED の両方から取れる
（`JPNCPIALLMINMEI`、`JPNRGDPEXP` 等）。同じ期間の値を突合すれば、自分のパースを外部基準で
検証できる。golden value を手で書くより信頼できるため、突合可能な系列は積極的に
二重取得する。

**PIT 不変条件**（基盤の心臓部なので性質として書く）:

- `as_of(d)` は `release_date > d` の行を絶対に含まない
- `as_of(d)` は前方補完しない（公表前の期間は行ごと存在しない）
- `as_of(今日)` == `latest()`
- `vintage_seq` は期間ごとに 1 から連番、欠番なし
- `vintage_kind='snapshot'` の行の `release_date` は `ingested_at` を超えない

最後の 1 つが日本側の要。取得していない時刻の公表日が入り込んだら壊れている。

e-Stat の既知の罠は最初からフィクスチャに入れる — 欠損表現（`-` `***` `X` `...` `－`）、
期間コードの月/年判定、全角数字、半角中黒の表記揺れ。

## 7. 実装順序

**Phase 3 を最速で終わらせるのが全体の肝**（日本の vintage 蓄積開始 = 失われるデータを
止める）。

| Phase | 内容 | 到達状態 |
|---|---|---|
| 1. 骨格 | パッケージ・DuckDB スキーマ・カタログローダ・PIT 関数。米 `core PCE` 1 本を `validated` まで貫通 | 1 系列だけ緑 |
| 2. カタログ記述 | 50 系列を YAML に書き切る（付録 A） | 全系列 `declared` |
| 3. raw 取得 ★最優先 | 全系列の `fetch_raw()` を通す。パースは書かない。ハッシュ重複排除と manifest | 全系列 `fetching` / **vintage 蓄積開始** |
| 4. パース | ソース単位で `parse()` 実装。順序は alfred → treasury → mof/boj → estat → cabinet/meti（素直な順） | 順次 `parsed` |
| 5. 検証・変換 | 相互検証・PIT 不変条件・変換関数・公表カレンダー | 順次 `validated` |
| 6. 確認 UI | `macrokit status` / `calendar`、確認用 notebook 1 冊 | — |

Phase 3 時点でパースは 1 行も無くてよい。生ファイルさえ貯まっていれば、パースは後から
遡って適用できる。

## 8. workspace 統合

3 箇所への登録が必要。

1. root `pyproject.toml` の `[tool.uv.workspace] members` に `macrokit`
2. 同 `[tool.pytest.ini_options] testpaths` に `macrokit/tests`
3. **root `conftest.py` に `import macrokit`**

3 番目は、ディレクトリ名とパッケージ名が一致するため必須。これが無いと全体 pytest で
namespace パッケージ化して壊れる（`AGENTS.md` に記録済みの pytest 9 問題。
`deep_hedge_price` が踏んだのと同じ罠。症状は `(unknown location)`）。

`macrokit/data/` は `.gitignore` と `.agentignore` の両方に追加する。

## 9. 決定記録

| 論点 | 決定 | 却下した案と理由 |
|---|---|---|
| プロジェクトの目的 | リサーチ／モデリング基盤 | 投資判断への接続・定点観測ダッシュボード・教材化 |
| `quantkit` との関係 | 完全独立（取得層も自前） | 依存する案（推奨したが不採用）。実装は参考にする |
| 最初に載せるモデル | なし。基盤のみ先に作る | GDP Nowcast・循環日付・物価基調分解は次フェーズ |
| 実装方式 | カタログ駆動（YAML 宣言） | コード駆動（50 本超で管理不能）、ハイブリッド（逃げ道が常態化） |
| MVP の広さ | Sol 案の約 50 系列 | 縦に薄く貫通（推奨したが不採用）、日本 vintage 最優先 |
| 市場データ | `observations` に同居 | 別テーブル（結合が増える） |
| 変換値 | 保存せず都度計算 | 事前計算（vintage × 変換で組み合わせ爆発） |
| 日本の公表カレンダー | YAML の規則宣言 | HTML スクレイピング |
| 日本の祝日 | 内閣府 CSV をカタログの 1 系列として取得 | `jpholiday` 等の新規依存追加 |
| 定期実行 | 当面は手動。cron は別途相談 | 即 cron 登録 |

**約 50 系列を選んだことによるパース泥沼リスク**は、4.2 節の実装状態管理と 7 節の
Phase 3 優先で構造的に緩和する。

## 10. 未解決事項

- **内閣府・経産省のソース形式**: GDP・景気動向指数・鉱工業生産の機械可読性を未確認。
  Excel 配布であればパースコストが上振れる。Phase 2 のカタログ記述時に確定する。
- **日銀 CSV の安定性**: `stat-search.boj.or.jp` の CSV エンドポイントの URL 規則と
  安定性を未確認。
- **無料入手性が不確かな市場データ**: コモディティ、CDX、MOVE。`declared` のまま保持し、
  入手経路が判明した時点で昇格させる。
- **e-Stat の改定時の旧データ保持**: API 仕様に記述がないため、旧データが残るのか
  上書きされるのかは不明。本設計は「残らない」前提（スナップショット蓄積）で組んでおり、
  仮に残っていても設計は壊れない。
- **`components` テーブルの粒度**: CPI の品目別をどの階層まで取るか（中分類か小分類か）を
  Phase 4 で決める。裾野の計算結果が階層で変わる。

## 付録 A: MVP 対象リリース群

Sol 案の MVP をそのまま採用。

### 日本（15 群）

東京都区部 CPI / 全国 CPI / 日銀 基調的インフレ指標（刈込平均・加重中央値・最頻値） /
毎月勤労統計 / 失業率・有効求人倍率 / GDP・GDP デフレーター / 鉱工業生産 /
第 3 次産業活動指数 / 小売販売・家計消費 / 日銀短観 / 機械受注 / 法人企業統計 /
貿易統計 / 国際収支 / 日銀会合・OIS・JGB 入札・国債発行計画

### 米国（15 群）

CPI / PCE / PPI / 雇用統計 / ECI / Jobless Claims / JOLTS / GDP / Retail Sales /
Personal Income and Outlays / ISM 製造業 / ISM 非製造業 / Industrial Production /
Durable Goods / Housing・FOMC・Treasury 入札・Quarterly Refunding

### 市場データ（日次、`observations` に同居）

| 分野 | 日本 | 米国 |
|---|---|---|
| 金利カーブ | JGB 2・5・10・20・30・40 年 | UST 3M・2・5・10・30 年 |
| 政策期待 | TONA OIS | SOFR OIS・先物 |
| 期待インフレ | JGBi BEI | TIPS 実質金利、5・10 年 BEI、5y5y |
| 為替 | USD/JPY、実質実効円レート | ドル実効レート |
| 株式 | TOPIX、銀行株 | S&P 500、Nasdaq、銀行株 |
| 信用 | 社債スプレッド | IG / HY OAS |
| ボラティリティ | （入手性未確認） | VIX、MOVE（入手性未確認） |

## 付録 B: 出典

- [FRED API](https://fred.stlouisfed.org/docs/api/fred/) —
  [releases/dates](https://fred.stlouisfed.org/docs/api/fred/releases_dates.html) /
  [series/vintagedates](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html) /
  [series/observations](https://fred.stlouisfed.org/docs/api/fred/series_observations.html)
- [e-Stat API 仕様 3.0 版](https://www.e-stat.go.jp/api/api-info/e-stat-manual3-0) /
  [2.1 版](https://www.e-stat.go.jp/api/api-info/e-stat-manual2-1)
- [日本銀行 消費活動指数](https://www.boj.or.jp/research/research_data/cai/index.htm)
