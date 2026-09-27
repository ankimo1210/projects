# Market Research Virtual Portfolio Risk Plan

**Goal:** 工程3cのF11のうち、保存済みの同一通貨価格から仮想ウェイトの制約と年率リスク寄与を再現可能に計算し、口座データなしで画面に示す。

**Boundary:** `market-research` の既存 NumPy / pandas を使う。旧 quantkit の数式は比較対象にするが runtime import はしない。入力は `IndicatorInput` の表示用 `retrospective` 履歴に限定し、PITバックテストや実口座配分として扱わない。通貨換算は未実装で、異通貨を混ぜずに明示的に拒否する。

## Task 1: 仮想ウェイトとリスクの純粋関数

**Files:** `market-research/src/market_research/research/portfolio.py`、`market-research/tests/test_research_portfolio.py`。

- `VirtualConstraints` は long-only、gross 上限、銘柄上限、現金下限を明示する。入力ウェイトは全銘柄を明示し、欠損・非有限値・マイナス・超過を拒否する。暗黙の正規化や欠損のゼロ埋めはしない。
- `virtual_risk_report(source, weights, *, lookback, periods_per_year, constraints)` は対象窓の全構成銘柄で確定価格とリターンが揃うときだけ、標本共分散から総ボラティリティと各銘柄の年率componentを計算する。componentの合計は総リスクに一致する。ゼロ分散は明示して0を返す。
- 結果は入力mode、通貨、調整方式、観測数、年間観測数、開始・終了時刻、現金比率、品質理由を保持する。価格を取得・保存しない。
- **Red:** 2銘柄の手計算値、0ウェイトと現金、負値/超過/欠落、窓不足、欠損日、文字列・非有限価格、異通貨の入力拒否、ゼロ分散。
- **Verify:** member suite、Ruff、pre-commit。

## Task 2: 保存データの仮想配分・リスク画面

**Files:** `market-research/src/market_research/app_real.py`、`market-research/tests/test_workflow.py`、READMEとSTATUS。

- 選択した価格snapshotの銘柄に対して、等ウェイトの仮想配分を初期値とし、明示した年率基準と窓で年率リスク・構成銘柄寄与・現金比率・品質を表示する。制約を満たさない入力と履歴不足は理由を示す。
- 保存データのほかの画面や合成デモを変更しない。GUI操作はオフラインのAppTestで確認する。これは将来の口座連携やFX換算を完成したとは示さない。

2026-09-27 実装記録: `VirtualConstraints` と `virtual_risk_report` を追加し、
同じ通貨・調整方式の保存済み表示履歴だけからリスク寄与を計算する。
仮想ウェイトは画面で銘柄別に入力し、銘柄上限・最低現金比率と照合する。
窓の価格欠損は拒否し、合成デモ、旧口座処理、外部通信は変更していない。
