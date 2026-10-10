"""Small synthetic terminal and four-file native byte closure probes."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

D = Path(__file__).resolve().parent
HELPER = D / "task-5-native-terminal-byte-candidate-v1.py"
OBSERVER = D / "task-5-full-pilot-root-saved-check-observer-v1.py"
TEMPLATE = D / "task-5-full-pilot-root-saved-check-resource-candidate-v1.json"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(root):
    observer = load(OBSERVER, "synthetic_terminal_observer")
    observer.D = root
    observer.ORIGINAL_NATIVE = root / "task-5-formal-pilot-root-v3"
    observer.ORIGINAL_PIDS = [9999901, 9999902, 9999903]
    prior = json.loads(TEMPLATE.read_text())
    prior["original_process_ids"] = observer.ORIGINAL_PIDS
    for key in ("original_terminal_monitor_receipt", "original_terminal_enclosing_receipt"):
        prior[key]["path"] = str(root / Path(prior[key]["path"]).relative_to(D))
    native = observer.ORIGINAL_NATIVE
    checkpoint = native / "checkpoint000001"
    checkpoint.mkdir(parents=True)
    # Exactly four tiny native files; no financial arrays or protocol decode.
    (checkpoint / "receipt.json").write_bytes(b'{"fixture":"receipt"}\n')
    (checkpoint / "metadata.json").write_bytes(b'{"fixture":"metadata"}\n')
    (checkpoint / "arrays.npz").write_bytes(b"synthetic bytes, not an NPZ")
    (native / "marker.json").write_bytes(b'{"fixture":"native"}\n')
    original = copy.deepcopy(prior)
    original.update(
        root_preapproved=True,
        formal_financial_launch_authorized=True,
        native_output_path=str(native),
    )
    guard = root / observer.ORIGINAL_GUARD_NAME
    dump(guard, original)
    observer.ORIGINAL_GUARD_SHA = sha(guard)
    prior["original_launch_guard"] = {"path": str(guard), "sha256": sha(guard)}
    monitor = {
        "status": "unclosed_child_exit",
        "child_exit_code": 1,
        "child_pid": observer.ORIGINAL_PIDS[2],
        "prior_sha256": sha(guard),
        "native_output_path": str(native),
        "financial_qualification": "unknown",
        "historical_cost": 12.5,
        "requested_administrative_stop": None,
    }
    outer = {
        "schema": "rb-f04-root-formal-monitor-enclosing-cost-v1",
        "status": "terminal_requires_native_and_saved_result_inspection",
        "monitor_exit_code": 3,
        "monitor_pid": observer.ORIGINAL_PIDS[1],
        "guard_sha256": sha(guard),
        "wall_seconds": 14.0,
    }
    dump(Path(prior["original_terminal_monitor_receipt"]["path"]), monitor)
    dump(Path(prior["original_terminal_enclosing_receipt"]["path"]), outer)
    seen = []
    observer.original_source_binding = lambda value: (
        seen.append("fixture_source_authority"),
        {"fixture_only": True, "original_source_parameters_untouched": True},
    )[1]
    return observer, prior, checkpoint, seen


def main():
    helper = load(HELPER, "native_terminal_candidate_prepared")
    results = []

    def run_case(name, mutate=None, *, expect=None, after=None):
        with tempfile.TemporaryDirectory(prefix="terminal-byte-pure-", dir=D) as directory:
            root = Path(directory)
            observer, prior, checkpoint, seen = fixture(root)
            output = root / "new-unapproved-candidate.json"
            if mutate:
                mutate(observer, prior, checkpoint, output)
            original = copy.deepcopy(prior)
            counter = []
            real_inventory = helper._native_inventory

            def inventory(observer_arg):
                counter.append("inventory")
                result = real_inventory(observer_arg)
                if after:
                    after(observer_arg, prior, checkpoint, output)
                return result

            with patch.object(helper, "_native_inventory", inventory):
                try:
                    result = helper.freeze_candidate(
                        observer,
                        prior,
                        output,
                        capacity_reader=lambda value: {"fixture_only": True, "whole_RSS_fit": None},
                    )
                except (observer.GuardRejectedError, OSError, ValueError) as exc:
                    assert expect and expect in str(exc), (name, str(exc))
                    assert not output.exists() or name == "existing_output_rejected"
                    result = None
                else:
                    assert expect is None, name + " accepted"
                    assert result["root_preapproved"] is False
                    assert result["execute_saved_check"] is False
                    assert result["finance_acceptance"] is False
                    assert result["new_saved_check_budget_approved"] is False
                    assert result["formal_financial_launch_authorized"] is False
                    assert result["financial_A_cap_projection_approved"] is False
                    assert result["financial_qualification"] == "unknown"
                    assert result["original_counts"] == original["original_counts"]
                    assert (
                        result["original_teacher_N_candidates"]
                        == original["original_teacher_N_candidates"]
                    )
                    assert result["expense_scope"] == original["expense_scope"]
                    assert (
                        result["required_external_expense_ids"]
                        == original["required_external_expense_ids"]
                    )
                    assert len(result["closed_native"]["files"]) == 4
                    assert result["closed_native"]["latest_checkpoint"]["receipt_sha256"] == sha(
                        checkpoint / "receipt.json"
                    )
                    assert seen == ["fixture_source_authority", "fixture_source_authority"]
                    observer.closed_native_binding(result)
                    stored = json.loads(output.read_text())
                    assert stored == result
            if name in (
                "live_pid_rejected_before_inventory",
                "missing_terminal_receipt",
                "wrong_guard_binding",
                "noninteger_monitor_exit",
                "missing_monitor_pid",
            ):
                assert counter == [], name
            assert prior == original
            results.append({"probe": name, "status": "PASS", "inventory_calls": len(counter)})

    run_case("complete_four_files_unknown_source_fault_preserved")

    def live(observer, prior, checkpoint, output):
        observer.ORIGINAL_PIDS = [1, 9999902, 9999903]
        prior["original_process_ids"] = observer.ORIGINAL_PIDS

    run_case("live_pid_rejected_before_inventory", live, expect="must all be terminal")

    def missing(observer, prior, checkpoint, output):
        Path(prior["original_terminal_monitor_receipt"]["path"]).unlink()

    run_case("missing_terminal_receipt", missing, expect="terminal receipt")

    def wrong_guard(observer, prior, checkpoint, output):
        prior["original_launch_guard"]["sha256"] = "0" * 64

    run_case("wrong_guard_binding", wrong_guard, expect="bytes changed")

    def bad_exit(observer, prior, checkpoint, output):
        path = Path(prior["original_terminal_monitor_receipt"]["path"])
        value = json.loads(path.read_text())
        value["child_exit_code"] = None
        dump(path, value)

    run_case("noninteger_monitor_exit", bad_exit, expect="terminal child")

    def bad_pid(observer, prior, checkpoint, output):
        path = Path(prior["original_terminal_monitor_receipt"]["path"])
        value = json.loads(path.read_text())
        value.pop("child_pid")
        dump(path, value)

    run_case("missing_monitor_pid", bad_pid, expect="terminal child")

    def bad_outer(observer, prior, checkpoint, output):
        path = Path(prior["original_terminal_enclosing_receipt"]["path"])
        value = json.loads(path.read_text())
        value["status"] = "running"
        dump(path, value)

    run_case("nonterminal_enclosing_receipt", bad_outer, expect="nonterminal")

    def existing(observer, prior, checkpoint, output):
        output.write_text("user owned")

    run_case("existing_output_rejected", existing, expect="already exists")

    def temporary(observer, prior, checkpoint, output):
        (checkpoint / "writer.tmp").write_bytes(b"partial")

    run_case("temporary_file_rejected", temporary, expect="temporary")

    def link(observer, prior, checkpoint, output):
        (checkpoint / "unsafe-link").symlink_to(checkpoint / "arrays.npz")

    run_case("symlink_rejected", link, expect="symbolic")

    def extra(observer, prior, checkpoint, output):
        (checkpoint / "extra.json").write_bytes(b"changed")

    run_case("extra_after_inventory_rejected", expect="changed", after=extra)

    def latest(observer, prior, checkpoint, output):
        (observer.ORIGINAL_NATIVE / "checkpoint999999").mkdir()

    run_case(
        "latest_checkpoint_after_inventory_rejected", expect="final saved checkpoint", after=latest
    )

    def receipt(observer, prior, checkpoint, output):
        (checkpoint / "receipt.json").write_bytes(b"changed")

    run_case("checkpoint_receipt_changed_rejected", expect="changed", after=receipt)

    def terminal(observer, prior, checkpoint, output):
        path = Path(prior["original_terminal_enclosing_receipt"]["path"])
        value = json.loads(path.read_text())
        value["guard_sha256"] = "0" * 64
        dump(path, value)

    run_case(
        "terminal_receipt_changed_after_inventory_rejected", expect="bytes changed", after=terminal
    )

    def source_changed(observer, prior, checkpoint, output):
        observer.original_source_binding = lambda value: {"changed_source_or_input": True}

    run_case(
        "source_input_plan_authority_changed_rejected",
        expect="authority changed",
        after=source_changed,
    )

    def missing_checkpoint_receipt(observer, prior, checkpoint, output):
        (checkpoint / "receipt.json").unlink()

    run_case(
        "latest_checkpoint_receipt_missing", missing_checkpoint_receipt, expect="checkpoint receipt"
    )
    return {
        "passed": len(results),
        "results": results,
        "financial_execution": 0,
        "genuine_native_inventory_or_raw_decode": 0,
        "Popen": 0,
        "fixture_native_files": 4,
        "root_preapproved": False,
        "execute_saved_check": False,
        "finance_acceptance": False,
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
