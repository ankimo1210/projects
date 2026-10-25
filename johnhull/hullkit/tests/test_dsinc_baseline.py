"""DSINC research input and upstream-observer contracts, independent of acceptance."""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "research" / "DSINC"


def _types():
    assert importlib.util.find_spec("hullkit._dsinc_types") is not None, "missing DSINC input types"
    return importlib.import_module("hullkit._dsinc_types")


def _baseline():
    path = RESEARCH / "heston_baseline.py"
    assert path.is_file(), "missing audited upstream adapter"
    spec = importlib.util.spec_from_file_location("dsinc_heston_baseline", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _paper_inputs():
    t = _types()
    return (
        t.PutContract(100, 0.25, 0.03, 0.025),
        t.VarianceModel("heston", 0.5, 0.6, 0.8, -0.4, 0.5),
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("strike", 0),
        ("expiry", -1),
        ("expiry", np.nan),
        ("domestic_rate", 0.01),
        ("foreign_rate", -0.01),
    ],
)
def test_contract_rejects_unsupported_or_nonfinite_input(field, value):
    t = _types()
    kwargs = dict(strike=1, expiry=0.5, domestic_rate=0.05, foreign_rate=0.02)
    kwargs[field] = value
    with pytest.raises(ValueError):
        t.PutContract(**kwargs)


def test_model_rejects_invalid_kind_moments_and_correlation():
    t = _types()
    for args in [
        ("sabr", 20, 0.04, 4, -0.5, 0.04),
        ("three_halves", 0.2, 0.04, 1, 0.9, 0.04),
        ("heston", 2, 0.04, 0.2, 1, 0.04),
        ("heston", 2, 0.04, 0, -0.5, 0.04),
    ]:
        with pytest.raises(ValueError):
            t.VarianceModel(*args)


def test_frozen_input_cannot_change_the_next_pricing_call():
    from dataclasses import FrozenInstanceError

    contract, model = _paper_inputs()
    with pytest.raises(FrozenInstanceError):
        contract.domestic_rate = 0.99
    with pytest.raises(FrozenInstanceError):
        model.kappa = 2


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chi": 0},
        {"chi": 1},
        {"n_time": 0},
        {"n_var": 2},
        {"panels": (0, 2, 1)},
        {"log_var_bounds": (1, 0)},
        {"root_max_width": 0.01},
    ],
)
def test_spectral_config_rejects_invalid_grid(kwargs):
    t = _types()
    values = dict(
        n_time=100,
        n_var=160,
        log_var_bounds=(-8, 1),
        chi=0.5,
        panels=(0, 2, 5),
        points_per_panel=12,
    )
    values.update(kwargs)
    with pytest.raises(ValueError):
        t.SpectralConfig(**values)


def test_source_hash_mismatch(tmp_path):
    baseline = _baseline()
    baseline.verify_upstream()
    import shutil

    copied = tmp_path / "upstream"
    shutil.copytree(RESEARCH / "upstream", copied)
    with (copied / "dsinc_pricer.py").open("a") as stream:
        stream.write("\n# altered\n")
    with pytest.raises(ValueError, match="hash"):
        baseline.verify_upstream(copied)


def test_baseline_parameter_mapping_and_raw_observer_match():
    baseline = _baseline()
    contract, model = _paper_inputs()
    ds = dict(Nv=6, Nt=6, Nom=64, om_max=100)
    fd = dict(N=8, m1=20)
    report = baseline.run_heston_baseline(
        contract, model, np.array([100.0]), dsinc_settings=ds, fd_settings=fd
    )
    row = report["spots"][0]
    assert row["dsinc"]["settings"]["kappa"] == 0.5
    assert row["fd"]["settings"]["kappa"] == 0.5
    assert row["dsinc"]["settings"]["sigma"] == 0.8
    assert row["fd"]["settings"]["xi"] == 0.8
    raw_ds, raw_fd = baseline.upstream_classes()
    original = raw_ds(
        dict(
            S=100,
            K=100,
            T=0.25,
            rd=0.03,
            rf=0.025,
            theta=0.6,
            sigma=0.8,
            rho=-0.4,
            v0=0.5,
            kappa=0.5,
            **ds,
        )
    ).price()
    np.testing.assert_allclose(row["dsinc"]["values"], original, atol=1e-12, rtol=0)
    original_fd = raw_fd(
        dict(K=100, T2=0.25, rd=0.03, rf=0.025, theta=0.6, xi=0.8, rho=-0.4, kappa=0.5, **fd)
    )
    np.testing.assert_allclose(
        row["fd"]["values"],
        [original_fd.price(100, 0.5, 0), original_fd.price(100, 0.5, 1)],
        atol=1e-12,
        rtol=0,
    )
    assert report["accepted"] is False
    assert report["timings"]["total_seconds"] >= row["dsinc"]["timings"]["setup_seconds"]
    json.dumps(report, allow_nan=False)


def test_settings_cannot_override_the_contract_or_model():
    baseline = _baseline()
    contract, model = _paper_inputs()
    with pytest.raises(ValueError):
        baseline.run_heston_baseline(
            contract, model, np.array([100.0]), dsinc_settings={"kappa": 2}, fd_settings={}
        )
    with pytest.raises(ValueError):
        baseline.run_heston_baseline(
            contract, model, np.array([100.0]), dsinc_settings={"unknown": 2}, fd_settings={}
        )


