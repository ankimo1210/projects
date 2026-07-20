# MODEL_INDEX — johnhull model library

How to use this index (for agents):

1. Search this file first for a model, method, or market term.
2. `package.module:symbol` names an implementation; open it under
   `johnhull/hullkit/src/hullkit/<module>.py` or
   `deep_hedge_price/src/deep_hedge_price/<module>.py`.
3. Tests are relative to each package's `tests/` directory; notebooks are
   `johnhull/volumes/<vol>/`. Companion docs: `ROADMAP.md` (volume <-> Hull
   chapters), `release_manifest.json` (vol 18-25 wiring), `VALIDATION.md`
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
| Black-Scholes-Merton prices & Greeks | Hull ch.15, 17, 19 | `hullkit.bsm:call_price`, `hullkit.bsm:put_price`, `hullkit.bsm:gamma`, `hullkit.bsm:vega`, `hullkit.bsm:vanna`, `hullkit.bsm:vomma` | `test_bsm.py` | vol 02, 03, legacy ch.15 | Pinned to Hull worked examples; put-call parity asserted |
| Cox-Ross-Rubinstein binomial tree | CRR (1979); Hull ch.13, 21 | `hullkit.trees:crr_params`, `hullkit.trees:binomial_tree`, `hullkit.trees:crr_price`, `hullkit.trees:tree_delta` | `test_trees.py` | vol 01, 06 | Converges to BSM; arbitrage guard on `p` |
| GBM Monte Carlo pricing | Hull ch.21 | `hullkit.mc:simulate_gbm_paths`, `hullkit.mc:price_european_mc` | `test_mc.py`, `test_mc_pricing.py` | vol 06 | Matches `gbm_theory` moments and BSM price within CI |
| American options by least-squares Monte Carlo | Longstaff & Schwartz (2001); Hull ch.27 | `hullkit.mc:price_american_lsm`, `hullkit.mc:lsm_exercise_boundary` | `test_mc.py` | vol 06 | LSM ~ tree ~ FD cross-check |
| Vanilla finite-difference pricer | Hull ch.21 | `hullkit.fd:fd_vanilla` | `test_fd.py` | vol 06 | Grid price vs BSM |
| Option strategy payoffs | Hull ch.10-12 | `hullkit.payoffs:leg_payoff`, `hullkit.payoffs:strategy_payoff`, `hullkit.payoffs:box_spread_value` | `test_payoffs.py` | vol 02 | Box-spread = PV of strike gap |
| Delta and stop-loss hedge simulation | Hull ch.19 | `hullkit.hedging:simulate_delta_hedge`, `hullkit.hedging:simulate_stop_loss_hedge` | `test_hedging.py` | vol 03 | Hedge-cost table pinned to Hull Table 19.2/19.3 pattern |

## 2. Volatility & smile

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Implied volatility inversion | Hull ch.20 | `hullkit.volatility:implied_vol` | `test_volatility.py` | vol 05 | Round-trips BSM prices |
| EWMA / GARCH(1,1) variance | RiskMetrics; Hull ch.23 | `hullkit.volatility:ewma_variance`, `hullkit.volatility:garch11_variance`, `hullkit.volatility:garch11_forecast`, `hullkit.volatility:garch11_fit` | `test_volatility.py` | vol 05 | Long-run variance and term-structure identities |
| Heston stochastic volatility | Heston (1993) | `hullkit.heston:heston_cf`, `hullkit.heston:heston_mc_price` | `test_heston.py` | vol 14 | COS(CF) ~ MC agreement |
| COS Fourier pricing | Fang & Oosterlee (2008) | `hullkit.fourier:cos_price`, `hullkit.fourier:cos_density` | `test_fourier.py` | vol 14 | COS == BSM under lognormal CF; density integrates to 1 |
| SABR (lognormal) smile & Greeks | Hagan et al. (2002); Hull ch.20 | `hullkit.sabr:sabr_implied_vol`, `hullkit.sabr:calibrate_sabr`, `hullkit.sabr:sabr_smile_delta` | `test_sabr.py` | vol 05 | Hagan limit checks (beta/nu edges) |
| Normal / shifted / free-boundary SABR | Hagan et al. (2002); Antonov et al. | `hullkit.sabr_normal:normal_sabr_implied_vol`, `hullkit.sabr_normal:shifted_sabr_implied_vol`, `hullkit.sabr_normal:free_boundary_sabr_implied_vol`, `hullkit.sabr_normal:bartlett_delta` | `test_sabr_normal.py` | vol 23 | Static no-arb checks at 1e-10; MC teacher cross-check |

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
| Pathwise / likelihood-ratio / bump Greeks (AAD) | Broadie & Glasserman (1996) | `hullkit.aad:pathwise_greeks`, `hullkit.aad:likelihood_ratio_greeks`, `hullkit.aad:bump_greeks` | `test_aad.py` | vol 15 | Pathwise delta == bump == closed form |

