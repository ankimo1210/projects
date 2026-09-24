# MODEL_INDEX — johnhull model library

How to use this index (for agents):

1. Search this file first for a model, method, or market term.
2. `package.module:symbol` names an implementation; open it under
   `johnhull/hullkit/src/hullkit/<module>.py` or
   `deep_hedge_price/src/deep_hedge_price/<module>.py`.
3. Tests are relative to each package's `tests/` directory; notebooks are
   `johnhull/volumes/<vol>/`. Companion docs: `ROADMAP.md` (volume <-> Hull
   chapters), `release_manifest.json` (vol 18-28 wiring), `VALIDATION.md`
   (what PASS does and does not mean).
4. Freshness is test-enforced: every module below must stay listed and every
   `module:symbol` reference must resolve (`test_model_index.py` in both
   packages).

Conventions: "Hull" = Hull, *Options, Futures, and Other Derivatives*, 11e
(Global Edition chapter numbering). All quantitative results in the volumes are
synthetic-data method demonstrations, not market-performance claims.

## 1. Core pricing (Black-Scholes, trees, Monte Carlo)

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Black-Scholes-Merton prices & Greeks | Hull ch.15, 17, 19 | `hullkit.bsm:call_price`, `hullkit.bsm:put_price`, `hullkit.bsm:gamma`, `hullkit.bsm:vega`, `hullkit.bsm:vanna`, `hullkit.bsm:vomma` | `test_bsm.py`, `test_greeks.py`, `test_hull_pins_options.py` | vol 02, 03 (the legacy ch.15 notebook does not import hullkit) | Pinned to Hull worked examples; put-call parity asserted |
| Known cash dividends (S0 − PV(D), Black's approximation, early-exercise conditions, bounds) | Hull ch.11 (§11.7), ch.15 (§15.12) | `hullkit.bsm:pv_dividends`, `hullkit.bsm:call_price_cash_dividends`, `hullkit.bsm:put_price_cash_dividends`, `hullkit.bsm:black_american_call_approx`, `hullkit.bsm:call_early_exercise_thresholds`, `hullkit.bsm:call_early_exercise_can_be_optimal`, `hullkit.bsm:european_call_lower_bound`, `hullkit.bsm:european_put_lower_bound`, `hullkit.bsm:put_call_parity_residual`, `hullkit.bsm:american_call_put_bounds` | `test_dividends.py` | — | Ex 15.9 (0.9742 / 0.2020 / −0.0102 / 3.67); no dividend in the option's life reduces exactly to BSM; Black ≥ European; parity (11.10) residual 0 |
| Cox-Ross-Rubinstein binomial tree | CRR (1979); Hull ch.13, 21 | `hullkit.trees:crr_params`, `hullkit.trees:binomial_tree`, `hullkit.trees:crr_price`, `hullkit.trees:tree_delta` | `test_trees.py` | vol 01, 06 | Converges to BSM; arbitrage guard on `p` |
| GBM Monte Carlo pricing | Hull ch.21 | `hullkit.mc:simulate_gbm_paths`, `hullkit.mc:price_european_mc` | `test_mc.py`, `test_mc_pricing.py` | vol 06 | Matches `gbm_theory` moments and BSM price within CI |
| American options by least-squares Monte Carlo | Longstaff & Schwartz (2001); Hull ch.27 | `hullkit.mc:price_american_lsm`, `hullkit.mc:lsm_exercise_boundary` | `test_mc_pricing.py` | vol 06 | LSM ~ tree ~ FD cross-check |
| Vanilla finite-difference pricer | Hull ch.21 | `hullkit.fd:fd_vanilla` | `test_fd.py` | vol 06 | Grid price vs BSM |
| Option strategy payoffs | Hull ch.10-12 | `hullkit.payoffs:leg_payoff`, `hullkit.payoffs:strategy_payoff`, `hullkit.payoffs:box_spread_value` | `test_payoffs.py` | vol 02 | Box-spread = PV of strike gap |
| Delta and stop-loss hedge simulation | Hull ch.19 | `hullkit.hedging:simulate_delta_hedge`, `hullkit.hedging:simulate_stop_loss_hedge` | `test_hedging.py` | vol 03 | MC hedge-cost pattern (mean/ratio checks; the printed Table 19.2/19.3 paths are not pinned) |

## 2. Volatility & smile

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Implied volatility inversion | Hull ch.20 | `hullkit.volatility:implied_vol` | `test_volatility.py` | vol 05 | Round-trips BSM prices |
| Breeden–Litzenberger implied density & smile axes (K/F0, delta) | Breeden & Litzenberger (1978); Hull ch.20 (§20.4, App. 20A) | `hullkit.volatility:breeden_litzenberger_density`, `hullkit.volatility:forward_moneyness`, `hullkit.volatility:strike_from_forward_moneyness`, `hullkit.volatility:delta_from_strike`, `hullkit.volatility:strike_from_delta` | `test_volatility.py`, `test_hull_pins_vol_var.py` | vol 05 | Ex 20A.1 g1..g8 and area 0.9985; flat σ → lognormal within 4e-4·δ²·peak (O(δ²)) |
| EWMA / GARCH(1,1) variance | RiskMetrics; Hull ch.23 | `hullkit.volatility:ewma_variance`, `hullkit.volatility:ewma_covariance`, `hullkit.volatility:garch11_variance`, `hullkit.volatility:garch11_long_run`, `hullkit.volatility:garch11_forecast`, `hullkit.volatility:garch11_fit` | `test_volatility.py` | vol 05 | Long-run variance and term-structure identities |
| Heston stochastic volatility | Heston (1993) | `hullkit.heston:heston_cf`, `hullkit.heston:heston_mc_price` | `test_heston.py` | vol 14 | COS(CF) ~ MC agreement |
| COS Fourier pricing | Fang & Oosterlee (2008) | `hullkit.fourier:cos_price`, `hullkit.fourier:cos_density` | `test_fourier.py` | vol 14 | COS == BSM under lognormal CF; density integrates to 1 |
| SABR (lognormal) smile & Greeks | Hagan et al. (2002); Hull §27.2 | `hullkit.sabr:sabr_implied_vol`, `hullkit.sabr:calibrate_sabr`, `hullkit.sabr:sabr_smile_delta` | `test_sabr.py` | vol 14 | Hagan limit checks (beta/nu edges) |
| Normal / shifted / free-boundary SABR | Hagan et al. (2002); free-boundary variant uses an explicit shift boundary, not the Antonov et al. endogenous boundary | `hullkit.sabr_normal:normal_sabr_implied_vol`, `hullkit.sabr_normal:shifted_sabr_implied_vol`, `hullkit.sabr_normal:free_boundary_sabr_implied_vol`, `hullkit.sabr_normal:bartlett_delta` | `test_sabr_normal.py` | vol 23 | Static no-arb checks at 1e-10; MC teacher cross-check |

## 3. Stochastic calculus & SDE

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Brownian paths & quadratic variation | Hull ch.14; Ito calculus | `hullkit.sde:brownian_paths`, `hullkit.sde:quadratic_variation`, `hullkit.sde:ito_riemann_sum` | `test_sde.py` | vol 13 | QV -> t; Ito correction = half QV |
| Euler-Maruyama discretization | Kloeden & Platen | `hullkit.sde:euler_maruyama` | `test_sde.py` | vol 13 | Moment match vs exact GBM |
| Girsanov measure change | Hull ch.28 | `hullkit.sde:girsanov_weights` | `test_sde.py` | vol 13 | Reweighted drift recovery |

## 4. Numerical methods (variance reduction, QMC, AAD)

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Explicit FD with stability analysis | von Neumann analysis; Hull ch.21 | `hullkit.fd_advanced:fd_explicit`, `hullkit.fd_advanced:stability_factor` | `test_fd_advanced.py` | vol 15 | Divergence demonstrated for factor > 0.5 |
| Control variates / importance sampling / Sobol QMC | Glasserman (2004) | `hullkit.mc_advanced:control_variate_price`, `hullkit.mc_advanced:importance_sampling_price`, `hullkit.mc_advanced:qmc_price`, `hullkit.mc_advanced:error_vs_n` | `test_mc_advanced.py` | vol 15 | Error-vs-n slopes; CV variance reduction |
| Pathwise / likelihood-ratio / bump Greeks (no AAD tape) | Broadie & Glasserman (1996) | `hullkit.aad:pathwise_greeks`, `hullkit.aad:likelihood_ratio_greeks`, `hullkit.aad:bump_greeks` | `test_aad.py` | vol 15 | Pathwise delta == bump == closed form |

## 5. Rates & swaps (curves, IR options, RFR post-LIBOR)

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Bond math & zero-curve bootstrap | Hull ch.4 (ch.5–6 have no hullkit symbols; see vol 04) | `hullkit.rates:bond_price`, `hullkit.rates:macaulay_duration`, `hullkit.rates:convexity`, `hullkit.rates:forward_rate`, `hullkit.rates:bootstrap_zero_curve` | `test_rates.py` | vol 04 | Pinned to Hull ch.4 examples |
| Interest-rate & currency swaps | Hull ch.7 | `hullkit.swaps:swap_rate`, `hullkit.swaps:irs_value_bonds`, `hullkit.swaps:irs_value_fras`, `hullkit.swaps:currency_swap_value` | `test_swaps.py` | vol 07 | Bond-view == FRA-view identity; seasoned swap (`first_accrual`) pinned to Hull Ex 7.1 (−0.292 receive-fixed) |
| Black-76 caps, swaptions, bond options | Black (1976); Hull ch.29 | `hullkit.ir_options:bond_option_black`, `hullkit.ir_options:cap_black`, `hullkit.ir_options:swaption_black`, `hullkit.ir_options:convexity_adjustment`, `hullkit.ir_options:bond_yield_convexity` | `test_ir_options.py`, `test_hull_pins_exotics_ir.py` | vol 11 | Hull Ex 29.1 / 29.3 / 29.4 and Ex 30.1 (G′ −2.6730, G″ 9.8910) pinned; Black parity |
| Backward-looking RFR conventions | Lyashenko & Mercurio (2019); ISDA fallbacks | `hullkit.rfr:BusinessCalendar`, `hullkit.rfr:RFRConvention`, `hullkit.rfr:compounded_rfr`, `hullkit.rfr:rfr_coupon`, `hullkit.rfr:RfrCurve`, `hullkit.rfr:MultiCurveScenario`, `hullkit.rfr:futures_forward_from_covariance`, `hullkit.rfr:policy_jump_path` | `test_rfr.py` | vol 23 | Daily-compounding hand checks = 0 error; convention edge cases |
| Bachelier options on compounded rates | Bachelier (1900); post-LIBOR practice | `hullkit.rfr_options:bachelier_price`, `hullkit.rfr_options:gaussian_quadrature_price`, `hullkit.rfr_options:compounded_rate_option_mc` | `test_rfr_options.py` | vol 23 | Quadrature vs MC vs closed form (~1e-18 hand check) |
| Hull–White one-factor term structure | Hull & White (1990) | `hullkit.hull_white:HullWhiteParams`, `hullkit.hull_white:hw_discount_bond`, `hullkit.hull_white:hw_zcb_option`, `hullkit.hull_white:hw_jamshidian_swaption`, `hullkit.hull_white:calibrate_hw1f` | `test_hull_white.py`, `test_hull_pins_exotics_ir.py` | vol 26 (the legacy IR notebook does not import hullkit) | Initial-curve fit; exact OU moments; ZCB parity; Jamshidian vs quadrature |
| CPI conventions, seasonality, ZCIS, and YoY swaps | Wu (2013); Canty (2009); Fisher relation | `hullkit.inflation:CPIObservationConvention`, `hullkit.inflation:MonthlySeasonality`, `hullkit.inflation:ZeroCouponInflationCurve`, `hullkit.inflation:interpolated_cpi`, `hullkit.inflation:seasonal_forward_index`, `hullkit.inflation:zcis_npv`, `hullkit.inflation:yoy_swap_npv` | `test_inflation.py` | vol 26 | Fixing/forecast split; quote round-trip; annual seasonality cancellation; explicit expected YoY ratios |
| Japanese inflation-linked government bonds (JGBi) and deflation floor | Ministry of Finance Japan JGBi conventions | `hullkit.jgbi:JGBITerms`, `hullkit.jgbi:jgbi_reference_index`, `hullkit.jgbi:jgbi_indexation_coefficient`, `hullkit.jgbi:jgbi_cashflows`, `hullkit.jgbi:jgbi_real_clean_price`, `hullkit.jgbi:jgbi_real_yield`, `hullkit.jgbi:jgbi_deflation_floor_jy`, `hullkit.jgbi:jgbi_floor_adjusted_price`, `hullkit.jgbi:jgbi_floor_risk` | `test_jgbi.py`, `test_jgbi_floor.py` | vol 26 | Three-month lag; tenth-day interpolation; staged rounding; redemption-only floor; analytic/MC option decomposition |
| Jarrow--Yildirim inflation model | Jarrow & Yildirim (2003) | `hullkit.jarrow_yildirim:JarrowYildirimParams`, `hullkit.jarrow_yildirim:jy_cpi_forward`, `hullkit.jarrow_yildirim:jy_payment_forward_cpi`, `hullkit.jarrow_yildirim:jy_cpi_total_variance`, `hullkit.jarrow_yildirim:jy_expected_cpi_ratio`, `hullkit.jarrow_yildirim:jy_cpi_option`, `hullkit.jarrow_yildirim:simulate_jy_paths` | `test_jarrow_yildirim.py` | vol 26 | Nominal/real numeraires; payment-forward measures; real-rate quanto drift; analytic/MC CPI options |

## 6. Risk & credit (VaR, CDS, XVA, copula)

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Historical & normal VaR / ES | Hull ch.22 | `hullkit.risk:historical_var_es`, `hullkit.risk:normal_var`, `hullkit.risk:normal_es`, `hullkit.risk:portfolio_sigma` | `test_risk.py` | vol 08 | Pinned to Hull examples |
| VaR backtesting (Kupiec POF, Christoffersen, Basel traffic light) | Kupiec (1995); Christoffersen (1998); BCBS (1996) | `hullkit.var_backtest:exceedance_series`, `hullkit.var_backtest:kupiec_pof`, `hullkit.var_backtest:christoffersen_independence`, `hullkit.var_backtest:christoffersen_cc`, `hullkit.var_backtest:basel_traffic_light`, `hullkit.var_backtest:BaselZone` | `test_var_backtest.py` | vol 27 | Hand-computed LR_pof; CC = POF(transitions) + independence exact identity; Basel zone/multiplier pinned at n=250 |
| Filtered historical simulation & EVT/GPD tail VaR-ES | Barone-Adesi, Giannopoulos & Vosper (1999); McNeil & Frey (2000); McNeil, Frey & Embrechts, *QRM* | `hullkit.tail_risk:filtered_historical_var_es`, `hullkit.tail_risk:fit_gpd_pot`, `hullkit.tail_risk:evt_var_es`, `hullkit.tail_risk:mean_excess`, `hullkit.tail_risk:GPDFit` | `test_tail_risk.py` | vol 27 | FHS == historical_var_es at constant sigma; current_sigma doubling homogeneity; GPD MLE recovers seeded xi/beta and exponential (xi~0) limit; evt_var_es matches independent genpareto.ppf quantile; mean-excess slope matches xi/(1-xi) via quadrature |
| Risk decomposition: Euler marginal/component/incremental VaR-ES | Tasche (1999); Tasche (2008) | `hullkit.risk_allocation:marginal_var_normal`, `hullkit.risk_allocation:component_var_normal`, `hullkit.risk_allocation:incremental_var`, `hullkit.risk_allocation:euler_es_components` | `test_risk_allocation.py` | vol 27 | component_var_normal sums to normal_var(portfolio_sigma) at 1e-12; marginal_var_normal matches central finite differences at rel 1e-6; euler_es_components sums to historical ES of the total (incl. tied worst-scenario rows) at 1e-12; incremental_var shows diversification and dominant-vs-hedge ordering on a seeded book |
| P&L explain: factor exposures, delta-gamma-vega attribution, limits, desk report | Desk P&L-explain / limit-monitoring practice (Hull ch.22 framing) | `hullkit.pnl_explain:aggregate_exposures`, `hullkit.pnl_explain:delta_gamma_vega_pnl`, `hullkit.pnl_explain:pnl_attribution`, `hullkit.pnl_explain:limit_utilization`, `hullkit.pnl_explain:desk_report` | `test_pnl_explain.py` | vol 27 | Linear book: delta explain == full revaluation at 1e-12; diagonal-quadratic payoff: delta+gamma explain exact at 1e-12; BSM full revaluation (via hullkit.bsm): delta-gamma-vega residual < delta-only residual and shrinks ~4x per move-halving (cross-gammas out of scope); limit utilization/breach flags and ValueError on non-positive limits; desk_report is deterministic and JSON-able |
| Hazard rates & CDS pricing | Hull ch.24-25 | `hullkit.credit:hazard_from_spread`, `hullkit.credit:cds_spread`, `hullkit.credit:survival_prob` | `test_credit.py` | vol 09 | Spread round-trip |
| Merton structural default model | Merton (1974) | `hullkit.credit:merton_default_prob` | `test_credit.py` | vol 09 | d2 convention pinned (sigma*sqrt(T)) |
| Vasicek / Gaussian copula portfolio credit | Vasicek (2002); Hull eq. (24.10) | `hullkit.copula:vasicek_loss_cdf`, `hullkit.copula:gaussian_copula_samples`, `hullkit.credit:vasicek_credit_var` | `test_copula.py`, `test_credit.py` | vol 09, 16 | Mean = pd; tail fattens with rho |
| XVA exposures (EE/PFE/CVA/DVA/FVA) | Hull ch.9; Green, *XVA* | `hullkit.xva:expected_exposure`, `hullkit.xva:pfe`, `hullkit.xva:cva`, `hullkit.xva:dva`, `hullkit.xva:fva` | `test_xva.py` | vol 16, 17, 28 | CVA hand-calculation match |
| Piecewise hazard curves; bond-price and spread bootstraps | Hull §24.4 (Examples 24.1, 24.2) | `hullkit.credit_curve:HazardCurve`, `hullkit.credit_curve:average_hazards_from_spreads`, `hullkit.credit_curve:forward_hazards_from_average`, `hullkit.credit_curve:bond_price_from_yield`, `hullkit.credit_curve:risk_free_bond_price`, `hullkit.credit_curve:forward_risk_free_value`, `hullkit.credit_curve:expected_default_loss_pv`, `hullkit.credit_curve:bootstrap_from_bonds`, `hullkit.credit_curve:BondBootstrapResult` | `test_credit_curve.py` | vol 28 | Ex 24.1 average→forward 3.5/3.75%; Ex 24.2 λ=2.46/3.48/3.74%, loss PV 1.50/3.53/5.61 |
| Single-name CDS legs, MTM, binary, fixed coupon/upfront, forward, option | Hull §25.2–25.5 (Tables 25.1–25.5, Example 25.1); Hull & White (2003) | `hullkit.cds:CDSLegs`, `hullkit.cds:cds_legs`, `hullkit.cds:cds_par_spread`, `hullkit.cds:cds_risky_duration`, `hullkit.cds:cds_mtm`, `hullkit.cds:binary_cds_spread`, `hullkit.cds:implied_hazard`, `hullkit.cds:bootstrap_from_cds`, `hullkit.cds:actual360_to_actual_actual`, `hullkit.cds:fixed_coupon_price`, `hullkit.cds:upfront_payment`, `hullkit.cds:cds_forward_spread`, `hullkit.cds:cds_option` | `test_cds.py` | vol 28 | 4.0728s/0.0422s/0.0506 → 123 bp; MTM 0.0111; binary 205 bp; Ex 25.1 λ=0.5717%, D=4.447, P=100.27; option parity |
| Synthetic CDO / kth-to-default by one-factor copula quadrature; compound & base correlation; double-t; ASB recursion | Hull §25.6–25.11 (Examples 25.2, 25.3, Tables 25.6–25.8); Andersen–Sidenius–Basu (2003); Hull & White (2004) | `hullkit.credit_portfolio:gauss_hermite_factor`, `hullkit.credit_portfolio:conditional_default_prob`, `hullkit.credit_portfolio:binomial_pmf`, `hullkit.credit_portfolio:heterogeneous_default_pmf`, `hullkit.credit_portfolio:tranche_principal_by_defaults`, `hullkit.credit_portfolio:TrancheValuation`, `hullkit.credit_portfolio:cdo_tranche_valuation`, `hullkit.credit_portfolio:cdo_tranche_spread`, `hullkit.credit_portfolio:cdo_upfront`, `hullkit.credit_portfolio:KthToDefaultValuation`, `hullkit.credit_portfolio:kth_to_default_valuation`, `hullkit.credit_portfolio:kth_to_default_spread`, `hullkit.credit_portfolio:compound_correlation`, `hullkit.credit_portfolio:base_correlations`, `hullkit.credit_portfolio:BaseCorrelationResult`, `hullkit.credit_portfolio:expected_loss_curve`, `hullkit.credit_portfolio:double_t_threshold`, `hullkit.credit_portfolio:double_t_conditional_prob`, `hullkit.credit_portfolio:double_t_factor_quadrature` | `test_credit_portfolio.py` | vol 28 | Ex 25.2 A/B/C=4.2846/0.0187/0.1496 → 348 bp incl. Table 25.7 columns; Ex 25.3 153 bp; Table 25.8 compound 17.7/7.8/14.0/18.2/23.3%, base 17.7/28.4/36.5/43.2/60.5%; loss conservation; ν→∞ Gaussian limit; ASB = binomial |
| CreditMetrics rating-transition credit VaR | Hull §24.9 (Table 24.4) | `hullkit.credit_metrics:TransitionMatrix`, `hullkit.credit_metrics:rating_thresholds`, `hullkit.credit_metrics:migrate`, `hullkit.credit_metrics:simulate_rating_migrations`, `hullkit.credit_metrics:credit_loss_distribution`, `hullkit.credit_metrics:credit_var`, `hullkit.credit_metrics:expected_loss` | `test_credit_metrics.py` | vol 28 | Thresholds 1.2719/2.4089/2.8070 and −3.7190/−3.0618/−1.7866, BBB default > 2.9290 (exact p_default, AAA never defaults); default frequency within binomial SE; ρ fattens the tail |
| Netting, collateral (cure period) and spread-implied CVA | Hull §24.7 (Example 24.4, eq. 24.5) | `hullkit.xva:default_probs_from_spreads`, `hullkit.xva:netting_set_exposure`, `hullkit.xva:collateralized_exposure`, `hullkit.xva:cva_single_payoff` | `test_xva.py` | vol 28 | 40 → 15 with netting; Ex 24.4 exposures 5/0/0/5; eq. 24.5 equals the general CVA with EE = f_nd e^{rt} |

## 7. Exotics & martingales

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Digital, gap, barrier, lookback options | Hull ch.26; Broadie–Glasserman–Kou (1997) | `hullkit.exotics:cash_or_nothing`, `hullkit.exotics:gap_put`, `hullkit.exotics:barrier_call`, `hullkit.exotics:barrier_put`, `hullkit.exotics:bgk_adjusted_barrier`, `hullkit.exotics:lookback_floating_call`, `hullkit.exotics:lookback_floating_put`, `hullkit.exotics:lookback_fixed_call`, `hullkit.exotics:lookback_fixed_put` | `test_exotics.py`, `test_exotics_puts.py`, `test_barrier_reference.py`, `test_lookback_reference.py` | vol 10 | §26.9: 48 independent bridge-integral cases, 16 inception-touch cases, 24 terminal-fixing cases, 64 displayed-price checks, negative vega; in-out parity; Ex 26.1 gap put (1,896) and Ex 26.2 floating lookback put (7.79) pinned; BGK and lookbacks within 3 SE of MC; section26.11: 128 independent extrema-tail prices, call/put Ex26.2 anchors, parity-preserving bias rejection |
| Asian options (moment matching) | Turnbull & Wakeman (1991); Hull §26.13 eqs. 26.3-26.4; Margrabe (1978) | `hullkit.exotics:asian_moments`, `hullkit.exotics:asian_average_price`, `hullkit.exotics:asian_call_turnbull_wakeman`, `hullkit.exotics:asian_seasoned_average_price`, `hullkit.exotics:asian_average_strike` | `test_exotics.py`, `test_asian_pricing.py`, `test_asian_reference.py` | vol 10 | §26.13: exact discrete moments; Ex 26.3 (5.62 / 12-52-250 dates 6.00-5.70-5.63) pinned; put-call parity to 1e-10; 144 rows against a geometric-control simulation and an exact two-date conditioning price; the moment match both overprices (+23.35%) and underprices (-6.85%) |
| Positive basket options (moment matching) | Hull §26.15 | `hullkit.exotics:basket_moments`, `hullkit.exotics:basket_option_price` | `test_basket_pricing.py`, `test_basket_reference.py` | vol 10 | Exact first/second moments and Black-forward lognormal proxy; 18 frozen two-asset proxy prices, direct put-call parity, single-asset and rho=1 proportional anchors; conditional/MC residuals are disclosed, not an accuracy claim |
| Private single-shout teaching tree | Hull §26.12 call; independently priced put extension | `hullkit._shout:_price`, `hullkit._shout:_tree` | `test_shout_tree.py` | vol 10 | CRR versus 42 frozen independent prices; signed payoff integration; actual node boundary brackets versus engine B; finite decision dates approximate continuous shouting |
| Exchange options (Margrabe) | Margrabe (1978); Hull §26.14; Rubinstein (1991) | `hullkit.exotics:exchange_option`, `hullkit.exotics:exchange_spread_volatility`, `hullkit.exotics:exchange_option_american`, `hullkit.exotics:better_of_two_assets`, `hullkit.exotics:worse_of_two_assets` | `test_exotics.py`, `test_exchange_reference.py`, `test_exchange_pricing.py` | vol 10 | §26.14: 24 prices against conditioning and numeraire-change quadratures agreeing to 1.8e-14 and a control-variate simulation; rate independence measured over r in {0, 8%, -2%}; better-of/worse-of decomposition to 8.5e-14; Rubinstein's American tree on V/U, whose early-exercise premium is 1.2e-13 at qV=0 against a 2.7e-3 grid residual, and up to 7.95 at qV=6% |
| Variance & volatility swaps (static OTM-strip replication) | Demeterfi et al. (1999); Hull §26.16 eqs. 26.6-26.10 | `hullkit.variance_swaps:realized_variance`, `hullkit.variance_swaps:realized_volatility`, `hullkit.variance_swaps:variance_notional`, `hullkit.variance_swaps:fair_variance`, `hullkit.variance_swaps:fair_variance_from_implied_vols`, `hullkit.variance_swaps:vix_cumulative_variance`, `hullkit.variance_swaps:vix_index`, `hullkit.variance_swaps:variance_swap_value`, `hullkit.variance_swaps:expected_volatility`, `hullkit.variance_swaps:volatility_swap_value` | `test_variance_swaps.py`, `test_variance_swap_contracts.py`, `test_variance_swap_reference.py` | vol 10 §4.6 | Hull Ex 26.4 (0.0621 / 1.69) and Ex 26.5 (0.2484 / 1.82) pinned; flat smile recovers sigma^2 up to the derived dK^2 grid bias; library strips equal an independent Heston reference whose continuous eq. 26.6 integral matches the closed-form E(V) within 1.5e-12; eq. 26.9 measured against the exact CIR-Laplace E[sqrt V] (error O(xi^4)); `docs/validation/section-26-16/` |

## 8. ML surrogates & differential machine learning

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Teacher data with MC uncertainty (CRN) | Glasserman (2004); Huge & Savine (2020) | `hullkit.surrogate_data:analytic_bsm_rows`, `hullkit.surrogate_data:mc_black_scholes_call_estimates`, `hullkit.surrogate_data:heston_cos_price`, `hullkit.surrogate_data:rbergomi_call_price` | `test_surrogate_data.py` | vol 18 | 20-seed CI coverage 0.9-1.0; SE ~ 1/sqrt(n) |
| Hard no-arbitrage validation suite | Merton bounds; Hull ch.11 | `hullkit.surrogate_validation:check_price_bounds`, `hullkit.surrogate_validation:check_put_call_parity`, `hullkit.surrogate_validation:check_strike_convexity`, `hullkit.surrogate_validation:check_calendar_monotonicity`, `hullkit.surrogate_validation:validation_report` | `test_surrogate_validation.py` | vol 18, 19 | `arbitrage_free` only when the complete check set passes |
| Fingerprinted pricing dataset artifacts | reproducibility contract (spec 2026-07-18) | `deep_hedge_price.pricing_artifacts:PricingDatasetManifest`, `deep_hedge_price.pricing_artifacts:split_overlap_count`, `deep_hedge_price.pricing_artifacts:fingerprint_rows` | `test_pricing_artifacts.py` | vol 18 | Split overlap = 0 enforced |
| Neural pricing surrogate (price / multi-task / DML) | Huge & Savine (2020) | `deep_hedge_price.pricing_policy:PricingMLP`, `deep_hedge_price.pricing_policy:PolynomialRidge`, `deep_hedge_price.pricing_losses:price_and_greek_loss`, `deep_hedge_price.pricing_losses:differential_delta_loss`, `deep_hedge_price.pricing_training:load_pricing_model` | `test_pricing_policy.py`, `test_pricing_training_smoke.py` | vol 18 | BS price MAE < 1e-3*K, delta MAE < 2e-3 (acceptance) |
| Autodiff vs direct-head Greeks | Broadie & Glasserman (1996) | `deep_hedge_price.greeks:autodiff_greeks`, `deep_hedge_price.greeks:direct_autodiff_consistency` | `test_pricing_greeks.py` | vol 18 | Consistency error reported per Greek |
| Soft arbitrage penalties | soft-vs-hard constraint comparison | `deep_hedge_price.arbitrage:price_bound_penalty`, `deep_hedge_price.arbitrage:structured_surface_penalty`, `deep_hedge_price.arbitrage:hard_validation_report` | `test_arbitrage.py` | vol 18 | Violations quantified before/after penalty |
| Seeded ablation protocol | negative-result-friendly design | `deep_hedge_price.pricing_ablation:PricingAblationProtocol` | `test_pricing_ablation.py` | vol 18 | 3-seed CPU reference JSON |

## 9. Inverse problems & arbitrage-aware surfaces

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| SSVI surface & butterfly checks | Gatheral & Jacquier (2014) | `hullkit.vol_surface:fit_ssvi_slice`, `hullkit.vol_surface:ssvi_butterfly_margins`, `hullkit.vol_surface:ssvi_total_variance` | `test_vol_surface.py` | vol 19 | Butterfly margins non-negative for safe params |
| Convex call-price projection (hard constraint) | Ait-Sahalia & Duarte (2003) style | `hullkit.vol_surface:project_convex_call_prices`, `hullkit.vol_surface:compare_surface_constraints` | `test_vol_surface.py` | vol 19 | Unconstrained/soft/hard trade-off in one table |
| Two-step calibration (forward surrogate + optimizer) | Bayer et al. (2019); Horvath et al. (2021) | `deep_hedge_price.pricing_calibration:CalibrationResult`, `deep_hedge_price.pricing_calibration:DirectInverseRidge` | `test_pricing_calibration.py` | vol 19 | Multi-start dispersion; repricing RMSE ~ 5e-11 |
| Teacher IV surfaces (Heston/SABR/rBergomi; teacher data, not a forward surrogate) | Heston (1993); Hagan (2002); Bayer-Friz-Gatheral (2016) | `deep_hedge_price.surface_data:ForwardSurfaceDataset`, `deep_hedge_price.surface_data:SurfaceTradeoff` | `test_surface_data.py` | vol 19 | Joint IV + variance-term objective (lambda_var Pareto) |
| Committed frontier reference artifacts | reproducibility contract | `hullkit.frontier_reference:build_frontier_reference`, `hullkit.frontier_reference:volume21_reference` | `test_frontier_reference.py` | vol 21-28 | Acceptance recomputed from arrays (`frontier_acceptance.py`; tamper contract for vol 23-25, 27, 28) |

## 10. Surface dynamics, forecasting & hedging decisions

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Purged walk-forward splits & train-window transforms | Lopez de Prado (2018) | `deep_hedge_price.volatility_data:purged_walk_forward_splits`, `deep_hedge_price.volatility_data:TrainWindowStandardizer`, `deep_hedge_price.volatility_data:TrainWindowPCA` | `test_volatility_data.py` | vol 20 | Embargo/overlap audited; fit on train window only |
| Classical vol forecasts (persistence/EWMA/GARCH/Log-HAR) | Corsi (2009) HAR; Hull ch.23 | `deep_hedge_price.walk_forward:persistence_forecast`, `deep_hedge_price.walk_forward:ewma_forecast`, `deep_hedge_price.walk_forward:garch11_variance_forecast`, `deep_hedge_price.walk_forward:fit_regularized_linear` | `test_walk_forward.py` | vol 20 | Log-HAR is the mandatory baseline |
| Neural challengers (HARNet/TCN/LSTM/Transformer) | Reisenhofer et al. (2022); PatchTST-style encoders | `deep_hedge_price.walk_forward:SequenceForecaster`, `deep_hedge_price.walk_forward:fit_sequence_forecaster` | `test_walk_forward.py` | vol 20 | QLIKE/RMSE/MAE with block-bootstrap CIs; no winner baked in |
| Forecast metrics & bootstrap CIs | Patton (2011) QLIKE | `deep_hedge_price.walk_forward:forecast_metrics`, `deep_hedge_price.walk_forward:block_bootstrap_metric_ci` | `test_walk_forward.py` | vol 20 | Regime/horizon breakdown |
| Attention & feature diagnostics (not explanations) | Jain & Wallace (2019) | `deep_hedge_price.feature_diagnostics:permutation_importance`, `deep_hedge_price.feature_diagnostics:occlusion_importance`, `deep_hedge_price.feature_diagnostics:integrated_gradients`, `deep_hedge_price.feature_diagnostics:diagnostic_rank_stability` | `test_feature_diagnostics.py` | vol 20 | Cross-method rank stability reported |
| Deep hedging policy (Phase 1) | Buehler et al. (2019) | `deep_hedge_price.policy:MLPHedgePolicy`, `deep_hedge_price.risks:RiskObjective`, `deep_hedge_price.risks:cvar_objective`, `deep_hedge_price.simulation:simulate_gbm`, `deep_hedge_price.pnl:rollout_policy`, `deep_hedge_price.pnl:account_hedge` | `test_policy.py`, `test_risks.py`, `test_pnl.py` | notebook 01 | BS-delta and no-hedge baselines on common paths |
| Common-path hedge comparison capstone | economic evaluation (P&L/CVaR/turnover) | `deep_hedge_price.hedge_capstone:HedgeComparison`, `deep_hedge_price.surface_hedge_pipeline:run_synthetic_surface_hedge_pipeline` | `test_hedge_capstone.py`, `test_surface_hedge_pipeline.py` | vol 20 | Same premium/costs/512 common paths across strategies |

## 11. SPX/VIX & path-dependent volatility

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| 4-factor path-dependent volatility | Guyon & Lekeufack (2023) | `hullkit.spx_vix:PDVParameters`, `hullkit.spx_vix:four_factor_pdv` | `test_spx_vix.py` | vol 21 | Coefficient/decay validation; finite paths |
| Affine forward variance / rough Heston kernel | Gatheral-Jaisson-Rosenbaum; El Euch-Rosenbaum | `hullkit.spx_vix:affine_forward_variance`, `hullkit.spx_vix:rough_heston_fractional_kernel` | `test_spx_vix.py` | vol 21 | Kernel limits |
| Quintic OU volatility | Abi Jaber et al. (2022) | `hullkit.spx_vix:quintic_ou_variance` | `test_spx_vix.py` | vol 21 | Polynomial-squared variance |
| Joint SPX/VIX calibration objective | joint calibration problem (Guyon 2020s) | `hullkit.spx_vix:joint_spx_vix_objective`, `hullkit.spx_vix:JointMarketTargets`, `hullkit.spx_vix:nested_vix_teacher` | `test_spx_vix.py` | vol 21 | All four objective components finite; nested MC teacher |
| CPU quadratic surrogate with OOD flags | frontier surrogate pattern | `hullkit.spx_vix:PolynomialSurrogate`, `hullkit.spx_vix:finite_difference_greeks` | `test_spx_vix.py` | vol 21 | Explicit training-domain box |

## 12. 0DTE (intraday clocks, events, jumps)

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Trading session & variance clock | market-microstructure conventions | `hullkit.zero_dte:TradingSession`, `hullkit.zero_dte:variance_clock_fraction`, `hullkit.zero_dte:trading_seconds_to_settlement` | `test_zero_dte.py` | vol 22 | Timezone-aware settlement; calendar violations = 0 |
| Scheduled-event variance & intraday jump intensity | event-time modeling (Sakuma 2026 as research ref) | `hullkit.zero_dte:ScheduledJump`, `hullkit.zero_dte:scheduled_variance`, `hullkit.zero_dte:intraday_jump_intensity`, `hullkit.zero_dte:scheduled_jump_intensity`, `hullkit.zero_dte:total_variance_consistency` | `test_zero_dte.py` | vol 22 | Total-variance consistency check; injected jump variance = scheduled variance (MC within 4 SE) |
| SV + jump 0DTE teacher | Bates-style SV+jump | `hullkit.zero_dte:sv_jump_teacher`, `hullkit.zero_dte:event_non_event_metrics` | `test_zero_dte.py` | vol 22 | Event/non-event and open/midday/close splits |

## 13. Crypto market structure (perps, liquidation, AMM)

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Perpetual futures funding & P&L | Kim & Park (2025), arXiv:2506.08573 | `hullkit.perpetuals:funding_rate`, `hullkit.perpetuals:funding_cashflow`, `hullkit.perpetuals:matched_funding_ledger`, `hullkit.perpetuals:position_pnl`, `hullkit.perpetuals:simulate_basis_feedback` | `test_perpetuals.py` | vol 24 | Funding conservation error <= 1e-12 |
| Margin, liquidation waterfall, insurance/ADL | exchange rulebooks (synthetic cascade) | `hullkit.liquidation:MarginAccount`, `hullkit.liquidation:liquidation_price`, `hullkit.liquidation:liquidation_waterfall`, `hullkit.liquidation:assess_oracle_risk`, `hullkit.liquidation:oracle_shock` | `test_liquidation.py` | vol 24 | Cash-conservation identities within 1e-12 |
| CPMM AMM & loss-versus-rebalancing | Milionis et al. (2022), arXiv:2208.06046 | `hullkit.amm:cpmm_swap_x_for_y`, `hullkit.amm:loss_versus_rebalancing`, `hullkit.amm:concentrated_loss_versus_rebalancing`, `hullkit.amm:dynamic_fee_rate` | `test_amm.py` | vol 24 | Invariant preservation; LVR >= 0 |

## 14. Climate & energy (carbon, weather, PPA)

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Carbon allowance options (Black-76 / SV / SV+jump) | Serafini & Bormetti (2025), arXiv:2501.17490 | `hullkit.carbon:black76_price`, `hullkit.carbon:carbon_option_mc`, `hullkit.carbon:risk_premium_sensitivity` | `test_carbon.py` | vol 25 | Model ladder MC vs Black-76; premium decomposition |
| Weather derivatives (OU/fOU, degree days, basis risk) | Alaton et al. (2002); incomplete markets | `hullkit.weather:simulate_ou_temperature`, `hullkit.weather:simulate_fractional_ou_temperature`, `hullkit.weather:degree_day_index`, `hullkit.weather:weather_contract_premium`, `hullkit.weather:optimal_basis_hedge` | `test_weather.py` | vol 25 | fOU lag-1 autocorr > OU; premium principles explicit |
| Renewable PPA valuation & CFaR | shape/volume/profile risk practice | `hullkit.ppa:evaluate_ppa`, `hullkit.ppa:simulate_price_generation`, `hullkit.ppa:cash_flow_risk`, `hullkit.ppa:hedge_sensitivity` | `test_ppa.py` | vol 25 | CFaR/CVaR rebuilt from committed samples; hedge-ratio sensitivity |

## 15. Infrastructure & utilities (non-model modules)

| Module | Role |
|---|---|
| `hullkit._asian_lesson` | Hull §26.13 の給付・平均の分布・観測回数・近似誤差を保存済みデータから共有する内部 Plotly 図ビルダー（`test_asian_lesson.py`） |
| `hullkit._binary_lesson` | Hull §26.10 の給付・複製・狭いスプレッド・cash-call delta を共有する内部 Plotly 図ビルダー |
| `hullkit._basket_lesson` | Hull §26.15 の2資産給付・相関と交差共分散寄与・近似/独立参照/MC比較・不確実性つき絶対相対誤差を保存済みデータから共有する内部 Plotly 図ビルダー（`test_basket_lesson.py`） |
| `hullkit._exchange_lesson` | Hull §26.14 の給付と分解・相関と σ̂・$r$ 非依存と $V/U$ 読み替え・米国型の早期行使を保存済みデータから共有する内部 Plotly 図ビルダー（`test_exchange_lesson.py`） |
| `hullkit._lookback_lesson` | Hull §26.11 の経路給付・履歴極値・評価時点の複製・離散 fixing を共有する内部 Plotly 図ビルダー |
| `hullkit._shout_lesson` | Hull §26.12 の給付・宣言木・実ノード境界・合成価格比較を保存済みデータから共有する内部 Plotly 図ビルダー（`test_shout_lesson.py`） |
| `hullkit.nbplot` | Matplotlib notebook setup (`setup`, `kde_xy`) for the classic volumes; `enable_static_figures` turns ipympl widgets into static PNG outputs for the committed book copies |
| `hullkit.plotly_viz` | Seeded Plotly figure builders for the offline portal (single source of figures) |
| `hullkit.teaching` | `scaffold`/`practice_box`/`caption` markdown blocks used across all volumes |
| `deep_hedge_price.cli` | Command-line entry points for training and reports |
| `deep_hedge_price.config` | Validated Phase-1 experiment configuration (YAML + fingerprint) |
| `deep_hedge_price.pricing_config` | Validated Phase-2 pricing configuration (bounds, weights, namespace) |
| `deep_hedge_price.experiments` | Artifact directory layout and JSON-safe writers |
| `deep_hedge_price.training` | Phase-1 training loop, checkpoints (`checkpoint_directory`) |
| `deep_hedge_price.evaluation` | Phase-1 evaluation metrics on common test paths |
| `deep_hedge_price.baselines` | No-hedge and Black-Scholes delta baselines |
| `deep_hedge_price.black_scholes` | Torch BS pricing/delta used inside policies and baselines |
| `deep_hedge_price.simulation` | Exact GBM path simulation (physical measure) |
| `deep_hedge_price.pnl` | Discounted trading-gain and hedged P&L accounting |
| `deep_hedge_price.pricing_data` | Latin-hypercube dataset generation for the pricing surrogate |
| `deep_hedge_price.pricing_evaluation` | Split/bucket/Greek/hard-check/benchmark evaluation (`evaluate_pricing_run`) |
| `deep_hedge_price.pricing_benchmark` | Latency/throughput benchmarks with warm-up and sync |
| `deep_hedge_price.pricing_residuals` | Residual-correction variants vs analytic baselines |
| `deep_hedge_price.research_models` | Research-track stubs (direct inverse net, local foundation adapter, diffusion scenarios) |
| `deep_hedge_price.frontier_reference` | Vol 19-20 committed reference builders on the dhp side |
| `deep_hedge_price.notebook` / `deep_hedge_price.pricing_notebook` | Deterministic notebook builders |
| `deep_hedge_price.plotting` / `deep_hedge_price.pricing_plotting` | Figure builders (matplotlib / Plotly) |
| `deep_hedge_price.report` / `deep_hedge_price.pricing_report` | Self-contained offline HTML reports |
| `deep_hedge_price.pricing_artifacts` | Manifest/NPZ round-trip with fingerprints (also listed in section 8) |

## Cross-project pointers (canonical implementations elsewhere)

| Topic | Canonical project | Note |
|---|---|---|
| Exact joint-Gaussian rBergomi, hybrid fBM, Hawkes microstructure | `~/projects/rough_volatility` | johnhull vol 19 uses its own hullkit rBergomi teacher; the heavy 100k-path experiments live there |
| Almgren-Chriss, Obizhaeva-Wang, reactive LOB, PPO execution | `~/projects/optimal_execution` | execution/RL is out of johnhull scope |
| Portfolio construction, leakage-safe backtests, market data connectors | `~/projects/quantkit` | research platform; johnhull stays education-first |
| Deep hedging training engine (torch) | `deep_hedge_price` (this index, sections 8-10) | hullkit stays torch-free by contract |
