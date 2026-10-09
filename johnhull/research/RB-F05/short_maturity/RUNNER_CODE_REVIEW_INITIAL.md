# RB-F05 short/0DTE runner independent review

2026-10-09。読み取り専用レビュー。結論: **凍結前に変更必要。Critical 0、Important 3、Minor 1。**

対象: `/home/kazumasa/worktrees/johnhull-research-roadmap` の `build_reference.py`、`analytics.py`、`protocol.py`、`test_short_maturity_study.py`、関連 private teacher/learner と protocol/reference tests。正式 design/plan と johnhull/AGENTS.md を照合。`pilot.py` の実装レビューは別担当であり、ここでは扱わない。Git、main/full pilot、外部通信、source edits は実施していない。

## Important 1: 費用 roster・charge・保存 timer の整合性が拘束されない

位置: `johnhull/research/RB-F05/short_maturity/build_reference.py:1406` 付近の費用検証。`analytics.expense_totals` は渡された rows の集計を正しく行うが、runner checker は必要な roster、各 row の category/charged、teacher の expense_id との対応を検証しない。fit receipt の seconds と stats の training_s の一致だけでは、実際の研究費用や fit cap へ教師費用を課金したことを保証できない。

許可された小さい smoke の原始配列をそのまま保持し、JSON を以下のように変更した。**全て check_record が passed=True**:

- train/validation の教師 receipt を全削除し、`costs.shared_train_teacher_s` と各 fit の `teacher_s` を0へ変更。各 fit の time total/overrun と費用合計を再計算。18教師の labels/moments/draws は残るのに、教師費用0・fit capにも0が通る。
- protocol/geometry/reference/grid/prepare/initialization/export/evaluation/timing/saved_check receipt を全削除し、合計だけ再計算。fit＋teacher と pending rows しか残らなくても通る。
- fit receipt 2件の `charged=False` として合計を再計算。stats の測定時間は正でも両 fit の全費用を除外できる。
- `timing` receipt の seconds を0へ変更して合計再計算。120 timing rows の measured repetition 合計は **0.06288719654548913 s** なのに、whole timing費用0が通る。

影響: main-only/cold/各独立導入の費用、教師生成を含めた120秒cap、strong baselineとの回収判定を過小評価できる。full pilotで financial sourceを凍結する前の修正対象。

修正要件: execution と元 teacher/fit/pair roster から必要な expense IDs・category・charged・scope/測定またはpending状態を拘束し、teacher.expense_id が自分の元 slot の唯一 receipt を指すことを確認する。shared train teacher はその receipt IDs の合計から再計算する。timing receipt は保存 measured repetitions 合計以上であることを適切な丸め余裕付きで拘束する。内部の初回 saved_check が receipt を追加する前に実行される現状は、保存前段階を明示的に扱い、最終保存結果全体への omission許容にしない。

再現: `/tmp/rbf05_runner_review_probe.py`、結果 `/tmp/rbf05-runner-probe-results.json`。timing0 probe は上記と同様に receipt `id=="timing"` の seconds を0とし categorized/main_only を再計算するだけ。

## Important 2: 未計測費用を0へ昇格した情報・archive load欠落が通る

位置: 同ファイル `build_reference.py:1416` 付近。pending check はserialization/cold_import/pilot_freeze/freshのIDだけを求め、cold/fresh/serialization statusとarchive_loadを照合しない。

原始配列を保持して以下のJSON変更を行い、**両方 passed=True** を再現:

- `costs.cold_pipeline_s=0.0`、`costs.fresh_s=0.0`、`costs.serialization_pending=False`。対応する expense rows は None/pending のまま。
- `archive_load` pending receiptを削除して categorized を再計算。

影響: 未計測はpendingであり0ではないという仕様に反し、保存表示がこの costs metadataを信頼すると cold/fresh/保存状態が虚偽になる。weights/archive load を全費用の外へ消せる。

修正要件: pending expense rosterはarchive_loadを含め完全一致で検証する。現在の runner はcold/fresh未実行であるため値はNone、serializationは別bound receiptを読むまでpending=Trueという実際のライフサイクルを拘束する。後続receipt導入時は測定状態と値を整合的に解決する。

再現: 同じ `/tmp/rbf05_runner_review_probe.py` の `promote_unmeasured_cold_fresh_serialization_fields_to_zero`、`remove_archive_load_pending`。

## Important 3: 不可能な fit 更新数・失敗理由・weights state を saved checker が認める

位置: `build_reference.py:1232`–`1280` 付近。checker は `0 <= updates <= attempts` と completed/status の単純な同値だけを確認し、learnerの実際の停止規則を検証しない。

baseline の fit0 は8 updates/8 attemptsでcompleted、teacher+training=**0.6421379741514102 s**、budget=120 s。原始配列・重み・objective・batchesを保持し、以下の単独変更をした。**全て passed=True**:

