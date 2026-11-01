# Bank Salary

Morgan Stanley / Goldman Sachs / JPMorgan Chase / Bank of America / Citi の公式求人から、勤務地に NY 州を含む求人と公開基本給レンジを収集するローカル CLI。Python 3.12 以上の標準ライブラリだけで動きます。

```bash
# WSL Ubuntu、workspace root で実行。依存のインストールは不要。
cd /home/kazumasa/projects
python3 bank-salary/collect.py collect
python3 bank-salary/collect.py validate
python3 bank-salary/collect.py export
python3 bank-salary/collect.py audit
PYTHONPATH=bank-salary python3 -m unittest discover -s bank-salary/tests -v
```

再び `collect` を実行すると、同じデータベースに新しい取得回を追加します。既存の観測は上書きせず、内容が同じなら原本を重複保存しません。自動実行のスケジュールや外部公開は設定しません。

## 出力

既定は `/home/kazumasa/projects/_data/bank-salary/`（gitignored）。`--output /absolute/path` で変更できます。

| ファイル | 内容 |
|---|---|
| `jobs.sqlite` | 求人、取得回、原文・圧縮した公式レスポンス・ハッシュ、給与レンジ、観測履歴 |
| `jobs.csv` | 最新の取得回に列挙した全求人。給与未記載・詳細失敗を含む |
| `salary_ranges.csv` | 1行 = 求人 × 原文で分かれた給与レンジ。勤務地別の記載を保持 |
| `validation.json` | 会社別の件数、給与記載、単位不明、各サイトとの件数照合、制限 |
| `audit.json` | 圧縮原本・内容のハッシュ、給与根拠、CSV と SQLite の一致の独立検証 |

初回（2026-10-31）は **1,705求人、給与レンジ2,316行**。給与が取れた求人は1,683件、給与未記載または抽出不可は22件。原文の誤記など8求人を `review` として残し、期間が明記されていない1,967行は `unspecified` です。全求人詳細の取得は成功していますが、後述の経路・件数不整合により取得 run の網羅性フラグは `partial` です。詳しくは [STATUS](docs/STATUS.md)。

BofA・Citi を加えた5社の取得（run 3、2026-10-31 19:31–19:57 JST）は **2,321求人、給与レンジ2,920行**。給与が取れた求人は2,287件（MS 350/351、GS 163/184、JPM 1,169/1,169、BofA 194/194、Citi 411/423）。期間が明記されていない行は2,378行で、Citi の411行はすべて `unspecified` です。Citi の1求人は JSON-LD の制御文字で詳細を読めず、取得失敗として残しています（読み取りは修正済みで、次回の取得から読めます）。MS 補助一覧の件数不整合とこの1件のため、網羅性フラグは `partial` です。run 2 は BofA 一覧のページ送りの誤りで中断し、DB に `running` のまま残しています。HTML は終了済みの最新 run（run 3）を使います。初回の CSV・検証記録・HTML は `_data/bank-salary/archive/run1/` に保存しています。

CSV は Excel で開ける UTF-8 BOM 付き。式として実行される可能性のある文字列には先頭に `'` を付けます。SQLite 内の原文は変更しません。`export --run-id N` は指定した取得回を再出力し、ネットワークには接続しません。

## 給与の読み方

- 金額は公開された基本給。賞与・コミッション・株式報酬を加えた総報酬ではありません。
- GS Campus の公開フィールド `Anaplan Salary Range Lower/Upper Limit` だけに記載された金額は、基本給と明記されていないため `pay_type=salary_unspecified` とします。`pay_type=base` と区別してください。
- 通貨は対象の米国求人における USD。`period` は原文に明記された `year` / `hour` / `month` / `week`、未記載なら `unspecified` です。金額だけで年俸や時給を断定せず、年換算もしません。
- JPM の `Base Pay/Salary` と GS の基本給欄には、給与の期間が書かれていない場合があります。比較時は `period` と `evidence`（根拠原文）を確認してください。
- BofA は `Pay Transparency details` の勤務地ごとに `annualized salary` か `hourly pay` を明記するので、`period` は `year` か `hour` になり、`region` はその勤務地の記載です。
- Citi は `Primary Location Full Time Salary Range` として主勤務地の1レンジだけを載せ、期間を書きません。`period` は `unspecified`、`region` は主勤務地です。他の勤務地の給与は分かりません。
- `region` が空欄なら、原文が給与の適用地域を明示していません。複数勤務地へ同じ給与が必ず適用されるとはみなしません。
- 1求人に複数地域の給与が書かれている場合、対象州以外の地域の記載も、原文の文脈とともに残します。
- `not_disclosed_or_unparsed` は給与記載がないか、現在の保守的な解析では抽出できなかった求人です。求人本文は SQLite の `observations.job_json` 内に残ります。`review` は原文の範囲の矛盾など、手動確認が必要な行です。
- `$` の省略・K の略記は米国求人の文脈で USD に正規化します。誤った桁区切り（例 `$30,0000`）や単語の誤配置は補正せず、原文と数字を残して `review` にします。
- 会社ごとの `job_level` は原文であり、同じ Vice President 等が各社で同じ職責・給与グレードという意味ではありません。

