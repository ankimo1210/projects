"""Tests for the saved-data runner boundary; no full pilot is certified."""

import copy
import importlib.util
import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "johnhull/research/RB-F04/dynamic_hedging/run_reference.py"
spec = importlib.util.spec_from_file_location("dynamic_research_runner", RUNNER_PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def validation_row(n=4):
    ids = runner.validation_candidate_ids()
    losses = {identifier: np.full(n, 0.4 + j * 0.1) for j, identifier in enumerate(ids)}
    candidates = [
        {
            "id": name,
            "status": "completed",
            "original_n": n,
            "mse": float(np.mean(losses[name] ** 2)),
            "reason": None,
        }
        for name in ids
    ]
    return {
        "id": "selection:Heston:U1",
        "generator": "Heston",
        "universe": "U1",
        "status": "completed",
        "original_n": n,
        "candidates": candidates,
        "selected_baseline": ids[0],
        "selected_bands": {"Heston": ids[1], "local": ids[8]},
        "band_failures": {},
        "reason": None,
    }, losses


def closed_fits_fixture():
    fits = []
    for slot in runner.protocol.study_roster()["fits"]:
        row = dict(slot)
        row.update(
            status="failed",
            attempted=True,
            original_n=8192,
            requested_updates=512,
            updates=0,
            elapsed_seconds=1.0,
            raw_fit=None,
            reason="retained failed attempt",
            checkpoint_id=None,
        )
        fits.append(row)
    first = fits[0]
    first.update(
        status="completed", updates=512, reason=None, checkpoint_id="last_finite_completed"
    )
    first["raw_fit"] = {
        "status": "completed",
        "complete": True,
        "seed": first["initialization"],
        "universe": first["universe"],
        "original_path_count": 8192,
        "training_generator": first["training_generator"],
        "fit_id": first["id"],
        "checkpoint_id": "last_finite_completed",
        "requested_updates": 512,
        "updates": 512,
        "weights": {
            "w1": np.zeros((9, 32)),
            "b1": np.zeros(32),
            "w2": np.zeros((32, 32)),
            "b2": np.zeros(32),
            "w3": np.zeros((32, 2)),
            "b3": np.zeros(2),
        },
        "scaler": {"mean": np.zeros(9), "std": np.ones(9)},
    }
    return {"fits": fits}


def test_raw_validation_recomputes_mse_and_original_denominator():
    row, losses = validation_row()
    result = runner.check_validation(row, losses, original_n=4)
    assert result["integrity"] == "pass"
    assert result["selection"]["selected_baseline"] == "greek:Heston"
    row["candidates"][0]["mse"] += 0.2
    with pytest.raises(ValueError, match="MSE"):
        runner.check_validation(row, losses, original_n=4)


def test_selection_flag_cannot_choose_a_worse_saved_loss():
    row, losses = validation_row()
    row["selected_baseline"] = "greek:local"
    with pytest.raises(ValueError, match="baseline"):
        runner.check_validation(row, losses, original_n=4)


def test_failed_validation_keeps_nan_in_original_n_without_filtering():
    row, losses = validation_row()
    losses["greek:Heston"][1] = np.nan
    row["candidates"][0].update(status="failed", mse=None, reason="original path unknown")
    row["selected_baseline"] = row["candidates"][1]["id"]
    result = runner.check_validation(row, losses, original_n=4)
    assert result["rows"][0]["original_n"] == 4
    assert result["rows"][0]["finite_n"] == 3
    assert result["rows"][0]["status"] == "failed"
    with pytest.raises(ValueError, match="original"):
        runner.check_validation(
            row, {**losses, "greek:Heston": losses["greek:Heston"][:3]}, original_n=4
        )


def test_source_closure_contains_package_init_and_relative_dependency(tmp_path):
    root = tmp_path
    package = root / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("from . import constants\n")
    (package / "constants.py").write_text("SCALE = 1\n")
    (package / "inner.py").write_text("from .constants import SCALE\n")
    (package / "entry.py").write_text("from .inner import SCALE\n")
    first = runner.source_identity(root, entrypoints=["pkg.entry"], package_roots={"pkg": "pkg"})
    assert set(first["files"]) == {
        "pkg/__init__.py",
        "pkg/constants.py",
        "pkg/inner.py",
        "pkg/entry.py",
    }
    (package / "constants.py").write_text("SCALE = 2\n")
    second = runner.source_identity(root, entrypoints=["pkg.entry"], package_roots={"pkg": "pkg"})
    assert first["files"]["pkg/constants.py"] != second["files"]["pkg/constants.py"]


def test_source_closure_contains_nested_package_initializer(tmp_path):
    package = tmp_path / "pkg"
    nested = package / "nested"
    nested.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (nested / "__init__.py").write_text("from . import helper\n")
    (nested / "helper.py").write_text("VALUE = 1\n")
    (nested / "entry.py").write_text("VALUE = 2\n")
    result = runner.source_identity(
        tmp_path, entrypoints=["pkg.nested.entry"], package_roots={"pkg": "pkg"}
    )
    assert set(result["files"]) == {
        "pkg/__init__.py",
        "pkg/nested/__init__.py",
        "pkg/nested/helper.py",
        "pkg/nested/entry.py",
    }


def test_source_closure_rejects_a_loaded_package_from_another_checkout(tmp_path, monkeypatch):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "entry.py").write_text("VALUE = 1\n")
    imported = types.ModuleType("pkg.entry")
    imported.__file__ = str(tmp_path / "other_checkout.py")
    monkeypatch.setitem(sys.modules, "pkg.entry", imported)
    with pytest.raises(ValueError, match="loaded source"):
        runner.source_identity(tmp_path, entrypoints=["pkg.entry"], package_roots={"pkg": "pkg"})


