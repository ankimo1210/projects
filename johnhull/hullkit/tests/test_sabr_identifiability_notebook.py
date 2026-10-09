"""Display-only RB-F06 tests; hand-made saved fixtures are not study evidence."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import matplotlib
import nbformat
import numpy as np
import pytest

matplotlib.use("Agg")
HERE = Path(__file__).resolve().parents[2] / "research/RB-F06"


def builder():
    spec = importlib.util.spec_from_file_location("rbf06_notebook_test", HERE / "build_notebook.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def toy(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    artifacts = tmp_path / "saved"
    artifacts.mkdir()
    arrays = {}
    protocol = {
        "forward": 100.0,
        "maturity": 1.0,
        "beta": 0.5,
        "discount": 1.0,
        "noise_scale": 0.0005,
        "parameter_scale": [0.2, 0.5, 0.5],
        "bounds": [[0.05, -0.95, 0.0], [0.50, 0.95, 1.5]],
        "truths": [
            {"name": "toy_ordinary", "theta": [0.2, -0.3, 0.4]},
            {"name": "toy_weak", "theta": [0.2, -0.3, 0.02]},
        ],
        "groups": {"full": [0, 1, 2], "atm": [0], "sparse": [0, 1]},
        "representative_noisy_rep": 0,
        "profile_threshold": 3.841458820694124,
        "baseline_improvement_tolerance": 1e-6,
        "noiseless_delta_q": 1e-6,
        "noiseless_max_iv_error": 1e-9,
        "jacobian_steps_u": [1e-4, 3e-5, 1e-5],
        "holdout_log_moneyness": [-0.15, 0.15],
        "holdout_kind": ["interpolation", "extrapolation"],
        "seed_ledger": [{"phase": "fixture", "seed": 123}],
        "claims": {"hagan": "approximate map only"},
    }
    spec = importlib.util.spec_from_file_location("rbf06_actual_analytics", HERE / "analytics.py")
    actual_analytics = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(actual_analytics)
    datasets = []
    for ti, group, rep, success in [
        (0, "full", 0, True),
        (0, "full", 1, False),
        (1, "sparse", 0, True),
    ]:
        name = f"toy_t{ti}_{group}_r{rep}"
        fid = name + "_fit"
        values = {
            "theta": [0.2, -0.3, 0.4 if ti == 0 else 0.0],
            "raw_residual": [0.0001, -0.0001],
            "singular_values": [4.0, 2.0, 1.0] if ti == 0 else [3.0, 0.0, 0.0],
            "right_vectors": np.eye(3),
            "boundary_flags": [False, False, ti == 1],
            "holdout_iv": [0.19, 0.2],
            "holdout_prices": [10.0, 2.0],
        }
        keys = {}
        for key, value in values.items():
            keys[key] = fid + "_" + key
            arrays[keys[key]] = np.asarray(value)
        jacobian_key = fid + "_stability_jacobians"
        base_jacobian = np.diag(values["singular_values"])
        factors = [1.00001, 1.0, 1.00002] if ti == 0 else [1.002, 1.0, 1.004]
        arrays[jacobian_key] = np.stack([base_jacobian * value for value in factors])
        actual_stability = actual_analytics.jacobian_stability(arrays[jacobian_key])
        assert isinstance(actual_stability["relative_matrix_change"], float)
        fit = {
            "fit_id": fid,
            "kind": "unrestricted",
            "q": 1.0,
            "success": success,
            "rank": 3 if ti == 0 else 1,
            "condition": 4.0 if ti == 0 else None,
            "array_keys": keys,
            "residual_calls": 2,
            "diagnostic_calls": 1,
            "scalar_iv_evaluations": 6,
            "seconds": 0.01,
            "stability_jacobians_key": jacobian_key,
            "numerical_stability": actual_stability,
        }
        points, curves = [], []
        for axis, grid in enumerate([[0.1, 0.2, 0.3], [-0.6, -0.3, 0.3], [0.0, 0.4, 1.5]]):
            ids = []
            for j, value in enumerate(grid):
                pid = name + f"_p{axis}_{j}"
                valid = success and not (axis == 2 and j == 1)
                q = (1.0 + j if ti == 0 else 0.4 + j) if valid else None
                points.append(
                    {
                        "point_id": pid,
                        "axis": axis,
                        "value": value,
                        "q": q,
                        "success": valid,
                        "slice_q": 5.0 + j,
                    }
                )
                ids.append(pid)
            curves.append(
                {
                    "axis": axis,
                    "point_ids": ids,
                    "initial_point_ids": ids,
                    "threshold": protocol["profile_threshold"],
                    "segments": {
                        "observed_components": [[grid[0], grid[0]]],
                        "unknown_brackets": [[grid[0], grid[1]], [grid[1], grid[2]]]
                        if axis == 2
                        else [],
                        "lower_censored": axis == 2,
                        "upper_censored": False,
                        "guaranteed_full_support": False,
                    },
                }
            )
        truth_iv, truth_prices = name + "_truth_iv", name + "_truth_prices"
        arrays[truth_iv], arrays[truth_prices] = np.array([0.19, 0.20]), np.array([9.9, 1.9])
        datasets.append(
            {
                "dataset_id": name,
                "truth_index": ti,
                "group": group,
                "rep": rep,
                "fits": [fit],
                "profile_points": points,
                "curves": curves,
                "truth_points": [curve["point_ids"][0] for curve in curves],
                "holdout_truth_iv_key": truth_iv,
                "holdout_truth_prices_key": truth_prices,
            }
        )
    record = {
        "schema": "RB-F06-study-v1",
        "phase": "fixture",
        "protocol": protocol,
        "protocol_digest": "toy-only",
        "datasets": datasets,
        "complete": True,
        "teaching_acceptance": False,
        "costs": {
            "solver_calls": 3,
            "exceptions": 0,
            "evaluation_count_unknown": 0,
            "attempt_seconds": 0.03,
            "solver_seconds": 0.02,
            "diagnostic_seconds": 0.01,
        },
        "runtime": {"invocation_seconds": 0.06, "cost_scope": "toy display-only fixture"},
    }
    (artifacts / "reference.json").write_text(json.dumps(record))
    np.savez(artifacts / "reference.npz", **arrays)
    loader = f"""
