# Limitations and Next Steps

## What can change the conclusions

### Estimator bias and finite samples

Variogram, madogram, and aggregated-variance estimates have different finite-sample biases. Their regression standard errors condition on the selected log–log model and do not capture every lag-selection or dependence effect. Nominal coverage in the synthetic recovery study should not be interpreted as calibrated confidence coverage for market data.

### Measurement noise and sampling

Additive noise dominates sufficiently fine increments and can pull an estimate toward zero or otherwise distort scaling. Aggregation and pre-averaging reduce some noise but also filter the latent signal. The heatmap demonstrates sensitivity; it does not select an optimal estimator or sampling interval.

### Nonstationarity

The synthetic fBM and fixed-parameter volatility models do not represent intraday seasonality, regime changes, jumps in the forward-variance curve, structural breaks, or evolving liquidity. Apparent roughness in nonstationary data may reflect unmodeled state changes.

### A fixed H

Each fractional model uses one H over the full horizon. Real systems may be multifractional, exhibit scale-dependent effective exponents, or transition between rough and smoother regimes. A single fitted H can conceal these effects.

### Calibration instability

No model is calibrated to option quotes or realized volatility. In real calibration, H, vol-of-vol, leverage, the forward-variance curve, quote errors, and discretization can trade off. A good synthetic recovery result does not guarantee parameter identifiability.

### Rough Bergomi simulation error

The grid-level Gaussian covariance is exact for the specified observation times, but spot integration remains discrete and option prices retain time-step and Monte Carlo error. The \(O(Nn^2)\) sampler is limited to moderate grids. Short-wing implied volatilities can be noisy even with 100,000 paths.

### Heston comparison

Heston parameters are broadly scale- and correlation-matched, not calibrated to the same smile. Its default parameters violate the Feller condition and rely on projected full truncation. Differences between models therefore illustrate dynamics; they are not a controlled empirical model-selection result.

### Simplified Hawkes microstructure

The bivariate process has only buy/sell marks, separable kernels, constant baselines, and no order size, spread, queue position, cancellation, seasonality, or strategic feedback. The signed-count price is pedagogical. The simulation is not a derivation of rough Heston and does not establish a unique microscopic origin for volatility roughness.

### No market data

There is no quote cleaning, corporate-action handling, timezone/session alignment, asynchronous sampling, or data-snooping control. All conclusions are conditional on known synthetic data-generating processes.

## Recommended extensions

1. **Empirical realized-volatility ingestion.** Add a clearly separated, optional data layer with exchange calendars, cleaning rules, provenance, and no hidden network dependency.
2. **Noise-robust estimators.** Implement pre-averaging theory, realized kernels, wavelet estimators, and simulation-based interval calibration.
3. **Multifractional or time-varying H.** Test whether local H estimates can recover controlled changes without confusing them with level nonstationarity.
4. **Markovian lifts.** Approximate fractional kernels with positive exponential factors and compare accuracy/runtime with the exact-grid operator.
5. **Rough Heston.** Add a fractional variance feedback model and benchmark weak simulation, characteristic-function pricing, and calibration stability.
6. **Rough SABR.** Extend the visual comparison to rough stochastic-alpha-beta-rho dynamics and rate/volatility smile applications.
7. **SPX/VIX joint calibration.** Introduce quote-error models, arbitrage filtering, regularization, and out-of-sample validation before making empirical claims.
8. **Neural pricing surrogate.** Train only against convergence-checked labels, retain an analytical/numerical baseline, and report interpolation and extrapolation errors separately.
9. **Deep Hedging under rough volatility.** Connect the simulator to hedging policies while separating training, validation, and test streams and reporting transaction-cost sensitivity.
10. **Multivariate rough volatility and rates.** Study cross-asset rough factors, rough correlation, term-structure models, and no-arbitrage constraints.

## Robustness questions to answer first

- Does the skew exponent remain stable under antithetic/control-variate pricing and denser short-maturity strike grids?
- How quickly do spot and option outputs converge as the main grid increases beyond 500 steps?
- Which H estimator is least biased under price discreteness, bid–ask bounce, asynchronous sampling, and regime changes?
- Can a Markovian lift reproduce the same path, forward-variance, and smile diagnostics at materially lower cost?
- How sensitive is Hawkes-proxy roughness to baseline seasonality, kernel misspecification, event marks, and bin width?

Until these are addressed, the correct claim remains modest: the lab demonstrates mechanisms and measurement fragility on synthetic data; it does not establish a market truth.
