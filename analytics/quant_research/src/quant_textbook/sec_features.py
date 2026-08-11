"""Leakage-aware feature helpers for the B9 SEC teaching chapters.

The bundled teaching fixture contains development-partition rows only.  It is
not the pre-registered candidate tournament and deliberately contains neither
raw filing text nor the locked outer-test rows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import lsqr


@dataclass(frozen=True)
class SECTeachingFixture:
    """Small, real-data-derived fixture for deterministic B9 laboratories."""

    row_ids: tuple[str, ...]
    entity_ids: tuple[str, ...]
    target_available_dates: np.ndarray
    partitions: np.ndarray
    numeric_feature_names: tuple[str, ...]
    numeric_features: np.ndarray
    baseline_prediction_contract: dict[str, object]
    baseline_predictions: dict[str, np.ndarray]
    token_hashes: np.ndarray
    targets: np.ndarray
    document_sha256: tuple[str, ...]
    provenance: dict[str, str]

    @property
    def training_mask(self) -> np.ndarray:
        return self.partitions == "inner_train"

    @property
    def validation_mask(self) -> np.ndarray:
        return self.partitions == "inner_validation"


@dataclass(frozen=True)
class NumericPreprocessor:
    """Training-only median imputation and standardization parameters."""

    medians: np.ndarray
    means: np.ndarray
    scales: np.ndarray

    def transform(self, features: np.ndarray) -> np.ndarray:
        values = _matrix(features, name="features", allow_nan=True)
        if values.shape[1] != self.medians.size:
            raise ValueError("features have an incompatible column count")
        missing = np.isnan(values)
        imputed = np.where(missing, self.medians, values)
        standardized = (imputed - self.means) / self.scales
        return np.column_stack([standardized, missing.astype(float)])


@dataclass(frozen=True)
class HashedTfidfModel:
    """Training-fitted vocabulary and IDF over lossy many-to-one token hashes."""

    vocabulary: np.ndarray
    inverse_document_frequency: np.ndarray

    def transform(self, token_hashes: np.ndarray) -> sparse.csr_matrix:
        tokens = _token_matrix(token_hashes)
        lookup = {int(token): index for index, token in enumerate(self.vocabulary)}
        rows: list[int] = []
        columns: list[int] = []
        values: list[float] = []
        for row_index, sequence in enumerate(tokens):
            counts: dict[int, int] = {}
            for token in sequence:
                column = lookup.get(int(token))
                if column is not None:
                    counts[column] = counts.get(column, 0) + 1
            for column, count in counts.items():
                rows.append(row_index)
                columns.append(column)
                values.append(1.0 + np.log(float(count)))
        matrix = sparse.csr_matrix(
            (values, (rows, columns)), shape=(tokens.shape[0], self.vocabulary.size)
        )
        matrix = matrix.multiply(self.inverse_document_frequency)
        norms = np.sqrt(matrix.multiply(matrix).sum(axis=1)).A1
        norms = np.where(norms > 0.0, norms, 1.0)
        return sparse.diags(1.0 / norms) @ matrix


@dataclass(frozen=True)
class RidgePrediction:
    """Sparse-compatible ridge coefficients and predictions."""

    intercept: float
    coefficients: np.ndarray
    ridge: float

    def predict(self, features: np.ndarray | sparse.spmatrix) -> np.ndarray:
        if sparse.issparse(features):
            matrix = sparse.csr_matrix(features, dtype=float)
        else:
            matrix = sparse.csr_matrix(_matrix(features, name="features"))
        if matrix.shape[1] != self.coefficients.size:
            raise ValueError("features have an incompatible column count")
        prediction = matrix @ self.coefficients + self.intercept
        return np.asarray(prediction).ravel()


def _resource_path(name: str) -> Path:
    return Path(str(files("quant_textbook").joinpath("resources", name)))


def _matrix(values: np.ndarray, *, name: str, allow_nan: bool = False) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError(f"{name} must be a non-empty two-dimensional array")
    if np.isinf(matrix).any() or (not allow_nan and np.isnan(matrix).any()):
        raise ValueError(f"{name} must contain valid finite values")
    return matrix


def _token_matrix(values: np.ndarray) -> np.ndarray:
    tokens = np.asarray(values)
    if tokens.ndim != 2 or tokens.shape[0] == 0 or tokens.shape[1] == 0:
        raise ValueError("token_hashes must be a non-empty two-dimensional array")
    if not np.issubdtype(tokens.dtype, np.integer) or (tokens <= 0).any():
        raise ValueError("token_hashes must contain strictly positive integers")
    return tokens.astype(np.int64, copy=False)


def load_sec_teaching_fixture() -> SECTeachingFixture:
    """Load and integrity-check the bundled development-only SEC fixture."""

    data_path = _resource_path("sec_b9_teaching_fixture.json")
    manifest_path = _resource_path("sec_b9_teaching_fixture.manifest.json")
    if not data_path.exists() or not manifest_path.exists():
        raise FileNotFoundError("bundled SEC teaching fixture is missing")
    payload_bytes = data_path.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256(payload_bytes).hexdigest() != manifest.get("fixture_sha256"):
        raise ValueError("SEC teaching fixture hash does not match its manifest")
    if manifest.get("schema_version") != "sec-b9-teaching-fixture-v1":
        raise ValueError("SEC teaching fixture manifest has an unsupported schema")
    payload = json.loads(payload_bytes)
    if payload.get("schema_version") != "sec-b9-teaching-fixture-v1":
        raise ValueError("SEC teaching fixture has an unsupported schema")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("SEC teaching fixture contains no rows")
    baseline_contract = payload.get("baseline_prediction_contract")
    expected_baselines = ("zero", "pooled_drift", "seasonal", "company_mean")
    if (
        not isinstance(baseline_contract, dict)
        or tuple(baseline_contract.get("names", ())) != expected_baselines
    ):
        raise ValueError("SEC teaching fixture baseline contract is inconsistent")
    if (
        baseline_contract.get("training_partition") != "full 1504-row inner training partition"
        or baseline_contract.get("locked_outer_used") is not False
    ):
        raise ValueError("SEC teaching fixture baseline partition is inconsistent")
    feature_names = tuple(payload["numeric_feature_names"])
    fixture = SECTeachingFixture(
        row_ids=tuple(str(row["row_id"]) for row in rows),
        entity_ids=tuple(str(row["entity_id"]) for row in rows),
        target_available_dates=np.asarray(
            [row["target_available_date"] for row in rows], dtype="datetime64[D]"
        ),
        partitions=np.asarray([row["partition"] for row in rows], dtype=str),
        numeric_feature_names=feature_names,
        numeric_features=np.asarray([row["numeric_features"] for row in rows], dtype=float),
        baseline_prediction_contract=baseline_contract,
        baseline_predictions={
            name: np.asarray([row["baseline_predictions"][name] for row in rows], dtype=float)
            for name in expected_baselines
        },
        token_hashes=np.asarray([row["token_hashes"] for row in rows], dtype=np.int64),
        targets=np.asarray([row["target"] for row in rows], dtype=float),
        document_sha256=tuple(str(row["document_sha256"]) for row in rows),
        provenance={str(key): str(value) for key, value in payload["provenance"].items()},
    )
    n_rows = len(rows)
    if fixture.numeric_features.shape != (n_rows, len(feature_names)):
        raise ValueError("SEC teaching fixture numeric shape is inconsistent")
    _token_matrix(fixture.token_hashes)
    if not np.isfinite(fixture.targets).all():
        raise ValueError("SEC teaching fixture targets must be finite")
    if any(
        prediction.shape != (n_rows,) or not np.isfinite(prediction).all()
        for prediction in fixture.baseline_predictions.values()
    ):
        raise ValueError("SEC teaching fixture baseline predictions must be finite")
    if set(fixture.partitions) != {"inner_train", "inner_validation"}:
        raise ValueError("SEC teaching fixture may contain only inner partitions")
    if len(set(fixture.row_ids)) != n_rows:
        raise ValueError("SEC teaching fixture row identifiers must be unique")
    if any(len(value) != 64 for value in fixture.document_sha256):
        raise ValueError("SEC teaching fixture document hashes are malformed")
    return fixture


def fit_numeric_preprocessor(
    features: np.ndarray, training_mask: np.ndarray
) -> NumericPreprocessor:
    """Fit imputation and scaling using training rows only."""

    values = _matrix(features, name="features", allow_nan=True)
    mask = np.asarray(training_mask, dtype=bool)
    if mask.shape != (values.shape[0],) or not mask.any():
        raise ValueError("training_mask must select at least one row")
    training = values[mask]
    if np.isnan(training).all(axis=0).any():
        raise ValueError("every feature needs at least one observed training value")
    medians = np.nanmedian(training, axis=0)
    imputed = np.where(np.isnan(training), medians, training)
    means = imputed.mean(axis=0)
    scales = imputed.std(axis=0, ddof=0)
    scales = np.where(scales > 0.0, scales, 1.0)
    return NumericPreprocessor(medians=medians, means=means, scales=scales)


def fit_hashed_tfidf(
    token_hashes: np.ndarray,
    training_mask: np.ndarray,
    *,
    maximum_features: int = 512,
    minimum_document_frequency: int = 2,
) -> HashedTfidfModel:
    """Fit vocabulary ranking and IDF exclusively on selected training rows."""

    tokens = _token_matrix(token_hashes)
    mask = np.asarray(training_mask, dtype=bool)
    if mask.shape != (tokens.shape[0],) or not mask.any():
        raise ValueError("training_mask must select at least one row")
    if (
        isinstance(maximum_features, bool)
        or not isinstance(maximum_features, int)
        or maximum_features <= 0
    ):
        raise ValueError("maximum_features must be a positive integer")
    if (
        isinstance(minimum_document_frequency, bool)
        or not isinstance(minimum_document_frequency, int)
        or minimum_document_frequency <= 0
    ):
        raise ValueError("minimum_document_frequency must be a positive integer")
    document_frequency: dict[int, int] = {}
    for sequence in tokens[mask]:
        for token in np.unique(sequence):
            document_frequency[int(token)] = document_frequency.get(int(token), 0) + 1
    eligible = [
        (token, frequency)
        for token, frequency in document_frequency.items()
        if frequency >= minimum_document_frequency
    ]
    eligible.sort(key=lambda item: (-item[1], item[0]))
    selected = eligible[: int(maximum_features)]
    if not selected:
        raise ValueError("no token satisfies the document-frequency contract")
    vocabulary = np.asarray([token for token, _ in selected], dtype=np.int64)
    frequency = np.asarray([frequency for _, frequency in selected], dtype=float)
    idf = np.log((1.0 + mask.sum()) / (1.0 + frequency)) + 1.0
    return HashedTfidfModel(vocabulary=vocabulary, inverse_document_frequency=idf)


def fit_sparse_ridge(
    features: np.ndarray | sparse.spmatrix,
    target: np.ndarray,
    *,
    ridge: float,
) -> RidgePrediction:
    """Fit an intercept-unpenalized ridge model without densifying features."""

    if not np.isfinite(ridge) or ridge < 0.0:
        raise ValueError("ridge must be finite and nonnegative")
    matrix = sparse.csr_matrix(features, dtype=float)
    response = np.asarray(target, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError("features must be a non-empty matrix")
    if not np.isfinite(matrix.data).all():
        raise ValueError("features must contain finite values")
    if response.shape != (matrix.shape[0],) or not np.isfinite(response).all():
        raise ValueError("target must be finite with one value per row")
    design = sparse.hstack([sparse.csr_matrix(np.ones((matrix.shape[0], 1))), matrix], format="csr")
    if ridge == 0.0:
        solution = lsqr(design, response, atol=1e-10, btol=1e-10)[0]
    else:
        penalty = sparse.diags(
            np.concatenate([[0.0], np.full(matrix.shape[1], np.sqrt(ridge))]),
            format="csr",
        )
        augmented = sparse.vstack([design, penalty], format="csr")
        augmented_target = np.concatenate([response, np.zeros(matrix.shape[1] + 1)])
        solution = lsqr(augmented, augmented_target, atol=1e-10, btol=1e-10)[0]
    intercept = float(solution[0])
    coefficients = solution[1:]
    return RidgePrediction(
        intercept=intercept,
        coefficients=np.asarray(coefficients, dtype=float),
        ridge=float(ridge),
    )


def regression_error_table(
    actual: np.ndarray, predicted: np.ndarray, entity_ids: tuple[str, ...] | np.ndarray
) -> dict[str, float]:
    """Return row MAE/median-AE/RMSE and equal-company macro MAE."""

    observed = np.asarray(actual, dtype=float)
    fitted = np.asarray(predicted, dtype=float)
    entities = np.asarray(entity_ids, dtype=str)
    if observed.shape != fitted.shape or observed.ndim != 1 or entities.shape != observed.shape:
        raise ValueError("actual, predicted, and entity_ids must have one matching dimension")
    if not np.isfinite(observed).all() or not np.isfinite(fitted).all():
        raise ValueError("actual and predicted must be finite")
    absolute = np.abs(observed - fitted)
    company_errors = [absolute[entities == entity].mean() for entity in np.unique(entities)]
    return {
        "mae": float(absolute.mean()),
        "median_absolute_error": float(np.median(absolute)),
        "rmse": float(np.sqrt(np.mean((observed - fitted) ** 2))),
        "company_macro_mae": float(np.mean(company_errors)),
    }


__all__ = [
    "HashedTfidfModel",
    "NumericPreprocessor",
    "RidgePrediction",
    "SECTeachingFixture",
    "fit_hashed_tfidf",
    "fit_numeric_preprocessor",
    "fit_sparse_ridge",
    "load_sec_teaching_fixture",
    "regression_error_table",
]