@pytest.mark.parametrize(
    "ds,fd",
    [
        ({"Nt": 1}, {}),
        ({"Nv": 1}, {}),
        ({"om_max": -1}, {}),
        ({"mode": "typo"}, {}),
        ({}, {"N": 0}),
        ({}, {"pp_maxiter": 0}),
        ({}, {"policy": 2}),
        ({}, {"Vmax": 0.1}),
    ],
)
def test_numerical_controls_cannot_silently_disable_the_solver(ds, fd):
    baseline = _baseline()
    contract, model = _paper_inputs()
    with pytest.raises(ValueError):
        baseline.run_heston_baseline(
            contract, model, np.array([100.0]), dsinc_settings=ds, fd_settings=fd
        )


def test_maturity_preserves_spot_order_and_exact_payoff():
    baseline = _baseline()
    t = _types()
    _, model = _paper_inputs()
    report = baseline.run_heston_baseline(
        t.PutContract(100, 0, 0.03, 0.025),
        model,
        np.array([120.0, 80.0, 100.0]),
        dsinc_settings={},
        fd_settings={},
    )
    assert [row["dsinc"]["values"] for row in report["spots"]] == [
        [0.0, 0.0, 0.0],
        [20.0, 20.0, 0.0],
        [0.0, 0.0, 0.0],
    ]


def _root_observer():
    observed, _ = _baseline().audited_classes()
    obj = observed.__new__(observed)
    obj.audit = []
    obj.phase_seconds = {}
    return obj


def test_upstream_fallback_is_not_certified():
    observer = _root_observer()
    observer._solve_boundary(lambda x: 1.0, -0.03)
    assert observer.audit[-1]["branch"] == "min_residual"
    assert observer.audit[-1]["success"] is False
    observer._solve_boundary(lambda x: np.nan, -0.03)
    assert observer.audit[-1]["finite_samples"] == 0


def test_upstream_raw_values_and_root_branches():
    observer = _root_observer()
    assert observer._solve_boundary(lambda x: x + 1, -0.9) == pytest.approx(-1)
    assert observer.audit[-1]["branch"] == "local_brentq"
    assert observer._solve_boundary(
        lambda x: x + 2 if abs(x + 2) < 0.5 else np.nan, -0.03
    ) == pytest.approx(-2)
    assert observer.audit[-1]["branch"] == "wide_scan"
    observer._solve_boundary(lambda x: x + 1, 100)
    assert any(event["code"] == "predictor_clip" for event in observer.audit)
    assert observer._european_value(0, (0, np.array([0.0]), np.array([-1.0 + 0j]), 1)) == 0
    assert observer.audit[-1]["raw"] == -1
    observer.kappa, observer.theta, observer.sigma, observer.rho = 0.5, 0.6, 0.8, -0.4
    observer.rd, observer.rf = 0.03, 0.025
    with np.errstate(all="ignore"):
        observer._heston_cf(np.array([complex(np.nan)]), 0.25, 0.5)
    assert observer.audit[-1]["code"] == "cf_nonfinite_replaced"


def test_upstream_negative_eep_and_intrinsic_floors_are_visible():
    observer = _root_observer()
    observer.Nt, observer.K, observer.M = 2, 1.0, 1
    observer.wc, observer.wq = np.array([0j]), np.array([1.0])
    observer.tt, observer.v0, observer.x0 = np.array([0.0, 1.0]), 0.04, 0.0
    observer.rd = observer.rf = observer.mu1 = observer.kappa = observer.rtx = 0.0
    observer.partial = False
    zero, one = np.zeros((1, 1)), np.ones((1, 1))
    observer._segcoef = lambda boundary, lag: (zero, zero, zero, zero, zero, one)
    assert observer._final_eep(np.zeros((2, 2))) == 0
    assert observer.audit[-1]["raw"] == pytest.approx(-1 / (4 * np.pi))
    observer.S, observer.T = 0.1, 1.0
    observer._backward_solve = lambda: -0.2
    observer._european_coeffs = lambda v, tau: None
    observer._european_value = lambda x, coeffs: 0.1
    assert observer.price()[1] == pytest.approx(0.9)
    assert observer.audit[-1]["code"] == "american_intrinsic_floor"
    assert observer.audit[-1]["raw"] == pytest.approx(-0.1)


def test_upstream_penalty_iteration_limit_is_visible():
    import scipy.sparse as sp

    _, observed = _baseline().audited_classes()
    observer = observed.__new__(observed)
    observer.audit = []
    observer.dt, observer.theta_mcs, observer.rho_AM = 1.0, 1.0, 10.0
    observer.mi, observer.mj, observer.pp_maxiter, observer.pp_tol = 1, 2, 1, 1e-9
    observer.Ibig, observer.A2, observer.phi = (
        sp.eye(2, format="csc"),
        sp.csc_matrix((2, 2)),
        np.ones(2),
    )
    observer._policy_iteration(np.zeros(2), np.array([0.5, -0.5]), np.zeros(2))
    assert observer.audit[-1]["code"] == "penalty_iteration"
    assert observer.audit[-1]["converged"] is False
    assert observer.audit[-1]["iterations"] == 1
