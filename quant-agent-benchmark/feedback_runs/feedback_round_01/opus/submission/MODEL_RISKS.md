# Model risk statement

What this curve assumes, where it is fragile, what has not been validated, and
what it may and may not be used for. Written to be read before the curve is
used, not after something goes wrong.

The scope is the artefacts produced by
`python -m quantcurve.cli run ... --valuation-date 2026-01-15` from
`market_observations.csv`: `outputs/curves/curve.csv` and the diagnostics beside
it.

---

## 1. Assumptions

### 1.1 One curve, one currency, no credit or collateral distinction

Deposits, OIS swaps and coupon bonds are discounted on a **single** curve. This
is the largest assumption in the project and it is certainly false in a real
market: unsecured deposits, cleared OIS and government bonds do not share a
discount curve. The model absorbs the difference into the per-instrument-type
noise term (§2.3) rather than modelling it, which means

- the bond residuals are structurally larger than the swap residuals (2.46bp
  against 0.82bp RMSE) and this is **not** a defect the calibration should chase;
- the curve is closer to the swaps than to the bonds, because the swaps are more
  numerous and more precisely quoted;
- a genuine change in the bond–OIS basis would appear here as "the bonds started
  repricing badly" with no way to tell it from a data problem.

A production build would fit an OIS discount curve and a bond spread curve
jointly. That was out of scope for a single-file, single-curve task, and the
consequence is stated rather than hidden.

### 1.2 Conventions inferred from the data

Day counts are not modelled. Maturities are taken from the supplied
`maturity_years` (cross-checked against `maturity_date` to within five days) and
every accrual is `1/frequency`. Schedules run backwards from maturity with
`n = max(1, round(T × frequency))` periods.

This rule was **inferred by testing candidate conventions against the quotes**,
not assumed: `ceil` mis-prices the 1.25Y annual OIS and `floor` mis-prices the
2.44Y semiannual bond, while `round` reprices every instrument consistently. It
is the right answer for this file. It is an empirical finding about this data
set, and a file built on a different convention would be silently mis-priced —
by roughly the coupon times half a period, which for a 3% semiannual bond is
about 0.7 price points. **Re-derive it before running this code on a different
source.**

Other convention assumptions: OIS fixed legs pay annually to 2Y and semiannually
beyond; deposits are simple-interest with `D(T) = 1/(1 + rT)`; bonds are bullet,
face 100, quoted clean with no accrued interest; settlement is spot-flat, so
`start_years = 0` for every observation and forward-starting instruments are not
supported.

### 1.3 Curve form

The published curve is a cubic spline in the **instantaneous forward rate** with
21 knots, so `D(T) = exp(-∫₀ᵀ f)`. Consequences:

- discount factors are positive by construction, at any level of rates, and
  negative rates need no special case (a dedicated test fits a wholly negative
  curve and checks `D > 1` and `D` finite);
- the curve is C² in the forward and therefore very smooth in the zero rate —
  **it cannot represent a genuine kink**, for example a real turn-of-year or
  meeting-date effect. If one exists in this market, this model will smear it
  across neighbouring maturities rather than show it.

### 1.4 The objective

`Σ wᵢ ρ(rᵢ) + λ ∫ (T/T_ref)^p f''(T)² dT`, with `rᵢ` in yield-equivalent basis
points and `ρ` Tukey's biweight. Three embedded judgements:

- **Yield-equivalent residuals.** A bond price residual is converted with
  `-1e4/(P·Duration)` so that a 1bp yield error on a 2Y bond and on a 30Y bond
  count the same. Without this the long bonds would dominate the fit.
- **Maturity-weighted roughness.** `p = 2` penalises curvature more at the long
  end than at the front. A flat penalty over-smooths the money-market end, which
  is where the term structure genuinely bends most.
- **λ chosen by cross-validation, not by eye.** The full CV table is published in
  `model_comparison.json` so the choice can be re-checked.

### 1.5 Robustness

Convex Huber warm-up (c = 1.345, four sweeps) then Tukey biweight (c = 4.685),
with the robust scale re-estimated for three sweeps and then frozen. The warm-up
is not decoration: started cold, the redescending estimator converged onto the
*contaminated* cluster of quotes on this data and rejected the good majority.

Three observations end with zero robust weight in the published fit. They are
visible in `repricing.csv` with their residuals, not silently deleted.

---

## 2. Data-quality risks

### 2.1 What was found in the file

143 observations, of which 90 were used as quoted, 15 corrected, 14 downweighted
and 24 excluded. The validation stage raised: 7 suspected unit-scale errors,
14 duplicate observations, 6 quotes outside their own bid/ask band, 5 stale
timestamps, 4 crossed markets, 4 missing quotes, 7 wide spreads and 20 illiquid
quotes. Every one of the 143 rows has a row in `cleaning.csv` with an action and
a reason.

