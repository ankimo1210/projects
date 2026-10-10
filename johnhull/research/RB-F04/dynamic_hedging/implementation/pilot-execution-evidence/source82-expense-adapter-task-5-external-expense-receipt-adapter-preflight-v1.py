"""Small future receipt fixtures only; no native decode or financial execution."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import tempfile
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

import numpy as np

D = Path(__file__).resolve().parent
W = D.parents[2]
R = W / "johnhull/research/RB-F04/dynamic_hedging"
ADAPTER = D / "task-5-external-expense-receipt-adapter-v1.py"
RESULT = D / "task-5-external-expense-receipt-adapter-results-v1.json"
CORE = W / "deep_hedge_price/src/deep_hedge_price"
IDS = (
    "cold_imports",
    "source_registry",
    "code_review",
    "math_review",
    "pilot_review",
    "serialization",
    "saved_check",
    "CAS_primary",
    "CAS_mirror",
    "domain_selection",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def functions(path, names, namespace):
    tree = ast.parse(path.read_text())
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in selected} == set(names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)


def actual_contracts():
    spec = importlib.util.spec_from_file_location(
        "isolated_actual_protocol", CORE / "_dynamic_hedging_protocol.py"
    )
    protocol = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(protocol)

    def require(ok, message):
        if not ok:
            raise ValueError(message)

    ns = {"np": np, "_require": require, "_v1": protocol}
    functions(CORE / "_dynamic_hedging_execution.py", ["_current_expenses"], ns)
    functions(R / "check_pilot.py", ["_check_actual_expense_clock"], ns)
    dns = {
        "np": np,
        "hashlib": hashlib,
        "json": json,
        "HestonParameters": type("UnusedParametersFixtureType", (), {}),
    }
    functions(R / "run_reference.py", ["_digest", "_encode_tree", "payload_digest"], dns)
    return (
        protocol,
        SimpleNamespace(_current_expenses=ns["_current_expenses"]),
        ns["_check_actual_expense_clock"],
        dns["payload_digest"],
    )


def raw_fixture():
    phase = {
        "id": "actual-native-phase",
        "scope": "synthetic native inclusive phase",
        "status": "complete",
        "parent_id": None,
        "includes_children": True,
        "timing": {"wall_seconds": 1.0, "cpu_seconds": 0.1, "overrun_seconds": 0.0},
        "timing_events": {
            "wall_start_ns": 1_000_000_000,
            "wall_stop_ns": 2_000_000_000,
            "cpu_start_ns": 10_000_000,
            "cpu_stop_ns": 110_000_000,
        },
    }
    return {
        "schema": "rb-f04-pilot-raw-v1",
        "source": {"fixture_only": True, "origin": "source82 future fixture"},
        "locked_plan": {"original_counts": [3138, 121, 51], "all_N": [1024, 4096, 16384, 65536]},
        "input_bindings": {"fixture_only": True, "seed": 913},
        "execution_phases": [phase],
        "jobs": [{"id": "tiny-source-fixture", "raw": {"values": np.arange(8.0)}}],
        "history": [{"original_failure": "unknown"}],
        "financial_qualification": "unknown",
    }


def expected(raw, digest):
    return {
        "source_sha256": digest(raw["source"]),
        "plan_sha256": digest(raw["locked_plan"]),
        "input_bindings_sha256": digest(raw["input_bindings"]),
        "raw_snapshot_sha256": digest(raw),
    }


def write_receipt(directory, eid, bindings, *, parent=None, includes=False, mutate=None):
    expense = {
        "id": eid,
        "scope": "whole future fixture:" + eid,
        "status": "complete",
        "parent_id": parent,
        "includes_children": includes,
        "timing": {"wall_seconds": 0.2, "cpu_seconds": 0.02, "overrun_seconds": 0.0},
        "timing_events": {
            "wall_start_ns": 1_200_000_000,
            "wall_stop_ns": 1_400_000_000,
            "cpu_start_ns": 20_000_000,
            "cpu_stop_ns": 40_000_000,
        },
        "whole_external_id_closed": True,
        "final_receipt_construction_write_stdout_tail_seconds": 0.001,
    }
    receipt = {"expense": expense, "bindings": copy.deepcopy(bindings)}
    if mutate:
        mutate(receipt)
    path = directory / (eid + ".json")
    path.write_text(json.dumps(receipt, allow_nan=False))
    return {"path": str(path), "sha256": sha(path), "id": eid, "scope": expense["scope"]}


def main():
    started = time.perf_counter()
    closure = json.loads((D / "current-production-source-closure-v1.json").read_text())
    assert len(closure["files"]) == 82
    before = {str(W / relative): sha(W / relative) for relative in closure["files"]}
    assert {relative: before[str(W / relative)] for relative in closure["files"]} == closure[
        "files"
    ]
    result = {
        "schema": "rb-f04-external-expense-receipt-adapter-pure-verification-v1",
        "financial_qualification": "unknown",
        "actual_native_read_or_finance": 0,
        "CAS_Git_operations": 0,
    }
    try:
        spec = importlib.util.spec_from_file_location("pure_receipt_adapter", ADAPTER)
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
    except FileNotFoundError:
        result.update(status="RED_expected", trace=traceback.format_exc())
        with RESULT.open("x") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(json.dumps({"status": result["status"], "sha256": sha(RESULT)}))
        return 1
    previous_result = json.loads(RESULT.read_text())
    old_red = previous_result.get("original_RED", previous_result)
    assert old_red["status"] == "RED_expected"
    protocol, execution, clock, digest = actual_contracts()
    checks = []
    raw = raw_fixture()
    original = digest(raw)
    bindings = expected(raw, digest)
    count = [0]

    def counted(value):
        if value is raw:
            count[0] += 1
        return digest(value)

    def build(refs, snapshot=raw, exp=bindings):
        return adapter.build_candidate(
            snapshot,
            refs,
            exp,
            protocol=protocol,
            execution=execution,
            check_actual_clock=clock,
            payload_digest=counted,
        )

    with tempfile.TemporaryDirectory(prefix="expense-receipt-fixture-") as temporary:
        base = Path(temporary)

        def batch(name, **options):
            root = base / name
            root.mkdir()
            return [write_receipt(root, eid, bindings, **options.get(eid, {})) for eid in IDS]

        refs = batch("valid")
        candidate = build(list(reversed(refs)))
        assert [row["id"] for row in candidate["snapshot"]["external_expenses"]] == list(IDS)
        assert candidate["external_rows_complete"] is True
        assert count[0] == 1
        assert candidate["snapshot"]["jobs"] is raw["jobs"]
        assert candidate["snapshot"]["source"] is raw["source"]
        assert candidate["snapshot"]["locked_plan"] is raw["locked_plan"]
        assert candidate["snapshot"]["history"] is raw["history"]
        assert "external_expenses" not in raw and digest(raw) == original
        assert (
            candidate["snapshot"]["external_expenses"][0]
            is not json.loads(Path(refs[0]["path"]).read_text())["expense"]
        )
        assert candidate["composite_lineage_is_native_payload_digest"] is False
        assert candidate["original_raw_snapshot_sha256"] == original
        assert candidate["actual_terminal_and_native_physical_bytes_authenticated"] is False
        assert all(
            candidate[key] is False
            for key in (
                "root_preapproved",
                "execute_saved_check",
                "finance_acceptance",
                "all_expenses_closed",
            )
        )
        checks.append(
            "valid10 existing contracts; original references/unmodified; original digest exactly once"
        )

        def incomplete(label, options):
            value = build(batch(label, **options))
            assert not value["external_rows_complete"]
            assert value["missing_external_expense_ids"] == ["saved_check"]
            assert value["external_accounting"][6]["status"] == "unclosed"
            assert len(value["snapshot"]["external_expenses"]) == 9
            assert value["unclosed_receipts"][0]["receipt_sha256"]
            return value

        incomplete(
            "prefix",
            {
                "saved_check": {
                    "mutate": lambda r: r.update(measured_prefix_expense=r.pop("expense"))
                }
            },
        )
        incomplete(
            "unknown",
            {"saved_check": {"mutate": lambda r: r["expense"]["timing"].update(cpu_seconds=None)}},
        )
        incomplete(
            "tail",
            {
                "saved_check": {
                    "mutate": lambda r: r["expense"].update(
                        final_receipt_construction_write_stdout_tail_seconds=None
                    )
                }
            },
        )
        incomplete(
            "elapsed",
            {
                "saved_check": {
                    "mutate": lambda r: r.update(
                        elapsed_seconds=0.2,
                        expense={"id": "saved_check", "scope": "whole future fixture:saved_check"},
                    )
                }
            },
        )
        checks.append(
            "prefix/unknown/tail/elapsed-only remain unclosed; no zero or endpoint fabrication"
        )

        def rejected(label, change, snapshot=raw, exp=bindings):
            try:
                build(change(), snapshot=snapshot, exp=exp)
            except ValueError:
                checks.append("reject:" + label)
            else:
                raise AssertionError(label + " accepted")

        rejected("receipt-byte-tamper", lambda: [dict(refs[0], sha256="0" * 64), *refs[1:]])
        rejected(
            "binding-tamper",
            lambda: batch(
                "badbinding",
                saved_check={"mutate": lambda r: r["bindings"].update(plan_sha256="0" * 64)},
            ),
        )
        rejected("duplicate-ID", lambda: [*refs, refs[0]])
        changed = copy.copy(raw)
        changed["external_expenses"] = []
        rejected(
            "existing external_expenses overwrite",
            lambda: refs,
            snapshot=changed,
            exp=expected(changed, digest),
        )

        no_domain = batch(
            "no-parent-domain",
            source_registry={"parent": "cold_imports"},
            cold_imports={"includes": True},
        )
        unproven = build(no_domain)
        assert not unproven["external_rows_complete"]
        assert unproven["missing_external_expense_ids"] == ["source_registry"]
        checks.append("parent forest alone does not establish CPU/domain inclusion")

        def replace_receipt(ref, change):
            path = Path(ref["path"])
            rec = json.loads(path.read_text())
            change(rec)
            path.write_text(json.dumps(rec, allow_nan=False))
            ref["sha256"] = sha(path)
            return rec

        def inclusion(ref, parent, exp=bindings, kind="same_process_child_scope", extra=None):
            child = json.loads(Path(ref["path"]).read_text())["expense"]
            proof = {
                "kind": kind,
                "bindings": copy.deepcopy(exp),
                "parent_id": parent["id"],
                "child_id": child["id"],
                "parent_expense_sha256": digest(parent),
                "child_expense_sha256": digest(child),
                "parent_scope": parent["scope"],
                "child_scope": child["scope"],
                "parent_wall_clock_domain": "fixture-host-boot:perf_counter_ns",
                "child_wall_clock_domain": "fixture-host-boot:perf_counter_ns",
                "parent_pid": 44,
                "child_pid": 44,
                "parent_cpu_clock_domain": "fixture-process_time_ns:44",
                "child_cpu_clock_domain": "fixture-process_time_ns:44",
            }
            if extra:
                proof.update(extra)
            path = Path(ref["path"]).with_name(ref["id"] + "-" + parent["id"] + "-coverage.json")
            path.write_text(json.dumps(proof, allow_nan=False))
            pref = {"path": str(path), "sha256": sha(path)}
            replace_receipt(ref, lambda r: r.update(parent_inclusion_receipts=[pref]))
            return pref

        nested = batch(
            "nested", source_registry={"parent": "cold_imports"}, cold_imports={"includes": True}
        )
        replace_receipt(
            nested[0],
            lambda r: r["expense"].update(
                timing=copy.deepcopy(raw["execution_phases"][0]["timing"]),
                timing_events=copy.deepcopy(raw["execution_phases"][0]["timing_events"]),
            ),
        )
        nested_parent = json.loads(Path(nested[0]["path"]).read_text())["expense"]
        inclusion(nested[1], nested_parent)
        tree = build(nested)
        assert tree["external_rows_complete"]
        charged = tree["expense_validation"]["charged_ids"]
        assert "source_registry" not in charged and "cold_imports" in charged
        assert (
            tree["snapshot"]["external_expenses"][1]["timing_events"]["wall_start_ns"]
            == 1_200_000_000
        )
        checks.append(
            "real external child scope inside same-process actual inclusive parent charged once"
        )

        native_refs = batch("native-parent", domain_selection={"parent": "actual-native-phase"})
        native_parent = raw["execution_phases"][0]
        inclusion(native_refs[-1], native_parent)
        linked = build(native_refs)
        assert linked["external_rows_complete"]
        assert "domain_selection" not in linked["expense_validation"]["charged_ids"]
        assert linked["authenticated_native_parent_ids"] == ["actual-native-phase"]
        assert (
            linked["snapshot"]["external_expenses"][-1]["timing_events"]["cpu_start_ns"]
            == 20_000_000
        )
        checks.append(
            "actual child clocks inside native phase preserved; native parent is not re-injected"
        )

        replace_receipt(
            native_refs[-1],
            lambda r: r["expense"].update(
                timing={"wall_seconds": 0.2, "cpu_seconds": 0.02, "overrun_seconds": 0.0},
                timing_events={
                    "wall_start_ns": 3_000_000_000,
                    "wall_stop_ns": 3_200_000_000,
                    "cpu_start_ns": 50_000_000,
                    "cpu_stop_ns": 70_000_000,
                },
            ),
        )
        inclusion(native_refs[-1], native_parent)
        late = build(native_refs)
        assert late["missing_external_expense_ids"] == ["domain_selection"]
        assert (
            late["unclosed_receipts"][0]["original_expense_or_prefix"]["timing_events"][
                "wall_start_ns"
            ]
            == 3_000_000_000
        )
        checks.append(
            "post-phase measured expense stays unclosed; cannot be hidden by inclusive parent"
        )

        alias_refs = batch("copied-alias", domain_selection={"parent": "actual-native-phase"})
        replace_receipt(
            alias_refs[-1],
            lambda r: r["expense"].update(
                timing=copy.deepcopy(native_parent["timing"]),
                timing_events=copy.deepcopy(native_parent["timing_events"]),
            ),
        )
        inclusion(alias_refs[-1], native_parent, kind="actual_parent_clock_alias")
        rejected("copied-parent-clock alias completing fixed external ID", lambda: alias_refs)

        projected_alias = batch(
            "existing-projected-alias", domain_selection={"parent": "actual-native-phase"}
        )
        alias_record = replace_receipt(
            projected_alias[-1],
            lambda r: r["expense"].update(
                scope="prior inclusive execution alias:domain_selection",
                timing=copy.deepcopy(native_parent["timing"]),
                timing_events=copy.deepcopy(native_parent["timing_events"]),
                alias_scope="actual parent inclusive clock; not separately timed child",
                actual_parent_sha256=digest(native_parent),
                prior_alias_sha256="fixture-only-prior",
            ),
        )
        projected_alias[-1]["scope"] = alias_record["expense"]["scope"]
        inclusion(projected_alias[-1], native_parent)
        rejected(
            "existing execution alias cannot become external child measurement",
            lambda: projected_alias,
        )

        ancestor_refs = batch(
            "inclusive-ancestor",
            cold_imports={"parent": "actual-native-phase"},
            source_registry={"parent": "cold_imports"},
        )
        inclusion(ancestor_refs[0], native_parent)
        replace_receipt(
            ancestor_refs[1],
            lambda r: r["expense"].update(
                timing_events={
                    "wall_start_ns": 3_000_000_000,
                    "wall_stop_ns": 3_200_000_000,
                    "cpu_start_ns": 20_000_000,
                    "cpu_stop_ns": 40_000_000,
                }
            ),
        )
        inclusion(ancestor_refs[1], native_parent)
        ancestor = build(ancestor_refs)
        assert ancestor["missing_external_expense_ids"] == ["source_registry"]
        checks.append(
            "every inclusive ancestor requires actual child coverage, even through noninclusive parent"
        )

        noninclusive = batch(
            "noninclusive",
            cold_imports={"includes": False},
            source_registry={"parent": "cold_imports"},
        )
        not_excluded = build(noninclusive)
        assert not_excluded["external_rows_complete"]
        # Distinct sibling wall/CPU events remain actual. A noninclusive parent
        # does not exclude the child in the existing protocol, so no coverage
        # proof is invented or required for it.
        assert "source_registry" in not_excluded["expense_validation"]["charged_ids"]
        checks.append("correct noninclusive parent forest preserved without blanket rejection")

        reaped_raw = copy.deepcopy(raw)
        reaped_parent = reaped_raw["execution_phases"][0]
        reaped_parent["timing"]["cpu_seconds"] = 0.21
        reaped_parent["timing_events"]["cpu_start_ns"] = 60_000_000
        reaped_parent["timing_events"]["cpu_stop_ns"] = 270_000_000
        reaped_bindings = expected(reaped_raw, digest)
        root = base / "reaped"
        root.mkdir()
        reaped_refs = [
            write_receipt(
                root,
                eid,
                reaped_bindings,
                parent="actual-native-phase" if eid == "domain_selection" else None,
            )
            for eid in IDS
        ]
        replace_receipt(
            reaped_refs[-1],
            lambda r: r["expense"]["timing_events"].update(
                cpu_start_ns=9_000_000_000, cpu_stop_ns=9_020_000_000
            ),
        )
        samples = {
            "parent_cpu_start_ns": 10_000_000,
            "parent_cpu_stop_ns": 110_000_000,
            "children_cpu_start": {
                "ru_utime_seconds": 0.04,
                "ru_stime_seconds": 0.01,
                "ru_utime_ns_rounded": 40_000_000,
                "ru_stime_ns_rounded": 10_000_000,
            },
            "children_cpu_stop": {
                "ru_utime_seconds": 0.14,
                "ru_stime_seconds": 0.02,
                "ru_utime_ns_rounded": 140_000_000,
                "ru_stime_ns_rounded": 20_000_000,
            },
        }
        reaped_proof = inclusion(
            reaped_refs[-1],
            reaped_parent,
            reaped_bindings,
            kind="reaped_child_scope",
            extra={
                "child_pid": 77,
                "parent_cpu_clock_domain": "fixture-parent44-process-plus-reaped-children",
                "child_cpu_clock_domain": "fixture-process_time_ns:77",
                "clock_source_samples": samples,
                "reaped_child_pids": [77],
                "reaped_child_scope": {
                    "id": "domain_selection",
                    "scope": "whole future fixture:domain_selection",
                    "pid": 77,
                    "cpu_seconds": 0.02,
                },
            },
        )
        reaped = build(reaped_refs, snapshot=reaped_raw, exp=reaped_bindings)
        assert reaped["external_rows_complete"]
        assert (
            reaped["snapshot"]["external_expenses"][-1]["timing_events"]["cpu_start_ns"]
            == 9_000_000_000
        )
        assert "domain_selection" not in reaped["expense_validation"]["charged_ids"]
        checks.append(
            "distinct-process real CPU axes not compared; original reaped samples/scope prove inclusion"
        )
        rp = Path(reaped_proof["path"])
        record = json.loads(rp.read_text())
        record["reaped_child_pids"] = []
        rp.write_text(json.dumps(record))
        reaped_proof["sha256"] = sha(rp)
        replace_receipt(
            reaped_refs[-1], lambda r: r.update(parent_inclusion_receipts=[reaped_proof])
        )
        uncovered = build(reaped_refs, snapshot=reaped_raw, exp=reaped_bindings)
        assert uncovered["missing_external_expense_ids"] == ["domain_selection"]
        checks.append("missing actual reaped child producer coverage remains unclosed")
        failed = batch(
            "failed",
            saved_check={
                "mutate": lambda r: r["expense"].update(
                    status="failed", reason="actual future fixture exit7"
                )
            },
        )
        assert build(failed)["external_rows_complete"] is True
        no_reason = batch(
            "failed-missing-reason",
            saved_check={"mutate": lambda r: r["expense"].update(status="failed")},
        )
        unclosed = build(no_reason)
        assert not unclosed["external_rows_complete"]
        checks.append("failed reason preserved; failed without original reason remains unclosed")
        rejected(
            "parent-cycle",
            lambda: batch(
                "cycle",
                source_registry={"parent": "cold_imports"},
                cold_imports={"parent": "source_registry", "includes": True},
            ),
        )
        assert digest(raw) == original and "external_expenses" not in raw
        lineage = {
            k: candidate[k]
            for k in (
                "original_raw_snapshot_sha256",
                "composite_lineage_sha256",
                "composite_lineage_is_native_payload_digest",
                "external_rows_complete",
            )
        }
    assert before == {path: sha(path) for path in before}
    result.update(
        status="PASS",
        checks=checks,
        check_count=len(checks),
        original_RED=old_red,
        previous_preflight_result=previous_result,
        future_fixture_only=True,
        source_bytes_unchanged=before,
        candidate_lineage=lineage,
        native_parent_fixture_accepted=True,
        previous_ordering_RED={
            "status": "observed_pre_correction_failure",
            "assertion": "external rows originally followed reversed receipt order, not fixed original10 order",
        },
        previous_alias_fixture_failure={
            "status": "observed_removed_unapproved_test_expectation",
            "assertion": "copied-clock native alias was not accepted after real-child scope correction",
        },
        verification_wall_seconds_before_write=time.perf_counter() - started,
        verification_tail_seconds=None,
    )
    RESULT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "PASS", "checks": len(checks), "sha256": sha(RESULT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
