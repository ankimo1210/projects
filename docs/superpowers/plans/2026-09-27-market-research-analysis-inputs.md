# Market Research Analysis Inputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 工程3cの分析が、保存済み価格の出典と利用可能時刻を維持したまま、オフラインで共通入力を作れるようにする。

**Architecture:** `ResearchStore` の完全な snapshot ID を明示して読み、価格・除外・欠損を不変の入力集合にまとめる。表示用の「現在から見た履歴」と、各判断時点に存在した snapshot だけを使うバックテスト用の履歴を別の関数にする。どちらも外部取得を行わず、通貨・調整方式・provider を暗黙に混ぜない。

**Tech Stack:** Python 3.12、既存の pandas / NumPy / DuckDB、pytest。新規 production 依存なし。

**Spec:** [market-research 統合仕様](../specs/2026-09-27-market-research-design.md) の F01、F05、F08、Q02–Q04、Q09–Q11、および [工程3bの保存契約](2026-09-27-market-data-ingestion.md)。

## Global Constraints

- `as_of` と判断時刻は timezone-aware 必須。取得時刻より前の snapshot を履歴へ遡及適用しない。
- `raw` と `unknown` の調整方式、異なる通貨・provider を同一系列へ自動結合しない。
- 非確定足と欠損はゼロリターンや前値埋めに変えない。警告と除外理由を保持する。
- 表示のための履歴は `retrospective` と表示し、保存時点以前の PIT データと呼ばない。
- 研究コードは口座ファイル、外部 API、旧4プロジェクトの runtime import を使わない。

## Review Focus

1. snapshot の `observed_at` が判断時刻より後でも過去の分析に採用される事故を拒否する。
2. 同じ銘柄の異なる provider や調整方式を混ぜたときに明示的に拒否する。
3. 休場・無約定・未確定足を価格ゼロやリターンゼロへ変えない。
4. 価格の後日訂正を追加しても、その訂正前の判断時刻の入力とウェイトを変えない。
5. 複数市場を同じ決定時刻に比べる場合、足がまだ閉じていない銘柄を保持中の計算へ渡さない。

---

### Task 1: 明示 snapshot から表示用の価格入力を読む

**Files:**
- Create: `market-research/src/market_research/research/__init__.py`
- Create: `market-research/src/market_research/research/dataset.py`
- Test: `market-research/tests/test_research_dataset.py`

**Interfaces:**
- Consumes: `ResearchStore.get_snapshot(id)`、`ResearchStore.snapshot_price_view(snapshot, as_of)`、`PriceBar`、`PriceGap`。
- Produces: `PriceDataset`（`as_of`、`mode="retrospective"`、`bars`、`gaps`、`exclusions`、`snapshot_ids`、`currency`、`adjustment`）と `load_price_dataset(store, snapshot_ids, *, as_of, currency, adjustment) -> PriceDataset`。

- [ ] **Step 1: Write the failing tests.** 実 `ResearchStore` に2銘柄の完全snapshotを保存する。`load_price_dataset` は両銘柄を返し、`mode` と ID を保持する。未来のsnapshot、未完成snapshot、別通貨、別調整方式、同銘柄の別provider、snapshot ID重複、空選択をそれぞれ拒否する。未確定足と `PriceGap` は返すが確定価格に昇格させない。
- [ ] **Step 2: Run the targeted test.** リポジトリルートで `uv run --no-sync pytest market-research/tests/test_research_dataset.py -q`。新モジュール未定義による失敗を確認する。
- [ ] **Step 3: Implement the reader.** `as_of` をUTCへ正規化し、各IDを `get_snapshot` で検証する。`snapshot.observed_at <= as_of`、`key.dataset == "prices"`、`key.currency == currency`、`key.adjustment == adjustment`、`complete` を要求する。同一銘柄の重複snapshotとprovider混在を拒否し、`snapshot_price_view` の `bars / gaps / exclusions` を連結して不変tupleへ収める。価格がない場合も欠損・除外があればその理由を保持する。
- [ ] **Step 4: Run the test and member suite.** `uv run --no-sync pytest market-research/tests/test_research_dataset.py -q` と `uv run --no-sync pytest market-research/tests -q` を実行し、出力と終了コードを読む。
- [ ] **Step 5: Commit.** `git add market-research/src/market_research/research market-research/tests/test_research_dataset.py && git commit -m "feat: load explicit research price snapshots"`。

### Task 2: 判断時点ごとの価格履歴を組み立てる

**Files:**
- Create: `market-research/src/market_research/research/history.py`
- Test: `market-research/tests/test_research_history.py`
- Modify: `market-research/src/market_research/research/__init__.py`

