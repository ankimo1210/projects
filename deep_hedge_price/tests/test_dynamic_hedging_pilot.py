"""Bounded source tests; small genuine paths are not a formal pilot."""

import sys
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))
import check_pilot  # noqa: E402
import run_pilot  # noqa: E402
from hullkit._dynamic_hedging_conditional import primitive_labels, teacher_primitives  # noqa: E402
from hullkit._heston_local_surface import HestonParameters  # noqa: E402


def teacher_args():
    return {
        "model": "Heston",
        "seed": 913,
        "original_n": 32,
        "chunk_paths": 6,
        "calendar_times": np.linspace(0, 1, 25),
        "start_index": 12,
        "spot": 100.0,
        "state": 0.04,
        "thresholds": np.linspace(0, 12, 5),
    }


def test_actual_chunked_teacher_preserves_global_blocks_and_crn():
    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    args = teacher_args()
    result = run_pilot.run_teacher_job(parameters, None, **args)
    z = np.random.default_rng(args["seed"]).standard_normal((32, 24, 2))
    direct = teacher_primitives(
        "heston",
        parameters,
        z[:, 12:],
        calendar_times=args["calendar_times"][12:],
        fixing_indices=np.arange(2, 13, 2),
        spot=100,
        state=0.04,
        memory_count=6,
        compact_status=True,
    )
    labels = primitive_labels(direct, args["thresholds"], blocks=16)
    assert result["original_n"] == 32
    assert np.array_equal(result["path_ids"], np.arange(32))
    assert np.array_equal(result["cluster_ids"], np.repeat(np.arange(16), 2))
    assert np.allclose(result["labels"]["block_means"], labels["block_means"], equal_nan=True)
    assert np.allclose(result["primitives"]["b"], direct["b"], equal_nan=True)
    checked = check_pilot.check_teacher_record(result, parameters, None)
    assert checked["original_n"] == 32
    assert checked["scope"] == "saved_primitive_boundary"


def test_teacher_prefix_is_exact_shared_stream_without_global_rng():
    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    args = teacher_args()
    first = run_pilot.run_teacher_job(parameters, None, **args)
    args.update(original_n=64, chunk_paths=7)
    second = run_pilot.run_teacher_job(parameters, None, **args)
    assert np.allclose(first["primitives"]["b"], second["primitives"]["b"][:32])
    assert first["stream_identity"] == second["stream_identity"]
    assert first["global_driver_id"] != second["global_driver_id"]


@pytest.mark.parametrize("key", ["path_ids", "cluster_ids"])
def test_saved_teacher_rejects_reordering_or_chunk_block_projection(key):
    record = run_pilot.run_teacher_job(
        HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7), None, **teacher_args()
    )
    record[key] = record[key][::-1].copy()
    with pytest.raises(ValueError, match=r"path|cluster"):
        check_pilot.check_teacher_record(
            record, HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7), None
        )


def test_saved_checker_rejects_tampered_teacher_label():
    record = run_pilot.run_teacher_job(
        HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7), None, **teacher_args()
    )
    record["labels"]["f"] = record["labels"]["f"] + 1
    with pytest.raises(ValueError, match=r"mismatch"):
        check_pilot.check_teacher_record(
            record, HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7), None
        )


def test_pnl_metrics_keep_full_original_n_nan_and_zero():
    base = np.array([0.0, 1.0, 2.0, np.nan])
    refined = np.array([0.0, 1.01, 2.0, np.nan])
    result = check_pilot.paired_pnl_metrics(base, refined, original_n=4)
    assert result["original_n"] == 4 and result["invalid_count"] == 1
    assert result["pnl_rms_difference"] is None
    assert result["baseline_mse"] is None
    assert np.isnan(result["raw_difference"][-1])
    with pytest.raises(ValueError, match=r"original"):
        check_pilot.paired_pnl_metrics(base[:3], refined[:3], original_n=4)


def test_pnl_metrics_independent_hand_calculation():
    base = np.array([1.0, -1.0, 2.0, -2.0])
    refined = base + np.array([0.1, -0.1, 0.2, -0.2])
    result = check_pilot.paired_pnl_metrics(base, refined, original_n=4)
    assert result["pnl_rms_difference"] == pytest.approx(np.sqrt(0.025))
    assert result["baseline_mse"] == pytest.approx(2.5)
    assert result["mse_difference"] == pytest.approx(0.525)


def test_raw_zero_event_uncertainty_never_becomes_valid_zero_se():
    raw = {
        "samples": np.zeros((32, 3)),
        "payoff_samples": np.zeros((13, 32)),
        "width_position_samples": np.zeros((3, 32, 2)),
        "N": 32,
        "original_path_count": 32,
        "path_mask": np.ones(32, dtype=bool),
        "status": "qualified",
        "spot_bump": 0.02,
        "quote_bump": 0.0001,
    }
    result = check_pilot.check_oracle_record(raw, original_n=32)
    assert np.array_equal(result["raw_standard_errors"], np.zeros(3))
    assert result["gate_standard_errors"] == [None, None, None]
    assert result["financial_qualification"] == "unknown"


def test_q_bins_preserve_original_denominator_and_unknown_small_bin():
    record = {
        "original_n": 512,
        "increments": np.zeros((512, 3)),
        "path_ids": np.arange(512),
        "bin_ids": np.r_[np.zeros(100), np.ones(412)],
        "delta": np.array([1 / 192, 1 / 384, 1 / 768]),
        "reference_error": np.zeros(3),
    }
    result = check_pilot.check_q_record(record)
    assert result["original_n"] == 512
    assert result["bins"][0]["original_n"] == 100
    assert result["bins"][0]["qualification"] == "unknown"


def test_source_defect_is_not_cap_or_structural_closure():
    result = run_pilot.failed_job_record("job", "ValueError: solver failed", defect=True)
    assert result["status"] == "unclosed_source_or_solver_defect"
    assert result["financial_qualification"] == "unknown"
    assert result["cap_evidence"] is None


def test_missing_required_jobs_do_not_create_a_receipt():
    result = check_pilot.check_pilot_records(
        {
            "schema": "rb-f04-pilot-raw-v1",
            "jobs": [],
            "case_bindings": [],
            "attempt_bindings": [],
            "original_n": 1024,
        },
        expected_plan=None,
    )
    assert result["closed"] is False
    assert len(result["missing_cases"]) == 121
    assert len(result["missing_attempts"]) == 51
    assert result["verification"] is None


def test_split_artifact_roundtrip_nan_original_arrays_and_immutable(tmp_path):
    payload = {
        "original_n": 32,
        "raw": np.array([1.0, np.nan, 0.0]),
        "scalar": np.asarray(3),
        "status": np.array(["ready", "unknown", "failed"]),
    }
    run_pilot.write_pilot_artifact(tmp_path / "raw", payload)
    loaded, _ = run_pilot.read_pilot_artifact(tmp_path / "raw")
    assert loaded["original_n"] == 32
    assert loaded["scalar"].shape == ()
    assert np.allclose(loaded["raw"], payload["raw"], equal_nan=True)
    assert np.array_equal(loaded["status"], payload["status"])
    with pytest.raises((ValueError, FileExistsError)):
        run_pilot.write_pilot_artifact(tmp_path / "raw", payload)


def test_plan_rejects_full_roster_ladder_or_cap_reduction():
    from deep_hedge_price._dynamic_hedging_execution import execution_candidate

    candidate = execution_candidate()
    original = candidate["original_candidate"]
    plan = {
        "schema": "rb-f04-pilot-plan-v1",
        "candidate": candidate,
        "test_opened": False,
        "teacher_n_candidates": original["teacher"]["n_candidates"],
        "teacher_grid_candidates": ["coarse", "high"],
        "sde_levels": [768, 1536],
        "frequencies": [12, 24, 48],
        "seeds": original["seeds"],
        "limits": original["limits"],
        "case_plan": candidate["pilot_cases"],
        "attempt_plan": [{"id": i} for i in candidate["required_pilot_attempt_ids"]],
        "history": [{"id": "prior", "unknown_cost": None}],
        "jobs": [
            {
                "id": "teacher",
                "operation": "teacher",
                "arguments": {},
                "prediction": {
                    "path_steps": 32 * 24,
                    "expanded_bytes": 10000,
                    "rate_source": "independently_reviewed_estimate",
                },
                "budget": {
                    "planned_before_attempt": True,
                    "review_sha256": "a" * 64,
                    "wall_seconds": 10,
                },
            }
        ],
    }
    run_pilot.validate_locked_plan(plan)
    plan["teacher_n_candidates"] = [1024]
    with pytest.raises(ValueError, match=r"ladder"):
        run_pilot.validate_locked_plan(plan)


def test_oracle_bump_recomputation_rejects_tampered_greek():
    n = 32
    z = np.linspace(-1, 1, n)
    raw = {
        "N": n,
        "original_path_count": n,
        "spot_bump": 0.02,
        "quote_bump": 0.0001,
        "payoff_samples": np.empty((13, n)),
        "path_mask": np.ones(n, dtype=bool),
    }
    raw["payoff_samples"][0] = 2 + z
    for i, multiplier in enumerate([1, 0.5, 2]):
        raw["payoff_samples"][1 + 2 * i] = 2 + z + 0.02 * multiplier * (0.5 + 0.01 * z)
        raw["payoff_samples"][2 + 2 * i] = 2 + z - 0.02 * multiplier * (0.5 + 0.01 * z)
        raw["payoff_samples"][7 + 2 * i] = 2 + z + 0.0001 * multiplier * (0.1 + 0.02 * z)
        raw["payoff_samples"][8 + 2 * i] = 2 + z - 0.0001 * multiplier * (0.1 + 0.02 * z)
    raw["samples"], raw["width_position_samples"] = check_pilot._oracle_samples(
        raw["payoff_samples"], 0.02, 0.0001
    )
    result = check_pilot.check_oracle_record(raw, original_n=n)
    assert result["mean"][1] == pytest.approx(0.5)
    assert result["mean"][2] == pytest.approx(0.1)
    raw["samples"][:, 1] = 0
    with pytest.raises(ValueError, match=r"mismatch"):
        check_pilot.check_oracle_record(raw, original_n=n)


def test_checker_never_financial_rng_or_teacher_regeneration(monkeypatch):
    record = run_pilot.run_teacher_job(
        HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7), None, **teacher_args()
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("financial regeneration forbidden")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(run_pilot, "teacher_primitives", forbidden)
    checked = check_pilot.check_teacher_record(
        record, HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7), None
    )
    assert checked["original_n"] == 32


def test_teacher_wall_cap_keeps_original_unexecuted_paths_unknown():
    args = teacher_args()
    record = run_pilot.run_teacher_job(
        HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7),
        None,
        **args,
        wall_cap_seconds=1e-12,
    )
    assert record["status"] == "failed_at_declared_cap"
    assert record["original_n"] == 32
    assert np.array_equal(record["path_ids"], np.arange(32))
    assert record["unexecuted_path_count"] == 32
    assert np.all(record["path_status"] == "not_executed_at_declared_cap")
    assert record["cap_evidence"]["consumed"] >= 1e-12
    assert record["labels"] is None


def test_no_metadata_flags_can_close_defect_or_missing_financial_groups():
    from deep_hedge_price._dynamic_hedging_execution import execution_candidate

    candidate = execution_candidate()
    record = {
        "schema": "rb-f04-pilot-raw-v1",
        "jobs": [],
        "test_opened": False,
        "case_bindings": [{"id": r["id"], "jobs": ["missing"]} for r in candidate["pilot_cases"]],
        "attempt_bindings": [
            {"id": i, "jobs": ["missing"]} for i in candidate["required_pilot_attempt_ids"]
        ],
        "integrity": {"raw_checked": True},
        "financial_qualification": "qualified",
    }
    result = check_pilot.check_pilot_records(record, expected_plan=None)
    assert result["closed"] is False
    assert result["verification"] is None
    assert len(result["missing_cases"]) == 121


def test_pnl_worker_executes_both_actual_policies_and_checker_rechecks_cash():
    from deep_hedge_price import _dynamic_hedging_study as study

    # Real self-financing no-hedge rollouts; no synthetic scalar metric acceptance.
    n = 16
    dates = np.array([0.0, 1.0])
    prices = np.zeros((n, 2, 2))
    prices[:, :, 0] = 100
    prices[:, :, 1] = 5
    dataset = {
        "model": "Heston",
        "original_n": n,
        "times": dates,
        "prices": prices,
        "memory_sum": np.zeros((n, 2)),
        "memory_count": np.array([0, 12]),
        "payoff": np.linspace(0, 2, n),
        "premium": 1.0,
        "rate": 0.03,
        "cost_rates": np.array([0.0005, 0.005]),
        "path_mask": np.ones(n, dtype=bool),
    }
    kwargs = {"dataset": dataset, "risk": {}, "universe": "U1", "policy": "none"}
    baseline = study.policy_rollout(**kwargs)
    raw = run_pilot.run_paired_pnl_job(base=kwargs, refined=kwargs)
    assert np.allclose(raw["base"], baseline["discounted_pnl"])
    result = check_pilot.check_paired_pnl_record(raw)
    assert result["pnl_rms_difference"] == pytest.approx(0.0)
    raw["base"][0] += 1
    with pytest.raises(ValueError, match=r"mismatch"):
        check_pilot.check_paired_pnl_record(raw)


def test_formal_job_refuses_small_n_changed_stream_or_calendar():
    args = teacher_args()
    job = {"operation": "teacher", "prediction": {"path_steps": 32 * 24}}
    with pytest.raises(ValueError, match=r"small"):
        run_pilot._job_identity(job, args)
    args.update(original_n=1024, calendar_times=np.arange(769) / 768)
    job["prediction"]["path_steps"] = 1024 * 768
    with pytest.raises(ValueError, match=r"stream"):
        run_pilot._job_identity(job, args)


def test_actual_field_identity_does_not_accept_qualification_projection():
    from hullkit._heston_local_surface import LocalVarianceGrid

    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    field = LocalVarianceGrid(
        np.array([0.1, 1.25]), np.array([-1.0, 0.0, 1.0]), np.full((2, 3), 0.04), parameters
    )
    original = run_pilot.input_identity(field)
    changed = LocalVarianceGrid(field.times, field.z_nodes, np.full((2, 3), 0.05), parameters)
    assert run_pilot.input_identity(changed) != original


def test_teacher_expense_ledger_is_measured_and_not_double_charged():
    from deep_hedge_price._dynamic_hedging_protocol import validate_expenses

    record = run_pilot.run_teacher_job(
        HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7), None, **teacher_args()
    )
    ledger = validate_expenses(record["expenses"], required_ids=["teacher_worker"])
    assert ledger["charged_ids"] == ["teacher_worker"]
    assert len(ledger["excluded_ids"]) == len(record["chunks"])
    assert ledger["charged_totals"]["wall_seconds"] > 0


def test_original_teacher_axes_include_exact_nodes_threshold_centers_t0():
    axes = run_pilot.teacher_axes("coarse", "Heston")
    assert np.array_equal(axes["state"], [1e-5, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.5])
    for j, x in enumerate(axes["threshold"]):
        assert x[0] == pytest.approx(0)
        assert x[-1] == pytest.approx(24)
        assert x[16] == pytest.approx(12 - j)
    fine = run_pilot.teacher_axes("high", "Heston")
    assert np.array_equal(fine["state"], np.sort(np.r_[axes["state"], 0.0025, 0.0075, 0.03, 0.06]))
    local = run_pilot.teacher_axes("coarse", "local")
    assert np.array_equal(local["t0_spot"], [99.5, 99.75, 100, 100.25, 100.5])


def test_actual_current37_solver_preserves_full_receipts_and_saved_query_arithmetic():
    from hullkit._heston_local_surface import LocalVarianceGrid

    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    field = LocalVarianceGrid(
        np.array([1e-4, 1.25]), np.array([-4.0, 0.0, 4.0]), np.full((2, 3), 0.04), parameters
    )
    controls = {
        "pde_stages": [
            {"id": "space", "space_nodes": 41, "time_steps": 24, "log_half_width": 1.8},
            {"id": "time", "space_nodes": 81, "time_steps": 48, "log_half_width": 1.8},
            {"id": "domain", "space_nodes": 81, "time_steps": 48, "log_half_width": 2.4},
        ]
    }
    record = run_pilot.run_quotes_job(parameters, field, controls=controls)
    assert record["original_n"] == 37 and len(record["groups"]) == 8
    checked = check_pilot.check_quotes_record(record)
    assert checked["cf_order_cutoff_error"].shape == (37,)
    assert checked["initial_quote_error"].shape == (37,)
    assert checked["financial_qualification"] == "unknown"
    record["pde_prices"][0, 0] += 1
    with pytest.raises(ValueError, match=r"mismatch"):
        check_pilot.check_quotes_record(record)


def test_closure_semantic_boundaries_preserve_full_rosters_nan_and_inputs(tmp_path):
    raw = {
        "operation": "closure",
        "raw": {
            "inputs": {
                "train_datasets": {"Heston": {"prices": np.arange(24).reshape(3, 4, 2)}},
                "validation_risks": {"local": {"raw": np.array([0.0, np.nan])}},
            },
            "closure": {
                "training": {
                    "fits": [{"id": f"fit{i}", "weights": np.ones((9, 32))} for i in range(12)]
                },
                "nn_validation": [{"id": f"nn{i}", "loss": np.arange(16.0)} for i in range(12)],
                "baseline_validation": [
                    {"id": f"baseline{i}", "allfailed": None} for i in range(4)
                ],
            },
        },
    }
    run_pilot.write_closure_artifact(tmp_path / "closure", raw)
    restored, _ = run_pilot.read_pilot_artifact(tmp_path / "closure")
    assert len(restored["raw"]["closure"]["training"]["fits"]) == 12
    assert len(restored["raw"]["closure"]["nn_validation"]) == 12
    assert len(restored["raw"]["closure"]["baseline_validation"]) == 4
    assert np.isnan(restored["raw"]["inputs"]["validation_risks"]["local"]["raw"][1])


def test_actual_q_full_half_arrays_and_unmeasured_reference_stay_unknown():
    from hullkit._dynamic_hedging_surfaces import build_call_cache

    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    dates = np.array([0, 1 / 1536, 1 / 768, 1 / 384, 1 / 192])
    cache = build_call_cache(
        parameters,
        None,
        dates=dates,
        spot_nodes=np.geomspace(80, 120, 5),
        state_nodes=run_pilot.teacher_axes("coarse", "Heston")["state"],
        model="heston",
    )
    raw = run_pilot.run_q_job(
        parameters,
        None,
        model="Heston",
        seed=23,
        original_n=32,
        chunk_paths=7,
        call_cache=cache,
        date=0.0,
        spot=100.0,
        state=0.04,
        bin_edges=[90, 110],
    )
    checked = check_pilot.check_q_record(raw)
    assert checked["original_n"] == 32
    assert checked["whole"]["qualification"] == "unknown"
    assert np.asarray(raw["half_increments"]).shape == (32, 3)
    raw["increments"][0, 0] += 0.1
    with pytest.raises(ValueError, match=r"mismatch"):
        check_pilot.check_q_record(raw)


