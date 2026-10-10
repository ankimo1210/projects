"""Task6 bounded source tests; these do not authorize formal test streams."""

import copy
import sys
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))
import run_reference as runner  # noqa: E402


def main_module():
    import run_main

    return run_main


def parameters():
    from hullkit._heston_local_surface import HestonParameters

    return HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)


def call_cache(model="heston", frequency=12):
    return runner._tiny_call_cache(
        model,
        parameters(),
        np.arange(frequency + 1) / frequency,
        np.geomspace(40, 250, 8),
        np.linspace(0.00001, 0.5, 8) if model == "heston" else np.geomspace(0.25, 4, 8),
    )


def test_missing_freeze_refuses_before_random_stream_or_output(tmp_path, monkeypatch):
    module = main_module()
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("stream opened"))
    with pytest.raises(ValueError, match=r"frozen|freeze"):
        module.run_main_experiment(tmp_path / "main", inputs={}, locked_plan={})
    assert not (tmp_path / "main").exists()


def test_market_chunk_size_keeps_global_path_step_factor_order():
    module = main_module()
    kwargs = dict(
        model="Heston",
        seed=921,
        original_n=32,
        levels=[24, 48, 96],
        frequency=12,
        call_cache=call_cache(),
        premium=5.0,
        cost_rates=[0.0005, 0.005],
        role="source_unit",
    )
    a = module.run_market_job(parameters(), None, chunk_paths=3, **kwargs)
    b = module.run_market_job(parameters(), None, chunk_paths=11, **kwargs)
    fine = np.random.default_rng(921).standard_normal((32, 96, 2))
    from hullkit._dynamic_hedging_core import heston_records

    for level in kwargs["levels"]:
        normals = fine.reshape(32, level, 96 // level, 2).sum(axis=2) / np.sqrt(96 // level)
        hand = heston_records(
            parameters(), normals, np.arange(level + 1) / level, np.arange(13) * (level // 12)
        )
        assert np.array_equal(
            a["datasets"][str(level)]["prices"], b["datasets"][str(level)]["prices"], equal_nan=True
        )
        assert np.allclose(a["datasets"][str(level)]["market"]["spot"], hand["spot"])
        assert np.array_equal(a["datasets"][str(level)]["path_ids"], np.arange(32))
    assert a["stream_identity"] == b["stream_identity"]


def test_frequency_does_not_add_claim_fixings():
    module = main_module()
    result = module.run_market_job(
        parameters(),
        None,
        model="Heston",
        seed=17,
        original_n=16,
        chunk_paths=4,
        levels=[48],
        frequency=24,
        call_cache=call_cache(frequency=24),
        premium=5,
        cost_rates=[0.0005, 0.005],
        role="source_unit",
    )
    data = result["datasets"]["48"]
    assert data["memory_count"].tolist() == np.repeat(np.arange(13), 2)[:-1].tolist()
    expected = np.cumsum(data["prices"][:, 2::2, 0], axis=1)
    assert np.allclose(data["memory_sum"][:, 2::2], expected)
    assert np.allclose(data["payoff"], np.maximum(expected[:, -1] / 12 - 100, 0))


def test_saved_market_replays_sde_and_rejects_changed_quote():
    module = main_module()
    import check_main

    record = module.run_market_job(
        parameters(),
        None,
        model="Heston",
        seed=17,
        original_n=16,
        chunk_paths=4,
        levels=[24],
        frequency=12,
        call_cache=call_cache(),
        premium=5,
        cost_rates=[0.0005, 0.005],
        role="source_unit",
    )
    checked = check_main.check_market_job(record, parameters(), None)
    assert checked["original_n"] == 16
    assert checked["rng_replayed"] is False
    record["datasets"]["24"]["prices"][0, 1, 1] += 0.1
    with pytest.raises(ValueError, match="mismatch"):
        check_main.check_market_job(record, parameters(), None)


def test_qualification_masks_keep_finite_unknown_losses_out_of_primary_decision():
    module = main_module()
    loss = np.tile(np.linspace(0.5, 2, 64), (3, 1))
    mask = np.ones_like(loss, dtype=bool)
    mask[1, 5] = False
    indices = np.zeros((2000, 3, 1), dtype=np.int16)
    result = module.qualified_pair_statistics(
        loss,
        loss / 2,
        mask,
        np.ones_like(mask),
        indices,
        numerical_envelope={"absolute": 0, "relative": 0},
    )
    assert result["status"] == "unknown"
    assert result["original_count"] == 192
    assert result["qualification_unknown_count"] == 1
    assert result["finite_only"]["status"] == "descriptive_only"
    assert np.isfinite(result["raw_scores"]["absolute"]).all()


def test_paired_scores_and_bootstrap_are_independent_hand_values():
    module = main_module()
    loss = np.tile(np.r_[np.ones(64), np.full(64, 2.0)], (3, 1))
    nn = loss - 0.1
    indices = np.tile(np.array([[[0, 1], [0, 1], [0, 1]]]), (2000, 1, 1))
    out = module.qualified_pair_statistics(
        loss,
        nn,
        np.ones_like(loss, bool),
        np.ones_like(loss, bool),
        indices,
        numerical_envelope={"absolute": 0, "relative": 0},
    )
    assert out["means"]["absolute"] == pytest.approx(-0.29)
    assert out["means"]["relative"] == pytest.approx(-0.165)
    assert out["upper_bounds"]["absolute"] == pytest.approx(-0.29)
    assert out["upper_bounds"]["relative"] == pytest.approx(-0.165)
    assert out["status"] == "supported"


def test_split_main_roundtrip_preserves_nan_and_never_overwrites(tmp_path):
    module = main_module()
    data = {"original_n": 3, "values": np.array([1, np.nan, 0.0]), "reason": "unknown"}
    receipt = module.write_main_artifact(tmp_path / "raw", data)
    loaded, found = module.read_main_artifact(tmp_path / "raw")
    assert found == receipt
    assert np.allclose(loaded["values"], data["values"], equal_nan=True)
    with pytest.raises((ValueError, FileExistsError)):
        module.write_main_artifact(tmp_path / "raw", copy.deepcopy(data))


def test_numeric_envelope_comes_from_original_paired_score_changes():
    module = main_module()
    base = np.full((3, 64), 2.0)
    nn = np.full((3, 64), 1.0)
    mask = np.ones_like(base, bool)
    record = module.score_refinement(
        base,
        nn,
        base + 0.1,
        nn + 0.05,
        mask,
        mask,
        mask,
        mask,
        original_n=64,
        group="sde",
        comparison_id="case",
    )
    # d changes from -3 to 1.1025-4.41=-3.3075; r changes by .3075-.05*.41.
    assert record["envelope"]["absolute"] == pytest.approx(0.3075)
    assert record["envelope"]["relative"] == pytest.approx(0.287)
    assert record["original_n_per_seed"] == 64
    record["refined_candidate_loss"][0, 0] = 9
    import check_main

    with pytest.raises(ValueError, match="mismatch"):
        check_main.check_score_refinement(record)


def test_numeric_envelope_unknown_qualification_does_not_become_zero():
    module = main_module()
    loss, mask = np.ones((3, 64)), np.ones((3, 64), bool)
    mask[2, 63] = False
    record = module.score_refinement(
        loss,
        loss,
        loss,
        loss,
        mask,
        mask,
        mask,
        mask,
        original_n=64,
        group="teacher_grid",
        comparison_id="case",
    )
    assert record["envelope"] == {"absolute": None, "relative": None}
    assert record["qualification"] == "unknown"
    assert record["original_count"] == 192


def test_formal_plan_refuses_missing_original_refinement_groups():
    module = main_module()
    from deep_hedge_price._dynamic_hedging_protocol import candidate_protocol, study_roster

    c = candidate_protocol()
    plan = {
        "schema": "rb-f04-main-plan-v1.1",
        "test_opened": False,
        "levels": c["sde"]["main_levels"],
        "test_seeds": c["seeds"]["test"],
        "test_n": 32768,
        "original_cells": study_roster()["primary_cells"],
        "limits": c["limits"],
        "chunk_paths": 512,
        "jobs": [],
        "refinement_jobs": [],
        "history": [{"id": "old", "cost": None}],
    }
    with pytest.raises(ValueError, match=r"refinement|job"):
        module.validate_main_plan(plan, c, test_n=32768)


def test_market_declared_cap_preserves_original_unexecuted_paths():
    module = main_module()
    result = module.run_market_job(
        parameters(),
        None,
        model="Heston",
        seed=17,
        original_n=16,
        chunk_paths=4,
        levels=[24],
        frequency=12,
        call_cache=call_cache(),
        premium=5,
        cost_rates=[0.0005, 0.005],
        role="source_unit",
        wall_cap_seconds=0,
    )
    assert result["status"] == "failed_at_declared_cap"
    assert result["original_n"] == result["unexecuted_n"] == 16
    assert result["datasets"] is None
    assert result["cap_evidence"]["limit"] == 0


def test_saved_checker_never_opens_normal_rng(tmp_path, monkeypatch):
    module = main_module()
    record = module.run_market_job(
        parameters(),
        None,
        model="Heston",
        seed=17,
        original_n=16,
        chunk_paths=4,
        levels=[24],
        frequency=12,
        call_cache=call_cache(),
        premium=5,
        cost_rates=[0.0005, 0.005],
        role="source_unit",
    )
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("RNG opened"))
    import check_main

    assert check_main.check_market_job(record, parameters(), None)["integrity"] == "pass"


def test_lazy_case_metadata_does_not_read_market_or_risk(monkeypatch):
    module = main_module()
    monkeypatch.setattr(module, "read_main_artifact", lambda *a: pytest.fail("arrays loaded"))
    cases = module._CaseSequence(
        [
            ({"generator": g, "seed_slot": s, "level": level}, "m", "r")
            for g in ["Heston", "local"]
            for s in range(3)
            for level in [192, 384, 768]
        ]
    )
    keys = [(row["generator"], row["seed_slot"], row["level"]) for row in cases]
    assert len(keys) == 18
    assert len(list(cases)) == 18


def test_original_main_job_roster_retains_all_universes_seeds_levels():
    module = main_module()
    ids = module.required_main_jobs()
    assert len(ids) == len(set(ids)) == 60
    assert len([key for key in ids if key.startswith("evaluation:")]) == 36
    assert len([key for key in ids if key.startswith("risk:")]) == 18
    assert len([key for key in ids if key.startswith("market:")]) == 6


def test_empty_claim_diagnostic_has_actual_fees_and_observable_adapted_control():
    module = main_module()
    times = np.arange(13) / 12
    prices = np.full((64, 13, 2), [100.0, 10.0])
    dataset = {
        "times": times,
        "prices": prices,
        "premium": 99,
        "payoff": np.full(64, 50.0),
        "rate": 0.0,
        "cost_rates": np.array([0.0005, 0.005]),
        "original_n": 64,
        "cashflows": np.zeros_like(prices),
    }
    result = module.empty_claim_diagnostics(dataset)
    fixed = result["controls"]["fixed_stock_call"]
    assert np.allclose(fixed["gross"]["discounted_pnl"], 0)
    # One stock and quarter call opened and liquidated: .1+.025=.125.
    assert np.allclose(fixed["net"]["discounted_pnl"], -0.125)
    assert np.allclose(fixed["net"]["costs"].sum(axis=1), 0.125)
    assert result["original_n"] == 64
    assert np.array_equal(result["payoff"], np.zeros(64))


def test_statistics_replay_retains396_records_and_all_three_init_iut(tmp_path):
    module = main_module()
    from deep_hedge_price._dynamic_hedging_protocol import study_roster

    references = []
    roster = study_roster()["primary_cells"]
    for model in ["Heston", "local"]:
        for seed in range(3):
            for level in [192, 384, 768]:
                for universe in ["U1", "U2"]:
                    cells = []
                    for slot in roster:
                        if slot["generator"] != model or slot["universe"] != universe:
                            continue
                        loss = np.full(64, 1.0 if slot["policy"] == "nn" else 2.0)
                        qualified = np.ones(64, bool)
                        if slot["policy_id"] == "nn:trainHeston:init11" and seed == 1:
                            qualified[0] = False
                        cells.append(
                            {**slot, "result": {"loss": loss, "qualified_path_mask": qualified}}
                        )
                    raw = {
                        "generator": model,
                        "seed_slot": seed,
                        "level": level,
                        "universe": universe,
                        "result": {"cells": cells},
                    }
                    identifier = f"evaluation:{model}:seed{seed}:level{level}:{universe}"
                    path = tmp_path / identifier.replace(":", "_")
                    receipt = module.write_main_artifact(path, {"raw": raw})
                    references.append({"id": identifier, "path": str(path), "receipt": receipt})
    selections = {
        "validation": [
            {"id": f"selection:{g}:{u}", "selected_baseline": "greek:Heston"}
            for g in ["Heston", "local"]
            for u in ["U1", "U2"]
        ]
    }
    envelopes = {
        f"{g}:{u}:level{level}:nn:train{train}:init{init}": {"absolute": 0.0, "relative": 0.0}
        for g in ["Heston", "local"]
        for u in ["U1", "U2"]
        for level in [192, 384, 768]
        for train in ["Heston", "local"]
        for init in [11, 29, 47]
    }
    q_checks = {g: {"qualified": True} for g in ["Heston", "local"]}
    result = module.main_statistics(
        references, selections, np.zeros((2000, 3, 1), dtype=np.int16), envelopes, q_checks=q_checks
    )
    assert result["original_records"] == 396
    assert len(result["summaries"]) == 132
    assert len(result["comparisons"]) == 72
    assert len(result["families"]) == 24
    pair = result["comparisons"]["Heston:U1:level768:nn:trainHeston:init11"]
    assert pair["status"] == "unknown" and pair["original_count"] == 192
    assert result["families"]["Heston:U1:trainHeston:level768"]["status"] == "unknown"
    assert result["families"]["Heston:U1:trainlocal:level768"]["status"] == "supported"


def test_restored_job_reader_is_confined_to_that_copy(tmp_path):
    module = main_module()
    original, restored = tmp_path / "original", tmp_path / "restored"
    original.mkdir()
    restored.mkdir()
    saved = {"raw": {"loss": np.array([1.0, np.nan])}}
    receipt = module.write_main_artifact(restored / "jobs" / "one", saved)
    refs = [
        {
            "id": "one",
            "path": "jobs/one",
            "receipt": receipt,
            "payload_sha256": runner.payload_digest(saved),
        }
    ]
    jobs = module._ReferenceJobs(refs, directory=restored)
    assert np.allclose(jobs["one"]["raw"]["loss"], saved["raw"]["loss"], equal_nan=True)
    refs[0]["path"] = "../original/one"
    with pytest.raises(ValueError, match="copy"):
        module._ReferenceJobs(refs, directory=restored)["one"]


def test_original_expense_history_keeps_unknown_and_parent_coverage():
    module = main_module()
    rows = [
        {
            "id": "prior",
            "expenses": [
                {
                    "id": "parent",
                    "scope": "old_teacher",
                    "status": "complete",
                    "parent_id": None,
                    "includes_children": True,
                    "timing": {"wall_seconds": None, "cpu_seconds": None, "overrun_seconds": None},
                },
                {
                    "id": "child",
                    "scope": "old_node",
                    "status": "failed",
                    "parent_id": "parent",
                    "includes_children": True,
                    "reason": "old failure",
                    "timing": {"wall_seconds": 2.0, "cpu_seconds": 1.0, "overrun_seconds": 0.0},
                },
            ],
        }
    ]
    result = module.history_expenses(rows)
    from deep_hedge_price._dynamic_hedging_protocol import validate_expenses

    checked = validate_expenses(
        result, required_ids=["history:prior:parent", "history:prior:child"]
    )
    assert checked["charged_totals"]["wall_seconds"] is None
    assert checked["excluded_ids"] == ["history:prior:child"]
    assert result[1]["reason"] == "old failure"


def test_incomplete_history_is_not_silently_omitted():
    with pytest.raises(ValueError, match="history"):
        main_module().history_expenses([{"id": "old", "cost": None}])


def execution_plan(identifier):
    return {
        "jobs": [
            {
                "id": identifier,
                "prediction": {
                    "path_steps": 16 * 24,
                    "chunk_expanded_bytes": 4 * 24 * 16,
                    "rate_source": "analytic_source_unit",
                },
                "budget": {"planned_before_attempt": True, "wall_seconds": 10.0},
            }
        ]
    }


def execution_args():
    return {
        "parameters": parameters(),
        "surface": None,
        "model": "Heston",
        "seed": 17,
        "original_n": 16,
        "chunk_paths": 4,
        "levels": [24],
        "frequency": 12,
        "call_cache": call_cache(),
        "premium": 5.0,
        "cost_rates": [0.0005, 0.005],
        "role": "source_unit",
    }


def test_actual_finance_dispatch_resume_requires_exact_inputs_and_costs(tmp_path, monkeypatch):
    module = main_module()
    identifier = "market:Heston:seed0"
    plan, arguments, bindings = execution_plan(identifier), execution_args(), {"source": "a" * 64}
    first, reference = module._execute(
        tmp_path, identifier, "market", arguments, plan, bindings, False
    )
    assert first["original_n"] == 16 and first["status"] == "executed"
    cost = module._read_cost(reference["serialization_cost"])
    assert cost["expense"]["timing"]["wall_seconds"] >= 0
    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **k: pytest.fail("resume stream opened")
    )
    second, resumed = module._execute(
        tmp_path, identifier, "market", arguments, plan, bindings, True
    )
    assert np.allclose(
        first["datasets"]["24"]["prices"], second["datasets"]["24"]["prices"], equal_nan=True
    )
    assert resumed["serialization_cost"] == reference["serialization_cost"]
    arguments["premium"] = 5.1
    with pytest.raises(ValueError, match="binding"):
        module._execute(tmp_path, identifier, "market", arguments, plan, bindings, True)


