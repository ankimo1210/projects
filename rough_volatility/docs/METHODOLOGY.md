# Methodology

## Scope and evidence

All evidence is synthetic and generated locally from a validated YAML profile. Experiments use named child random streams derived from a base seed, so adding or reordering an unrelated experiment does not change existing draws. Every reported metric is linked to a configuration fingerprint and sample size.

The project distinguishes three kinds of statement:

1. deterministic numerical identities, such as covariance reconstruction;
2. Monte Carlo checks, such as \(\mathbb E[V_t]=\xi_0(t)\) within sampling error;
3. descriptive diagnostics, such as an effective H estimated from a Hawkes-derived RV proxy.

Only the first two are validation gates. The third is never treated as structural identification.

## Fractional Brownian motion

Fractional Brownian motion is centered Gaussian with covariance

\[
\operatorname{Cov}(B_t^H,B_s^H)
=\frac12\left(t^{2H}+s^{2H}-|t-s|^{2H}\right),
\qquad H\in(0,1).
\]

Its unit-grid increments, fractional Gaussian noise, have autocovariance

\[
\gamma(k)=\frac12\left(|k+1|^{2H}-2|k|^{2H}+|k-1|^{2H}\right).
\]

Davies–Harte simulation embeds \(\gamma\) in a circulant covariance. A two-for-one complex FFT produces two independent real fGn samples. Unit increments are scaled by \((T/n)^H\), cumulatively summed, and prefixed with \(B_0^H=0\). Small grids can be cross-checked with an exact Toeplitz Cholesky factor.

## Scaling and Hurst estimation

For order \(q>0\), the structure function is

\[
S_q(\Delta)=\mathbb E|X_{t+\Delta}-X_t|^q.
\]

For monofractal fBM, \(S_q(\Delta)\propto\Delta^{qH}\). The project fits log–log regressions over unique log-spaced lags bounded to at most 10% of the sample. It reports slope, regression standard error, \(R^2\), and the fitted lag range.

Three estimators are compared:

- variogram: second moment slope divided by two;
- madogram: first absolute-moment slope;
- aggregated variance: block-mean variance slope \(2H-2\).

Recovery experiments report bias, RMSE, empirical dispersion, and nominal regression-interval coverage. Coverage is diagnostic because ordinary regression errors do not capture every dependence and finite-sample effect.

## Ordinary and fractional OU log-volatility

The standard OU process

\[
dX_t=-\kappa(X_t-\mu)\,dt+\nu\,dW_t
\]

uses its exact Gaussian AR(1) transition. The fractional comparison

\[
dX_t=-\kappa(X_t-\mu)\,dt+\nu_H\,dB_t^H
\]

uses Euler drift with Davies–Harte fBM increments and a burn-in interval. The noise scale is matched approximately to a target stationary standard deviation using the continuous-time fOU variance formula. This comparison is meant to isolate local regularity; it is not an exact stationary fractional-OU sampler.

Volatility is \(\sigma_t=\exp(X_t)\), which guarantees positivity.

## Rough Bergomi-style model

Under the pricing measure,

\[
V_t=\xi_0(t)\exp\left(\eta\widetilde W_t^H-	frac12\eta^2t^{2H}\right),
\qquad
\widetilde W_t^H=\sqrt{2H}\int_0^t(t-s)^{H-1/2}\,dW_s.
\]

The implementation samples the exact joint Gaussian law of regular-grid Brownian increments and \(\widetilde W^H\). The normalization makes \(\operatorname{Var}(\widetilde W_t^H)=t^{2H}\), so the exponential correction enforces \(\mathbb E[V_t]=\xi_0(t)\) analytically at the simulated grid points.

Spot uses log-Euler steps

\[
\log S_{k+1}=\log S_k+r\Delta-	frac12V_k\Delta
+\sqrt{V_k\Delta}\left(\rho z_k+\sqrt{1-\rho^2}z_k^\perp\right).
\]

The conditional exponential correction makes every discrete step a martingale after discounting.

## Heston benchmark and common random numbers

The benchmark is

\[
dV_t=\kappa(\theta-V_t)dt+\nu\sqrt{V_t}\,dW_t,
\qquad
dS_t=rS_tdt+\sqrt{V_t}S_t\,dB_t.
\]

It uses a projected full-truncation Euler update. Heston and rBergomi consume identical arrays for \(z\), \(z^\perp\), and therefore the correlated spot driver. rBergomi alone consumes an additional residual Volterra stream. This common-random-number protocol reduces comparison noise without asserting that the parameter sets are calibrated equivalents.

## Option pricing and implied volatility

Calls are estimated from terminal paths:

\[
C(K,T)=e^{-rT}\frac1N\sum_{i=1}^N(S_T^{(i)}-K)^+.
\]

The payoff standard deviation supplies the Monte Carlo standard error. Strikes use forward log-moneyness \(k=\log(K/F_T)\). Black–Scholes implied volatility is inverted with Brent's method on \([10^{-6},5]\) after checking intrinsic and upper no-arbitrage bounds. Failed or numerically degenerate inversions remain explicit `NaN`/`ok=False` rows. IV standard errors use the delta method, price SE divided by Black–Scholes vega.

## ATM skew

For each maturity, the local window is

\[
w(T)=\operatorname{clip}\left(1.5\sqrt{\xi_0T},0.03,0.10\right).
\]

A weighted quadratic \(\sigma(k)=a+bk+ck^2\) is fitted with inverse-IV-variance weights; \(b\) is the ATM skew. At least five valid points are required. The term structure fits

\[
\log|b(T)|=a+\beta\log T,
\]

and compares \(\beta\) with \(H-1/2\). This is a finite-maturity diagnostic with Monte Carlo uncertainty, not exact asymptotic confirmation.

## Hawkes microstructure

Buy and sell events have intensities

\[
\lambda_t^i=\mu_i+\sum_j\int_0^t\phi_{ij}(t-s)\,dN_s^j.
\]

The stable baseline uses a single exponential kernel. The near-critical model uses a matrix amplitude times a normalized exponential mixture; weights proportional to \(\beta_m^\alpha\) approximate a power-law tail. Branching ratios are restricted below 0.995. Baseline intensity is set to \(\mu=\Lambda(1-n)\) per side so Poisson, stable, and near-critical scenarios have the same target unconditional rate.

Ogata thinning produces event times and marks. An exact compensator calculation checks event budgets. Events are binned into counts and imbalance; a pedagogical price is

\[
P_t=P_0+\epsilon(N_t^+-N_t^-)+\text{observation noise}.
\]

Rolling squared returns and intensity are proxies. An H estimate of log RV is labeled “empirical diagnostic only.”

## Measurement fragility

The final experiment holds latent fBM paths fixed while varying Gaussian observation noise, sampling stride, estimator, and raw/aggregated/pre-averaged processing. Differences therefore measure the procedure's sensitivity rather than different latent realizations. The main implication is negative: observing \(\widehat H<1/2\) is insufficient to identify fractional dynamics.
