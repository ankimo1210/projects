# 節別台帳の更新方法

この台帳は「節の一覧」と「人が確認した学習要求・証跡」を管理する。
検査成功は登録内容と証跡の整合性を表し、教科書の全論点が自動的に検証されたという意味ではない。

- [現在の台帳](SECTION_LEDGER.md)：JSONから生成した一覧。
- [原典inventory](section_inventory.json)：番号付き299節と付録7本。各開始ページはGlobal Edition PDFのoutlineに由来する。
- [要求と証跡](section_ledger.json)：節の状態、学習要求、前提、除外理由、証拠ファイル。
- [§26.9の受入例](SECTION_26_9_ACCEPTANCE_2026-09-15.md)：B01–B09と実際の数値・画面の根拠。
- [M1設計](superpowers/specs/2026-09-15-section-ledger-m1-design.md)：入力契約と検査範囲。

## 原典の扱い

正本は `options, futures and other derivatives 11th.pdf`。inventoryにSHA-256を保存した。
抽出コマンドはproject rootから次のとおり：

```bash
mutool show 'options, futures and other derivatives 11th.pdf' outline
```

番号付き節と章末Appendixだけを登録する。Summary / Further Reading / Practice Questionsは含めない。
例えばCh.26には§26.17 Static Options Replicationもある。商品taxonomyの行数を章の節数として扱わない。
ID `3.appendix` 等は台帳の識別子であり、教科書の印刷された節番号ではない。
`page_start` はoutlineの物理ページ（1始まり）。節末ページはoutlineから推測しない。
詳細レビュー時に `source_pages` を本文で確認して記載する。

## 状態を更新する

| 状態 | 意味 |
|---|---|
| unreviewed | 今回の方法では学習要求を再監査していない。実装がないという判定ではない |
| gaps_found | 要求を確認し、不足が見つかっている |
| pending_validation | 作業はあるが、受入に必要な確認が残っている |
| accepted | 記載した学習要求が受入済みで、その証跡が揃っている |
| out_of_scope | 理由を記して今回の対象から外した。受入件数には含めない |

`status` だけをacceptedへ変えても検査は通らない。
review日、原典のページ、scope、assumptions、limitations、受入メモ、evidence、requirementsが必要。
required項目の詳細は設計を参照する。

要求ごとの `coverage` は次の5観点：

1. explanation：学習者が読む説明。
2. implementation：計算・契約例・図を作る実装。
3. independent_validation：独立根拠と実行済みの検証記録。
4. visualization：学習上の問いに対応する図。
5. rendered：配布画面の読込・操作・表示値・数式の確認。

`verified` には証拠ID、`not_applicable` には具体的な理由が必要。
acceptedに未検証の `pending` を残さない。explanationとrenderedは省略できない。
図や数値計算が不要な定性節でも、説明と実画面の確認は記録する。

`locator` にはnotebookの見出し・テスト関数など、人が根拠を探せる位置を記載できる。
場所の説明の妥当性や、要求自体の網羅性は人のレビュー対象である。
ファイルの存在・同じハッシュだけで、内容が正しいと判断しない。

## 検証する

以下はprojects root（`/home/kazumasa/projects`）から実行する。

```bash
.venv/bin/python johnhull/scripts/verify_section_ledger.py
```

既定ではinventory・ledgerの対応、状態と根拠、ファイルの存在・SHA-256、
検証記録のPASSとそのsource_sha256、生成Markdownの鮮度を確認する。
未評価が残ること自体はFAILではない。出力のaccepted件数と未評価件数を併読する。

記録にある成果物（Book/portalや数値比較表）も照合する場合：

```bash
.venv/bin/python johnhull/scripts/verify_section_ledger.py --check-artifacts
```

このモードは検証記録内のartifact_sha256も確認し、ファイル欠落・不一致ならFAILにする。
数値検証の記録も、実際に生成した比較表等のartifact_sha256を登録する。
Book/portalの記録が要求する配布物を作っていないcheckoutでは、先に対応するbuildを行う。
既定モードでは配布物の鮮度を確認したと主張しない。

## データと要約を更新する

JSONの学習要求や証跡を修正した後、整合性を検査してから要約を更新する：

