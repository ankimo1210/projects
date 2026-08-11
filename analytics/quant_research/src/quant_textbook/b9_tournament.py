"""Leakage-aware utilities for the development-only B9 model tournament.

The full SEC artifact and the locked outer rows stay outside the repository.  This
module therefore contains only deterministic feature hashing, metric, bootstrap,
and pre-outer selection helpers.  The command-line runner that materializes the
external development data lives in ``tools/run_b9_tournament.py``.
"""

from __future__ import annotations

import re
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import sparse

TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class CandidateMetrics:
    """Validation metrics and provenance for one fixed candidate configuration."""

    candidate_id: str
    family: str
    configuration: dict[str, object]
    mae: float
    median_absolute_error: float
    rmse: float
    company_macro_mae: float
    n: int
    parameter_count: int
    runtime_seconds: float
    status: str = "evaluated"


@dataclass(frozen=True)
class PairedBootstrapResult:
    """Company-cluster paired bootstrap for candidate-minus-baseline MAE."""

    delta_mae: float
    lower_95: float
    upper_95: float
    replications: int
    seed: int


def regression_metrics(
    actual: np.ndarray, predicted: np.ndarray, entity_ids: np.ndarray
) -> dict[str, float]:
    """Return the locked B9 row and equal-company metrics."""

    observed = np.asarray(actual, dtype=float)
    fitted = np.asarray(predicted, dtype=float)
    entities = np.asarray(entity_ids, dtype=str)
    if observed.ndim != 1 or fitted.shape != observed.shape or entities.shape != observed.shape:
        raise ValueError("actual, predicted, and entity_ids must have one matching dimension")
    if observed.size == 0 or not np.isfinite(observed).all() or not np.isfinite(fitted).all():
        raise ValueError("actual and predicted must be finite and non-empty")
    absolute = np.abs(observed - fitted)
    company_means = [absolute[entities == company].mean() for company in np.unique(entities)]
    return {
        "mae": float(absolute.mean()),
        "median_absolute_error": float(np.median(absolute)),
        "rmse": float(np.sqrt(np.mean((observed - fitted) ** 2))),
        "company_macro_mae": float(np.mean(company_means)),
    }


def paired_company_bootstrap(
    actual: np.ndarray,
    candidate: np.ndarray,
    baseline: np.ndarray,
    entity_ids: np.ndarray,
    *,
    replications: int = 2_000,
    seed: int = 20_260_812,
) -> PairedBootstrapResult:
    """Estimate a paired candidate-minus-baseline MAE interval by company.

    A company is the resampling unit.  Within each sampled company all available
    validation rows are retained, so repeated rows from a single issuer are not
    treated as independent clusters.
    """

    observed = np.asarray(actual, dtype=float)
    candidate_values = np.asarray(candidate, dtype=float)
    baseline_values = np.asarray(baseline, dtype=float)
    entities = np.asarray(entity_ids, dtype=str)
    if candidate_values.shape != observed.shape or baseline_values.shape != observed.shape:
        raise ValueError("all prediction arrays must have one matching dimension")
    if replications <= 0 or isinstance(replications, bool):
        raise ValueError("replications must be a positive integer")
    companies = np.unique(entities)
    if companies.size == 0:
        raise ValueError("at least one company is required")
    company_delta = np.asarray(
        [
            np.abs(observed[entities == company] - candidate_values[entities == company]).mean()
            - np.abs(observed[entities == company] - baseline_values[entities == company]).mean()
            for company in companies
        ],
        dtype=float,
    )
    rng = np.random.default_rng(np.random.SeedSequence([int(seed), int(companies.size)]))
    sampled = rng.integers(0, companies.size, size=(int(replications), companies.size))
    distribution = company_delta[sampled].mean(axis=1)
    return PairedBootstrapResult(
        delta_mae=float(company_delta.mean()),
        lower_95=float(np.quantile(distribution, 0.025)),
        upper_95=float(np.quantile(distribution, 0.975)),
        replications=int(replications),
        seed=int(seed),
    )


