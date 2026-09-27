"""Pure parts of the D1-preflight comparison driver (overlay, parsing, summaries)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from johnhull.scripts.d1_preflight_compare import (
    build_overlay,
    coverage_states,
    parse_json_lines,
)


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    for name in ("hullkit/src", "report/site", "book/_build", "scripts"):
        (root / name).mkdir(parents=True)
    section = root / "docs/validation/section-27-3"
    section.mkdir(parents=True)
    (section / "reference.json").write_text('{"a": 1}', encoding="utf-8")
    (section / "numerical-check.json").write_text('{"status": "PASS"}', encoding="utf-8")
    (section / "book-ivf_smile-1440.png").write_bytes(b"accepted image")
    (root / "docs/validation/section-27-2").mkdir()
    (root / "docs/SECTION_LEDGER.md").write_text("# ledger", encoding="utf-8")
    return root


def test_overlay_links_the_project_and_copies_only_the_verifier_inputs(project, tmp_path):
    overlay = tmp_path / "overlay"
    build_overlay(
        project,
        overlay,
        "docs/validation/section-27-3",
        ["docs/validation/section-27-3/reference.json"],
    )
    assert (overlay / "hullkit").is_symlink()
    assert (overlay / "report").resolve() == (project / "report").resolve()
    assert (overlay / "docs/SECTION_LEDGER.md").is_symlink()
    assert (overlay / "docs/validation/section-27-2").is_symlink()
    section = overlay / "docs/validation/section-27-3"
    assert section.is_dir() and not section.is_symlink()
    copied = section / "reference.json"
    assert copied.read_text(encoding="utf-8") == '{"a": 1}' and not copied.is_symlink()
    assert not (section / "book-ivf_smile-1440.png").exists()


def test_writes_into_the_overlay_section_never_reach_the_project(project, tmp_path):
    overlay = tmp_path / "overlay"
    build_overlay(project, overlay, "docs/validation/section-27-3", [])
    (overlay / "docs/validation/section-27-3/book-ivf_smile-1440.png").write_bytes(b"new capture")
    accepted = project / "docs/validation/section-27-3/book-ivf_smile-1440.png"
    assert accepted.read_bytes() == b"accepted image"


def test_overlay_refuses_an_existing_directory(project, tmp_path):
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    with pytest.raises(FileExistsError):
        build_overlay(project, overlay, "docs/validation/section-27-3", [])


def test_overlay_inputs_must_live_in_the_section_directory(project, tmp_path):
    with pytest.raises(ValueError, match="section directory"):
        build_overlay(
            project,
            tmp_path / "overlay",
            "docs/validation/section-27-3",
            ["docs/SECTION_LEDGER.md"],
        )


def test_parse_json_lines_keeps_only_json_objects():
    output = 'noise\n{"wrapper": {"renames": 2}}\n[1, 2]\n{"status": "PASS"}\n'
    assert parse_json_lines(output) == [{"wrapper": {"renames": 2}}, {"status": "PASS"}]


def test_coverage_states_lists_surface_figure_and_width():
    record = {
        "pages": {
            "portal": {"states": [{"figure": "a", "width": 1440, "numeric_checked": True}]},
            "book": {"states": [{"figure": "a", "width": 1000, "numeric_checked": True}]},
        }
    }
    assert coverage_states(record) == [
        ["book", "a", 1000, True],
        ["portal", "a", 1440, True],
    ]


# --- the Node wrapper ----------------------------------------------------------------

WRAPPER = Path(__file__).resolve().parents[2] / "scripts/run_browser_verifier.cjs"
FAKE_VERIFIER = """const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
fs.writeFileSync(path.join(root, 'docs/validation/section-27-3/out.txt'), 'heading 10. Old');
"""


def _wrapper_project(tmp_path, renames):
    project = tmp_path / "project"
    (project / "scripts").mkdir(parents=True)
    (project / "scripts/verify.cjs").write_text(FAKE_VERIFIER, encoding="utf-8")
    (project / "docs/validation/section-27-3").mkdir(parents=True)
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "sections": {
                    "27.3": {"verifier": "scripts/verify.cjs", "verifier_text_renames": renames}
                },
            }
        ),
        encoding="utf-8",
    )
    overlay = tmp_path / "overlay"
    build_overlay(project, overlay, "docs/validation/section-27-3", [])
    return project, overlay, config


def _run_wrapper(config, project, overlay):
    return subprocess.run(
        ["node", str(WRAPPER), str(config), "27.3", str(project), str(overlay)],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_wrapper_redirects_the_verifier_root_and_applies_declared_renames(tmp_path):
    project, overlay, config = _wrapper_project(tmp_path, {"10. Old": "12. New"})
    completed = _run_wrapper(config, project, overlay)
    assert completed.returncode == 0, completed.stderr
    written = overlay / "docs/validation/section-27-3/out.txt"
    assert written.read_text(encoding="utf-8") == "heading 12. New"
    assert not (project / "docs/validation/section-27-3/out.txt").exists()
    meta = parse_json_lines(completed.stdout)[0]["wrapper"]
    assert meta["renames"] == [{"from": "10. Old", "to": "12. New"}]
    assert meta["original_sha256"] != meta["executed_sha256"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_wrapper_rejects_a_rename_that_does_not_match_exactly_once(tmp_path):
    project, overlay, config = _wrapper_project(tmp_path, {"11. Missing": "13. New"})
    completed = _run_wrapper(config, project, overlay)
    assert completed.returncode != 0
    assert "matched 0 times" in completed.stderr
    assert not (overlay / "docs/validation/section-27-3/out.txt").exists()


def test_overlay_replacements_change_only_the_named_file(project, tmp_path):
    (project / "report/site/numerics.html").write_text("original", encoding="utf-8")
    (project / "report/site/other.html").write_text("other", encoding="utf-8")
    overlay = tmp_path / "overlay"
    build_overlay(
        project,
        overlay,
        "docs/validation/section-27-3",
        [],
        replacements={"report/site/numerics.html": b"mutated"},
    )
    assert (overlay / "report/site/numerics.html").read_bytes() == b"mutated"
    assert not (overlay / "report/site/numerics.html").is_symlink()
    assert (overlay / "report/site/other.html").is_symlink()
    assert (overlay / "hullkit").is_symlink()
    assert (project / "report/site/numerics.html").read_text(encoding="utf-8") == "original"


def test_overlay_replacement_must_name_an_existing_file(project, tmp_path):
    with pytest.raises(FileNotFoundError):
        build_overlay(
            project,
            tmp_path / "overlay",
            "docs/validation/section-27-3",
            [],
            replacements={"report/site/missing.html": b"x"},
        )


def test_source_hashes_pin_section_inputs_but_not_the_driver(tmp_path):
    from johnhull.scripts.d1_preflight_compare import (
        DRIVER_FILES,
        _source_hashes,
        driver_provenance,
    )

    root = tmp_path / "records"
    files = {
        "volumes/nb.ipynb": b"{}",
        "hullkit/src/hullkit/lv.py": b"x = 1",
        "docs/validation/section-27-3/reference.json": b"{}",
        "scripts/verify.cjs": b"//",
        "hullkit/tests/test_lv.py": b"def test(): pass",
    }
    for name in DRIVER_FILES:
        files[name] = b"driver"
    for name, data in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(data)
    spec = {"notebook": {"path": "volumes/nb.ipynb"}, "tests": ["hullkit/tests/test_lv.py"]}
    fingerprint = {
        "components": {
            "python_sources": {"hullkit/src/hullkit/lv.py": "0"},
            "data_files": {"docs/validation/section-27-3/reference.json": "0"},
            "verifier": {"scripts/verify.cjs": "0"},
        }
    }
    hashes = _source_hashes(root, spec, fingerprint)
    assert set(hashes) == {
        "volumes/nb.ipynb",
        "hullkit/src/hullkit/lv.py",
        "docs/validation/section-27-3/reference.json",
        "scripts/verify.cjs",
        "hullkit/tests/test_lv.py",
    }
    assert set(driver_provenance(root)) == set(DRIVER_FILES)


def test_overlay_replacement_of_a_verifier_input_is_applied(project, tmp_path):
    overlay = build_overlay(
        project,
        tmp_path / "overlay",
        "docs/validation/section-27-3",
        ["docs/validation/section-27-3/reference.json"],
        replacements={"docs/validation/section-27-3/reference.json": b'{"a": 2}'},
    )
    assert (overlay / "docs/validation/section-27-3/reference.json").read_bytes() == b'{"a": 2}'


def test_overlay_rejects_a_replacement_in_the_section_that_is_not_an_input(project, tmp_path):
    with pytest.raises(ValueError, match="not a verifier input"):
        build_overlay(
            project,
            tmp_path / "overlay",
            "docs/validation/section-27-3",
            ["docs/validation/section-27-3/reference.json"],
            replacements={"docs/validation/section-27-3/numerical-check.json": b"{}"},
        )
