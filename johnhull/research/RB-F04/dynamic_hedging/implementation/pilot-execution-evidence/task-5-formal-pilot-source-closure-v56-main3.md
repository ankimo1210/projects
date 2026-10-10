# 正式 pilot のソース封鎖準備 — v56 / main3

確認日: 2026-10-10。**実行ソースの封鎖条件は現在の固定状態で満たせます。正式 pilot・main の実行、予算承認、金融資格の確定は含みません。**

## 確認結果

| 項目 | 実確認 |
|---|---|
| phase の実行ソース | 80 ファイル、必須 root 11 本、未登録の局所 import 0 |
| 動的 import | v55 の 3 件を発見 → v56 で 0 件 |
| 固定 snapshot | v56 3 ファイル + main3 3 ファイルの 6/6 が実ファイル・保存コピーと一致 |
| mixed DAG | 3,138 jobs / 28 operations / 原 121 cases・51 attempts を保存 metadata から確認 |
| 実 dispatch | 28 operations 全て対応。実 worker 呼出先の封鎖漏れ 0 |
| 専用検証 | 191 passed（元 190 + 回帰 1）、59.70 秒。3 ファイルの Ruff・format PASS |
| 検査中の変更 | 80 ソース・固定 6 ファイルの SHA 変化 0 |
| 金融資格 | unknown。正式金融 worker 呼出し 0 |

source identity SHA-256: b04ce2e63dce80eb17e5dae917369e04d661c6dba0d3dc6a08e7178da2610688

完全な 80 ファイル・環境版・局所 import graph は task-5-formal-pilot-source-closure-v56-main3-inventory.json に保存しました。テスト 2 ファイルは固定 snapshot で別途照合し、金融実行の 80 ファイルには数えていません。

## 最小修正と保持した失敗

v55 の check_pilot.py に動的 hashlib import が 2 件、run_pilot import が 1 件ありました。実際の _locked_bindings が「unresolved dynamic financial source」で拒否する回帰 RED を保存しました。v56 は静的 hashlib import と関数内の from run_pilot import unpack_inputs に置き換えています。後者は元の遅延 load を保ち、循環 import の起動を避けます。

run_pilot.py は不変。checker の変更は 2 関数のみで、3 import の置換を除けば AST 等価です。元 v55 の test/helper 115 定義は AST 不変、新規回帰 1 件だけ追加しました。public API・依存・金融計算・入出力・原 N/seed/失敗/cap は変更していません。

v55 snapshot と独立レビュー、source probe v1 の失敗、修正した静的 dispatch probe v2、回帰 RED、最初の format 拒否を保持しています。v1 の dispatch 読み取りは先頭 if しか見ていない probe の不備でした。v2 で 28 operation 全件を確認したうえで、動的 import 3 件の実 blocker を再確認しています。v56 の限定独立再レビューは依頼済みです。

## 封鎖の境界

execution_source_identity は worker/checker、関数内の静的 import、package init、局所依存の実 bytes と環境の版を束ねます。formal plan の入力出所・job/control/attempt 仕様・reviewed budgets を別途 prior 固定する必要があります。AST の registry は数値 branch、native library の bytes、実時計、較正・学習履歴の成功を証明しません。

D の graph compiler と base compiler、保存 draft は別の provenance SHA として記録しました。D compiler の literal file load は prior metadata の作成経路であり、実 worker の局所 import closure とは分けています。正式 plan には作成結果の仕様・入力出所を固定し、恣意的な後付け変更を許さないことが必要です。

旧 phase inventory と現ソースは 9 ファイルの SHA が異なります。現 mixed v3 の古い dry-run は checker v54（3ccda575...）を記録しています。既存証跡を上書きせず、**正式 lock では v56 を含む今回の source identity に更新**してください。保存 draft に formal source はまだなく、formal_plan_locked は false です。

## source identity と分ける未決事項

以下は保存済み controls/budget draft に記録された未決事項で、ソース欠落や動的 import と混同しません。

- 共通 CF/PDE 等の数値 controls、原仕事量・展開 bytes・rates・prior budget/cap options の確定。保存 structure draft には予測の照合点が 109 件あります。
- 現パイプラインの教師・oracle の実 rate は未測定。過去の rate から正式 runtime を確定できません。
- allocation budget は未承認の candidate、budget policy は draft_not_approved_for_lock。
- 外部 10 項目の inclusive expense/alias と原 history、必要な独立レビューの完結。

このリストは hash を保存した draft 時点の記録です。同時進行する親担当の更新を完了済みと扱いません。元 121/51、全候補・比較・tiny fit は source transport の確認で金融 qualified に昇格しません。

## 実測コストと次の接続

今回の静的 source/graph probe の外側実時計は 2.497 秒、child CPU は 2.493 秒。専用テストの outer 実時計は 60.773 秒でした。RED・format 拒否を含む測定済み子プロセス区間の合計は 75.519 秒です。未計測の読取・編集・報告時間を含む全費用とは主張しません。短い source-unit 時間から正式金融 pilot の所要時間は推定していません。

次は独立 v56 レビューを受領し、親担当が controls/budget/費用証跡を確定した後、今回の固定 source と入力出所を正式 plan に結合します。正式金融実行・全 suite・Git/docs 操作は今回行っていません。

## 主な証跡

- task-5-pilot-source-snapshot-v56/manifest.json
- task-5-source-closure-red-v56.log
- task-5-pilot-source-v56-tests.json
- task-5-pilot-source-v56-ruff-final.json
- task-5-pilot-v56-ast-delta.json
- task-5-pilot-source-interface-v56.json
- task-5-formal-pilot-source-closure-v56-main3-inventory.json
- task-5-formal-pilot-source-closure-v56-main3-cost-v3.json
- task-5-pilot-v56-actual-cost-manifest.json
