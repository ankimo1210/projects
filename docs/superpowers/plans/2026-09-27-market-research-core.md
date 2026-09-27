# market-research Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `market-research` を新しい uv workspace メンバーとして作り、合成データだけで価格時点管理→研究計算→7画面とCLIの入口まで一貫して動かす。

**Architecture:** `src/market_research` がデータ契約と計算の正本、`app/` と CLI は薄い入口。実データの取得は明示的な操作だけにし、オフライン demo と区別する。旧プロジェクトは比較対象に残す。

**Tech Stack:** Python 3.12+、uv、pandas、numpy、Streamlit、Plotly、pytest。既存 workspace で使う依存のみ。DuckDB 保存は後続。

**Spec:** [工程2の統合仕様](../specs/2026-09-27-market-research-design.md)。この計画は工程3の最初の垂直スライスで、旧機能 F01–F19 の全面移行・切替は後続計画で扱う。

## Global Constraints

- 口座・保有・取引データは読まない。portfolio-analyzer と定時タスクを変更しない。
- Demo は画面と出力に合成と明記。閲覧、分析、レポート作成で通信しない。
- UTC の `available_at` を各判断に適用し、後日訂正を過去の情報へ混入させない。
- 価格調整方式を明示し、不明な調整価格を補作しない。品質問題を黙って補正・欠落除去しない。
- バックテストは lag 1 の close-to-close 研究近似。初回コスト・欠損・通貨・基準を固定する。
- `uv` は worktree のリポジトリルートから起動。新しい production ライブラリは追加しない。
- このスライスの UI は7画面の操作経路と明示した未移行項目を示し、機能がない画面を完成扱いしない。

## Review Focus

- 同じ表示 symbol で市場または provider が違う場合のデータ混入を拒否する。
- DST、休日、確定していない足では利用可能時刻を推定値として保存し、当日確定と誤認しない。
- 後日判明した一時的な1/10価格が、過去の判断時点の系列を変えない。
- 保有銘柄の欠損・通貨違いがバックテストの成績をよく見せない。
- demo画面の表示・再描画・レポート書き出しが黙って通信しない。

## File map

| パス | 責務 |
|---|---|
| `market-research/pyproject.toml`, root `pyproject.toml`, `uv.lock` | workspaceメンバー、依存、テスト登録 |
| `market-research/src/market_research/contracts.py` | ID、UTC時刻、価格・マクロの不変契約 |
| `market-research/src/market_research/prices.py` | provider正規化、品質、時点別読取 |
| `market-research/src/market_research/macro.py` | 公表・改定の時点別読取 |
| `market-research/src/market_research/backtest.py` | lagと欠損を固定した研究近似 |
| `market-research/src/market_research/services.py` | demo run、各入口共通の計算 |
| `market-research/src/market_research/cli.py`, `market-research/app/main.py` | 明示的なCLI・Streamlit入口 |
| `market-research/tests/` | Q01–Q04、Q06、Q09–Q11、Q13 のオフラインfixture |
| `market-research/README.md`, `market-research/docs/STATUS.md`, root `README.md` | 起動・進捗・49件目の索引 |

### Task 1: Workspace member and immutable contracts

**Files:** 上記 package設定、`contracts.py`、`tests/test_contracts.py`。

**Interfaces:** `Instrument(market,symbol,currency,timezone)` の `instrument_id`、`PriceBar(instrument,provider,interval,bar_start,bar_end,available_at,observed_at,close,adjustment,revision_id,quality)`、`MacroObservation(indicator,period_start,release_at,value,source,vintage_id)`。すべて frozen dataclass。

- [ ] Workspace の member・testpaths、package metadataを追加する。依存は既存の pandas / numpy / duckdb / streamlit / plotly / pyarrow / click のうち実際に使うものだけ。
- [ ] `test_contracts.py` に市場が異なる同名symbolの ID 非一致、naive datetime拒否、`available_at < bar_end` 拒否、`adjustment='unknown'` の明示保持を先に書く。
- [ ] `uv run --no-sync pytest market-research/tests/test_contracts.py -q` が契約欠如で失敗することを確認。
- [ ] frozen契約とUTC正規化を実装し、同コマンドが成功することを確認。型別の失敗理由は `ValueError` に固定。
- [ ] `uv sync --package market-research` と独立 import を検証し、コミット。

### Task 2: Price normalization, quality and revisions

**Files:** `prices.py`、`tests/test_prices.py`。

**Interfaces:** `normalize_yfinance(raw,instrument,observed_at)`、`assess_bars(bars,as_of)`、`select_bars_as_of(bars,decision_at)`。引数は入力を変更せず、後者は価格の原行と来歴を返す。

