from __future__ import annotations

from hashlib import sha256

import numpy as np
import pytest
from quant_textbook.research_engineering import (
    ModelRegistry,
    batch_inference,
    benchmark_function,
    build_experiment_run,
    deterministic_chunk_plan,
    numeric_drift_report,
    promote_run,
    register_run,
    rollback_production,
)


def _digest(label: str) -> str:
    return sha256(label.encode()).hexdigest()


def _run(candidate: str, *, stage: str = "candidate"):
    return build_experiment_run(
        experiment_name="b10-test",
        candidate_name=candidate,
        stage=stage,
        config={"ridge": 1.0, "seed": 7},
        data_sha256=_digest("data"),
        code_revision="abc123",
        metrics={"mae": 0.1},
        artifact_sha256={"prediction": _digest(candidate)},
    )


def test_experiment_run_is_content_addressed_and_registry_is_immutable() -> None:
    first = _run("numeric-ridge")
    repeated = _run("numeric-ridge")
    assert first == repeated

    empty = ModelRegistry()
    registered = register_run(empty, first)
    assert empty.runs == ()
    assert registered.runs == (first,)
    with pytest.raises(ValueError, match="already registered"):
        register_run(registered, repeated)


def test_promotion_and_rollback_move_pointer_without_rewriting_runs() -> None:
    first = _run("first")
    second = _run("second")
    registry = register_run(register_run(ModelRegistry(), first), second)

    promoted = promote_run(registry, second.run_id)
    rolled_back = rollback_production(promoted, first.run_id)

    assert promoted.production_run_id == second.run_id
    assert rolled_back.production_run_id == first.run_id
    assert rolled_back.runs == registry.runs


def test_development_run_cannot_be_promoted() -> None:
    run = _run("development", stage="development")
    registry = register_run(ModelRegistry(), run)
    with pytest.raises(ValueError, match="candidate"):
        promote_run(registry, run.run_id)


def test_deterministic_chunk_plan_covers_each_row_once() -> None:
    chunks = deterministic_chunk_plan(10, 3)
    assert chunks == ((0, 4), (4, 7), (7, 10))
    covered = [row for start, stop in chunks for row in range(start, stop)]
    assert covered == list(range(10))


def test_benchmark_records_distribution_without_speed_assertion() -> None:
    result = benchmark_function(lambda: np.arange(100).sum(), repeats=5, warmups=1)
    assert result.durations_seconds.shape == (5,)
    assert np.all(result.durations_seconds >= 0.0)
    assert result.median_seconds >= 0.0


def test_numeric_drift_detects_shift_and_reports_reference_bins() -> None:
    rng = np.random.default_rng(42)
    reference = rng.normal(size=1000)
    stable = rng.normal(size=1000)
    shifted = rng.normal(loc=2.0, size=1000)

    stable_report = numeric_drift_report(reference, stable)
    shifted_report = numeric_drift_report(reference, shifted)

    assert shifted_report.population_stability_index > stable_report.population_stability_index
    assert shifted_report.ks_statistic > stable_report.ks_statistic
    np.testing.assert_allclose(shifted_report.reference_proportions.sum(), 1.0)
    np.testing.assert_allclose(shifted_report.current_proportions.sum(), 1.0)


def test_batch_inference_binds_model_input_and_prediction_hashes() -> None:
    features = np.arange(12, dtype=float).reshape(4, 3)
    run = _run("batch")

    first = batch_inference(
        lambda values: values.sum(axis=1),
        features,
        model_run_id=run.run_id,
        input_sha256=_digest("input"),
    )
    second = batch_inference(
        lambda values: values.sum(axis=1),
        features,
        model_run_id=run.run_id,
        input_sha256=_digest("input"),
    )

    assert first.output_sha256 == second.output_sha256
    assert first.row_count == 4
    np.testing.assert_array_equal(first.predictions, [3.0, 12.0, 21.0, 30.0])
