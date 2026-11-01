# Bank Salary status

更新日: 2026-10-31（Asia/Tokyo）

## 目標と完了条件

5社（2026-10-31 に BofA・Citi を追加）の NY 州を含む公式公開求人を収集し、勤務地別基本給の SQLite・CSV、再実行コード、探索用HTMLレポートを提供する。公式一覧と件数照合、全詳細の成功・失敗を確認し、給与原文と単位を検証する。取得経路の限界を隠さない。

## 現在

- 完了: 設計、収集・更新 CLI、給与解析、SQLite 観測履歴、CSV、独立監査、初回収集と原文からの再計算、インタラクティブHTMLレポート、部門・サブ部門・職種の独立分類と絞り込み。
- 実施中の処理: なし。コードと run 3（5社）のデータ・HTMLは引き渡し可能。
- BofA・Citi の追加（2026-10-31）: 収集・給与抽出・分類・HTMLを5社に拡張し、run 3 を取得（後述）。
- 追加成果: 全1,705求人・3分類のAI本文監査と別HTML/CSV。Opusの独立レビュー（[結果](2026-10-31-opus-classification-review.md)、[依頼](2026-10-31-opus-classification-review-handoff.md)）で、規則の誤り8件を分類 `2026-10-31.4` に反映して給与HTMLを再生成し、監査に第2調整層と訂正の5区分を追加した。訂正候補505求人のうち明確な誤分類を含むのは214求人。
- 監査の読了記録: `shared_full` 437件は全文通読ではなく、同一本文の参照238件と、既読求人との共通文を隠した差分表示199件。未読ではないが、監査HTMLの「完全一致共有」表記は実態に合わせて直した。
- 方針決定（2026-10-31）: Business Bankingは当面リテール、LOB内の管理機能はコーポレート、CDAO・AIチームはTechnology、ラベルは細かくしすぎず新ラベルは職種5・サブ部門4だけ（残りは既存ラベルか「その他」）。監査と分類 `2026-10-31.5` に反映し、監査の要判断は0。
- 未検証: GS Higher を含む全採用経路の網羅、MS Eightfold の表示総数の不整合（後述）。run 3 は Citi の詳細1件の失敗もあり `partial`。BofA・Citi の分類は監査していない。

## 初回データ（run 1）

取得期間: 2026-10-31 12:57:58–13:13:01 JST。求人詳細は全1,705件で成功、失敗0件。給与再計算後の件数:

| 会社 | 求人 | 給与取得 | 未記載または抽出不可 | 給与行 | 要確認の求人 | 期間未記載の行 |
|---|---:|---:|---:|---:|---:|---:|
| Morgan Stanley | 352 | 351 | 1 | 363 | 4 | 16 |
| Goldman Sachs | 184 | 163 | 21 | 164 | 2 | 162 |
| JPMorgan Chase | 1,169 | 1,169 | 0 | 1,789 | 2 | 1,789 |
| 合計 | 1,705 | 1,683 | 22 | 2,316 | 8 | 1,967 |

給与行の粒度は求人×原文の勤務地別・職位別レンジ。GS Campus の16行は基本給と明記されていないため `salary_unspecified`。期間は金額から推測しない。原文の誤った桁区切りや上下逆転など8求人は `review` で、訂正・補完していない。

## BofA・Citi の追加と run 3（2026-10-31）

- 判断: ユーザーが BofA と Citi の両方を対象に加えた。Citigroup の利用規約はデータのスクレイピングを含む無許可の利用を禁じており、収集の許可はユーザーが確認・取得する前提。Citi は robots.txt が許可する勤務地ページと求人ページだけを読み、同じホストへの間隔を1秒以上にした。
- 出典: BofA は公式キャリアサイトの全求人一覧（2,053件）から州略号付きの勤務地で NY を選び（194件）、詳細は Workday `Lateral-US` を求人番号の完全一致で読む。Citi は jobs.citi.com の NY 州の勤務地ページ（423件）と各求人ページの JSON-LD。学生向けの BofA 採用（tal.net）は対象外。
- run 2（19:14 JST 開始）は中断。BofA の一覧が `rows` を件数でなく終了位置として扱うため2ページ目が空になり（100件だけ）、Citi の勤務地ページの応答が途中で切れた（`IncompleteRead`）。ページ送りと再試行を回帰テスト付きで直し、BofA の一覧が2,053件そろうことを確かめてから run 3 を取り直した。run 2 は DB に `running` のまま残す（DB を書き換えない）。
- run 3（19:31:43–19:57:42 JST）の結果:

