# Task 5 initial37 checker and conditional-call default independent review

## Outcome

Critical 0 / Important 1 / Minor 1; I1/I2 unresolved. Source approval withheld. Conditional call default change itself has no identified finding; formal pilot is not qualified.

## I1 — Important: erased original PDE attempt is skipped

At `check_initial_quotes.py:104`, absence of `<id>.prices` means `continue`. Removing actual `pde_space4801.prices` while its original37 completed receipt remains yields `integrity=pass` and `initial_quote_gate=pass`; original eight PDE stages become seven. Require complete raw arrays for every declared PDE stage; field/CF diagnostic stages may be skipped by explicit metadata type rather than absence of an expected result. Retain original failed/unknown attempts, and reject attempt erasure.

## I2 — Minor: claimed refinement replay is not implemented

The opening docstring says measured refinements are recalculated. Stage `max_refinement` and raw refinement arrays are unused: changing saved `pde2401x1920.max_refinement` to 12345 leaves integrity pass and no refinement output. Narrow that claim, or recompute actual stage-to-stage differences with saved original price arrays.

## Verified evidence

- Checker targeted tests: **8 passed in 0.42s**.
- Surface targeted tests, including new late-ATM Black example: **20 passed in 6.86s**.
- Actual NPZ: **487 arrays**, no object arrays, **37 original quotes**, **8 PDE stages**. An independently constructed time/strike→original-ID map reproduces every saved price/error, including chronological receipts.
- Separate primary/mirror restores each reproduce 487 members and the same numeric checker result. Blob SHA256 `dda742e71078be19383c4fb4209413a346c8e7259ed8e899d3288b28f0ee2591`, 30,535,323 bytes. Hashes establish provenance, not financial accuracy.
- Saved call tensors independently interpolated at all **18 states** per old/new probe reproduce local error maxima **0.00144997329261 → 0.000291248527875**.
- Both retain the **one unknown Heston case** at t=11/12, S80, v.02, condition≈0.8078254. No filtering or false Greek/reference qualification.
- RNG entry points were disabled during all saved semantic probes; no solver/training was rerun. The source has only saved array arithmetic/interpolation.

## Limits

Initial CF/PDE solver generation is not replayed. Conditional Greeks, teacher precision, Q drift, policy P&L and formal pilot remain unqualified. Surface's reference_status stays unmeasured / derivative_error NaN. Timing receipts explicitly exclude startup/final serialization and keep missing total CPU/wall values unknown. Existing CAS recovery correctly keeps financial qualification unknown.

## Source identity

- johnhull/research/RB-F04/dynamic_hedging/check_initial_quotes.py: 64fc78e2715bd12651999ea49f26a973b734997d1fc669e620402b76ccbaf209
- deep_hedge_price/tests/test_dynamic_hedging_initial_quotes.py: a3ff24e9218146c7046d521eb9fbedfe4bb170045314742f10b21fe4d25eddbd
- johnhull/hullkit/src/hullkit/_dynamic_hedging_surfaces.py: fff3bc88d497210a846956d464317d5ddb00941a1e3ef25193f9cbaa26a8c406
- johnhull/hullkit/tests/test_dynamic_hedging_surfaces.py: 55071a03a936b89a26a85bed5531f31a515d04d041491a3c737d28c2613da825

Raw targeted outputs and independent probe source/results are saved with the task-5-initial-call-review prefix.
