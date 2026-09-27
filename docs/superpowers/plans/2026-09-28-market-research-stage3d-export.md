# Market Research Stage 3d Portfolio Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Status:** 2026-09-28: Task 1–3実装・合成受入済み。旧結果の照合と旧入口切替は別ゲート。

**Goal:** 保存済み市場価格とFXを口座側へ一方向に渡すversioned exportを作り、既存の日次経路を変えずに合成入力でQ12を受け入れる。

**Architecture:** market-researchが明示snapshotからas-of時点の確定・品質合格バーだけをParquetとJSON manifestへ不変保存する。portfolio-analyzerの独立adapterがmanifestの契約版・ハッシュ・時刻を検査し、既存mtm.Quoteへ変換する。口座の保有・取引・損益データを市場側へ渡さない。

**Tech Stack:** Python 3.12、DuckDB、標準ライブラリ、pytest。既存のmarket-research依存だけで書出し、口座側はDuckDBを依存として明示する。

**Spec:** docs/superpowers/specs/2026-09-27-market-research-design.md の5.1、5.3、6、F18、Q12。

## Global Constraints

- exportの出力先は既定でResearchStoreのGit管理外データルート下。外部送信・定時タスク変更は行わない。
- 各バーはinstrument_id、provider_symbol、currency、adjustment、quality、available_at、observed_at、is_final、session_date、snapshot_idを保持する。
- 異なるcurrencyの価格を無換算で足さない。FXはJPY=Xを明示し、staleまたは欠損なら拒否する。
- 個人口座の識別子、保有数量、取引、損益をmanifestへ書かない。
- 既存の日次レポートは従来の取得経路を維持し、依存変更後にメールなしで生成を確認する。

## Review Focus

- manifestのdata_fileに相対脱出パスが混入しても任意ファイルを読まない。
- Parquetを後から差し替えた場合、SHA-256不一致で口座側が拒否する。
- as-ofより後に観測・利用可能となった足をexportしない。
- 同じprovider_symbolに別通貨や別銘柄が衝突したら曖昧なQuoteを作らない。
- 休日明けの価格とFXの古さを別の上限で検査し、失敗理由を分ける。

---

### Task 1: 市場側の不変export

**Files:** market-research/src/market_research/portfolio_export.py、market-research/tests/test_portfolio_export.py。

**Interfaces:** Consumes research.dataset.PriceDatasetとcontracts.PriceBar。Produces write_portfolio_export(datasets: Sequence[PriceDataset], destination: Path, *, fx_symbol: str = "JPY=X") -> Path。返値はmanifest.jsonのパス。

- [x] **Step 1: failing test.** 合成USD株2足、JPY株2足、JPY=XのFX2足を保存済みPriceDatasetとして渡し、manifestとprices.parquetが作成されること、manifestにschema_version=1、SHA-256、行数、snapshot IDs、as_of、fx_symbolがあることをassertする。個人口座の項目がないこともassertする。
- [x] **Step 2: RED.** Run: .venv/bin/pytest -q market-research/tests/test_portfolio_export.py -p no:cacheprovider。Expected: portfolio_export module/function missing.
- [x] **Step 3: minimal implementation.** 各datasetのas_ofが同じtimezone-aware UTCであり、mode=retrospective、バーが確定済み・quality=ok・available_atとobserved_atがas_of以下・adjustment=rawであることを検査。選択したバーを安定ソートしてDataFrame化しDuckDBでprices.parquetを書く。ParquetのSHA-256を計算し、canonical JSONからexport_idを生成。destination/export_idを一時ディレクトリから原子的に確定し、同一IDの既存内容が違えば拒否する。
- [x] **Step 4: GREEN and boundary tests.** Run Task 1 test。追加で未確定、未来、拒否品質、混在as_of、同名symbol衝突、保存先の既存不一致をassertする。
- [x] **Step 5: commit.** market-researchの2ファイルと必要なREADME説明だけをコミット。

### Task 2: 口座側の読取adapter

**Files:** portfolio-analyzer/src/portfolio_analyzer/market_export.py、portfolio-analyzer/tests/test_market_export.py、portfolio-analyzer/pyproject.toml、uv.lock。