| 会社 | 求人 | 給与取得 | 未記載または抽出不可 | 詳細失敗 | 給与行 | 要確認の求人 | 期間未記載の行 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Morgan Stanley | 351 | 350 | 1 | 0 | 362 | 4 | 16 |
| Goldman Sachs | 184 | 163 | 21 | 0 | 164 | 2 | 162 |
| JPMorgan Chase | 1,169 | 1,169 | 0 | 0 | 1,789 | 2 | 1,789 |
| Bank of America | 194 | 194 | 0 | 0 | 194 | 0 | 0 |
| Citi | 423 | 411 | 11 | 1 | 411 | 0 | 411 |
| 合計 | 2,321 | 2,287 | 33 | 1 | 2,920 | 8 | 2,378 |

- 網羅性フラグは `partial`: MS 補助一覧（Eightfold）の総数1,227と一意なID数1,225の不一致（run 1 と同じ）と、Citi の詳細1件の失敗（JSON-LD の文字列内の制御文字で `json.loads` が失敗）。読み取りは `strict=False` に直し、同じページを読み直して取れることを確認した（`source_samples.json`）。Citi の9求人は Job Family Group の後ろに区切りがなく、保存した公開部門に次の欄（`Job Family: …`）が付いている。読み取りは直したが run 3 の保存値は変えず、分類規則はこの付加があっても照合する。
- BofA の給与は勤務地ごとに `annualized salary`（140行）か `hourly pay`（54行）が明記される。Citi は主勤務地の1レンジだけで期間の記載がない（411行すべて `unspecified`）。
- HTML（run 3）: 2,321求人。参考比較（年額明記または期間未記載・下限$20,000以上、NY、基本給、学生向け候補を除く）は1,931求人・1,944レンジ、うち期間仮定1,466行。中点の中央値は MS $150,000、GS $187,500、JPM $171,500、BofA $142,500、Citi $123,700。厳密年額は470求人・480行（BofA $142,500）、厳密時給は59行（MS $30.135、BofA $31.25）。職種構成を調整した給与差ではない。
- 分類 `2026-10-31.6`: BofA の LOB（Global Research & Institute、Global Operations、Enterprise Credit、The CFO Group、Chief People Organization、Corporate Audit 等）と Citi の Job Family Group（Consumer Sales、Private Client Coverage、Institutional Sales/Banking、Operations - … 等）の対応、実データで見つかった誤り（Treasury Product・Treasury Trading を社内財務、Risk Arbitrage をリスク管理、Consumer & Small Business を中小企業、Global Research 職の秘書をリサーチと判定）の修正、Financial Solutions Advisor・Client Associate・Credit Officer 等の職種。run 1 で変わったのは8項目（8求人）で、すべて監査の最終ラベルと一致する方向（`report-qa/v2026-10-31.6-reclassification.json`）。run 3 の未分類は部門203件・サブ部門1,026件・職種494件（BofA 0・70・25、Citi 57・164・87）。BofA・Citi の分類は監査していない。
- 学生向け候補に「卒業年度付きの Full Time Analyst/Associate」（Citi の新卒採用の書き方）を追加。run 1 の判定は変わらない。
- 監査: run 1 の監査は DB 全体のハッシュを照合するため、run 1 時点の `jobs.sqlite` を `classification-audit/frozen-run1/` に凍結して読む。監査記録の validate はエラー0、監査HTMLのChrome 33項目PASS。run 1 の CSV・検証記録・HTML・QA は `_data/bank-salary/archive/run1/`。
- 検証: Python 92件・Node 12件PASS、ruff check/format PASS。`collect.py audit --run-id 3` は2,320観測・2,920給与行でエラー0。給与HTMLのChrome 17項目PASS（5社の件数・中央値が独立したSQLite基準と一致、BofA・Citi の詳細画面と公式リンク、ライト/ダーク、390pxスマホ、オフライン）。BofA・Citi 各1件を公式詳細から取り直し、給与が一致（`source_samples.json`）。オフラインの再exportでCSV 2つがバイト一致（`delivery_checks.json`）。HTML生成の前後でDBのハッシュ `759cc844…de64` は不変。`du -sh _data/bank-salary` は101M（DB 27M、監査62M、run 1 の保存5.7M）。

## 検証証拠

この節と次の「HTMLレポート」は run 1（3社）時点の記録。run 3 は前の節にある。