def test_saved_projection_counts_measured_quotes_without_promoting_zero_se():
    checked = {
        "original_n": 37,
        "initial_quote_error": np.zeros(37),
        "cf_order_cutoff_error": np.zeros(37),
    }
    raw = {"original_n": 37, "quote_ids": np.arange(37)}
    candidate = run_pilot.execution.execution_candidate()
    descriptor = candidate["pilot_cases"][0]
    row = check_pilot.project_case(descriptor, checked, raw, {"original_n": 1})
    assert row["outcome"] == "within_envelope"
    assert row["measurements"] == {"initial_quote_error": 0.0, "cf_order_cutoff_error": 0.0}
    assert row["financial_qualification"] == "qualified"
    checked["initial_quote_error"] = None
    row = check_pilot.project_case(descriptor, checked, raw, {"original_n": 1})
    assert row["outcome"] == "measured_precision_failure"
    assert row["measurements"]["initial_quote_error"] is None
    assert row["financial_qualification"] == "unknown"


def test_group_projection_cannot_close_teacher_with_a_named_pnl_result():
    candidate = run_pilot.execution.execution_candidate()
    jobs = {"j": {"operation": "paired_pnl", "status": "executed", "raw": {"original_n": 1024}}}
    checks = {"j": {"pnl_rms_difference": 0.0, "mse_difference": 0.0, "baseline_mse": 0.0}}
    with pytest.raises(ValueError, match=r"teacher"):
        check_pilot.project_attempt("teacher:Heston:date0", ["j"], jobs, checks, candidate, {})


def test_source_identity_group_never_trusts_flags():
    candidate = run_pilot.execution.execution_candidate()
    jobs = {
        "j": {
            "operation": "source",
            "status": "executed",
            "raw": {"source_complete": True, "dynamic_imports": []},
        }
    }
    with pytest.raises(ValueError, match=r"source"):
        check_pilot.project_attempt("source_closure", ["j"], jobs, {"j": {}}, candidate, {})


def test_formal_grid_identity_rejects_changed_teacher_stream_before_dispatch():
    args = {
        "model": "Heston",
        "original_n": 1024,
        "seed": 0,
        "grid": "coarse",
        "chunk_paths": 512,
        "evaluation_domains": None,
    }
    with pytest.raises(ValueError, match=r"stream"):
        run_pilot._job_identity(
            {"operation": "teacher_grid", "prediction": {"path_steps": 1024 * 768}}, args
        )


def test_saved_current_cost_ledger_keeps_unexecuted_plan_job_missing():
    from deep_hedge_price._dynamic_hedging_protocol import validate_expenses

    del validate_expenses
    snapshot = {"jobs": []}
    plan = {"jobs": [{"expense_id": "missing"}], "history": [{"id": "old"}]}
    result = check_pilot.check_raw_costs(snapshot, plan)
    assert result["missing_current_expense_ids"] == ["missing"]
    assert result["closed"] is False


def test_genuine_market_pair_cash_empty_claim_and_saved_no_financial_rng(monkeypatch):
    from hullkit._dynamic_hedging_surfaces import build_call_cache

    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    cache = build_call_cache(
        parameters,
        None,
        dates=np.arange(13) / 12,
        spot_nodes=np.geomspace(50, 200, 5),
        state_nodes=run_pilot.teacher_axes("coarse", "Heston")["state"],
        model="heston",
    )
    market = run_pilot.run_market_pair_job(
        parameters,
        None,
        model="Heston",
        seed=23,
        original_n=32,
        chunk_paths=7,
        call_cache=cache,
        premium=3.0,
        cost_rates=[0.0005, 0.005],
    )
    assert market["datasets"][0]["original_n"] == 32
    pair = run_pilot.run_paired_pnl_job(
        base={"dataset": market["datasets"][0], "risk": None, "universe": "U1", "policy": "none"},
        refined={
            "dataset": market["datasets"][1],
            "risk": None,
            "universe": "U1",
            "policy": "none",
        },
        shared_market=market,
        refinement_kind="SDE",
    )
    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **k: pytest.fail("saved financial RNG forbidden")
    )
    checked = check_pilot.check_paired_pnl_record(pair)
    assert checked["shared_CRN_checked"] is True
    assert checked["original_n"] == 32


def test_additional_exact_date_teacher_has_no_monthly_interpolation_or_local_homogeneity():
    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    case = {
        "id": "frequency24:Heston",
        "date": 1 / 24,
        "spot": 100.0,
        "state": 0.04,
        "memory_sum": 0.0,
        "memory_count": 0,
        "thresholds": np.linspace(0, 24, 5),
    }
    raw = run_pilot.run_teacher_diagnostic_job(
        parameters, None, model="Heston", original_n=32, seed=23, chunk_paths=7, cases=[case]
    )
    checked = check_pilot.check_teacher_diagnostic_record(raw, parameters, None)
    assert checked["checks"][0]["original_n"] == 32
    assert raw["rows"][0]["teacher"]["primitives"]["calendar_times"][0] == 1 / 24
    raw["rows"][0]["case"] = {**case, "date": 0.5}
    with pytest.raises(ValueError, match=r"mismatch"):
        check_pilot.check_teacher_diagnostic_record(raw, parameters, None)


def test_actual_empty_claim_cash_keeps_missing_reference_unknown():
    from hullkit._dynamic_hedging_surfaces import build_call_cache

    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    dates = np.array([0, 1 / 1536, 1 / 768, 1 / 384, 1 / 192])
    cache = build_call_cache(
        parameters,
        None,
        dates=dates,
        spot_nodes=np.geomspace(80, 120, 5),
        state_nodes=run_pilot.teacher_axes("coarse", "Heston")["state"],
        model="heston",
    )
    q = run_pilot.run_q_job(
        parameters,
        None,
        model="Heston",
        seed=23,
        original_n=32,
        chunk_paths=7,
        call_cache=cache,
        date=0.0,
        spot=100.0,
        state=0.04,
        bin_edges=[90, 110],
    )
    raw = run_pilot.run_empty_claim_job(q)
    checked = check_pilot.check_empty_claim_record(raw)
    assert checked["original_n"] == 32
    assert checked["measurements"]["call_accumulated_drift_error"] is None
    raw["rows"][0]["raw"]["discounted_pnl"][0] += 1.0
    with pytest.raises(ValueError, match=r"mismatch"):
        check_pilot.check_empty_claim_record(raw)


def test_pilot_fit_projection_refuses_main_full_twelve_even_with_pass_flags():
    candidate = run_pilot.execution.execution_candidate()
    descriptor = next(r for r in candidate["pilot_cases"] if r["kind"] == "fit")
    with pytest.raises(ValueError, match=r"full12"):
        check_pilot.project_case(
            descriptor, {"fits": []}, {"kind": "closure", "original_n": 8192}, {"original_n": 8192}
        )


def test_actual_four_tiny_nn_attempts_and_saved_weights_do_not_replace_main(monkeypatch):
    from hullkit._dynamic_hedging_surfaces import build_call_cache
    from hullkit._heston_local_surface import LocalVarianceGrid

    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    field = LocalVarianceGrid(
        np.array([1e-4, 1.25]), np.array([-4.0, 0.0, 4.0]), np.full((2, 3), 0.04), parameters
    )
    datasets = {}
    for model, surface in (("Heston", None), ("local", field)):
        states = run_pilot.teacher_axes("coarse", model)["state"]
        cache = build_call_cache(
            parameters,
            surface,
            dates=np.arange(13) / 12,
            spot_nodes=np.geomspace(50, 200, 33),
            state_nodes=states,
            model=model.lower(),
        )
        market = run_pilot.run_market_pair_job(
            parameters,
            surface,
            model=model,
            seed=23,
            original_n=16,
            chunk_paths=8,
            call_cache=cache,
            premium=3.0,
            cost_rates=[0.0005, 0.005],
        )
        datasets[model] = market["datasets"][0]
    config = dict(run_pilot.protocol.candidate_protocol()["training"])
    config.update(original_n=16, updates=1, batch_size=16, cap_seconds=30)
    raw = run_pilot.run_tiny_fits_job(
        datasets, datasets, {}, pilot_training_config=config, stream_receipts=[]
    )
    assert raw["original_fit_slots"] == 4 and len(raw["training_fits"]) == 4
    assert {r["initialization"] for r in raw["fits"]} == {11}
    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **k: pytest.fail("saved financial RNG forbidden")
    )
    checked = check_pilot.check_tiny_fits_record(raw)
    assert checked["original_fit_slots"] == 4
    assert checked["closed"] is True
    assert checked["financial_qualification"] == "unknown"
    for descriptor in run_pilot.execution.execution_candidate()["pilot_cases"]:
        if descriptor["kind"] != "fit":
            continue
        projected = check_pilot.project_case(
            descriptor, checked, raw, {"original_n": 16, "validation_original_n": 16}
        )
        receipt = projected["fit_validation"]
        assert receipt["optimizer_status"] == "completed"
        assert receipt["optimizer_complete"] is True
        assert receipt["validation_original_n"] == 16
        assert receipt["training_original_n"] == projected["original_n"]
        assert receipt["evidence_sha256"] == projected["evidence_sha256"]
        assert receipt["first_failure_date"] is None
    row = next(
        r
        for r in raw["training_fits"]
        if r["raw_fit"] is not None and r["raw_fit"]["status"] == "completed"
    )
    row["raw_fit"]["train_discounted_pnl"][0] += 1
    with pytest.raises(ValueError, match=r"mismatch"):
        check_pilot.check_tiny_fits_record(raw)


def test_teacher_solver_defect_retains_completed_prefix_and_failed_driver(monkeypatch):
    original = run_pilot.teacher_primitives
    calls = []

    def fail_second(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("independent test solver defect")
        return original(*args, **kwargs)

    monkeypatch.setattr(run_pilot, "teacher_primitives", fail_second)
    raw = run_pilot.run_teacher_job(
        HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7), None, **teacher_args()
    )
    assert raw["status"] == "unclosed_source_or_solver_defect"
    assert raw["original_n"] == 32
    assert raw["executed_path_ids"].tolist() == list(range(6))
    assert len(raw["raw_chunks"]) == 1
    assert raw["failed_driver"]["normals"].shape == (6, 24, 2)
    assert raw["labels"] is None and raw["cap_evidence"] is None


def test_actual_field_in_wrapped_saved_args_roundtrips_losslessly(tmp_path):
    from hullkit._heston_local_surface import LocalVarianceGrid

    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    field = LocalVarianceGrid(
        np.array([1e-4, 1.25]), np.array([-4.0, 0.0, 4.0]), np.full((2, 3), 0.04), parameters
    )
    packed = run_pilot.pack_inputs({"parameters": parameters, "surface": field})
    run_pilot.write_pilot_artifact(tmp_path / "inputs", packed)
    saved, _ = run_pilot.read_pilot_artifact(tmp_path / "inputs")
    restored = run_pilot.unpack_inputs(saved)
    assert run_pilot.input_identity(restored) == run_pilot.input_identity(
        {"parameters": parameters, "surface": field}
    )
    assert np.array_equal(restored["surface"].values, field.values)


def test_actual_all_path_refit_bump_uses_same_scalar_cache_and_preserves_unknowns(monkeypatch):
    bundle = run_pilot.runner.run_tiny(original_n=16, updates=0, train=False)
    raw = run_pilot.run_bump_risk_job(
        bundle["parameters"],
        bundle["datasets"]["Heston"],
        bundle["caches"],
        bundle["risks"]["Heston"],
        chunk_paths=7,
    )
    assert raw["original_n"] == 16 and raw["original_query_path_count"] == 2 * 13 * 16 * 12
    assert raw["unexecuted_query_path_count"] == 0
    assert all(len(r["queries"]) == 13 for r in raw["chunks"])
    assert raw["scope"] == "within-cache full-root/refit FD; no MC truth certification"
    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **k: pytest.fail("saved financial RNG forbidden")
    )
    checked = check_pilot.check_bump_risk_record(raw)
    assert checked["original_n"] == 16
    raw["prices"]["heston"][0, 0, 0] = 12345.0
    with pytest.raises(ValueError, match=r"mismatch"):
        check_pilot.check_bump_risk_record(raw)


def test_same_risk_position_tag_is_not_a_position_refinement():
    candidate = run_pilot.execution.execution_candidate()
    jobs = {
        "p": {
            "operation": "paired_pnl",
            "status": "executed",
            "raw": {"refinement_kind": "position", "original_n": 1024},
        },
        "m": {
            "operation": "market_pair",
            "status": "executed",
            "raw": {"kind": "market_pair", "model": "Heston", "original_n": 1024},
        },
        "o": {"operation": "oracle", "status": "executed", "raw": {"original_n": 1024}},
    }
    checks = {"p": {"shared_CRN_checked": True}, "m": {}, "o": {}}
    with pytest.raises(ValueError, match=r"all-path"):
        check_pilot.project_attempt(
            "refinement:position:Heston", ["p", "m", "o"], jobs, checks, candidate, {}
        )


def _lifecycle_source_plan(monkeypatch):
    candidate = run_pilot.execution.execution_candidate()
    original = candidate["original_candidate"]
    source = {"source_unit": "actual dispatch/cap boundary, no financial qualification"}
    monkeypatch.setattr(run_pilot, "_pilot_source", lambda root: source)
    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    inputs = {"parameters": parameters}

    def job(identifier, operation, arguments, steps=0, budget=10, **extra):
        return {
            "id": identifier,
            "operation": operation,
            "arguments": arguments,
            "original_n": 1024,
            "expense_id": identifier + ":actual",
            "prediction": {
                "path_steps": steps,
                "expanded_bytes": 20000000,
                "rate_source": "independently_reviewed_estimate",
            },
            "budget": {
                "planned_before_attempt": True,
                "review_sha256": "a" * 64,
                "wall_seconds": budget,
            },
            **extra,
        }

    parent = job(
        "teacher-cap",
        "teacher",
        {
            "parameters": {"input": "parameters"},
            "surface": None,
            "model": "Heston",
            "seed": original["seeds"]["teacher"][0],
            "original_n": 1024,
            "chunk_paths": 16,
            "calendar_times": np.arange(769) / 768,
            "start_index": 0,
            "spot": 100.0,
            "state": 0.04,
            "thresholds": np.linspace(0, 24, 33),
        },
        steps=1024 * 768,
        budget=1e-12,
    )
    parent["cap_scope"] = {
        "job_ids": ["teacher-cap", "dependent"],
        "case_ids": [],
        "attempt_ids": [candidate["required_pilot_attempt_ids"][0]],
        "expense_id": parent["expense_id"],
    }
    return inputs, {
        "schema": "rb-f04-pilot-plan-v1",
        "candidate": candidate,
        "test_opened": False,
        "teacher_n_candidates": original["teacher"]["n_candidates"],
        "teacher_grid_candidates": original["teacher"]["grid_candidates"],
        "sde_levels": [768, 1536],
        "frequencies": [12, 24, 48],
        "seeds": original["seeds"],
        "limits": original["limits"],
        "case_plan": candidate["pilot_cases"],
        "attempt_plan": [{"id": i} for i in candidate["required_pilot_attempt_ids"]],
        "history": [{"id": "unit_only_not_formal_budget", "unknown_cost": None}],
        "source": source,
        "input_bindings": {k: run_pilot.input_identity(v) for k, v in inputs.items()},
        "jobs": [
            parent,
            job("dependent", "asian_cache", {"rows": {"job": "teacher-cap", "path": ["labels"]}}),
            job("independent", "source", {}),
        ],
        "case_bindings": [],
        "attempt_bindings": [],
    }


def test_actual_cap_continues_independent_jobs_and_keeps_dependency_unexecuted(
    tmp_path, monkeypatch
):
    inputs, plan = _lifecycle_source_plan(monkeypatch)
    raw = run_pilot.run_pilot(tmp_path / "pilot", inputs=inputs, locked_plan=plan)
    jobs = {r["id"]: r for r in raw["jobs"]}
    assert jobs["teacher-cap"]["status"] == "failed_at_declared_cap"
    assert jobs["independent"]["status"] == "executed"
    row = jobs["dependent"]
    assert row["status"] == "unexecuted_dependency_cap"
    assert row["cap_evidence"] is None and row["raw"]["executed_n"] == 0
    assert row["raw"]["original_n"] == 1024
    assert row["raw"]["parent_cap_job_ids"] == ["teacher-cap"]
    assert row["expense"]["timing"]["wall_seconds"] < 10
    checked = check_pilot.check_dependency_cap_job(row, plan["jobs"][1], plan, jobs)
    assert checked["executed_n"] == 0 and checked["cap_scope_parent_ids"] == ["teacher-cap"]
    # Resealing metadata cannot broaden a prior parent cap scope.
    row["raw"]["parent_cap_bindings"][0]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match=r"parent cap binding"):
        check_pilot.check_dependency_cap_job(row, plan["jobs"][1], plan, jobs)


def test_cap_resume_does_not_reexecute_or_overwrite_capped_job(tmp_path, monkeypatch):
    inputs, plan = _lifecycle_source_plan(monkeypatch)
    write = run_pilot.write_pilot_artifact

    def interrupt_before_dependent(path, raw, **kwargs):
        if Path(path).name == "dependent":
            raise OSError("source-unit simulated interruption after immutable parent")
        return write(path, raw, **kwargs)

    monkeypatch.setattr(run_pilot, "write_pilot_artifact", interrupt_before_dependent)
    with pytest.raises(OSError, match=r"simulated"):
        run_pilot.run_pilot(tmp_path / "pilot", inputs=inputs, locked_plan=plan)
    parent, _ = run_pilot.read_pilot_artifact(tmp_path / "pilot/jobs/teacher-cap")
    parent_hash = run_pilot.runner.payload_digest(parent)
    monkeypatch.setattr(run_pilot, "write_pilot_artifact", write)
    monkeypatch.setattr(
        run_pilot, "run_teacher_job", lambda *a, **k: pytest.fail("immutable cap rerun")
    )
    raw = run_pilot.run_pilot(tmp_path / "pilot", inputs=inputs, locked_plan=plan, resume=True)
    assert [r["status"] for r in raw["jobs"]] == [
        "failed_at_declared_cap",
        "unexecuted_dependency_cap",
        "executed",
    ]
    unchanged, _ = run_pilot.read_pilot_artifact(tmp_path / "pilot/jobs/teacher-cap")
    assert run_pilot.runner.payload_digest(unchanged) == parent_hash


def test_solver_defect_still_stops_lifecycle_without_cap_closure(tmp_path, monkeypatch):
    inputs, plan = _lifecycle_source_plan(monkeypatch)
    plan["jobs"][0]["operation"] = "invalid-source-operation"
    plan["jobs"][0]["prediction"]["path_steps"] = 0
    raw = run_pilot.run_pilot(tmp_path / "pilot", inputs=inputs, locked_plan=plan)
    assert len(raw["jobs"]) == 1
    assert raw["jobs"][0]["status"] == "unclosed_source_or_solver_defect"
    assert raw["jobs"][0]["cap_evidence"] is None


def test_parent_cap_scope_must_include_only_actual_descendants(monkeypatch):
    _, plan = _lifecycle_source_plan(monkeypatch)
    plan["jobs"][0]["cap_scope"]["job_ids"].append("independent")
    with pytest.raises(ValueError, match=r"descendant"):
        run_pilot.validate_locked_plan(plan)


