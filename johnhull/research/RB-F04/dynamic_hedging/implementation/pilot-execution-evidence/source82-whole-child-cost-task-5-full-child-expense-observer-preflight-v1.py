"""Synthetic child lifecycle only; real root permissions/native data never used."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import time
import traceback
from pathlib import Path

import numpy as np

D = Path(__file__).resolve().parent
W = D.parents[2]
HELPER = D / "task-5-full-child-expense-observer-v1.py"
RESULT = D / "task-5-full-child-expense-observer-results-v1.json"
STUB = r"""import argparse,json,resource,sys,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
p=argparse.ArgumentParser();p.add_argument("--guard");p.add_argument("--guard-sha256")
a=p.parse_args();g=json.loads(Path(a.guard).read_text())
out=Path(g["enclosing_receipt_directory"]);out.mkdir()
ws=time.perf_counter_ns();cs=time.process_time_ns()
sum(i*i for i in range(1000))
ce=time.process_time_ns();we=time.perf_counter_ns()
prefix={"id":"saved_check","status":"complete" if g["fixture_exit_code"]==0 else "failed",
"scope":"future_saved_only_whole_monitor_invocation_measured_prefix",
"timing":{"wall_seconds":(we-ws)/1e9,"cpu_seconds":(ce-cs)/1e9,"overrun_seconds":None},
"timing_events":{"wall_start_ns":ws,"wall_stop_ns":we,"cpu_start_ns":cs,"cpu_stop_ns":ce},
"whole_external_saved_check_expense_closed":False,
"final_receipt_construction_write_stdout_tail_seconds":None}
time.sleep(.025)
receipt={"measured_prefix_expense":prefix,"monitor_exit_code":g["fixture_exit_code"],
"guard_sha256":a.guard_sha256,"clock_source_samples":{"wall_clock":"time.perf_counter_ns"},
"scope":"tiny stdlib stub only","reason":None if g["fixture_exit_code"]==0 else "actual synthetic exit7"}
(out/"parent-cost-and-status.json").write_text(json.dumps(receipt)+"\n")
print(json.dumps({"stub_only":True}),flush=True)
raise SystemExit(g["fixture_exit_code"])
"""


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, allow_nan=False) + "\n")
    return sha(path)


def original_source():
    cpath = D / "current-production-source-closure-v1.json"
    closure = json.loads(cpath.read_text())
    assert len(closure["files"]) == 82
    actual = {relative: sha(W / relative) for relative in closure["files"]}
    assert actual == closure["files"]
    return actual


def native_clock_contract():
    path = W / "johnhull/research/RB-F04/dynamic_hedging/check_pilot.py"
    tree = ast.parse(path.read_text())
    f = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "_check_actual_expense_clock"
    )

    def require(value, message):
        if not value:
            raise ValueError(message)

    ns = {"np": np, "_require": require}
    exec(compile(ast.Module(body=[f], type_ignores=[]), str(path), "exec"), ns)
    return ns[f.name]


def native_expense_contracts():
    core = W / "deep_hedge_price/src/deep_hedge_price"
    spec = importlib.util.spec_from_file_location(
        "isolated_expense_protocol", core / "_dynamic_hedging_protocol.py"
    )
    protocol = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(protocol)
    tree = ast.parse((core / "_dynamic_hedging_execution.py").read_text())
    function = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_current_expenses"
    )

    def require(ok, message):
        if not ok:
            raise ValueError(message)

    namespace = {"_v1": protocol, "_require": require}
    exec(
        compile(
            ast.Module(body=[function], type_ignores=[]),
            str(core / "_dynamic_hedging_execution.py"),
            "exec",
        ),
        namespace,
    )
    return protocol, namespace["_current_expenses"]


def fixture(root, code=0, budget=30.0):
    root.mkdir()
    child = root / "task-5-full-pilot-root-saved-check-enclosing-v2.py"
    child.write_text(STUB)
    binding = {
        "source_sha256": "ef14264e5127ca5edbab5b642505fc7505589e351a8d64cba0b9387574cfb9c7",
        "plan_sha256": "1" * 64,
        "input_bindings_sha256": "2" * 64,
        "raw_snapshot_sha256": "3" * 64,
    }
    child_guard = root / "child-guard.json"
    cg = {
        "root_preapproved": True,
        "execute_saved_check": True,
        "finance_acceptance": False,
        "formal_financial_launch_authorized": False,
        "original_bindings": binding,
        "source_identity_sha256": "75ac0db805e437af50fc101d6f82d1c9df26ff433897726b8800d107e72af29e",
        "source_native_payload_sha256": binding["source_sha256"],
        "enclosing_receipt_directory": str(root / "child-prefix"),
        "phase_wall_limit_seconds": 30.0,
        "poll_seconds": 0.01,
        "child_rss_limit_bytes": 1024**3,
        "parent_rss_limit_bytes": 1024**3,
        "volume_probes": [{"id": "synthetic-volume", "reserve_bytes": 0}],
        "fixture_exit_code": code,
        "enclosing_observer_sha256": sha(child),
    }
    csha = write_json(child_guard, cg)
    helper_copy = root / HELPER.name
    if HELPER.exists():
        helper_copy.write_bytes(HELPER.read_bytes())
    guard = {
        "schema": "rb-f04-full-child-expense-observer-root-guard-v1",
        "candidate_only": False,
        "root_preapproved": True,
        "execute_saved_check": True,
        "finance_acceptance": False,
        "formal_financial_launch_authorized": False,
        "planned_before_attempt": True,
        "helper_sha256": sha(helper_copy) if helper_copy.exists() else None,
        "child_sha256": sha(child),
        "child_guard": {"path": str(child_guard), "sha256": csha},
        "original_bindings": binding,
        "receipt_directory": str(root / "full-child-receipts"),
        "whole_child_observation_wall_budget_seconds": budget,
        "python_executable": "/home/kazumasa/projects/.venv/bin/python",
        "original_administrative_limits": {
            k: cg[k]
            for k in (
                "phase_wall_limit_seconds",
                "poll_seconds",
                "child_rss_limit_bytes",
                "parent_rss_limit_bytes",
                "volume_probes",
            )
        },
        "synthetic_fixture_only": True,
    }
    gp = root / "outer-guard.json"
    gsha = write_json(gp, guard)
    return child, child_guard, cg, gp, gsha, guard, helper_copy


def load_copy(path, child):
    spec = importlib.util.spec_from_file_location("isolated_full_child_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Deliberate private seam in copied TempDirectory module only; actual
    # CLI retains its constant SHA for the unchanged real enclosing-v2.
    module.CHILD_SHA256 = sha(child)
    return module


def main():
    started = time.perf_counter()
    source_before = original_source()
    previous = json.loads(RESULT.read_text()) if RESULT.exists() else None
    checks = []
    with tempfile.TemporaryDirectory(prefix="full-child-expense-fixture-") as temp:
        base = Path(temp)
        if not HELPER.exists():
            child, cg, cgb, gp, gs, g, copy = fixture(base / "baseline")
            r = subprocess.run(
                [
                    "/home/kazumasa/projects/.venv/bin/python",
                    "-B",
                    str(child),
                    "--guard",
                    str(cg),
                    "--guard-sha256",
                    sha(cg),
                ],
                text=True,
                capture_output=True,
                timeout=30,
            )
            assert r.returncode == 0
            receipt_path = Path(cgb["enclosing_receipt_directory"]) / "parent-cost-and-status.json"
            raw = receipt_path.read_bytes()
            prefix = json.loads(raw)["measured_prefix_expense"]
            try:
                assert prefix["final_receipt_construction_write_stdout_tail_seconds"] is not None
            except AssertionError:
                trace = traceback.format_exc()
            else:
                raise AssertionError("baseline unexpectedly closed missing tail")
            result = {
                "status": "RED_expected",
                "prior_fixture_setup_failure": previous,
                "baseline_RED": {
                    "original_receipt_utf8": raw.decode(),
                    "sha256": sha(receipt_path),
                    "exit_code": r.returncode,
                    "stdout": r.stdout,
                    "stderr": r.stderr,
                    "trace": trace,
                    "scope": "actual tiny child prefix lacks its own post-stop tail",
                },
                "source82_unchanged": source_before == original_source(),
                "actual_finance_native_CAS_Git_operations": 0,
            }
            RESULT.write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps({"status": result["status"], "sha256": sha(RESULT)}))
            return 1
        assert previous is not None
        baseline = (
            previous
            if previous["status"] == "RED_expected"
            else {
                "status": "RED_expected",
                "baseline_RED": previous["baseline_RED"],
                "prior_fixture_setup_failure": previous.get("prior_fixture_setup_failure"),
            }
        )
        clock = native_clock_contract()
        protocol, current_expenses = native_expense_contracts()
        for name, code, budget in [
            ("success", 0, 30.0),
            ("failed", 7, 30.0),
            ("unknown-budget", 0, None),
        ]:
            child, cg, cgb, gp, gs, g, copy = fixture(base / name, code, budget)
            module = load_copy(copy, child)
            observation = module.observe(gp, gs)
            expense = observation["expense"]
            clock(expense, expense["timing_events"])
            assert observation["child_exit_code"] == code
            assert observation["observed_child_completion_tail"]["includes_reap_delay"] is True
            assert observation["observed_child_completion_tail"]["wall_seconds"] >= 0.025
            assert observation["pure_CPU_tail_seconds"] is None
            origin = observation["original_prefix_receipt"]
            assert (
                Path(origin["path"]).read_bytes()
                == (Path(g["receipt_directory"]) / "original-prefix-receipt.bytes").read_bytes()
            )
            assert origin["sha256"] == sha(origin["path"])
            assert (
                json.loads(Path(origin["path"]).read_bytes())["measured_prefix_expense"][
                    "final_receipt_construction_write_stdout_tail_seconds"
                ]
                is None
            )
            samples = observation["clock_source_samples"]
            for endpoint in ("start", "stop"):
                children = samples["children_cpu_" + endpoint]
                assert (
                    expense["timing_events"]["cpu_" + endpoint + "_ns"]
                    == samples["parent_cpu_" + endpoint + "_ns"]
                    + children["ru_utime_ns_rounded"]
                    + children["ru_stime_ns_rounded"]
                )
            assert expense["timing"]["overrun_seconds"] == (
                None if budget is None else max(0, expense["timing"]["wall_seconds"] - budget)
            )
            assert expense["whole_external_id_closed"] is (budget is not None)
            assert expense["status"] == ("complete" if code == 0 else "failed")
            if code:
                assert "7" in expense["reason"]
            assert observation["administrative_unclosed_expense"]["timing"] == {
                "wall_seconds": None,
                "cpu_seconds": None,
                "overrun_seconds": None,
            }
            rows = [expense, observation["administrative_unclosed_expense"]]
            costs = protocol.validate_expenses(rows, required_ids=[r["id"] for r in rows])
            assert costs["charged_totals"] == {"wall_seconds": None, "cpu_seconds": None}
            if budget is None:
                try:
                    current_expenses(rows, ["saved_check"])
                except ValueError:
                    pass
                else:
                    raise AssertionError(
                        "unknown actual overrun promoted to closed current expense"
                    )
            else:
                current_expenses(rows, ["saved_check"])
            assert all(
                observation[k] is False
                for k in (
                    "all_expenses_closed",
                    "all_external10_closed",
                    "finance_acceptance",
                    "financial_phase_completion_claimed",
                    "root_actual_permission_approved_by_this_helper",
                )
            )
            assert (
                observation["original_bindings"]
                == g["original_bindings"]
                == observation["bindings"]
            )
            checks.append(
                name
                + ": real child through reap; actual clock/single-inclusive CPU; raw prefix and unknown scopes preserved"
            )
        child, cg, cgb, gp, gs, g, copy = fixture(base / "false")
        module = load_copy(copy, child)
        calls = []

        def forbid(*args, **kwargs):
            calls.append(args)
            raise AssertionError("Popen before authority")

        module.subprocess.Popen = forbid
        g["root_preapproved"] = False
        gs = write_json(gp, g)
        try:
            module.observe(gp, gs)
        except ValueError:
            pass
        else:
            raise AssertionError("false guard accepted")
        assert not calls and not Path(g["receipt_directory"]).exists()
        try:
            module.observe(module.D / "absent-guard.json", "0" * 64)
        except ValueError:
            pass
        else:
            raise AssertionError("missing guard accepted")
        assert not calls
        g["root_preapproved"] = True
        g["original_bindings"]["plan_sha256"] = "4" * 64
        gs = write_json(gp, g)
        try:
            module.observe(gp, gs)
        except ValueError:
            pass
        else:
            raise AssertionError("original binding mismatch accepted")
        assert not calls
        checks.append("false guard and original binding mismatch refused before Popen/output")
    assert source_before == original_source()
    result = {
        "status": "PASS",
        "checks": checks,
        "check_count": len(checks),
        "baseline_RED": baseline["baseline_RED"],
        "prior_fixture_setup_failure": baseline.get("prior_fixture_setup_failure"),
        "source82_unchanged": source_before,
        "synthetic_child_only": True,
        "synthetic_root_permissions_are_not_real_D2_authority": True,
        "actual_finance_native_CAS_Git_operations": 0,
        "financial_qualification": "unknown",
        "all_expenses_closed": False,
        "verification_wall_seconds_before_result_write": time.perf_counter() - started,
        "verification_own_result_write_tail_seconds": None,
    }
    RESULT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "PASS", "checks": len(checks), "sha256": sha(RESULT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