- `PYTHONPATH=bank-salary python3 -m unittest discover -s bank-salary/tests -q`: 61 tests PASS（収集等39＋HTML生成2＋分類20）。
- `.venv/bin/ruff check bank-salary` と `ruff format --check bank-salary`: PASS。
- 独立コードレビュー後、固定給・賞与/AUMの混入・賞与のannualの誤帰属・null値による中断・同runの古い給与残留・存在しないrunのCSV破壊を回帰テストで修正。実データで見つかった$省略、K略記、職位別固定給、GS上下限フィールド、改行・空白区切りの複数勤務地にも対応。
- `collect.py audit --run-id 1`: 全1,705観測の内容・圧縮原本 SHA-256、給与原文と金額、SQLite整合性・外部キー、CSVの1,705求人・2,316給与行の金額・単位一致を確認、エラー0。
- 3社各1件を公式詳細から再取得し、給与の一致を確認（`source_samples.json`）。オフライン再exportのCSVは両方ともバイト一致（`delivery_checks.json`）。
- `du -sh _data/bank-salary`: **20M**。SQLite 18,362,368 bytes。収集中に観測した VmHWM は62,692 KiB（終了時の最終peakは計測していない）。200 MB未満の容量見積り内。

データは `_data/bank-salary/` の `jobs.sqlite`、`jobs.csv`、`salary_ranges.csv`、`validation.json`、`audit.json` と小さな検証記録。生成物は gitignored、コードの本番依存は0。

## HTMLレポート

- 成果物: `_data/bank-salary/report.html`（2,118,605 bytes、約2.1 MB）。ワークスペースのclaude-reportテンプレートに、1,705求人・2,316給与行と3分類・根拠を埋め込んだ単一HTML。
- ソース: `build_report.py`、`bank_salary/report.py`、`report/`。READMEに再生成手順を追加。既存の収集処理は変更していない。
- 機能: 会社・部門・サブ部門・職種・従来の大分類・職位語・募集区分・取得状態・キーワードで絞り込み。給与公開状況、期間記載状況、会社別箱ひげ図、ヒストグラム、職位語／部門／サブ部門／職種の切替ヒート表、原文dialog、公式求人リンク、選択CSV、ダーク表示、印刷。
- 初期表示は年額を仮定する参考比較。年額明記または期間未記載・下限$20,000以上、NY適用可能、基本給、学生向け候補を除外。1,443求人・1,456ユニークレンジ、うち期間仮定1,117行（76.7%）。厳密年額・厳密時給・期間未記載の原額へ切替でき、元の単位と仮定はCSVにも保持する。
- 独立SQL/Python基準とブラウザー値が一致。厳密年額（全募集区分）は341行331求人、MS中点中央値147,500・GS193,750・JPM該当なし。厳密時給5行5求人、MS中央値30.135。参考比較の中点中央値はMS150,000・GS187,500・JPM171,500で、職種構成調整後の実給与差とは扱わない。
- 検証: Node10テストPASS、Python全61テストPASS、ruff check/format PASS。入力DBへの出力上書きを拒否するガード（同一パス・symlink・hardlinkの回帰テスト）も保持。実DBの生成前後SHA-256は `dfa13ce2963f0e8507a0748afe743448cbf43e71a3d984d79973c146a1d1c457` で不変。
- Chromeで16項目のブラウザー検証、JavaScriptエラー0。検索、空選択、給与欠損、原文dialog、分類・根拠付きCSV、3フィルターの候補連動、切替ヒート表とセルからの絞り込み、ライト/ダーク、390pxスマホ、オフライン動作を確認。ユーザー指摘の技術職2件のTechnology表示、xVA Tradingのトレーダー表示も確認。図表を目視し、上段グラフの実文字サイズは14px。記録は `report-qa/{browser-checks,expected,build-checks,classification-checks,technology-reclassification,xva-reclassification}.json` と画面PNG。
- ローカルのセッション用プレビューは `http://127.0.0.1:8786/report.html`。自動起動や外部公開は設定していない。保存HTMLは単独で開ける。

### 部門・サブ部門・職種の追加

