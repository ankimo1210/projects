# D1-preflight 実装計画（johnhull）

- 作成: 2026-09-27。**計画のみ**。コード・設定・既存の証跡・台帳・保管庫フォルダーはどれも変更していない。
- 対象: `main` `7c4bb109` 時点の johnhull（M14 まで受入、台帳は accepted 14・unreviewed 292）。
- 正本: [D1 方針](../../EVIDENCE_POLICY.md)、[ADR 0004](../../../../docs/decisions/0004-artifact-storage-and-evidence.md)、
  [ROADMAP](../../../ROADMAP.md)、[台帳規約](../../SECTION_LEDGER_GUIDE.md)、
  [整理計画 工程5](../../../../docs/superpowers/plans/2026-09-27-workspace-cleanup.md)。
- 数値は下記コマンドの実測値。パスは特記なしで `johnhull/` からの相対パス。

## 0. 要約

既存証跡のファイル内容は約108 MB、内容が異なる blob は約26 MBで、約82 MBは画像の重複だった。
新しい再検査では「対象節の依存が変わったか」と「証跡の実体を復元・照合できるか」を別々に判定する。
不変なら直接の基準画像参照を残し、影響あり・未知なら再描画する。数値・意味・release の検査は毎回維持する。

**2026-09-27 本人判断：** ワークスペース全体の移行を待たず、johnhull に必要な保管庫と作業分離が整えば実装を再開する。
本書は手順の準備であり、保管庫の作成・2コピーの検証・D1-preflight の PASS はまだない。
次の5段階を完了してから M15（§27.6）へ戻る。既存の受入14件はこの計画では変更しない。

## 1. 現状の棚卸し（実測）

### 1.1 計測コマンド

引き継いだ調査は `/home/kazumasa/projects` から読み取りのみで実行したもの。2026-09-27 に付録 A の小集計でファイル数・バイト・重複総量を再確認した。
系列・参照到達性の内訳は先行調査の記録で、この追記時には再計測していない。

```bash
du -sb johnhull/docs/validation                           # 108213461
find johnhull/docs/validation -type f | wc -l               # 1832
git ls-files johnhull/docs/validation | wc -l               # 1832（全件 Git 追跡。未追跡・ignore は 0）
find johnhull/docs/validation -type f | sed -E 's/.*\.//' | sort | uniq -c   # png 1554 / json 269 / md 9
for d in johnhull/docs/validation/*/; do printf '%s\t%s\t%s\n' "$d" \
  "$(find "$d" -type f | wc -l)" "$(find "$d" -type f -printf '%s\n' | awk '{s+=$1} END{print s+0}')"; done
python3 evidence_stats.py johnhull/docs/validation         # 付録 A（SHA-256・重複総量の独立再確認）
grep -rlE 'docs/validation|artifact_sha256|source_sha256|recheck|\.png' johnhull \
  --include='*.py' --include='*.cjs' | grep -v _build      # 1.3 の一覧
.venv/bin/python johnhull/scripts/verify_section_ledger.py                   # status: PASS
.venv/bin/python johnhull/scripts/verify_section_ledger.py --check-artifacts # status: PASS
```

### 1.2 証跡の作られ方（現行）

**新しい節の受入（例: M14 §27.5）**

1. `scripts/build_<topic>_reference.py` → `docs/validation/section-XX/reference.json`（独立参照値）。
2. `scripts/verify_<topic>_numerics.py` → `numerical-check.json`（`source_sha256` と reference の digest）。
3. `scripts/verify_<topic>_notebook.py` → `notebook-check.json`（基点 commit との比較、負の対照、`verify_core_notebooks.check_committed_outputs` による fresh 実行）。
4. `scripts/verify_<topic>_browser.cjs`（Playwright + Chromium）→ Book と portal を 1440/1000 幅で開き、
   図の数値を DOM から照合し、図要素のスクリーンショットを `docs/validation/section-XX/{book,portal}-<figure>-<width>.png` に書く（新しい節は 16 枚。§26.9–§26.16 は式・例題の範囲切り出しも）。
   `browser-check.json` に `browser_version`・`pages`・`source_sha256`・`artifact_sha256`（HTML 2 本と PNG）。
