# Opusへの求人分類監査レビュー引き継ぎ

更新日: 2026-10-31（Asia/Tokyo）

## 依頼すること

MS・GS・JPMの保存済み全1,705求人について作成した「部門・サブ部門・職種」の監査を、求人本文に戻って独立に検証してください。主目的は分類の意味的な妥当性です。引用が原文に存在することや検証コードの成功だけで、分類を承認しないでください。

**レビューだけを行い、収集・分類コード、DB、既存HTML、既存の監査記録を変更しないでください。** 新しいレビュー結果と必要な小さな検証記録だけを別ファイルへ保存してください。今回の依頼は、修正実装・再収集・公開ではありません。

とくに以下を確認してください。

1. 本文を読んだという監査記録の十分性。下記の `shared_full` フラグの問題を優先する。
2. 現行分類と監査提案の双方の妥当性。`confirm`、`correct`、`resolve` も誤っている可能性がある。
3. 明確な誤分類と、許容できる粗い分類を細分化するだけの変更の区別。
4. 未分類・要判断を残した根拠と、同じ仕事に異なるラベル・確信度を付けていないか。

対象全体は1,705求人・5,115項目です。意味の再確認も全件を対象とし、途中で区切る場合は、実読したID・範囲・未確認範囲を記録してください。限定的なサンプル確認を全件の独立再監査として報告しないでください。

## 最初に確認する問題

### 本文共有フラグが全文一致の証明になっていない

この引き継ぎ作成時の追加照合で、統合記録の `body_review="shared_full"` **437求人のうち199求人は、他の求人と正規化本文全体のSHA-256が一致しない**ことを確認しました。

| 原レビュー | shared_fullだが本文ハッシュが単独の求人 |
|---|---:|
| `ms_part3_reviews.jsonl` | 76 |
| `ms_part4_reviews.jsonl` | 107 |
| `jpm_institutional_part4_reviews.jsonl` | 16 |
| 合計 | 199 |

例は `MS:PT-JR037125`、`JPM:210798422`。監査中の説明とhelperからは、既読の完全一致段落・文を参照して新しい差分を読む方式が、本文全体の共有と同じフラグに入った可能性があります。関連helperは `ms3_helper.py`、`ms4_helper.py`、`inst4_helper.py` です。

**この199件が未読だと確定したわけではありません。一方、437件を「本文全体が同じなので共有した件数」と読むことはできません。** 参照置換の条件、新規文章が省略されないこと、実際の意味判断の根拠を再確認してください。現行監査HTMLの「完全一致共有」という説明と、フラグの定義・検証には見直す余地があります。既存成果物はこの発見後も変更せず残しています。

### 訂正候補の件数は確定的な誤分類数ではない

集計上は510求人が `correct` を含みます。ただし、たとえば「資産運用・WM（横断）→資産運用」が、誤分類の訂正なのか、本文からの具体化なのかは再検討が必要です。許容できる上位分類を誤りと数えていないかを重点的に確認してください。現行の件数を承認すべき目標値にしないでください。

## 作業場所と読む順序

- WSL repository: `/home/kazumasa/projects`
- Windows: `//wsl.localhost/Ubuntu/home/kazumasa/projects`
- 実装: `bank-salary/`
- 原本・既存の給与出力: `_data/bank-salary/`
- 今回の監査成果物: `_data/bank-salary/classification-audit/`

repository rootの `AGENTS.md`、[README](../README.md)、[STATUS](STATUS.md) を確認してください。Git・Python等の実行はWSLのrepository rootから行い、他プロジェクトを走査しないでください。`_data/` はgitignoredなので、リポジトリだけを別環境へcloneしても原本・監査記録は取得できません。

最初に以下を読んでください。

| ファイル | 内容 |
|---|---|
| 本書 | 今回依頼・保護対象・追加発見・レビュー観点 |
| `_data/bank-salary/classification-audit/README.txt` | 成果物と再生成の説明 |
| `audit-summary.json` | 集計、入力・原レビューのハッシュ、取得時点 |
| `audit-decisions.jsonl` | **調整後の統合判定**。レビューの主対象 |
| `adjudications.json` | 異名の統一・個別再判定。原レビューとの差分 |
| `consistency_review.json` | 先行する限定QA。35求人・30本文の実読であり全件の二重監査ではない |

表の省略パスはすべて `_data/bank-salary/classification-audit/` 配下です。

### 閲覧用成果物

