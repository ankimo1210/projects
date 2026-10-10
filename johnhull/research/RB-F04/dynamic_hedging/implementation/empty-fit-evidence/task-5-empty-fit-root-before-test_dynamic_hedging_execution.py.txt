"""Execution-only contracts; synthetic receipts do not certify financial pilot."""

import copy
import hashlib
import importlib
import json

import pytest


def execution():
    try:
        return importlib.import_module("deep_hedge_price._dynamic_hedging_execution")
    except ModuleNotFoundError:
        pytest.fail("Separate execution-readiness schema is not implemented")


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def verification(inputs):
    return {
        "checker": "independent_unit_fixture",
        "evidence_sha256": digest(inputs),
        "inputs": inputs,
    }


def expense(identifier):
    return {
        "id": identifier,
        "scope": identifier,
        "status": "complete",
        "parent_id": None,
        "includes_children": False,
        "timing": {"wall_seconds": 0.01, "cpu_seconds": 0.01, "overrun_seconds": 0.0},
    }


def reseal(fixture):
    """Rebind fixtures so rejection tests exercise semantics, not just stale SHA."""
    c, s, p, rv, sel, ds = (
        fixture[k] for k in ("candidate", "source", "pilot", "review", "selection", "domains")
    )
    common = {"candidate": digest(c), "source": digest(s), "domains": digest(ds)}
    for collection, plan_key in [(p["cases"], "case_plan"), (p["attempts"], "attempt_plan")]:
        plan = {x["id"]: x for x in p[plan_key]}
        for row in collection:
            raw = {k: v for k, v in row.items() if k != "verification"}
            row["verification"] = verification(
                common | {"plan": digest(plan[row["id"]]), "record": digest(raw)}
            )
    p["verification"] = verification(common | {"selection": digest(sel)})
    rv["case_decisions"] = [
        {
            "id": row["id"],
            "outcome": row["outcome"],
            "financial_qualification": row["financial_qualification"],
            "record_sha256": digest(row),
            "decision": "approved",
        }
        for row in p["cases"]
    ]
    rv["attempt_decisions"] = [
        {
            "id": row["id"],
            "status": row["status"],
            "record_sha256": digest(row),
            "decision": "approved",
        }
        for row in p["attempts"]
    ]
    rv["verification"] = verification(common | {"pilot": digest(p), "selection": digest(sel)})