def test_main_loader_is_not_called_when_real_freeze_gate_refuses():
    calls = []
    with pytest.raises(ValueError, match="frozen"):
        runner.run_main(
            frozen={},
            candidate=runner.candidate_protocol(),
            source={},
            selection_receipts={},
            raw_validation={},
            main_test_loader=lambda: calls.append("opened"),
        )
    assert calls == []


def test_main_loader_follows_raw_selection_and_protocol_gate(monkeypatch):
    calls = []
    row, losses = validation_row(n=2048)
    validations = []
    raw = {}
    for g in ["Heston", "local"]:
        for u in ["U1", "U2"]:
            record = copy.deepcopy(row)
            record.update(id=f"selection:{g}:{u}", generator=g, universe=u)
            validations.append(record)
            raw[record["id"]] = {k: v.copy() for k, v in losses.items()}
    closed = closed_fits_fixture()
    receipts = {
        "validation": validations,
        "fits": copy.deepcopy(closed["fits"]),
        "closed_fits_sha256": runner.payload_digest(closed),
    }
    monkeypatch.setattr(
        runner.protocol, "assert_main_ready", lambda *args: calls.append("protocol_gate")
    )
    source = runner.source_identity()["protocol_source"]
    result = runner.run_main(
        frozen={"schema": "fixture"},
        candidate=runner.candidate_protocol(),
        source=source,
        selection_receipts=receipts,
        raw_validation=raw,
        main_test_loader=lambda: calls.append("test_opened") or {},
        closed_fits=closed,
    )
    assert calls == ["protocol_gate", "test_opened"]
    assert result["main_execution"] == "not_implemented"
    receipts["validation"][0]["selected_baseline"] = "greek:local"
    calls.clear()
    with pytest.raises(ValueError, match="baseline"):
        runner.run_main(
            frozen={"schema": "fixture"},
            candidate=runner.candidate_protocol(),
            source=source,
            selection_receipts=receipts,
            raw_validation=raw,
            main_test_loader=lambda: calls.append("test_opened"),
            closed_fits=closed,
        )
    assert calls == []


