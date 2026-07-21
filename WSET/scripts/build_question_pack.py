#!/usr/bin/env python3
"""Build the iOS question pack from the user-authored Excel workbook.

The reader intentionally uses only the Python standard library. An ``.xlsx`` file is
a ZIP archive containing Office Open XML, so no spreadsheet package is required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "QuestionSources" / "wset_level3_original_questions_1100_v7.xlsx"
DEFAULT_OUTPUT = PROJECT_ROOT / "WSET" / "QuestionData" / "question_pack.json"
SHEET_NAME = "問題集"
SCHEMA_VERSION = 4
SOURCE_ID = "wset_level3_original_1100_v7"
EXPECTED_QUESTION_COUNT = 1100

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

LO_MAP = {
    "LO1": "u1_lo1",
    "LO2": "u1_lo2",
    "LO3": "u1_lo3",
    "LO4": "u1_lo4",
    "LO5": "u1_lo5",
}
EXPECTED_LO_COUNTS = {
    "LO1": 180,
    "LO2": 380,
    "LO3": 180,
    "LO4": 180,
    "LO5": 180,
}
EXPECTED_CORRECT_ANSWER_COUNTS = {letter: 275 for letter in "ABCD"}
CHOICE_COLUMNS = ["選択肢A", "選択肢B", "選択肢C", "選択肢D"]
CHOICE_EXPLANATION_COLUMNS = ["A解説", "B解説", "C解説", "D解説"]

REQUIRED_COLUMNS = {
    "問題ID",
    "LO",
    "LO名称",
    "トピック",
    "問題文",
    *CHOICE_COLUMNS,
    "正答",
    "正答本文",
    "正答解説",
    *CHOICE_EXPLANATION_COLUMNS,
    "知識領域",
    "小分類",
    "ワイン区分",
    "国",
    "産地",
    "主要品種",
    "思考スキル",
    "難易度",
    "誤概念タグ",
    "要レビュー",
    "レビュー理由",
    "作成区分",
    "作成根拠",
    "レビュー状態",
}

_COLUMN_REFERENCE_RE = re.compile(r"^([A-Z]+)")
_LIST_SEPARATOR_RE = re.compile(r"\s*(?:[、,，;/；／]|\r?\n)\s*")
_TAG_SEPARATOR_RE = re.compile(r"\s*[;；]\s*")


class QuestionPackError(ValueError):
    """Raised when the workbook or generated pack violates the data contract."""


def _tag(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def _clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def _column_index(cell_reference: str) -> int:
    match = _COLUMN_REFERENCE_RE.match(cell_reference)
    if match is None:
        raise QuestionPackError(f"Invalid Excel cell reference: {cell_reference!r}")
    index = 0
    for character in match.group(1):
        index = index * 26 + ord(character) - ord("A") + 1
    return index - 1


def _resolve_archive_member(base_member: str, target: str) -> str:
    if target.startswith("/"):
        member = target.lstrip("/")
    else:
        member = posixpath.join(posixpath.dirname(base_member), target)
    member = posixpath.normpath(member)
    if member == ".." or member.startswith("../"):
        raise QuestionPackError(f"Unsafe relationship target: {target!r}")
    return member


def _shared_strings(archive: ZipFile) -> list[str]:
    member = "xl/sharedStrings.xml"
    if member not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read(member))
    return [
        "".join(node.text or "" for node in item.iter(_tag(MAIN_NS, "t")))
        for item in root.findall(_tag(MAIN_NS, "si"))
    ]


def _cell_text(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        inline = cell.find(_tag(MAIN_NS, "is"))
        if inline is None:
            return ""
        return "".join(node.text or "" for node in inline.iter(_tag(MAIN_NS, "t")))

    value = cell.find(_tag(MAIN_NS, "v"))
    raw = value.text if value is not None and value.text is not None else ""
    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (IndexError, ValueError) as error:
            raise QuestionPackError(
                f"Invalid shared-string index {raw!r} in cell {cell.attrib.get('r')}"
            ) from error
    if cell_type == "b":
        return "TRUE" if raw == "1" else "FALSE"
    return raw


def _worksheet_member(archive: ZipFile, sheet_name: str) -> str:
    workbook_member = "xl/workbook.xml"
    relationships_member = "xl/_rels/workbook.xml.rels"
    workbook = ElementTree.fromstring(archive.read(workbook_member))
    sheets = workbook.find(_tag(MAIN_NS, "sheets"))
    if sheets is None:
        raise QuestionPackError("Workbook has no sheets collection")

    relationship_id: str | None = None
    for sheet in sheets.findall(_tag(MAIN_NS, "sheet")):
        if sheet.attrib.get("name") == sheet_name:
            relationship_id = sheet.attrib.get(_tag(OFFICE_REL_NS, "id"))
            break
    if relationship_id is None:
        available = [
            sheet.attrib.get("name", "") for sheet in sheets.findall(_tag(MAIN_NS, "sheet"))
        ]
        raise QuestionPackError(
            f"Sheet {sheet_name!r} was not found; available sheets: {available}"
        )

    relationships = ElementTree.fromstring(archive.read(relationships_member))
    for relationship in relationships.findall(_tag(PACKAGE_REL_NS, "Relationship")):
        if relationship.attrib.get("Id") == relationship_id:
            target = relationship.attrib.get("Target")
            if not target:
                break
            return _resolve_archive_member(workbook_member, target)
    raise QuestionPackError(
        f"Relationship {relationship_id!r} for sheet {sheet_name!r} was not found"
    )


def read_question_rows(workbook_path: Path, sheet_name: str = SHEET_NAME) -> list[dict[str, str]]:
    """Read the named worksheet into dictionaries keyed by its first-row headers."""

    if not workbook_path.is_file():
        raise QuestionPackError(f"Workbook not found: {workbook_path}")
    try:
        with ZipFile(workbook_path) as archive:
            worksheet_member = _worksheet_member(archive, sheet_name)
            worksheet = ElementTree.fromstring(archive.read(worksheet_member))
            shared_strings = _shared_strings(archive)
    except (BadZipFile, ElementTree.ParseError, KeyError) as error:
        raise QuestionPackError(f"Invalid .xlsx workbook: {workbook_path}") from error

    sheet_data = worksheet.find(_tag(MAIN_NS, "sheetData"))
    if sheet_data is None:
        raise QuestionPackError(f"Sheet {sheet_name!r} has no sheetData")

    indexed_rows: list[tuple[int, dict[int, str]]] = []
    for row in sheet_data.findall(_tag(MAIN_NS, "row")):
        row_number = int(row.attrib.get("r", len(indexed_rows) + 1))
        values: dict[int, str] = {}
        for cell in row.findall(_tag(MAIN_NS, "c")):
            reference = cell.attrib.get("r")
            if not reference:
                raise QuestionPackError(f"Cell without a reference in Excel row {row_number}")
            values[_column_index(reference)] = _clean_text(_cell_text(cell, shared_strings))
        if any(values.values()):
            indexed_rows.append((row_number, values))

    if not indexed_rows:
        raise QuestionPackError(f"Sheet {sheet_name!r} is empty")

    header_row_number, header_values = indexed_rows[0]
    headers = {column_index: header for column_index, header in header_values.items() if header}
    if len(headers) != len(set(headers.values())):
        raise QuestionPackError(f"Duplicate headers in Excel row {header_row_number}")
    missing_columns = sorted(REQUIRED_COLUMNS - set(headers.values()))
    if missing_columns:
        raise QuestionPackError(f"Missing required columns: {missing_columns}")

    records: list[dict[str, str]] = []
    for row_number, values in indexed_rows[1:]:
        unexpected = [index for index, value in values.items() if value and index not in headers]
        if unexpected:
            raise QuestionPackError(f"Excel row {row_number} has data outside the header range")
        record = {header: values.get(index, "") for index, header in headers.items()}
        record["__excel_row__"] = str(row_number)
        records.append(record)
    return records


def _row_label(row: Mapping[str, str]) -> str:
    identifier = row.get("問題ID") or "unknown ID"
    excel_row = row.get("__excel_row__") or "?"
    return f"Excel row {excel_row} ({identifier})"


def _required(row: Mapping[str, str], column: str) -> str:
    value = _clean_text(row.get(column))
    if not value:
        raise QuestionPackError(f"{_row_label(row)}: {column} is blank")
    return value


def _split_values(value: str, *, strip_etc: bool = False) -> list[str]:
    result: list[str] = []
    for item in _LIST_SEPARATOR_RE.split(_clean_text(value)):
        item = item.strip()
        if strip_etc and item.endswith("等"):
            item = item[:-1].rstrip()
        if item and item not in result:
            result.append(item)
    return result


def _split_tags(value: str) -> list[str]:
    return [item for item in _TAG_SEPARATOR_RE.split(_clean_text(value)) if item]


def _needs_review(row: Mapping[str, str]) -> bool:
    value = _required(row, "要レビュー").upper()
    if value == "Y":
        return True
    if value == "N":
        return False
    raise QuestionPackError(f"{_row_label(row)}: 要レビュー must be Y or N, got {value!r}")


def _review_status(row: Mapping[str, str]) -> str:
    source_status = _required(row, "レビュー状態")
    status_map = {
        "未レビュー": "unreviewed",
        "確認中": "in_review",
        "修正要": "needs_revision",
        "承認": "approved",
        "レビュー済": "human_reviewed",
        "レビュー済み": "human_reviewed",
        "公開": "published",
        "公開済": "published",
        "改稿済み・専門家未承認": "ai_reviewed_pending_expert",
        "要修正": "needs_revision",
        "却下": "rejected",
    }
    try:
        return status_map[source_status]
    except KeyError as error:
        raise QuestionPackError(
            f"{_row_label(row)}: unknown レビュー状態 {source_status!r}"
        ) from error


_REVIEW_FIELDS = {
    "reviewStatus",
    "needsReview",
    "reviewReason",
    "reviewer",
    "reviewedAt",
    "reviewComment",
    "reviewTargetHash",
    "reviewedContentHash",
}
_NON_HUMAN_REVIEWER_PLACEHOLDERS = {
    "AI",
    "生成AI",
    "AI誤答レビュー",
    "AI選択肢論理監査",
}


def _review_target_hash(question: Mapping[str, Any]) -> str:
    """Fingerprint only reviewable content, not its mutable review metadata."""

    content = {
        key: value for key, value in question.items() if key not in _REVIEW_FIELDS
    }
    return _sha256(_canonical_questions([content]))


def _validate_published_review(question: Mapping[str, Any], label: str) -> None:
    """Require auditable human evidence before a question can be published."""

    if question.get("reviewStatus") != "published":
        return
    if question.get("needsReview") is not False:
        raise QuestionPackError(f"{label}: published question must set 要レビュー to N")

    reviewer = _clean_text(question.get("reviewer"))
    if not reviewer or reviewer in _NON_HUMAN_REVIEWER_PLACEHOLDERS:
        raise QuestionPackError(
            f"{label}: published question requires an external human reviewer"
        )
    reviewed_at = _clean_text(question.get("reviewedAt"))
    try:
        if date.fromisoformat(reviewed_at).isoformat() != reviewed_at:
            raise ValueError
    except ValueError as error:
        raise QuestionPackError(
            f"{label}: published question requires レビュー日 in YYYY-MM-DD format"
        ) from error
    if not _clean_text(question.get("reviewComment")):
        raise QuestionPackError(
            f"{label}: published question requires a non-empty レビューコメント"
        )
    if question.get("reviewedContentHash") != question.get("reviewTargetHash"):
        raise QuestionPackError(
            f"{label}: レビュー対象ハッシュ is missing or stale; regenerate the "
            "content review packet and re-review the current content"
        )


def pack_question(row: Mapping[str, str]) -> dict[str, Any]:
    """Map one source row to the schema-version-4 app contract."""

    source_lo = _required(row, "LO")
    try:
        learning_outcome = LO_MAP[source_lo]
    except KeyError as error:
        raise QuestionPackError(f"{_row_label(row)}: unsupported LO {source_lo!r}") from error

    choices = [_required(row, column) for column in CHOICE_COLUMNS]
    choice_explanations = [_required(row, column) for column in CHOICE_EXPLANATION_COLUMNS]
    correct_letter = _required(row, "正答").upper()
    if correct_letter not in "ABCD" or len(correct_letter) != 1:
        raise QuestionPackError(
            f"{_row_label(row)}: 正答 must be A, B, C, or D, got {correct_letter!r}"
        )
    correct_index = ord(correct_letter) - ord("A")
    answer = _required(row, "正答本文")
    if choices[correct_index] != answer:
        raise QuestionPackError(
            f"{_row_label(row)}: 正答本文 does not match 選択肢{correct_letter}"
        )

    needs_review = _needs_review(row)
    review_reason = _clean_text(row.get("レビュー理由")) or None
    if needs_review and review_reason is None:
        raise QuestionPackError(f"{_row_label(row)}: レビュー理由 is required when 要レビュー is Y")

    countries = _split_values(row.get("国", ""))
    regions = _split_values(row.get("産地", ""))
    geography = list(countries)
    for place in regions:
        if place not in geography:
            geography.append(place)

    question: dict[str, Any] = {
        "id": _required(row, "問題ID"),
        "prompt": _required(row, "問題文"),
        "answer": answer,
        "explanation": _required(row, "正答解説"),
        "choices": choices,
        "correctAnswerIndex": correct_index,
        "choiceExplanations": choice_explanations,
        "studyMode": "multiple_choice",
        "originalFormat": "multiple_choice",
        "unit": "unit_1",
        "learningOutcome": learning_outcome,
        "learningOutcomeName": _required(row, "LO名称"),
        "category": _required(row, "知識領域"),
        "topic": _required(row, "トピック"),
        "subcategory": _required(row, "小分類"),
        "wineType": _required(row, "ワイン区分"),
        "cognitiveSkill": _required(row, "思考スキル"),
        "commandVerb": None,
        "difficulty": _required(row, "難易度"),
        "language": "ja",
        "geography": geography,
        "countries": countries,
        "regions": regions,
        "grapeVarieties": _split_values(row.get("主要品種", ""), strip_etc=True),
        "misconceptionTags": _split_tags(row.get("誤概念タグ", "")),
        "markAllocation": 1,
        "sourceID": SOURCE_ID,
        "sourceURL": "",
        "qualityScore": None,
        "reviewStatus": _review_status(row),
        "needsReview": needs_review,
        "reviewReason": review_reason,
        "creationType": _required(row, "作成区分"),
        "creationBasis": _required(row, "作成根拠"),
    }
    question["reviewer"] = _clean_text(row.get("レビュアー")) or None
    question["reviewedAt"] = _clean_text(row.get("レビュー日")) or None
    question["reviewComment"] = _clean_text(row.get("レビューコメント")) or None
    question["reviewTargetHash"] = _review_target_hash(question)
    question["reviewedContentHash"] = (
        _clean_text(row.get("レビュー対象ハッシュ")) or None
    )
    _validate_published_review(question, _row_label(row))
    return question


def _counts(rows: Iterable[Mapping[str, str]], key: str) -> Counter[str]:
    return Counter(_clean_text(row.get(key)) for row in rows)


def validate_source_rows(rows: list[dict[str, str]]) -> None:
    if len(rows) != EXPECTED_QUESTION_COUNT:
        raise QuestionPackError(f"Expected {EXPECTED_QUESTION_COUNT} questions, found {len(rows)}")

    identifiers = [_required(row, "問題ID") for row in rows]
    duplicate_ids = sorted(
        identifier for identifier, count in Counter(identifiers).items() if count > 1
    )
    if duplicate_ids:
        raise QuestionPackError(f"Duplicate question IDs: {duplicate_ids}")

    lo_counts = dict(_counts(rows, "LO"))
    if lo_counts != EXPECTED_LO_COUNTS:
        raise QuestionPackError(
            f"Unexpected LO distribution: {lo_counts}; expected {EXPECTED_LO_COUNTS}"
        )
    answer_counts = dict(_counts(rows, "正答"))
    if answer_counts != EXPECTED_CORRECT_ANSWER_COUNTS:
        raise QuestionPackError(
            "Unexpected correct-answer distribution: "
            f"{answer_counts}; expected {EXPECTED_CORRECT_ANSWER_COUNTS}"
        )

    for row in rows:
        pack_question(row)


def _canonical_questions(questions: list[dict[str, Any]]) -> bytes:
    return json.dumps(
        questions,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _distribution_status(questions: list[Mapping[str, Any]]) -> str:
    """Mark every structurally valid non-empty question pack as releasable.

    Editorial review metadata remains attached to each question for traceability,
    but it no longer controls whether owner-approved content ships.
    """

    return "release" if questions else "development_only"


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _source_display_path(input_path: Path) -> str:
    try:
        return input_path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(input_path.resolve())


def build_pack(
    input_path: Path = DEFAULT_INPUT,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    rows = read_question_rows(input_path)
    validate_source_rows(rows)
    questions = [pack_question(row) for row in rows]
    source_file_hash = _sha256(input_path.read_bytes())
    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at
        or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "sourceHash": _sha256(_canonical_questions(questions)),
        "questionCount": len(questions),
        "distributionStatus": _distribution_status(questions),
        "source": {
            "id": SOURCE_ID,
            "type": "user_authored_workbook",
            "file": _source_display_path(input_path),
            "sha256": source_file_hash,
            "sheet": SHEET_NAME,
        },
        "questions": questions,
    }
    validate_pack(payload)
    return payload


def validate_pack(payload: Mapping[str, Any]) -> None:
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        raise QuestionPackError(f"Question pack must use schema v{SCHEMA_VERSION}")
    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise QuestionPackError("Question pack questions must be a list")
    if payload.get("questionCount") != len(questions):
        raise QuestionPackError("Question pack questionCount does not match questions")
    if len(questions) != EXPECTED_QUESTION_COUNT:
        raise QuestionPackError(f"Question pack must contain {EXPECTED_QUESTION_COUNT} questions")
    expected_distribution_status = _distribution_status(questions)
    if payload.get("distributionStatus") != expected_distribution_status:
        raise QuestionPackError(
            "Question pack distributionStatus does not match its content"
        )

    identifiers = [question.get("id") for question in questions]
    if len(identifiers) != len(set(identifiers)):
        raise QuestionPackError("Question pack contains duplicate IDs")
    for question in questions:
        _validate_published_review(question, str(question.get("id") or "unknown"))
        if question.get("language") != "ja":
            raise QuestionPackError(f"{question.get('id')}: language must be ja")
        if question.get("studyMode") != "multiple_choice":
            raise QuestionPackError(f"{question.get('id')}: studyMode must be multiple_choice")
        countries = question.get("countries")
        regions = question.get("regions")
        geography = question.get("geography")
        if not isinstance(countries, list) or not all(
            isinstance(value, str) for value in countries
        ):
            raise QuestionPackError(f"{question.get('id')}: countries must be a string list")
        if not isinstance(regions, list) or not all(isinstance(value, str) for value in regions):
            raise QuestionPackError(f"{question.get('id')}: regions must be a string list")
        expected_geography = list(dict.fromkeys([*countries, *regions]))
        if geography != expected_geography:
            raise QuestionPackError(
                f"{question.get('id')}: geography must equal countries followed by regions"
            )
        choices = question.get("choices")
        explanations = question.get("choiceExplanations")
        correct_index = question.get("correctAnswerIndex")
        if not isinstance(choices, list) or len(choices) != 4:
            raise QuestionPackError(f"{question.get('id')}: exactly 4 choices required")
        if not isinstance(explanations, list) or len(explanations) != 4:
            raise QuestionPackError(f"{question.get('id')}: exactly 4 choice explanations required")
        if not isinstance(correct_index, int) or not 0 <= correct_index < 4:
            raise QuestionPackError(f"{question.get('id')}: invalid correctAnswerIndex")
        if question.get("answer") != choices[correct_index]:
            raise QuestionPackError(
                f"{question.get('id')}: answer does not match the correct choice"
            )
        forbidden_translation_keys = {
            "translations",
            "translationStatus",
            "translationModel",
        }
        if forbidden_translation_keys & question.keys():
            raise QuestionPackError(
                f"{question.get('id')}: translation fields are not allowed in schema v4"
            )

    expected_hash = _sha256(_canonical_questions(questions))
    if payload.get("sourceHash") != expected_hash:
        raise QuestionPackError("Question pack sourceHash does not match its questions")


def write_pack(payload: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    temporary = output_path.with_name(f".{output_path.name}.tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(output_path)


def check_existing_pack(input_path: Path, output_path: Path) -> None:
    if not output_path.is_file():
        raise QuestionPackError(f"Generated pack not found: {output_path}")
    expected = build_pack(input_path, generated_at="ignored-for-check")
    existing = json.loads(output_path.read_text(encoding="utf-8"))
    validate_pack(existing)
    for key in (
        "schemaVersion",
        "sourceHash",
        "questionCount",
        "distributionStatus",
        "source",
        "questions",
    ):
        if existing.get(key) != expected.get(key):
            raise QuestionPackError(f"Generated pack is stale or differs from the workbook: {key}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the Japanese schema-v4 app question pack from the original Excel source"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate that the existing output exactly matches the workbook",
    )
    args = parser.parse_args()

    if args.check:
        check_existing_pack(args.input, args.output)
        print(
            f"Verified {args.output}: {EXPECTED_QUESTION_COUNT} Japanese questions, "
            f"schema v{SCHEMA_VERSION}"
        )
        return

    payload = build_pack(args.input)
    write_pack(payload, args.output)
    lo_counts = Counter(question["learningOutcome"] for question in payload["questions"])
    review_count = sum(question["needsReview"] for question in payload["questions"])
    print(
        f"Wrote {payload['questionCount']} Japanese questions to {args.output} "
        f"(schema v{payload['schemaVersion']}, "
        f"distribution={payload['distributionStatus']}, "
        f"sourceHash={payload['sourceHash']})"
    )
    print(f"LO distribution: {dict(sorted(lo_counts.items()))}")
    print(f"Needs review: {review_count}")


if __name__ == "__main__":
    main()
