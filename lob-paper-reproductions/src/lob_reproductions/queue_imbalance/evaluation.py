from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


def evaluate_binary_probability_forecast(
    response: np.ndarray, probability_up: np.ndarray
) -> dict[str, Any]:
    y = np.asarray(response, dtype=np.int64).reshape(-1)
    probability = np.asarray(probability_up, dtype=float).reshape(-1)
    if y.shape != probability.shape:
        raise ValueError("response and forecasts must align")
    if not np.all(np.isin(y, (0, 1))):
        raise ValueError("response must be binary")
    if np.unique(y).size < 2:
        raise ValueError("response contains a single class; ROC-AUC is undefined")
    if not np.all(np.isfinite(probability)) or np.any((probability < 0) | (probability > 1)):
        raise ValueError("forecasts must be finite probabilities")
    false_positive, true_positive, thresholds = roc_curve(y, probability)
    return {
        "roc_auc": float(roc_auc_score(y, probability)),
        "mean_squared_residual": float(np.mean((probability - y) ** 2)),
        "roc_curve": {
            "false_positive_rate": false_positive.tolist(),
            "true_positive_rate": true_positive.tolist(),
            "thresholds": thresholds.tolist(),
        },
    }


def null_model_metrics(response: np.ndarray) -> dict[str, float]:
    y = np.asarray(response, dtype=float)
    probability = np.full_like(y, 0.5, dtype=float)
    return {
        "roc_auc": 0.5,
        "mean_squared_residual": float(np.mean((probability - y) ** 2)),
    }
