"""Summarize already-run §26.17 and M9 checks with current source/artifact hashes."""

import argparse
import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-26-17/m9-check.json"
SECTION = "docs/validation/section-26-17/"


def digest(name):
    return hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    records = [
        SECTION + "numerical-check.json",
        SECTION + "notebook-check.json",
        SECTION + "browser-check.json",
        *(f"docs/validation/section-26-{number}/m9-recheck.json" for number in range(9, 17)),
        *(
            f"docs/validation/section-26-{number}/browser-m9-recheck.json"
            for number in range(9, 17)
        ),
    ]
    for name in records:
        record = json.loads((PROJECT / name).read_text(encoding="utf-8"))
        if record.get("status") != "PASS":
            raise ValueError(f"not passing: {name}")
        for category in ("source_sha256", "artifact_sha256"):
            hashes = record.get(category, {})
            if isinstance(hashes, dict):
                for source, expected in hashes.items():
                    if digest(source) != expected:
                        raise ValueError(f"stale {category}: {name}: {source}")
    sources = [
        "scripts/build_static_replication_acceptance_record.py",
        "scripts/build_static_replication_reference.py",
        "scripts/verify_static_replication_notebook.py",
        "scripts/verify_static_replication_browser.cjs",
        "scripts/recheck_exotics_m9.py",
        "scripts/recheck_exotics_m9.cjs",
        "hullkit/src/hullkit/static_replication.py",
        "hullkit/src/hullkit/_static_replication_lesson.py",
        "hullkit/tests/test_static_replication.py",
        "hullkit/tests/test_static_replication_reference.py",
        "hullkit/tests/test_static_replication_lesson.py",
        "report/tests/test_static_replication_notebook.py",
        "report/report_builder/figures.py",
        "report/assets/style.css",
        "volumes/10_exotics_martingales/build_exotics_notebook.py",
        "volumes/10_exotics_martingales/exotics.ipynb",
        *records,
    ]
    artifacts = [
        SECTION + "reference.json",
        "report/site/exotics.html",
        "book/_build/html/notebooks/10_exotics.html",
        *(
            SECTION + f"{surface}-{key}-{width}.png"
            for surface in ("book", "portal")
            for key in (
                "static_boundary",
                "static_ladder",
                "static_boundary_error",
                "static_convergence",
            )
            for width in (1440, 1000)
        ),
    ]
    result = {
        "section": "26.17",
        "status": "PASS",
        "numerical": "independent triangular system and absorbed-density quadrature",
        "notebook": "125 fresh-executed cells; 115 preserved; four exact saved Plotly payloads",
        "browser": "Book/portal, 1440/1000 px, 24 numeric states, 16 screenshots",
        "regression": "eight accepted sections rerun in tests and both browser surfaces",
        "source_sha256": {name: digest(name) for name in sources},
        "artifact_sha256": {name: digest(name) for name in artifacts},
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("m9-check.json is missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §26.17 M9 acceptance record")


if __name__ == "__main__":
    main()