def test_unimplemented_operation_saves_source_defect_and_never_financial_cap(tmp_path):
    module = main_module()
    identifier = "bad"
    with pytest.raises(ValueError, match="source defect"):
        module._execute(tmp_path, identifier, "missing", {}, execution_plan(identifier), {}, False)
    saved, _ = module.read_main_artifact(tmp_path / "jobs" / "bad")
    assert saved["status"] == "unclosed_source_defect"
    assert saved["raw"]["kind"] == "unclosed_source_defect"
    assert saved["expense"]["status"] == "failed"
    with pytest.raises(ValueError, match="unclosed"):
        module._execute(tmp_path, identifier, "missing", {}, execution_plan(identifier), {}, True)


def test_formal_score_dispatch_requires_actual_three_seed_rollout_producers():
    module = main_module()
    mask = np.ones((3, 64), bool)
    arguments = {
        "original_n": 64,
        "group": "sde",
        "comparison_id": "Heston:U1:level768:nn:trainHeston:init11",
        **{
            name: np.ones((3, 64))
            for name in (
                "base_baseline_loss",
                "base_candidate_loss",
                "refined_baseline_loss",
                "refined_candidate_loss",
            )
        },
        **{
            name: mask
            for name in (
                "base_baseline_mask",
                "base_candidate_mask",
                "refined_baseline_mask",
                "refined_candidate_mask",
            )
        },
    }
    with pytest.raises(ValueError, match="rollout producer"):
        module._dispatch_refinement(
            {"operation": "paired_score_refinement", "arguments": arguments}
        )


