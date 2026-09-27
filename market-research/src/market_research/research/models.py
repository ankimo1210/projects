"""Simple out-of-sample baselines and train-only model candidates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from .signals import SignalDataset
from .splits import walk_forward_splits


@dataclass(frozen=True, slots=True)
class ModelEvaluation:
    table: pd.DataFrame
    instrument_id: str
    snapshot_ids: tuple[str, ...]
    currency: str
    adjustment: str
    horizon: int


def _ridge_predict(
    train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray, alpha: float
) -> np.ndarray:
    mean_x = train_x.mean(axis=0)
    scale_x = train_x.std(axis=0)
    scale_x = np.where(scale_x > 0.0, scale_x, 1.0)
    standardized_train = (train_x - mean_x) / scale_x
    standardized_test = (test_x - mean_x) / scale_x
    mean_y = train_y.mean()
    gram = standardized_train.T @ standardized_train
    penalty = alpha * np.eye(train_x.shape[1])
    try:
        coefficients = np.linalg.solve(gram + penalty, standardized_train.T @ (train_y - mean_y))
    except np.linalg.LinAlgError as error:
        raise ValueError("training design is singular; increase ridge_alpha") from error
    return standardized_test @ coefficients + mean_y


def _tree_predict(
    train_x: np.ndarray,
    train_y: np.ndarray,
    test_x: np.ndarray,
    max_depth: int,
    min_leaf: int,
) -> np.ndarray:
    """Fit squared-error splits on training rows and predict test leaves."""
    predictions = np.empty(len(test_x), dtype=float)

    def visit(train_rows: np.ndarray, test_rows: np.ndarray, depth: int) -> None:
        labels = train_y[train_rows]
        leaf_value = float(labels.mean())
        if depth >= max_depth or len(train_rows) < 2 * min_leaf:
            predictions[test_rows] = leaf_value
            return

        best_loss = float(np.sum((labels - leaf_value) ** 2))
        best_feature: int | None = None
        best_threshold = 0.0
        for feature in range(train_x.shape[1]):
            ordered = train_rows[np.argsort(train_x[train_rows, feature], kind="stable")]
            values = train_x[ordered, feature]
            targets = train_y[ordered] - leaf_value
            sums = np.cumsum(targets)
            squares = np.cumsum(targets**2)
            for count in range(min_leaf, len(ordered) - min_leaf + 1):
                if values[count - 1] == values[count]:
                    continue
                left_sum = sums[count - 1]
                right_sum = sums[-1] - left_sum
                left_loss = max(0.0, squares[count - 1] - left_sum**2 / count)
                right_loss = max(
                    0.0,
                    squares[-1] - squares[count - 1] - right_sum**2 / (len(ordered) - count),
                )
                loss = left_loss + right_loss
                if loss < best_loss:
                    best_loss = loss
                    best_feature = feature
                    best_threshold = float(values[count - 1])

        if best_feature is None:
            predictions[test_rows] = leaf_value
            return
        train_left = train_x[train_rows, best_feature] <= best_threshold
        test_left = test_x[test_rows, best_feature] <= best_threshold
        if test_left.any():
            visit(train_rows[train_left], test_rows[test_left], depth + 1)
        if (~test_left).any():
            visit(train_rows[~train_left], test_rows[~test_left], depth + 1)

    visit(np.arange(len(train_y)), np.arange(len(test_x)), 0)
    return predictions


def evaluate_models(
    dataset: SignalDataset,
    *,
    train_size: int,
    test_size: int,
    feature_names: tuple[str, ...] = ("momentum", "volatility"),
    embargo: int = 0,
    step: int | None = None,
    expanding: bool = False,
    lockbox_start: datetime | None = None,
    ridge_alpha: float = 1.0,
    tree_max_depth: int = 2,
    tree_min_leaf: int = 2,
) -> ModelEvaluation:
    """Compare zero, train mean, ridge and tree on the same forward-only rows."""
    if not isinstance(dataset, SignalDataset):
        raise TypeError("a SignalDataset is required")
    if not feature_names or len(feature_names) != len(set(feature_names)):
        raise ValueError("feature_names must be nonempty and unique")
    if not set(feature_names).issubset({"momentum", "volatility"}):
        raise ValueError("only causal feature columns may be selected")
    if not set(feature_names).issubset(dataset.table.columns):
        raise ValueError("requested features are missing")
    if isinstance(ridge_alpha, bool) or not np.isfinite(ridge_alpha) or ridge_alpha < 0:
        raise ValueError("ridge_alpha must be finite and nonnegative")
    for name, value in (("tree_max_depth", tree_max_depth), ("tree_min_leaf", tree_min_leaf)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    splits = walk_forward_splits(
        dataset,
        train_size=train_size,
        test_size=test_size,
        embargo=embargo,
        step=step,
        expanding=expanding,
        lockbox_start=lockbox_start,
    )
    table = dataset.table
    output = []
    for fold, split in enumerate(splits):
        train_x = table.iloc[list(split.train_indices)].loc[:, feature_names].to_numpy(dtype=float)
        train_y = table.iloc[list(split.train_indices)]["label"].to_numpy(dtype=float)
        complete_train = np.isfinite(train_x).all(axis=1) & np.isfinite(train_y)
        train_x = train_x[complete_train]
        train_y = train_y[complete_train]
        if len(train_y) < 2:
            raise ValueError("at least two complete training rows are required")
        test = table.iloc[list(split.test_indices)]
        test_x = test.loc[:, feature_names].to_numpy(dtype=float)
        if not np.isfinite(test_x).all():
            raise ValueError("test features must be complete")
        ridge = _ridge_predict(train_x, train_y, test_x, ridge_alpha)
        tree = _tree_predict(train_x, train_y, test_x, tree_max_depth, tree_min_leaf)
        for offset, (index, row) in enumerate(test.iterrows()):
            output.append(
                {
                    "decision_at": index,
                    "fold": fold,
                    "train_rows": len(train_y),
                    "zero": 0.0,
                    "mean": float(train_y.mean()),
                    "ridge": float(ridge[offset]),
                    "tree": float(tree[offset]),
                    "label": float(row["label"]),
                    "label_available_at": row["label_available_at"],
                }
            )
    results = pd.DataFrame(output).set_index("decision_at")
    results.index = pd.DatetimeIndex(results.index)
    return ModelEvaluation(
        results,
        dataset.instrument_id,
        dataset.snapshot_ids,
        dataset.currency,
        dataset.adjustment,
        dataset.horizon,
    )
