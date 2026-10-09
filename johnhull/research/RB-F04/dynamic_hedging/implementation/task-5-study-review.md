# Task5 study connector independent review

Reviewed at UTC: 2026-10-09T14:25:26.628661+00:00

**Result: changes required — Critical 0 / Important 4 / Minor 0.** Scoped tests: 35 passed (5.69s). Financial/main/pilot acceptance is not established.

## Bound source

- deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_study.py: 1921842da8d0a3a2951d95ec8d11be6cdeebfe37931617127a051775505ae4c3
- deep_hedge_price/tests/test_dynamic_hedging_study.py: 081b908ecaae734134b4cfc49b63edcaa168d75e48aaecc531d06138090001df
- johnhull/research/RB-F04/dynamic_hedging/DESIGN.md: 8fbef30a824aa0b4e4153ad0e559255a6fe77b102d8fde223adb25f6138248ce
- johnhull/docs/superpowers/plans/2026-10-09-dynamic-cross-model-hedging.md: f2818f56afcc8fa97b0070c6aea4c387dbb3f7be94a5ff4b03c635ddecbc17e5

## Findings

### I1 (Important) — Exact linear Asian targets still depend on an unnecessary quote fit

Location: deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_study.py lines 308, 318, 364, 444.

Evidence: A=1300,n=3,t=.25,Q=99: both model Asian values=82.58908192266331, VS=.7425528449356018,Vtheta=0,status=not_required_linear_claim; fit=no_root and U1/U2 targets are NaN.

Requirement: DESIGN section 7.1 explicitly makes scalar quote fit unnecessary for x<=0; targets are VS and zero call exposure.

Suggested correction: Compute exact linear stock/call targets and zero label uncertainty without division by missing Ctheta; distinguish claim-target validity from optional model/covariance validity. Band covariance can remain unknown when an independently required covariance cannot be assessed; do not add a nonlinear fit fallback.

### I2 (Important) — Training generator identity is not checked against its original fit slot

Location: deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_study.py lines 806, 809, 810.

Evidence: Supplying the same dataset with model=heston under both Heston/local keys produces all six fit:local:* slots with completed status.

Requirement: DESIGN sections 2,8,10 require separate training-generator IDs and preservation of the fixed 12-fit roster; a local training family cannot silently use Heston data.

Suggested correction: Check dataset model against slot training_generator before fit, retain all wrong/missing-generator attempts as reason-bearing failed slots, and update tiny fixtures to actually use separate market annotations/paths.

### I3 (Important) — Raw checkpoint identities are ignored during a labeled test-cell replay

Location: deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_study.py lines 879, 923, 926.

Evidence: Replacing fit:Heston:U2:init11 raw_fit by fit:Heston:U1:init29 raw_fit still completes cell:Heston:U2:nn:trainHeston:init11, including nonzero call actions from the U1-untrained output.

Requirement: DESIGN sections 10,13 require a fixed original training generator/universe/init/checkpoint identity and no cross-slot replacement.

Suggested correction: Bind raw_fit universe, seed/initialization, original_n, training generator and checkpoint identity to the outer fit slot before replay; reject or mark unknown mismatch with original N retained. Record missing provenance rather than inventing it. The protocol caller should validate source/selection bindings separately.

### I4 (Important) — Local band covariance samples the middle of the hedge month instead of the declared current diffusion

Location: deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_study.py lines 369, 372.

Evidence: For base_variance(t,S)=.04+.24t at t=.25, ell=1, code samples .2916667 and uses .11 instead of current .10; stock covariance is 92.12614774544511 versus 83.75104340495011 (+10%).

Requirement: DESIGN section 8 and price_covariance docstring define local continuous diffusion covariance at the current calendar/spot state, multiplied by delta-t; section 4.2 midpoint applies to an internal SDE step, not an entire monthly hedge interval.

Suggested correction: Use the current calendar field for t>0 and an explicitly defined/measured t0 early closure convention; preserve early-proxy support and uncertainty. Do not silently substitute the monthly midpoint covariance. Add a nonconstant calendar field regression test.

## Confirmed locally

- Original path counts and arrays are retained in market/risk/policy failures; full-N selection rejects unknown arithmetic/precision results.
- Quote fit uses S/Q/A/n/time and does not read actual latent market variance; 16-block labels pass through joint IFT covariance.
- Cash recursion, discounted gains, initial/interim/final spreads and one terminal claim payment agree with independent scoped cash fixtures.
- Tiny actual training preserves all 12 attempted slots, last finite weights, cap/failure metadata, train-only scaling and global NumPy/Torch RNG state.
- Missing price/derivative precision leaves arithmetic targets available with unknown qualification; bounds/root failure is not replaced with a nearest state.

## Evidence and limits

- review is source connector scope only; formal runner, test-opening authorization, full source closure, all-cost completeness, full pilot/main/fresh/CAS/notebook/final acceptance are not certified
- existing test fixtures are used to construct small smooth toy caches; independent numerical expectations for linear targets and covariance are derived separately
- original test stream not opened, no full suites run, no source/Git/docs edits, no main unrelated changes or xaa inspected

Saved raw evidence: task-5-study-review-tests.txt, task-5-study-review-probe.py/json, task-5-study-review-covariance-probe.py/json. Exact reviewed source/test snapshots are task-5-study-review-source.py and task-5-study-review-tests-source.py.
