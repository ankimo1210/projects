# Phase 2 Roadmap: Deep Pricing

Phase 2 must be implemented as a separate, validated pricing problem. It must not infer a price merely from the Phase 1 hedge loss.

## Ownership and A5 mapping

- `deep_hedge_price` is the source of truth for the Phase 2 PyTorch learning engine,
  pricing configs, checkpoints, evaluation, and standalone report.
- `hullkit` owns NumPy/SciPy analytic/COS/Monte-Carlo teachers and hard financial
  validation. It remains torch-free.
- `johnhull` owns the vol 18 teaching notebook and book/portal integration.
- Differentiable penalties in `deep_hedge_price.arbitrage` are training aids. Only
  `hullkit.surrogate_validation` produces the canonical hard report and aggregate
  `arbitrage_free` decision.
- Phase 1 uses `ProjectConfig`, `artifacts/checkpoints/`, and the hedge manifest.
  Phase 2 uses `PricingConfig`, `artifacts/pricing/<namespace>/<fingerprint>/`, and
  versioned JSON+NPZ datasets. Their configs, checkpoints, and manifests are not interchangeable.

Mapping to the A5 implementation plan:

| This roadmap | A5 task |
|---|---:|
| BS supervised surrogate | G1 Task 4–5 |
| Joint/Differential Greeks | G1 Task 6 |
| Arbitrage-aware losses/checks | G0 Task 3 + G1 Task 7 |
| MC and Heston/COS labels | G1 Task 8 |
| Calibration/speed/OOD | G1 Task 9 |
| Notebook/report delivery | G1 Task 10–11 |

G0 contracts are implemented without adding a new production dependency. Gate
completion still requires the project-scoped test/lint and delivery verification
listed in Task 12 of the A5 plan.

## 1. Black–Scholes supervised surrogate

Add `pricing_data.py`, `pricing_policy.py`, `pricing_training.py`, `greeks.py`, and `arbitrage.py`. Generate a stratified design over normalized spot/strike, maturity, rate, dividend yield, and volatility. Labels are analytic Black–Scholes prices, delta, gamma, vega, theta, and rho. Train a small MLP on normalized price `C/K` and retain analytic values as the baseline.

Acceptance: in-domain price MAE below `1e-3 * K`, delta MAE below `2e-3`, stable automatic-differentiation Greeks, and explicit expiry/zero-volatility boundary tests.

## 2. Monte Carlo label generation

Build a seed-addressable, chunked label generator for payoffs without closed forms. Use common random numbers, antithetic variates, and the discounted underlying as a control variate. Save estimates, standard errors, confidence intervals, path counts, generator version, and parameters.

Acceptance: Black–Scholes calls fall inside nominal 95% intervals at the expected empirical rate; doubling paths reduces standard error near `1/sqrt(n)`; reruns with the same seed are identical.

## 3. Joint price-and-Greeks learning

Use a shared trunk with explicit price and Greeks heads. Compare direct Greek labels with Greeks obtained by differentiating the price head. Report consistency error between the two routes and retain a price-only baseline.

Acceptance: the joint model must improve at least one Greek without materially degrading price error; otherwise retain the simpler model and document the negative result.

## 4. Differential machine learning

Add derivative observations to the loss with scale-balanced weights and per-output normalization. Compare price-only, multi-task direct labels, and differential-learning variants on common train/validation/test parameter grids.

Acceptance: evaluate convergence speed, price error, Greek error, and out-of-domain stability; do not claim improvement from training loss alone.

## 5. Arbitrage-aware losses

Implement soft penalties and hard evaluation checks for price bounds, monotonicity in spot, monotonicity in strike, convexity in strike, non-negative gamma, calendar monotonicity under applicable assumptions, and put–call parity. Use finite differences on structured mini-batches plus autodiff where stable.

Acceptance: publish violation rates and magnitudes before and after penalties. No model is called arbitrage-free unless every hard check passes within a documented numerical tolerance.

## 6. Calibration and scenario-speed benchmarks

Provide implied-volatility inversion and calibration adapters that use the surrogate inside repeated optimization. Benchmark batch latency and throughput against analytic Black–Scholes and Monte Carlo on CPU and optional CUDA, including warm-up and synchronized timing.

Acceptance: report accuracy/latency trade-offs, break-even batch size, calibration parameter recovery on synthetic surfaces, and failure behavior outside the training domain.

## 7. Notebook and package delivery

Create `notebooks/02_neural_pricing_surrogate.ipynb` with label QA, analytic baseline, learning curves, error surfaces, Greek slices, arbitrage diagnostics, calibration recovery, and speed benchmarks. Reuse the existing artifact/report pipeline but keep Phase 1 and Phase 2 manifests distinct.

## 8. Phase 2 completion criteria

- Analytic and Monte Carlo label generators independently tested.
- No train/test parameter-grid overlap and explicit extrapolation sets.
- Price-only baseline established before multi-task or differential models.
- Price and Greek errors reported by moneyness and maturity buckets.
- Arbitrage violations quantified rather than hidden by aggregate error.
- CPU inference and calibration benchmarks reproducible.
- Executed Notebook 02 and a separate self-contained pricing report generated.
