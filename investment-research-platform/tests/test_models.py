"""Model-layer tests: design matrix (no fill), Tier-0 baselines, train-only
standardization, and walk-forward OOS (signal recovery + no date leakage).

The harness must fit per fold, predict only test dates, and standardize using
training statistics only — so a learnable relationship is recovered out-of-sample
without leaking the test set into the fit.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from irp import backtest as B
from irp import models as MD


def _panels(n=400, k=5, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-01", periods=n)
    assets = [f"A{i}" for i in range(k)]
    f1 = pd.DataFrame(rng.normal(0, 1, (n, k)), index=idx, columns=assets)
    f2 = pd.DataFrame(rng.normal(0, 1, (n, k)), index=idx, columns=assets)
    noise = pd.DataFrame(rng.normal(0, 0.1, (n, k)), index=idx, columns=assets)
    label = 2.0 * f1 - 1.0 * f2 + noise  # a learnable linear relationship
    return {"f1": f1, "f2": f2}, label


# --- design matrix ------------------------------------------------------------
def test_make_design_stacks_and_drops_nan():
    feats, label = _panels(n=20, k=3)
    feats["f1"].iloc[0, 0] = np.nan  # inject a gap
    X, y, dropped = MD.make_design(feats, label, return_dropped=True)
    assert list(X.columns) == ["f1", "f2"]
    assert X.index.names == ["date", "asset"]
    assert dropped == 1  # the NaN row removed, not imputed
    assert not X.isna().any().any() and not y.isna().any()


def test_predictions_to_panel_roundtrips_shape():
    feats, label = _panels(n=15, k=4)
    _, y = MD.make_design(feats, label)
    panel = MD.predictions_to_panel(y)
    assert panel.shape[1] == 4  # assets back as columns


# --- Tier-0 baselines ---------------------------------------------------------
def test_tier0_baselines():
    feats, label = _panels(n=30, k=3)
    X, y = MD.make_design(feats, label)
    assert (MD.ZeroModel().fit(X, y).predict(X) == 0).all()
    mean_pred = MD.MeanModel().fit(X, y).predict(X)
    assert mean_pred.nunique() == 1 and mean_pred.iloc[0] == pytest.approx(y.mean())
    persist = MD.PersistenceModel("f1").fit(X, y).predict(X)
    pd.testing.assert_series_equal(persist, X["f1"].rename("prediction"))
    with pytest.raises(KeyError):
        MD.PersistenceModel("nope").fit(X, y)


# --- standardization fits on train only --------------------------------------
def test_sklearn_standardizes_on_train_only():
    feats, label = _panels(n=60, k=3)
    X, y = MD.make_design(feats, label)
    m = MD.ridge(alpha=0.1).fit(X, y)
    # scaler stats came from the fitted X; predicting a shifted copy must use the
    # SAME stored mean/std (not recompute on the new data).
    assert m._mu is not None and m._sd is not None
    shifted = X + 100.0
    p_shifted = m.predict(shifted)
    # with train-only scaling, a +100 shift in raw features moves predictions a lot;
    # if it re-standardized on `shifted` the prediction would be ~unchanged.
    assert not np.allclose(p_shifted.to_numpy(), m.predict(X).to_numpy())


# --- walk-forward OOS: recovery + no leakage ---------------------------------
def test_walk_forward_predict_recovers_and_is_oos():
    feats, label = _panels(n=500, k=5)
    X, y = MD.make_design(feats, label)
    folds = B.walk_forward(label.index, train=150, test=50, horizon=1, embargo=1)
    pred = MD.walk_forward_predict(lambda: MD.ridge(alpha=0.1), X, y, folds)
    assert not pred.empty
    # predictions land only on test dates (never train) -> out-of-sample
    pred_dates = pred.index.get_level_values("date").unique()
    test_dates = pd.DatetimeIndex(np.concatenate([f.test.values for f in folds])).unique()
    assert set(pred_dates) <= set(test_dates)
    # the learnable signal is recovered OOS: predictions correlate with the truth
    truth = y.loc[pred.index]
    assert truth.corr(pred) > 0.9


def test_walk_forward_fresh_model_per_fold():
    # a model that records how many times it was fitted proves a new instance per fold
    feats, label = _panels(n=300, k=3)
    X, y = MD.make_design(feats, label)
    folds = B.walk_forward(label.index, train=120, test=40, horizon=1)
    made = {"n": 0}

    def factory():
        made["n"] += 1
        return MD.MeanModel()

    MD.walk_forward_predict(factory, X, y, folds)
    assert made["n"] == len(folds)  # one fresh model per fold, no reuse
