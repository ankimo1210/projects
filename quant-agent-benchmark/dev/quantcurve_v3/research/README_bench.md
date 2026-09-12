# Synthetic validation bench (`research/synthetic_bench.py`)

Purpose: judge estimator changes on **known curves** under unseen conditions before touching
the public holdout. Every change is evaluated as one factor against a reference run.

```bash
PYTHONPATH=src python research/synthetic_bench.py <name> bench/<name> [key=value ...]
PYTHONPATH=src python research/bench_compare.py bench/<ref>/results.csv bench/<name>/results.csv
```

Keys: `penalty_shape`, `max_knots`, `use_loo_screen=0/1`, `stub_rule`, `knot_bond_gap`,
`cv_loss` (`square|factor_square|huber3`), `lambda_grid_points`, `cv_max_tolerance`, `scenarios=a,b,c`.

## Scenario library (30, fixed seeds `20260906 + 100*index`)
- shapes: flat 2 %, steep up, inverted, humped (2Y hump), negative front, all-negative, long hump (14Y, like the
  round-02 public data)
- tenor patterns: `new_public` (unique off-grid tenors of the round-02 data), `round_grid` (2 quotes per round tenor),
  `sparse_long` (no rate quotes beyond 12Y), `no_deposits`, `front_only_5y` (intentional extrapolation failure,
  informational only)
- noise: gaussian 0.5 bp, heteroscedastic `0.3 + 0.03 T` bp, Student t(3)
- contamination: outliers 5/10/20 % (+/-15 bp yield-equivalent), unit defects (labelled DECIMAL, mislabelled PERCENT,
  bond price /100), 30 % missing bid/ask, 15 % duplicates, 5 % stale (+5 bp), 20 % missing rows, one combined stress
- hidden instruments: deposits/OIS/bonds at off-grid maturities (bond frequencies 1/2/4, some zero coupon) priced
  from the truth without noise; error = yield-equivalent bp

## Metrics (never mixed)
S1 zero / forward RMSE and max vs truth on a fixed grid (1/48..30), bands short T<=2 / mid 2<T<15 / long T>=15;
S1h hidden-instrument RMSE by band and type; R robust bookkeeping (contaminated caught, clean excluded).

## Adoption rule (`bench_compare.py`)
Advanced-model zero RMSE (all band) improves by > 0.05 bp in >= 2 scenarios, no scenario/band worsens by > 0.5 bp in
zero, forward or hidden RMSE, no new failures. A change that removes a failure mode (a scenario with > 5 bp error)
without breaching the worsening tolerance is also adopted, recorded as such.

## Log
| run | change | outcome |
|---|---|---|
| V0_ref | round-02 final + grid 1/48 | reference; failure: `tenor_sparse_long_long_hump` zero 10.6 bp (6 clean bonds rejected); `combo_stress` 2.6 bp |
| H3a_bondknots | `knot_bond_gap=1.5` | fixes sparse-long failure (10.63 -> 0.33 bp), other cases within 0.26 bp -> **adopted (default 1.5)** |
| H3b_tref3 / H3c_tref8 | penalty reference maturity | tref only rescales lambda (the weight ratio is tref-free); differences are lambda-grid artefacts -> knob removed |
| V2_nbguard | neighbour consensus guard in the LOO screen | keeps adjacent same-sign outliers: `combo_stress` 2.6 -> 5.3 bp -> **rejected, removed** |
| V3 | (invalid: zsh did not word-split the arguments) | ignored |
| V4_bondknots_default | defaults after adoption | confirmation of H3a |
| E1_grid43 | lambda grid 43 points | no gain; `outliers10_humped` hidden 0.59 -> 1.10 bp -> rejected |
| E2a_factor_sq | CV loss weighted by robust factors | small forward gains on long-hump outlier cases, `sparse_long_long_hump` forward 6.0 -> 7.8 bp -> rejected |
| E2b_huber3 | factor-weighted Huber CV loss (c=3) | `outliers20_long_hump` 0.94 -> 0.53 bp but `outliers20_humped` hidden 0.23 -> 0.56 bp; max band worsening 0.73 bp -> rejected (borderline, keep as option) |
| E3_1se10 | 1-SE rule, cap 10 % | over-smoothing: 8 scenarios worse, `tenor_round_grid_humped` 0.22 -> 3.86 bp -> rejected (consistent with round 1) |
| E4_loo_window1 | leave out the +/-1 neighbouring clusters together with the tested cluster (anti-masking) | mean zero 3.81 -> 3.63 bp but 3-7 clean quotes rejected in 8 scenarios (genuine shape removed), `combo_stress` unchanged, public holdout 0.256 -> 0.259 bp -> rejected (option kept, default 0) |

## Open weaknesses after this session
- `combo_stress_long_hump` (t(3) noise + 10 % outliers + unit defects + 20 % missing + 30 % missing bid/ask): 2.6 bp zero
  RMSE, concentrated at 20-25Y where two same-sign +15 bp outliers sit next to low-liquidity quotes and mask each
  other in the leave-tenor-out screen. None of the lambda-selection or screening variants fixed it without harming
  other scenarios.
- `tenor_front_only_5y_humped`: no instruments beyond 5Y; flat-forward extrapolation is tens of bp wrong (both
  models). Informational; a curve cannot know an unobserved region.
- Public-data outputs are unchanged by every adopted change (the round-02 data has no bond-only region); the
  improvements are robustness under unseen conditions, not a better public score.
