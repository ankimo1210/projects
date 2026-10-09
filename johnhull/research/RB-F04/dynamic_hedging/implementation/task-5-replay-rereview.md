# Task5 replay independent rereview

UTC: 2026-10-09T14:55:18.912052+00:00

**Source boundary approved: Critical0 / Important0 / Minor0 / unresolved0. Formal pilot/main acceptance is not approved by this review.**

## Bindings

- deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_replay.py: d52ac6ee48b9eb638701f35d08732fcfe9ada436c4d0f31a2d47cfb170589b61
- deep_hedge_price/tests/test_dynamic_hedging_replay.py: 5d257a9eb7ab191ac7a3153e588b90acf52624504d35ae5878694da59726801a

## Original findings and extra cases

- R1: resolved: all provided dataset and cell population aliases are checked against unsliced raw path axis
- R2: resolved: every group sharing global ID has one original N and one global grid length
- Scoped 82 tests PASS (0.76s).
- Independent manual 2asset/CF/event-fee cash gives discounted P&L 3.076956452050289; replay gives 3.076956452050294.
- All dataset/cell original_n/original_path_count mismatches reject; mixed shared global768/1536 mapping rejects.
- Unknown call price/CF contributes zero only for zero exposure/entitlement. Nonzero liquidation and invalid raw action remain unknown; no zero/hold repair.
- RNG creation and seed calls were forbidden throughout the independent numeric probe.

## Boundaries

- Replay derives primitive final-step flags/coefficient/auxiliary metadata and checks compact code/legend/status plus original N; earlier SDE/actual random values remain unverified.
- Numeric label/cache/quote checking does not measure independent pricing, Greek, root/field/variance bias or financial suitability.
- Cash boundary independently checks recurrence, discounted gain, all event fees, one terminal claim, original declarations and supplied zero-input masks; raw policy target origin, model calibration and market accuracy remain external.
- Stats uses fixed saved indices and paired statistics; numerical envelope truth, all3init IUT, training/full-expense/source closure/formal pilot/main/fresh/CAS/acceptance are not certified.
- Only exact existing scoped suite and independent small probes were run; no full suites/source/Git/docs/index edits. No self-rereview of my study fixes was performed.

Evidence: task-5-replay-rereview-tests.txt, task-5-replay-rereview-probes.py/json/stderr.txt.