def test_position_refinement_rejects_tags_without_original_full_refit_evidence():
    module = main_module()
    with pytest.raises(ValueError, match="refit"):
        module.require_position_refinement(
            {
                "refinement_kind": "position",
                "original_n": 64,
                "base_risk_source": {"kind": "quote_risk"},
                "refined_risk_source": {"kind": "quote_risk"},
            }
        )


def test_completed_overrun_preserves_raw_work_and_declared_cap_reason(tmp_path, monkeypatch):
    module = main_module()
    identifier = "refinement:work"
    plan = execution_plan(identifier)
    plan["jobs"][0]["budget"]["wall_seconds"] = 1e-12
    monkeypatch.setattr(
        module,
        "_dispatch_refinement",
        lambda args: {
            "kind": "source_unit",
            "original_n": 64,
            "values": np.arange(64.0),
        },
    )
    raw, ref = module._execute(tmp_path, identifier, "refinement", {}, plan, {}, False)
    saved = module.read_main_artifact(ref["path"])[0]
    assert raw["original_n"] == 64 and np.array_equal(raw["values"], np.arange(64.0))
    assert saved["status"] == "failed_at_declared_cap"
    assert saved["expense"]["status"] == "failed"
    assert saved["expense"]["timing"]["overrun_seconds"] > 0
    assert saved["cap_evidence"]["finished_raw_work_preserved"] is True


def test_numeric_refinement_cannot_relabel_the_same_risk_or_sde_date():
    module = main_module()
    source = {"kind": "quote_risk", "arguments": {"caches": {}}}
    record = {
        "base_risk_source": source,
        "refined_risk_source": source,
        "dataset_indices": [0, 0],
        "shared_driver_binding": "same",
        "shared_market": {"levels": [768, 1536], "frequencies": [12, 12]},
    }
    for group in ("teacher_n", "teacher_grid", "sde"):
        with pytest.raises(ValueError, match="refinement"):
            module.require_independent_refinement_change(record, record, group)


def test_saved_cap_status_is_recomputed_from_raw_work_and_prior_budget():
    module = main_module()
    saved = {
        "identity": {"plan": {"budget": {"wall_seconds": 1.0}}},
        "status": "failed_at_declared_cap",
        "reason": "completed overrun",
        "expense": module._expense("risk", "risk", 2.0, 1.5, reason="completed overrun"),
        "raw": {"kind": "risk"},
    }
    saved["expense"]["timing"]["overrun_seconds"] = 1.0
    assert module.check_execution_status(saved)["qualified"] is False
    saved["status"] = "executed"
    with pytest.raises(ValueError, match="cap status"):
        module.check_execution_status(saved)
    saved["status"] = "failed_at_declared_cap"
    saved["raw"]["status"] = "failed_at_declared_cap"
    with pytest.raises(ValueError, match=r"actual.*cap"):
        module.check_execution_status(saved)


def test_resume_statistics_preserves_original_cost_and_never_regenerates_indices(tmp_path):
    module = main_module()
    stats = {"bootstrap_indices": np.zeros((2000, 3, 1), np.int16), "score": np.array([1.0])}
    expenses = [
        module._expense("main_statistics", "source_unit", 2.0, 1.0),
        module._expense("serialization:main_statistics", "source_unit", 0.5, 0.3),
    ]
    bindings = {"source": "a" * 64}
    first, rows = module.save_statistics_boundary(tmp_path, stats, expenses, bindings, False)
    resumed, old_rows = module.save_statistics_boundary(tmp_path, stats, [], bindings, True)
    assert first == resumed and old_rows == rows == expenses
    with pytest.raises(ValueError, match="statistics"):
        module.save_statistics_boundary(
            tmp_path, {**stats, "score": np.array([2.0])}, [], bindings, True
        )


def test_actual_paired_score_dispatch_replays_cash_risk_and_fixed_weights(monkeypatch):
    """Small synthetic-cache source-unit; no original reserved stream is opened."""
    module = main_module()
    import check_main
    from test_dynamic_hedging_study import ConstantField, asian_cache, call_cache, parameters

    original_candidate = module.protocol.candidate_protocol()
    source_candidate = copy.deepcopy(original_candidate)
    source_candidate["seeds"]["refinement"] = [101, 102, 103]
    monkeypatch.setattr(module.protocol, "candidate_protocol", lambda: source_candidate)
    dates = np.arange(13) / 12
    p, field = parameters(), ConstantField()
    caches = {
        model: {"call": call_cache(model, dates), "asian": asian_cache(model, dates[:-1])}
        for model in ("heston", "local")
    }
    fit = {
        "status": "completed",
        "complete": True,
        "weights": {
            "w1": np.zeros((9, 32)),
            "b1": np.zeros(32),
            "w2": np.zeros((32, 32)),
            "b2": np.zeros(32),
            "w3": np.zeros((32, 2)),
            "b3": np.array([0.1, 0.0]),
        },
        "scaler": {"mean": np.zeros(9), "std": np.ones(9)},
    }
    base_records, refined_records = [], []
    for seed in source_candidate["seeds"]["refinement"]:
        market = module.pilot.run_market_pair_job(
            p,
            None,
            model="Heston",
            seed=seed,
            original_n=16,
            chunk_paths=8,
            call_cache=caches["heston"]["call"],
            premium=5.0,
            cost_rates=[0.0005, 0.005],
        )
        for index, records in ((0, base_records), (1, refined_records)):
            dataset = market["datasets"][index]
            source = module.pilot._dispatch(
                "quote_risk",
                {"parameters": p, "surface": field, "dataset": dataset, "caches": caches},
            )
            records.append(
                module.pilot.run_paired_pnl_job(
                    base={
                        "dataset": dataset,
                        "risk": source["value"],
                        "universe": "U1",
                        "policy": "greek",
                        "model": "Heston",
                    },
                    refined={
                        "dataset": dataset,
                        "risk": source["value"],
                        "universe": "U1",
                        "policy": "nn",
                        "fit": fit,
                    },
                    shared_market=market,
                    dataset_indices=(index, index),
                    base_risk_source=source,
                    refined_risk_source=source,
                )
            )
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("replay RNG"))
    arguments = {
        "base_records": base_records,
        "refined_records": refined_records,
        "original_n": 16,
        "group": "sde",
        "comparison_id": "source_unit",
    }
    result = module._dispatch_refinement(
        {"operation": "paired_score_refinement", "arguments": arguments}
    )
    assert result["original_count"] == 48
    check_main.check_score_refinement(result)
    validation = module.study.select_validation(
        base_records[0]["base_dataset"],
        base_records[0]["base_risk"],
        generator="Heston",
        universe="U1",
        widths=source_candidate["hedging"]["band_width_candidates"],
    )
    selected = validation["selected_baseline"]
    policy, valuation = selected.split(":")[:2] if selected else ("greek", "Heston")
    baseline_identity = next(
        r
        for r in module.protocol.study_roster()["primary_cells"]
        if r["generator"] == "Heston"
        and r["universe"] == "U1"
        and r["policy"] == policy
        and r.get("valuation") == valuation
    )
    fit_rows = [{"id": f"fit:Heston:U1:init{init}", "raw_fit": fit} for init in (11, 29, 47)]
    for init in (11, 29, 47):
        candidate_identity = next(
            r
            for r in module.protocol.study_roster()["primary_cells"]
            if r["generator"] == "Heston"
            and r["universe"] == "U1"
            and r["policy"] == "nn"
            and r["training_generator"] == "Heston"
            and r["initialization"] == init
        )
        cells = [[], []]
        for a, b in zip(base_records, refined_records, strict=True):
            for identity, rows in zip((baseline_identity, candidate_identity), cells, strict=True):
                rows.append(
                    module.pilot.run_cell_pair_job(
                        base_dataset=a["base_dataset"],
                        refined_dataset=b["base_dataset"],
                        base_risk=a["base_risk"],
                        refined_risk=b["base_risk"],
                        identity=identity,
                        validation=validation,
                        fits=fit_rows,
                        refinement_kind="sde",
                        shared_market=a["shared_market"],
                        dataset_indices=(0, 1),
                        base_risk_source=a["base_risk_source"],
                        refined_risk_source=b["base_risk_source"],
                    )
                )
        actual = module._dispatch_refinement(
            {
                "operation": "paired_score_cell_refinement",
                "arguments": {
                    "baseline_records": cells[0],
                    "candidate_records": cells[1],
                    "original_n": 16,
                    "group": "sde",
                    "comparison_id": f"Heston:U1:level768:nn:trainHeston:init{init}",
                },
            }
        )
        hand = np.stack(
            [
                c["refined_rollout"]["loss"] ** 2
                - b["refined_rollout"]["loss"] ** 2
                - (c["base_rollout"]["loss"] ** 2 - b["base_rollout"]["loss"] ** 2)
                for b, c in zip(cells[0], cells[1], strict=True)
            ]
        )
        if selected:
            assert np.allclose(actual["raw_score_changes"]["absolute"], hand, equal_nan=True)
        else:
            assert actual["qualification"] == "unknown"
            assert np.isnan(actual["base_baseline_loss"]).all()
        check_main.check_score_refinement(actual)
        changed_pair = copy.deepcopy(cells[1])
        changed_pair[0]["identity"]["universe"] = "U2"
        with pytest.raises(ValueError, match=r"identity|universe"):
            module.score_refinement_from_cell_pairs(
                baseline_records=cells[0],
                candidate_records=changed_pair,
                original_n=16,
                group="sde",
                comparison_id=actual["comparison_id"],
            )
    changed = copy.deepcopy(refined_records)
    changed[0]["refined_arguments"]["fit"]["weights"]["b3"][0] += 0.01
    with pytest.raises(ValueError, match=r"policy|weights"):
        module.score_refinement_from_rollouts(**{**arguments, "refined_records": changed})