## 5. Rates & swaps (curves, IR options, RFR post-LIBOR)

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Bond math & zero-curve bootstrap | Hull ch.4-6 | `hullkit.rates:bond_price`, `hullkit.rates:macaulay_duration`, `hullkit.rates:convexity`, `hullkit.rates:forward_rate`, `hullkit.rates:bootstrap_zero_curve` | `test_rates.py` | vol 04 | Pinned to Hull examples |
| Interest-rate & currency swaps | Hull ch.7 | `hullkit.swaps:swap_rate`, `hullkit.swaps:irs_value_bonds`, `hullkit.swaps:irs_value_fras`, `hullkit.swaps:currency_swap_value` | `test_swaps.py` | vol 07 | Bond-view == FRA-view identity |
| Black-76 caps, swaptions, bond options | Black (1976); Hull ch.29 | `hullkit.ir_options:bond_option_black`, `hullkit.ir_options:cap_black`, `hullkit.ir_options:swaption_black`, `hullkit.ir_options:convexity_adjustment` | `test_ir_options.py` | vol 11 | Hull ch.29 worked examples |
| Backward-looking RFR conventions | Lyashenko & Mercurio (2019); ISDA fallbacks | `hullkit.rfr:BusinessCalendar`, `hullkit.rfr:RFRConvention`, `hullkit.rfr:compounded_rfr`, `hullkit.rfr:rfr_coupon`, `hullkit.rfr:RfrCurve`, `hullkit.rfr:MultiCurveScenario`, `hullkit.rfr:futures_forward_from_covariance`, `hullkit.rfr:policy_jump_path` | `test_rfr.py` | vol 23 | Daily-compounding hand checks = 0 error; convention edge cases |
| Bachelier options on compounded rates | Bachelier (1900); post-LIBOR practice | `hullkit.rfr_options:bachelier_price`, `hullkit.rfr_options:gaussian_quadrature_price`, `hullkit.rfr_options:compounded_rate_option_mc` | `test_rfr_options.py` | vol 23 | Quadrature vs MC vs closed form (~1e-18 hand check) |

## 6. Risk & credit (VaR, CDS, XVA, copula)

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Historical & normal VaR / ES | Hull ch.22 | `hullkit.risk:historical_var_es`, `hullkit.risk:normal_var`, `hullkit.risk:normal_es`, `hullkit.risk:portfolio_sigma` | `test_risk.py` | vol 08 | Pinned to Hull examples |
| Hazard rates & CDS pricing | Hull ch.24-25 | `hullkit.credit:hazard_from_spread`, `hullkit.credit:cds_spread`, `hullkit.credit:survival_prob` | `test_credit.py` | vol 09 | Spread round-trip |
| Merton structural default model | Merton (1974) | `hullkit.credit:merton_default_prob` | `test_credit.py` | vol 09 | d2 convention pinned (sigma*sqrt(T)) |
| Vasicek / Gaussian copula portfolio credit | Vasicek (2002); Hull ch.25 | `hullkit.copula:vasicek_loss_cdf`, `hullkit.copula:gaussian_copula_samples`, `hullkit.credit:vasicek_credit_var` | `test_copula.py`, `test_credit.py` | vol 09, 16 | Mean = pd; tail fattens with rho |
| XVA exposures (EE/PFE/CVA/DVA/FVA) | Hull ch.9; Green, *XVA* | `hullkit.xva:expected_exposure`, `hullkit.xva:pfe`, `hullkit.xva:cva`, `hullkit.xva:dva`, `hullkit.xva:fva` | `test_xva.py` | vol 16, 17 | CVA hand-calculation match |

