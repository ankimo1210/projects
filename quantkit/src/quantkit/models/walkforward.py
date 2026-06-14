"""Walk-forward training: fit on each fold's train, predict its test, out-of-sample.

A **fresh** model is built per fold (via the ``make_model`` factory), so nothing
learned on a later fold can leak backward, and the purge+embargo already baked
into the folds (:mod:`quantkit.backtest.split`) keeps each train strictly behind its
test. The concatenated test predictions form one honest out-of-sample series that
feeds the same backtest engine and baseline comparison as everything else.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from ..backtest.split import Fold
from .base import Model


def walk_forward_predict(
    make_model: Callable[[], Model],
    X: pd.DataFrame,
    y: pd.Series,
    folds: list[Fold],
) -> pd.Series:
    """Out-of-sample predictions over ``folds``.

    ``X``/``y`` are ``(date, asset)``-indexed (see :func:`quantkit.models.design.make_design`).
    For each fold, fit ``make_model()`` on rows whose date is in ``fold.train`` and
    predict rows whose date is in ``fold.test``. Returns the concatenated test
    predictions (a ``(date, asset)`` Series). Test blocks from ``walk_forward`` are
    non-overlapping, so no date is predicted twice.
    """
    dates = X.index.get_level_values("date")
    preds: list[pd.Series] = []
    for fold in folds:
        tr = X[dates.isin(fold.train)]
        te = X[dates.isin(fold.test)]
        if tr.empty or te.empty:
            continue
        model = make_model().fit(tr, y.loc[tr.index])
        preds.append(model.predict(te))
    if not preds:
        return pd.Series(dtype="float64", name="prediction")
    return pd.concat(preds).rename("prediction")