def test_main_rejects_same_identity_different_test_weights(monkeypatch):
    row, losses = validation_row(n=2048)
    closed = closed_fits_fixture()
    receipts = {
        "validation": [],
        "fits": copy.deepcopy(closed["fits"]),
        "closed_fits_sha256": runner.payload_digest(closed),
    }
    raw = {}
    for g in ["Heston", "local"]:
        for u in ["U1", "U2"]:
            saved = copy.deepcopy(row)
            saved.update(id=f"selection:{g}:{u}", generator=g, universe=u)
            receipts["validation"].append(saved)
            raw[saved["id"]] = copy.deepcopy(losses)
    test_fits = copy.deepcopy(closed)
    test_fits["fits"][0]["raw_fit"]["weights"]["w1"][0, 0] += 0.1
    monkeypatch.setattr(runner.protocol, "assert_main_ready", lambda *a: None)
    with pytest.raises(ValueError, match=r"test.*fits"):
        runner.run_main(
            frozen={"fixture": True},
            candidate=runner.candidate_protocol(),
            source=runner.source_identity()["protocol_source"],
            selection_receipts=receipts,
            raw_validation=raw,
            closed_fits=closed,
            main_test_loader=lambda: {"fits": test_fits},
        )


@pytest.mark.parametrize(
    "key",
    [
        "original_path_count",
        "training_generator",
        "fit_id",
        "checkpoint_id",
        "requested_updates",
        "updates",
        "weights",
        "scaler",
    ],
)
def test_main_requires_closed_raw_checkpoint_before_test_opening(monkeypatch, key):
    closed = closed_fits_fixture()
    closed["fits"][0]["raw_fit"].pop(key)
    receipts = {
        "fits": copy.deepcopy(closed["fits"]),
        "closed_fits_sha256": runner.payload_digest(closed),
    }
    opened = []
    monkeypatch.setattr(runner.protocol, "assert_main_ready", lambda *a: None)
    with pytest.raises(ValueError, match="completed fit slot"):
        runner.run_main(
            frozen={"fixture": True},
            candidate=runner.candidate_protocol(),
            source=runner.source_identity()["protocol_source"],
            selection_receipts=receipts,
            raw_validation={},
            closed_fits=closed,
            main_test_loader=lambda: opened.append(True),
        )
    assert opened == []


def test_closed_fit_digest_survives_canonical_saved_roundtrip(tmp_path):
    closed = closed_fits_fixture()
    expected = runner.payload_digest(closed)
    runner.save_bundle(tmp_path / "closed", closed)
    loaded, _ = runner.load_bundle(tmp_path / "closed")
    runner._same(closed, loaded, "closed finance")
    assert runner.payload_digest(loaded) == expected


def test_main_validation_selection_cannot_be_mutated_by_test_loader(monkeypatch):
    row, losses = validation_row(n=2048)
    closed, source = closed_fits_fixture(), runner.source_identity()["protocol_source"]
    receipts = {
        "validation": [],
        "fits": copy.deepcopy(closed["fits"]),
        "closed_fits_sha256": runner.payload_digest(closed),
    }
    raw = {}
    for g in ["Heston", "local"]:
        for u in ["U1", "U2"]:
            saved = copy.deepcopy(row)
            saved.update(id=f"selection:{g}:{u}", generator=g, universe=u)
            receipts["validation"].append(saved)
            raw[saved["id"]] = copy.deepcopy(losses)
    candidate = runner.candidate_protocol()
    cases = [
        {
            "generator": g,
            "seed_slot": seed,
            "level": level,
            "dataset": {"original_n": 8192},
            "risk": {},
        }
        for g in ["Heston", "local"]
        for seed in range(3)
        for level in [192, 384, 768]
    ]

    def loader():
        receipts["validation"][0]["selected_bands"]["Heston"] = "band:Heston:width0.2"
        return {"test_cases": cases}

    monkeypatch.setattr(runner.protocol, "assert_main_ready", lambda *a: None)
    monkeypatch.setattr(
        runner.study,
        "test_roster",
        lambda data, risk, fits, validation, **kw: {
            "chosen": validation["selected_bands"]["Heston"]
        },
    )
    result = runner.run_main(
        frozen={"fixture": True, "selection": {"test_n": 8192}},
        candidate=candidate,
        source=source,
        selection_receipts=receipts,
        raw_validation=raw,
        closed_fits=closed,
        main_test_loader=loader,
    )
    assert result["evaluations"][0]["result"]["chosen"] == "band:Heston:width0"


