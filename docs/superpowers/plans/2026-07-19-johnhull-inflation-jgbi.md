# JohnHull Inflation-Linked Rates & JGBi — Implementation Plan

**Date:** 2026-07-19
**Target project:** `johnhull`
**Implementation scope for this execution:** Phase 1 through Phase 7
**Planned volume:** `volumes/26_inflation_jgbi`

## 1. Objective

Add a tested, reusable inflation-linked rates stack to `hullkit` and a reproducible
teaching volume covering:

1. one-factor Hull–White as a production-quality financial teacher rather than a
   notebook-local illustration;
2. zero-coupon and year-on-year inflation swaps, including observation/payment
   dates and deterministic CPI seasonality;
3. the three-factor Jarrow–Yildirim nominal/real/CPI model with explicit numeraire
   and measure conventions;
4. Japanese inflation-indexed government bonds (JGBi), including the Ministry of
   Finance reference-index convention and the post-2013 redemption principal floor;
5. analytic and Monte Carlo valuation of the JGBi deflation-floor option;
6. an artifact-only vol.26 notebook backed by versioned synthetic JSON/NPZ
   references and semantic tests.

The implementation must remain torch-free, require no new production dependency,
and preserve the `synthetic-offline` release policy.

## 2. Sources of truth

- Hull–White model: Hull and White (1990), *Pricing Interest-Rate-Derivative
  Securities*; existing pedagogical coverage in
  `johnhull/interest_rate_models/build_ir_models_notebook.py`.
- Jarrow–Yildirim: Jarrow and Yildirim (2003), *Pricing Treasury Inflation
  Protected Securities and Related Derivatives Using an HJM Model*.
- JGBi product and reference-index rules: Ministry of Finance Japan,
  *10-year Inflation-Indexed Bonds* and *Ref Index and Indexation Coefficient
  applicable to Inflation-Indexed Bonds*.
- CPI definition and rebasing: Statistics Bureau of Japan CPI documentation.
- BEI limitations: Bank of Japan Working Paper 20-E-5, including deflation-floor,
  liquidity, and nominal/real term-premium effects.

The public rules above define the educational implementation. Full licensed ISDA
disruption fallbacks, vendor quote mappings, tax, and production settlement
operations are not claimed.

## 3. Architecture and ownership

```text
hullkit.rates ───────────────┐
                            ├─> hullkit.hull_white ──┐
hullkit.inflation ───────────┼───────────────────────┼─> hullkit.jarrow_yildirim
                            └─> hullkit.jgbi <───────┘
                                      │
                                      └─> vol.26 reference + notebook
```

New semantic modules:

| Module | Responsibility |
|---|---|
| `hullkit.hull_white` | Initial-curve fit, exact Gaussian transition, ZCB, ZCB option, Jamshidian European swaption, synthetic calibration |
| `hullkit.inflation` | Monthly CPI fixings, observation lag/interpolation, rebasing, deterministic seasonality, inflation curve, ZCIS and YoY cash flows |
| `hullkit.jarrow_yildirim` | Nominal/real Gaussian factors, CPI dynamics, correlations, forward-measure moments, CPI options, analytic/MC comparison |
| `hullkit.jgbi` | MOF reference index, indexation coefficient, coupons/redemption, clean/dirty/settlement values, real yield/BEI, deflation floor |

Notebook builders remain presentation layers. Financial identities and hard
validation belong to `hullkit` and its tests.

## 4. Global mathematical contract

### 4.1 Curves and units

- Rates use decimal units and continuous compounding, consistent with existing
  `hullkit.rates` and `hullkit.swaps`.
- `P_n(t,T)` denotes a nominal discount factor.
- `P_r(t,T)` denotes a real discount factor in real units.
- `I(t)` denotes nominal currency per real CPI unit.
- Nominal cash flows are discounted only with the nominal curve.
- CPI index levels and index ratios are dimensionless in the public APIs.

