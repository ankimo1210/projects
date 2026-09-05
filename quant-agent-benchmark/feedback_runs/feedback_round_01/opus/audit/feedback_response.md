# feedback_response.md — feedback_round_01 / opus

Each §4 "Opus" bullet, and the §2 common points, answered with: what the code
actually does (fact), what I ran (experiment), the verdict
(**supported / rejected / unverified**), and what remains uncertain.

Improvement ratios are `(before − after) / before` and are omitted where the
denominator is zero or the two sides were not measured under identical
conditions. No hidden score, hidden RMSE, token count or billing figure is
reconstructed anywhere in this round.

---

## §4-Opus-1 — "Main-data accuracy was good, but the forward was unstable under some stress conditions"

**Fact in the code.** Both estimators are parameterised in the instantaneous
forward, and on the public data cross-validation selects `λ=1e-5` — the
second-smallest weight in the grid, i.e. near-interpolating. A near-interpolating
fit is exactly the configuration in which `f = z + T z'` can be right in level
and wrong in slope.

**Experiment (E03).** A stress grid of my own design: 5 known analytic curves
(upward, inverted, humped, steep-front, wholly negative) × 5 conditions (clean,
sparse maturities, gross contamination, low liquidity, sparse + contaminated),
both estimators, scored against the known truth for **zero and forward
separately, by maturity band**. 50 fits, 0 failures, discount factors positive
everywhere. Seed 20260905 (the pipeline itself draws no random numbers).

**Verdict: SUPPORTED, and localised.**

| condition | advanced zero RMSE (mid) | advanced forward RMSE (mid) |
|---|---|---|
| clean | 0.02 bp | 0.13 bp |
| sparse | 0.10 bp | 0.48 bp |
| contaminated | 0.06 bp | 0.22 bp |
| illiquid | 0.02 bp | 0.13 bp |
| **sparse + contaminated** | **7.27 bp** | **12.86 bp** |

Forward error runs 4–8× zero error throughout — the `f = z + T z'` amplification
the common feedback names, confirmed on my own code. But the instability is not
diffuse: **one** condition carries it, sparse maturities *together with*
contamination. Sparseness alone and contamination alone are both handled.

**Mechanism, reduced to a minimal reproduction (E07,
`audit/diag/repro_sparse_contam.py`).** Five swap pillars (1, 2, 5, 10, 30Y) and
one 40bp outlier planted at the isolated 5Y pillar. The robust stage does its
job — the outlier's weight goes to exactly 0.000 — but rejecting it leaves an
eight-year hole that only the roughness penalty can fill, so forward RMSE rises
11.84 → 19.61 bp. This is an **identifiability limit, not a defect**: an outlier
at a maturity with no near neighbour is not distinguishable from a genuine local
feature by any robust estimator. I have documented and bounded it rather than
pretending to fix it.

**Residual uncertainty.** The five shapes and three defect types are mine; a
condition I did not think of is by construction untested. I deliberately did not
try to guess the hidden scenarios.

---

## §4-Opus-2 — "Validate curvature control, weights and model-selection criteria on your own diverse conditions"

### Curvature control (E04, E05) — **REJECTED**

Two one-factor changes, each the only thing changed from the reproduced baseline,
judged against criteria fixed in `protocol.md` §6 *before* the numbers existed
(A2: no band may degrade by more than 10% relative).

| variant | where it helps | where it hurts | verdict |
|---|---|---|---|
| CV one-standard-error rule | sparse+contam forward 12.86 → 6.62 bp (mid); worst case 251.7 → 53.1 bp | **plain contaminated** forward 0.22 → 8.04 bp (mid), zero 0.06 → 3.17 bp | **rejected (A2, +3555%)** |
| roughness grid floored at 1e-4 | clean short forward 1.00 → 0.83 bp | clean long forward 0.20 → 0.24 bp (+20%); no effect at all where it matters | **rejected (A2, +20%)** |

The one-standard-error rule buys robustness in the sparse+contaminated corner by
paying for it, heavily, in the far more common contaminated-but-well-populated
case. That is a bad trade for this data set, and the pre-registered rule
disqualifies it. **Hypothesis H4 — that the CV selection rule was the effective
lever — is rejected.**

### Model selection (E06) — **SUPPORTED, and stronger than I claimed in round 1**

Round 1 justified the forward-admissibility gate on the public data alone, where
it looked like a tie-breaker that happened to overturn the accuracy ranking. On
the stress grid it behaves as a genuine safety net:

- The single worst advanced fit in all 50 (252 bp forward error, inverted curve
  with three planted outliers) is **exactly** the one case the gate rejects.
- **1 of 1** true failures caught; **0 of 24** good fits falsely rejected.
- It also rejects 5 of 25 baseline fits, all of them piecewise-flat forward
  curves with genuine step artefacts.

So the pipeline is safe on the one case where the estimator is not: it would
fall back to the bootstrap. This is now pinned by
`tests/test_stress_conditions.py::TestAdmissibilityGateIsTheSafetyNet`.

### Weights — **UNVERIFIED**

I did not run a one-factor experiment on the per-type variance component inside
the time limit. The stress grid used uniform half-spreads except in the
`illiquid` condition, where results were identical to `clean` to two decimal
places — weak evidence that the liquidity path is not doing harm, but not a test
of the weighting scheme itself. Recorded as unverified, not as "fine".