### 2.2 The corrections themselves are model risk

- **Unit rescaling** (a rate quoted as `0.0225` instead of `2.25`) is detected by
  comparing an observation with its maturity peers, not by a fixed threshold.
  The decision rule requires the rescaled quote to be both four times closer to
  the peer level *and* within 35% of it. On a steeply sloping curve a genuine
  short-dated outlier could in principle satisfy this and be "corrected" into
  agreement with its neighbours. The rule was tuned so that all 7 genuine cases
  in this file are caught and no clean synthetic quote is touched, but it is a
  heuristic, and a rescaled quote is a *changed* quote.
- **Missing quotes rebuilt from bid/ask mid** assume the two-way market is
  reliable when the composite is not. Where the market is also crossed, the
  uncrossing (swap bid and ask) is applied first.
- **Downweighting** is not exclusion. A quote with a 10bp spread and a 0.12
  liquidity score still moves the curve, just less.

### 2.3 Weights and the noise estimate

`σᵢ² = σ_quote,ᵢ² + σ_model,type²`. The second term is estimated from a
preliminary robust fit's residual MAD per instrument type: **0.25bp deposits
(floored), 0.56bp swaps, 2.14bp bonds**. This is what stops the weighting from
being badly overconfident — the bid/ask half-spreads alone imply a σ of about
0.1bp for instruments that genuinely disagree by 2–3bp.

The risk is circularity: the noise estimate comes from a fit, and the fit uses
the noise estimate. It is a single pass, not iterated to convergence, precisely
to bound that feedback, but a badly wrong preliminary fit would propagate into
the weights. The `outlier_exclusion_policy` sensitivity check (1.95bp) is the
direct measurement of how much this matters here.

### 2.4 The outlier screen can be wrong in both directions

An observation is excluded only if it is **both** more than 4.685 robust sigma
from the screening reference **and** at least 5bp (yield-equivalent) from its
maturity neighbours. Both gates are needed. Without the second, a flexible
reference fit drives the robust scale down to a fraction of a basis point and
ordinary quotes 2bp from their neighbours become "40-sigma outliers" — this
happened, and it is why the absolute gate exists. Without the first, a genuinely
dispersed but honest pillar would be trimmed.

Residual risks: the screen is capped at 25% of the sample, so a file that is more
than a quarter contaminated will retain contamination; a *whole pillar* that is
uniformly wrong cannot be detected at all, because the local-residual reference
is that pillar's own consensus; and a maturity neighbourhood is never emptied
completely, so the least-extreme member of a wholly bad neighbourhood is
reinstated (with a low weight) rather than dropped.

### 2.5 Staleness

Quotes more than 24 hours older than the freshest observation are treated as
stale. The valuation date is 2026-01-15 and the file's freshest timestamp is the
same day, so this is a *relative* rule. If a whole file were stale, nothing here
would notice.

---

## 3. Numerical risks

| Risk | Control | Residual exposure |
|---|---|---|
| Discount factors going non-positive | Curve parameterised through `f`, `D = exp(-∫f)` | None structurally; asserted in `outputs.py` before writing |
| Bootstrap forward explosion between near-coincident pillars | Pillars closer than 0.10Y merged; forward solve bracketed to (−95%, +150%) | The baseline still produces −1.8%…+5.9% forwards on this file, which is why it is not published |
| IRLS oscillation | Robust scale frozen after three sweeps; 25-iteration cap; convergence recorded (`irls_converged: true`, 10 iterations) | A non-converged fit is reported, not hidden |
| IRLS converging on the wrong cluster | Convex Huber warm-up before the redescending stage | Breakdown is still possible above ~40% contamination |
| Robust scale collapsing to zero | Floored at 0.5bp, plus the 5bp absolute exclusion gate | The floor binds on this data (raw scale 0.47bp) |
| Spline basis too coarse for the maturity span | Knot budget takes the larger of "one knot per four observations" and a maturity-coverage floor of four knots per log-decade | Without the floor a 20-quote file spanning 1M–30Y got five knots and mis-priced the 1M deposit by 10bp |
| Over-fitting from a generous basis | λ chosen by maturity-blocked CV; effective degrees of freedom controlled by the penalty, not the knot count | CV minimum is used, not the one-standard-error rule (see §5.2) |
| Finite-difference risk being wrong | Every DV01 is cross-checked against an analytic cash-flow derivative; key rates must sum to the parallel DV01 | Agreement is 1.3×10⁻⁶ and 5.3×10⁻⁷ relative; this check caught a sign error in the OIS floating leg |
| Silent NaN propagation | `RuntimeWarning` and `FutureWarning` are errors in the test suite; output contract asserts finiteness, positivity and monotonicity | — |
| Non-reproducible output | No RNG anywhere; sorted outputs; `%.12g` floats; `sort_keys` JSON; PNG `Software` metadata stripped; the report is stamped with the market snapshot rather than the wall clock | Byte-identical reruns are asserted in the tests |

