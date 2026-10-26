"""DSINC decision rules: reference construction, level selection, boundary, bounds and paper gates."""

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[2] / "research/DSINC/gates.py"
REF = {
    "reference_final_change": 5e-6,
    "reference_resolution": 5e-7,
    "reference_order_range": [1.0, 3.0],
}
TH = {"adjacent": 5e-6, "independent": 2e-5, "sensitivity": 5e-6}
BOUNDARY = {
    "time_window": [0.1, 0.9],
    "variance_window": [0.01, 0.16],
    "edge_cells": 4,
    "coverage": 0.9,
    "max_cells": 2.0,
    "fd_shift_cells": 1.0,
    "root_residual": 1e-8,
}
SENSITIVITIES = (
    "crossing_lower",
    "time_x2",
    "time_x2_cutoff_x2",
    "var_next",
    "points_plus4",
    "cutoff_x2",
    "chi_0.25",
    "chi_0.75",
    "domain_expand",
    "offset_plus_half",
    "offset_minus_half",
)
# planning-run American prices at T = .5 on the wide variance domain (rows: levels, columns: S/K .9, 1, 1.1)
X = np.array(
    [
        [0.10757684, 0.04861780, 0.01946888],
        [0.10759692, 0.04864835, 0.01948780],
        [0.10760209, 0.04865596, 0.01949251],
        [0.10760299, 0.04865785, 0.01949368],
    ]
)
VAR = np.array(
    [
        [0.10757684, 0.04861780, 0.01946888],
        [0.10757491, 0.04861748, 0.01946949],
        [0.10757471, 0.04861744, 0.01946973],
    ]
)
TIME = np.array(
    [
        [0.10757684, 0.04861780, 0.01946888],
        [0.10757601, 0.04861829, 0.01946962],
        [0.10757582, 0.04861849, 0.01946989],
    ]
)