def test_small_raw_arrays_pack_losslessly_without_one_file_per_query(tmp_path):
    raw = {
        "queries": [
            {"roots": np.array([0.04]), "extrema": np.array([0.0, 1.0]), "blocks": np.arange(16.0)}
            for _ in range(400)
        ],
        "empty": np.zeros((0, 3)),
        "scalar": np.array(7),
    }
    run_pilot.write_pilot_artifact(tmp_path / "packed", raw)
    loaded, _ = run_pilot.read_pilot_artifact(tmp_path / "packed")
    run_pilot.runner._same(raw, loaded, "original packed raw")
    assert len([p for p in (tmp_path / "packed").iterdir() if p.is_dir()]) == 1
    assert loaded["empty"].shape == (0, 3) and loaded["scalar"].shape == ()


def test_two_independent_measured_caps_close_only_their_explicit_scope_union(tmp_path, monkeypatch):
    import copy

    inputs, plan = _lifecycle_source_plan(monkeypatch)
    first = plan["jobs"][0]
    second = copy.deepcopy(first)
    second.update(id="teacher-cap2", expense_id="teacher-cap2:actual")
    aid = "refinement:teacher_N:Heston"
    first["cap_scope"].update(job_ids=["teacher-cap"], attempt_ids=[aid])
    second["cap_scope"] = {
        "job_ids": ["teacher-cap2"],
        "case_ids": [],
        "attempt_ids": [aid],
        "expense_id": second["expense_id"],
    }
    plan["jobs"] = [first, second, plan["jobs"][2]]
    plan["attempt_bindings"] = [{"id": aid, "job_ids": ["teacher-cap", "teacher-cap2"]}]
    raw = run_pilot.run_pilot(tmp_path / "two", inputs=inputs, locked_plan=plan)
    checked = check_pilot.check_pilot_records(raw, expected_plan=plan, context={"inputs": inputs})
    row = next(r for r in checked["attempt_results"] if r["id"] == aid)
    assert row["financial_qualification"] == "unknown"
    assert row["cap_parent_job_ids"] == ["teacher-cap", "teacher-cap2"]
    assert len(row["parent_cap_bindings"]) == 2
    assert all(
        b["cap_evidence"]["consumed"] >= b["cap_evidence"]["limit"]
        for b in row["parent_cap_bindings"]
    )
    # An unrelated, genuinely unexecuted required job cannot hide in that union.
    raw["attempt_bindings"][0]["job_ids"].append("never-executed")
    with pytest.raises(ValueError, match=r"prior original attempt bindings"):
        check_pilot.check_pilot_records(raw, expected_plan=plan, context={"inputs": inputs})


def test_actual_paired_cell_keeps_all_failed_band_none_and_full_original_n(monkeypatch):
    bundle = run_pilot.runner.run_tiny(original_n=16, updates=0, train=False)
    data = bundle["datasets"]["Heston"]
    risk = bundle["risks"]["Heston"]
    validation = run_pilot.study.select_validation(
        data,
        risk,
        generator="Heston",
        universe="U1",
        widths=run_pilot.protocol.candidate_protocol()["hedging"]["band_width_candidates"],
    )
    assert validation["selected_bands"]["Heston"] is None
    identity = next(
        r["identity"]
        for r in run_pilot.execution.execution_candidate()["pilot_cases"]
        if r["kind"] == "cell"
        and r["identity"]["generator"] == "Heston"
        and r["identity"]["universe"] == "U1"
        and r["identity"]["policy"] == "band"
        and r["identity"]["valuation"] == "Heston"
    )
    raw = run_pilot.run_cell_pair_job(
        base_dataset=data,
        refined_dataset=data,
        base_risk=risk,
        refined_risk=risk,
        identity=identity,
        validation=validation,
        fits=[],
        refinement_kind="pnl",
    )
    assert raw["base_arguments"]["width"] is None
    assert np.isnan(raw["base"]).all() and raw["original_n"] == 16
    assert "original width" in raw["base_rollout"]["reason"]
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("checker RNG"))
    checked = check_pilot.check_paired_pnl_record(raw)
    assert checked["pnl_rms_difference"] is None
    raw["base_arguments"]["width"] = 0.0
    with pytest.raises(ValueError, match=r"selection"):
        check_pilot.check_paired_pnl_record(raw)


def test_genuine_precision_worker_preserves_all48_cells_unknown_and_saved_no_rng(monkeypatch):
    bundle = run_pilot.runner.run_tiny(original_n=16, updates=0, train=False)
    data = bundle["datasets"]
    risk = bundle["risks"]
    selections = {}
    for model in ("Heston", "local"):
        for universe in ("U1", "U2"):
            selections[model + ":" + universe] = run_pilot.study.select_validation(
                data[model],
                risk[model],
                generator=model,
                universe=universe,
                widths=run_pilot.protocol.candidate_protocol()["hedging"]["band_width_candidates"],
            )
    raw = run_pilot.run_precision_job(
        datasets={m: [d, d, d] for m, d in data.items()},
        risks={m: [r, r, r] for m, r in risk.items()},
        validation=selections,
        stream_receipts=[],
        original_n=16,
    )
    assert len(raw["planned_cells"]) == len(raw["rows"]) == 48
    assert raw["unexecuted_cell_count"] == 0
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("checker RNG"))
    checked = check_pilot.check_precision_record(raw)
    assert checked["financial_qualification"] == "unknown"
    assert checked["worst_mean_loss_se"] is None
    assert all(r["original_n"] == 16 for r in checked["rows"])


def test_precision_group_without_qualified_original_measurements_is_explicitly_unavailable():
    candidate = run_pilot.execution.execution_candidate()
    jobs = {
        f"N{n}": {"operation": "precision", "status": "executed", "raw": {"original_n": n}}
        for n in (8192, 16384, 32768)
    }
    checks = {
        key: {"financial_qualification": "unknown", "original_n": row["raw"]["original_n"]}
        for key, row in jobs.items()
    }
    result = check_pilot.project_attempt("test_precision", list(jobs), jobs, checks, candidate, {})
    assert result["financial_qualification"] == "unknown"
    assert result["selected_test_n"] is None and result["unavailable_at_original_n"] == 32768


def test_shared_teacher_driver_is_saved_once_and_replays_full_sde_without_rng(
    tmp_path, monkeypatch
):
    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    args = teacher_args()
    driver = run_pilot.run_teacher_driver_job(
        seed=args["seed"],
        original_n=32,
        chunk_paths=args["chunk_paths"],
        calendar_times=args["calendar_times"],
        work_directory=tmp_path / "driver",
    )
    expected = np.random.default_rng(args["seed"]).standard_normal((32, 24, 2))
    chunks = list(run_pilot.read_teacher_driver_chunks(driver))
    assert np.array_equal(np.concatenate([r["normal"] for r in chunks]), expected)
    first = run_pilot.run_teacher_job(parameters, None, **args, driver=driver)
    args["state"] = 0.08
    second = run_pilot.run_teacher_job(parameters, None, **args, driver=driver)
    assert first["driver"] == second["driver"]
    assert first["global_driver_id"] == driver["global_driver_id"]
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved RNG"))
    check = check_pilot.check_teacher_record(first, parameters, None)
    assert check["full_saved_driver_sde_replayed"] is True
    first["primitives"]["last_left_spot"][0] += 1
    with pytest.raises(ValueError, match=r"SDE|primitive"):
        check_pilot.check_teacher_record(first, parameters, None)


def test_saved_driver_sde_replay_uses_restored_container_without_original_path(
    tmp_path, monkeypatch
):
    import shutil

    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    original = tmp_path / "original"
    restored = tmp_path / "restored"
    args = teacher_args()
    driver = run_pilot.run_teacher_driver_job(
        seed=args["seed"],
        original_n=32,
        chunk_paths=args["chunk_paths"],
        calendar_times=args["calendar_times"],
        work_directory=original / "driver",
    )
    raw = run_pilot.run_teacher_job(parameters, None, **args, driver=driver)
    shutil.copytree(original, restored)
    original.rename(tmp_path / "original-retained-unavailable")
    context = {"original_root": str(original), "restored_root": str(restored)}
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved RNG"))
    result = check_pilot.check_teacher_record(raw, parameters, None, artifact_context=context)
    assert result["full_saved_driver_sde_replayed"] is True
    assert not original.exists()


def test_additional_exact_date_teacher_reuses_saved_driver_and_checker_without_rng(
    tmp_path, monkeypatch
):
    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    driver = run_pilot.run_teacher_driver_job(
        seed=913,
        original_n=16,
        chunk_paths=7,
        calendar_times=np.arange(769) / 768,
        work_directory=tmp_path / "driver",
    )
    cases = [
        {
            "id": "exact24",
            "date": 1 / 24,
            "spot": 100.0,
            "state": 0.04,
            "memory_sum": 0.0,
            "memory_count": 0,
            "thresholds": np.linspace(0, 24, 5),
        }
    ]
    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **k: pytest.fail("shared driver regenerated")
    )
    raw = run_pilot.run_teacher_diagnostic_job(
        parameters,
        None,
        model="Heston",
        original_n=16,
        seed=913,
        chunk_paths=7,
        cases=cases,
        driver=driver,
    )
    assert raw["rows"][0]["teacher"]["driver"] is driver
    checked = check_pilot.check_teacher_diagnostic_record(raw, parameters, None)
    assert checked["checks"][0]["full_saved_driver_sde_replayed"] is True


def test_resolved_dependency_binding_rejects_dropped_teacher_driver(tmp_path):
    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    args = teacher_args()
    driver = run_pilot.run_teacher_driver_job(
        seed=args["seed"],
        original_n=32,
        chunk_paths=args["chunk_paths"],
        calendar_times=args["calendar_times"],
        work_directory=tmp_path / "driver",
    )
    raw = run_pilot.run_teacher_job(parameters, None, **args, driver=driver)
    planned = {
        "id": "node",
        "operation": "teacher",
        "arguments": {
            "parameters": {"input": "parameters"},
            "surface": None,
            **args,
            "driver": {"job": "shared"},
        },
        "budget": {"wall_seconds": 100.0},
    }
    jobs = {"shared": {"raw": driver}}
    inputs = {"parameters": parameters}
    arguments = run_pilot._resolve(planned["arguments"], inputs, jobs)
    arguments["wall_cap_seconds"] = 100.0
    row = {"raw": raw, "resolved_arguments_sha256": run_pilot.input_identity(arguments)}
    check_pilot.check_resolved_job_arguments(
        row, planned, inputs=inputs, jobs=jobs, artifact_directory=str(tmp_path)
    )
    raw["driver"] = None
    with pytest.raises(ValueError, match=r"driver"):
        check_pilot.check_resolved_job_arguments(
            row, planned, inputs=inputs, jobs=jobs, artifact_directory=str(tmp_path)
        )


def test_local_shared_driver_replays_all_sde_primitives_without_rng(tmp_path, monkeypatch):
    from hullkit._heston_local_surface import LocalVarianceGrid

    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    field = LocalVarianceGrid(
        np.array([0.01, 1.25]), np.array([-2.0, 0.0, 2.0]), np.full((2, 3), 0.04), parameters
    )
    args = teacher_args()
    args.update(model="local", state=1.0)
    driver = run_pilot.run_teacher_driver_job(
        seed=args["seed"],
        original_n=32,
        chunk_paths=args["chunk_paths"],
        calendar_times=args["calendar_times"],
        work_directory=tmp_path / "driver",
    )
    raw = run_pilot.run_teacher_job(parameters, field, **args, driver=driver)
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("checker RNG"))
    checked = check_pilot.check_teacher_record(raw, parameters, field)
    assert checked["full_saved_driver_sde_replayed"] is True


def test_paired_unknown_cell_still_binds_original_selection_identity():
    import copy

    bundle = run_pilot.runner.run_tiny(original_n=16, updates=0, train=False)
    data = bundle["datasets"]["Heston"]
    risk = bundle["risks"]["Heston"]
    validation = run_pilot.study.select_validation(
        data,
        risk,
        generator="Heston",
        universe="U1",
        widths=run_pilot.protocol.candidate_protocol()["hedging"]["band_width_candidates"],
    )
    identity = next(
        r
        for r in run_pilot.protocol.study_roster()["primary_cells"]
        if r["generator"] == "Heston"
        and r["universe"] == "U1"
        and r["policy"] == "band"
        and r["valuation"] == "Heston"
    )
    raw = run_pilot.run_cell_pair_job(
        base_dataset=data,
        refined_dataset=data,
        base_risk=risk,
        refined_risk=risk,
        identity=identity,
        validation=validation,
        fits=[],
        refinement_kind="pnl",
    )
    altered = copy.deepcopy(raw)
    altered["selection_inputs"]["identity"]["valuation"] = "local"
    with pytest.raises(ValueError, match=r"identity|selection"):
        check_pilot.check_paired_pnl_record(altered)


def test_outer_cap_keeps_and_checks_full_completed_teacher_raw(tmp_path, monkeypatch):
    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    args = teacher_args()
    driver = run_pilot.run_teacher_driver_job(
        seed=args["seed"],
        original_n=32,
        chunk_paths=args["chunk_paths"],
        calendar_times=args["calendar_times"],
        work_directory=tmp_path / "driver",
    )
    raw = run_pilot.run_teacher_job(parameters, None, **args, driver=driver)
    row = {"operation": "teacher", "raw": raw, "argument_manifest": {"original_n": 32}}
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved RNG"))
    checked = check_pilot.check_capped_job_raw(
        row, context={"parameters": parameters, "surface": None}
    )
    assert checked["original_n"] == 32 and checked["executed_n"] == 32
    assert checked["financial_qualification"] == "unknown"
    assert raw["labels"] is not None and raw.get("status") is None


def test_saved_nonconverged_independent_call_table_keeps_raw_estimates_unknown(monkeypatch):
    import reference_methods

    parameters = {
        "spot": 100.0,
        "rate": 0.03,
        "dividend_yield": 0.0,
        "v0": 0.04,
        "kappa": 2.0,
        "theta": 0.04,
        "xi": 0.3,
        "rho": -0.7,
    }
    table = reference_methods.independent_call_table(
        parameters,
        None,
        model="heston",
        dates=[11 / 12],
        query_spots=[80.0],
        state_nodes=[1e-5, 0.01, 0.04, 0.5],
        controls={"upper": 250.0, "quadrature_limit": 1},
    )
    assert np.isnan(table["prices"]).any()
    assert any(np.isfinite(r["raw_prices"]).all() for r in table["integration_receipts"])
    monkeypatch.setattr(
        reference_methods,
        "independent_heston_call",
        lambda *a, **k: pytest.fail("saved table solver rerun"),
    )
    actual = check_pilot.check_call_table(table)
    assert np.array_equal(actual, table["prices"], equal_nan=True)
    failed = next(r for r in table["integration_receipts"] if r["status"] == "unknown")
    failed["price"] = failed["raw_prices"].copy()
    with pytest.raises(ValueError, match=r"nonconvergence"):
        check_pilot.check_call_table(table)


def test_frequency_cache_view_keeps_monthly_raw_and_unknown_extra_dates_without_interpolation():
    from hullkit._dynamic_hedging_surfaces import evaluate_asian

    bundle = run_pilot.runner.run_tiny(original_n=16, updates=0, train=False)
    dates = np.arange(24) / 24
    raw = run_pilot.run_frequency_cache_job(caches=bundle["caches"], dates=dates)
    for model in ("heston", "local"):
        original = bundle["caches"][model]["asian"]
        view = raw["value"][model]["asian"]
        assert np.array_equal(view["dates"], dates)
        assert view["original_N"] == original["original_N"]
        assert np.array_equal(view["f"][::2], original["f"], equal_nan=True)
        assert np.isnan(view["f"][1::2]).all()
        assert view["missing_exact_date_mask"][1::2].all()
        if view.get("evaluation_domains") is not None:
            assert all(view["evaluation_domains"][i] is None for i in range(1, 24, 2))
        known = evaluate_asian(original, 0, 100.0, 0.04 if model == "heston" else 1.0, 0.0, 0)
        same = evaluate_asian(view, 0, 100.0, 0.04 if model == "heston" else 1.0, 0.0, 0)
        run_pilot.runner._same(known, same, "same original monthly operator")
        extra = evaluate_asian(view, 1, 100.0, 0.04 if model == "heston" else 1.0, 0.0, 0)
        assert extra["status"] == "unknown" and extra["reason"] in (
            "no_evaluation_domain",
            "nonfinite_nodes",
        )
    checked = check_pilot.check_frequency_cache_record(raw)
    assert checked["financial_qualification"] == "unknown"


def test_chunked_quote_risk_keeps_kind_value_and_saved_only_original_paths(monkeypatch):
    bundle = run_pilot.runner.run_tiny(original_n=16, updates=0, train=False)
    field = run_pilot.LocalVarianceGrid(
        np.array([1e-4, 1.25]),
        np.array([-4.0, 0.0, 4.0]),
        np.full((2, 3), 0.04),
        bundle["parameters"],
    )
    raw = run_pilot.run_quote_risk_job(
        bundle["parameters"], field, bundle["datasets"]["Heston"], bundle["caches"], chunk_paths=7
    )
    assert raw["kind"] == "quote_risk" and raw["original_n"] == 16
    assert raw["chunked_worker"]["processed_n"] == 16
    assert np.array_equal(raw["chunked_worker"]["path_ids"], np.arange(16))
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved RNG"))
    checked = check_pilot.check_wrapped_operation(raw, "quote_risk", {})
    assert checked["original_n"] == 16


def test_all_three_bump_variants_have_actual_cell_rollouts_and_saved_source_binding(monkeypatch):
    bundle = run_pilot.runner.run_tiny(original_n=16, updates=0, train=False)
    data = bundle["datasets"]["Heston"]
    risk = bundle["risks"]["Heston"]
    bump = run_pilot.run_bump_risk_job(
        bundle["parameters"], data, bundle["caches"], risk, chunk_paths=7
    )
    validation = run_pilot.study.select_validation(
        data,
        risk,
        generator="Heston",
        universe="U1",
        widths=run_pilot.protocol.candidate_protocol()["hedging"]["band_width_candidates"],
    )
    identity = next(
        r
        for r in run_pilot.protocol.study_roster()["primary_cells"]
        if r["generator"] == "Heston"
        and r["universe"] == "U1"
        and r["policy"] == "greek"
        and r["valuation"] == "Heston"
    )
    rows = []
    for index in range(3):
        rows.append(
            run_pilot.run_cell_pair_job(
                base_dataset=data,
                refined_dataset=data,
                base_risk=risk,
                refined_risk=bump["risk_variants"][index],
                identity=identity,
                validation=validation,
                fits=[],
                refinement_kind="position",
                refined_risk_source=bump,
                refined_risk_width_index=index,
            )
        )
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved RNG"))
    for index, row in enumerate(rows):
        checked = check_pilot.check_paired_pnl_record(row)
        assert checked["original_n"] == 16 and row["refined_risk_width_index"] == index
    rows[0]["refined_risk_width_index"] = 1
    with pytest.raises(ValueError, match=r"variant|width"):
        check_pilot.check_paired_pnl_record(rows[0])


