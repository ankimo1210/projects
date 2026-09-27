# market-research 開発状況

更新日: 2026-09-28
基準: [工程2の統合仕様](../../docs/superpowers/specs/2026-09-27-market-research-design.md)、
[工程3の初期計画](../../docs/superpowers/plans/2026-09-27-market-research-core.md)、
[価格取得・保存計画](../../docs/superpowers/plans/2026-09-27-market-data-ingestion.md)、
[マクロ・財務の計画](../../docs/superpowers/plans/2026-09-27-market-macro-fundamentals.md)、
[財務・バスケットの計画](../../docs/superpowers/plans/2026-09-27-market-research-fundamentals-baskets.md)、
[仮想配分・リスクの計画](../../docs/superpowers/plans/2026-09-27-market-research-virtual-risk.md)、
[市場概要・品質の計画](../../docs/superpowers/plans/2026-09-27-market-research-overview-quality.md)、
[マクロ画面の計画](../../docs/superpowers/plans/2026-09-27-market-research-macro-view.md)。

## 目標と完了条件

F01–F19 の採否を実装と検証結果に結び、Q01–Q13 を満たす新入口で
市場研究を行えるようにする。旧入口の切替は、その機能の比較・受入後に行う。

| 段階 | 状態 | 根拠・残り |
|---|---|---|
| 工程2 設計 | 完了 | 上記統合仕様、ADR 0004 |
| 工程3a オフライン中核 | main `7c4bb109` へ取込み済み | 価格/マクロ契約、時点別読取、lag1バックテスト、CLI、合成7画面 |
| 工程3b 実データと保存 | main `7b7cbd1b` へ取込み済み | 4価格provider、ALFRED/ESRI/MoF/e-Stat/SEC、manifestと時点別読取、日米株の自動カレンダー。認証元のライブ疎通は残り |
| 工程3c 分析機能 | codex/market-research-stage3c で実装・検証中、main未反映 | 品質付き指標・3値スクリーナー・basket・公式指数の明示出典照合・円換算の仮想リスク・マクロ/財務表示、PIT履歴からのzero/mean/ridge/tree比較、Mag7固定例、5ノート、合成runのHTMLと不変保存を実装。7画面の代表操作はAppTestで確認。実providerの網羅、保存データの研究run永続化、ノート分析を一括HTMLへ載せる機能は残る |
| 工程3d 連携・切替 | 一方向exportと口座側adapterを実装・検証中、main未反映 | Q12の合成入力、版・ハッシュ・時刻・FX鮮度検査、日次レポートの従来経路を確認。旧結果の差分記録と旧入口の切替、旧市場プロジェクトの個別退避は残る |

## 2026-09-28の実装・検証

- 工程3cの時点別信号、前向き分割、zero/mean/ridge/treeとbuy-and-holdの同条件比較、
  公式指数の出典を利用者が宣言する照合、保存済みUSD/JPY日足の評価時刻別円換算、
  5本の独立した合成ノート、自己完結HTMLと不変の合成run保存を追加した。
  保存データ画面は複数の当時観測済みsnapshotを選んだときだけ戦略を比較し、
  円換算ではFX snapshot・UTC評価時刻・鮮度上限を要求する。公式指数の真正性と
  過去の構成銘柄は自動確認できない。合成runのartifact IDは入力・コードcommit・
  設定などから作り、元のrun_idを別に記録する。
- market-research member suiteは290 passed。Streamlit AppTestで合成7画面、
  保存データのPIT戦略比較・公式指数比較・円換算リスク、CLIのHTML・保存run再読込を確認。
  5ノートはnbformatとnbclientで各先頭から実行でき、コミットしたセル出力は空。
  コードはRuffとpre-commitを実施する。実データの手動画面確認と認証付きproviderの
  ライブ疎通は未実施。
