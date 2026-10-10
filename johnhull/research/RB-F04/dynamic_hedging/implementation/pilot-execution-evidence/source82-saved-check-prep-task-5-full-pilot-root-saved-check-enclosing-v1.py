"""Outer actual cost receipt around the prepared saved-only monitor."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import resource
import subprocess
import time
from pathlib import Path

D = Path(__file__).resolve().parent
MONITOR = D / "task-5-full-pilot-root-saved-check-observer-v1.py"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guard", type=Path, required=True)
    parser.add_argument("--guard-sha256", required=True)
    args = parser.parse_args(argv)
    started, cpu_start = time.perf_counter(), time.process_time()
    usage_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    utc = datetime.datetime.now(datetime.UTC).isoformat()
    assert args.guard.parent.resolve() == D and not args.guard.is_symlink()
    assert sha(args.guard) == args.guard_sha256
    prior = json.loads(args.guard.read_text())
    # No pending/false candidate may reach Popen.
    assert prior["root_preapproved"] is True and prior["execute_saved_check"] is True
    assert prior["finance_acceptance"] is False
    assert prior["formal_financial_launch_authorized"] is False
    assert sha(__file__) == prior["enclosing_observer_sha256"]
    assert sha(MONITOR) == prior["monitor_sha256"]
    spec = importlib.util.spec_from_file_location("prepared_saved_monitor", MONITOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.load_guard(args.guard)
    receipts = Path(prior["enclosing_receipt_directory"])
    assert receipts.parent == D and receipts.name.startswith("task-5-formal-pilot-saved-check-")
    assert not receipts.exists()
    assert str(receipts) not in (prior["native_output_path"], prior["receipt_directory"])
    receipts.mkdir()
    command = [prior["python_executable"], str(MONITOR), "--guard", str(args.guard)]
    env = os.environ.copy()
    env.update(
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        PYTHONDONTWRITEBYTECODE="1",
    )
    with (
        (receipts / "monitor-stdout.log").open("wb") as stdout,
        (receipts / "monitor-stderr.log").open("wb") as stderr,
    ):
        process = subprocess.Popen(command, cwd=D.parents[2], env=env, stdout=stdout, stderr=stderr)
        while process.poll() is None:
            state = {
                "schema": "rb-f04-root-actual-formal-monitor-invocation-v1",
                "status": "running",
                "monitor_pid": process.pid,
                "root_pid": os.getpid(),
                "argv": command,
                "guard_sha256": sha(args.guard),
                "start_UTC": utc,
                "elapsed_seconds": time.perf_counter() - started,
                "financial_phase_completion_claimed": False,
                "qualification": "unknown",
                "saved_only": True,
            }
            (receipts / "observer-progress.json").write_text(json.dumps(state, indent=2) + "\n")
            time.sleep(prior["poll_seconds"])
        code = process.wait()
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    status = {
        "schema": "rb-f04-root-formal-monitor-enclosing-cost-v1",
        "status": "terminal_requires_native_and_saved_result_inspection",
        "monitor_exit_code": code,
        "monitor_pid": process.pid,
        "guard_sha256": sha(args.guard),
        "argv": command,
        "start_UTC": utc,
        "end_UTC": datetime.datetime.now(datetime.UTC).isoformat(),
        "wall_seconds": time.perf_counter() - started,
        "parent_CPU_seconds": time.process_time() - cpu_start,
        "children_CPU_seconds": usage.ru_utime
        + usage.ru_stime
        - usage_start.ru_utime
        - usage_start.ru_stime,
        "parent_kernel_peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "child_kernel_peak_RSS_bytes": usage.ru_maxrss * 1024,
        "scope": "saved-only enclosing invocation including guard imports/authentication, all full-job hydration/SDE/labels/final serialization, monitor postbinding/receipts; nested clocks not added again",
        "monitor_status_not_reclassified": True,
        "financial_qualification": "unknown",
        "finance_acceptance": False,
        "original_generation_costs_readded": False,
        "own_final_receipt_write_stdout_cost": None,
    }
    (receipts / "parent-cost-and-status.json").write_text(json.dumps(status, indent=2) + "\n")
    (receipts / "observer-progress.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
