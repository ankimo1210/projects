"""Verify §27.5 delivery and thirteen earlier sections on final M14 assets."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-27-5/m14-check.json"
SECTION = "docs/validation/section-27-5/"
EARLIER = [f"26-{number}" for number in range(9, 18)] + ["27-1", "27-2", "27-3", "27-4"]
KEYS = ("path_grids", "path_interpolation", "path_prices", "path_exact")


def digest(name):
    return hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(PROJECT / "scripts"))
    from verify_path_dependent_notebook import check as check_notebook
    from verify_path_dependent_numerics import evaluate as check_numerics
    from verify_static_replication_notebook import check as check_exotics_notebook

    numerics = check_numerics()
    findings = check_notebook()
    if findings:
        raise ValueError(f"vol06 notebook check failed: {findings[:2]}")
    findings = check_exotics_notebook()
    if findings:
        raise ValueError(f"vol10 notebook changed: {findings[:2]}")

    records = [
        SECTION + name
        for name in ("numerical-check.json", "notebook-check.json", "browser-check.json")
    ]
    records.extend(f"docs/validation/section-{section}/m14-recheck.json" for section in EARLIER)
    records.extend(
        f"docs/validation/section-{section}/browser-m14-recheck.json" for section in EARLIER
    )
    passed = {}
    for name in records:
        record = json.loads((PROJECT / name).read_text(encoding="utf-8"))
        if record.get("status") != "PASS":
            raise ValueError(f"not passing: {name}")
        if name.endswith("/m14-recheck.json"):
            if record.get("lesson_numeric_payload_unchanged") is False:
                raise ValueError(f"earlier lesson data changed: {name}")
            passed[name.split("/")[2].removeprefix("section-")] = record["passed"]
        for category in ("source_sha256", "artifact_sha256"):
            hashes = record.get(category, {})
            if isinstance(hashes, dict):
                for file, expected in hashes.items():
                    if digest(file) != expected:
                        raise ValueError(f"stale {category}: {name}: {file}")
    if numerics["artifact_sha256"] != digest(SECTION + "reference.json"):
        raise ValueError("numerical reference digest changed")

    browser = json.loads((PROJECT / SECTION / "browser-check.json").read_text(encoding="utf-8"))
    notebook = json.loads((PROJECT / SECTION / "notebook-check.json").read_text(encoding="utf-8"))
    if browser["state_checks"] != 16 or browser["screenshots"] != 16:
        raise ValueError("incomplete §27.5 browser matrix")
    sources = [
        "scripts/build_path_dependent_acceptance_record.py",
        "scripts/build_path_dependent_reference.py",
        "scripts/verify_path_dependent_numerics.py",
        "scripts/verify_path_dependent_notebook.py",
        "scripts/verify_path_dependent_browser.cjs",
        "scripts/recheck_accepted_m14.py",
        "scripts/recheck_accepted_m14.cjs",
        "hullkit/src/hullkit/path_dependent_tree.py",
        "hullkit/src/hullkit/_path_dependent_lesson.py",
        "hullkit/tests/test_path_dependent_tree.py",
        "hullkit/tests/test_path_dependent_lesson.py",
        "report/tests/test_path_dependent_notebook.py",
        "report/tests/test_report_build.py",
        "report/report_builder/figures.py",
        "report/assets/style.css",
        "volumes/06_numerical_methods/build_numerical_notebook.py",
        "volumes/06_numerical_methods/numerical.ipynb",
        "release_manifest.json",
        *records,
    ]
    artifacts = [
        SECTION + "reference.json",
        "report/site/numerics.html",
        "book/_build/html/notebooks/06_numerical.html",
        "report/site/exotics.html",
        "book/_build/html/notebooks/10_exotics.html",
        *(
            SECTION + f"{surface}-{key}-{width}.png"
            for surface in ("book", "portal")
            for key in KEYS
            for width in (1440, 1000)
        ),
    ]
    result = {
        "section": "27.5",
        "milestone": "M14",
        "status": "PASS",
        "numerical": {"method": numerics["method"], "measured": numerics["measured"]},
        "notebook": {
            "cells": notebook["cells"],
            "lesson_cells": notebook["lesson_cells"],
            "preserved_cells_outside_lesson": notebook["preserved_cells_outside_lesson"],
            "renumbered_headings": notebook["renumbered_headings"],
            "negative_controls_rejected": [
                r["mutation"] for r in notebook["negative_controls"] if r["rejected"]
            ],
        },
        "browser": {
            "chromium": browser["browser_version"],
            "surfaces": sorted(browser["pages"]),
            "widths": [1440, 1000],
            "state_checks": browser["state_checks"],
            "screenshots": browser["screenshots"],
            "numeric_mutation_rejected": all(
                page["numeric_mutation_rejected"] for page in browser["pages"].values()
            ),
            "book_math": browser["book_math"],
        },
        "regression": {
            "sections": [s.replace("-", ".") for s in EARLIER],
            "tests_passed": passed,
            "browser": "each accepted section's original verifier rerun on M14 Book/portal assets",
            "vol10_notebook_unchanged": True,
        },
        "source_sha256": {name: digest(name) for name in sources},
        "artifact_sha256": {name: digest(name) for name in artifacts},
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("m14-check.json is missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §27.5 M14 acceptance and thirteen earlier lessons")


if __name__ == "__main__":
    main()
