"""Non-causal feature diagnostics for forecasting models."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import torch
from torch import nn


def _diagnostic_inputs(features: np.ndarray, targets: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(features, dtype=float)
    y = np.asarray(targets, dtype=float)
    if (
        x.ndim != 2
        or x.shape[0] < 2
        or x.shape[1] < 1
        or y.shape != (len(x),)
        or np.any(~np.isfinite(x))
        or np.any(~np.isfinite(y))
    ):
        raise ValueError("features must be finite 2-D data with aligned targets")
    return x, y


def _prediction(predict: Callable[[np.ndarray], np.ndarray], features: np.ndarray) -> np.ndarray:
    values = np.asarray(predict(features), dtype=float)
    if values.shape != (len(features),) or np.any(~np.isfinite(values)):
        raise ValueError("predict must return one finite value per row")
    return values


def permutation_importance(
    predict: Callable[[np.ndarray], np.ndarray],
    features: np.ndarray,
    targets: np.ndarray,
    *,
    seed: int = 0,
) -> np.ndarray:
    """MSE increase per feature when that feature column is shuffled."""
    x, y = _diagnostic_inputs(features, targets)
    baseline = np.mean((_prediction(predict, x) - y) ** 2)
    rng = np.random.default_rng(seed)
    result = np.empty(x.shape[1])
    for column in range(x.shape[1]):
        perturbed = x.copy()
        rng.shuffle(perturbed[:, column])
        result[column] = np.mean((_prediction(predict, perturbed) - y) ** 2) - baseline
    return result


def occlusion_importance(
    predict: Callable[[np.ndarray], np.ndarray],
    features: np.ndarray,
    targets: np.ndarray,
) -> np.ndarray:
    """MSE increase per feature when that feature is fixed at its median."""
    x, y = _diagnostic_inputs(features, targets)
    baseline = np.mean((_prediction(predict, x) - y) ** 2)
    result = np.empty(x.shape[1])
    for column in range(x.shape[1]):
        occluded = x.copy()
        occluded[:, column] = np.median(x[:, column])
        result[column] = np.mean((_prediction(predict, occluded) - y) ** 2) - baseline
    return result


def integrated_gradients(
    model: nn.Module,
    inputs: torch.Tensor,
    *,
    baseline: torch.Tensor | None = None,
    steps: int = 32,
) -> torch.Tensor:
    """Trapezoid integrated gradients from a baseline to the inputs."""
    if steps < 2:
        raise ValueError("steps must be at least two")
    reference = torch.zeros_like(inputs) if baseline is None else baseline
    if reference.shape != inputs.shape:
        raise ValueError("baseline must match inputs")
    gradients = []
    for alpha in torch.linspace(0, 1, steps, device=inputs.device, dtype=inputs.dtype):
        point = (reference + alpha * (inputs - reference)).detach().requires_grad_(True)
        output = model(point).sum()
        gradients.append(torch.autograd.grad(output, point)[0])
    stacked = torch.stack(gradients)
    average = 0.5 * (stacked[:-1] + stacked[1:]).mean(dim=0)
    return (inputs - reference) * average


def diagnostic_rank_stability(*importances: np.ndarray) -> float:
    """Return the minimum pairwise rank correlation; diagnostics are not causal."""
    if len(importances) < 2:
        raise ValueError("need at least two diagnostics")
    arrays = [np.asarray(values, dtype=float) for values in importances]
    if (
        any(array.ndim != 1 or array.size < 2 for array in arrays)
        or len({array.shape for array in arrays}) != 1
        or any(np.any(~np.isfinite(array)) for array in arrays)
    ):
        raise ValueError("diagnostics must be matching finite vectors with at least two features")
    ranks = [np.argsort(np.argsort(array)) for array in arrays]
    correlations = [
        np.corrcoef(ranks[i], ranks[j])[0, 1]
        for i in range(len(ranks))
        for j in range(i + 1, len(ranks))
    ]
    return float(np.nanmin(correlations))
