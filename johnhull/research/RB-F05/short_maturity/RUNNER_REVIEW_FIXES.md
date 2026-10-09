# RB-F05 runner independent-review repairs

2026-10-09. Scope: ONLY build_reference.py and test_short_maturity_study.py. No Git, docs, sampler/teacher formula, real main sampling or6mainfits. This supplements /tmp/rbf05-runner-report.md and supersedes its earlier25test source checkpoint.

Reviewed evidence:
- /tmp/rbf05-runner-independent-review.md: Critical0 / Important3 / Minor1.
- /tmp/rbf05-runner-probe-results.json
- /tmp/rbf05-runner-fit-probe-results.json
- actual private learner's status/attempt/cap/weights behavior.

## Repairs

1. Closed original expense roster is derived from execution slots: all fixed protocol/geometry/reference/grid/prepare/evaluation/timing/savedcheck, all train/validation teacher slots, all common initializations, all fit/export/evaluation slots, and pending serialization/cold_import/archive_load/pilot_freeze/fresh. Every row must have its exact category, charged=True, no parent, nonempty scope and measured finite nonnegative seconds or requiredNone. Missing/extra/duplicate/reclassified/unpaid receipts fail even if categorized totals are recomputed consistently.
2. Teacher expense_id is bound to its original slot, generation_s is independently retained in its teacher record and compared to the required receipt. Shared generation teacher_s is the sum of these original train receipts and is bound to all fit caps; it remains charged once.
3. Cost dictionary has a fixed schema: cold_pipeline_s/fresh_s/archive_load_s remainNone; serialization_pending remainsTrue in the immutable pre-I/O financial record. Actual serialization receipt remains separate. Exact5pending IDs must remain pending; external receipt resolution cannot silently rewrite those original flags.
4. Timing charged duration must be at least the sum of its saved measured whole-call repetitions (64epsilon scale roundoff allowance); warmup/aggregation/in-memory output saving are still included in the actual outer timer.
5. Saved fit lifecycle matches the actual learner: completed attempts=updates=cap; optimizer_error/nonfinite_gradient attempts=updates+1; nonfinite_parameters increments after its completed step; time_cap attempts=updates<cap and final teacher+train time reaches the cap; initial/training/final nonfinite-loss branches are distinguished. A completed final-step/evaluation overrun is explicitly valid. Returned learner fits use weights_state=final; only the runner's escaped training_exception uses initial_after_exception, no returned observed update/objective claims, and its exported fallback equals the recorded common initial weights.

The runner's internal pre-save checker is private _check_record(...recording=True) only while measuring its own saved_check receipt. It permits exactly that one not-yet-added row, then the actual elapsed charge is added before any serialization. Public/private-study API check_record(record,arrays) always requires the full saved roster; no recording flag is accepted from the record.

## Witnessed TDD

RED:13concrete reviewer mutations were accepted (13failed tests);1positive completed final-step overrun already passed,25old tests deselected. Mutations cover omitted teachers, omitted supporting costs, pending0promotion, omitted archive, unpaid fits, recategorization, added parent, extra ID, changed teacher link, timing0, impossible optimizer counts/timecap/completedinitialweights.

GREEN:39passed in9.00s after fixes. Added only2positive lifecycle regressions to confirm preservation:
- Actual learner pre-update time cap under a controlled clock retains2original slots /0updates /0attempts /final returned snapshots.
- Escaped train RuntimeError retains2original initial_after_exception fallbacks, original reasons and no returned-fit observed updates.

Final: **41passed in9.91s, exit0**, ruff check PASS, ruff format --check2files already formatted. Existing guarded saved replay, real subprocessCLI smoke/--check/output refusal, genuine optimizer failure, numeric tamper, expired ATM/invalid original denominators all remain green. No heavy or main experiments were run.

Commands:
env PYTHONPATH=/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src:/home/kazumasa/worktrees/johnhull-research-roadmap/deep_hedge_price/src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/kazumasa/projects/.venv/bin/python -m pytest -q /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/tests/test_short_maturity_study.py
/home/kazumasa/projects/.venv/bin/python -m ruff check <ownedsource> <ownedtests>
/home/kazumasa/projects/.venv/bin/python -m ruff format --check <ownedsource> <ownedtests>

Source complete again for parent/fresh review and financial freeze. Original stochastic estimators, normalized learner map, raw/safe routes, original counts and all numeric error outputs remain unchanged. Main/fullpilot/freeze/adoption, other cost receipts and final broad suite remain parent-owned.


## Follow-up independent re-review: zero-update / nonfinite-weight consistency

The independent re-review found that a pre-initial-evaluation time_cap could
claim0updates/0attempts/noobjectives while retaining actual trained weights
(max initializer difference .02401324). The same impossible initializer
claim also applied to initial nonfinite_loss.

Witnessed RED:2mutations accepted; positive partially mutated optimizer_error
already passed. Repair: zero-update time_cap/nonfinite_loss/nonfinite_gradient
(no optimizer call) must numerically equal the recorded original initializer.
optimizer_error is explicitly excluded because a failed step can partially
mutate parameters. Escaped training_exception already has its separate
initial snapshot contract.

A further witnessed RED showed finite final weights could be labeled
nonfinite_parameters. Repair: that status must retain at least1nonfinite
exported parameter, in addition to its post-step attempt/update contract.
Actual optimizer-injected NaN weights remain failed original slots with
updates=attempts=1, raw error failed_rows12 and safe fallbacks; no raw repair
or original-slot removal was made.

Positive regressions retain actual pre-update caps, an optimizer step which
mutates parameters then raises, actual NaN post-step failure, escaped
training exceptions and completed final-step overrun.

Final checkpoint after these additions: **46passed in11.26s, exit0**.
ruff check PASS and ruff format --check2files already formatted. This
supersedes the prior41test checkpoint. Owned source/test editing is complete
again; no main/fullpilot/6fit/Git or other financial source edits.
