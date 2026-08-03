# kaggle

Kaggle competition experiments. Each subdirectory is self-contained: its own
data, scripts and README with the full trial-and-error log (what was tried,
what was rejected, and why).

Not a uv workspace member — there is no `pyproject.toml` here. Scripts declare
their own dependencies inline via `uv run --with`, so nothing in these
directories can drift the shared root `.venv`.

## Competitions

| Directory | Competition | Metric | Best result |
|---|---|---|---|
| [`house_prices/`](house_prices/) | House Prices — Advanced Regression Techniques | RMSE on log(SalePrice) | true test 0.11731 (public LB 0.12109) |
| [`titanic/`](titanic/) | Titanic — Machine Learning from Disaster | accuracy | public LB 0.80382 (v3) |

## Run

```bash
# house_prices (from kaggle/house_prices/)
uv run --no-project --with pandas --with scikit-learn python src/check_data.py
uv run --no-project --with pandas --with scikit-learn --with lightgbm --with xgboost \
    python src/train.py

# titanic (from the repo root)
uv run python kaggle/titanic/src/train.py   # v1: ML models
uv run python kaggle/titanic/src/wcg2.py    # v3 + v4: ticket-linked groups
```

## What these two are worth reading for

Both write-ups are really about **when cross-validation lies to you**, which is
the reusable part:

- **Titanic** — the best 5-fold CV model (HistGB, 0.8395) scored *worse* on the
  public LB than the plain "predict survival iff female" rule. With 891 rows CV
  systematically overstates generalization. Direct group-membership evidence
  (this specific family/ticket) transferred; population-level demographic
  priors did not (v4 went 5/13 correct and was dropped).
- **House Prices** — the original Ames data recovers the true label for all
  1459 test rows, giving a real held-out set instead of the ~50% public LB.
  Scored against it, dropping the classic "huge cheap outliers" turned out to
  be a **CV artifact**: it improves CV but worsens true test error, because the
  test set contains that exact profile. Recovered labels stay out of the
  training and submission path — they are an audit tool, not model skill.

## Conventions

- `submission*.csv` are gitignored (repo-wide `*.csv` rule); regenerate them by
  rerunning the scripts.
- `_external/` holds derived reference data used for offline diagnostics only.