def test_main_loader_cannot_accept_a_different_source_registry(monkeypatch):
    calls = []
    monkeypatch.setattr(runner.protocol, "assert_main_ready", lambda *a: None)
    with pytest.raises(ValueError, match="source"):
        runner.run_main(
            frozen={"fixture": True},
            candidate=runner.candidate_protocol(),
            source={"different.py": "0" * 64},
            selection_receipts={},
            raw_validation={},
            main_test_loader=lambda: calls.append("opened"),
        )
    assert calls == []


def test_tree_artifact_roundtrip_and_checker_never_draws_rng(tmp_path, monkeypatch):
    payload = {
        "kind": "tiny",
        "values": np.array([1.0, np.nan]),
        "nested": (np.array([True, False]), None),
    }
    runner.save_bundle(tmp_path / "chunk", payload)
    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **k: pytest.fail("saved checker drew RNG")
    )
    read, receipt = runner.load_bundle(tmp_path / "chunk")
    assert read["values"] == pytest.approx(payload["values"], nan_ok=True)
    assert np.array_equal(read["nested"][0], payload["nested"][0])
    assert receipt["artifact_sha256"]


def test_teacher_restart_uses_compact_status_and_retains_global_mapping():
    from hullkit._heston_local_surface import HestonParameters

    p = HestonParameters(100.0, 0.03, 0.0, 0.04, 2.0, 0.04, 0.0, -0.7)
    times = np.arange(13) / 12
    normals = np.zeros((32, 12, 2))
    result = runner.teacher_restart(
        "heston",
        p,
        None,
        normals,
        times,
        start_index=10,
        spot=100.0,
        state=0.04,
        thresholds=np.array([-1.0, 0.0, 1.0, 3.0]),
    )
    assert result["primitives"]["local_step_status"].dtype == np.uint8
    assert result["driver_mapping"]["start_step"] == 10
    assert result["primitives"]["shared_driver_id"] != result["global_driver_id"]
    assert result["labels"]["shared_driver_id"] == result["global_driver_id"]


def test_tiny_real_pipeline_preserves_all_44_slots_and_unknown_precision(monkeypatch):
    bundle = runner.run_tiny(original_n=32, updates=1)
    assert bundle["kind"] == "tiny"
    assert bundle["formal_pilot_qualification"] == "unknown"
    assert len(bundle["fits"]["fits"]) == 12
    assert sum(len(row["cells"]) for row in bundle["evaluations"].values()) == 44
    assert all(row["original_n"] == 32 for row in bundle["fits"]["fits"])
    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **k: pytest.fail("saved checker drew RNG")
    )
    monkeypatch.setattr(
        runner.study, "fit_roster", lambda *a, **k: pytest.fail("saved checker trained")
    )
    result = runner.check_bundle(bundle)
    assert result["integrity"] == "pass"
    assert result["formal_pilot_qualification"] == "unknown"


def test_tiny_saved_checker_rejects_missing_required_expense():
    bundle = runner.run_tiny(original_n=32, updates=0, train=False)
    bundle["expenses"] = [row for row in bundle["expenses"] if row["id"] != "market:Heston"]
    with pytest.raises(ValueError, match="expense"):
        runner.check_bundle(bundle)


def test_tiny_saved_checker_rejects_cash_tamper():
    bundle = runner.run_tiny(original_n=32, updates=0, train=False)
    first = next(iter(bundle["evaluations"].values()))["cells"][0]["result"]
    first["cash"][0, -1] += 1.0
    with pytest.raises(ValueError, match="cash"):
        runner.check_bundle(bundle)