- 初期実装: `bank_salary/classification.py`、HTML生成への分類埋め込み、`report/` の連動フィルター・一覧3列・詳細の根拠・CSV・ヒート表切替、分類13テストとNode3テスト、ブラウザーQA、READMEの説明。既存の収集処理・本番依存・DBスキーマは変更していない。
- 部門は所属する機能・分野、サブ部門は部門内の担当領域、職種は役割として独立。支援先の商品より所属機能を優先する。技術職以外はタイトルと公開部門を優先し、不足時に限り本文の明示的な職務紹介や公開職務カテゴリを使う。公開区分のCIB/AWMしか分からない場合は横断分類を維持する。
- 分類版 `2026-10-31.5` の未分類は、全1,705求人に対し部門146件、サブ部門792件、職種382件（`2026-10-31.4` は167・959・428件）。正式な組織階層の復元や全求人の手動確認ではない。未分類を許し、根拠のない補完を避ける。根拠は詳細と選択CSVから確認できる。
- xVA Tradingの職種修正: MS `JR036102` の職種を未分類からトレーダーへ変更。Traderと一部のTrading表現だけに対応していた判定へ、xVA Tradingの役割を追加した。明示された開発・オペレーション・業務管理・リスク管理を優先し、全1,705件で分類が変わったのはこの1件だけ。変更は分類コード・回帰テスト1件・ブラウザーQA・説明文書に限定。差分は `report-qa/xva-reclassification.json`、画面は `report-qa/xva-correction.png`。給与集計と元DBは不変。
- 独立レビューの実例から、担当業界Softwareとエンジニア、AI製品とProduct/Program Manager、Researchの担当業種Paymentsと決済部門、Trader Assistantとトレーダー、Private Equityと上場株式運用の取り違えを回帰テストで修正。実DBの指摘8例を再確認し承認済み。未分類が増える精度優先の変更で、分類なしの既存給与集計値は一致する。
- 再監査は1,705観測・2,316給与行、エラー0。生成物一式の容量は `du -sh _data/bank-salary` で23M。

### Technology部門の誤分類修正

- 原因: v1の部門は支援先の金融業務を優先していたため、Equities/Tradingが技術職の所属より先に判定された。ユーザー指摘に従い所属機能優先へ訂正。Technical Lead/Engineering Lead/Java Dev、公開技術カテゴリ、文の開始にあるTechnology divisionの所属紹介を優先する。本文の連携先の言及や、運用チームに属するQuantitative DeveloperだけではTechnologyに移さない。
- 今回変更したソース: `classification.py`、`tests/test_classification.py`（6回帰テスト追加・既存期待値訂正）、`tests/test_report.py`、`report/template.html`、`report/check-browser.cjs`、READMEと本書。JavaScriptの給与計算、収集処理、元DBは変更していない。
- 全1,705求人を再分類し150件がTechnologyへ移動（旧マーケッツ13件、旧Technology部門不明29件等）。変更全件は `report-qa/technology-reclassification.json`。その場で150件すべてを手動確認したという意味ではない。
- ユーザー指摘のMS `PT-JR042997` はTechnology／電子取引システム、`PT-JR037125` はTechnology／株式・デリバティブ技術。同様の `PT-JR042136`（Java Dev）も修正。JPM `210779070`（運用チーム所属のQuantitative Developer）は資産運用／株式運用を維持。独立レビューでこの4実例を読み取り専用DBから再確認。
- 全Python60件・Node10件・Chrome15項目PASS、既存の会社別給与集計は基準値と一致、元DBハッシュ不変。保存HTMLとプレビューを更新し、求人詳細の修正画面を `report-qa/technology-correction.png` に保存。

### Opus独立レビューの反映（2026-10-31）

- 分類 `2026-10-31.4`: リテールの住宅ローンと支店の規則順、`auto` の単語境界、Tax Smart、Equity Zen、Asset Wealth Management、Private Client Advisor、IBのEnergy Technology、IBのMedia & Communicationsの8件。全1,705件で72項目（67求人）が変わり、65項目は監査の最終ラベルと一致、残り7項目も誤ったラベルを外す方向。回帰テスト16例を追加（v3では修正8例が落ちることを確認）。
- 監査: 原レビューと `adjudications.json` は変えず、`classification-audit/opus-review/` に第2調整層（上書き31件、別名12組）、訂正570項目の区分、指摘28件、`shared_full` の分析、点検範囲を保存。監査は分類 `2026-10-31.3` の凍結コピー（`classification-audit/frozen-v2026-10-31.3/`）に対して再生成する。変更前の出力は `opus-review/baseline-before-opus-review/`。
- 検証: Python 62件・Node 10件・給与HTMLのChrome 16項目・監査HTMLのChrome 33項目 PASS。会社別の給与件数・中央値は基準値と一致。元DBは読み取りのみ。

### F03 の読み直しと F12（2026-10-31）

