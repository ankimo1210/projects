"""4象限への割り当てと、右上（AI解放）ランキング。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import (
    Q_CONSTRAINED,
    Q_ESCAPE,
    Q_INSENSITIVE,
    Q_MARGIN,
    Config,
)


def thresholds(shortage: pd.Series, ai: pd.Series, cfg: Config) -> tuple[float, float]:
    """Return the (shortage, ai) cut points that define the quadrant boundaries."""
    cfg.validate()
    if cfg.threshold_method == "fixed":
        return cfg.fixed_threshold, cfg.fixed_threshold
    return float(shortage.median()), float(ai.median())


def project_cut(raw_cut: float, raw: pd.Series) -> float:
    """Express ``raw_cut`` on the 0-100 rescale that :func:`axes.rescale_0_100` gives ``raw``.

    The quadrant boundary is defined once, on the 33業種 distribution. Companies
    live on the same map, but their ``*_score`` columns are min-max rescaled over
    the *company* universe, so the sector median lands at a different number on
    that axis. Projecting the cut keeps one boundary across both levels instead of
    letting each population re-draw the gridlines around its own middle.
    """
    lo, hi = float(raw.min()), float(raw.max())
    if np.isclose(hi, lo):
        return 50.0
    return (raw_cut - lo) / (hi - lo) * 100.0


def assign_quadrants(
    shortage: pd.Series,
    ai: pd.Series,
    cfg: Config | None = None,
    cuts: tuple[float, float] | None = None,
) -> pd.Series:
    """Label each row with one of the four quadrants.

    Boundary handling: a value exactly on the cut point counts as the *lower*
    side, so an entity must strictly exceed the threshold to be called
    high-shortage or high-AI. With a median split on an even-sized universe
    this keeps the top-right cell from being inflated by ties.

    ``cuts`` overrides the boundary with explicit values *in the same units as
    the passed series*. :func:`company.company_frame` uses it to inherit the
    sector-level boundary rather than splitting the company universe at its own
    median — see :func:`project_cut`.
    """
    cfg = cfg or Config()
    x_cut, y_cut = cuts if cuts is not None else thresholds(shortage, ai, cfg)

    high_shortage = shortage > x_cut
    high_ai = ai > y_cut

    labels = np.where(
        high_shortage & high_ai,
        Q_ESCAPE,
        np.where(
            high_shortage & ~high_ai,
            Q_CONSTRAINED,
            np.where(~high_shortage & high_ai, Q_MARGIN, Q_INSENSITIVE),
        ),
    )
    return pd.Series(labels, index=shortage.index, name="quadrant")


def escape_potential(shortage: pd.Series, ai: pd.Series) -> pd.Series:
    """幾何平均。両軸とも高いときだけ高くなる（片方が0なら0）。

    算術平均だと「人手不足は極端だがAIでは解けない」建設業のような
    ケースが上位に来てしまい、framework の意味が失われる。
    """
    return pd.Series(np.sqrt(shortage.clip(lower=0) * ai.clip(lower=0)), index=shortage.index)


def top_right(df: pd.DataFrame, n: int | None = None) -> pd.DataFrame:
    """Rows in the top-right quadrant, ranked by escape potential."""
    out = df[df["quadrant"] == Q_ESCAPE].sort_values("escape_potential", ascending=False)
    return out if n is None else out.head(n)


def rankable(df: pd.DataFrame) -> pd.Series:
    """Rows whose parent-company P/L can carry a ranking.

    Two exclusions, neither of them a tuning knob:

    * **営業利益が0以下** — the uplift is undefined there (``op_uplift_pct`` is
      already NaN), and leaving the row in the table reads as "loss-making yet
      top-ranked".
    * **人件費が売上を上回る** — impossible for a going concern, so it is
      evidence that the 提出会社 figures do not describe an operating business.
      It happens to pure holding companies, whose parent books the group's head
      office payroll against a fraction of the group's revenue.

    Both rows stay in the exported data; they are only kept out of the ranking.
    """
    if "op_uplift_pct" not in df.columns:
        return pd.Series(True, index=df.index)
    keep = df["op_uplift_pct"].notna()
    if "labor_cost_ratio" in df.columns:
        keep &= ~(df["labor_cost_ratio"] > 1.0)
    return keep


def quadrant_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Counts and mean coordinates per quadrant — a sanity check on the split."""
    grouped = df.groupby("quadrant", observed=True).agg(
        n=("escape_potential", "size"),
        mean_shortage=("shortage_score", "mean"),
        mean_ai=("ai_score", "mean"),
        mean_escape=("escape_potential", "mean"),
    )
    order = [q for q in (Q_ESCAPE, Q_CONSTRAINED, Q_MARGIN, Q_INSENSITIVE) if q in grouped.index]
    return grouped.loc[order].round(1)