```bash
.venv/bin/python johnhull/scripts/verify_section_ledger.py --write-summary
.venv/bin/python johnhull/scripts/verify_section_ledger.py
```

入力が無効なら既存の要約は上書きしない。
Markdownを直接編集しても、次の鮮度検査で不一致として検出する。

証跡を更新する順序は、
対象の説明・実装を修正 → 必要な数値検査と出力・画面検査を再実行 →
検証記録を保存 → ledgerの証拠とハッシュを更新 → summaryを生成。
失敗を消すためだけにハッシュを更新しない。

`inventory_sha256` はinventoryファイルそのもののSHA-256。
evidenceの `sha256` は各ファイルのSHA-256。
変更があった場合、その変更が学習要求に影響するかを確認してから更新する。

## 現在の境界

M1では306項目の識別を完了し、§26.9のみ既存の受入証跡を登録した。
続くM2aで[§26.10の要求と独立価格検証](SECTION_26_10_REVIEW_2026-09-15.md)を追加した。
M2bで[§26.10のD01–D06](SECTION_26_10_ACCEPTANCE_2026-09-15.md)も受入済みとなった。
M3aで[§26.11のL01–L06と独立128価格](SECTION_26_11_REVIEW_2026-09-15.md)を確認した。
M3bでは本文6小節・共有4図・Book/portal両面2幅、全体1,695テストと台帳の成果物ハッシュ検査を完了した。最終ブランチレビューも承認済み。
M3b時点の判定は[§26.11受入ノート](SECTION_26_11_ACCEPTANCE_2026-09-16.md)と[m4a-recheck](validation/section-26-11/m4a-recheck.json)を参照。
M4aで[§26.12の要求S01–S06と独立参照価格42件](SECTION_26_12_REVIEW_2026-09-16.md)を登録した。
M4a時点では実装・教材・図が無く、gaps_foundだった。
M4bで独立CRR・本文6小節・共有4図・Book/portal52状態を確認し、Task1–3の独立レビューが承認された。
現在は[§26.12受入ノート](SECTION_26_12_ACCEPTANCE_2026-09-16.md)と[M4b統合記録](validation/section-26-12/m4b-check.json)を参照。
M5aで[§26.13の要求A01–A06と独立参照価格144件](SECTION_26_13_REVIEW_2026-09-16.md)を登録した。
既存実装は連続平均callの1本のみで、離散観測・既発契約・平均行使型が無く、gaps_foundである。
台帳は受入済み4、不足あり1、未評価301項目。全体テスト・最終ブランチ判定は統合記録へ保存する。
段階ごとの進捗は[ROADMAP](../ROADMAP.md)の節別台帳の表を正本とする。
過去の実装分類をそのまま学習内容の受入へ移していない。
全節の現在の充足率・計算カバレッジは、この台帳だけではまだ確定できない。

M3bは共有成果物を変更した§26.9・§26.10も今回のBook/portalで再検証した。
M4bの現行台帳には[§26.9 m4b-recheck](validation/section-26-9/m4b-recheck.json)、
[§26.10 m4b-recheck](validation/section-26-10/m4b-recheck.json)、[§26.11 m4b-recheck](validation/section-26-11/m4b-recheck.json)を結ぶ。
過去の日時付き18数値・統合記録は保持し、lookbackの古いブラウザJSONと18画像も元のバイト列を維持する。
最新のlookback画像はm4b接頭辞、ブラウザ記録はbrowser-m4b-check.jsonへ保存する。
§26.12の登録でledger guard testの期待件数が変わり、それをpinしていた§26.11のM3b統合記録が鮮度切れになった。
教材側が無変更であることをハッシュ比較で確かめた上で回帰を再実行し、m4a-recheckを現行の根拠に差し替えた。
**状態件数をassertするテストは検証記録にpinしない**（どの節を登録しても必ず変わるため）。

L05の新しいr=q極限価格エンジンはM3b対象外。実装・可視化のnot_applicableには理由を記録し、適用域の説明と実画面確認は省略しない。
価格APIは変更していない。次の未評価節も要求抽出から始め、既存の実装分類をacceptedへ流用しない。
