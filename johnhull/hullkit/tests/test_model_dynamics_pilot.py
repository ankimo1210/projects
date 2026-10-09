"""Streaming common-driver and numerical pilot wiring for RB-F04."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[2] / "research" / "RB-F04" / "pilot.py"


def _pilot():
    assert PATH.is_file(), "RB-F04 numerical pilot is not implemented"
    spec = importlib.util.spec_from_file_location("rb_f04_pilot_test", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parameters():
    return SimpleNamespace(
        spot=100.0, rate=0.03, dividend_yield=0.01, v0=0.04, kappa=2.0, theta=0.04, xi=0.0, rho=-0.7
    )


class ConstantSurface:
    def evaluate(self, t, spots):
        return {"variance": np.full_like(spots, 0.04), "status": np.full(spots.shape, "interior")}


def test_streaming_preserves_monthly_gbm_driver_at_all_three_levels():
    pilot = _pilot()
    result = pilot.simulate(
        _parameters(), ConstantSurface(), paths=19, seed=17, steps=[12, 24, 48], block_size=7
    )
    arrays = result["arrays"]
    rng = np.random.default_rng(17)
    expected = []
    for size in [7, 7, 5]:
        z = rng.standard_normal((size, 48, 2))
        brownian = z[:, :, 0].reshape(size, 12, 4).sum(axis=2) / np.sqrt(48)
        monthly = 100 * np.exp(np.cumsum(brownian * 0.2, axis=1))
        expected.append(np.column_stack([np.full(size, 100), monthly]))
    expected = np.concatenate(expected)
    # r-q-v/2 is zero in this fixture, so only the exact accumulated Brownian matters.
    for level in [12, 24, 48]:
        for model in ["heston", "local"]:
            assert arrays[f"{level}.{model}.observations"] == pytest.approx(expected)
            assert not arrays[f"{level}.{model}.failures"].any()
    assert arrays["12.heston.negative_variance_counts"].sum() == 0
    assert arrays["48.local.status.interior"].sum() == 19 * 48


def test_failed_surface_paths_remain_in_original_row_order():
    pilot = _pilot()

    class UnsupportedSurface:
        def evaluate(self, t, spots):
            return {
                "variance": np.full_like(spots, np.nan),
                "status": np.full(spots.shape, "unsupported_test"),
            }

    result = pilot.simulate(
        _parameters(), UnsupportedSurface(), paths=9, seed=18, steps=[12, 24], block_size=4
    )
    for level in [12, 24]:
        values = result["arrays"][f"{level}.local.observations"]
        assert values.shape == (9, 13)
        assert values[:, 0] == pytest.approx(np.full(9, 100))
        assert np.isnan(values[:, 1:]).all()
        assert result["arrays"][f"{level}.local.failures"].all()


@pytest.mark.parametrize("steps", [[12, 25], [24, 36], []])
def test_streaming_rejects_levels_without_nested_monthly_driver(steps):
    with pytest.raises(ValueError, match="nested"):
        _pilot().simulate(
            _parameters(), ConstantSurface(), paths=3, seed=1, steps=steps, block_size=3
        )


def test_sampling_and_step_bias_are_separate_components():
    pilot = _pilot()
    p = {
        "contract": {"expiry": 1.0, "asian_strike": 100.0},
        "parameters": {"rate": 0.03},
        "quotes": {"times": [0.25, 0.5, 1], "strikes": [90, 100, 110]},
        "two_date": {
            "first": 0.5,
            "second": 1.0,
            "bins": [90, 100, 110],
            "conditional_threshold": 110,
            "minimum_count": 2,
        },
    }
    result = pilot.simulate(
        _parameters(), ConstantSurface(), paths=15, seed=19, steps=[12, 24], block_size=5
    )
    summary = pilot.path_metrics(result["arrays"], p, steps=[12, 24])
    assert len(summary["levels"]) == 2
    assert summary["levels"][0]["asian"]["difference"]["mean"] == pytest.approx(0, abs=1e-13)
    assert summary["levels"][0]["asian"]["heston"]["standard_error"] > 0
    bias = summary["step_changes"][0]
    assert bias["coarse"] == 12 and bias["fine"] == 24
    assert bias["heston_asian"]["mean"] == pytest.approx(0, abs=1e-13)
    assert bias["local_asian"]["mean"] == pytest.approx(0, abs=1e-13)
    assert bias["difference_asian"]["mean"] == pytest.approx(0, abs=1e-13)


def test_surface_builder_preserves_time_dependent_deterministic_variance():
    pilot = _pilot()
    parameters = pilot.module("surface").HestonParameters(
        spot=100, rate=0.03, dividend_yield=0.01, v0=0.09, kappa=2, theta=0.04, xi=0, rho=-0.7
    )
    times = np.array([0.001, 0.1, 0.5, 1.0])
    z = np.linspace(-3, 3, 13)
    result = pilot.build_surface(parameters, times=times, z_nodes=z)
    assert result["grid"] is not None
    assert result["arrays"]["surface.supported"].all()
    expected = 0.04 + 0.05 * np.exp(-2 * times)
    assert result["arrays"]["surface.local_variance"] == pytest.approx(
        np.repeat(expected[:, None], len(z), axis=1)
    )
    assert result["grid"].evaluate(0, np.array([100]))["variance"] == pytest.approx([0.09])


def test_surface_builder_retains_missing_cells_without_fabricating_a_grid():
    pilot = _pilot()
    parameters = pilot.module("surface").HestonParameters(
        spot=100, rate=0.03, dividend_yield=0, v0=0.04, kappa=2, theta=0.04, xi=0, rho=-0.7
    )
    result = pilot.build_surface(
        parameters,
        times=np.array([0.1, 1.0]),
        z_nodes=np.linspace(-4, 4, 9),
        density_floor=1e9,
        allow_row_wings=True,
    )
    assert result["grid"] is None
    assert result["unsupported_cells"] == 18
    assert np.isnan(result["arrays"]["surface.local_variance"]).all()
    assert np.isfinite(result["arrays"]["surface.price"]).all()
    assert result["failure"]


def test_step_refinement_reports_each_models_two_date_numerical_change():
    pilot = _pilot()
    protocol = {
        "contract": {"expiry": 1.0, "asian_strike": 100.0},
        "parameters": {"rate": 0.03},
        "quotes": {"times": [0.25, 0.5, 1], "strikes": [90, 100, 110]},
        "two_date": {
            "first": 0.5,
            "second": 1.0,
            "bins": [90, 100, 110],
            "conditional_threshold": 110,
            "minimum_count": 2,
        },
    }
    result = pilot.simulate(
        _parameters(), ConstantSurface(), paths=15, seed=19, steps=[12, 24], block_size=5
    )
    changes = pilot.path_metrics(result["arrays"], protocol, steps=[12, 24])["step_changes"][0]
    assert "heston_two_date" in changes, "two-date numerical refinement is missing"
    for model in ["heston", "local"]:
        comparison = changes[model + "_two_date"]
        assert comparison["direction"] == "fine-minus-coarse"
        assert np.array(comparison["joint_difference"]) == pytest.approx(np.zeros((4, 4)))
        assert np.array(comparison["joint_standard_error"]) == pytest.approx(np.zeros((4, 4)))


@pytest.fixture(scope="module")
def saved_smoke(tmp_path_factory):
    pilot = _pilot()
    assert callable(getattr(pilot, "run_pilot", None)), "saved numerical pilot is missing"
    directory = tmp_path_factory.mktemp("rbf04-pilot")
    pilot.run_pilot(directory, smoke=True)
    return directory


def _copied_bundle(saved, target):
    import shutil

    shutil.copytree(saved, target)
    return target


def _rewrite_bundle(directory, *, mutate_array=None, mutate_record=None):
    import json

    record_file = directory / "pilot.json"
    record = json.loads(record_file.read_text())
    with np.load(directory / "pilot.npz", allow_pickle=False) as saved:
        arrays = {key: saved[key] for key in saved.files}
    if mutate_array is not None:
        mutate_array(arrays)
        np.savez_compressed(directory / "pilot.npz", **arrays)
    if mutate_record is not None:
        mutate_record(record)
    # SHA is provenance only: let numerical checks inspect deliberately changed arrays.
    record.pop("artifact", None)
    record_file.write_text(json.dumps(record))


def test_smoke_saved_bundle_recomputes_without_research_acceptance(saved_smoke):
    import json

    pilot = _pilot()
    record = json.loads((saved_smoke / "pilot.json").read_text())
    assert record["state"] == "smoke"
    assert record["research_acceptance"] is False
    assert record["freeze_eligible"] is False
    outcome = pilot.check(saved_smoke)
    assert outcome["passed"], outcome["failures"]
    assert outcome["research_acceptance"] is False
    with np.load(saved_smoke / "pilot.npz", allow_pickle=False) as saved:
        assert saved["paths.baseline.96.heston.observations"].shape == (128, 13)
        assert saved["surface.baseline.local_variance"].shape[0] > 1
        assert len(saved["pde.baseline.quote_times"]) == 28
        assert "surface.early_min.times" in saved.files
        baseline_times = saved["surface.baseline.times"]
        early_times = saved["surface.early_min.times"]
        assert early_times[1:] == pytest.approx(baseline_times)
        assert early_times[0] == pytest.approx(baseline_times[0] / 4)
        coarse = record["summary"]["paths"]["baseline"]["step_changes"][0]
        assert "heston_two_date" in coarse
        assert "two_date" in record["summary"]["surface_changes"]["time_refined"]


def test_saved_checker_rejects_numerical_observation_tamper(saved_smoke, tmp_path):
    directory = _copied_bundle(saved_smoke, tmp_path / "altered")

    def alter(arrays):
        arrays["paths.baseline.96.local.observations"][0, -1] += 30

    _rewrite_bundle(directory, mutate_array=alter)
    outcome = _pilot().check(directory)
    assert not outcome["passed"]
    assert any("summary" in failure for failure in outcome["failures"])


def test_saved_checker_rejects_surface_visit_counts_tamper(saved_smoke, tmp_path):
    directory = _copied_bundle(saved_smoke, tmp_path / "altered")

    def alter(arrays):
        key = next(key for key in arrays if key.startswith("paths.baseline.96.local.status."))
        arrays[key][0] += 1

    _rewrite_bundle(directory, mutate_array=alter)
    outcome = _pilot().check(directory)
    assert not outcome["passed"]
    assert any("count" in failure or "summary" in failure for failure in outcome["failures"])


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("parameters", "spot", 101.0),
        ("contract", "include_initial", True),
    ],
)
def test_saved_checker_rejects_parameter_or_contract_mismatch(
    saved_smoke, tmp_path, section, field, value
):
    directory = _copied_bundle(saved_smoke, tmp_path / "altered")

    def alter(record):
        record["protocol"][section][field] = value

    _rewrite_bundle(directory, mutate_record=alter)
    outcome = _pilot().check(directory)
    assert not outcome["passed"]
    assert any("protocol" in failure or "contract" in failure for failure in outcome["failures"])


def test_fresh_check_uses_numerical_tolerance_and_ignores_wall_clock(saved_smoke, tmp_path):
    directory = _copied_bundle(saved_smoke, tmp_path / "altered")

    def alter_record(record):
        record["timing"]["total_wall_s"] = 12345.0

    def alter_array(arrays):
        arrays["paths.baseline.96.local.observations"][0, -1] += 1e-10

    _rewrite_bundle(directory, mutate_record=alter_record, mutate_array=alter_array)
    outcome = _pilot().check(directory, fresh=True)
    assert outcome["passed"], outcome["failures"]
    assert outcome["fresh_regenerated"] is True


def test_surface_builder_retains_raw_support_resolution_evidence():
    pilot = _pilot()
    parameters = pilot.module("surface").HestonParameters(
        spot=100, rate=0.03, dividend_yield=0, v0=0.04, kappa=2, theta=0.04, xi=0.3, rho=-0.7
    )
    result = pilot.build_surface(
        parameters, times=[0.01, 0.5], z_nodes=[-2, 0, 2], allow_row_wings=True
    )
    arrays = result["arrays"]
    assert "surface.half_density" in arrays, "source support resolution evidence is missing"
    assert arrays["surface.half_density"].shape == (2, 3)
    assert arrays["surface.half_weighted_density"].shape == (2, 3)
    assert arrays["surface.cutoff_cf_abs"].shape == (2,)
    assert arrays["surface.cutoff_weighted_cf_abs"].shape == (2,)


def test_surface_pde_refinement_uses_one_fixed_pde_grid(saved_smoke):
    import json

    record = json.loads((saved_smoke / "pilot.json").read_text())
    assert "surface_pde" in record["summary"], "surface/PDE errors are not separated"
    with np.load(saved_smoke / "pilot.npz", allow_pickle=False) as arrays:
        assert "surface.joint_refined.times" in arrays.files
        assert (
            arrays["surface.joint_refined.times"].shape
            == arrays["surface.time_refined.times"].shape
        )
        assert (
            arrays["surface.joint_refined.z_nodes"].shape
            == arrays["surface.z_refined.z_nodes"].shape
        )
        for variant in record["settings"]["surface_specs"]:
            prefix = f"surface_pde.{variant}."
            assert arrays[prefix + "price"].shape == (28,)
            assert arrays[prefix + "grid.0.space_nodes"] == 121
            assert arrays[prefix + "grid.0.time_steps"] == 48
        assert arrays["surface_pde.baseline.price"] == pytest.approx(arrays["pde.joint_fine.price"])
        assert (
            record["summary"]["surface_pde"]["time_refined"]["direction"]
            == "variant-minus-baseline"
        )


def test_saved_checker_recomputes_surface_support_even_when_summary_is_rewritten(
    saved_smoke, tmp_path
):
    import json

    pilot = _pilot()
    directory = _copied_bundle(saved_smoke, tmp_path / "altered")
    record = json.loads((directory / "pilot.json").read_text())
    with np.load(directory / "pilot.npz", allow_pickle=False) as saved:
        arrays = {key: saved[key] for key in saved.files}
    row, col = np.argwhere(arrays["surface.baseline.supported"])[0]
    arrays["surface.baseline.density"][row, col] = -1e-5
    record["summary"] = pilot.summarize(record, arrays)
    record.pop("artifact", None)
    np.savez_compressed(directory / "pilot.npz", **arrays)
    (directory / "pilot.json").write_text(json.dumps(record))
    outcome = pilot.check(directory)
    assert not outcome["passed"]
    assert any("support" in failure for failure in outcome["failures"])


def test_saved_checker_preserves_unsupported_surface_cells(saved_smoke):
    with np.load(saved_smoke / "pilot.npz", allow_pickle=False) as arrays:
        unsupported = 0
        for variant in [
            "baseline",
            "time_refined",
            "z_refined",
            "joint_refined",
            "wing4",
            "wing6",
            "early_min",
        ]:
            support = arrays[f"surface.{variant}.supported"]
            local = arrays[f"surface.{variant}.local_variance"]
            unsupported += np.count_nonzero(~support)
            assert np.isnan(local[~support]).all()
        assert unsupported > 0, "smoke must exercise retained unsupported wing cells"


def test_checker_recomputes_fourier_support_when_summary_is_rewritten(saved_smoke, tmp_path):
    import json

    pilot = _pilot()
    directory = _copied_bundle(saved_smoke, tmp_path / "altered")
    record = json.loads((directory / "pilot.json").read_text())
    with np.load(directory / "pilot.npz", allow_pickle=False) as saved:
        arrays = {key: saved[key] for key in saved.files}
    prefix = "fourier.order_refined."
    row, col = np.argwhere(arrays[prefix + "supported"])[0]
    arrays[prefix + "supported"][row, col] = False
    arrays[prefix + "local_variance"][row, col] = np.nan
    record["summary"] = pilot.summarize(record, arrays)
    record.pop("artifact", None)
    np.savez_compressed(directory / "pilot.npz", **arrays)
    (directory / "pilot.json").write_text(json.dumps(record))
    outcome = pilot.check(directory)
    assert not outcome["passed"]
    assert any("fourier" in failure and "support" in failure for failure in outcome["failures"])


def test_embedded_pilot_check_uses_raw_arrays_without_a_saved_bundle(saved_smoke, tmp_path):
    import json

    pilot = _pilot()
    directory = _copied_bundle(saved_smoke, tmp_path / "embedded")
    record = json.loads((directory / "pilot.json").read_text())
    with np.load(directory / "pilot.npz", allow_pickle=False) as saved:
        arrays = {key: saved[key] for key in saved.files}
    (directory / "pilot.json").unlink()
    (directory / "pilot.npz").unlink()
    result = pilot.check_record(record, arrays)
    assert result["passed"], result["failures"]
    arrays["paths.baseline.96.local.status.initial_state"][0] += 1
    result = pilot.check_record(record, arrays)
    assert not result["passed"]


def test_fresh_regeneration_rejects_a_rewritten_path_summary(saved_smoke, tmp_path):
    import json

    pilot = _pilot()
    directory = _copied_bundle(saved_smoke, tmp_path / "altered")
    record = json.loads((directory / "pilot.json").read_text())
    with np.load(directory / "pilot.npz", allow_pickle=False) as saved:
        arrays = {key: saved[key] for key in saved.files}
    arrays["paths.baseline.96.local.observations"][0, -1] += 5
    record["summary"] = pilot.summarize(record, arrays)
    record.pop("artifact", None)
    np.savez_compressed(directory / "pilot.npz", **arrays)
    (directory / "pilot.json").write_text(json.dumps(record))
    # Matching summaries establish internal consistency, not independent regeneration.
    assert pilot.check(directory)["passed"]
    result = pilot.check(directory, fresh=True)
    assert not result["passed"]
    assert result["fresh_regenerated"]
    assert any(
        "fresh paths.baseline.96.local.observations" in failure for failure in result["failures"]
    )


def test_pilot_cli_returns_check_result_and_never_freezes_smoke(saved_smoke, tmp_path, capsys):
    import json

    pilot = _pilot()
    assert pilot.main(["--check", "--output", str(saved_smoke)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True
    assert payload["research_acceptance"] is False
    assert pilot.main(["--check", "--output", str(tmp_path / "missing")]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is False
    with pytest.raises(SystemExit) as exit_error:
        pilot.main(["--fresh"])
    assert exit_error.value.code == 2
