# johnhull G4–G7 Detailed Implementation Record

- Date: 2026-07-18
- Status: implemented; final G8 integration verification is authoritative
- Parent design: `docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-a5-design.md`
- Release contract: `johnhull/release_manifest.json`

## Contract decision

G4–G7の公開APIはtorch-freeな`hullkit`が所有し、既定データは固定seedのsynthetic fixtureだけとする。
実市場data source、vendor API、download、checkpointをcore経路へ入れない。未査読・計算量の大きい候補は
`johnhull/research_profiles.json`で無効化し、core gateの依存にしない。

## G4 — Joint SPX/VIX and 0DTE

### vol 21 public API

- `hullkit.spx_vix.PDVParameters` / `four_factor_pdv`
- `affine_forward_variance`, `rough_heston_fractional_kernel`, `quintic_ou_variance`
- `joint_spx_vix_objective`
- `nested_vix_teacher`, `fit_polynomial_surrogate`, `compare_teacher_surrogate`
- `finite_difference_greeks`, `out_of_domain_flags`

Validation contract:

- [x] SPX IV、VIX target、variance termを別metricとしてjoint objectiveへ渡す。
- [x] nested teacherとsurrogateの誤差・速度を同じsampleで測る。
- [x] PDV、AFV、rough-Heston kernel、quintic OUを比較可能にする。
- [x] signature modelとperturbed optimal transportはdisabled research trackに置く。

### vol 22 public API

- `hullkit.zero_dte.TradingSession`, `trading_seconds_to_settlement`
- `variance_clock_fraction`, `time_of_day_bucket`, `intraday_jump_intensity`
- `total_variance_consistency`
- `ScheduledJump`, `scheduled_variance`, `event_non_event_metrics`
- `sv_jump_teacher`

Validation contract:

- [x] timezone、session、holiday、settlementを入力契約に含める。
- [x] 隣接expiryのtotal varianceが非減少かhard checkする。
- [x] event/non-eventとopen/midday/closeを分けて評価する。
- [x] dealer-flowの因果は主張せず、DML/PIDEはdisabled research trackに置く。

## G5 — RFR and post-LIBOR smiles

Public API:

- `hullkit.rfr.BusinessCalendar`, `RFRConvention`, `daily_accrual_schedule`, `compounded_rfr`
- `rfr_coupon`, `continuous_compounding_approximation`, `RfrCurve`, `curve_basis_spread`
- `futures_forward_from_covariance`, `policy_jump_path`, `collateralized_present_value`
- `hullkit.rfr_options.bachelier_price`, `gaussian_quadrature_price`, `compounded_rate_option_mc`
- `hullkit.sabr_normal.normal_sabr_implied_vol`, `shifted_sabr_implied_vol`,
  `free_boundary_sabr_implied_vol`, `normal_sabr_mc_price`
- `hagan_error_diagnostics`, `call_grid_arbitrage_diagnostics`, `compare_delta_hedges`

Validation contract:

- [x] lookback、lockout、observation shift、in-advance/in-arrearsを独立テストする。
- [x] zero-vol hand checkとcontinuous-compounding limitを固定する。
- [x] curve/basis、convexity、policy jump、collateral currencyを別scenarioにする。
- [x] Bachelier → shifted/free-boundary SABR → quadrature/MC teacherのladderを作る。
- [x] Hagan errorとstatic arbitrage、sticky-strike/Bartlett deltaを別metricで報告する。
- [x] Deep XVA/SIMM/MVAは既存`hullkit.xva`へのhandoffに留める。

## G6 — Crypto perpetuals, liquidation, and AMMs

Public API:

- `hullkit.perpetuals`: linear/inverse/quanto P&L、index/mark/last state、funding ledger、basis feedback
- `hullkit.liquidation`: margin account、bankruptcy/liquidation price、oracle shock、execution、waterfall
- `hullkit.amm`: CPMM、concentrated liquidity、fee、LVR、dynamic fee

Validation contract:

- [x] payoff sign conventionとfundingのzero-sum identityをhand checkする。
- [x] insurance fund → ADL → socialized lossを同じstress ledgerで保存する。
- [x] oracle age/dislocation/latency/manipulationを明示的なshockとする。
- [x] LVR reductionとfee compensationを別指標にする。
- [x] cascade fixtureはsyntheticと明記し、実市場再現と表現しない。

## G7 — Carbon, weather, and renewable PPAs

Public API:

- `hullkit.carbon`: Black-76、GBM/Heston/SV+jump MC、return/variance/jump premium sensitivity
- `hullkit.weather`: trend/seasonality、OU/fOU、degree-day、premium principle、station basis hedge
- `hullkit.ppa`: fixed/pay-as-produced/floor-collar、price-generation scenario、fair value、CFaR/CVaR、hedge sensitivity

Validation contract:

- [x] non-traded weather indexのpremium principleを入力として明示する。
- [x] station/location/index mismatchをbasis residualとして測る。
- [x] PPA fair value、shape/volume/profile risk、CFaR/CVaR、hedge residualを分ける。
- [x] storage real optionはdisabled research trackとし、coreを遅延させない。

## Delivery

各volumeは`johnhull/volumes/21_*`〜`25_*`にreference JSON/NPZ、実行済みnotebook、
`VALIDATION.md`を持つ。book・portal・ROADMAPとの整合は`make hull-release-check`、fresh notebook実行は
`make hull-notebooks-check`で検証する。
