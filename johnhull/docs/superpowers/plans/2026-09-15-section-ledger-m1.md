# Section Ledger M1 Implementation Plan
> **For agentic workers:** Use superpowers:subagent-driven-development with task-scoped review. No commits or remote operations.

**Goal:** 原典306項目の台帳と、§26.9の受入根拠を検査・集計する実装を完成させる。
**Architecture:** 2つのJSONを正本とし、stdlibの検査CLIで整合性・証跡の鮮度・生成Markdownを検査する。
**Tech Stack:** Python 3.12 / JSON / pytest / Markdown、既存mutoolは原典inventory抽出時のみ。
**Spec:** [M1 design](../specs/2026-09-15-section-ledger-m1-design.md)

## Global Constraints
- johnhull内に限定。既存ユーザー変更を保持する。
- 新規依存・公開API変更・移行・広範なrefactorを行わない。
- コミット・push・公開を行わない。
- 同じ問題への修正試行は3回を上限とする。
- 未評価を受入済みにしない。M1の成功を全節の完成にしない。

### Task 1: 証跡検査CLIと回帰テスト
Files: scripts/verify_section_ledger.py, report/tests/test_section_ledger.py
Interfaces: specに記載のevaluate_ledger / render_summary / main。
Controllerがinventory、ledgerのデータ作成と既存文書の接続を担当する。データを推測して新規作成しない。

- [x] 実入力を扱う負例を先に書き、欠落IDや証拠改変を通すstubで失敗することを確認。
```python
def test_removing_an_inventory_row_is_not_accepted(project_fixture):
    inventory, ledger = project_fixture.inventory, project_fixture.ledger
    ledger["sections"].pop()
    result = evaluate_ledger(project_fixture.root, inventory, ledger)
    assert result["status"] == "FAIL"
    assert result["errors"]
```
- [x] specの型・パス・状態・hash・record鮮度・summary driftの検査を最小限で実装。
- [x] 実CLIをsubprocessで呼び、正常終了・改変時の非ゼロ終了・無効入力での非上書きを確認。
- [x] scoped pytestとruffを実行し、RED/GREENの根拠をreportへ保存。
- [x] 作業差分に対する独立レビューを受ける。

### Task 2: 原典inventory、受入証跡、文書の接続
Files: docs/section_inventory.json, docs/section_ledger.json, docs/SECTION_LEDGER.md,
ROADMAP.md, docs/SECTION_REVIEW_HANDOFF_2026-09-15.md, docs/SECTION_AUDIT_2026-09-14_FEEDBACK.md,
docs/validation/section-ledger-m1/validation.json
- [x] mutool showのoutlineから306項目と各開始ページを抽出し、章別連番・付録・総数を照合。
- [x] §26.9のB01–B09を元の受入表・画像・数値・browser記録へ結び、残り305項目をunreviewedで登録。
- [x] CLI --write-summaryでMarkdownを生成し、既定CLIで鮮度一致を確認。
- [x] missing ID / stale proof / false accepted / stale summaryの実改変プローブが失敗することを確認。
- [x] 全project pytest、ruff、差分検査。既存pilotソースのhash不変を確認。
- [x] M1の完了とM2の未着手を文書へ追記し、検証記録を保存。
- [x] 最終レビューの後、元checkoutの基準hashを確認して今回のファイルだけ反映する。
