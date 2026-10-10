"""Pure administrative refusal probes; no financial imports, numerical decode or child."""

from __future__ import annotations

import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

D = Path(__file__).resolve().parent
OBSERVER = D / "task-5-full-pilot-root-saved-check-observer-v1.py"
CANDIDATE = D / "task-5-full-pilot-root-saved-check-resource-candidate-v1.json"


def main():
    started = time.perf_counter()
    spec = importlib.util.spec_from_file_location("saved_check_prepared", OBSERVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = json.loads(CANDIDATE.read_text())
    results = []
    touched = []

    def forbidden(*args, **kwargs):
        touched.append("forbidden")
        raise AssertionError("financial/child/large input path reached")

    def refusal(name, change, message, *, live=False):
        prior = copy.deepcopy(original)
        change(prior)
        with tempfile.TemporaryDirectory(prefix="saved-check-pure-", dir=D) as directory:
            guard = D / (Path(directory).name + ".json")
            guard.write_text(json.dumps(prior))
            try:
                exists = Path.exists

                def probe_exists(path):
                    if str(path).startswith("/proc/"):
                        return live
                    return exists(path)

                with (
                    patch.object(Path, "exists", probe_exists),
                    patch.object(module.subprocess, "Popen", forbidden),
                    patch.object(module, "source_binding", forbidden),
                ):
                    try:
                        module.load_guard(guard)
                    except module.GuardRejectedError as exc:
                        assert message in str(exc), (name, str(exc))
                    else:
                        raise AssertionError(name + " accepted")
            finally:
                guard.unlink()
        results.append({"probe": name, "status": "PASS"})

    def approved(prior):
        prior.update(
            root_preapproved=True, execute_saved_check=True, saved_check_authorized_by="root"
        )

    refusal("candidate_no_authority", lambda prior: None, "root saved-check prior")
    refusal(
        "separate_execute_missing",
        lambda prior: prior.update(root_preapproved=True),
        "separate root saved-only",
    )

    def finance(prior):
        approved(prior)
        prior["finance_acceptance"] = True

    refusal("finance_acceptance_promotion_rejected", finance, "cannot grant financial")

    def launch(prior):
        approved(prior)
        prior["formal_financial_launch_authorized"] = True

    refusal("new_financial_launch_rejected", launch, "cannot grant financial")
    refusal("original_three_live_rejected", approved, "must all be terminal", live=True)

    def wrong_pid(prior):
        approved(prior)
        prior["original_process_ids"] = [1, 2, 3]

    refusal("original_process_binding_not_substituted", wrong_pid, "all three original process")
    refusal("pending_terminal_receipt_rejected_before_decode", approved, "pending reference SHA")
    try:
        module.closed_native_binding(original)
    except module.GuardRejectedError as exc:
        assert "finite file set" in str(exc)
    else:
        raise AssertionError("pending native closure accepted")
    results.append({"probe": "pending_native_byte_set_rejected", "status": "PASS"})

    volumes = [
        {"id": key, "path": "/", "reserve_bytes": 10 * module.GiB, "free_bytes": 11 * module.GiB}
        for key in ("WSL", "C", "F")
    ]
    cap = original
    assert module.choose_stop(2592000, 0, 0, volumes, cap)["metric"] == "outer_phase_wall"
    assert (
        module.choose_stop(1, 16 * module.GiB + 1, 0, volumes, cap)["metric"]
        == "individual_child_rss"
    )
    assert (
        module.choose_stop(1, 0, 16 * module.GiB + 1, volumes, cap)["metric"]
        == "individual_parent_rss"
    )
    low = copy.deepcopy(volumes)
    low[2]["free_bytes"] = 10 * module.GiB
    assert module.choose_stop(1, 0, 0, low, cap)["metric"] == "volume_reserve"
    assert module.choose_stop(1, None, None, volumes, cap) is None
    assert module.terminal_status(None, None, False, [], True) == "unclosed_child_terminal_unknown"
    assert module.terminal_status(1, None, False, [], True) == "unclosed_child_exit"
    assert (
        module.terminal_status(-9, {"metric": "outer_phase_wall"}, True, [], True)
        == "administrative_partial_unclosed"
    )
    assert (
        module.terminal_status(0, None, False, ["observer error"], True)
        == "unclosed_monitor_observer_error"
    )
    assert (
        module.terminal_status(0, None, False, [], False)
        == "unclosed_source_or_input_binding_changed"
    )
    assert (
        module.terminal_status(0, None, False, [], True)
        == "saved_checker_terminal_needs_result_inspection"
    )
    results.append(
        {
            "probe": "original_admin_caps_unknown_and_source_fault_not_financial_cap",
            "status": "PASS",
        }
    )

    before = ast.parse((D / "task-5-full-pilot-root-operational-monitor-v5.py").read_text())
    after = ast.parse(OBSERVER.read_text())

    def functions(tree):
        return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}

    old, new = functions(before), functions(after)
    untouched = (
        "digest",
        "sha",
        "clock",
        "save",
        "require",
        "absolute",
        "positive",
        "tree_binding",
        "reference_path",
        "fixed_reference",
        "limited_source_review",
        "actual_budget_review",
        "metadata_authority",
        "rss",
        "volume_sample",
        "choose_stop",
    )
    for name in untouched:
        assert ast.dump(old[name], include_attributes=False) == ast.dump(
            new[name], include_attributes=False
        ), name
    call = next(
        node
        for node in ast.walk(new["child"])
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "check_pilot"
    )
    context = next(keyword.value for keyword in call.keywords if keyword.arg == "context")
    assert isinstance(context, ast.Dict) and [key.value for key in context.keys] == [
        "inputs",
        "parameters",
    ]
    assert ast.unparse(context.values[1]) == "inputs['parameters']"
    assert (
        ast.unparse(
            next(keyword.value for keyword in call.keywords if keyword.arg == "source_root")
        )
        == "WT"
    )
    results.append(
        {
            "probe": "exact_context_inputs_parameters_and16_original_helpers_AST_preserved",
            "status": "PASS",
        }
    )

    with (
        patch.object(module.subprocess, "Popen", forbidden),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        assert module.main(["--guard", str(CANDIDATE)]) == 2
    assert touched == []
    results.append({"probe": "CLI_false_candidate_launch0_and_decode0", "status": "PASS"})
    outer_path = D / "task-5-full-pilot-root-saved-check-enclosing-v1.py"
    outer_spec = importlib.util.spec_from_file_location("saved_check_outer_prepared", outer_path)
    outer = importlib.util.module_from_spec(outer_spec)
    outer_spec.loader.exec_module(outer)
    with patch.object(outer.subprocess, "Popen", forbidden):
        try:
            outer.main(
                [
                    "--guard",
                    str(CANDIDATE),
                    "--guard-sha256",
                    hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
                ]
            )
        except AssertionError:
            pass
        else:
            raise AssertionError("unapproved outer candidate reached launch")
    assert touched == []
    results.append({"probe": "enclosing_false_candidate_launch0_and_decode0", "status": "PASS"})
    output = {
        "results": results,
        "passed": len(results),
        "new_numerical_execution": 0,
        "financial_imports_or_large_raw_decode": 0,
        "Popen_calls": 0,
        "fixture_scope": "synthetic administrative guards only; no native arrays read",
        "financial_qualification": "unknown",
        "finance_acceptance": False,
        "candidate_authority": False,
        "elapsed_seconds": time.perf_counter() - started,
        "observer_sha256": hashlib.sha256(OBSERVER.read_bytes()).hexdigest(),
        "candidate_sha256": hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
    }
    print(json.dumps(output, indent=2))
    return output


if __name__ == "__main__":
    main()
