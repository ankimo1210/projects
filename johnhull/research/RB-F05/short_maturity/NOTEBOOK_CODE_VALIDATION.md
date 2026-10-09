# RB-F05 short-maturity notebook implementation

2026-10-09. Own files: `johnhull/research/RB-F05/short_maturity/build_notebook.py`, `johnhull/hullkit/tests/test_short_maturity_notebook.py`.

## Interface

`build(artifacts=HERE, output=None, *, source=HERE, execute=False) -> Path`.
Default output `short_maturity_dml.ipynb`. CLI `--artifacts DIR --source DIR --output FILE [--execute]`.
Portable artifact/source overrides: `JOHNHULL_SHORT_MATURITY_ARTIFACTS_DIR`, `JOHNHULL_SHORT_MATURITY_SOURCE_DIR`.
Calls actual loader `load_result` and `check_record(record, arrays)`; no fresh path. The fixture loader deliberately probes forbidden entries inside the checker.

Three deterministic code figure cells and `nbplot.setup`: teacher SE/true error/rare counts; all raw NN paired-seed C/Delta/KGamma/error/expiry diagnostics; strong baseline accuracy and saved online/research/cold expense scope. Full fit/row/teacher denominators and failed/nonfinite rows remain. Optional saved raw/safe time/event/ATM buckets displayed without synthesizing absent fixture buckets. Unknown pipeline/payback/adoption remains unknown. Serialization receipt is separately displayed without mutating original accounting.

## Witnessed RED -> GREEN

RED `pytest -q johnhull/hullkit/tests/test_short_maturity_notebook.py -x`: missing builder file, 1 failed.
GREEN same target: 4 passed (5.10s final). Real nbclient fixture execution yields exactly 3 PNGs and zero cell errors.
Final commands run in WSL WT with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, `PYTHONPATH=<WT>/johnhull/hullkit/src:<WT>/deep_hedge_price/src`, `/home/kazumasa/projects/.venv/bin/python`.
`ruff format` and `ruff check` for the 2 own files: PASS.

Guard probes: NumPy default_rng/normal, scipy minimize, Torch manual_seed, learner train, Adam step, urllib urlopen all raise Artifact-only. Reserved-ledger SeedSequence provenance recomputation is allowed; no sample generator is allowed. Network HTTP request, model initialization RNG and main study generation are also blocked.

## Visual QA / limits

Viewed 3 fixture PNGs at `/tmp/rbf05-short-figure{1,2,3}.png`: readable labels/legend, zero analytic teacher observed MC, failed fit5/time_cap retained, unknown cold cost clearly separated. Fixture is explicitly mode smoke; no formal main data or performance conclusion. Actual runner smoke/main integration and real-main visual QA remain for root after financial freeze/main instruction. No formal notebook generated in repo; no fullpilot/fullmain/Git operation.

## Separate pilot fix completed during this task

Parent requested the independent-review expense-gate fix. Own prior `pilot.py` and `test_short_maturity_pilot.py` were temporarily authorized. RED 5 failed/2 passed confirmed deletion/forged scopes/unregistered extra timers passed. GREEN 29 passed (2.21s), ruff/format PASS. Root/case/stream complete status-specific timer keys and fixed cost/run scopes are now required before one-to-one expense reconstruction. Clock/reference/raw mathematical failures keep their measured receipt requirements. No numerical sample/price/time value or fixed roster changed.
