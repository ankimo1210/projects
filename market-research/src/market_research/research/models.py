"""Simple out-of-sample baselines and a train-only ridge candidate."""

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
) -> ModelEvaluation:
    """Compare zero, train mean and ridge on the same forward-only rows."""
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
        for offset, (index, row) in enumerate(test.iterrows()):
            output.append(
                {
                    "decision_at": index,
                    "fold": fold,
                    "train_rows": len(train_y),
                    "zero": 0.0,
                    "mean": float(train_y.mean()),
                    "ridge": float(ridge[offset]),
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
