"""End-to-end pipeline helpers (notebook 10).

Everything routes through a single scikit-learn ``Pipeline`` so that preprocessing
is refit on each training fold (no leakage), the whole object can be persisted and
reloaded as one unit, and hyper-parameter search tunes preprocessing and model
together.
"""

from __future__ import annotations

import joblib
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    StratifiedKFold,
    cross_val_score,
)
from sklearn.pipeline import Pipeline

from .preprocessing import make_preprocessor


def build_preprocess_pipeline(numeric_cols, categorical_cols, scaler: str = "standard"):
    """The canonical tabular ColumnTransformer (delegates to preprocessing)."""
    return make_preprocessor(numeric_cols, categorical_cols, scaler=scaler)


def build_model_pipeline(preprocessor, model) -> Pipeline:
    """Glue a preprocessor and an estimator into one ``Pipeline``."""
    return Pipeline([("preprocess", preprocessor), ("model", model)])


def make_full_pipeline(numeric_cols, categorical_cols, model, scaler: str = "standard") -> Pipeline:
    """Convenience: preprocessor + model in one call."""
    return build_model_pipeline(
        make_preprocessor(numeric_cols, categorical_cols, scaler=scaler), model
    )


def grid_search(pipeline, param_grid, X, y, cv: int = 5, scoring=None, n_jobs: int = -1):
    """Fit an exhaustive ``GridSearchCV`` and return it (inspect ``.best_params_``)."""
    search = GridSearchCV(pipeline, param_grid, cv=cv, scoring=scoring, n_jobs=n_jobs)
    return search.fit(X, y)


def random_search(
    pipeline,
    param_distributions,
    X,
    y,
    n_iter: int = 20,
    cv: int = 5,
    scoring=None,
    n_jobs: int = -1,
    seed: int = 0,
):
    """Fit a ``RandomizedSearchCV`` (cheaper than grid for large spaces) and return it."""
    search = RandomizedSearchCV(
        pipeline,
        param_distributions,
        n_iter=n_iter,
        cv=cv,
        scoring=scoring,
        n_jobs=n_jobs,
        random_state=seed,
    )
    return search.fit(X, y)


def nested_cv_score(pipeline, param_grid, X, y, inner: int = 3, outer: int = 5, scoring=None):
    """Nested cross-validation: tune in an inner loop, score in an outer loop.

    The honest estimate of "how well does my *tuning procedure* generalise". A
    single CV that both tunes and reports is optimistically biased because the
    same folds chose the hyper-parameters and graded them.
    """
    inner_cv = StratifiedKFold(n_splits=inner, shuffle=True, random_state=0)
    outer_cv = StratifiedKFold(n_splits=outer, shuffle=True, random_state=1)
    search = GridSearchCV(pipeline, param_grid, cv=inner_cv, scoring=scoring)
    return cross_val_score(search, X, y, cv=outer_cv, scoring=scoring)


def save_pipeline(pipeline, path) -> None:
    """Persist a fitted pipeline to disk with joblib."""
    joblib.dump(pipeline, path)


def load_pipeline(path):
    """Load a pipeline saved by :func:`save_pipeline`."""
    return joblib.load(path)


def predict_new(pipeline, X_new):
    """Run a fitted pipeline on new raw data (preprocessing is applied inside)."""
    return pipeline.predict(X_new)
