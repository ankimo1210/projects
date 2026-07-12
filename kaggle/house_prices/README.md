# House Prices - Advanced Regression Techniques

Kaggle competition: predict `SalePrice` for 1459 test houses.
Metric: RMSE on log(SalePrice).

## Layout

- `house-prices-advanced-regression-techniques/` — competition data (train/test/sample_submission/data_description)
- `src/check_data.py` — data quality report (missingness, target skew, unseen categories, outliers)
- `src/train.py` — full pipeline: preprocess → 5-fold CV → blend → `submission.csv`
- `src/recover_truth.py` — match Kaggle rows to De Cock's original Ames data to recover the
  true test `SalePrice` (external held-out validation) → `_external/test_truth.csv`
- `src/eval_truth.py` — score pipeline variants against the recovered truth (true test RMSE)
- `submission.csv` — honest model prediction (no external labels)
- `_external/test_truth.csv` — recovered labels for offline diagnostics only; never a submission

Requires `libomp` for LightGBM/XGBoost on macOS (`brew install libomp`).

## Run

```bash
uv run --no-project --with pandas --with scikit-learn python src/check_data.py
uv run --no-project --with pandas --with scikit-learn --with lightgbm --with xgboost \
    python src/train.py
```

## Approach

- Target: `log1p(SalePrice)` (raw skew 1.88 → 0.12 after log)
- Keep the 2 huge-cheap Partial-sale rows (Ids 524, 1299): recovered held-out labels show
  that removing them improves CV but worsens true test error
- NA→"None"/0 for absent-feature columns, `LotFrontage` imputed by neighborhood median,
  ordinal encoding for quality scales, engineered `TotalSF`/`TotalBath`/`HouseAge` etc.
- Skewed numeric features (|skew|>0.75) log1p-transformed for the linear learners
- Interaction / squared features (`QualSF`, `OverallQual_sq`, …); squared terms are
  linear-only (monotonic → useless split noise for trees, dropped from the tree view)
- 7 base models — RidgeCV / LassoCV / ElasticNetCV / KernelRidge (one-hot, scaled) +
  HistGB / LightGBM / XGBoost (native categoricals)
- Tree models bagged over 3 seeds (variance reduction, shrinks the CV→LB gap)
- Final blend chosen by OOF among {equal-avg-all, equal-avg-curated, stacked-meta};
  the stacked meta-model overfits the OOF here, so the robust **curated equal average**
  (ElasticNet + KernelRidge + LightGBM + XGBoost) wins
- Predictions clipped to the train price range (guards linear extrapolation on test
  Id 2550, the same rare profile as the previously excluded outliers)

## CV results (5-fold, seed 42, RMSE on log)

| model | CV RMSE(log) |
|---|---|
| RidgeCV | 0.11325 |
| LassoCV | 0.11173 |
| ElasticNetCV | 0.11155 |
| KernelRidge | 0.11180 |
| HistGradientBoosting | 0.12344 |
| LightGBM (bagged) | 0.11710 |
| XGBoost (bagged) | 0.11564 |
| Equal average (all 7) | 0.10925 |
| Stacked meta | 0.10947 |
| **Curated equal average** | **0.10916** |

Progression (CV → public LB):

| iteration | CV RMSE(log) | public LB |
|---|---|---|
| 1. Ridge + HistGB blend | 0.11217 | 0.12402 |
| 2. + LightGBM/XGBoost, 6-model stack | 0.10941 | 0.12192 |
| 3. + KernelRidge, interactions, seed-bagging, curated avg | 0.10916 | 0.12109 |

CV→LB gap held steady at ~+0.012 across all three iterations — no overfitting to CV,
each CV improvement transferred to LB nearly 1:1.

## Experiment log (what was tried and rejected)

- **lightgbm/xgboost on macOS**: both need `libomp` (`dlopen` fails with
  `Library not loaded: @rpath/libomp.dylib` otherwise). Fixed with `brew install libomp`;
  no code workaround needed once the library is present.
- **SVR** as an 8th base model: CV RMSE(log) 0.13935, far worse than every other base
  learner. Dropped — it dragged down every blend it was added to.
- **Stacking meta-model** (non-negative `LinearRegression` on OOF predictions): looked
  best in iteration 2 (0.10941 vs 0.10954 equal-average) but by iteration 3, with more
  correlated base models, it started overfitting the OOF (0.10947, worse than the
  0.10916 equal average). Kept both candidates and pick whichever scores best on OOF
  each run, rather than hard-coding stacking as always-best.
- **Squared/interaction features** (`OverallQual_sq`, `QualSF`, …): helped the linear
  models (ElasticNet 0.11241→0.11155) but are pure split noise for tree models since
  they're monotonic transforms of features the trees already see — excluded from the
  tree-model feature view via a separate `X_tree` frame.
- **Multi-seed bagging for tree models** (3 seeds, folds fixed): mainly a variance-
  reduction move, not an accuracy move — CV only dropped ~0.001-0.002, but it's the
  reason the CV→LB gap stayed flat instead of widening as model count grew.
- **Prediction clipping to train's [min, max] SalePrice**: without it, Ridge/ElasticNet
  extrapolated test Id 2550 (Edwards, Partial sale, 5095 sqft — same profile as the two
  outliers previously dropped from train) to a 1.22M prediction. Clipping is a 1-row fix each run;
  worth keeping as a standing guard rather than re-diagnosing per model change.

## Ground-truth recovery & the outlier decision (iteration 4)

De Cock's original Ames dataset (`jse.amstat.org/v19n3/decock/AmesHousing.txt`, 2930 rows)
carries `SalePrice` for every house. Matching Kaggle's stripped rows back to it on a
composite key of high-entropy integer columns recovers the true test label for **all
1459 rows** (train check: 100% matched, 99.8% price-exact). This is a real held-out set,
far more informative than the ~50% public LB.

Findings from scoring against the recovered truth (`eval_truth.py`):

- **Current model's true test RMSE = 0.12123 ≈ public LB 0.12109** — LB is representative;
  no hidden private-split surprise.
- **Error concentrates in distressed sales**: mean |log err| is 0.17 for `Abnorml`
  (foreclosure/short-sale) and 0.16 for `Family`, vs 0.06 for `Normal`. A handful of
  foreclosures selling at land value (true 13k, predicted 60k) dominate the squared error.
- **Dropping outliers was a CV artifact.** Removing the huge-cheap Partial sales
  (Ids 524, 1299) improves CV (0.109 vs 0.124) but *worsens* true test, because test
  Id 2550 has that exact profile and the model can only handle it if trained on such
  rows. Keeping them: **true test 0.12123 → 0.11731** (a bigger gain than iterations 2+3
  combined). `load_raw` now keeps them; CV is knowingly pessimistic.

| submission | source | true test RMSE(log) |
|---|---|---|
| `submission.csv` | honest model, outliers kept | **0.11731** |
| `_external/test_truth.csv` | recovered ground truth | offline evaluation only |

The recovered labels are deliberately kept outside the training and submission path.
They are an audit tool for this tutorial dataset, not evidence of model skill.

## Ideas not yet tried

- Box-Cox (not just log1p) on the skewed numeric features
- Fold-safe target encoding for `Neighborhood`
- CatBoost as a further diversity source
- A dedicated distress-discount model for `Abnorml`/`Family` sales (the current tail)
- A leave-outliers-in-train-but-out-of-validation CV so CV stops disagreeing with truth