**Interfaces:** Consumes Task 1 manifest/parquet。Produces load_market_quotes(manifest_path: Path, *, now: datetime, max_price_age: timedelta, max_fx_age: timedelta) -> tuple[dict[str, mtm.Quote], mtm.Quote]。辞書キーはprovider_symbol。

- [x] **Step 1: failing test.** Task 1の合成exportを読み、USD/JPYの2銘柄とJPY=XがDecimalのclose/prev_closeに変換されることをassertする。version違い、hash違い、data_fileの絶対/親パス、stale FX、欠損FX、衝突するprovider_symbolを個別に拒否するテストを追加。
- [x] **Step 2: RED.** Run: portfolio-analyzer/tests/test_market_export.py。Expected: adapter missing.
- [x] **Step 3: minimal implementation.** JSONを標準ライブラリで読み、schema_versionと固定basename prices.parquet、Parquet hash、UTC as_ofを先に検証する。DuckDBでParquetを読み、列schema・一意性・時刻・通貨を照合し、最新と直前のバーからmtm.Quoteを作る。FXは別のmax_fx_ageで判定する。保有データは引数にも戻り値にも含めない。portfolio-analyzerのproduction依存にduckdb>=1.0を明示しlockを更新する。
- [x] **Step 4: GREEN.** 対象テストとportfolio-analyzerの既存suite、Ruffを実行する。
- [x] **Step 5: commit.** adapter・テスト・依存とlockだけをコミット。

### Task 3: 明示的なCLI入口とQ12受入

**Files:** market-research/src/market_research/cli.py、market-research/tests/test_portfolio_export.py、market-research/README.md、portfolio-analyzer/README.md、market-research/docs/STATUS.md。

**Interfaces:** market-research export-portfolio --snapshot-id ID (repeat) --fx-snapshot-id ID --as-of ISO --destination PATH。既定のdestinationはdata-root/exports。

- [x] **Step 1: failing test.** 一時ResearchStoreの合成snapshotでCLIを実行し、返却JSONのexport_idとmanifestパスが実在すること、通信関数を呼ばないこと、同じ入力の再実行で同一IDになることをassertする。
- [x] **Step 2: RED.** Run: .venv/bin/pytest -q market-research/tests/test_portfolio_export.py -p no:cacheprovider。Expected: unrecognized export-portfolio command.
- [x] **Step 3: minimal implementation.** 明示IDごとに保存済みsnapshotを読み、同じas_ofでPriceDatasetを作りTask 1 writerへ渡す。既定destinationはResearchStore root下、エラー表示に口座や秘密の値を出さない。READMEに一方向・Git管理外・従来日次未変更を記載。
- [x] **Step 4: GREEN and acceptance.** market-research member suite、portfolio adapter suite、CLI合成実行、uv lock --check、Ruff/pre-commitを確認する。共有.venvを同期した場合は日次レポートをメール指定なし・一時出力先で1回生成し、生成物の内容を表示せず削除する。
- [x] **Step 5: commit.** CLI、テスト、説明、STATUSをコミット。Q12の証拠と未接続の旧日次経路を明記する。

## Finish

工程3cの保存run・HTML・画面の受入と合わせてQ13を確認し、工程3dのexportと旧入口切替を別々のゲートとして扱う。旧市場5プロジェクトの退避は、その機能の照合と復元手順を記録してから工程4で実施する。


## 検証記録（2026-09-28）

- market-research 290件成功、portfolio-analyzer 318件成功・private fixture不足で19件skip。
- 市場側の不変Parquet/manifestから口座側Quoteへ変換する合成統合を確認。schema版、
  SHA-256、as-of、価格とFXの別々の鮮度、同名symbol衝突、パス逸脱を拒否する。
- uv lock --check成功。隔離worktreeで全workspaceをsync後、既存日次スクリプトを
  メール指定なし・履歴とHTMLを一時フォルダにして実行。終了コード0、HTML 2件。
  一時ファイルは削除し、Windows定時タスクと共有mainの環境は変更していない。
- 工程3d全体の完了には、旧入口の結果差分と採否を記録し、対象ごとの切替・退避後に
  workspace設定と起動経路を再検証する必要がある。