**Interfaces:**
- Consumes: Task 1 の `PriceDataset` と `ResearchStore`。
- Produces: `build_pit_close_frame(store, snapshot_ids_by_instrument, decision_times, *, currency, adjustment) -> pd.DataFrame`。行はUTCの判断時刻、列は明示したinstrument ID。値はその時刻までに観測済みの完全snapshotが示す直近の確定終値。

- [ ] **Step 1: Write the failing tests.** 2つの判断時刻の間に訂正snapshotを追加し、最初の行と `run_prefix_strategy` の最初のウェイトが不変であることを確認する。取得時刻が未来のsnapshot、古い足しかない銘柄、未確定足、無約定、通貨・調整方式の不一致、重複・naive判断時刻を拒否する。固定した2銘柄×3時点の終値は手計算値と一致させる。
- [ ] **Step 2: Run the targeted test.** `uv run --no-sync pytest market-research/tests/test_research_history.py -q` で新関数未定義の失敗を見る。
- [ ] **Step 3: Implement the frame builder.** 判断時刻ごとに、各銘柄の `observed_at <= decision_at` の完全snapshotを選び、最新snapshotの `snapshot_price_view` から確定・利用可能な足だけを読む。その判断時刻までの最後の新しい足がない場合は `ValueError` とし、前値埋めを行わない。市場間の同日結合は日付ラベルで推測せず、呼出側の共通 `decision_times` に従う。行列に `timing="decision_close"` を付ける。
- [ ] **Step 4: Run the targeted and member suites.** `uv run --no-sync pytest market-research/tests/test_research_history.py -q` と `uv run --no-sync pytest market-research/tests -q`。
- [ ] **Step 5: Commit.** `git add market-research/src/market_research/research market-research/tests/test_research_history.py && git commit -m "feat: assemble point-in-time research closes"`。

### Task 3: 表示指標とデータ品質を同じ入力から出す

**Files:**
- Create: `market-research/src/market_research/research/indicators.py`
- Test: `market-research/tests/test_research_indicators.py`
- Modify: `market-research/src/market_research/research/__init__.py`

**Interfaces:**
- Consumes: `PriceDataset` の確定バー、`build_pit_close_frame` の価格行列。
- Produces: `close_history(dataset) -> IndicatorInput`（`prices` は市場ごとの `session_date` で揃え、行時刻はその日の最後の `bar_end`。mode・通貨・調整方式・品質を別フィールドで保持）と `indicator_table(source, *, momentum_window, volatility_window) -> pd.DataFrame`（変化率、年率volatility、drawdown、z-score、欠損理由）。

- [ ] **Step 1: Write the failing tests.** 既知の5観測で変化率・drawdown・volatilityを手計算で照合する。prefixの後ろへ極端な価格を追加しても前の指標値が変わらないこと、短い系列は `NaN` と理由を返すこと、`warn` は理由を残し `reject` は分析値に使わないこと、異通貨・別provider混合を拒否することを確認する。
- [ ] **Step 2: Run the targeted test.** `uv run --no-sync pytest market-research/tests/test_research_indicators.py -q` で新関数未定義の失敗を見る。
- [ ] **Step 3: Implement pure calculations.** pandasの `pct_change(fill_method=None)`、`rolling`、`cummax` を使い、対象ウィンドウ不足をゼロにしない。`IndicatorInput` に入力モード、通貨、価格調整、quality reasons を明示し、`attrs` に依存しない。`reject`・無約定・未確定足から古い終値を「現在値」に繰り上げない。取得・保存やUI処理はこのモジュールに入れない。
- [ ] **Step 4: Run verification.** 対象とmember suite、`ruff check market-research`、`ruff format --check market-research` を実行する。
- [ ] **Step 5: Commit.** `git add market-research/src/market_research/research market-research/tests/test_research_indicators.py && git commit -m "feat: calculate quality-aware market indicators"`。

## Self-review and handoff

- この計画の出口は、実snapshotを使う表示入力と、後日訂正を遡及させないバックテスト入力が別々に動くこと。Q02–Q04・Q09–Q11 のうち価格入力側だけを満たす。
- 財務・バスケット・機械学習・リスク・HTML・7画面・5ノート・口座連携は、それぞれ既存仕様の別計画とテストで実装し、工程3完了をこの3タスクの成功だけでは宣言しない。
- 実データの日足を今日初めて取得した場合、そのsnapshotから過去のPITバックテストは作れない。表示用は `retrospective` と明示し、PIT用には各判断時点に存在したsnapshotが必要。
