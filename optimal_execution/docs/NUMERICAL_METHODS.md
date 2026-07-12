# Numerical methods

## Time grids and execution prices

The decision grid has \(N\) equal intervals of length \(\Delta t=T/N\).
Classical child orders execute at step-start unaffected prices. Price risk over
step \(k\) is therefore carried by post-trade inventory \(x_{k+1}\). The LOB
uses configurable event sub-steps within each decision interval.

Impact models charge block-average permanent and transient states. This avoids
assigning the entire current impulse before the block itself has executed and
keeps the discrete transient scheduling quadratic positive definite.

## Stable Almgren–Chriss evaluation

Direct hyperbolic sine ratios overflow for large \(\kappa T\). The code uses

\[
\frac{\sinh a}{\sinh b}
=e^{a-b}\frac{1-e^{-2a}}{1-e^{-2b}}
\]

and switches to the linear limit for very small \(\kappa T\). Unit tests check
endpoints, monotonicity, sensitivities, and continuous/discrete cost agreement.

## Resilience quadratic program

For a positive-definite kernel matrix \(M\), the equality-constrained solution
is proportional to \(M^{-1}\mathbf 1\). Negative coordinates, possible under
some discretized kernels, are pinned to zero and the reduced KKT system is
solved again. A small diagonal ridge controls floating-point conditioning.

## Monte Carlo and memory

Classical simulations are vectorized and evaluated in chunks configured by
`mc_chunk_size`. Each chunk reconstructs the same named primitive streams for
all schedules. Path-level frames are concatenated only after per-strategy TCA.
LOB simulations are episode loops because state reacts sequentially to actions.

The quick profile uses 5,000 classical test paths and 600 main LOB/RL test
episodes. The full profile uses 100,000 classical paths and writes Parquet to
control storage. Results record seed, profile, compact model parameters,
timestamp, and Git commit.

## Uncertainty and tail metrics

Reported quantiles use empirical interpolation from NumPy. For cost (larger is
worse), VaR at level \(p\) is the empirical \(p\)-quantile, and CVaR is the mean
of observations at or above VaR. The 95% interval for the mean is a seeded
percentile bootstrap with 1,000 resamples.

The interval measures Monte Carlo sampling uncertainty conditional on this
simulator. It does not measure model, calibration, or deployment uncertainty.
Common random numbers reduce variance in pairwise strategy differences.

## PPO optimization

The actor-critic has two tanh hidden layers, a categorical 15-action head, and
a value head. Orthogonal initialization, clipped policy ratios, generalized
advantage estimation, entropy annealing, value loss, gradient clipping, and a
finite-parameter guard are implemented directly in PyTorch.

Rollouts can end between episode boundaries; the final value bootstraps only a
nonterminal partial episode. Validation is deterministic on fixed disjoint
seeds. The checkpoint with lowest validation mean economic IS is retained.
Early stopping counts validation rounds without improvement.

## Reproducibility and validation

NumPy and PyTorch seeds are explicit. Scenario streams use stable CRC32 labels
rather than Python's randomized hash. Reports and plots read saved files, so
localization cannot change numerical results. The bilingual reports embed the
same SHA-256 quantitative fingerprint.

Validation comprises unit tests, stochastic smoke tests, lint, a fresh quick
pipeline, notebook execution, HTML structural/offline checks, and visual
inspection of static renderings. The full profile is configured but not part of
the quick acceptance run due to CPU cost.
