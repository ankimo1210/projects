"""Out-of-sample feature importance by mean-decrease-accuracy (MDA).

MDA (López de Prado) measures importance *out of sample*: fit a model on each
fold's train block, score its predictions on the test block, then permute one
feature inside the test block and re-score. A feature that genuinely drives the
label loses score when shuffled; a noise feature does not. The decrease, averaged
over folds and permutation repeats, is the importance.

It reuses the purge+embargo folds (:mod:`quantkit.backtest.split`) and the common
``fit``/``predict`` model contract, so importances are computed on exactly the same
honest evaluation as every backtest — not on in-sample fit, where noise features
can look important. The default score is the cross-sectional **rank IC** (the metric
the strategies are judged on); pass ``scorer`` to use another.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from ..backtest.split import Fold
from .base import Model


def rank_ic(pred: pd.Series, label: pd.Series) -> float:
    """Mean cross-sectional rank IC (Spearman) between ``pred`` and ``label`` over dates.

    Both are ``(date, asset)``-indexed. For each date, rank-correlate the
    predictions with the labels across assets; the importance metric is the mean
    over dates. Dates with fewer than two assets are skipped (corr undefined).
    """
    df = pd.DataFrame({"pred": pred, "label": label}).dropna()
    if df.empty:
        return float("nan")
    dates = df.index.get_level_values("date")
    ics: list[float] = []
    for _, g in df.groupby(dates, sort=False):
        if len(g) < 2:
            continue
        ic = g["pred"].rank().corr(g["label"].rank())
        if pd.notna(ic):
            ics.append(float(ic))
    return float(np.mean(ics)) if ics else float("nan")


def mda_importance(
    make_model: Callable[[], Model],
    X: pd.DataFrame,
    y: pd.Series,
    folds: list[Fold],
    *,
    features: list[str] | None = None,
    scorer: Callable[[pd.Series, pd.Series], float] | None = None,
    n_repeats: int = 5,
    random_state: int = 0,
) -> pd.DataFrame:
    """Mean-decrease-accuracy importance of each feature over ``folds``.

    For every fold a fresh ``make_model()`` is fit on the train block and scored on
    the test block (baseline). Each feature is then permuted within the test block
    ``n_repeats`` times and re-scored with the *same* fitted model; the importance is
    ``baseline - permuted`` averaged over folds and repeats. Permutations come from a
    seeded generator, so the result is deterministic given ``random_state``.

    Returns a frame indexed by feature with columns ``importance`` (mean decrease),
    ``std`` (across fold×repeat) and ``n`` (sample count), sorted most-important first.
    """
    feats = list(features) if features is not None else list(X.columns)
    score = scorer or rank_ic
    rng = np.random.default_rng(random_state)
    dates = X.index.get_level_values("date")
    decreases: dict[str, list[float]] = {f: [] for f in feats}
    for fold in folds:
        tr = X[dates.isin(fold.train)]
        te = X[dates.isin(fold.test)]
        if tr.empty or te.empty:
            continue
        model = make_model().fit(tr, y.loc[tr.index])
        y_te = y.loc[te.index]
        base = score(model.predict(te), y_te)
        for f in feats:
            col = te[f].to_numpy()
            for _ in range(n_repeats):
                te_perm = te.copy()
                te_perm[f] = rng.permutation(col)
                permuted = score(model.predict(te_perm), y_te)
                decreases[f].append(base - permuted)
    rows = {}
    for f in feats:
        vals = np.asarray(decreases[f], dtype=float)
        rows[f] = {
            "importance": float(np.nanmean(vals)) if vals.size else float("nan"),
            "std": float(np.nanstd(vals)) if vals.size else float("nan"),
            "n": int(vals.size),
        }
    out = pd.DataFrame(rows).T[["importance", "std", "n"]]
    out.index.name = "feature"
    return out.sort_values("importance", ascending=False)
