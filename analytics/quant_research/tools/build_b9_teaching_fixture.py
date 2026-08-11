"""Build a compact development-only B9 fixture from external SEC artifacts.

The output contains no filing text, accession, CIK, or locked outer-test row.
Only lossy many-to-one token hashes, real numeric features, targets, document hashes,
and source artifact digests are retained for reproducible textbook laboratories.
"""

from __future__ import annotations

import argparse
import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

TOKEN_PATTERN = re.compile(r"[a-z]+|[0-9]+", re.ASCII)
SCHEMA_VERSION = "sec-b9-teaching-fixture-v1"
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-artifact", required=True, type=Path)
    parser.add_argument("--provenance-sidecar", required=True, type=Path)
    parser.add_argument("--normalized-root", required=True, type=Path)
    parser.add_argument("--preanalysis-contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--training-rows", type=int, default=192)
    parser.add_argument("--validation-rows", type=int, default=64)
    parser.add_argument("--sequence-length", type=int, default=128)
    parser.add_argument("--hash-buckets", type=int, default=4096)
    return parser


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _stable_rank(row: pd.Series, *, partition: str) -> str:
    key = (
        f"{partition}|{int(row['cik'])}|{row['previous_period_end'].date()}|"
        f"{row['target_period_end'].date()}"
    )
    return sha256(key.encode("ascii")).hexdigest()


def _select_partition(frame: pd.DataFrame, *, partition: str, count: int) -> pd.DataFrame:
    if len(frame) < count:
        raise ValueError(f"{partition} has only {len(frame)} rows; requested {count}")
    ranked = frame.assign(
        _rank=[_stable_rank(row, partition=partition) for _, row in frame.iterrows()]
    )
    return ranked.sort_values("_rank").head(count).drop(columns="_rank")


def _numeric_features(row: pd.Series, full_panel: pd.DataFrame) -> list[float | None]:
    known_at = row["known_at"]
    history = full_panel.loc[
        (full_panel["cik"] == row["cik"]) & (full_panel["target_available_date"] < known_at)
    ].sort_values(["target_available_date", "target_period_end"])
    history_target = history["target_log_change"].to_numpy(dtype=float)
    lag_1 = float(history_target[-1]) if history_target.size >= 1 else None
    lag_2 = float(history_target[-2]) if history_target.size >= 2 else None
    expanding_mean = float(history_target.mean()) if history_target.size else None
    expanding_std = float(history_target.std(ddof=1)) if history_target.size >= 2 else None
    quarter = int(row["target_period_end"].quarter)
    return [
        float(np.log(row["previous_assets_usd"])),
        lag_1,
        lag_2,
        expanding_mean,
        expanding_std,
        float(history_target.size),
        float((row["known_at"] - row["previous_period_end"]).days),
        float((row["target_period_end"] - row["previous_period_end"]).days),
        *[float(quarter == value) for value in range(1, 5)],
    ]


def _token_hashes(text: str, *, sequence_length: int, hash_buckets: int) -> list[int]:
    raw_tokens = TOKEN_PATTERN.findall(text.casefold())
    if not raw_tokens:
        raise ValueError("normalized filing has no auditable tokens")
    normalized = ["<NUM>" if token.isdigit() else token for token in raw_tokens]
    if len(normalized) >= sequence_length:
        indexes = np.linspace(0, len(normalized) - 1, sequence_length, dtype=int)
        selected = [normalized[index] for index in indexes]
    else:
        selected = [normalized[index % len(normalized)] for index in range(sequence_length)]
    return [
        int.from_bytes(sha256(token.encode("utf-8")).digest()[:8], "big") % hash_buckets + 1
        for token in selected
    ]