def primary_baseline_name(
    baseline_metrics: dict[str, dict[str, float]],
    *,
    tie_break_order: tuple[str, ...] = ("zero", "pooled_drift", "seasonal", "company_mean"),
) -> str:
    """Freeze the lowest-MAE baseline using the pre-registered tie-break."""

    missing = [name for name in tie_break_order if name not in baseline_metrics]
    if missing:
        raise ValueError(f"baseline metrics are missing: {missing}")
    order = {name: index for index, name in enumerate(tie_break_order)}
    return min(
        tie_break_order,
        key=lambda name: (float(baseline_metrics[name]["mae"]), order[name]),
    )


def selection_gate(
    candidate: dict[str, float], baseline_metrics: dict[str, dict[str, float]]
) -> dict[str, object]:
    """Apply the amended inner-validation point and guardrail gate."""

    minimum_mae = min(float(metrics["mae"]) for metrics in baseline_metrics.values())
    minimum_medAE = min(
        float(metrics["median_absolute_error"]) for metrics in baseline_metrics.values()
    )
    minimum_company = min(
        float(metrics["company_macro_mae"]) for metrics in baseline_metrics.values()
    )
    checks = {
        "mae_at_most_99_percent_of_best_baseline": float(candidate["mae"]) <= 0.99 * minimum_mae,
        "median_absolute_error_not_above_baseline_minimum": float(
            candidate["median_absolute_error"]
        )
        <= minimum_medAE,
        "company_macro_mae_not_above_baseline_minimum": float(candidate["company_macro_mae"])
        <= minimum_company,
    }
    return {
        "accepted": bool(all(checks.values())),
        "checks": checks,
        "baseline_metric_minima": {
            "mae": minimum_mae,
            "median_absolute_error": minimum_medAE,
            "company_macro_mae": minimum_company,
        },
    }


def _normalize_tokens(text: str) -> list[str]:
    tokens = [token.casefold() for token in TOKEN_PATTERN.findall(text)]
    return ["<NUM>" if token.isdecimal() else token for token in tokens]


def _selected_chunks(
    tokens: list[str], *, chunk_length: int, maximum_chunks: int
) -> list[list[str]]:
    if not tokens:
        raise ValueError("normalized text contains no auditable tokens")
    if chunk_length <= 0 or maximum_chunks <= 0:
        raise ValueError("chunk_length and maximum_chunks must be positive")
    number_of_chunks = (len(tokens) + chunk_length - 1) // chunk_length
    selected_count = min(number_of_chunks, maximum_chunks)
    indexes = np.linspace(0, number_of_chunks - 1, selected_count, dtype=int)
    return [
        tokens[index * chunk_length : (index + 1) * chunk_length] for index in sorted(set(indexes))
    ]


def _bucket(ngram: tuple[str, ...], maximum_features: int) -> int:
    payload = "\x1f".join(ngram).encode("utf-8")
    return int(zlib.crc32(payload) % maximum_features)


