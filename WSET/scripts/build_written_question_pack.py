#!/usr/bin/env python3
"""Build the offline written-answer pack from the canonical JSON source."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "QuestionSources" / "wset_level3_written_questions.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "WSET" / "QuestionData" / "written_question_pack.json"
DEFAULT_REFERENCE_PACK = PROJECT_ROOT / "WSET" / "ReferenceData" / "reference_pack.json"
SCHEMA_VERSION = 1
REVIEW_STATUSES = {"draft", "pending_external_review", "published", "rejected"}
_NON_HUMAN_REVIEWER_PLACEHOLDERS = {
    "AI",
    "生成AI",
    "AI誤答レビュー",
    "AI選択肢論理監査",
}


class WrittenQuestionPackError(ValueError):
    """Raised when written-question content violates the app contract."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def source_display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def review_target_hash(question: dict[str, Any]) -> str:
    """Fingerprint answerable content independently of mutable review state."""

    content = {
        key: value
        for key, value in question.items()
        if key
        not in {
            "reviewStatus",
            "reviewer",
            "reviewedAt",
            "reviewedContentHash",
        }
    }
    metadata = content.get("metadata")
    if isinstance(metadata, dict):
        content["metadata"] = {
            key: value
            for key, value in metadata.items()
            if key not in {"externalReviewRequired", "reviewNotes"}
        }
    return sha256(canonical_json(content))


def required_text(question: dict[str, Any], field: str) -> str:
    value = question.get(field)
    if not isinstance(value, str) or not value.strip():
        raise WrittenQuestionPackError(
            f"{question.get('id', '<unknown>')}: {field} must be non-empty text"
        )
    return value.strip()


def required_string_list(question: dict[str, Any], field: str) -> list[str]:
    value = question.get(field)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise WrittenQuestionPackError(
            f"{question.get('id', '<unknown>')}: {field} must be a string list"
        )
    return list(dict.fromkeys(item.strip() for item in value))