- F03: AWM担当の既定メモのままの判断203求人・432項目を本文から読み直した。現行どおり397、未分類を具体化29、訂正5、情報不足のまま1。JPM Workplace Solutions 5件は MS at Work・GS Ayco と同じ 職域・退職給付 に揃えた。記録は `opus-review/reread-f03.jsonl`。
- 読み直しで見つかった誤り: P2 のリスク規則がポートフォリオ・クオンツのリスク分析3求人をコーポレートに移していた（監査と規則の両方で除外）。JPM:210796669 の職種はリサーチ→リスク管理。
- F12: 分類 `2026-10-31.5` で、技術サブ部門の “Asset & Wealth Management” を資産運用技術、Private Wealth・PWM・private bank を WM 技術にした。GS:163039 は監査がアプリケーション開発（本文が GSAM を示さない）で、規則と一致しない。
- 監査: 訂正候補566求人・674項目、明確な誤分類を含む210求人、方針による上書き523件、要判断0。未分類のまま確定したサブ部門は137→108。
- 分類 `2026-10-31.5`（最終版）と F03 後の監査の最終ラベルとの一致率: 部門70.9%→79.1%、サブ部門45.5%→56.0%、職種63.9%→68.2%（左は v4）。v4から変わった415項目のうち396項目は監査と一致する方向、外れたのは5項目。
- 検証: Python 66件・Node 10件・給与HTMLのChrome 16項目・監査HTMLのChrome 33項目 PASS。DB（`jobs.sqlite`）のハッシュは不変。

### 方針決定の反映（2026-10-31、分類 `2026-10-31.5`）

この節の数値は F03 前の時点。

- 規則: Business Bankingはリテール銀行、LOB内の財務・F&BM・Treasury・人事・リスク・広報・秘書はコーポレート、CDAO・Applied AI/ML・技術リスクはTechnology、Market Manager・BSOは支店業務、相続・ウェルスプランナーはFA。新しい職種ラベル5つ（デザイン・UX、投資プロダクトスペシャリスト、秘書・事務サポート、融資・信用審査、データ分析・データ管理）を追加。回帰テスト2件（25例、v4では16例が落ちる）を追加し、旧設計の期待値1件（Technology Risk）を更新。
- 監査の最終ラベルとの一致率: 部門71.0%→79.3%、サブ部門47.4%→58.0%、職種64.0%→68.3%。v4から変わった416項目のうち400項目は監査と一致する方向、外れたのは5項目。変更全件は `report-qa/v2026-10-31.5-reclassification.json`。
- 監査: 方針と語彙を `opus-review/adjudications-opus.json` の `vocabulary`・`policy_overrides`（530件）として追加。要判断0、訂正候補562求人、明確な誤分類を含む207求人。
- 検証: Python 64件・Node 10件・給与HTMLのChrome 16項目・監査HTMLのChrome 33項目 PASS。会社別の給与件数・中央値は基準値と一致。

## 判断と制限

- 全職種を含める。年／時の単位が原文になければ `unspecified` とし、補わない。
- コードは新規 `bank-salary/`、原本と生成データは `_data/bank-salary/`。新しい本番依存なし。
- GS Higher は調査時 HTTP 502。Oracle Lateral/Campus 内の完了と、全経路の網羅は区別する。
- MS補助一覧は総数と一意なID数が一致せず、完全性を確認できない。Workdayの後続ページは総件数を0で省略するため、先頭ページの実際の総件数を前後で確認する。再確認ではWorkday347件（初回348件）、既存データにないNY求人は見つからなかった。
- Eightfoldで境界の重なりを増やす再確認も行ったが件数は一致しなかったため、その方式は採用せず、不完全なソースとして記録する。追加探索はここで打ち切る。
- Citi は規約上データのスクレイピングを禁じており、収集はユーザーの許可を前提とする。robots.txt が禁じる `/search-jobs/` と Workday（`citi.wd5.myworkdayjobs.com`）は使わない。範囲（他地域・他の経路）を広げる前にユーザーに確認する。
- Citi の給与は主勤務地の1レンジだけで、他の勤務地の給与は分からない。BofA の学生向け採用（tal.net）は対象外。
- 作業は承認された新規ディレクトリに限定し、他プロジェクト、既存の変更、依存関係、コミットや公開操作を変更しない。

## 次回

分類の続き: レビューの指摘で残るのは、読み直しが必要な1件（GS:175379）と、現行も許容とした2件。通常の最新化は root で `python3 bank-salary/collect.py collect`（5社で約26分、Citi は1秒間隔）。BofA・Citi の分類を監査する場合は run 3 を対象にする。将来 Higher が復旧した場合はその公開一覧と比較する余地がある。GSの全経路の網羅やMS補助一覧の解消を、今回の完了済み成果と混同しない。
