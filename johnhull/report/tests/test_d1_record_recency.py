"""The latest acceptance record must cite D1 rechecks made for that milestone.

A D1 record is valid evidence only for the commit it ran on.  The acceptance
builders check the record contents and hashes, but not when the record was
made, so an older PASS record could be cited again.  Every D1 record selected
by the newest integrated record must have run on a commit that strictly
descends from the commit that added the previous milestone's integrated record.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
VALIDATION = PROJECT / "docs/validation"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=PROJECT, capture_output=True, text=True)


def _integrated_records() -> dict[int, Path]:
    records = {}
    for path in VALIDATION.glob("section-*/m*-check.json"):
        match = re.fullmatch(r"m(\d+)-check\.json", path.name)
        if match:
            records[int(match.group(1))] = path
    return records


def _added_in(path: Path) -> str:
    added = _git(
        "log", "--diff-filter=A", "--format=%H", "--", path.relative_to(PROJECT).as_posix()
    )
    commits = added.stdout.split()
    assert added.returncode == 0 and commits, f"no commit added {path}"
    return commits[-1]


def _exists(commit: str) -> bool:
    return _git("cat-file", "-e", f"{commit}^{{commit}}").returncode == 0


def _strictly_after(base: str, commit: str) -> bool:
    if not _exists(commit):
        return False
    if _git("rev-parse", commit).stdout.strip() == _git("rev-parse", base).stdout.strip():
        return False
    return _git("merge-base", "--is-ancestor", base, commit).returncode == 0


@pytest.fixture(scope="module")
def history():
    if _git("rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        pytest.skip("needs the git history of the project")
    records = _integrated_records()
    latest = max(records)
    if latest - 1 not in records:
        pytest.skip(f"no integrated record for M{latest - 1}")
    return records[latest], _added_in(records[latest - 1])


def test_latest_record_cites_d1_rechecks_made_after_previous_milestone(history):
    latest, base = history
    d1 = json.loads(latest.read_text(encoding="utf-8"))["regression"]["d1"]
    assert d1, f"{latest.name} cites no D1 rechecks"
    records = {
        section: json.loads((PROJECT / entry["record"]).read_text(encoding="utf-8"))
        for section, entry in d1.items()
    }
    shallow = _git("rev-parse", "--is-shallow-repository").stdout.strip() == "true"
    if shallow and not all(_exists(record["commit"]) for record in records.values()):
        pytest.skip("this shallow clone lacks a commit that a D1 record cites")
    stale = []
    for section, entry in d1.items():
        record = records[section]
        if record["dirty"] or not _strictly_after(base, record["commit"]):
            stale.append(f"§{section}: {entry['record']} ran on {record['commit'][:8]}")
    assert not stale, f"{latest.name} cites D1 records older than {base[:8]}: {stale}"


def test_recency_rejects_the_base_commit_and_its_ancestors(history):
    _, base = history
    assert not _strictly_after(base, base)
    assert not _strictly_after(base, f"{base}~1")
    assert not _strictly_after(base, "0" * 40)