import importlib.util
import json
from pathlib import Path
import numpy as np
import scipy.optimize as opt

def forbidden(*args, **kwargs):
    raise AssertionError("notebook attempted RNG/optimization")
np.random.default_rng = forbidden
np.random.normal = forbidden
np.random.seed = forbidden
opt.least_squares = forbidden
opt.minimize = forbidden

def load_result(directory):
    directory = Path(directory)
    record = json.loads((directory / "reference.json").read_text())
    with np.load(directory / "reference.npz", allow_pickle=False) as values:
        arrays = {{key: values[key] for key in values.files}}
    return record, arrays

def check_record(record, arrays, fresh=False):
    assert fresh is False
    return {{"passed": record.get("toy_checker_pass", True), "scope": "toy schema wiring only"}}

def module(name):
    assert name == "analytics"
    spec = importlib.util.spec_from_file_location("toy_saved_analytics", {str(HERE / "analytics.py")!r})
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded
"""
    (source / "build_reference.py").write_text(loader)
    monkeypatch.setenv("JOHNHULL_SABR_IDENTIFIABILITY_SOURCE_DIR", str(source))
    # Toy loader guards global APIs; restore them automatically after each test.
    import scipy.optimize

    for name in [
        "default_rng",
        "RandomState",
        "SeedSequence",
        "seed",
        "rand",
        "randn",
        "random",
        "random_sample",
        "normal",
        "standard_normal",
        "uniform",
        "poisson",
        "choice",
        "permutation",
        "shuffle",
    ]:
        monkeypatch.setattr(np.random, name, getattr(np.random, name))
    for name in [
        "least_squares",
        "minimize",
        "differential_evolution",
        "dual_annealing",
        "basinhopping",
    ]:
        monkeypatch.setattr(scipy.optimize, name, getattr(scipy.optimize, name))
    return artifacts, source, record, arrays


def test_notebook_has_stable_ids_and_three_figure_cells(toy, tmp_path):
    artifacts, _, _, _ = toy
    module = builder()
    first = nbformat.read(module.build(artifacts, tmp_path / "a.ipynb"), as_version=4)
    second = nbformat.read(module.build(artifacts, tmp_path / "b.ipynb"), as_version=4)
    assert [c.id for c in first.cells] == [c.id for c in second.cells]
    figures = [c for c in first.cells if c.metadata.get("rbf06_figure")]
    assert len(figures) == 3
    assert first.metadata["rbf06"]["artifact_only"] is True
    text = "\n".join(c.source for c in first.cells)
    assert "pointwise" in text and "unexplored" in text and "not a joint" in text
    assert "fixture" in text and "teaching_acceptance" in text
    for prohibited in ("default_rng(", "least_squares(", "minimize(", "run_study("):
        assert prohibited not in text


def execute_cells(module, artifacts, source, monkeypatch):
    import IPython.display
    import matplotlib.pyplot as plt

    captured = []
    messages = []

    def display(value):
        if isinstance(value, matplotlib.figure.Figure):
            captured.append(value)
        else:
            messages.append(str(getattr(value, "data", value)))

    monkeypatch.setattr(IPython.display, "display", display)
    namespace = {"get_ipython": lambda: type("Dummy", (), {"run_line_magic": lambda *args: None})()}
    with module._environment(artifacts, source):
        for code in (module.LOAD, module.FIGURE_1, module.FIGURE_2, module.FIGURE_3):
            exec(code, namespace)
    plt.close("all")
    return captured, messages, namespace


def test_saved_toy_cells_render_with_rng_and_optimizer_forbidden(
    toy, monkeypatch, tmp_path, capsys
):
    artifacts, source, _, _ = toy
    figures, messages, namespace = execute_cells(builder(), artifacts, source, monkeypatch)
    assert len(figures) == 3
    for i, figure in enumerate(figures):
        path = tmp_path / f"toy-figure-{i}.png"
        figure.savefig(path)
        assert path.stat().st_size > 10_000
    assert namespace["summary"]["cells"][0]["original_noisy_slots"] == 2
    assert namespace["summary"]["cells"][0]["converged_noisy_slots"] == 1
    assert any("unknown" in message for message in messages)
    assert "not a joint" in capsys.readouterr().out


def test_failed_profile_gap_zero_sv_and_unsupported_remain_visible(toy, monkeypatch):
    artifacts, source, _, _ = toy
    figures, _, namespace = execute_cells(builder(), artifacts, source, monkeypatch)
    profile_line = next(
        line for line in figures[0].axes[0].lines if line.get_label() == "profile: nuisance re-fit"
    )
    assert np.isnan(profile_line.get_ydata()[1])
    assert "unsupported" in figures[0].axes[-1].get_title()
    assert any("missing" in text.get_text() for ax in figures[0].axes for text in ax.texts)
    assert any(np.any(np.asarray(line.get_ydata()) == 0) for line in figures[1].axes[0].lines)
    assert namespace["summary"]["per_dataset"][1]["support"]["truth_outcomes"] == ["unknown"] * 3


def test_missing_artifacts_fail_before_notebook_write(tmp_path):
    module = builder()
    destination = tmp_path / "bad.ipynb"
    with pytest.raises(FileNotFoundError):
        module.build(tmp_path, destination)
    assert not destination.exists()


def test_checker_failure_is_not_promoted(toy, tmp_path):
    artifacts, _, record, _ = toy
    record["toy_checker_pass"] = False
    (artifacts / "reference.json").write_text(json.dumps(record))
    destination = tmp_path / "bad.ipynb"
    with pytest.raises(ValueError, match="checker"):
        builder().build(artifacts, destination)
    assert not destination.exists()


def test_pilot_is_not_presented_as_holdout_study(toy, tmp_path):
    artifacts, _, record, _ = toy
    record["phase"] = "pilot"
    (artifacts / "reference.json").write_text(json.dumps(record))
    with pytest.raises(ValueError, match="pilot"):
        builder().build(artifacts, tmp_path / "pilot.ipynb")


def test_environment_override_and_kernel_guard_execution(toy, tmp_path, monkeypatch):
    artifacts, _, _, _ = toy
    monkeypatch.setenv("JOHNHULL_SABR_IDENTIFIABILITY_ARTIFACTS_DIR", str(artifacts))
    output = builder().build(tmp_path / "wrong", tmp_path / "guarded.ipynb", execute=True)
    notebook = nbformat.read(output, as_version=4)
    images = [
        o.data["image/png"]
        for cell in notebook.cells
        if cell.cell_type == "code"
        for o in cell.outputs
        if o.output_type == "display_data" and "image/png" in o.data
    ]
    assert len(images) == 3
    assert not any(
        o.output_type == "error" for c in notebook.cells if c.cell_type == "code" for o in c.outputs
    )


def test_zero_holdout_width_is_a_visible_observation(toy, monkeypatch):
    artifacts, source, _, _ = toy
    figures, _, _ = execute_cells(builder(), artifacts, source, monkeypatch)
    ax = figures[2].axes[3]
    zeros = [line for line in ax.lines if line.get_label() == "zero visited width"]
    assert zeros and len(zeros[0].get_ydata()) == 2
    assert ax.get_ylim()[0] == 0


def test_actual_stability_scalar_schema_displays_saved_step_matrices(toy, monkeypatch):
    artifacts, source, record, arrays = toy
    saved_fit = record["datasets"][0]["fits"][0]
    stability = saved_fit["numerical_stability"]
    assert isinstance(stability["relative_matrix_change"], float)
    figures, messages, _ = execute_cells(builder(), artifacts, source, monkeypatch)
    saved_js = arrays[saved_fit["stability_jacobians_key"]]
    middle = saved_js[1]
    expected = np.array(
        [np.linalg.norm(j - middle, 2) / np.linalg.norm(middle, 2) for j in saved_js]
    )
    line = figures[1].axes[1].lines[0]
    assert np.allclose(line.get_ydata(), expected, rtol=1e-12, atol=1e-15)
    assert max(line.get_ydata()) == pytest.approx(stability["relative_matrix_change"])
    assert any("maximum relative change (scalar)" in value for value in messages)


def test_notebook_cells_install_their_own_artifact_guard(toy, monkeypatch):
    artifacts, source, _, _ = toy
    _, _, namespace = execute_cells(builder(), artifacts, source, monkeypatch)
    with pytest.raises(RuntimeError, match="Artifact-only guard"):
        namespace["np"].random.default_rng(1)
    import scipy.optimize

    with pytest.raises(RuntimeError, match="Artifact-only guard"):
        scipy.optimize.least_squares(lambda x: x, [1.0])