def execution_fixture():
    """Full synthetic metadata fixture for guard/loader tests, never real freeze."""
    e = execution()
    c = e.execution_candidate()
    original = c["original_candidate"]
    source = {name: digest(name) for name in c["required_source_files"]}
    domains = []
    selection = {
        "teacher_n": {"Heston": 4096, "local": 4096},
        "teacher_grid": {"Heston": "coarse", "local": "coarse"},
        "test_n": 32768,
        "precision_selection": "unavailable",
        "premium": {
            "value": 5.0,
            "se": 0.01,
            "scheme_error": 0.01,
            "original_n": 65536,
            "steps_per_year": 1536,
            "seed": original["premium"]["seed"],
        },
        "band_width_candidates": original["hedging"]["band_width_candidates"],
        "baseline_rule": original["hedging"]["baseline_rule"],
        "checkpoint_rule": original["hedging"]["checkpoint_rule"],
    }
    for model in original["market"]["generators"]:
        for j in range(12):
            axes = {"state": [0, 9], "threshold": [0, 33]}
            if model == "local":
                axes = {"spot": [0, 5 if j == 0 else 9], "state": [0, 5], "threshold": [0, 33]}
            domains.append(
                {
                    "id": f"domain:{model}:date{j}",
                    "model": model,
                    "date_index": j,
                    "status": "defined",
                    "method": "fixed_cartesian_not_a_knot",
                    "selection_rule": "independent_pilot_fixed_box",
                    "indices": axes,
                    "evidence_sha256": digest([model, j]),
                    "selected_before_test": True,
                }
            )
    case_plan, cases = [], []
    for descriptor in c["pilot_cases"]:
        plan = {
            **descriptor,
            "original_n": 1 if descriptor["kind"] == "quote" else 4096,
            "expense_id": "case:" + descriptor["id"],
            "cap": None,
        }
        case_plan.append(plan)
        cases.append(
            {
                "id": descriptor["id"],
                "original_n": plan["original_n"],
                "outcome": "within_envelope",
                "financial_qualification": "qualified",
                "measurements": {name: 0.0 for name in descriptor["gates"]},
                "unmeasured_reasons": {},
                "reason": None,
                "rejection_kind": None,
                "first_failure_date": None,
                "cap_evidence": None,
                "evidence_sha256": digest(["case", descriptor["id"]]),
                "expense_id": plan["expense_id"],
            }
        )
    bad = next(x for x in cases if x["id"] == "state15.Heston")
    bad.update(
        outcome="validated_structural_rejection",
        financial_qualification="unknown",
        reason="independent three-width quote condition exceeds .25",
        rejection_kind="ill_conditioned",
        first_failure_date=11 / 12,
    )
    bad["measurements"]["quote_condition_number"] = 0.8080740677660992
    attempt_plan = [
        {
            "id": x,
            "original_n": 65536 if x == "premium" else 4096,
            "expense_id": "attempt:" + x,
            "cap": None,
        }
        for x in c["required_pilot_attempt_ids"]
    ]
    attempts = [
        {
            "id": x["id"],
            "original_n": x["original_n"],
            "status": "complete",
            "reason": None,
            "expense_id": x["expense_id"],
            "cap_evidence": None,
            "evidence_sha256": digest(["attempt", x["id"]]),
            "financial_qualification": "qualified",
            "measurements": {g: 0.0 for g in c["pilot_attempt_gates"][x["id"]]},
            "unmeasured_reasons": {},
        }
        for x in attempt_plan
    ]
    ids = [x["expense_id"] for x in case_plan + attempt_plan] + c["current_pilot_expense_ids"]
    hist = expense("original_unknown_failure")
    hist.update(status="failed", reason="historic serialization failure")
    hist["timing"] = {k: None for k in hist["timing"]}
    p = {
        "schema": "rb-f04-execution-pilot-v1.1",
        "test_opened": False,
        "original_counts": original["pilot"],
        "original_model_state_slots": 36,
        "case_plan": case_plan,
        "cases": cases,
        "attempt_plan": attempt_plan,
        "attempts": attempts,
        "plans_locked_before_execution": True,
        "integrity": {
            "source_complete": True,
            "raw_checked": True,
            "original_counts_checked": True,
            "rng_isolation_checked": True,
            "history_complete": True,
            "unresolved_issues": [],
        },
        "expenses": [expense(x) for x in ids],
        "history": [
            {"id": "prior_v1_attempts", "evidence_sha256": digest("history"), "expenses": [hist]}
        ],
        "financial_qualification": "unknown",
        "test_precision": [
            {
                "original_n": n,
                "qualification": "unknown",
                "worst_mean_loss_se": 0.02,
                "worst_mse_se": 0.01,
                "baseline_mse": 0.1,
                "reason": "original baseline not qualified",
                "evidence_sha256": digest(["precision", n]),
            }
            for n in original["test"]["n_candidates"]
        ],
    }
    review = {
        "reviewer": "independent_unit_fixture_review",
        "scopes": {"code": "approved", "math": "approved", "pilot_execution": "approved"},
        "unresolved_issues": [],
        "case_decisions": [],
        "attempt_decisions": [],
    }
    f = {
        "candidate": c,
        "source": source,
        "pilot": p,
        "review": review,
        "selection": selection,
        "domains": domains,
    }
    reseal(f)
    return f


def freeze(f):
    return execution().freeze_execution(
        f["candidate"], f["source"], f["pilot"], f["review"], f["selection"], f["domains"]
    )


