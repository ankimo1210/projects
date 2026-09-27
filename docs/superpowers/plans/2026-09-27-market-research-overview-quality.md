# Market Research Overview and Quality Plan

**Goal:** 工程3cのF13のうち、市場概要・品質表示・アプリ内アラートを保存済み公開価格の共通分析へ接続する。

**Boundary:** `retrospective` 価格履歴だけを表示する。相関は同時に有効なリターンの組数を記録し、欠損を補完しない。通知は画面内だけ。保存run、取得失敗履歴、外部送信、定時実行は別工程で扱う。

## Task 1: 概要と相関の共通サービス

**Files:** `market-research/src/market_research/research/overview.py`、`market-research/tests/test_research_overview.py`。

- 価格履歴と `indicator_table` を同じ銘柄集合・通貨・調整方式で照合し、変化率の横断順位を作る。欠損値や品質警告を順位0として扱わない。
- リターンの相関は明示した窓内で、各組の有効な共通リターン数を出す。最低3組未満または分散0なら相関を空欄にし、件数を表示する。異なる通貨、PIT/retrospective混同を拒否する。
- 品質警告、値欠損、明示したdrawdown・z-score閾値からアプリ内アラートを作る。閾値は結果に残す。警告は売買指示ではない。
- **Red:** 2銘柄の手計算順位・相関、欠損で共通組減少、定数列、品質理由、負のdrawdown閾値、入力不一致。

## Task 2: 保存データの市場概要・品質画面

**Files:** `market-research/src/market_research/app_real.py`、`market-research/tests/test_workflow.py`、READMEとSTATUS。

- 概要画面に価格変化・volatility・drawdown・z-score・順位と相関・有効組数、品質画面に選択snapshotの出典・観測時刻、欠損と除外の理由、アプリ内アラートを示す。
- 保存runと取得失敗履歴は未実装と明示する。閲覧はオフラインAppTestで確認する。

2026-09-27 実装記録: 共通サービスで順位、相関と有効組数、品質・閾値アラートを計算し、
保存データの市場概要と品質画面へ接続した。保存run・取得失敗履歴の永続記録は後続と明示した。
