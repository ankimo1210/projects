"""Pinned upstream Heston DSINC/FD code: provenance, input mapping and observed branches."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2] / "research/DSINC"
H00 = {
    "case_id": "H00",
    "S": 100.0,
    "K": 100.0,
    "T": 0.25,
    "rd": 0.03,
    "rf": 0.025,
    "theta": 0.6,
    "xi": 0.8,
    "rho": -0.4,
    "v0": 0.5,
    "kappa": 0.5,
}
TINY_FD = {"N": 20, "m1": 40}
FD_PARAMS = {
    "K": 100.0,
    "T2": 0.25,
    "rd": 0.03,
    "rf": 0.025,
    "theta": 0.6,
    "xi": 0.8,
    "rho": -0.4,
    "kappa": 0.5,
} | TINY_FD


@pytest.fixture(scope="module")
def baseline():
    spec = importlib.util.spec_from_file_location(
        "dsinc_heston_baseline_tests", ROOT / "heston_baseline.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def dsinc_params(**settings):
    keys = ("S", "K", "T", "rd", "rf", "theta", "rho", "v0", "kappa")
    return {k: H00[k] for k in keys} | {"sigma": H00["xi"]} | settings


def test_manifest_pins_the_four_upstream_files():
    manifest = json.loads((ROOT / "upstream_manifest.json").read_text())
    assert manifest["commit"] == "20cfb802673b0a792984d25e1f45cd09d37e8c07"
    expected = {
        "dsinc_pricer.py": (
            "7ce004ae819252e98cc287c06acc74be6ee57216d2ab09aac8b49f1f66fae927",
            15973,
        ),
        "fd_adi_pricer.py": (
            "535d8da63827be1eb977312042e52204d2cf863a57219b1217bdd534fbf8b12c",
            18243,
        ),
        "benchmark.py": ("35eba4f34f2690091518e2e3e801d317d54f8ee1ec5e155e0e8334d1ebd89a35", 3294),
        "LICENSE": ("028d0ca606b35b691ec82fda12fae43370bee49548a37f3f8b97ce15dbb7202b", 1075),
    }
    for name, (sha, size) in expected.items():
        data = (ROOT / "upstream" / name).read_bytes()
        assert (hashlib.sha256(data).hexdigest(), len(data)) == (sha, size)
        assert (manifest["files"][name]["sha256"], manifest["files"][name]["bytes"]) == (sha, size)
    assert "Copyright (c) 2026 <COPYRIGHT HOLDER>" in (ROOT / "upstream/LICENSE").read_text()


def test_load_upstream_rejects_modified_bytes_and_benchmark(baseline, tmp_path, monkeypatch):
    for name in ("dsinc_pricer.py", "fd_adi_pricer.py"):
        (tmp_path / name).write_bytes((ROOT / "upstream" / name).read_bytes())
    (tmp_path / "dsinc_pricer.py").write_bytes((tmp_path / "dsinc_pricer.py").read_bytes() + b"\n")
    monkeypatch.setattr(baseline, "UPSTREAM_DIR", tmp_path)
    with pytest.raises(ValueError, match="sha256"):
        baseline.load_upstream("dsinc_pricer")
    with pytest.raises(ValueError, match="benchmark"):
        baseline.load_upstream("benchmark")


def test_load_upstream_leaves_sys_path_alone(baseline):
    before = list(sys.path)
    baseline.load_upstream("fd_adi_pricer")
    assert sys.path == before


def test_one_normalized_input_reaches_both_solvers(baseline):
    out = baseline.run_heston_baseline(
        H00, dsinc_settings={"Nv": 6, "Nt": 8, "Nom": 600}, fd_settings=TINY_FD
    )
    d, f = out["dsinc"]["parameters"], out["fd"]["parameters"]
    assert (d["sigma"], d["kappa"], d["T"], d["v0"]) == (0.8, 0.5, 0.25, 0.5)
    assert (f["xi"], f["kappa"], f["T2"]) == (0.8, 0.5, 0.25) and "v0" not in f
    assert out["dsinc"]["settings"]["chi"] == -1.0
    assert (out["fd"]["settings"]["policy"], out["fd"]["docstring_policy_default"]) == (1, 0)
    assert out["certified"] is False


def test_observed_classes_return_the_upstream_values(baseline):
    dsinc, fd = baseline.load_upstream("dsinc_pricer"), baseline.load_upstream("fd_adi_pricer")
    observed_dsinc, observed_fd = baseline.observed_classes()
    plain, seen = (
        dsinc.DSINCPut(dsinc_params(Nv=6, Nt=8, Nom=600)),
        observed_dsinc(dsinc_params(Nv=6, Nt=8, Nom=600)),
    )
    assert plain.price() == seen.price()
    np.testing.assert_array_equal(plain.xstar, seen.xstar)
    a, b = fd.HestonFDSolver(FD_PARAMS), observed_fd(FD_PARAMS)
    assert [a.price(100.0, 0.5, k) for k in (0, 1)] == [b.price(100.0, 0.5, k) for k in (0, 1)]


def test_upstream_eep_floor_is_observed_and_not_certified(baseline):
    low = baseline.run_heston_baseline(
        H00, dsinc_settings={"Nv": 6, "Nt": 8, "Nom": 120}, fd_settings=TINY_FD
    )
    assert low["dsinc"]["final"]["eep_raw"] == pytest.approx(-0.0778381085, abs=1e-9)
    assert low["dsinc"]["eep"] == 0.0 and low["dsinc"]["american"] == low["dsinc"]["european"]
    assert "eep_floor" in low["dsinc"]["post_processing"]
    ok = baseline.run_heston_baseline(
        H00, dsinc_settings={"Nv": 6, "Nt": 8, "Nom": 600}, fd_settings=TINY_FD
    )
    assert ok["dsinc"]["final"]["eep_raw"] == pytest.approx(0.0255717953, abs=1e-9)
    assert "eep_floor" not in ok["dsinc"]["post_processing"]


@pytest.mark.parametrize(
    "residual, x0, path, expected",
    [
        (lambda x: 0.0, -0.2, "exact_zero", -0.2),
        (lambda x: -(x + 0.1), -0.09, "local_bracket", -0.1),
        (lambda x: 1.0 if -6.0 <= x <= -5.9 else -1.0, 0.0, "wide_scan", -6.0),
        (lambda x: (x + 3.0) ** 2 + 1e-3, 0.0, "min_residual", -2.9525),
    ],
)
def test_boundary_paths_are_classified(baseline, residual, x0, path, expected):
    dsinc = baseline.load_upstream("dsinc_pricer")
    observed, _ = baseline.observed_classes()
    plain, seen = (
        dsinc.DSINCPut(dsinc_params(Nv=6, Nt=8, Nom=120)),
        observed(dsinc_params(Nv=6, Nt=8, Nom=120)),
    )
    value = seen._solve_boundary(residual, x0)
    assert value == plain._solve_boundary(residual, x0) and value == pytest.approx(
        expected, abs=1e-4
    )
    assert seen.counts[path] == 1


def test_clip_and_safe_nan_are_counted(baseline):
    observed, _ = baseline.observed_classes()
    seen = observed(dsinc_params(Nv=6, Nt=8, Nom=120))
    assert seen._solve_boundary(lambda x: -(x + 0.1), 1.0) == pytest.approx(-0.1)
    assert seen.counts["clip_high"] == 1

    def fragile(x):
        if x < -0.095:
            raise ValueError("outside")
        return -(x + 0.1)

    assert seen._solve_boundary(fragile, -0.09) == pytest.approx(
        0.02
    )  # every scan point but the last raises
    assert seen.counts["safe_nan"] >= 1 and seen.counts["min_residual"] == 1


def test_cf_replacement_and_european_floor_are_counted(baseline):
    dsinc = baseline.load_upstream("dsinc_pricer")
    observed, _ = baseline.observed_classes()
    plain, seen = (
        dsinc.DSINCPut(dsinc_params(Nv=6, Nt=8, Nom=120)),
        observed(dsinc_params(Nv=6, Nt=8, Nom=120)),
    )
    u = np.array([0.5, np.inf])
    with np.errstate(all="ignore"):
        np.testing.assert_array_equal(seen._heston_cf(u, 0.25, 0.5), plain._heston_cf(u, 0.25, 0.5))
    assert seen.counts["cf_nonfinite"] == 1
    coeffs = (0.0, np.array([0.0]), np.array([-1.0 + 0.0j]), 100.0)
    assert seen._european_value(0.0, coeffs) == plain._european_value(0.0, coeffs) == 0.0
    assert seen.counts["european_floor"] == 1 and seen.extremes[
        "european_min_raw"
    ] == pytest.approx(-100.0)


def test_price_floor_is_recorded(baseline, monkeypatch):
    observed, _ = baseline.observed_classes()
    put = observed(dsinc_params(Nv=6, Nt=8, Nom=120) | {"S": 50.0})
    monkeypatch.setattr(put, "_backward_solve", lambda: 0.0)
    monkeypatch.setattr(put, "_european_value", lambda x, coeffs: 40.0)
    assert put.price() == (40.0, 50.0, 0.0)
    assert put.final["american_raw"] == 40.0 and "american_floor" in put.post_processing


def test_penalty_stop_reasons_are_counted(baseline):
    _, observed_fd = baseline.observed_classes()
    solver = observed_fd(FD_PARAMS | {"pp_maxiter": 1})
    solver.price(100.0, 0.5, 1)
    assert (
        sum(solver.policy_stop_reasons.values()) == 20
        and solver.policy_stop_reasons["maxiter"] >= 1
    )
    assert solver.policy_solves == 20


def test_cases_transcribe_the_paper_and_upstream_tables():
    cases = json.loads((ROOT / "cases.json").read_text())
    paper = cases["three_halves_paper"]
    assert paper["T0.5"] == {
        "american_n100": [0.107601, 0.048662, 0.019499],
        "european": [0.102557, 0.047224, 0.019105],
        "eep": [0.005044, 0.001438, 0.000394],
        "american_n200": [0.107599, 0.048660, 0.019497],
        "fd_coarse": [0.107575, 0.048618, 0.019469],
        "fd_fine": [0.107593, 0.048648, 0.019490],
    }
    assert paper["T1"] == {
        "american_atm": 0.063668,
        "fd_fine_atm": 0.063658,
        "non_atm": "not_available",
    }
    assert paper["roles"]["gate"] == ["T0.5.american_n100", "T0.5.european", "T1.american_atm"]
    heston = cases["heston_upstream"]["cases"]
    assert heston[0] == H00 | {
        "reference": {
            "ie_european": 13.6633,
            "ie_american": 13.6749,
            "fd_european": 13.6611,
            "fd_american": 13.6837,
        }
    }
    assert [c["reference"]["american"] for c in heston[1:]] == [
        2.0000,
        1.1076,
        0.5199,
        0.2135,
        0.0820,
        2.0785,
        1.3336,
        0.7959,
        0.4482,
        0.2427,
    ]


def test_out_of_scope_rates_are_rejected(baseline):
    with pytest.raises(ValueError):
        baseline.run_heston_baseline(
            H00 | {"rd": 0.025, "rf": 0.05},
            dsinc_settings={"Nv": 6, "Nt": 8, "Nom": 120},
            fd_settings=TINY_FD,
        )
