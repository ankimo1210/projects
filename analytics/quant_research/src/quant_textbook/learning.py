"""Leakage-resistant statistical-learning primitives for Stage 2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy.special import expit, logsumexp
from scipy.stats import spearmanr

from .treasury_data import DEFAULT_TENORS, TREASURY_METHOD_BREAK, audit_treasury_data


@dataclass(frozen=True)
class ForecastDataset:
    """Features known at prediction time and explicitly future targets."""

    features: np.ndarray
    regression_target: np.ndarray
    direction_target: np.ndarray
    prediction_dates: np.ndarray
    target_dates: np.ndarray
    feature_names: tuple[str, ...]
    target_name: str
    target_unit: str
    horizon_publications: int
    methodology_regime: np.ndarray
    availability_contract: str

    def __post_init__(self) -> None:
        features = np.asarray(self.features)
        target = np.asarray(self.regression_target)
        direction = np.asarray(self.direction_target)
        n_rows = features.shape[0] if features.ndim == 2 else -1
        if features.ndim != 2 or n_rows < 10:
            raise ValueError("features must be a two-dimensional array with at least ten rows")
        if features.shape[1] != len(self.feature_names):
            raise ValueError("feature_names must match the feature columns")
        if len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError("feature_names must be unique")
        if target.shape != (n_rows,) or direction.shape != (n_rows,):
            raise ValueError("targets must have one value per feature row")
        prediction_dates = np.asarray(self.prediction_dates, dtype="datetime64[ns]")
        target_dates = np.asarray(self.target_dates, dtype="datetime64[ns]")
        if prediction_dates.shape != (n_rows,):
            raise ValueError("prediction_dates must have one value per feature row")
        if target_dates.shape != (n_rows,):
            raise ValueError("target_dates must have one value per feature row")
        if np.any(np.isnat(prediction_dates)) or np.any(np.isnat(target_dates)):
            raise ValueError("prediction_dates and target_dates must not contain NaT")
        if not np.all(target_dates > prediction_dates):
            raise ValueError("every target date must be later than its prediction date")
        crosses_methodology_break = (prediction_dates < TREASURY_METHOD_BREAK.to_datetime64()) & (
            target_dates >= TREASURY_METHOD_BREAK.to_datetime64()
        )
        if np.any(crosses_methodology_break):
            raise ValueError("targets must not cross the official methodology break")
        if np.asarray(self.methodology_regime).shape != (n_rows,):
            raise ValueError("methodology_regime must have one value per feature row")
        if not np.all(np.isfinite(features)) or not np.all(np.isfinite(target)):
            raise ValueError("features and regression_target must be finite")
        if not np.all(np.isin(direction, [0, 1])):
            raise ValueError("direction_target must contain only zero and one")
        if (
            isinstance(self.horizon_publications, bool)
            or not isinstance(self.horizon_publications, int)
            or self.horizon_publications < 1
        ):
            raise ValueError("horizon_publications must be a positive integer")


@dataclass(frozen=True)
class TemporalSplit:
    """Chronological indices with a purged gap before later partitions."""

    train: np.ndarray
    validation: np.ndarray
    test: np.ndarray
    gap: int


@dataclass(frozen=True)
class LinearModel:
    """Standardized linear/elastic-net model with raw-input prediction."""

    coefficients: np.ndarray
    intercept: float
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    alpha: float
    l1_ratio: float
    iterations: int
    converged: bool
    objective: float

    def predict(self, features: np.ndarray) -> np.ndarray:
        matrix = _as_feature_matrix(features, n_features=self.coefficients.size)
        standardized = (matrix - self.feature_mean) / self.feature_scale
        return self.intercept + standardized @ self.coefficients


@dataclass(frozen=True)
class LogisticModel:
    """Ridge-logistic model used for direction and Platt calibration."""

    coefficients: np.ndarray
    intercept: float
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    alpha: float
    iterations: int
    converged: bool
    gradient_norm: float

    def decision_function(self, features: np.ndarray) -> np.ndarray:
        matrix = _as_feature_matrix(features, n_features=self.coefficients.size)
        standardized = (matrix - self.feature_mean) / self.feature_scale
        return self.intercept + standardized @ self.coefficients

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        return expit(self.decision_function(features))


@dataclass(frozen=True)
class GaussianClassifier:
    """LDA, QDA, or Gaussian-naive-Bayes parameters."""

    kind: Literal["lda", "qda", "naive_bayes"]
    classes: np.ndarray
    means: np.ndarray
    covariances: np.ndarray
    log_priors: np.ndarray
    regularization: float
    feature_mean: np.ndarray
    feature_scale: np.ndarray


@dataclass(frozen=True)
class RegressionMetrics:
    rmse: float
    mae: float
    rank_correlation: float


@dataclass(frozen=True)
class ClassificationMetrics:
    log_loss: float
    brier_score: float
    accuracy: float
    expected_calibration_error: float


def _as_feature_matrix(features: np.ndarray, *, n_features: int | None = None) -> np.ndarray:
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


def _as_target(target: np.ndarray, *, n_rows: int) -> np.ndarray:
    vector = np.asarray(target, dtype=float)
    if vector.shape != (n_rows,) or not np.all(np.isfinite(vector)):
        raise ValueError("target must be finite with one value per feature row")
    return vector


def _standardize(features: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = features.mean(axis=0)
    scale = features.std(axis=0, ddof=0)
    scale = np.where(scale > np.finfo(float).eps * np.maximum(np.abs(mean), 1.0), scale, 1.0)
    return (features - mean) / scale, mean, scale


def make_treasury_forecast_dataset(
    treasury_rates: pd.DataFrame,
    *,
    target_tenor: str = "10y",
    horizon_publications: int = 1,
    lags: tuple[int, ...] = (1, 2, 5),
    volatility_window: int = 20,
) -> ForecastDataset:
    """Create a real-data forecast table with features available after day-t publication."""
    quality = audit_treasury_data(treasury_rates)
    if not quality.accepted:
        raise ValueError("treasury_rates failed the date-by-tenor quality contract")
    if target_tenor not in DEFAULT_TENORS:
        raise ValueError(f"target_tenor must be one of {DEFAULT_TENORS}")
    if (
        isinstance(horizon_publications, bool)
        or not isinstance(horizon_publications, int)
        or horizon_publications < 1
    ):
        raise ValueError("horizon_publications must be a positive integer")
    if not lags or any(
        isinstance(lag, bool) or not isinstance(lag, int) or lag < 1 for lag in lags
    ):
        raise ValueError("lags must contain positive integers")
    if len(set(lags)) != len(lags):
        raise ValueError("lags must be unique")
    if isinstance(volatility_window, bool) or volatility_window < 3:
        raise ValueError("volatility_window must be at least three")

    frame = treasury_rates.loc[:, ["date", *DEFAULT_TENORS]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame = frame.sort_values("date").reset_index(drop=True)
    yields = frame.loc[:, DEFAULT_TENORS].astype(float)

    factors = pd.DataFrame(index=frame.index)
    factors["curve_level_pct"] = yields.loc[:, ["2y", "5y", "10y", "30y"]].mean(axis=1)
    factors["curve_slope_pct"] = yields["10y"] - yields["2y"]
    factors["curve_curvature_pct"] = 2.0 * yields["5y"] - yields["2y"] - yields["10y"]

    features = pd.DataFrame(index=frame.index)
    for tenor in DEFAULT_TENORS:
        features[f"yield_{tenor}_pct"] = yields[tenor]
    features = pd.concat([features, factors], axis=1)

    target_change = yields[target_tenor].diff() * 100.0
    factor_changes = factors.diff() * 100.0
    for lag in lags:
        features[f"{target_tenor}_change_lag{lag}_bp"] = target_change.shift(lag - 1)
    for name in factor_changes:
        features[f"{name.removesuffix('_pct')}_change_lag1_bp"] = factor_changes[name]
    features[f"{target_tenor}_rolling_vol_{volatility_window}d_bp"] = target_change.rolling(
        volatility_window
    ).std(ddof=1)
    day_of_week = frame["date"].dt.dayofweek.to_numpy(dtype=float)
    features["day_of_week_sin"] = np.sin(2.0 * np.pi * day_of_week / 5.0)
    features["day_of_week_cos"] = np.cos(2.0 * np.pi * day_of_week / 5.0)

    future_change_bp = (
        yields[target_tenor].shift(-horizon_publications) - yields[target_tenor]
    ) * 100.0
    target_dates = frame["date"].shift(-horizon_publications)
    same_methodology = (frame["date"] < TREASURY_METHOD_BREAK) == (
        target_dates < TREASURY_METHOD_BREAK
    )
    complete = (
        features.notna().all(axis=1)
        & future_change_bp.notna()
        & target_dates.notna()
        & same_methodology
    )

    selected_dates = frame.loc[complete, "date"].to_numpy(dtype="datetime64[ns]")
    selected_target_dates = target_dates.loc[complete].to_numpy(dtype="datetime64[ns]")
    selected_target = future_change_bp.loc[complete].to_numpy(dtype=float)
    regimes = np.where(
        selected_dates >= TREASURY_METHOD_BREAK.to_datetime64(),
        "monotone-convex",
        "hermite-spline",
    )
    return ForecastDataset(
        features=features.loc[complete].to_numpy(dtype=float),
        regression_target=selected_target,
        direction_target=(selected_target > 0.0).astype(int),
        prediction_dates=selected_dates,
        target_dates=selected_target_dates,
        feature_names=tuple(features.columns),
        target_name=f"next_{horizon_publications}_publication_{target_tenor}_change",
        target_unit="basis points",
        horizon_publications=horizon_publications,
        methodology_regime=regimes,
        availability_contract=(
            "features are usable only after the official day-t curve is published, "
            "usually by 18:00 America/New_York; publication can be delayed"
        ),
    )


def chronological_split(
    n_observations: int,
    *,
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
    gap: int = 1,
) -> TemporalSplit:
    """Create one train/validation/test split without random shuffling."""
    if (
        isinstance(n_observations, bool)
        or not isinstance(n_observations, int)
        or n_observations < 30
    ):
        raise ValueError("n_observations must be an integer of at least 30")
    if not 0.0 < train_fraction < 1.0 or not 0.0 < validation_fraction < 1.0:
        raise ValueError("train_fraction and validation_fraction must lie in (0, 1)")
    if train_fraction + validation_fraction >= 0.95:
        raise ValueError("at least five percent of observations must remain for test")
    if isinstance(gap, bool) or not isinstance(gap, int) or gap < 0:
        raise ValueError("gap must be a non-negative integer")

    train_boundary = int(np.floor(n_observations * train_fraction))
    validation_boundary = int(np.floor(n_observations * (train_fraction + validation_fraction)))
    train = np.arange(0, train_boundary - gap, dtype=int)
    validation = np.arange(train_boundary, validation_boundary - gap, dtype=int)
    test = np.arange(validation_boundary, n_observations, dtype=int)
    if min(train.size, validation.size, test.size) == 0:
        raise ValueError("split fractions and gap leave an empty partition")
    return TemporalSplit(train=train, validation=validation, test=test, gap=gap)


def expanding_window_splits(
    n_observations: int,
    *,
    initial_train_size: int,
    test_size: int,
    step: int | None = None,
    gap: int = 1,
) -> tuple[tuple[np.ndarray, np.ndarray], ...]:
    """Return deterministic expanding-window folds with a purged boundary."""
    values = (n_observations, initial_train_size, test_size, gap)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise ValueError("window sizes and gap must be integers")
    if n_observations < 10 or initial_train_size < 5 or test_size < 1 or gap < 0:
        raise ValueError("invalid expanding-window dimensions")
    actual_step = test_size if step is None else step
    if isinstance(actual_step, bool) or not isinstance(actual_step, int) or actual_step < 1:
        raise ValueError("step must be a positive integer")

    folds: list[tuple[np.ndarray, np.ndarray]] = []
    train_end = initial_train_size
    while train_end + gap + test_size <= n_observations:
        train = np.arange(0, train_end, dtype=int)
        test = np.arange(train_end + gap, train_end + gap + test_size, dtype=int)
        folds.append((train, test))
        train_end += actual_step
    if not folds:
        raise ValueError("window configuration produces no folds")
    return tuple(folds)


def fit_elastic_net(
    features: np.ndarray,
    target: np.ndarray,
    *,
    alpha: float = 0.0,
    l1_ratio: float = 0.0,
    max_iterations: int = 10_000,
    tolerance: float = 1e-9,
) -> LinearModel:
    """Fit OLS, ridge, lasso, or elastic net by a transparent coordinate solver."""
    matrix = _as_feature_matrix(features)
    vector = _as_target(target, n_rows=matrix.shape[0])
    if not np.isfinite(alpha) or alpha < 0.0:
        raise ValueError("alpha must be finite and non-negative")
    if not np.isfinite(l1_ratio) or not 0.0 <= l1_ratio <= 1.0:
        raise ValueError("l1_ratio must lie in [0, 1]")
    if isinstance(max_iterations, bool) or max_iterations < 1:
        raise ValueError("max_iterations must be a positive integer")
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("tolerance must be strictly positive")

    standardized, feature_mean, feature_scale = _standardize(matrix)
    intercept = float(vector.mean())
    centered_target = vector - intercept
    n_rows, n_features = standardized.shape

    if l1_ratio == 0.0:
        penalty_rows = np.sqrt(n_rows * alpha) * np.eye(n_features)
        augmented_features = np.vstack([standardized, penalty_rows])
        augmented_target = np.r_[centered_target, np.zeros(n_features)]
        coefficients = np.linalg.lstsq(
            augmented_features,
            augmented_target,
            rcond=None,
        )[0]
        iterations = 1
        converged = True
    else:
        coefficients = np.zeros(n_features, dtype=float)
        residual = centered_target.copy()
        converged = False
        iterations = max_iterations
        l1_penalty = alpha * l1_ratio
        l2_penalty = alpha * (1.0 - l1_ratio)
        column_norms = np.sum(standardized**2, axis=0) / n_rows
        for iteration in range(1, max_iterations + 1):
            previous = coefficients.copy()
            for column in range(n_features):
                residual += standardized[:, column] * coefficients[column]
                partial = float(standardized[:, column] @ residual / n_rows)
                coefficients[column] = (
                    np.sign(partial)
                    * max(abs(partial) - l1_penalty, 0.0)
                    / (column_norms[column] + l2_penalty)
                )
                residual -= standardized[:, column] * coefficients[column]
            if np.max(np.abs(coefficients - previous)) <= tolerance * max(
                1.0, np.max(np.abs(previous))
            ):
                converged = True
                iterations = iteration
                break

    residual = centered_target - standardized @ coefficients
    objective = float(
        0.5 * np.mean(residual**2)
        + alpha
        * (
            l1_ratio * np.sum(np.abs(coefficients))
            + 0.5 * (1.0 - l1_ratio) * np.sum(coefficients**2)
        )
    )
    return LinearModel(
        coefficients=coefficients,
        intercept=intercept,
        feature_mean=feature_mean,
        feature_scale=feature_scale,
        alpha=float(alpha),
        l1_ratio=float(l1_ratio),
        iterations=iterations,
        converged=converged,
        objective=objective,
    )


def fit_ridge(features: np.ndarray, target: np.ndarray, *, alpha: float = 1.0) -> LinearModel:
    return fit_elastic_net(features, target, alpha=alpha, l1_ratio=0.0)


def fit_lasso(features: np.ndarray, target: np.ndarray, *, alpha: float = 0.1) -> LinearModel:
    return fit_elastic_net(features, target, alpha=alpha, l1_ratio=1.0)


def fit_logistic_ridge(
    features: np.ndarray,
    target: np.ndarray,
    *,
    alpha: float = 1e-3,
    max_iterations: int = 100,
    tolerance: float = 1e-8,
) -> LogisticModel:
    """Fit binary logistic regression by damped Newton iterations."""
    matrix = _as_feature_matrix(features)
    vector = _as_target(target, n_rows=matrix.shape[0])
    if not np.all(np.isin(vector, [0.0, 1.0])) or np.unique(vector).size != 2:
        raise ValueError("target must contain both binary classes")
    if not np.isfinite(alpha) or alpha < 0.0:
        raise ValueError("alpha must be finite and non-negative")

    standardized, feature_mean, feature_scale = _standardize(matrix)
    design = np.column_stack([np.ones(matrix.shape[0]), standardized])
    parameters = np.zeros(design.shape[1], dtype=float)
    parameters[0] = np.log(vector.mean() / (1.0 - vector.mean()))
    penalty = np.diag(np.r_[0.0, np.full(matrix.shape[1], alpha)])
    converged = False
    gradient_norm = np.inf
    iterations = max_iterations

    def objective(candidate: np.ndarray) -> float:
        logits = design @ candidate
        return float(
            np.mean(np.logaddexp(0.0, logits) - vector * logits)
            + 0.5 * alpha * np.sum(candidate[1:] ** 2)
        )

    for iteration in range(1, max_iterations + 1):
        logits = design @ parameters
        probabilities = expit(logits)
        gradient = design.T @ (probabilities - vector) / matrix.shape[0] + penalty @ parameters
        gradient_norm = float(np.max(np.abs(gradient)))
        if gradient_norm <= tolerance:
            converged = True
            iterations = iteration - 1
            break
        weights = np.maximum(probabilities * (1.0 - probabilities), 1e-10)
        hessian = design.T @ (weights[:, None] * design) / matrix.shape[0] + penalty
        step = np.linalg.solve(hessian, gradient)
        current_objective = objective(parameters)
        step_scale = 1.0
        while step_scale >= 2.0**-20:
            candidate = parameters - step_scale * step
            if objective(candidate) <= current_objective:
                parameters = candidate
                break
            step_scale *= 0.5
        else:
            break
    else:
        logits = design @ parameters
        gradient = design.T @ (expit(logits) - vector) / matrix.shape[0] + penalty @ parameters
        gradient_norm = float(np.max(np.abs(gradient)))

    if not converged and gradient_norm <= max(tolerance, np.sqrt(np.finfo(float).eps)):
        converged = True
    return LogisticModel(
        coefficients=parameters[1:],
        intercept=float(parameters[0]),
        feature_mean=feature_mean,
        feature_scale=feature_scale,
        alpha=float(alpha),
        iterations=iterations,
        converged=converged,
        gradient_norm=gradient_norm,
    )


def fit_gaussian_classifier(
    features: np.ndarray,
    target: np.ndarray,
    *,
    kind: Literal["lda", "qda", "naive_bayes"] = "lda",
    regularization: float = 1e-6,
) -> GaussianClassifier:
    """Fit a two-class Gaussian generative classifier."""
    matrix = _as_feature_matrix(features)
    vector = _as_target(target, n_rows=matrix.shape[0])
    classes = np.unique(vector)
    if classes.size != 2:
        raise ValueError("target must contain exactly two classes")
    if kind not in ("lda", "qda", "naive_bayes"):
        raise ValueError("kind must be 'lda', 'qda', or 'naive_bayes'")
    if not np.isfinite(regularization) or regularization <= 0.0:
        raise ValueError("regularization must be strictly positive")

    standardized, feature_mean, feature_scale = _standardize(matrix)
    means = np.vstack([standardized[vector == label].mean(axis=0) for label in classes])
    priors = np.array([(vector == label).mean() for label in classes])
    class_covariances = []
    for label, mean in zip(classes, means, strict=True):
        centered = standardized[vector == label] - mean
        covariance = centered.T @ centered / max(centered.shape[0] - 1, 1)
        if kind == "naive_bayes":
            covariance = np.diag(np.diag(covariance))
        covariance += regularization * np.eye(matrix.shape[1])
        class_covariances.append(covariance)
    if kind == "lda":
        pooled = sum(
            (np.sum(vector == label) - 1) * covariance
            for label, covariance in zip(classes, class_covariances, strict=True)
        ) / (matrix.shape[0] - classes.size)
        covariances = np.stack([pooled, pooled])
    else:
        covariances = np.stack(class_covariances)
    return GaussianClassifier(
        kind=kind,
        classes=classes,
        means=means,
        covariances=covariances,
        log_priors=np.log(priors),
        regularization=float(regularization),
        feature_mean=feature_mean,
        feature_scale=feature_scale,
    )


def predict_gaussian_proba(model: GaussianClassifier, features: np.ndarray) -> np.ndarray:
    matrix = _as_feature_matrix(features, n_features=model.means.shape[1])
    standardized = (matrix - model.feature_mean) / model.feature_scale
    scores = np.empty((matrix.shape[0], model.classes.size), dtype=float)
    for class_index in range(model.classes.size):
        covariance = model.covariances[class_index]
        sign, log_determinant = np.linalg.slogdet(covariance)
        if sign <= 0.0:
            raise ValueError("classifier covariance must be positive definite")
        centered = standardized - model.means[class_index]
        solved = np.linalg.solve(covariance, centered.T).T
        scores[:, class_index] = (
            model.log_priors[class_index]
            - 0.5 * log_determinant
            - 0.5 * np.sum(centered * solved, axis=1)
        )
    probabilities = np.exp(scores - logsumexp(scores, axis=1, keepdims=True))
    positive_index = int(np.argmax(model.classes))
    return probabilities[:, positive_index]


def knn_predict_proba(
    train_features: np.ndarray,
    train_target: np.ndarray,
    test_features: np.ndarray,
    *,
    n_neighbors: int = 15,
) -> np.ndarray:
    train = _as_feature_matrix(train_features)
    target = _as_target(train_target, n_rows=train.shape[0])
    test = _as_feature_matrix(test_features, n_features=train.shape[1])
    if not np.all(np.isin(target, [0.0, 1.0])):
        raise ValueError("train_target must be binary")
    if isinstance(n_neighbors, bool) or not 1 <= n_neighbors <= train.shape[0]:
        raise ValueError("n_neighbors must lie between one and the training size")
    standardized_train, mean, scale = _standardize(train)
    standardized_test = (test - mean) / scale
    probabilities = np.empty(test.shape[0], dtype=float)
    for row_index, row in enumerate(standardized_test):
        distances = np.sum((standardized_train - row) ** 2, axis=1)
        neighbors = np.argpartition(distances, n_neighbors - 1)[:n_neighbors]
        probabilities[row_index] = target[neighbors].mean()
    return probabilities


def calibration_table(
    probabilities: np.ndarray, target: np.ndarray, *, n_bins: int = 10
) -> pd.DataFrame:
    probability = np.asarray(probabilities, dtype=float)
    outcome = np.asarray(target, dtype=float)
    if probability.ndim != 1 or outcome.shape != probability.shape or probability.size == 0:
        raise ValueError("probabilities and target must be equally sized one-dimensional arrays")
    if not np.all(np.isfinite(probability)) or not np.all(
        (0.0 <= probability) & (probability <= 1.0)
    ):
        raise ValueError("probabilities must be finite and lie in [0, 1]")
    if not np.all(np.isin(outcome, [0.0, 1.0])):
        raise ValueError("target must be binary")
    if isinstance(n_bins, bool) or not isinstance(n_bins, int) or n_bins < 2:
        raise ValueError("n_bins must be an integer of at least two")

    bin_index = np.minimum((probability * n_bins).astype(int), n_bins - 1)
    rows = []
    for index in range(n_bins):
        selected = bin_index == index
        if not np.any(selected):
            continue
        rows.append(
            {
                "bin": index,
                "count": int(np.sum(selected)),
                "mean_probability": float(probability[selected].mean()),
                "observed_frequency": float(outcome[selected].mean()),
            }
        )
    return pd.DataFrame(rows)


def regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> RegressionMetrics:
    actual_array = np.asarray(actual, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    if (
        actual_array.ndim != 1
        or predicted_array.shape != actual_array.shape
        or actual_array.size == 0
    ):
        raise ValueError("actual and predicted must be equally sized one-dimensional arrays")
    if not np.all(np.isfinite(actual_array)) or not np.all(np.isfinite(predicted_array)):
        raise ValueError("actual and predicted must be finite")
    if np.ptp(actual_array) == 0.0 or np.ptp(predicted_array) == 0.0:
        correlation = 0.0
    else:
        correlation = spearmanr(actual_array, predicted_array).statistic
    return RegressionMetrics(
        rmse=float(np.sqrt(np.mean((actual_array - predicted_array) ** 2))),
        mae=float(np.mean(np.abs(actual_array - predicted_array))),
        rank_correlation=float(correlation) if np.isfinite(correlation) else 0.0,
    )


def classification_metrics(
    actual: np.ndarray, probabilities: np.ndarray, *, n_bins: int = 10
) -> ClassificationMetrics:
    outcome = np.asarray(actual, dtype=float)
    probability = np.asarray(probabilities, dtype=float)
    table = calibration_table(probability, outcome, n_bins=n_bins)
    clipped = np.clip(probability, 1e-12, 1.0 - 1e-12)
    ece = np.sum(
        table["count"]
        / outcome.size
        * np.abs(table["mean_probability"] - table["observed_frequency"])
    )
    return ClassificationMetrics(
        log_loss=float(-np.mean(outcome * np.log(clipped) + (1.0 - outcome) * np.log1p(-clipped))),
        brier_score=float(np.mean((probability - outcome) ** 2)),
        accuracy=float(np.mean((probability >= 0.5) == outcome)),
        expected_calibration_error=float(ece),
    )


__all__ = [
    "ClassificationMetrics",
    "ForecastDataset",
    "GaussianClassifier",
    "LinearModel",
    "LogisticModel",
    "RegressionMetrics",
    "TemporalSplit",
    "calibration_table",
    "chronological_split",
    "classification_metrics",
    "expanding_window_splits",
    "fit_elastic_net",
    "fit_gaussian_classifier",
    "fit_lasso",
    "fit_logistic_ridge",
    "fit_ridge",
    "knn_predict_proba",
    "make_treasury_forecast_dataset",
    "predict_gaussian_proba",
    "regression_metrics",
]
