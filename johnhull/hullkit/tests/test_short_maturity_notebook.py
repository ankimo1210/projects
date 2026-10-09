"""Real guarded notebook execution on explicitly toy saved study evidence."""

import importlib.util
import json
import sys
from pathlib import Path

import nbformat
import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[2] / "research/RB-F05/short_maturity"


def builder():
    spec = importlib.util.spec_from_file_location(
        "short_notebook_tests", HERE / "build_notebook.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    directory = tmp_path_factory.mktemp("short_notebook")
    source = directory / "source"
    source.mkdir()
    artifacts = directory / "saved"
    artifacts.mkdir()
    arrays = {}

    def put(key, value):
        arrays[key] = np.asarray(value)
        return key

    p = {
        "contract": {"strike": 100.0, "synthetic": True},
        "pilot": {"minimum_active_count": 100, "max_price_se": 0.002, "max_delta_se": 0.0005},
        "accuracy": {
            "price_abs": 0.01,
            "delta_abs": 0.005,
            "scaled_gamma_abs": 0.05,
            "scaled_gamma_relative": 0.05,
        },
    }
    tx = np.array(
        [
            [98, 60, 0],
            [100, 60, 0],
            [102, 60, 0],
            [98, 1800, 1],
            [100, 1800, 1],
            [102, 1800, 1],
            [100, 23400, 0],
            [102, 23400, 1],
        ],
        float,
    )
    truth = np.array(
        [
            [0.01, 0.03, 0.01],
            [0.1, 0.5, 0.7],
            [2.0, 0.98, 0.02],
            [0.15, 0.2, 0.1],
            [0.3, 0.6, 0.2],
            [2.1, 0.9, 0.04],
            [0.6, 0.5, 0.1],
            [2.5, 0.8, 0.08],
        ]
    )
    datasets = {}
    for split, n in [("train", 3), ("validation", 1), ("test", 8)]:
        x, y = tx[:n], truth[:n]
        dataset = {
            "original_count": n,
            "inputs_key": put(split + "/inputs", x),
            "oracle_key": put(split + "/oracle", y),
            "teachers": [],
        }
        if split != "test":
            labels = y + np.array([0.001, 0.0001, 0.00001])
            dataset["labels_key"] = put(split + "/labels", labels)
            for i in range(n):
                teacher = {
                    "keys": {
                        "mean": put(f"{split}/mean{i}", labels[i]),
                        "se": put(
                            f"{split}/se{i}",
                            [0.0, 0.0, 0.0] if i == 0 else [0.002, 0.0004, 0.00001],
                        ),
                    },
                    "active_count": 0 if i < 2 else 101,
                    "count": 0 if i == 0 else 512,
                    "reserved_sample_count": 512,
                    "actual_random_draws": 0 if i == 0 else 512 + (0 if i == 1 else 101),
                    "status": "analytic_deterministic"
                    if i == 0
                    else "rare_event_unobserved"
                    if i == 1
                    else "ready",
                    "precision_ready": i != 1,
                    "reason": "rare_event_unobserved" if i == 1 else None,
                }
                dataset["teachers"].append(teacher)
        else:
            dataset["independent_key"] = put("test/independent", truth.copy())
        datasets[split] = dataset
    diag = np.array([[100, 0, 0], [99, 0, 0], [101, 0, 1], [100, -1, 0]], float)
    reference = np.array([[0, np.nan, np.nan], [0, 0, 0], [1, 1, 0], [np.nan, np.nan, np.nan]])
    fits = []
    for i in range(6):
        raw = truth + np.array([0.001 * (i + 1), 0.0001 * (i + 1), 0.00001 * (i + 1)])
        if i == 5:
            raw[-1] = np.nan
        fid = f"fit{i}"
        fits.append(
            {
                "id": fid,
                "pair_id": i // 2,
                "dml": bool(i % 2),
                "stats": {
                    "seed": [11, 29, 47][i // 2],
                    "status": "time_cap" if i == 5 else "completed",
                    "complete": i != 5,
                    "updates": 4 if i == 5 else 8,
                    "requested_updates": 8,
                    "batch_attempts": 5 if i == 5 else 8,
                    "reason": "toy_time_cap" if i == 5 else None,
                    "training_s": 0.01 * (i + 1),
                    "overrun_s": 0.01 if i == 5 else 0.0,
                },
                "predictions": {
                    "test": {
                        "raw_key": put(fid + "/raw", raw),
                        "safe_key": put(fid + "/safe", np.nan_to_num(raw)),
                        "original_count": 8,
                    }
                },
                "diagnostics": {
                    "raw_key": put(fid + "/diag_raw", np.full((4, 3), np.nan)),
                    "safe_key": put(fid + "/diag_safe", reference),
                    "routes_key": put(
                        fid + "/routes",
                        [
                            "expiry_undefined_atm",
                            "expiry_exact",
                            "expiry_exact",
                            "invalid_contract",
                        ],
                    ),
                    "original_count": 4,
                },
            }
        )
    methods = ["core_mixture", "hermite", *[f"fit{i}/raw" for i in range(6)]]
    timing = [
        {
            "method": method,
            "batch_size": 1,
            "minutes": 1,
            "event": 0,
            "seconds_key": put(f"timing{i}", [1e-5 * (i + 1), 1.1e-5 * (i + 1)]),
        }
        for i, method in enumerate(methods)
    ]
    expenses = [
        {"id": "teacher", "category": "teacher_train", "seconds": 0.3, "charged": True},
        {"id": "fit", "category": "fit", "seconds": 0.21, "charged": True},
        *[
            {"id": k, "category": k, "seconds": None, "charged": True}
            for k in ["serialization", "cold_import", "pilot_freeze", "fresh"]
        ],
    ]
    record = {
        "schema": "RB-F05-short-study-v1",
        "mode": "smoke",
        "phase": "pilot",
        "fixture": True,
        "accepted": False,
        "teaching_acceptance": False,
        "complete": True,
        "protocol": p,
        "datasets": datasets,
        "fits": fits,
        "timing": timing,
        "expenses": expenses,
        "hermite": {
            "predictions": {
                "test": put("hermite/test", truth + np.array([0.0001, 0.00001, 0.000001]))
            }
        },
        "diagnostics": {
            "inputs_key": put("diagnostic/inputs", diag),
            "reference_key": put("diagnostic/reference", reference),
            "original_count": 4,
        },
        "costs": {"main_only_s": 0.51, "cold_pipeline_s": None, "fresh_s": None},
        "analytics_path": str(HERE / "analytics.py"),
    }
    (artifacts / "reference.json").write_text(json.dumps(record))
    np.savez_compressed(artifacts / "reference.npz", **arrays)
    loader = r"""import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
def load_result(directory):
    directory=Path(directory)
    record=json.loads((directory/"reference.json").read_text())
    with np.load(directory/"reference.npz",allow_pickle=False) as b:
        arrays={k:b[k].copy() for k in b.files}
    return record,arrays
def module(name):
    if name!="analytics":
        raise KeyError(name)
    record,_=load_result(Path(__file__).parent.parent/"saved")
    spec=importlib.util.spec_from_file_location("toy_short_analytics",record["analytics_path"])
    value=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=value
    spec.loader.exec_module(value)
    return value
def check_record(record,arrays):
    assert record["fixture"] and len(record["fits"])==6
    assert arrays[record["datasets"]["test"]["inputs_key"]].shape==(8,3)
    # The notebook must install guards before entering even a fixture checker.
    import scipy.optimize
    import urllib.request
    import torch
    from deep_hedge_price import _short_maturity_dml
    blocked=0
    callbacks=[lambda:np.random.default_rng(1),lambda:np.random.normal(size=1),
               lambda:scipy.optimize.minimize(lambda x: x*x,1.),
               lambda:torch.manual_seed(1),lambda:_short_maturity_dml.train(),
               lambda:torch.optim.Adam.step(None),
               lambda:urllib.request.urlopen("https://invalid.example")]
    for callback in callbacks:
        try:
            callback()
        except RuntimeError as exc:
            assert "Artifact-only" in str(exc)
            blocked+=1
    assert blocked==len(callbacks)
    # Deterministic reserved-ledger seed provenance is not a sample draw.
    assert np.random.SeedSequence(123).generate_state(1).shape==(1,)
    return {"passed":True,"accepted":False,"scope":"toy fixture numerical/display wiring only"}
def run_study(*args,**kwargs):
    raise AssertionError("study generation must not run")
"""
    (source / "build_reference.py").write_text(loader)
    return artifacts, source, directory


def test_builder_witnessed_red_has_deterministic_cell_ids_and_saved_scope(toy):
    artifacts, source, directory = toy
    m = builder()
    first = m.build(artifacts, directory / "one.ipynb", source=source)
    second = m.build(artifacts, directory / "two.ipynb", source=source)
    a, b = nbformat.read(first, as_version=4), nbformat.read(second, as_version=4)
    assert [c.id for c in a.cells] == [c.id for c in b.cells]
    assert len({c.id for c in a.cells}) == len(a.cells)
    assert a.metadata["rbf05_short"]["artifact_only"]
    assert a.metadata["rbf05_short"]["figures"] == 3
    joined = "\n".join(c.source for c in a.cells)
    assert "nbplot.setup" in joined and "loader.check_record(record, arrays)" in joined
    assert "unknown" in joined and "raw" in joined and "cold" in joined


@pytest.fixture(scope="module")
def executed(toy):
    artifacts, source, directory = toy
    m = builder()
    path = m.build(artifacts, directory / "executed.ipynb", source=source, execute=True)
    return path, nbformat.read(path, as_version=4)


def test_real_nbclient_guarded_fixture_retains_three_pngs_and_original_failures(executed):
    _, notebook = executed
    pngs = [
        out["data"]["image/png"]
        for cell in notebook.cells
        for out in cell.get("outputs", [])
        if "image/png" in out.get("data", {})
    ]
    assert len(pngs) == 3
    assert all(len(png) > 10000 for png in pngs)
    text = "\n".join(
        out.get("text", "") + out.get("data", {}).get("text/markdown", "")
        for cell in notebook.cells
        for out in cell.get("outputs", [])
    )
    for word in [
        "smoke",
        "fixture",
        "time_cap",
        "toy_time_cap",
        "rare_event_unobserved",
        "expiry_undefined_atm",
        "cold_import",
        "unknown",
        "fit5",
    ]:
        assert word in text
    assert "original test rows: 8" in text
    assert "original fit slots: 6" in text
    assert "ordinary Greeks: unknown" in text
    assert not any(o.output_type == "error" for c in notebook.cells for o in c.get("outputs", []))


def test_notebook_does_not_require_accepted_or_successful_fits(toy):
    artifacts, source, directory = toy
    output = builder().build(artifacts, directory / "failed_kept.ipynb", source=source)
    notebook = nbformat.read(output, as_version=4)
    assert any("independent" in c.source and "acceptance" in c.source for c in notebook.cells)


def test_missing_saved_evidence_fails_before_creating_a_notebook(tmp_path):
    output = tmp_path / "missing.ipynb"
    with pytest.raises(FileNotFoundError):
        builder().build(tmp_path / "absent", output)
    assert not output.exists()