@pytest.fixture(scope="module")
def gates():
    spec = importlib.util.spec_from_file_location("dsinc_gates_tests", PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def level(value):
    return {q: np.full(3, value) for q in ("european", "american", "eep")}


def test_order_is_fitted_on_actual_step_sizes(gates):
    for h in (np.array([0.02, 0.01, 0.005]), 1.0 / np.array([100.0, 150.0, 200.0])):
        assert gates.order_from_levels(h, 1.0 + 3.0 * h**2) == pytest.approx(2.0, abs=1e-9)
    assert (
        gates.order_from_levels(np.array([0.02, 0.01, 0.005]), np.array([1.0, 1.0 + 1e-6, 1.0]))
        is None
    )


def test_axis_convergence_on_the_planning_ladders(gates):
    x = gates.axis_convergence(1.0 / np.array([240.0, 480.0, 960.0, 1920.0]), X, REF)
    assert x["status"] == "converged" and x["final_change"] == pytest.approx(1.89e-6, abs=1e-12)
    assert x["orders"] == pytest.approx([2.522, 2.010, 2.009], abs=2e-3)
    assert (
        gates.axis_convergence(1.0 / np.array([100.0, 150.0, 200.0]), VAR, REF)["status"]
        == "below_resolution"
    )
    assert (
        gates.axis_convergence(1.0 / np.array([300.0, 600.0, 1200.0]), TIME, REF)["status"]
        == "below_resolution"
    )
    three = gates.axis_convergence(1.0 / np.array([240.0, 480.0, 960.0]), X[:3], REF)
    assert three["status"] == "final_change_too_large"  # D-2: stopping at 961 fails the 5e-6 rule


def test_non_contracting_axis_is_not_converged(gates):
    values = np.array([[0.0], [1e-6], [3e-6]])
    assert (
        gates.axis_convergence(np.array([0.02, 0.01, 0.005]), values, REF)["status"]
        == "not_contracting"
    )


def test_reference_adds_each_axis_correction_to_the_base(gates):
    ref = gates.fd_reference(X[0], {"x": X[-1], "var": VAR[-1], "time": TIME[-1]})
    np.testing.assert_allclose(ref, [0.10759984, 0.04865818, 0.01949554], rtol=0, atol=1e-11)


def test_reference_verdict_requires_every_axis_and_the_domain(gates):
    ok = {"converged": True, "status": "converged"}
    assert gates.reference_verdict({"x": ok, "var": ok, "time": ok}, 0.0, REF)["converged"]
    bad = gates.reference_verdict(
        {"x": {"converged": False, "status": "final_change_too_large"}, "var": ok, "time": ok},
        0.0,
        REF,
    )
    assert not bad["converged"] and "x" in " ".join(bad["reasons"])
    assert not gates.reference_verdict({"x": ok, "var": ok, "time": ok}, 6e-6, REF)["converged"]


def test_level_selection_takes_the_coarse_side_of_the_first_passing_pair(gates):
    ref = level(0.1)
    calm = {name: level(0.1 + 1e-6) for name in SENSITIVITIES}
    levels = {"S0": level(0.1), "S1": level(0.1 + 4e-6), "S2": level(0.1 + 4.5e-6)}
    assert gates.select_level(levels, ref, {"S0": calm, "S1": None}, TH)["adopted"] == "S0"
    noisy_s0 = calm | {"chi_0.75": level(0.1 + 6e-6)}
    s1_calm = {name: level(0.1 + 4e-6) for name in SENSITIVITIES}
    assert gates.select_level(levels, ref, {"S0": noisy_s0, "S1": s1_calm}, TH)["adopted"] == "S1"
    assert (
        gates.select_level(levels, ref, {"S0": noisy_s0, "S1": None}, TH)["status"]
        == "not_achieved_budget"
    )
    apart = {"S0": level(0.1), "S1": level(0.1 + 6e-6), "S2": level(0.1 + 1.2e-5)}
    out = gates.select_level(apart, ref, {"S0": calm, "S1": s1_calm}, TH)
    assert (out["adopted"], out["status"]) == (None, "not_achieved")  # S2 is never adopted
    spotwise = {
        "S0": level(0.1),
        "S1": {q: np.array([0.1, 0.1, 0.1 + 6e-6]) for q in ("european", "american", "eep")},
        "S2": level(0.1),
    }
    assert (
        gates.select_level(spotwise, ref, {"S0": calm, "S1": None}, TH)["adopted"] is None
    )  # one spot decides


def boundary_case(dx=0.0025):
    spec_z = np.linspace(math.log(2e-4), math.log(2.0), 160)
    fd_z = np.linspace(math.log(1e-5), math.log(8.0), 101)
    fd_edge = np.full((601, 101), -0.2)
    fd_edge[-1] = np.nan
    return dict(
        spectral_log_var=spec_z,
        spectral_boundary=np.full((101, 160), -0.2 + dx / 2),
        spectral_status=np.zeros((101, 160), np.int8),
        fd_log_var=fd_z,
        fd_primary=fd_edge,
        fd_check=fd_edge[::2].copy(),
        fd_dx=dx,
        fd_x_bounds=(-1.2, 1.2),
        thresholds=BOUNDARY,
    )


def test_boundary_gate_pass_fail_mask_and_coverage(gates):
    case = boundary_case()
    ok = gates.boundary_gate(**case)
    assert ok["status"] == "pass" and ok["coverage"] == 1.0 and ok["max_deviation_cells"] == 0.0
    near = gates.boundary_gate(
        **(case | {"spectral_boundary": np.full((101, 160), -0.2 - 1.99 * 0.0025)})
    )
    far = gates.boundary_gate(
        **(case | {"spectral_boundary": np.full((101, 160), -0.2 - 2.01 * 0.0025)})
    )
    assert near["status"] == "pass" and far["status"] == "fail"
    edge = case["fd_primary"].copy()
    edge[:540] = (
        -1.2 + 3 * 0.0025
    )  # within 4 cells of the left x edge at every window time but t/T = .9
    masked = gates.boundary_gate(**(case | {"fd_primary": edge, "fd_check": edge[::2].copy()}))
    assert masked["status"] == "unsupported" and masked["coverage"] < 0.9


def test_boundary_gate_rejects_multiple_crossings_and_unconverged_fd(gates):
    case = boundary_case()
    status = case["spectral_status"].copy()
    status[50, 100] = 1  # multiple_crossings at t/T = .5, v inside [.01, .16]
    assert (
        "multiple_crossings_in_window"
        in gates.boundary_gate(**(case | {"spectral_status": status}))["reasons"]
    )
    shifted = case["fd_check"].copy()
    shifted[150, 60] -= 2 * 0.0025
    out = gates.boundary_gate(**(case | {"fd_check": shifted}))
    assert out["status"] == "fail" and out["fd_shift_cells"] == pytest.approx(2.0)


def test_bounds_check_reports_raw_violations(gates):
    spots = np.array([0.9, 1.0, 1.1])
    contract = {"domestic_rate": 0.05, "foreign_rate": 0.02, "expiry": 0.5}
    eu = np.array([0.1025, 0.0472, 0.0191])
    assert gates.bounds_check(eu, np.array([0.1076, 0.0487, 0.0195]), spots, contract, 2e-5)["pass"]
    bad = gates.bounds_check(eu, np.array([0.0999, 0.0487, 0.0195]), spots, contract, 2e-5)
    assert not bad["pass"] and bad["american_minus_payoff_min"] == pytest.approx(-1e-4)


def test_paper_match_uses_six_millionths_without_relaxation(gates):
    anchors = {
        "T0.5.american_n100": [0.107601, 0.048662, 0.019499],
        "T0.5.european": [0.102557, 0.047224, 0.019105],
        "T1.american_atm": 0.063668,
    }
    values = {
        "T0.5.american_n100": [0.10760094, 0.04866224, 0.01949905],
        "T0.5.european": [0.10255734, 0.04722426, 0.01910466],
        "T1.american_atm": 0.06366789,
    }
    assert gates.paper_match(values, anchors, 6e-6)["pass"]
    out = gates.paper_match(values | {"T1.american_atm": 0.063668 + 6.1e-6}, anchors, 6e-6)
    assert (
        not out["pass"]
        and out["failed"] == ["T1.american_atm"]
        and out["status"] == "paper_mismatch"
    )
    printed_only = gates.paper_match(values, anchors | {"T1.non_atm": "not_available"}, 6e-6)
    assert printed_only["pass"] and printed_only["not_available"] == ["T1.non_atm"]


def test_estimates_follow_the_design_formula(gates):
    measured = {
        "setup_seconds": 4.0,
        "solve_seconds": 2.0,
        "n_omega": 108,
        "n_var": 160,
        "n_time": 100,
        "scan_spacing": 0.0015625,
    }
    job = {"n_omega": 120, "n_var": 240, "n_time": 400, "scan_spacing": math.pi / 2560}
    w, v, t, s = 120 / 108, 1.5, 4.0, 0.0015625 / (math.pi / 2560)
    out = gates.estimate_seconds("spectral", measured, job, factor=2.0)
    assert out["seconds"] == pytest.approx(2.0 * (4.0 * w * v**3 + 2.0 * t * w * v**2 * s))
    same = gates.estimate_seconds("spectral", measured, {k: measured[k] for k in job}, factor=2.0)
    assert same["seconds"] == pytest.approx(12.0)
    fd = gates.estimate_seconds(
        "fd",
        {
            "setup_seconds": 1.4,
            "solve_seconds": 4.3,
            "nodes": 193819,
            "bandwidth": 101,
            "n_time": 150,
        },
        {"nodes": 193819, "bandwidth": 101, "n_time": 300},
        factor=2.0,
    )
    assert fd["seconds"] == pytest.approx(2.0 * (1.4 + 4.3 * 2.0))
    assert gates.estimate_seconds("spectral", None, job, factor=2.0)["status"] == "unmeasured"


def test_reproduced_requires_both_gates(gates):
    passed = {
        "0.5": {"price": True, "boundary": "pass"},
        "1.0": {"price": True, "boundary": "pass"},
    }
    assert gates.reproduction_label({"pass": True}, passed) == "reproduced"
    partial = passed | {"0.5": {"price": True, "boundary": "unsupported"}}
    assert gates.reproduction_label({"pass": True}, partial) == "constrained"
    assert gates.reproduction_label({"pass": False}, passed) == "not_reproduced"


def test_deltas_use_central_differences(gates):
    s, b = np.array([0.9, 1.0, 1.1]), 1e-3
    np.testing.assert_allclose(
        gates.deltas(0.3 * (s + b) ** 2, 0.3 * (s - b) ** 2, b), 0.6 * s, rtol=0, atol=1e-12
    )