def closure(f, frozen):
    """All 12 fit/4 original validation closures, with no baseline rescue."""
    c = f["candidate"]
    original = c["original_candidate"]
    fits = []
    for slot in c["original_roster"]["fits"]:
        fits.append(
            {
                **slot,
                "status": "completed",
                "attempted": True,
                "original_n": 8192,
                "validation_original_n": 2048,
                "requested_updates": 512,
                "updates": 512,
                "elapsed_seconds": 1.0,
                "selection_status": "completed",
                "checkpoint_id": "last_finite_completed",
                "weights_sha256": digest(["weights", slot["id"]]),
                "raw_fit_evidence_sha256": digest(["raw", slot["id"]]),
                "reason": None,
            }
        )
    validation = []
    for g in original["market"]["generators"]:
        for u in original["universes"]:
            candidates = []
            for model in original["market"]["generators"]:
                ids = [f"greek:{model}"] + [
                    f"band:{model}:width{w:g}" for w in original["hedging"]["band_width_candidates"]
                ]
                candidates.extend(
                    {
                        "id": i,
                        "original_n": 2048,
                        "status": "failed",
                        "qualification": "unknown",
                        "mse": None,
                        "reason": "original paths unqualified",
                    }
                    for i in ids
                )
            validation.append(
                {
                    "id": f"selection:{g}:{u}",
                    "generator": g,
                    "universe": u,
                    "status": "failed",
                    "original_n": 2048,
                    "candidates": candidates,
                    "selected_bands": {"Heston": None, "local": None},
                    "selected_baseline": None,
                    "band_failures": {
                        "Heston": "all original candidates unqualified",
                        "local": "all original candidates unqualified",
                    },
                    "reason": "all original candidates failed",
                }
            )
    rc = {
        "test_opened": False,
        "fits": fits,
        "validation": validation,
        "expenses": [expense(x["id"]) for x in fits + validation] + [expense("execution_freeze")],
    }
    seal_closure(f, frozen, rc)
    return rc


def seal_closure(f, frozen, receipt):
    raw = {k: v for k, v in receipt.items() if k != "verification"}
    receipt["verification"] = verification(
        {
            "frozen": frozen["frozen_sha256"],
            "candidate": digest(f["candidate"]),
            "source": digest(f["source"]),
            "closure": digest(raw),
        }
    )


def test_candidate_preserves_exact_v1_and_full_obligations():
    e = execution()
    old = importlib.import_module("deep_hedge_price._dynamic_hedging_protocol")
    c = e.execution_candidate()
    assert c["original_candidate"] == old.candidate_protocol()
    assert c["original_roster"] == old.study_roster()
    assert len(c["pilot_cases"]) == 121
    assert c["original_pilot_fit_ids"] == [
        "fit:Heston:U1:init11",
        "fit:Heston:U2:init11",
        "fit:local:U1:init11",
        "fit:local:U2:init11",
    ]
    assert c["main_obligations"]["evaluation_slots"] == 396
    assert c["main_obligations"]["fit_slots"] == 12
    assert {
        "fresh",
        "CAS_primary",
        "CAS_mirror",
        "three_plots",
        "full_suites",
        "final_acceptance",
        "main_integration",
    } <= set(c["main_obligations"]["required_outputs"])


def test_execution_freeze_keeps_financial_rejection_unknown_and_detached():
    f = execution_fixture()
    frozen = freeze(f)
    assert frozen["schema"] == "rb-f04-execution-freeze-v1.1"
    assert frozen["execution_readiness"] == "approved_for_full_roster_evaluation"
    assert frozen["financial_qualification"] == "unknown"
    bad = next(x for x in frozen["pilot"]["cases"] if x["id"] == "state15.Heston")
    assert bad["measurements"]["quote_condition_number"] == pytest.approx(0.8080740677660992)
    assert bad["financial_qualification"] == "unknown"
    f["pilot"]["cases"][0]["measurements"]["initial_quote_error"] = 500.0
    assert frozen["pilot"]["cases"][0]["measurements"]["initial_quote_error"] == 0.0


