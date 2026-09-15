# M1：節別台帳と証跡検査の設計
日付：2026-09-15。ユーザーの「start implementing of milestone」に基づき、[引き継ぎ §9](../../SECTION_REVIEW_HANDOFF_2026-09-15.md) の最初の段階を実装する。

## 到達点
- 原典PDFのoutlineから番号付き299節・付録7本のinventoryを作る。学習内容の再監査とは分ける。
- 全306項目に状態を持たせ、§26.9のみ既存B01–B09を証跡つきで登録する。残りは未評価。
- ID重複・欠落・未知ID、曖昧なaccepted、証拠欠落・変更、集計や生成文書のドリフトを失敗として返す。
- JSONを正本に、人向けMarkdown台帳を決定的に生成する。登録件数と受入件数を表示し、全節の完成率は出さない。
- 価格ロジックや配布画面は変更しない。次の教材節の実装はM2として未着手を明記する。

## ファイルと入力契約
- `docs/section_inventory.json`: schema_version=1, edition, source={path,sha256,method}, expected_counts={sections,appendices,chapters}, entries=[{id,chapter,kind,title,page_start}]. kindはsectionまたはappendix。IDは26.9、3.appendix等。原典にない終端ページは推測しない。
- `docs/section_ledger.json`: schema_version=1, inventory_sha256, sections=[{id,status,requirements,...}].
- status: unreviewed / gaps_found / pending_validation / accepted / out_of_scope。
- accepted節はreviewed_at (ISO日付)、source_pages (開始・終了の2整数)、scope、assumptions、limitations、acceptance_note (project内相対パス)、evidence、requirementsを持つ。
- evidenceはIDをキーにした辞書。値は{path,sha256,kind}。kind: source / test / note / image / record / reference。recordはJSONでtop-level status=PASSを持つ検証記録。
- requirementsは{id,statement,coverage}。coverageの5キーは explanation / implementation / independent_validation / visualization / rendered。
- 各coverageは{state,refs,reason?,locator?}。stateはverified / pending / not_applicable。verifiedは1件以上の実在するevidence IDを参照。not_applicableは具体的なreasonが必須。acceptedにはpendingがなく、explanationとrenderedは必ずverified。independent_validationがverifiedなら少なくとも1つのrecord、implementationならsource、visualizationならimage、explanationならsourceまたはnote、renderedならrecordを参照する。
- acceptedのevidenceにはrecordが少なくとも1つ必要。recordのsource_sha256がある場合は全ファイルの鮮度を確認。artifact_sha256は--check-artifacts指定時に存在・一致を必須とする。既定検査は未生成の配布HTMLを要求しない。この差は画面と出力に明記する。
- 未評価はrequirements=[]。gaps_found / pending_validationは要求を持てる。out_of_scopeはreason必須。accepted以外も記載されたrefsの解決を確認し、対象外をaccepted件数へ加算しない。
- パスはproject内の相対パスだけ。../、絶対パス、外部へのsymlinkを拒否する。
- inventory hash、原典PDF hash、登録証跡hashを照合する。過去PASSの文字列だけで現在の計算が正しいと宣言しない。実際の数値再計算・画面再実行は既存の検査へ接続する。

## 実装の境界
標準ライブラリのみの `scripts/verify_section_ledger.py`。
`evaluate_ledger(project: Path, inventory: dict, ledger: dict, *, check_artifacts=False) -> dict`:
status、errors、counts（全5状態）、inventory_total、accepted_sections、artifacts_checkedを返す。
入力不正は人が理解できるFAILを返し、未評価が残るだけでは失敗にしない。
`render_summary(inventory, ledger, result) -> str`: 検査成功と教材の完成を分けた日本語Markdown、章別件数と全節一覧を出す。
`main(argv=None) -> int`: --project-root (既定はscriptの親project)、--write-summary、--check-artifacts。
既定は検査と `docs/SECTION_LEDGER.md` の鮮度照合。成功0、失敗1。--write-summaryは有効な入力のときだけ書く。
出力先は固定の `docs/SECTION_LEDGER.md`。無効入力で既存の要約を上書きしない。

## 確認
実データの登録件数306、299節+7付録、37章、§26.9 accepted=1、残り305 unreviewed。
欠落・重複・未知ID、未証明accepted、NA理由なし、未知refs、証拠の欠落・変更・FAIL、
壊れたJSON、scope外path、summary drift、条件付きartifact検査を負例として固定する。
GUIは追加しないため新規のブラウザ試験は不要。既存pilotのソース・成果物hashを照合して影響がないことを確認する。

## 作業上の制約
- johnhull内に限定。既存ユーザー変更を保持する。
- 新規依存・公開API変更・移行・広範なrefactorを行わない。
- コミット・push・公開を行わない。
- 分離した作業ツリーで実装・検証し、元ファイルが基準から変わっていないことを確認して今回の変更だけを戻す。
- 同じ問題への修正試行は3回を上限とする。
