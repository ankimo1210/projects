"""Contract tests for the section-ledger provenance checker."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from johnhull.scripts.verify_section_ledger import evaluate_ledger, render_summary

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "johnhull/scripts/verify_section_ledger.py"
STATUSES = (
    "unreviewed",
    "gaps_found",
    "pending_validation",
    "accepted",
    "out_of_scope",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@dataclass
class ProjectFixture:
    root: Path
    inventory: dict
    ledger: dict

    def persist(self) -> None:
        inventory_path = self.root / "docs/section_inventory.json"
        _write_json(inventory_path, self.inventory)
        self.ledger["inventory_sha256"] = _sha256(inventory_path)
        _write_json(self.root / "docs/section_ledger.json", self.ledger)


@pytest.fixture
def project_fixture(tmp_path: Path) -> ProjectFixture:
    project = tmp_path / "project"
    (project / "docs").mkdir(parents=True)
    (project / "src").mkdir()
    (project / "generated").mkdir()

    source_pdf = project / "docs/source.pdf"
    source_pdf.write_bytes(b"source-pdf\n")
    implementation = project / "src/implementation.py"
    implementation.write_text("VALUE = 1\n", encoding="utf-8")
    note = project / "docs/acceptance.md"
    note.write_text("# Acceptance\n", encoding="utf-8")
    image = project / "docs/render.png"
    image.write_bytes(b"png\n")
    artifact = project / "generated/render.html"
    artifact.write_text("<p>rendered</p>\n", encoding="utf-8")

    record = {
        "status": "PASS",
        "source_sha256": {"src/implementation.py": _sha256(implementation)},
        "artifact_sha256": {"generated/render.html": _sha256(artifact)},
    }
    record_path = project / "docs/record.json"
    _write_json(record_path, record)

    inventory = {
        "schema_version": 1,
        "edition": "Fixture Edition",
        "source": {
            "path": "docs/source.pdf",
            "sha256": _sha256(source_pdf),
            "method": "hand-written fixture",
        },
        "expected_counts": {"sections": 2, "appendices": 1, "chapters": 2},
        "entries": [
            {"id": "1.1", "chapter": 1, "kind": "section", "title": "One", "page_start": 1},
            {"id": "1.2", "chapter": 1, "kind": "section", "title": "Two", "page_start": 2},
            {
                "id": "2.appendix",
                "chapter": 2,
                "kind": "appendix",
                "title": "Appendix",
                "page_start": 3,
            },
        ],
    }
    accepted = {
        "id": "1.1",
        "status": "accepted",
        "reviewed_at": "2026-09-15",
        "source_pages": [1, 2],
        "scope": "fixture scope",
        "assumptions": ["fixture assumption"],
        "limitations": ["fixture limitation"],
        "acceptance_note": "docs/acceptance.md",
        "evidence": {
            "implementation": {
                "path": "src/implementation.py",
                "sha256": _sha256(implementation),
                "kind": "source",
            },
            "note": {"path": "docs/acceptance.md", "sha256": _sha256(note), "kind": "note"},
            "record": {
                "path": "docs/record.json",
                "sha256": _sha256(record_path),
                "kind": "record",
            },
            "image": {"path": "docs/render.png", "sha256": _sha256(image), "kind": "image"},
        },
        "requirements": [
            {
                "id": "R01",
                "statement": "The fixture is covered",
                "coverage": {
                    "explanation": {"state": "verified", "refs": ["note"]},
                    "implementation": {"state": "verified", "refs": ["implementation"]},
                    "independent_validation": {"state": "verified", "refs": ["record"]},
                    "visualization": {"state": "verified", "refs": ["image"]},
                    "rendered": {"state": "verified", "refs": ["record"]},
                },
            }
        ],
    }
    ledger = {
        "schema_version": 1,
        "inventory_sha256": "set by persist",
        "sections": [
            accepted,
            {"id": "1.2", "status": "unreviewed", "requirements": []},
            {
                "id": "2.appendix",
                "status": "out_of_scope",
                "reason": "fixture only",
                "requirements": [],
            },
        ],
    }
    fixture = ProjectFixture(project, inventory, ledger)
    fixture.persist()
    return fixture


def _run_cli(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(project), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_valid_ledger_returns_the_public_result_contract(project_fixture: ProjectFixture) -> None:
    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result == {
        "status": "PASS",
        "errors": [],
        "counts": {
            "unreviewed": 1,
            "gaps_found": 0,
            "pending_validation": 0,
            "accepted": 1,
            "out_of_scope": 1,
        },
        "inventory_total": 3,
        "accepted_sections": 1,
        "artifacts_checked": False,
    }


def test_removing_an_inventory_row_is_not_accepted(project_fixture: ProjectFixture) -> None:
    project_fixture.ledger["sections"].pop()

    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result["status"] == "FAIL"
    assert any("2.appendix" in error and "missing" in error for error in result["errors"])


@pytest.mark.parametrize("change", ["duplicate", "unknown"])
def test_duplicate_and_unknown_ledger_ids_fail(
    project_fixture: ProjectFixture, change: str
) -> None:
    if change == "duplicate":
        project_fixture.ledger["sections"].append(
            copy.deepcopy(project_fixture.ledger["sections"][0])
        )
    else:
        project_fixture.ledger["sections"][1]["id"] = "99.1"

    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result["status"] == "FAIL"
    assert any(change in error for error in result["errors"])


def test_inventory_counts_ids_and_source_hash_are_checked(project_fixture: ProjectFixture) -> None:
    project_fixture.inventory["expected_counts"]["sections"] = 99
    project_fixture.inventory["entries"][1]["id"] = "1.appendix"
    (project_fixture.root / "docs/source.pdf").write_bytes(b"changed\n")

    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result["status"] == "FAIL"
    assert any("expected_counts.sections" in error for error in result["errors"])
    assert any("kind" in error and "ID" in error for error in result["errors"])
    assert any("source.sha256" in error for error in result["errors"])


def test_inventory_file_hash_must_match_ledger(project_fixture: ProjectFixture) -> None:
    project_fixture.ledger["inventory_sha256"] = "0" * 64

    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result["status"] == "FAIL"
    assert any("inventory_sha256" in error for error in result["errors"])


def test_tampered_evidence_and_record_source_are_rejected(project_fixture: ProjectFixture) -> None:
    (project_fixture.root / "docs/acceptance.md").write_text("tampered\n", encoding="utf-8")
    (project_fixture.root / "src/implementation.py").write_text("VALUE = 2\n", encoding="utf-8")

    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result["status"] == "FAIL"
    assert any("evidence note" in error and "sha256" in error for error in result["errors"])
    assert any("record" in error and "source_sha256" in error for error in result["errors"])


def test_record_requires_pass_status(project_fixture: ProjectFixture) -> None:
    record_path = project_fixture.root / "docs/record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["status"] = "FAIL"
    _write_json(record_path, record)
    project_fixture.ledger["sections"][0]["evidence"]["record"]["sha256"] = _sha256(record_path)

    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result["status"] == "FAIL"
    assert any("record" in error and "status=PASS" in error for error in result["errors"])


def test_artifacts_are_only_checked_when_requested(project_fixture: ProjectFixture) -> None:
    artifact = project_fixture.root / "generated/render.html"
    artifact.unlink()

    default_result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )
    artifact_result = evaluate_ledger(
        project_fixture.root,
        project_fixture.inventory,
        project_fixture.ledger,
        check_artifacts=True,
    )

    assert default_result["status"] == "PASS"
    assert default_result["artifacts_checked"] is False
    assert artifact_result["status"] == "FAIL"
    assert artifact_result["artifacts_checked"] is True
    assert any("artifact_sha256" in error for error in artifact_result["errors"])


def test_project_relative_paths_cannot_escape_or_follow_external_symlinks(
    project_fixture: ProjectFixture, tmp_path: Path
) -> None:
    external = tmp_path / "external.md"
    external.write_text("external\n", encoding="utf-8")
    escaped = project_fixture.ledger["sections"][0]["evidence"]["note"]
    escaped["path"] = "../external.md"
    symlink = project_fixture.root / "docs/external-link.md"
    symlink.symlink_to(external)
    project_fixture.ledger["sections"][0]["acceptance_note"] = "docs/external-link.md"

    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result["status"] == "FAIL"
    assert sum("project-relative" in error for error in result["errors"]) >= 2


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda section: section.pop("reviewed_at"), "reviewed_at"),
        (lambda section: section.__setitem__("source_pages", [1]), "source_pages"),
        (lambda section: section["evidence"].pop("record"), "record evidence"),
        (
            lambda section: section["requirements"][0]["coverage"]["rendered"].__setitem__(
                "state", "pending"
            ),
            "pending",
        ),
        (
            lambda section: section["requirements"][0]["coverage"]["explanation"].__setitem__(
                "refs", ["missing"]
            ),
            "unknown evidence ref",
        ),
        (
            lambda section: section["requirements"][0]["coverage"]["visualization"].update(
                {"state": "not_applicable", "refs": []}
            ),
            "reason",
        ),
    ],
)
def test_accepted_sections_cannot_have_ambiguous_coverage(
    project_fixture: ProjectFixture, mutate, message: str
) -> None:
    mutate(project_fixture.ledger["sections"][0])

    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result["status"] == "FAIL"
    assert any(message in error for error in result["errors"])


def test_accepted_section_requires_at_least_one_requirement(
    project_fixture: ProjectFixture,
) -> None:
    project_fixture.ledger["sections"][0]["requirements"] = []

    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result["status"] == "FAIL"
    assert any("accepted" in error and "at least one" in error for error in result["errors"])


def test_unreviewed_section_allows_empty_requirements(project_fixture: ProjectFixture) -> None:
    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result["status"] == "PASS"
    assert project_fixture.ledger["sections"][1]["requirements"] == []


@pytest.mark.parametrize(
    ("mutate", "message", "diagnostic"),
    [
        (
            lambda fixture: fixture.inventory["entries"][0].__setitem__("kind", []),
            ".kind",
            "expected",
        ),
        (
            lambda fixture: fixture.ledger["sections"][0]["evidence"]["note"].__setitem__(
                "kind", {}
            ),
            ".kind",
            "unknown",
        ),
        (
            lambda fixture: fixture.ledger["sections"][0]["requirements"][0]["coverage"][
                "explanation"
            ].__setitem__("state", []),
            ".state",
            "unknown",
        ),
        (
            lambda fixture: fixture.ledger["sections"][1].__setitem__("status", []),
            ".status",
            "unknown",
        ),
    ],
)
def test_malformed_enum_values_return_diagnostic_fail(
    project_fixture: ProjectFixture, mutate, message: str, diagnostic: str
) -> None:
    mutate(project_fixture)

    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result["status"] == "FAIL"
    assert any(message in error and diagnostic in error for error in result["errors"])


@pytest.mark.parametrize(
    ("coverage_name", "refs", "message"),
    [
        ("explanation", ["image"], "source or note"),
        ("implementation", ["note"], "source evidence"),
        ("independent_validation", ["note"], "record evidence"),
        ("visualization", ["note"], "image evidence"),
        ("rendered", ["note"], "record evidence"),
    ],
)
def test_verified_coverage_requires_evidence_of_the_right_kind(
    project_fixture: ProjectFixture, coverage_name: str, refs: list[str], message: str
) -> None:
    coverage = project_fixture.ledger["sections"][0]["requirements"][0]["coverage"]
    coverage[coverage_name]["refs"] = refs

    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result["status"] == "FAIL"
    assert any(message in error for error in result["errors"])


def test_nonaccepted_refs_are_also_resolved(project_fixture: ProjectFixture) -> None:
    project_fixture.ledger["sections"][1]["status"] = "gaps_found"
    project_fixture.ledger["sections"][1]["requirements"] = [
        {
            "id": "R02",
            "statement": "Known gap",
            "coverage": {
                "explanation": {"state": "pending", "refs": ["missing"]},
                "implementation": {"state": "pending", "refs": []},
                "independent_validation": {"state": "pending", "refs": []},
                "visualization": {"state": "pending", "refs": []},
                "rendered": {"state": "pending", "refs": []},
            },
        }
    ]

    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    assert result["status"] == "FAIL"
    assert any("unknown evidence ref" in error for error in result["errors"])


def test_summary_separates_checker_pass_from_material_completion(
    project_fixture: ProjectFixture,
) -> None:
    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )

    summary = render_summary(project_fixture.inventory, project_fixture.ledger, result)

    assert "証跡検査: **PASS**" in summary
    assert "教材全体の完成を意味しません" in summary
    assert "成果物ハッシュ: **既定では未検査（--check-artifacts で追加検査）**" in summary
    assert "| 1 | 2 | 1 | 0 | 0 | 1 | 0 |" in summary
    assert "| 1.1 | 1 | section | One | accepted |" in summary
    assert "| 2.appendix | 2 | appendix | Appendix | out_of_scope |" in summary
    assert "%" not in summary


def test_cli_writes_then_checks_a_fresh_summary(project_fixture: ProjectFixture) -> None:
    write_result = _run_cli(project_fixture.root, "--write-summary")
    check_result = _run_cli(project_fixture.root)
    artifact_result = _run_cli(project_fixture.root, "--check-artifacts")

    assert write_result.returncode == 0, write_result.stderr
    assert check_result.returncode == 0, check_result.stderr
    assert artifact_result.returncode == 0, artifact_result.stderr
    assert (project_fixture.root / "docs/SECTION_LEDGER.md").is_file()
    assert "status: PASS" in check_result.stdout
    assert "artifacts_checked: true" in artifact_result.stdout


def test_cli_rejects_summary_drift(project_fixture: ProjectFixture) -> None:
    summary = project_fixture.root / "docs/SECTION_LEDGER.md"
    summary.write_text("stale\n", encoding="utf-8")

    result = _run_cli(project_fixture.root)

    assert result.returncode == 1
    assert "SECTION_LEDGER.md" in result.stderr
    assert summary.read_text(encoding="utf-8") == "stale\n"


def test_cli_tamper_failure_is_nonzero(project_fixture: ProjectFixture) -> None:
    (project_fixture.root / "docs/acceptance.md").write_text("tampered\n", encoding="utf-8")

    result = _run_cli(project_fixture.root, "--write-summary")

    assert result.returncode == 1
    assert "status: FAIL" in result.stdout
    assert not (project_fixture.root / "docs/SECTION_LEDGER.md").exists()


def test_cli_does_not_overwrite_summary_for_invalid_json(project_fixture: ProjectFixture) -> None:
    summary = project_fixture.root / "docs/SECTION_LEDGER.md"
    summary.write_text("keep me\n", encoding="utf-8")
    (project_fixture.root / "docs/section_ledger.json").write_text("{broken", encoding="utf-8")

    result = _run_cli(project_fixture.root, "--write-summary")

    assert result.returncode == 1
    assert "JSON" in result.stderr
    assert summary.read_text(encoding="utf-8") == "keep me\n"


@pytest.mark.parametrize("link_kind", ["summary_external", "summary_internal", "docs_parent"])
def test_cli_write_refuses_summary_symlinks_and_external_docs_parents(
    project_fixture: ProjectFixture, tmp_path: Path, link_kind: str
) -> None:
    summary = project_fixture.root / "docs/SECTION_LEDGER.md"
    if link_kind.startswith("summary"):
        external_target = (
            tmp_path / "external-summary.md"
            if link_kind == "summary_external"
            else project_fixture.root / "docs/internal-summary-target.md"
        )
        external_target.write_bytes(b"keep external\n")
        summary.symlink_to(external_target)
    else:
        external_docs = tmp_path / "external-docs"
        (project_fixture.root / "docs").rename(external_docs)
        (project_fixture.root / "docs").symlink_to(external_docs, target_is_directory=True)
        external_target = external_docs / "SECTION_LEDGER.md"
        external_target.write_bytes(b"keep external\n")

    result = _run_cli(project_fixture.root, "--write-summary")

    assert result.returncode == 1
    assert "SECTION_LEDGER.md" in result.stderr
    assert external_target.read_bytes() == b"keep external\n"


@pytest.mark.parametrize("loop_kind", ["summary", "docs_parent"])
def test_cli_reports_cyclic_summary_paths(project_fixture: ProjectFixture, loop_kind: str) -> None:
    if loop_kind == "summary":
        (project_fixture.root / "docs/SECTION_LEDGER.md").symlink_to("SECTION_LEDGER.md")
    else:
        (project_fixture.root / "docs").rename(project_fixture.root / "docs-real")
        (project_fixture.root / "docs").symlink_to("docs", target_is_directory=True)

    result = _run_cli(project_fixture.root, "--write-summary")

    assert result.returncode == 1
    assert "SECTION_LEDGER.md path could not be resolved safely" in result.stderr
    assert "Traceback" not in result.stderr


def test_real_inventory_and_section_26_migration_are_complete() -> None:
    project = REPO_ROOT / "johnhull"
    inventory = json.loads((project / "docs/section_inventory.json").read_text(encoding="utf-8"))
    ledger = json.loads((project / "docs/section_ledger.json").read_text(encoding="utf-8"))

    result = evaluate_ledger(project, inventory, ledger)
    section_26_ids = [entry["id"] for entry in inventory["entries"] if entry["chapter"] == 26]
    accepted = next(section for section in ledger["sections"] if section["id"] == "26.9")

    assert result["status"] == "PASS", result["errors"]
    assert result["inventory_total"] == 306
    assert result["counts"] == {
        "unreviewed": 301,
        "gaps_found": 0,
        "pending_validation": 0,
        "accepted": 5,
        "out_of_scope": 0,
    }
    assert "26.17" in section_26_ids
    asian = next(section for section in ledger["sections"] if section["id"] == "26.13")
    # Accepted after the review's F1-F7 were fixed; the re-review was waived by the user,
    # which the acceptance note and the ledger limitations both say.
    assert asian["status"] == "accepted"
    assert any("再レビュー" in text for text in asian["limitations"])
    assert [row["id"] for row in asian["requirements"]] == [f"A{i:02}" for i in range(1, 7)]
    assert asian["requirements"][1]["coverage"]["implementation"]["state"] == "verified"
    assert asian["requirements"][3]["coverage"]["independent_validation"]["state"] == "verified"
    assert asian["requirements"][3]["coverage"]["visualization"]["state"] == "not_applicable"
    assert all(
        axis["state"] in {"verified", "not_applicable"}
        for row in asian["requirements"]
        for axis in row["coverage"].values()
    )
    shout = next(section for section in ledger["sections"] if section["id"] == "26.12")
    assert shout["status"] == "accepted"
    assert [row["id"] for row in shout["requirements"]] == [f"S{i:02}" for i in range(1, 7)]
    assert shout["requirements"][1]["coverage"]["independent_validation"]["state"] == "verified"
    assert all(
        axis["state"] == "verified"
        for row in shout["requirements"]
        for axis in row["coverage"].values()
    )
    binary = next(section for section in ledger["sections"] if section["id"] == "26.10")
    assert binary["status"] == "accepted"
    assert [row["id"] for row in binary["requirements"]] == [f"D{i:02}" for i in range(1, 7)]
    assert binary["requirements"][1]["coverage"]["independent_validation"]["state"] == "verified"
    assert all(row["coverage"]["rendered"]["state"] == "verified" for row in binary["requirements"])
    assert [requirement["id"] for requirement in accepted["requirements"]] == [
        "B01",
        "B02",
        "B03",
        "B04",
        "B05",
        "B06",
        "B07",
        "B08",
        "B09",
    ]