5. `scripts/build_<topic>_acceptance_record.py` → `mNN-check.json`。1–4 と既受入節の再検査記録を集約し、HTML 4 本と自節 PNG 16 枚の SHA-256 を持つ。
6. `scripts/update_<topic>_ledger.py` → `docs/section_ledger.json`。新節の evidence を登録し、既受入節の record 参照を最新の再検査記録へ差し替える。
   その後 `verify_section_ledger.py --write-summary` で `docs/SECTION_LEDGER.md` を再生成。

**マイルストーンごとの既受入節の再検査（M7 以降は全受入節の全画像を撮り直し）**

- `scripts/recheck_accepted_mNN.py`: 節ごとの pytest、`lesson-data.json`/`reference.json` が基点 commit とバイト一致か、
  `source_sha256`（節テスト＋共有ソース＋前回 record のキー）、`artifact_sha256`（HTML 4 本）→ `section-XX/mNN-recheck.json`。
- `scripts/recheck_accepted_mNN.cjs`: 各節の元の verifier をロード時に文字列置換
  （`.png`→`-mNN-recheck.png`、`browser-*-check.json`→`browser-mNN-recheck.json`、§27.2–§27.4 は後続見出しの番号）し、
  `fs.writeFileSync` をフックして `recheck` メタと新 PNG の `artifact_sha256` を記録へ追記する。
- 再検査スクリプトはマイルストーンごとに複製している（m13→m14 の差分は節 1 行・基点 commit・record 名だけ）。
- `scripts/verify_accepted_vol06_notebook.py --check`（HEAD 常設）: vol06 の `## N. ` 見出しで切った節スライスを
  各受入 commit と比較（ソースと `_output_signature`）、保存図と `_figures()` の一致、notebook 全体の fresh 実行。

### 1.3 スクリーンショットのパスや証跡ハッシュを読み書きするファイル

`grep` の一致から paper corpus（`scripts/paper_corpus/*`、`tests/paper_corpus/*`、`build_paper_corpus.py`。
`source_sha256` という語を別の意味で使う）を除いた一覧。

