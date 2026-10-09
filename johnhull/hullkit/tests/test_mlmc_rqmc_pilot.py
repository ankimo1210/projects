"""RB-F08 fixed pilot accounting and evidence recomputation."""

import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[2] / "research" / "RB-F08" / "pilot.py"


def _pilot():
    assert PATH.is_file(), "RB-F08 pilot is not implemented"
    spec = importlib.util.spec_from_file_location("rb_f08_pilot_test", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _small_protocol(pilot):
    protocol = pilot.module("protocol")
    p = protocol.candidate_protocol()
    p["main"]["outer_runs"] = 2
    p["rqmc"].update(strikes=[100.0], powers=[2], scrambles=[2], outer_runs=2)
    p["fresh_review"].update(strikes=[100.0], coverage_replay_runs=[0, 1])
    return protocol.attach_seed_ledger(p, protocol.build_seed_ledger(p))


def _source(pilot):
    protocol = pilot.module("protocol")
    source = {
        "files": dict.fromkeys(protocol.SOURCE_FILES, "a" * 64),
        "dependencies": {"python": "test", "numpy": "test", "scipy": "test"},
    }
    source["digest"] = protocol.json_digest(source)
    return source


def _fixture(pilot, *, bias=(-0.20, -0.08, -0.02), negative=0):
    p = pilot.module("protocol").candidate_protocol()
    p["epsilon"] = [0.10]
    p["pilot"]["levels"] = [0, 1, 2]
    p["main"]["levels_reserved"] = [0, 1, 2]
    n = 100000
    fine_means = np.array([10.0, 10.1, 10.12])
    fine_variance = np.array([4.0, 3.0, 2.25])
    coarse_means = np.array([0.0, 10.0, 10.1])
    coarse_variance = np.array([0.0, 4.0, 3.0])
    difference_mean = fine_means - coarse_means
    difference_variance = np.array([4.0, 1.0, 0.25])
    bias_variance = np.array([0.01, 0.01, 0.001]) ** 2 * n
    arrays = {
        "euler.level": np.arange(3),
        "euler.stream": np.zeros(3, dtype=int),
        "euler.block": np.zeros(3, dtype=int),
        "euler.seed": np.array([11, 13, 17], dtype=np.uint32),
        "euler.count": np.full(3, n, dtype=int),
        "euler.fine.mean": fine_means,
        "euler.fine.m2": fine_variance * (n - 1),
        "euler.coarse.mean": coarse_means,
        "euler.coarse.m2": coarse_variance * (n - 1),
        "euler.difference.mean": difference_mean,
        "euler.difference.m2": difference_variance * (n - 1),
        "euler.bias.mean": np.asarray(bias),
        "euler.bias.m2": bias_variance * (n - 1),
        "euler.exact.mean": fine_means - np.asarray(bias),
        "euler.exact.m2": fine_variance * (n - 1),
        "euler.fine_coarse_c2": (fine_variance + coarse_variance - difference_variance)
        / 2
        * (n - 1),
        "euler.fine_exact_c2": (2 * fine_variance - bias_variance) / 2 * (n - 1),
        "euler.fine_negative_states": np.zeros(3, dtype=int),
        "euler.coarse_negative_states": np.zeros(3, dtype=int),
        "euler.negative_paths": np.full(3, negative, dtype=int),
        "euler.rng_s": np.full(3, 0.1),
        "euler.engine_s": np.full(3, 0.2),
        "euler.summary_s": np.full(3, 0.01),
        "calibration.level": np.repeat(np.arange(3), 8),
        "calibration.repeat": np.tile(np.arange(8), 3),
        "calibration.warmup": np.tile([True] + [False] * 7, 3),
        "calibration.count": np.ones(24, dtype=int),
        "calibration.total_s": np.repeat([1.0, 4.0, 16.0], 8),
        "exact.stream": np.array([0]),
        "exact.block": np.array([0]),
        "exact.seed": np.array([19], dtype=np.uint32),
        "exact.count": np.array([n]),
        "exact.payoff.mean": np.array([10.0]),
        "exact.payoff.m2": np.array([4.0 * (n - 1)]),
        "exact.control.mean": np.array([100.0]),
        "exact.control.m2": np.array([9.0 * (n - 1)]),
        "exact.payoff_control_c2": np.array([3.0 * (n - 1)]),
        "exact.rng_s": np.array([0.1]),
        "exact.engine_s": np.array([0.2]),
        "exact.summary_s": np.array([0.01]),
    }
    return p, arrays


def test_cost_counts_do_not_double_count_the_fine_normals():
    pilot = _pilot()
    assert pilot.cost_counts(level=0, base_steps=4, paths=10) == {
        "stock_updates": 40,
        "normal_draws": 40,
        "payoff_evaluations": 10,
        "coarse_aggregations": 0,
    }
    assert pilot.cost_counts(level=2, base_steps=4, paths=10) == {
        "stock_updates": 240,
        "normal_draws": 160,
        "payoff_evaluations": 20,
        "coarse_aggregations": 80,
    }


@pytest.mark.parametrize("level,base_steps,paths", [(-1, 4, 10), (1, 0, 10), (1, 4, 0)])
def test_cost_counts_reject_meaningless_counts(level, base_steps, paths):
    with pytest.raises(ValueError):
        _pilot().cost_counts(level=level, base_steps=base_steps, paths=paths)


def test_fixed_moments_select_paired_bias_level_and_ceil_allocation():
    pilot = _pilot()
    p, arrays = _fixture(pilot)
    out = pilot.choose_allocations({}, arrays, p)[0]
    assert out["status"] == "ready"
    assert out["level"] == 2
    assert out["bias_bound"] == pytest.approx(0.02 + 2.57588 * 0.001, rel=2e-5)
    expected = np.ceil(
        np.sqrt(np.array([4.0, 1.0, 0.25]) / np.array([1.0, 4.0, 16.0]))
        * np.sqrt(np.array([4.0, 1.0, 0.25]) * np.array([1.0, 4.0, 16.0])).sum()
        / 0.005
    ).astype(int)
    assert out["mlmc_paths"] == expected.tolist()
    assert out["plain_euler_paths"] == 450
    assert out["exact_plain_paths"] == 800
    assert out["exact_cv_paths"] == 600
    assert out["method_status"] == dict.fromkeys(
        ["mlmc", "plain_euler", "exact_plain", "exact_cv"], "ready"
    )


def test_bias_unresolved_keeps_exact_baselines_and_failure_roster():
    pilot = _pilot()
    p, arrays = _fixture(pilot, bias=(0.2, 0.2, 0.2))
    out = pilot.choose_allocations({}, arrays, p)[0]
    assert out["status"] == "bias_unresolved"
    assert out["level"] is None
    assert out["mlmc_paths"] is None
    assert out["method_status"]["exact_plain"] == "ready"
    assert out["exact_plain_paths"] == 800
    assert len(out["candidate_levels"]) == 1


def test_observed_negative_paths_above_threshold_do_not_get_filtered():
    pilot = _pilot()
    p, arrays = _fixture(pilot, negative=2)
    out = pilot.choose_allocations({}, arrays, p)[0]
    assert out["status"] == "coarse_grid_invalid"
    assert out["candidate_levels"][0]["negative_path_rate"] == pytest.approx(2e-5)
    assert out["method_status"]["exact_plain"] == "ready"


def test_budget_failure_keeps_allocations_and_other_methods():
    pilot = _pilot()
    p, arrays = _fixture(pilot)
    p["caps"]["paths_per_run"] = 900
    out = pilot.choose_allocations({}, arrays, p)[0]
    assert out["status"] == "budget_failure"
    assert out["mlmc_paths"] is not None
    assert out["method_status"]["plain_euler"] == "ready"
    assert out["method_status"]["exact_plain"] == "ready"


def test_block_covariance_merges_centered_moments():
    pilot = _pilot()
    fine = np.array([1.0, 2.0, 4.0, 8.0])
    coarse = np.array([0.5, 2.0, 3.0, 6.0])
    blocks = [pilot._pair_moments(fine[:2], coarse[:2]), pilot._pair_moments(fine[2:], coarse[2:])]
    out = pilot._merge_pair_moments(blocks)
    assert out["covariance"] == pytest.approx(np.cov(fine, coarse, ddof=1)[0, 1])
    assert out["first"]["variance"] == pytest.approx(np.var(fine, ddof=1))
    assert out["second"]["variance"] == pytest.approx(np.var(coarse, ddof=1))


def test_smoke_keeps_block_denominators_and_typed_ledger(monkeypatch):
    pilot = _pilot()
    p = _small_protocol(pilot)
    monkeypatch.setattr(pilot, "_current_source", lambda: _source(pilot))
    record, arrays = pilot.run_pilot(p, mode="smoke")
    assert record["mode"] == "smoke"
    assert len(record["level_summaries"]) == 3
    assert [row["count"] for row in record["level_summaries"]] == [32, 32, 32]
    assert record["exact_summary"]["payoff"]["count"] == 32
    assert record["source_fingerprint"] == _source(pilot)["digest"]
    assert any(key.startswith("seed_ledger_") for key in arrays)
    assert all(np.asarray(value).dtype.kind != "O" for value in arrays.values())
    assert len({item["expense_id"] for item in record["expenses"]}) == len(record["expenses"])
    assert pilot.validate_pilot(record, arrays, p)["passed"] is True


def test_smoke_numeric_replay_uses_saved_seeds_and_ignores_new_timings(monkeypatch):
    pilot = _pilot()
    p = _small_protocol(pilot)
    monkeypatch.setattr(pilot, "_current_source", lambda: _source(pilot))
    record, arrays = pilot.run_pilot(p, mode="smoke")
    assert pilot.fresh_check(record, arrays, p)["passed"] is True


@pytest.mark.parametrize(
    "target",
    [
        "allocations",
        "cv_beta",
        "negative_counts",
        "moment_relation",
        "expense",
        "source",
        "diagnostic_cost",
    ],
)
def test_saved_flags_or_moments_are_not_accepted_without_recomputation(monkeypatch, target):
    pilot = _pilot()
    p = _small_protocol(pilot)
    monkeypatch.setattr(pilot, "_current_source", lambda: _source(pilot))
    record, arrays = pilot.run_pilot(p, mode="smoke")
    record, arrays = deepcopy(record), {key: value.copy() for key, value in arrays.items()}
    if target == "allocations":
        record["allocations"][0]["exact_plain_paths"] += 10
    elif target == "cv_beta":
        record["cv_beta"] += 0.2
    elif target == "negative_counts":
        arrays["euler.negative_paths"][0] = 33
    elif target == "moment_relation":
        arrays["euler.difference.mean"][0] += 1
    elif target == "expense":
        record["expenses"][0]["seconds"] += 1
    elif target == "diagnostic_cost":
        arrays["euler.diagnostic_cost.normal_sums"][0] += 1
    else:
        record["source_fingerprint"] = "0" * 64
    with pytest.raises(ValueError):
        pilot.validate_pilot(record, arrays, p)


def test_smoke_cannot_freeze_even_with_approved_hashes(monkeypatch):
    pilot = _pilot()
    protocol = pilot.module("protocol")
    p = _small_protocol(pilot)
    source = _source(pilot)
    monkeypatch.setattr(pilot, "_current_source", lambda: source)
    record, arrays = pilot.run_pilot(p, mode="smoke")
    conditions = protocol.protocol_conditions(p)
    review = {
        "decision": "approved",
        "pilot_record_digest": protocol.json_digest(record),
        "pilot_arrays_digest": protocol.arrays_digest(arrays),
        "protocol_digest": protocol.json_digest(conditions),
        "seed_ledger_digest": p["seed_ledger_meta"]["digest"],
        "source_fingerprint": source["digest"],
        "approved_conditions": conditions,
        "approved_allocations": record["allocations"],
        "approved_cv_beta": record["cv_beta"],
    }
    with pytest.raises(ValueError, match=r"full|smoke"):
        protocol.freeze_protocol(p, record, arrays, review, source=source)


def test_missing_required_source_fails_before_any_sampling(monkeypatch):
    pilot = _pilot()
    protocol = pilot.module("protocol")
    p = _small_protocol(pilot)
    monkeypatch.setattr(protocol, "SOURCE_FILES", ("missing_required_source.py",))
    monkeypatch.setattr(np.random, "default_rng", lambda *args: pytest.fail("sampling began"))
    with pytest.raises(FileNotFoundError):
        pilot.run_pilot(p, mode="smoke")


def test_odd_final_singleton_is_merged_without_losing_original_paths():
    pilot = _pilot()
    assert pilot._block_sizes(3, 2) == [3]
    assert pilot._block_sizes(5, 2) == [2, 3]

    assert pilot._block_sizes(2049, 2048) == [2049]
    assert pilot._block_sizes(4097, 2048) == [2048, 2049]


def test_pilot_clip_diagnostic_is_fixed_seed_crn_and_not_an_mlmc_sample(monkeypatch):
    pilot = _pilot()
    p = _small_protocol(pilot)
    monkeypatch.setattr(pilot, "_current_source", lambda: _source(pilot))
    record, arrays = pilot.run_pilot(p, mode="smoke")
    diagnostic = record["clip_diagnostic"]
    slot = next(row for row in p["seed_ledger"] if row["method"] == "clip_diagnostic")
    assert diagnostic["seed"] == slot["seed"]
    assert diagnostic["power"] == p["clip_diagnostic"]["power"]
    assert arrays["clip.uniforms"].shape == (2 ** diagnostic["power"],)
    assert len(record["level_summaries"]) == 3
    assert record["level_summaries"][0]["count"] == 32
    for index, case in enumerate(diagnostic["cases"]):
        assert case["sample_difference"] == pytest.approx(
            arrays["clip.payoffs"][index, 1].mean() - arrays["clip.payoffs"][index, 0].mean()
        )
        assert case["analytic_difference"] == pytest.approx(
            arrays["clip.truths"][index, 1] - arrays["clip.truths"][index, 0]
        )
    assert pilot.fresh_check(record, arrays, p)["passed"] is True


def test_allocation_fees_do_not_force_euler_work_onto_exact_baselines(monkeypatch):
    pilot = _pilot()
    p = _small_protocol(pilot)
    monkeypatch.setattr(pilot, "_current_source", lambda: _source(pilot))
    record, arrays = pilot.run_pilot(p, mode="smoke")
    euler = [row for row in record["expenses"] if row["expense_id"].startswith("allocation.euler")]
    assert euler
    assert all(
        "exact_plain" not in row["methods"] and "exact_cv" not in row["methods"] for row in euler
    )
    arrays["allocation.methods"][0] = "exact_plain"
    next(row for row in record["expenses"] if row["expense_id"] == "allocation.euler_summary")[
        "methods"
    ] = ["exact_plain"]
    with pytest.raises(ValueError):
        pilot.validate_pilot(record, arrays, p)


def test_clip_payoffs_and_seed_tampering_is_rejected(monkeypatch):
    pilot = _pilot()
    p = _small_protocol(pilot)
    monkeypatch.setattr(pilot, "_current_source", lambda: _source(pilot))
    record, arrays = pilot.run_pilot(p, mode="smoke")
    arrays["clip.payoffs"][0, 0, 0] += 1
    with pytest.raises(ValueError):
        pilot.validate_pilot(record, arrays, p)


def test_planned_cli_generates_smoke_from_explicit_protocol_and_fresh_checks(tmp_path):
    pilot = _pilot()
    source = tmp_path / "input.json"
    source.write_text(json.dumps(_small_protocol(pilot)))
    output = tmp_path / "smoke"
    command = [
        sys.executable,
        str(PATH),
        "--protocol",
        str(source),
        "--mode",
        "smoke",
        "--output",
        str(output),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    record = json.loads((output / "pilot.json").read_text())
    assert record["mode"] == "smoke"
    assert record["actual"]["paths"] == 32
    assert (output / "protocol.json").is_file()
    result = subprocess.run(
        [sys.executable, str(PATH), "--check", str(output), "--fresh"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["passed"] is True
    assert json.loads(result.stdout)["numerical_columns"] > 0
    # The pre-existing --directory/--fresh-alone spelling remains supported.
    result = subprocess.run(
        [sys.executable, str(PATH), "--directory", str(output), "--fresh"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_hydrated_input_ledger_is_loaded_from_input_parent_not_output(tmp_path):
    pilot = _pilot()
    p = _small_protocol(pilot)
    original_record, arrays = pilot.run_pilot(p, mode="smoke")
    input_dir = tmp_path / "input"
    pilot.save_pilot(original_record, arrays, directory=input_dir)
    output = tmp_path / "new_output"
    result = subprocess.run(
        [
            sys.executable,
            str(PATH),
            "--protocol",
            str(input_dir / "protocol.json"),
            "--mode",
            "smoke",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    saved = json.loads((output / "pilot.json").read_text())
    assert saved["seed_ledger_digest"] == original_record["seed_ledger_digest"]
    assert saved["setup_ledger_generated"] is False


def test_save_refuses_existing_pilot_evidence_without_touching_it(tmp_path):
    pilot = _pilot()
    target = tmp_path / "pilot.json"
    target.write_text("existing independently reviewed evidence\n")
    with pytest.raises(FileExistsError):
        pilot.save_pilot({}, {}, directory=tmp_path)
    assert target.read_text() == "existing independently reviewed evidence\n"
    assert not (tmp_path / "pilot.npz").exists()


def test_generation_refuses_existing_output_before_starting_full_pilot(tmp_path, monkeypatch):
    pilot = _pilot()
    target = tmp_path / "pilot.npz"
    target.write_bytes(b"existing original observations")
    monkeypatch.setattr(
        pilot, "run_pilot", lambda *args, **kwargs: pytest.fail("full sampling began")
    )
    with pytest.raises(FileExistsError):
        pilot.main(["--mode", "full", "--output", str(tmp_path)])
    assert target.read_bytes() == b"existing original observations"


def test_freeze_cli_accepts_directory_argument_and_preserves_smoke_rejection(tmp_path):
    pilot = _pilot()
    record, arrays = pilot.run_pilot(_small_protocol(pilot), mode="smoke")
    pilot.save_pilot(record, arrays, directory=tmp_path)
    review = tmp_path / "review.json"
    review.write_text("{}")
    result = subprocess.run(
        [sys.executable, str(PATH), "--freeze", str(tmp_path), "--review", str(review)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "full pilot required" in result.stderr
    assert "unrecognized arguments" not in result.stderr
    assert not (tmp_path / "freeze_cost.json").exists()