def test_stream_receipts_derive_global_ids_from_actual_saved_market_normals(monkeypatch):
    import hashlib

    bundle = run_pilot.runner.run_tiny(original_n=16, updates=0, train=False)
    p = bundle["parameters"]
    cache = bundle["caches"]["heston"]["call"]
    ns = run_pilot.protocol.candidate_protocol()["seeds"]
    markets = {}
    for role, seed in (("train", ns["pilot"][0]), ("validation", ns["pilot"][2])):
        markets[role] = run_pilot.run_market_pair_job(
            p,
            None,
            model="Heston",
            seed=seed,
            original_n=16,
            chunk_paths=7,
            call_cache=cache,
            premium=3.0,
            cost_rates=[0.0005, 0.005],
        )
    roles = {r: {"Heston": r} for r in markets}
    raw = run_pilot.run_stream_receipts_job(markets=markets, roles=roles, seed_namespace=ns)
    normal = np.concatenate([r["primitives"]["normals"] for r in markets["train"]["raw_chunks"][1]])
    assert (
        raw["value"]["train"]["Heston"]["global_driver_id"]
        == hashlib.sha256(normal.tobytes()).hexdigest()
    )
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("receipt RNG"))
    checked = check_pilot.check_stream_receipts_record(
        raw, markets=markets, roles=roles, seed_namespace=ns
    )
    assert checked["financial_qualification"] == "unknown"
    raw["value"]["train"]["Heston"]["global_driver_id"] = "0" * 64
    with pytest.raises(ValueError, match=r"receipt|binding"):
        check_pilot.check_stream_receipts_record(
            raw, markets=markets, roles=roles, seed_namespace=ns
        )


def test_quote_projection_keeps_full_37_raw_and_single_original_case():
    candidate = run_pilot.execution.execution_candidate()
    checked = {
        "original_n": 37,
        "initial_quote_error": np.zeros(37),
        "cf_order_cutoff_error": np.zeros(37),
    }
    raw = {"original_n": 37, "quote_ids": np.arange(37)}
    for descriptor in candidate["pilot_cases"][:37]:
        row = check_pilot.project_case(descriptor, checked, raw, {"original_n": 1})
        assert row["original_n"] == 1
        assert row["raw_original_n"] == 37
        assert row["raw_quote_index"] == int(descriptor["id"][5:])
    with pytest.raises(ValueError, match=r"original quote"):
        check_pilot.project_case(candidate["pilot_cases"][0], checked, raw, {"original_n": 37})
    raw["quote_ids"] = raw["quote_ids"][::-1]
    with pytest.raises(ValueError, match=r"original quote"):
        check_pilot.project_case(candidate["pilot_cases"][0], checked, raw, {"original_n": 1})


def test_execution_expense_aliases_copy_actual_parent_clock_without_double_charge():
    parent = {
        "id": "actual-parent",
        "scope": "measured-worker",
        "status": "failed",
        "reason": "real cap",
        "parent_id": None,
        "includes_children": True,
        "timing": {"wall_seconds": 2.0, "cpu_seconds": 1.0, "overrun_seconds": 0.5},
    }
    job = {
        "id": "actual-job",
        "expense": parent,
        "timing_events": {
            "wall_start_ns": 100,
            "wall_stop_ns": 2000000100,
            "cpu_start_ns": 300,
            "cpu_stop_ns": 1000000300,
        },
    }
    aliases = [
        {
            "id": "case-alias",
            "parent_expense_id": "actual-parent",
            "required_job_ids": ["actual-job"],
        },
        {
            "id": "attempt-alias",
            "parent_expense_id": "actual-parent",
            "required_job_ids": ["actual-job"],
        },
    ]
    checked = check_pilot.project_execution_expense_aliases(
        [parent], aliases, jobs={"actual-job": job}
    )
    assert checked["charged_totals"]["wall_seconds"] == pytest.approx(2.0)
    assert checked["charged_ids"] == ["actual-parent"]
    assert all(r["timing"] == parent["timing"] for r in checked["raw_records"])
    assert checked["raw_records"][1]["timing_events"] == job["timing_events"]
    assert checked["raw_records"][1]["actual_parent_sha256"] == run_pilot.input_identity(parent)
    import copy

    bad = copy.deepcopy(job)
    bad["expense"]["timing"]["wall_seconds"] = 0.0
    with pytest.raises(ValueError, match=r"actual.*clock"):
        check_pilot.project_execution_expense_aliases(
            [bad["expense"]], aliases, jobs={"actual-job": bad}
        )
    with pytest.raises(ValueError, match=r"covered"):
        check_pilot.project_execution_expense_aliases(
            [parent],
            [
                {
                    "id": "unrelated",
                    "parent_expense_id": "actual-parent",
                    "required_job_ids": ["unexecuted"],
                }
            ],
            jobs={"actual-job": job},
        )


def test_execution_expense_aliases_require_prior_parent_and_explicit_actual_phase_scope():
    phase = {
        "id": "actual-phase",
        "scope": "actual-full-pilot",
        "status": "complete",
        "parent_id": None,
        "includes_children": True,
        "timing": {"wall_seconds": 3.0, "cpu_seconds": 1.0, "overrun_seconds": 0.0},
        "timing_events": {
            "wall_start_ns": 100,
            "wall_stop_ns": 3000000100,
            "cpu_start_ns": 300,
            "cpu_stop_ns": 1000000300,
        },
        "covered_job_ids": ["j1", "j2"],
    }
    alias = {
        "id": "group-alias",
        "parent_expense_id": "actual-phase",
        "required_job_ids": ["j1", "j2"],
    }
    jobs = {
        j: {
            "id": j,
            "expense": dict(
                phase,
                id=j,
                timing={"wall_seconds": 1.0, "cpu_seconds": 0.1, "overrun_seconds": 0.0},
            ),
            "timing_events": {
                "wall_start_ns": 100,
                "wall_stop_ns": 1000000100,
                "cpu_start_ns": 300,
                "cpu_stop_ns": 100000300,
            },
        }
        for j in ("j1", "j2")
    }
    checked = check_pilot.project_execution_expense_aliases([phase], [alias], jobs=jobs)
    assert checked["charged_totals"]["wall_seconds"] == pytest.approx(3.0)
    assert checked["raw_records"][1]["covered_job_ids"] == ["j1", "j2"]
    import copy

    missing = copy.deepcopy(phase)
    missing.pop("covered_job_ids")
    with pytest.raises(ValueError, match=r"actual.*scope"):
        check_pilot.project_execution_expense_aliases([missing], [alias], jobs=jobs)
    with pytest.raises(ValueError, match=r"prior.*parent"):
        check_pilot.project_execution_expense_aliases(
            [phase], [dict(alias, parent_expense_id="nonexistent")], jobs={}
        )


def test_actual_lifecycle_phase_clock_is_inclusive_and_resume_keeps_prior_timer(
    tmp_path, monkeypatch
):
    inputs, plan = _lifecycle_source_plan(monkeypatch)
    first = run_pilot.run_pilot(tmp_path, inputs=inputs, locked_plan=plan)
    assert len(first["execution_phases"]) == 1
    phase = first["execution_phases"][0]
    assert set(phase["covered_job_ids"]) == {j["id"] for j in first["jobs"]}
    costs = check_pilot.check_raw_costs(first, plan)
    assert phase["id"] in costs["current"]["charged_ids"]
    assert all(j["expense"]["id"] not in costs["current"]["charged_ids"] for j in first["jobs"])
    resumed = run_pilot.run_pilot(tmp_path, inputs=inputs, locked_plan=plan, resume=True)
    assert len(resumed["execution_phases"]) == 2
    assert run_pilot.input_identity(resumed["execution_phases"][0]) == run_pilot.input_identity(
        phase
    )
    assert resumed["execution_phases"][1]["covered_job_ids"] == []
    check_pilot.check_raw_costs(resumed, plan)


def test_execution_projection_refuses_partial_raw_pilot_and_receipt_flags(monkeypatch):
    inputs, plan = _lifecycle_source_plan(monkeypatch)
    snapshot = {
        "schema": run_pilot.SCHEMA,
        "locked_plan": plan,
        "jobs": [],
        "source": plan["source"],
        "case_bindings": [],
        "attempt_bindings": [],
        "test_opened": False,
        "history": plan["history"],
        "closed": True,
        "verification": {"integrity": "pass"},
    }
    with pytest.raises(ValueError, match=r"saved original pilot.*closed"):
        check_pilot.project_execution_pilot(
            snapshot,
            expected_plan=plan,
            context={"inputs": inputs, "parameters": inputs["parameters"]},
            selection={},
            domains=[],
        )


def test_progressive_teacher_gate_refuses_flags_or_shrunken_original_state_roster():
    stage = {
        "model": "Heston",
        "original_n": 1024,
        "grid": "coarse",
        "qualification": "qualified",
        "all_passed": True,
    }
    with pytest.raises(ValueError, match=r"original.*stage.*binding"):
        run_pilot.run_teacher_candidate_gate_job(
            HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7),
            None,
            stage_plan=stage,
            evidence=[],
        )
    stage.update(
        required_job_ids=["teacher"],
        teacher_job_id="teacher",
        next_teacher_job_id=None,
        grid_teacher_job_id="teacher",
        date_bindings=[],
        state_bindings=[],
        pnl_bindings={},
        reference_rule="next_prefix",
        oracle_original_n=4096,
    )
    with pytest.raises(ValueError, match=r"full12date.*18state"):
        run_pilot.run_teacher_candidate_gate_job(
            HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7),
            None,
            stage_plan=stage,
            evidence=[
                {
                    "id": "teacher",
                    "operation": "teacher_grid",
                    "raw": {"original_n": 1024, "qualification": "qualified"},
                }
            ],
        )


@pytest.mark.parametrize("operation", ["teacher_grid", "teacher_driver"])
def test_max_teacher_reference_is_prior_typed_and_original_reserved_stream_only(operation):
    import copy

    c = run_pilot.protocol.candidate_protocol()
    purpose = {
        "reference_rule": "independent_reserved_stream_grid_max",
        "stream_namespace": "oracle",
        "seed": c["seeds"]["oracle"][0],
    }
    args = {
        "model": "Heston",
        "original_n": 65536,
        "seed": purpose["seed"],
        "grid": "coarse",
        "calendar_times": np.arange(769) / 768,
        "teacher_reference": purpose,
    }
    count = 108 if operation == "teacher_grid" else 1
    prediction = {"path_steps": 65536 * 768, "total_path_steps": 65536 * 768 * count}
    if count > 1:
        prediction.update(financial_child_count=count, child_boundary="original_teacher_node")
    job = {
        "operation": operation,
        "prediction": prediction,
        "driver_model": "Heston",
        "teacher_reference": purpose,
    }
    size = run_pilot._job_identity(job, args)
    assert size["original_n"] == 65536
    for key, value in (
        ("original_n", 16384),
        ("seed", 991992),
        ("teacher_reference", dict(purpose, stream_namespace="test")),
    ):
        bad = copy.deepcopy(args)
        bad[key] = value
        with pytest.raises(ValueError, match=r"maximum.*reference|reserved.*stream"):
            run_pilot._job_identity(job, bad)
    with pytest.raises(ValueError, match=r"maximum.*reference|prior"):
        run_pilot._job_identity({k: v for k, v in job.items() if k != "teacher_reference"}, args)
    principal = copy.deepcopy(args)
    principal.pop("teacher_reference")
    with pytest.raises(ValueError, match=r"stream|principal"):
        run_pilot._job_identity(job, principal)


def test_progressive_activation_recomputes_teacher_gate_instead_of_saved_flag():
    prior = {
        "id": "g",
        "operation": "teacher_candidate_gate",
        "arguments": {"parameters": None, "surface": None, "stage_plan": {}, "evidence": []},
    }
    previous = {
        "g": {
            "id": "g",
            "operation": "teacher_candidate_gate",
            "status": "executed",
            "raw": {"qualification": "qualified", "original_n": 1024},
        }
    }
    job = {"id": "next", "activation": {"previous_teacher_gate_job_id": "g"}}
    with pytest.raises(ValueError, match=r"original.*stage.*binding"):
        run_pilot.teacher_activation_decision(job, {}, previous, {"g": prior}, {})
    with pytest.raises(ValueError, match=r"teacher.*gate"):
        run_pilot.teacher_activation_decision(
            job, {}, previous, {"g": dict(prior, operation="source")}, {}
        )


def test_actual_progressive_next_work_runs_after_consumed_parent_gate_cap(tmp_path, monkeypatch):
    import copy

    inputs, plan = _lifecycle_source_plan(monkeypatch)
    parent = plan["jobs"][0]
    gate = copy.deepcopy(plan["jobs"][1])
    gate.update(
        id="stage-unavailable",
        operation="teacher_candidate_gate",
        expense_id="stage-unavailable:actual",
        arguments={"evidence": {"job": "teacher-cap"}},
    )
    nextjob = copy.deepcopy(parent)
    nextjob.update(
        id="next-prefix",
        expense_id="next-prefix:actual",
        activation={"previous_teacher_gate_job_id": "stage-unavailable"},
    )
    nextjob["original_n"] = 4096
    nextjob["arguments"]["original_n"] = 4096
    nextjob["prediction"]["path_steps"] = 4096 * 768
    parent.pop("cap_scope")
    nextjob.pop("cap_scope", None)
    plan["jobs"] = [parent, gate, nextjob, plan["jobs"][2]]
    snapshot = run_pilot.run_pilot(tmp_path, inputs=inputs, locked_plan=plan)
    jobs = {j["id"]: j for j in snapshot["jobs"]}
    assert jobs["stage-unavailable"]["status"] == "unexecuted_dependency_cap"
    assert jobs["next-prefix"]["status"] == "failed_at_declared_cap"
    assert jobs["next-prefix"]["raw"]["original_n"] == 4096
    assert jobs["independent"]["status"] == "executed"
    resumed = run_pilot.run_pilot(tmp_path, inputs=inputs, locked_plan=plan, resume=True)
    assert run_pilot.input_identity(resumed["jobs"][2]["raw"]) == run_pilot.input_identity(
        jobs["next-prefix"]["raw"]
    )


def test_progressive_boundary_unit_unused_keeps_denominator_and_actual_inspection_cost(
    tmp_path, monkeypatch
):
    # This controlled arithmetic boundary is not financial evidence.
    import copy

    inputs, plan = _lifecycle_source_plan(monkeypatch)
    gate = copy.deepcopy(plan["jobs"][2])
    gate.update(
        id="gate",
        operation="teacher_candidate_gate",
        original_n=1024,
        expense_id="gate:actual",
        arguments={
            "parameters": {"input": "parameters"},
            "surface": None,
            "stage_plan": {"original_n": 1024},
            "evidence": [],
        },
    )
    later = copy.deepcopy(plan["jobs"][0])
    later.pop("cap_scope")
    later.update(
        id="later", expense_id="later:actual", activation={"previous_teacher_gate_job_id": "gate"}
    )
    later["original_n"] = 4096
    later["arguments"]["original_n"] = 4096
    later["prediction"]["path_steps"] = 4096 * 768
    plan["jobs"] = [gate, later]
    actual = {
        "kind": "teacher_candidate_gate",
        "original_n": 1024,
        "qualification": "qualified",
        "source_unit_scope": "controlled arithmetic/activation boundary only",
    }
    monkeypatch.setattr(
        run_pilot, "run_teacher_candidate_gate_job", lambda **kw: copy.deepcopy(actual)
    )
    monkeypatch.setattr(
        check_pilot, "calculate_teacher_candidate_gate", lambda *a, **kw: copy.deepcopy(actual)
    )
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **kw: pytest.fail("unused RNG"))
    snapshot = run_pilot.run_pilot(tmp_path, inputs=inputs, locked_plan=plan)
    row = snapshot["jobs"][1]
    assert row["status"] == "not_required_after_qualified_prefix"
    assert row["raw"]["original_n"] == row["raw"]["unexecuted_n"] == 4096
    assert row["raw"]["qualification"] == "unknown"
    assert row["expense"]["timing"]["wall_seconds"] > 0
    assert row["raw"]["qualified_original_n"] == 1024
    assert row["raw"]["lower_gate_evidence_sha256"] == run_pilot.input_identity(actual)
    resumed = run_pilot.run_pilot(tmp_path, inputs=inputs, locked_plan=plan, resume=True)
    assert run_pilot.input_identity(resumed["jobs"][1]["raw"]) == run_pilot.input_identity(
        row["raw"]
    )


def test_saved_unused_prefix_recomputes_lower_gate_and_inherited_proof(tmp_path, monkeypatch):
    # Arithmetic boundary fixture, never a substitute for the actual financial gate.
    import copy

    inputs, plan = _lifecycle_source_plan(monkeypatch)
    gate = copy.deepcopy(plan["jobs"][2])
    gate.update(
        id="gate",
        operation="teacher_candidate_gate",
        original_n=1024,
        expense_id="gate:actual",
        arguments={
            "parameters": {"input": "parameters"},
            "surface": None,
            "stage_plan": {"original_n": 1024},
            "evidence": [],
        },
    )
    later = copy.deepcopy(plan["jobs"][0])
    later.pop("cap_scope")
    later.update(
        id="later", expense_id="later:actual", activation={"previous_teacher_gate_job_id": "gate"}
    )
    later["original_n"] = 4096
    later["arguments"]["original_n"] = 4096
    later["prediction"]["path_steps"] = 4096 * 768
    inherited = copy.deepcopy(later)
    inherited.update(
        id="inherited",
        expense_id="inherited:actual",
        operation="teacher_candidate_gate",
        activation={"previous_teacher_gate_job_id": "gate"},
    )
    inherited["original_n"] = 4096
    inherited["arguments"] = {
        "parameters": {"input": "parameters"},
        "surface": None,
        "stage_plan": {"original_n": 4096},
        "evidence": [],
    }
    final = copy.deepcopy(later)
    final.update(
        id="final",
        expense_id="final:actual",
        activation={"previous_teacher_gate_job_id": "inherited"},
    )
    final["original_n"] = 16384
    final["arguments"]["original_n"] = 16384
    final["prediction"]["path_steps"] = 16384 * 768
    plan["jobs"] = [gate, later, inherited, final]
    actual = {
        "kind": "teacher_candidate_gate",
        "original_n": 1024,
        "qualification": "qualified",
        "source_unit_scope": "controlled arithmetic/activation boundary only",
    }
    monkeypatch.setattr(
        run_pilot, "run_teacher_candidate_gate_job", lambda **kw: copy.deepcopy(actual)
    )
    monkeypatch.setattr(
        check_pilot, "calculate_teacher_candidate_gate", lambda *a, **kw: copy.deepcopy(actual)
    )
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **kw: pytest.fail("checker RNG"))
    snapshot = run_pilot.run_pilot(tmp_path, inputs=inputs, locked_plan=plan)
    jobs = {r["id"]: r for r in snapshot["jobs"]}
    planned = {r["id"]: r for r in plan["jobs"]}
    for identifier in ("later", "inherited", "final"):
        checked = check_pilot.check_unused_teacher_job(
            jobs[identifier],
            planned[identifier],
            inputs=inputs,
            jobs=jobs,
            planned_jobs=planned,
            activation_cache={},
        )
        assert checked["integrity"] == "pass"
        assert checked["executed_original_n"] == 0
        assert checked["original_n"] == planned[identifier]["original_n"]
    bad = copy.deepcopy(jobs)
    bad["inherited"]["raw"]["lower_gate_evidence_sha256"] = "b" * 64
    with pytest.raises(ValueError, match=r"unused|original|qualification"):
        check_pilot.check_unused_teacher_job(
            bad["final"],
            planned["final"],
            inputs=inputs,
            jobs=bad,
            planned_jobs=planned,
            activation_cache={},
        )
    bad = copy.deepcopy(jobs)
    bad["gate"]["raw"]["qualification"] = "unknown"
    with pytest.raises(ValueError, match=r"actual lower|unused|qualified"):
        check_pilot.check_unused_teacher_job(
            bad["later"],
            planned["later"],
            inputs=inputs,
            jobs=bad,
            planned_jobs=planned,
            activation_cache={},
        )