def test_main_input_roundtrip_preserves_actual_local_field_descriptor(tmp_path):
    module = main_module()
    from hullkit._heston_local_surface import LocalVarianceGrid

    times, z = np.array([1 / 1536, 0.5, 1.25]), np.arange(-2.0, 3.0)
    field = LocalVarianceGrid(
        times, z, np.full((3, 5), 0.04), parameters(), np.tile([0, 4], (3, 1))
    )
    module.write_main_artifact(tmp_path / "inputs", {"field": field})
    restored = module.read_main_artifact(tmp_path / "inputs")[0]["field"]
    assert isinstance(restored, LocalVarianceGrid)
    assert module.pilot.input_identity(restored) == module.pilot.input_identity(field)
    assert np.array_equal(restored.support_mask, field.support_mask)
    import check_main

    check_main.same_finance(restored, field, "restored actual local field")


def test_actual_market_cap_keeps_unexecuted_risk_and_all_eleven_policy_slots(tmp_path, monkeypatch):
    module = main_module()
    identifier = "market:Heston:seed0"
    plan = execution_plan(identifier)
    plan["jobs"][0]["budget"]["wall_seconds"] = 1e-12
    arguments = {**execution_args(), "levels": [192, 384, 768]}
    _, market_ref = module._execute(tmp_path, identifier, "market", arguments, plan, {}, False)
    risk_id = "risk:Heston:seed0:level192"
    plan["jobs"] += execution_plan(risk_id)["jobs"]
    _, risk_ref = module.save_dependency_job(
        tmp_path, risk_id, "risk", 16, [market_ref], plan, {}, False
    )
    case = {
        "generator": "Heston",
        "seed_slot": 0,
        "level": 192,
        "execution_status": "unexecuted_dependency_cap",
        "original_n": 16,
        "artifact_directory": str(tmp_path),
        "dependency_reference": module.relative_reference(risk_ref, tmp_path),
        "bindings": {},
    }
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("dependency RNG"))
    result = module.dependency_cap_evaluation(case, "U1", 16)
    assert result["original_cell_slots"] == 11 and len(result["cells"]) == 11
    for cell in result["cells"]:
        assert cell["original_n"] == 16
        assert np.isnan(cell["result"]["loss"]).all()
        assert not cell["result"]["qualified_path_mask"].any()
        assert cell["status"] == "unexecuted_dependency_cap"
        assert "cash" not in cell["result"] and "holdings" not in cell["result"]
    evaluation_id = "evaluation:Heston:seed0:level192:U1"
    plan["jobs"] += execution_plan(evaluation_id)["jobs"]
    row = {"generator": "Heston", "seed_slot": 0, "level": 192, "universe": "U1", "result": result}
    _, evaluation_ref = module.save_dependency_job(
        tmp_path, evaluation_id, "evaluation", 16, [risk_ref], plan, {}, False, additional_raw=row
    )
    _, resumed = module.save_dependency_job(
        tmp_path, evaluation_id, "evaluation", 16, [risk_ref], plan, {}, True, additional_raw=row
    )
    assert resumed == evaluation_ref
    assert (
        module.check_execution_status(
            module.read_main_artifact(risk_ref["path"])[0], directory=tmp_path
        )["qualified"]
        is False
    )
    restored = tmp_path / "restored"
    import shutil

    shutil.copytree(tmp_path / "jobs", restored / "jobs")
    shutil.copytree(tmp_path / "costs", restored / "costs")
    module.dependency_cap_evaluation({**case, "artifact_directory": str(restored)}, "U1", 16)
    with pytest.raises(ValueError, match=r"cap|receipt|binding"):
        module.dependency_cap_evaluation({**case, "bindings": {"changed": True}}, "U1", 16)


def test_parent_actual_guard_and_actual_cap_helper_retain_all_396_original_slots(
    tmp_path, monkeypatch
):
    """Synthetic source registry/A fixture; actual raw guard and cap worker, no finance draws."""
    from test_dynamic_hedging_runner import actual_execution_inputs

    module = main_module()
    _, fixture, frozen, receipts, validation, closed = actual_execution_inputs()
    n = frozen["selection"]["test_n"]
    assert n == 32768
    cases, original_cells = [], []
    for model in module.MODELS:
        for slot in range(3):
            market_id = f"market:{model}:seed{slot}"
            plan = execution_plan(market_id)
            plan["jobs"][0]["budget"]["wall_seconds"] = 1e-12
            args = {
                **execution_args(),
                "model": model,
                "seed": 17 + slot,
                "original_n": n,
                "levels": [192, 384, 768],
            }
            _, market_ref = module._execute(tmp_path, market_id, "market", args, plan, {}, False)
            for level in (192, 384, 768):
                risk_id = f"risk:{model}:seed{slot}:level{level}"
                plan["jobs"] += execution_plan(risk_id)["jobs"]
                _, ref = module.save_dependency_job(
                    tmp_path, risk_id, "risk", n, [market_ref], plan, {}, False
                )
                cases.append(
                    (
                        {
                            "generator": model,
                            "seed_slot": slot,
                            "level": level,
                            "execution_status": "unexecuted_dependency_cap",
                            "original_n": n,
                            "artifact_directory": str(tmp_path),
                            "bindings": {},
                            "dependency_reference": module.relative_reference(ref, tmp_path),
                        },
                        market_ref["path"],
                        ref["path"],
                    )
                )
    monkeypatch.setattr(
        module.runner, "execution_source_identity", lambda: {"protocol_source": fixture["source"]}
    )
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("reserved RNG"))
    monkeypatch.setattr(
        module.study, "test_roster", lambda *a, **k: pytest.fail("unexecuted policy")
    )

    def sink(row):
        assert row["result"]["original_n"] == n
        original_cells.extend(
            (row["generator"], row["seed_slot"], row["level"], c["id"])
            for c in row["result"]["cells"]
        )
        return {"original_cells": 11, "original_n": n}

    out = module.runner.run_execution_main(
        frozen=frozen,
        candidate=fixture["candidate"],
        source=fixture["source"],
        selection_receipts=receipts,
        raw_validation=validation,
        closed_fits=closed,
        main_test_loader=lambda: {"test_cases": module._CaseSequence(cases)},
        evaluation_sink=sink,
    )
    assert len(out["evaluations"]) == 36
    assert len(original_cells) == len(set(original_cells)) == 396
    assert out["qualification"] == "unknown"


