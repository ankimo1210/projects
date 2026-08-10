"""Small, inspectable B6 models and shift diagnostics built on NumPy/SciPy."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _feature_matrix(features: np.ndarray, *, n_features: int | None = None) -> np.ndarray:
    matrix = np.asarray(features, dtype=float)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    if matrix.ndim != 2 or matrix.shape[0] == 0:
        raise ValueError("features must be a non-empty two-dimensional array")
    if n_features is not None and matrix.shape[1] != n_features:
        raise ValueError(f"features must have {n_features} columns")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("features must be finite")
    return matrix


def _target_vector(target: np.ndarray, *, n_rows: int) -> np.ndarray:
    vector = np.asarray(target, dtype=float)
    if vector.shape != (n_rows,) or not np.all(np.isfinite(vector)):
        raise ValueError("target must be finite with one value per feature row")
    return vector


def _standardize(features: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = features.mean(axis=0)
    scale = features.std(axis=0, ddof=0)
    scale = np.where(scale > np.finfo(float).eps * np.maximum(np.abs(mean), 1.0), scale, 1.0)
    return (features - mean) / scale, mean, scale


def _rbf_kernel(
    left: np.ndarray,
    right: np.ndarray,
    *,
    length_scale: float,
    amplitude: float = 1.0,
) -> np.ndarray:
    left_norm = np.sum(left**2, axis=1)[:, None]
    right_norm = np.sum(right**2, axis=1)[None, :]
    squared_distance = np.maximum(left_norm + right_norm - 2.0 * left @ right.T, 0.0)
    return amplitude * np.exp(-0.5 * squared_distance / length_scale**2)


@dataclass(frozen=True)
class DecisionStump:
    n_features: int
    feature_index: int
    threshold: float
    left_value: float
    right_value: float
    squared_error: float

    def predict(self, features: np.ndarray) -> np.ndarray:
        matrix = _feature_matrix(features, n_features=self.n_features)
        if not 0 <= self.feature_index < self.n_features:
            raise ValueError("stump feature_index is outside the feature matrix")
        return np.where(
            matrix[:, self.feature_index] <= self.threshold,
            self.left_value,
            self.right_value,
        )


@dataclass(frozen=True)
class GradientBoostingModel:
    initial_prediction: float
    stumps: tuple[DecisionStump, ...]
    learning_rate: float
    training_loss: np.ndarray

    def predict(self, features: np.ndarray) -> np.ndarray:
        matrix = _feature_matrix(features)
        prediction = np.full(matrix.shape[0], self.initial_prediction, dtype=float)
        for stump in self.stumps:
            prediction += self.learning_rate * stump.predict(matrix)
        return prediction


@dataclass(frozen=True)
class KernelRidgeModel:
    train_features: np.ndarray
    dual_coefficients: np.ndarray
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    target_mean: float
    length_scale: float
    ridge: float

    def predict(self, features: np.ndarray) -> np.ndarray:
        matrix = _feature_matrix(features, n_features=self.train_features.shape[1])
        standardized = (matrix - self.feature_mean) / self.feature_scale
        kernel = _rbf_kernel(standardized, self.train_features, length_scale=self.length_scale)
        return self.target_mean + kernel @ self.dual_coefficients


@dataclass(frozen=True)
class GaussianProcessPrediction:
    mean: np.ndarray
    standard_deviation: np.ndarray


@dataclass(frozen=True)
class GaussianProcessModel:
    train_features: np.ndarray
    dual_coefficients: np.ndarray
    cholesky_factor: np.ndarray
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    target_mean: float
    length_scale: float
    signal_variance: float
    noise_variance: float

    def predict(self, features: np.ndarray) -> GaussianProcessPrediction:
        matrix = _feature_matrix(features, n_features=self.train_features.shape[1])
        standardized = (matrix - self.feature_mean) / self.feature_scale
        cross_kernel = _rbf_kernel(
            standardized,
            self.train_features,
            length_scale=self.length_scale,
            amplitude=self.signal_variance,
        )
        mean = self.target_mean + cross_kernel @ self.dual_coefficients
        solved = np.linalg.solve(self.cholesky_factor, cross_kernel.T)
        latent_variance = np.maximum(
            self.signal_variance - np.sum(solved**2, axis=0),
            0.0,
        )
        return GaussianProcessPrediction(
            mean=mean,
            standard_deviation=np.sqrt(latent_variance + self.noise_variance),
        )


@dataclass(frozen=True)
class KMeansModel:
    centers: np.ndarray
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    labels: np.ndarray
    inertia: float
    iterations: int
    converged: bool

    def predict(self, features: np.ndarray) -> np.ndarray:
        matrix = _feature_matrix(features, n_features=self.centers.shape[1])
        standardized = (matrix - self.feature_mean) / self.feature_scale
        distances = np.sum((standardized[:, None, :] - self.centers[None, :, :]) ** 2, axis=2)
        return np.argmin(distances, axis=1)


@dataclass(frozen=True)
class FeatureDriftReport:
    feature_names: tuple[str, ...]
    standardized_mean_difference: np.ndarray
    population_stability_index: np.ndarray
    maximum_absolute_mean_difference: float
    maximum_population_stability_index: float


@dataclass(frozen=True)
class ConformalInterval:
    lower: np.ndarray
    upper: np.ndarray
    residual_quantile: float
    nominal_coverage: float


def fit_decision_stump(
    features: np.ndarray,
    target: np.ndarray,
    *,
    min_leaf_size: int = 20,
    max_thresholds_per_feature: int = 64,
) -> DecisionStump:
    """Fit a squared-error regression stump with bounded threshold search."""
    matrix = _feature_matrix(features)
    vector = _target_vector(target, n_rows=matrix.shape[0])
    if isinstance(min_leaf_size, bool) or not 1 <= min_leaf_size <= matrix.shape[0] // 2:
        raise ValueError("min_leaf_size must permit two non-empty leaves")
    if isinstance(max_thresholds_per_feature, bool) or max_thresholds_per_feature < 1:
        raise ValueError("max_thresholds_per_feature must be positive")

    best: DecisionStump | None = None
    for feature_index in range(matrix.shape[1]):
        order = np.argsort(matrix[:, feature_index], kind="mergesort")
        values = matrix[order, feature_index]
        ordered_target = vector[order]
        possible = np.flatnonzero(values[:-1] < values[1:]) + 1
        possible = possible[
            (possible >= min_leaf_size) & (possible <= matrix.shape[0] - min_leaf_size)
        ]
        if possible.size > max_thresholds_per_feature:
            chosen = (
                np.linspace(0, possible.size - 1, max_thresholds_per_feature).round().astype(int)
            )
            possible = possible[chosen]
        cumulative = np.cumsum(ordered_target)
        cumulative_squared = np.cumsum(ordered_target**2)
        total = cumulative[-1]
        total_squared = cumulative_squared[-1]
        for split in possible:
            left_sum = cumulative[split - 1]
            left_squared = cumulative_squared[split - 1]
            right_sum = total - left_sum
            right_squared = total_squared - left_squared
            left_mean = left_sum / split
            right_count = matrix.shape[0] - split
            right_mean = right_sum / right_count
            error = left_squared - left_sum**2 / split + right_squared - right_sum**2 / right_count
            candidate = DecisionStump(
                n_features=matrix.shape[1],
                feature_index=feature_index,
                threshold=float(0.5 * (values[split - 1] + values[split])),
                left_value=float(left_mean),
                right_value=float(right_mean),
                squared_error=float(max(error, 0.0)),
            )
            if best is None or candidate.squared_error < best.squared_error:
                best = candidate
    if best is None:
        raise ValueError("no valid stump split exists for the requested leaf size")
    return best


def fit_gradient_boosting(
    features: np.ndarray,
    target: np.ndarray,
    *,
    n_estimators: int = 50,
    learning_rate: float = 0.05,
    min_leaf_size: int = 20,
) -> GradientBoostingModel:
    """Fit deterministic first-order gradient boosting with regression stumps."""
    matrix = _feature_matrix(features)
    vector = _target_vector(target, n_rows=matrix.shape[0])
    if isinstance(n_estimators, bool) or not isinstance(n_estimators, int) or n_estimators < 1:
        raise ValueError("n_estimators must be a positive integer")
    if not np.isfinite(learning_rate) or not 0.0 < learning_rate <= 1.0:
        raise ValueError("learning_rate must lie in (0, 1]")

    initial = float(vector.mean())
    prediction = np.full(vector.size, initial, dtype=float)
    stumps: list[DecisionStump] = []
    losses = [float(np.mean((vector - prediction) ** 2))]
    for _ in range(n_estimators):
        residual = vector - prediction
        stump = fit_decision_stump(matrix, residual, min_leaf_size=min_leaf_size)
        prediction += learning_rate * stump.predict(matrix)
        stumps.append(stump)
        losses.append(float(np.mean((vector - prediction) ** 2)))
    return GradientBoostingModel(
        initial_prediction=initial,
        stumps=tuple(stumps),
        learning_rate=float(learning_rate),
        training_loss=np.asarray(losses),
    )


def fit_kernel_ridge(
    features: np.ndarray,
    target: np.ndarray,
    *,
    length_scale: float = 1.0,
    ridge: float = 1e-2,
) -> KernelRidgeModel:
    matrix = _feature_matrix(features)
    vector = _target_vector(target, n_rows=matrix.shape[0])
    if not np.isfinite(length_scale) or length_scale <= 0.0:
        raise ValueError("length_scale must be strictly positive")
    if not np.isfinite(ridge) or ridge <= 0.0:
        raise ValueError("ridge must be strictly positive")
    standardized, mean, scale = _standardize(matrix)
    target_mean = float(vector.mean())
    centered = vector - target_mean
    kernel = _rbf_kernel(standardized, standardized, length_scale=length_scale)
    dual = np.linalg.solve(kernel + ridge * np.eye(matrix.shape[0]), centered)
    return KernelRidgeModel(
        train_features=standardized,
        dual_coefficients=dual,
        feature_mean=mean,
        feature_scale=scale,
        target_mean=target_mean,
        length_scale=float(length_scale),
        ridge=float(ridge),
    )


def fit_gaussian_process(
    features: np.ndarray,
    target: np.ndarray,
    *,
    length_scale: float = 1.0,
    noise_variance: float = 0.05,
) -> GaussianProcessModel:
    matrix = _feature_matrix(features)
    vector = _target_vector(target, n_rows=matrix.shape[0])
    if not np.isfinite(length_scale) or length_scale <= 0.0:
        raise ValueError("length_scale must be strictly positive")
    if not np.isfinite(noise_variance) or noise_variance <= 0.0:
        raise ValueError("noise_variance must be strictly positive")
    standardized, mean, scale = _standardize(matrix)
    target_mean = float(vector.mean())
    centered = vector - target_mean
    signal_variance = float(max(np.var(centered), np.finfo(float).eps))
    kernel = _rbf_kernel(
        standardized,
        standardized,
        length_scale=length_scale,
        amplitude=signal_variance,
    )
    covariance = kernel + noise_variance * np.eye(matrix.shape[0])
    cholesky = np.linalg.cholesky(covariance)
    dual = np.linalg.solve(cholesky.T, np.linalg.solve(cholesky, centered))
    return GaussianProcessModel(
        train_features=standardized,
        dual_coefficients=dual,
        cholesky_factor=cholesky,
        feature_mean=mean,
        feature_scale=scale,
        target_mean=target_mean,
        length_scale=float(length_scale),
        signal_variance=signal_variance,
        noise_variance=float(noise_variance),
    )


def fit_kmeans(
    features: np.ndarray,
    n_clusters: int,
    *,
    rng: np.random.Generator,
    max_iterations: int = 200,
    tolerance: float = 1e-7,
) -> KMeansModel:
    """Fit standardized k-means with explicit RNG and k-means++ seeding."""
    matrix = _feature_matrix(features)
    if isinstance(n_clusters, bool) or not 2 <= n_clusters < matrix.shape[0]:
        raise ValueError("n_clusters must lie between two and n_observations - 1")
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    if isinstance(max_iterations, bool) or max_iterations < 1:
        raise ValueError("max_iterations must be positive")
    standardized, mean, scale = _standardize(matrix)

    centers = [standardized[int(rng.integers(standardized.shape[0]))]]
    for _ in range(1, n_clusters):
        distance = np.min(
            np.sum((standardized[:, None, :] - np.asarray(centers)[None, :, :]) ** 2, axis=2),
            axis=1,
        )
        if float(distance.sum()) <= 0.0:
            remaining = np.setdiff1d(
                np.arange(standardized.shape[0]),
                np.unique(
                    [np.argmin(np.sum((standardized - center) ** 2, axis=1)) for center in centers]
                ),
            )
            centers.append(standardized[int(rng.choice(remaining))])
        else:
            centers.append(
                standardized[int(rng.choice(standardized.shape[0], p=distance / distance.sum()))]
            )
    center_array = np.asarray(centers)
    converged = False
    labels = np.zeros(matrix.shape[0], dtype=int)
    iterations = max_iterations
    for iteration in range(1, max_iterations + 1):
        distances = np.sum(
            (standardized[:, None, :] - center_array[None, :, :]) ** 2,
            axis=2,
        )
        labels = np.argmin(distances, axis=1)
        if np.unique(labels).size != n_clusters:
            raise ValueError(
                "k-means produced an empty cluster; use a different seed or fewer clusters"
            )
        updated = np.vstack(
            [standardized[labels == cluster].mean(axis=0) for cluster in range(n_clusters)]
        )
        if np.max(np.abs(updated - center_array)) <= tolerance:
            center_array = updated
            converged = True
            iterations = iteration
            break
        center_array = updated
    distances = np.sum((standardized - center_array[labels]) ** 2, axis=1)
    return KMeansModel(
        centers=center_array,
        feature_mean=mean,
        feature_scale=scale,
        labels=labels,
        inertia=float(distances.sum()),
        iterations=iterations,
        converged=converged,
    )


def feature_drift_report(
    reference_features: np.ndarray,
    current_features: np.ndarray,
    *,
    feature_names: tuple[str, ...] | None = None,
    n_bins: int = 10,
) -> FeatureDriftReport:
    """Compare periods with standardized mean differences and reference-bin PSI."""
    reference = _feature_matrix(reference_features)
    current = _feature_matrix(current_features, n_features=reference.shape[1])
    if isinstance(n_bins, bool) or not isinstance(n_bins, int) or n_bins < 3:
        raise ValueError("n_bins must be an integer of at least three")
    names = (
        tuple(f"x{index}" for index in range(reference.shape[1]))
        if feature_names is None
        else tuple(feature_names)
    )
    if len(names) != reference.shape[1] or len(set(names)) != len(names):
        raise ValueError("feature_names must be unique and match the feature columns")

    pooled_scale = np.sqrt(0.5 * (reference.var(axis=0) + current.var(axis=0)))
    pooled_scale = np.where(pooled_scale > np.finfo(float).eps, pooled_scale, 1.0)
    mean_difference = (current.mean(axis=0) - reference.mean(axis=0)) / pooled_scale
    psi = np.empty(reference.shape[1], dtype=float)
    quantiles = np.linspace(0.0, 1.0, n_bins + 1)
    for column in range(reference.shape[1]):
        interior = np.unique(np.quantile(reference[:, column], quantiles[1:-1]))
        edges = np.r_[-np.inf, interior, np.inf]
        reference_counts = np.histogram(reference[:, column], bins=edges)[0]
        current_counts = np.histogram(current[:, column], bins=edges)[0]
        reference_share = np.maximum(reference_counts / reference.shape[0], 1e-8)
        current_share = np.maximum(current_counts / current.shape[0], 1e-8)
        psi[column] = float(
            np.sum((current_share - reference_share) * np.log(current_share / reference_share))
        )
    return FeatureDriftReport(
        feature_names=names,
        standardized_mean_difference=mean_difference,
        population_stability_index=psi,
        maximum_absolute_mean_difference=float(np.max(np.abs(mean_difference))),
        maximum_population_stability_index=float(np.max(psi)),
    )


def split_conformal_interval(
    calibration_actual: np.ndarray,
    calibration_prediction: np.ndarray,
    test_prediction: np.ndarray,
    *,
    miscoverage: float = 0.1,
) -> ConformalInterval:
    """Construct a symmetric split-conformal interval.

    The finite-sample marginal guarantee requires exchangeability.  This helper
    computes the interval but does not claim that time-series observations meet
    that assumption.
    """
    actual = np.asarray(calibration_actual, dtype=float)
    calibration = np.asarray(calibration_prediction, dtype=float)
    test = np.asarray(test_prediction, dtype=float)
    if actual.ndim != 1 or calibration.shape != actual.shape or actual.size < 2:
        raise ValueError("calibration arrays must be equally sized with at least two rows")
    if test.ndim != 1 or test.size == 0:
        raise ValueError("test_prediction must be a non-empty one-dimensional array")
    if (
        not np.all(np.isfinite(actual))
        or not np.all(np.isfinite(calibration))
        or not np.all(np.isfinite(test))
    ):
        raise ValueError("conformal inputs must be finite")
    if not np.isfinite(miscoverage) or not 0.0 < miscoverage < 1.0:
        raise ValueError("miscoverage must lie in (0, 1)")

    residuals = np.sort(np.abs(actual - calibration))
    rank = min(int(np.ceil((residuals.size + 1) * (1.0 - miscoverage))), residuals.size)
    quantile = float(residuals[rank - 1])
    return ConformalInterval(
        lower=test - quantile,
        upper=test + quantile,
        residual_quantile=quantile,
        nominal_coverage=1.0 - float(miscoverage),
    )


__all__ = [
    "ConformalInterval",
    "DecisionStump",
    "FeatureDriftReport",
    "GaussianProcessModel",
    "GaussianProcessPrediction",
    "GradientBoostingModel",
    "KMeansModel",
    "KernelRidgeModel",
    "feature_drift_report",
    "fit_decision_stump",
    "fit_gaussian_process",
    "fit_gradient_boosting",
    "fit_kernel_ridge",
    "fit_kmeans",
    "split_conformal_interval",
]
