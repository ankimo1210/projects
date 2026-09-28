"""Verify §27.6 delivery and fourteen earlier sections' D1 rechecks on final M15 assets."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-27-6/m15-check.json"
SECTION = "docs/validation/section-27-6/"
RECHECK_DIR = "docs/validation/d1-recheck"
EARLIER = [f"26.{number}" for number in range(9, 18)] + ["27.1", "27.2", "27.3", "27.4", "27.5"]
KEYS = ("barrier_lattice", "barrier_convergence", "barrier_errors", "barrier_near")


def digest(name):
    return hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()


def d1_record(section_id):
    """The one schema-2 D1 record written for this section in M15."""
    folder = PROJECT / RECHECK_DIR / f"section-{section_id.replace('.', '-')}"
    records = sorted(
        path for path in folder.glob("*.json") if not path.name.endswith(".browser.json")
    )
    if len(records) != 1:
        raise ValueError(f"expected one M15 D1 record for §{section_id}, found {len(records)}")
    return records[0].relative_to(PROJECT).as_posix()


def check_d1(section_id):
    """Summarise a PASS schema-2 record whose section inputs are still current."""
    name = d1_record(section_id)
    record = json.loads((PROJECT / name).read_text(encoding="utf-8"))
    if record.get("schema_version") != 2 or record.get("status") != "PASS":
        raise ValueError(f"D1 recheck not passing: {name}")
    if record["section"] != section_id or record["decision"] not in ("redrawn", "reused"):
        raise ValueError(f"unexpected D1 recheck: {name}")
    for check, result in record["checks"].items():
        if result.get("status") != "PASS":
            raise ValueError(f"D1 check {check} failed: {name}")
    if record["storage_verification"]["status"] != "PASS":
        raise ValueError(f"D1 storage verification failed: {name}")
    for file, expected in record["source_sha256"].items():
        if digest(file) != expected:
            raise ValueError(f"stale D1 source: {name}: {file}")
    for file, expected in record["artifact_sha256"].items():
        if digest(file) != expected:
            raise ValueError(f"stale D1 artifact: {name}: {file}")
    return name, {
        "decision": record["decision"],
        "images": len(record["images"]),
        "stored_new_bytes": record["observations"]["stored_new_bytes"],
        "tests_passed": record["checks"]["pytest"]["passed"],
        "baseline": (record.get("baseline") or {}).get("record"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(PROJECT / "scripts"))
    from verify_barrier_tree_notebook import check as check_notebook
    from verify_barrier_tree_numerics import evaluate as check_numerics
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
    for name in records:
        record = json.loads((PROJECT / name).read_text(encoding="utf-8"))
        if record.get("status") != "PASS":
            raise ValueError(f"not passing: {name}")
        for category in ("source_sha256", "artifact_sha256"):
            hashes = record.get(category, {})
            if isinstance(hashes, dict):
                for file, expected in hashes.items():
                    if digest(file) != expected:
                        raise ValueError(f"stale {category}: {name}: {file}")
    if numerics["artifact_sha256"] != digest(SECTION + "reference.json"):
        raise ValueError("numerical reference digest changed")
    regression = {}
    for section_id in EARLIER:
        name, summary = check_d1(section_id)
        records.append(name)
        regression[section_id] = summary

    browser = json.loads((PROJECT / SECTION / "browser-check.json").read_text(encoding="utf-8"))
    notebook = json.loads((PROJECT / SECTION / "notebook-check.json").read_text(encoding="utf-8"))
    if browser["state_checks"] != 16 or browser["screenshots"] != 16:
        raise ValueError("incomplete §27.6 browser matrix")
    sources = [
        "scripts/build_barrier_tree_acceptance_record.py",
        "scripts/build_barrier_tree_reference.py",
        "scripts/verify_barrier_tree_numerics.py",
        "scripts/verify_barrier_tree_notebook.py",
        "scripts/verify_barrier_tree_browser.cjs",
        "scripts/verify_accepted_vol06_notebook.py",
        "scripts/evidence_dependencies.json",
        "hullkit/src/hullkit/barrier_tree.py",
        "hullkit/src/hullkit/_barrier_tree_lesson.py",
        "hullkit/tests/test_barrier_tree.py",
        "hullkit/tests/test_barrier_tree_lesson.py",
        "report/tests/test_barrier_tree_notebook.py",
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
        "section": "27.6",
        "milestone": "M15",
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
            "sections": EARLIER,
            "d1": regression,
            "redrawn": sorted(s for s, row in regression.items() if row["decision"] == "redrawn"),
            "reused": sorted(s for s, row in regression.items() if row["decision"] == "reused"),
            "stored_new_bytes": sum(row["stored_new_bytes"] for row in regression.values()),
            "browser": (
                "each accepted section's original verifier rerun on M15 Book/portal assets "
                "through the D1 driver; new recheck images live in the C:/F: artifact stores"
            ),
            "vol10_notebook_unchanged": True,
        },
        "source_sha256": {name: digest(name) for name in sources},
        "artifact_sha256": {name: digest(name) for name in artifacts},
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("m15-check.json is missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §27.6 M15 acceptance and fourteen earlier lessons")


if __name__ == "__main__":
    main()