- [監査HTML](../../_data/bank-salary/classification-audit/report.html): 現行・提案・判定・理由・引用・全文の検索。
- [全件CSV](../../_data/bank-salary/classification-audit/audit.csv): 1求人1行、各分類の新旧・状態・根拠。
- [統合JSONL](../../_data/bank-salary/classification-audit/audit-decisions.jsonl): 原レビュー名、原提案、出典ハッシュ、個別調整理由を含む。
- プレビュー: `http://127.0.0.1:8786/classification-audit/report.html`
- 従来の給与HTML: `_data/bank-salary/report.html`、同ポートの `/report.html`。

プレビューサーバーが止まっていても保存HTMLは単体で開けます。監査HTMLは約10.6 MBです。引用・全文は保存済みの入力から埋め込んでいます。リンク先の現在の求人と保存本文が異なる場合、今回の判定対象は保存時点の本文です。

## 背景とユーザーが指定した分類意図

当初の依頼は、NYで給与レンジが公開されるMS・GS・JPMの求人を収集し、更新可能な収集コードと分析用HTMLを作ることでした。承認した収集範囲はNY州を勤務地に含む公式公開求人で、全職種・複数勤務地・インターン等を含みます。今回のレビューで地域や収集範囲を広げる必要はありません。

部門・サブ部門・職種の追加後、ユーザーが次を指摘しました。

- Electronic Trading PlatformのTechnical Lead、Equities Derivatives TechnologyのEngineering Leadは、支援先商品が株式・デリバティブでも **Technology部門**。
- `xVA Trading - Fixed Income Division - Associate or Vice President` は **トレーダー**。
- その他の誤分類と未分類も含め、全求人を本文まで見てチェックする。

前2点を反映した現行分類コードは `2026-10-31.3`。その後の全件AI監査の提案は、分類コード・従来給与HTMLへまだ反映していません。SQLiteにも監査提案の分類列を追加していません。

分類は分析用で、正式な組織図を復元したものではありません。支援先の商品、顧客業種、経験要件、ツール、連携先組織と、本人の所属・主務を区別する必要があります。

## 入力の範囲と監査の実施記録

- run 1、取得期間 **2026-10-31 12:57:58–13:13:01 JST**。
- MS352、GS184、JPM1,169、合計1,705求人ID。最新サイトを再収集した監査ではありません。
- 通常の `description` が非空: 1,689求人、本文ハッシュは1,464種類。
- GS Campus16求人は正規化本文が空。ただし保存 `raw_zlib` の `OrganizationDescriptionStr` / `CorporateDescriptionStr` に説明が残っており、`gs_raw_evidence.jsonl` に回復した原文と原本ハッシュがあります。企業・採用プログラム一般の記述だけで、個別の担当を断定していないかも確認してください。
- 原レビューの読了フラグは `full=1,252`、`shared_full=437`、`missing=16`。16件は別途 `raw_body_review=full`。これらは求人行の記録上のフラグで、独立した本文実読回数や人的査読の証明ではありません。共有フラグの問題は本書冒頭参照。
- 複数のAI担当で本文・タイトル・公開分類を確認し、完全一致本文や既読の一致文を共有しました。人間による全件査読ではありません。

取得run自体は `partial`。GS Higher独自求人の列挙、MS補助一覧の完全性は未確認です。「全件」はこの保存済み1,705求人の全件を指し、全採用経路の網羅を意味しません。

## 現在の判定と集計

| 状態 | 意味 |
|---|---|
| `confirm` | 現行分類と本文・公開分類が整合すると判断 |
| `correct` | 現行分類に明確な不整合があると判断した訂正候補 |
| `resolve` | 現行の未分類を具体化する候補 |
| `ambiguous` | 組織・機能・粒度・原文矛盾等で判断を保留 |
| `insufficient` | 根拠不足等で未分類を維持 |

以下は**個別調整後**の `audit-decisions.jsonl` の集計です。原レビューだけを集計すると一致しません。

| 分類 | confirm | correct | resolve | ambiguous | insufficient | 合計 |
|---|---:|---:|---:|---:|---:|---:|
| 部門 | 1,189 | 261 | 151 | 102 | 2 | 1,705 |
| サブ部門 | 647 | 77 | 746 | 50 | 185 | 1,705 |
| 職種 | 993 | 241 | 390 | 74 | 7 | 1,705 |
| 合計 | 2,829 | 579 | 1,287 | 226 | 194 | 5,115 |

求人単位ではcorrect510、resolve949、ambiguous191、insufficient187。3項目のどれかが該当すれば数えるため、求人件数は重複します。