@pytest.mark.parametrize(
    "mutation",
    [
        "threshold",
        "seed",
        "case_missing",
        "case_duplicate",
        "n_erasure",
        "measurement",
        "falsequalified",
        "solver_as_structural",
        "missing_case_review",
        "attempt_missing",
        "source_missing",
        "integrity",
        "review_scope",
        "global_flag_only",
        "current_cost_unknown",
        "history_erased",
        "domain_missing",
        "domain_short_axis",
        "precision_falsequalified",
        "research_n",
        "cap_without_plan",
    ],
)
def test_freeze_refuses_incomplete_or_falsified_rebound_metadata(mutation):
    f = execution_fixture()
    c, p, s, rv, ds = (f[k] for k in ("candidate", "pilot", "selection", "review", "domains"))
    if mutation == "threshold":
        c["original_candidate"]["gates"]["quote_condition_number"] = 1.0
    elif mutation == "seed":
        c["original_candidate"]["seeds"]["test"][0] += 1
    elif mutation == "case_missing":
        p["cases"].pop()
    elif mutation == "case_duplicate":
        p["cases"].append(copy.deepcopy(p["cases"][0]))
    elif mutation == "n_erasure":
        p["cases"][0]["original_n"] += 1
    elif mutation == "measurement":
        p["cases"][0]["measurements"].pop("initial_quote_error")
    elif mutation == "falsequalified":
        next(x for x in p["cases"] if x["id"] == "state15.Heston")["financial_qualification"] = (
            "qualified"
        )
    elif mutation == "solver_as_structural":
        next(x for x in p["cases"] if x["id"] == "state15.Heston")["rejection_kind"] = (
            "solver_failure"
        )
    elif mutation == "attempt_missing":
        p["attempts"].pop()
    elif mutation == "source_missing":
        f["source"].pop(c["required_source_files"][0])
    elif mutation == "integrity":
        p["integrity"]["raw_checked"] = False
    elif mutation == "review_scope":
        rv["scopes"]["math"] = "pending"
    elif mutation == "current_cost_unknown":
        p["expenses"][0]["timing"]["wall_seconds"] = None
    elif mutation == "history_erased":
        p["history"] = []
    elif mutation == "domain_missing":
        ds.pop()
    elif mutation == "domain_short_axis":
        ds[0]["indices"]["state"] = [0, 3]
    elif mutation == "precision_falsequalified":
        p["test_precision"][0]["qualification"] = "qualified"
    elif mutation == "research_n":
        s["test_n"] = 16384
    elif mutation == "cap_without_plan":
        p["cases"][0].update(
            outcome="attempt_failed_at_declared_cap",
            financial_qualification="unknown",
            reason="cap",
            cap_evidence={"metric": "wall_seconds", "consumed": 1.0},
        )
    reseal(f)
    if mutation == "missing_case_review":
        rv["case_decisions"].pop()
    elif mutation == "global_flag_only":
        rv["case_decisions"] = []
        rv["approved"] = True
    with pytest.raises(ValueError):
        freeze(f)


def test_smallest_qualified_test_n_uses_all_original_ordered_projections():
    f = execution_fixture()
    for row in f["pilot"]["test_precision"]:
        row.update(
            qualification="qualified", worst_mean_loss_se=0.005, worst_mse_se=0.001, reason=None
        )
    f["selection"].update(test_n=8192, precision_selection="smallest_qualified")
    reseal(f)
    assert freeze(f)["selection"]["test_n"] == 8192
    f["selection"]["test_n"] = 16384
    reseal(f)
    with pytest.raises(ValueError, match="smallest"):
        freeze(f)


def test_legacy_v1_still_rejects_unknown_execution_pilot():
    f = execution_fixture()
    old = importlib.import_module("deep_hedge_price._dynamic_hedging_protocol")
    with pytest.raises(ValueError, match="formally qualified"):
        old.freeze_contract(
            f["candidate"]["original_candidate"], f["source"], {"qualification": "unknown"}, {}, {}
        )


def test_assert_execution_ready_accepts_full_closed_failed_baselines():
    f = execution_fixture()
    frozen = freeze(f)
    rc = closure(f, frozen)
    execution().assert_execution_ready(frozen, f["candidate"], f["source"], rc)
    assert all(row["selected_baseline"] is None for row in rc["validation"])
    assert frozen["financial_qualification"] == "unknown"


