"""Dual-source checker integration with tiny source/job metadata only.

The normal verifier identity walker is represented by two tiny canonical files.
The real saved provenance helper and source_registry authenticate actual bytes;
only the formal whole-plan validator and whole-cost aggregator are replaced by
unit scope fixtures. Per-job envelopes/resolved argument checks run unchanged.
Synthetic clocks are test values, never expense or financial approval evidence.
"""

import copy
import sys
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))
import _pilot_saved_storage as storage  # noqa: E402
import check_pilot as checker  # noqa: E402
import run_pilot as pilot  # noqa: E402
import run_reference as runner  # noqa: E402


@pytest.fixture
def unit(tmp_path, monkeypatch):
    roots = {}
    names = ("source.py", "helper.py")
    for role in ("producer", "verifier"):
        root = tmp_path / role
        root.mkdir()
        for name in names:
            (root / name).write_text(f"# tiny {role}: {name}\n")
        roots[role] = root

    def identity(root):
        root = Path(root).resolve()
        assert root in roots.values(), "fixture identity used outside tiny verifier source"
        return {
            "files": runner.protocol.source_registry(root, names),
            "dynamic_imports": [],
            "fixture_role": root.name,
        }

    producer = identity(roots["producer"])
    verifier = identity(roots["verifier"])
    monkeypatch.setattr(runner, "execution_source_identity", identity)
    inputs = {"parameters": {"synthetic_spot": 100.0}, "axis": np.array([0.0, 1.0])}
    bindings = {key: pilot.input_identity(value) for key, value in inputs.items()}
    planned = {
        "id": "unit-source",
        "operation": "source",
        "arguments": {},
        "prediction": {"fixture": "no-finance"},
        "budget": {"wall_seconds": 4.0},
        "expense_id": "unit-source-expense",
    }
    plan = {
        "schema": "unit-original-plan",
        "source": producer,
        "input_bindings": bindings,
        "jobs": [planned],
        "case_bindings": [],
        "attempt_bindings": [],
        "case_plan": [],
        "attempt_plan": [],
    }
    row = {
        **planned,
        "status": "executed",
        "raw": producer,
        "plan_sha256": storage.payload_digest(plan),
        "source_sha256": storage.payload_digest(producer),
        "input_bindings": bindings,
        "resolved_arguments_sha256": pilot.input_identity({}),
        "timing_events": {
            "wall_start_ns": 1_000_000_000,
            "wall_stop_ns": 2_000_000_000,
            "cpu_start_ns": 1_000_000_000,
            "cpu_stop_ns": 1_500_000_000,
        },
        "expense": {
            "id": planned["expense_id"],
            "scope": "unit source fixture",
            "status": "complete",
            "parent_id": None,
            "includes_children": False,
            "timing": {"wall_seconds": 1.0, "cpu_seconds": 0.5, "overrun_seconds": 0.0},
        },
    }
    snapshot = {
        "schema": "rb-f04-pilot-raw-v1",
        "source": producer,
        "locked_plan": plan,
        "jobs": [row],
        "test_opened": False,
        "case_bindings": [],
        "attempt_bindings": [],
        "external_expenses": [
            {
                "id": "saved_check",
                "scope": "whole original saved-check cost",
                "status": "pending",
                "parent_id": None,
                "includes_children": False,
                "timing": {"wall_seconds": None, "cpu_seconds": None, "overrun_seconds": None},
            }
        ],
        "fixture_fault_tail": {"status": "unknown", "reason": "KeyError: result", "raw": None},
    }
    trusted = {
        "schema": "rb-f04-saved-producer-verifier-binding-v1",
        "planned_before_check": True,
        "root_preapproved": True,
        "scope": "saved_original_raw_only",
        "producer_source_sha256": storage.payload_digest(producer),
        "producer_source_files": producer["files"],
        "producer_plan_sha256": storage.payload_digest(plan),
        "producer_input_bindings_sha256": storage.payload_digest(bindings),
        "verifier_source_sha256": storage.payload_digest(verifier),
    }
    context = {
        "saved_source_binding": trusted,
        "producer_source_root": roots["producer"],
        "source_root": roots["verifier"],
        "inputs": inputs,
    }

    def validate(actual):
        assert actual is plan
        assert actual["source"] is producer
        assert actual["input_bindings"] == bindings

    monkeypatch.setattr(pilot, "validate_locked_plan", validate)
    cost = {
        "closed": False,
        "charged_totals": {"wall_seconds": None, "cpu_seconds": None},
        "external_pending": ["saved_check", "proof_cas"],
    }
    monkeypatch.setattr(checker, "check_raw_costs", lambda actual, locked: copy.deepcopy(cost))
    return {
        "roots": roots,
        "producer": producer,
        "verifier": verifier,
        "inputs": inputs,
        "bindings": bindings,
        "plan": plan,
        "row": row,
        "snapshot": snapshot,
        "trusted": trusted,
        "context": context,
        "cost": cost,
    }


def run(unit):
    return checker.check_pilot_records(
        unit["snapshot"], expected_plan=unit["plan"], context=unit["context"]
    )