| 区分 | ファイル | 読み書きするもの |
|---|---|---|
| 台帳検査 | `scripts/verify_section_ledger.py` | evidence の `path`/`sha256`、record の `status`・`source_sha256`・（`--check-artifacts` 時）`artifact_sha256` |
| 台帳データ | `docs/section_ledger.json`（267,756 B）、`docs/section_inventory.json`、`docs/SECTION_LEDGER.md`（生成物） | 306 項目、accepted 14 節の evidence 276 パス・record 31 本 |
| 台帳テスト | `report/tests/test_section_ledger.py` | fixture（png・record・artifact）と実台帳（件数 14/292、各節の要求 ID） |
| 台帳更新 | `scripts/update_{static_replication,alternative_models,stochastic_volatility,local_volatility,convertible_bond,path_dependent}_ledger.py`（6） | evidence 登録、record 参照の差し替え、PNG パスの直書き |
| 受入記録 | `scripts/build_{同じ 6 題材}_acceptance_record.py`（6） | `mNN-check.json`。PNG を `artifact_sha256` に列挙 |
| ブラウザ検証 | `scripts/verify_{barrier_pilot,binary_lesson,lookback_lesson,shout_lesson,asian_lesson,exchange_lesson,basket_lesson,variance_swap_lesson,static_replication,alternative_models,stochastic_volatility,local_volatility,convertible_bond,path_dependent}_browser.cjs`（14） | PNG の書き出し、browser record |
| 再検査 | `scripts/recheck_exotics_m7.cjs`、`recheck_exotics_m{8,9,10}.{py,cjs}`、`recheck_accepted_m{11..14}.{py,cjs}`（15） | `mNN-recheck.json`、`browser-mNN-recheck.json`、`*-mNN-recheck.png` |
| notebook 検証 | `scripts/verify_*_notebook.py`（10）、`verify_accepted_vol06_notebook.py`、`verify_core_notebooks.py`（`_output_signature`） | `notebook-check.json` |
| 数値検証 | `scripts/verify_{alternative_models,stochastic_volatility,local_volatility,convertible_bond,path_dependent}_numerics.py`（5） | `numerical-check.json` |
| 参照生成 | `scripts/build_*_reference.py`（11）、`build_*_lesson_data.py`（5）、`build_*_browser_reference.py`（5） | validation 配下の JSON と `source_sha256` |
| 実行時の入力 | `hullkit/src/hullkit/_{alternative_models,asian,basket,convertible_bond,exchange,local_volatility,path_dependent,shout,static_replication,stochastic_volatility,variance_swap}_lesson.py`（11）、`exotics.py`（docstring のみ） | validation の JSON 21 本を読み、record の `artifact_sha256`/`source_sha256` で改竄を検査 |
| hullkit テスト | `hullkit/tests/test_{asian_lesson,asian_pricing,basket_lesson,exchange_lesson,exchange_pricing,exchange_reference,shout_lesson,shout_tree,static_replication_lesson,variance_swap_contracts,variance_swap_lesson,variance_swap_reference}.py`（12） | validation の JSON |
| Markdown | 41 ファイル・138 リンク（`VALIDATION.md` 17、`docs/SECTION_REVIEW_HANDOFF_2026-09-15.md` 16、`docs/SECTION_26_9_ACCEPTANCE_2026-09-15.md` 13 ほか） | PNG へのリンクは 14 本で、§26.9・§26.10 の受入時画像だけ |
| 記録 JSON | `docs/validation/**/*.json` 269 本 | 台帳が直接参照するのは 31 本 |

### 1.4 サイズと件数

**全体**: 1,832 ファイル・108,213,461 B（103.20 MiB）。PNG 1,554 本・99,393,479 B（94.79 MiB）、JSON 269 本・8,764,543 B（8.36 MiB）、Markdown 9 本・55,439 B。

名前で分類した内訳（`-mNN-recheck` 接尾辞と §26.11 の `m4b-` 接頭辞を再検査とする）:

| 区分 | ファイル | バイト |
|---|---:|---:|
| 再検査（recheck） | 1,495 | 92,212,898（87.94 MiB） |
| うち再検査 PNG | 1,316 | 86,311,799（82.31 MiB） |
| 受入時（接尾辞なし） | 302 | 14,220,692（13.56 MiB） |
| 受入時（`mNN-check` 付き） | 35 | 1,779,871（1.70 MiB） |

**節別**（全ファイルと再検査 PNG）:

| ディレクトリ | ファイル | バイト | 再検査 PNG | 再検査 PNG バイト |
|---|---:|---:|---:|---:|
| section-26-9 | 116 | 3,576,307 | 80 | 2,965,591 |
| section-26-10 | 192 | 11,829,781 | 144 | 10,300,726 |
| section-26-11 | 219 | 13,354,179 | 162 | 11,715,559 |
| section-26-12 | 194 | 18,269,591 | 144 | 10,666,795 |
| section-26-13 | 187 | 12,887,911 | 144 | 11,097,762 |
| section-26-14 | 185 | 13,664,739 | 144 | 11,857,505 |
| section-26-15 | 167 | 10,684,743 | 126 | 9,065,570 |
| section-26-16 | 159 | 13,571,555 | 120 | 11,437,934 |
| section-26-17 | 111 | 2,413,608 | 80 | 1,882,898 |
| section-27-1 | 93 | 2,513,929 | 64 | 1,948,160 |
| section-27-2 | 91 | 2,939,488 | 60 | 2,138,430 |
| section-27-3 | 57 | 1,300,343 | 32 | 827,154 |
| section-27-4 | 39 | 855,930 | 16 | 407,715 |
| section-27-5 | 21 | 344,099 | 0 | 0 |
| section-ledger-m1 | 1 | 7,258 | 0 | 0 |
| **計** | **1,832** | **108,213,461** | **1,316** | **86,311,799** |

