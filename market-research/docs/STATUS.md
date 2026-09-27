# market-research 開発状況

更新日: 2026-09-27
基準: [工程2の統合仕様](../../docs/superpowers/specs/2026-09-27-market-research-design.md)、
[工程3の初期計画](../../docs/superpowers/plans/2026-09-27-market-research-core.md)、
[今回の取得・保存計画](../../docs/superpowers/plans/2026-09-27-market-data-ingestion.md)。

## 目標と完了条件

F01–F19 の採否を実装と検証結果に結び、Q01–Q13 を満たす新入口で
市場研究を行えるようにする。旧入口の切替は、その機能の比較・受入後に行う。

| 段階 | 状態 | 根拠・残り |
|---|---|---|
| 工程2 設計 | 完了 | 上記統合仕様、ADR 0004 |
| 工程3a オフライン中核 | main `7c4bb109` へ取込み済み | 価格/マクロ契約、時点別読取、lag1バックテスト、CLI、合成7画面 |
| 工程3b 実データと保存 | 価格取得・保存をブランチ `codex/market-data-stage3b` で実装 | 4価格provider、明示取引時間表、cache、DuckDB。外部マクロ/財務と自動カレンダーは残り |
| 工程3c 分析機能 | 未着手 | 財務・basket・高度信号・比較・リスク・5ノート・HTML |
| 工程3d 連携・切替 | 未着手 | portfolio向け一方向export、旧結果との照合、代表画面の手動確認 |

## 検証

- 今回は86件成功、ruff check/format・pre-commit・相対リンク122件・`uv lock --check` 成功。
  価格取得CLIと保存後のオフライン読取を確認。
  [DATA](DATA.md)にライブ疎通を区別して記録（Binance/yfinance成功、Stooqは検証HTML、J-Quants未検証）。
  依存は既存workspaceのDuckDB/pytz/yfinanceをmemberに明示。専用worktreeだけをsyncし、
  共有mainの `.venv`・定時タスク・口座データには触れていない。全workspace `make test` は未実行。
- 独立レビューの重要2件（正常なnull行で全期間拒否、取得完了時刻/再開による確定昇格）と、
  暗号資産のセッション日を回帰テストで修正。[判断と検証記録](STAGE3B_REVIEW.md)。
- 以下は工程3a時点の根拠。今回のライブ疎通とは分けて読む。
- オフラインテスト44件、CLIの `demo --json`、Streamlit AppTestの7画面、ruff check/formatを確認。
  pre-commit、相対リンクと49件の索引（13 / 7 / 13 / 6 / 10）も確認済み。
- 比較基準として quantkit のバックテストと macrokit のPITテストを実行し、24件成功。
- 工程3aでは旧プロジェクトの実データ・保存DB、個人口座、外部APIへの疎通は確認していない。
- 同じ `run_id` は合成runの入力時刻・価格と費用条件のハッシュに基づく。
  デモの判断は足終端1時間後で、価格の `available_at` と一致する。永続run保管は未実装。
- 独立レビュー後に、日付ラベルから足境界を推定せず明示入力を要求し、provider symbolを照合、
  異通貨リターンを拒否する契約を追加した。実provider側の時刻・FX変換の検証は後続。

## 次の作業

1. 新規カレンダー依存への回答を反映し、日米株の自動解決とライブの銘柄範囲を拡張する。
2. ALFRED/ESRI/MoF/SEC/e-Statの取得・公表時刻・vintage区分・中断再開を移植し、Q06–Q08を完成する。
   現在の `MacroObservation` 保存は合成系列を用いたPIT部分のみで、外部取得器は未接続。
3. 旧分析の採用機能と7画面を順に接続し、Q09–Q13、HTML、portfolio向けexportを完成させる。
4. 依存を変えてroot workspaceを同期した後、portfolio-analyzerの日次処理をメールなしで検証する。

制約: 株は確認済み時間表が必要。J-Quantsのライブ認証は未検証。Stooqはブラウザ検証要求でライブ取得不可。
画面は合成デモのままで、実データの分析画面接続は工程3c。

## 既知の不具合と修正

- 取引時間中のスナップショットの不具合は修正済み（2026-09-27）。未確定足を保存でき、
  `price_view_as_of` は確定足と除外理由を返す。14:00 JST の当日足と前日確定足の混在、
  翌日も自動確定しないこと、後の確定revisionを選ぶことを含め47件成功。
- 二重lagの検出は `DataFrame.attrs["timing"]` に依存し、属性が消えると素通りする。
- `assess_bars` は直前の足と比べるため、一時的な1/10価格の翌日（元の水準へ戻った日）にも警告が付く。