### 4.2 Measures and numeraires

- `Q^n`: nominal money-market risk-neutral measure.
- `Q^{n,T}`: nominal `T`-forward measure for a payment at `T`.
- `Q^r`: real money-market measure, used to define the real term structure.
- `Q^{r,T}`: real `T`-forward measure when useful for derivation.

The foreign-currency analogy must satisfy

```math
P_n(t,T) E_t^{Q^{n,T}}[I(T)] = I(t) P_r(t,T).
```

Every CPI-linked product stores an observation date `U` independently from its
payment date `T`. A payoff paid at `T` is evaluated under `Q^{n,T}` even when
`U < T`; changing to an observation-date measure requires an explicit payment-lag
convexity adjustment.

### 4.3 Seasonality and reference-index order

The order of operations is fixed:

```text
trend CPI forward
  -> monthly seasonality
  -> CPI base-revision bridge
  -> observation lag
  -> daily interpolation
  -> product cash flow
```

Monthly log-seasonality factors `s_m` satisfy

```math
\sum_{m=1}^{12} s_m = 0,
```

equivalently the twelve multiplicative factors have product one. This preserves
annual inflation while redistributing it across months.

## 5. Phase 1 — shared rates helpers

### Files

- Modify `johnhull/hullkit/src/hullkit/rates.py`.
- Extend `johnhull/hullkit/tests/test_rates.py`.

### API

```python
discount_factor(t, curve)
forward_discount(start, end, curve)
instantaneous_forward(t, curve, *, bump=1e-5)
```

`curve` remains the existing `(times, continuously_compounded_zero_rates)` tuple.
No broad curve-class migration is performed.

### Validation

- `P(0)=1` and positive finite discount factors.
- Flat-curve discount and forward-rate hand calculations.
- Central-difference instantaneous forward against an analytic flat curve.
- Invalid time grids, non-finite data, and non-positive bump are rejected.

## 6. Phase 2 — Hull–White 1F

### Files

- Add `johnhull/hullkit/src/hullkit/hull_white.py`.
- Add `johnhull/hullkit/tests/test_hull_white.py`.
- Update `johnhull/MODEL_INDEX.md` when the module is added.

### Model

Use the shifted-Gaussian representation

```math
r_t = x_t + \phi(t), \qquad dx_t = -a x_t dt + \sigma dW_t^n,
```

with `phi` chosen to reproduce the initial discount curve. This avoids treating a
numerically differentiated notebook `theta(t)` as the simulation state.

### API

```python
@dataclass(frozen=True)
class HullWhiteParams:
    mean_reversion: float
    volatility: float

hw_b(t, maturity, mean_reversion)
hw_phi(t, curve, params)
hw_discount_bond(t, maturity, state, curve, params)
hw_exact_transition(state, start, end, params, *, normal=0.0)
simulate_hw_paths(times, initial_state, params, *, n_paths, seed)
hw_zcb_option(expiry, bond_maturity, strike, curve, params, *, option_type)
hw_jamshidian_swaption(expiry, payment_times, fixed_cashflows, curve, params, *, option_type)
calibrate_hw1f(expiries, payment_schedules, market_prices, curve, initial_guess)
```

The public state is the zero-mean factor `x_t`. Functions document the distinction
between `x_t` and the observable short rate `r_t`.

### Validation

- `P^{HW}(0,T) == P^{market}(0,T)` to `1e-12` on a non-flat curve.
- Exact transition conditional mean and variance.
- Monte Carlo terminal moments within reported standard errors.
- ZCB option put-call parity to `1e-12`.
- Zero-volatility limit equals discounted intrinsic value.
- Jamshidian price agrees with direct one-dimensional Gaussian quadrature to
  `1e-8`.
- Synthetic calibration reproduces teacher prices; parameter recovery is reported
  separately because `(a, sigma)` can be weakly identified from sparse quotes.

## 7. Phase 3 — CPI, seasonality, ZCIS, and YoY