現行の未分類は部門167・サブ部門954・職種428。ambiguousを採用せずその他の提案を採用する試算では16・209・38です。これは未反映の試算で、現行レポートの値ではありません。誤ったサブ部門を未分類へ戻した1項目（`MS:PT-JR035408`）も含みます。

### 判定データの構造

各JSONL行に `id`、`title`、`company`、`public_department`、`public_category`、`url`、`body_sha256`、`raw_sha256`、`body_review`、`review_file` などがあります。3分類はそれぞれ独立したobjectです。

```json
{
  "department": {
    "current": "現行ラベル",
    "proposed": "統合後の提案",
    "status": "correct",
    "evidence": [{"source": "description", "quote": "原文の連続した引用"}],
    "note": "日本語の理由",
    "reviewer_proposed": "元担当の提案"
  }
}
```

`source` は `description`、`title`、`public_department`、`public_category`、GS回復原文フィールド等。`adjudication_reason` があれば統合時の個別調整です。`body_id` は監査HTML内の本文辞書を引くキーであり、GS回復本文では正規化本文ハッシュとは異なります。原本の `raw_sha256` は展開後のキー順固定JSONのハッシュで、HTTP転送バイト列のハッシュではありません。

## 意味判断で重点的に確認する例

| 求人ID | 確認する点 |
|---|---|
| `MS:PT-JR042997`、`MS:PT-JR037125` | ユーザー指定のTechnology優先。後者は共有フラグ追加確認の対象でもある |
| `MS:JR036102` | xVAの主務は価格付け・ヘッジ・トレーディングブック。前回修正済みのトレーダーを確認 |
| `JPM:210779070` | AM運用研究チーム側のQuant Developer。開発という語だけでTechnologyへ移さない例 |
| `JPM:210777333` | Paid Social Automationを自動車金融とした部分一致の誤り |
| `JPM:210709230` | Private Wealth Planner。公開Product Developmentでも顧客の包括的資産計画が主務 |
| `JPM:210760883` | Quant Analyticsの肩書と、カードの顧客・キャンペーン分析／BIという主務の区別 |
| `JPM:210781060` | Tax Smart投資商品の提案と、税務職の区別 |
| `JPM:210797711` | IPB Associate Bankerとリテール支店Bankerの区別 |
| `GS:176910`、`GS:177899`、`GS:178011`、`GS:179861` | Client Portfolio Managerの投資商品説明・提案と、実際の運用判断の区別 |
| `JPM:210804583` | Branch Operations Leadというtitle/categoryに対し、本文がAssociate Banker。原文の矛盾を維持 |
| `MS:JR036489`、`MS:JR045751` | 同一title・本文の職種提案が分かれ、統合時に両方ambiguousへ戻した |
| `MS:PT-JR035089`、`MS:PT-JR043306` | 同一本文のWM営業網支援。前者のサブ部門変更を取り消して支店に統一した |
| `JPM:210783355`、`JPM:210792604`、`JPM:210803400`、`JPM:210803461` | PricingDirectの独立証券評価。職種の異名を統一し、Marketsへの所属分類は要判断 |
| `JPM:210794763`、`JPM:210804332` | 同一title・本文の産業サブ部門の異名を個別統一した |
| `MS:JR038727` | 本文が非空でも実際の職務内容が不足する例 |
| `MS:PT-JR035408` | EquityZen UX職。株式部を取り消したがサブ部門未分類。根拠不足か体系未整備かを再確認 |

あわせて、LOB内のFinance/HR、独立Risk、AI導入戦略とAIモデル研究、Product/Program Manager、研修・秘書、営業支援、支店勤務の住宅ローン専門職を横断して確認してください。未分類を減らすために根拠のない正式部署名を作らないでください。

既存限定QAでは、信用商品の分析と融資組成、信託受託業務と相続税務計画と投資取引助言、施設警備と身辺警護は、一括で同義語にしない判断をしています。これも結論を追認せず本文で確かめてください。

## 検証済みのことと検証の限界

- 原レビューの求人ID漏れ・重複なし。統合CSVは1,705求人、3分類計5,115判断。
- 統合後の全引用を保存原文に対して大文字小文字・空白を変更せず照合し、不一致0。記録は `qa/data-checks.json`。
- 元DB・分類コード・従来給与HTMLのハッシュ不変。
- 監査HTMLのChrome検証30項目PASS、JavaScriptエラー0。会社・状態・分類対象・検索・ページング・CSV・根拠全文・回復原文を確認。PC明暗・390px表示を目視。記録は `qa/browser-checks.json` とPNG。
- 既存実装のPython61件・Node10件等の合格は前段の実装時点の記録であり、今回の意味的な監査の正しさを証明するものではない。