**マイルストーン別の再検査**（全節の合計）。M7 以降は受入済みの全節を撮り直しているため、節数に比例して増える:

| タグ | 対象節 | ファイル | バイト | うち PNG |
|---|---:|---:|---:|---:|
| m2b / m3b / m4a | 1 / 2 / 1 | 1 / 2 / 1 | 4,148 / 23,799 / 3,896 | 0 |
| m4b | 3 | 21 | 1,337,293 | 18 |
| m5b / m6b | 4 / 5 | 7 / 13 | 38,228 / 591,102 | 0 |
| m7 | 6 | 112 | 7,748,720 | 100 |
| m8 | 7 | 132 | 9,064,777 | 118 |
| m9 | 8 | 154 | 10,994,124 | 138 |
| m10 | 9 | 172 | 11,388,604 | 154 |
| m11 | 10 | 190 | 11,886,407 | 170 |
| m12 | 11 | 212 | 12,616,270 | 190 |
| m13 | 12 | 230 | 13,044,213 | 206 |
| m14 | 13 | 248 | 13,471,317 | 222 |

ROADMAP D1 の「M7 7.7MB → M13 13.0MB」は m7 7,748,720 B・m13 13,044,213 B と一致する。
新しい節自身の受入証跡は §27.5 で 344,099 B（PNG 16 枚＋JSON 5 本）。

### 1.5 SHA-256 の重複と削減できる量

| 指標 | 値 |
|---|---:|
| 異なる内容（blob） | 586 |
| 2 回以上現れる内容 | 263 グループ・1,509 ファイル |
| 内容アドレス保管で必要なバイト（各内容 1 回） | 25,803,907 B（24.61 MiB） |
| **削減できる量**（Σ(出現数−1)×サイズ） | **82,409,554 B（78.59 MiB）＝全体の 76.2%** |
| うち PNG / JSON / Markdown | 82,409,554 B / 0 / 0 |

重複 263 グループはすべて「同じ節・同じ画像名で、マイルストーンだけが違う」系列の中にある。節をまたぐ重複と JSON の重複は 0。
再検査 PNG 1,316 枚のうち 1,073 枚（71,412,431 B）は受入時の画像とバイト一致、1,209 枚（80,114,211 B）は直前の回とバイト一致。

注意: この削減量は既存ファイルをすべて保管庫へ移した場合の上限で、Git の過去履歴の容量は減らない（ADR 0004）。
D1-preflight では既存ファイルを移さない（第 5 章 Q4）。今後の増分に効くのは 1.6 の「毎回ほぼ同じバイト列を撮り直している」事実のほう。

### 1.6 画像系列の安定性（再描画は毎回ほぼ同じバイト列）

節×画像名の系列 238 本（受入時と各回の再検査を時系列に並べたもの）を分類した:

| 分類 | 系列 | 意味 |
|---|---:|---|
| 1 種類の内容のまま | 190 | 撮り直しても常にバイト一致 |
| 変化して戻らない | 29 | 大半は M8 の一斉変化（下記） |
| 以前の内容に戻る（A→B→A） | 19 | 入力が同じでもバイト列が揺れる。§26.10 に 7、§26.17 に 6、§27.2 に 2、§26.11・§26.12・§26.15・§26.16 に各 1 |

各回で「直前と違う内容」になった PNG: m4b 1/18、m7 7/100、**m8 27/118**、m9 6/138、m10 9/154、m11 12/170、m12 11/190、m13 16/206、m14 18/222。
browser record の `browser_version` は m7 まで `141.0.7390.37`、m8 から `145.0.7632.6` で、m8 の変化の多さは Chromium の更新と一致する。
§27.1・§27.3・§27.4・§27.5 の全 64 系列は一度も変わっていない（§27.1 は受入時＋m11–m14 の 5 回）。

