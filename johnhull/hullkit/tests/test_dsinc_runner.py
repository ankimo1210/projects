"""Budget enforcement, frozen inputs and honest reproduction accounting."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest


def _runner():
    path = Path(__file__).resolve().parents[2] / "research/DSINC/run.py"
    assert path.is_file(), "missing bounded research runner"
    spec = importlib.util.spec_from_file_location("dsinc_research_runner", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_every_original_slot_is_accounted():
    runner = _runner()
    slots = runner.original_slots([], reason="pilot_boundary_failure")
    assert len(slots) == 6
    assert len({s["case_id"] for s in slots}) == 6
    assert {s["status"] for s in slots} == {"not_run"}
    assert all(s["american"] is None for s in slots)
    off_atm = [s for s in slots if s["expiry"] == 1 and s["spot"] != 1]
    assert all(s["paper_american_status"] == "not_available" for s in off_atm)


def test_main_requires_frozen_pilot(tmp_path):
    runner = _runner()
    with pytest.raises(ValueError, match="freeze"):
        runner.validate_freeze(None)
    frozen = runner.make_freeze({"preflight": {"eligible": False}, "records": []}, tmp_path)
    with pytest.raises(ValueError, match="ineligible"):
        runner.validate_freeze(frozen)


@pytest.mark.parametrize(
    ("command", "wall", "memory", "status"),
    [
        (
            [sys.executable, "-c", "import time; time.sleep(2)"],
            0.15,
            2 * 1024**3,
            "time_budget_exceeded",
        ),
        (
            [sys.executable, "-c", "import time; a=bytearray(100*1024**2); time.sleep(2)"],
            5,
            40 * 1024**2,
            "memory_budget_exceeded",
        ),
    ],
)
def test_timeout_and_memory_are_failures(tmp_path, command, wall, memory, status):
    record = _runner().run_bounded(
        command, tmp_path, "budget", wall_limit=wall, memory_limit=memory
    )
    assert record["status"] == status
    assert record["values"]["american"] == [None] * 3
    assert record["wall_seconds"] > 0


def test_setup_included_in_total_cost():
    runner = _runner()
    record = {
        "timings": {"setup_seconds": 2.0, "solve_seconds": 3.0, "query_seconds": 0.01},
        "wall_seconds": 5.5,
    }
    accounting = runner.cost_accounting([record])
    assert accounting["solver_seconds"] == pytest.approx(5.01)
    assert accounting["charged_wall_seconds"] == pytest.approx(5.5)
    assert accounting["query_only_seconds"] == pytest.approx(0.01)


def test_hash_mismatch_rejected(tmp_path):
    runner = _runner()
    p = tmp_path / "boundary.npz"
    np.savez_compressed(p, x=np.array([1.0, 2.0]))
    artifacts = {p.name: runner.file_sha256(p)}
    assert runner.verify_artifacts(tmp_path, artifacts)
    np.savez_compressed(p, x=np.array([1.0, 3.0]))
    with pytest.raises(ValueError, match="hash"):
        runner.verify_artifacts(tmp_path, artifacts)


def test_result_replay_from_small_artifacts(tmp_path, monkeypatch):
    runner = _runner()
    monkeypatch.setattr(runner, "build_roster", lambda phase: [])
    report = {
        "schema": 1,
        "phase": "pilot",
        "records": [],
        "artifacts": {},
        "sources": runner.source_hashes(),
    }
    report["paper_match"] = runner.paper_gate(report["records"])
    report["preflight"] = runner.preflight(report["records"])
    report.update(
        costs=runner.cost_accounting([]),
        slots=runner.original_slots([]),
        main_slots=runner.original_slots([], reason="main_not_run_in_pilot"),
        reproduction_status="not_reproduced",
    )
    (tmp_path / "results.json").write_text(json.dumps(report, allow_nan=False))
    assert runner.replay(tmp_path)["paper_match"]["passed"] is False
    report["paper_match"]["passed"] = True
    (tmp_path / "results.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="replay"):
        runner.replay(tmp_path)


def test_reproduction_requires_both_gates():
    runner = _runner()
    for paper, independent in ((False, False), (True, False), (False, True)):
        assert runner.reproduction_status(paper, independent) == "not_reproduced"
    assert runner.reproduction_status(True, True) == "reproduced"
    assert runner.paper_gate([])["passed"] is False


def test_frozen_ladder_no_posthoc_tuning():
    runner = _runner()
    roster = runner.build_roster("main")
    s2 = next(j for j in roster if j["id"] == "T0.5:S2")
    assert s2["settings"]["n_var"] == 320
    assert s2["settings"]["panels"][-1] == 2560
    stages = {
        "S0": np.array([0.11, 0.05, 0.02]),
        "S1": np.array([0.110001, 0.050001, 0.020001]),
        "S2": np.array([0.110002, 0.050002, 0.020002]),
    }
    sensitivities = {"S0": {name: stages["S0"].copy() for name in runner.SENSITIVITIES}}
    assert (
        runner.select_stage(
            stages, sensitivities, stages["S1"], reference_supported=True, boundary_accepted=True
        )["stage"]
        == "S0"
    )
    sensitivities["S0"]["chi_low"][1] += 1e-4
    assert (
        runner.select_stage(
            stages, sensitivities, stages["S1"], reference_supported=True, boundary_accepted=True
        )["stage"]
        is None
    )


def test_paper_gate_checks_each_printed_anchor():
    runner = _runner()
    records = []
    for case in runner.load_cases()["primary_groups"]:
        t = case["contract"]["expiry"]
        records.append(
            {
                "id": f"T{t:g}:S0",
                "status": "completed",
                "values": {
                    "american": [
                        x if x is not None else 0.1 for x in case["paper_anchors"]["american"]
                    ],
                    "european": [
                        x if x is not None else 0.09 for x in case["paper_anchors"]["european"]
                    ],
                },
            }
        )
    assert runner.paper_gate(records)["passed"]
    records[0]["values"]["european"][0] += 7e-6
    assert not runner.paper_gate(records)["passed"]


def test_nonfinite_json_and_unfinished_cost_are_not_success():
    runner = _runner()
    assert runner.json_safe({"x": np.nan, "y": np.array([1.0, np.inf])}) == {
        "x": None,
        "y": [1.0, None],
    }
    assessment = runner.preflight([])
    assert assessment["eligible"] is False
    assert "coefficients_unmeasured" in assessment["reasons"]


def test_independent_price_gate_checks_european_eep_and_bounds():
    runner = _runner()
    record = {
        "status": "completed",
        "contract": {"strike": 1.0, "expiry": 0.5, "domestic_rate": 0.05, "foreign_rate": 0.02},
        "spots": [0.9, 1.0, 1.1],
        "values": {
            "american": [0.1076, 0.04866, 0.01950],
            "european": [0.10256, 0.04722, 0.01911],
            "eep": [0.00504, 0.00144, 0.00039],
        },
    }
    eu, am = np.array(record["values"]["european"]), np.array(record["values"]["american"])
    assert runner.independent_price_gate(record, eu, am)["accepted"]
    record["values"]["european"][0] += 1e-4
    assert not runner.independent_price_gate(record, eu, am)["accepted"]
    record["values"]["european"][0] -= 1e-4
    record["values"]["american"][0] = 0.09  # Below exercise payoff.
    assert not runner.independent_price_gate(record, eu, am)["accepted"]


def test_short_rss_peak_reported_at_exit_is_a_failure(tmp_path):
    runner = _runner()
    payload = {
        "id": "peak",
        "status": "completed",
        "peak_rss_bytes": 2 * 1024**3 + 1,
        "values": {
            "american": [0.1, 0.05, 0.02],
            "european": [0.09, 0.04, 0.01],
            "eep": [0.01] * 3,
        },
    }
    script = (
        "from pathlib import Path; Path("
        + repr(str(tmp_path / "peak.worker.json"))
        + ").write_text("
        + repr(json.dumps(payload))
        + ")"
    )
    record = runner.run_bounded([sys.executable, "-c", script], tmp_path, "peak")
    assert record["status"] == "memory_budget_exceeded"
    assert record["values"]["american"] == [None] * 3


def test_output_budget_keeps_every_remaining_slot(tmp_path, monkeypatch):
    runner = _runner()
    monkeypatch.setattr(runner, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(runner, "BUDGETS", {**runner.BUDGETS, "output_bytes": 1})
    monkeypatch.setattr(
        runner,
        "build_roster",
        lambda phase: [{"id": "a", "method": "heston"}, {"id": "b", "method": "heston"}],
    )
    monkeypatch.setattr(
        runner,
        "run_bounded",
        lambda *a, **k: {
            "id": "a",
            "status": "completed",
            "wall_seconds": 0,
            "values": {"american": [None] * 3, "european": [None] * 3, "eep": [None] * 3},
        },
    )
    result = runner.run_phase("pilot", tmp_path / "run")
    assert len(result["records"]) == 2
    assert [r["status"] for r in result["records"]] == ["output_budget_exceeded", "not_run"]
    assert len(result["main_slots"]) == 6


def test_imported_source_must_be_the_hashed_worktree(tmp_path, monkeypatch):
    import hullkit._dsinc_spectral as spectral

    runner = _runner()
    monkeypatch.setattr(spectral, "__file__", str(tmp_path / "another_checkout.py"))
    with pytest.raises(ValueError, match="imported source"):
        runner.source_hashes()


@pytest.mark.parametrize("axis", ["adjacent", "sensitivity"])
def test_european_eep_cancellation_cannot_select_american_only(axis, monkeypatch):
    runner = _runner()
    case = runner.load_cases()["primary_groups"][0]
    eu = np.array([0.10256, 0.04722, 0.01911])
    am = np.array([0.10760, 0.04866, 0.01950])

    def row(tag, european=eu):
        return {
            "id": "T0.5:" + tag,
            "status": "completed",
            "contract": case["contract"],
            "spots": case["spots"],
            "values": {
                "european": european.tolist(),
                "american": am.tolist(),
                "eep": (am - european).tolist(),
            },
            "boundary_comparison": {"accepted": True},
        }

    records = [row("S0"), row("S1", eu + 1e-5 if axis == "adjacent" else eu)]
    records += [
        row("S0:" + name, eu + 1e-5 if axis == "sensitivity" and name == "chi_low" else eu)
        for name in runner.SENSITIVITIES
    ]
    records += [row("ref:european:base"), row("ref:american:base")]
    monkeypatch.setattr(runner, "_refinement", lambda *a: {"supported": True})
    assert runner._main_selection(records)["T0.5"]["stage"] is None


@pytest.mark.parametrize("field", ["reproduction_status", "selection", "slots", "costs"])
def test_main_replay_recomputes_final_decision(tmp_path, monkeypatch, field):
    runner = _runner()
    selection = {"T0.5": {"stage": None}, "T1": {"stage": None}}
    monkeypatch.setattr(runner, "validate_freeze", lambda f: [])
    monkeypatch.setattr(runner, "_main_selection", lambda rows: selection)
    (tmp_path / "freeze_manifest.json").write_text("{}")
    report = {
        "schema": 1,
        "phase": "main",
        "sources": runner.source_hashes(),
        "records": [],
        "artifacts": {
            "freeze_manifest.json": runner.file_sha256(tmp_path / "freeze_manifest.json")
        },
        "selection": selection,
        "paper_match": runner.paper_gate([]),
        "elapsed_seconds": 0.0,
        "slots": runner.original_slots([], selected={}),
        "main_slots": runner.original_slots([], selected={}),
        "costs": runner.cost_accounting([]),
        "reproduction_status": "not_reproduced",
    }
    (tmp_path / "results.json").write_text(json.dumps(report))
    assert runner.replay(tmp_path)["reproduction_status"] == "not_reproduced"
    report[field] = "forged"
    (tmp_path / "results.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="replay"):
        runner.replay(tmp_path)


def test_record_settings_cannot_escape_frozen_roster():
    runner = _runner()
    job = runner.build_roster("main")[0]
    record = {
        **json.loads(json.dumps(job)),
        "status": "completed",
        "input_sha256": runner._digest(job),
    }
    assert runner.verify_record_roster([record], [job])
    record["settings"]["n_var"] += 1
    with pytest.raises(ValueError, match="roster"):
        runner.verify_record_roster([record], [job])


def test_status_compression_is_explicit_and_lossless():
    runner = _runner()
    statuses = [
        ["not_run"] * 3,
        ["not_run"] * 3,
        ["ok", "multiple_roots", "ok"],
        ["ok"] * 3,
        ["maturity_limit"] * 3,
    ]
    encoded = runner._encode_statuses(statuses, 2)
    assert encoded["index_convention"] == "half_open"
    assert encoded["later_rows"]["stop"] == 4
    assert runner._decode_statuses(encoded) == statuses
    statuses[0][0] = "ok"
    with pytest.raises(ValueError, match="status"):
        runner._encode_statuses(statuses, 2)


def test_freeze_rejects_changed_library_version(tmp_path):
    runner = _runner()
    frozen = runner.make_freeze({"preflight": {"eligible": True}}, tmp_path)
    frozen["runtime"]["numpy"] = "different-version"
    frozen["digest"] = runner._digest({k: v for k, v in frozen.items() if k != "digest"})
    with pytest.raises(ValueError, match="policy mismatch"):
        runner.validate_freeze(frozen)


def test_main_replay_rejects_broken_freeze_without_mock(tmp_path):
    runner = _runner()
    frozen = runner.make_freeze({"preflight": {"eligible": False}}, tmp_path)
    frozen["digest"] = "broken"
    (tmp_path / "freeze_manifest.json").write_text(json.dumps(frozen))
    report = {
        "phase": "main",
        "records": [],
        "sources": runner.source_hashes(),
        "artifacts": {
            "freeze_manifest.json": runner.file_sha256(tmp_path / "freeze_manifest.json")
        },
    }
    (tmp_path / "results.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="freeze hash mismatch"):
        runner.replay(tmp_path)
