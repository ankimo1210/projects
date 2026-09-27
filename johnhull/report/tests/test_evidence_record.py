"""Schema-2 recheck records and their ledger checks (D1-preflight stage 2)."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from johnhull.report.tests.test_section_ledger import (  # project_fixture is a fixture
    ProjectFixture,
    project_fixture,
)
from johnhull.scripts.evidence_record import baseline_ref, build_record, validate_record
from johnhull.scripts.evidence_store import init_store, manifest_entry
from johnhull.scripts.verify_section_ledger import evaluate_ledger

PNG_A = b"\x89PNG\r\n\x1a\nbaseline-a"
PNG_B = b"\x89PNG\r\n\x1a\nbaseline-b"
COMMIT = "a" * 40
RUNTIME = {
    "browser_version": "145.0.7632.6",
    "mathjax_version": "3.2.2",
    "mathjax_scripts": [{"url": "https://example.test/mathjax.js", "sha256": "f" * 64}],
    "fonts": {
        "portal_plot_text": [{"family": "Liberation Sans", "file": "font.ttf", "sha256": "e" * 64}]
    },
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _fingerprint(digest: str = "1" * 64, unknown=None) -> dict:
    return {
        "section_id": "1.1",
        "rules": {"fingerprint_schema": 1, "normalizer_version": 1, "normalization": []},
        "components": {"notebook_slice": "2" * 64},
        "unknown": list(unknown or []),
        "digest": digest,
    }


def _storage(status: str = "PASS") -> dict:
    return {
        "status": status,
        "primary": {"status": "PASS"},
        "mirror": {"status": status},
        "checked_at": "2026-09-28T00:00:00+00:00",
    }


@pytest.fixture
def stores(tmp_path, monkeypatch):
    primary = init_store(tmp_path / "store-c", role="primary")
    mirror = init_store(tmp_path / "store-f", role="mirror")
    for store in (primary, mirror):
        store.put_bytes(PNG_A)
        store.put_bytes(PNG_B)
    monkeypatch.setenv("PROJECTS_ARTIFACT_STORE", str(primary.root))
    monkeypatch.setenv("PROJECTS_ARTIFACT_MIRROR", str(mirror.root))
    return primary, mirror


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "src/lesson.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "site").mkdir()
    (root / "site/page.html").write_text("<p>page</p>\n", encoding="utf-8")
    return root


def _images():
    return [
        manifest_entry("docs/validation/section-1-1/book-a-1440.png", PNG_A),
        manifest_entry("docs/validation/section-1-1/portal-a-1440.png", PNG_B),
    ]


def _record(project: Path, **overrides) -> dict:
    values = dict(
        run_id="d1-1.1-redrawn",
        created_at="2026-09-28T00:00:00+00:00",
        commit=COMMIT,
        dirty=False,
        section_id="1.1",
        decision="redrawn",
        reasons=["first run under schema 2"],
        fingerprint=_fingerprint(),
        baseline=None,
        images=_images(),
        checks={"browser": {"status": "PASS"}, "pytest": {"status": "PASS"}},
        environment={"runtime": dict(RUNTIME)},
        storage_verification=_storage(),
        source_sha256={"src/lesson.py": _sha((project / "src/lesson.py").read_bytes())},
        artifact_sha256={"site/page.html": _sha((project / "site/page.html").read_bytes())},
    )
    values.update(overrides)
    return build_record(**values)


def _save(project: Path, name: str, record: dict) -> str:
    relative = f"docs/validation/d1-preflight/section-1-1/{name}.json"
    _write(project / relative, record)
    return relative


def _reused(project: Path, baseline_path: str, **overrides) -> dict:
    baseline = json.loads((project / baseline_path).read_text(encoding="utf-8"))
    values = dict(
        run_id="d1-1.1-reused",
        decision="reused",
        reasons=[],
        baseline=baseline_ref(project, baseline_path),
        images=copy.deepcopy(baseline["images"]),
    )
    values.update(overrides)
    return _record(project, **values)


# --- building ---------------------------------------------------------------------


def test_build_record_marks_a_complete_run_as_pass(project):
    record = _record(project)
    assert record["schema_version"] == 2
    assert record["kind"] == "johnhull-section-recheck"
    assert record["status"] == "PASS"
    assert validate_record(project, record) == []


def test_dirty_run_cannot_claim_pass_without_a_reproducible_diff(project):
    record = _record(project, dirty=True)
    assert record["status"] == "FAIL"
    assert any("dirty" in error for error in validate_record(project, record))


def test_raw_browser_record_is_hashed_and_must_remain_available(project):
    raw_path = project / "docs/validation/d1-preflight/raw.browser.json"
    _write(raw_path, {"status": "PASS"})
    record = _record(
        project,
        checks={
            "browser": {
                "status": "PASS",
                "raw_record_path": raw_path.relative_to(project).as_posix(),
                "raw_record_sha256": _sha(raw_path.read_bytes()),
            }
        },
    )
    assert validate_record(project, record) == []
    raw_path.write_text('{"status":"FAIL"}', encoding="utf-8")
    assert any("raw_record_sha256" in error for error in validate_record(project, record))
    raw_path.unlink()
    assert any("raw_record_path" in error for error in validate_record(project, record))


def test_a_failed_check_makes_the_record_fail(project):
    record = _record(project, checks={"browser": {"status": "FAIL"}})
    assert record["status"] == "FAIL"


def test_unverified_storage_makes_the_record_fail(project):
    record = _record(project, storage_verification=_storage("FAIL"))
    assert record["status"] == "FAIL"


def test_a_redrawn_record_needs_images(project):
    record = _record(project, images=[])
    assert record["status"] == "FAIL"
    assert any("images" in error for error in validate_record(project, record))


# --- schema --------------------------------------------------------------------------


def test_unknown_top_level_fields_are_rejected(project):
    record = _record(project) | {"surprise": True}
    assert any("unknown fields" in error for error in validate_record(project, record))


def test_claimed_pass_with_a_failed_check_is_rejected(project):
    record = _record(project)
    record["checks"]["browser"]["status"] = "FAIL"
    assert any("status" in error for error in validate_record(project, record))


def test_wrong_kind_is_rejected(project):
    record = _record(project) | {"kind": "other"}
    assert any("kind" in error for error in validate_record(project, record))


# --- reuse ---------------------------------------------------------------------------


def test_a_reused_record_points_directly_at_a_redrawn_baseline(project):
    baseline_path = _save(project, "redrawn", _record(project))
    record = _reused(project, baseline_path)
    assert record["status"] == "PASS"
    assert validate_record(project, record) == []


def test_reuse_without_a_baseline_is_rejected(project):
    record = _record(project, decision="reused", reasons=[])
    assert record["status"] == "FAIL"
    assert any("baseline" in error for error in validate_record(project, record))


def test_reuse_chains_are_rejected(project):
    first = _save(project, "redrawn", _record(project))
    second = _save(project, "reused", _reused(project, first))
    record = _reused(project, second, run_id="d1-1.1-reused-2")
    assert any("chain" in error for error in validate_record(project, record))


def test_reuse_with_a_different_fingerprint_is_rejected(project):
    baseline_path = _save(project, "redrawn", _record(project))
    record = _reused(project, baseline_path, fingerprint=_fingerprint("9" * 64))
    assert any("fingerprint" in error for error in validate_record(project, record))


def test_reuse_with_an_unknown_dependency_is_rejected(project):
    baseline_path = _save(project, "redrawn", _record(project))
    record = _reused(project, baseline_path, fingerprint=_fingerprint(unknown=["x: missing"]))
    assert any("unknown" in error for error in validate_record(project, record))


def test_reuse_with_different_images_is_rejected(project):
    baseline_path = _save(project, "redrawn", _record(project))
    record = _reused(project, baseline_path, images=_images()[:1])
    assert any("images" in error for error in validate_record(project, record))


def test_reuse_after_a_browser_update_is_rejected(project):
    baseline_path = _save(project, "redrawn", _record(project))
    record = _reused(
        project,
        baseline_path,
        environment={"runtime": RUNTIME | {"browser_version": "146.0.0.0"}},
    )
    assert any("browser_version" in error for error in validate_record(project, record))


def test_reuse_of_an_edited_baseline_is_rejected(project):
    baseline_path = _save(project, "redrawn", _record(project))
    record = _reused(project, baseline_path)
    edited = json.loads((project / baseline_path).read_text(encoding="utf-8"))
    edited["reasons"] = ["edited after the fact"]
    _write(project / baseline_path, edited)
    assert any("record_sha256" in error for error in validate_record(project, record))


# --- artifacts in the store ----------------------------------------------------------


def test_artifact_check_verifies_images_in_both_stores(project, stores):
    record = _record(project)
    assert validate_record(project, record, check_artifacts=True, stores=stores) == []


def test_artifact_check_reports_a_corrupted_mirror_blob(project, stores):
    _, mirror = stores
    blob = mirror.blob_path(_sha(PNG_B))
    blob.chmod(0o644)
    blob.write_bytes(b"broken")
    errors = validate_record(project, _record(project), check_artifacts=True, stores=stores)
    assert any("mirror" in error and "portal-a-1440.png" in error for error in errors)


def test_artifact_check_without_stores_is_unverified(project, monkeypatch):
    monkeypatch.delenv("PROJECTS_ARTIFACT_STORE", raising=False)
    errors = validate_record(project, _record(project), check_artifacts=True)
    assert any("UNVERIFIED" in error for error in errors)


# --- ledger integration -------------------------------------------------------------


def _swap_record(fixture: ProjectFixture, record: dict) -> None:
    path = fixture.root / "docs/record.json"
    _write(path, record)
    fixture.ledger["sections"][0]["evidence"]["record"]["sha256"] = _sha(path.read_bytes())
    fixture.persist()


def _v2_for_fixture(fixture: ProjectFixture) -> dict:
    root = fixture.root
    return build_record(
        run_id="fixture-run",
        created_at="2026-09-28T00:00:00+00:00",
        commit=COMMIT,
        dirty=False,
        section_id="1.1",
        decision="redrawn",
        reasons=["fixture"],
        fingerprint=_fingerprint(),
        baseline=None,
        images=_images(),
        checks={"browser": {"status": "PASS"}},
        environment={"runtime": dict(RUNTIME)},
        storage_verification=_storage(),
        source_sha256={
            "src/implementation.py": _sha((root / "src/implementation.py").read_bytes())
        },
        artifact_sha256={
            "generated/render.html": _sha((root / "generated/render.html").read_bytes())
        },
    )


def test_ledger_accepts_a_schema_2_record(project_fixture):  # noqa: F811
    _swap_record(project_fixture, _v2_for_fixture(project_fixture))
    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )
    assert result["status"] == "PASS", result["errors"]


def test_ledger_still_checks_source_freshness_for_schema_2(project_fixture):  # noqa: F811
    _swap_record(project_fixture, _v2_for_fixture(project_fixture))
    (project_fixture.root / "src/implementation.py").write_text("VALUE = 2\n", encoding="utf-8")
    project_fixture.ledger["sections"][0]["evidence"]["implementation"]["sha256"] = _sha(
        (project_fixture.root / "src/implementation.py").read_bytes()
    )
    project_fixture.persist()
    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )
    assert any("source_sha256" in error for error in result["errors"])


def test_ledger_rejects_an_invalid_schema_2_record(project_fixture):  # noqa: F811
    record = _v2_for_fixture(project_fixture)
    record["decision"] = "reused"
    _swap_record(project_fixture, record)
    result = evaluate_ledger(
        project_fixture.root, project_fixture.inventory, project_fixture.ledger
    )
    assert any("baseline" in error for error in result["errors"])


def test_ledger_artifact_check_uses_the_store_for_schema_2(project_fixture, stores):  # noqa: F811
    _swap_record(project_fixture, _v2_for_fixture(project_fixture))
    result = evaluate_ledger(
        project_fixture.root,
        project_fixture.inventory,
        project_fixture.ledger,
        check_artifacts=True,
    )
    assert result["status"] == "PASS", result["errors"]


def test_ledger_artifact_check_fails_for_a_missing_blob(project_fixture, stores):  # noqa: F811
    primary, _ = stores
    blob = primary.blob_path(_sha(PNG_A))
    blob.chmod(0o644)
    blob.unlink()
    _swap_record(project_fixture, _v2_for_fixture(project_fixture))
    result = evaluate_ledger(
        project_fixture.root,
        project_fixture.inventory,
        project_fixture.ledger,
        check_artifacts=True,
    )
    assert any("missing" in error for error in result["errors"])


def test_ledger_artifact_check_recomputes_full_fingerprint(project_fixture, stores, monkeypatch):  # noqa: F811
    from johnhull.scripts import verify_section_ledger

    root = project_fixture.root
    config = root / "scripts/evidence_dependencies.json"
    _write(config, {"schema_version": 1, "sections": {"1.1": {}}})
    record = _v2_for_fixture(project_fixture)
    record["dependency_fingerprint"]["components"].update(
        {
            "book_section": "3" * 64,
            "portal_cards": {},
            "book_assets": {},
            "portal_assets": {},
        }
    )
    record["environment"]["fingerprint_config"] = "scripts/evidence_dependencies.json"
    record["source_sha256"]["scripts/evidence_dependencies.json"] = _sha(config.read_bytes())
    _swap_record(project_fixture, record)
    monkeypatch.setattr(
        verify_section_ledger.evidence_fingerprint,
        "compute_fingerprint",
        lambda *_args, **_kwargs: {"unknown": [], "digest": "9" * 64},
    )
    result = evaluate_ledger(
        root, project_fixture.inventory, project_fixture.ledger, check_artifacts=True
    )
    assert any("current inputs differ" in error for error in result["errors"])


def test_reuse_after_a_font_change_is_rejected(project):
    baseline_path = _save(project, "redrawn", _record(project))
    record = _reused(
        project,
        baseline_path,
        environment={"runtime": RUNTIME | {"fonts": {"portal_plot_text": ["DejaVu Sans"]}}},
    )
    assert any("fonts" in error for error in validate_record(project, record))