---

## 4. Interpolation and extrapolation behaviour

**Between knots (0.083Y – 30Y).** Cubic in `f`, so the zero curve is smooth and
the forward curve has no steps. The published grid is 601 points from 1/12Y to
30Y, **geometrically spaced below 2Y and uniform above it**. That shape is not
cosmetic: a uniform 601-point grid has a 0.05Y step everywhere, and a consumer
who linearly interpolates `zero_rate` between published rows would pick up
0.55bp of error inside the first six months — larger than the calibration
residual of every money-market instrument in the file, and entirely an artefact
of publication. On the grid actually published that interpolation error is below
0.01bp everywhere.

**Below the first knot (T < 1/12Y).** The instantaneous forward is held **flat**
at `f(t₀)`. This is a deliberate choice — extrapolating the cubic would let a
small curvature at the front knot swing the overnight rate by tens of basis
points — but it means the curve carries **no information at all** below one
month. There is no observation there either: the shortest instrument in the file
is the 1M deposit. Treat any output below 1/12Y as a flat-forward convention,
not a rate.

**Beyond the last knot (T > 30Y).** Flat forward again, at `f(30Y)`. The 30Y swap
is the longest instrument, so anything past it is convention rather than
information. `curve.csv` deliberately stops at 30Y.

**The 20Y–30Y gap.** The file has instruments at 20Y and 30Y and essentially
nothing in between. The penalty, not the data, determines the shape there. The
`leave_one_block_out_stability` check (5.54bp worst case) is dominated by exactly
this region; that number is the honest uncertainty of the long end, not the
0.8bp repricing RMSE.

**Negative rates.** Structurally supported and tested end to end: a fully
negative synthetic data set produces discount factors above 1, finite and
positive at every maturity, through both estimators and the full CLI.

---

## 5. Validation gaps

### 5.1 What was validated

- Every instrument type round-trips exactly against a known analytic curve.
- A dense spline reproduces a Nelson–Siegel curve to 0.02bp; the front-end
  extrapolation error is bounded and tested against its analytic estimate.
- The vectorised calibration path equals the scalar path to 1e-12.
- The bootstrap reprices its pillars to 0.02bp; the spline recovers the
  generating curve to 3bp and beats the bootstrap on a smooth truth.
- The screen finds an injected 40bp outlier, and only it, and does not delete a
  pillar.
- Maturity-blocked holdout: no training instrument lies within a block gap of a
  held-out one, and the blocked holdout error is more than 3× a random split's
  on a data set with deliberately duplicated venues — the measurement of the
  leakage the block structure exists to prevent.
- Key rates sum to DV01; finite differences match analytic derivatives.
- The CLI is byte-reproducible and exits non-zero with an actionable message on
  five distinct classes of bad input.

### 5.1b Stress grid measured in feedback_round_01

Five self-designed known curves (upward, inverted, humped, steep-front,
wholly negative) crossed with five conditions (clean, sparse maturities, gross
contamination, low liquidity, sparse *and* contaminated); both estimators fitted
to each and scored against the known truth, zero **and** instantaneous forward,
by maturity band. 50 fits, no failures, discount factors positive throughout.

- The advanced estimator beats the bootstrap on every condition, on both the
  zero curve (median 0.12bp vs 0.94bp) and the forward (0.78bp vs 7.51bp).
- Forward error runs roughly 4-8x the zero error throughout, which is what
  `f = z + T z'` predicts: the forward is a slope, and a curve can be right in
  level and wrong in slope.
- **The one condition that degrades materially is sparse maturities *plus*
  contamination.** Forward RMSE goes from 0.13bp (mid) / 0.20bp (long) on clean
  data to 12.9bp / 13.5bp, and zero RMSE from 0.02bp to 7.3bp in the mid band.
  The mechanism is identifiability, not a defect: an outlier at a maturity with
  no near neighbour cannot be distinguished from a genuine local feature by any
  robust method, and once it is (correctly) rejected the resulting hole is
  filled by the penalty rather than by data. `tests/test_stress_conditions.py`
  pins this behaviour and its bound.
- The single worst advanced fit in the whole grid (252bp forward error on an
  inverted, contaminated market) is **exactly** the one case the
  forward-admissibility gate rejects: 1 of 1 true failures caught, 0 of 24 good
  fits falsely rejected. The gate is a working safety net, not just a
  tie-breaker; the pipeline would fall back to the bootstrap there.
