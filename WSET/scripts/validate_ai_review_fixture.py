#!/usr/bin/env python3
"""Validate the rubric-centered human-evaluation fixture for remote AI review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "EvaluationFixtures" / "ai_written_review_cases.json"


class FixtureValidationError(ValueError):
    pass


def _nonempty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FixtureValidationError(f"{path} must be a non-empty string")
    return value


def validate_fixture(payload: dict[str, Any]) -> None:
    if payload.get("schemaVersion") != 1:
        raise FixtureValidationError("schemaVersion must be 1")
    _nonempty_string(payload.get("evaluationPurpose"), "evaluationPurpose")

    scale = payload.get("ratingScale")
    if not isinstance(scale, dict) or set(scale) != {"1", "2", "3", "4", "5"}:
        raise FixtureValidationError("ratingScale must define 1 through 5")
    for key, description in scale.items():
        _nonempty_string(description, f"ratingScale.{key}")

    checks = payload.get("requiredHumanChecks")
    if not isinstance(checks, list) or len(checks) < 3:
        raise FixtureValidationError("requiredHumanChecks must contain at least 3 checks")
    for index, check in enumerate(checks):
        _nonempty_string(check, f"requiredHumanChecks[{index}]")

    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) < 3:
        raise FixtureValidationError("cases must contain at least 3 cases")

    case_ids: set[str] = set()
    for case_index, case in enumerate(cases):
        path = f"cases[{case_index}]"
        if not isinstance(case, dict):
            raise FixtureValidationError(f"{path} must be an object")
        case_id = _nonempty_string(case.get("id"), f"{path}.id")
        if case_id in case_ids:
            raise FixtureValidationError(f"duplicate case id: {case_id}")
        case_ids.add(case_id)
        _nonempty_string(case.get("questionID"), f"{path}.questionID")
        _nonempty_string(case.get("prompt"), f"{path}.prompt")
        _nonempty_string(case.get("candidateAnswer"), f"{path}.candidateAnswer")

        rubric = case.get("rubric")
        if not isinstance(rubric, list) or not rubric:
            raise FixtureValidationError(f"{path}.rubric must not be empty")
        rubric_ids: set[str] = set()
        maximum_total = 0
        for rubric_index, criterion in enumerate(rubric):
            criterion_path = f"{path}.rubric[{rubric_index}]"
            if not isinstance(criterion, dict):
                raise FixtureValidationError(f"{criterion_path} must be an object")
            criterion_id = _nonempty_string(criterion.get("id"), f"{criterion_path}.id")
            if criterion_id in rubric_ids:
                raise FixtureValidationError(f"duplicate rubric id in {case_id}: {criterion_id}")
            rubric_ids.add(criterion_id)
            _nonempty_string(criterion.get("criterion"), f"{criterion_path}.criterion")
            marks = criterion.get("maximumMarks")
            if not isinstance(marks, int) or isinstance(marks, bool) or marks <= 0:
                raise FixtureValidationError(f"{criterion_path}.maximumMarks must be positive")
            maximum_total += marks

        score_range = case.get("expectedScoreRange")
        if not isinstance(score_range, dict):
            raise FixtureValidationError(f"{path}.expectedScoreRange must be an object")
        minimum = score_range.get("minimum")
        maximum = score_range.get("maximum")
        if (
            not isinstance(minimum, int)
            or isinstance(minimum, bool)
            or not isinstance(maximum, int)
            or isinstance(maximum, bool)
            or minimum < 0
            or minimum > maximum
            or maximum > maximum_total
        ):
            raise FixtureValidationError(f"{path}.expectedScoreRange exceeds rubric bounds")

        forbidden_claims = case.get("mustNotClaim")
        if not isinstance(forbidden_claims, list) or not forbidden_claims:
            raise FixtureValidationError(f"{path}.mustNotClaim must not be empty")
        for claim_index, claim in enumerate(forbidden_claims):
            _nonempty_string(claim, f"{path}.mustNotClaim[{claim_index}]")


def load_and_validate(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FixtureValidationError(f"cannot read fixture: {error}") from error
    if not isinstance(payload, dict):
        raise FixtureValidationError("fixture root must be an object")
    validate_fixture(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    payload = load_and_validate(args.path)
    print(f"Validated {len(payload['cases'])} AI review evaluation cases: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
