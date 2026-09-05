# Hidden reference solution

This implementation is owned by the benchmark evaluator and must never be copied into the public input. It provides an independent high-quality calibration used to validate dataset difficulty and score separation.

The workflow normalizes units using quote-and-spread evidence, repairs inverted markets, resolves duplicates by freshness and liquidity, and retains a complete observation-level audit trail. It first fits a transparent piecewise-linear proxy baseline, then calibrates a regularized cubic zero-rate model directly to all instrument cash flows with spread/liquidity weights and a robust loss. A second residual pass downweights or excludes statistical outliers before final calibration.

The implementation generates a dense continuously compounded zero curve, exact discount factors, numerical instantaneous forwards, full repricing diagnostics, central finite-difference DV01, maturity-local key-rate allocations, four deterministic SVG charts, and an HTML report. It uses no hidden curve parameter or truth file at runtime.

Run from this directory with `PYTHONPATH=src python -m quantcurve.cli run --market-data MARKET.csv --output-dir OUTPUT --valuation-date 2026-01-15`. Run tests with `PYTHONPATH=src python -m unittest discover -s tests -q`.
