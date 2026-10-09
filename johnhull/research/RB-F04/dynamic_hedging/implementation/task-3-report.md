# Task 3 report — 2026-10-09

## Result / scope

Implemented the three owned files, without commits, shared docs/index edits,
public exports, production dependencies, or changes to existing pricing APIs:

- `johnhull/hullkit/src/hullkit/_dynamic_hedging_surfaces.py`: six exact planned
  functions; calendar call snapshots; normalized Asian/CV block price surfaces;
  ordinary derivatives from the same not-a-knot tensor cubic; quote state fit.
- `johnhull/hullkit/tests/test_dynamic_hedging_surfaces.py`: 17 small tests.
- `johnhull/research/RB-F04/dynamic_hedging/reference_methods.py`: independently
  transcribed adaptive CF, banded calendar CN snapshots, separate selected
  cutoff/adaptive-quadrature/space/time/domain comparisons, direct-payoff
  conditional MC with own adapted stock / implicit-CIR update and CRN bumps.

The main grid and formal 18-state pilot were deliberately not executed here.
This implementation is not evidence that candidate accuracy budgets are met.

## RED / GREEN evidence

First selected test collection failed with `ModuleNotFoundError` for the missing
surface module. After the initial source, all 12 planned financial fixtures
passed. Added group denominator/driver, t0 sheet/vector, and joint support tests:
13 passed / 3 failed for missing original N, ignored dedicated sheet, unsupported
array fits. Those features were implemented; 16 passed. Actual stochastic CF
versus the separate adaptive integral and state-coordinate invariance added a
17th verification test. Group memory-date inconsistency was separately observed
RED (did not raise), validated in source, then GREEN.

Final command (WSL root of this worktree):

```
PYTHONPATH=/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src \
 /home/kazumasa/projects/.venv/bin/python -m pytest -q \
 --confcutdir=johnhull/hullkit johnhull/hullkit/tests/test_dynamic_hedging_surfaces.py
```

Final result: **17 passed, 1.80 seconds**. `ruff check` passed on all three owned
files; `ruff format --check` previously passed, subsequent reference formatting
was applied. No whole suite or heavyweight grid build was run.

Checks cover node C1 derivatives, S/Q recalibration, all cubic roots/extrema
(including multiple interior roots despite endpoint brackets), no-root quote,
bound root, tangent/near-zero J, independent delta-J uncertainty, exact calendar
index, unsupported spot/state/threshold, Heston homogeneity/local log-S chain,
exact x<=0 linear claim without finite quote-fit state, 16 shared CV block
covariance, original N consistency, actual remaining-time/current-v Heston
CF, nonconstant absolute-calendar local PDE, independent PDE snapshots,
independent direct m=1 GBM MC/CRN and scalar coordinate invariance.

## Units and interfaces

- `parameters`: approved `_heston_local_surface.HestonParameters`.
- `surface`: approved `LocalVarianceGrid.evaluate(calendar_t, spots)`.
- `build_call_cache`: fixed K100/T1.25, physical spot/current-v or ell axes,
  exact date snapshots; >=4 nodes on each cubic axis. Local performs one
  sparse CN/Rannacher backward solve from T1.25 per ell, preserving absolute
  coefficients and all requested endpoints. Heston uses `fourier_surface`
  with replaced current spot/v0 and remaining T1.25-date.
- Asian production input: `{'parameters':p,'groups':[Task2_label_dict plus
  date_index]}`. Axes `dates`, `state`, `threshold` (1D shared or 2D per-date),
  and `spot` for local. All groups require the same positive original N divisible
  by 16 and shared_driver_id. Group memory_count/calendar restart and node axes
  must match exactly. Raw label dictionaries (including f_x, f_x block means,
  primitive records and statuses) are retained.
- Local groups containing t0 require `axes['t0_spot']` with >=4 near-S0 nodes;
  these populate a separate t0 sheet. The wide later-date sheet is not evaluated
  at t0. Heston's normalized sheet has no spot axis by homogeneity.
- Dense analytic fixtures may supply `f` shape `(date,[spot],state,threshold)`
  and `block_means` with trailing `(16,3)`; optional `t0_f/t0_block_means`.
  Production groups map Task2 `(16,threshold,3)` blocks to this shape.