def test_tiny_saved_checker_rejects_saved_global_driver_tamper():
    bundle = runner.run_tiny(original_n=32, updates=0, train=False)
    bundle["teacher_global_driver"][0, 0, 0] += 0.01
    with pytest.raises(ValueError, match="driver"):
        runner.check_bundle(bundle)


def test_tiny_saved_checker_rejects_erased_twelve_fit_roster():
    bundle = runner.run_tiny(original_n=32, updates=0, train=False)
    bundle["fits"]["fits"] = []
    with pytest.raises(ValueError, match="twelve"):
        runner.check_bundle(bundle)


def execution_runner_fixture():
    row, losses = validation_row(n=2048)
    closed = closed_fits_fixture()
    receipts = {
        "validation": [],
        "fits": copy.deepcopy(closed["fits"]),
        "closed_fits_sha256": runner.payload_digest(closed),
    }
    raw = {}
    for g in ["Heston", "local"]:
        for u in ["U1", "U2"]:
            record = copy.deepcopy(row)
            record.update(id=f"selection:{g}:{u}", generator=g, universe=u)
            receipts["validation"].append(record)
            raw[record["id"]] = {"losses": copy.deepcopy(losses)}
    return {
        "frozen": {
            "schema": "execution_boundary_fixture",
            "selection": {"test_n": 32768, "precision_selection": "unavailable"},
        },
        "candidate": {"original_candidate": runner.candidate_protocol()},
        "source": runner.source_identity()["protocol_source"],
        "selection_receipts": receipts,
        "raw_validation": raw,
        "closed_fits": closed,
    }


def test_execution_runner_refuses_before_loader_for_empty_actual_freeze():
    calls = []
    with pytest.raises(ValueError, match="execution schema"):
        runner.run_execution_main(
            frozen={},
            candidate={},
            source={},
            selection_receipts={},
            raw_validation={},
            main_test_loader=lambda: calls.append("opened"),
        )
    assert calls == []


def test_execution_runner_uses_own_guard_and_preserves_unavailable_precision(monkeypatch):
    args = execution_runner_fixture()
    monkeypatch.setattr(runner, "execution_source_identity", runner.source_identity)
    calls = []

    def guard(frozen, candidate, source, selection):
        assert candidate["original_candidate"] == runner.candidate_protocol()
        assert frozen["selection"]["precision_selection"] == "unavailable"
        assert "qualification" not in frozen
        calls.append("execution_guard")

    monkeypatch.setattr(runner.execution, "assert_execution_ready", guard)
    monkeypatch.setattr(
        runner.protocol,
        "assert_main_ready",
        lambda *args: pytest.fail("legacy gate must not be projected"),
    )
    out = runner.run_execution_main(
        **args, main_test_loader=lambda: calls.append("test_opened") or {}
    )
    assert calls == ["execution_guard", "test_opened"]
    assert out["qualification"] == "unknown"
    assert out["precision_selection"] == "unavailable"
    assert out["main_execution"] == "not_implemented"


def test_execution_runner_rechecks_raw_validation_before_loader(monkeypatch):
    args = execution_runner_fixture()
    monkeypatch.setattr(runner, "execution_source_identity", runner.source_identity)
    args["selection_receipts"]["validation"][0]["candidates"][0]["mse"] += 1
    calls = []
    monkeypatch.setattr(runner.execution, "assert_execution_ready", lambda *args: None)
    with pytest.raises(ValueError, match="MSE"):
        runner.run_execution_main(**args, main_test_loader=lambda: calls.append("opened"))
    assert calls == []