def _dense_teacher_domain_fixture(model):
    from hullkit._dynamic_hedging_surfaces import build_asian_cache

    axes = run_pilot.teacher_axes("coarse", model)
    shape = (12,) + ((len(axes["spot"]),) if model == "local" else ()) + (len(axes["state"]), 33)
    groups = {
        "parameters": HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7),
        "N": 16,
        "f": np.ones(shape),
        "block_means": np.ones((*shape, 16, 3)),
    }
    if model == "local":
        t0shape = (len(axes["t0_spot"]), len(axes["state"]), 33)
        groups.update(t0_f=np.ones(t0shape), t0_block_means=np.ones((*t0shape, 16, 3)))
    cache = build_asian_cache(groups, model=model.lower(), axes=axes)
    return {
        "kind": "teacher_grid",
        "model": model,
        "grid": "coarse",
        "original_n": 16,
        "axes": axes,
        "cache": cache,
        "financial_qualification": "unknown",
    }


@pytest.mark.parametrize("model", ["Heston", "local"])
def test_teacher_domain_selection_max_finite_box_is_only_support_and_preserves_full_raw(
    model, monkeypatch
):
    import copy

    raw = _dense_teacher_domain_fixture(model)
    cache = raw["cache"]
    cache["f"][1, ..., -1] = np.nan
    cache["block_means"][1, ..., 0, :, :] = np.nan
    # One nonfinite block must disqualify that node even when its mean is finite.
    cache["block_means"][2, ..., -2, 7, 1] = np.nan
    if model == "local":
        cache["t0_sheet"]["block_means"][0, ...] = np.nan
    cache["f"][3, ...] = np.nan
    before = run_pilot.input_identity(raw)
    rule = run_pilot.teacher_domain_rule(model)
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **kw: pytest.fail("domain RNG"))
    result = run_pilot.run_teacher_domain_selection_job(teacher=raw, selection_rule=rule)
    assert run_pilot.input_identity(raw) == before
    assert result["financial_qualification"] == "unknown"
    assert result["evaluation_domains"][3] is None
    assert result["evaluation_domains"][1]["threshold"] == [1, 32]
    assert result["evaluation_domains"][2]["threshold"] == [0, 31]
    if model == "local":
        assert result["evaluation_domains"][0]["spot"] == [1, 5]
        assert result["cache"]["evaluation_domain_sheets"][0] == "t0_sheet"
    np.testing.assert_equal(result["cache"]["f"], cache["f"])
    np.testing.assert_equal(result["cache"]["block_means"], cache["block_means"])
    assert result["cache"]["original_N"] == 16
    assert run_pilot.input_identity(
        result["cache"]["primitive_groups"]
    ) == run_pilot.input_identity(cache["primitive_groups"])
    checked = check_pilot.check_teacher_domain_selection_record(raw, result, selection_rule=rule)
    assert checked["integrity"] == "pass"
    tampered = copy.deepcopy(result)
    tampered["evaluation_domains"][1]["threshold"] = [2, 32]
    with pytest.raises(ValueError, match=r"domain|box"):
        check_pilot.check_teacher_domain_selection_record(raw, tampered, selection_rule=rule)
    badrule = copy.deepcopy(rule)
    badrule["anchors"]["state"] = 0.08 if model == "Heston" else 2
    with pytest.raises(ValueError, match=r"prior.*rule|anchor"):
        run_pilot.run_teacher_domain_selection_job(teacher=raw, selection_rule=badrule)


def test_actual_field_time_scaled_cutoff_retains_original_controls_and_saved_binding(monkeypatch):
    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    times = np.array([1 / 4096, 1 / 1024])
    z = np.array([-0.1, 0, 0.1])
    fixed = run_pilot.run_field_job(parameters, times=times, z_nodes=z, order=1024, cutoff=1024)
    assert fixed["status"] == "unavailable"
    raw = run_pilot.run_field_job(
        parameters, times=times, z_nodes=z, order=1024, frequency_scale=512, density_floor=1e-10
    )
    assert raw["status"] == "executed"
    assert raw["frequency_rule"] == "scale_over_sqrt_time"
    np.testing.assert_allclose([r["max_frequency"] for r in raw["rows"]], 512 / np.sqrt(times))
    args = {
        "parameters": parameters,
        "times": times,
        "z_nodes": z,
        "order": 1024,
        "frequency_scale": 512,
        "density_floor": 1e-10,
    }
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **kw: pytest.fail("field checker RNG"))
    checked = check_pilot._raw_job_check(
        {"operation": "field", "raw": raw}, {"resolved_arguments": args}
    )
    assert checked["financial_qualification"] == "unknown"
    import copy

    tampered = copy.deepcopy(raw)
    tampered["rows"][0]["max_frequency"] = 1024
    with pytest.raises(ValueError, match=r"field.*frequency|controls"):
        check_pilot._raw_job_check(
            {"operation": "field", "raw": tampered}, {"resolved_arguments": args}
        )
    with pytest.raises(ValueError, match=r"field.*controls"):
        check_pilot._raw_job_check(
            {"operation": "field", "raw": raw},
            {"resolved_arguments": dict(args, frequency_scale=256)},
        )


def test_progressive_control_references_keep_real_capped_envelope_without_numerical_fallback():
    job = {
        "id": "capped",
        "status": "failed_at_declared_cap",
        "raw": {"original_n": 65536, "cache": None},
        "expense": {"actual": True},
        "artifact_path": "/original/path",
    }
    results = {"capped": job}
    assert run_pilot._dependency_ids({"envelope": {"job_record": "capped"}}) == {"capped"}
    assert run_pilot._numeric_dependency_ids({"envelope": {"job_record": "capped"}}) == set()
    resolved = run_pilot._resolve({"job_record": "capped"}, {}, results)
    assert resolved["status"] == "failed_at_declared_cap"
    assert "artifact_path" not in resolved
    assert resolved["raw"]["cache"] is None


def test_teacher_selector_arithmetic_boundary_preserves_unknown_and_actual_cap_no_fallback(
    monkeypatch,
):
    import copy

    stages = []
    teachers = {}
    for N in (1024, 4096, 16384, 65536):
        for grid in ("coarse", "high"):
            identifier = f"gate:{N}:{grid}"
            teacher = f"teacher:{N}:{grid}"
            raw = {
                "kind": "teacher_candidate_gate",
                "model": "Heston",
                "original_n": N,
                "grid": grid,
                "qualification": "unknown",
            }
            state_bindings = [
                {"id": r["id"], "job_id": f"state:{N}:{grid}:" + r["id"]}
                for r in run_pilot.execution.execution_candidate()["pilot_cases"]
                if r["kind"] == "state" and r["identity"]["model"] == "Heston"
            ]
            date_bindings = [{"date_index": j, "job_id": f"date:{N}:{grid}:{j}"} for j in range(12)]
            stages.append(
                {
                    "id": identifier,
                    "job": {"id": identifier, "status": "executed", "raw": raw},
                    "state_bindings": state_bindings,
                    "date_bindings": date_bindings,
                    "arguments": {
                        "parameters": None,
                        "surface": None,
                        "stage_plan": {
                            "original_n": N,
                            "grid": grid,
                            "state_bindings": state_bindings,
                            "date_bindings": date_bindings,
                        },
                        "evidence": [],
                    },
                    "teacher_job_id": teacher,
                    "original_n": N,
                    "grid": grid,
                }
            )
            teachers[teacher] = {
                "id": teacher,
                "status": "executed",
                "raw": {
                    "original_n": N,
                    "grid": grid,
                    "model": "Heston",
                    "cache": {"original_N": N},
                    "domain_selection": {"qualification": "unknown"},
                },
            }
    monkeypatch.setattr(
        check_pilot,
        "calculate_teacher_candidate_gate",
        lambda *a, stage_plan, **kw: {
            "kind": "teacher_candidate_gate",
            "model": "Heston",
            "original_n": stage_plan["original_n"],
            "grid": stage_plan["grid"],
            "qualification": "unknown",
        },
    )
    rule = run_pilot.teacher_selection_rule("Heston")
    result = run_pilot.run_teacher_selection_job(
        model="Heston", stages=stages, teachers=teachers, selection_rule=rule
    )
    assert result["selection_status"] == "research_only_unqualified"
    assert result["original_n"] == 65536
    assert result["cache"]["original_N"] == 65536
    assert result["financial_qualification"] == "unknown"
    checked = check_pilot.check_teacher_selection_record(
        result, model="Heston", stages=stages, teachers=teachers, selection_rule=rule
    )
    assert checked["integrity"] == "pass"
    capped = copy.deepcopy(teachers)
    for row in capped.values():
        if row["raw"]["original_n"] == 65536:
            row.update(status="failed_at_declared_cap", cap_evidence={"actual": True})
            row["raw"]["cache"] = None
    unavailable = run_pilot.run_teacher_selection_job(
        model="Heston", stages=stages, teachers=capped, selection_rule=rule
    )
    assert unavailable["selection_status"] == "unavailable"
    assert unavailable["cache"] is None
    assert len(unavailable["parent_unavailable_job_ids"]) == 2
    assert unavailable["original_n"] == 65536
    bad = copy.deepcopy(result)
    bad["selection_status"] = "qualified_selection"
    with pytest.raises(ValueError, match=r"original.*selection"):
        check_pilot.check_teacher_selection_record(
            bad, model="Heston", stages=stages, teachers=teachers, selection_rule=rule
        )


def test_selector_missing_max_cache_preserves_actual_parent_cap_then_downstream_nonexecution(
    tmp_path, monkeypatch
):
    import copy

    inputs, plan = _lifecycle_source_plan(monkeypatch)
    parent = plan["jobs"][0]
    selection = copy.deepcopy(plan["jobs"][2])
    selection.update(
        id="selection",
        operation="teacher_selection",
        original_n=65536,
        expense_id="selection:actual",
        arguments={"teacher": {"job_record": parent["id"]}},
    )
    selection["budget"]["wall_seconds"] = 5.0
    downstream = copy.deepcopy(plan["jobs"][1])
    downstream.update(
        id="selected-numerical",
        expense_id="selected-numerical:actual",
        original_n=65536,
        arguments={"selected": {"job": "selection"}},
    )
    downstream["budget"]["wall_seconds"] = 5.0
    parent["cap_scope"] = {
        "job_ids": [parent["id"], "selection", "selected-numerical"],
        "case_ids": [],
        "attempt_ids": [],
        "expense_id": parent["expense_id"],
    }
    plan["jobs"] = [parent, selection, downstream, plan["jobs"][2]]

    def selected(**kwargs):
        assert kwargs["teacher"]["status"] == "failed_at_declared_cap"
        return {
            "kind": "teacher_selection",
            "selection_status": "unavailable",
            "cache": None,
            "original_n": 65536,
            "parent_unavailable_job_ids": [parent["id"]],
        }

    monkeypatch.setattr(run_pilot, "run_teacher_selection_job", selected)
    snapshot = run_pilot.run_pilot(tmp_path, inputs=inputs, locked_plan=plan)
    jobs = {j["id"]: j for j in snapshot["jobs"]}
    assert jobs["selection"]["status"] == "unexecuted_dependency_cap"
    assert jobs["selection"]["raw"]["selection_inspection"]["cache"] is None
    assert jobs["selection"]["raw"]["parent_cap_job_ids"] == [parent["id"]]
    assert jobs["selected-numerical"]["status"] == "unexecuted_dependency_cap"
    assert jobs["selected-numerical"]["raw"]["original_n"] == 65536
    assert jobs["independent"]["status"] == "executed"
    check_pilot.check_dependency_cap_job(jobs["selection"], selection, plan, jobs, inputs=inputs)
    resumed = run_pilot.run_pilot(tmp_path, inputs=inputs, locked_plan=plan, resume=True)
    assert run_pilot.input_identity(resumed["jobs"][1]["raw"]) == run_pilot.input_identity(
        jobs["selection"]["raw"]
    )
    bad = copy.deepcopy(jobs)
    bad["selection"]["raw"]["selection_inspection"]["cache"] = {"fake": 0}
    with pytest.raises(ValueError, match=r"selection|unavailable"):
        check_pilot.check_dependency_cap_job(bad["selection"], selection, plan, bad, inputs=inputs)


def test_selected_state_retains_teacher_n_separate_from_next_prefix_oracle_n():
    from hullkit._dynamic_hedging_surfaces import build_call_cache, evaluate_call

    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    teacher = _dense_teacher_domain_fixture("Heston")
    call = build_call_cache(
        parameters,
        None,
        dates=[0.0],
        spot_nodes=[98.0, 99.0, 100.0, 101.0, 102.0],
        state_nodes=[0.02, 0.03, 0.04, 0.05, 0.06],
        model="heston",
    )
    quote = evaluate_call(call, 0, 100.0, 0.04)["value"]
    raw = run_pilot.run_state_job(
        parameters,
        None,
        model="Heston",
        call_cache=call,
        asian_cache=teacher["cache"],
        date_index=0,
        spot=100.0,
        quote=quote,
        memory_sum=0,
        memory_count=0,
        oracle={"original_path_count": 64},
    )
    assert raw["original_n"] == 16
    assert raw["oracle_original_n"] == 64
    assert raw["oracle"]["original_path_count"] == 64


def test_conditional_selected_case_bindings_and_n_are_recomputed_without_fixed_n_changes():
    candidate = run_pilot.execution.execution_candidate()
    descriptor = next(r for r in candidate["pilot_cases"] if r["kind"] == "state")
    model = descriptor["identity"]["model"]
    identifier = descriptor["id"]
    selection = {
        "id": "selection",
        "operation": "teacher_selection",
        "status": "executed",
        "raw": {
            "kind": "teacher_selection",
            "model": model,
            "original_n": 4096,
            "grid": "high",
            "selection_status": "qualified_selection",
            "selected_teacher_job_id": "domain",
            "selected_state_case_job_ids": {identifier: "state-4096"},
            "selected_date_job_ids": {"0": "date-4096"},
            "financial_qualification": "unknown",
        },
    }
    jobs = {"selection": selection}
    source = {"teacher_selection_job_id": "selection", "model": model}
    plan = {"id": identifier, "original_n": None, "original_n_source": source}
    concrete = check_pilot.concrete_original_n_plan(plan, jobs)
    assert concrete["original_n"] == 4096
    assert concrete["prior_template_sha256"] == run_pilot.input_identity(plan)
    assert concrete["selector_raw_sha256"] == run_pilot.input_identity(selection["raw"])
    case = {"id": identifier, "job_id_source": dict(source, case_id=identifier)}
    actual = check_pilot.concrete_case_binding(case, jobs)
    assert actual["job_id"] == "state-4096"
    attempt = {"id": f"teacher:{model}:date0", "job_ids_source": dict(source, date_index=0)}
    assert check_pilot.concrete_attempt_binding(attempt, jobs)["job_ids"] == ["domain", "date-4096"]
    fixed = {"id": "fit:Heston:U1:init11", "original_n": 1024}
    assert check_pilot.concrete_original_n_plan(fixed, jobs) == fixed
    import copy

    bad = copy.deepcopy(plan)
    bad["original_n_source"]["model"] = "local" if model == "Heston" else "Heston"
    with pytest.raises(ValueError, match=r"original.*selector|model"):
        check_pilot.concrete_original_n_plan(bad, jobs)
    with pytest.raises(ValueError, match=r"fixed|conditional"):
        check_pilot.concrete_original_n_plan(dict(fixed, original_n_source=source), jobs)


def test_A_selection_uses_prior_rules_and_measured_premium_not_future_result_hash():
    candidate = run_pilot.execution.execution_candidate()
    original = candidate["original_candidate"]
    static = {
        k: original["hedging"][k]
        for k in ("band_width_candidates", "baseline_rule", "checkpoint_rule")
    }
    specs = {
        "teacher_selection_job_ids": {"Heston": "H", "local": "L"},
        "premium_job_id": "premium",
        "precision_job_ids": ["p8192", "p16384", "p32768"],
        "static": static,
    }
    jobs = {
        m: {
            "operation": "teacher_selection",
            "status": "executed",
            "raw": {
                "kind": "teacher_selection",
                "model": model,
                "original_n": 4096,
                "grid": "high",
                "selection_status": "research_only_unqualified",
            },
        }
        for m, model in (("H", "Heston"), ("L", "local"))
    }
    jobs["premium"] = {"operation": "premium", "status": "executed", "raw": {}}
    checks = {
        "H": {},
        "L": {},
        "premium": {
            "original_n": 65536,
            "value": 7.3,
            "standard_error": 0.001,
            "scheme_error": 0.002,
        },
    }
    for N in (8192, 16384, 32768):
        identifier = f"p{N}"
        jobs[identifier] = {"operation": "precision", "status": "executed", "raw": {}}
        checks[identifier] = {
            "original_n": N,
            "qualification": "unknown",
            "worst_mean_loss_se": None,
            "worst_mse_se": None,
            "baseline_mse": None,
        }
    result = check_pilot.derive_execution_selection(specs, jobs, checks)
    assert result["teacher_n"] == {"Heston": 4096, "local": 4096}
    assert result["premium"]["value"] == 7.3
    assert result["precision_selection"] == "unavailable"
    assert result["test_n"] == 32768
    assert result["teacher_selection_status"]["Heston"] == "research_only_unqualified"
    bad = dict(specs, static=dict(static, baseline_rule="largest finite"))
    with pytest.raises(ValueError, match=r"prior.*selection"):
        check_pilot.derive_execution_selection(bad, jobs, checks)


def test_saved_next_prefix_compares_actual_driver_bytes_across_different_chunk_boundaries(
    tmp_path, monkeypatch
):
    import copy

    times = np.linspace(0, 1, 25)
    a = run_pilot.run_teacher_driver_job(
        seed=913, original_n=16, calendar_times=times, chunk_paths=7, work_directory=tmp_path / "a"
    )
    b = run_pilot.run_teacher_driver_job(
        seed=913, original_n=32, calendar_times=times, chunk_paths=5, work_directory=tmp_path / "b"
    )
    left = {"original_n": 16, "seed": 913, "driver": a}
    right = {"original_n": 32, "seed": 913, "driver": b}
    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **kw: pytest.fail("prefix checker RNG")
    )
    checked = check_pilot.check_teacher_driver_comparison(left, right, reference_rule="next_prefix")
    assert checked["actual_prefix_n"] == 16
    assert checked["original_reference_n"] == 32
    bad = copy.deepcopy(right)
    bad["seed"] = 914
    with pytest.raises(ValueError, match=r"original.*stream"):
        check_pilot.check_teacher_driver_comparison(left, bad, reference_rule="next_prefix")
    same = {
        "original_n": 65536,
        "seed": run_pilot.protocol.candidate_protocol()["seeds"]["oracle"][0],
        "driver": {"global_driver_id": "a" * 64, "original_n": 65536},
    }
    principal = {
        "original_n": 65536,
        "seed": 913,
        "driver": {"global_driver_id": "a" * 64, "original_n": 65536},
    }
    with pytest.raises(ValueError, match=r"independent.*driver"):
        check_pilot.check_teacher_driver_comparison(
            principal, same, reference_rule="independent_reserved_stream_grid_max"
        )