- [ ] MultiIndexの単一symbol、調整列がない入力、重複、1/10の値、あとから来たrevisionをfixtureにしたテストを先に書く。
- [ ] `uv run --no-sync pytest market-research/tests/test_prices.py -q` の失敗理由を確認する。
- [ ] rawとadjを区別して正規化し、同じ `(instrument_id,provider,interval,bar_end,adjustment)` には指定時点で利用可能な最後のrevisionだけを選ぶ。未来のrevisionは除外。初版で利用できないadjustmentは明示的にエラー。
- [ ] 戻り値には `ok/warn/reject` と理由を付け、前埋め・0埋めをしない。対象テストと既存の契約テストを通してコミット。

### Task 3: Macro point-in-time reader

**Files:** `macro.py`、`tests/test_macro.py`。

**Interfaces:** `as_of(observations,indicator,when)` と `latest(observations,indicator)`。値と出典・vintageを含む `MacroObservation` の列を返す。

- [ ] 公表直前・同時・直後、過去期改定、naive日時、同時刻競合、source違いのテストを先に書く。
- [ ] `uv run --no-sync pytest market-research/tests/test_macro.py -q` の期待した失敗を確認。
- [ ] `release_at <= when` のみを使い、同periodの最終公表を返す。`latest` は別の現在視点。競合をエラーとして実装。
- [ ] 対象テストと契約テストを通してコミット。

### Task 4: Backtest and prefix isolation

**Files:** `backtest.py`、`tests/test_backtest.py`。

**Interfaces:** `run_backtest(target_weights,returns,commission_bps=0,slippage_bps=0)` は持分・費用・gross/net・equityを返す。`run_prefix_strategy(prices,strategy)` は時点までのコピーだけを callbackへ渡す。

- [ ] 3〜5日手計算の初回建玉・exit・反転、保有列欠落、保有return NaN、価格未来攪乱のテストを先に書く。
- [ ] `uv run --no-sync pytest market-research/tests/test_backtest.py -q` の期待した失敗を確認。
- [ ] engine側で target を1回 shift、費用を `sum(abs(held_t-held_prev)) * (commission_bps+slippage_bps)/10000` で計算。異なる列・保有中欠損・二重lag契約違反はエラー。prefix callbackは過去・当日データのみ。
- [ ] 対象テストと価格テストを通してコミット。

### Task 5: First runnable offline workflow

**Files:** `services.py`、`cli.py`、`app/main.py`、`tests/test_workflow.py`、README・STATUS・ルート索引。

**Interfaces:** `build_demo_run()` は固定seedの合成価格・品質・lag1戦略・run IDを一度計算し、CLIとStreamlitに同じ結果を渡す。CLIの `demo --json` は標準出力へ要約を出す。

- [ ] `build_demo_run()` の再現性、合成ラベル、ネットワーク不使用、CLI JSONのschema、画面用7 view-modelの最低限の値をテストに書く。
- [ ] `uv run --no-sync pytest market-research/tests/test_workflow.py -q` の期待した失敗を確認。
- [ ] `services.py` に共通runを作り、CLIとStreamlitの7画面入口を実装。未移行の財務・basket・liveマクロ等は画面内で未接続と明記する。
- [ ] package READMEにルートからの起動とデモの制限、STATUSに完了・未検証・次のF/Qを記録。ルートREADMEへ49件目を追加。
- [ ] `uv run --no-sync pytest market-research/tests -q`、CLI実行、Streamlit smoke、ruff、pre-commitを確認しコミット。

## Next increments

次の計画では実provider接続と不変cache・PIT DuckDB保存、財務・バスケット・e-Stat/SEC、戦略/リスク/5ノート、HTML、portfolio向け一方向export、旧コードとの差分照合、代表画面の手動操作、メールなしの日次確認、切替を扱う。上記Task 5の7画面は初版の完成判定ではない。

## 実装レビューでの契約補強（2026-09-27）

- yfinance形式の入力indexは日付ラベルかもしれないため、`normalize_yfinance` は
  `expected_provider_symbol` と各行の `BarTiming(start, end, is_final)` を要求する。
  取引所カレンダーからこの値を供給する実provider adapterは後続。
- 合成デモは足終端から1時間後を判断時刻とし、`available_at` と照合した。
- `run_backtest` は `base_currency` と資産ごとの `return_currencies` の明示を要求し、
  異通貨の値を合算しない。FX換算済みであることの証跡・実装は後続。
