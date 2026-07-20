from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import expit


def tricube(distance: np.ndarray, radius: float) -> np.ndarray:
    if radius <= 0:
        return np.ones_like(distance, dtype=float)
    scaled = np.abs(distance) / radius
    return np.where(scaled < 1.0, (1.0 - scaled**3) ** 3, 0.0)


@dataclass
class LocalLogisticRegression:
    """Local-linear logistic fit with a nearest-neighbour tricube kernel."""

    bandwidth: float = 0.65
    max_iter: int = 50
    tolerance: float = 1e-9
    x_: np.ndarray | None = None
    y_: np.ndarray | None = None

    def fit(self, imbalance: np.ndarray, response: np.ndarray) -> LocalLogisticRegression:
        x = np.asarray(imbalance, dtype=float).reshape(-1)
        y = np.asarray(response, dtype=float).reshape(-1)
        if x.shape != y.shape or x.size < 5:
            raise ValueError("local logistic regression requires aligned vectors of length >= 5")
        if not 0 < self.bandwidth <= 1:
            raise ValueError("nearest-neighbour bandwidth must be in (0, 1]")
        if not np.all(np.isin(y, (0.0, 1.0))):
            raise ValueError("response must be binary")
        order = np.argsort(x, kind="mergesort")
        self.x_ = x[order]
        self.y_ = y[order]
        return self

    @staticmethod
    def _weighted_deviance(
        design: np.ndarray, response: np.ndarray, weights: np.ndarray, beta: np.ndarray
    ) -> float:
        linear = design @ beta
        return float(np.sum(weights * (np.logaddexp(0.0, linear) - response * linear)))

    def _fit_at(self, query: float) -> tuple[float, np.ndarray]:
        if self.x_ is None or self.y_ is None:
            raise RuntimeError("model is not fitted")
        distance = np.abs(self.x_ - query)
        neighbour_count = min(self.x_.size, max(3, int(np.ceil(self.bandwidth * self.x_.size))))
        radius = float(np.partition(distance, neighbour_count - 1)[neighbour_count - 1])
        if radius == 0:
            positive = distance[distance > 0]
            radius = float(positive.min()) if positive.size else 1.0
        # nextafter includes the furthest selected neighbour rather than assigning it zero.
        weights = tricube(distance, float(np.nextafter(radius, np.inf)))
        design = np.column_stack((np.ones_like(self.x_), self.x_ - query))
        beta = np.zeros(2, dtype=float)
        deviance = self._weighted_deviance(design, self.y_, weights, beta)
        for _ in range(self.max_iter):
            probability = expit(design @ beta)
            variance = np.clip(probability * (1.0 - probability), 1e-12, None)
            gradient = design.T @ (weights * (self.y_ - probability))
            hessian = design.T @ ((weights * variance)[:, None] * design)
            hessian.flat[::3] += 1e-10
            try:
                step = np.linalg.solve(hessian, gradient)
            except np.linalg.LinAlgError:
                step = np.linalg.pinv(hessian) @ gradient
            # Newton with step halving: on separated neighbourhoods a full step can
            # overshoot into non-finite territory; damping keeps the fit monotone.
            step_scale = 1.0
            candidate = beta + step
            candidate_deviance = self._weighted_deviance(design, self.y_, weights, candidate)
            for _ in range(30):
                if np.isfinite(candidate_deviance) and candidate_deviance <= deviance + 1e-12:
                    break
                step_scale *= 0.5
                candidate = beta + step_scale * step
                candidate_deviance = self._weighted_deviance(design, self.y_, weights, candidate)
            if np.max(np.abs(candidate - beta)) < self.tolerance:
                beta = candidate
                break
            beta = candidate
            deviance = candidate_deviance
        return float(expit(beta[0])), beta

    def predict_proba(self, imbalance: np.ndarray) -> np.ndarray:
        query = np.asarray(imbalance, dtype=float)
        flat = query.reshape(-1)
        predictions = np.fromiter((self._fit_at(float(value))[0] for value in flat), dtype=float)
        return predictions.reshape(query.shape)


def cross_validate_bandwidth(
    imbalance: np.ndarray,
    response: np.ndarray,
    *,
    candidates: tuple[float, ...] = (0.5, 0.6, 0.65, 0.7, 0.8),
    folds: int = 5,
    seed: int = 7,
) -> tuple[float, dict[float, float]]:
    """Five-fold CV minimizing mean squared residual, as stated in Sec. 6.4."""

    x = np.asarray(imbalance, dtype=float).reshape(-1)
    y = np.asarray(response, dtype=float).reshape(-1)
    if x.shape != y.shape or folds < 2 or folds > x.size:
        raise ValueError("invalid cross-validation input")
    permutation = np.random.default_rng(seed).permutation(x.size)
    fold_indices = np.array_split(permutation, folds)
    scores: dict[float, float] = {}
    for candidate in candidates:
        residuals: list[np.ndarray] = []
        for validation_index in fold_indices:
            training_mask = np.ones(x.size, dtype=bool)
            training_mask[validation_index] = False
            model = LocalLogisticRegression(bandwidth=candidate).fit(
                x[training_mask], y[training_mask]
            )
            prediction = model.predict_proba(x[validation_index])
            residuals.append((prediction - y[validation_index]) ** 2)
        scores[candidate] = float(np.concatenate(residuals).mean())
    selected = min(candidates, key=lambda value: (scores[value], value))
    return selected, scores