- 工程3dのmarket側immutable Parquet/JSON exportとportfolio側read-only adapter、
  明示CLIを合成入力で統合。portfolio-analyzer suiteは318 passed、19 skipped
  （隔離worktreeにprivate test fixtureがない）。uv lock --checkが成功。
  隔離worktreeの全workspaceをuv syncした後、private入力を読み込む日次レポートを
  メール指定なし・履歴とHTMLを一時フォルダにして実行し、終了コード0・HTML 2件を確認。
  内容や個人の数値は出力せず、一時ファイルは削除。Windows定時タスクと共有mainの
  .venvは変更していない。

## 検証（以下は各実装時点の履歴。現在の状態は上の表を参照）

- 工程3bのmain取込み後に共有 `.venv` を同期。導入は `exchange-calendars` と関連2パッケージ、
  `market-research` の入れ直しのみ。`portfolio-analyzer` の日次レポートは
  メール指定なし・履歴とHTMLを一時フォルダにして実行し、2つのHTMLを生成して終了コード0。
  一時生成物は削除。全体の `make test` は5分で89%、10分で99%まで進んだが時間上限に達したため、
  全体成功とは扱わない。途中に失敗表示はなかった。
- F09の基礎として、PIT判断時刻ごとの終値から過去特徴量と将来ラベルを別時刻で作り、
  horizon・embargoを空ける前向き分割を追加した。分割器はPIT出典付きのデータセットだけを受け取り、
  評価ラベルが未完成の末尾を除外し、途中の欠損ラベルは拒否する。lockboxの境界は評価行と
  ラベル利用可能時刻の両方で確認する。
  zero/mean/ridgeの前向き予測は同じ訓練・評価行を使い、特徴量の欠損を補完せず、
  ridgeは訓練行だけで標準化する。将来ラベルを特徴量名として指定する経路は拒否する。
  one-stepの予測が正ならlong、それ以外はcashとしてlag1バックテストへ渡し、
  zero/mean/ridgeとbuy-and-holdに同じ価格・費用を適用する。lockbox以降のリターンは使わない。
  treeと戦略比較画面は未接続。追加後のmemberテスト221件、Ruff checkは成功。
- F15のMag7モメンタム順位の固定例を、7銘柄の判断時点に観測済みの日足snapshotから組み立てる
  `run_mag7_example` として追加。旧設定のlookback 126期、銘柄上限0.5、総上限1.0、費用5bpsを既定とし、
  戦略に価格prefixだけを渡してlag1で評価する。合成7銘柄の手計算、将来価格攪乱、lockbox除外を確認。
  完全な合成132営業日では、旧 `generate_weights` + `enforce_constraints` と新prefix例の目標ウェイトが
  全行一致（最大絶対差0）。旧 autostock のsuiteはmainの共有環境で17件成功。
  旧 autostock の一括取得Parquetには過去の取得時点版がなく、当時の履歴PIT成績は再現済みと扱わない。
  新memberテスト224件、Ruff checkは成功。旧プロジェクトの退避は未判断。
  増分レビューで指摘された封印領域への検証依存を修正し、境界前の分割が封印ラベルの不正値・型変更に左右されないことを回帰テストで確認。
  修正後のmemberテスト226件が成功した。
- 工程3cの最初の入力層は[実装計画](../../docs/superpowers/plans/2026-09-27-market-research-analysis-inputs.md)
  に沿い、表示用のretrospective履歴と、当時観測済みsnapshotだけのPIT履歴を分離した。
  独立レビューで見つかった5件を回帰テストで修正し、欠損日を他銘柄によらず保持、初回を含むPIT判断で
  確認済みの足終了時刻を照合、足間隔の混在を拒否、過去の品質警告と年率換算基準を指標に残す。
  後日取得した欠損日の表示順も検証した。
  工程3c全体とQ09–Q13の受入は未完了。