## 範囲と公式出典

- MS: [Workday External](https://ms.wd5.myworkdayjobs.com/External) の州フィルターを主に、[公式 Eightfold](https://morganstanley.eightfold.ai/careers) の公開一覧と照合・補完します。取得原本のどちらを採用したかは `source` で識別できます。
- GS: [Lateral](https://hdpc.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/LateralHiring/jobs) と [Campus](https://hdpc.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CampusHiring/jobs)。公開メタデータから有効な実サイト番号を読み、別名を API サイト番号に使いません。通常の [Higher](https://higher.gs.com/) は事前調査で HTTP 502 だったため、Higher 独自求人を含めた全経路の網羅は未検証です。
- JPM: [全社サイト](https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs)、Chase、Alumni の有効な公開一覧を照合・重複排除します。
- BofA: [公式キャリアサイト](https://careers.bankofamerica.com/en-us/job-search) の全求人一覧から、州略号付きの勤務地（主勤務地と追加勤務地）に NY を含む求人を選び、詳細は [Workday Lateral-US](https://ghr.wd1.myworkdayjobs.com/Lateral-US) で求人番号が完全一致する求人だけを読みます。Workday の勤務地は州のない都市名なので、対象の判定には使いません。学生向け採用は別システムで、対象外です。
- Citi: [jobs.citi.com](https://jobs.citi.com/) の NY 州の勤務地ページ（`/location/new-york-jobs/287/6252001-5128638/3/{page}`）と各求人ページの JSON-LD だけを読みます。robots.txt が禁止する `/search-jobs/` と Workday（`citi.wd5.myworkdayjobs.com`）は使いません。Citigroup の利用規約はデータのスクレイピングを含む無許可の利用を禁じていて、収集の許可はユーザーが確認・取得する前提です（2026-10-31）。同じホストへの間隔は1秒以上にしています。

NY 州の勤務地を選べる求人が対象で、主勤務地が他州でも含みます。インターン、支店・リテール業務、時給職も除外しません。終了した過去の求人の復元、応募者数や実際の内定条件の取得は行いません。

初回収集では MS Eightfold の表示総数と一意な求人 ID 数が一致しませんでした。Workday の全州フィルター結果と、Eightfold で確認できた NY 求人を重複排除して保存し、補助一覧の完全性は未確認として残します。追加の再確認は `source_recheck.json` にあります。

一覧は取得前後に再列挙します。件数・ID の変動、重複、一覧や詳細の失敗があれば `partial`（終了コード 2）、列挙した対象ソースの照合に成功すれば `complete`（終了コード 0）です。`complete` は記載したソース集合内の意味であり、採用経路すべてや給与記載率100%を保証しません。

不完全な取得や異なる対象設定の回から、求人が募集終了したとは推測しません。`Store.presence()` は、完全な同じ対象設定の一覧から外れた場合だけ `not_listed_in_complete_scan` を返します。これは採用終了の確定や実際の終了日ではありません。

給与抽出ロジックを変更した後は `python3 bank-salary/collect.py reparse --run-id N` で取得済み原本から給与行を再計算できます。ネットワークへ接続せず、求人観測・原本・ハッシュを保持し、派生する給与行を更新します。同じ観測を参照する過去 run の給与行も更新されます。実行日時と抽出器の SHA-256 を `report_json.derivations` に記録します。これは求人情報を最新に取得する操作ではなく、最新化には `collect` を使います。

`raw_zlib` は公開レスポンスの JSON をキー順固定でシリアライズして圧縮したものです。`raw_sha256` はその展開後 JSON バイト列の SHA-256 で、HTTP ヘッダーや転送時の空白まで保存するものではありません。

## 地域・負荷を変更する場合

`--state-name` は Workday の州名、`--state-code` は Eightfold と BofA の州略号、`--gs-location-id` と `--jpm-location-id` はそれぞれの Oracle の州 Geography ID です。別地域ではすべてを対応する値に変更してください。会社間で ID を使い回せません。`--ms-location` は補助的な Eightfold 地域検索（既定は全一覧から州で抽出）です。Citi の勤務地ページはコードの `CitiSource.location_path` に固定しているので、別地域ではそこも変えてください。

既定は同時取得3件・同一ホストの最小間隔0.35秒（jobs.citi.com は1秒）、最大3回再試行、タイムアウト30秒。`--workers` と `--delay` で変更できます。認証・アクセス制限の回避や応募処理はありません。大規模化する場合は、workspace の容量見積りルールに従ってください。

## 保存データの例

```sql
-- 取得回ごとの会社・求人を、当時の観測に結びつける
SELECT j.company, j.requisition_id, r.checked_at,
       s.minimum, s.maximum, s.currency, s.period, s.region, s.evidence
FROM run_jobs r JOIN jobs j ON j.id=r.job_id
JOIN salary_ranges s ON s.observation_id=r.observation_id
WHERE r.run_id=(SELECT MAX(id) FROM runs);
```

本収集前の概算は2,000求人 × 30 KBで約60 MB、SQLiteとCSVを含め200 MB未満、メモリ300 MB未満。実際の検証結果と容量は [STATUS](docs/STATUS.md) を参照してください。

## インタラクティブHTMLレポート

```bash
cd /home/kazumasa/projects
python3 bank-salary/build_report.py
node --test bank-salary/report/report.test.cjs
```

出力は `_data/bank-salary/report.html`。単一HTMLにデータ・JavaScript・CSSを内蔵し、ファイルをブラウザーで開くとオフラインでも絞り込みとCSV出力を利用できます。表示フォントだけはGoogle Fontsを任意に使用し、オフライン時にはOSフォントへ切り替わります。

会社・部門・サブ部門・職種・職位語・募集区分・キーワード等で絞り込み、会社別の箱ひげ図、中点の分布、分類を切り替えられるヒート表、給与原文付きの求人一覧を表示します。部門を選ぶとサブ部門、その下で職種の候補が連動します。従来の粗いタイトル分類も「大分類」として残しています。

部門は投資銀行・マーケッツ・Technology等、サブ部門は各部門内の担当領域、職種は営業・トレーダー・エンジニア等を独立して付けます。例: `Equity Trading Software Engineer` → `Technology / 株式・デリバティブ技術 / エンジニア・開発`。`bank_salary/classification.py` は支援先の商品より所属機能を優先し、明示されたTechnology division、技術職・技術職カテゴリをTechnologyへ分類します。Technical Lead・Engineering Lead・Java Devにも対応。担当業種のTechnology、連携先の技術チーム、運用チームに属するQuantitative Developerは単語だけでTechnologyへ移しません。技術職以外はタイトル・公開部門を優先し、不足時に本文の明示的な職務紹介や公開職務カテゴリを参照します。CIB・AWMの広い区分しか分からない場合は横断分類、根拠不足は未分類とします。

これは分析用のルール分類で、正式な組織階層や全求人の手動確認を意味しません。初回1,705求人の未分類は部門146件、サブ部門792件、職種382件（分類版 `2026-10-31.5`）。`2026-10-31.4` は単語の誤一致・規則順の誤り8件の修正、`2026-10-31.5` は2026-10-31に決めた分類方針（Business Bankingはリテール、LOB内の財務・人事・リスク・広報・秘書はコーポレート、CDAO・AIチームはTechnology、新しい職種ラベル5つ）と、AWM技術職のサブ部門（F12）の反映。`2026-10-31.6` は BofA の LOB と Citi の Job Family Group の対応と、5社のデータで見つかった誤り（Treasury Product・Treasury Trading を社内財務、Risk Arbitrage をリスク管理と誤認など）の修正。run 1 で変わったのは8項目で、すべて監査の最終ラベルと一致する方向です。run 3 の2,321求人の未分類は部門203件、サブ部門1,026件、職種494件で、BofA・Citi の分類は監査していません。変更と監査の最終ラベルとの照合は `report-qa/v2026-10-31.4-reclassification.json`・`v2026-10-31.5-reclassification.json`・`v2026-10-31.6-reclassification.json`。監査と方針判断の論点は [Opusレビュー](docs/2026-10-31-opus-classification-review.md)。Technologyは150件で、従来マーケッツだった13件を含みます。変更全件と判定根拠は `report-qa/technology-reclassification.json` に保持。xVA Tradingは明示された他の担当職種がない場合、マーケッツのトレーダーと判定します。3分類・判定に使った情報の種類・根拠原文は詳細画面と選択CSVに含まれます。公開部門の原文も保持し、SQLiteや元の求人CSVは変更しません。職位語・学生向け候補も各社共通の公式分類ではありません。

初期表示は、基本給の「年額明記」または「期間未記載で下限$20,000以上」を年額候補と仮定する参考比較です。仮定の割合を画面に明示し、判定基準も変更できます。「年額明記のみ」「時給明記のみ」「期間未記載の原額」に切り替え可能。原文の給与期間は変更せず、CSVにも仮定の有無を残します。原文要確認の行は統計から除外し、詳細で確認できます。

データは最新の終了済みrunから読み取り専用で取得します。`--run-id N`、`--database /path/jobs.sqlite`、`--output /path/report.html` を指定可能。入力DBと同一ファイル・シンボリックリンク・ハードリンクへの出力は拒否します。既存のデータ収集を再実行した後は、このコマンドでHTMLも再生成してください。

レポートのソースは `bank_salary/report.py`、`bank_salary/classification.py` と `report/`。ワークスペース指定の `docs/templates/claude-report/` の全文CSSを埋め込みます。ブラウザーQAはホストに用意されたPlaywrightを使い、プロジェクト依存は追加していません。検証記録・画面キャプチャは `_data/bank-salary/report-qa/`（run 1 の分は `archive/run1/report-qa/`）にあります。
