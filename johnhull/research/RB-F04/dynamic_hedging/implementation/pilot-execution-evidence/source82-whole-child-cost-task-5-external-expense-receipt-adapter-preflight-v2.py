"""Tiny producer-to-adapter admin retention probes; no financial/native run."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import time
import traceback
from pathlib import Path

D = Path(__file__).resolve().parent
W = D.parents[2]
R = W / "johnhull/research/RB-F04/dynamic_hedging"
ADAPTER = D / "task-5-external-expense-receipt-adapter-v2.py"
OLD = D / "task-5-external-expense-receipt-adapter-v1.py"
RESULT = D / "task-5-external-expense-receipt-adapter-results-v2.json"
ADMIN_ID = "saved_check:outer_unmeasured_bookkeeping"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    start = time.perf_counter_ns()
    cpu = time.process_time_ns()
    previous_red = json.loads(RESULT.read_text()) if RESULT.exists() else None
    if previous_red is not None:
        previous_red = previous_red.get("initial_v2_RED", previous_red)
    closure = json.loads((D / "current-production-source-closure-v1.json").read_text())
    before = {relative: sha(W / relative) for relative in closure["files"]}
    assert len(before) == 82 and before == closure["files"]
    frozen = {
        name: sha(D / name)
        for name in (
            "task-5-external-expense-receipt-adapter-v1.py",
            "task-5-external-expense-receipt-adapter-preflight-v1.py",
            "task-5-external-expense-receipt-adapter-results-v1.json",
            "task-5-external-expense-receipt-adapter-fixed-manifest-v1.json",
            "task-5-full-child-expense-observer-v1.py",
            "task-5-full-child-expense-observer-preflight-v1.py",
            "task-5-full-child-expense-observer-results-v1.json",
            "task-5-full-child-expense-observer-fixed-manifest-v1.json",
        )
    }
    fixture = module(
        D / "task-5-external-expense-receipt-adapter-preflight-v1.py", "v1_fixture_only"
    )
    protocol, execution, clock, digest = fixture.actual_contracts()
    adapter = module(ADAPTER, "candidate_v2")
    old = module(OLD, "fixed_v1")
    checks = []
    raw = fixture.raw_fixture()
    phase = raw["execution_phases"][0]
    phase["covered_job_ids"] = []
    native = copy.deepcopy(phase)
    native.update(id="native-job", scope="tiny actual native job", parent_id=phase["id"])
    raw["jobs"][0]["expense"] = native
    raw["jobs"][0]["timing_events"] = native["timing_events"]
    raw["locked_plan"].update(jobs=[], required_external_expense_ids=list(fixture.IDS), history=[])
    bindings = fixture.expected(raw, digest)
    original_digest = digest(raw)
    counts = [0]

    def counted(value):
        if value is raw:
            counts[0] += 1
        return digest(value)

    def build(target, refs):
        return target.build_candidate(
            raw,
            refs,
            bindings,
            protocol=protocol,
            execution=execution,
            check_actual_clock=clock,
            payload_digest=counted,
        )

    with tempfile.TemporaryDirectory(prefix="adapter-admin-fixture-") as temp:
        base = Path(temp)
        refs = [fixture.write_receipt(base, eid, bindings) for eid in fixture.IDS]
        saved = refs[6]
        path = Path(saved["path"])
        receipt = json.loads(path.read_text())
        receipt["schema"] = "rb-f04-full-child-expense-observation-v1"
        admin = {
            "id": ADMIN_ID,
            "scope": "outer imports before sampling and post-stop provenance/copy/receipt/stdout",
            "status": "pending",
            "parent_id": None,
            "includes_children": False,
            "timing": {"wall_seconds": None, "cpu_seconds": None, "overrun_seconds": None},
        }
        receipt["administrative_unclosed_expense"] = admin
        receipt["original_bindings"] = copy.deepcopy(bindings)

        def replace(ref, content):
            p = Path(ref["path"])
            p.write_text(json.dumps(content, allow_nan=False) + "\n")
            ref["sha256"] = sha(p)

        replace(saved, receipt)
        red = {"source": {"path": str(OLD), "sha256": sha(OLD)}}
        try:
            value = build(old, refs)
            assert ADMIN_ID in [row["id"] for row in value["snapshot"]["external_expenses"]], (
                "fixed v1 erased producer administrative unknown cost"
            )
        except AssertionError:
            red.update(status="RED_expected", trace=traceback.format_exc())
        else:
            raise AssertionError("original v1 counterexample did not fail")

        value = build(adapter, refs)
        emitted = value["snapshot"]["external_expenses"]
        assert [row["id"] for row in emitted[:10]] == list(fixture.IDS)
        assert emitted[-1]["id"] == ADMIN_ID
        assert value["external_rows_complete"] is True
        row = emitted[-1]
        assert {k: v for k, v in row.items() if k != "receipt_provenance"} == admin
        assert row is not admin and row["timing"] is not admin["timing"]
        assert row["receipt_provenance"]["sha256"] == saved["sha256"]
        assert row["receipt_provenance"]["id"] == "saved_check"
        assert ADMIN_ID in value["expense_validation"]["charged_ids"]
        assert ADMIN_ID in value["expense_validation"]["unknown_ids"]
        assert value["expense_validation"]["charged_totals"] == {
            "wall_seconds": None,
            "cpu_seconds": None,
        }
        assert value["composite_lineage"]["external_expense_rows_sha256"] == digest(emitted)
        assert value["composite_lineage_is_native_payload_digest"] is False
        assert "external_expenses" not in raw and digest(raw) == original_digest
        assert value["snapshot"]["jobs"] is raw["jobs"]
        ns = {
            "protocol": protocol,
            "_check_actual_expense_clock": clock,
            "_require": fixture.actual_contracts()[2].__globals__["_require"],
        }
        fixture.functions(R / "check_pilot.py", ["check_raw_costs"], ns)
        accounting = ns["check_raw_costs"](value["snapshot"], raw["locked_plan"])
        assert accounting["missing_current_expense_ids"] == []
        assert accounting["closed"] is False
        assert accounting["current"]["charged_totals"]["wall_seconds"] is None
        assert accounting["current"]["charged_totals"]["cpu_seconds"] is None
        row["timing"]["wall_seconds"] = 99
        assert admin["timing"]["wall_seconds"] is None and digest(raw) == original_digest
        checks.append(
            "producer receipt admin retained detached; required10 complete but full costs unknown"
        )

        # The same producer's required row may remain unclosed; admin must still survive.
        incomplete = copy.deepcopy(receipt)
        incomplete["expense"]["whole_external_id_closed"] = False
        replace(saved, incomplete)
        pending = build(adapter, refs)
        assert [r["id"] for r in pending["snapshot"]["external_expenses"]][-1] == ADMIN_ID
        assert "saved_check" in pending["missing_external_expense_ids"]
        assert pending["expense_validation"]["charged_totals"]["wall_seconds"] is None
        replace(saved, receipt)
        checks.append("admin survives when producer whole required scope remains unclosed")

        def reject(label, replacements):
            restore = {
                ref["id"]: json.loads(Path(ref["path"]).read_text()) for ref, _ in replacements
            }
            try:
                for ref, content in replacements:
                    replace(ref, content)
                try:
                    build(adapter, refs)
                except ValueError as error:
                    checks.append({"reject": label, "reason": str(error)})
                else:
                    raise AssertionError(label + " accepted")
            finally:
                for ref, _ in replacements:
                    replace(ref, restore[ref["id"]])

        duplicate = json.loads(Path(refs[5]["path"]).read_text())
        duplicate["administrative_unclosed_expense"] = copy.deepcopy(admin)
        reject("duplicate supplemental ID", [(refs[5], duplicate)])
        collision = copy.deepcopy(receipt)
        collision["administrative_unclosed_expense"]["id"] = "native-job"
        reject("supplemental native expense ID collision", [(saved, collision)])
        cycle = copy.deepcopy(receipt)
        cycle["administrative_unclosed_expense"]["parent_id"] = ADMIN_ID
        reject("supplemental self-cycle", [(saved, cycle)])
        absorption = copy.deepcopy(receipt)
        absorption["administrative_unclosed_expense"]["parent_id"] = "saved_check"
        absorption["expense"]["includes_children"] = True
        reject("unknown admin cannot disappear inside inclusive parent", [(saved, absorption)])
        assert "external_expenses" not in raw and digest(raw) == original_digest
        checks.append("immutable raw; fixed10 order and original clocks/provenance unchanged")

    after = {relative: sha(W / relative) for relative in closure["files"]}
    assert after == before == closure["files"]
    assert {name: sha(D / name) for name in frozen} == frozen
    result = {
        "schema": "rb-f04-external-expense-adapter-admin-retention-pure-v2",
        "status": "PASS",
        "original_RED": red,
        "initial_v2_RED": previous_red,
        "checks": checks,
        "raw_digest_call_count": counts[0],
        "raw_digest_count_scope": "one per build invocation",
        "source82_all_original_bytes_unchanged": True,
        "fixed_v1_and_producer_files": frozen,
        "source_canonical_sha256": "75ac0db805e437af50fc101d6f82d1c9df26ff433897726b8800d107e72af29e",
        "source_native_sha256": "ef14264e5127ca5edbab5b642505fc7505589e351a8d64cba0b9387574cfb9c7",
        "financial_qualification": "unknown",
        "finance_acceptance": False,
        "root_preapproved": False,
        "execute_saved_check": False,
        "actual_finance_native_CAS_Git_operations": 0,
        "pure_probe_wall_seconds": (time.perf_counter_ns() - start) / 1e9,
        "pure_probe_cpu_seconds": (time.process_time_ns() - cpu) / 1e9,
        "end_of_measurement_receipt_write_tail_seconds": None,
    }
    RESULT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "PASS", "check_count": len(checks), "result_sha256": sha(RESULT)}))


if __name__ == "__main__":
    main()
