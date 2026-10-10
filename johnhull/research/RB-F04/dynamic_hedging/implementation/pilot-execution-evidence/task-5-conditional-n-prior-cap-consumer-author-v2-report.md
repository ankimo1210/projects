# Conditional N prior-cap consumer 最小修復
2026-10-10。**実装・scoped検証完了、独立承認待ち。**

## 変更

- check_pilot.py:4023のoption選択へ、親IDに加え「capを除くplan全欄が具体化baseと一致」を追加した。同じ親の先頭N枝を誤選択して後続の正しい4N枝を拒否する欠陥を修復。
- 既存 test_dynamic_hedging_pilot.py にmetadata専用22ケースを追加。原N1024/4096/16384/65536、枝順序反転、複数実親capの順序/全binding/inclusive費用、欠落枝・template/producer/expense/未来selector混入・親status/caplimit/decision改変拒否、縮小N拒否、uncapped固定N互換を確認。
- 元option列順・最初の互換親を保持し、global唯一親の新条件を導入していない。元metric/limit/計画時刻/decisionSHA・全parent証跡・expense scope・失敗/unknownも保持。

concrete_original_n_planと正式callerのselector pop、execution._review、公開API、数学/solver/codecは不変。実selector hashは結果rowだけに置く元契約のため、静的template＋N＋既知template hashで事前decisionを結合できる。

## 実検証

- RED: 8 failed / 14 passed / 191 deselected（旧sourceで同親4N/plural枝誤選択を検出）。
- GREEN: 追加22 passed / 191 deselected、1.55s。
- 関連する既存metadata conditional/cap/expense/source境界: 16 passed、2.02s。
- Ruff・format: 変更2ファイルPASS。既存test全functionのAST不変。
- runtime closureは実81files / dynamic0、checkerだけが変更、他80fileのbytes不変。checker変更functionは _prior_execution_projection のみ。

最初のpytest収集はPYTHONPATH不足で失敗したため、既存WSL runtimeとworktreeのsrcを明示して再実行した。Ruffの新test未使用変数とformat修正の途中失敗も、原log/費用を保持。原有意REDと最終GREENは別証跡。

## 固定

- checker SHA: 952b8f89c930578db1f6531bd6e73ade947d7cfbef246cc8510d246a54ed6197
- 既存test SHA: e183f20b876cee2684b9a78bba7b3e00755210740e0758d3efdfcd46301e8d83
- runner._digest(actual identity): dc7631fe73a457cd995d109aa693be9401b266410b9f53aa4e2d51e59f56d39c
- 旧identity408f2bc2…/checker a37626ff…は source-before、closure-before と旧証跡に保全。source-after/closure-after/source.diff/results/decision/manifestへ新固定を保存。

実金融pilot/RNG/SDE/CF/PDE・全suiteは未実行。今回のsource著者検証を正式budget/phase又は金融資格の承認へ広げない。Git/docs/CASはroot担当。次は独立レビューと新sourceへのprior/candidate再結合。