vol06 notebook の節スライス（`## N.` 見出しから次の `## ` まで）を、Plotly 出力の乱数 div ID（UUID）と
埋め込み plotly.js を伏せて SHA-256 で比べると、§27.1 のスライスは M10 受入 `c3dd6ae5` から HEAD まで 6 つの commit で同じ値だった。
その間に notebook は 46→94 セルに増え、ファイル全体のハッシュとスライスの生ハッシュ（UUID 込み）は毎回変わっている。
§27.2–§27.4 のスライスも受入後の全 commit で不変だった。ファイル単位のハッシュでは毎回「変更あり」になり、スライス＋正規化なら「不変」と判定でき、実画像のバイト一致とも合う。

### 1.7 台帳から到達できる証跡と、履歴だけの証跡

台帳の evidence（276 パス、うち record 31 本）と、その record の `source_sha256`/`artifact_sha256` をたどると 595 ファイルに届く。
docs/validation 内では:

| 区分 | ファイル | バイト |
|---|---:|---:|
| 台帳からたどれる（現行の証跡） | 417 | 19,888,841（18.97 MiB） |
| どの現行 record からも参照されない（過去の再検査など） | 1,415 | 88,324,620（84.23 MiB） |

現行の PNG は 300 枚（16,824,049 B）で、うち 222 枚が `*-m14-recheck.png`。台帳の `image` evidence 自体は受入時の画像（§26.11 は `m4b-` 画像）を指す。

### 1.8 設計に効く制約（実測で確認）

1. **台帳が固定しているファイルは直せない。** 上の 595 ファイルには `scripts/` 60 本（全 browser verifier、`recheck_accepted_m11–m14.*`、`verify_core_notebooks.py` など）、
   `report/report_builder/{figures,render}.py`、`report/assets/style.css`、vol06/vol10 の notebook と builder、`book/_config.yml`、`book/_ext/book_runtime.py`、
   `release_manifest.json`、原典 PDF が含まれる。変更すると `verify_section_ledger.py` が鮮度切れで FAIL する。
   **固定されていない**: `scripts/verify_section_ledger.py`、`scripts/verify_accepted_vol06_notebook.py`、`report/tests/test_section_ledger.py`。
   D1 の検査器はこの 3 本の拡張と新規ファイルで実装し、固定ファイルには触れない。
2. **docs/validation は証跡置き場であると同時に実行時の入力置き場。** lesson モジュール 11 本が JSON 21 本を読み、ハッシュで照合する。これらは Git に残す（移管対象外）。
3. **Book の MathJax は CDN の浮動版。** 構築済み `06_numerical.html` は `https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js` を読み、
   `release_manifest.json` の `allowed_legacy_book_runtime_dependencies` がこれを許可している。Book の検査はネットワークが必要で、MathJax の版は実行時にしか分からない。
4. **描画環境はリポジトリで固定されていない。** Chromium は `~/.cache/ms-playwright/chromium-1208`（Chrome for Testing 145.0.7632.6）、
   Playwright は npx キャッシュ（record には `PLAYWRIGHT_MODULE=<existing runtime>` とだけ残る）、Node v26.7.0。
   browser context は locale・timezone・deviceScaleFactor を指定していない（シェルは `LANG=C.UTF-8`）。
   viewport の高さは verifier ごとに違う（§27.1 は 1000、§27.5 は 1050）。
5. **フォントは fontconfig の代替に依存。** portal のフォント指定は `-apple-system, "Hiragino Kaku Gothic ProN", "Noto Sans JP", "Segoe UI", sans-serif`。
   この機械では `fc-match "Noto Sans JP"` が `NotoSans-Regular.ttf` を返す（fontconfig 2.15.0、`fc-list` 2,106 件）。
