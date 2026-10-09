"""Saved short-call study keeps original rows and forbids resampling on replay."""

import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[2] / "research/RB-F05/short_maturity/build_reference.py"


def module():
    spec = importlib.util.spec_from_file_location("short_study_tests", PATH)
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value


@pytest.fixture(scope="module")
def smoke(tmp_path_factory):
    m = module()
    directory = tmp_path_factory.mktemp("short-study")
    p = m.module("protocol").candidate_protocol()
    record, arrays = m.run_study(p, directory, mode="smoke")
    return m, directory, record, arrays


def test_main_requires_real_numeric_freeze_before_any_sampling_or_torch(tmp_path, monkeypatch):
    m = module()
    p = m.module("protocol").candidate_protocol()

    def forbidden(*args, **kwargs):
        raise AssertionError("main observed data before numeric freeze")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(m, "_learner", forbidden)
    with pytest.raises(ValueError, match="frozen"):
        m.run_study(p, tmp_path / "main", mode="main")
    assert not (tmp_path / "main").exists()


def test_smoke_retains_original_small_rosters_and_cannot_be_accepted(smoke):
    m, directory, record, arrays = smoke
    assert record["mode"] == "smoke"
    assert record["accepted"] is False and record["teaching_acceptance"] is False
    assert record["execution"]["splits"] == {"train": 12, "validation": 6, "test": 12}
    assert record["execution"]["teacher_sample_count"] == 512
    assert len(record["fits"]) == 2
    assert [fit["dml"] for fit in record["fits"]] == [False, True]
    assert len(record["fits"][0]["test_buckets"]) == 48
    assert arrays[record["datasets"]["test"]["inputs_key"]].shape == (12, 3)
    loaded, saved = m.load_result(directory)
    assert loaded == record
    assert set(saved) == set(arrays)
    assert m.check_record(loaded, saved)["passed"]
    receipt = m.serialization_receipt(directory, record)
    assert receipt["pending"] is False and receipt["seconds"] > 0


def test_compact_teachers_preserve_original_denominator_and_precision_failures(smoke):
    _, _, r, a = smoke
    teachers = r["datasets"]["train"]["teachers"]
    assert len(teachers) == 12
    event_rows = []
    for t in teachers:
        assert t["reserved_sample_count"] == 512
        if t["status"] == "analytic_deterministic":
            assert t["count"] == 0 and t["actual_random_draws"] == 0
        else:
            event_rows.append(t)
            assert t["count"] == 512
            assert t["actual_random_draws"] == 512 + t["active_count"]
            assert not t["precision_ready"]
            assert t["reason"]
        assert a[t["keys"]["m2_matrix"]].shape == (3, 3)
    assert event_rows


def test_saved_checker_uses_no_rng_training_or_optimizer(smoke, monkeypatch):
    m, _, r, a = smoke
    import torch

    def forbidden(*args, **kwargs):
        raise AssertionError("saved checker sampled or trained")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(torch, "manual_seed", forbidden)
    monkeypatch.setattr(torch.optim.Adam, "step", forbidden)
    monkeypatch.setattr(m._learner(), "train", forbidden)
    checked = m.check_record(r, a)
    assert checked["passed"] and checked["fit_slots"] == 2
    assert checked["original_test_count"] == 12


@pytest.mark.parametrize(
    "target",
    ["teacher", "moment", "reference", "weights", "raw", "safe", "grid", "batch", "timing"],
)
def test_saved_numeric_tampering_is_rejected(smoke, target):
    m, _, r, a = smoke
    r, a = deepcopy(r), {k: v.copy() for k, v in a.items()}
    fit = r["fits"][0]
    if target == "teacher":
        t = next(t for t in r["datasets"]["train"]["teachers"] if t["active_count"])
        key = t["keys"]["active_values"]
    elif target == "moment":
        key = r["datasets"]["train"]["teachers"][0]["keys"]["mean"]
    elif target == "reference":
        key = r["datasets"]["test"]["independent_key"]
    elif target == "weights":
        key = fit["weights_keys"]["last.bias"]
    elif target == "raw":
        key = fit["predictions"]["test"]["raw_key"]
    elif target == "safe":
        key = fit["predictions"]["test"]["safe_key"]
    elif target == "grid":
        key = r["hermite"]["keys"]["derivatives"]
    elif target == "batch":
        key = fit["batch_indices_key"]
    else:
        key = r["timing"][0]["values_key"]
    a[key].flat[0] += 1
    with pytest.raises(ValueError, match=r"changed|disagree|mismatch|invalid"):
        m.check_record(r, a)


