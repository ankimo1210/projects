# Runner source independent review — original

UTC: 2026-10-09T14:49:40.230396+00:00

**Changes required: Important1 (RUN1); formal pilot/main/Task5 acceptance not reviewed.**

## Binding

- johnhull/research/RB-F04/dynamic_hedging/run_reference.py: 7458819bb3f0864f2ced8ff5b3b969ac9e9158436fb8e5cdeed376b7f18e2816
- deep_hedge_price/tests/test_dynamic_hedging_runner.py: bd7bdfc4f2022cec272a4fce4adc5ea6c0c21ce91efda6b298367295c65a833e

## RUN1 — Test artifact supplies selected checkpoint weights after test opening

An independent orchestration-only probe uses the real protocol.freeze_contract/assert_main_ready with synthetic bound pilot/review receipts and 4x14 original2048 raw validation losses. The loader then supplies weight=123 for all same-ID fit slots. run_main opens the test data and forwards that test-artifact weight to 36 evaluation calls; no pretest weights were present or bound in the closed receipts.

The actual NN used for test evaluation is not fixed by the closed train/validation selection. Matching slot labels do not bind weights/scalers, permitting post-test checkpoint replacement.

Require actual closed_fits before loader access, bind payload digest to closed selection receipts, verify all12 original slot/raw identities, detach a fixed copy before authorization, and use only that fixed copy after opening market/risk test data. Reject or compare any test-artifact fit payload without using it.

## Review boundaries

- Only bounded source checkpoint reviewed, not Task5 whole-phase acceptance
- Synthetic financial gate receipts are unit scaffolding, not a real freeze/pilot result
- Expensive study evaluation is replaced at its consumer boundary solely to observe which actual fits the real runner forwards; no pricing/training performance is inferred
- Initial check_bundle does not certify earlier market/teacher SDE, independent train-only scaler, training-to-weights linkage or original timing linkage; final source must state those limits rather than delegating unverified scope to caller JSON
- No runner/source/Git/docs edits; study was not rereviewed by its implementer