def test_risk_chunks_preserve_targets_blocks_and_date_major_root_order(monkeypatch):
    from test_dynamic_hedging_study import ConstantField, setup
    from test_dynamic_hedging_study import parameters as p

    module = main_module()
    import check_main

    data, direct, caches = setup(n=13)
    data["path_ids"] = np.arange(13)
    record = module.run_risk_job(p(), ConstantField(), data, caches, chunk_paths=3)
    assert record["processed_n"] == record["original_n"] == 13
    assert record["unexecuted_n"] == 0
    assert [(c["path_start"], c["path_stop"]) for c in record["chunks"]] == [
        (0, 3),
        (3, 6),
        (6, 9),
        (9, 12),
        (12, 13),
    ]
    for chunk in record["chunks"]:
        arrays = {}
        tree = module.runner._encode_tree(module.pilot.pack_inputs(chunk["risk"]), arrays)
        import json

        string_bytes = len(json.dumps(tree, sort_keys=True, separators=(",", ":")).encode())
        assert chunk["payload_string_bytes"] == string_bytes
        assert chunk["expanded_bytes"] == sum(a.nbytes for a in arrays.values()) + string_bytes
        assert chunk["expanded_bytes"] <= 256 * 1024**2
    for model, expected in direct["models"].items():
        for key, value in expected.items():
            if isinstance(value, np.ndarray):
                check_main.same_finance(record["risk"]["models"][model][key], value, key)
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("risk replay RNG"))
    check_main.check_risk_job(record, p(), ConstantField(), data, caches)
    changed = copy.deepcopy(record)
    changed["chunks"][0]["risk"]["models"]["heston"]["u2_target"][0, 0, 0] += 0.1
    with pytest.raises(ValueError, match=r"target|mismatch"):
        check_main.check_risk_job(changed, p(), ConstantField(), data, caches)


def test_risk_soft_cap_preserves_completed_chunk_and_original_remaining_paths(monkeypatch):
    from test_dynamic_hedging_study import ConstantField, setup
    from test_dynamic_hedging_study import parameters as p

    module = main_module()
    import check_main

    data, _, caches = setup(n=4)
    clock = [0.0]
    actual = module.study.quote_risk_dataset

    def measured(*args, **kwargs):
        result = actual(*args, **kwargs)
        clock[0] += 2.0
        return result

    monkeypatch.setattr(module, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(module.study, "quote_risk_dataset", measured)
    record = module.run_risk_job(
        p(), ConstantField(), data, caches, chunk_paths=2, wall_cap_seconds=1.0
    )
    assert record["status"] == "failed_at_declared_cap"
    assert (record["original_n"], record["processed_n"], record["unexecuted_n"]) == (4, 2, 2)
    assert record["risk"] is None and len(record["chunks"]) == 1
    assert record["cap_evidence"]["consumed"] == 2.0
    assert record["financial_qualification"] == "unknown"
    check_main.check_risk_job(record, p(), ConstantField(), data, caches)


def test_risk_source_exception_keeps_prior_actual_raw_and_is_not_a_cap(tmp_path, monkeypatch):
    from hullkit._heston_local_surface import LocalVarianceGrid
    from test_dynamic_hedging_study import parameters as p
    from test_dynamic_hedging_study import setup

    module = main_module()
    data, _, caches = setup(n=4)
    field = LocalVarianceGrid(
        np.array([1 / 1536, 0.5, 1.25]),
        np.arange(-2.0, 3.0),
        np.full((3, 5), 0.04),
        p(),
        np.tile([0, 4], (3, 1)),
    )
    actual, calls = module.study.quote_risk_dataset, []

    def defective(*args, **kwargs):
        calls.append(None)
        if len(calls) == 2:
            raise ValueError("actual solver source defect")
        return actual(*args, **kwargs)

    monkeypatch.setattr(module.study, "quote_risk_dataset", defective)
    identifier = "risk:Heston:seed0:level192"
    with pytest.raises(ValueError, match="saved unclosed"):
        module._execute(
            tmp_path,
            identifier,
            "risk",
            {
                "parameters": p(),
                "surface": field,
                "dataset": data,
                "caches": caches,
                "chunk_paths": 2,
            },
            execution_plan(identifier),
            {},
            False,
        )
    saved = module.read_main_artifact(tmp_path / "jobs" / identifier.replace(":", "_"))[0]
    assert saved["status"] == "unclosed_source_defect" and saved["cap_evidence"] is None
    assert saved["raw"]["processed_n"] == 2 and saved["raw"]["unexecuted_n"] == 2
    assert len(saved["raw"]["chunks"]) == 1 and saved["raw"]["risk"] is None
    assert "solver source defect" in saved["reason"]


def test_saved_refinement_rebinds_producers_to_original_resolved_plan_arguments():
    module = main_module()
    import check_main

    args = {
        "operation": "paired_score_cell_refinement",
        "arguments": {
            "baseline_records": [{"actual_producer": "original-baseline"}],
            "candidate_records": [{"actual_producer": "original-NN"}],
            "original_n": 4096,
            "group": "sde",
            "comparison_id": "original-init11",
        },
    }
    saved = {
        "identity": {"argument_identity": module.pilot.input_identity(args)},
        "raw": {
            "producer_evidence": {
                "kind": "typed_cell_pairs",
                "baseline_records": args["arguments"]["baseline_records"],
                "candidate_records": args["arguments"]["candidate_records"],
            }
        },
    }
    check_main.check_refinement_binding(saved, args)
    changed = copy.deepcopy(saved)
    changed["raw"]["producer_evidence"]["candidate_records"][0]["actual_producer"] = "different-NN"
    with pytest.raises(ValueError, match=r"producer|binding"):
        check_main.check_refinement_binding(changed, args)
    changed = copy.deepcopy(saved)
    changed["identity"]["argument_identity"] = "b" * 64
    with pytest.raises(ValueError, match=r"argument|binding"):
        check_main.check_refinement_binding(changed, args)


def test_policy_risk_view_retains_full_raw_and_actual_cash_matches_full_risk(monkeypatch, tmp_path):
    import check_main
    from test_dynamic_hedging_study import ConstantField, setup
    from test_dynamic_hedging_study import parameters as p

    module = main_module()
    data, _, caches = setup(n=4)
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("view RNG"))
    full = module.run_risk_job(p(), ConstantField(), data, caches, chunk_paths=2)
    view = module.run_risk_job(
        p(), ConstantField(), data, caches, chunk_paths=2, retain_full_merged=False
    )
    for a, b in zip(view["chunks"], full["chunks"], strict=True):
        check_main.same_finance(a["risk"], b["risk"], "all original raw/16blocks/roots")
    assert (
        module.chunk_payload_sizes(view)["expanded_bytes"]
        < module.chunk_payload_sizes(full)["expanded_bytes"]
    )
    assert view["original_n"] == full["original_n"] == 4
    for universe in ("U1", "U2"):
        for model in ("Heston", "local"):
            for policy in ("greek", "band"):
                kwargs = {"universe": universe, "model": model, "policy": policy, "width": 0.001}
                a = module.study.policy_rollout(data, full["risk"], **kwargs)
                b = module.study.policy_rollout(data, view["risk"], **kwargs)
                check_main.same_finance(b, a, "actual full/view policy/cash/masks/fees")
    check_main.check_risk_job(view, p(), ConstantField(), data, caches)
    receipt = module.write_main_artifact(tmp_path / "actual_view", view)
    restored, restored_receipt = module.read_main_artifact(tmp_path / "actual_view")
    assert receipt == restored_receipt
    check_main.same_finance(restored, view, "actual serialized policy view and full raw chunks")
    check_main.check_risk_job(restored, p(), ConstantField(), data, caches)


def test_exact_resume_keeps_original_cost_and_adds_bound_actual_load_receipt(tmp_path, monkeypatch):
    module = main_module()
    import check_main

    plan, bindings, args = (
        execution_plan("market:Heston:seed0"),
        {"source": "source-unit-original"},
        execution_args(),
    )
    raw, original = module._execute(
        tmp_path, "market:Heston:seed0", "market", args, plan, bindings, False
    )
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("resume RNG"))
    _, repeated = module._execute(
        tmp_path, "market:Heston:seed0", "market", args, plan, bindings, True
    )
    assert repeated == original
    checks = check_main.check_resume_costs(tmp_path, bindings)
    assert len(checks["records"]) == 1
    item = checks["records"][0]
    assert item["target"]["receipt"] == original["receipt"]
    assert item["scope"] == "exact_job_load_and_binding"
    assert item["expenses"][0]["timing"]["wall_seconds"] > 0
    assert item["expenses"][0]["timing"]["cpu_seconds"] >= 0
    assert module.read_main_artifact(original["path"])[0]["raw"]["original_n"] == raw["original_n"]
    changed = copy.deepcopy(item["raw"])
    changed["clock"]["wall_stop"] = changed["clock"]["wall_start"] - 1
    with pytest.raises(ValueError, match=r"clock|timing"):
        check_main.check_resume_work_record(changed, tmp_path, bindings)
    changed = copy.deepcopy(item["raw"])
    changed["target"]["payload_sha256"] = "a" * 64
    with pytest.raises(ValueError, match=r"target|payload|binding"):
        check_main.check_resume_work_record(changed, tmp_path, bindings)