def test_authenticated_unused_jobs_do_not_need_an_unrelated_budget_cap_scope():
    jobs = {
        "realcap": {
            "status": "failed_at_declared_cap",
            "operation": "teacher_grid",
            "raw": {"original_n": 1024},
            "cap_evidence": {"metric": "wall_seconds", "limit": 1, "consumed": 2},
            "expense": {"id": "actual"},
        },
        "unused": {"status": "not_required_after_qualified_prefix"},
    }
    # No parent is allowed to relabel this authenticated unused work as a measured cap.
    planned = {
        "realcap": {
            "cap_scope": {
                "job_ids": ["realcap"],
                "attempt_ids": ["saved_replay"],
                "expense_id": "actual",
            }
        }
    }
    checks = {
        "realcap": {"original_n": 1024},
        "unused": {"integrity": "pass", "executed_original_n": 0},
    }
    parents = check_pilot._cap_scope_parents(
        "saved_replay", "attempt", ["realcap", "unused"], jobs, checks, planned
    )
    assert len(parents) == 1


def test_domain_attempt_accepts_actual_pilot_rule_and_keeps_unavailable_dates_unknown():
    candidate = run_pilot.execution.execution_candidate()
    jobs = {}
    checks = {}
    for model in ("Heston", "local"):
        teacher = _dense_teacher_domain_fixture(model)
        selected = run_pilot.run_teacher_domain_selection_job(
            teacher=teacher, selection_rule=run_pilot.teacher_domain_rule(model)
        )
        identifier = f"selection:{model}"
        jobs[identifier] = {
            "id": identifier,
            "operation": "teacher_selection",
            "status": "executed",
            "raw": {
                "kind": "teacher_selection",
                "model": model,
                "original_n": 1024,
                "cache": selected["cache"],
            },
        }
        checks[identifier] = {"integrity": "pass"}
    context = {
        "domain_plan": {
            "selection_rules": {m: run_pilot.teacher_domain_rule(m) for m in ("Heston", "local")}
        }
    }
    result = check_pilot.project_attempt(
        "domain_selection", list(jobs), jobs, checks, candidate, context
    )
    assert result["status"] == "complete"
    assert result["measurements"] == {}


def _stage_risk_binding_source_unit():
    """Actual N16 transport/cash unit; not original-count teacher qualification."""
    bundle = run_pilot.runner.run_tiny(original_n=16, updates=0, train=False)
    parameters = bundle["parameters"]
    field = run_pilot.LocalVarianceGrid(
        np.array([1e-4, 1.25]),
        np.array([-4.0, 0.0, 4.0]),
        np.full((2, 3), 0.04),
        parameters,
    )
    dataset = bundle["datasets"]["Heston"]
    arguments = dict(
        parameters=parameters,
        surface=field,
        dataset=dataset,
        caches=bundle["caches"],
        chunk_paths=7,
        wall_cap_seconds=None,
    )
    risk = run_pilot.run_quote_risk_job(**arguments)
    validation = run_pilot.study.select_validation(
        dataset,
        risk["value"],
        generator="Heston",
        universe="U1",
        widths=run_pilot.protocol.candidate_protocol()["hedging"]["band_width_candidates"],
    )
    identity = next(
        r
        for r in run_pilot.protocol.study_roster()["primary_cells"]
        if r["generator"] == "Heston"
        and r["universe"] == "U1"
        and r["policy"] == "greek"
        and r["valuation"] == "Heston"
    )
    pair_arguments = dict(
        base_dataset=dataset,
        refined_dataset=dataset,
        base_risk=risk["value"],
        refined_risk=risk["value"],
        identity=identity,
        validation=validation,
        fits=[],
        refinement_kind="pnl",
        base_risk_source=risk,
        refined_risk_source=risk,
    )
    pair = run_pilot.run_cell_pair_job(**pair_arguments)
    rows = {
        "risk": {"id": "risk", "operation": "quote_risk", "raw": risk, "arguments": arguments},
        "pair": {"id": "pair", "operation": "cell_pair", "raw": pair, "arguments": pair_arguments},
    }
    declared = {}
    for model in ("Heston", "local"):
        caches = bundle["caches"][model.lower()]
        call_id, asian_id = "call:" + model, "asian:" + model
        rows[call_id] = {
            "id": call_id,
            "operation": "call_cache",
            "raw": {
                "kind": "call_cache",
                "value": caches["call"],
                "arguments": run_pilot.pack_inputs(dict(parameters=parameters, surface=field)),
            },
        }
        rows[asian_id] = {
            "id": asian_id,
            "operation": "teacher_grid",
            "raw": {
                "kind": "teacher_grid",
                "model": model,
                "grid": "coarse",
                "original_n": 16,
                "cache": caches["asian"],
            },
        }
        declared[model] = {"call_job_id": call_id, "asian_job_id": asian_id}
    binding = {
        "cell_id": identity["id"],
        "job_id": "pair",
        "base_risk_job_id": "risk",
        "refined_risk_job_id": "risk",
    }
    stage = {
        "model": "Heston",
        "original_n": 16,
        "grid": "coarse",
        "teacher_job_id": "asian:Heston",
        "next_teacher_job_id": "asian:Heston",
        "grid_teacher_job_id": "asian:Heston",
        "cache_bindings": {"pnl": {"base": declared, "refined": declared}},
        "pnl_bindings": {"pnl": [binding]},
    }
    return parameters, field, stage, rows


def test_teacher_stage_saved_risk_sources_bind_actual_cache_arrays_and_cash(monkeypatch, tmp_path):
    parameters, field, stage, rows = _stage_risk_binding_source_unit()
    record = {
        "parameters": parameters,
        "surface": run_pilot.pack_inputs(field),
        "stage_plan": stage,
        "rows": rows,
    }
    record["rows"]["risk"]["arguments"] = run_pilot.pack_inputs(record["rows"]["risk"]["arguments"])
    run_pilot.write_pilot_artifact(tmp_path / "actual", record)
    loaded, _ = run_pilot.read_pilot_artifact(tmp_path / "actual")
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved RNG"))
    for row in loaded["rows"].values():
        if row["operation"] == "quote_risk":
            check_pilot.check_wrapped_operation(row["raw"], "quote_risk", {})
        elif row["operation"] == "cell_pair":
            check_pilot.check_paired_pnl_record(row["raw"])
    checked = check_pilot.check_teacher_stage_risk_sources(
        loaded["parameters"],
        run_pilot.unpack_inputs(loaded["surface"]),
        stage_plan=loaded["stage_plan"],
        rows=loaded["rows"],
    )
    assert checked["bound_pair_count"] == 1
    assert checked["financial_qualification"] == "unknown"
    assert checked["raw_cache_sha256"]["pnl"]["base"]["Heston"]["asian"] == (
        run_pilot.input_identity(rows["asian:Heston"]["raw"]["cache"])
    )


@pytest.mark.parametrize(
    "mutation", ["cache", "risk_producer", "field", "dataset", "validation", "call_parameters"]
)
def test_teacher_stage_refuses_swapped_same_shape_actual_sources(mutation):
    import copy

    parameters, field, stage, rows = _stage_risk_binding_source_unit()
    altered = copy.deepcopy(rows)
    if mutation == "cache":
        wrong = copy.deepcopy(altered["asian:Heston"]["raw"]["cache"])
        wrong["f"].flat[np.flatnonzero(np.isfinite(wrong["f"]))[0]] += 0.1
        assert wrong["f"].shape == altered["asian:Heston"]["raw"]["cache"]["f"].shape
        altered["asian:other"] = {
            "id": "asian:other",
            "operation": "teacher_grid",
            "raw": dict(altered["asian:Heston"]["raw"], cache=wrong),
        }
        stage["cache_bindings"]["pnl"]["base"]["Heston"]["asian_job_id"] = "asian:other"
    elif mutation == "risk_producer":
        altered["risk:other"] = copy.deepcopy(altered["risk"])
        altered["risk:other"]["raw"]["value"]["models"]["heston"]["u2_target"].flat[0] = 0.123
        stage["pnl_bindings"]["pnl"][0]["base_risk_job_id"] = "risk:other"
    elif mutation == "field":
        args = run_pilot.unpack_inputs(altered["risk"]["raw"]["arguments"])
        values = args["surface"].values.copy()
        values[0, 0] += 0.001
        args["surface"] = run_pilot.LocalVarianceGrid(
            args["surface"].times,
            args["surface"].z_nodes,
            values,
            parameters,
            args["surface"].wing_boundaries,
        )
        altered["risk"]["raw"]["arguments"] = run_pilot.pack_inputs(args)
        altered["risk"]["arguments"] = args
    elif mutation == "dataset":
        args = run_pilot.unpack_inputs(altered["risk"]["raw"]["arguments"])
        args["dataset"] = copy.deepcopy(args["dataset"])
        args["dataset"]["prices"][0, 0, 0] += 0.01
        altered["risk"]["raw"]["arguments"] = run_pilot.pack_inputs(args)
        altered["risk"]["arguments"] = args
    elif mutation == "call_parameters":
        from dataclasses import replace

        altered["call:Heston"]["raw"]["arguments"]["parameters"] = replace(parameters, rate=0.04)
    else:
        altered["pair"]["arguments"]["validation"] = copy.deepcopy(
            altered["pair"]["arguments"]["validation"]
        )
        altered["pair"]["arguments"]["validation"]["candidates"][0]["reason"] = "swapped"
    with pytest.raises(ValueError, match=r"stage.*(cache|producer|field|dataset|validation)"):
        check_pilot.check_teacher_stage_risk_sources(
            parameters, field, stage_plan=stage, rows=altered
        )


def test_saved_risk_transport_success_does_not_qualify_a_reduced_teacher_denominator():
    parameters, field, stage, rows = _stage_risk_binding_source_unit()
    result = check_pilot.check_teacher_stage_risk_sources(
        parameters,
        field,
        stage_plan=stage,
        rows=rows,
    )
    assert result["financial_qualification"] == "unknown"
    with pytest.raises(ValueError, match=r"actual1024coarse"):
        check_pilot._teacher_stage_cache_geometry(stage, rows)


@pytest.mark.parametrize("mutation", ["other_model", "candidate_refinement", "common_call"])
def test_stage_cache_geometry_rejects_wrong_coordinate_refinement(mutation):
    import copy

    # Geometry-only typed metadata; no numerical/driver qualification is asserted.
    stage = {
        "model": "Heston",
        "original_n": 1024,
        "grid": "coarse",
        "teacher_job_id": "H:1024coarse",
        "next_teacher_job_id": "H:4096coarse",
        "grid_teacher_job_id": "H:1024high",
    }
    rows = {}
    for identifier, model, n, grid in [
        ("H:1024coarse", "Heston", 1024, "coarse"),
        ("H:4096coarse", "Heston", 4096, "coarse"),
        ("H:1024high", "Heston", 1024, "high"),
        ("L:1024coarse", "local", 1024, "coarse"),
        ("L:4096coarse", "local", 4096, "coarse"),
    ]:
        rows[identifier] = {
            "raw": {"model": model, "original_n": n, "grid": grid, "cache": {"original_N": n}}
        }
    base = {
        "Heston": {"call_job_id": "callH", "asian_job_id": "H:1024coarse"},
        "local": {"call_job_id": "callL", "asian_job_id": "L:1024coarse"},
    }
    stage["cache_bindings"] = {}
    for kind in ("SDE", "teacher_N", "teacher_grid", "position", "pnl"):
        refined = copy.deepcopy(base)
        if kind == "teacher_N":
            refined["Heston"]["asian_job_id"] = "H:4096coarse"
        elif kind == "teacher_grid":
            refined["Heston"]["asian_job_id"] = "H:1024high"
        stage["cache_bindings"][kind] = {"base": copy.deepcopy(base), "refined": refined}
    check_pilot._teacher_stage_cache_geometry(stage, rows)
    if mutation == "other_model":
        stage["cache_bindings"]["teacher_N"]["refined"]["local"]["asian_job_id"] = "L:4096coarse"
    elif mutation == "candidate_refinement":
        stage["cache_bindings"]["teacher_N"]["refined"]["Heston"]["asian_job_id"] = "H:1024coarse"
    else:
        stage["cache_bindings"]["position"]["refined"]["local"]["call_job_id"] = "narrowCall"
    with pytest.raises(ValueError, match=r"stage.*(cache|refinement)"):
        check_pilot._teacher_stage_cache_geometry(stage, rows)


def _selected_teacher_inputs_source_unit(monkeypatch, *, chosen_n=65536, model="Heston"):
    """Typed metadata only; no original-count financial teacher is fabricated."""
    import copy

    original = run_pilot.protocol.candidate_protocol()
    stages, teachers, drivers = [], {}, {}
    ladder = original["teacher"]["n_candidates"]
    for n in ladder:
        driver_id = f"driver:{n}"
        driver = {
            "kind": "teacher_driver",
            "original_n": n,
            "seed": original["seeds"]["teacher"][0 if model == "Heston" else 1],
            "teacher_reference": None,
            "global_driver_id": str(n).zfill(64),
            "calendar_times": np.arange(769) / 768,
            "processed_n": n,
            "unexecuted_n": 0,
        }
        drivers[driver_id] = {
            "id": driver_id,
            "operation": "teacher_driver",
            "status": "executed",
            "raw": driver,
        }
        for grid in ("coarse", "high"):
            identifier = f"teacher:{n}:{grid}"
            teachers[identifier] = {
                "id": identifier,
                "operation": "teacher_domain_selection",
                "status": "executed",
                "raw": {
                    "kind": "teacher_grid",
                    "model": model,
                    "original_n": n,
                    "grid": grid,
                    "seed": driver["seed"],
                    "teacher_reference": None,
                    "driver": driver,
                    "cache": {"model": model.lower(), "original_N": n, "f": np.array([[float(n)]])},
                    "domain_selection": {"qualification": "unknown"},
                },
            }
    maximum = ladder[-1]
    ref_purpose = {
        "reference_rule": "independent_reserved_stream_grid_max",
        "stream_namespace": "oracle",
        "seed": original["seeds"]["oracle"][0 if model == "Heston" else 1],
    }
    reference_driver = copy.deepcopy(drivers[f"driver:{maximum}"]["raw"])
    reference_driver.update(
        seed=ref_purpose["seed"], teacher_reference=ref_purpose, global_driver_id="f" * 64
    )
    drivers["driver:reference"] = {
        "id": "driver:reference",
        "operation": "teacher_driver",
        "status": "executed",
        "raw": reference_driver,
    }
    for grid in ("coarse", "high"):
        teachers[f"reference:{grid}"] = copy.deepcopy(teachers[f"teacher:{maximum}:{grid}"])
        teachers[f"reference:{grid}"]["id"] = f"reference:{grid}"
        teachers[f"reference:{grid}"]["raw"].update(
            seed=ref_purpose["seed"], teacher_reference=ref_purpose, driver=reference_driver
        )
    for ni, n in enumerate(ladder):
        next_n = ladder[min(ni + 1, len(ladder) - 1)]
        for grid in ("coarse", "high"):
            gate_id = f"gate:{n}:{grid}"
            bindings = {
                "teacher_job_id": f"teacher:{n}:{grid}",
                "next_teacher_job_id": f"teacher:{next_n}:{grid}"
                if n < maximum
                else f"reference:{grid}",
                "grid_teacher_job_id": f"teacher:{n}:{'high' if grid == 'coarse' else 'coarse'}",
                "teacher_driver_job_id": f"driver:{n}",
            }
            states = [
                {"id": row["id"], "job_id": gate_id + ":" + row["id"]}
                for row in run_pilot.execution.execution_candidate()["pilot_cases"]
                if row["kind"] == "state" and row["identity"]["model"] == model
            ]
            dates = [{"date_index": j, "job_id": gate_id + f":date{j}"} for j in range(12)]
            stage_plan = dict(
                bindings, original_n=n, grid=grid, state_bindings=states, date_bindings=dates
            )
            gate = {
                "kind": "teacher_candidate_gate",
                "model": model,
                "original_n": n,
                "grid": grid,
                "qualification": "qualified"
                if n == chosen_n and chosen_n != maximum
                else "unknown",
            }
            stages.append(
                dict(
                    bindings,
                    id=gate_id,
                    original_n=n,
                    grid=grid,
                    state_bindings=states,
                    date_bindings=dates,
                    job={"id": gate_id, "status": "executed", "raw": gate},
                    arguments={
                        "parameters": None,
                        "surface": None,
                        "stage_plan": stage_plan,
                        "evidence": [],
                    },
                )
            )

    def metadata_gate(*args, stage_plan, **kwargs):
        return next(
            row["job"]["raw"]
            for row in stages
            if row["original_n"] == stage_plan["original_n"] and row["grid"] == stage_plan["grid"]
        )

    monkeypatch.setattr(check_pilot, "calculate_teacher_candidate_gate", metadata_gate)
    arguments = dict(
        model=model,
        stages=stages,
        teachers=teachers,
        drivers=drivers,
        selection_rule=run_pilot.teacher_selection_rule(model),
    )
    selector = {
        "id": "selection:Heston",
        "operation": "teacher_selection",
        "status": "executed",
        "raw": run_pilot.run_teacher_selection_job(**arguments),
    }
    return dict(
        model=model,
        selector=selector,
        selection_arguments=arguments,
        teachers=teachers,
        drivers=drivers,
    )


@pytest.mark.parametrize("purpose", ["principal", "teacher_N", "teacher_grid", "extra_dates"])
def test_selected_teacher_inputs_bind_actual_purpose_without_principal_substitution(
    monkeypatch, tmp_path, purpose
):
    arguments = _selected_teacher_inputs_source_unit(monkeypatch)
    result = run_pilot.run_teacher_selected_inputs_job(purpose=purpose, **arguments)
    assert result["financial_qualification"] == "unknown"
    assert result["availability"] == "available"
    assert result["original_n"] == 65536
    expected = {
        "principal": "teacher:65536:coarse",
        "extra_dates": "teacher:65536:coarse",
        "teacher_N": "reference:coarse",
        "teacher_grid": "teacher:65536:high",
    }
    assert result["selected_teacher_job_id"] == expected[purpose]
    if purpose == "teacher_N":
        assert (
            result["driver"]["global_driver_id"]
            != arguments["drivers"]["driver:65536"]["raw"]["global_driver_id"]
        )
    run_pilot.write_pilot_artifact(tmp_path / "saved", result)
    saved, _ = run_pilot.read_pilot_artifact(tmp_path / "saved")
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved adapter RNG"))
    checked = check_pilot.check_teacher_selected_inputs_record(saved, purpose=purpose, **arguments)
    assert checked["integrity"] == "pass"
    assert checked["financial_qualification"] == "unknown"