def test_fit_pairs_use_identical_prices_scales_and_attempted_batch_prefixes(smoke):
    _, _, r, a = smoke
    left, right = r["fits"]
    assert left["normalization"] == right["normalization"]
    assert left["initial_weights_id"] == right["initial_weights_id"]
    x, y = a[left["batch_indices_key"]], a[right["batch_indices_key"]]
    n = min(len(x), len(y))
    assert np.array_equal(x[:n], y[:n])
    assert left["stats"]["updates"] == right["stats"]["updates"] == 8
    assert left["stats"]["gamma_loss"] is False
    assert right["stats"]["gamma_loss"] is False


def test_diagnostics_keep_expiry_unknown_invalid_and_safe_fallbacks(smoke):
    m, _, r, a = smoke
    d = r["diagnostics"]
    x = a[d["inputs_key"]]
    assert len(x) == d["original_count"]
    for fit in r["fits"]:
        v = a[fit["diagnostics"]["safe_key"]]
        routes = a[fit["diagnostics"]["routes_key"]]
        assert np.isnan(v[0, 1:]).all()
        assert routes[0] == "expiry_undefined_atm"
        assert "expiry_exact" in routes and "fallback_time" in routes
        assert "fallback_spot" in routes and "invalid_contract" in routes
    assert m.check_record(r, a)["passed"]


def test_unique_costs_timing_whole_outputs_and_pending_are_honest(smoke):
    m, _, r, a = smoke
    totals = m.module("analytics").expense_totals(r["expenses"])
    assert totals == r["costs"]["categorized"]
    assert set(totals["pending_ids"]) >= {"serialization", "cold_import", "pilot_freeze", "fresh"}
    assert totals["measured_seconds"] > 0
    for timing in r["timing"]:
        assert a[timing["values_key"]].shape == (3, timing["batch_size"], 3)
        assert a[timing["seconds_key"]].shape == (2,)
        assert np.all(a[timing["seconds_key"]] >= 0)
    wrong = deepcopy(r)
    wrong["expenses"].append(deepcopy(wrong["expenses"][0]))
    with pytest.raises(ValueError, match=r"duplicate|cost"):
        m.check_record(wrong, a)


def test_source_binding_and_existing_result_rejection(smoke):
    m, directory, r, a = smoke
    wrong = deepcopy(r)
    name = next(iter(wrong["source_registry"]))
    wrong["source_registry"][name] = "changed"
    with pytest.raises(ValueError, match="source"):
        m.check_record(wrong, a)
    with pytest.raises(FileExistsError):
        m.run_study(r["protocol"], directory, mode="smoke")


def test_compact_seed_ids_belong_to_original_teacher_slot(smoke):
    m, _, r, a = smoke
    r = deepcopy(r)
    t = r["datasets"]["train"]["teachers"][0]
    other = r["datasets"]["train"]["teachers"][1]
    t["seeds"] = deepcopy(other["seeds"])
    with pytest.raises(ValueError, match="seed"):
        m.check_record(r, a)


def test_saved_density_report_cannot_inflate_error_to_hide_tampering(smoke):
    m, _, r, a = smoke
    r, a = deepcopy(r), {k: v.copy() for k, v in a.items()}
    d = r["references"]["density"][0]
    a[d["values_key"]][0] += 0.01
    a[d["errors_key"]][0] += 100.0
    with pytest.raises(ValueError, match=r"density|changed|disagree"):
        m.check_record(r, a)


def test_failed_optimizer_attempts_keep_both_original_slots(tmp_path, monkeypatch):
    m = module()
    import torch

    def fail(self, *args, **kwargs):
        raise RuntimeError("retained synthetic optimizer failure")

    monkeypatch.setattr(torch.optim.Adam, "step", fail)
    p = m.module("protocol").candidate_protocol()
    r, a = m.run_study(p, tmp_path / "failed", mode="smoke")
    assert len(r["fits"]) == 2
    assert all(not f["stats"]["complete"] for f in r["fits"])
    assert all(f["stats"]["updates"] == 0 for f in r["fits"])
    assert all(f["stats"]["batch_attempts"] == 1 for f in r["fits"])
    assert all("retained" in f["stats"]["reason"] for f in r["fits"])
    assert m.check_record(r, a)["passed"]


