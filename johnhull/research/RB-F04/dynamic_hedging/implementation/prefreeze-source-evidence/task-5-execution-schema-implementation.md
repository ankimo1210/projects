# Task 5 A — separate execution schema implementation

2026-10-10. Bounded source implementation, independent source review pending.

## Scope and result

Only the new private execution module and its dedicated test file were changed.
Legacy protocol, runner, canonical documents, public API, dependencies and Git
were not changed by this subtask. No formal pilot, market/test RNG, training,
actual readiness freeze or financial qualification was run or approved.

- Original v1 candidate/roster, gates/seeds and all original main obligations are
  included verbatim under original_candidate/original_roster.
- Original pilot cases are 37 quotes + 36 model/state cases + 44 tiny cells +
  four deterministic pilot fit IDs (init11 × G2 × U2) = 121. All twelve full
  training slots remain independent mandatory closures.
- Required pilot teacher/Q/refinement/frequency/source/replay/cost/premium
  obligations have 51 explicit IDs, measured gate tables and independent
  per-case/group decisions. An aggregate review flag cannot replace them.
- Fixed Asian domains retain the B axis spelling spot/state/threshold and
  contiguous original-node indices of at least four nodes. Lower-case model
  conversion and physical endpoint/cache-sheet checking belongs to the raw
  cache checker; all supplied domain metadata is detached and digest-bound.
- Structural rejection excludes solver/source failure. Ill-conditioned
  rejection requires the unchanged measured κ>.25, with the original date.
  Gate failure/unmeasured reason can close as unknown; measured all-PASS cannot
  be called precision failure.
- Every required current cost has wall/CPU/overrun measurements. Prior unknown
  costs remain None, separate from legitimate measured zero. Failed caps need
  predeclared metric/limit, consumption, cost match and separately bound prior
  independent budget review.
- Original ordered test precision projections are retained. Smallest-qualified
  N uses the first qualifying original projection. If none qualifies, the new
  branch requires precision_selection=unavailable and research N32768.
- Main guard checks all12 fit attempts and all4 original validation selections,
  8192/2048/512/300s rules, full baseline candidate roster, no rescue fallback.
  All failed bands/baselines remain None plus reason.
- This freeze schema is rb-f04-execution-freeze-v1.1. Strict v1 is untouched;
  original_v1_financial_qualification=not_claimed. Execution readiness and
  financial qualification are separate fields.

## Interface

execution_candidate() -> dict
freeze_execution(candidate, source, pilot, review, selection, domains) -> dict
assert_execution_ready(frozen, candidate, source, selection_receipts) -> None

Returned frozen values are JSON-detached snapshots. Digests detect mutation
rather than making Python dictionaries physically immutable.

The dedicated tests expose execution_fixture(), closure(f,frozen) and
seal_closure(f,frozen,receipt), explicitly synthetic metadata. They are reusable
by runner tests without a financial pilot or fresh/main data.

## Verification

Initial RED: 37 failures for the absent execution module, preserved in
task-5-execution-schema-implementation-red.txt.
Independent classification issue: a resealed all-PASS quote could claim
measured_precision_failure; one test failed with DID NOT RAISE. A local guard
was added, while reasoned None uncertainty remains unknown. RED preserved in
task-5-execution-schema-implementation-classification-red.txt.

Scoped final: 50 passed in 0.99s.
Ruff check: PASS. Ruff format --check: PASS (two files).
No broad suites or optional experiments were run.

Source SHA:
473d1352fbcebd2c1255e093e1d4757274c7e51a04add5d6f00c58850c229494
Dedicated tests SHA:
27b5eaca7dec461bb2f4d2360dd263c58df254d82ff41a11ef8620fbdba3a508
Unchanged strict v1 protocol SHA:
5f63d5871cdf6871f83fb08bf8f403b556cf6730c40430c0fc391f5da29bda0f

## Remaining boundaries

This is an evidence-binding guard. It does not read/check source bytes,
authenticate independent humans, recompute raw numerical measurements or
prove that a claimed experiment actually ran. Raw financial and import-closure
checkers must verify those facts before issuing source/pilot/selection closure
receipts, including actual N/grid/refinement work and original unknown history.
Digests are provenance bindings, never numerical accuracy certificates.

Main evaluation must still preserve original denominators, original raw paths,
all44cells×3seeds×3levels (396 slots), all12fits, Q/refinements, premium, costs,
fresh/CAS/saved replay, three plots, notebook, full suites/final acceptance/main
integration. A guard accepting an unknown financial outcome does not waive any
of these deliverables or permit a supported primary/speedup assertion.