- updates=0、attempts=8、status=optimizer_error、complete=False、reasonを失敗文に変更。learnerは失敗した最初のoptimizer.stepでbreakするため、8 attemptsなら7 completed updatesが必要であり、0/8はこの実装では生成できない。
- status=time_cap、complete=False、reasonをcap文に変更。全8更新終了かつ測定合計0.642秒/120秒なので、実際のcap branchと矛盾する。
- completedのまま `weights_state="initial_after_exception"` に変更。runnerが保存したfinal weightsとの状態が矛盾する。

影響: paired比較で実update数や失敗slotの理由を信用できない。source freeze/main後の保存checkerが original failure/unknownを保つという契約を満たさない。

修正要件: statusの許可集合、status毎のupdates/attempts/completion/reason/objective制約、time_capの実測時間との関係、weights_stateとtraining_exceptionとの対応を検証する。training_exceptionの0 attempts/0 updates/初期weightsは元のpaired initializationと数値照合する。再学習・optimizer再実行は不要。

再現: `/tmp/rbf05_runner_fit_probe.py`、結果 `/tmp/rbf05-runner-fit-probe-results.json`。

## Minor 1: ATM bucket の±2sigma endpointが丸めでtailへ移る

位置: `analytics.py:219` の `abs(log(S/K)) <= 2 sqrt(W)`。固定testの±2 scaled distanceはexp→logの丸めにより片側または両側がtailへ移る。

決定論的 `_fixed_test_inputs(candidate_protocol())` の各time no-event先頭17 scaled slotsでATM indexが本来4..12に対して、1/15/30/60分は5..11、5/240分は5..12になる。元rowはtailに残るので全分母は失われないが、同じscaled endpointのbucket分類が時刻で変わる。

事前の境界丸め方針を固定し、spot endpointの既存許容同様に微小丸めを認めるか、元scenario distance metadataからbucketを定義すると解釈が安定する。必須の数値精度問題ではなくMinor。

## 独立確認の証拠

- scoped既存 runner tests: **25 passed in 8.47 s**。実行 command:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src:/home/kazumasa/worktrees/johnhull-research-roadmap/deep_hedge_price/src \
/home/kazumasa/projects/.venv/bin/python -m pytest -q -p no:cacheprovider \
--basetemp=/tmp/rbf05-runner-review-tests johnhull/hullkit/tests/test_short_maturity_study.py
```

- 独立 smoke: train12/validation6/test12、teacher N512、paired2 fits×8 updates、120 timing slots。baseline checkerはpassed=True、accepted=False。financial source registry全10件存在。
- 保存compact教師を独立に512行へdense展開して NumPy直接統計を計算。保存mean/M2/covariance/SEに対する最大絶対差は **1.0436096431476471e-14 / 2.1316282072803006e-12 / 4.163336342344337e-15 / 4.616657255280602e-16**。このscopeで教師モーメントの不一致はない。
- code/test照合により、numeric freeze前のmain RNG/learner拒否、original12 test indices、raw/safe分離、expiry ATM Greeks NaN、invalid/OOD counts、same scalar priceのDelta/Gamma、Hermite node再生成、Merton/density/独立mixture・NN replay・48 buckets・保存benchmark outputsの再計算を確認。
- `hull-derivatives` のGreeks参照を使用。main価格精度・Delta改善・Gamma利用・標準高速器採用の判定は行っていない。

## 境界・未検証

full MC pilot、正式source freeze、main512/128/336・六 fits、cold import/archive load/fresh・回収・実3図は未実施。別担当が修正中のpilot checkerはレビュー対象外。外部・Git・production dependency変更なし。保存配列の金融比較は許容差であり、SHAはsource/provenanceの記録だけに使用した。

本findingは以下baseline source snapshotに対するもの。後続修正後は新しいsmokeを作り、RED回帰とGREENを確認してからfullpilot/source freezeへ進む必要がある。

| Source | Baseline SHA256 provenance |
|---|---|
| `johnhull/research/RB-F05/short_maturity/build_reference.py` | `8ee5d07b79ac4f17229da3d6bd3244f00610a5dabc69f2feb31fac55f1803175` |
| `johnhull/research/RB-F05/short_maturity/analytics.py` | `09430708a7256774f09a73120398684db0893477111b3fd8f8af18dccc879235` |
| `johnhull/research/RB-F05/short_maturity/protocol.py` | `894a3e0d8c0efcde90d92ea165796b3e0f647bf66a205e117b73a65d66c4cf5b` |
| `deep_hedge_price/src/deep_hedge_price/_short_maturity_dml.py` | `bf28b110f1706668d8d206651a7ceafd8c58ad637c7279355e1f738ea17a720b` |

Baseline artifact directory: `/tmp/rbf05-independent-runner-smoke-1791535773583769635`。