def test_original_source_and_new_verifier_are_authenticated_twice(unit, monkeypatch):
    original_registry = runner.protocol.source_registry
    producer_calls = []
    original_raw_check = checker._raw_job_check
    memo_sources = []

    def registry(root, names):
        if Path(root).resolve() == unit["roots"]["producer"]:
            producer_calls.append(tuple(names))
        return original_registry(root, names)

    def raw_check(job, context):
        memo_sources.append(context["teacher_verification_context"]["source"])
        return original_raw_check(job, context)

    monkeypatch.setattr(runner.protocol, "source_registry", registry)
    monkeypatch.setattr(checker, "_raw_job_check", raw_check)
    result = run(unit)
    assert len(producer_calls) == 2
    assert memo_sources == [unit["verifier"]]
    source = result["raw_checks"]["unit-source"]
    assert source["actual_source"] == unit["producer"]
    assert source["current_verifier_source"] == unit["verifier"]
    provenance = result["saved_source_provenance"]
    assert provenance["producer_source_sha256"] == unit["trusted"]["producer_source_sha256"]
    assert provenance["verifier_source_sha256"] == unit["trusted"]["verifier_source_sha256"]
    assert provenance["producer_plan_sha256"] == storage.payload_digest(unit["plan"])
    assert provenance["producer_input_bindings_sha256"] == storage.payload_digest(unit["bindings"])
    assert provenance["provenance"]["trusted_binding_sha256"] == storage.payload_digest(
        unit["trusted"]
    )
    assert provenance["provenance"]["scope"] == "saved_original_raw_only"
    assert result["raw_snapshot"] is unit["snapshot"]
    assert result["costs"] == unit["cost"]
    assert result["raw_snapshot"]["fixture_fault_tail"] == {
        "status": "unknown",
        "reason": "KeyError: result",
        "raw": None,
    }
    assert len(result["missing_cases"]) == 121
    assert len(result["missing_attempts"]) == 51
    assert result["closed"] is False
    assert result["financial_qualification"] == "unknown"
    assert result["verification"] is None


@pytest.mark.parametrize(
    "mutation",
    [
        "unapproved",
        "not_prior",
        "scope",
        "flags_only",
        "roles_reversed",
        "producer_root_replaced",
        "stale_verifier",
        "actual_input_changed",
        "actual_input_roster_changed",
    ],
)
def test_bad_saved_binding_is_rejected_without_internal_auth_bypass(unit, mutation):
    trusted = unit["trusted"]
    if mutation == "unapproved":
        trusted["root_preapproved"] = False
    elif mutation == "not_prior":
        trusted["planned_before_check"] = False
    elif mutation == "scope":
        trusted["scope"] = "fresh_run"
    elif mutation == "flags_only":
        for key in list(trusted):
            if key.endswith("sha256") or key == "producer_source_files":
                del trusted[key]
    elif mutation == "roles_reversed":
        trusted["producer_source_sha256"], trusted["verifier_source_sha256"] = (
            trusted["verifier_source_sha256"],
            trusted["producer_source_sha256"],
        )
    elif mutation == "producer_root_replaced":
        unit["context"]["producer_source_root"] = unit["roots"]["verifier"]
    elif mutation == "stale_verifier":
        (unit["roots"]["verifier"] / "source.py").write_text("# stale source\n")
    elif mutation == "actual_input_changed":
        unit["inputs"]["axis"][-1] = 2.0
    else:
        unit["inputs"]["unplanned"] = 123.0
    unit["context"]["saved_source_authentication"] = {
        "producer_source": unit["producer"],
        "verifier_source": unit["verifier"],
        "claimed_authenticated": True,
    }
    with pytest.raises(ValueError):
        run(unit)


def test_injected_internal_auth_is_replaced_by_real_authentication(unit):
    unit["context"]["saved_source_authentication"] = {
        "producer_source": unit["verifier"],
        "verifier_source": unit["producer"],
        "provenance": {"scope": "forged"},
    }
    result = run(unit)
    assert result["raw_checks"]["unit-source"]["actual_source"] == unit["producer"]
    assert result["saved_source_provenance"]["provenance"]["scope"] == "saved_original_raw_only"


def test_source_raw_relabel_remains_unclosed_and_original_snapshot_is_retained(unit):
    unit["row"]["raw"] = unit["verifier"]
    result = run(unit)
    assert "unit-source" not in result["raw_checks"]
    assert any(
        row["id"] == "unit-source" and row["status"] == "unclosed_semantic_check"
        for row in result["issues"]
    )
    assert result["raw_snapshot"]["jobs"][0]["raw"] is unit["verifier"]
    assert result["raw_snapshot"]["source"] is unit["producer"]
    assert result["financial_qualification"] == "unknown"
    assert result["closed"] is False


