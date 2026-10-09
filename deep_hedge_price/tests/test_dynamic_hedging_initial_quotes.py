"""Financial saved-boundary tests of all 37 initial quote IDs."""

import copy
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


def _module(name):
    path = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging" / name
    if not path.exists():
        raise AssertionError("initial quote checker is not implemented")
    spec = importlib.util.spec_from_file_location("dynamic_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def evidence():
    ref = _module("reference_methods.py")
    parameters = dict(
        spot=100.0, rate=0.03, dividend_yield=0.0, v0=0.04, kappa=2.0, theta=0.04, xi=0.3, rho=-0.7
    )
    groups = [("fit", t, [80.0, 90.0, 100.0, 110.0, 120.0]) for t in [0.25, 0.5, 0.75, 1.0, 1.25]]
    groups += [("holdout", t, [85.0, 95.0, 105.0, 115.0]) for t in [1 / 3, 2 / 3, 1.125]]
    quotes, receipts, truth = [], [], []
    arrays = {}
    for i, (kind, t, strikes) in enumerate(groups):
        upper250 = ref.independent_heston_call(
            strikes, t, parameters, upper=250, return_receipt=True
        )
        upper500 = ref.independent_heston_call(
            strikes, t, parameters, upper=500, return_receipt=True
        )
        receipts.append(dict(time=t, strikes=strikes, upper250=upper250, upper500=upper500))
        truth.extend(upper500["price"])
        quotes.extend(dict(kind=kind, time=t, strike=k) for k in strikes)
        arrays[f"pde.group{i}.log_spots"] = np.log(100.0) + np.array([-0.02, 0.0, 0.02])
        arrays[f"pde.group{i}.values"] = np.tile(upper500["price"][:, None], (1, 3))
    truth = np.array(truth)
    arrays.update(
        truth250=np.concatenate([x["upper250"]["price"] for x in receipts]),
        truth500=truth,
        truth500_error=np.concatenate([x["upper500"]["price_unit_error"] for x in receipts]),
        cf1024_cutoff512=truth.copy(),
        cf2048_cutoff512=truth.copy(),
        cf2048_cutoff1024=truth.copy(),
    )
    arrays["pde.quote_ids"] = np.arange(37)
    arrays["pde.prices"] = truth.copy()
    arrays["pde.errors"] = np.zeros(37)
    metadata = dict(
        parameters=parameters,
        quotes=quotes,
        cf_receipts=receipts,
        stages=[
            dict(
                id="pde",
                field="field",
                original_quote_count=37,
                status="completed",
                failure=None,
                pde_receipts=[
                    dict(time=t, strikes=ks, supported=True, failure=None) for _, t, ks in groups
                ],
            )
        ],
    )
    arrays.update(
        {
            "field.surface.times": np.array([1 / 4096, 0.1, 0.5, 1.25]),
            "field.surface.local_variance": np.full((4, 4), 0.04),
            "field.surface.supported": np.ones((4, 4), dtype=bool),
            "field.surface.wing_boundaries": np.tile([0, 3], (4, 1)),
        }
    )
    return metadata, arrays


def test_initial_quote_boundary_recomputes_raw_probabilities_and_grid_prices(evidence, monkeypatch):
    check = _module("check_initial_quotes.py")
    monkeypatch.setattr(
        np.random,
        "default_rng",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("RNG forbidden")),
    )
    metadata, arrays = evidence
    got = check.check_initial_quotes(metadata, arrays)
    assert got["integrity"] == "pass"
    assert got["original_quote_count"] == 37
    assert got["initial_quote_gate"] == "pass"
    assert got["formal_pilot_qualification"] == "unknown"
    assert got["pde_stages"]["pde"]["max_error"] == pytest.approx(0.0, abs=1e-11)