---

## §4-Opus-3 — "Reduce the failure condition to a concise reproduction rather than adding tests"

Done, and the test count moved by six, not by fifty:
`audit/diag/repro_sparse_contam.py` is a ~60-line standalone script, and
`submission/tests/test_stress_conditions.py` pins two measured behaviours (the
sparse+contaminated bound; the gate's sensitivity and specificity). No test was
added for coverage's sake, and none was weakened.

---

## §4-Opus-4 — "Check the hardcoded personal absolute path and model_comparison.json"

**Fact.** `tests/test_cli.py` hardcoded
`/Users/ankimo1210/.../market_observations.csv`. On any other machine the
end-to-end test silently skipped — the single most valuable test in the suite,
disabled by a path.

**Fixed (F01).** Resolution order is now `QUANTCURVE_MARKET_DATA`, then an
ancestor search for `input/market_data/market_observations.csv`, then skip. Zero
`/Users/` strings remain in `src/` or `tests/`; the ones left in `README.md` are
worked examples, labelled as such.

**Fact.** `model_comparison.json` had `model_selected`, not the mandated
`selected_model`.

**Fixed (F02).** `selected_model` added as the mandated top-level key alongside
`baseline`, `advanced`, `selection_rationale`; `model_selected` kept as an alias
so a round-1 consumer does not break. Both models carry `train_metrics` and
`holdout_metrics`, and a new `metric_units` block states the unit of every
metric name (7 entries). **This is a format fix and is not counted as a
numerical improvement anywhere in this round.**

---

## §4-Opus-5 — "State explicitly any improvement bought at the cost of main-data accuracy"

**Nothing was traded.** No numerical change was adopted, so the public-data
results are bit-for-bit the round-1 results: 143 observations → 119 calibrating
instruments, advanced selected, holdout weighted RMSE 1.151 bp, baseline 0.705
bp, per-type weighted repricing 0.09 / 0.89 / 2.55 bp. Verified by rerunning the
CLI after every edit.

---

## §2 common points

| point | verdict | evidence |
|---|---|---|
| Completion and green tests ≠ a good curve | **supported** | 204/204 green in round 1 while the sparse+contaminated forward error was 12.9 bp and unmeasured |
| Averages hide band-specific weakness | **supported** | pooled advanced forward median 0.78 bp vs 13.5 bp in the sparse+contaminated long band |
| Choosing baseline or advanced is not itself success | **supported** | advanced wins on truth in all 5 conditions, yet the gate must still overrule it in 1 of 25 |
| Convention mismatch may distort the curve | **supported, quantified, unresolved** | see below |
| `f = z + T z'` amplifies slope error | **supported** | forward RMSE is 4–8× zero RMSE across the grid |
| Numerical quality and submission format are different problems | **supported** | four format defects fixed with zero numerical change |

### Pricing and conventions (H1, H2)

**H1 — pricing is correct in isolation: SUPPORTED.** A reference pricer written
directly from `CONVENTIONS.md`, sharing no schedule or cash-flow code with
`quantcurve`, was handed the same known `D(T)` on 7 curve shapes × 16 maturities
(integer and fractional) including a wholly negative curve:

- deposits: max disagreement **0.0 bp**
- OIS par rates: **1.0e-13 bp**
- bond clean prices: **2.8e-14 price points**
- quote round-trip residual: **2.9e-12 bp**
- schedule mismatches between the two implementations: **0**

**H2 — the fractional-period rule is undetermined and material: SUPPORTED.**
`CONVENTIONS.md` fixes the payment frequency, the accrual, face, and the par
condition, but is silent on how many periods a fractional maturity has. Pricing
the same `D(T)` under round / ceil / floor:

| instrument | maturity | spread |
|---|---|---|
| OIS par rate | 1.25Y | **94.3 bp** |
| OIS par rate | 2.44Y | 45.6 bp |
| OIS par rate | 26.4Y | 7.5 bp |
| bond clean price | any fractional | **~1.25 price points** |

I use `round`, because it is the only rule that reprices the 1.25Y OIS *and* the
2.44Y bond consistently. **Fitting the observations well is not proof that this
is the rule the data was generated under** — the prompt is right to warn against
that inference, and I am not making it. The table is the size of the exposure if
the rule is wrong, and it is an order of magnitude larger than every fitting
effect measured in this round. **Unresolved**, and not something I may repair by
regenerating benchmark data.

---

## Summary of verdicts

| hypothesis | verdict |
|---|---|
| H1 pricing correct in isolation | **supported** |
| H2 fractional-period convention undetermined and material | **supported, quantified, unresolved** |
| H3 forward degrades under stress via `f = z + T z'` | **supported**, localised to sparse + contaminated |
| H4 the CV selection rule is the effective lever | **rejected** (both variants fail pre-registered criteria) |
| H5 the selection gate is itself stable | **supported** (1/1 sensitivity, 24/24 specificity) |
| weighting scheme one-factor test | **unverified** (not run inside the time limit) |
| out-of-time (day-to-day) stability | **unverified** (still one snapshot; unchanged from round 1) |

**Net numerical outcome of this round: no verified improvement, and no
regression.** Two candidate improvements were tested and rejected on
pre-registered criteria; that is the result, and it is reported as such rather
than dressed up as a change.
