"""Pure candidate expense bridge; authenticates provenance, never finance or permission.

Only small JSON expense rows are detached. The original hydrated jobs/source/
plan/history remain shared read-only references; this function never rewrites
the saved raw. Its composite lineage digest is not a native payload digest.
Protocol/execution/clock/digest functions are injected from the existing private
contracts, so this preparation helper imports no financial worker.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

EXTERNAL_IDS = (
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
BINDING_KEYS = (
    "source_sha256",
    "plan_sha256",
    "input_bindings_sha256",
    "raw_snapshot_sha256",
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _finite_nonnegative(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def _read_original(ref):
    path = Path(ref["path"])
    _require(
        path.is_absolute() and path.is_file() and not path.is_symlink() and path.resolve() == path,
        "regular absolute receipt path required",
    )
    data = path.read_bytes()
    actual_sha = hashlib.sha256(data).hexdigest()
    _require(actual_sha == ref.get("sha256"), "original receipt bytes/SHA differ")
    try:
        record = json.loads(data)
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("original receipt is not closed JSON") from error
    _require(isinstance(record, dict), "receipt object required")
    return record, {"path": str(path), "sha256": actual_sha, "bytes": len(data)}


def _parent_inclusion_reason(proof, parent, child, parent_digest, child_digest, bindings):
    """Check actual child clocks and original producer scope evidence, never aliases."""
    _require(proof.get("bindings") == bindings, "parent producer original bindings differ")
    _require(
        proof.get("parent_id") == parent["id"]
        and proof.get("child_id") == child["id"]
        and proof.get("parent_expense_sha256") == parent_digest
        and proof.get("child_expense_sha256") == child_digest,
        "parent producer original expense binding differs",
    )
    kind = proof.get("kind")
    _require(kind != "actual_parent_clock_alias", "copied parent alias cannot close external ID")
    if kind not in ("same_process_child_scope", "reaped_child_scope"):
        return "actual parent producer child-scope coverage remains unknown"
    if proof.get("parent_scope") != parent["scope"] or proof.get("child_scope") != child["scope"]:
        return "actual producer scope coverage remains unknown"
    parent_domain = proof.get("parent_wall_clock_domain")
    if (
        not isinstance(parent_domain, str)
        or not parent_domain
        or parent_domain != proof.get("child_wall_clock_domain")
    ):
        return "actual wall-clock domains are missing or incomparable"
    pe, ce = parent["timing_events"], child["timing_events"]
    if not pe["wall_start_ns"] <= ce["wall_start_ns"] <= ce["wall_stop_ns"] <= pe["wall_stop_ns"]:
        return "inclusive parent actual wall does not cover child scope"
    pp, cp = proof.get("parent_pid"), proof.get("child_pid")
    if any(not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 for pid in (pp, cp)):
        return "actual producer PIDs remain unknown"
    parent_cpu_domain, child_cpu_domain = (
        proof.get("parent_cpu_clock_domain"),
        proof.get("child_cpu_clock_domain"),
    )
    if not all(
        isinstance(domain, str) and domain for domain in (parent_cpu_domain, child_cpu_domain)
    ):
        return "actual CPU clock domains remain unknown"
    if kind == "same_process_child_scope":
        if pp != cp or parent_cpu_domain != child_cpu_domain:
            return "same-process CPU producer/domain coverage is not established"
        if not pe["cpu_start_ns"] <= ce["cpu_start_ns"] <= ce["cpu_stop_ns"] <= pe["cpu_stop_ns"]:
            return "inclusive same-process actual CPU does not cover child scope"
        return None

    # Distinct process CPU endpoints have different absolute origins. Compare
    # only the child's measured duration with original parent reaped samples.
    if pp == cp or parent_cpu_domain == child_cpu_domain:
        return "distinct-process CPU domains are not established"
    samples = proof.get("clock_source_samples")
    scope = proof.get("reaped_child_scope")
    if not isinstance(samples, dict) or not isinstance(scope, dict):
        return "actual reaped-child producer samples or scope remain unknown"
    if (
        scope.get("id") != child["id"]
        or scope.get("scope") != child["scope"]
        or scope.get("pid") != cp
    ):
        return "actual reaped-child scope does not cover this expense"
    child_cpu_ns = ce["cpu_stop_ns"] - ce["cpu_start_ns"]
    scoped_cpu = scope.get("cpu_seconds")
    if not _finite_nonnegative(scoped_cpu) or not math.isclose(
        scoped_cpu, child_cpu_ns / 1e9, rel_tol=1e-12, abs_tol=1e-9
    ):
        return "actual reaped-child measured CPU scope differs"
    roster = proof.get("reaped_child_pids")
    if (
        not isinstance(roster, list)
        or cp not in roster
        or any(not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 for pid in roster)
    ):
        return "actual reaped-child PID coverage remains unknown"
    cumulative = {}
    for endpoint in ("start", "stop"):
        own = samples.get("parent_cpu_" + endpoint + "_ns")
        children = samples.get("children_cpu_" + endpoint)
        if (
            not isinstance(own, int)
            or isinstance(own, bool)
            or own < 0
            or not isinstance(children, dict)
        ):
            return "actual parent/reaped-child CPU samples remain unknown"
        total = 0
        for axis in ("utime", "stime"):
            seconds = children.get("ru_" + axis + "_seconds")
            rounded = children.get("ru_" + axis + "_ns_rounded")
            if (
                not _finite_nonnegative(seconds)
                or not isinstance(rounded, int)
                or isinstance(rounded, bool)
            ):
                return "actual RUSAGE_CHILDREN samples remain unknown"
            if rounded != round(seconds * 1e9):
                return "actual RUSAGE_CHILDREN sample conversion differs"
            total += rounded
        cumulative[endpoint] = total
        if own + total != pe["cpu_" + endpoint + "_ns"]:
            return "original parent composite CPU endpoint differs from actual samples"
    if (
        samples["parent_cpu_stop_ns"] < samples["parent_cpu_start_ns"]
        or cumulative["stop"] < cumulative["start"]
    ):
        return "actual parent/reaped-child samples are not monotonic"
    if child_cpu_ns > cumulative["stop"] - cumulative["start"]:
        return "actual reaped-child CPU does not cover the child's measured duration"
    return None


def build_candidate(
    snapshot,
    receipt_refs,
    expected_bindings,
    *,
    protocol,
    execution,
    check_actual_clock,
    payload_digest,
):
    """Return a false derived envelope; real root/native authority is not checked.

    Future receipts explicitly provide their existing expense and bindings.
    Completion requires the producer's whole_external_id_closed=True and a
    measured final_receipt_construction_write_stdout_tail_seconds; no missing
    receipt field, event or overrun is supplied by this adapter. Prefix receipts
    and historical elapsed-only records remain evidence of unclosed scope.

    Receipt refs bind id/scope/path/SHA. An actual native inclusive phase/job
    parent additionally requires parent_expense_sha256 in the original receipt.
    Original raw is digested exactly once; only small lineage/expense objects
    are subsequently digested or copied.
    """
    _require(isinstance(snapshot, dict), "hydrated original snapshot required")
    _require(
        "external_expenses" not in snapshot, "existing external_expenses must not be overwritten"
    )
    _require(
        isinstance(expected_bindings, dict) and set(expected_bindings) == set(BINDING_KEYS),
        "four original expected bindings required",
    )
    original_raw_digest = payload_digest(snapshot)
    actual_bindings = {
        "source_sha256": payload_digest(snapshot["source"]),
        "plan_sha256": payload_digest(snapshot["locked_plan"]),
        "input_bindings_sha256": payload_digest(snapshot["input_bindings"]),
        "raw_snapshot_sha256": original_raw_digest,
    }
    _require(actual_bindings == expected_bindings, "original source/plan/input/raw bindings differ")
    accepted, unclosed, provenance, seen = [], [], [], set()
    receipts_by_id = {}
    for ref in receipt_refs:
        _require(isinstance(ref, dict), "receipt reference must be an object")
        eid = ref.get("id")
        _require(eid in EXTERNAL_IDS and eid not in seen, "unknown or duplicate external ID")
        seen.add(eid)
        path = Path(ref["path"])
        _require(
            path.is_absolute()
            and path.is_file()
            and not path.is_symlink()
            and path.resolve() == path,
            "regular absolute receipt path required",
        )
        data = path.read_bytes()
        actual_sha = hashlib.sha256(data).hexdigest()
        _require(actual_sha == ref.get("sha256"), "original receipt bytes/SHA differ")
        try:
            receipt = json.loads(data)
        except (ValueError, UnicodeDecodeError) as error:
            raise ValueError("original receipt is not closed JSON") from error
        _require(isinstance(receipt, dict), "receipt object required")
        provenance.append({"id": eid, "path": str(path), "sha256": actual_sha, "bytes": len(data)})
        receipts_by_id[eid] = receipt
        provided = receipt.get("bindings")
        if provided is not None:
            _require(isinstance(provided, dict), "receipt bindings malformed")
            for key in BINDING_KEYS:
                if key in provided:
                    _require(
                        provided[key] == expected_bindings[key],
                        "receipt original source/plan/input/raw binding differs",
                    )
        reason = None
        expense = receipt.get("expense")
        if not isinstance(provided, dict) or not set(BINDING_KEYS) <= provided.keys():
            reason = "original receipt lacks source/plan/input/raw bindings"
        elif not isinstance(expense, dict):
            reason = "prefix-only or elapsed-only receipt is not a whole expense row"
        else:
            _require(
                expense.get("id") == eid and expense.get("scope") == ref.get("scope"),
                "original receipt expense ID/scope differs",
            )
            _require(
                "alias_scope" not in expense
                and "prior_alias_sha256" not in expense
                and not expense["scope"].startswith("prior inclusive execution alias:"),
                "existing inclusive execution alias cannot close an external ID",
            )
            if expense.get("whole_external_id_closed") is not True:
                reason = "producer did not close whole external scope"
            elif not _finite_nonnegative(
                expense.get("final_receipt_construction_write_stdout_tail_seconds")
            ):
                reason = "whole scope tail remains unknown"
            else:
                try:
                    # Root-only local contract validation is followed by the
                    # actual original parent forest check below. No emitted
                    # expense parent field is changed.
                    check_actual_clock(expense, expense.get("timing_events"))
                    standalone = copy.deepcopy(expense)
                    standalone["parent_id"] = None
                    execution._current_expenses([standalone], [eid])
                except (ValueError, KeyError, TypeError) as error:
                    reason = "incomplete original expense contract: " + str(error)
        if reason is not None:
            unclosed.append(
                {
                    "id": eid,
                    "receipt_path": str(path),
                    "receipt_sha256": actual_sha,
                    "reason": reason,
                    "original_expense_or_prefix": copy.deepcopy(
                        expense
                        if isinstance(expense, dict)
                        else receipt.get("measured_prefix_expense")
                    ),
                    "original_bindings": copy.deepcopy(provided),
                }
            )
            continue
        row = copy.deepcopy(expense)
        row["receipt_provenance"] = provenance[-1].copy()
        accepted.append(row)

    actual_parents = {}
    for phase in snapshot.get("execution_phases", []):
        _require(phase["id"] not in actual_parents, "duplicate native phase expense ID")
        actual_parents[phase["id"]] = (phase, phase.get("timing_events"))
    for job in snapshot.get("jobs", []):
        if "expense" in job:
            expense = job["expense"]
            _require(expense["id"] not in actual_parents, "duplicate native job/phase expense ID")
            actual_parents[expense["id"]] = (expense, job.get("timing_events"))
    accepted_by_id = {row["id"]: row for row in accepted}
    _require(
        not (set(accepted_by_id) & set(actual_parents)), "external ID collides with native expense"
    )
    native_rows = {}
    originals = {eid: receipts_by_id[eid]["expense"] for eid in accepted_by_id}
    dropped = {}

    def native_ancestors(row):
        parent_id, chain = row["parent_id"], set()
        while parent_id is not None:
            _require(parent_id not in chain, "invalid expense parent cycle")
            chain.add(parent_id)
            if parent_id in accepted_by_id:
                parent_id = accepted_by_id[parent_id]["parent_id"]
            elif parent_id in actual_parents:
                parent, events = actual_parents[parent_id]
                check_actual_clock(parent, events)
                item = copy.deepcopy(parent)
                item["timing_events"] = copy.deepcopy(events)
                native_rows[parent_id] = item
                originals[parent_id] = parent
                parent_id = item["parent_id"]
            elif parent_id in seen:
                return "original external parent expense remains unclosed"
            else:
                raise ValueError("external expense parent unavailable")
        return None

    for row in accepted:
        reason = native_ancestors(row)
        if reason:
            dropped[row["id"]] = reason
    complete_forest = [*native_rows.values(), *accepted]
    by_id = {row["id"]: row for row in complete_forest}
    # Validate original shape/cycles before dropping unknown coverage. A
    # malformed known parent graph never becomes a candidate accounting PASS.
    if not dropped:
        protocol.validate_expenses(complete_forest, required_ids=list(by_id))
    inclusion_provenance = []
    for row in accepted:
        if row["id"] in dropped:
            continue
        ancestors, parent_id = [], row["parent_id"]
        while parent_id is not None:
            parent = by_id[parent_id]
            if parent["includes_children"]:
                ancestors.append(parent)
            parent_id = parent["parent_id"]
        refs = receipts_by_id[row["id"]].get("parent_inclusion_receipts", [])
        _require(isinstance(refs, list), "parent inclusion receipt refs malformed")
        proofs = {}
        for ref in refs:
            proof, physical = _read_original(ref)
            parent_id = proof.get("parent_id")
            _require(
                parent_id not in proofs and parent_id in {p["id"] for p in ancestors},
                "duplicate or unrelated parent inclusion receipt",
            )
            proofs[parent_id] = proof
            inclusion_provenance.append({"child_id": row["id"], "parent_id": parent_id, **physical})
        for parent in ancestors:
            proof = proofs.get(parent["id"])
            if proof is None:
                dropped[row["id"]] = (
                    "actual inclusive parent producer domain/CPU evidence remains unknown"
                )
                break
            reason = _parent_inclusion_reason(
                proof,
                parent,
                row,
                payload_digest(originals[parent["id"]]),
                payload_digest(originals[row["id"]]),
                expected_bindings,
            )
            if reason:
                dropped[row["id"]] = reason
                break
    # If an external parent is unclosed, keep its descendants unclosed too.
    while True:
        additional = {
            row["id"]: "original external parent expense remains unclosed"
            for row in accepted
            if row["id"] not in dropped and row["parent_id"] in dropped
        }
        if not additional:
            break
        dropped.update(additional)
    for row in accepted:
        if row["id"] in dropped:
            receipt = receipts_by_id[row["id"]]
            ref = next(item for item in provenance if item["id"] == row["id"])
            unclosed.append(
                {
                    "id": row["id"],
                    "receipt_path": ref["path"],
                    "receipt_sha256": ref["sha256"],
                    "reason": dropped[row["id"]],
                    "original_expense_or_prefix": copy.deepcopy(receipt["expense"]),
                    "original_bindings": copy.deepcopy(receipt["bindings"]),
                }
            )
    accepted = sorted(
        (row for row in accepted if row["id"] not in dropped),
        key=lambda row: EXTERNAL_IDS.index(row["id"]),
    )
    accepted_by_id = {row["id"]: row for row in accepted}
    # Include only actual native ancestors still referenced by accepted rows;
    # their expense remains in the original snapshot, not injected a second time.
    needed = set()
    for row in accepted:
        parent_id = row["parent_id"]
        while parent_id is not None:
            if parent_id in native_rows:
                needed.add(parent_id)
            parent_id = by_id[parent_id]["parent_id"]
    native_rows = {eid: row for eid, row in native_rows.items() if eid in needed}
    complete_forest = [*native_rows.values(), *accepted]
    expense_validation = protocol.validate_expenses(
        complete_forest, required_ids=[row["id"] for row in complete_forest]
    )
    if accepted:
        execution._current_expenses(complete_forest, [row["id"] for row in accepted])
    missing = [eid for eid in EXTERNAL_IDS if eid not in accepted_by_id]
    derived = dict(snapshot)
    derived["external_expenses"] = accepted
    small_lineage = {
        "original_raw_snapshot_sha256": original_raw_digest,
        "source_plan_input_raw_bindings": actual_bindings,
        "receipt_refs": provenance,
        "parent_inclusion_receipt_refs": inclusion_provenance,
        "external_expense_rows_sha256": payload_digest(accepted),
    }
    return {
        "snapshot": derived,
        "original_raw_snapshot_sha256": original_raw_digest,
        "composite_lineage_sha256": payload_digest(small_lineage),
        "composite_lineage_is_native_payload_digest": False,
        "composite_lineage": small_lineage,
        "required_external_expense_ids": list(EXTERNAL_IDS),
        "external_accounting": [
            {
                "id": eid,
                "status": "validated_whole_row"
                if eid in accepted_by_id
                else "unclosed"
                if eid in seen
                else "missing",
            }
            for eid in EXTERNAL_IDS
        ],
        "missing_external_expense_ids": missing,
        "unclosed_receipts": unclosed,
        "authenticated_native_parent_ids": sorted(native_rows),
        "expense_validation": expense_validation,
        "external_rows_complete": not missing,
        "candidate_only": True,
        "root_preapproved": False,
        "execute_saved_check": False,
        "finance_acceptance": False,
        "all_expenses_closed": False,
        "financial_qualification": "unknown",
        "actual_terminal_and_native_physical_bytes_authenticated": False,
        "actual_root_permission_authenticated": False,
        "numerical_qualification_authenticated": False,
        "shared_original_snapshot_fields_must_remain_readonly": True,
        "scope": "receipt provenance and expense contract candidate only; no native checker, solver or permission",
    }