- CV channel 2 is primary. Each block is transformed by exactly the same price
  interpolation/derivative/chain operator as the mean. Returned covariance is
  covariance of the mean of 16 independent blocks for `(price,VS,Vtheta)`;
  node errors are never treated as independent.
- Heston Vtheta is currency per variance; local Vtheta currency per ell.
  `normalized_price_greeks` local `f_state` is derivative with respect to log ell,
  and `f_log_spot` derivative with respect to log spot. Division by ell and the
  extra f_log_spot term are applied once.
- Evaluation scalar/batch returns value/spot_derivative/state_derivative/status/
  reason/error. Unknown raw prices are saved where available. Batch variable
  root diagnostics use NaN-padded numeric arrays (no object arrays).
- Fit caller attaches `call_cache['asian_state_bounds']=(asian_state_low,
  asian_state_high)` to enforce joint support. Root enumeration covers each
  cubic piece, extrema are saved, and a unique root is refined by scaled
  bracketed Brent with xtol/rtol=1e-10/maxiter100. Unknown state stays NaN;
  raw root/residual/J/condition are retained. Condition=.01/abs(J*state_scale).
  No nearest, clipping, previous-state or zero substitution occurs.
- Call caches return price_error/derivative_error NaN and reference_status
  unmeasured until independently measured. Raw PDE status/domain/damping and
  negative-operator diagnostics are retained. This does not certify precision.

## Independent reference / remaining gates

`calendar_call_snapshots` uses the independently transcribed RB-F04 banded CN
solver; absolute coefficients and exact requested endpoints are preserved.
`selected_call_refinement` compares own CF cutoff/adaptive quadrature or local
space/time/domain changes, retaining all prices, three-width derivative values,
deterministic changes, and finite-width errors. No exact/high-precision claim
is made from a successful solver status. `direct_conditional_asian` uses no
teacher CE/control; a fresh local RNG is restarted for each CRN bump, O(N)
driver storage, with original samples/N/SE/covariance and scheme error explicitly
unmeasured until separate refinement.

Task 5 must run and save the selected call/Greek precision gates, real conditional
18-state oracle/bump gates, grid doubling, N-prefix/SDE refinement and timing.
The root owner registers the module in MODEL_INDEX.md and updates shared
development docs; those files were intentionally outside this task ownership.

Ruling: independent Heston integration uses adaptive quadrature refinement
rather than pretending its independent adaptive integrator has the production
Gauss-Legendre order parameter. Cutoff and adaptive tolerance/subdivision-limit
changes are stored separately; pilot must assess the resulting measured error.
Cost if inadequate: a source revision before freeze, not a relaxed main gate.

## Independent review fix pass

Important 1: own direct MC used the implicit Lamperti root also at xi=0, which
biased the nonstationary deterministic variance path when v!=theta. A new
32-path/two-step fixed-driver regression with v=.08/theta=.04 first failed:
11/32 payoff samples differed, maximum difference .00043285. The own reference
now uses theta+(v-theta)*exp(-kappa*dt) at xi=0, keeping old-v adapted stock,
local CRN RNG and original N. No production helper is imported. GREEN: 18 tests.

Important 2: adaptive CF discarded QUADPACK errors/status. Forced limit=1
regression first failed (missing receipt interface). `independent_heston_call`
now accepts optional `return_receipt=True`, preserving both integrals' raw
values, absolute error estimates, convergence message/status, neval, actual
used subintervals and numerical settings. Errors are propagated into currency
price units. A nonconverged ordinary price is NaN; the raw finite price remains
in its receipt. `selected_call_refinement` saves every base/bump integration
receipt and estimated price/derivative integration errors separately, and
propagates any nonconvergence to unknown. Its optional quadrature_limit permits
reproducible failure inspection. Existing converged array API is preserved.
The limit=1 case now verifies unknown and retained raw finite/error diagnostics.

Final after both fixes: **19 passed, 1.78 seconds**; ruff check succeeds on all
three owned files. No fullpilot/18-state or convergence-budget gate was run.