def test_execution_runner_keeps_all_failed_baselines_and_original_paths(monkeypatch):
    args = execution_runner_fixture()
    monkeypatch.setattr(runner, "execution_source_identity", runner.source_identity)
    for record in args["selection_receipts"]["validation"]:
        for item in record["candidates"]:
            item.update(status="failed", mse=None, reason="original risk unqualified")
        record.update(
            status="failed",
            selected_baseline=None,
            selected_bands={"Heston": None, "local": None},
            band_failures={"Heston": "all failed", "local": "all failed"},
            reason="all original candidates failed",
        )
        raw = args["raw_validation"][record["id"]]
        raw["qualifications"] = {name: np.zeros(2048, bool) for name in raw["losses"]}
    calls = []

    def loader():
        calls.append("opened")
        for raw in args["raw_validation"].values():
            assert all(loss.shape == (2048,) for loss in raw["losses"].values())
        return {}

    monkeypatch.setattr(runner.execution, "assert_execution_ready", lambda *args: None)
    out = runner.run_execution_main(**args, main_test_loader=loader)
    assert calls == ["opened"]
    assert out["qualification"] == "unknown"
    assert all(r["selected_baseline"] is None for r in args["selection_receipts"]["validation"])


def test_execution_runner_detaches_earlier_inputs_before_untrusted_loader(monkeypatch):
    args = execution_runner_fixture()
    monkeypatch.setattr(runner, "execution_source_identity", runner.source_identity)
    checked = []

    def guard(frozen, candidate, source, receipts):
        checked.append(candidate["original_candidate"]["training"]["original_n"])

    def loader():
        args["candidate"]["original_candidate"]["training"]["original_n"] = 1
        args["frozen"]["selection"]["precision_selection"] = "fabricated_success"
        return {}

    monkeypatch.setattr(runner.execution, "assert_execution_ready", guard)
    out = runner.run_execution_main(**args, main_test_loader=loader)
    assert checked == [8192]
    assert out["precision_selection"] == "unavailable"
    assert out["qualification"] == "unknown"


def test_execution_runner_cli_demands_closed_inputs(capsys):
    with pytest.raises(SystemExit) as exc:
        runner.main(["--phase", "execution-main"])
    assert exc.value.code == 2
    assert "execution-main requires" in capsys.readouterr().err


def test_execution_runner_domain_generation_keeps_explicit_config_and_replays(monkeypatch):
    domains = {"heston": [None] * 12, "local": [None] * 12}
    bundle = runner.run_tiny(
        original_n=16, updates=0, train=False, evaluation_domains_by_model=domains
    )
    domains["heston"][0] = {"state": [0, 4], "threshold": [0, 4]}
    for model in ["heston", "local"]:
        assert bundle["teachers"][model]["evaluation_domains"] == [None] * 12
        cache = bundle["caches"][model]["asian"]
        assert cache["evaluation_domains"] == [None] * 12
        assert cache["original_N"] == 16
    calls = []
    real = runner.replay.rebuild_asian_cache

    def traced(*args, **kwargs):
        assert kwargs["evaluation_domains"] == [None] * 12
        assert kwargs["saved_cache"]["original_N"] == 16
        calls.append(kwargs["model"])
        return real(*args, **kwargs)

    monkeypatch.setattr(runner.replay, "rebuild_asian_cache", traced)
    result = runner.check_bundle(bundle)
    assert calls == ["heston", "local"]
    assert result["formal_pilot_qualification"] == "unknown"


def test_execution_runner_saved_domain_tamper_cannot_change_generation_config():
    domains = {"heston": [None] * 12, "local": [None] * 12}
    bundle = runner.run_tiny(
        original_n=16, updates=0, train=False, evaluation_domains_by_model=domains
    )
    bundle["caches"]["heston"]["asian"]["evaluation_domains"][0] = {
        "state": [0, 4],
        "threshold": [0, 4],
    }
    with pytest.raises(ValueError, match="domain"):
        runner.check_bundle(bundle)


def test_execution_source_requires_missing_real_fresh_entry_before_opening(tmp_path):
    base = tmp_path / "johnhull/research/RB-F04/dynamic_hedging"
    base.mkdir(parents=True)
    (base / "reference_methods.py").write_text("REFERENCE = 1\n")
    with pytest.raises(ValueError, match=r"required execution source.*run_fresh"):
        runner.execution_source_identity(tmp_path)