6. **plotly.js 本体（v3.7.0、約 4.85 MB）は notebook の最初の図の出力に埋め込まれる。** vol06 ではセル 28＝§27.1 の `alternative_cev`、
   vol10 ではセル 8（§26.10）。この 2 節のスライスは全節共通の描画資産を含むため、正規化で分離する必要がある。
7. **notebook の Plotly 出力の div ID は実行ごとに変わる**（例 `80233466-de52-4f56-a166-aec23d89b480`）。正規化しないとスライスの指紋が毎回変わる（1.6）。
8. **portal は新しい節ごとに共有 CSS に 1 行足している。** 例: `ad365fee` の `.fig-card:has([id^="fig-stochvol_"]) { grid-column: 1 / -1; min-width: 0; }`。
   `report/assets/style.css` は 2026-09-15 以降 9 commit で変更。ファイル単位で指紋を取ると、この 1 行で portal の全節が再描画になる。
   `render.py`・`theme.py`・`templates/`・`book/_config.yml`・`book/_ext`・`book/_static` は同期間に変更 0 回。
9. **record の形がそろっていない。** `numerical-check.json` の `artifact_sha256` は §27.x では文字列、§26.15/§26.16 では mapping。
   §27.5 はこれを `reference` として登録しているので現行検査は通るが、新しい検査器は両方の形を扱う必要がある。
10. **現行の台帳検査は両モードとも PASS**（`--check-artifacts` は gitignore された構築物 `report/site/{exotics,numerics}.html`・
    `book/_build/html/notebooks/{10_exotics,06_numerical}.html` がこの checkout に最新で存在するため。4 本の SHA-256 は m14-check.json の値と一致）。

## 2. 目標設計

### 2.1 保存先と責務

| 層 | 置くもの | 読み出し・検査 |
|---|---|---|
| Git | run manifest、依存指紋、基準参照、数値JSON、受入時の最小画像 | clean cloneで検査可能な最小fixtureを含む |
| C: 主保管庫 | 新しい再検査画像の不変blob | `PROJECTS_ARTIFACT_STORE`から読取り。SHA-256とsizeを照合 |
| F: 第2コピー | 同じblobのバックアップ | `PROJECTS_ARTIFACT_MIRROR`から独立に復元して照合 |
| scratch | 実行中の画像・復元先 | 一時生成→検証→atomicな登録。検証前の実体をmanifestで公開しない |

物理場所は ADR 0004 の `%USERPROFILE%\ProjectArtifacts\projects` と `F:\ProjectArtifacts\projects-backup`。
コードには固定せず環境変数で与える。WSLからの可視性・別物理媒体・空き容量・書込権限を着手時に確認する。
公開manifestは `artifact:sha256:<64桁digest>` を使い、個人の絶対パスを保存しない。
公開clone用fixtureの成功と、私有保管庫を使った完全な復元監査の成功は別の結果にする。

### 2.2 新規recordの契約案

既存JSONはそのまま読む互換経路を残し、新形式には明示的なschema versionを付ける。
既存 `source_sha256` の「ファイル全体」を新形式の「節スライス」へ暗黙に読み替えない。

| フィールド（案） | 必須内容 |
|---|---|
| `schema_version`, `run_id`, `commit` | 型・一意run・検証対象commit。dirtyなら差分digestも記録 |
| `section_id`, `surface`, `viewport` | Book/portal別、幅と高さ、device scale |
| `dependency_fingerprint` | 規約versionと全構成要素のdigest。除外・正規化ルールもversion管理 |
| `decision`, `reason` | `redrawn` / `reused`。不変を判断した根拠または再描画理由 |
| `baseline` | 元の検証run・commit・検証器・指紋・画像への直接参照。参照チェーン禁止 |
| `images` | 論理参照、SHA-256、bytes、MIME、復元先の安全なproject相対パス |
| `checks` | 数値・意味・notebook・表示値・相互作用・releaseの個別結果と記録digest |
| `environment` | Python/Node/Playwright/Chromium/Plotly/MathJax/OS/locale/timezone/実フォント |
| `storage_verification` | 主・第2コピーそれぞれのhash/size/復元結果と日時 |

