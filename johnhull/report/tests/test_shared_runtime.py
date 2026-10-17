"""The shared Book/portal runtime is validated once against its manifest."""

import json

from johnhull.scripts import shared_runtime


def test_runtime_classification_is_path_based():
    assert shared_runtime.is_runtime("book/_config.yml")
    assert shared_runtime.is_runtime("book/_toc.yml")
    assert shared_runtime.is_runtime("book/_ext/book_runtime.py")
    assert shared_runtime.is_runtime("book/_static/mathjax-3.2.2-tex-svg-full.js")
    assert shared_runtime.is_runtime("book/_static/deleted-since.css")
    assert shared_runtime.is_runtime("report/assets/style.css")
    assert not shared_runtime.is_runtime("book/_static/MATHJAX.md")
    assert not shared_runtime.is_runtime("book/_ext/__pycache__/book_runtime.cpython-312.pyc")
    assert not shared_runtime.is_runtime("report/report_builder/render.py")
    assert not shared_runtime.is_runtime("scripts/evidence_dependencies.json")
    assert not shared_runtime.is_runtime("volumes/18_ml_surrogates/ml_surrogates.ipynb")


def _project(tmp_path):
    for name, data in {
        "book/_config.yml": "title: Book\n",
        "book/_toc.yml": "root: intro\n",
        "book/_static/app.js": "// js\n",
        "report/assets/style.css": "body {}\n",
    }.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(data)
    (tmp_path / "docs/validation").mkdir(parents=True)
    return tmp_path


def test_manifest_detects_changed_added_and_missing_files(tmp_path):
    project = _project(tmp_path)
    shared_runtime.write(project, ["make hull-book: PASS"], "test")
    assert shared_runtime.check(project) == []

    (project / "book/_config.yml").write_text("title: Changed\n")
    (project / "book/_static/new.css").write_text("p {}\n")
    (project / "report/assets/style.css").unlink()
    problems = shared_runtime.check(project)
    assert any("book/_config.yml changed" in p for p in problems)
    assert any("book/_static/new.css is not recorded" in p for p in problems)
    assert any("report/assets/style.css is recorded but missing" in p for p in problems)


def test_manifest_without_checks_is_rejected(tmp_path):
    project = _project(tmp_path)
    manifest = shared_runtime.write(project, ["make hull-book: PASS"], "test")
    manifest["checks"] = []
    (project / shared_runtime.MANIFEST).write_text(json.dumps(manifest))
    assert shared_runtime.check(project) == [
        f"shared_runtime: {shared_runtime.MANIFEST} records no checks"
    ]


def test_real_runtime_matches_its_manifest():
    assert shared_runtime.check() == []
