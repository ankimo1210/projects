"""Verify §26.5 delivery and twenty-one earlier sections' D1 rechecks on M22 assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    from . import evidence_record
except ImportError:  # executed as a script from johnhull/scripts
    import evidence_record

PROJECT = Path(__file__).resolve().parents[1]
SECTION = "docs/validation/section-26-5/"
OUT = PROJECT / SECTION / "m22-check.json"
RECHECK_DIR = "docs/validation/d1-recheck"
EARLIER = [
    "26.1",
    "26.2",
    "26.3",
    "26.4",
    *[f"26.{n}" for n in range(9, 18)],
    *[f"27.{n}" for n in range(1, 9)],
]
KEYS = (
    "forward_contract",
    "forward_homogeneity",
    "forward_start_delay",
    "forward_fixed_expiry",
)
RECORD_SOURCES = {
    "numerical-check.json": {
        "scripts/build_forward_start_reference.py",
        "scripts/verify_forward_start_numerics.py",
        "hullkit/src/hullkit/forward_start.py",
        "hullkit/src/hullkit/bsm.py",
    },
    "notebook-check.json": {
        "scripts/verify_forward_start_notebook.py",
        "scripts/verify_core_notebooks.py",
        "hullkit/src/hullkit/_forward_start_lesson.py",
        "hullkit/src/hullkit/forward_start.py",
        "hullkit/src/hullkit/bsm.py",
        SECTION + "reference.json",
        SECTION + "numerical-check.json",
        "volumes/10_exotics_martingales/build_exotics_notebook.py",
        "volumes/10_exotics_martingales/exotics.ipynb",
    },
    "browser-check.json": {
        "hullkit/src/hullkit/forward_start.py",
        "hullkit/src/hullkit/bsm.py",
        "hullkit/src/hullkit/_forward_start_lesson.py",
        "scripts/build_forward_start_reference.py",
        "scripts/verify_forward_start_browser.cjs",
        SECTION + "reference.json",
        SECTION + "numerical-check.json",
        "volumes/10_exotics_martingales/build_exotics_notebook.py",
        "volumes/10_exotics_martingales/exotics.ipynb",
        "report/report_builder/figures.py",
        "report/assets/style.css",
    },
}
RECORD_ARTIFACTS = {
    "notebook-check.json": {
        "volumes/10_exotics_martingales/exotics.ipynb",
    },
    "browser-check.json": {
        "report/site/exotics.html",
        "book/_build/html/notebooks/10_exotics.html",
        *(
            SECTION + f"{surface}-{key}-{width}.png"
            for surface in ("book", "portal")
            for key in KEYS
            for width in (1440, 1000)
        ),
    },
}


def digest(name: str) -> str:
    return hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()


def check_record(
    name: str,
    *,
    required_sources: set[str] | frozenset[str] = frozenset(),
    required_artifacts: set[str] | frozenset[str] = frozenset(),
) -> dict:
    """Require a PASS record whose hashed inputs and outputs are still current."""
    record = json.loads((PROJECT / name).read_text(encoding="utf-8"))
    section = record.get("section")
    if record.get("status") != "PASS" or (
        section != "26.5" and not (name.endswith("browser-check.json") and section is None)
    ):
        raise ValueError(f"not a passing §26.5 record: {name}")
    sources = record.get("source_sha256")
    if not isinstance(sources, dict) or not sources:
        raise ValueError(f"missing source_sha256: {name}")
    missing = required_sources - sources.keys()
    if missing:
        raise ValueError(f"missing source_sha256: {name}: {sorted(missing)}")
    artifacts = record.get("artifact_sha256")
    if isinstance(artifacts, dict):
        missing = required_artifacts - artifacts.keys()
        if missing:
            raise ValueError(f"missing artifact_sha256: {name}: {sorted(missing)}")
    for category in ("source_sha256", "artifact_sha256"):
        hashes = record.get(category)
        if not isinstance(hashes, dict):
            if category == "artifact_sha256" and name.endswith("numerical-check.json"):
                if hashes != digest(SECTION + "reference.json"):
                    raise ValueError("numerical reference digest changed")
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


def check_d1_payload(section_id: str, name: str, record: dict) -> None:
    """Reject incomplete schema-2 records before checking current files and stores."""
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
    for key in ("browser", "runtime_probe", "pytest"):
        if not isinstance(checks.get(key), dict) or checks[key].get("status") != "PASS":
            raise ValueError(f"D1 {key} check failed: {name}")
    if any(row.get("status") != "PASS" for row in checks.values()):
        raise ValueError(f"D1 checks failed: {name}")
    storage = record.get("storage_verification", {})
    for key in ("status", "primary", "mirror"):
        status = storage.get(key)
        if key != "status":
            status = status.get("status") if isinstance(status, dict) else None
        if status != "PASS":
            raise ValueError(f"D1 storage {key} verification failed: {name}")
    if not isinstance(record.get("images"), list) or not record["images"]:
        raise ValueError(f"D1 images missing: {name}")
    if record.get("dependency_fingerprint", {}).get("unknown"):
        raise ValueError(f"D1 unknown dependencies: {name}")
    for category in ("source_sha256", "artifact_sha256"):
        hashes = record.get(category)
        if not isinstance(hashes, dict) or not hashes:
            raise ValueError(f"D1 {category} missing: {name}")
    problems = evidence_record.validate_record(PROJECT, record)
    if problems:
        raise ValueError(f"D1 record invalid: {name}: {problems[:2]}")


def check_d1(section_id: str) -> tuple[str, dict]:
    """Check the newest PASS schema-2 D1 record and both artifact-store copies."""
    folder = PROJECT / RECHECK_DIR / f"section-{section_id.replace('.', '-')}"
    records = sorted(
        path for path in folder.glob("*.json") if not path.name.endswith(".browser.json")
    )
    if not records:
        raise ValueError(f"no M22 D1 record for §{section_id}")
    path = records[-1]
    name = path.relative_to(PROJECT).as_posix()
    record = json.loads(path.read_text(encoding="utf-8"))
    check_d1_payload(section_id, name, record)
    problems = evidence_record.validate_record(PROJECT, record, check_artifacts=True)
    if problems:
        raise ValueError(f"D1 artifact store invalid: {name}: {problems[:2]}")
    for category in ("source_sha256", "artifact_sha256"):
        hashes = record[category]
        for file, expected in hashes.items():
            if digest(file) != expected:
                raise ValueError(f"stale D1 {category}: {name}: {file}")
    return name, {
        "record": name,
        "decision": record["decision"],
        "images": len(record["images"]),
        "stored_new_bytes": record["observations"]["stored_new_bytes"],
        "tests_passed": record["checks"]["pytest"]["passed"],
        "baseline": (record.get("baseline") or {}).get("record"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(PROJECT / "scripts"))
    sys.path.insert(0, str(PROJECT / "hullkit/src"))
    from verify_forward_start_notebook import check as check_exotics_notebook
    from verify_forward_start_numerics import negative_controls, verify

    reference = json.loads((PROJECT / SECTION / "reference.json").read_text(encoding="utf-8"))
    numbers = verify(reference)
    controls = negative_controls(reference)
    if not controls or any(not row["rejected"] for row in controls):
        raise ValueError("§26.5 numerical negative control accepted")
    findings, notebook_controls = check_exotics_notebook()
    if findings:
        raise ValueError(f"vol10 notebook check failed: {findings[:2]}")
    if not notebook_controls or any(not row["rejected"] for row in notebook_controls):
        raise ValueError("§26.5 notebook negative control accepted")

    record_names = [
        SECTION + name
        for name in ("numerical-check.json", "notebook-check.json", "browser-check.json")
    ]
    numerical, notebook, browser = (
        check_record(
            name,
            required_sources=RECORD_SOURCES[Path(name).name],
            required_artifacts=RECORD_ARTIFACTS.get(Path(name).name, frozenset()),
        )
        for name in record_names
    )
    if not notebook.get("negative_controls") or any(
        not row.get("rejected") for row in notebook["negative_controls"]
    ):
        raise ValueError("notebook negative control accepted")
    if not numerical.get("negative_controls") or any(
        not row.get("rejected") for row in numerical["negative_controls"]
    ):
        raise ValueError("numerical negative control accepted")
    if (
        numerical["case_count"] != numbers["case_count"]
        or numerical["max_price_error"] != numbers["max_price_error"]
        or any(
            numerical[key] != numbers[key]
            for key in (
                "max_quadrature_error",
                "max_mc_standard_errors",
                "mc_paths",
                "same_life_zero_yield_error",
                "homogeneity_error",
                "example_price",
                "same_life_atm",
            )
        )
        or numerical["negative_controls"] != controls
    ):
        raise ValueError("numerical record differs from current calculation")
    if notebook["negative_controls"] != notebook_controls:
        raise ValueError("notebook record differs from current negative controls")
    check_browser(browser)
    regression = {}
    for section_id in EARLIER:
        name, summary = check_d1(section_id)
        record_names.append(name)
        regression[section_id] = summary

    sources = [
        "scripts/build_forward_start_acceptance_record.py",
        "scripts/build_forward_start_reference.py",
        "scripts/verify_forward_start_numerics.py",
        "scripts/verify_forward_start_notebook.py",
        "scripts/verify_forward_start_browser.cjs",
        "scripts/verify_core_notebooks.py",
        "scripts/evidence_dependencies.json",
        "scripts/update_forward_start_ledger.py",
        "scripts/verify_section_ledger.py",
        "hullkit/src/hullkit/forward_start.py",
        "hullkit/src/hullkit/bsm.py",
        "hullkit/src/hullkit/_forward_start_lesson.py",
        "hullkit/tests/test_forward_start.py",
        "hullkit/tests/test_forward_start_reference.py",
        "hullkit/tests/test_forward_start_numerics.py",
        "hullkit/tests/test_forward_start_lesson.py",
        "report/tests/test_forward_start_notebook.py",
        "report/tests/test_forward_start_acceptance_record.py",
        "report/tests/test_forward_start_ledger_update.py",
        "report/tests/test_forward_start_registry.py",
        "report/tests/test_section_ledger.py",
        "report/tests/test_report_build.py",
        "report/report_builder/figures.py",
        "report/assets/style.css",
        "volumes/10_exotics_martingales/build_exotics_notebook.py",
        "volumes/10_exotics_martingales/exotics.ipynb",
        "release_manifest.json",
        *record_names,
    ]
    artifacts = [
        SECTION + "reference.json",
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
        "section": "26.5",
        "milestone": "M22",
        "status": "PASS",
        "numerical": {
            "method": "independent two-increment GBM density quadrature and two-time Monte Carlo",
            "cases": numbers["case_count"],
            "max_abs_error": numbers["max_price_error"],
            **{
                key: numbers[key]
                for key in (
                    "max_quadrature_error",
                    "max_mc_standard_errors",
                    "mc_paths",
                    "same_life_zero_yield_error",
                    "homogeneity_error",
                    "example_price",
                    "same_life_atm",
                )
            },
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
            "browser": "each accepted section's verifier rerun on M22 Book/portal assets through the D1 driver; new images live in the C:/F: artifact stores",
        },
        "source_sha256": {name: digest(name) for name in sources},
        "artifact_sha256": {name: digest(name) for name in artifacts},
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("m22-check.json is missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §26.5 M22 acceptance and twenty-one earlier lessons")


if __name__ == "__main__":
    main()
