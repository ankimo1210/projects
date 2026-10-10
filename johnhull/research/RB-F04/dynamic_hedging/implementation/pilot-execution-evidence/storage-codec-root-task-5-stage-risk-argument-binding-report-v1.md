# Stage risk引数照合の限定修正

- 修正はW2 check_pilot.pyのstage金融引数比較のみ。wall_cap_secondsだけを分離し、5金融引数と余分な金融キーの比較を維持。
- check_resolved_job_arguments / check_job_envelopeはAST不変。raw cap改変、resolved SHAまで書き換える改変、元prior budget差を専用試験が拒否。
- 実typed dispatchから元quote wrapperへ入り、金融workerだけ記録stubへ置換。原N1024・全65thresholds・16blocks・NaN・unknown・失敗/unknown費用メタデータ保持。RNGは禁止。
- 期待RED 1 failed / 11 passed → 最終GREEN 12 passed。既存の純metadata cap/unknown/closure 20 passed。Ruff/formatは2ファイルPASS。
- 元RED-v1は不存在oracle sentinel名によるsetup error、Ruff-v1はraw regex指定漏れ。実装前後の原ログ・費用は保全し、期待REDと区別。
- runtime closureは82源、変化はchecker1件のみ、dynamic import 0。他source/helper/root/teacherrecipeは変更していない。
- 既存stage testのrun_tinyを使う2fixtureは今回再生成していない。実金融rawのgate再検算、全suite、正式phase/budget/source独立承認は未実施。
- W1 partialとfault/cost/source由来は不変。新sourceを旧rawの生成sourceと偽装しない。Git/CAS/docsは変更していない。
