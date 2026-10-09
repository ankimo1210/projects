"""Private execution-only v1.1 contract, separate from strict financial v1.

This module binds detached metadata and checker/reviewer receipts; it does not
run numerical checks, read source bytes, authenticate reviewers or draw RNG.
Callers must independently recompute raw financial semantics and the transitive
source closure. An execution freeze never certifies a price, Greek or precision
gate, and never licenses finite-only comparisons or fallback baselines.
"""

import hashlib
import json
import math
from pathlib import PurePosixPath

from . import _dynamic_hedging_protocol as _v1

_PROPOSAL = "3728b09ab65b0960a13bc54309dee13f476c606c36c6ce9b6cbcc10281ea271b"
_SCHEMA = "rb-f04-execution-freeze-v1.1"
_QUALIFICATIONS = {"qualified", "unknown", "not_qualified"}


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _snapshot(value):
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(value):
    _require(
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
        "missing evidence SHA",
    )


def _number(value):
    _require(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0,
        "measurement must be finite nonnegative",
    )


def _count(value):
    _require(
        isinstance(value, int) and not isinstance(value, bool) and value > 0,
        "missing original count",
    )


def _text(value):
    _require(isinstance(value, str) and bool(value.strip()), "missing reason/checker")


def _receipt(value, inputs):
    _require(isinstance(value, dict), "missing independent verification receipt")
    _text(value.get("checker"))
    _sha(value.get("evidence_sha256"))
    _require(value.get("inputs") == inputs, "stale or misbound verification receipt")


def _rows(values, identifiers, label):
    _require(isinstance(values, list), f"missing {label}")
    _require(
        len(values) == len(identifiers) and {r.get("id") for r in values} == set(identifiers),
        f"incomplete {label}",
    )
    return {r["id"]: r for r in values}


