# Task 5 initial37/call checker independent re-review

## Outcome

**Critical 0 / Important 0 / Minor 0 / unresolved 0.** Original I1/I2 are resolved. Proceed with these source components within their declared saved arithmetic boundaries. **Formal pilot, Greeks, Q/P&L and phase acceptance remain unqualified.**

## Original findings

- **I1 resolved:** every declared PDE stage requires prices, IDs and errors; duplicate attempt IDs are rejected. Deleting actual `pde_space4801.prices` now fails. Actual **8 original stages / 37 quotes** survive standalone and both CAS checks.
- **I2 resolved:** all **7 refinement pairs** are recomputed from the two complete original37 saved price vectors and compared with raw refinement arrays/reported maxima. Fake max=12345 fails. Separate arithmetic reproduces all seven maxima by tolerance.

## Evidence

- Changed checker target tests: **16 passed in 0.81s**.
- Unchanged surface source/test retain the previous same-SHA **20 passed in 6.86s**, including independent late-ATM Black price and unmeasured derivative status.
- Initial evidence: **487 arrays**, 37 original quotes, 8 PDE stages, 7 refinement pairs.
- Selected before/refined: **18 states each**, local price error **0.00144997329261 (FAIL) → 0.000291248527875 (PASS)**, **one Heston unknown each**. Altering that saved unknown to ok fails.
- Independent separate primary/mirror restores cover **6 artifacts**: initial raw NPZ and before/refined call NPZ from each store. All restored semantic checks pass within scope; formal qualification remains unknown.
- Saved probe RNG entry points disabled. No source generation, CF/PDE/SDE solve, training or network execution occurred.

## Limits

The new selected-call checker explicitly reuses the existing reviewed spline/root helpers, so it is an arithmetic replay rather than a second independent root algorithm. The original review separately interpolated all18 saved tensors and reproduced the unknown Heston condition≈0.8078254 at t11/12,S80,v.02. Stored Q and independent-PDE grids are inputs; their earlier generation is not re-certified. No hash is used as financial truth. These approvals do not qualify the whole dynamic pilot or publishability.

## Source identity

- johnhull/research/RB-F04/dynamic_hedging/check_initial_quotes.py: 7fe16943f2ead6dbe17a17e969930afde863681ed9eb24b9ea8b7b18c4a004d4
- johnhull/research/RB-F04/dynamic_hedging/check_selected_calls.py: 681548eb4753946fe6c896a588b2314cb47e85736f347ca92ee2d2513a46f9a1
- deep_hedge_price/tests/test_dynamic_hedging_initial_quotes.py: 1bc212184fe080f1074f37715f879b64adcd58a586ea52b77af0a2f8f30b3091
- deep_hedge_price/tests/test_dynamic_hedging_selected_calls.py: f3b0363939ac00edd50c69c502c03db96b1b5099dffaf1d8280ffb88c25e4b0b
- johnhull/hullkit/src/hullkit/_dynamic_hedging_surfaces.py: fff3bc88d497210a846956d464317d5ddb00941a1e3ef25193f9cbaa26a8c406
- johnhull/hullkit/tests/test_dynamic_hedging_surfaces.py: 55071a03a936b89a26a85bed5531f31a515d04d041491a3c737d28c2613da825

Exact raw target outputs/probes and original review records are preserved in the same ignored task directory.
