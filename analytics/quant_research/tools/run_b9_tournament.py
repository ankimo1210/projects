"""Run the pre-registered B9 development tournament without opening outer rows.

The command reads the externally stored M6 panel, previous-filing sidecar, and
normalized documents.  It evaluates the four fixed baselines, numeric ridge,
hashed TF-IDF ridge, joint/numeric NumPy MLP variants, and diagnostic fixed
encoder probes on the development partition only.  The locked outer partition
is counted for an audit trail but never materialized into features or predictions.

Raw filings, normalized text, contact-bearing User-Agent values, and prediction
rows are never written to the repository.  The output is intended for the
external ``derived`` directory under the SEC cache.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from quant_textbook.b9_tournament import (
    CandidateMetrics,
    HashedTfidfDocuments,
    paired_company_bootstrap,
    primary_baseline_name,
    regression_metrics,
    selection_gate,
    text_token_chunk_hashes,
    text_token_hash_sequence,
)
from quant_textbook.deep_learning import (
    lstm_chunk_average_predict,
    mlp_predict,
    self_attention,
    temporal_convolution_encode,
    token_embedding,
    train_lstm_chunk_average,
    train_mlp,
)
from quant_textbook.sec_features import fit_numeric_preprocessor, fit_sparse_ridge
from scipy import sparse

NUMERIC_FEATURE_NAMES = (
    "log_previous_assets",
    "lag_1_target_log_change",
    "lag_2_target_log_change",
    "expanding_mean_target_log_change",
    "expanding_std_target_log_change",
    "history_count",
    "previous_filing_lag_days",
    "period_gap_days",
    "fiscal_quarter_1",
    "fiscal_quarter_2",
    "fiscal_quarter_3",
    "fiscal_quarter_4",
)
BASELINE_NAMES = ("zero", "pooled_drift", "seasonal", "company_mean")
NEURAL_FAMILIES = frozenset({"numpy_mlp", "numpy_lstm", "joint_text_numeric_mlp"})
ALL_CORE_FAMILIES = (
    "numpy_mlp",
    "numpy_lstm",
    "numpy_tcn",
    "numpy_small_self_attention",
    "joint_text_numeric_mlp",
)


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, check=True, text=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _numeric_features(row: pd.Series, full_panel: pd.DataFrame) -> list[float | None]:
    history = full_panel.loc[
        (full_panel["cik"] == row["cik"]) & (full_panel["target_available_date"] < row["known_at"])
    ].sort_values(["target_available_date", "target_period_end"])
    history_target = history["target_log_change"].to_numpy(dtype=float)
    quarter = int(row["target_period_end"].quarter)
    return [
        float(np.log(row["previous_assets_usd"])),
        float(history_target[-1]) if history_target.size >= 1 else None,
        float(history_target[-2]) if history_target.size >= 2 else None,
        float(history_target.mean()) if history_target.size else None,
        float(history_target.std(ddof=1)) if history_target.size >= 2 else None,
        float(history_target.size),
        float((row["known_at"] - row["previous_period_end"]).days),
        float((row["target_period_end"] - row["previous_period_end"]).days),
        *[float(quarter == value) for value in range(1, 5)],
    ]


def _baseline_predictions(train: pd.DataFrame, evaluation: pd.DataFrame, name: str) -> np.ndarray:
    if name not in BASELINE_NAMES:
        raise ValueError(f"unknown baseline: {name}")
    predictions: list[float] = []
    for _, row in evaluation.iterrows():
        known = train.loc[train["target_available_date"] < row["known_at"]]
        if name == "zero" or known.empty:
            predictions.append(0.0)
        elif name == "pooled_drift":
            predictions.append(float(known["target_log_change"].mean()))
        elif name == "company_mean":
            company = known.loc[known["cik"] == row["cik"], "target_log_change"]
            predictions.append(
                float(company.mean())
                if not company.empty
                else float(known["target_log_change"].mean())
            )
        else:
            previous_period = row["target_period_end"] - pd.DateOffset(years=1)
            seasonal = known.loc[
                (known["cik"] == row["cik"]) & (known["target_period_end"] == previous_period),
                "target_log_change",
            ]
            predictions.append(float(seasonal.iloc[-1]) if not seasonal.empty else 0.0)
    return np.asarray(predictions, dtype=float)


def _materialize_data(
    panel_artifact: Path,
    sidecar_path: Path,
    normalized_root: Path,
    contract_path: Path,
) -> tuple[pd.DataFrame, dict[str, str], dict[str, Any]]:
    panel_payload = _read_object(panel_artifact)
    sidecar = _read_object(sidecar_path)
    manifest_path = normalized_root / "manifest.json"
    manifest = _read_object(manifest_path)
    contract = _read_object(contract_path)
    if panel_payload.get("schema_version") != "b9-sec-panel-v1":
        raise ValueError("unsupported M6 panel schema")
    if sidecar.get("schema_version") != "b9-previous-filing-provenance-v1":
        raise ValueError("unsupported previous-filing sidecar schema")
    if manifest.get("schema_version") != "b9-sec-normalized-text-v1":
        raise ValueError("unsupported normalized text manifest schema")
    panel = pd.DataFrame(panel_payload["panel"]["rows"])
    side = pd.DataFrame(sidecar["rows"])
    date_columns = (
        "previous_period_end",
        "target_period_end",
        "previous_available_date",
        "target_available_date",
        "known_at",
    )
    for column in date_columns:
        panel[column] = pd.to_datetime(panel[column], errors="raise")
    side["previous_available_date"] = pd.to_datetime(
        side["previous_available_date"], errors="raise"
    )
    side["target_available_date"] = pd.to_datetime(side["target_available_date"], errors="raise")
    join_columns = ["cik", "previous_available_date", "target_available_date"]
    side = side.loc[
        :,
        [
            *join_columns,
            "previous_accession",
            "previous_form",
            "previous_filing_date",
            "previous_acceptance_datetime",
            "previous_primary_document",
            "previous_document_sha256",
        ],
    ]
    if side.duplicated(join_columns).any() or panel.duplicated(join_columns).any():
        raise ValueError("panel and sidecar join keys must be unique")
    frame = panel.merge(side, on=join_columns, how="left", validate="one_to_one")
    if frame["previous_accession"].isna().any():
        raise ValueError("panel rows are missing previous-filing provenance")
    if (frame["previous_accession"] == frame.get("target_accession", "__missing__")).any():
        raise ValueError("target accession leaked into a previous filing feature")
    documents = {str(row["accession"]): row for row in manifest.get("documents", [])}
    if len(documents) != len(manifest.get("documents", [])):
        raise ValueError("normalized manifest contains duplicate accessions")
    paths: list[str] = []
    normalized_hashes: list[str] = []
    missing_documents: list[str] = []
    for _, row in frame.iterrows():
        document = documents.get(str(row["previous_accession"]))
        if document is None:
            missing_documents.append(str(row["previous_accession"]))
            paths.append("")
            continue
        if int(document["cik"]) != int(row["cik"]):
            raise ValueError("normalized document CIK does not match panel CIK")
        if str(document["form"]) not in {"10-K", "10-Q", "10-K/A", "10-Q/A"}:
            raise ValueError("normalized document form is outside the B9 contract")
        path = (normalized_root / str(document["path"])).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"normalized document is missing: {path}")
        if (
            int(document.get("normalized_byte_count", 0)) <= 0
            or int(document.get("token_count", 0)) <= 0
        ):
            raise ValueError("normalized document has no auditable text")
        if path.stat().st_size != int(document["normalized_byte_count"]):
            raise ValueError(f"normalized document byte count changed: {path}")
        paths.append(str(path))
        normalized_hashes.append(str(document["normalized_text_sha256"]))
    if missing_documents:
        raise ValueError(f"normalized manifest lacks previous accessions: {missing_documents[:3]}")
    frame["normalized_path"] = paths
    frame["normalized_text_sha256"] = normalized_hashes
    if len(frame) != 4631:
        raise ValueError(f"M6 row count changed before tournament: {len(frame)}")
    contract_expected_sha = str(contract["parent_data"]["derived_panel_sha256"])
    if _digest(panel_artifact) != contract_expected_sha:
        raise ValueError("M6 panel hash does not match the pre-analysis contract")
    hashes = {
        "panel_sha256": _digest(panel_artifact),
        "sidecar_sha256": _digest(sidecar_path),
        "normalized_manifest_sha256": _digest(manifest_path),
        "preanalysis_contract_sha256": _digest(contract_path),
    }
    split = contract["splits"]
    outer_cutoff = pd.Timestamp(split["outer_time_cutoff"])
    inner_cutoff = pd.Timestamp(split["inner_validation"]["time_cutoff"])
    development = (frame["target_available_date"] < outer_cutoff) & (frame["cik"] % 3 != 0)
    outer = (frame["target_available_date"] >= outer_cutoff) & (frame["cik"] % 3 == 0)
    if int(development.sum()) != int(split["development"]["rows"]):
        raise ValueError("development partition count changed from the contract")
    if int(outer.sum()) != int(split["outer_test"]["rows"]):
        raise ValueError("outer partition count changed from the contract")
    frame = frame.sort_values(["target_available_date", "cik", "target_period_end"]).reset_index(
        drop=True
    )
    frame["development"] = (frame["target_available_date"] < outer_cutoff) & (frame["cik"] % 3 != 0)
    frame["inner_train"] = frame["development"] & (frame["target_available_date"] < inner_cutoff)
    frame["inner_validation"] = frame["development"] & (
        frame["target_available_date"] >= inner_cutoff
    )
    frame["outer_locked"] = (frame["target_available_date"] >= outer_cutoff) & (
        frame["cik"] % 3 == 0
    )
    development_frame = frame.loc[frame["development"]]
    split_pairs = {
        "time": (development_frame["inner_train"], development_frame["inner_validation"]),
        "company_mod_1_to_2": (
            development_frame["cik"] % 3 == 1,
            development_frame["cik"] % 3 == 2,
        ),
        "company_mod_2_to_1": (
            development_frame["cik"] % 3 == 2,
            development_frame["cik"] % 3 == 1,
        ),
    }
    cross_partition_duplicates_by_axis: dict[str, list[str]] = {}
    for axis_name, (train_axis, validation_axis) in split_pairs.items():
        axis_frame = development_frame.loc[train_axis | validation_axis]
        duplicate_families = axis_frame.groupby("normalized_text_sha256")
        cross_partition_duplicates = [
            digest
            for digest, group in duplicate_families
            if bool(train_axis.loc[group.index].any())
            and bool(validation_axis.loc[group.index].any())
        ]
        cross_partition_duplicates_by_axis[axis_name] = cross_partition_duplicates
        if cross_partition_duplicates:
            raise ValueError(
                "identical normalized document families cross the inner selection axis "
                f"{axis_name}: {cross_partition_duplicates[:3]}"
            )
    return (
        frame,
        hashes,
        {
            "contract": contract,
            "normalized_manifest": manifest,
            "outer_rows": int(frame["outer_locked"].sum()),
            "development_rows": int(frame["development"].sum()),
            "inner_train_rows": int(frame["inner_train"].sum()),
            "inner_validation_rows": int(frame["inner_validation"].sum()),
            "cross_partition_duplicate_families_by_axis": {
                axis: len(digests) for axis, digests in cross_partition_duplicates_by_axis.items()
            },
        },
    )


def _candidate_record(
    candidate_id: str,
    family: str,
    configuration: dict[str, object],
    metrics: dict[str, float],
    parameter_count: int,
    runtime_seconds: float,
    *,
    selection_eligible: bool = True,
) -> CandidateMetrics:
    return CandidateMetrics(
        candidate_id=candidate_id,
        family=family,
        configuration=configuration,
        mae=metrics["mae"],
        median_absolute_error=metrics["median_absolute_error"],
        rmse=metrics["rmse"],
        company_macro_mae=metrics["company_macro_mae"],
        n=int(metrics["n"]) if "n" in metrics else 0,
        parameter_count=int(parameter_count),
        runtime_seconds=float(runtime_seconds),
        selection_eligible=bool(selection_eligible),
    )


def _evaluate_selection_axis(
    *,
    axis_name: str,
    seed_namespace: int,
    train_mask: np.ndarray,
    validation_mask: np.ndarray,
    numeric_values: np.ndarray,
    targets: np.ndarray,
    actual: np.ndarray,
    entities: np.ndarray,
    document_paths: tuple[Path, ...],
    chunk_features: np.ndarray,
    active_chunks: np.ndarray,
) -> tuple[list[CandidateMetrics], dict[str, np.ndarray]]:
    """Evaluate all selection-eligible families on one pre-registered axis."""

    records: list[CandidateMetrics] = []
    predictions_by_id: dict[str, np.ndarray] = {}
    numeric_preprocessor = fit_numeric_preprocessor(numeric_values, train_mask)
    numeric_matrix = numeric_preprocessor.transform(numeric_values)

    for ridge in (0.01, 0.1, 1.0, 10.0):
        started = time.perf_counter()
        model = fit_sparse_ridge(numeric_matrix[train_mask], targets[train_mask], ridge=ridge)
        predictions = model.predict(numeric_matrix[validation_mask])
        metrics = regression_metrics(actual, predictions, entities)
        metrics["n"] = float(actual.size)
        candidate_id = f"numeric_ridge_lambda_{ridge:g}"
        records.append(
            _candidate_record(
                candidate_id,
                "numeric_ridge",
                {
                    "ridge_lambda": ridge,
                    "feature_names": list(NUMERIC_FEATURE_NAMES),
                    "validation_axis": axis_name,
                },
                metrics,
                numeric_matrix.shape[1],
                time.perf_counter() - started,
            )
        )
        predictions_by_id[candidate_id] = predictions

    joint_source_matrix: sparse.csr_matrix | None = None
    for maximum_features in (5000, 10000):
        for ngram_maximum in (1, 2):
            vectorizer = HashedTfidfDocuments(
                maximum_features=maximum_features,
                ngram_maximum=ngram_maximum,
                minimum_document_frequency=3,
            )
            started = time.perf_counter()
            text_matrix = vectorizer.fit_transform(document_paths, train_mask)
            if maximum_features == 5000 and ngram_maximum == 2:
                joint_source_matrix = text_matrix.copy()
            for ridge in (0.1, 1.0, 10.0):
                fit_started = time.perf_counter()
                model = fit_sparse_ridge(text_matrix[train_mask], targets[train_mask], ridge=ridge)
                predictions = model.predict(text_matrix[validation_mask])
                metrics = regression_metrics(actual, predictions, entities)
                metrics["n"] = float(actual.size)
                candidate_id = f"tfidf_ridge_features_{maximum_features}_ngram_{ngram_maximum}_lambda_{ridge:g}"
                records.append(
                    _candidate_record(
                        candidate_id,
                        "tfidf_ridge",
                        {
                            **vectorizer.metadata,
                            "ridge_lambda": ridge,
                            "feature_scope": "previous_primary_document_only",
                            "validation_axis": axis_name,
                        },
                        metrics,
                        text_matrix.shape[1],
                        time.perf_counter() - fit_started,
                    )
                )
                predictions_by_id[candidate_id] = predictions
            text_runtime = time.perf_counter() - started
            for record_index in range(len(records) - 3, len(records)):
                record = records[record_index]
                records[record_index] = CandidateMetrics(
                    **{**asdict(record), "runtime_seconds": text_runtime}
                )

    for width in (16, 32):
        for learning_rate in (0.001, 0.003):
            for seed_offset in (0, 1, 2):
                started = time.perf_counter()
                result = train_mlp(
                    numeric_matrix[train_mask],
                    targets[train_mask],
                    numeric_matrix[validation_mask],
                    targets[validation_mask],
                    hidden_width=width,
                    learning_rate=learning_rate,
                    epochs=200,
                    patience=20,
                    rng=np.random.default_rng(
                        np.random.SeedSequence([20260811, seed_namespace, 33, width, seed_offset])
                    ),
                )
                predictions = mlp_predict(result.parameters, numeric_matrix[validation_mask])
                metrics = regression_metrics(actual, predictions, entities)
                metrics["n"] = float(actual.size)
                candidate_id = f"numpy_mlp_width_{width}_lr_{learning_rate:g}_seed_{seed_offset}"
                parameter_count = (
                    result.parameters.input_weights.size
                    + result.parameters.hidden_bias.size
                    + result.parameters.output_weights.size
                    + 1
                )
                records.append(
                    _candidate_record(
                        candidate_id,
                        "numpy_mlp",
                        {
                            "hidden_width": width,
                            "learning_rate": learning_rate,
                            "seed_offset": seed_offset,
                            "epochs": 200,
                            "patience": 20,
                            "feature_scope": "numeric_only",
                            "validation_axis": axis_name,
                        },
                        metrics,
                        parameter_count,
                        time.perf_counter() - started,
                    )
                )
                predictions_by_id[candidate_id] = predictions

    if joint_source_matrix is None:
        raise RuntimeError("joint text source matrix was not materialized for selection axis")
    projection_rng = np.random.default_rng(np.random.SeedSequence([20260811, 36, 5000, 2]))
    projection = projection_rng.normal(
        scale=1.0 / np.sqrt(64.0), size=(joint_source_matrix.shape[1], 64)
    )
    joint_matrix = np.column_stack(
        [numeric_matrix, np.asarray(joint_source_matrix @ projection, dtype=float)]
    )
    for width in (16, 32):
        for learning_rate in (0.001, 0.003):
            for seed_offset in (0, 1, 2):
                started = time.perf_counter()
                result = train_mlp(
                    joint_matrix[train_mask],
                    targets[train_mask],
                    joint_matrix[validation_mask],
                    targets[validation_mask],
                    hidden_width=width,
                    learning_rate=learning_rate,
                    epochs=200,
                    patience=20,
                    rng=np.random.default_rng(
                        np.random.SeedSequence([20260811, seed_namespace, 36, width, seed_offset])
                    ),
                )
                predictions = mlp_predict(result.parameters, joint_matrix[validation_mask])
                metrics = regression_metrics(actual, predictions, entities)
                metrics["n"] = float(actual.size)
                candidate_id = (
                    f"joint_text_numeric_mlp_width_{width}_lr_{learning_rate:g}_seed_{seed_offset}"
                )
                parameter_count = (
                    result.parameters.input_weights.size
                    + result.parameters.hidden_bias.size
                    + result.parameters.output_weights.size
                    + 1
                )
                records.append(
                    _candidate_record(
                        candidate_id,
                        "joint_text_numeric_mlp",
                        {
                            "hidden_width": width,
                            "learning_rate": learning_rate,
                            "seed_offset": seed_offset,
                            "epochs": 200,
                            "patience": 20,
                            "feature_scope": "numeric_plus_hashed_tfidf_random_projection",
                            "text_features": 5000,
                            "text_ngram_maximum": 2,
                            "text_projection_width": 64,
                            "text_projection_seed": 20260811,
                            "validation_axis": axis_name,
                        },
                        metrics,
                        parameter_count,
                        time.perf_counter() - started,
                    )
                )
                predictions_by_id[candidate_id] = predictions

    for hidden_width in (16, 32):
        for learning_rate in (0.001, 0.003):
            for seed_offset in (0, 1, 2):
                started = time.perf_counter()
                result = train_lstm_chunk_average(
                    chunk_features[train_mask],
                    active_chunks[train_mask],
                    targets[train_mask],
                    chunk_features[validation_mask],
                    active_chunks[validation_mask],
                    targets[validation_mask],
                    hidden_width=hidden_width,
                    learning_rate=learning_rate,
                    epochs=200,
                    patience=20,
                    rng=np.random.default_rng(
                        np.random.SeedSequence(
                            [20260811, seed_namespace, 37, hidden_width, seed_offset]
                        )
                    ),
                )
                predictions = lstm_chunk_average_predict(
                    result.parameters,
                    chunk_features[validation_mask],
                    active_chunks[validation_mask],
                )
                metrics = regression_metrics(actual, predictions, entities)
                metrics["n"] = float(actual.size)
                candidate_id = (
                    f"numpy_lstm_width_{hidden_width}_lr_{learning_rate:g}_seed_{seed_offset}"
                )
                parameter_count = (
                    16 * 4 * hidden_width
                    + hidden_width * 4 * hidden_width
                    + 4 * hidden_width
                    + hidden_width
                    + 1
                )
                records.append(
                    _candidate_record(
                        candidate_id,
                        "numpy_lstm",
                        {
                            "hidden_width": hidden_width,
                            "learning_rate": learning_rate,
                            "seed_offset": seed_offset,
                            "epochs": 200,
                            "patience": 20,
                            "feature_scope": "previous_primary_document_only",
                            "chunk_length": 512,
                            "maximum_chunks": 8,
                            "chunk_aggregation": "mean_token_embedding_per_chunk_then_mean_chunk_predictions",
                            "token_embedding_width": 16,
                            "token_embedding_seed": 20260811,
                            "active_chunk_average": True,
                            "validation_axis": axis_name,
                        },
                        metrics,
                        parameter_count,
                        time.perf_counter() - started,
                    )
                )
                predictions_by_id[candidate_id] = predictions

    return records, predictions_by_id


def run_tournament(args: argparse.Namespace) -> dict[str, Any]:
    panel_path = args.panel_artifact.expanduser().resolve()
    sidecar_path = args.provenance_sidecar.expanduser().resolve()
    normalized_root = args.normalized_root.expanduser().resolve()
    contract_path = args.preanalysis_contract.expanduser().resolve()
    frame, input_hashes, partition_info = _materialize_data(
        panel_path, sidecar_path, normalized_root, contract_path
    )
    development = frame.loc[frame["development"]].copy()
    train_mask = development["inner_train"].to_numpy(dtype=bool)
    validation_mask = development["inner_validation"].to_numpy(dtype=bool)
    train = development.loc[train_mask]
    validation = development.loc[validation_mask]
    actual = validation["target_log_change"].to_numpy(dtype=float)
    entities = validation["cik"].astype(str).to_numpy()
    baseline_results: dict[str, dict[str, float]] = {}
    baseline_predictions: dict[str, np.ndarray] = {}
    for name in BASELINE_NAMES:
        predictions = _baseline_predictions(train, validation, name)
        metrics = regression_metrics(actual, predictions, entities)
        metrics["n"] = float(actual.size)
        baseline_results[name] = metrics
        baseline_predictions[name] = predictions
    primary_baseline = primary_baseline_name(baseline_results)

    numeric_values = np.asarray(
        [_numeric_features(row, frame) for _, row in development.iterrows()], dtype=float
    )
    numeric_preprocessor = fit_numeric_preprocessor(numeric_values, train_mask)
    numeric_matrix = numeric_preprocessor.transform(numeric_values)
    targets = development["target_log_change"].to_numpy(dtype=float)
    candidate_records: list[CandidateMetrics] = []
    prediction_store: dict[str, np.ndarray] = {}
    joint_source_matrix: sparse.csr_matrix | None = None

    for ridge in (0.01, 0.1, 1.0, 10.0):
        started = time.perf_counter()
        model = fit_sparse_ridge(numeric_matrix[train_mask], targets[train_mask], ridge=ridge)
        predictions = model.predict(numeric_matrix[validation_mask])
        elapsed = time.perf_counter() - started
        metrics = regression_metrics(actual, predictions, entities)
        metrics["n"] = float(actual.size)
        candidate_id = f"numeric_ridge_lambda_{ridge:g}"
        candidate_records.append(
            _candidate_record(
                candidate_id,
                "numeric_ridge",
                {"ridge_lambda": ridge, "feature_names": list(NUMERIC_FEATURE_NAMES)},
                metrics,
                numeric_matrix.shape[1],
                elapsed,
            )
        )
        prediction_store[candidate_id] = predictions

    document_paths = tuple(Path(path) for path in development["normalized_path"])
    for maximum_features in (5000, 10000):
        for ngram_maximum in (1, 2):
            vectorizer = HashedTfidfDocuments(
                maximum_features=maximum_features,
                ngram_maximum=ngram_maximum,
                minimum_document_frequency=3,
            )
            started = time.perf_counter()
            text_matrix = vectorizer.fit_transform(document_paths, train_mask)
            if maximum_features == 5000 and ngram_maximum == 2:
                joint_source_matrix = text_matrix.copy()
            for ridge in (0.1, 1.0, 10.0):
                fit_started = time.perf_counter()
                model = fit_sparse_ridge(text_matrix[train_mask], targets[train_mask], ridge=ridge)
                predictions = model.predict(text_matrix[validation_mask])
                elapsed = time.perf_counter() - fit_started
                metrics = regression_metrics(actual, predictions, entities)
                metrics["n"] = float(actual.size)
                candidate_id = f"tfidf_ridge_features_{maximum_features}_ngram_{ngram_maximum}_lambda_{ridge:g}"
                candidate_records.append(
                    _candidate_record(
                        candidate_id,
                        "tfidf_ridge",
                        {
                            **vectorizer.metadata,
                            "ridge_lambda": ridge,
                            "feature_scope": "previous_primary_document_only",
                        },
                        metrics,
                        text_matrix.shape[1],
                        time.perf_counter() - fit_started,
                    )
                )
                prediction_store[candidate_id] = predictions
            text_runtime = time.perf_counter() - started
            for record_index in range(len(candidate_records) - 3, len(candidate_records)):
                record = candidate_records[record_index]
                candidate_records[record_index] = CandidateMetrics(
                    **{**asdict(record), "runtime_seconds": text_runtime}
                )

    for width in (16, 32):
        for learning_rate in (0.001, 0.003):
            for seed_offset in (0, 1, 2):
                started = time.perf_counter()
                rng = np.random.default_rng(
                    np.random.SeedSequence([20260811, 33, width, seed_offset])
                )
                result = train_mlp(
                    numeric_matrix[train_mask],
                    targets[train_mask],
                    numeric_matrix[validation_mask],
                    targets[validation_mask],
                    hidden_width=width,
                    learning_rate=learning_rate,
                    epochs=200,
                    patience=20,
                    rng=rng,
                )
                predictions = mlp_predict(result.parameters, numeric_matrix[validation_mask])
                metrics = regression_metrics(actual, predictions, entities)
                metrics["n"] = float(actual.size)
                candidate_id = f"numpy_mlp_width_{width}_lr_{learning_rate:g}_seed_{seed_offset}"
                parameter_count = (
                    result.parameters.input_weights.size
                    + result.parameters.hidden_bias.size
                    + result.parameters.output_weights.size
                    + 1
                )
                candidate_records.append(
                    _candidate_record(
                        candidate_id,
                        "numpy_mlp",
                        {
                            "hidden_width": width,
                            "learning_rate": learning_rate,
                            "seed_offset": seed_offset,
                            "epochs": 200,
                            "patience": 20,
                            "feature_scope": "numeric_only",
                        },
                        metrics,
                        parameter_count,
                        time.perf_counter() - started,
                    )
                )
                prediction_store[candidate_id] = predictions

    if joint_source_matrix is None:
        raise RuntimeError("joint text source matrix was not materialized")
    projection_rng = np.random.default_rng(np.random.SeedSequence([20260811, 36, 5000, 2]))
    projection = projection_rng.normal(
        scale=1.0 / np.sqrt(64.0), size=(joint_source_matrix.shape[1], 64)
    )
    text_projection = np.asarray(joint_source_matrix @ projection, dtype=float)
    joint_matrix = np.column_stack([numeric_matrix, text_projection])
    for width in (16, 32):
        for learning_rate in (0.001, 0.003):
            for seed_offset in (0, 1, 2):
                started = time.perf_counter()
                rng = np.random.default_rng(
                    np.random.SeedSequence([20260811, 36, width, seed_offset])
                )
                result = train_mlp(
                    joint_matrix[train_mask],
                    targets[train_mask],
                    joint_matrix[validation_mask],
                    targets[validation_mask],
                    hidden_width=width,
                    learning_rate=learning_rate,
                    epochs=200,
                    patience=20,
                    rng=rng,
                )
                predictions = mlp_predict(result.parameters, joint_matrix[validation_mask])
                metrics = regression_metrics(actual, predictions, entities)
                metrics["n"] = float(actual.size)
                candidate_id = (
                    f"joint_text_numeric_mlp_width_{width}_lr_{learning_rate:g}_seed_{seed_offset}"
                )
                parameter_count = (
                    result.parameters.input_weights.size
                    + result.parameters.hidden_bias.size
                    + result.parameters.output_weights.size
                    + 1
                )
                candidate_records.append(
                    _candidate_record(
                        candidate_id,
                        "joint_text_numeric_mlp",
                        {
                            "hidden_width": width,
                            "learning_rate": learning_rate,
                            "seed_offset": seed_offset,
                            "epochs": 200,
                            "patience": 20,
                            "feature_scope": "numeric_plus_hashed_tfidf_random_projection",
                            "text_features": 5000,
                            "text_ngram_maximum": 2,
                            "text_projection_width": 64,
                            "text_projection_seed": 20260811,
                        },
                        metrics,
                        parameter_count,
                        time.perf_counter() - started,
                    )
                )
                prediction_store[candidate_id] = predictions

    # The sequence contract is 512-token chunks, up to eight deterministic
    # chunks per filing.  Token embeddings are fixed for this Core run; the
    # LSTM predicts each active chunk and averages those predictions at the
    # document level.  Padding is excluded from the average.
    chunk_hashes = np.asarray(
        [text_token_chunk_hashes(path) for path in document_paths], dtype=np.int64
    )
    embedding_width = 16
    hash_buckets = 2_000
    embedding_ids = np.arange(1, hash_buckets + 1, dtype=np.int64).reshape(1, -1)
    embedding_table = np.vstack(
        [
            np.zeros((1, embedding_width)),
            token_embedding(embedding_ids, embedding_width, seed=20260811)[0],
        ]
    )
    chunk_features = np.empty((chunk_hashes.shape[0], chunk_hashes.shape[1], embedding_width))
    active_chunks = np.zeros(chunk_hashes.shape[:2], dtype=bool)
    for start in range(0, chunk_hashes.shape[0], 64):
        stop = min(start + 64, chunk_hashes.shape[0])
        batch_hashes = chunk_hashes[start:stop]
        batch_embeddings = embedding_table[batch_hashes]
        active = (batch_hashes > 0).astype(float)
        counts = np.maximum(active.sum(axis=2, keepdims=True), 1.0)
        means = (batch_embeddings * active[..., None]).sum(axis=2) / counts
        chunk_features[start:stop] = means
        active_chunks[start:stop] = active.sum(axis=2) > 0.0
    for hidden_width in (16, 32):
        for learning_rate in (0.001, 0.003):
            for seed_offset in (0, 1, 2):
                started = time.perf_counter()
                result = train_lstm_chunk_average(
                    chunk_features[train_mask],
                    active_chunks[train_mask],
                    targets[train_mask],
                    chunk_features[validation_mask],
                    active_chunks[validation_mask],
                    targets[validation_mask],
                    hidden_width=hidden_width,
                    learning_rate=learning_rate,
                    epochs=200,
                    patience=20,
                    rng=np.random.default_rng(
                        np.random.SeedSequence([20260811, 37, hidden_width, seed_offset])
                    ),
                )
                predictions = lstm_chunk_average_predict(
                    result.parameters,
                    chunk_features[validation_mask],
                    active_chunks[validation_mask],
                )
                metrics = regression_metrics(actual, predictions, entities)
                metrics["n"] = float(actual.size)
                candidate_id = (
                    f"numpy_lstm_width_{hidden_width}_lr_{learning_rate:g}_seed_{seed_offset}"
                )
                parameter_count = (
                    embedding_width * 4 * hidden_width
                    + hidden_width * 4 * hidden_width
                    + 4 * hidden_width
                    + hidden_width
                    + 1
                )
                candidate_records.append(
                    _candidate_record(
                        candidate_id,
                        "numpy_lstm",
                        {
                            "hidden_width": hidden_width,
                            "learning_rate": learning_rate,
                            "seed_offset": seed_offset,
                            "epochs": 200,
                            "patience": 20,
                            "feature_scope": "previous_primary_document_only",
                            "chunk_length": 512,
                            "maximum_chunks": 8,
                            "chunk_aggregation": "mean_token_embedding_per_chunk_then_mean_chunk_predictions",
                            "token_embedding_width": embedding_width,
                            "token_embedding_seed": 20260811,
                            "active_chunk_average": True,
                        },
                        metrics,
                        parameter_count,
                        time.perf_counter() - started,
                    )
                )
                prediction_store[candidate_id] = predictions

    # These are fixed-encoder probes, not end-to-end sequence learners.  They
    # are reported for diagnostics but are excluded from nominee selection.
    sequence_hashes = np.asarray(
        [text_token_hash_sequence(path) for path in document_paths], dtype=np.int64
    )
    for channel_width in (16, 32):
        for kernel_size in (3, 5):
            for seed_offset in (0, 1, 2):
                started = time.perf_counter()
                encoder_rng = np.random.default_rng(
                    np.random.SeedSequence([20260811, 34, channel_width, kernel_size, seed_offset])
                )
                embeddings = token_embedding(sequence_hashes, 16, seed=20260811 + seed_offset)
                kernels = encoder_rng.normal(
                    scale=1.0 / np.sqrt(16.0), size=(kernel_size, 16, channel_width)
                )
                encoded = temporal_convolution_encode(embeddings, kernels, np.zeros(channel_width))
                result = train_mlp(
                    encoded[train_mask],
                    targets[train_mask],
                    encoded[validation_mask],
                    targets[validation_mask],
                    hidden_width=16,
                    learning_rate=0.003,
                    epochs=200,
                    patience=20,
                    rng=np.random.default_rng(np.random.SeedSequence([20260811, 34, seed_offset])),
                )
                predictions = mlp_predict(result.parameters, encoded[validation_mask])
                metrics = regression_metrics(actual, predictions, entities)
                metrics["n"] = float(actual.size)
                candidate_id = f"numpy_tcn_probe_channels_{channel_width}_kernel_{kernel_size}_seed_{seed_offset}"
                parameter_count = (
                    kernels.size
                    + channel_width
                    + result.parameters.input_weights.size
                    + result.parameters.hidden_bias.size
                    + result.parameters.output_weights.size
                    + 1
                )
                candidate_records.append(
                    _candidate_record(
                        candidate_id,
                        "numpy_tcn",
                        {
                            "channel_width": channel_width,
                            "kernel_size": kernel_size,
                            "seed_offset": seed_offset,
                            "encoder_trainable": False,
                            "readout": "numpy_mlp",
                            "sequence_length": 64,
                        },
                        metrics,
                        parameter_count,
                        time.perf_counter() - started,
                        selection_eligible=False,
                    )
                )
                prediction_store[candidate_id] = predictions

    for model_width in (16, 32):
        for attention_heads in (1, 2):
            for seed_offset in (0, 1, 2):
                started = time.perf_counter()
                embeddings = token_embedding(
                    sequence_hashes, model_width, seed=20260811 + seed_offset
                )
                attention_rng = np.random.default_rng(
                    np.random.SeedSequence(
                        [20260811, 35, model_width, attention_heads, seed_offset]
                    )
                )
                head_outputs = []
                for _ in range(attention_heads):
                    matrices = [
                        attention_rng.normal(
                            scale=1.0 / np.sqrt(float(model_width)),
                            size=(model_width, model_width),
                        )
                        for _ in range(3)
                    ]
                    output, _ = self_attention(embeddings, *matrices, causal=True)
                    head_outputs.append(output.mean(axis=1))
                encoded = np.mean(np.stack(head_outputs, axis=0), axis=0)
                result = train_mlp(
                    encoded[train_mask],
                    targets[train_mask],
                    encoded[validation_mask],
                    targets[validation_mask],
                    hidden_width=16,
                    learning_rate=0.003,
                    epochs=200,
                    patience=20,
                    rng=np.random.default_rng(np.random.SeedSequence([20260811, 35, seed_offset])),
                )
                predictions = mlp_predict(result.parameters, encoded[validation_mask])
                metrics = regression_metrics(actual, predictions, entities)
                metrics["n"] = float(actual.size)
                candidate_id = f"numpy_attention_probe_width_{model_width}_heads_{attention_heads}_seed_{seed_offset}"
                parameter_count = (
                    attention_heads * 3 * model_width * model_width
                    + result.parameters.input_weights.size
                    + result.parameters.hidden_bias.size
                    + result.parameters.output_weights.size
                    + 1
                )
                candidate_records.append(
                    _candidate_record(
                        candidate_id,
                        "numpy_small_self_attention",
                        {
                            "model_width": model_width,
                            "attention_heads": attention_heads,
                            "seed_offset": seed_offset,
                            "encoder_trainable": False,
                            "readout": "numpy_mlp",
                            "sequence_length": 64,
                            "causal": True,
                        },
                        metrics,
                        parameter_count,
                        time.perf_counter() - started,
                        selection_eligible=False,
                    )
                )
                prediction_store[candidate_id] = predictions

    # Audit the generalization axis that the locked outer uses.  The two
    # development company folds are evaluated in both directions so that the
    # nominee is not tied to an arbitrary remainder assignment.
    axis_baseline_results: dict[str, dict[str, dict[str, float]]] = {"time": baseline_results}
    axis_candidate_records: dict[str, list[CandidateMetrics]] = {"time": candidate_records}
    axis_prediction_store: dict[str, dict[str, np.ndarray]] = {"time": prediction_store}
    axis_actuals: dict[str, np.ndarray] = {"time": actual}
    axis_entity_values: dict[str, np.ndarray] = {"time": entities}
    axis_baseline_predictions: dict[str, dict[str, np.ndarray]] = {"time": baseline_predictions}
    axis_specs = {
        "company_mod_1_to_2": (
            development["cik"].to_numpy() % 3 == 1,
            development["cik"].to_numpy() % 3 == 2,
            41,
        ),
        "company_mod_2_to_1": (
            development["cik"].to_numpy() % 3 == 2,
            development["cik"].to_numpy() % 3 == 1,
            42,
        ),
    }
    axis_metadata: dict[str, dict[str, int | str]] = {
        "time": {
            "training_rows": int(train_mask.sum()),
            "validation_rows": int(validation_mask.sum()),
            "training_companies": int(development.loc[train_mask, "cik"].nunique()),
            "validation_companies": int(development.loc[validation_mask, "cik"].nunique()),
        }
    }
    for axis_name, (axis_train_mask, axis_validation_mask, seed_namespace) in axis_specs.items():
        axis_train = development.loc[axis_train_mask]
        axis_validation = development.loc[axis_validation_mask]
        axis_actual = axis_validation["target_log_change"].to_numpy(dtype=float)
        axis_entities = axis_validation["cik"].astype(str).to_numpy()
        axis_baselines: dict[str, dict[str, float]] = {}
        for name in BASELINE_NAMES:
            axis_predictions = _baseline_predictions(axis_train, axis_validation, name)
            axis_metrics = regression_metrics(axis_actual, axis_predictions, axis_entities)
            axis_metrics["n"] = float(axis_actual.size)
            axis_baselines[name] = axis_metrics
        axis_records, axis_predictions = _evaluate_selection_axis(
            axis_name=axis_name,
            seed_namespace=seed_namespace,
            train_mask=axis_train_mask,
            validation_mask=axis_validation_mask,
            numeric_values=numeric_values,
            targets=targets,
            actual=axis_actual,
            entities=axis_entities,
            document_paths=document_paths,
            chunk_features=chunk_features,
            active_chunks=active_chunks,
        )
        axis_baseline_results[axis_name] = axis_baselines
        axis_candidate_records[axis_name] = axis_records
        axis_prediction_store[axis_name] = axis_predictions
        axis_actuals[axis_name] = axis_actual
        axis_entity_values[axis_name] = axis_entities
        axis_baseline_predictions[axis_name] = {
            name: _baseline_predictions(axis_train, axis_validation, name)
            for name in BASELINE_NAMES
        }
        axis_metadata[axis_name] = {
            "training_rows": int(axis_train_mask.sum()),
            "validation_rows": int(axis_validation_mask.sum()),
            "training_companies": int(axis_train["cik"].nunique()),
            "validation_companies": int(axis_validation["cik"].nunique()),
        }

    axis_gate_results: dict[str, dict[str, dict[str, object]]] = {}
    for axis_name, records in axis_candidate_records.items():
        baseline_metric_dict = {
            name: dict(metrics) for name, metrics in axis_baseline_results[axis_name].items()
        }
        axis_gate_results[axis_name] = {
            record.candidate_id: selection_gate(
                {
                    "mae": record.mae,
                    "median_absolute_error": record.median_absolute_error,
                    "company_macro_mae": record.company_macro_mae,
                },
                baseline_metric_dict,
            )
            for record in records
            if record.selection_eligible
        }
    gate_results: dict[str, dict[str, object]] = {}
    for record in candidate_records:
        time_gate = axis_gate_results["time"].get(record.candidate_id, {"accepted": False})
        company_gates = {
            axis_name: axis_gate_results[axis_name].get(record.candidate_id, {"accepted": False})
            for axis_name in axis_specs
        }
        gate_results[record.candidate_id] = {
            **time_gate,
            "accepted": bool(
                time_gate.get("accepted", False)
                and all(gate.get("accepted", False) for gate in company_gates.values())
            ),
            "axis_gates": {"time": time_gate, **company_gates},
        }
    ordered = sorted(
        candidate_records,
        key=lambda record: (
            record.mae,
            record.median_absolute_error,
            record.parameter_count,
            record.candidate_id,
        ),
    )
    accepted_overall = [
        record
        for record in ordered
        if record.selection_eligible and gate_results[record.candidate_id]["accepted"]
    ]
    overall = accepted_overall[0] if accepted_overall else None
    tfidf_records = [record for record in candidate_records if record.family == "tfidf_ridge"]
    best_tfidf = min(
        tfidf_records,
        key=lambda record: (record.mae, record.median_absolute_error, record.parameter_count),
    )
    best_tfidf_by_axis = {
        axis_name: min(
            (record for record in records if record.family == "tfidf_ridge"),
            key=lambda record: (record.mae, record.median_absolute_error, record.parameter_count),
        )
        for axis_name, records in axis_candidate_records.items()
    }
    neural_gate_results: dict[str, dict[str, object]] = {}
    for record in candidate_records:
        if record.selection_eligible and record.family in NEURAL_FAMILIES:
            axis_gates: dict[str, dict[str, object]] = {}
            for axis_name, records in axis_candidate_records.items():
                candidate = next(
                    (
                        candidate
                        for candidate in records
                        if candidate.candidate_id == record.candidate_id
                    ),
                    None,
                )
                if candidate is None:
                    axis_gates[axis_name] = {"accepted": False, "reason": "candidate_missing"}
                    continue
                axis_gates[axis_name] = selection_gate(
                    {
                        "mae": candidate.mae,
                        "median_absolute_error": candidate.median_absolute_error,
                        "company_macro_mae": candidate.company_macro_mae,
                    },
                    {"tfidf_ridge": asdict(best_tfidf_by_axis[axis_name])},
                )
            neural_gate_results[record.candidate_id] = {
                "accepted": all(gate.get("accepted", False) for gate in axis_gates.values()),
                "axis_gates": axis_gates,
            }
    accepted_neural = [
        record
        for record in candidate_records
        if record.candidate_id in neural_gate_results
        and neural_gate_results[record.candidate_id]["accepted"]
    ]
    neural = min(
        accepted_neural,
        key=lambda record: (
            record.mae,
            record.median_absolute_error,
            record.parameter_count,
            record.candidate_id,
        ),
        default=None,
    )

    bootstrap: dict[str, Any] = {}
    if overall is not None:
        bootstrap["overall_vs_primary_baseline"] = {
            axis_name: asdict(
                paired_company_bootstrap(
                    axis_actuals[axis_name],
                    axis_prediction_store[axis_name][overall.candidate_id],
                    axis_baseline_predictions[axis_name][primary_baseline],
                    axis_entity_values[axis_name],
                )
            )
            for axis_name in axis_candidate_records
        }
    if neural is not None:
        bootstrap["neural_vs_tfidf_ridge"] = {
            axis_name: asdict(
                paired_company_bootstrap(
                    axis_actuals[axis_name],
                    axis_prediction_store[axis_name][neural.candidate_id],
                    axis_prediction_store[axis_name][best_tfidf_by_axis[axis_name].candidate_id],
                    axis_entity_values[axis_name],
                )
            )
            for axis_name in axis_candidate_records
        }

    payload = {
        "schema_version": "b9-development-tournament-v1",
        "status": "candidate_nominee_available" if overall is not None else "no_model_selected",
        "outer_accessed": False,
        "outer_access_policy": "counted only; no outer rows, text, features, or predictions were read",
        "input_provenance": input_hashes,
        "code_commit": _git_commit(),
        "runner_sha256": _digest(Path(__file__).resolve()),
        "partitions": {
            key: partition_info[key]
            for key in (
                "outer_rows",
                "development_rows",
                "inner_train_rows",
                "inner_validation_rows",
            )
        },
        "selection_axis_duplicate_family_counts": partition_info[
            "cross_partition_duplicate_families_by_axis"
        ],
        "selection_axes": axis_metadata,
        "baseline_results": baseline_results,
        "baseline_results_by_axis": axis_baseline_results,
        "primary_baseline_frozen": primary_baseline,
        "candidate_results": [asdict(record) for record in candidate_records],
        "candidate_results_by_axis": {
            axis_name: [asdict(record) for record in records]
            for axis_name, records in axis_candidate_records.items()
        },
        "selection_gates": gate_results,
        "selection_gates_by_axis": axis_gate_results,
        "neural_selection_gates": neural_gate_results,
        "nominees": {
            "overall": asdict(overall) if overall is not None else None,
            "neural": asdict(neural) if neural is not None else None,
            "best_tfidf_ridge": asdict(best_tfidf),
            "best_tfidf_ridge_by_axis": {
                axis_name: asdict(record) for axis_name, record in best_tfidf_by_axis.items()
            },
        },
        "inner_validation_bootstrap": bootstrap,
        "implemented_families": [
            "numeric_ridge",
            "tfidf_ridge",
            "numpy_mlp",
            "numpy_lstm",
            "joint_text_numeric_mlp",
            "numpy_tcn_probe",
            "numpy_small_self_attention_probe",
        ],
        "deferred_families": [],
        "diagnostic_only_families": ["numpy_tcn", "numpy_small_self_attention"],
        "text_audit": {
            "development_document_coverage": 1.0,
            "development_duplicate_family_count": int(
                frame.loc[frame["development"], "normalized_text_sha256"].duplicated().sum()
            ),
            "cross_partition_duplicate_family_count": int(
                sum(partition_info["cross_partition_duplicate_families_by_axis"].values())
            ),
            "cross_partition_duplicate_family_count_by_axis": partition_info[
                "cross_partition_duplicate_families_by_axis"
            ],
            "target_document_accessed": False,
            "outer_document_accessed": False,
            "chunk_length": 512,
            "maximum_chunks": 8,
        },
        "selection_note": "Nominee requires the time and both company-disjoint development axes; this is pre-outer evidence only. Outer remains unopened and no production decision is made.",
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-artifact", required=True, type=Path)
    parser.add_argument("--provenance-sidecar", required=True, type=Path)
    parser.add_argument("--normalized-root", required=True, type=Path)
    parser.add_argument("--preanalysis-contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    payload = run_tournament(args)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "outer_accessed": payload["outer_accessed"],
                "development_rows": payload["partitions"]["development_rows"],
                "inner_validation_rows": payload["partitions"]["inner_validation_rows"],
                "candidate_count": sum(
                    len(records) for records in payload["candidate_results_by_axis"].values()
                ),
                "candidate_count_by_axis": {
                    axis: len(records)
                    for axis, records in payload["candidate_results_by_axis"].items()
                },
                "overall_nominee": payload["nominees"]["overall"],
                "neural_nominee": payload["nominees"]["neural"],
                "output": str(args.output.expanduser().resolve()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
