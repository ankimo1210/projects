# Numerical Methods

## Random-stream protocol

Every semantic stream is derived from the base seed and a CRC32 name key through NumPy `SeedSequence`. This is order-independent: requesting `asset_zperp` before `asset_z` does not change either stream. Separate streams are used for spot Brownian shocks, orthogonal shocks, Volterra residuals, fBM studies, Hawkes scenarios, and observation noise.

## Davies–Harte safeguards

For \(n\) fGn increments, the circulant first row is

\[
c=(\gamma(0),\ldots,\gamma(n-1),\gamma(n),\gamma(n-1),\ldots,\gamma(1)).
\]

FFT eigenvalues must satisfy

\[
\lambda_{\min}\ge -10^{-10}\lambda_{\max}.
\]

Tiny negative roundoff values are clipped to zero, with count and removed mass recorded. A materially indefinite embedding raises; the high-level simulator falls back to Toeplitz Cholesky only for grids of at most 2,048 steps. The tested H/grid combinations have nonnegative embeddings without meaningful clipping.

Davies–Harte costs \(O(n\log n)\) per path and stores the complex embedding batch. Cholesky costs \(O(n^3)\) to factor and \(O(Nn^2)\) to sample, so it is validation-only.

## Exact-grid Volterra construction

For \(s\le t\), the normalized Riemann–Liouville covariance is

\[
\operatorname{Cov}(\widetilde W_s,\widetilde W_t)
=\frac{2H}{H+1/2}s^{H+1/2}t^{H-1/2}
{}_2F_1(1/2-H,1;H+3/2;s/t).
\]

The cross-covariance with Brownian interval \([t_{k-1},t_k]\) is

\[
\frac{\sqrt{2H}}{H+1/2}
\left[(t_j-t_{k-1})_+^{H+1/2}-(t_j-t_k)_+^{H+1/2}\right].
\]

With standardized increments \(z_k=\Delta W_k/\sqrt{\Delta_k}\), define \(C=\operatorname{Cov}(\widetilde W,z)\). The Schur residual is

\[
R=\Sigma_{\widetilde W}-CC^\top=MM^\top.
\]

Sampling uses \(\widetilde W=zC^\top+\widetilde zM^\top\). Only the \(n\times n\) residual requires Cholesky; a single jitter retry of \(10^{-12}\operatorname{tr}(\Sigma)/n\) is permitted and recorded. The reconstructed diagonal is checked against \(t^{2H}\).

### Rejected left-point kernel

A straightforward left-point discretization of \((t-s)^{H-1/2}\) was rejected. At \(H=0.1\), \(n=252\), it loses roughly 26% of terminal Volterra variance. The exponential correction would then be inconsistent with the simulated variance, producing \(\mathbb E[V_T]\) around 75% of \(\xi_0\). The exact-grid covariance avoids this bias at the project’s moderate grid sizes.

The operator costs \(O(n^3)\) once per H/maturity grid; a path batch costs \(O(Nn^2)\). This is acceptable for \(n\le500\), but a hybrid or FFT scheme is the natural extension to finer grids.

## Maturity-grid correction

The original suggested 252-step annual grid does not contain \(T=0.02\): \(252\times0.02=5.04\). Interpolating terminal spots would undermine common-grid comparisons. Therefore:

- `default` and `full` use 500 steps, aligning 0.02, 0.05, 0.10, 0.25, 0.50, and 1.00;
- `quick` uses 200 steps and omits 0.02;
- validation rejects any maturity whose grid index differs from an integer by more than \(10^{-9}\).

Experiment E uses an independent refined grid on \([0,T]\) for every maturity: 128 steps in `quick`, 256 in `default`/`full`. This prevents the shortest maturity from inheriting only a handful of annual-grid steps.

## Monte Carlo chunking

rBergomi and Heston terminal arrays are retained, but full path matrices are stored only for a small reservoir. Named generators are advanced sequentially across chunks, so changing chunk size preserves the random sequence. BLAS row blocking can change the last floating-point bit; tests require agreement within \(10^{-13}\), not byte identity.

The full profile uses 20,000-path chunks. At 500 steps, peak memory is dominated by three normal matrices, Volterra products, variance, and spot arrays. Terminal and realized-variance summaries are copied out before the next chunk.

## Spot and variance discretization

rBergomi uses left-point variance in an exponential log-Euler spot step. Conditional on \(V_k\), the \(-V_k\Delta/2\) correction makes the discrete discounted spot a martingale.

Heston uses current positive variance in drift/diffusion and projects the next candidate to zero. This is a projected full-truncation Euler scheme. Default parameters violate the Feller condition:

\[
2\kappa\theta=0.16<\nu^2=0.25.
\]

That choice is typical of equity-like demonstrations and intentionally exercises the positivity treatment. It is documented rather than hidden.

## Implied-volatility solver

Call prices must satisfy

\[
\max(S-Ke^{-rT},0)\le C<S.
\]

The solver returns zero on the intrinsic boundary and `NaN` outside admissible bounds or after a failed bracket. Brent's method uses \([10^{-6},5]\). Deep in-the-money calls with nearly zero time value are ill-conditioned in float64; tests use a looser tolerance for the single 5-vol, \(k=-0.3\) corner and strict \(10^{-8}\) recovery elsewhere.

## Regressions and failure propagation

Log–log fits require at least three positive finite observations. Hurst fits use 15 or fewer unique log-spaced lags, capped at 10% of path length. ATM skew needs five valid IVs within its maturity-scaled window. Failed inversions and insufficient fits are retained as explicit failed rows; they are never silently dropped from artifact generation.

## Hawkes thinning and compensators

Ogata thinning maintains exponential states for each source side and decay scale. The inner loop uses scalar event time and mark operations while keeping only the small state matrix. Complexity is proportional to candidate count times the number of exponential scales. A hard event cap sets a visible truncation flag.

The exact integrated intensity is calculated from every accepted event:

\[
\int_0^T\lambda_i(t)dt=\mu_iT+
\sum_j A_{ij}\sum_{t_k^j<T}\sum_mw_m\left(1-e^{-\beta_m(T-t_k^j)}\right).
\]

Its sum is compared with the realized event count as a compensator diagnostic.

## Rendering and offline constraints

Static figures use Matplotlib at 150 DPI and SVG path fonts. Dense scatter marks are rasterized within SVG, and displayed paths are thinned to at most 2,500 points.

The standalone report embeds the Plotly bundle once and disables the modebar. It contains no remote `src` or `href` attributes. Equations are pre-rendered by Matplotlib mathtext into SVG data URIs, avoiding a MathJax dependency in the standalone report. The notebook is Matplotlib/static-image based; its separate nbconvert HTML may retain nbconvert's default MathJax reference.
