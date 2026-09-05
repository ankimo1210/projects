# Benchmark Owner Scorecard

This file is private evaluator documentation. Never expose it to a candidate.

## Capability score (100 points)

The automated capability score is deliberately separate from elapsed time, quota use, and cost.

| Category | Points | Main evidence |
|---|---:|---|
| Numerical correctness | 30 | finite outputs, positive discount factors, zero/discount/forward identities, grid/interpolation/extrapolation behavior, hidden repricing, DV01, key-rate consistency, negative rates |
| Quantitative/statistical model quality | 20 | dense true-curve error, maturity-weighted error, forward error, hidden instrument repricing, baseline comparison, regularity and sensitivity evidence |
| Hidden-scenario robustness | 15 | accuracy and validity over ten independently generated conforming inputs; source changes are not permitted between scenarios |
| Software engineering and reproducibility | 15 | import, candidate tests, required CLI, clean temporary execution, deterministic artifacts, portable paths, package structure |
| Data-quality handling | 10 | bad-observation treatment, valid-observation retention, ambiguous-valid retention, unit normalization, duplicates, missing values, outliers |
| Report completeness | 5 | non-empty HTML, nine required concepts, four non-empty charts; no pixel-level aesthetic score |
| Completion integrity | 5 | fresh required outputs, summary schema, README, model-risk documentation |

Continuous metrics receive partial credit between a high-quality threshold and a clearly unacceptable threshold. Exact thresholds live only in `scoring.py`. Candidate curves are interpolated onto hidden dense grids for comparison; this does not require a particular internal curve class.

## Quantitative normalization

- Zero and forward errors are basis points.
- Discount-factor RMSE is multiplied by 10,000 for readability.
- Hidden instrument errors use basis points for deposit/swap par rates and tenths of a price point for bonds before pooling.
- Short end is at or below 2Y; long end is at or above 15Y.
- Robustness combines hidden zero-curve and forward-curve errors, conditional on finite, positive-discount output and required grid coverage.
- An in-sample fit cannot compensate for poor hidden curve, hidden instrument, or scenario performance.

## Data-quality policy

True labels distinguish genuine corruption from unusual-but-valid observations. The evaluator accepts several reasonable actions: an extreme outlier may be excluded or heavily downweighted; stale quotes may be downweighted or excluded; an inversion may be repaired or excluded. Unit defects must be normalized, duplicates must not retain full independent influence, and missing quotes must be excluded. False-positive removal of ordinary or unusual-valid observations reduces credit.

## Risk checks

The evaluator reconstructs candidate-curve PVs independently from documented cash flows. Reported DV01 is compared with a central parallel ±1bp finite difference. Four key-rate sensitivities must be finite and aggregate reasonably to parallel DV01; no exact bump basis is required.

## Software execution

Candidate source is copied into a temporary directory. Existing outputs and caches are ignored. Import, tests, the main workflow, a deterministic repeat, and every hidden scenario run occur against the copy with a sanitized environment and `PYTHONPATH=src`. Original candidate files are never modified.

## Anti-leakage review

Text files are scanned for private paths, hidden filenames, selected scenario identifiers, arrays closely matching ground truth, and references to other result directories. Findings are warnings for manual review, not automatic accusations. Final disqualification remains a human decision.

## Efficiency metrics (not capability points)

`benchmark_summary.json` is merged with optional owner-supplied metadata. The evaluator reports model, reasoning effort, wall time, test runs, failed runs, corrective iterations, human interventions, quota percentage, credits, estimated USD cost, score per minute, and score per dollar. Missing values remain null.

## Human review

Human reviewers may separately assess clarity, chart design, originality, and the credibility of the research narrative. This review must be recorded separately and must not silently alter the automated 100-point capability score.