## 7. Exotics & martingales

| Model | Theory | Implementation | Tests | Notebook | Validation |
|---|---|---|---|---|---|
| Digital, barrier, lookback options | Hull ch.26 | `hullkit.exotics:cash_or_nothing`, `hullkit.exotics:barrier_call`, `hullkit.exotics:lookback_floating_call` | `test_exotics.py` | vol 10 | In-out parity; domain guards |
| Asian options (Turnbull-Wakeman) | Turnbull & Wakeman (1991); Hull ch.26 | `hullkit.exotics:asian_call_turnbull_wakeman` | `test_exotics.py` | vol 10 | Moment-matched lognormal vs MC |
| Exchange options (Margrabe) | Margrabe (1978); Hull ch.26, 28 | `hullkit.exotics:exchange_option` | `test_exotics.py` | vol 10 | Numeraire-change demo |

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
| Teacher IV surfaces (Heston/SABR/rBergomi) | Heston (1993); Hagan (2002); Bayer-Friz-Gatheral (2016) | `deep_hedge_price.surface_data:ForwardSurfaceDataset`, `deep_hedge_price.surface_data:SurfaceTradeoff` | `test_surface_data.py` | vol 19 | Joint IV + variance-term objective (lambda_var Pareto) |
| Committed frontier reference artifacts | reproducibility contract | `hullkit.frontier_reference:build_frontier_reference`, `hullkit.frontier_reference:volume21_reference` | `test_frontier_reference.py` | vol 19, 21-25 | Acceptance recomputed from arrays (`frontier_acceptance.py`) |

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
| Scheduled-event variance & intraday jump intensity | event-time modeling (Sakuma 2026 as research ref) | `hullkit.zero_dte:ScheduledJump`, `hullkit.zero_dte:scheduled_variance`, `hullkit.zero_dte:intraday_jump_intensity`, `hullkit.zero_dte:total_variance_consistency` | `test_zero_dte.py` | vol 22 | Total-variance consistency check |
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
| Renewable PPA valuation & CFaR | shape/volume/profile risk practice | `hullkit.ppa:evaluate_ppa`, `hullkit.ppa:simulate_price_generation`, `hullkit.ppa:cash_flow_risk`, `hullkit.ppa:hedge_sensitivity` | `test_ppa.py` | vol 25 | CFaR/CVaR finite; correlation sensitivity |

## 15. Infrastructure & utilities (non-model modules)

| Module | Role |
|---|---|
| `hullkit.nbplot` | Matplotlib notebook setup (`setup`, `kde_xy`) for the classic volumes |
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
| Exact joint-Gaussian rBergomi, hybrid fBM, Hawkes microstructure | `~/projects/rough_volatility` | johnhull vol 19 uses small committed artifacts only; heavy 100k-path experiments live there |
| Almgren-Chriss, Obizhaeva-Wang, reactive LOB, PPO execution | `~/projects/optimal_execution` | execution/RL is out of johnhull scope |
| Portfolio construction, leakage-safe backtests, market data connectors | `~/projects/quantkit` | research platform; johnhull stays education-first |
| Deep hedging training engine (torch) | `deep_hedge_price` (this index, sections 8-10) | hullkit stays torch-free by contract |
