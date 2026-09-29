"""Verify §26.2 delivery and eighteen earlier sections' D1 rechecks on M19 assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SECTION = "docs/validation/section-26-2/"
OUT = PROJECT / SECTION / "m19-check.json"
RECHECK_DIR = "docs/validation/d1-recheck"
EARLIER = ["26.1", *[f"26.{n}" for n in range(9, 18)], *[f"27.{n}" for n in range(1, 9)]]
KEYS = (
    "perpetual_value",
    "perpetual_boundaries",
    "perpetual_zero_dividend",
    "perpetual_convergence",
)


def digest(name: str) -> str:
    return hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()


def check_record(name: str) -> dict:
    """Require a PASS record whose hashed inputs and outputs are still current."""
    record = json.loads((PROJECT / name).read_text(encoding="utf-8"))
    section = record.get("section")
    if record.get("status") != "PASS" or (
        section != "26.2" and not (name.endswith("browser-check.json") and section is None)
    ):
        raise ValueError(f"not a passing §26.2 record: {name}")
    sources = record.get("source_sha256")
    if not isinstance(sources, dict) or not sources:
        raise ValueError(f"missing source_sha256: {name}")
    for category in ("source_sha256", "artifact_sha256"):
        hashes = record.get(category)
        if not isinstance(hashes, dict):
            if category == "artifact_sha256" and name.endswith("numerical-check.json"):
                continue  # The numerical verifier stores the reference digest as one string.
            raise ValueError(f"missing {category}: {name}")
        if not hashes:
            raise ValueError(f"empty {category}: {name}")
        for file, expected in hashes.items():
            if digest(file) != expected:
                raise ValueError(f"stale {category}: {name}: {file}")
    return record


def check_browser(browser: dict) -> None:
    """Require every figure and width on both rendered surfaces."""
    expected = {(key, width) for key in KEYS for width in (1440, 1000)}
    pages = browser.get("pages")
    if browser.get("status") != "PASS" or not isinstance(pages, dict):
        raise ValueError("browser matrix is not passing")
    if set(pages) != {"book", "portal"}:
        raise ValueError("browser matrix must contain Book and portal")
    if browser.get("state_checks") != 16 or browser.get("screenshots") != 16:
        raise ValueError("incomplete browser matrix")
    math = browser.get("book_math", {})
    if math.get("rendered", 0) <= 20 or math.get("errors") != 0:
        raise ValueError("Book math rendering failed")
    for surface, page in pages.items():
        states = page.get("states", [])
        actual = [(row.get("figure"), row.get("width")) for row in states]
        if len(actual) != len(expected) or set(actual) != expected:
            raise ValueError(f"incomplete browser matrix: {surface}")
        if any(row.get("numeric_checked") is not True for row in states):
            raise ValueError(f"browser numeric check failed: {surface}")
        screenshots = page.get("screenshots", [])
        expected_paths = {SECTION + f"{surface}-{key}-{width}.png" for key, width in expected}
        if len(screenshots) != len(expected) or set(screenshots) != expected_paths:
            raise ValueError(f"incomplete browser matrix screenshots: {surface}")
        if (
            page.get("numeric_mutation_rejected") is not True
            or page.get("page_errors")
            or page.get("unapproved_requests")
        ):
            raise ValueError(f"browser checks failed: {surface}")


def check_d1(section_id: str) -> tuple[str, dict]:
    """Check the newest PASS schema-2 D1 record and every file it fingerprints."""
    folder = PROJECT / RECHECK_DIR / f"section-{section_id.replace('.', '-')}"
    records = sorted(
        path for path in folder.glob("*.json") if not path.name.endswith(".browser.json")
    )
    if not records:
        raise ValueError(f"no M19 D1 record for §{section_id}")
    path = records[-1]
    name = path.relative_to(PROJECT).as_posix()
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("schema_version") != 2
        or record.get("status") != "PASS"
        or record.get("section_id") != section_id
        or record.get("decision") not in ("redrawn", "reused")
    ):
        raise ValueError(f"D1 recheck not passing: {name}")
    baseline = (record.get("baseline") or {}).get("record")
    if record["decision"] == "reused" and not (PROJECT / str(baseline)).is_file():
        raise ValueError(f"§{section_id}: reused D1 record without its baseline")
    checks = record.get("checks", {})
    if not checks or any(row.get("status") != "PASS" for row in checks.values()):
        raise ValueError(f"D1 checks failed: {name}")
    if record.get("storage_verification", {}).get("status") != "PASS":
        raise ValueError(f"D1 storage verification failed: {name}")
    for category in ("source_sha256", "artifact_sha256"):
        hashes = record.get(category, {})
        for file, expected in hashes.items():
            if digest(file) != expected:
                raise ValueError(f"stale D1 {category}: {name}: {file}")
    return name, {
        "decision": record["decision"],
        "images": len(record["images"]),
        "stored_new_bytes": record["observations"]["stored_new_bytes"],
        "tests_passed": checks["pytest"]["passed"],
        "baseline": baseline,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(PROJECT / "scripts"))
    sys.path.insert(0, str(PROJECT / "hullkit/src"))
    from verify_american_mc_notebook import check as check_vol06_notebook
    from verify_perpetual_notebook import check as check_exotics_notebook
    from verify_perpetual_numerics import evaluate, negative_controls

    reference = json.loads((PROJECT / SECTION / "reference.json").read_text(encoding="utf-8"))
    findings, errors = evaluate(reference)
    if findings:
        raise ValueError(f"§26.2 numerical check failed: {findings[:2]}")
    controls = negative_controls(reference)
    if not controls or any(not row["rejected"] for row in controls):
        raise ValueError("§26.2 numerical negative control accepted")
    for label, check in (
        ("vol10", check_exotics_notebook),
        ("vol06", check_vol06_notebook),
    ):
        findings = check()
        if findings:
            raise ValueError(f"{label} notebook check failed: {findings[:2]}")

    record_names = [
        SECTION + name
        for name in ("numerical-check.json", "notebook-check.json", "browser-check.json")
    ]
    numerical, notebook, browser = (check_record(name) for name in record_names)
    if numerical.get("artifact_sha256") != digest(SECTION + "reference.json"):
        raise ValueError("numerical reference digest changed")
    if not notebook.get("negative_controls") or any(
        not row.get("rejected") for row in notebook["negative_controls"]
    ):
        raise ValueError("notebook negative control accepted")
    check_browser(browser)
    regression = {}
    for section_id in EARLIER:
        name, summary = check_d1(section_id)
        record_names.append(name)
        regression[section_id] = summary

    sources = [
        "scripts/build_perpetual_acceptance_record.py",
        "scripts/build_perpetual_reference.py",
        "scripts/verify_perpetual_numerics.py",
        "scripts/verify_perpetual_notebook.py",
        "scripts/verify_perpetual_browser.cjs",
        "scripts/verify_accepted_vol06_notebook.py",
        "scripts/evidence_dependencies.json",
        "hullkit/src/hullkit/perpetual_american.py",
        "hullkit/src/hullkit/_perpetual_american_lesson.py",
        "hullkit/tests/test_perpetual_american.py",
        "hullkit/tests/test_perpetual_american_lesson.py",
        "report/tests/test_perpetual_american_notebook.py",
        "report/tests/test_report_build.py",
        "report/report_builder/figures.py",
        "report/assets/style.css",
        "volumes/10_exotics_martingales/build_exotics_notebook.py",
        "volumes/10_exotics_martingales/exotics.ipynb",
        "volumes/06_numerical_methods/numerical.ipynb",
        "release_manifest.json",
        *record_names,
    ]
    artifacts = [
        SECTION + "reference.json",
        "report/site/exotics.html",
        "book/_build/html/notebooks/10_exotics.html",
        "report/site/numerics.html",
        "book/_build/html/notebooks/06_numerical.html",
        *(
            SECTION + f"{surface}-{key}-{width}.png"
            for surface in ("book", "portal")
            for key in KEYS
            for width in (1440, 1000)
        ),
    ]
    result = {
        "section": "26.2",
        "milestone": "M19",
        "status": "PASS",
        "numerical": {
            "method": reference["independent_method"],
            "cases": numerical["cases"],
            "max_abs_error": errors["price"],
            "max_boundary_error": errors["boundary"],
            "max_exponent_error": errors["exponent"],
            "negative_controls_rejected": [row["mutation"] for row in controls],
        },
        "notebook": {
            "cells": notebook["cells"],
            "lesson_cells": notebook["lesson_cells"],
            "preserved_cells_outside_lesson": notebook["preserved_cells_outside_lesson"],
            "negative_controls_rejected": [
                row["mutation"] for row in notebook["negative_controls"]
            ],
        },
        "browser": {
            "chromium": browser["browser_version"],
            "surfaces": sorted(browser["pages"]),
            "widths": [1440, 1000],
            "state_checks": browser["state_checks"],
            "screenshots": browser["screenshots"],
            "numeric_mutation_rejected": True,
            "book_math": browser["book_math"],
        },
        "regression": {
            "sections": EARLIER,
            "d1": regression,
            "redrawn": sorted(s for s, row in regression.items() if row["decision"] == "redrawn"),
            "reused": sorted(s for s, row in regression.items() if row["decision"] == "reused"),
            "stored_new_bytes": sum(row["stored_new_bytes"] for row in regression.values()),
            "browser": "each accepted section's verifier rerun on M19 Book/portal assets through the D1 driver; new images live in the C:/F: artifact stores",
            "vol06_notebook_unchanged": True,
        },
        "source_sha256": {name: digest(name) for name in sources},
        "artifact_sha256": {name: digest(name) for name in artifacts},
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("m19-check.json is missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §26.2 M19 acceptance and eighteen earlier lessons")


if __name__ == "__main__":
    main()
