# Task 5 replay R1/R2 fix

## Implementation

- R1: A shared `_check_original_counts` validates every supplied canonical `original_n` and alias `original_path_count` against raw array N. Market/cash inputs use it, as do supplied cash-cell counts. Complete alias declarations are accepted; erased original paths are rejected.
- R2: Shared global driver identity now binds `global_steps` as well as original N. Per-date start/stop and aggregation remain checked individually; a real same-grid two-date example with aggregation 32/64 remains accepted.
- Owned source/test imports were sorted and an existing unused `deepcopy` removed after Ruff reported those issues.

## Evidence

- RED against original source: **5 failed, 5 passed, 62 deselected in 0.75s**, the expected missing-rejection failures.
- GREEN before import cleanup: **72 passed in 0.83s**.
- GREEN after cleanup: **........................................................................ [100%]
72 passed in 0.85s** (process wall 1.347324s).
- Ruff on both owned files: **All checks passed**.
- Final source SHA256: `85f2138a921e623a5748c9f8889b3c4a447b07a6eac7bb255136c0dd46ad87b5`.
- Final test SHA256: `10e19ce9e89de22ca5dc33f6158698fcb00015240dd9934a9f936024841fb70f`.

Original `task-5-replay-review.*` and original independent probes remain unchanged. Exact before sources, `task-5-replay-fix.diff`, `task-5-replay-fix-source.json`, RED/GREEN and initial/final Ruff outputs are preserved alongside this report.

## Remaining boundary

**Independent re-review is pending.** This implementation report is not source approval or formal pilot acceptance. No full suite, index/docs or Git mutation was performed. Fixed sixteen-block teacher semantics and explicit unknown earlier-SDE/global-driver generation boundary remain unchanged.
