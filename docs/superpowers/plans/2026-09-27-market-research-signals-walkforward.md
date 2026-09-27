# Market Research Signals and Walk-Forward Plan

**Goal:** 工程3cのF09とQ11の基礎として、PIT価格から因果的な特徴量、将来ラベルとその利用可能時刻、purge・embargo付きの時系列分割を作る。

**Boundary:** バックテスト入力は工程3cの `build_pit_close_frame` で実際に当時観測済みのsnapshotから組み立てた価格に限る。現在から見た `retrospective` 表示履歴を過去の訓練・成績と呼ばない。特徴量生成は将来ラベルを参照しない。モデル・画面は別タスクで接続する。

## Task 1: 特徴量とラベルの時間を分離

**Files:** `market-research/src/market_research/research/signals.py`、`market-research/tests/test_research_signals.py`。

- PITフレームのラッパーを設け、判断時刻、同一通貨、snapshot出典を要求する。表示用の `IndicatorInput(mode=retrospective)` は受け付けない。
- 特徴量は終値の過去 `window` 期変化率と trailing volatility。`pct_change(fill_method=None)` で欠損を補完しない。ラベルは未来 `horizon` 期のリターンで、その `label_available_at` を別列に持つ。末尾 `horizon` 行はラベルを空欄にする。
- **Red:** 将来価格攪乱で過去特徴量は不変、ラベルは利用可能時刻より前に使えない、欠損が前値埋めされない、naive・重複・異通貨の入力拒否。

## Task 2: purge・embargo付き前向き分割

**Files:** `market-research/src/market_research/research/splits.py`、`market-research/tests/test_research_splits.py`。

- `walk_forward_splits` はPIT出典付きの `SignalDataset` を受け、そこから `horizon` を得る。訓練末尾からテスト先頭まで `horizon + embargo` の空白を取る。各訓練ラベルの利用可能時刻はテスト先頭より厳密に前。step既定は非重複のテスト幅。評価ラベルが未完成の末尾は分割から除き、途中の欠損ラベルは拒否する。
- **Red:** horizon/embargo境界、ローリングと拡大型、重複・naive時刻、短期データ、lockbox内ラベルの学習拒否。

## Task 3: モデルと戦略比較

- baseline / linear / tree の候補を、同じ分割・費用・データで比較する。scikit-learnを本番依存に追加する場合は、既に送った依存追加の確認への回答を待つ。回答前は追加しない。代替実装を採る場合も、モデルの契約と受入テストを先に固定する。
- CLI・画面・固定例へ接続し、未来データ攪乱と同一run再現をQ09–Q11・Q13で検証する。