def test_statistics_resume_retains_additional_recalculation_expense_separately(tmp_path):
    module = main_module()
    import check_main

    bindings, statistics = (
        {"source": "source-unit-stats"},
        {"bootstrap_indices": np.zeros((2, 1), int)},
    )
    old = [
        module._expense("main_statistics", "source-unit", 2.0, 1.0),
        module._expense("serialization:main_statistics", "source-unit", 0.5, 0.3),
    ]
    receipt, saved = module.save_statistics_boundary(tmp_path, statistics, old, bindings, False)
    extra = [module._expense("main_statistics", "actual_replayed_statistics", 7.0, 5.0)]
    repeated, original = module.save_statistics_boundary(
        tmp_path, statistics, extra, bindings, True
    )
    assert repeated == receipt and original == saved == old
    result = check_main.check_resume_costs(tmp_path, bindings)
    assert len(result["records"]) == 1
    rows = result["records"][0]["expenses"]
    assert any(
        row["scope"] == "replayed_statistics" and row["timing"]["wall_seconds"] == 7.0
        for row in rows
    )
    assert result["records"][0]["target"]["receipt"] == receipt


def test_replayed_actual_cash_evaluation_has_separate_cost_without_original_mutation(tmp_path):
    from time import perf_counter, process_time

    import check_main
    from test_dynamic_hedging_study import setup

    module = main_module()
    data, risk, _ = setup(n=4)
    start, cpu = perf_counter(), process_time()
    actual = module.study.policy_rollout(data, risk, universe="U2", model="Heston", policy="greek")
    observed = {
        "scope": "actual_source_unit_cash",
        "wall_seconds": perf_counter() - start,
        "cpu_seconds": process_time() - cpu,
        "includes_children": True,
    }
    row = {
        "generator": "Heston",
        "seed_slot": 0,
        "level": 192,
        "universe": "U2",
        "result": {"cells": [{"id": "actual_greek", "result": actual}], "expense": observed},
    }
    identifier = "evaluation:Heston:seed0:level192:U2"
    bindings, plan = {"source": "actual-source-unit"}, execution_plan(identifier)
    original = module.save_evaluation_job(tmp_path, row, plan, bindings, False)
    second = copy.deepcopy(row)
    second["result"]["expense"]["wall_seconds"] += 0.25
    repeated = module.save_evaluation_job(tmp_path, second, plan, bindings, True)
    assert repeated == original
    saved = module.read_main_artifact(original["path"])[0]
    assert saved["raw"]["result"]["expense"] == observed
    check_main.same_finance(
        saved["raw"]["result"]["cells"][0]["result"], actual, "original real cash"
    )
    extra = check_main.check_resume_costs(tmp_path, bindings)["records"][0]
    assert any(
        r["scope"] == "replayed_evaluation"
        and r["timing"]["wall_seconds"] == observed["wall_seconds"] + 0.25
        for r in extra["expenses"]
    )


def test_completed_resume_saves_new_readiness_and_checker_cost_without_mutating_main(
    tmp_path, monkeypatch
):
    """Synthetic readiness/check math; actual immutable main/extra-cost serialization."""
    import check_main

    module = main_module()
    bindings, snapshot = (
        {"source": "source-unit-completed"},
        {"bindings": {"source": "source-unit-completed"}},
    )
    receipt = module.write_main_artifact(tmp_path / "main", snapshot)
    module.write_main_artifact(
        tmp_path / "main_serialization",
        {
            "bindings": bindings,
            "main_receipt": receipt,
            "expense": module._expense("serialization:main_snapshot", "unit", 0.2, 0.1),
        },
    )
    monkeypatch.setattr(module, "_pretest", lambda *a: ({}, bindings, {}, {}))
    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **k: pytest.fail("completed resume RNG")
    )

    def checker(directory, *, inputs, source_root, save_receipt=None):
        assert save_receipt is not None, "new checker work requires its own posttest receipt"
        checked = {
            "integrity": "pass",
            "verification_scope": "source-unit-cost-boundary",
            "check_expense": module._expense("saved_main_check", "actual_saved_check", 0.7, 0.4),
            "expenses": {"scope": "source-unit-only"},
            "original_evaluation_records": 396,
            "original_test_n_per_seed": 32768,
        }
        check_main.save_checked_receipt(directory, save_receipt, checked, bindings, receipt)
        return checked

    monkeypatch.setattr(check_main, "check_main", checker)
    result = module.run_main_experiment(
        tmp_path,
        inputs={},
        locked_plan={},
        resume=True,
        input_load_expense=module._expense("main_input_load", "unit_load", 0.3, 0.2),
    )
    assert module.read_main_artifact(tmp_path / "main") == (snapshot, receipt)
    extra = check_main.check_resume_costs(tmp_path, bindings)
    assert len(extra["records"]) == 2
    assert result["resume_check"] == "pass" and len(result["additional_costs"]) == 2
    rows = extra["expenses"]
    assert any(
        row["scope"] == "saved_main_check" and row["timing"]["wall_seconds"] == 0.7 for row in rows
    )
    assert any(
        row["scope"] == "main_input_load" and row["timing"]["wall_seconds"] == 0.3 for row in rows
    )


def test_resume_costs_restore_locally_and_interrupted_measurement_remains_unknown(
    tmp_path, monkeypatch
):
    import shutil

    import check_main

    module = main_module()
    original, restored = tmp_path / "original", tmp_path / "restored"
    identifier, bindings = "market:Heston:seed0", {"source": "copy-bound-source-unit"}
    args, plan = execution_args(), execution_plan(identifier)
    _, reference = module._execute(original, identifier, "market", args, plan, bindings, False)
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("restore RNG"))
    module._execute(original, identifier, "market", args, plan, bindings, True)
    shutil.copytree(original, restored)
    expected = check_main.check_resume_costs(original, bindings)
    actual = check_main.check_resume_costs(restored, bindings)
    assert actual["references"] == expected["references"]
    assert actual["accounting"]["charged_totals"]["wall_seconds"] is None
    assert actual["accounting"]["charged_measured_subtotals"]["wall_seconds"] > 0
    raw = copy.deepcopy(actual["records"][0]["raw"])
    raw["target"]["path"] = reference["path"]
    with pytest.raises(ValueError, match="restored copy"):
        check_main.check_resume_work_record(raw, restored, bindings)


@pytest.mark.parametrize(
    "key,value", [("generator", "local"), ("seed_slot", 1), ("level", 384), ("universe", "U1")]
)
def test_evaluation_outer_labels_bind_to_job_identity_before_statistics(key, value, tmp_path):
    """Numerically identical real cash must not be relabeled to another original cell."""
    import check_main
    from test_dynamic_hedging_study import setup

    module = main_module()
    data, risk, _ = setup(n=4)
    actual = module.study.policy_rollout(data, risk, universe="U2", model="Heston", policy="greek")
    identifier = "evaluation:Heston:seed0:level192:U2"
    saved = {
        "identity": {"id": identifier},
        "raw": {
            "generator": "Heston",
            "seed_slot": 0,
            "level": 192,
            "universe": "U2",
            "result": {
                "generator": "Heston",
                "universe": "U2",
                "cells": [{"id": "actual_greek", "result": actual}],
            },
        },
    }
    check_main.check_evaluation_metadata(saved, identifier)
    tampered = copy.deepcopy(saved)
    tampered["raw"][key] = value
    np.testing.assert_equal(tampered["raw"]["result"]["cells"][0]["result"]["loss"], actual["loss"])
    with pytest.raises(ValueError, match=r"evaluation.*metadata|metadata.*identity"):
        check_main.check_evaluation_metadata(tampered, identifier)
    receipt = module.write_main_artifact(tmp_path / "relabeled", tampered)
    with pytest.raises(ValueError, match=r"evaluation.*metadata|metadata.*identity"):
        module.main_statistics(
            [{"id": identifier, "path": str(tmp_path / "relabeled"), "receipt": receipt}],
            {"validation": []},
            np.zeros((2000, 3, 1), dtype=int),
            {},
        )