`PASS` は必要な全条件を満たしたときだけ付ける。保管庫未接続は `SKIP/UNVERIFIED` とし受入には使わない。
任意の未知fieldを無視して誤ったversionを通す方式は避ける。既存reference記録にある文字列型digestは
既存形式として扱い、新形式のpath→digest mappingと混ぜない（現行台帳のrecord/reference区分を維持）。

### 2.3 依存指紋と変更の伝播

1. 節の見出し・セルID・ソース・出力、図のdata/layout、読込JSON、呼出す関数とその推移的依存を含める。
2. Book/portalの対象DOMと、共有template/CSS/JS/font/rendering環境を含める。依存一覧が曖昧ならファイル全体を使う。
3. Plotlyの一時div IDは同じ構造IDへ正規化できるが、埋込みplotly.jsを捨てず別の共有資産digestへ移す。
   日時を除外できるのは規約で特定したmetadataキーだけ。数値・本文・式・figure payloadは除外しない。
4. MathJaxの浮動CDNは取得した実バイトと版を記録する。取得不能・版不明なら不変と判断しない。
   CDNや共有CSSの仕組みを変えるのは別の変更であり、preflightの省容量化に紛れて行わない。
5. まず共有CSSは全体ハッシュとする。selector単位の影響解析がない段階で「追加1行だから無関係」と推定しない。
6. 環境・normalizer・依存schemaが変われば基準失効。画像が同一でも意味の検査の代用にはならない。

### 2.4 保存・復元器の安全条件

- hash指定のblobは上書きせず、同名既存blobも中身を検査する。書込み途中のファイルを完成blobとして読まない。
- 2コピーをそれぞれ別一時ディレクトリへ復元し、元入力・manifest・復元バイトの3者を照合する。
- 絶対パス、`..`、Windows drive/UNC、symlink経由のroot外参照、循環・連鎖参照、既存の異なるファイルへの復元を拒否する。
- 同一digestで異なるsize/MIME等の矛盾、manifest改竄、欠損、切詰め、1 byte破損を負のfixtureにする。
- 主コピーが壊れた場合も黙ってPASSせず、失敗を記録して第2コピーから復旧し、再照合したrunを作る。

## 3. 実装計画（5 段階）

新規ファイル名は設計上の候補。既存記録にpinされたファイルは §1.8 の一覧を着手時に再取得する。

| 段階 | 作業・候補ファイル | 検証して残す結果 |
|---|---|---|
| 1 | 新規 `scripts/evidence_store.py`、schema/小fixture、`report/tests/test_evidence_store.py`。保管庫の実接続 | 保存・復元・衝突・path拒否・破損検出。C/Fそれぞれの復元バイト一致。実体の無いhashだけのPASSを拒否 |
| 2 | 新規 `scripts/evidence_fingerprint.py`、`scripts/recheck_accepted.py`。未pinの `verify_section_ledger.py` と関連testsの互換対応 | v1既存record全件を以前と同じ条件で読める。v2のschema・直接参照・現行run鮮度を検査。公開最小fixtureとstore依存検査を区別 |
| 3 | §27.3を対象に新規runをscratchへ出す比較driver | §4の全再描画/再利用比較。基準画像の復元と閲覧。既存JSON・台帳の上書きなし |
| 4 | dependencyの負の対照とfallback | 無関係セルだけが再利用可。関連数値/本文/CSS/JS/フォント/環境/未知依存は再描画。欠損・破損はFAIL |
| 5 | 小群の実store保管・両媒体復元、既存gate、レビュー、ROADMAP更新 | 対象節の数値/notebook/Book/portal、台帳通常・artifact、release、hullkit+report。実行コマンド・commit・環境・全結果を統合記録へ |

段階2で旧recordのsource hashが変更ファイルをpinしていたら、単にhashを書き換えず新しいrunとして必要な再検査を行う。
旧verifierの文字列置換フックを増殖させず、新driverの入出力引数で保存先を指定する。
ただしこの整理が大きな既存refactorになる場合は、互換wrapperを先に作り、広範な変更を別途判断する。

