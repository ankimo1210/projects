# JHRMBS

住宅金融支援機構（JHF）の公開情報だけを使い、MBS の回号別月次パネル、期限前償還モデル、
将来キャッシュフロー、WAL・Duration・Convexity・価格を再現可能に計算する Python 3.12+
パッケージです。

MVP は JHF の予定／実績 Factor と任意期限前償還率を中核に、固定 PSJ と3段階の
fractional logit を時系列・vintage の out-of-sample で比較します。入力の原本・SHA-256・
取得日時・定義・加工履歴から、モデル run、予測、回号別 HTML レポートまで追跡できます。

> 調査・教育用です。投資判断、会計・規制報告、公式な価格評価には、商品内容説明書・
> 債券要項と利用者自身の検証が必要です。

## Quick start

リポジトリルート `/home/kazumasa/projects` で実行します。Python 環境はルートの単一 uv
workspace を使います。

```bash
uv sync --package jhrmbs

uv run --no-sync jhrmbs ingest
uv run --no-sync jhrmbs build-dataset
uv run --no-sync jhrmbs train

uv run --no-sync jhrmbs predict --issue JHF-220
uv run --no-sync jhrmbs cashflow --issue JHF-220 --scenario model
uv run --no-sync jhrmbs cashflow --issue JHF-220 --scenario psj --psj-terminal-cpr-pct 6
uv run --no-sync jhrmbs report --issue JHF-220
```

既定設定は [`config/default.yml`](config/default.yml) です。データはリポジトリ管理外の
`/home/kazumasa/projects/_data/jhrmbs` に保存されます。別の場所を使う場合は
`JHRMBS_DATA_ROOT`、別設定は `--config` または `JHRMBS_CONFIG` で指定します。

## CLI

| コマンド | 役割 | 主な出力 |
|---|---|---|
| `ingest` | 公開データを retry・HTTP cache 付きで取得 | raw object、snapshot manifest |
| `build-dataset` | 回号マスター、月次 panel、特徴量と品質検査を作成 | processed / features |
| `train` | 固定 PSJ と3モデルを2種類の OOS で比較し champion を選択・全量再学習 | models / metrics |
| `predict` | 回号の予定 Factor 終了まで CPR・Factor を予測 | predictions |
| `cashflow` | model または PSJ の元利金とリスク指標を計算 | cashflows |
| `report` | 定義・根拠・評価・限界を含む self-contained HTML | reports |

```bash
# 一部ソースだけ更新（複数回指定可能）
uv run --no-sync jhrmbs ingest --source jhf_monthly --source mof_jgb

# 学習時点を固定した予測、金利仮定の上書き
uv run --no-sync jhrmbs predict --issue JHF-220 \
  --run-id 20260720T120000Z --jgb-10y-pct 2.10

# clean-up call は自動推測せず明示した場合だけ残高10%で発動
uv run --no-sync jhrmbs cashflow --issue JHF-220 --cleanup-call \
  --valuation-yield-pct 2.25

# 長期延滞・その他解約の直近12か月平均を生存確率積で合成した total decrement シナリオ
uv run --no-sync jhrmbs cashflow --issue JHF-220 --include-other-decrements

# 凍結 rate feature の平行シフト感応度（レポートには ±0.5pt の表を自動掲載）
uv run --no-sync jhrmbs cashflow --issue JHF-220 --rate-feature-shift-pct 0.5
```

`cashflow` でシナリオに無関係な引数（`--scenario model` での `--psj-terminal-cpr-pct` 等）を
指定した場合は警告を表示して無視します。

## 計算の要点

- 公開 CPR は年率百分率、内部 SMM は月率小数です。
  $SMM_t=1-(1-CPR_t)^{1/12}$ を用います。
- 日本証券業協会の標準 PSJ は WALA 0か月で CPR 0%、60か月で終端 CPR に達し、以後一定です。
- 予測説明変数は原則1か月ラグです。同月の実績 CPR / Factor は使いません。
- 既定の `--model champion` は、時系列・vintage split 内の加重 RMSE 順位を平均し、同順位なら
  平均 RMSE、worst split RMSE の順で run ごとに選びます。`seasoning`、`rate`、`full` の直接指定も可能です。