def test_execution_source_includes_both_phase_roots_and_relative_dependency(tmp_path):
    base = tmp_path / "johnhull/research/RB-F04/dynamic_hedging"
    base.mkdir(parents=True)
    for name in ["run_reference", "check_initial_quotes", "check_selected_calls"]:
        (base / f"{name}.py").write_text("SCALE = 1\n")
    (base / "reference_methods.py").write_text("from .shared import SCALE\n")
    (base / "run_fresh.py").write_text("from .shared import SCALE\n")
    (base / "shared.py").write_text("SCALE = 2\n")
    identity = runner.execution_source_identity(tmp_path)
    assert {str(p.relative_to(tmp_path)) for p in base.glob("*.py")} <= set(identity["files"])
    first = identity["files"][str((base / "shared.py").relative_to(tmp_path))]
    (base / "shared.py").write_text("SCALE = 3\n")
    second = runner.execution_source_identity(tmp_path)["files"][
        str((base / "shared.py").relative_to(tmp_path))
    ]
    assert first != second


def actual_execution_inputs():
    path = ROOT / "deep_hedge_price/tests/test_dynamic_hedging_execution.py"
    helper_spec = importlib.util.spec_from_file_location("execution_unit_helpers", path)
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    fixture = helper.execution_fixture()
    frozen = runner.execution.freeze_execution(**fixture)
    receipts = helper.closure(fixture, frozen)
    closed = closed_fits_fixture()
    raw_by_id = {r["id"]: r for r in closed["fits"]}
    for row in receipts["fits"]:
        raw = raw_by_id[row["id"]]
        for key in [
            "status",
            "attempted",
            "original_n",
            "requested_updates",
            "updates",
            "elapsed_seconds",
            "checkpoint_id",
            "reason",
        ]:
            row[key] = raw[key]
        row["selection_status"] = raw["status"]
        row["weights_sha256"] = (
            runner.payload_digest(raw["raw_fit"]["weights"])
            if raw["status"] == "completed"
            else None
        )
        if raw["status"] == "failed":
            row["failure_kind"] = "unqualified_training_data"
    receipts["closed_fits_sha256"] = runner.payload_digest(closed)
    helper.seal_closure(fixture, frozen, receipts)
    validation = {}
    for row in receipts["validation"]:
        ids = [c["id"] for c in row["candidates"]]
        validation[row["id"]] = {
            "losses": {identifier: np.full(2048, np.nan) for identifier in ids},
            "qualifications": {identifier: np.zeros(2048, bool) for identifier in ids},
        }
    return helper, fixture, frozen, receipts, validation, closed


def test_execution_actual_metadata_guard_and_raw_closure_reach_loader(monkeypatch):
    helper, fixture, frozen, receipts, validation, closed = actual_execution_inputs()
    # Only the physical source registry is a fixture; A guard and raw replay are actual.
    monkeypatch.setattr(
        runner, "execution_source_identity", lambda: {"protocol_source": fixture["source"]}
    )
    calls = []
    result = runner.run_execution_main(
        frozen=frozen,
        candidate=fixture["candidate"],
        source=fixture["source"],
        selection_receipts=receipts,
        raw_validation=validation,
        closed_fits=closed,
        main_test_loader=lambda: calls.append("opened") or {},
    )
    assert calls == ["opened"]
    assert result["qualification"] == "unknown" and result["precision_selection"] == "unavailable"
    receipts["validation"][0]["selected_baseline"] = "greek:Heston"
    helper.seal_closure(fixture, frozen, receipts)
    calls.clear()
    with pytest.raises(ValueError, match="baseline"):
        runner.run_execution_main(
            frozen=frozen,
            candidate=fixture["candidate"],
            source=fixture["source"],
            selection_receipts=receipts,
            raw_validation=validation,
            closed_fits=closed,
            main_test_loader=lambda: calls.append("opened") or {},
        )
    assert calls == []


