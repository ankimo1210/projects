#!/usr/bin/env python3
"""Validate the local Genequest ancestor snapshot."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"

JSON_PATH = DATA_DIR / "ancestor.json"
SUMMARY_CSV_PATH = DATA_DIR / "ancestor.csv"
JOURNEY_CSV_PATH = DATA_DIR / "ancestor_journey.csv"
REGIONS_CSV_PATH = DATA_DIR / "ancestor_regions.csv"
HAPLOGROUPS_CSV_PATH = DATA_DIR / "ancestor_haplogroups.csv"
MARKDOWN_PATH = DATA_DIR / "ancestor.md"
VERIFICATION_PATH = DATA_DIR / "ancestor_verification.json"
MANIFEST_PATH = DATA_DIR / "ancestor_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main() -> None:
    required_files = (
        JSON_PATH,
        SUMMARY_CSV_PATH,
        JOURNEY_CSV_PATH,
        REGIONS_CSV_PATH,
        HAPLOGROUPS_CSV_PATH,
        MARKDOWN_PATH,
        VERIFICATION_PATH,
        MANIFEST_PATH,
    )
    missing = [str(path) for path in required_files if not path.is_file()]
    assert not missing, f"Missing snapshot files: {missing}"

    snapshot = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    result = snapshot["result"]
    assert str(result["haplogroup"]).strip(), "Haplogroup is missing"
    assert str(result["subgroup"]).strip(), "Subgroup is missing"
    assert result["lineage_scope"] == "ミトコンドリアDNAによる母系系統"
    assert result["birth_estimate"]
    assert result["origin"]
    assert result["diffusion"]
    assert result["distribution"]
    assert str(result["japan_ratio_text"]).strip()
    assert 0 <= float(result["japan_ratio_approx_percent"]) <= 100

    assert len(snapshot["pages"]) == 5, "Unexpected captured page count"
    assert len(snapshot["journey"]) == 5, "Unexpected journey step count"
    assert len(snapshot["regional_rankings"]) == 6, (
        "Unexpected regional ranking count"
    )
    assert len(snapshot["haplogroup_catalog"]) == 23, (
        "Unexpected haplogroup catalog count"
    )
    selected_subgroups = [
        row["subgroup"]
        for row in snapshot["subgroup_comparison"]
        if row["selected"]
    ]
    assert selected_subgroups == [result["subgroup"]], (
        "Selected subgroup does not match the result"
    )

    summary_rows = read_csv(SUMMARY_CSV_PATH)
    assert len(summary_rows) == 1, "Ancestor summary CSV must contain one row"
    assert summary_rows[0]["haplogroup"] == result["haplogroup"]
    assert summary_rows[0]["subgroup"] == result["subgroup"]
    assert len(read_csv(JOURNEY_CSV_PATH)) == len(snapshot["journey"])
    assert len(read_csv(REGIONS_CSV_PATH)) == len(snapshot["regional_rankings"])
    assert len(read_csv(HAPLOGROUPS_CSV_PATH)) == len(
        snapshot["haplogroup_catalog"]
    )

    verification = json.loads(VERIFICATION_PATH.read_text(encoding="utf-8"))
    required_checks = (
        "result_page_group_match",
        "result_page_subgroup_match",
        "detail_page_group_match",
        "detail_page_subgroup_match",
        "public_group_page_match",
        "methodology_confirms_maternal_mtdna",
    )
    for check in required_checks:
        assert verification[check], f"Verification failed: {check}"
    assert verification["missing_fields"] == [], "Required fields are missing"
    assert verification["mismatch_count"] == 0, "Verification contains mismatches"
    assert verification["browser_error_count"] == 0, (
        "Verification contains browser errors"
    )

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["result"]["haplogroup"] == result["haplogroup"]
    assert manifest["result"]["subgroup"] == result["subgroup"]
    assert manifest["page_count"] == len(snapshot["pages"])
    assert manifest["haplogroup_catalog_count"] == len(
        snapshot["haplogroup_catalog"]
    )
    for filename, expected_hash in manifest["sha256"].items():
        assert sha256(DATA_DIR / filename) == expected_hash, (
            f"SHA-256 mismatch: {filename}"
        )

    print(
        "Genequest ancestor snapshot is valid: "
        f"{len(snapshot['pages'])} pages, "
        f"{len(snapshot['journey'])} journey steps, "
        f"{len(snapshot['regional_rankings'])} regional rankings, "
        f"{len(snapshot['haplogroup_catalog'])} catalog groups, "
        "no mismatches."
    )


if __name__ == "__main__":
    main()