@pytest.mark.parametrize(
    "target", ["quote_count", "pde_grid", "cf_probability", "reported_errors", "missing_stage"]
)
def test_initial_quote_boundary_rejects_erased_or_changed_original_evidence(evidence, target):
    check = _module("check_initial_quotes.py")
    metadata, arrays = copy.deepcopy(evidence)
    if target == "quote_count":
        metadata["quotes"].pop()
    elif target == "pde_grid":
        arrays["pde.group0.values"][0, 1] += 1.0
    elif target == "cf_probability":
        metadata["cf_receipts"][0]["upper500"]["integration_receipts"][0][0]["value"] += 0.1
    elif target == "missing_stage":
        arrays.pop("pde.prices")
    else:
        arrays["pde.errors"][0] += 0.01
    with pytest.raises(ValueError):
        check.check_initial_quotes(metadata, arrays)


def test_initial_quote_gate_keeps_all_37_when_absolute_accuracy_fails(evidence):
    check = _module("check_initial_quotes.py")
    metadata, arrays = copy.deepcopy(evidence)
    for i in range(8):
        arrays[f"pde.group{i}.values"] += 0.002
    arrays["pde.prices"] += 0.002
    arrays["pde.errors"] += 0.002
    got = check.check_initial_quotes(metadata, arrays)
    assert got["initial_quote_gate"] == "fail"
    assert got["original_quote_count"] == 37
    assert got["pde_stages"]["pde"]["max_error"] == pytest.approx(0.002, abs=1e-10)
    assert got["formal_pilot_qualification"] == "unknown"


def test_chronological_receipts_restore_original_fit_holdout_quote_order(evidence):
    check = _module("check_initial_quotes.py")
    metadata, arrays = copy.deepcopy(evidence)
    stage = metadata["stages"][0]
    receipts = stage["pde_receipts"]
    for i, receipt in enumerate(receipts):
        prefix = f"pde.t{receipt['time']:.17g}"
        arrays[prefix + ".log_spots"] = arrays.pop(f"pde.group{i}.log_spots")
        arrays[prefix + ".values"] = arrays.pop(f"pde.group{i}.values")
    stage["pde_receipts"] = sorted(receipts, key=lambda r: r["time"])
    got = check.check_initial_quotes(metadata, arrays)
    assert got["initial_quote_gate"] == "pass"
    assert got["pde_stages"]["pde"]["original_quote_count"] == 37


def test_duplicate_maturity_receipt_cannot_replace_original_holdout(evidence):
    check = _module("check_initial_quotes.py")
    metadata, arrays = copy.deepcopy(evidence)
    metadata["stages"][0]["pde_receipts"][-1] = copy.deepcopy(
        metadata["stages"][0]["pde_receipts"][0]
    )
    with pytest.raises(ValueError, match=r"roster|duplicate|original|maturity"):
        check.check_initial_quotes(metadata, arrays)


def test_measured_refinement_is_recomputed_from_both_original_price_vectors(evidence):
    check = _module("check_initial_quotes.py")
    metadata, original = copy.deepcopy(evidence)
    stage = metadata["stages"][0]
    arrays = {k.replace("pde.", "pde1201x960."): v.copy() for k, v in original.items()}
    stage["id"] = "pde1201x960"
    refined = copy.deepcopy(stage)
    refined["id"] = "pde2401x1920"
    metadata["stages"].append(refined)
    for key, value in list(arrays.items()):
        if key.startswith("pde1201x960."):
            arrays[key.replace("pde1201x960.", "pde2401x1920.")] = value.copy()
    arrays["pde2401x1920.refinement"] = np.zeros(37)
    got = check.check_initial_quotes(metadata, arrays)
    assert got["refinements"]["pde2401x1920"]["max_difference"] == pytest.approx(0.0)
    arrays["pde2401x1920.refinement"][0] = 1.0
    with pytest.raises(ValueError, match="refinement"):
        check.check_initial_quotes(metadata, arrays)


def test_a_surviving_candidate_cannot_hide_an_erased_original_attempt(evidence):
    check = _module("check_initial_quotes.py")
    metadata, arrays = copy.deepcopy(evidence)
    second = copy.deepcopy(metadata["stages"][0])
    second["id"] = "surviving"
    metadata["stages"].append(second)
    for key, value in list(arrays.items()):
        if key.startswith("pde."):
            arrays[key.replace("pde.", "surviving.")] = value.copy()
    arrays.pop("pde.prices")
    with pytest.raises(ValueError, match=r"original|missing"):
        check.check_initial_quotes(metadata, arrays)
