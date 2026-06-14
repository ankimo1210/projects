"""Design-matrix construction for cross-sectional learning.

Stacks several feature panels (each ``dates × assets``) and a label panel into a
long, ``(date, asset)``-indexed feature frame ``X`` and aligned target ``y``.
Rows with any missing feature or label are **dropped, not imputed** — consistent
with the platform's no-silent-fill rule — and the drop count is returned so the
loss of coverage is visible, never hidden.
"""

from __future__ import annotations

import pandas as pd


def _stack(panel: pd.DataFrame, name: str) -> pd.Series:
    p = panel.copy()
    p.index.name = "date"
    p.columns.name = "asset"
    return p.stack(future_stack=True).rename(name)


def make_design(
    features: dict[str, pd.DataFrame], label: pd.DataFrame, *, return_dropped: bool = False
):
    """Build ``(X, y)`` from feature panels and a label panel.

    Parameters
    ----------
    features : name -> (dates × assets) feature panel.
    label : (dates × assets) target panel (e.g. forward returns).
    return_dropped : if True, also return the number of rows dropped for NaN.
    """
    if not features:
        raise ValueError("need at least one feature panel")
    cols = {name: _stack(panel, name) for name, panel in features.items()}
    X = pd.DataFrame(cols)
    y = _stack(label, "label")
    full = X.join(y, how="inner")
    n_before = len(full)
    full = full.dropna()
    X_out, y_out = full[list(features)], full["label"]
    if return_dropped:
        return X_out, y_out, n_before - len(full)
    return X_out, y_out


def predictions_to_panel(pred: pd.Series) -> pd.DataFrame:
    """Pivot a ``(date, asset)``-indexed prediction Series back to a dates × assets panel."""
    return pred.unstack("asset").sort_index()
