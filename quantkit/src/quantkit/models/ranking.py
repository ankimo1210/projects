"""Learning-to-rank for cross-sectional alpha.

The strategies are judged on cross-sectional *ordering* (rank IC), not on the level
of predicted returns, so it pays to train on the order directly. ``cross_sectional_rank``
replaces each date's targets with their centered, zero-mean within-date ranks, and
:class:`RankModel` fits any base model on that rank-target. The fitted model then
scores assets for ranking — a pragmatic pointwise learning-to-rank that optimizes the
metric the book is actually graded on, and is robust to the heavy tails of raw returns.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from .base import Model


def cross_sectional_rank(y: pd.Series) -> pd.Series:
    """Per-date, zero-mean rank transform of a ``(date, asset)`` target.

    Within each date the values are ranked and centered to mean 0 (scaled by the
    cross-section size), preserving the ordering while discarding magnitude and
    outliers — the natural target for a ranking objective.
    """
    dates = y.index.get_level_values("date")

    def _centered_rank(s: pd.Series) -> pd.Series:
        n = len(s)
        if n <= 1:
            return s * 0.0
        return (s.rank() - (n + 1) / 2.0) / n

    return y.groupby(dates, group_keys=False).apply(_centered_rank).rename("rank_target")


class RankModel(Model):
    """Wrap a base model to train on the within-date rank target (learning-to-rank)."""

    def __init__(self, base: Model, name: str = "learning_to_rank"):
        self.base = base
        self.name = name

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RankModel:
        self.base.fit(X, cross_sectional_rank(y))
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        return self.base.predict(X)


def learning_to_rank(base_factory: Callable[..., Model], **kw) -> RankModel:
    """Build a :class:`RankModel` around ``base_factory(**kw)`` (e.g. ``ridge``)."""
    return RankModel(base_factory(**kw))