def execution_candidate() -> dict:
    """Return the fixed full-roster candidate; no measured success is implied."""
    original, roster = _v1.candidate_protocol(), _v1.study_roster()
    cases = []
    quotes = [(t, k, "fit") for t in (0.25, 0.5, 0.75, 1.0, 1.25) for k in (80, 90, 100, 110, 120)]
    quotes += [(t, k, "holdout") for t in (1 / 3, 2 / 3, 1.125) for k in (85, 95, 105, 115)]
    for i, (t, k, role) in enumerate(quotes):
        cases.append(
            {
                "id": f"quote{i:02d}",
                "kind": "quote",
                "identity": {"expiry": t, "strike": k, "role": role},
                "gates": ["initial_quote_error", "cf_order_cutoff_error"],
            }
        )
    dates = [0.0, 1 / 12, 0.25, 0.5, 0.75, 11 / 12]
    state_gates = [
        "call_price_error",
        "call_stock_derivative_error",
        "call_scaled_state_derivative_error",
        "quote_condition_number",
        "teacher_price_se",
        "asian_price_error",
        "stock_position_se",
        "call_position_se",
        "stock_position_error",
        "call_position_error",
    ]
    for i in range(18):
        t, scenario = dates[i // 3], i % 3
        for model in original["market"]["generators"]:
            cases.append(
                {
                    "id": f"state{i:02d}.{model}",
                    "kind": "state",
                    "identity": {
                        "state_index": i,
                        "model": model,
                        "date": t,
                        "scenario": scenario,
                        "spot": ([99.95, 100.0, 100.05] if t == 0 else [80.0, 100.0, 120.0])[
                            scenario
                        ],
                        "diagnostic_heston_variance": [0.02, 0.04, 0.08][scenario],
                    },
                    "gates": state_gates,
                }
            )
    cases += [
        {
            "id": "pilot:" + r["id"],
            "kind": "cell",
            "identity": r,
            "gates": ["pnl_rms_difference", "mse_difference", "baseline_mse"],
        }
        for r in roster["primary_cells"]
    ]
    four = [r for r in roster["fits"] if r["initialization"] == 11]
    cases += [{"id": "pilot:" + r["id"], "kind": "fit", "identity": r, "gates": []} for r in four]
    attempts = [f"teacher:{m}:date{j}" for m in ("Heston", "local") for j in range(12)]
    attempts += [
        f"refinement:{k}:{m}"
        for k in ("SDE", "teacher_N", "teacher_grid", "position", "pnl")
        for m in ("Heston", "local")
    ]
    attempts += [
        f"Q:{k}:{m}" for k in ("one_step", "empty_claim", "state_bins") for m in ("Heston", "local")
    ]
    attempts += [
        "frequency:24",
        "frequency:48",
        "initial_common_surface",
        "premium",
        "source_closure",
        "tiny_nn",
        "tiny_roster",
        "test_precision",
        "costs",
        "domain_selection",
        "saved_replay",
    ]
    attempt_gates = {}
    for identifier in attempts:
        gates = []
        if identifier.startswith("teacher:"):
            gates = ["teacher_price_se", "stock_position_se", "call_position_se"]
        elif identifier.startswith(("refinement:", "frequency:")):
            gates = ["pnl_rms_difference", "mse_difference", "baseline_mse"]
        elif identifier.startswith("Q:"):
            gates = ["call_accumulated_drift_error"]
        attempt_gates[identifier] = gates
    hull = "johnhull/hullkit/src/hullkit/"
    deep = "deep_hedge_price/src/deep_hedge_price/"
    research = "johnhull/research/RB-F04/dynamic_hedging/"
    return _snapshot(
        {
            "version": "rb-f04-execution-candidate-v1.1",
            "original_candidate": original,
            "original_roster": roster,
            "revision": {
                "proposal_sha256": _PROPOSAL,
                "readiness_separate_from_financial_qualification": True,
                "fixed_cartesian_domain_is_separate_revision": True,
                "original_v1_guard_unchanged": True,
                "no_safe_or_hold_fallback": True,
            },
            "pilot_cases": cases,
            "original_pilot_fit_ids": [r["id"] for r in four],
            "required_pilot_attempt_ids": attempts,
            "pilot_attempt_gates": attempt_gates,
            "required_source_files": [
                hull + n + ".py"
                for n in (
                    "_dynamic_hedging_core",
                    "_dynamic_hedging_conditional",
                    "_dynamic_hedging_surfaces",
                    "_dynamic_hedging_risk",
                    "_dynamic_hedging_statistics",
                    "_heston_local_surface",
                )
            ]
            + [
                deep + n + ".py"
                for n in (
                    "_dynamic_hedging_policy",
                    "_dynamic_hedging_study",
                    "_dynamic_hedging_protocol",
                    "_dynamic_hedging_execution",
                    "_dynamic_hedging_replay",
                )
            ]
            + [
                research + n + ".py"
                for n in (
                    "run_reference",
                    "reference_methods",
                    "run_fresh",
                    "check_initial_quotes",
                    "check_selected_calls",
                )
            ],
            "current_pilot_expense_ids": [
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
            ],
            "main_obligations": {
                "evaluation_slots": 396,
                "fit_slots": 12,
                "all_original_n_and_unknown": True,
                "required_outputs": [
                    "full_market_generators",
                    "full_teachers",
                    "all_training_attempts",
                    "all_validation_candidates",
                    "all_evaluation_cells",
                    "raw_original_paths",
                    "independent_premium",
                    "mandatory_Q",
                    "empty_claim",
                    "state_bins",
                    "teacher_position_pnl_refinements",
                    "same_holdings_zero_fee_counterfactual",
                    "all_costs",
                    "saved_replay",
                    "fresh",
                    "CAS_primary",
                    "CAS_mirror",
                    "three_plots",
                    "artifact_only_notebook",
                    "full_suites",
                    "final_acceptance",
                    "main_integration",
                ],
            },
        }
    )


def _candidate(candidate, source):
    _require(_digest(candidate) == _digest(execution_candidate()), "changed original candidate")
    _require(isinstance(source, dict) and bool(source), "missing source closure")
    for path, sha in source.items():
        p = PurePosixPath(path)
        _require(
            not p.is_absolute() and str(p) == path and "\\" not in path and ".." not in p.parts,
            "noncanonical source path",
        )
        _sha(sha)
    _require(set(candidate["required_source_files"]) <= set(source), "missing source dependency")


def _domains(candidate, selection, domains):
    identifiers = [f"domain:{m}:date{j}" for m in ("Heston", "local") for j in range(12)]
    rows = _rows(domains, identifiers, "fixed domains")
    for identifier, row in rows.items():
        _, model, date = identifier.split(":")
        j = int(date[4:])
        _require(
            row.get("model") == model
            and row.get("date_index") == j
            and row.get("selected_before_test") is True
            and row.get("method") == "fixed_cartesian_not_a_knot"
            and row.get("selection_rule") == "independent_pilot_fixed_box",
            "domain selection must be fixed before test",
        )
        _sha(row.get("evidence_sha256"))
        if row.get("status") == "unavailable":
            _require(row.get("indices") is None, "unavailable domain has indices")
            _text(row.get("reason"))
            continue
        _require(row.get("status") == "defined", "unclosed domain")
        high = selection["teacher_grid"][model] == "high"
        axes = {"state": 13 if high else 9, "threshold": 65 if high else 33}
        if model == "local":
            axes = {
                "spot": (5 if j == 0 else (17 if high else 9)),
                "state": 7 if high else 5,
                "threshold": 65 if high else 33,
            }
        indices = row.get("indices")
        _require(
            isinstance(indices, dict) and set(indices) == set(axes),
            "domain original node axes differ",
        )
        for axis, size in axes.items():
            interval = indices[axis]
            _require(
                isinstance(interval, list)
                and len(interval) == 2
                and all(isinstance(i, int) and not isinstance(i, bool) for i in interval)
                and 0 <= interval[0] < interval[1] <= size
                and interval[1] - interval[0] >= 4,
                "domain needs contiguous four-node axes",
            )


def _current_expenses(records, required):
    result = _v1.validate_expenses(records, required_ids=required)
    rows = {r["id"]: r for r in result["raw_records"]}
    for identifier in required:
        row = rows[identifier]
        _require(row["status"] in {"complete", "failed"}, "current expense is pending")
        _require(
            all(
                row["timing"].get(k) is not None
                for k in ("wall_seconds", "cpu_seconds", "overrun_seconds")
            ),
            "current expense measurement unavailable",
        )
    return rows


def _cap(plan, row, costs, original):
    cap, evidence = plan.get("cap"), row.get("cap_evidence")
    _require(isinstance(cap, dict) and isinstance(evidence, dict), "unplanned cap closure")
    _require(cap.get("planned_before_attempt") is True, "cap was not declared before attempt")
    _sha(cap.get("budget_review_sha256"))
    _sha(evidence.get("evidence_sha256"))
    metric = cap.get("metric")
    _require(metric in {"wall_seconds", "path_steps", "expanded_bytes"}, "unknown cap metric")
    _number(cap.get("limit"))
    _number(evidence.get("consumed"))
    _require(
        cap["limit"] > 0
        and evidence.get("metric") == metric
        and evidence.get("limit") == cap["limit"]
        and evidence["consumed"] >= cap["limit"],
        "cap has not been reached",
    )
    if metric == "wall_seconds":
        _require(
            evidence["consumed"] <= costs[row["expense_id"]]["timing"]["wall_seconds"] + 1e-8,
            "cap consumption exceeds recorded wall time",
        )
    elif metric == "path_steps":
        _require(cap["limit"] <= original["limits"]["job_path_steps"], "cap exceeds job bound")
    else:
        _require(
            cap["limit"] <= original["limits"]["chunk_uncompressed_bytes"],
            "cap exceeds chunk bound",
        )


def _measurements(gates, row, original):
    values, reasons = row.get("measurements"), row.get("unmeasured_reasons")
    _require(isinstance(values, dict) and set(values) == set(gates), "missing measured gates")
    _require(
        isinstance(reasons, dict) and set(reasons) == {k for k, v in values.items() if v is None},
        "unmeasured reasons differ",
    )
    passed = True
    for name, value in values.items():
        if value is None:
            _text(reasons[name])
            passed = False
            continue
        _number(value)
        if name == "baseline_mse":
            continue
        if name == "mse_difference":
            baseline = values.get("baseline_mse")
            if baseline is None:
                passed = False
                continue
            limit = max(
                original["gates"]["mse_difference_absolute"],
                original["gates"]["mse_difference_relative"] * baseline,
            )
        else:
            limit = original["gates"][name]
        passed &= value <= limit
    return passed


def _selection(candidate, pilot, selection):
    original = candidate["original_candidate"]
    for key in ("teacher_n", "teacher_grid"):
        _require(set(selection.get(key, {})) == {"Heston", "local"}, "missing model selection")
    for model in ("Heston", "local"):
        _require(
            selection["teacher_n"][model] in original["teacher"]["n_candidates"],
            "teacher N not an original candidate",
        )
        _require(
            selection["teacher_grid"][model] in original["teacher"]["grid_candidates"],
            "teacher grid not an original candidate",
        )
    for key in ("band_width_candidates", "baseline_rule", "checkpoint_rule"):
        _require(selection.get(key) == original["hedging"][key], "changed selection rule")
    premium = selection.get("premium", {})
    for key in ("original_n", "steps_per_year", "seed"):
        _require(premium.get(key) == original["premium"][key], "changed independent premium")
    for key in ("value", "se", "scheme_error"):
        _number(premium.get(key))
    rows = pilot.get("test_precision")
    _require(
        isinstance(rows, list)
        and [r.get("original_n") for r in rows] == original["test"]["n_candidates"],
        "missing original ordered precision projections",
    )
    qualified = []
    for row in rows:
        _sha(row.get("evidence_sha256"))
        _require(row.get("qualification") in _QUALIFICATIONS, "unclosed precision projection")
        for key in ("worst_mean_loss_se", "worst_mse_se", "baseline_mse"):
            if row.get(key) is not None:
                _number(row[key])
        if row["qualification"] == "qualified":
            _require(
                all(
                    row.get(k) is not None
                    for k in ("worst_mean_loss_se", "worst_mse_se", "baseline_mse")
                ),
                "qualified projection lacks measurements",
            )
            _require(
                row["worst_mean_loss_se"] <= original["test"]["mean_loss_se_max"]
                and row["worst_mse_se"]
                <= max(
                    original["test"]["mse_se_absolute"],
                    original["test"]["mse_se_relative"] * row["baseline_mse"],
                ),
                "precision projection is falsely qualified",
            )
            qualified.append(row["original_n"])
        else:
            _text(row.get("reason"))
    if qualified:
        _require(
            selection.get("precision_selection") == "smallest_qualified"
            and selection.get("test_n") == qualified[0],
            "use smallest qualified original N",
        )
    else:
        _require(
            selection.get("precision_selection") == "unavailable"
            and selection.get("test_n") == 32768,
            "unavailable precision requires research N32768",
        )


def _pilot(candidate, source, pilot, selection, domains):
    original = candidate["original_candidate"]
    _require(
        pilot.get("schema") == "rb-f04-execution-pilot-v1.1"
        and pilot.get("test_opened") is False
        and pilot.get("plans_locked_before_execution") is True,
        "pilot is not pretest closed",
    )
    _require(
        pilot.get("original_counts") == original["pilot"]
        and pilot.get("original_model_state_slots") == 36,
        "changed original pilot counts",
    )
    integrity = pilot.get("integrity", {})
    _require(
        all(
            integrity.get(k) is True
            for k in (
                "source_complete",
                "raw_checked",
                "original_counts_checked",
                "rng_isolation_checked",
                "history_complete",
            )
        )
        and integrity.get("unresolved_issues") == [],
        "source/integrity remains incomplete",
    )
    descriptors = {d["id"]: d for d in candidate["pilot_cases"]}
    plans = _rows(pilot.get("case_plan"), descriptors, "original case plans")
    cases = _rows(pilot.get("cases"), descriptors, "original case measurements")
    ids = candidate["required_pilot_attempt_ids"]
    attempt_plans = _rows(pilot.get("attempt_plan"), ids, "required attempt plans")
    attempts = _rows(pilot.get("attempts"), ids, "required attempt measurements")
    expense_ids = [r.get("expense_id") for r in list(plans.values()) + list(attempt_plans.values())]
    _require(
        len(set(expense_ids)) == len(expense_ids) and all(expense_ids),
        "each original attempt needs a distinct expense scope",
    )
    costs = _current_expenses(
        pilot.get("expenses"), expense_ids + candidate["current_pilot_expense_ids"]
    )
    history = pilot.get("history")
    _require(
        isinstance(history, list) and bool(history), "original unknown expense history missing"
    )
    for record in history:
        _text(record.get("id"))
        _sha(record.get("evidence_sha256"))
        _v1.validate_expenses(
            record.get("expenses"), required_ids=[r["id"] for r in record["expenses"]]
        )
    common = {
        "candidate": _digest(candidate),
        "source": _digest(source),
        "domains": _digest(domains),
    }
    qualifications = []
    for identifier, descriptor in descriptors.items():
        plan, row = plans[identifier], cases[identifier]
        _require(
            all(plan.get(k) == descriptor[k] for k in ("kind", "identity", "gates")),
            "changed original case identity",
        )
        _count(plan.get("original_n"))
        _require(row.get("original_n") == plan["original_n"], "original case N differs")
        if descriptor["kind"] == "quote":
            _require(plan["original_n"] == 1, "changed original quote count")
        elif descriptor["kind"] == "state":
            _require(
                plan["original_n"] == selection["teacher_n"][descriptor["identity"]["model"]],
                "state count differs from selected original teacher N",
            )
        _sha(row.get("evidence_sha256"))
        _require(row.get("expense_id") == plan["expense_id"], "case expense misbound")
        outcome, qualification = row.get("outcome"), row.get("financial_qualification")
        _require(
            outcome
            in {
                "within_envelope",
                "validated_structural_rejection",
                "measured_precision_failure",
                "attempt_failed_at_declared_cap",
            }
            and qualification in _QUALIFICATIONS,
            "unclosed case classification",
        )
        passed = _measurements(descriptor["gates"], row, original)
        if outcome == "within_envelope":
            _require(
                passed
                and qualification == "qualified"
                and row.get("reason") is None
                and row.get("cap_evidence") is None,
                "false within-envelope qualification",
            )
        else:
            _require(qualification != "qualified", "failed/unknown case cannot be qualified")
            _text(row.get("reason"))
            if descriptor["kind"] == "state":
                _require(
                    row.get("first_failure_date") == descriptor["identity"]["date"],
                    "first failure date does not preserve original state",
                )
            if outcome == "validated_structural_rejection":
                kind = row.get("rejection_kind")
                _require(
                    kind in {"ill_conditioned", "outside_support", "no_root", "nonunique", "bound"},
                    "solver/source failure is not a structural rejection",
                )
                if kind == "ill_conditioned":
                    value = row["measurements"].get("quote_condition_number")
                    _number(value)
                    _require(
                        value > original["gates"]["quote_condition_number"],
                        "structural condition rejection lacks measured original failure",
                    )
            elif outcome == "measured_precision_failure":
                _require(
                    not passed, "precision failure requires failed or unmeasured original gate"
                )
            elif outcome == "attempt_failed_at_declared_cap":
                _cap(plan, row, costs, original)
        qualifications.append(qualification)
        _receipt(
            row.get("verification"),
            common
            | {
                "plan": _digest(plan),
                "record": _digest({k: v for k, v in row.items() if k != "verification"}),
            },
        )
    for identifier, plan in attempt_plans.items():
        row = attempts[identifier]
        _count(plan.get("original_n"))
        _require(row.get("original_n") == plan["original_n"], "original attempt N differs")
        if identifier.startswith("teacher:"):
            model = identifier.split(":")[1]
            _require(
                plan["original_n"] == selection["teacher_n"][model],
                "teacher attempt differs from selected original N",
            )
        if identifier == "premium":
            _require(
                plan["original_n"] == original["premium"]["original_n"],
                "premium attempt original N differs",
            )
        _require(row.get("expense_id") == plan["expense_id"], "attempt expense misbound")
        _sha(row.get("evidence_sha256"))
        status, qualification = row.get("status"), row.get("financial_qualification")
        _require(
            status in {"complete", "failed_at_declared_cap", "validated_rejection"}
            and qualification in _QUALIFICATIONS,
            "required attempt remains unclosed",
        )
        passed = _measurements(candidate["pilot_attempt_gates"][identifier], row, original)
        if qualification == "qualified":
            _require(
                status == "complete" and passed and row.get("reason") is None,
                "failed/unmeasured attempt is falsely qualified",
            )
        else:
            _text(row.get("reason"))
        if status != "complete":
            _require(qualification != "qualified", "failed attempt cannot be qualified")
            if status == "failed_at_declared_cap":
                _cap(plan, row, costs, original)
            else:
                _require(
                    row.get("rejection_kind")
                    in {"ill_conditioned", "outside_support", "no_root", "nonunique", "bound"},
                    "source/solver failure cannot close required attempt",
                )
        qualifications.append(qualification)
        _receipt(
            row.get("verification"),
            common
            | {
                "plan": _digest(plan),
                "record": _digest({k: v for k, v in row.items() if k != "verification"}),
            },
        )
    _receipt(pilot.get("verification"), common | {"selection": _digest(selection)})
    financial = (
        "qualified"
        if (
            all(q == "qualified" for q in qualifications)
            and all(d["status"] == "defined" for d in domains)
            and selection["precision_selection"] == "smallest_qualified"
        )
        else "unknown"
    )
    _require(
        pilot.get("financial_qualification") == financial,
        "pilot financial qualification cannot override original failures/unknown",
    )
    return financial


def _review(candidate, source, pilot, review, selection, domains):
    _text(review.get("reviewer"))
    _require(
        review.get("scopes")
        == {"code": "approved", "math": "approved", "pilot_execution": "approved"}
        and review.get("unresolved_issues") == [],
        "independent code/math/pilot review incomplete",
    )
    for key, rows, fields in (
        ("case_decisions", pilot["cases"], ("outcome", "financial_qualification")),
        ("attempt_decisions", pilot["attempts"], ("status",)),
    ):
        decisions = _rows(review.get(key), [r["id"] for r in rows], key)
        for row in rows:
            decision = decisions[row["id"]]
            _require(
                decision.get("decision") == "approved"
                and all(decision.get(k) == row[k] for k in fields)
                and decision.get("record_sha256") == _digest(row),
                "independent per-case/attempt decision missing or misbound",
            )
    capped = [p for p in pilot["case_plan"] + pilot["attempt_plan"] if p.get("cap") is not None]
    if capped:
        decisions = _rows(
            review.get("budget_decisions"), [p["id"] for p in capped], "prior budget decisions"
        )
        for plan in capped:
            decision = decisions[plan["id"]]
            _text(decision.get("reviewer"))
            _require(
                decision.get("decision") == "approved"
                and decision.get("planned_before_attempt") is True
                and decision.get("plan_sha256")
                == _digest(
                    {k: v for k, v in plan.items() if k != "cap"}
                    | {"cap": {k: v for k, v in plan["cap"].items() if k != "budget_review_sha256"}}
                )
                and plan["cap"]["budget_review_sha256"] == _digest(decision),
                "cap lacks bound independent prior budget approval",
            )
    _receipt(
        review.get("verification"),
        {
            "candidate": _digest(candidate),
            "source": _digest(source),
            "domains": _digest(domains),
            "pilot": _digest(pilot),
            "selection": _digest(selection),
        },
    )


def freeze_execution(candidate, source, pilot, review, selection, domains) -> dict:
    """Bind complete pretest execution evidence; never waive financial v1."""
    _candidate(candidate, source)
    _selection(candidate, pilot, selection)
    _domains(candidate, selection, domains)
    financial = _pilot(candidate, source, pilot, selection, domains)
    _review(candidate, source, pilot, review, selection, domains)
    components = dict(
        candidate=candidate,
        source=source,
        pilot=pilot,
        review=review,
        selection=selection,
        domains=domains,
    )
    result = _snapshot(components)
    result.update(
        schema=_SCHEMA,
        execution_readiness="approved_for_full_roster_evaluation",
        financial_qualification=financial,
        original_v1_financial_qualification="not_claimed",
        bindings={k: _digest(v) for k, v in components.items()},
    )
    result["frozen_sha256"] = _digest(result)
    return result


def _closed_fits(candidate, fits):
    original, roster = candidate["original_candidate"], candidate["original_roster"]
    rows = _rows(fits, [r["id"] for r in roster["fits"]], "all twelve fit attempts")
    for slot in roster["fits"]:
        row = rows[slot["id"]]
        _require(
            all(row.get(k) == v for k, v in slot.items()) and row.get("attempted") is True,
            "fit original slot not attempted",
        )
        _require(
            row.get("original_n") == original["training"]["original_n"]
            and row.get("validation_original_n") == original["validation"]["original_n"]
            and row.get("requested_updates") == original["training"]["updates"],
            "fit original training/validation counts differ",
        )
        _sha(row.get("raw_fit_evidence_sha256"))
        updates = row.get("updates")
        _require(
            isinstance(updates, int)
            and not isinstance(updates, bool)
            and 0 <= updates <= original["training"]["updates"],
            "invalid completed updates",
        )
        _number(row.get("elapsed_seconds"))
        if row.get("status") == "completed":
            _require(
                updates == original["training"]["updates"]
                and row["elapsed_seconds"] <= original["training"]["cap_seconds"]
                and row.get("selection_status") == "completed"
                and row.get("checkpoint_id") == original["hedging"]["checkpoint_rule"]
                and row.get("reason") is None,
                "fit is not a completed original attempt",
            )
            _sha(row.get("weights_sha256"))
        else:
            _require(
                row.get("status") == "failed"
                and row.get("selection_status") == "failed"
                and row.get("checkpoint_id") is None,
                "unclosed fit selection",
            )
            _text(row.get("reason"))
            _require(
                row.get("failure_kind")
                in {"time_cap", "nonfinite", "unqualified_training_data", "unqualified_validation"},
                "source/solver defect cannot close fit",
            )
            if row["failure_kind"] == "time_cap":
                _require(
                    row["elapsed_seconds"] >= original["training"]["cap_seconds"],
                    "training cap not reached",
                )
            if row.get("weights_sha256") is not None:
                _sha(row["weights_sha256"])


def _closed_validation(candidate, validation):
    original = candidate["original_candidate"]
    ids = [
        f"selection:{g}:{u}"
        for g in original["market"]["generators"]
        for u in original["universes"]
    ]
    rows = _rows(validation, ids, "all four validation selections")
    widths, n = original["hedging"]["band_width_candidates"], original["validation"]["original_n"]
    candidate_ids = [
        identifier
        for model in ("Heston", "local")
        for identifier in [f"greek:{model}"] + [f"band:{model}:width{w:g}" for w in widths]
    ]
    for identifier, row in rows.items():
        _, generator, universe = identifier.split(":")
        _require(
            row.get("generator") == generator
            and row.get("universe") == universe
            and row.get("original_n") == n,
            "changed original validation slot",
        )
        candidates = _rows(row.get("candidates"), candidate_ids, "all original baseline candidates")
        valid = []
        for item in row["candidates"]:
            _require(item.get("original_n") == n, "baseline original N differs")
            if item.get("status") == "completed":
                _require(item.get("qualification") == "qualified", "completed baseline unqualified")
                _number(item.get("mse"))
                valid.append(item)
            else:
                _require(
                    item.get("status") == "failed"
                    and item.get("qualification") in {"unknown", "not_qualified"}
                    and item.get("mse") is None,
                    "failed baseline cannot rescue a score",
                )
                _text(item.get("reason"))
        _require(
            set(row.get("selected_bands", {})) == {"Heston", "local"},
            "missing original band selections",
        )
        failures = row.get("band_failures", {})
        for model in ("Heston", "local"):
            eligible = [
                candidates[f"band:{model}:width{w:g}"]
                for w in widths
                if candidates[f"band:{model}:width{w:g}"]["status"] == "completed"
            ]
            if eligible:
                selected = min(eligible, key=lambda r: r["mse"])["id"]
                _require(
                    row["selected_bands"][model] == selected and failures.get(model) is None,
                    "band selection differs from original minimum rule",
                )
            else:
                _require(row["selected_bands"][model] is None, "failed band cannot use fallback")
                _text(failures.get(model))
        if valid:
            selected = min(
                (candidates[i] for i in candidate_ids if candidates[i]["status"] == "completed"),
                key=lambda r: r["mse"],
            )["id"]
            _require(
                row.get("status") == "completed"
                and row.get("selected_baseline") == selected
                and row.get("reason") is None,
                "baseline differs from original minimum rule",
            )
        else:
            _require(
                row.get("status") == "failed" and row.get("selected_baseline") is None,
                "all failed baselines cannot use fallback",
            )
            _text(row.get("reason"))


def assert_execution_ready(frozen, candidate, source, selection_receipts) -> None:
    """Reject stale freezes or unclosed full training/validation before test RNG.

    This is an evidence-binding guard, not a raw financial checker. The runner
    must preserve every original path and leave primary support unknown whenever
    its numerical checker finds any invalid/unqualified original constituent.
    """
    _require(frozen.get("schema") == _SCHEMA, "execution schema required")
    _require(
        frozen.get("frozen_sha256")
        == _digest({k: v for k, v in frozen.items() if k != "frozen_sha256"}),
        "execution freeze mutated",
    )
    current = freeze_execution(
        candidate, source, frozen["pilot"], frozen["review"], frozen["selection"], frozen["domains"]
    )
    _require(current == frozen, "execution freeze stale or source changed")
    _require(selection_receipts.get("test_opened") is False, "test RNG already opened")
    _closed_fits(candidate, selection_receipts.get("fits"))
    _closed_validation(candidate, selection_receipts.get("validation"))
    required = [r["id"] for r in selection_receipts["fits"] + selection_receipts["validation"]]
    _current_expenses(selection_receipts.get("expenses"), [*required, "execution_freeze"])
    _receipt(
        selection_receipts.get("verification"),
        {
            "frozen": frozen["frozen_sha256"],
            "candidate": _digest(candidate),
            "source": _digest(source),
            "closure": _digest(
                {k: v for k, v in selection_receipts.items() if k != "verification"}
            ),
        },
    )
