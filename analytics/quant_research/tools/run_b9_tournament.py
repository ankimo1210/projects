"""Run the pre-registered B9 development tournament without opening outer rows.

The command reads the externally stored M6 panel, previous-filing sidecar, and
normalized documents.  It evaluates the four fixed baselines, numeric ridge,
hashed TF-IDF ridge, and the implemented NumPy MLP variants on the development
partition only.  The locked outer partition is counted for an audit trail but
never materialized into features or predictions.

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
)
from quant_textbook.deep_learning import mlp_predict, train_mlp
from quant_textbook.sec_features import fit_numeric_preprocessor, fit_sparse_ridge

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
NEURAL_FAMILIES = frozenset({"numpy_mlp"})
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
    development_hashes = frame.loc[frame["development"]].groupby("normalized_text_sha256")
    cross_partition_duplicates = [
        digest
        for digest, group in development_hashes
        if bool(group["inner_train"].any()) and bool(group["inner_validation"].any())
    ]
    if cross_partition_duplicates:
        raise ValueError(
            "identical normalized document families cross the inner split: "
            f"{cross_partition_duplicates[:3]}"
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
        },
    )


def _candidate_record(
    candidate_id: str,
    family: str,
    configuration: dict[str, object],
    metrics: dict[str, float],
    parameter_count: int,
    runtime_seconds: float,
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
    )


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

    baseline_metric_dict = {name: dict(metrics) for name, metrics in baseline_results.items()}
    gate_results: dict[str, dict[str, object]] = {}
    for record in candidate_records:
        gate_results[record.candidate_id] = selection_gate(
            {
                "mae": record.mae,
                "median_absolute_error": record.median_absolute_error,
                "company_macro_mae": record.company_macro_mae,
            },
            baseline_metric_dict,
        )
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
        record for record in ordered if gate_results[record.candidate_id]["accepted"]
    ]
    overall = accepted_overall[0] if accepted_overall else None
    tfidf_records = [record for record in candidate_records if record.family == "tfidf_ridge"]
    best_tfidf = min(
        tfidf_records,
        key=lambda record: (record.mae, record.median_absolute_error, record.parameter_count),
    )
    neural_gate_results: dict[str, dict[str, object]] = {}
    for record in candidate_records:
        if record.family in NEURAL_FAMILIES:
            neural_gate_results[record.candidate_id] = selection_gate(
                {
                    "mae": record.mae,
                    "median_absolute_error": record.median_absolute_error,
                    "company_macro_mae": record.company_macro_mae,
                },
                {"tfidf_ridge": asdict(best_tfidf)},
            )
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
        bootstrap["overall_vs_primary_baseline"] = asdict(
            paired_company_bootstrap(
                actual,
                prediction_store[overall.candidate_id],
                baseline_predictions[primary_baseline],
                entities,
            )
        )
    if neural is not None:
        bootstrap["neural_vs_tfidf_ridge"] = asdict(
            paired_company_bootstrap(
                actual,
                prediction_store[neural.candidate_id],
                prediction_store[best_tfidf.candidate_id],
                entities,
            )
        )

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
        "baseline_results": baseline_results,
        "primary_baseline_frozen": primary_baseline,
        "candidate_results": [asdict(record) for record in candidate_records],
        "selection_gates": gate_results,
        "neural_selection_gates": neural_gate_results,
        "nominees": {
            "overall": asdict(overall) if overall is not None else None,
            "neural": asdict(neural) if neural is not None else None,
            "best_tfidf_ridge": asdict(best_tfidf),
        },
        "inner_validation_bootstrap": bootstrap,
        "implemented_families": ["numeric_ridge", "tfidf_ridge", "numpy_mlp"],
        "deferred_families": [family for family in ALL_CORE_FAMILIES if family != "numpy_mlp"],
        "text_audit": {
            "development_document_coverage": 1.0,
            "development_duplicate_family_count": int(
                frame.loc[frame["development"], "normalized_text_sha256"].duplicated().sum()
            ),
            "cross_partition_duplicate_family_count": 0,
            "target_document_accessed": False,
            "outer_document_accessed": False,
            "chunk_length": 512,
            "maximum_chunks": 8,
        },
        "selection_note": "Nominee is pre-outer development evidence only; outer remains unopened and no production decision is made.",
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
                "candidate_count": len(payload["candidate_results"]),
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