def outcome_plan_fixture():
    module = main_module()
    c = module.protocol.candidate_protocol()
    rows, groups = [], {g: [] for g in ("sde", "teacher_n", "teacher_grid", "frequency", "Q")}
    for model in module.MODELS:
        for slot, seed in enumerate(c["seeds"]["refinement"]):
            rows.append(
                {
                    "id": f"reserved_market:{model}:seed{slot}",
                    "original_n": 4096,
                    "arguments": {
                        "operation": "market_pair",
                        "arguments": {"model": model, "seed": seed, "original_n": 4096},
                    },
                }
            )
    for group in ("sde", "teacher_n", "teacher_grid"):
        for model in module.MODELS:
            for policy in ("baseline", "nn"):
                for slot in range(3):
                    rows.append(
                        {
                            "id": f"original_{policy}:{group}:{model}:seed{slot}",
                            "original_n": 4096,
                            "arguments": {
                                "operation": "cell_pair",
                                "arguments": {
                                    "shared_market": {
                                        "job": f"reserved_market:{model}:seed{slot}",
                                        "path": [],
                                    }
                                },
                            },
                        }
                    )
        for cell in module.protocol.study_roster()["primary_cells"]:
            if cell["policy"] != "nn":
                continue
            comparison = f"{cell['generator']}:{cell['universe']}:level768:{cell['policy_id']}"
            identifier = f"refinement:{group}:{comparison}"
            groups[group].append(identifier)
            rows.append(
                {
                    "id": identifier,
                    "original_n": 4096,
                    "arguments": {
                        "operation": "paired_score_cell_refinement",
                        "arguments": {
                            "group": group,
                            "comparison_id": comparison,
                            "original_n": 4096,
                            "baseline_records": [
                                {
                                    "job": f"original_baseline:{group}:{cell['generator']}:seed{i}",
                                    "path": [],
                                }
                                for i in range(3)
                            ],
                            "candidate_records": [
                                {"job": f"original_nn:{group}:{cell['generator']}:seed{i}"}
                                for i in range(3)
                            ],
                        },
                    },
                }
            )
    for cell in module.protocol.study_roster()["primary_cells"]:
        if cell["policy"] not in ("greek", "band"):
            continue
        for frequency in (24, 48):
            for slot, _seed in enumerate(c["seeds"]["refinement"]):
                identifier = f"refinement:frequency:{cell['id']}:{frequency}:seed{slot}"
                groups["frequency"].append(identifier)
                rows.append(
                    {
                        "id": identifier,
                        "original_n": 4096,
                        "diagnostic_binding": {
                            "cell_id": cell["id"],
                            "frequency": frequency,
                            "seed_slot": slot,
                        },
                        "arguments": {
                            "operation": "cell_pair",
                            "arguments": {"identity": cell, "refinement_kind": "frequency"},
                        },
                    }
                )
    for model in module.MODELS:
        for seed in c["seeds"]["refinement"]:
            identifier = f"refinement:Q:{model}:{seed}"
            groups["Q"].append(identifier)
            rows.append(
                {
                    "id": identifier,
                    "original_n": 4096,
                    "arguments": {
                        "operation": "Q",
                        "arguments": {"model": model, "seed": seed, "original_n": 4096},
                    },
                }
            )
    return {"refinement_jobs": rows, "refinement_groups": groups}, c


def test_outcome_plan_requires_original24_scores_selected_frequency_and_Q_rosters():
    plan, candidate = outcome_plan_fixture()
    result = main_module().validate_refinement_outcomes(plan, candidate)
    assert result["numeric_comparisons_per_group"] == 24
    assert result["frequency_original_slots"] == 96
    assert result["Q_model_stream_slots"] == 6


@pytest.mark.parametrize(
    "change", ["overlap", "missing_score", "wrong_operation", "reduced_N", "repeated_stream"]
)
def test_outcome_plan_rejects_metadata_only_group_completion(change):
    module = main_module()
    plan, candidate = outcome_plan_fixture()
    if change == "overlap":
        plan["refinement_groups"]["sde"] = plan["refinement_groups"]["Q"]
    elif change == "missing_score":
        plan["refinement_groups"]["sde"].pop()
    elif change == "wrong_operation":
        outcome = plan["refinement_groups"]["sde"][0]
        next(row for row in plan["refinement_jobs"] if row["id"] == outcome)["arguments"][
            "operation"
        ] = "Q"
    elif change == "reduced_N":
        outcome = plan["refinement_groups"]["sde"][0]
        next(row for row in plan["refinement_jobs"] if row["id"] == outcome)["original_n"] = 64
    else:
        outcome = plan["refinement_groups"]["sde"][0]
        args = next(row for row in plan["refinement_jobs"] if row["id"] == outcome)["arguments"][
            "arguments"
        ]
        args["baseline_records"][1] = args["baseline_records"][0]
    with pytest.raises(ValueError, match=r"original|outcome|group|refinement"):
        module.validate_refinement_outcomes(plan, candidate)


def test_canonical_refinement_refs_use_actual_resolver_and_original_reserved_producers(monkeypatch):
    module = main_module()
    plan, candidate = outcome_plan_fixture()
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("RNG opened"))
    monkeypatch.setattr(
        module.pilot, "_dispatch", lambda *a, **k: pytest.fail("finance dispatched")
    )
    module.validate_refinement_outcomes(plan, candidate)
    identifier = plan["refinement_groups"]["sde"][0]
    job = next(row for row in plan["refinement_jobs"] if row["id"] == identifier)
    expected = module.pilot._dependency_ids(job["arguments"])
    assert len(expected) == 6
    raw = {name: {"raw": {"actual_producer_id": name}} for name in expected}
    resolved = module.pilot._resolve(job["arguments"], {}, raw)["arguments"]
    assert {
        row["actual_producer_id"]
        for row in resolved["baseline_records"] + resolved["candidate_records"]
    } == expected


@pytest.mark.parametrize("legacy", [True, False])
def test_prior_guard_rejects_all_unresolved_legacy_refs_or_inline_reduced_record_N(legacy):
    module = main_module()
    plan, candidate = outcome_plan_fixture()
    numeric = set().union(
        *(plan["refinement_groups"][g] for g in ("sde", "teacher_n", "teacher_grid"))
    )
    for job in plan["refinement_jobs"]:
        if job["id"] not in numeric:
            continue
        args = job["arguments"]["arguments"]
        for key in ("baseline_records", "candidate_records"):
            args[key] = [
                {"$job": ref["job"]}
                if legacy
                else {
                    "kind": "paired_pnl",
                    "original_n": 64 if slot == 0 else 4096,
                    "shared_market": {
                        "seed": candidate["seeds"]["refinement"][slot],
                        "role": "refinement",
                        "original_n": 4096,
                    },
                }
                for slot, ref in enumerate(args[key])
            ]
    with pytest.raises(ValueError, match=r"original|producer|refinement"):
        module.validate_refinement_outcomes(plan, candidate)


@pytest.mark.parametrize(
    "change", ["legacy_unresolved", "missing", "wrong_seed", "reduced_N", "partial_raw"]
)
def test_prior_refinement_refs_reject_unresolved_or_changed_original_producers(change):
    module = main_module()
    plan, candidate = outcome_plan_fixture()
    identifier = plan["refinement_groups"]["sde"][0]
    outcome = next(row for row in plan["refinement_jobs"] if row["id"] == identifier)
    records = outcome["arguments"]["arguments"]["baseline_records"]
    if change == "legacy_unresolved":
        records[0] = {"$job": records[0]["job"]}
    elif change == "missing":
        records[0]["job"] = "undeclared_original_producer"
    elif change == "partial_raw":
        records[0]["path"] = ["base_rollout"]
    elif change == "reduced_N":
        next(row for row in plan["refinement_jobs"] if row["id"] == records[0]["job"])[
            "original_n"
        ] = 64
    else:
        market = next(
            row for row in plan["refinement_jobs"] if row["id"] == "reserved_market:Heston:seed0"
        )
        market["arguments"]["arguments"]["seed"] += 1
    with pytest.raises(ValueError, match=r"original|refinement|reserved|producer"):
        module.validate_refinement_outcomes(plan, candidate)


def test_success_worker_expense_cannot_be_shortened_to_hide_completed_overrun():
    module = main_module()
    saved = {
        "identity": {"plan": {"budget": {"wall_seconds": 1.0}}},
        "status": "executed",
        "reason": None,
        "expense": module._expense("job", "current_worker", 0.5, 0.2),
        "raw": {
            "kind": "main_risk",
            "expense": {"wall_seconds": 2.0, "cpu_seconds": 1.5},
            "status": "executed",
        },
    }
    with pytest.raises(ValueError, match=r"worker|expense|timing"):
        module.check_execution_status(saved)


@pytest.mark.parametrize(
    "worker", ["main_market", "main_risk", "Q", "bump_risk", "evaluation", "delegated"]
)
@pytest.mark.parametrize("change", ["deleted", "unknown", "unknown_cpu"])
def test_success_current_measurement_cannot_be_deleted_or_made_unknown(worker, change):
    module = main_module()
    raw = {"kind": worker, "status": "executed"}
    location = raw
    if worker == "evaluation":
        location = raw["result"] = {}
    elif worker == "delegated":
        location = raw["chunked_worker"] = {"kind": "main_risk", "status": "executed"}
    if change != "deleted":
        location["expense"] = {
            "wall_seconds": None if change == "unknown" else 0.25,
            "cpu_seconds": None,
        }
    saved = {
        "identity": {"plan": {"budget": {"wall_seconds": 1.0}}},
        "status": "executed",
        "reason": None,
        "expense": module._expense("job", "current_worker", 0.5, 0.2),
        "raw": raw,
    }
    with pytest.raises(ValueError, match=r"worker|expense|timing|measured"):
        module.check_execution_status(saved)


def test_current_worker_guard_does_not_charge_historical_unknown_costs_again():
    module = main_module()
    saved = {
        "identity": {"plan": {"budget": {"wall_seconds": 1.0}}},
        "status": "executed",
        "reason": None,
        "expense": module._expense("job", "paired_score_adapter", 0.5, 0.2),
        "raw": {
            "kind": "paired_score_refinement",
            "producer_evidence": {
                "expenses": [{"timing": {"wall_seconds": None, "cpu_seconds": None}}]
            },
        },
    }
    assert module.check_execution_status(saved)["qualified"]


