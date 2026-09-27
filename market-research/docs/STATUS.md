# market-research 開発状況

更新日: 2026-09-27
基準: [工程2の統合仕様](../../docs/superpowers/specs/2026-09-27-market-research-design.md)、
[工程3の初期計画](../../docs/superpowers/plans/2026-09-27-market-research-core.md)、
[価格取得・保存計画](../../docs/superpowers/plans/2026-09-27-market-data-ingestion.md)、
[マクロ・財務の計画](../../docs/superpowers/plans/2026-09-27-market-macro-fundamentals.md)。

## 目標と完了条件

F01–F19 の採否を実装と検証結果に結び、Q01–Q13 を満たす新入口で
市場研究を行えるようにする。旧入口の切替は、その機能の比較・受入後に行う。

| 段階 | 状態 | 根拠・残り |
|---|---|---|
| 工程2 設計 | 完了 | 上記統合仕様、ADR 0004 |
| 工程3a オフライン中核 | main `7c4bb109` へ取込み済み | 価格/マクロ契約、時点別読取、lag1バックテスト、CLI、合成7画面 |
| 工程3b 実データと保存 | main `7b7cbd1b` へ取込み済み | 4価格provider、ALFRED/ESRI/MoF/e-Stat/SEC、manifestと時点別読取、日米株の自動カレンダー。認証元のライブ疎通は残り |
| 工程3c 分析機能 | `codex/market-research-stage3c` で着手 | 明示snapshotの表示入力、時点別の価格履歴、品質付き指標を実装。財務・basket・信号モデル・比較・リスク・5ノート・HTML・実データ画面は残り |
| 工程3d 連携・切替 | 未着手 | portfolio向け一方向export、旧結果との照合、代表画面の手動確認 |

## 検証

- 工程3bのmain取込み後に共有 `.venv` を同期。導入は `exchange-calendars` と関連2パッケージ、
  `market-research` の入れ直しのみ。`portfolio-analyzer` の日次レポートは
  メール指定なし・履歴とHTMLを一時フォルダにして実行し、2つのHTMLを生成して終了コード0。
  一時生成物は削除。全体の `make test` は5分で89%、10分で99%まで進んだが時間上限に達したため、
  全体成功とは扱わない。途中に失敗表示はなかった。
- 工程3cの最初の入力層は[実装計画](../../docs/superpowers/plans/2026-09-27-market-research-analysis-inputs.md)
  に沿い、表示用のretrospective履歴と、当時観測済みsnapshotだけのPIT履歴を分離した。
  独立レビューで見つかった5件を回帰テストで修正し、欠損日を他銘柄によらず保持、初回を含むPIT判断で
  確認済みの足終了時刻を照合、足間隔の混在を拒否、過去の品質警告と年率換算基準を指標に残す。
  後日取得した欠損日の表示順も検証した。memberテスト165件が成功。
  工程3c全体とQ09–Q13の受入は未完了。
- 工程3bのブランチはALFREDの全版取得と再開、ESRIの公表一覧とGDPの回別表、MoFの履歴・当月、
  e-Statの分類指定とページ再開、SEC companyfactsの提出日と対象期を実装した。
  `estimated` と `snapshot` を区別し、完成snapshot単位でオフライン読取する。
  [取得ガイド](DATA.md)にCLIと制約を記録。専用worktreeのmemberテストは129件成功。
- 独立レビューの重要4件を回帰テストで修正。ALFRED/SECの当日取得版は保存できても
  推定利用可能時刻までは読取不可、ESRIは公表回と表の最終四半期を照合、MoFは
  月またぎ再開時に履歴CSVを再取得、ALFRED/e-Statは応答中の資格情報と不正JSONの例外を保護する。
- 公開元のライブ疎通は修正後もESRI公表一覧148件と2026年4–6月期GDP1次速報129行、
  MoF履歴・当月CSVを一時保存先で再確認。CLIの取得→読取は修正前にも確認済み。
- 価格取得は公式取引時間に合わせた一時的な明示スケジュールで、
  2026-09-24〜25のNYSE `IBM` と東証 `7203.T` をyfinanceから各2足取得し、
  除外0件・保存後の再読込各2足を確認。自動カレンダーでも同じ範囲を
  手動JSONなしで再確認し、カレンダーの版をmanifestへ保存できた。他銘柄の網羅性は未検証。
  自動カレンダーの独立レビューでは重大・重要・軽微の指摘なし。
  ALFRED・e-Stat・SECの資格情報は未設定で、ライブ疎通は未実施。
  承認済みの `exchange-calendars` を本番依存に追加し、専用worktreeの `.venv` だけを同期。
  共有mainの `.venv`、定時処理、個人口座には触れていない。
- 以下は前の価格取得ブランチと工程3aの検証記録であり、今回の検証とは分けて読む。
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

1. 工程3cの財務・basket・信号モデル・比較・リスクを共通サービスへ接続し、
   5ノート・HTML・7画面で代表操作を確認する。Q09–Q11・Q13を完了する。
2. ALFRED・e-Stat・SECの設定済み環境で実通信を確認する。ESRIの過去掲載は
   表の取得成功まで実績に昇格させず、MoF/e-Statは収集前の時点を再現しない。
   Q06–Q08のfixtureを継続し、必要な改定・期間の広がりを追加する。
3. 工程3dでportfolio向けexportと口座側adapterを作り、Q12、旧結果との照合、
   旧入口の切替を確認する。

制約: 日米株は自動カレンダーを使用し、それ以外の市場は確認済み時間表が必要。
J-Quantsのライブ認証は未検証。Stooqはブラウザ検証要求でライブ取得不可。
画面は合成デモのままで、実データの分析画面接続は工程3c。
今回のマクロ・財務も旧DBの移管と旧入口の切替はしていない。

## 既知の不具合と修正

- 取引時間中のスナップショットの不具合は修正済み（2026-09-27）。未確定足を保存でき、
  `price_view_as_of` は確定足と除外理由を返す。14:00 JST の当日足と前日確定足の混在、
  翌日も自動確定しないこと、後の確定revisionを選ぶことを含め47件成功。
- 二重lagの検出は `DataFrame.attrs["timing"]` に依存し、属性が消えると素通りする。
- `assess_bars` は直前の足と比べるため、一時的な1/10価格の翌日（元の水準へ戻った日）にも警告が付く。