`review.py validate` はフラグが所定の値であるかは検査しますが、shared_fullが他の全文と一致するか、担当が新規差分をすべて読んだかは証明しません。引用が存在するだけでも、それが本人の主務・所属を示すとは限りません。

## 読み取り中心の確認手順

原本SQLはread-only接続で使用してください。正規化本文は `observations.job_json`、圧縮公式レスポンスは `observations.raw_zlib`、runとの対応は `run_jobs` にあります。既存 `review.py` の `jobs()` で、同じrunの求人・公開情報・本文・ハッシュを参照できます。

以下は出力を表示するだけの初期照合例です。

```bash
cd /home/kazumasa/projects
python3 - <<'PY'
import collections, csv, json, sys
from pathlib import Path
sys.path.insert(0, '_data/bank-salary/classification-audit')
from review import jobs

base = Path('_data/bank-salary/classification-audit')
source = {j['id']: j for j in jobs()}
records = [json.loads(s) for s in (base / 'audit-decisions.jsonl').read_text().splitlines() if s]
assert len(records) == len({r['id'] for r in records}) == len(source) == 1705
assert {r['id'] for r in records} == set(source)
with (base / 'audit.csv').open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
assert len(rows) == 1705 and {r['id'] for r in rows} == set(source)
for d in ('department', 'subdepartment', 'occupation'):
    print(d, dict(collections.Counter(r[d]['status'] for r in records)))
body_counts = collections.Counter(j['body_sha256'] for j in source.values() if j['description'])
singletons = [r for r in records if r['body_review'] == 'shared_full' and body_counts[r['body_sha256']] == 1]
print('shared_full with unique full-body hash', len(singletons))
print('by review file', dict(collections.Counter(r['review_file'] for r in singletons)))
PY
```

`review.py show --owner ... --offset ... --limit ...` は本文を読むためのコマンドです。出力が切れたら件数を減らして再読してください。ownerは `ms`、`gs_awm`、`jpm_institutional`、`jpm_consumer`。ownerと会社名は一致しない場合があるので、ID一覧を先に確認してください。

**最初に `build_audit.py` を実行しないでください。** 同じ場所の監査HTML・CSV・統合JSONL・summaryを上書きします。`review.py validate` も `coverage.json` を更新します。レビュー中の再計算は別出力にし、既存helperやbatchを一括実行しないでください。

### 引き継ぎ時点のハッシュ

```text
_data/bank-salary/jobs.sqlite
dfa13ce2963f0e8507a0748afe743448cbf43e71a3d984d79973c146a1d1c457

_data/bank-salary/report.html
3b14a7645b1c5720ed975f84eb10127e24722abf466be68435a64af39d96c3b5

bank-salary/bank_salary/classification.py
4d60f4fc5311233e99cd432684bdd66a2be66b085dce3387f7e28febea7c7cf3

_data/bank-salary/classification-audit/report.html
c7b827205f863b6b3d18378e0d41a0f401038bb20fb5d5374407d471e2637674

_data/bank-salary/classification-audit/audit-decisions.jsonl
28daa15b0e1ff4d41197d5b9b12a31ec0c0de33125471f31e09a642bf93b409d

_data/bank-salary/classification-audit/audit.csv
00c630ca2ac9178b7b9c3474af50fb9ff04b0fa054fe44383a91197dd1b02705
```

## 期待するレビュー結果

プロジェクトの `docs/` に日本語のレビュー要約、必要なら `_data/bank-salary/classification-audit/opus-review/` にID単位の詳細を、新規ファイルとして保存してください。

1. 重要度順の指摘。各指摘に求人ID・分類軸・現行値・監査提案・Opusの推奨・原文引用・理由を付ける。
2. 「誤分類」「許容できる現行」「具体化・粒度の選択」「根拠不足・原文矛盾」を分けた判断。
3. 対象全件の機械照合件数と、実際に本文を再読した求人ID・件数・未確認範囲。
4. shared_full199件の扱い、本文参照共有方式、全件読了という前回説明をどこまで支持できるか。
5. 監査件数の修正案と、将来の分類ルールへ反映できる項目・方針判断が必要な項目。

誤りが見つかった場合も、元の監査提案を上書きせず、反証と代案を示してください。実装はユーザーの別の依頼を待ってください。
