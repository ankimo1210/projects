#!/usr/bin/env python3
"""Build the offline glossary and classification pack from the canonical workbook."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import unicodedata
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "ReferenceSources" / "wset_reference_master.xlsx"
DEFAULT_QUESTION_PACK = PROJECT_ROOT / "WSET" / "QuestionData" / "question_pack.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "WSET" / "ReferenceData" / "reference_pack.json"
SCHEMA_VERSION = 1

EXPECTED_TERM_COUNT = 680
EXPECTED_ALIAS_COUNT = 224
EXPECTED_SYSTEM_COUNT = 6
EXPECTED_CLASSIFICATION_COUNT = 279

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
COLUMN_REFERENCE_RE = re.compile(r"^([A-Z]+)")
JAPANESE_CHARACTER_RE = re.compile(r"[ぁ-んァ-ヶ一-龠々]")

SHEETS = {
    "用語": {
        "term_id", "日本語", "English", "Français", "読み", "種別", "概要", "詳細", "国",
        "産地", "ラベル", "関連用語IDs", "source_id", "確認日", "公開",
    },
    "別名": {"alias_id", "term_id", "表記", "言語", "別名種別"},
    "格付け制度": {
        "system_id", "地域", "日本語名", "English", "Français", "概要", "基準日", "source_id",
    },
    "格付け項目": {
        "entry_id", "system_id", "日本語名", "原語名", "階級", "村・アペラシオン",
        "サブリージョン", "対象種別", "term_id", "注記", "source_id",
    },
    "情報源": {"source_id", "名称", "URL", "基準日", "確認日"},
}


class ReferencePackError(ValueError):
    """Raised when reference data violates the app data contract."""


def tag(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def clean(value: str | None) -> str:
    return (value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def column_index(reference: str) -> int:
    match = COLUMN_REFERENCE_RE.match(reference)
    if match is None:
        raise ReferencePackError(f"Invalid Excel cell reference: {reference!r}")
    result = 0
    for character in match.group(1):
        result = result * 26 + ord(character) - ord("A") + 1
    return result - 1


def resolve_member(base_member: str, target: str) -> str:
    member = target.lstrip("/") if target.startswith("/") else posixpath.join(
        posixpath.dirname(base_member), target
    )
    member = posixpath.normpath(member)
    if member == ".." or member.startswith("../"):
        raise ReferencePackError(f"Unsafe relationship target: {target!r}")
    return member


def shared_strings(archive: ZipFile) -> list[str]:
    member = "xl/sharedStrings.xml"
    if member not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read(member))
    return [
        "".join(node.text or "" for node in item.iter(tag(MAIN_NS, "t")))
        for item in root.findall(tag(MAIN_NS, "si"))
    ]


def cell_text(cell: ElementTree.Element, strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        inline = cell.find(tag(MAIN_NS, "is"))
        return "" if inline is None else "".join(
            node.text or "" for node in inline.iter(tag(MAIN_NS, "t"))
        )
    value = cell.find(tag(MAIN_NS, "v"))
    raw = value.text if value is not None and value.text is not None else ""
    if cell_type == "s":
        try:
            return strings[int(raw)]
        except (IndexError, ValueError) as error:
            raise ReferencePackError(f"Invalid shared-string index {raw!r}") from error
    if cell_type == "b":
        return "TRUE" if raw == "1" else "FALSE"
    return raw


def worksheet_member(archive: ZipFile, sheet_name: str) -> str:
    workbook_member = "xl/workbook.xml"
    workbook = ElementTree.fromstring(archive.read(workbook_member))
    sheets = workbook.find(tag(MAIN_NS, "sheets"))
    if sheets is None:
        raise ReferencePackError("Workbook has no sheets")
    relationship_id = next(
        (
            sheet.attrib.get(tag(OFFICE_REL_NS, "id"))
            for sheet in sheets.findall(tag(MAIN_NS, "sheet"))
            if sheet.attrib.get("name") == sheet_name
        ),
        None,
    )
    if relationship_id is None:
        raise ReferencePackError(f"Missing sheet: {sheet_name}")
    relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for relationship in relationships.findall(tag(PACKAGE_REL_NS, "Relationship")):
        if relationship.attrib.get("Id") == relationship_id:
            target = relationship.attrib.get("Target")
            if target:
                return resolve_member(workbook_member, target)
    raise ReferencePackError(f"Missing relationship for sheet: {sheet_name}")


def read_sheet_rows(
    workbook_path: Path, sheet_name: str, required_columns: set[str]
) -> list[dict[str, str]]:
    try:
        with ZipFile(workbook_path) as archive:
            root = ElementTree.fromstring(archive.read(worksheet_member(archive, sheet_name)))
            strings = shared_strings(archive)
    except (BadZipFile, ElementTree.ParseError, KeyError) as error:
        raise ReferencePackError(f"Invalid workbook: {workbook_path}") from error
    sheet_data = root.find(tag(MAIN_NS, "sheetData"))
    if sheet_data is None:
        raise ReferencePackError(f"Sheet has no data: {sheet_name}")
    indexed_rows: list[tuple[int, dict[int, str]]] = []
    for row in sheet_data.findall(tag(MAIN_NS, "row")):
        row_number = int(row.attrib.get("r", len(indexed_rows) + 1))
        values: dict[int, str] = {}
        for cell in row.findall(tag(MAIN_NS, "c")):
            reference = cell.attrib.get("r")
            if reference:
                values[column_index(reference)] = clean(cell_text(cell, strings))
        if any(values.values()):
            indexed_rows.append((row_number, values))
    if not indexed_rows:
        raise ReferencePackError(f"Empty sheet: {sheet_name}")
    _, header_values = indexed_rows[0]
    headers = {index: value for index, value in header_values.items() if value}
    missing = sorted(required_columns - set(headers.values()))
    if missing:
        raise ReferencePackError(f"{sheet_name}: missing columns {missing}")
    rows: list[dict[str, str]] = []
    for row_number, values in indexed_rows[1:]:
        record = {header: values.get(index, "") for index, header in headers.items()}
        record["__excel_row__"] = str(row_number)
        rows.append(record)
    return rows


def required(row: dict[str, str], column: str, sheet: str) -> str:
    value = clean(row.get(column))
    if not value:
        raise ReferencePackError(
            f"{sheet} row {row.get('__excel_row__', '?')}: {column} is blank"
        )
    return value


def split_semicolon(value: str) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in value.split(";") if item.strip()))


def normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", normalized)
        if not unicodedata.combining(character)
    ).replace("・", "").replace(" ", "")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def validate_unique(rows: list[dict[str, str]], column: str, sheet: str) -> set[str]:
    values = [required(row, column, sheet) for row in rows]
    duplicates = sorted(value for value in set(values) if values.count(value) > 1)
    if duplicates:
        raise ReferencePackError(f"{sheet}: duplicate {column}: {duplicates[:10]}")
    return set(values)


def question_ids_for_term(
    term: dict[str, Any], questions: list[dict[str, Any]]
) -> list[str]:
    names = [term["nameJapanese"], *term["aliases"]]
    normalized_names = [normalize(name) for name in names if len(normalize(name)) >= 2]
    result: list[str] = []
    for question in questions:
        direct_values: list[str] = []
        if term["category"] == "国":
            direct_values = question.get("countries", [])
        elif term["category"] == "産地・地名":
            direct_values = question.get("regions", [])
        elif term["category"] == "品種":
            direct_values = question.get("grapeVarieties", [])
        direct_match = bool(set(map(normalize, direct_values)) & set(normalized_names))
        visible = "\n".join(
            value
            for value in [
                question.get("prompt", ""),
                question.get("answer", ""),
                question.get("explanation", ""),
                *question.get("choices", []),
                *question.get("choiceExplanations", []),
            ]
            if value
        )
        normalized_visible = normalize(visible)
        if direct_match or any(name in normalized_visible for name in normalized_names):
            result.append(str(question["id"]))
    return sorted(set(result))


def build_pack(
    workbook_path: Path = DEFAULT_INPUT,
    question_pack_path: Path = DEFAULT_QUESTION_PACK,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    rows = {
        sheet: read_sheet_rows(workbook_path, sheet, columns)
        for sheet, columns in SHEETS.items()
    }
    if len(rows["用語"]) != EXPECTED_TERM_COUNT:
        raise ReferencePackError(f"Expected {EXPECTED_TERM_COUNT} terms")
    if len(rows["別名"]) != EXPECTED_ALIAS_COUNT:
        raise ReferencePackError(f"Expected {EXPECTED_ALIAS_COUNT} aliases")
    if len(rows["格付け制度"]) != EXPECTED_SYSTEM_COUNT:
        raise ReferencePackError(f"Expected {EXPECTED_SYSTEM_COUNT} systems")
    if len(rows["格付け項目"]) != EXPECTED_CLASSIFICATION_COUNT:
        raise ReferencePackError(f"Expected {EXPECTED_CLASSIFICATION_COUNT} classifications")

    term_ids = validate_unique(rows["用語"], "term_id", "用語")
    validate_unique(rows["別名"], "alias_id", "別名")
    system_ids = validate_unique(rows["格付け制度"], "system_id", "格付け制度")
    validate_unique(rows["格付け項目"], "entry_id", "格付け項目")
    source_ids = validate_unique(rows["情報源"], "source_id", "情報源")

    aliases_by_term: dict[str, list[str]] = defaultdict(list)
    canonical_names = {
        normalize(required(row, "日本語", "用語")): required(row, "term_id", "用語")
        for row in rows["用語"]
    }
    for row in rows["別名"]:
        identifier = required(row, "term_id", "別名")
        if identifier not in term_ids:
            raise ReferencePackError(f"別名: unknown term_id {identifier}")
        alias = required(row, "表記", "別名")
        collision = canonical_names.get(normalize(alias))
        if collision is not None and collision != identifier:
            raise ReferencePackError(f"別名 {alias!r} conflicts with another canonical term")
        aliases_by_term[identifier].append(alias)

    question_pack = json.loads(question_pack_path.read_text(encoding="utf-8"))
    questions = question_pack.get("questions")
    if not isinstance(questions, list):
        raise ReferencePackError("Question pack has no questions")

    terms: list[dict[str, Any]] = []
    for row in rows["用語"]:
        if required(row, "公開", "用語") not in {"Y", "N"}:
            raise ReferencePackError("用語: 公開 must be Y or N")
        if row["公開"] != "Y":
            continue
        identifier = required(row, "term_id", "用語")
        source_id = required(row, "source_id", "用語")
        if source_id not in source_ids:
            raise ReferencePackError(f"用語: unknown source_id {source_id}")
        term: dict[str, Any] = {
            "id": identifier,
            "nameJapanese": required(row, "日本語", "用語"),
            "nameEnglish": required(row, "English", "用語"),
            "nameFrench": clean(row["Français"]) or None,
            "reading": clean(row["読み"]) or None,
            "category": required(row, "種別", "用語"),
            "summary": required(row, "概要", "用語"),
            "description": required(row, "詳細", "用語"),
            "country": clean(row["国"]) or None,
            "region": clean(row["産地"]) or None,
            "labels": split_semicolon(row["ラベル"]),
            "relatedTermIDs": split_semicolon(row["関連用語IDs"]),
            "aliases": sorted(set(aliases_by_term[identifier])),
            "questionIDs": [],
            "sourceID": source_id,
            "checkedAt": required(row, "確認日", "用語"),
        }
        term["questionIDs"] = question_ids_for_term(term, questions)
        terms.append(term)

    for term in terms:
        unknown = set(term["relatedTermIDs"]) - term_ids
        if unknown:
            raise ReferencePackError(f"{term['id']}: unknown related terms {sorted(unknown)}")

    systems: list[dict[str, Any]] = []
    for row in rows["格付け制度"]:
        source_id = required(row, "source_id", "格付け制度")
        if source_id not in source_ids:
            raise ReferencePackError(f"格付け制度: unknown source_id {source_id}")
        systems.append({
            "id": required(row, "system_id", "格付け制度"),
            "region": required(row, "地域", "格付け制度"),
            "nameJapanese": required(row, "日本語名", "格付け制度"),
            "nameEnglish": clean(row["English"]) or None,
            "nameFrench": clean(row["Français"]) or None,
            "summary": required(row, "概要", "格付け制度"),
            "effectiveDate": required(row, "基準日", "格付け制度"),
            "sourceID": source_id,
        })

    entries: list[dict[str, Any]] = []
    for row in rows["格付け項目"]:
        system_id = required(row, "system_id", "格付け項目")
        identifier = required(row, "term_id", "格付け項目")
        source_id = required(row, "source_id", "格付け項目")
        if system_id not in system_ids or identifier not in term_ids or source_id not in source_ids:
            raise ReferencePackError(f"格付け項目 row {row['__excel_row__']}: broken reference")
        name_japanese = required(row, "日本語名", "格付け項目")
        name_original = required(row, "原語名", "格付け項目")
        if name_japanese == name_original or not JAPANESE_CHARACTER_RE.search(name_japanese):
            raise ReferencePackError(
                f"格付け項目 row {row['__excel_row__']}: 日本語名 must be a Japanese rendering"
            )
        entries.append({
            "id": required(row, "entry_id", "格付け項目"),
            "systemID": system_id,
            "nameJapanese": name_japanese,
            "nameOriginal": name_original,
            "tier": required(row, "階級", "格付け項目"),
            "village": required(row, "村・アペラシオン", "格付け項目"),
            "subregion": required(row, "サブリージョン", "格付け項目"),
            "entryType": required(row, "対象種別", "格付け項目"),
            "termID": identifier,
            "notes": clean(row["注記"]) or None,
            "sourceID": source_id,
        })

    terms_by_id = {term["id"]: term for term in terms}
    for entry in entries:
        term = terms_by_id[entry["termID"]]
        if (
            term["nameJapanese"] != entry["nameJapanese"]
            or term["nameEnglish"] != entry["nameOriginal"]
        ):
            raise ReferencePackError(
                f"{entry['id']}: classification and glossary names must match"
            )

    sources = [
        {
            "id": required(row, "source_id", "情報源"),
            "name": required(row, "名称", "情報源"),
            "url": clean(row["URL"]),
            "effectiveDate": required(row, "基準日", "情報源"),
            "checkedAt": required(row, "確認日", "情報源"),
        }
        for row in rows["情報源"]
    ]
    content = {
        "terms": terms,
        "classificationSystems": systems,
        "classificationEntries": entries,
        "sources": sources,
    }
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at
        or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "sourceHash": sha256(canonical_json(content)),
        "questionPackSourceHash": question_pack.get("sourceHash", ""),
        "termCount": len(terms),
        "classificationEntryCount": len(entries),
        "source": {
            "file": workbook_path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix(),
            "sha256": sha256(workbook_path.read_bytes()),
        },
        **content,
    }
    validate_pack(payload)
    return payload


def validate_pack(payload: dict[str, Any]) -> None:
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        raise ReferencePackError("Unsupported reference pack schema")
    terms = payload.get("terms")
    entries = payload.get("classificationEntries")
    if not isinstance(terms, list) or len(terms) != EXPECTED_TERM_COUNT:
        raise ReferencePackError("Reference pack term count mismatch")
    if not isinstance(entries, list) or len(entries) != EXPECTED_CLASSIFICATION_COUNT:
        raise ReferencePackError("Reference pack classification count mismatch")
    if payload.get("termCount") != len(terms):
        raise ReferencePackError("termCount mismatch")
    if payload.get("classificationEntryCount") != len(entries):
        raise ReferencePackError("classificationEntryCount mismatch")
    content = {
        "terms": terms,
        "classificationSystems": payload.get("classificationSystems"),
        "classificationEntries": entries,
        "sources": payload.get("sources"),
    }
    if payload.get("sourceHash") != sha256(canonical_json(content)):
        raise ReferencePackError("sourceHash mismatch")


def write_pack(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_existing_pack(input_path: Path, question_pack: Path, output_path: Path) -> None:
    existing = json.loads(output_path.read_text(encoding="utf-8"))
    validate_pack(existing)
    expected = build_pack(input_path, question_pack, generated_at="ignored-for-check")
    for key in (
        "schemaVersion", "sourceHash", "questionPackSourceHash", "termCount",
        "classificationEntryCount", "source", "terms", "classificationSystems",
        "classificationEntries", "sources",
    ):
        if existing.get(key) != expected.get(key):
            raise ReferencePackError(f"Generated reference pack is stale: {key}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the WSET offline reference pack")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--question-pack", type=Path, default=DEFAULT_QUESTION_PACK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check_existing_pack(args.input, args.question_pack, args.output)
        print(f"Verified {args.output}: {EXPECTED_TERM_COUNT} terms, {EXPECTED_CLASSIFICATION_COUNT} classifications")
        return
    payload = build_pack(args.input, args.question_pack)
    write_pack(payload, args.output)
    linked = sum(bool(term["questionIDs"]) for term in payload["terms"])
    print(
        f"Wrote {payload['termCount']} terms and {payload['classificationEntryCount']} "
        f"classification entries to {args.output}; {linked} terms link to questions"
    )


if __name__ == "__main__":
    main()
