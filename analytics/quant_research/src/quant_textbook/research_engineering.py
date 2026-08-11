"""Reproducible experiment, registry, inference, and drift helpers for B10."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Any, Literal

import numpy as np
from scipy.stats import ks_2samp


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )


def _sha256_text(value: str, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{name} must be a 64-character SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError(f"{name} must be hexadecimal") from error
    return value.lower()


@dataclass(frozen=True)
class BenchmarkSummary:
    """Warm-up-aware timing distribution without a machine-specific pass gate."""

    durations_seconds: np.ndarray
    warmups: int
    median_seconds: float
    interquartile_range_seconds: float


@dataclass(frozen=True)
class ExperimentRun:
    """Content-addressed, immutable experiment metadata."""

    run_id: str
    experiment_name: str
    candidate_name: str
    stage: Literal["development", "candidate", "production", "archived"]
    config: dict[str, Any]
    config_sha256: str
    data_sha256: str
    code_revision: str
    metrics: dict[str, float]
    artifact_sha256: dict[str, str]


@dataclass(frozen=True)
class ModelRegistry:
    """Append-only registry state with one optional production pointer."""

    runs: tuple[ExperimentRun, ...] = ()
    production_run_id: str | None = None


@dataclass(frozen=True)
class DriftReport:
    """Reference-bin PSI and two-sample KS diagnostics."""

    reference_count: int
    current_count: int
    population_stability_index: float
    ks_statistic: float
    ks_pvalue: float
    bin_edges: np.ndarray
    reference_proportions: np.ndarray
    current_proportions: np.ndarray


@dataclass(frozen=True)
class BatchInferenceResult:
    """Predictions plus hashes that bind model, input, and output."""

    predictions: np.ndarray
    model_run_id: str
    input_sha256: str
    output_sha256: str
    row_count: int


def benchmark_function(
    function: Callable[[], Any], *, repeats: int = 7, warmups: int = 2
) -> BenchmarkSummary:
    """Measure a nullary callable after warm-up; never assert a speed threshold."""

    if not callable(function):
        raise TypeError("function must be callable")
    for name, value in (("repeats", repeats), ("warmups", warmups)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    if repeats == 0:
        raise ValueError("repeats must be positive")
    for _ in range(warmups):
        function()
    durations = np.empty(repeats)
    for index in range(repeats):
        started = time.perf_counter()
        function()
        durations[index] = time.perf_counter() - started
    return BenchmarkSummary(
        durations_seconds=durations,
        warmups=warmups,
        median_seconds=float(np.median(durations)),
        interquartile_range_seconds=float(
            np.quantile(durations, 0.75) - np.quantile(durations, 0.25)
        ),
    )


def deterministic_chunk_plan(row_count: int, worker_count: int) -> tuple[tuple[int, int], ...]:
    """Partition ordered rows without making scheduling part of the result."""

    for name, value in (("row_count", row_count), ("worker_count", worker_count)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    workers = min(row_count, worker_count)
    quotient, remainder = divmod(row_count, workers)
    chunks: list[tuple[int, int]] = []
    start = 0
    for worker in range(workers):
        size = quotient + int(worker < remainder)
        chunks.append((start, start + size))
        start += size
    return tuple(chunks)


def build_experiment_run(
    *,
    experiment_name: str,
    candidate_name: str,
    stage: Literal["development", "candidate", "production", "archived"],
    config: dict[str, Any],
    data_sha256: str,
    code_revision: str,
    metrics: dict[str, float],
    artifact_sha256: dict[str, str],
) -> ExperimentRun:
    """Create a deterministic run ID from configuration, lineage, and metrics."""

    if not experiment_name.strip() or not candidate_name.strip():
        raise ValueError("experiment_name and candidate_name must be non-empty")
    if stage not in {"development", "candidate", "production", "archived"}:
        raise ValueError("stage is unsupported")
    if not isinstance(config, dict) or not config:
        raise ValueError("config must be a non-empty dictionary")
    config_bytes = _canonical_json(config)
    config_sha = sha256(config_bytes).hexdigest()
    data_sha = _sha256_text(data_sha256, name="data_sha256")
    if not isinstance(code_revision, str) or not code_revision.strip():
        raise ValueError("code_revision must be non-empty")
    if not metrics or any(not np.isfinite(value) for value in metrics.values()):
        raise ValueError("metrics must be non-empty and finite")
    normalized_artifacts = {
        str(name): _sha256_text(value, name=f"artifact_sha256.{name}")
        for name, value in sorted(artifact_sha256.items())
    }
    run_payload = {
        "experiment_name": experiment_name,
        "candidate_name": candidate_name,
        "stage": stage,
        "config_sha256": config_sha,
        "data_sha256": data_sha,
        "code_revision": code_revision,
        "metrics": {key: float(value) for key, value in sorted(metrics.items())},
        "artifact_sha256": normalized_artifacts,
    }
    run_id = sha256(_canonical_json(run_payload)).hexdigest()[:24]
    return ExperimentRun(
        run_id=run_id,
        experiment_name=experiment_name,
        candidate_name=candidate_name,
        stage=stage,
        config=dict(config),
        config_sha256=config_sha,
        data_sha256=data_sha,
        code_revision=code_revision,
        metrics=run_payload["metrics"],
        artifact_sha256=normalized_artifacts,
    )


def register_run(registry: ModelRegistry, run: ExperimentRun) -> ModelRegistry:
    """Append one immutable run, rejecting ID collision or duplicate content."""

    if not isinstance(registry, ModelRegistry) or not isinstance(run, ExperimentRun):
        raise TypeError("registry and run have incompatible types")
    if any(existing.run_id == run.run_id for existing in registry.runs):
        raise ValueError("run_id is already registered")
    return replace(registry, runs=(*registry.runs, run))


def promote_run(registry: ModelRegistry, run_id: str) -> ModelRegistry:
    """Move a candidate pointer to production without mutating run evidence."""

    matches = [run for run in registry.runs if run.run_id == run_id]
    if len(matches) != 1:
        raise ValueError("run_id is not registered exactly once")
    if matches[0].stage not in {"candidate", "production"}:
        raise ValueError("only a candidate run can be promoted")
    return replace(registry, production_run_id=run_id)


def rollback_production(registry: ModelRegistry, prior_run_id: str) -> ModelRegistry:
    """Repoint production to an already registered production-capable run."""

    if registry.production_run_id is None:
        raise ValueError("registry has no production run to roll back")
    return promote_run(registry, prior_run_id)


def numeric_drift_report(
    reference: np.ndarray, current: np.ndarray, *, bins: int = 10
) -> DriftReport:
    """Compute PSI on reference quantiles and a two-sample KS diagnostic."""

    reference_values = np.asarray(reference, dtype=float)
    current_values = np.asarray(current, dtype=float)
    if reference_values.ndim != 1 or current_values.ndim != 1:
        raise ValueError("reference and current must be one-dimensional")
    if min(reference_values.size, current_values.size) < 2:
        raise ValueError("reference and current need at least two values")
    if not np.isfinite(reference_values).all() or not np.isfinite(current_values).all():
        raise ValueError("reference and current must be finite")
    if isinstance(bins, bool) or not isinstance(bins, int) or bins < 2:
        raise ValueError("bins must be an integer of at least two")
    quantiles = np.linspace(0.0, 1.0, bins + 1)
    edges = np.unique(np.quantile(reference_values, quantiles))
    if edges.size < 3:
        raise ValueError("reference has insufficient variation for drift bins")
    edges[0] = -np.inf
    edges[-1] = np.inf
    reference_counts = np.histogram(reference_values, bins=edges)[0]
    current_counts = np.histogram(current_values, bins=edges)[0]
    epsilon = 0.5 / max(reference_values.size, current_values.size)
    reference_proportions = np.maximum(reference_counts / reference_values.size, epsilon)
    current_proportions = np.maximum(current_counts / current_values.size, epsilon)
    reference_proportions /= reference_proportions.sum()
    current_proportions /= current_proportions.sum()
    psi = float(
        np.sum(
            (current_proportions - reference_proportions)
            * np.log(current_proportions / reference_proportions)
        )
    )
    ks = ks_2samp(reference_values, current_values, method="auto")
    return DriftReport(
        reference_count=reference_values.size,
        current_count=current_values.size,
        population_stability_index=psi,
        ks_statistic=float(ks.statistic),
        ks_pvalue=float(ks.pvalue),
        bin_edges=edges,
        reference_proportions=reference_proportions,
        current_proportions=current_proportions,
    )


def batch_inference(
    predictor: Callable[[np.ndarray], np.ndarray],
    features: np.ndarray,
    *,
    model_run_id: str,
    input_sha256: str,
) -> BatchInferenceResult:
    """Bind deterministic predictions to model and input fingerprints."""

    if not callable(predictor):
        raise TypeError("predictor must be callable")
    matrix = np.asarray(features, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or not np.isfinite(matrix).all():
        raise ValueError("features must be a non-empty finite matrix")
    if not isinstance(model_run_id, str) or not model_run_id.strip():
        raise ValueError("model_run_id must be non-empty")
    input_digest = _sha256_text(input_sha256, name="input_sha256")
    predictions = np.asarray(predictor(matrix), dtype=float)
    if predictions.shape != (matrix.shape[0],) or not np.isfinite(predictions).all():
        raise ValueError("predictor must return one finite value per row")
    output_digest = sha256(predictions.astype("<f8", copy=False).tobytes()).hexdigest()
    return BatchInferenceResult(
        predictions=predictions,
        model_run_id=model_run_id,
        input_sha256=input_digest,
        output_sha256=output_digest,
        row_count=matrix.shape[0],
    )


__all__ = [
    "BatchInferenceResult",
    "BenchmarkSummary",
    "DriftReport",
    "ExperimentRun",
    "ModelRegistry",
    "batch_inference",
    "benchmark_function",
    "build_experiment_run",
    "deterministic_chunk_plan",
    "numeric_drift_report",
    "promote_run",
    "register_run",
    "rollback_production",
]
