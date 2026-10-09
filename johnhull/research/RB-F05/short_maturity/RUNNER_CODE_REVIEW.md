# RB-F05 runner independent re-review

2026-10-09。**最終結論: Critical 0、Important 0、Minor 1（前回ATM端点、未変更）**。前回3 Importantおよび初回再レビューで見つかった同じfit lifecycle範囲の2 witnessは解消を独立確認した。以下に初回再レビューと最終確認の証拠を記録する。

## 再実行結果

最新sourceから新smokeを生成: train12/validation6/test12、N512、2 paired fits×8 updates、120 timing slots。baseline saved checker PASS、accepted=False。

前回の全9改変witnessは**全て拒否**された。

| Witness | 最新checkerの拒否 |
|---|---|
| 全teacher費用削除＋fit教師cap0 | closed expense roster |
| protocol/reference/grid/init/export/eval/timing/check費用削除 | closed expense roster |
| cold/fresh0、serialization_pending False | fixed costs/pending status |
| archive_load pending削除 | closed expense roster |
| 両fit charged False | category/charged/parent schema |
| timing receipt0＋正の保存repetitions | timing receipt below measured repetitions |
| optimizer_error 0updates/8attempts | step attempts/completed update mismatch |
| budget未満かつ全更新済のtime_cap | time_cap lifecycle impossible |
| completedをinitial_after_exception表示 | weights state mismatch |

独立のscoped既存テスト結果: **41 passed in 9.90 s**（owner報告39件の後に追加された正当cap/escaped exception fixtureを含む現時点のファイル）。`pytest -q -p no:cacheprovider --basetemp=/tmp/rbf05-runner-rereview-tests johnhull/hullkit/tests/test_short_maturity_study.py`、共有Python・WT PYTHONPATH・BLAS/OMP/MKL1thread・PYTHONDONTWRITEBYTECODE=1で実行。

再現/結果: `/tmp/rbf05_runner_rereview_probe.py`、`/tmp/rbf05-runner-rereview-probe-results.json`、`/tmp/rbf05_runner_rereview_fit_probe.py`、`/tmp/rbf05-runner-rereview-fit-probe-results.json`。

## 初回再レビューで残ったImportant（最終確認で解消）: no-step weightsとnonfinite-parameter state

### A. time_cap 0updatesのままtrained final weightsが通る

baseline fit0をstatus=time_cap、complete=False、updates=attempts=0、initial_loss=final_loss=None、batch_indices emptyへ変更。training_s/fit receiptを120秒へ変更しtotal/overrun/categorizedを再計算。**trained final weights・raw/safe predictionsはそのまま**。

checkerはpassed=True。最終重みと記録された初期重みの最大絶対差は **0.024013242566144455**。

learnerのpre-update cap branchはoptimizer.stepを実行しないため、initial_loss=Noneのtime_capは初期重みと同じでなければならない。`_fit_lifecycle`のtime_capではその照合がなく、training_exceptionだけで照合していた。初期nonfinite_loss/0 attemptsにも同じno-step制約が適用できる。optimizer_errorのfailed stepは部分mutationがあり得るため、全statusに無条件updates0一致を要求するものではない。

再現: `/tmp/rbf05_runner_rereview_zero_update_probe.py`、結果 `/tmp/rbf05-runner-rereview-zero-update-probe-results.json`。

### B. finite weightsでnonfinite_parametersが通る

baseline completed fit0の重み/objective/arraysを変えず、status=nonfinite_parameters、complete=False、reasonを変更するだけで**passed=True**。learnerは非有限parameterを検出して停止し、その後のobjective評価はparameterを書き換えない。したがってこのstatusと全exported weightsが有限という組合せは実装の結果と矛盾する。

結果: `/tmp/rbf05-runner-rereview-nonfinite-probe-results.json`。同ファイルのnonfinite_loss/finite NumPy replay witnessはbackendの数値差の余地を分け、この時点では追加Importantと断定しない。

## Scope

read-only source/test review、/tmpのみへprobe/result/report保存。main/fullpilot/freeze/Git/source/test変更は行っていない。source provenanceは新smokeに記録されている。financial pilotのレビューは別担当。前回Minorの±2sigma ATM/tail丸め分類はanalytics.pyで未変更。

## 最終確認: Critical/Importantなし

所有agentの追加修正後、さらに新しいsmokeを最新sourceで作成して確認した。前回9 witnessに加えて、上記の2 witnessも拒否された。

| 最終追加witness | 結果 |
|---|---|
| 0updates/0attempts time_capでtrained weights保持 | ValueError: zero-update fit initial weights changed or disagrees |
| 全重み有限なのにnonfinite_parameters状態 | ValueError: nonfinite-parameter fit has no observed nonfinite weights |

実際の停止経路を独立に生成して、正当な失敗の元slotが誤って拒否されないことも確認:

- learner時計を固定fixtureで進めたpre-update cap: 両fit time_cap、updates0、初期重みとの差0、saved checker PASS。
- 実optimizer.step後にlast.biasへInfを入れたnonfinite parameters: 両fit nonfinite_parameters、updates1、非有限exported weightsを保持、saved checker PASS。
- 最終scoped suite: **46 passed in 11.02 s**。`--basetemp=/tmp/rbf05-runner-rereview-final-tests`以外は上記と同じ共有Python/WT paths/1thread条件。追加suiteにはoptimizer_errorのstep部分mutationの正当fixtureも含まれ、updates0でもこれを不正に初期重みへ戻さない契約を確認した。

最新baseline saved checkerもPASS。train12/validation6/test12、N512、paired2fits×8updates、timing120、accepted=Falseのscope。fullpilot/mainの精度・六fits・採否・実費用測定は行っていない。

最終結果ファイル:

- `/tmp/rbf05-runner-rereview-probe-results.json`（前回費用/pending6 witness、全部拒否）
- `/tmp/rbf05-runner-rereview-fit-probe-results.json`（前回fit3 witness、全部拒否）
- `/tmp/rbf05-runner-rereview-zero-update-probe-results.json`（残りtimecap witness、拒否）
- `/tmp/rbf05-runner-rereview-nonfinite-final-results.json`（残りparameter witness、拒否）
- `/tmp/rbf05-runner-rereview-positive-probe-results.json`（正当cap/nonfinite停止、両方PASS）
- `/tmp/rbf05_runner_rereview_positive_probe.py`（正当停止の独立再現script）

再レビューはread-onlyで、reviewerが変更したのは/tmpの成果物のみ。費用/状態の修正は所有agentの作業。前回Minorの±2sigma ATM/tail丸めは残り、元全分母が失われる問題ではない。このrunner範囲で金融source freezeを止めるCritical/Importantは残っていない。

最終source snapshot（provenanceのみ、金融比較のSHA代替ではない）:

| Source | SHA256 |
|---|---|
| `johnhull/research/RB-F05/short_maturity/build_reference.py` | `a198d21853693bb73e6f5e86530ff4affbe72da91a39abbbff0b27d599502bd6` |
| `johnhull/research/RB-F05/short_maturity/analytics.py` | `09430708a7256774f09a73120398684db0893477111b3fd8f8af18dccc879235` |
| `johnhull/research/RB-F05/short_maturity/protocol.py` | `894a3e0d8c0efcde90d92ea165796b3e0f647bf66a205e117b73a65d66c4cf5b` |

最新baseline artifact: `/tmp/rbf05-independent-runner-smoke-1791537213017454630`。全financial source10件あり。