def reference_term_ids(path: Path = DEFAULT_REFERENCE_PACK) -> set[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        terms = payload["terms"]
    except (OSError, KeyError, json.JSONDecodeError) as error:
        raise WrittenQuestionPackError(
            f"Unable to load reference term ids from {path}"
        ) from error
    if not isinstance(terms, list):
        raise WrittenQuestionPackError("Reference pack terms must be a list")
    identifiers = {
        term.get("id")
        for term in terms
        if isinstance(term, dict) and isinstance(term.get("id"), str)
    }
    if len(identifiers) != len(terms):
        raise WrittenQuestionPackError("Reference pack contains invalid or duplicate term ids")
    return identifiers


def reference_pack_source_hash(path: Path = DEFAULT_REFERENCE_PACK) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise WrittenQuestionPackError(
            f"Unable to load reference pack source hash from {path}"
        ) from error
    value = payload.get("sourceHash")
    if not isinstance(value, str) or len(value) != 64:
        raise WrittenQuestionPackError("Reference pack sourceHash must be a SHA-256 hex string")
    try:
        int(value, 16)
    except ValueError as error:
        raise WrittenQuestionPackError(
            "Reference pack sourceHash must be a SHA-256 hex string"
        ) from error
    return value


def validate_review_metadata(question: dict[str, Any], identifier: str) -> None:
    status = required_text(question, "reviewStatus")
    if status not in REVIEW_STATUSES:
        raise WrittenQuestionPackError(f"{identifier}: unsupported reviewStatus {status}")
    if "reviewer" not in question or "reviewedAt" not in question:
        raise WrittenQuestionPackError(
            f"{identifier}: reviewer and reviewedAt must be explicit (null while pending)"
        )
    reviewer = question["reviewer"]
    reviewed_at = question["reviewedAt"]
    if reviewer is not None and (not isinstance(reviewer, str) or not reviewer.strip()):
        raise WrittenQuestionPackError(f"{identifier}: reviewer must be text or null")
    if reviewed_at is not None:
        if not isinstance(reviewed_at, str):
            raise WrittenQuestionPackError(f"{identifier}: reviewedAt must be ISO-8601 text or null")
        try:
            parsed = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise WrittenQuestionPackError(
                f"{identifier}: reviewedAt must be ISO-8601 text or null"
            ) from error
        if parsed.tzinfo is None:
            raise WrittenQuestionPackError(f"{identifier}: reviewedAt must include a timezone")
    if status == "published" and (reviewer is None or reviewed_at is None):
        raise WrittenQuestionPackError(
            f"{identifier}: published questions require reviewer and reviewedAt"
        )
    if status == "published" and reviewer.strip() in _NON_HUMAN_REVIEWER_PLACEHOLDERS:
        raise WrittenQuestionPackError(
            f"{identifier}: published questions require an external human reviewer"
        )
    if status == "published" and question.get("reviewedContentHash") != review_target_hash(
        question
    ):
        raise WrittenQuestionPackError(
            f"{identifier}: reviewedContentHash is missing or stale"
        )
    if status != "published" and reviewed_at is not None:
        raise WrittenQuestionPackError(
            f"{identifier}: reviewedAt is only valid for published questions"
        )

    metadata = question.get("metadata")
    if not isinstance(metadata, dict):
        raise WrittenQuestionPackError(f"{identifier}: metadata must be an object")
    if not isinstance(metadata.get("externalReviewRequired"), bool):
        raise WrittenQuestionPackError(
            f"{identifier}: metadata.externalReviewRequired must be boolean"
        )
    if status == "published" and metadata["externalReviewRequired"]:
        raise WrittenQuestionPackError(
            f"{identifier}: published questions cannot require external review"
        )
    if status == "pending_external_review" and not metadata["externalReviewRequired"]:
        raise WrittenQuestionPackError(
            f"{identifier}: pending questions must require external review"
        )
    for field in ("authoringMethod", "reviewNotes"):
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip():
            raise WrittenQuestionPackError(f"{identifier}: metadata.{field} is required")


def validate_source(
    source: dict[str, Any],
    *,
    known_term_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    if source.get("schemaVersion") != SCHEMA_VERSION:
        raise WrittenQuestionPackError("Unsupported written source schema")
    questions = source.get("questions")
    if not isinstance(questions, list) or not questions:
        raise WrittenQuestionPackError("Written source must contain questions")
    known_term_ids = known_term_ids if known_term_ids is not None else reference_term_ids()

    identifiers: set[str] = set()
    for question in questions:
        if not isinstance(question, dict):
            raise WrittenQuestionPackError("Each written question must be an object")
        identifier = required_text(question, "id")
        if identifier in identifiers:
            raise WrittenQuestionPackError(f"Duplicate written question id: {identifier}")
        if not identifier.startswith("SAQ-"):
            raise WrittenQuestionPackError(f"{identifier}: id must start with SAQ-")
        identifiers.add(identifier)
        validate_review_metadata(question, identifier)

        for field in (
            "prompt",
            "modelAnswer",
            "learningOutcome",
            "category",
            "topic",
            "cognitiveSkill",
            "commandVerb",
            "difficulty",
        ):
            required_text(question, field)
        for field in ("geography", "countries", "regions", "grapeVarieties"):
            required_string_list(question, field)

        marks = question.get("markAllocation")
        minutes = question.get("suggestedMinutes")
        if not isinstance(marks, int) or marks <= 0:
            raise WrittenQuestionPackError(
                f"{identifier}: markAllocation must be a positive integer"
            )
        if not isinstance(minutes, int) or minutes <= 0:
            raise WrittenQuestionPackError(
                f"{identifier}: suggestedMinutes must be a positive integer"
            )

        rubric = question.get("rubricItems")
        if not isinstance(rubric, list) or not rubric:
            raise WrittenQuestionPackError(f"{identifier}: rubricItems are required")
        rubric_ids: set[str] = set()
        rubric_marks = 0
        for item in rubric:
            if not isinstance(item, dict):
                raise WrittenQuestionPackError(f"{identifier}: invalid rubric item")
            rubric_id = item.get("id")
            criterion = item.get("criterion")
            item_marks = item.get("marks")
            if not isinstance(rubric_id, str) or not rubric_id:
                raise WrittenQuestionPackError(f"{identifier}: rubric id is required")
            if rubric_id in rubric_ids:
                raise WrittenQuestionPackError(
                    f"{identifier}: duplicate rubric id {rubric_id}"
                )
            rubric_ids.add(rubric_id)
            if not isinstance(criterion, str) or not criterion.strip():
                raise WrittenQuestionPackError(
                    f"{identifier}: rubric criterion is required"
                )
            if not isinstance(item_marks, int) or item_marks <= 0:
                raise WrittenQuestionPackError(
                    f"{identifier}: rubric marks must be positive"
                )
            rubric_marks += item_marks
            for field in ("knowledgeTags", "relatedTermIDs"):
                value = item.get(field, [])
                if not isinstance(value, list) or not value or not all(
                    isinstance(entry, str) and entry for entry in value
                ):
                    raise WrittenQuestionPackError(
                        f"{identifier}: {field} must be a non-empty string list"
                    )
                if len(value) != len(set(value)):
                    raise WrittenQuestionPackError(
                        f"{identifier}: {field} must not contain duplicates"
                    )
            unknown_terms = set(item["relatedTermIDs"]) - known_term_ids
            if unknown_terms:
                raise WrittenQuestionPackError(
                    f"{identifier}: unknown relatedTermIDs {sorted(unknown_terms)}"
                )
        if rubric_marks != marks:
            raise WrittenQuestionPackError(
                f"{identifier}: rubric marks {rubric_marks} != markAllocation {marks}"
            )
    return questions


def packed_question(question: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": question["id"],
        "prompt": question["prompt"].strip(),
        "answer": question["modelAnswer"].strip(),
        "explanation": question.get("explanation") or None,
        "choices": [],
        "correctAnswerIndex": None,
        "studyMode": "written_answer",
        "originalFormat": "short_answer",
        "unit": question.get("unit", "Theory"),
        "learningOutcome": question["learningOutcome"],
        "learningOutcomeName": question.get("learningOutcomeName"),
        "category": question["category"],
        "subcategory": question.get("subcategory"),
        "topic": question["topic"],
        "cognitiveSkill": question["cognitiveSkill"],
        "commandVerb": question["commandVerb"],
        "language": "ja",
        "geography": list(dict.fromkeys(question["geography"])),
        "countries": list(dict.fromkeys(question["countries"])),
        "regions": list(dict.fromkeys(question["regions"])),
        "grapeVarieties": list(dict.fromkeys(question["grapeVarieties"])),
        "markAllocation": question["markAllocation"],
        "suggestedMinutes": question["suggestedMinutes"],
        "rubricItems": question["rubricItems"],
        "sourceID": "original-written-question",
        "sourceURL": "",
        "qualityScore": 1.0 if question["reviewStatus"] == "published" else None,
        "reviewStatus": question["reviewStatus"],
        "reviewer": question["reviewer"],
        "reviewedAt": question["reviewedAt"],
        "reviewTargetHash": review_target_hash(question),
        "reviewedContentHash": question.get("reviewedContentHash"),
        "contentMetadata": question["metadata"],
        "choiceExplanations": [],
        "wineType": question.get("wineType"),
        "difficulty": question["difficulty"],
        "misconceptionTags": question.get("misconceptionTags", []),
        "needsReview": question["reviewStatus"] != "published",
        "reviewReason": (
            None
            if question["reviewStatus"] == "published"
            else question["metadata"]["reviewNotes"]
        ),
        "creationType": "original",
        "creationBasis": "original-rubric",
    }


def build_pack(
    input_path: Path = DEFAULT_INPUT,
    *,
    generated_at: str | None = None,
    include_pending_for_development: bool = False,
) -> dict[str, Any]:
    source = json.loads(input_path.read_text(encoding="utf-8"))
    candidates = validate_source(source)
    included_statuses = {"published"}
    if include_pending_for_development:
        included_statuses.add("pending_external_review")
    questions = [
        packed_question(question)
        for question in candidates
        if question["reviewStatus"] in included_statuses
    ]
    review_summary = {
        status: sum(question["reviewStatus"] == status for question in candidates)
        for status in sorted(REVIEW_STATUSES)
    }
    content = {
        "distributionStatus": (
            "development_only" if include_pending_for_development else "release"
        ),
        "referencePackSourceHash": reference_pack_source_hash(),
        "candidateQuestionCount": len(candidates),
        "reviewSummary": review_summary,
        "questions": questions,
    }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at
        or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "sourceHash": sha256(canonical_json(content)),
        "questionCount": len(questions),
        "source": {
            "file": source_display_path(input_path),
            "sha256": sha256(input_path.read_bytes()),
        },
        **content,
    }


def write_pack(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def check_existing_pack(
    input_path: Path,
    output_path: Path,
    *,
    include_pending_for_development: bool = False,
) -> None:
    existing = json.loads(output_path.read_text(encoding="utf-8"))
    expected = build_pack(
        input_path,
        generated_at="ignored-for-check",
        include_pending_for_development=include_pending_for_development,
    )
    for key in (
        "schemaVersion",
        "distributionStatus",
        "sourceHash",
        "referencePackSourceHash",
        "questionCount",
        "candidateQuestionCount",
        "reviewSummary",
        "source",
        "questions",
    ):
        if existing.get(key) != expected.get(key):
            raise WrittenQuestionPackError(f"Generated written pack is stale: {key}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build WSET written-answer pack")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--include-pending-for-development",
        action="store_true",
        help="include pending_external_review questions in a development-only pack",
    )
    args = parser.parse_args()
    if args.check:
        check_existing_pack(
            args.input,
            args.output,
            include_pending_for_development=args.include_pending_for_development,
        )
        print(f"Verified {args.output}")
        return
    payload = build_pack(
        args.input,
        include_pending_for_development=args.include_pending_for_development,
    )
    write_pack(payload, args.output)
    print(f"Wrote {payload['questionCount']} written questions to {args.output}")


if __name__ == "__main__":
    main()
