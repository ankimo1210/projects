"""Verify provenance for the section-review ledger and render its summary.

The checker establishes inventory completeness and evidence freshness. It does
not rerun the numerical or browser validations referenced by historical PASS
records, so a successful result is not a claim that the teaching material is
complete or that its financial results remain correct.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path, PurePosixPath

STATUSES = (
    "unreviewed",
    "gaps_found",
    "pending_validation",
    "accepted",
    "out_of_scope",
)
COVERAGE_NAMES = (
    "explanation",
    "implementation",
    "independent_validation",
    "visualization",
    "rendered",
)
COVERAGE_STATES = {"verified", "pending", "not_applicable"}
EVIDENCE_KINDS = ("source", "test", "note", "image", "record", "reference")
REQUIRED_EVIDENCE_KINDS = {
    "explanation": {"source", "note"},
    "implementation": {"source"},
    "independent_validation": {"record"},
    "visualization": {"image"},
    "rendered": {"record"},
}
KIND_ERROR_LABELS = {
    "explanation": "source or note evidence",
    "implementation": "source evidence",
    "independent_validation": "record evidence",
    "visualization": "image evidence",
    "rendered": "record evidence",
}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
SECTION_ID_RE = re.compile(r"([1-9][0-9]*)\.([1-9][0-9]*)")
APPENDIX_ID_RE = re.compile(r"([1-9][0-9]*)\.appendix")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _safe_file(project: Path, value: object, label: str, errors: list[str]) -> Path | None:
    if not _nonempty_string(value):
        errors.append(f"{label}: path must be a non-empty project-relative path")
        return None
    assert isinstance(value, str)
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or "\\" in value
        or re.match(r"^[A-Za-z]:", value)
        or ".." in relative.parts
    ):
        errors.append(f"{label}: path must be project-relative: {value!r}")
        return None

    root = project.resolve()
    path = root.joinpath(*relative.parts)
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(root):
        errors.append(f"{label}: path must remain project-relative (external symlink): {value!r}")
        return None
    if not path.is_file():
        errors.append(f"{label}: file does not exist: {value!r}")
        return None
    return path


def _check_hashed_file(
    project: Path,
    path_value: object,
    hash_value: object,
    label: str,
    errors: list[str],
) -> Path | None:
    path = _safe_file(project, path_value, label, errors)
    if not _sha256(hash_value):
        errors.append(f"{label}.sha256: expected 64 lowercase hexadecimal characters")
        return path
    if path is not None and _sha256_file(path) != hash_value:
        errors.append(f"{label}.sha256: digest does not match {path_value!r}")
    return path


def _validate_inventory(
    project: Path, inventory: object, errors: list[str]
) -> tuple[list[dict], set[str]]:
    if not isinstance(inventory, dict):
        errors.append("inventory: top level must be an object")
        return [], set()
    if inventory.get("schema_version") != 1:
        errors.append("inventory.schema_version: expected 1")
    if not _nonempty_string(inventory.get("edition")):
        errors.append("inventory.edition: expected a non-empty string")

    source = inventory.get("source")
    if not isinstance(source, dict):
        errors.append("inventory.source: expected an object")
    else:
        if not _nonempty_string(source.get("method")):
            errors.append("inventory.source.method: expected a non-empty string")
        _check_hashed_file(
            project,
            source.get("path"),
            source.get("sha256"),
            "inventory.source",
            errors,
        )

    raw_entries = inventory.get("entries")
    if not isinstance(raw_entries, list):
        errors.append("inventory.entries: expected a list")
        return [], set()

    entries: list[dict] = []
    ids: list[str] = []
    for index, entry in enumerate(raw_entries):
        label = f"inventory.entries[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: expected an object")
            continue
        entries.append(entry)
        entry_id = entry.get("id")
        chapter = entry.get("chapter")
        kind = entry.get("kind")
        if not _nonempty_string(entry_id):
            errors.append(f"{label}.id: expected a non-empty string")
        else:
            ids.append(entry_id)
        if not _integer(chapter) or chapter < 1:
            errors.append(f"{label}.chapter: expected a positive integer")
        if not isinstance(kind, str) or kind not in ("section", "appendix"):
            errors.append(f"{label}.kind: expected section or appendix")
        if not _nonempty_string(entry.get("title")):
            errors.append(f"{label}.title: expected a non-empty string")
        if not _integer(entry.get("page_start")) or entry["page_start"] < 1:
            errors.append(f"{label}.page_start: expected a positive integer")

        if _nonempty_string(entry_id) and _integer(chapter):
            pattern = SECTION_ID_RE if kind == "section" else APPENDIX_ID_RE
            match = pattern.fullmatch(entry_id) if kind in ("section", "appendix") else None
            if match is None or int(match.group(1)) != chapter:
                errors.append(f"{label}: kind/chapter does not match ID {entry_id!r}")

    duplicates = sorted(entry_id for entry_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        errors.append(f"inventory.entries: duplicate IDs: {', '.join(duplicates)}")

    expected = inventory.get("expected_counts")
    if not isinstance(expected, dict):
        errors.append("inventory.expected_counts: expected an object")
    else:
        actual_counts = {
            "sections": sum(entry.get("kind") == "section" for entry in entries),
            "appendices": sum(entry.get("kind") == "appendix" for entry in entries),
            "chapters": len(
                {entry.get("chapter") for entry in entries if _integer(entry.get("chapter"))}
            ),
        }
        for name, actual in actual_counts.items():
            declared = expected.get(name)
            if not _integer(declared) or declared < 0:
                errors.append(f"inventory.expected_counts.{name}: expected a non-negative integer")
            elif declared != actual:
                errors.append(
                    f"inventory.expected_counts.{name}: declared {declared}, found {actual}"
                )
    return entries, set(ids)


def _validate_record_mapping(project: Path, mapping: object, label: str, errors: list[str]) -> None:
    if not isinstance(mapping, dict):
        errors.append(f"{label}: expected a path-to-sha256 object")
        return
    for path_value, hash_value in mapping.items():
        _check_hashed_file(project, path_value, hash_value, f"{label}[{path_value!r}]", errors)


def _validate_record_hashes(
    project: Path,
    record_path: Path,
    evidence_label: str,
    check_artifacts: bool,
    errors: list[str],
) -> None:
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{evidence_label}: record is not valid JSON: {exc}")
        return
    if not isinstance(record, dict):
        errors.append(f"{evidence_label}: record top level must be an object")
        return
    if record.get("status") != "PASS":
        errors.append(f"{evidence_label}: record must have top-level status=PASS")

    source_hashes = record.get("source_sha256")
    if source_hashes is not None:
        _validate_record_mapping(
            project, source_hashes, f"{evidence_label}.record.source_sha256", errors
        )
    if check_artifacts:
        artifact_hashes = record.get("artifact_sha256")
        if not isinstance(artifact_hashes, dict) or not artifact_hashes:
            errors.append(
                f"{evidence_label}.record.artifact_sha256: required with --check-artifacts"
            )
        else:
            _validate_record_mapping(
                project,
                artifact_hashes,
                f"{evidence_label}.record.artifact_sha256",
                errors,
            )


def _validate_evidence(
    project: Path,
    section_label: str,
    evidence: object,
    check_artifacts: bool,
    errors: list[str],
) -> dict[str, str]:
    if not isinstance(evidence, dict):
        errors.append(f"{section_label}.evidence: expected an object")
        return {}
    kinds: dict[str, str] = {}
    for evidence_id, item in evidence.items():
        label = f"{section_label}.evidence {evidence_id}"
        if not _nonempty_string(evidence_id):
            errors.append(f"{section_label}.evidence: IDs must be non-empty strings")
            continue
        if not isinstance(item, dict):
            errors.append(f"{label}: expected an object")
            continue
        kind = item.get("kind")
        if not isinstance(kind, str) or kind not in EVIDENCE_KINDS:
            errors.append(f"{label}.kind: unknown kind {kind!r}")
        else:
            kinds[evidence_id] = kind
        path_value = item.get("path")
        path = _check_hashed_file(project, path_value, item.get("sha256"), label, errors)
        if kind == "record" and path is not None:
            _validate_record_hashes(project, path, label, check_artifacts, errors)
    return kinds


def _validate_string_list(value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, list) or any(not _nonempty_string(item) for item in value):
        errors.append(f"{label}: expected a list of non-empty strings")


def _validate_accepted_fields(
    project: Path,
    section: dict,
    section_label: str,
    evidence: object,
    evidence_kinds: dict[str, str],
    errors: list[str],
) -> None:
    reviewed_at = section.get("reviewed_at")
    try:
        if (
            not isinstance(reviewed_at, str)
            or date.fromisoformat(reviewed_at).isoformat() != reviewed_at
        ):
            raise ValueError
    except ValueError:
        errors.append(f"{section_label}.reviewed_at: expected an ISO date (YYYY-MM-DD)")

    source_pages = section.get("source_pages")
    if (
        not isinstance(source_pages, list)
        or len(source_pages) != 2
        or any(not _integer(page) for page in source_pages)
        or (
            len(source_pages) == 2
            and all(_integer(page) for page in source_pages)
            and source_pages[0] > source_pages[1]
        )
    ):
        errors.append(f"{section_label}.source_pages: expected [start, end] integers")
    if not _nonempty_string(section.get("scope")):
        errors.append(f"{section_label}.scope: expected a non-empty string")
    _validate_string_list(section.get("assumptions"), f"{section_label}.assumptions", errors)
    _validate_string_list(section.get("limitations"), f"{section_label}.limitations", errors)

    note_path = _safe_file(
        project, section.get("acceptance_note"), f"{section_label}.acceptance_note", errors
    )
    if note_path is not None and isinstance(evidence, dict):
        matching_note = any(
            isinstance(item, dict)
            and item.get("kind") == "note"
            and item.get("path") == section.get("acceptance_note")
            for item in evidence.values()
        )
        if not matching_note:
            errors.append(f"{section_label}.acceptance_note: must be registered as note evidence")
    if "record" not in set(evidence_kinds.values()):
        errors.append(f"{section_label}: accepted section requires record evidence")


def _validate_requirements(
    section: dict,
    section_label: str,
    evidence_kinds: dict[str, str],
    errors: list[str],
) -> None:
    requirements = section.get("requirements")
    if not isinstance(requirements, list):
        errors.append(f"{section_label}.requirements: expected a list")
        return
    if section.get("status") == "unreviewed" and requirements:
        errors.append(f"{section_label}.requirements: unreviewed must use requirements=[]")
    if section.get("status") == "accepted" and not requirements:
        errors.append(f"{section_label}.requirements: accepted requires at least one requirement")

    requirement_ids: list[str] = []
    for requirement_index, requirement in enumerate(requirements):
        label = f"{section_label}.requirements[{requirement_index}]"
        if not isinstance(requirement, dict):
            errors.append(f"{label}: expected an object")
            continue
        requirement_id = requirement.get("id")
        if not _nonempty_string(requirement_id):
            errors.append(f"{label}.id: expected a non-empty string")
        else:
            requirement_ids.append(requirement_id)
        if not _nonempty_string(requirement.get("statement")):
            errors.append(f"{label}.statement: expected a non-empty string")
        coverage = requirement.get("coverage")
        if not isinstance(coverage, dict):
            errors.append(f"{label}.coverage: expected an object")
            continue
        missing_coverage = [name for name in COVERAGE_NAMES if name not in coverage]
        unknown_coverage = sorted(set(coverage) - set(COVERAGE_NAMES))
        if missing_coverage:
            errors.append(f"{label}.coverage: missing keys: {', '.join(missing_coverage)}")
        if unknown_coverage:
            errors.append(f"{label}.coverage: unknown keys: {', '.join(unknown_coverage)}")
        for coverage_name in COVERAGE_NAMES:
            if coverage_name not in coverage:
                continue
            item = coverage[coverage_name]
            item_label = f"{label}.coverage.{coverage_name}"
            if not isinstance(item, dict):
                errors.append(f"{item_label}: expected an object")
                continue
            state = item.get("state")
            refs = item.get("refs")
            if not isinstance(state, str) or state not in COVERAGE_STATES:
                errors.append(f"{item_label}.state: unknown state {state!r}")
            if not isinstance(refs, list) or any(not _nonempty_string(ref) for ref in refs):
                errors.append(f"{item_label}.refs: expected a list of evidence IDs")
                refs = []
            unknown_refs = sorted({ref for ref in refs if ref not in evidence_kinds})
            if unknown_refs:
                errors.append(f"{item_label}: unknown evidence ref: {', '.join(unknown_refs)}")
            if state == "verified" and not refs:
                errors.append(f"{item_label}: verified requires at least one evidence ref")
            if state == "not_applicable" and not _nonempty_string(item.get("reason")):
                errors.append(f"{item_label}: not_applicable requires a concrete reason")
            if "locator" in item and not _nonempty_string(item.get("locator")):
                errors.append(f"{item_label}.locator: expected a non-empty string")
            if state == "verified" and refs:
                kinds = {evidence_kinds.get(ref) for ref in refs}
                if not kinds.intersection(REQUIRED_EVIDENCE_KINDS[coverage_name]):
                    errors.append(
                        f"{item_label}: verified requires {KIND_ERROR_LABELS[coverage_name]}"
                    )
            if section.get("status") == "accepted" and state == "pending":
                errors.append(f"{item_label}: accepted coverage cannot be pending")

        if section.get("status") == "accepted":
            for required_name in ("explanation", "rendered"):
                item = coverage.get(required_name)
                if not isinstance(item, dict) or item.get("state") != "verified":
                    errors.append(f"{label}.coverage.{required_name}: accepted must be verified")

    duplicates = sorted(item for item, count in Counter(requirement_ids).items() if count > 1)
    if duplicates:
        errors.append(f"{section_label}.requirements: duplicate IDs: {', '.join(duplicates)}")


def evaluate_ledger(
    project: Path, inventory: dict, ledger: dict, *, check_artifacts: bool = False
) -> dict:
    """Validate ledger structure, provenance, and evidence freshness.

    Historical record files are inspected for ``status=PASS`` and their stored
    hashes are compared with current files. Their calculations are not rerun.
    """
    project = Path(project)
    errors: list[str] = []
    entries, inventory_ids = _validate_inventory(project, inventory, errors)
    counts = {status: 0 for status in STATUSES}

    if not isinstance(ledger, dict):
        errors.append("ledger: top level must be an object")
        sections: list[object] = []
    else:
        if ledger.get("schema_version") != 1:
            errors.append("ledger.schema_version: expected 1")
        inventory_hash = ledger.get("inventory_sha256")
        inventory_path = project / "docs/section_inventory.json"
        if not _sha256(inventory_hash):
            errors.append("ledger.inventory_sha256: expected 64 lowercase hexadecimal characters")
        elif not inventory_path.is_file():
            errors.append("ledger.inventory_sha256: docs/section_inventory.json does not exist")
        elif _sha256_file(inventory_path) != inventory_hash:
            errors.append(
                "ledger.inventory_sha256: digest does not match docs/section_inventory.json"
            )
        raw_sections = ledger.get("sections")
        if not isinstance(raw_sections, list):
            errors.append("ledger.sections: expected a list")
            sections = []
        else:
            sections = raw_sections

    ledger_ids: list[str] = []
    for index, section in enumerate(sections):
        label = f"ledger.sections[{index}]"
        if not isinstance(section, dict):
            errors.append(f"{label}: expected an object")
            continue
        section_id = section.get("id")
        if not _nonempty_string(section_id):
            errors.append(f"{label}.id: expected a non-empty string")
        else:
            ledger_ids.append(section_id)
            label = f"ledger section {section_id}"
        status = section.get("status")
        if status not in STATUSES:
            errors.append(f"{label}.status: unknown status {status!r}")
        else:
            counts[status] += 1
        if status == "out_of_scope" and not _nonempty_string(section.get("reason")):
            errors.append(f"{label}.reason: out_of_scope requires a concrete reason")

        evidence = section.get("evidence", {})
        if status == "accepted" and "evidence" not in section:
            evidence = None
        evidence_kinds = _validate_evidence(project, label, evidence, check_artifacts, errors)
        if status == "accepted":
            _validate_accepted_fields(project, section, label, evidence, evidence_kinds, errors)
        _validate_requirements(section, label, evidence_kinds, errors)

    duplicate_ids = sorted(
        section_id for section_id, count in Counter(ledger_ids).items() if count > 1
    )
    if duplicate_ids:
        errors.append(f"ledger.sections: duplicate IDs: {', '.join(duplicate_ids)}")
    ledger_id_set = set(ledger_ids)
    missing_ids = sorted(inventory_ids - ledger_id_set)
    unknown_ids = sorted(ledger_id_set - inventory_ids)
    if missing_ids:
        errors.append(f"ledger.sections: missing inventory IDs: {', '.join(missing_ids)}")
    if unknown_ids:
        errors.append(f"ledger.sections: unknown IDs: {', '.join(unknown_ids)}")

    return {
        "status": "FAIL" if errors else "PASS",
        "errors": errors,
        "counts": counts,
        "inventory_total": len(entries),
        "accepted_sections": counts["accepted"],
        "artifacts_checked": bool(check_artifacts),
    }


def render_summary(inventory: dict, ledger: dict, result: dict) -> str:
    """Render a deterministic Japanese Markdown view of valid ledger data."""
    entries = inventory["entries"]
    sections_by_id = {section["id"]: section for section in ledger["sections"]}
    chapter_counts: dict[int, Counter] = defaultdict(Counter)
    for entry in entries:
        chapter_counts[entry["chapter"]][sections_by_id[entry["id"]]["status"]] += 1

    lines = [
        "# 節別レビュー台帳",
        "",
        f"- 証跡検査: **{result['status']}**",
        f"- 登録項目: **{result['inventory_total']}**",
        f"- accepted: **{result['accepted_sections']}**",
        "- 成果物ハッシュ: **既定では未検査（--check-artifacts で追加検査）**",
        "",
        "> PASS は台帳の網羅性・証拠の存在・保存ハッシュに対する現在ファイルの鮮度を示します。",
        "> 保存済み検証の計算や画面を再実行しておらず、教材全体の完成を意味しません。",
        "",
        "## 状態別件数",
        "",
        "| 状態 | 件数 |",
        "|---|---:|",
    ]
    lines.extend(f"| {status} | {result['counts'][status]} |" for status in STATUSES)
    lines.extend(
        [
            "",
            "## 章別件数",
            "",
            "| 章 | 登録 | unreviewed | gaps_found | pending_validation | accepted | out_of_scope |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for chapter in sorted(chapter_counts):
        counts = chapter_counts[chapter]
        total = sum(counts.values())
        lines.append(
            f"| {chapter} | {total} | "
            + " | ".join(str(counts[status]) for status in STATUSES)
            + " |"
        )
    lines.extend(
        [
            "",
            "## 全登録項目",
            "",
            "| ID | 章 | 種別 | タイトル | 状態 |",
            "|---|---:|---|---|---|",
        ]
    )
    for entry in entries:
        status = sections_by_id[entry["id"]]["status"]
        title = str(entry["title"]).replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {entry['id']} | {entry['chapter']} | {entry['kind']} | {title} | {status} |"
        )
    return "\n".join(lines) + "\n"


def _load_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{label}: file does not exist: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label}: JSON top level must be an object")
    return value


def _print_result(result: dict) -> None:
    print(f"status: {result['status']}")
    print(f"inventory_total: {result['inventory_total']}")
    print(f"accepted_sections: {result['accepted_sections']}")
    print(f"artifacts_checked: {str(result['artifacts_checked']).lower()}")


def _summary_path_error(project: Path, summary_path: Path) -> str | None:
    """Return a diagnostic when the fixed summary path is unsafe."""
    try:
        if not summary_path.resolve(strict=False).is_relative_to(project.resolve()):
            return "docs/SECTION_LEDGER.md must resolve inside the project root"
        if summary_path.is_symlink():
            return "docs/SECTION_LEDGER.md must not be a symlink"
    except (OSError, RuntimeError) as exc:
        return f"docs/SECTION_LEDGER.md path could not be resolved safely: {exc}"
    return None


def main(argv: list[str] | None = None) -> int:
    """Check the canonical JSON files and optionally refresh the fixed summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="johnhull project root (default: parent of this script directory)",
    )
    parser.add_argument("--write-summary", action="store_true")
    parser.add_argument("--check-artifacts", action="store_true")
    args = parser.parse_args(argv)

    project = args.project_root.resolve()
    inventory_path = project / "docs/section_inventory.json"
    ledger_path = project / "docs/section_ledger.json"
    summary_path = project / "docs/SECTION_LEDGER.md"
    if summary_error := _summary_path_error(project, summary_path):
        print(summary_error, file=sys.stderr)
        return 1
    try:
        inventory = _load_json(inventory_path, "inventory JSON")
        ledger = _load_json(ledger_path, "ledger JSON")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    result = evaluate_ledger(project, inventory, ledger, check_artifacts=args.check_artifacts)
    if result["status"] == "FAIL":
        _print_result(result)
        for error in result["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    summary = render_summary(inventory, ledger, result)
    if args.write_summary:
        try:
            summary_path.write_text(summary, encoding="utf-8")
        except OSError as exc:
            print(f"SECTION_LEDGER.md: could not write summary: {exc}", file=sys.stderr)
            return 1
    else:
        try:
            current_summary = summary_path.read_text(encoding="utf-8")
        except OSError:
            current_summary = None
        if current_summary != summary:
            result["status"] = "FAIL"
            result["errors"].append(
                "docs/SECTION_LEDGER.md is missing or stale; rerun with --write-summary"
            )
            _print_result(result)
            print(f"ERROR: {result['errors'][-1]}", file=sys.stderr)
            return 1

    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