@pytest.mark.parametrize(
    "mutation",
    [
        "frozen_tamper",
        "source_stale",
        "test_opened",
        "fit_erased",
        "incomplete_fit",
        "failed_fit_without_reason",
        "validation_erased",
        "candidate_erased",
        "failed_band_fallback",
        "closed_cost_unknown",
        "receipt_stale",
    ],
)
def test_assert_ready_refuses_unclosed_or_replaced_original_attempts(mutation):
    f = execution_fixture()
    frozen = freeze(f)
    rc = closure(f, frozen)
    if mutation == "frozen_tamper":
        frozen["financial_qualification"] = "qualified"
    elif mutation == "source_stale":
        f["source"][next(iter(f["source"]))] = digest("changed")
    elif mutation == "test_opened":
        rc["test_opened"] = True
    elif mutation == "fit_erased":
        rc["fits"].pop()
    elif mutation == "incomplete_fit":
        rc["fits"][0]["updates"] = 511
    elif mutation == "failed_fit_without_reason":
        rc["fits"][0].update(status="failed", selection_status="failed")
    elif mutation == "validation_erased":
        rc["validation"].pop()
    elif mutation == "candidate_erased":
        rc["validation"][0]["candidates"].pop()
    elif mutation == "failed_band_fallback":
        rc["validation"][0]["selected_bands"]["Heston"] = "band:Heston:width0"
    elif mutation == "closed_cost_unknown":
        rc["expenses"][0]["timing"]["cpu_seconds"] = None
    elif mutation == "receipt_stale":
        rc["verification"]["inputs"]["source"] = digest("wrong")
    if mutation != "receipt_stale":
        seal_closure(f, frozen, rc)
    with pytest.raises(ValueError):
        execution().assert_execution_ready(frozen, f["candidate"], f["source"], rc)


def capped_fixture():
    f = execution_fixture()
    p = f["pilot"]
    plan = next(r for r in p["attempt_plan"] if r["id"] == "refinement:teacher_N:Heston")
    row = next(r for r in p["attempts"] if r["id"] == plan["id"])
    plan["cap"] = {"metric": "wall_seconds", "limit": 0.01, "planned_before_attempt": True}
    decision = {
        "id": plan["id"],
        "reviewer": "independent_budget_fixture",
        "planned_before_attempt": True,
        "decision": "approved",
        "plan_sha256": digest(plan),
    }
    plan["cap"]["budget_review_sha256"] = digest(decision)
    f["review"]["budget_decisions"] = [decision]
    row.update(
        status="failed_at_declared_cap",
        financial_qualification="unknown",
        reason="predeclared measured cap reached",
        cap_evidence={
            "metric": "wall_seconds",
            "limit": 0.01,
            "consumed": 0.01,
            "evidence_sha256": digest("cap"),
        },
    )
    reseal(f)
    return f


def test_prior_reviewed_measured_cap_closes_attempt_without_qualification():
    f = capped_fixture()
    frozen = freeze(f)
    assert frozen["financial_qualification"] == "unknown"
    row = next(r for r in frozen["pilot"]["attempts"] if r["id"] == "refinement:teacher_N:Heston")
    assert row["status"] == "failed_at_declared_cap"
    assert row["original_n"] == 4096


@pytest.mark.parametrize(
    "mutation",
    ["approval_missing", "not_prior", "not_reached", "unrecorded_consumption", "plan_replaced"],
)
def test_cap_closure_refuses_unapproved_unreached_or_replaced_budget(mutation):
    f = capped_fixture()
    plan = next(r for r in f["pilot"]["attempt_plan"] if r["cap"])
    row = next(r for r in f["pilot"]["attempts"] if r["id"] == plan["id"])
    if mutation == "approval_missing":
        f["review"]["budget_decisions"] = []
    elif mutation == "not_prior":
        plan["cap"]["planned_before_attempt"] = False
    elif mutation == "not_reached":
        row["cap_evidence"]["consumed"] = 0.009
    elif mutation == "unrecorded_consumption":
        row["cap_evidence"]["consumed"] = 1.0
    else:
        plan["original_n"] = row["original_n"] = 16384
    reseal(f)
    with pytest.raises(ValueError):
        freeze(f)


def all_cases_qualified(f):
    row = next(r for r in f["pilot"]["cases"] if r["id"] == "state15.Heston")
    row.update(
        outcome="within_envelope",
        financial_qualification="qualified",
        reason=None,
        rejection_kind=None,
        first_failure_date=None,
    )
    row["measurements"]["quote_condition_number"] = 0.1
    for precision in f["pilot"]["test_precision"]:
        precision.update(
            qualification="qualified", worst_mean_loss_se=0.005, worst_mse_se=0.001, reason=None
        )
    f["selection"].update(test_n=8192, precision_selection="smallest_qualified")
    f["pilot"]["financial_qualification"] = "qualified"