@pytest.mark.parametrize(
    "mutation", ["principal_as_reference", "driver", "selected_n", "returned_cache"]
)
def test_selected_teacher_inputs_refuse_wrong_purpose_or_changed_saved_binding(
    monkeypatch, mutation
):
    import copy

    arguments = _selected_teacher_inputs_source_unit(monkeypatch)
    result = run_pilot.run_teacher_selected_inputs_job(purpose="teacher_N", **arguments)
    altered = copy.deepcopy(arguments)
    if mutation == "principal_as_reference":
        altered["selection_arguments"]["stages"][-2]["next_teacher_job_id"] = "teacher:65536:coarse"
        with pytest.raises(ValueError, match=r"selected|reference|stage"):
            run_pilot.run_teacher_selected_inputs_job(purpose="teacher_N", **altered)
    elif mutation == "driver":
        # Break the fixture's shared object alias: swap the driver producer while
        # preserving the actual teacher's embedded original driver.
        altered["drivers"]["driver:reference"]["raw"] = copy.deepcopy(
            altered["drivers"]["driver:reference"]["raw"]
        )
        altered["drivers"]["driver:reference"]["raw"]["global_driver_id"] = "e" * 64
        with pytest.raises(ValueError, match=r"selected|driver|stage"):
            run_pilot.run_teacher_selected_inputs_job(purpose="teacher_N", **altered)
    else:
        bad = copy.deepcopy(result)
        if mutation == "selected_n":
            bad["original_n"] = 16384
        else:
            bad["cache"]["f"][0, 0] += 1
        with pytest.raises(ValueError, match=r"selected"):
            check_pilot.check_teacher_selected_inputs_record(bad, purpose="teacher_N", **arguments)


def test_selected_reference_unavailable_keeps_actual_cap_and_never_uses_principal(monkeypatch):
    arguments = _selected_teacher_inputs_source_unit(monkeypatch)
    target = arguments["teachers"]["reference:coarse"]
    target.update(status="failed_at_declared_cap", cap_evidence={"actual": True})
    target["raw"]["cache"] = None
    # The principal remains actually available, but it is not this operation's purpose.
    result = run_pilot.run_teacher_selected_inputs_job(purpose="teacher_N", **arguments)
    assert result["availability"] == "unavailable"
    assert result["cache"] is None
    assert result["original_n"] == 65536
    assert result["parent_unavailable_job_ids"] == ["reference:coarse"]
    assert result["financial_qualification"] == "unknown"


def _conditional_diagnostic_source_job(selector, *, model="Heston"):
    source = {"teacher_selection_job_id": selector["id"], "model": model}
    branches = {
        str(n): {
            "path_steps": n * 768,
            "total_path_steps": n * 768 * 2,
            "expanded_bytes": n * 128,
            "rate_source": "independently_reviewed_estimate",
        }
        for n in (1024, 4096, 16384, 65536)
    }
    return {
        "id": "diagnostic:" + model,
        "operation": "teacher_diagnostic",
        "original_n": None,
        "original_n_source": source,
        "diagnostic_cases": [{"id": "date24"}, {"id": "date48"}],
        "prediction": {
            "path_steps": 65536 * 768,
            "total_path_steps": 65536 * 768 * 2,
            "expanded_bytes": 65536 * 128,
            "rate_source": "independently_reviewed_estimate",
            "by_original_n": branches,
        },
        "arguments": {"selector": {"job_record": selector["id"]}},
    }


@pytest.mark.parametrize("n", [1024, 4096, 16384, 65536])
def test_conditional_diagnostic_prediction_selects_exact_prior_original_n_branch(monkeypatch, n):
    arguments = _selected_teacher_inputs_source_unit(monkeypatch, chosen_n=n)
    selected = run_pilot.run_teacher_selected_inputs_job(purpose="extra_dates", **arguments)
    job = _conditional_diagnostic_source_job(arguments["selector"])
    actual = dict(
        model="Heston",
        original_n=n,
        seed=run_pilot.protocol.candidate_protocol()["seeds"]["teacher"][0],
        cases=job["diagnostic_cases"],
        selector=arguments["selector"],
        selected_inputs=selected,
        driver=selected["driver"],
    )
    size = run_pilot._job_identity(job, actual)
    assert size["original_n"] == n
    assert size["path_steps"] == n * 768
    assert size["total_path_steps"] == n * 768 * 2
    assert size["selected_prediction_sha256"] == run_pilot.input_identity(
        job["prediction"]["by_original_n"][str(n)]
    )
    assert size["original_n_binding"]["selector_raw_sha256"] == run_pilot.input_identity(
        arguments["selector"]["raw"]
    )
    wrong = dict(actual, original_n=1024 if n != 1024 else 4096)
    with pytest.raises(ValueError, match=r"conditional.*(N|denominator)|selected"):
        run_pilot._job_identity(job, wrong)


def test_conditional_diagnostic_dependency_cap_retains_selected_n_without_numerical_execution(
    monkeypatch,
):
    arguments = _selected_teacher_inputs_source_unit(monkeypatch, chosen_n=16384)
    selector = arguments["selector"]
    job = _conditional_diagnostic_source_job(selector)
    job["arguments"]["driver"] = {"job": "failed-adapter", "path": ["driver"]}
    parent = {
        "id": "failed-adapter",
        "operation": "teacher_selected_inputs",
        "status": "failed_at_declared_cap",
        "raw": {"original_n": 16384},
        "source_sha256": "a" * 64,
        "input_bindings": {"actual": "b" * 64},
        "timing_events": {
            "wall_start_ns": 1,
            "wall_stop_ns": 2,
            "cpu_start_ns": 1,
            "cpu_stop_ns": 2,
        },
        "expense": {"id": "actual"},
        "cap_evidence": {"actual": True},
    }
    jobs = {selector["id"]: selector, parent["id"]: parent}
    raw = run_pilot._dependency_cap_raw(job, run_pilot._dependency_ids(job["arguments"]), jobs)
    assert raw["original_n"] == raw["unexecuted_n"] == 16384
    assert raw["executed_n"] == 0
    assert raw["original_n_binding"]["teacher_selection_job_id"] == selector["id"]
    assert raw["parent_cap_job_ids"] == ["failed-adapter"]


@pytest.mark.parametrize("mutation", ["missing_N", "smaller_max", "wrong_source"])
def test_conditional_diagnostic_refuses_unplanned_prediction_or_selector_source(
    monkeypatch, mutation
):
    arguments = _selected_teacher_inputs_source_unit(monkeypatch)
    selected = run_pilot.run_teacher_selected_inputs_job(purpose="extra_dates", **arguments)
    job = _conditional_diagnostic_source_job(arguments["selector"])
    actual = dict(
        model="Heston",
        original_n=65536,
        seed=run_pilot.protocol.candidate_protocol()["seeds"]["teacher"][0],
        cases=job["diagnostic_cases"],
        selector=arguments["selector"],
        selected_inputs=selected,
        driver=selected["driver"],
    )
    if mutation == "missing_N":
        del job["prediction"]["by_original_n"]["16384"]
    elif mutation == "smaller_max":
        job["prediction"]["expanded_bytes"] = 1024
    else:
        job["original_n_source"]["teacher_selection_job_id"] = "not-original-selector"
    with pytest.raises(ValueError, match=r"conditional|selected"):
        run_pilot._job_identity(job, actual)


def test_selected_inputs_actual_dispatch_cap_resume_preserves_true_parent_and_saved_inspection(
    monkeypatch, tmp_path
):
    import copy

    metadata = _selected_teacher_inputs_source_unit(monkeypatch)
    inputs, plan = _lifecycle_source_plan(monkeypatch)
    # All stage arithmetic in this unit is explicitly typed metadata; the parent
    # cap below is an actual run_teacher_grid_job clock boundary, not a flag.
    stages, teachers, drivers = (
        metadata["selection_arguments"][k] for k in ("stages", "teachers", "drivers")
    )
    parent = copy.deepcopy(plan["jobs"][0])
    parent.update(
        id="actual-reference-grid",
        operation="teacher_grid",
        original_n=65536,
        expense_id="actual-reference-grid:actual",
    )
    parent["arguments"] = {
        "parameters": {"input": "parameters"},
        "surface": None,
        "model": "Heston",
        "grid": "coarse",
        "original_n": 65536,
        "seed": run_pilot.protocol.candidate_protocol()["seeds"]["oracle"][0],
        "chunk_paths": 16,
        "evaluation_domains": [None] * 12,
        "teacher_reference": {
            "reference_rule": "independent_reserved_stream_grid_max",
            "stream_namespace": "oracle",
            "seed": run_pilot.protocol.candidate_protocol()["seeds"]["oracle"][0],
        },
    }
    parent["teacher_reference"] = parent["arguments"]["teacher_reference"]
    parent["prediction"]["path_steps"] = 65536 * 768
    # The entire original grid remains declared even though the actual tiny
    # source-test budget expires before its first numerical node.
    count = 12 * len(run_pilot.teacher_axes("coarse", "Heston")["state"])
    parent["prediction"].update(
        total_path_steps=65536 * 768 * count,
        financial_child_count=count,
        child_boundary="original_teacher_node",
    )
    domain = copy.deepcopy(plan["jobs"][2])
    domain.update(
        id="reference:coarse",
        operation="teacher_domain_selection",
        original_n=65536,
        expense_id="reference:coarse:actual",
        arguments={
            "teacher": {"job": parent["id"]},
            "selection_rule": run_pilot.teacher_domain_rule("Heston"),
        },
    )
    controls = copy.deepcopy(teachers)
    controls["reference:coarse"] = {"job_record": domain["id"]}
    selector = copy.deepcopy(plan["jobs"][2])
    selector.update(
        id="selection:Heston",
        operation="teacher_selection",
        original_n=None,
        expense_id="selection:Heston:actual",
        arguments=dict(
            model="Heston",
            stages=stages,
            teachers=controls,
            drivers=drivers,
            selection_rule=run_pilot.teacher_selection_rule("Heston"),
        ),
    )
    adapter = copy.deepcopy(plan["jobs"][2])
    adapter.update(
        id="selected-reference",
        operation="teacher_selected_inputs",
        original_n=None,
        original_n_source={
            "teacher_selection_job_id": selector["id"],
            "model": "Heston",
            "purpose": "teacher_N",
        },
        expense_id="selected-reference:actual",
        arguments={
            "model": "Heston",
            "purpose": "teacher_N",
            "selector": {"job_record": selector["id"]},
            "selection_arguments": {"job_arguments": selector["id"]},
            "teachers": controls,
            "drivers": drivers,
        },
    )
    downstream = copy.deepcopy(plan["jobs"][1])
    downstream.update(
        id="reference-dependent",
        expense_id="reference-dependent:actual",
        arguments={"actual_cache": {"job": adapter["id"], "path": ["cache"]}},
    )
    parent["cap_scope"] = {
        "job_ids": [parent["id"], domain["id"], selector["id"], adapter["id"], downstream["id"]],
        "case_ids": [],
        "attempt_ids": [],
        "expense_id": parent["expense_id"],
    }
    plan["jobs"] = [parent, domain, selector, adapter, downstream, plan["jobs"][2]]
    # Enforce no new RNG: the actual financial worker must stop at its measured cap.
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("cap-source RNG"))
    snapshot = run_pilot.run_pilot(tmp_path, inputs=inputs, locked_plan=plan)
    jobs = {row["id"]: row for row in snapshot["jobs"]}
    assert jobs[parent["id"]]["status"] == "failed_at_declared_cap"
    assert jobs[adapter["id"]]["status"] == "unexecuted_dependency_cap"
    assert jobs[adapter["id"]]["raw"]["original_n"] == 65536
    assert jobs[adapter["id"]]["raw"]["selected_inputs_inspection"]["cache"] is None
    assert jobs[adapter["id"]]["raw"]["parent_cap_job_ids"] == [parent["id"]]
    assert jobs[downstream["id"]]["status"] == "unexecuted_dependency_cap"
    checked = check_pilot.check_dependency_cap_job(
        jobs[adapter["id"]], adapter, plan, jobs, inputs=inputs
    )
    assert checked["financial_qualification"] == "unknown"
    resumed = run_pilot.run_pilot(tmp_path, inputs=inputs, locked_plan=plan, resume=True)
    resumed_jobs = {row["id"]: row for row in resumed["jobs"]}
    assert run_pilot.input_identity(resumed_jobs[adapter["id"]]["raw"]) == run_pilot.input_identity(
        jobs[adapter["id"]]["raw"]
    )
    bad = copy.deepcopy(jobs)
    bad[adapter["id"]]["raw"]["selected_inputs_inspection"]["cache"] = teachers[
        "teacher:65536:coarse"
    ]["raw"]["cache"]
    with pytest.raises(ValueError, match=r"selected-purpose"):
        check_pilot.check_dependency_cap_job(bad[adapter["id"]], adapter, plan, bad, inputs=inputs)


def _conditional_attempt_sources_unit(monkeypatch):
    """Transport original selected metadata; this fixture certifies no financial teacher."""
    import copy

    jobs, selectors, adapters = {}, {}, {}
    chosen = {"Heston": 1024, "local": 16384}
    for model in ("Heston", "local"):
        supplied = _selected_teacher_inputs_source_unit(
            monkeypatch, chosen_n=chosen[model], model=model
        )
        arguments = supplied["selection_arguments"]
        originals = (
            set(arguments["teachers"])
            | set(arguments["drivers"])
            | {row["id"] for row in arguments["stages"]}
            | {supplied["selector"]["id"]}
        )
        names = {identifier: model + ":" + identifier for identifier in originals}

        def rename(value, names=names):
            if isinstance(value, dict):
                return {names.get(key, key): rename(item, names) for key, item in value.items()}
            if isinstance(value, list):
                return [rename(item, names) for item in value]
            if isinstance(value, str):
                return names.get(value, value)
            return value

        arguments = rename(copy.deepcopy(arguments))

        def metadata_gate(*a, stage_plan, saved_stages=arguments["stages"], **kw):
            return next(
                row["job"]["raw"]
                for row in saved_stages
                if row["original_n"] == stage_plan["original_n"]
                and row["grid"] == stage_plan["grid"]
            )

        monkeypatch.setattr(check_pilot, "calculate_teacher_candidate_gate", metadata_gate)
        selector = {
            "id": names[supplied["selector"]["id"]],
            "operation": "teacher_selection",
            "status": "executed",
            "raw": run_pilot.run_teacher_selection_job(**arguments),
        }
        jobs.update(arguments["teachers"])
        jobs.update(arguments["drivers"])
        jobs[selector["id"]] = selector
        selectors[model] = selector["id"]
        adapters[model] = {}
        for purpose in ("principal", "teacher_N", "teacher_grid"):
            identifier = f"adapter:{model}:{purpose}"
            result = run_pilot.run_teacher_selected_inputs_job(
                model=model,
                purpose=purpose,
                selector=selector,
                selection_arguments=arguments,
                teachers=arguments["teachers"],
                drivers=arguments["drivers"],
            )
            jobs[identifier] = {
                "id": identifier,
                "operation": "teacher_selected_inputs",
                "status": "executed",
                "raw": result,
            }
            adapters[model][purpose] = identifier
    return jobs, selectors, adapters


@pytest.mark.parametrize("identifier", ["domain_selection", "frequency:24", "frequency:48"])
def test_limited_selected_count_attempts_derive_max_both_models_without_changing_path_n(
    monkeypatch, identifier
):
    jobs, selectors, _ = _conditional_attempt_sources_unit(monkeypatch)
    plan = {
        "id": identifier,
        "original_n": None,
        "expense_id": "original",
        "original_n_source": {
            "teacher_selection_job_ids": selectors,
            "rule": "max_selected_teacher_N",
        },
    }
    concrete = check_pilot.concrete_original_n_plan(plan, jobs)
    assert concrete["original_n"] == 16384
    assert concrete["prior_template_sha256"] == run_pilot.input_identity(plan)
    assert concrete["selector_raw_sha256"] != concrete["prior_template_sha256"]
    assert (
        check_pilot.concrete_original_n_plan({"id": "fixed-path", "original_n": 1024}, jobs)[
            "original_n"
        ]
        == 1024
    )


@pytest.mark.parametrize("kind", ["teacher_N", "teacher_grid"])
def test_conditional_refinement_binds_only_actual_selected_purposes_and_fixed_original_work(
    monkeypatch, kind
):
    jobs, _, adapters = _conditional_attempt_sources_unit(monkeypatch)
    source = {m: {p: adapters[m][p] for p in ("principal", kind)} for m in adapters}
    fixed = ["actual-market", *[f"actual-pair:{i}" for i in range(8)]]
    for identifier in fixed:
        jobs[identifier] = {"id": identifier, "status": "executed", "raw": {"original_n": 1024}}
    binding = {
        "id": f"refinement:{kind}:Heston",
        "job_ids_source": {"selected_inputs_job_ids": source, "fixed_job_ids": fixed},
    }
    concrete = check_pilot.concrete_attempt_binding(binding, jobs)
    expected = fixed + [
        jobs[source[m][p]]["raw"]["selected_teacher_job_id"]
        for m in ("Heston", "local")
        for p in ("principal", kind)
    ]
    assert concrete["job_ids"] == expected
    if kind == "teacher_grid":
        assert all("65536" not in identifier for identifier in concrete["job_ids"])
    plan = {
        "id": binding["id"],
        "original_n": None,
        "expense_id": "original",
        "original_n_source": {"selected_inputs_job_ids": source, "rule": "max_selected_purpose_N"},
    }
    assert check_pilot.concrete_original_n_plan(plan, jobs)["original_n"] == (
        65536 if kind == "teacher_N" else 16384
    )
    controls = [source[m][p] for m in ("Heston", "local") for p in ("principal", kind)]
    controls += [
        jobs[source[m]["principal"]]["raw"]["selector_job_id"] for m in ("Heston", "local")
    ]
    assert concrete["control_job_ids"] == controls
    spec = {"required_attempt_binding": binding}
    assert (
        check_pilot.concrete_execution_specification(spec, jobs)["required_job_ids"]
        == expected + controls
    )


@pytest.mark.parametrize(
    "mutation", ["fixed_count_scope", "wrong_purpose", "missing_source", "target_sha"]
)
def test_conditional_attempt_source_gaps_raise_and_cannot_become_caps(monkeypatch, mutation):
    import copy

    jobs, selectors, adapters = _conditional_attempt_sources_unit(monkeypatch)
    source = {m: {p: adapters[m][p] for p in ("principal", "teacher_N")} for m in adapters}
    if mutation == "fixed_count_scope":
        bad = {
            "id": "Q:one_step:Heston",
            "original_n": None,
            "original_n_source": {
                "teacher_selection_job_ids": selectors,
                "rule": "max_selected_teacher_N",
            },
        }
        with pytest.raises(ValueError, match=r"conditional.*scope"):
            check_pilot.concrete_original_n_plan(bad, jobs)
        return
    bad_jobs = copy.deepcopy(jobs)
    if mutation == "wrong_purpose":
        source["Heston"]["teacher_N"] = adapters["Heston"]["principal"]
    elif mutation == "missing_source":
        del bad_jobs[adapters["local"]["teacher_N"]]
    else:
        bad_jobs[adapters["Heston"]["teacher_N"]]["raw"]["selected_teacher_raw_sha256"] = "0" * 64
    binding = {
        "id": "refinement:teacher_N:Heston",
        "job_ids_source": {"selected_inputs_job_ids": source, "fixed_job_ids": []},
    }
    with pytest.raises(ValueError, match=r"conditional|selected"):
        check_pilot.concrete_attempt_binding(binding, bad_jobs)


