# RB-F05 core / protocol cross-review
Date: 2026-10-09. Scope: read-only review of private core and candidate protocol; own learner excluded.

## Result

**Critical / Important findings: 0 for the current canonical candidate.** The implemented clocks, conditional / raw Greek identities, IID compact-prefix moments, seed separation, and candidate→main pre-draw guard agree with the approved synthetic v1 design. This is not approval of full pilot / numerical freeze / main execution, which have not been exercised here.

Reviewed:
- johnhull/hullkit/src/hullkit/_short_maturity_teachers.py
- johnhull/research/RB-F05/short_maturity/protocol.py
- corresponding core / protocol tests
- docs/superpowers/specs/2026-10-09-short-maturity-dml-design.md
- docs/superpowers/plans/2026-10-09-short-maturity-dml.md

SHA256 at probe time:
- core: a51a5850fa11666e07019af5efd644124be2f36f7396d84a8292bc7755879b37
- protocol: 02b705d568e1fa04f76541f3f263a99979982e2962e55dcf0e2c359ede65dbdf

## Checks and evidence

1. **Clock / compensation.** ACT/365 uses UTC seconds; the independent session integral normalizer is .15×2+.70×.5+.15×2=.95. Integrated variance is .20²/252 times the remaining normalized integral. Pulse count is .028×min(remaining_minutes,30)/30. Core and protocol agree at 10 cases from expiry to 390 minutes, including both U-clock breaks; largest absolute variance difference 2.71e-20. Equivalent UTC / NY instants produce the same state. Terminal log drift includes −Lambda×expm1(mu+.5 sigmaJ²), so the jump exponential is martingale-compensated while the compound-Poisson log variance is Lambda(mu²+sigmaJ²).

2. **Greeks.** Conditional C/Delta/Gamma integrate the Brownian variable while keeping the count and aggregate jump mark fixed. Gamma is D exp(a) phi(d1)/(S sqrt(W)). For terminal S_T and original Brownian Z, raw LR-PW Gamma is D S_T 1{S_T>K}(Z/sqrt(W)−1)/S²; LR2 Gamma is D payoff(Z²−Z sqrt(W)−1)/(S² W). These are derivatives at fixed contract/clocks/jump law, with no individual-label clipping. Six small deterministic normal-density integrals at 1,30,390 minutes and count0/count1 agree with conditional / independent analytic Gamma within 5e-14 absolute in this probe. Expiry ATM ordinary Greeks remain NaN plus a reason; naive path Gamma0 is explicitly a negative control.

3. **Mixture / tails.** The n-th lognormal term uses a_n=carry−kappa Lambda+n(mu+.5sigmaJ²), variance W+n sigmaJ². The stored conservative C/Delta/Gamma tails follow the tilted Poisson mean Lambda exp(mu+.5sigmaJ²); the Gamma upper bound uses sqrt(W), valid since component variance is at least W. Lambda0 has one deterministic term / zero tail. This portion was checked algebraically plus the existing meaningful reference / tail tests, not through a new large experiment.

4. **Compact IID / prefix.** All original N counts are sampled; normal draws occur only for active counts. The saved active indices preserve original ordering and zero-block multiplicity. The Chan correction m(N−m)/N outer(mean_active−zero,mean_active−zero) reconstructs the joint M2; denominator is N−1 and each SE denominator is N(N−1). A fresh tiny N4000 probe, with 101 active counts, matched reconstructed means/covariances against an expanded sample at prefixes2/111/1000/4000. Each prefix correctly retains actual_random_draws=4101; prefix_equivalent_draws is separately2/112/1018/4101. Lambda0 under a default_rng trap reserves4000 slots but has count0, no RNG, drawcost0, deterministic SE0. Positive Lambda with no observed events retains the original N and rare_event_unobserved classification.

5. **Candidate / seeds / geometry.** All3870 current slot IDs and concrete seeds are unique. Scenario/count/mark/raw Brownian/fit batch/fresh roles are separated; fixed main initialization seeds11/29/47 are explicit paired slots. Pilot train512 and validation128 use different streams with exactly balanced event labels. Fixed test336 retains8 maturities×2 event regimes×21 distance positions, including original ATM / tails. Candidate main train/validation/test all raise before default_rng under a trap. The new N2^20 candidate is a pre-freeze design change supported by the parent's independent price-SE probe; no main observation was used.

6. **Freeze topology.** Missing source files are not silently skipped. A full pilot record, source registry, conditions, raw-array digest, concrete seed ledger, and independent approved review are bound before assigning the chosen teacher N. scenario_inputs(...phase='main') asks for frozen metadata plus saved numerical pilot evidence before sampling. The actual numerical pilot checker and end-to-end lifecycle remain unverified at this development point.

Probe artifact: /tmp/rbf05-cross-review-probes.json. Read-only Python probe used the existing .venv, scoped PYTHONPATH and BLAS threads1; exit0. No full suite, heavy experiment, Git, or repository writes were performed. The first probe had a local reviewer call-site error (treated conditional_values ndarray as a dict); correcting that call yielded the successful evidence above; no production defect was inferred.

## Nonblocking follow-up / limits

- Protocol metadata currently assumes the canonical v1 session/calendar/252/365/pulse constants. _variance constructs default TradingSession and core fixes 252/365 / last30minutes / .028. If configurable contract fields are later accepted, validate their semantic consistency with core before freezing; do not imply the present functions support arbitrary session metadata.
- verify_frozen_evidence loads DIRECTORY/pilot; a copied protocol path alone is not a complete portable bundle. Runner/CAS reconstruction must include that pilot location or pass an explicitly verified artifact directory.
- Source / condition metadata and refusal tests are not a substitute for the real saved-only numerical pilot checker, smoke rejection, precision/rare-event selection, freeze replay, final reviewer, and main original-slot accounting. These are the parent/Task2's remaining gates.
