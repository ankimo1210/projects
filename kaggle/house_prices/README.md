# House Prices - Advanced Regression Techniques

Kaggle competition: predict `SalePrice` for 1459 test houses.
Metric: RMSE on log(SalePrice).

## Layout

- `house-prices-advanced-regression-techniques/` — competition data (train/test/sample_submission/data_description)
- `src/check_data.py` — data quality report (missingness, target skew, unseen categories, outliers)
- `src/train.py` — full pipeline: preprocess → 5-fold CV → blend → `submission.csv`
- `submission.csv` — generated submission file

Requires `libomp` for LightGBM/XGBoost on macOS (`brew install libomp`).

## Run

```bash
uv run --no-project --with pandas --with scikit-learn python src/check_data.py
uv run --no-project --with pandas --with scikit-learn --with lightgbm --with xgboost \
    python src/train.py
```

## Approach

- Target: `log1p(SalePrice)` (raw skew 1.88 → 0.12 after log)
- Dropped 2 train outliers (Ids 524, 1299: >4500 sqft, Partial sales, abnormally low price)
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
  Id 2550, same profile as the dropped outliers)

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
  outliers dropped from train) to a 1.22M prediction. Clipping is a 1-row fix each run;
  worth keeping as a standing guard rather than re-diagnosing per model change.

## Ideas not yet tried

- Box-Cox (not just log1p) on the skewed numeric features
- Fold-safe target encoding for `Neighborhood`
- CatBoost as a further diversity source
- Feature selection / pruning the ~80-column one-hot space for the linear models