@pytest.mark.parametrize("target", ["inputs", "producer", "verifier", "internal_recipe"])
def test_final_authentication_rejects_midcheck_changes(unit, monkeypatch, target):
    original_raw_check = checker._raw_job_check

    def raw_check(job, context):
        value = original_raw_check(job, context)
        if target == "inputs":
            unit["inputs"]["axis"][-1] = 4.0
        elif target == "producer":
            (unit["roots"]["producer"] / "helper.py").write_text("# changed original bytes\n")
        else:
            (unit["roots"]["verifier"] / "helper.py").write_text("# changed verifier bytes\n")
            if target == "internal_recipe":
                updated = runner.execution_source_identity(unit["roots"]["verifier"])
                context["saved_source_binding"]["verifier_source_sha256"] = storage.payload_digest(
                    updated
                )
        return value

    monkeypatch.setattr(checker, "_raw_job_check", raw_check)
    with pytest.raises(ValueError):
        run(unit)


def test_external_recipe_alias_change_does_not_replace_initial_recipe(unit, monkeypatch):
    original_raw_check = checker._raw_job_check
    original_digest = storage.payload_digest(unit["trusted"])

    def raw_check(job, context):
        value = original_raw_check(job, context)
        unit["trusted"]["scope"] = "external alias changed"
        return value

    monkeypatch.setattr(checker, "_raw_job_check", raw_check)
    result = run(unit)
    assert result["saved_source_provenance"]["provenance"]["trusted_binding_sha256"] == (
        original_digest
    )
    assert unit["context"]["saved_source_binding"]["scope"] == "external alias changed"


def test_fresh_binding_still_refuses_new_source_despite_internal_injection(unit):
    unit["context"].pop("saved_source_binding")
    unit["context"]["saved_source_authentication"] = {
        "producer_source": unit["producer"],
        "verifier_source": unit["verifier"],
    }
    with pytest.raises(ValueError, match="current transitive source differs"):
        run(unit)


def test_default_same_source_uses_original_fresh_authentication(unit):
    unit["context"].pop("saved_source_binding")
    unit["context"]["source_root"] = unit["roots"]["producer"]
    result = run(unit)
    assert result["saved_source_provenance"] is None
    assert result["raw_checks"]["unit-source"]["actual_source"] == unit["producer"]
    assert result["closed"] is False
    assert result["costs"]["charged_totals"]["wall_seconds"] is None


def test_real_fault_tail_unknown_and_original_none_expense_are_retained(unit):
    fault_plan = {
        "id": "unit-fault-tail",
        "operation": "validation",
        "arguments": {},
        "prediction": {"fixture": "original source fault"},
        "budget": {"wall_seconds": 4.0},
        "expense_id": "unit-fault-expense",
    }
    unit["plan"]["jobs"].append(fault_plan)
    fault = copy.deepcopy(unit["row"])
    fault.update(
        id=fault_plan["id"],
        operation=fault_plan["operation"],
        prediction=fault_plan["prediction"],
        budget=fault_plan["budget"],
        status="unclosed_source_or_solver_defect",
        reason="KeyError: result",
        raw=None,
    )
    fault["expense"].update(id=fault_plan["expense_id"], status="failed", reason=fault["reason"])
    unit["snapshot"]["jobs"].append(fault)
    for row in unit["snapshot"]["jobs"]:
        row["plan_sha256"] = storage.payload_digest(unit["plan"])
    unit["trusted"]["producer_plan_sha256"] = storage.payload_digest(unit["plan"])
    original_snapshot_digest = storage.payload_digest(unit["snapshot"])
    result = run(unit)
    assert result["issues"] == [
        {"id": fault["id"], "reason": "KeyError: result", "status": fault["status"]}
    ]
    assert result["raw_snapshot"]["jobs"][-1] is fault
    assert fault["raw"] is None
    assert storage.payload_digest(unit["snapshot"]) == original_snapshot_digest
    assert result["costs"] == unit["cost"]
    assert result["raw_snapshot"]["external_expenses"] == unit["snapshot"]["external_expenses"]
    assert result["raw_snapshot"]["external_expenses"][0]["timing"] == {
        "wall_seconds": None,
        "cpu_seconds": None,
        "overrun_seconds": None,
    }
    assert result["verification"] is None
    assert result["financial_qualification"] == "unknown"


def test_closed_unit_receipt_preserves_producer_and_adds_separate_verifier_ids(unit, monkeypatch):
    # An EMPTY artificial roster isolates receipt serialization. It is not the
    # formal 121/51 scope, and a vacuous unit closure confers no finance approval.
    monkeypatch.setattr(
        checker.execution,
        "execution_candidate",
        lambda: {"pilot_cases": [], "required_pilot_attempt_ids": []},
    )
    monkeypatch.setattr(
        checker,
        "check_raw_costs",
        lambda snapshot, plan: {"closed": True, "charged_totals": {"wall_seconds": 1.0}},
    )
    result = run(unit)
    assert result["closed"] is True
    receipt = result["verification"]["inputs"]
    assert receipt["source_sha256"] == unit["trusted"]["producer_source_sha256"]
    assert receipt["producer_source_sha256"] == unit["trusted"]["producer_source_sha256"]
    assert receipt["verifier_source_sha256"] == unit["trusted"]["verifier_source_sha256"]
    assert receipt["trusted_binding_sha256"] == storage.payload_digest(unit["trusted"])
    assert receipt["plan_sha256"] == unit["trusted"]["producer_plan_sha256"]
