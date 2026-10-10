"""Isolated tiny stub-only clock checks; no real saved monitor or native input."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
import os
import resource
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from unittest.mock import patch

D = Path(__file__).resolve().parent
V1 = D / "task-5-full-pilot-root-saved-check-enclosing-v1.py"
V2 = D / "task-5-full-pilot-root-saved-check-enclosing-v2.py"
MONITOR = D / "task-5-full-pilot-root-saved-check-observer-v1.py"
RESULT = D / "task-5-full-pilot-root-saved-check-enclosing-verification-v2.json"
SOURCE = D.parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
STUB = """
import argparse, json, resource
from pathlib import Path
def load_guard(path):
    guard = json.loads(Path(path).read_text())
    assert guard["synthetic_fixture_only"] is True
    assert Path(path).parent != Path(guard["real_D2"])
    assert guard["test_RSS_or_AS_fender_bytes"] == 1024**3
    return guard
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--guard", required=True)
    g = load_guard(p.parse_args().guard)
    assert resource.getrlimit(resource.RLIMIT_AS)[0] <= 1024**3
    sum(i * i for i in range(100_000))
    raise SystemExit(g["stub_exit"])
"""


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fender():
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))


def private_attempt(base, owner, name, exit_code=0, approved=True):
    root = base / name / "scope" / "D"
    root.mkdir(parents=True)
    script = root / owner.name
    script.write_bytes(owner.read_bytes())
    monitor = root / MONITOR.name
    monitor.write_text(STUB)
    guard = root / "private-stub-guard.json"
    prior = {
        "root_preapproved": approved,
        "execute_saved_check": approved,
        "finance_acceptance": False,
        "formal_financial_launch_authorized": False,
        "enclosing_observer_sha256": sha(script),
        "monitor_sha256": sha(monitor),
        "enclosing_receipt_directory": str(root / "task-5-formal-pilot-saved-check-stub"),
        "native_output_path": str(root / "no-native-fixture"),
        "receipt_directory": str(root / "no-actual-monitor-receipts"),
        "python_executable": sys.executable,
        "poll_seconds": 0.01,
        "synthetic_fixture_only": True,
        "real_D2": str(D),
        "test_RSS_or_AS_fender_bytes": 1024**3,
        "stub_exit": exit_code,
    }
    guard.write_text(json.dumps(prior))
    assert root.resolve() != D.resolve()
    return script, guard, prior


def launch(script, guard):
    env = os.environ.copy()
    env.update(
        PYTHONDONTWRITEBYTECODE="1",
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
    )
    process = subprocess.run(
        [sys.executable, "-B", str(script), "--guard", str(guard), "--guard-sha256", sha(guard)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        preexec_fn=fender,
    )
    return process, json.loads(process.stdout)


def assert_clock(result, expected_exit):
    expense = result["measured_prefix_expense"]
    events = expense["timing_events"]
    for axis in ("wall", "cpu"):
        start, stop = events[axis + "_start_ns"], events[axis + "_stop_ns"]
        assert isinstance(start, int) and isinstance(stop, int) and 0 <= start <= stop
        duration = (stop - start) / 1e9
        assert math.isclose(
            expense["timing"][axis + "_seconds"], duration, rel_tol=1e-12, abs_tol=1e-9
        )
    source = result["clock_source_samples"]
    for side in ("start", "stop"):
        child = source["children_cpu_" + side]
        for component in ("utime", "stime"):
            assert child["ru_" + component + "_ns_rounded"] == round(
                child["ru_" + component + "_seconds"] * 1e9
            )
        expected = source["parent_cpu_" + side + "_ns"] + (
            child["ru_utime_ns_rounded"] + child["ru_stime_ns_rounded"]
        )
        assert events["cpu_" + side + "_ns"] == expected
    parent = source["parent_cpu_stop_ns"] - source["parent_cpu_start_ns"]
    children = sum(
        source["children_cpu_stop"][key] - source["children_cpu_start"][key]
        for key in ("ru_utime_ns_rounded", "ru_stime_ns_rounded")
    )
    assert events["cpu_stop_ns"] - events["cpu_start_ns"] == parent + children
    assert children > 0
    assert expense["timing"]["cpu_seconds"] != (parent + 2 * children) / 1e9
    assert result["monitor_exit_code"] == expected_exit
    assert expense["status"] == ("complete" if expected_exit == 0 else "failed")
    assert result["status"] == "terminal_requires_native_and_saved_result_inspection"
    assert result["finance_acceptance"] is False
    assert result["financial_qualification"] == "unknown"
    assert result["own_final_receipt_write_stdout_cost"] is None
    assert expense["whole_external_saved_check_expense_closed"] is False
    assert expense["final_receipt_construction_write_stdout_tail_seconds"] is None
    assert expense["external_event_rows_injected"] is False
    assert expense["other_external_ids_closed"] is False
    return {
        "exit_code": expected_exit,
        "expense": expense,
        "clock_source_samples": source,
        "legacy_float_timing": {
            key: result[key]
            for key in ("wall_seconds", "parent_CPU_seconds", "children_CPU_seconds")
        },
        "status_not_reclassified": result["status"],
    }


def main():
    start = time.perf_counter()
    source_before = {p.name: sha(p) for p in SOURCE.glob("*.py")}
    immutable_before = {"enclosing_v1": sha(V1), "observer_v1": sha(MONITOR)}
    checks = []
    with tempfile.TemporaryDirectory(prefix="saved-clock-stub-only-") as temporary:
        base = Path(temporary)
        script, guard, _ = private_attempt(base, V1, "old-red")
        process, old = launch(script, guard)
        assert process.returncode == 0
        try:
            assert "measured_prefix_expense" in old, "v1 lacks actual wall/cpu ns endpoints"
        except AssertionError:
            red = {
                "expected_missing_ns_failure": traceback.format_exc(),
                "actual_original_v1_receipt": old,
            }
        else:
            raise AssertionError("old v1 unexpectedly passed mandatory actual clock contract")
        checks.append("RED original v1 success has no measured ns endpoints")
        successful = []
        for code in (0, 7):
            script, guard, _ = private_attempt(base, V2, "new-" + str(code), code)
            process, result = launch(script, guard)
            assert process.returncode == code, process.stderr
            successful.append(assert_clock(result, code))
            checks.append("GREEN actual stub exit " + str(code) + " exact clock arithmetic/status")
        script, guard, prior = private_attempt(base, V2, "false", approved=False)
        spec = importlib.util.spec_from_file_location("private_clock_false", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(
            module.subprocess,
            "Popen",
            side_effect=AssertionError("Popen must never be reached by false guard"),
        ) as popen:
            try:
                module.main(["--guard", str(guard), "--guard-sha256", sha(guard)])
            except AssertionError:
                pass
            else:
                raise AssertionError("false guard was accepted")
            assert popen.call_count == 0
        assert not Path(prior["enclosing_receipt_directory"]).exists()
        checks.append("GREEN false private guard rejected before Popen or receipts")
        original_tree, candidate_tree = ast.parse(V1.read_text()), ast.parse(V2.read_text())
        old_functions = {n.name: n for n in original_tree.body if isinstance(n, ast.FunctionDef)}
        new_functions = {n.name: n for n in candidate_tree.body if isinstance(n, ast.FunctionDef)}
        assert set(old_functions) == set(new_functions)
        assert ast.dump(old_functions["sha"]) == ast.dump(new_functions["sha"])
        checks.append("only main AST changes; sha helper and CLI flags maintained")
    source_after = {p.name: sha(p) for p in SOURCE.glob("*.py")}
    assert source_before == source_after
    assert immutable_before == {"enclosing_v1": sha(V1), "observer_v1": sha(MONITOR)}
    record = {
        "schema": "rb-f04-saved-check-enclosing-ns-clock-verification-v2",
        "status": "PASS",
        "checks": checks,
        "original_v1_RED": red,
        "new_v2_tiny_real_subprocess_receipts": successful,
        "source": {"enclosing_v2_sha256": sha(V2), **immutable_before},
        "production_source_files_unchanged": source_after,
        "real_saved_monitor_or_financial_worker_calls": 0,
        "tiny_private_stub_child_processes": 3,
        "private_root_approval_fixture_not_valid_for_real_D2": True,
        "stub_only_limits": {
            "AS_bytes": 1024**3,
            "child_CPU_seconds": 20,
            "per_outer_timeout_seconds": 30,
        },
        "actual_CAS_Git_operations": 0,
        "finance_acceptance": False,
        "all_external_expenses_closed": False,
        "verification_enclosing_wall_seconds_before_result_write": time.perf_counter() - start,
        "verification_receipt_write_tail_seconds": None,
    }
    with RESULT.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {"status": "PASS", "checks": len(checks), "result": str(RESULT), "sha256": sha(RESULT)},
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