def test_unmeasured_required_Q_gate_keeps_original_global_unknown():
    f = execution_fixture()
    all_cases_qualified(f)
    row = next(r for r in f["pilot"]["attempts"] if r["id"] == "Q:one_step:Heston")
    row.update(
        financial_qualification="unknown",
        reason="independent drift unavailable",
        measurements={"call_accumulated_drift_error": None},
        unmeasured_reasons={"call_accumulated_drift_error": "insufficient independent oracle"},
    )
    f["pilot"]["financial_qualification"] = "unknown"
    reseal(f)
    assert freeze(f)["financial_qualification"] == "unknown"
    f["pilot"]["financial_qualification"] = "qualified"
    reseal(f)
    with pytest.raises(ValueError, match="qualification"):
        freeze(f)


def test_defined_domain_is_separate_from_unknown_financial_qualification():
    f = execution_fixture()
    f["domains"][0].update(status="unavailable", indices=None, reason="no eligible finite box")
    reseal(f)
    frozen = freeze(f)
    assert frozen["domains"][0]["indices"] is None
    assert frozen["financial_qualification"] == "unknown"


def test_current_measured_zero_and_historic_unknown_remain_distinct():
    f = execution_fixture()
    f["pilot"]["expenses"][0]["timing"] = dict(
        wall_seconds=0.0, cpu_seconds=0.0, overrun_seconds=0.0
    )
    reseal(f)
    frozen = json.loads(json.dumps(freeze(f)))
    assert frozen["pilot"]["expenses"][0]["timing"]["wall_seconds"] == 0.0
    assert frozen["pilot"]["history"][0]["expenses"][0]["timing"]["wall_seconds"] is None
    execution().assert_execution_ready(frozen, f["candidate"], f["source"], closure(f, frozen))


def test_all_twelve_fit_slots_keep_measured_failed_cap_attempt():
    f = execution_fixture()
    frozen = freeze(f)
    rc = closure(f, frozen)
    row = rc["fits"][0]
    row.update(
        status="failed",
        selection_status="failed",
        updates=511,
        elapsed_seconds=300.0,
        checkpoint_id=None,
        failure_kind="time_cap",
        reason="300 second cap reached",
    )
    seal_closure(f, frozen, rc)
    execution().assert_execution_ready(frozen, f["candidate"], f["source"], rc)
    row["failure_kind"] = "source_bug"
    seal_closure(f, frozen, rc)
    with pytest.raises(ValueError, match="defect"):
        execution().assert_execution_ready(frozen, f["candidate"], f["source"], rc)


def test_completed_fit_over_cap_cannot_be_completed_family():
    f = execution_fixture()
    frozen = freeze(f)
    rc = closure(f, frozen)
    rc["fits"][0]["elapsed_seconds"] = 300.001
    seal_closure(f, frozen, rc)
    with pytest.raises(ValueError, match="completed"):
        execution().assert_execution_ready(frozen, f["candidate"], f["source"], rc)


def test_qualified_baseline_selection_uses_original_candidates_and_first_tie():
    f = execution_fixture()
    frozen = freeze(f)
    rc = closure(f, frozen)
    row = rc["validation"][0]
    for item in row["candidates"]:
        item.update(status="completed", qualification="qualified", mse=0.01, reason=None)
    row.update(
        status="completed",
        selected_baseline="greek:Heston",
        reason=None,
        selected_bands={"Heston": "band:Heston:width0", "local": "band:local:width0"},
        band_failures={"Heston": None, "local": None},
    )
    seal_closure(f, frozen, rc)
    execution().assert_execution_ready(frozen, f["candidate"], f["source"], rc)
    row["selected_baseline"] = "greek:local"
    seal_closure(f, frozen, rc)
    with pytest.raises(ValueError, match="minimum"):
        execution().assert_execution_ready(frozen, f["candidate"], f["source"], rc)


def test_precision_failure_requires_failed_or_reasoned_unmeasured_original_gate():
    f = execution_fixture()
    row = f["pilot"]["cases"][0]
    row.update(
        outcome="measured_precision_failure",
        financial_qualification="unknown",
        reason="precision failed",
    )
    reseal(f)
    with pytest.raises(ValueError, match="precision"):
        freeze(f)
    row["measurements"]["initial_quote_error"] = None
    row["unmeasured_reasons"] = {"initial_quote_error": "original quote uncertainty not measured"}
    reseal(f)
    assert freeze(f)["financial_qualification"] == "unknown"
