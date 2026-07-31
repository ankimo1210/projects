#!/usr/bin/env python3
"""Validate the local Genequest health-risk snapshot."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
JSON_PATH = DATA_DIR / "health_risks.json"
CSV_PATH = DATA_DIR / "health_risks.csv"
MARKDOWN_PATH = DATA_DIR / "health_risks.md"
GENOTYPE_CSV_PATH = DATA_DIR / "genotypes.csv"
GENOTYPE_VERIFICATION_PATH = DATA_DIR / "genotype_verification.json"
MANIFEST_PATH = DATA_DIR / "manifest.json"

REQUIRED_FIELDS = {
    "id",
    "illness",
    "category",
    "risk_level",
    "short_description",
    "source_url",
    "full_text",
    "genotype_capture_status",
    "genotype_source_comparisons",
    "genotype_verified_at",
    "markers",
}

ALLOWED_GENOTYPE_STATUSES = {
    "verified",
    "not_applicable_pgs",
    "no_result",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    required_files = (
        JSON_PATH,
        CSV_PATH,
        MARKDOWN_PATH,
        GENOTYPE_CSV_PATH,
        GENOTYPE_VERIFICATION_PATH,
        MANIFEST_PATH,
    )
    missing = [str(path) for path in required_files if not path.is_file()]
    assert not missing, f"Missing snapshot files: {missing}"

    records = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    assert isinstance(records, list) and records, "JSON snapshot has no records"

    ids = [str(record.get("id", "")) for record in records]
    assert all(ids), "At least one JSON record has no id"
    assert len(ids) == len(set(ids)), "JSON record ids are not unique"

    for record in records:
        missing_fields = REQUIRED_FIELDS - record.keys()
        assert not missing_fields, (
            f"Record {record.get('id')} is missing fields: {sorted(missing_fields)}"
        )
        assert str(record["illness"]).strip(), f"Record {record['id']} has no illness"
        assert str(record["full_text"]).strip(), (
            f"Record {record['id']} has no detail text"
        )
        status = record["genotype_capture_status"]
        assert status in ALLOWED_GENOTYPE_STATUSES, (
            f"Record {record['id']} has invalid genotype status: {status}"
        )

        markers = record["markers"]
        assert isinstance(markers, list), f"Record {record['id']} markers is not a list"
        if status == "verified":
            assert all(record["genotype_source_comparisons"].values()), (
                f"Record {record['id']} differs from the verified source"
            )
            assert markers, f"Verified record {record['id']} has no markers"
            for marker in markers:
                assert marker["snp"], f"Record {record['id']} marker has no SNP"
                assert marker["genotype"], (
                    f"Record {record['id']} marker has no genotype"
                )
                assert marker["effect"] is not None, (
                    f"Record {record['id']} marker has no matched effect"
                )
                options = {
                    option["genotype"]: option["effect"]
                    for option in marker["genotype_options"]
                }
                assert options.get(marker["genotype"]) == marker["effect"], (
                    f"Record {record['id']} genotype/effect does not match its table"
                )
        elif status == "not_applicable_pgs":
            assert record["has_pgs"], (
                f"Record {record['id']} is marked PGS but has_pgs is false"
            )
            assert not markers, f"PGS record {record['id']} unexpectedly has markers"
        elif status == "no_result":
            assert all(record["genotype_source_comparisons"].values()), (
                f"No-result record {record['id']} differs from the verified source"
            )
            assert not any(marker["genotype"] for marker in markers), (
                f"No-result record {record['id']} unexpectedly has a genotype"
            )

    with CSV_PATH.open(encoding="utf-8-sig", newline="") as file:
        csv_rows = list(csv.DictReader(file))
    assert len(csv_rows) == len(records), "CSV and JSON record counts differ"
    assert {row["id"] for row in csv_rows} == set(ids), "CSV and JSON ids differ"
    records_by_id = {str(record["id"]): record for record in records}
    for row in csv_rows:
        record = records_by_id[row["id"]]
        captured_markers = [
            marker for marker in record["markers"] if marker["genotype"]
        ]
        assert row["genotype_capture_status"] == record["genotype_capture_status"], (
            f"CSV genotype status differs for record {row['id']}"
        )
        assert int(row["genotype_count"]) == len(captured_markers), (
            f"CSV genotype count differs for record {row['id']}"
        )
        assert row["genotypes"] == "|".join(
            marker["genotype"] for marker in captured_markers
        ), f"CSV genotypes differ for record {row['id']}"
        assert row["snps"] == "|".join(
            marker["snp"] for marker in record["markers"] if marker["snp"]
        ), f"CSV SNPs differ for record {row['id']}"

    with GENOTYPE_CSV_PATH.open(encoding="utf-8-sig", newline="") as file:
        genotype_rows = list(csv.DictReader(file))
    expected_marker_count = sum(len(record["markers"]) for record in records)
    assert len(genotype_rows) == expected_marker_count, (
        "Genotype CSV and JSON marker counts differ"
    )
    marker_keys = [
        (row["illness_id"], row["marker_index"]) for row in genotype_rows
    ]
    assert len(marker_keys) == len(set(marker_keys)), (
        "Genotype CSV marker keys are not unique"
    )
    expected_markers = {
        (str(record["id"]), str(marker["marker_index"])): (
            record,
            marker,
        )
        for record in records
        for marker in record["markers"]
    }
    for row in genotype_rows:
        record, marker = expected_markers[
            (row["illness_id"], row["marker_index"])
        ]
        expected_values = {
            "illness": record["illness"],
            "capture_status": record["genotype_capture_status"],
            "snp": marker["snp"] or "",
            "genotype": marker["genotype"] or "",
            "effect_header": marker["effect_header"] or "",
            "effect": marker["effect"] or "",
        }
        for field, expected_value in expected_values.items():
            assert row[field] == expected_value, (
                f"Genotype CSV {field} differs for "
                f"{row['illness_id']} marker {row['marker_index']}"
            )

    verification = json.loads(
        GENOTYPE_VERIFICATION_PATH.read_text(encoding="utf-8")
    )
    status_counts = {
        status: sum(
            record["genotype_capture_status"] == status for record in records
        )
        for status in ALLOWED_GENOTYPE_STATUSES
    }
    assert verification["record_count"] == len(records), (
        "Genotype verification record count differs"
    )
    assert verification["status_counts"] == status_counts, (
        "Genotype verification status counts differ"
    )
    assert verification["mismatch_count"] == 0, (
        "Genotype verification contains mismatches"
    )
    assert verification["browser_error_count"] == 0, (
        "Genotype verification contains browser errors"
    )

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["record_count"] == len(records), "Manifest count differs"

    expected_hashes = manifest["sha256"]
    for filename, expected_hash in expected_hashes.items():
        path = DATA_DIR / filename
        assert sha256(path) == expected_hash, (
            f"SHA-256 mismatch: {filename}"
        )

    print(
        "Genequest snapshot is valid: "
        f"{len(records)} records, {len(set(ids))} unique ids, "
        f"{verification['captured_genotype_count']} verified genotypes."
    )


if __name__ == "__main__":
    main()