- 既定の `rate_feature_mode: jgb_proxy` は全学習・予測期間で一貫して `WAC - JGB 10年` を使います。
  公式フラット35 snapshot と proxy を同一係数へ混在させません。これは住宅ローン借換金利そのものではありません。
- キャッシュフローは「予定 Factor 比による約定元本 → 予定元本後残高への SMM → 任意の
  clean-up call」の順です。既定の SMM は任意期限前償還のみで、`--include-other-decrements`
  指定時だけ長期延滞・その他解約の直近12か月平均を生存確率積で合成します。
- 価格は指定した年複利のフラット利回りによる dirty price です。Duration / Convexity は
  期限前償還パスを固定した平行シフトで、OAS ではありません。
- 学習母集団は通常回号（`series_type=monthly`）のみです。S・T・グリーン・E55 への予測は
  外挿として警告し、予測メタデータに `outside_training_population` を記録します。

## 任意の住宅ローン金利履歴

公式スナップショットより前の金利履歴を使用する場合は、データ root の
`raw/manual/mortgage_rates.csv` に次の列を置けます。出所・定義を利用者側で管理し、将来月の値を
入れないでください。モデルに使うには設定を `rate_feature_mode: mortgage_rate` に変更して dataset と
model を再構築します。定義混在を防ぐため、`mortgage_rate_definition`（手動 CSV は `source_note`）で
識別される**単一の定義**が学習行の90%以上を覆わない場合、学習は停止します。

```csv
month,mortgage_rate_mode_pct,source_note
2025-01-01,1.86,officially verified historical series
```

## データレイヤー

```text
raw/          immutable object store + acquisition manifests
processed/    issue master, issue-month panel, external monthly series, quality/lineage
features/     lagged leakage-controlled model table
models/       coefficients, run metadata, OOS metrics and predictions
predictions/  issue-level future CPR / Factor
cashflows/    issue/scenario monthly cash flows and risk summaries
reports/      issue-level technical HTML and metadata
logs/         JSONL execution logs
```

Parquet は計算用、同じ場所の UTF-8 CSV は監査用です。すべての表 artifact に row 数・列・
SHA-256 を記録した metadata JSON を付けます。

## 検証と Notebook

```bash
uv run --no-sync pytest JHRMBS/tests
uv run --no-sync ruff check JHRMBS
uv run --no-sync mypy --config-file JHRMBS/pyproject.toml JHRMBS/src/jhrmbs

# pipeline 実行後にサンプル分析を再実行
uv run --no-sync python JHRMBS/scripts/build_sample_notebook.py --execute
```

Notebook は既存 artifact の読取・可視化だけを行い、取得・学習ロジックは package に残します。

## 仕様書

- [MVP 実装・検証ノート](docs/MVP_IMPLEMENTATION_REPORT.md)
- [実装計画](docs/IMPLEMENTATION_PLAN.md)
- [データソース](docs/SOURCES.md)
- [データ辞書](docs/DATA_DICTIONARY.md)
- [モデル仕様](docs/MODEL_SPEC.md)
- [ADR 0001：公開データ MVP](docs/decisions/0001-public-data-mvp.md)
- [ADR 0002：時点整合とキャッシュフロー](docs/decisions/0002-timing-and-cashflow.md)

## 既知の限界

- 公開プール月次データでは、個別債務者属性や competing risk の因果的識別はできません。
- フラット35の公式過去金利は現状 PDF グラフ中心です。既定 MVP は定義の混在を避けて全期間を
  JGB proxy とし、十分な同一定義履歴を用意した別 run で mortgage-rate model を比較します。
- clean-up call、支払ラグ、経過利息、休日規則は商品資料に基づく銘柄別確定処理ではありません。
- 高度モデル、確率的金利パス、rate-dependent prepayment、OAS は予測・cashflow interface の
  拡張先であり、MVP の算定対象外です。