### Files

- Add `johnhull/hullkit/src/hullkit/inflation.py`.
- Add `johnhull/hullkit/tests/test_inflation.py`.
- Update `johnhull/MODEL_INDEX.md`.

### Data structures

```python
@dataclass(frozen=True)
class CPIObservationConvention:
    lag_months: int = 3
    interpolation: Literal["linear", "flat"] = "linear"

@dataclass(frozen=True)
class MonthlySeasonality:
    log_factors: tuple[float, ...]  # exactly 12, sum zero

@dataclass(frozen=True)
class ZeroCouponInflationCurve:
    base_date: date
    base_index: float
    maturities: tuple[float, ...]
    zero_rates: tuple[float, ...]
    seasonality: MonthlySeasonality
```

Monthly CPI fixings use first-of-month `date` keys. Public functions validate that
the series is ordered, positive, and has no duplicate month.

### API

```python
monthly_cpi_value(month, fixings)
interpolated_cpi(day, fixings, convention)
apply_cpi_rebase(value, bridge_factor)
seasonal_forward_index(day, curve)
zcis_cashflow(notional, start_index, end_index, fixed_rate, accrual_years)
zcis_npv(...)
zcis_par_rate(...)
bootstrap_zc_inflation_curve(...)
yoy_rate(start_index, end_index)
yoy_swap_npv(...)
```

The deterministic curve layer takes forward CPI values explicitly. Model-based
convexity is injected through expected-ratio callbacks rather than hidden inside
cash-flow construction.

### Validation

- ZCIS par NPV is zero to `1e-10`.
- Quote -> curve -> quote absolute rate error is at most `1e-10`.
- Twelve-month seasonality sum/product constraints hold to `1e-12`.
- Same-reference-month annual ZCIS cancels seasonality.
- Off-cycle ZCIS and YoY retain seasonality.
- Fixed and forecast CPI observations are separated at the valuation date.
- Rebase bridges preserve all index ratios.
- Forward-starting YoY does not use a ratio of marginal expectations.

## 8. Phase 4 — JGBi conventions and deterministic valuation

### Files

- Add `johnhull/hullkit/src/hullkit/jgbi.py`.
- Add `johnhull/hullkit/tests/test_jgbi.py`.
- Update `johnhull/MODEL_INDEX.md`.

### Data structures

```python
@dataclass(frozen=True)
class JGBITerms:
    issue_date: date
    maturity_date: date
    coupon_dates: tuple[date, ...]
    coupon_rate: float
    face_value: float
    base_reference_date: date
    principal_floor: bool
    reference_index_decimals: int = 3
    index_ratio_decimals: int = 5
```

`principal_floor` is explicit. It is not inferred solely from the issue date, so
historical/reopened instruments can be represented without hidden assumptions.

### API

```python
jgbi_reference_index(day, monthly_cpi)
jgbi_indexation_coefficient(day, terms, monthly_cpi)
jgbi_cashflows(terms, monthly_cpi)
jgbi_accrued_interest(settlement, terms, monthly_cpi)
jgbi_real_clean_price(...)
jgbi_nominal_settlement_amount(...)
jgbi_real_yield(...)
jgbi_breakeven_inflation(nominal_yield, real_yield)
```

### Rules covered

- Japan CPI excluding fresh food as an input series.
- Three-month lag.
- Reference index on the tenth day of the month.
- Linear interpolation before and after the tenth day.
- Reference-index and index-ratio rounding.
- Reopened-issue base reference index.
- Short first coupon-period base-date override as explicit terms data.
- Inflation-adjusted coupons.
- Redemption-only principal floor; coupons are never floored.

### Validation

- Hand calculations for dates before, on, and after the tenth.
- Rounding at the documented stage, not at arbitrary intermediate steps.
- Reopened issue retains the original base reference index.
- Coupon cash flows equal adjusted principal times coupon rate / 2.
- Redemption equals `N*R_T` without the floor and `N*max(R_T, 1)` with it.
- Clean/dirty/nominal settlement reconciliation.