def test_actual_numeric_pilot_is_required_after_metadata_gate(tmp_path, monkeypatch):
    m = module()
    protocol = m.module("protocol")
    p = protocol.candidate_protocol()
    monkeypatch.setattr(protocol, "validate_protocol", lambda value, **kwargs: value)

    def reject(value):
        raise ValueError("actual numeric pilot evidence not approved")

    def forbidden(*args, **kwargs):
        raise AssertionError("main sampled or imported learner before real pilot")

    monkeypatch.setattr(protocol, "verify_frozen_evidence", reject)
    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(m, "_learner", forbidden)
    with pytest.raises(ValueError, match="actual numeric pilot"):
        m.run_study(p, tmp_path / "main", mode="main")
    assert not (tmp_path / "main").exists()


def test_analytic_reserved_slots_cannot_be_reported_as_observed_mc(smoke):
    m, _, r, a = smoke
    r = deepcopy(r)
    t = next(
        t for t in r["datasets"]["train"]["teachers"] if t["status"] == "analytic_deterministic"
    )
    t["observed_mc_count"] = 512
    with pytest.raises(ValueError, match=r"observation|count|draw"):
        m.check_record(r, a)


def test_cli_smoke_saved_check_and_existing_result_refusal(tmp_path):
    directory = tmp_path / "cli"
    command = [sys.executable, str(PATH), "--directory", str(directory), "--mode", "smoke"]
    created = subprocess.run(command, capture_output=True, text=True, check=True)
    header = json.loads(created.stdout)
    assert header["mode"] == "smoke" and header["fit_slots"] == 2
    assert header["accepted"] is False
    checked = subprocess.run(
        [sys.executable, str(PATH), "--directory", str(directory), "--check"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(checked.stdout)["passed"]
    repeated = subprocess.run(command, capture_output=True, text=True, check=False)
    assert repeated.returncode != 0
    assert "FileExistsError" in repeated.stderr


def test_completed_fit_requires_real_initial_and_final_objective(smoke):
    m, _, r, a = smoke
    r = deepcopy(r)
    r["fits"][0]["stats"]["initial_loss"] = None
    r["fits"][0]["stats"]["final_loss"] = None
    with pytest.raises(ValueError, match=r"complete|objective"):
        m.check_record(r, a)


def test_fit_budget_learning_rate_and_threads_are_frozen_conditions(smoke):
    m, _, r, a = smoke
    for field, value in [("budget_s", 999), ("learning_rate", 0.1), ("threads", 8)]:
        wrong = deepcopy(r)
        wrong["fits"][0]["stats"][field] = value
        with pytest.raises(ValueError, match=r"fit|cap|thread|condition|changed"):
            m.check_record(wrong, a)


def _recost(m, record):
    record["costs"]["categorized"] = m.module("analytics").expense_totals(record["expenses"])
    record["costs"]["main_only_s"] = record["costs"]["categorized"]["measured_seconds"]


@pytest.mark.parametrize(
    "mutation",
    [
        "remove_teachers",
        "remove_support",
        "promote_pending",
        "remove_archive",
        "uncharge_fit",
        "change_category",
        "add_parent",
        "extra_id",
        "teacher_link",
        "timing_zero",
    ],
)
def test_cost_roster_links_and_pending_cannot_be_rewritten(smoke, mutation):
    m, _, original, arrays = smoke
    r = deepcopy(original)
    if mutation == "remove_teachers":
        r["expenses"] = [e for e in r["expenses"] if not e["id"].startswith("teacher/")]
        r["costs"]["shared_train_teacher_s"] = 0.0
        for fit in r["fits"]:
            fit["stats"]["teacher_s"] = 0.0
            fit["stats"]["teacher_and_training_s"] = fit["stats"]["training_s"]
            fit["stats"]["overrun_s"] = max(
                0.0, fit["stats"]["training_s"] - fit["stats"]["budget_s"]
            )
    elif mutation == "remove_support":
        r["expenses"] = [
            e
            for e in r["expenses"]
            if e["id"].startswith(("teacher/", "fit/")) or e["seconds"] is None
        ]
    elif mutation == "promote_pending":
        r["costs"].update(
            cold_pipeline_s=0.0, fresh_s=0.0, archive_load_s=0.0, serialization_pending=False
        )
    elif mutation == "remove_archive":
        r["expenses"] = [e for e in r["expenses"] if e["id"] != "archive_load"]
    elif mutation == "uncharge_fit":
        for e in r["expenses"]:
            if e["id"].startswith("fit/"):
                e["charged"] = False
    elif mutation == "change_category":
        next(e for e in r["expenses"] if e["id"] == "fit/fit0")["category"] = "unassigned"
    elif mutation == "add_parent":
        next(e for e in r["expenses"] if e["id"] == "protocol_gate")["charged"] = False
        next(e for e in r["expenses"] if e["id"] == "fit/fit0")["parent"] = "protocol_gate"
    elif mutation == "extra_id":
        r["expenses"].append(
            {
                "id": "extra",
                "category": "extra",
                "seconds": 0.0,
                "charged": False,
                "scope": "undeclared",
            }
        )
    elif mutation == "teacher_link":
        r["datasets"]["train"]["teachers"][0]["expense_id"] = "teacher/train/1"
    else:
        next(e for e in r["expenses"] if e["id"] == "timing")["seconds"] = 0.0
    _recost(m, r)
    with pytest.raises(ValueError, match=r"expense|cost|receipt|pending|teacher|timing"):
        m.check_record(r, arrays)


@pytest.mark.parametrize(
    "mutation",
    [
        "optimizer_attempts",
        "time_cap_below_budget",
        "completed_initial_weights",
    ],
)
def test_saved_fit_lifecycle_cannot_claim_impossible_attempts(smoke, mutation):
    m, _, original, arrays = smoke
    r = deepcopy(original)
    f, stats = r["fits"][0], r["fits"][0]["stats"]
    if mutation == "optimizer_attempts":
        stats.update(
            status="optimizer_error",
            complete=False,
            updates=0,
            reason="claimed optimizer failure after eight attempted batches",
        )
    elif mutation == "time_cap_below_budget":
        stats.update(
            status="time_cap", complete=False, reason="claimed cap while total cost is below120s"
        )
    else:
        f["weights_state"] = "initial_after_exception"
    with pytest.raises(ValueError, match=r"fit|attempt|weights|time.cap|budget"):
        m.check_record(r, arrays)


def test_completed_final_step_overrun_is_permitted(smoke):
    m, _, original, arrays = smoke
    r = deepcopy(original)
    f = r["fits"][0]
    f["stats"]["training_s"] = 121.0
    f["stats"]["teacher_and_training_s"] = 121.0 + f["stats"]["teacher_s"]
    f["stats"]["overrun_s"] = f["stats"]["teacher_and_training_s"] - f["stats"]["budget_s"]
    next(e for e in r["expenses"] if e["id"] == "fit/fit0")["seconds"] = 121.0
    _recost(m, r)
    assert m.check_record(r, arrays)["passed"]


def test_actual_preupdate_time_cap_retains_initial_model_and_original_slots(tmp_path, monkeypatch):
    m = module()
    clock = {"seconds": 0.0}

    def tick():
        value = clock["seconds"]
        clock["seconds"] += 120.0
        return value

    monkeypatch.setattr(m._learner(), "perf_counter", tick)
    p = m.module("protocol").candidate_protocol()
    r, arrays = m.run_study(p, tmp_path / "capped", mode="smoke")
    assert len(r["fits"]) == 2
    assert all(f["stats"]["status"] == "time_cap" for f in r["fits"])
    assert all(f["stats"]["updates"] == f["stats"]["batch_attempts"] == 0 for f in r["fits"])
    assert all(f["stats"]["initial_loss"] is None for f in r["fits"])
    assert all(f["weights_state"] == "final" for f in r["fits"])
    assert m.check_record(r, arrays)["passed"]


def test_escaped_training_exception_retains_initial_fallback_without_claiming_updates(
    tmp_path, monkeypatch
):
    m = module()

    def failure(*args, **kwargs):
        raise RuntimeError("synthetic escaped training exception")

    monkeypatch.setattr(m._learner(), "train", failure)
    p = m.module("protocol").candidate_protocol()
    r, arrays = m.run_study(p, tmp_path / "exception", mode="smoke")
    assert len(r["fits"]) == 2
    assert all(f["stats"]["status"] == "training_exception" for f in r["fits"])
    assert all(f["stats"]["updates"] == f["stats"]["batch_attempts"] == 0 for f in r["fits"])
    assert all(f["weights_state"] == "initial_after_exception" for f in r["fits"])
    assert m.check_record(r, arrays)["passed"]


@pytest.mark.parametrize("status", ["time_cap", "nonfinite_loss"])
def test_zero_update_non_optimizer_failure_cannot_keep_trained_weights(smoke, status):
    m, _, original, saved = smoke
    r, arrays = deepcopy(original), {key: value.copy() for key, value in saved.items()}
    fit = r["fits"][0]
    stats = fit["stats"]
    stats.update(
        status=status,
        complete=False,
        reason="failure before optimizer",
        updates=0,
        batch_attempts=0,
        initial_loss=None,
        final_loss=None,
    )
    arrays[fit["batch_indices_key"]] = np.empty(
        (0, r["execution"]["fit"]["batch_size"]), dtype=np.int32
    )
    if status == "time_cap":
        stats["training_s"] = 120.0
        stats["teacher_and_training_s"] = 120.0 + stats["teacher_s"]
        stats["overrun_s"] = stats["teacher_and_training_s"] - stats["budget_s"]
        next(e for e in r["expenses"] if e["id"] == "fit/fit0")["seconds"] = 120.0
        _recost(m, r)
    with pytest.raises(ValueError, match=r"initial|weight|zero.update"):
        m.check_record(r, arrays)


def test_zero_update_optimizer_error_may_retain_partial_step_mutation(tmp_path, monkeypatch):
    m = module()
    import torch

    original_step = torch.optim.Adam.step

    def changed_then_failed(self, *args, **kwargs):
        original_step(self, *args, **kwargs)
        raise RuntimeError("failure after partial parameter mutation")

    monkeypatch.setattr(torch.optim.Adam, "step", changed_then_failed)
    r, arrays = m.run_study(
        m.module("protocol").candidate_protocol(), tmp_path / "partial-optimizer", mode="smoke"
    )
    assert all(f["stats"]["status"] == "optimizer_error" for f in r["fits"])
    assert all(f["stats"]["updates"] == 0 and f["stats"]["batch_attempts"] == 1 for f in r["fits"])
    initial = r["initializations"][0]
    fit = r["fits"][0]
    assert any(
        not np.allclose(arrays[key], arrays[initial["weights_keys"][name]])
        for name, key in fit["weights_keys"].items()
    )
    assert m.check_record(r, arrays)["passed"]


def test_nonfinite_parameters_status_requires_observed_nonfinite_weights(smoke):
    m, _, original, arrays = smoke
    r = deepcopy(original)
    r["fits"][0]["stats"].update(
        status="nonfinite_parameters",
        complete=False,
        reason="claimed nonfinite weights after optimizer step",
    )
    with pytest.raises(ValueError, match=r"nonfinite|parameter|weight"):
        m.check_record(r, arrays)


def test_actual_nonfinite_optimizer_weights_keep_failed_original_slots(tmp_path, monkeypatch):
    m = module()
    import torch

    original_step = torch.optim.Adam.step

    def nonfinite_after_step(self, *args, **kwargs):
        result = original_step(self, *args, **kwargs)
        with torch.no_grad():
            self.param_groups[0]["params"][-1].fill_(float("nan"))
        return result

    monkeypatch.setattr(torch.optim.Adam, "step", nonfinite_after_step)
    r, arrays = m.run_study(
        m.module("protocol").candidate_protocol(), tmp_path / "nonfinite-parameters", mode="smoke"
    )
    assert len(r["fits"]) == 2
    for fit in r["fits"]:
        assert fit["stats"]["status"] == "nonfinite_parameters"
        assert fit["stats"]["updates"] == fit["stats"]["batch_attempts"] == 1
        assert not fit["stats"]["complete"]
        assert any(not np.isfinite(arrays[key]).all() for key in fit["weights_keys"].values())
        assert fit["predictions"]["test"]["raw_errors"]["failed_rows"] == 12
    assert m.check_record(r, arrays)["passed"]