class HashedTfidfDocuments:
    """Deterministic sparse TF-IDF over selected 512-token filing chunks.

    The feature map is a fixed hashing map rather than a Python hash or a
    learned vocabulary.  Document-frequency filtering and IDF are fit only on
    the supplied training mask; validation rows influence neither operation.
    """

    def __init__(
        self,
        *,
        maximum_features: int,
        ngram_maximum: int,
        minimum_document_frequency: int = 3,
        chunk_length: int = 512,
        maximum_chunks: int = 8,
    ) -> None:
        if maximum_features <= 0 or ngram_maximum not in {1, 2}:
            raise ValueError("maximum_features must be positive and ngram_maximum must be 1 or 2")
        if minimum_document_frequency <= 0:
            raise ValueError("minimum_document_frequency must be positive")
        self.maximum_features = int(maximum_features)
        self.ngram_maximum = int(ngram_maximum)
        self.minimum_document_frequency = int(minimum_document_frequency)
        self.chunk_length = int(chunk_length)
        self.maximum_chunks = int(maximum_chunks)
        self.document_frequency_: np.ndarray | None = None
        self.inverse_document_frequency_: np.ndarray | None = None

    def _counts(self, path: Path) -> dict[int, float]:
        text = path.read_text(encoding="utf-8")
        counts: dict[int, float] = {}
        for chunk in _selected_chunks(
            _normalize_tokens(text),
            chunk_length=self.chunk_length,
            maximum_chunks=self.maximum_chunks,
        ):
            for ngram_size in range(1, self.ngram_maximum + 1):
                for start in range(len(chunk) - ngram_size + 1):
                    bucket = _bucket(
                        tuple(chunk[start : start + ngram_size]), self.maximum_features
                    )
                    counts[bucket] = counts.get(bucket, 0.0) + 1.0
        if not counts:
            raise ValueError(f"no feature ngrams found in normalized document: {path}")
        return counts

    def fit_transform(
        self, paths: tuple[Path, ...] | list[Path], training_mask: np.ndarray
    ) -> sparse.csr_matrix:
        if not paths:
            raise ValueError("paths must not be empty")
        mask = np.asarray(training_mask, dtype=bool)
        if mask.shape != (len(paths),) or not mask.any():
            raise ValueError("training_mask must select at least one document")
        counts = [self._counts(path) for path in paths]
        document_frequency = np.zeros(self.maximum_features, dtype=np.int64)
        for index in np.flatnonzero(mask):
            for bucket in counts[int(index)]:
                document_frequency[bucket] += 1
        eligible = document_frequency >= self.minimum_document_frequency
        self.document_frequency_ = document_frequency
        self.inverse_document_frequency_ = np.zeros(self.maximum_features, dtype=float)
        self.inverse_document_frequency_[eligible] = (
            np.log((1.0 + float(mask.sum())) / (1.0 + document_frequency[eligible])) + 1.0
        )
        return self._matrix(counts)

    def _matrix(self, counts: list[dict[int, float]]) -> sparse.csr_matrix:
        if self.inverse_document_frequency_ is None:
            raise RuntimeError("fit_transform must be called before _matrix")
        rows: list[int] = []
        columns: list[int] = []
        values: list[float] = []
        for row_index, row_counts in enumerate(counts):
            norm_terms: list[tuple[int, float]] = []
            for bucket, count in row_counts.items():
                idf = self.inverse_document_frequency_[bucket]
                if idf > 0.0:
                    norm_terms.append((bucket, (1.0 + np.log(count)) * idf))
            norm = float(np.sqrt(sum(value * value for _, value in norm_terms)))
            if norm > 0.0:
                for bucket, value in norm_terms:
                    rows.append(row_index)
                    columns.append(bucket)
                    values.append(value / norm)
        return sparse.csr_matrix(
            (values, (rows, columns)), shape=(len(counts), self.maximum_features)
        )

    @property
    def metadata(self) -> dict[str, object]:
        if self.document_frequency_ is None:
            raise RuntimeError("fit_transform must be called before metadata")
        return {
            "maximum_features": self.maximum_features,
            "ngram_maximum": self.ngram_maximum,
            "minimum_document_frequency": self.minimum_document_frequency,
            "chunk_length": self.chunk_length,
            "maximum_chunks": self.maximum_chunks,
            "eligible_feature_count": int(
                np.count_nonzero(self.document_frequency_ >= self.minimum_document_frequency)
            ),
            "hash": "crc32_utf8_ngram_bucket",
        }


__all__ = [
    "CandidateMetrics",
    "HashedTfidfDocuments",
    "PairedBootstrapResult",
    "paired_company_bootstrap",
    "primary_baseline_name",
    "regression_metrics",
    "selection_gate",
]
