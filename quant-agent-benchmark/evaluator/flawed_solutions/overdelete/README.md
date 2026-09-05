# Deliberately flawed calibration fixture

This evaluator-only candidate exercises the public CLI and output contract while preserving a known quantitative defect. It is used to confirm that the benchmark distinguishes code that runs from a reliable quantitative workflow. The implementation is deterministic, creates the required files, and is intentionally not suitable for real curve construction.

Run with `PYTHONPATH=src python -m quantcurve.cli run --market-data MARKET.csv --output-dir OUTPUT --valuation-date 2026-01-15`. The hidden benchmark owner, not a benchmarked agent, controls this fixture.
