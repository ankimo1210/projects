from __future__ import annotations

from pathlib import Path

import numpy as np
from quant_textbook.b9_tournament import (
    HashedTfidfDocuments,
    paired_company_bootstrap,
    primary_baseline_name,
    regression_metrics,
    selection_gate,
)
from scipy import sparse


def test_regression_metrics_include_equal_company_macro() -> None:
    actual = np.asarray([0.0, 2.0, 1.0])
    predicted = np.asarray([1.0, 1.0, 1.0])
    metrics = regression_metrics(actual, predicted, np.asarray(["a", "a", "b"]))
    assert metrics["mae"] == 2.0 / 3.0
    assert metrics["company_macro_mae"] == 0.5
    assert metrics["median_absolute_error"] == 1.0


def test_selection_gate_uses_each_baseline_metric_minimum() -> None:
    baselines = {
        "zero": {"mae": 1.0, "median_absolute_error": 0.4, "company_macro_mae": 0.7},
        "pooled_drift": {"mae": 1.1, "median_absolute_error": 0.3, "company_macro_mae": 0.8},
        "seasonal": {"mae": 1.2, "median_absolute_error": 0.5, "company_macro_mae": 0.6},
        "company_mean": {"mae": 1.3, "median_absolute_error": 0.6, "company_macro_mae": 0.9},
    }
    accepted = selection_gate(
        {"mae": 0.98, "median_absolute_error": 0.3, "company_macro_mae": 0.6},
        baselines,
    )
    rejected = selection_gate(
        {"mae": 0.98, "median_absolute_error": 0.31, "company_macro_mae": 0.6},
        baselines,
    )
    assert accepted["accepted"] is True
    assert rejected["accepted"] is False
    assert primary_baseline_name(baselines) == "zero"


def test_company_cluster_bootstrap_is_deterministic() -> None:
    actual = np.asarray([0.0, 1.0, 2.0, 3.0])
    candidate = np.asarray([0.1, 1.3, 1.8, 3.4])
    baseline = np.asarray([0.2, 1.1, 2.2, 3.1])
    entities = np.asarray(["a", "a", "b", "b"])
    first = paired_company_bootstrap(
        actual, candidate, baseline, entities, replications=200, seed=123
    )
    second = paired_company_bootstrap(
        actual, candidate, baseline, entities, replications=200, seed=123
    )
    assert first == second
    assert first.replications == 200
    assert first.lower_95 <= first.delta_mae <= first.upper_95


def test_hashed_tfidf_fits_idf_on_training_documents_only(tmp_path: Path) -> None:
    paths = []
    for index, text in enumerate(("alpha alpha beta", "alpha gamma", "validation_only unique")):
        path = tmp_path / f"doc{index}.txt"
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    vectorizer = HashedTfidfDocuments(
        maximum_features=64,
        ngram_maximum=1,
        minimum_document_frequency=1,
    )
    matrix = vectorizer.fit_transform(paths, np.asarray([True, True, False]))
    assert sparse.isspmatrix_csr(matrix)
    assert matrix.shape == (3, 64)
    assert vectorizer.metadata["eligible_feature_count"] > 0
    assert vectorizer.metadata["ngram_maximum"] == 1