## 4. 1 節での比較実験（段階 3）

対象候補は **§27.3 IVF**。M12以降の画像系列が安定し、M14までに同じ巻へ無関係な節を追加した履歴がある。
Book/portal、既定2幅、全図・操作を列挙したcoverage集合を基準にする。

| 実験 | 期待 |
|---|---|
| 同一commit/環境で全再描画 A | 既存の数値・表示・相互作用の全検査を実行、画像をC/Fへ保存 |
| 同一入力で基準再利用 B | Aと同じcoverage集合と検査結果。新runからAの画像を直接参照し両媒体から復元できる |
| 無関係な節のセル追加 | 対象節payloadと共有資産に差がなければB可。全notebookの実行・整合検査は維持 |
| 対象節数値/式/説明の1箇所変更 | 指紋が変わりAへ。表示値または意味の負の検査が失敗する |
| 共通CSS/JS/実フォント/Chromium変更 | 関連する全節で基準を失効。CSSの局所変更も初版は保守的に失効 |
| blob欠損/破損・旧版normalizer・未知依存 | 再利用PASSを拒否。復元または全再描画が必要 |

画像の完全一致は観測指標として残すが、描画揺れ（§1.6）があるので、それだけをA/Bの合格条件にしない。
合格は必要なcoverageと数値・意味・表示検査が同等で、どの画像を根拠にしたかが追跡・復元できること。
時間・新規画像bytes・重複blob数も記録し、改善幅を実測する。約76%削減という過去総量からの上限を性能目標に流用しない。

## 5. リスクと利用者への確認事項

| 項目 | 判断・対応 |
|---|---|
| 実装の再開時点 | 本人承認済み：johnhullの必要保管庫・作業分離が整えば再開。全workspace移行の完了は不要 |
| C/Fの実機準備 | 現時点では未検証。別媒体と復元を確認できるまではM15へ進まない。F接続が必要なら、その具体的な操作だけ依頼する |
| D3軽量化 | 本preflightとは別判断。explanation/rendered省略は行わない |
| 既存証跡の移管・削除 | この計画に含めない。旧画像・JSONは保持し、新しい再検査から適用 |
| 外部blobを利用できないpublic clone | 最小fixtureの検査は可能。完全監査は未検証として区別し、release PASSに読み替えない |
| 保管庫ツールの他projectへの展開 | 最初はjohnhull内で必要範囲を実証。workspace全域の移管・共有基盤refactorは別作業 |

## 6. この計画の範囲

- accepted/unreviewed件数、Hull要求、数値許容差、意味の照合、release契約は維持する。
- 新規受入の最小画面証跡と、実行入力になっているlesson JSONはGitに残す。
- D1-preflightを完了するまでは、台帳や既存recordの参照を外部blobへ変更しない。
- §27.6の実装、研究コード、モデル性能の承認、過去履歴の圧縮・書換えは含まない。

## 付録 A. 重複総量の再確認

2026-09-27に下の読み取り専用処理と同じ集計を実行し、1,832 files / 108,213,461 bytes /
586 unique blobs / 25,803,907 unique bytes / 263 duplicate groups / 82,409,554 duplicate bytes を得た。
ディレクトリ自体の容量を含めないファイルの論理バイト数である。

```python
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import sys

root = Path(sys.argv[1])
groups = defaultdict(list)
for path in sorted(p for p in root.rglob('*') if p.is_file()):
    data = path.read_bytes()
    groups[sha256(data).hexdigest()].append(len(data))
total = sum(sum(g) for g in groups.values())
unique = sum(g[0] for g in groups.values())
print('files', sum(map(len, groups.values())), 'bytes', total)
print('unique_blobs', len(groups), 'unique_bytes', unique)
print('duplicate_groups', sum(len(g) > 1 for g in groups.values()))
print('duplicate_bytes', total - unique)
```