- SEC財務は完全snapshotの観測時刻と開示の利用可能時刻を分け、未取得・未公表を空欄にする。
  出力にはCIK・taxonomy・concept・formを保持し、財務スクリーニングは同じ定義・単位だけを比較する。
  テクニカルと財務の条件は `pass` / `fail` / `unknown` を区別する。
  バスケットは構成日をPAF=1の仮定日として記録して retrospective として計算し、欠損を埋めない。
  比較対象は同じ通貨・調整方式・セッション日・終値時刻の保存済み価格に限定する。
  保存データ画面は通信を行わない AppTest で価格・財務snapshot選択と仮想リスクまで確認。
  独立レビューの重要3件（CIKの隠れた割当、別概念の比較、run IDの誤表示）を回帰テストと表示修正で対応した。
  画面の財務対応は表示されたCIKを手入力した場合だけ有効。企業名対応表は未実装で手動照合を要する。
  保存データ画面は研究runを永続保存していないためrun IDを表示しない。
  バスケット比較と財務レビュー修正時点のmemberテスト185件、Ruff check/format、pre-commit、
  変更文書の相対リンク19件は成功。
- F11の仮想配分は手動ウェイトの銘柄上限・現金下限を検査し、欠損窓を拒否する。
  同一通貨の保存済み価格から年率ボラティリティと銘柄別寄与を算出し、3つ目の保存データ画面で表示する。
  FX換算、実口座、PITバックテストとは接続しない。追加後のmemberテスト189件は成功。
- F13の保存データ画面は変化率順位、共通リターン数を伴う相関、品質・欠損・閾値の
  アプリ内アラートを表示する。選択snapshotの出典、gap、除外理由も表示する。
  保存runと取得失敗履歴は未記録で、外部送信や定時実行は追加していない。
  追加後のmemberテスト192件は成功。
- F06の保存データ画面は、完全なマクロsnapshotの公表・観測時刻を照合し、同じkeyの過去版との差を表示する。
  ESRIの公表calendarは保存時点に知られた予定として表示する。価格snapshotなしでもマクロは閲覧可能。
  追加後のmemberテスト195件は成功。独立レビューの2件を追加修正し、行の単位・頻度・季節調整が異なる改定差を拒否する。
  最新1000件の一覧にない古いsnapshotはIDを明示して追加できる。未完了・未来・読取不能なIDは候補に入れない。
  修正後のmemberテスト197件は成功。
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

1. 工程3c/3dブランチをmainの最新へ追随させ、文書リンク・Ruff・pre-commit・対象suite、
   代表画面を再検証してmainへ統合する。Q09–Q13のfixtureと旧結果の差分を記録する。
2. 旧 stock / quantkit / market-viz / macrokit / autostock は、採用機能と旧入口の
   実行条件を個別に照合する。後継で置き換えない高度モデル、イントラデイ、
   税/NISA、AIチャット、API scaffoldは歴史的成果として復元方法を残す。
   退避時にworkspace設定・Makefile・CI・索引・Git外参照を更新する。
3. 認証がある環境でALFRED・e-Stat・SECの実通信を小範囲で確認する。
   Stooqのブラウザ検証とJ-Quantsの未検証は、初版の対応済み扱いにしない。
   長期のPIT履歴がないと過去の成績は再現できない。

制約: 日米株は自動カレンダーを使用し、それ以外の市場は確認済み時間表が必要。
保存データモードの戦略比較は実際に観測された複数の版を要する。
保存データの研究runはまだ永続保存しない。Mag7旧Parquetの過去PIT成績は不明。

## 既知の不具合と修正

- 取引時間中のスナップショットの不具合は修正済み（2026-09-27）。未確定足を保存でき、
  `price_view_as_of` は確定足と除外理由を返す。14:00 JST の当日足と前日確定足の混在、
  翌日も自動確定しないこと、後の確定revisionを選ぶことを含め47件成功。
- 二重lagの検出は `DataFrame.attrs["timing"]` に依存し、属性が消えると素通りする。
- `assess_bars` は直前の足と比べるため、一時的な1/10価格の翌日（元の水準へ戻った日）にも警告が付く。
