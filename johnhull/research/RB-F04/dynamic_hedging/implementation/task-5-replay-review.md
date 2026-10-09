# Task 5 saved-only replay independent source review

Reviewed source SHA256: `9966db6c4b98a211d186657b96acb37dd5f9101a98c055853ec7638d3e13a860`
Reviewed tests SHA256: `771f3f0b0721cf0588b9d2320904ca9a9e6daef594a5b88cbb95cebd74c85fd7`

## Outcome

Critical 0 / Important 2 / Minor 0. Source approval withheld pending R1/R2. Formal pilot and phase acceptance are outside this review.

## R1 — Important: dataset original denominator can be erased

`_market_arrays` (line 319) derives N from saved arrays and ignores canonical `original_n` and `original_path_count`. `check_cash` accepts declared original N=2 with only one saved path and returns N=1, `qualification=verified`. `check_market` checks only the alias `original_path_count`, not study's canonical `original_n`.

Require every supplied denominator declaration to match raw array N; check supplied cell declarations as well. Add market/cash tamper regressions for both names. Failed original rows must remain in the arrays.

## R2 — Important: contradictory shared global grid is accepted

`rebuild_asian_cache` (line 250) accepts one `global_driver_id` with mixed global lengths 768 and 1536 if start/stop/aggregation are changed proportionally so sliced dates still agree. One named global array cannot have two lengths.

Bind original N and global step count once for the shared driver; retain per-date slice/aggregation maps, and reject contradictory global lengths.

## Evidence

- Scoped target suite: **62 passed in 0.72s**, process wall 1.0392s. Raw output: `task-5-replay-review-tests.txt`.
- Independent tamper probes: `task-5-replay-review-probes.py` / `task-5-replay-review-probes.txt`. Canonical `original_n` and alias both reproduce R1; proportional calendar map reproduces R2.
- Tests cover scalar/coefficient/status/aux tampering, original failed rows, actual quote/fixing memory, independent cash/costs/liquidation, statistic counts/ES95/CI tampering, RNG and solver prohibition, missing cache nodes, generator streams and summary-only cache retention.

## Verified boundaries and limits

- Teacher rederives final coefficients, auxiliary control/loading, one-step restart conditions, analytic/deterministic flags and primitive labels. Compact uint8 status code/legend/shape/prefix are checked without Unicode expansion; all-failed attempts retain original N and raw flags.
- Cache reconstruction retains common block summaries and global/slice bindings; complete Cartesian missing nodes remain NaN/unknown. It drops N×threshold samples across nodes, though one replay node uses samples transiently.
- Market reads saved call tables and rederives observations/payoff/gains. It does not certify prior SDE or call accuracy.
- Cash recurrence and discounted gains independently agree; zero-fee counterfactual and ex-dividend/terminal-mid handling are tested. Boundary accounting approval does not prove policy or market qualification.
- Statistics consume saved stratified indices and original losses, preserving failures/counts and conditional numerical-envelope qualification. No RNG, simulation, training or CF/PDE solve is invoked.
- N=1 exact-linear teacher replay is rejected by the fixed sixteen-block label API. Formal teacher prefixes are sixteen multiples; this is a domain limit, not a counted finding.
- Source closure, expenses, train-only scaler, validation selection, fresh replay and full pilot reductions remain study/runner responsibilities.
