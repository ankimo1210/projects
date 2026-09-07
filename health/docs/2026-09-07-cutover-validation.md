# Next.js切り替えの検証 — 2026-09-07

CLIによるGoogle Healthの原本保存と、ローカルのNext.jsポータルを接続した。
7画面の操作確認後に旧Streamlit UIと専用テストを削除し、健康データ・認可情報は既存の
private保存先に維持した。ブランチは`codex/health-full-archive-nextjs`。

## 検証範囲

- 原本文のbytes復元、未知フィールド・複数source・版・エラー応答の保持。
- ENOSPC、fsync失敗、DB書き込み失敗時の停止、再実行時の耐久性。
- legacy importのtransactionと一度だけの取り込み、成功最終pageが必要な完了判定。
- 途中pageからの再開、429/403、繰り返しtoken、型間とprojection内の公平な実行。
- 詳細GETキューの原子的作成、停止後の復旧、ID欠落時の未完了判定。
- typed tableと履歴期間の分離、期間拡張時の境界補修、取得範囲外の既存行保持。
- OAuth callbackのstate・timeout・ポート競合、読み取りscope、秘密値を出さない終了処理。
- DDL前のcheckpointとバックアップ。失敗時はStoreを開かない。
- full-history baseline、期間別相関、欠損・有限数・civil time・睡眠分類。
- 全点のexport、世代単位の切り替え、失敗時の前世代保持、private permissions。
- sourceの保存総数と最新試行件数、typed系列の件数・保存期間・CSV。
- 日内の短い区間を含む極値・欠損境界の保持、ズーム時の全点への復帰。

## 最終結果

- Python: **413 tests passed**。
- Ruff check・format check: **49ファイル成功**。
- TypeScript・ESLint・Vitest: **44 tests passed**、Next.js静的build成功。
- Python wheelにカタログJSON・CLI entry pointを同梱。

## 実行手順

workspace rootでPython suite・lint・format check、`make health-web-check`で
TypeScript・ESLint・Vitest・静的production buildを実行。
`uv build --package health`でwheelにカタログJSONとCLI entry pointが入ることも確認。
rootのuv.lock変更はhealthからStreamlit/Plotlyの参照を外す4行だけ。

ブラウザはChromiumの一時ハーネスを使用し、通常の開発依存へE2Eツールを追加していない。
架空データのlight/dark・desktop/mobile、7route、CSV、日付・期間切替、遅延応答、
失敗・空・世代不一致を確認した。記録は[Web検証](../web/VALIDATION.md)。
本人DBもバックアップ後にexportし、7routeでJSエラー・読込エラー・横はみ出しがないことを確認。

## 実API確認の限界

保存済みの3scopeでbounded probeとsyncを実行。追加scopeがない経路は権限不足として表示する。
全履歴性が文書や応答から確認できない場合は、ページの取得が終わっても`unknown_history`。
Google上の全データを保存済みとするものではなく、Google Takeoutは自動化していない。

VO2 Maxの型名を公式の`daily-vo2-max` / `run-vo2-max` / `vo2-max`へ修正。
2種類のdailyRollUpはoptional pageSize付きで400、省略時は200だったため、API既定値を使う。
この5経路を再取得して応答の保存を確認した。以前の失敗応答も削除しない。
API本文・token・本人データ・生成JSON・実行途中のcursorはcommit対象外。