- Two one-factor changes to the curvature control were tested and **rejected**
  against pre-registered criteria: the one-standard-error CV rule (helps the
  sparse+contaminated case, but degrades the plain contaminated case by 30-100x)
  and flooring the roughness grid at 1e-4 (marginal, and worse in the long band
  on clean data). No numerical change was adopted.

### 5.1c Convention risk, quantified

`CONVENTIONS.md` does not state how many periods a *fractional* maturity has.
Pricing the same known discount function under the three defensible rules gives:

| Instrument | Maturity | Spread across round / ceil / floor |
|---|---|---|
| OIS par rate | 1.25Y | **94.3 bp** |
| OIS par rate | 2.44Y | 45.6 bp |
| OIS par rate | 26.4Y | 7.5 bp |
| Bond clean price | any fractional | **~1.25 price points** |

This project uses `n = max(1, round(T x frequency))`, chosen because it is the
only rule that reprices the 1.25Y OIS *and* the 2.44Y bond consistently. Fitting
the observations well is **not** proof that the rule is the one the data was
generated with; the table above is the size of the exposure if it is not, and it
dwarfs every fitting improvement in this project. It remains unresolved.

### 5.2 What was **not** validated

1. **No out-of-time validation.** The file is a single snapshot. Every stability
   claim here is cross-sectional. Whether this curve is stable *day to day* —
   the property that actually matters for a hedging book — is untested, and the
   penalty-based smoother in particular could exhibit day-to-day jitter that a
   single snapshot cannot reveal. This is the most important gap in the project.
2. **No independent benchmark.** There is no third-party curve to compare
   against. "Correct" here means internally consistent and consistent with the
   quotes, which is weaker.
3. **The 5% parsimony margin and the 200bp admissibility tolerance are
   judgements.** They were fixed before the numbers were looked at, and they are
   published in `model_comparison.json`, but they were not themselves validated.
   On this file the gate is decisive: it overturns an accuracy ranking that
   favoured the baseline (0.71bp against 1.15bp on the holdout). A reader who
   rejects the gate should prefer the bootstrap, and the diagnostics for both are
   published so that choice can be made independently.
4. **The one-standard-error rule is off.** Using it costs about 5bp of accuracy
   at the genuine 7Y feature in this data. That is a defensible trade the other
   way for someone who values stability over fit; the CV table is published so it
   can be re-made.
5. **Convention inference is validated only against this file** (§1.2).
6. **Bond accrued interest is assumed zero** because prices are quoted clean and
   no settlement convention is supplied beyond `settlement_days`. If the file's
   prices were in fact dirty, every bond would be mis-weighted.
7. **No test of behaviour under a genuinely different curve shape** — inverted,
   humped at the front, or with a real discontinuity. The synthetic fixtures are
   Nelson–Siegel, which is smooth by construction, so the estimator has never
   been shown a shape it cannot represent.
8. **Cleaning rules are validated on injected defects of the kinds anticipated.**
   A defect class nobody thought of is, by construction, untested.

---

## 6. Appropriate use

**Reasonable.**

- Marking and PV-ing vanilla USD OIS swaps, deposits and bullet bonds between
  1/12Y and 30Y, on this valuation date, with an understood uncertainty of about
  1bp in the well-populated 1Y–20Y region and about 5bp in the 20Y–30Y gap.
- Relative-value work *within* an instrument type, where the missing basis (§1.1)
  largely cancels.
- Producing DV01 and 2Y/5Y/10Y/30Y key-rate ladders for those instruments; the
  bucket decomposition is exact against the parallel number.
- As the basis for a discussion about data quality: `cleaning.csv` is the
  deliverable most likely to be useful to someone else.

**Not appropriate without further work.**

- **Cross-product basis trades** (bond versus swap), which are precisely the
  quantity this single-curve model assumes away.
- **Anything below 1M or beyond 30Y**, where the output is a flat-forward
  convention rather than a rate.
- **Forward-starting and path-dependent valuation** that depends on the shape of
  the instantaneous forward between quoted maturities. The published curve is
  admissible (its forward stays inside the quoted range) but the 20Y–30Y region
  is penalty-driven; the bootstrap alternative would be worse, not better.
- **Hedging a book day over day**, until out-of-time stability has been measured
  (§5.2.1).
- **Any market other than the one in this file**, until §1.2's conventions have
  been re-derived.
- **Automated trading, risk limits, or regulatory reporting.** This is a research
  artefact. It has one author, one data snapshot, no independent review and no
  production controls.

---

## 7. If one thing is done next

Rerun this pipeline over a series of consecutive valuation dates and measure the
day-to-day movement of the published curve and of the key-rate ladder against the
day-to-day movement of the quotes. Every other gap listed here is bounded; that
one is not.