def _native_q_source_unit(model, *, failed=False):
    from hullkit._heston_local_surface import LocalVarianceGrid
    from scipy.special import ndtr

    parameters = HestonParameters(100.0, 0.03, 0.0, 0.04, 2.0, 0.04, 0.3, -0.7)
    date = 0.25
    times = date + np.array([0, 1, 2, 4, 8]) / 1536
    states = np.linspace(0.00001, 0.5, 8) if model == "Heston" else np.linspace(0.25, 4.0, 8)
    spots = np.geomspace(40.0, 250.0, 8)
    variance = states if model == "Heston" else 0.04 * states
    tau = (1.25 - times)[:, None, None]
    stock = spots[None, :, None]
    sig = np.sqrt(tau * variance[None, None, :])
    d1 = (np.log(stock / 100) + (0.03 + variance[None, None, :] / 2) * tau) / sig
    values = stock * ndtr(d1) - 100 * np.exp(-0.03 * tau) * ndtr(d1 - sig)
    # An analytic arithmetic fixture, never a Heston/local reference-price claim.
    cache = {
        "model": model.lower(),
        "dates": times,
        "spot_nodes": spots,
        "state_nodes": states,
        "values": values,
        "rate": 0.03,
        "dividend_yield": 0.0,
        "strike": 100.0,
        "maturity": 1.25,
        "price_error": np.nan,
        "derivative_error": np.nan,
        "reference_status": "unmeasured",
        "support_mask": np.isfinite(values),
        "interpolation": "not_a_knot_tensor_cubic",
        "diagnostics": [{"method": "independent_analytic_toy_source_unit"}],
    }
    surface = (
        None
        if model == "Heston"
        else LocalVarianceGrid(
            np.array([0.001, 1.25]), np.array([-12.0, 12.0]), np.full((2, 2), 0.04), parameters
        )
    )
    initial = np.full(32, 100.0)
    if failed:
        initial[0] = np.nan
    return run_pilot.run_q_job(
        parameters,
        surface,
        model=model,
        seed=913,
        original_n=32,
        chunk_paths=7,
        call_cache=cache,
        date=date,
        spot=initial,
        state=0.04 if model == "Heston" else 1.0,
        bin_edges=[90.0, 100.0, 110.0],
        state_id=f"source_unit:{model}:{failed}",
    )


@pytest.mark.parametrize("model", ["Heston", "local"])
@pytest.mark.parametrize("failed", [False, True])
def test_native_q_scalar_local_contract_saved_empty_cash_and_failures(
    tmp_path, monkeypatch, model, failed
):
    q = _native_q_source_unit(model, failed=failed)
    assert q["original_n"] == 32 and q["status"] == "executed"
    assert sum(row["path_steps"] for row in q["chunks"]) == 32 * 4
    assert all(row["normal"].shape[1:] == (8, 2) for row in q["chunks"])
    if model == "local":
        np.testing.assert_allclose(q["states"], 1.0)
    assert q["path_mask"].sum() == 32 - int(failed)
    if failed:
        assert q["failure_reasons"][0] == "original_one_step_SDE_failure"
        assert np.isnan(q["increments"][0]).all()
    raw = run_pilot.run_empty_claim_job(q)
    run_pilot.write_pilot_artifact(tmp_path / "empty", run_pilot.pack_inputs(raw))
    saved, _ = run_pilot.read_pilot_artifact(tmp_path / "empty")
    saved = run_pilot.unpack_inputs(saved)
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **kw: pytest.fail("saved Q RNG"))
    monkeypatch.setattr(run_pilot, "run_q_job", lambda *a, **kw: pytest.fail("saved Q simulation"))
    checked = check_pilot.check_empty_claim_record(saved)
    assert checked["original_n"] == 32 and checked["financial_qualification"] == "unknown"
    assert checked["Q_check"]["whole"]["qualification"] == "unknown"
    for row, column in zip(saved["rows"], (4, 3, 2), strict=True):
        expected = (
            q["quoted_calls"][:, column] * np.exp(-q["rate"] * (q["times"][column] - q["times"][0]))
            - q["quoted_calls"][:, 0]
        )
        np.testing.assert_allclose(
            row["raw"]["discounted_pnl"], expected, rtol=1e-12, atol=1e-12, equal_nan=True
        )
        if failed:
            assert not row["raw"]["path_mask"][0] and np.isnan(row["raw"]["discounted_pnl"][0])


@pytest.mark.parametrize("model", ["Heston", "local"])
def test_native_q_saved_replay_refuses_self_consistent_sde_record_change(monkeypatch, model):
    q = _native_q_source_unit(model)
    q["chunks"][0]["raw_records"][0]["records"]["variance"][:, 1] += 0.001
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **kw: pytest.fail("saved Q RNG"))
    with pytest.raises(ValueError, match=r"Q.*saved|Q.*one.step"):
        check_pilot.check_q_record(q)


@pytest.mark.parametrize("model", ["Heston", "local"])
def test_actual_selector_own_cap_preserves_control_n_and_no_numerical_inputs(
    monkeypatch, tmp_path, model
):
    import copy

    metadata = _selected_teacher_inputs_source_unit(monkeypatch, model=model)
    inputs, plan = _lifecycle_source_plan(monkeypatch)
    template = plan["jobs"][-1]
    selector = copy.deepcopy(template)
    selector.update(
        id="selection:" + model,
        operation="teacher_selection",
        original_n=None,
        expense_id="selector:actual",
        arguments=metadata["selection_arguments"],
    )
    selector["budget"]["wall_seconds"] = 1e-12
    adapter = copy.deepcopy(template)
    adapter.update(
        id="selected-principal",
        operation="teacher_selected_inputs",
        original_n=None,
        original_n_source={
            "teacher_selection_job_id": selector["id"],
            "model": model,
            "purpose": "principal",
        },
        expense_id="adapter:actual",
        arguments=dict(
            model=model,
            purpose="principal",
            selector={"job_record": selector["id"]},
            selection_arguments={"job_arguments": selector["id"]},
            teachers=metadata["teachers"],
            drivers=metadata["drivers"],
        ),
    )
    diagnostic = copy.deepcopy(template)
    diagnostic.update(_conditional_diagnostic_source_job(selector, model=model))
    diagnostic["expense_id"] = "diagnostic:actual"
    diagnostic["arguments"].update(
        parameters={"input": "parameters"},
        surface=None,
        model=model,
        original_n={"job": adapter["id"], "path": ["original_n"]},
        selected_inputs={"job": adapter["id"]},
        driver={"job": adapter["id"], "path": ["driver"]},
        seed=run_pilot.protocol.candidate_protocol()["seeds"]["teacher"][
            0 if model == "Heston" else 1
        ],
        chunk_paths=16,
        cases=diagnostic["diagnostic_cases"],
    )
    selector["cap_scope"] = {
        "job_ids": [selector["id"], adapter["id"], diagnostic["id"]],
        "case_ids": [],
        "attempt_ids": [],
        "expense_id": selector["expense_id"],
    }
    plan["jobs"] = [selector, adapter, diagnostic, template]
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("selector cap RNG"))
    snapshot = run_pilot.run_pilot(tmp_path, inputs=inputs, locked_plan=plan)
    jobs = {row["id"]: row for row in snapshot["jobs"]}
    parent = jobs[selector["id"]]
    assert parent["status"] == "failed_at_declared_cap"
    assert parent["raw"]["kind"] == "teacher_selection" and parent["raw"]["original_n"] == 65536
    assert jobs["independent"]["status"] == "executed"
    checked = check_pilot.check_capped_job_raw(
        parent, context={"resolved_arguments": metadata["selection_arguments"]}
    )
    assert checked["original_n"] == 65536 and checked["financial_qualification"] == "unknown"
    for job in (adapter, diagnostic):
        row = jobs[job["id"]]
        assert row["status"] == "unexecuted_dependency_cap"
        assert row["raw"]["original_n"] == row["raw"]["unexecuted_n"] == 65536
        assert row["raw"]["executed_n"] == 0
        assert row["raw"]["parent_cap_job_ids"] == [selector["id"]]
        checked = check_pilot.check_dependency_cap_job(row, job, plan, jobs, inputs=inputs)
        assert checked["financial_qualification"] == "unknown"
    selected = jobs[adapter["id"]]["raw"]["selected_inputs_inspection"]
    assert (
        selected["availability"] == "unavailable"
        and selected["cache"] is selected["driver"] is None
    )
    assert selected["parent_unavailable_job_ids"] == [selector["id"]]
    assert selected["selector_raw_sha256"] == run_pilot.input_identity(parent["raw"])
    resumed = run_pilot.run_pilot(tmp_path, inputs=inputs, locked_plan=plan, resume=True)
    assert run_pilot.input_identity(resumed["jobs"]) == run_pilot.input_identity(snapshot["jobs"])
    bad = copy.deepcopy(parent)
    bad["cap_evidence"]["consumed"] = 0.0
    with pytest.raises(ValueError, match=r"selector.*cap|cap.*selector"):
        run_pilot._selector_job_n_binding(adapter, bad)
    original_arguments = run_pilot._resolve(
        {"job_arguments": selector["id"]},
        inputs,
        jobs,
        planned_jobs={row["id"]: row for row in plan["jobs"]},
    )
    assert run_pilot.input_identity(original_arguments) == run_pilot.input_identity(
        metadata["selection_arguments"]
    )
    missing = copy.deepcopy(parent)
    missing["raw"] = None
    with pytest.raises(ValueError, match="selector inspection"):
        run_pilot._resolve(
            {"job_arguments": selector["id"]},
            inputs,
            {selector["id"]: missing},
            planned_jobs={selector["id"]: selector},
        )
    # Incomplete numerical stages still have no arguments available to re-evaluate.
    stage = dict(parent, id="numerical-stage", operation="teacher_candidate_gate")
    assert (
        run_pilot._resolve(
            {"job_arguments": stage["id"]},
            inputs,
            {stage["id"]: stage},
            planned_jobs={stage["id"]: dict(selector, operation=stage["operation"])},
        )
        is None
    )


def test_conditional_case_date_and_refinement_keep_actual_control_work(monkeypatch):
    jobs, selectors, adapters = _conditional_attempt_sources_unit(monkeypatch)
    model = "Heston"
    selected = jobs[selectors[model]]["raw"]
    case_id = next(iter(selected["selected_state_case_job_ids"]))
    case = {
        "id": case_id,
        "job_id_source": {
            "teacher_selection_job_id": selectors[model],
            "model": model,
            "case_id": case_id,
        },
    }
    concrete = check_pilot.concrete_case_binding(case, jobs)
    assert concrete["control_job_ids"] == [selectors[model]]
    spec = check_pilot.concrete_execution_specification({"required_case_binding": case}, jobs)
    assert spec["required_job_ids"] == [concrete["job_id"], selectors[model]]
    date = {
        "id": "teacher:Heston:date0",
        "job_ids_source": {
            "teacher_selection_job_id": selectors[model],
            "model": model,
            "date_index": 0,
        },
    }
    concrete = check_pilot.concrete_attempt_binding(date, jobs)
    assert concrete["control_job_ids"] == [selectors[model]]
    spec = check_pilot.concrete_execution_specification({"required_attempt_binding": date}, jobs)
    assert spec["required_job_ids"] == concrete["job_ids"] + [selectors[model]]
    source = {m: {p: adapters[m][p] for p in ("principal", "teacher_grid")} for m in adapters}
    refinement = {
        "id": "refinement:teacher_grid:Heston",
        "job_ids_source": {"selected_inputs_job_ids": source, "fixed_job_ids": []},
    }
    concrete = check_pilot.concrete_attempt_binding(refinement, jobs)
    control = [source[m][p] for m in ("Heston", "local") for p in ("principal", "teacher_grid")]
    control += [selectors[m] for m in ("Heston", "local")]
    assert concrete["control_job_ids"] == control
    spec = check_pilot.concrete_execution_specification(
        {"required_attempt_binding": refinement}, jobs
    )
    assert spec["required_job_ids"] == list(dict.fromkeys(concrete["job_ids"] + control))


def _native_q_locked_input_source_unit(model, *, failed=False):
    from unittest.mock import patch

    arguments = {}
    native = run_pilot.run_q_job

    def captured(parameters, surface, **kwargs):
        arguments.update(parameters=parameters, surface=surface, **kwargs)
        return native(parameters, surface, **kwargs)

    with patch.object(run_pilot, "run_q_job", captured):
        raw = _native_q_source_unit(model, failed=failed)
    arguments["wall_cap_seconds"] = 10.0
    job = {
        "id": "source-unit-Q:" + model,
        "operation": "Q",
        "arguments": arguments,
        "budget": {"wall_seconds": 10.0},
    }
    row = {"raw": raw, "resolved_arguments_sha256": run_pilot.input_identity(arguments)}
    return raw, row, job


@pytest.mark.parametrize("model", ["Heston", "local"])
@pytest.mark.parametrize(
    "key",
    [
        "parameters",
        "surface",
        "initial_spot",
        "initial_state",
        "model",
        "seed",
        "state_id",
        "call_cache",
        "times",
        "bin_edges",
        "quoted_calls",
        "chunks",
        "kind",
    ],
)
def test_native_q_saved_required_inputs_cannot_disable_sde_replay(monkeypatch, model, key):
    raw, row, job = _native_q_locked_input_source_unit(model)
    raw["chunks"][0]["raw_records"][0]["records"]["variance"][:, 1] += 0.001
    del raw[key]
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved Q RNG"))
    with pytest.raises(ValueError, match=r"native Q|required Q"):
        check_pilot.check_q_record(raw)
    with pytest.raises(ValueError, match=r"native Q|required Q"):
        check_pilot.check_resolved_job_arguments(
            row, job, inputs={}, jobs={}, artifact_directory=None
        )


@pytest.mark.parametrize("model", ["Heston", "local"])
@pytest.mark.parametrize(
    "key",
    [
        "parameters",
        "surface",
        "initial_spot",
        "initial_state",
        "model",
        "seed",
        "original_n",
        "state_id",
        "call_cache",
        "date",
        "bin_edges",
    ],
)
def test_native_q_raw_inputs_bound_to_original_locked_worker(monkeypatch, model, key):
    import copy
    from dataclasses import replace

    from hullkit._heston_local_surface import LocalVarianceGrid

    original, row, job = _native_q_locked_input_source_unit(model)
    raw = copy.deepcopy(original)
    row["raw"] = raw
    if key == "parameters":
        # Explicit initial_spot means this parameter does not change the saved SDE.
        raw["parameters"] = replace(raw["parameters"], spot=101.0)
    elif key == "surface":
        if raw["surface"] is None:
            raw["surface"] = LocalVarianceGrid(
                np.array([0.001, 1.25]),
                np.array([-12.0, 12.0]),
                np.full((2, 2), 0.05),
                raw["parameters"],
            )
        else:
            raw["surface"].values[0, 0] += 0.001
    elif key == "initial_spot":
        raw[key] = np.asarray(raw[key]).copy() + 1.0
    elif key == "initial_state":
        raw[key] += 0.01
    elif key == "model":
        raw[key] = "local" if model == "Heston" else "Heston"
    elif key in ("seed", "original_n"):
        raw[key] += 1
    elif key == "state_id":
        raw[key] += ":substituted"
    elif key == "call_cache":
        raw[key]["diagnostics"][0]["method"] += ":substituted"
    elif key == "date":
        raw["times"] = raw["times"] + 0.125
    else:
        raw[key] = np.asarray(raw[key]).copy() + 0.5
    # The original worker hash remains intact; it cannot authenticate substituted raw.
    assert row["resolved_arguments_sha256"] == run_pilot.input_identity(job["arguments"])
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved Q RNG"))
    with pytest.raises(ValueError, match=r"Q.*(input|date|timeline|source)|producer.*Q"):
        check_pilot.check_resolved_job_arguments(
            row, job, inputs={}, jobs={}, artifact_directory=None
        )


@pytest.mark.parametrize("model", ["Heston", "local"])
@pytest.mark.parametrize("failed", [False, True])
def test_native_q_locked_binding_saved_replay_preserves_all_original_paths(
    monkeypatch, tmp_path, model, failed
):
    raw, row, job = _native_q_locked_input_source_unit(model, failed=failed)
    empty = run_pilot.run_empty_claim_job(raw)
    run_pilot.write_pilot_artifact(tmp_path / "empty", run_pilot.pack_inputs(empty))
    saved, _ = run_pilot.read_pilot_artifact(tmp_path / "empty")
    saved = run_pilot.unpack_inputs(saved)
    row["raw"] = saved["Q"]
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved Q RNG"))
    monkeypatch.setattr(run_pilot, "run_q_job", lambda *a, **k: pytest.fail("saved Q regeneration"))
    check_pilot.check_resolved_job_arguments(row, job, inputs={}, jobs={}, artifact_directory=None)
    checked = check_pilot.check_empty_claim_record(saved)
    assert checked["original_n"] == 32 and checked["financial_qualification"] == "unknown"
    assert checked["Q_check"]["whole"]["qualification"] == "unknown"
    assert np.array_equal(saved["Q"]["path_ids"], np.arange(32))
    assert saved["Q"]["path_mask"].sum() == 32 - int(failed)
    assert saved["Q"]["seed"] == 913
    assert saved["Q"]["expense"] == raw["expense"]
    if failed:
        assert np.isnan(saved["Q"]["increments"][0]).all()
        assert saved["Q"]["failure_reasons"][0] == "original_one_step_SDE_failure"


@pytest.mark.parametrize("model", ["Heston", "local"])
def test_native_q_saved_parameter_null_is_not_optional_replay(monkeypatch, model):
    raw = _native_q_source_unit(model)
    raw["parameters"] = None
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved Q RNG"))
    with pytest.raises(ValueError, match=r"native Q.*input"):
        check_pilot.check_q_record(raw)


def test_native_q_saved_local_field_null_is_rejected_before_sde(monkeypatch):
    raw = _native_q_source_unit("local")
    raw["surface"] = None
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved Q RNG"))
    with pytest.raises(ValueError, match=r"native Q.*input"):
        check_pilot.check_q_record(raw)


@pytest.mark.parametrize("model", ["Heston", "local"])
def test_native_q_original_chunk_shape_bound_to_resolved_input(monkeypatch, model):
    raw, row, job = _native_q_locked_input_source_unit(model)
    # This source unit presents a different original chunk plan under its own hash.
    # The unchanged saved 7-path chunks must still disagree with the 8-path input.
    job["arguments"]["chunk_paths"] = 8
    row["resolved_arguments_sha256"] = run_pilot.input_identity(job["arguments"])
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved Q RNG"))
    with pytest.raises(ValueError, match=r"Q.*chunk_paths.*input"):
        check_pilot.check_resolved_job_arguments(
            row, job, inputs={}, jobs={}, artifact_directory=None
        )
    assert raw["original_n"] == 32 and raw["chunks"][0]["path_stop"] == 7


@pytest.mark.parametrize("model", ["Heston", "local"])
def test_native_q_actual_cap_does_not_waive_required_saved_inputs(monkeypatch, model):
    _, _, job = _native_q_locked_input_source_unit(model)
    arguments = dict(job["arguments"], wall_cap_seconds=1e-12)
    raw = run_pilot.run_q_job(**arguments)
    assert raw["status"] == "failed_at_declared_cap" and raw["original_n"] == 32
    assert raw["chunks"] == [] and not raw["path_mask"].any()
    row = {"operation": "Q", "status": "failed_at_declared_cap", "raw": raw}
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("saved Q RNG"))
    checked = check_pilot.check_capped_job_raw(row)
    assert checked["original_n"] == 32 and checked["financial_qualification"] == "unknown"
    del raw["parameters"]
    with pytest.raises(ValueError, match=r"native Q.*input"):
        check_pilot.check_capped_job_raw(row)
