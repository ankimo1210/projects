"""Rerun the accepted §26.9–§26.15 test suites on the M8 build and write m8-recheck.json.

M8 (§26.16) changed the shared vol10 notebook and builder, the portal registry and
stylesheet, the release manifest and the READMEs, whose hashes the accepted
sections' evidence pins. It changed no pricing code or lesson data of those
sections; this driver records that (lesson data byte-identical to the base
commit) next to a fresh run of each section's own tests. Historical M7 records
are left untouched.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
TESTS = {
    "26-9": ["hullkit/tests/test_barrier_reference.py"],
    "26-10": ["hullkit/tests/test_binary_reference.py", "hullkit/tests/test_binary_lesson.py"],
    "26-11": ["hullkit/tests/test_lookback_reference.py", "hullkit/tests/test_lookback_lesson.py"],
    "26-12": [
        "hullkit/tests/test_shout_reference.py",
        "hullkit/tests/test_shout_tree.py",
        "hullkit/tests/test_shout_lesson.py",
    ],
    "26-13": [
        "hullkit/tests/test_asian_reference.py",
        "hullkit/tests/test_asian_pricing.py",
        "hullkit/tests/test_asian_lesson.py",
    ],
    "26-14": [
        "hullkit/tests/test_exchange_reference.py",
        "hullkit/tests/test_exchange_pricing.py",
        "hullkit/tests/test_exchange_lesson.py",
    ],
    "26-15": [
        "hullkit/tests/test_basket_reference.py",
        "hullkit/tests/test_basket_pricing.py",
        "hullkit/tests/test_basket_lesson.py",
    ],
}
SHARED_SOURCES = (
    "hullkit/src/hullkit/exotics.py",
    "report/report_builder/figures.py",
    "report/assets/style.css",
    "volumes/10_exotics_martingales/build_exotics_notebook.py",
    "volumes/10_exotics_martingales/exotics.ipynb",
    "scripts/recheck_exotics_m8.py",
)
ARTIFACTS = ("report/site/exotics.html", "book/_build/html/notebooks/10_exotics.html")


def _sha256(relative):
    return hashlib.sha256((PROJECT / relative).read_bytes()).hexdigest()


def _base_bytes(reference, relative):
    completed = subprocess.run(
        ["git", "show", f"{reference}:johnhull/{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    return completed.stdout if completed.returncode == 0 else None


def _sources(section):
    record = PROJECT / f"docs/validation/section-{section}/m7-recheck.json"
    names = set(TESTS[section]) | set(SHARED_SOURCES)
    if record.is_file():
        names |= set(json.loads(record.read_text(encoding="utf-8"))["source_sha256"])
    return {name: _sha256(name) for name in sorted(names)}


def recheck(section, base):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        str(PROJECT / part) for part in ("hullkit/src", "scripts", "report")
    )
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *TESTS[section]]
    completed = subprocess.run(
        command, cwd=PROJECT, env=environment, capture_output=True, text=True, check=False
    )
    lesson = PROJECT / f"docs/validation/section-{section}/lesson-data.json"
    unchanged = None
    if lesson.is_file():
        unchanged = _base_bytes(base, f"docs/validation/section-{section}/lesson-data.json") == (
            lesson.read_bytes()
        )
    summary = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
    passed = int(summary.split(" passed")[0].split()[-1]) if " passed" in summary else 0
    status = "PASS" if completed.returncode == 0 and unchanged is not False else "FAIL"
    return {
        "status": status,
        "milestone": "M8",
        "base_commit": base,
        "lesson_numeric_payload_unchanged": unchanged,
        "hash_refresh": [],
        "checked_at": datetime.now(UTC).isoformat(),
        "command": "python -m pytest -q -p no:cacheprovider " + " ".join(TESTS[section]),
        "environment": {"PYTHONPATH": "hullkit/src:scripts:report (this checkout)"},
        "exit_code": completed.returncode,
        "pytest_output": completed.stdout[-2000:],
        "passed": passed,
        "source_sha256": _sources(section),
        "artifact_sha256": {name: _sha256(name) for name in ARTIFACTS},
        "scope": (
            "Accepted section tests against the final M8 assets after the shared vol10 notebook, "
            "portal registry and stylesheet changed; no pricing code or lesson data of this "
            "section changed. Historical numerical and browser records preserved."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="f6a2b62e")
    parser.add_argument("sections", nargs="*", default=list(TESTS))
    options = parser.parse_args()
    failed = []
    for section in options.sections:
        record = recheck(section, options.base)
        path = PROJECT / f"docs/validation/section-{section}/m8-recheck.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(section, record["status"], record["passed"], "passed")
        if record["status"] != "PASS":
            failed.append(section)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
