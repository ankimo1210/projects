"""Enhanced-model tests: ensembling/stacking, learning-to-rank, and uncertainty.

These sit on the same (date, asset) design matrix and fit/predict contract as the
rest of :mod:`quantkit.models`, so they drop straight into ``walk_forward_predict`` and
are judged on the same out-of-sample walk. Uncertainty models (quantile, conformal)
return *intervals* rather than a point Series, so they are exercised directly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantkit import backtest as B
from quantkit import models as MD


def _design(n_dates=200, n_assets=20, seed=0, noise=0.5):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2018-01-01", periods=n_dates)
    assets = [f"A{i:02d}" for i in range(n_assets)]
    a = pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    b = pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    label = (
        a
        - 0.5 * b
        + noise
        * pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    )
    X, y = MD.make_design({"a": a, "b": b}, label)
    return X, y, dates


# --- ensembling / stacking ----------------------------------------------------
def test_ensemble_averages_member_predictions():
    X, y, _ = _design()
    ens = MD.EnsembleModel([MD.ridge(0.5), MD.ridge(10.0)]).fit(X, y)
    m1 = MD.ridge(0.5).fit(X, y)
    m2 = MD.ridge(10.0).fit(X, y)
    expected = (m1.predict(X) + m2.predict(X)) / 2
    np.testing.assert_allclose(ens.predict(X).to_numpy(), expected.to_numpy(), rtol=1e-9)


def test_stacking_oof_meta_features_track_the_signal():
    X, y, _ = _design(noise=0.3)
    stack = MD.StackingModel([MD.ridge, MD.gradient_boosting], MD.ridge, n_splits=4).fit(X, y)
    pred = stack.predict(X)
    assert pred.index.equals(X.index)
    # the stacked prediction should be positively rank-correlated with the target
    assert MD.rank_ic(pred, y) > 0.2


# --- learning-to-rank ---------------------------------------------------------
def test_cross_sectional_rank_is_zero_mean_per_date_and_monotone():
    _, y, _ = _design(n_dates=5, n_assets=10)
    r = MD.cross_sectional_rank(y)
    means = r.groupby(r.index.get_level_values("date")).mean()
    np.testing.assert_allclose(means.to_numpy(), 0.0, atol=1e-12)
    # within a date, rank transform preserves the ordering of y
    d0 = y.index.get_level_values("date")[0]
    assert (y.xs(d0, level="date").rank().values == r.xs(d0, level="date").rank().values).all()


def test_learning_to_rank_predicts_orderable_scores():
    X, y, dates = _design(noise=0.4)
    folds = B.walk_forward(dates, train=120, test=20, horizon=1)
    pred = MD.walk_forward_predict(lambda: MD.learning_to_rank(MD.ridge), X, y, folds)
    assert MD.rank_ic(pred, y.loc[pred.index]) > 0.2  # learns the cross-sectional order


# --- uncertainty: quantile + conformal ----------------------------------------
def test_quantile_model_predicts_ordered_quantiles_with_coverage():
    X, y, _ = _design(noise=1.0)
    qm = MD.quantile_gbm(quantiles=(0.1, 0.5, 0.9), n_estimators=60).fit(X, y)
    q = qm.predict(X)
    assert list(q.columns) == [0.1, 0.5, 0.9]
    assert (q[0.1] <= q[0.9]).mean() > 0.95  # quantiles are (almost always) ordered
    below_90 = (y < q[0.9]).mean()
    assert 0.80 < below_90 < 0.98  # ~90% of outcomes fall below the 0.9 quantile


def test_conformal_interval_achieves_target_coverage():
    X, y, dates = _design(n_dates=300, n_assets=20, noise=1.0)
    split = dates[200]
    is_train = X.index.get_level_values("date") < split
    Xtr, ytr = X[is_train], y[is_train]
    Xte, yte = X[~is_train], y[~is_train]
    cm = MD.ConformalModel(MD.ridge(1.0), alpha=0.1).fit(Xtr, ytr)
    out = cm.predict(Xte)
    assert list(out.columns) == ["lower", "point", "upper"]
    cov = ((yte >= out["lower"]) & (yte <= out["upper"])).mean()
    assert 0.83 < cov < 0.97  # target 90% coverage, finite-sample tolerance
    assert cm.coverage(Xte, yte) == cov
