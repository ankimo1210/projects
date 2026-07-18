#!/usr/bin/env python3
"""Validate that the curated free tier refers to real, balanced content IDs."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "WSET" / "FreeContentManifest.json"
DEFAULT_QUESTION_PACK = ROOT / "WSET" / "QuestionData" / "question_pack.json"
DEFAULT_WRITTEN_PACK = ROOT / "WSET" / "QuestionData" / "written_question_pack.json"
DEFAULT_REFERENCE_PACK = ROOT / "WSET" / "ReferenceData" / "reference_pack.json"
DEFAULT_MAP_PACK = ROOT / "WSET" / "MapData" / "region_map_pack.json"


class FreeContentManifestError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FreeContentManifestError(f"{path.name} must contain an object")
    return value


def _unique_ids(manifest: dict[str, Any], key: str, expected_count: int) -> list[str]:
    values = manifest.get(key)
    if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values):
        raise FreeContentManifestError(f"{key} must be a non-empty string array")
    if len(values) != expected_count or len(set(values)) != len(values):
        raise FreeContentManifestError(f"{key} must contain {expected_count} unique IDs")
    return values


def validate_manifest(
    manifest_path: Path = DEFAULT_MANIFEST,
    question_pack_path: Path = DEFAULT_QUESTION_PACK,
    written_pack_path: Path = DEFAULT_WRITTEN_PACK,
    reference_pack_path: Path = DEFAULT_REFERENCE_PACK,
    map_pack_path: Path = DEFAULT_MAP_PACK,
) -> dict[str, Any]:
    manifest = _load(manifest_path)
    if manifest.get("schemaVersion") != 1 or not manifest.get("selectionVersion"):
        raise FreeContentManifestError("manifest schemaVersion/selectionVersion is invalid")

    mcq_ids = _unique_ids(manifest, "multipleChoiceQuestionIDs", 100)
    written_ids = _unique_ids(manifest, "writtenQuestionIDs", 1)
    term_ids = _unique_ids(manifest, "glossaryTermIDs", 60)
    countries = _unique_ids(manifest, "mapCountries", 1)

    questions = _load(question_pack_path).get("questions", [])
    written_questions = _load(written_pack_path).get("questions", [])
    terms = _load(reference_pack_path).get("terms", [])
    maps = _load(map_pack_path).get("maps", [])
    question_by_id = {item.get("id"): item for item in questions}
    written_by_id = {item.get("id"): item for item in written_questions}
    term_by_id = {item.get("id"): item for item in terms}

    missing_mcq = set(mcq_ids) - set(question_by_id)
    missing_written = set(written_ids) - set(written_by_id)
    missing_terms = set(term_ids) - set(term_by_id)
    available_countries = {item.get("country") for item in maps}
    missing_countries = set(countries) - available_countries
    if missing_mcq or missing_written or missing_terms or missing_countries:
        raise FreeContentManifestError(
            "manifest has dangling IDs: "
            f"mcq={sorted(missing_mcq)}, written={sorted(missing_written)}, "
            f"terms={sorted(missing_terms)}, maps={sorted(missing_countries)}"
        )

    if any(question_by_id[item]["studyMode"] != "multiple_choice" for item in mcq_ids):
        raise FreeContentManifestError("multipleChoiceQuestionIDs includes a non-MCQ")
    if any(written_by_id[item]["studyMode"] != "written_answer" for item in written_ids):
        raise FreeContentManifestError("writtenQuestionIDs includes a non-written question")

    outcome_counts = Counter(question_by_id[item]["learningOutcome"] for item in mcq_ids)
    expected_outcomes = {f"u1_lo{number}" for number in range(1, 6)}
    if set(outcome_counts) != expected_outcomes or set(outcome_counts.values()) != {20}:
        raise FreeContentManifestError("free MCQs must include 20 questions from each LO")

    category_counts = Counter(term_by_id[item]["category"] for item in term_ids)
    if len(category_counts) < 8:
        raise FreeContentManifestError("free glossary must span at least eight categories")

    return {
        "selectionVersion": manifest["selectionVersion"],
        "multipleChoiceCount": len(mcq_ids),
        "writtenCount": len(written_ids),
        "glossaryCount": len(term_ids),
        "learningOutcomeCounts": dict(sorted(outcome_counts.items())),
        "glossaryCategoryCount": len(category_counts),
    }


def main() -> None:
    summary = validate_manifest()
    print(
        "Validated free content manifest "
        f"{summary['selectionVersion']}: {summary['multipleChoiceCount']} MCQ, "
        f"{summary['writtenCount']} written, {summary['glossaryCount']} glossary terms"
    )


if __name__ == "__main__":
    main()
