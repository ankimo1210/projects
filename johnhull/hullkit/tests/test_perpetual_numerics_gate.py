"""The §26.2 numeric gate must accept the reference and reject changed prices."""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT / "scripts/verify_perpetual_numerics.py"
REFERENCE = PROJECT / "docs/validation/section-26-2/reference.json"


def _run(path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT / "hullkit/src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--reference", str(path)],
        cwd=PROJECT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_gate_accepts_independent_reference():
    result = _run(REFERENCE)
    assert result.returncode == 0, result.stdout + result.stderr


def test_gate_rejects_changed_call_value(tmp_path):
    data = json.loads(REFERENCE.read_text(encoding="utf-8"))
    data["cases"][0]["call"]["value"] += 1.0
    changed = tmp_path / "reference.json"
    changed.write_text(json.dumps(data), encoding="utf-8")
    result = _run(changed)
    assert result.returncode != 0
    assert "call value" in result.stdout + result.stderr


def test_gate_rejects_falsified_lattice_values_even_if_gaps_look_valid(tmp_path):
    data = json.loads(REFERENCE.read_text(encoding="utf-8"))
    for case in data["cases"]:
        for row in case["lattice"]["rows"]:
            row["call"] = -12345.0
            row["put"] = -12345.0
            row["call_gap"] = 0.0
            row["put_gap"] = 0.0
    changed = tmp_path / "reference.json"
    changed.write_text(json.dumps(data), encoding="utf-8")
    result = _run(changed)
    assert result.returncode != 0
    assert "lattice" in result.stdout + result.stderr