def test_execution_cli_uses_execution_source_with_actual_guard(monkeypatch, tmp_path, capsys):
    _, fixture, frozen, receipts, validation, closed = actual_execution_inputs()
    frozen_path = tmp_path / "frozen.json"
    frozen_path.write_text(json.dumps(frozen))
    opened, saved = [], []
    train, test, output = [tmp_path / name for name in ("train", "test", "out")]

    def loader(path):
        if path == train:
            return {
                "selection_receipts": receipts,
                "raw_validation": validation,
                "closed_fits": closed,
            }, {}
        assert path == test
        opened.append("test")
        return {}, {}

    def writer(path, result):
        assert path == output
        saved.append(result)
        return {"unit": "artifact writer not certified"}

    # Physical source/artifact I/O is supplied; the A and raw financial guards are actual.
    monkeypatch.setattr(
        runner, "execution_source_identity", lambda: {"protocol_source": fixture["source"]}
    )
    monkeypatch.setattr(runner, "load_bundle", loader)
    monkeypatch.setattr(runner, "save_bundle", writer)
    assert (
        runner.main(
            [
                "--phase",
                "execution-main",
                "--frozen",
                str(frozen_path),
                "--input",
                str(train),
                "--test-artifact",
                str(test),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert opened == ["test"] and len(saved) == 1
    assert saved[0]["precision_selection"] == "unavailable"
    assert saved[0]["qualification"] == "unknown"
    shown = json.loads(capsys.readouterr().out)
    assert shown["qualification"] == "unknown"


def test_execution_sink_streams_original_cases_without_retaining_raw_arrays(monkeypatch):
    import weakref

    _, fixture, frozen, receipts, validation, closed = actual_execution_inputs()
    monkeypatch.setattr(
        runner, "execution_source_identity", lambda: {"protocol_source": fixture["source"]}
    )
    alive, order, persisted = [], [], []

    def engine(dataset, risk, fits, selected, *, generator, universe):
        assert not any(ref() is not None for ref in alive), "prior raw evaluation retained"
        assert dataset["original_n"] == 32768
        order.append(("evaluate", generator, universe))
        loss = np.full(32768, np.nan)
        alive.append(weakref.ref(loss))
        return {"source_unit": True, "original_n": 32768, "loss": loss}

    def sink(row):
        assert row["result"]["loss"].shape == (32768,)
        key = (row["generator"], row["seed_slot"], row["level"], row["universe"])
        persisted.append(key)
        order.append(("persist", row["generator"], row["universe"]))
        return {"immutable_ref": key, "original_n": row["result"]["original_n"]}

    cases = [
        {
            "generator": g,
            "seed_slot": s,
            "level": level,
            "dataset": {"original_n": 32768},
            "risk": {},
        }
        for g in ["Heston", "local"]
        for s in range(3)
        for level in [192, 384, 768]
    ]
    monkeypatch.setattr(runner.study, "test_roster", engine)
    out = runner.run_execution_main(
        frozen=frozen,
        candidate=fixture["candidate"],
        source=fixture["source"],
        selection_receipts=receipts,
        raw_validation=validation,
        closed_fits=closed,
        main_test_loader=lambda: {"test_cases": cases},
        evaluation_sink=sink,
    )
    assert len(persisted) == len(out["evaluations"]) == 36
    assert order[::2] == [("evaluate", g, u) for g, _, _, u in persisted]
    assert order[1::2] == [("persist", g, u) for g, _, _, u in persisted]
    assert all("result" not in row for row in out["evaluations"])
    assert not any(ref() is not None for ref in alive)
    assert out["qualification"] == "unknown"


def test_execution_sink_never_opens_before_actual_gate(monkeypatch):
    touched = []
    with pytest.raises(ValueError, match="execution schema"):
        runner.run_execution_main(
            frozen={},
            candidate={},
            source={},
            selection_receipts={},
            raw_validation={},
            main_test_loader=lambda: touched.append("test"),
            evaluation_sink=lambda row: touched.append("sink"),
        )
    assert touched == []
