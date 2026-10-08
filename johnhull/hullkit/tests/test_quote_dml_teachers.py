"""Calibrated digital teachers against independent bootstrap and density integrals."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from hullkit import _quote_risk as risk

Q = np.array([0.03, 0.032, 0.033, 0.0345, 0.036])
CASES = [(80, 0.05), (95, 0.25), (100, 1.5), (110, 4.5), (120, 5.0)]


@pytest.fixture(scope="module")
def teacher():
    def load():
        name = "hullkit._quote_dml_teachers"
        assert importlib.util.find_spec(name) is not None, (
            "calibrated quote digital teacher is missing"
        )
        return importlib.import_module(name)

    return load


@pytest.fixture(scope="module")
def reference():
    def load():
        path = (
            Path(__file__).resolve().parents[2] / "research/RB-F07/quote_dml/reference_methods.py"
        )
        assert path.exists(), "independent calibrated digital reference is missing"
        spec = importlib.util.spec_from_file_location("quote_dml_reference", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return load


@pytest.mark.parametrize("spot,maturity", CASES)
def test_price_and_total_risk_match_independent_density(teacher, reference, spot, maturity):
    teacher, reference = teacher(), reference()
    market = teacher.prepare_market(Q)
    got = teacher.analytic(market, spot, maturity)
    expected = reference.digital_moments(Q, spot, maturity)
    assert got["price"] == pytest.approx(expected["price"], abs=1e-12, rel=1e-10)
    np.testing.assert_allclose(got["g_quote"], expected["g_quote"], atol=1e-10, rtol=1e-9)
    np.testing.assert_allclose(
        got["g_quote"][1:], market.dz_dq.T @ got["g_theta"][1:], atol=1e-10, rtol=1e-9
    )
    assert got["g_quote"][0] > 0


@pytest.mark.parametrize("q", [Q, Q - 0.04, Q + np.array([0.001, -0.001, 0.002, -0.002, 0.001])])
def test_market_and_inverse_calibration_use_correct_coordinates(teacher, reference, q):
    teacher, reference = teacher(), reference()
    market = teacher.prepare_market(q)
    pillars, zeros = reference.bootstrap(q)
    np.testing.assert_allclose(market.calibration.times, pillars, atol=1e-14, rtol=1e-12)
    np.testing.assert_allclose(market.calibration.zeros, zeros, atol=1e-12, rtol=1e-10)
    np.testing.assert_allclose(
        market.calibration.jacobian @ market.dz_dq, np.eye(5), atol=1e-12, rtol=1e-10
    )


@pytest.mark.parametrize("maturity", [0.5, 1.0, 2.0, 3.0, 5.0])
def test_pillar_maturity_risk_matches_rebootstrap(teacher, reference, maturity):
    teacher, reference = teacher(), reference()
    got = teacher.analytic(teacher.prepare_market(Q), 100.0, maturity)
    for width in (1e-4, 1e-5, 1e-6):
        changes = np.eye(5) * width
        bumped = np.array(
            [
                (
                    reference.digital_price(Q + d, 100, maturity)
                    - reference.digital_price(Q - d, 100, maturity)
                )
                / (2 * width)
                for d in changes
            ]
        )
        np.testing.assert_allclose(got["g_quote"][1:], bumped, atol=1e-7, rtol=1e-6)


def test_fixed_cashflow_market_connection(teacher, reference):
    teacher, reference = teacher(), reference()
    market = teacher.prepare_market(Q)
    pv, gz = risk.cashflow_value(market.calibration, (1.5,), (-3_000_000,))

    def value(q):
        times, zeros = reference.bootstrap(q)
        return -3_000_000 * np.exp(-1.5 * np.interp(1.5, times, zeros))

    changes = np.eye(5) * 1e-5
    bumped = np.array([(value(Q + d) - value(Q - d)) / 2e-5 for d in changes])
    assert pv == pytest.approx(value(Q), abs=1e-6, rel=1e-10)
    np.testing.assert_allclose(
        risk.quote_sensitivity(market.calibration, gz).per_unit, bumped, atol=1e-4, rtol=1e-6
    )


def test_log_discount_and_quote_bp_preserve_physical_risk(teacher):
    teacher = teacher()
    market = teacher.prepare_market(Q)
    got = teacher.analytic(market, 100.0, 1.5)
    dz_dlogdf = np.diag(-1 / market.calibration.times)
    j_logdf = market.calibration.jacobian @ dz_dlogdf
    g_logdf = dz_dlogdf.T @ got["g_theta"][1:]
    np.testing.assert_allclose(
        np.linalg.solve(j_logdf.T, g_logdf), got["g_quote"][1:], atol=1e-10, rtol=1e-9
    )
    np.testing.assert_allclose(
        (market.dz_dq * 1e-4).T @ got["g_theta"][1:],
        got["g_quote"][1:] * 1e-4,
        atol=1e-14,
        rtol=1e-9,
    )


@pytest.mark.parametrize("kwargs", [{"spot": 0}, {"maturity": 0}, {"sigma": 0}, {"strike": 0}])
def test_mathematically_invalid_contract_rejected(teacher, kwargs):
    teacher = teacher()
    args = {"spot": 100.0, "maturity": 1.0, "sigma": 0.2, "strike": 100.0} | kwargs
    with pytest.raises(ValueError):
        teacher.analytic(teacher.prepare_market(Q), **args)


def test_invalid_quote_shape_rejected(teacher):
    teacher = teacher()
    with pytest.raises(ValueError):
        teacher.prepare_market(Q[:4])


@pytest.mark.parametrize("spot", [95.0, 100.0, 105.0])
@pytest.mark.parametrize("maturity", [0.05, 0.25, 1.5, 4.5])
def test_lrm_and_conditioning_within_independent_six_se(teacher, reference, spot, maturity):
    teacher, reference = teacher(), reference()
    z = np.random.default_rng(1107).standard_normal(65536)
    got = teacher.samples(teacher.prepare_market(Q), spot, maturity, z)
    expected = reference.digital_moments(Q, spot, maturity)
    assert got["mc_regime"] == "regular"
    for key in ("lrm", "conditional"):
        mean = got[key].mean(axis=0)
        se = got[key].std(axis=0, ddof=1) / np.sqrt(z.size)
        assert np.all(np.abs(mean - expected["g_quote"]) <= 6 * se + 1e-10)
    for key in ("payoff", "conditional_price"):
        mean = got[key].mean()
        se = got[key].std(ddof=1) / np.sqrt(z.size)
        assert abs(mean - expected["price"]) <= 6 * se + 1e-12


@pytest.mark.parametrize("spot,maturity", CASES)
def test_lrm_variance_matches_independent_second_moment(teacher, reference, spot, maturity):
    teacher, reference = teacher(), reference()
    expected = reference.digital_moments(Q, spot, maturity)
    variance = expected["lrm_second_moment"] - expected["g_quote"] ** 2
    got = teacher.lrm_variance(teacher.prepare_market(Q), spot, maturity)
    np.testing.assert_allclose(got, variance, atol=1e-10, rtol=1e-9)
    assert np.all(got >= 0)


def test_negative_controls_keep_the_known_discount_and_boundary_bias(teacher, reference):
    teacher, reference = teacher(), reference()
    market = teacher.prepare_market(Q)
    z = np.random.default_rng(6017).standard_normal(4096)
    out = teacher.samples(market, 100.0, 1.5, z)
    exact = teacher.analytic(market, 100.0, 1.5)
    missing_discount = out["payoff"][:, None] * np.r_[0.0, exact["a_quote"]]
    np.testing.assert_allclose(
        out["discount_omitted"] - out["lrm"], missing_discount, atol=1e-13, rtol=1e-10
    )
    np.testing.assert_allclose(out["naive_pathwise"][:, 0], 0.0, atol=1e-14)
    np.testing.assert_allclose(
        out["naive_pathwise"][:, 1:],
        -out["payoff"][:, None] * exact["a_quote"],
        atol=1e-13,
        rtol=1e-10,
    )
    ref = reference.digital_moments(Q, 100, 1.5)
    np.testing.assert_allclose(
        ref["discount_omitted_mean"] - ref["g_quote"],
        ref["price"] * np.r_[0, exact["a_quote"]],
        atol=1e-10,
        rtol=1e-9,
    )
    assert ref["naive_pathwise_mean"][0] == pytest.approx(0, abs=1e-14)
    assert ref["g_quote"][0] > 0


def test_conditioning_uses_total_nonflat_curve_drift(teacher, reference):
    teacher, reference = teacher(), reference()
    q = Q + np.array([0.005, -0.005, 0.003, -0.003, 0.004])
    market = teacher.prepare_market(q)
    z = np.array([-1.5, -0.25, 0.0, 0.5, 2.0])
    out = teacher.samples(market, 103.0, 4.5, z)
    exact = teacher.analytic(market, 103.0, 4.5)
    from scipy.special import ndtr

    b = (
        np.log(103 / 100) + exact["integrated_rate"] - 0.2**2 * 4.5 / 2 + 0.2 * np.sqrt(2.25) * z
    ) / (0.2 * np.sqrt(2.25))
    np.testing.assert_allclose(
        out["conditional_price"], exact["discount"] * ndtr(b), atol=1e-12, rtol=1e-10
    )
    expected = reference.conditioning_moments(q, 103, 4.5)
    np.testing.assert_allclose(expected["g_quote"], exact["g_quote"], atol=1e-10, rtol=1e-9)


def test_rare_zero_hit_sample_is_not_regular_mc_evidence(teacher):
    teacher = teacher()
    z = np.random.default_rng(1107).standard_normal(65536)
    out = teacher.samples(teacher.prepare_market(Q), 80.0, 0.05, z)
    assert out["expected_hits"] < 20
    assert out["mc_regime"] == "rare_event"
    assert np.count_nonzero(out["payoff"]) == 0
    assert teacher.analytic(teacher.prepare_market(Q), 80.0, 0.05)["price"] > 0


def test_path_axis_precedes_last_risk_component_axis(teacher):
    teacher = teacher()
    market = teacher.prepare_market(Q)
    z = np.random.default_rng(6017).standard_normal((3, 64))
    out = teacher.samples(market, 100, 1.5, z)
    assert out["payoff"].shape == (3, 64)
    assert out["lrm"].shape == (3, 64, 6)
    for index in range(3):
        single = teacher.samples(market, 100, 1.5, z[index])
        np.testing.assert_allclose(out["lrm"][index], single["lrm"], atol=1e-12, rtol=1e-10)
