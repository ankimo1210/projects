"""Future saved-only child expense observer; never approves finance or a phase.

The fixed enclosing-v2 child is unchanged. Its prefix receipt is retained byte
for byte. This observer measures one inclusive clock through child reap and
stdout/stderr close; its own imports/post-stop bookkeeping remain unknown.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

D = Path(__file__).resolve().parent
CHILD = D / "task-5-full-pilot-root-saved-check-enclosing-v2.py"
CHILD_SHA256 = "c66aa768457bff4930eaef6bb47b6ba85e85017e36f027bc675feef3cdba46fc"
SOURCE_PLAIN = "75ac0db805e437af50fc101d6f82d1c9df26ff433897726b8800d107e72af29e"
SOURCE_NATIVE = "ef14264e5127ca5edbab5b642505fc7505589e351a8d64cba0b9387574cfb9c7"
BINDINGS = ("source_sha256", "plan_sha256", "input_bindings_sha256", "raw_snapshot_sha256")
LIMITS = (
    "phase_wall_limit_seconds",
    "poll_seconds",
    "child_rss_limit_bytes",
    "parent_rss_limit_bytes",
    "volume_probes",
)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_original(path, expected_sha=None):
    path = Path(path)
    require(
        path.is_absolute() and path.is_file() and not path.is_symlink() and path.resolve() == path,
        "regular absolute original file required",
    )
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    require(
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
        "original file changed while reading",
    )
    actual = sha_bytes(data)
    require(expected_sha is None or actual == expected_sha, "original file SHA differs")
    return data, {"path": str(path), "sha256": actual, "bytes": len(data)}


def load_guard(path, expected_sha):
    path = Path(path)
    require(path.parent == D, "guard must belong to this fixed helper directory")
    data, physical = read_original(path, expected_sha)
    guard = json.loads(data)
    require(
        guard.get("schema") == "rb-f04-full-child-expense-observer-root-guard-v1",
        "future whole child guard required",
    )
    require(
        guard.get("root_preapproved") is True
        and guard.get("execute_saved_check") is True
        and guard.get("candidate_only") is False
        and guard.get("planned_before_attempt") is True,
        "missing or false root saved-check authority",
    )
    require(
        guard.get("finance_acceptance") is False
        and guard.get("formal_financial_launch_authorized") is False,
        "financial launch or acceptance is outside this helper",
    )
    read_original(Path(__file__).resolve(), guard["helper_sha256"])
    read_original(CHILD, guard["child_sha256"])
    require(guard["child_sha256"] == CHILD_SHA256, "only fixed enclosing-v2 child allowed")
    cpath = Path(guard["child_guard"]["path"])
    require(cpath.parent == D and cpath != path, "distinct original child guard required")
    cbytes, cphysical = read_original(cpath, guard["child_guard"]["sha256"])
    child_guard = json.loads(cbytes)
    require(
        child_guard.get("root_preapproved") is True
        and child_guard.get("execute_saved_check") is True
        and child_guard.get("finance_acceptance") is False
        and child_guard.get("formal_financial_launch_authorized") is False,
        "original child permission differs",
    )
    require(
        child_guard.get("enclosing_observer_sha256") == CHILD_SHA256,
        "original child guard source differs",
    )
    original = guard.get("original_bindings")
    require(
        isinstance(original, dict)
        and set(original) == set(BINDINGS)
        and all(
            isinstance(v, str) and len(v) == 64 and set(v) <= set("0123456789abcdef")
            for v in original.values()
        ),
        "original four SHA bindings required",
    )
    require(
        child_guard.get("original_bindings") == original
        and original["source_sha256"] == SOURCE_NATIVE
        and child_guard.get("source_identity_sha256") == SOURCE_PLAIN
        and child_guard.get("source_native_payload_sha256") == SOURCE_NATIVE,
        "original source/plan/input/raw bindings differ",
    )
    require(
        guard.get("original_administrative_limits") == {key: child_guard[key] for key in LIMITS},
        "original administrative caps/poll/volumes differ",
    )
    budget = guard.get("whole_child_observation_wall_budget_seconds")
    require(
        budget is None
        or (
            isinstance(budget, (int, float))
            and not isinstance(budget, bool)
            and math.isfinite(budget)
            and budget > 0
        ),
        "actual whole scope budget invalid",
    )
    output = Path(guard["receipt_directory"])
    prefix_dir = Path(child_guard["enclosing_receipt_directory"])
    require(
        output.parent == D
        and prefix_dir.parent == D
        and output != prefix_dir
        and not output.exists()
        and not prefix_dir.exists()
        and not output.is_symlink()
        and not prefix_dir.is_symlink(),
        "fresh distinct whole/prefix output required",
    )
    require(guard["python_executable"] == sys.executable, "original interpreter differs")
    return guard, physical, child_guard, cphysical, output


def child_samples():
    r = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "ru_utime_seconds": r.ru_utime,
        "ru_stime_seconds": r.ru_stime,
        "ru_utime_ns_rounded": round(r.ru_utime * 1e9),
        "ru_stime_ns_rounded": round(r.ru_stime * 1e9),
        "kernel_peak_RSS_bytes": r.ru_maxrss * 1024,
    }


def boot_id():
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def observe(guard_path, guard_sha256):
    wall_start = time.perf_counter_ns()
    own_start = time.process_time_ns()
    reaped_start = child_samples()
    boot_start = boot_id()
    guard, guard_ref, child_guard, child_guard_ref, output = load_guard(guard_path, guard_sha256)
    output.mkdir()
    argv = [
        guard["python_executable"],
        "-B",
        str(CHILD),
        "--guard",
        child_guard_ref["path"],
        "--guard-sha256",
        child_guard_ref["sha256"],
    ]
    env = os.environ.copy()
    env.update(
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        PYTHONDONTWRITEBYTECODE="1",
    )
    with (output / "stdout.log").open("xb") as stdout, (output / "stderr.log").open("xb") as stderr:
        process = subprocess.Popen(argv, cwd=D.parents[2], env=env, stdout=stdout, stderr=stderr)
        code = process.wait()
    reaped_stop = child_samples()
    own_stop = time.process_time_ns()
    wall_stop = time.perf_counter_ns()
    cpu_start = (
        own_start + reaped_start["ru_utime_ns_rounded"] + reaped_start["ru_stime_ns_rounded"]
    )
    cpu_stop = own_stop + reaped_stop["ru_utime_ns_rounded"] + reaped_stop["ru_stime_ns_rounded"]
    # Everything below is post-stop bookkeeping, never silently added as zero.
    original_prefix = None
    prefix_error = None
    tail = None
    try:
        path = Path(child_guard["enclosing_receipt_directory"]) / "parent-cost-and-status.json"
        raw, original_prefix = read_original(path)
        (output / "original-prefix-receipt.bytes").write_bytes(raw)
        receipt = json.loads(raw)
        require(
            receipt.get("guard_sha256") == child_guard_ref["sha256"],
            "original prefix guard differs",
        )
        prefix = receipt["measured_prefix_expense"]
        require(
            prefix["id"] == "saved_check"
            and receipt["clock_source_samples"]["wall_clock"] == "time.perf_counter_ns"
            and boot_start == boot_id(),
            "same actual wall domain not established",
        )
        events = prefix["timing_events"]
        for axis in ("wall", "cpu"):
            start, stop = events[axis + "_start_ns"], events[axis + "_stop_ns"]
            require(
                isinstance(start, int)
                and isinstance(stop, int)
                and 0 <= start <= stop
                and math.isclose(
                    prefix["timing"][axis + "_seconds"],
                    (stop - start) / 1e9,
                    rel_tol=1e-12,
                    abs_tol=1e-9,
                ),
                "original prefix clock differs",
            )
        require(
            wall_start <= events["wall_start_ns"] <= events["wall_stop_ns"] <= wall_stop,
            "prefix is not contained in actual launch/reap observation",
        )
        tail = {
            "wall_start_ns": events["wall_stop_ns"],
            "wall_stop_ns": wall_stop,
            "wall_seconds": (wall_stop - events["wall_stop_ns"]) / 1e9,
            "wall_clock_domain": "same local boot " + boot_start + " time.perf_counter_ns",
            "includes_reap_delay": True,
            "scope": "observed completion tail includes child receipt/stdout/exit plus wait and close latency; not pure serialization CPU",
        }
    except (OSError, ValueError, KeyError, TypeError) as error:
        prefix_error = type(error).__name__ + ": " + str(error)
    unchanged = True
    try:
        read_original(Path(guard_path), guard_ref["sha256"])
        read_original(Path(__file__).resolve(), guard["helper_sha256"])
        read_original(CHILD, guard["child_sha256"])
        read_original(Path(child_guard_ref["path"]), child_guard_ref["sha256"])
        if original_prefix is not None:
            read_original(Path(original_prefix["path"]), original_prefix["sha256"])
    except (OSError, ValueError):
        unchanged = False
    budget = guard["whole_child_observation_wall_budget_seconds"]
    elapsed = (wall_stop - wall_start) / 1e9
    expense = {
        "id": "saved_check",
        "scope": "full fixed enclosing-v2 child lifecycle plus outer measured prefix",
        "status": "complete" if code == 0 and prefix_error is None and unchanged else "failed",
        "parent_id": None,
        "includes_children": True,
        "timing": {
            "wall_seconds": elapsed,
            "cpu_seconds": (cpu_stop - cpu_start) / 1e9,
            "overrun_seconds": None if budget is None else max(0.0, elapsed - budget),
        },
        "timing_events": {
            "wall_start_ns": wall_start,
            "wall_stop_ns": wall_stop,
            "cpu_start_ns": cpu_start,
            "cpu_stop_ns": cpu_stop,
        },
        "whole_external_id_closed": tail is not None and unchanged and budget is not None,
        "final_receipt_construction_write_stdout_tail_seconds": None
        if tail is None
        else tail["wall_seconds"],
    }
    if expense["status"] == "failed":
        expense["reason"] = (
            "actual enclosing child exit_code="
            + str(code)
            + "; prefix_error="
            + str(prefix_error)
            + "; original bytes unchanged="
            + str(unchanged)
        )
    result = {
        "schema": "rb-f04-full-child-expense-observation-v1",
        "expense": expense,
        "original_prefix_receipt": original_prefix,
        "prefix_error": prefix_error,
        "guard": guard_ref,
        "original_child_guard": child_guard_ref,
        "original_bindings": guard["original_bindings"],
        "bindings": guard["original_bindings"],
        "child_pid": process.pid,
        "child_exit_code": code,
        "argv": argv,
        "original_bytes_unchanged": unchanged,
        "observed_child_completion_tail": tail,
        "pure_CPU_tail_seconds": None,
        "clock_source_samples": {
            "wall_clock": "time.perf_counter_ns",
            "wall_domain": "local boot " + boot_start,
            "parent_cpu_start_ns": own_start,
            "parent_cpu_stop_ns": own_stop,
            "children_cpu_start": reaped_start,
            "children_cpu_stop": reaped_stop,
            "sampling_order": "start wall,parentCPU,reaped; stop wait+close,reaped,parentCPU,wall",
            "cpu_domain": "parent process CPU plus rounded cumulative reaped child user/system CPU",
            "double_charge_rule": "single inclusive duration; original prefix/nested clocks never added",
        },
        "parent_kernel_peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "child_kernel_peak_RSS_bytes": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        * 1024,
        "RSS_fit_or_full_capacity_guarantee": None,
        "kernel_RSS_scope": "process/reaped-children cumulative highwater, including prior baseline and bookkeeping; no exclusive full-check fit claim",
        "administrative_unclosed_expense": {
            "id": "saved_check:outer_unmeasured_bookkeeping",
            "scope": "outer imports before sampling and post-stop provenance/copy/receipt/stdout",
            "status": "pending",
            "parent_id": None,
            "includes_children": False,
            "timing": {"wall_seconds": None, "cpu_seconds": None, "overrun_seconds": None},
        },
        "all_expenses_closed": False,
        "all_external10_closed": False,
        "finance_acceptance": False,
        "financial_qualification": "unknown",
        "financial_phase_completion_claimed": False,
        "root_actual_permission_approved_by_this_helper": False,
        "actual_numerical_qualification_authenticated": False,
        "external_expense_rows_injected": False,
        "original_raw_modified": False,
        "resource_enforcement": "original fixed child monitor retains original administrative guards; this outer wrapper only measures its declared inclusive expense",
    }
    (output / "full-child-expense.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guard", type=Path, required=True)
    parser.add_argument("--guard-sha256", required=True)
    args = parser.parse_args(argv)
    result = observe(args.guard, args.guard_sha256)
    print(
        json.dumps(
            {
                "child_exit_code": result["child_exit_code"],
                "expense_status": result["expense"]["status"],
                "all_expenses_closed": False,
            }
        ),
        flush=True,
    )
    return 0 if result["expense"]["status"] == "complete" else 3


if __name__ == "__main__":
    raise SystemExit(main())