def build_fixture(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    if min(args.training_rows, args.validation_rows, args.sequence_length, args.hash_buckets) <= 0:
        raise ValueError("row counts, sequence length, and hash buckets must be positive")
    panel_artifact = _read_object(args.panel_artifact)
    sidecar = _read_object(args.provenance_sidecar)
    normalized_manifest_path = args.normalized_root / "manifest.json"
    normalized_manifest = _read_object(normalized_manifest_path)
    contract = _read_object(args.preanalysis_contract)
    if sidecar.get("schema_version") != "b9-previous-filing-provenance-v1":
        raise ValueError("unsupported previous filing sidecar")
    if normalized_manifest.get("schema_version") != "b9-sec-normalized-text-v1":
        raise ValueError("unsupported normalized text manifest")

    panel = pd.DataFrame(panel_artifact["panel"]["rows"])
    for column in (
        "previous_period_end",
        "target_period_end",
        "previous_available_date",
        "target_available_date",
        "known_at",
    ):
        panel[column] = pd.to_datetime(panel[column], errors="raise")
    outer_cutoff = pd.Timestamp(contract["splits"]["outer_time_cutoff"])
    inner_cutoff = pd.Timestamp(contract["splits"]["inner_validation"]["time_cutoff"])
    development = panel.loc[
        (panel["target_available_date"] < outer_cutoff) & (panel["cik"] % 3 != 0)
    ]
    inner_train = development.loc[development["target_available_date"] < inner_cutoff]
    inner_validation = development.loc[development["target_available_date"] >= inner_cutoff]
    selected = pd.concat(
        [
            _select_partition(
                inner_train, partition="inner_train", count=args.training_rows
            ).assign(partition="inner_train"),
            _select_partition(
                inner_validation,
                partition="inner_validation",
                count=args.validation_rows,
            ).assign(partition="inner_validation"),
        ],
        ignore_index=True,
    )

    provenance = pd.DataFrame(sidecar["rows"])
    join_columns = ["cik", "previous_period_end", "target_period_end"]
    for column in join_columns[1:]:
        provenance[column] = pd.to_datetime(provenance[column], errors="raise")
    provenance_columns = [
        *join_columns,
        "previous_accession",
        "target_accession",
    ]
    selected = selected.merge(
        provenance.loc[:, provenance_columns],
        on=join_columns,
        how="left",
        validate="one_to_one",
    )
    if selected["previous_accession"].isna().any():
        raise ValueError("selected fixture rows lack previous filing provenance")
    if (selected["previous_accession"] == selected["target_accession"]).any():
        raise ValueError("target accession leaked into a previous filing feature")

    documents = {row["accession"]: row for row in normalized_manifest["documents"]}
    output_rows: list[dict[str, Any]] = []
    for _, row in selected.iterrows():
        accession = str(row["previous_accession"])
        document = documents.get(accession)
        if document is None:
            raise ValueError(f"normalized manifest lacks previous accession {accession}")
        document_path = (args.normalized_root / document["path"]).resolve()
        if (
            not document_path.is_file()
            or _digest(document_path) != document["normalized_text_sha256"]
        ):
            raise ValueError(f"normalized document integrity failed: {accession}")
        row_key = (
            f"{int(row['cik'])}|{row['previous_period_end'].date()}|"
            f"{row['target_period_end'].date()}"
        )
        output_rows.append(
            {
                "row_id": sha256(("row|" + row_key).encode("ascii")).hexdigest()[:16],
                "entity_id": sha256(f"entity|{int(row['cik'])}".encode("ascii")).hexdigest()[:12],
                "target_available_date": row["target_available_date"].date().isoformat(),
                "partition": row["partition"],
                "numeric_features": _numeric_features(row, panel),
                "token_hashes": _token_hashes(
                    document_path.read_text(encoding="utf-8"),
                    sequence_length=args.sequence_length,
                    hash_buckets=args.hash_buckets,
                ),
                "target": float(row["target_log_change"]),
                "document_sha256": document["normalized_text_sha256"],
            }
        )
    output_rows.sort(
        key=lambda row: (row["partition"], row["target_available_date"], row["row_id"])
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract": (
            "Development-only real SEC-derived teaching fixture; not candidate evaluation; "
            "no raw text, CIK, accession, or locked outer rows."
        ),
        "numeric_feature_names": list(NUMERIC_FEATURE_NAMES),
        "token_hash_contract": (
            "ASCII letters/numeric class; deterministic evenly spaced positions; "
            f"SHA-256 first 64 bits modulo {args.hash_buckets}, plus one"
        ),
        "provenance": {
            "panel_artifact_sha256": _digest(args.panel_artifact),
            "previous_filing_sidecar_sha256": _digest(args.provenance_sidecar),
            "normalized_manifest_sha256": _digest(normalized_manifest_path),
            "preanalysis_contract_sha256": _digest(args.preanalysis_contract),
        },
        "rows": output_rows,
    }
    payload_bytes = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "fixture_sha256": sha256(payload_bytes).hexdigest(),
        "row_count": len(output_rows),
        "training_row_count": sum(row["partition"] == "inner_train" for row in output_rows),
        "validation_row_count": sum(row["partition"] == "inner_validation" for row in output_rows),
        "sequence_length": args.sequence_length,
        "contains_locked_outer_rows": False,
        "contains_raw_or_normalized_text": False,
        "contains_cik_or_accession": False,
        "redistribution_decision": (
            "Commit only compact derived numeric values and lossy token hashes from "
            "public SEC filings; keep source documents and contact configuration external."
        ),
    }
    return payload, manifest


def main() -> None:
    args = _parser().parse_args()
    payload, manifest = build_fixture(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload_bytes = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    args.output.write_bytes(payload_bytes)
    manifest_path = args.output.with_name(args.output.stem + ".manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