## 9. Phase 5 — Jarrow–Yildirim

### Files

- Add `johnhull/hullkit/src/hullkit/jarrow_yildirim.py`.
- Add `johnhull/hullkit/tests/test_jarrow_yildirim.py`.
- Update `johnhull/MODEL_INDEX.md`.

### Parameters

```python
@dataclass(frozen=True)
class JarrowYildirimParams:
    nominal_mean_reversion: float
    nominal_volatility: float
    real_mean_reversion: float
    real_volatility: float
    inflation_volatility: float
    rho_nominal_real: float
    rho_nominal_inflation: float
    rho_real_inflation: float
```

### API

```python
jy_correlation_matrix(params)
jy_cpi_forward(t, maturity, spot_cpi, nominal_curve, real_curve)
jy_cpi_total_variance(t, observation, payment, params)
jy_expected_cpi_ratio(...)
jy_cpi_option(...)
jy_zcis_value(...)
jy_yoy_value(...)
simulate_jy_paths(...)
```

### Measure implementation

- Simulate under the nominal measure with the correct real-rate quanto/HJM drift
  adjustment.
- Provide analytic CPI-forward and log-variance functions under the relevant
  nominal payment-date forward measure.
- Do not simulate two ordinary independent Hull–White models under one measure.
- Validate the three-by-three Brownian correlation matrix as positive
  semidefinite before simulation or pricing.

### Validation

- Invalid correlations are rejected.
- `P_n/B_n` is a nominal-measure martingale within Monte Carlo standard error.
- `I*P_r/B_n` is a nominal-measure martingale within standard error.
- Analytic `F_I = I P_r / P_n` identity.
- Change-of-numeraire density has expectation one.
- Analytic CPI option and nominal-measure MC agree within three standard errors.
- Nominal-forward-measure and nominal-money-market-measure valuations agree.
- Zero-volatility limit matches the deterministic curve layer.
- YoY convexity disappears in the zero-volatility/correlation limit.

## 10. Phase 6 — JGBi deflation-floor option

### Payoff decomposition

For index ratio `R_T`, post-2013 redemption is

```math
N\max(R_T,1) = N R_T + N(1-R_T)^+.
```

The second term is a nominally paid put on the CPI index ratio. Under the nominal
`T`-forward measure,

```math
V_{floor}(t) = N P_n(t,T) E_t^{Q^{n,T}}[(1-R_T)^+].
```

### API additions in `hullkit.jgbi`

```python
jgbi_deflation_floor_black(...)
jgbi_deflation_floor_jy(...)
jgbi_floor_adjusted_price(...)
jgbi_floor_risk(...)
```

The analytic Black-style formula uses the Jarrow–Yildirim forward index ratio and
integrated log variance. Monte Carlo provides an independent teacher.

### Validation

- Floor value is non-negative.
- Floor value is non-decreasing in CPI volatility.
- Zero-volatility value equals discounted intrinsic value.
- Analytic and MC prices agree within three standard errors.
- Floored price equals unfloored price plus the option value.
- Coupons are identical with and without the floor.
- Legacy instruments with `principal_floor=False` receive no option value.
- Floor-adjusted and unadjusted BEI are reported separately.

## 11. Phase 7 — volume 26 reference and notebook

### Files

```text
johnhull/volumes/26_inflation_jgbi/
  build_26_inflation_jgbi_notebook.py
  inflation_jgbi.ipynb
  VALIDATION.md
  reference/
    metrics.json
    inflation_scenarios.npz
```

Also modify the minimum infrastructure needed to build and validate the volume:

- `johnhull/scripts/build_frontier_artifacts.py`
- `johnhull/scripts/frontier_acceptance.py`
- `johnhull/scripts/build_frontier_notebooks.py`
- `johnhull/scripts/verify_frontier_artifacts.py`
- `johnhull/scripts/verify_frontier_notebooks.py`
- `johnhull/release_manifest.json`
- `johnhull/ROADMAP.md`
- `johnhull/docs/DATA_PROVENANCE.md`

Book and portal integration are planned after Phase 7 unless required by the
existing release verifier to make the new volume buildable. Phase 7 does not add
remote runtime dependencies.

### Notebook sections

1. Nominal rates, real rates, and CPI as a foreign-currency analogy.
2. CPI fixings, three-month lag, interpolation, and rebasing.
3. Deterministic monthly seasonality.
4. Hull–White initial-curve fit and option ladder.
5. ZCIS curve and par valuation.
6. YoY swaps and convexity.
7. Jarrow–Yildirim measures and joint dynamics.
8. JGBi cash flows and settlement value.
9. Deflation-floor analytic and MC valuation.
10. Raw versus floor-adjusted BEI.
11. Synthetic JGBi + nominal bond + inflation swap hedge decomposition.
12. Limitations, exercises, citations, and rebuild instructions.

### Reference artifact

The NPZ contains only small fixed-seed synthetic arrays, including:

- initial nominal and real discount curves;
- Hull–White fit and swaption teacher prices;
- monthly CPI trend/seasonality paths;
- ZCIS and YoY quote/repricing ladders;
- Jarrow–Yildirim analytic and MC CPI moments;
- JGBi cash-flow and floor-value scenarios;
- raw and floor-adjusted BEI components.

The JSON records schema, units, seed, semantic source/test paths, companion SHA-256,
acceptance results, limitations, and negative results.

### Phase 7 acceptance

- Every semantic module has direct tests and is listed in `MODEL_INDEX.md`.
- Artifact rebuild is byte-identical for ordinary fixed-seed paths.
- Notebook reads committed JSON/NPZ only.
- Notebook has no training, download, GPU detection, or network access.
- Notebook executes from a temporary directory without errors.
- Validation states `integration_and_reproducibility` only and explicitly denies
  production/model-performance approval.

## 12. Validation commands through Phase 7

Run from the workspace root:

```bash
uv run --no-sync --package hullkit pytest -q \
  johnhull/hullkit/tests/test_rates.py \
  johnhull/hullkit/tests/test_hull_white.py \
  johnhull/hullkit/tests/test_inflation.py \
  johnhull/hullkit/tests/test_jgbi.py \
  johnhull/hullkit/tests/test_jarrow_yildirim.py

uv run --no-sync --package hullkit pytest -q \
  johnhull/hullkit/tests/test_docstrings.py \
  johnhull/hullkit/tests/test_model_index.py

uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 26
uv run --no-sync --package hullkit python \
  johnhull/volumes/26_inflation_jgbi/build_26_inflation_jgbi_notebook.py
```

Then run the scoped full package and report tests if Phase 7 infrastructure touches
shared release code:

```bash
uv run --no-sync --package hullkit pytest -q \
  johnhull/hullkit/tests johnhull/report/tests
```

## 13. Explicitly deferred after Phase 7

- Portal registration and final figure-count contract.
- Jupyter Book TOC/symlink and full book build.
- Full tracked release gate and final release documentation.
- Two-factor Hull–White/G2++ and Bermudan swaptions.
- Inflation volatility smile, caps/floors surface calibration, and stochastic
  seasonality.
- Live market-data ingestion or redistribution.
- Full licensed ISDA disruption fallbacks and production settlement operations.
- Jarrow–Yildirim real-market MLE and claims of empirical performance.

## 14. Completion rule

Phase 1–7 is complete only when all scoped semantic tests pass, the vol.26 reference
artifact is reproducible, the artifact-only notebook fresh-executes, and every
limitation above is visible in its validation report. A failed numerical validation
is repaired with the smallest relevant change and rerun; after three failed repair
attempts on the same blocker, stop and report the blocker and next action.
