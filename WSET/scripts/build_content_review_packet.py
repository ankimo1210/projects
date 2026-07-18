#!/usr/bin/env python3
"""Build and validate the external content-review handoff packet.

The packet contains stable fingerprints and item identifiers, not an assertion that
review happened. A human reviewer records findings in the issue log and copies the
approved fingerprint into each canonical source before setting it to published.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

try:
    from scripts.build_question_pack import (
        DEFAULT_INPUT as DEFAULT_MCQ_INPUT,
        pack_question,
        read_question_rows,
    )
    from scripts.build_region_map_pack import (
        DEFAULT_INPUT as DEFAULT_MAP_INPUT,
        REVIEW_SCOPES,
        build_pack as build_map_pack,
    )
    from scripts.build_written_question_pack import (
        DEFAULT_INPUT as DEFAULT_WRITTEN_INPUT,
        review_target_hash as written_review_target_hash,
        validate_source as validate_written_source,
    )
except ModuleNotFoundError:  # Direct execution: python3 scripts/this_file.py
    from build_question_pack import (  # type: ignore[no-redef]
        DEFAULT_INPUT as DEFAULT_MCQ_INPUT,
        pack_question,
        read_question_rows,
    )
    from build_region_map_pack import (  # type: ignore[no-redef]
        DEFAULT_INPUT as DEFAULT_MAP_INPUT,
        REVIEW_SCOPES,
        build_pack as build_map_pack,
    )
    from build_written_question_pack import (  # type: ignore[no-redef]
        DEFAULT_INPUT as DEFAULT_WRITTEN_INPUT,
        review_target_hash as written_review_target_hash,
        validate_source as validate_written_source,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "ContentReviews" / "content_review_request.json"
DEFAULT_ISSUE_LOG = ROOT / "ContentReviews" / "review_issues.json"
SCHEMA_VERSION = 1
TARGET_TYPES = {"mcq", "written", "region_map"}
ISSUE_STATUSES = {"open", "resolved"}
SEVERITIES = {"low", "medium", "high", "critical"}


class ContentReviewError(ValueError):
    """Raised when the review handoff or issue log is invalid."""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContentReviewError(f"Unable to load {label}: {path}") from error
    if not isinstance(value, dict):
        raise ContentReviewError(f"{label} must be a JSON object")
    return value


def validate_issue_log(path: Path = DEFAULT_ISSUE_LOG) -> list[dict[str, Any]]:
    """Validate the canonical finding log and return unresolved findings."""

    payload = _load_object(path, "content review issue log")
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        raise ContentReviewError("Unsupported content review issue-log schema")
    issues = payload.get("issues")
    if not isinstance(issues, list) or not all(isinstance(item, dict) for item in issues):
        raise ContentReviewError("review_issues.json issues must be an object list")

    identifiers: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    for issue in issues:
        identifier = issue.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ContentReviewError("Every review issue requires a non-empty id")
        if identifier in identifiers:
            raise ContentReviewError(f"Duplicate review issue id: {identifier}")
        identifiers.add(identifier)

        target_type = issue.get("targetType")
        if target_type not in TARGET_TYPES:
            raise ContentReviewError(
                f"{identifier}: targetType must be one of {sorted(TARGET_TYPES)}"
            )
        for field in ("itemID", "finding", "reportedBy"):
            if not isinstance(issue.get(field), str) or not issue[field].strip():
                raise ContentReviewError(f"{identifier}: {field} is required")
        if issue.get("severity") not in SEVERITIES:
            raise ContentReviewError(
                f"{identifier}: severity must be one of {sorted(SEVERITIES)}"
            )
        status = issue.get("status")
        if status not in ISSUE_STATUSES:
            raise ContentReviewError(
                f"{identifier}: status must be one of {sorted(ISSUE_STATUSES)}"
            )
        updated_at = issue.get("updatedAt")
        try:
            if not isinstance(updated_at, str) or date.fromisoformat(updated_at).isoformat() != updated_at:
                raise ValueError
        except ValueError as error:
            raise ContentReviewError(
                f"{identifier}: updatedAt must use YYYY-MM-DD"
            ) from error
        resolution = issue.get("resolution")
        if status == "resolved" and (
            not isinstance(resolution, str) or not resolution.strip()
        ):
            raise ContentReviewError(
                f"{identifier}: resolved issue requires a resolution"
            )
        if status == "open":
            unresolved.append(issue)
    return unresolved


def build_packet(
    mcq_input: Path = DEFAULT_MCQ_INPUT,
    written_input: Path = DEFAULT_WRITTEN_INPUT,
    map_input: Path = DEFAULT_MAP_INPUT,
    issue_log: Path = DEFAULT_ISSUE_LOG,
) -> dict[str, Any]:
    """Build a deterministic request manifest bound to current source content."""

    unresolved = validate_issue_log(issue_log)

    mcq_rows = read_question_rows(mcq_input)
    mcq_items = []
    for row in mcq_rows:
        question = pack_question(row)
        mcq_items.append(
            {
                "id": question["id"],
                "excelRow": int(row["__excel_row__"]),
                "reviewTargetHash": question["reviewTargetHash"],
                "currentStatus": question["reviewStatus"],
                "needsReview": question["needsReview"],
            }
        )

    written_source = _load_object(written_input, "written-question source")
    written_questions = validate_written_source(written_source)
    written_items = [
        {
            "id": question["id"],
            "reviewTargetHash": written_review_target_hash(question),
            "currentStatus": question["reviewStatus"],
        }
        for question in written_questions
    ]

    map_payload, _ = build_map_pack(input_path=map_input)
    map_items = [
        {
            "id": map_document["id"],
            "regionIDs": [region["id"] for region in map_document["regions"]],
        }
        for map_document in map_payload["maps"]
    ]

    sources = {
        "mcq": {
            "source": _display_path(mcq_input),
            "itemCount": len(mcq_items),
            "requestHash": _sha256(mcq_items),
            "items": mcq_items,
            "approvalFields": [
                "レビュー状態=公開",
                "要レビュー=N",
                "レビュアー",
                "レビュー日",
                "レビューコメント",
                "レビュー対象ハッシュ",
            ],
        },
        "written": {
            "source": _display_path(written_input),
            "itemCount": len(written_items),
            "requestHash": _sha256(written_items),
            "items": written_items,
            "approvalFields": [
                "reviewStatus=published",
                "reviewer",
                "reviewedAt",
                "reviewedContentHash",
                "metadata.externalReviewRequired=false",
                "metadata.reviewNotes",
            ],
        },
        "regionMap": {
            "source": _display_path(map_input),
            "itemCount": len(map_items),
            "requestHash": map_payload["reviewTargetHash"],
            "currentStatus": map_payload["review"]["status"],
            "requiredScopes": list(REVIEW_SCOPES),
            "items": map_items,
            "approvalFields": [
                "review.status=published",
                "review.reviewer",
                "review.reviewedAt",
                "review.reviewedContentHash",
                "review.scopes.*=true",
                "review.notes",
            ],
        },
    }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "instructions": "docs/content-review-workflow.md",
        "issueLog": _display_path(issue_log),
        "unresolvedIssueCount": len(unresolved),
        "sources": sources,
    }


def write_packet(payload: dict[str, Any], output_path: Path = DEFAULT_OUTPUT) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def check_packet(
    output_path: Path = DEFAULT_OUTPUT,
    **build_arguments: Path,
) -> None:
    actual = _load_object(output_path, "generated content review packet")
    expected = build_packet(**build_arguments)
    if actual != expected:
        raise ContentReviewError(
            f"Content review packet is stale; run {Path(__file__).name}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcq-input", type=Path, default=DEFAULT_MCQ_INPUT)
    parser.add_argument("--written-input", type=Path, default=DEFAULT_WRITTEN_INPUT)
    parser.add_argument("--map-input", type=Path, default=DEFAULT_MAP_INPUT)
    parser.add_argument("--issue-log", type=Path, default=DEFAULT_ISSUE_LOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    build_arguments = {
        "mcq_input": arguments.mcq_input,
        "written_input": arguments.written_input,
        "map_input": arguments.map_input,
        "issue_log": arguments.issue_log,
    }
    try:
        if arguments.check:
            check_packet(arguments.output, **build_arguments)
        else:
            write_packet(build_packet(**build_arguments), arguments.output)
    except ContentReviewError as error:
        print(f"error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