def test_actual_outcome_metadata_must_match_original_declared_frequency_and_Q_slots():
    module = main_module()
    plan, candidate = outcome_plan_fixture()
    freq_job = next(
        row
        for row in plan["refinement_jobs"]
        if row["id"] in plan["refinement_groups"]["frequency"]
    )
    binding = freq_job["diagnostic_binding"]
    identity = freq_job["arguments"]["arguments"]["identity"]
    raw = {
        "kind": "paired_pnl",
        "refinement_kind": "frequency",
        "original_n": 4096,
        "selection_inputs": {"identity": identity},
        "dataset_indices": [0, 1],
        "shared_market": {
            "model": identity["generator"],
            "seed": candidate["seeds"]["refinement"][binding["seed_slot"]],
            "role": "refinement",
            "original_n": 4096,
            "frequencies": [12, binding["frequency"]],
        },
    }
    module.check_refinement_outcome_raw(freq_job, raw, plan, candidate)
    bad = copy.deepcopy(raw)
    bad["shared_market"]["frequencies"][1] = 48
    with pytest.raises(ValueError, match="frequency"):
        module.check_refinement_outcome_raw(freq_job, bad, plan, candidate)
    q_job = next(
        row for row in plan["refinement_jobs"] if row["id"] in plan["refinement_groups"]["Q"]
    )
    args = q_job["arguments"]["arguments"]
    raw = {"kind": "Q", "model": args["model"], "seed": args["seed"], "original_n": 4096}
    module.check_refinement_outcome_raw(q_job, raw, plan, candidate)
    raw["seed"] += 1
    with pytest.raises(ValueError, match="Q"):
        module.check_refinement_outcome_raw(q_job, raw, plan, candidate)


def empty_q_source_unit(monkeypatch, *, failed_path=False):
    """Actual Q arithmetic on deterministic source-unit normals, no formal RNG."""
    module = main_module()

    class DeterministicDriver:
        def standard_normal(self, shape):
            return np.zeros(shape)

    monkeypatch.setattr(np.random, "default_rng", lambda seed: DeterministicDriver())
    date = 0.25
    spots = np.full(4096, 100.0)
    if failed_path:
        spots[0] = np.nan
    raw = module.pilot.run_q_job(
        parameters(),
        None,
        model="Heston",
        seed=module.protocol.candidate_protocol()["seeds"]["refinement"][2],
        original_n=4096,
        chunk_paths=256,
        call_cache=runner._tiny_call_cache(
            "heston",
            parameters(),
            date + np.array([0, 1, 2, 4, 8]) / 1536,
            np.geomspace(40, 250, 8),
            np.linspace(0.00001, 0.5, 8),
        ),
        date=date,
        spot=spots,
        state=0.04,
        bin_edges=[90.0, 100.0, 110.0],
        state_id="source_unit_original_state",
    )
    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **k: pytest.fail("saved empty Q opened RNG")
    )
    return raw


def test_main_empty_claim_dispatch_saves_original_Q_cash_costs_and_replays(tmp_path, monkeypatch):
    import check_main

    module = main_module()
    q = empty_q_source_unit(monkeypatch)
    arguments = {"operation": "empty_claim", "arguments": {"q_record": q}}
    identifier = "refinement:producer:empty_Q:Heston:state6:seed2"
    plan = execution_plan(identifier)
    raw, ref = module._execute(tmp_path, identifier, "refinement", arguments, plan, {}, False)
    saved = module.read_main_artifact(ref["path"])[0]
    assert saved["status"] == "executed"
    assert raw["original_n"] == 4096
    assert np.array_equal(raw["path_ids"], np.arange(4096))
    assert raw["Q"]["seed"] == q["seed"] and raw["Q"]["state_id"] == q["state_id"]
    assert raw["financial_qualification"] == "unknown"
    for row, column in zip(raw["rows"], (4, 3, 2), strict=True):
        expected = (
            q["quoted_calls"][:, column] * np.exp(-q["rate"] * (q["times"][column] - q["times"][0]))
            - q["quoted_calls"][:, 0]
        )
        assert np.allclose(row["raw"]["discounted_pnl"], expected, atol=1e-12, rtol=1e-12)
        assert np.allclose(row["raw"]["discounted_gain_pnl"], expected, atol=1e-12, rtol=1e-12)
        assert row["raw"]["cash"].shape == row["raw"]["costs"].shape == (4096, 2)
        assert np.allclose(row["raw"]["costs"], 0)
    assert raw["expense"]["timing"]["wall_seconds"] >= 0
    assert raw["expense"]["timing"]["cpu_seconds"] >= 0
    assert module.check_execution_status(saved)["qualified"]
    check_main.check_refinement_binding(saved, arguments)
    checked = check_main.check_empty_claim_job(raw)
    assert checked["original_n"] == 4096
    assert checked["financial_qualification"] == "unknown"
    resumed, resumed_ref = module._execute(
        tmp_path, identifier, "refinement", arguments, plan, {}, True
    )
    check_main.check_empty_claim_job(resumed)
    assert resumed_ref["serialization_cost"] == ref["serialization_cost"]

    changed = copy.deepcopy(saved)
    changed["raw"]["Q"]["state_id"] = "different_state"
    with pytest.raises(ValueError, match=r"empty|producer|binding"):
        check_main.check_refinement_binding(changed, arguments)
    changed = copy.deepcopy(raw)
    changed["rows"][0]["raw"]["discounted_pnl"][0] += 0.01
    with pytest.raises(ValueError, match=r"empty|cash|financial"):
        check_main.check_empty_claim_job(changed)


@pytest.mark.parametrize("change", ["N", "seed", "model", "state_id", "path_order", "path_shape"])
def test_main_empty_claim_refuses_changed_original_Q_scope_before_cash(monkeypatch, change):
    module = main_module()
    q = copy.deepcopy(empty_q_source_unit(monkeypatch))
    if change == "N":
        q["original_n"] = 2048
    elif change == "seed":
        q["seed"] = 99
    elif change == "model":
        q["model"] = "different"
    elif change == "state_id":
        q["state_id"] = None
    elif change == "path_order":
        q["path_ids"] = np.arange(4096)[::-1]
    else:
        q["quoted_calls"] = q["quoted_calls"][:-1]
    monkeypatch.setattr(
        module.pilot, "run_empty_claim_job", lambda *a, **k: pytest.fail("cash ran after invalid Q")
    )
    with pytest.raises(ValueError, match=r"original|Q"):
        module._dispatch_refinement({"operation": "empty_claim", "arguments": {"q_record": q}})


def test_main_empty_claim_failed_original_path_is_preserved_without_zero_fallback(monkeypatch):
    import check_main

    module = main_module()
    q = empty_q_source_unit(monkeypatch, failed_path=True)
    raw = module._dispatch_refinement({"operation": "empty_claim", "arguments": {"q_record": q}})
    assert raw["original_n"] == 4096 and len(raw["path_ids"]) == 4096
    assert raw["Q"]["failure_reasons"][0] == "original_one_step_SDE_failure"
    assert raw["financial_qualification"] == "unknown"
    for row in raw["rows"]:
        assert row["raw"]["discounted_pnl"].shape == (4096,)
        assert np.isnan(row["raw"]["discounted_pnl"][0])
        assert not row["raw"]["path_mask"][0]
    checked = check_main.check_empty_claim_job(raw)
    assert checked["original_n"] == 4096
    assert checked["Q_check"]["whole"]["qualification"] == "unknown"


def test_main_empty_claim_completed_overrun_keeps_all_original_raw_and_costs(tmp_path, monkeypatch):
    module = main_module()
    q = empty_q_source_unit(monkeypatch)
    identifier = "empty_completed_overrun"
    plan = execution_plan(identifier)
    plan["jobs"][0]["budget"]["wall_seconds"] = 1e-12
    raw, ref = module._execute(
        tmp_path,
        identifier,
        "refinement",
        {"operation": "empty_claim", "arguments": {"q_record": q}},
        plan,
        {},
        False,
    )
    saved = module.read_main_artifact(ref["path"])[0]
    assert saved["status"] == "failed_at_declared_cap"
    assert saved["cap_evidence"]["finished_raw_work_preserved"] is True
    assert raw["original_n"] == 4096 and len(raw["rows"]) == 3
    assert raw["expense"]["timing"]["wall_seconds"] > 0
    assert not module.check_execution_status(saved)["qualified"]


@pytest.mark.parametrize("change", ["deleted", "unknown", "cpu", "clock", "overrun"])
def test_main_empty_claim_worker_measurement_is_required_and_bound(monkeypatch, change):
    import check_main

    module = main_module()
    q = empty_q_source_unit(monkeypatch)
    raw = module._dispatch_refinement({"operation": "empty_claim", "arguments": {"q_record": q}})
    if change == "deleted":
        del raw["expense"]
    elif change == "unknown":
        raw["expense"]["timing"]["wall_seconds"] = None
    elif change == "cpu":
        raw["expense"]["timing"]["cpu_seconds"] = None
    elif change == "clock":
        raw["expense"]["timing_events"]["wall_stop"] += 1.0
    else:
        raw["expense"]["timing"]["wall_seconds"] = 100.0
    with pytest.raises(ValueError, match=r"worker|expense|timing|clock"):
        check_main.check_empty_claim_job(raw)
