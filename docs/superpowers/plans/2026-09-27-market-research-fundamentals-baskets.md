# Market Research Fundamentals and Baskets Implementation Plan

**Goal:** 工程3cの F03・F04 を、保存済みの公開データだけで再現できる分析として追加する。財務の公表時刻と取得時刻、構成銘柄の基準日、指数近似を結果に残す。

**Scope:** [統合仕様](../specs/2026-09-27-market-research-design.md) の F03・F04 と Q03・Q04・Q10・Q11 の該当部分。[入力層](2026-09-27-market-research-analysis-inputs.md)と[保存契約](2026-09-27-market-macro-fundamentals.md)を使う。通信・口座データ・旧プロジェクトの runtime import・新規本番依存は使わない。

**Boundary:** SEC companyfacts 初版は米国企業の開示値だけ。旧 stock の yfinance `info` にある時点不明の PER・ROE 等を、過去の特徴量として埋めない。バスケットは明示した構成銘柄を過去へ固定した **retrospective 近似**であり、PIT バックテスト入力として使えない。

## Task 1: 開示スナップショットから財務表を作る

**Files:** `market-research/src/market_research/research/fundamentals.py`、`market-research/tests/test_research_fundamentals.py`。

- `FundamentalField` に名称、taxonomy、concept、unit、form を固定する。`FundamentalRequest` は instrument ID、CIK、field、完全 snapshot ID（未取得なら `None`）を持つ。
- `load_fundamental_table(store, requests, *, as_of)` は snapshot の `observed_at <= as_of`、SEC の key、CIK・field の一致を検証する。`snapshot_fundamental_view` から取得時点で利用可能な最新決算期を選ぶ。
- 戻り値は銘柄×field の長い表。値・CIK・taxonomy・concept・unit・form・決算期・`available_at`・`observed_at`・`vintage_kind`・accession・snapshot ID・欠損理由を同じ行に残す。未取得と公表前を区別する。
- **Red:** 後から取った snapshot を過去に使う、別 CIK/概念/単位/form、未完成 snapshot、後日訂正、未取得、公表前、同一期末の曖昧な候補、naive `as_of`。
- **Green/verify:** 対象テスト、market-research 全テスト、Ruff、pre-commit。

## Task 2: テクニカルと開示値を条件表で評価する

**Files:** `market-research/src/market_research/research/screener.py`、`market-research/tests/test_research_screener.py`。

- `ThresholdRule` は出典（`technical` / `fundamental`）、列名、比較演算、数値閾値を明示する。
- `screen_research(indicators, fundamentals, rules)` は asset ごとに `pass` / `fail` / `unknown` を返し、失敗条件と欠損条件を別に記録する。欠損を0や不合格に置き換えない。
- 価格の品質拒否、財務の未取得・公表前、単位の違いを条件結果から見えるようにする。入力表の取得や補完は行わない。
- **Red:** 既知値の境界、複数条件、欠損・不正比較、異なる銘柄の財務を使う事故。
- **Green/verify:** 対象テスト、member全テスト、Ruff、pre-commit。

## Task 3: 構成基準日付きのバスケット近似を計算する

**Files:** `market-research/src/market_research/research/baskets.py`、`market-research/tests/test_research_baskets.py`。

- `BasketDefinition` は名称、構成銘柄、構成基準日、出典、`price` / `market_cap`、PAFまたは株数の仮定日を明示する。
- 価格は `close_history(PriceDataset)` の同通貨・同調整方式の履歴から取る。価格加重は `sum(price_i * PAF_i)`、時価総額加重は `sum(price_i * shares_i)` の水準比。欠損した構成銘柄を前値・ゼロで埋めず、その日の水準を欠損とする。
- 結果に `retrospective`、構成基準日、価格調整、通貨、PAF/株数の仮定、利用 snapshot ID を残す。旧 stock の現構成銘柄遡及・PAF=1を公式指数値やPITとして表示しない。
- **Red:** 2銘柄×3日の手計算、欠損、異通貨、古い構成基準日、PAF/株数不足、同じ日付の異市場終値、PIT用途への転用拒否。
- **Green/verify:** 対象テスト、member全テスト、Ruff、pre-commit。

## Task 4: 比較と入口

- 価格・財務・バスケットの共通結果を、実データの銘柄・バスケット画面とシグナル・スクリーナー画面へ接続する。通信は明示取得CLIだけに残す。
- [STATUS](../../../market-research/docs/STATUS.md) と [README](../../../market-research/README.md) にできた操作、近似、残件を反映する。
- 代表的なオフライン fixture で二画面の入力、欠損表示、出典、基準日を確認する。これだけで工程3c全体の完成とはしない。

2026-09-27 の実装範囲: 保存済みデータモードを既定の合成デモから分け、選択した価格・SEC snapshot を
銘柄・バスケット画面とシグナル・スクリーナー画面に表示する。CIKと銘柄の対応は利用者が明示確認する。
その他5画面は未接続と表示する。代表 fixture の AppTest は通信を遮断して検証した。
保存済みの価格snapshotを比較対象に選ぶ経路を追加し、同じ通貨・調整方式・セッション日・
終値時刻だけを基準化して比較する。欠損は補完しない。公式指数値の再現とPITバックテストへの
転用は今回の範囲外。

独立レビューの修正: 財務表にCIK・taxonomy・concept・formを保持して条件の定義を照合する。
画面はCIKと銘柄を並べ、利用者がCIKを入力した場合だけ財務値を示す（企業名の対応表は未実装）。
保存済みデータの画面は永続runや入力manifest hashをまだ作らないため、研究run IDを表示しない。
PAF=1の仮定日は構成基準日を使う。
