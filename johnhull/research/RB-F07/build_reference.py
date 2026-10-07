"""Build RB-F07 synthetic research data; no network, training or new dependency."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from hullkit import _quote_risk as risk
from hullkit import rates
from scipy.optimize import brentq

HERE = Path(__file__).resolve().parent


def quotes():
    """The five synthetic deposit/FRA/swap quotes fixed by the design memo."""
    return (
        risk.Quote("deposit", 0.03, (0.5,)),
        risk.Quote("fra", 0.032, (0.5, 1)),
        risk.Quote("swap", 0.033, (1, 2)),
        risk.Quote("swap", 0.0345, (1, 2, 3)),
        risk.Quote("swap", 0.036, (1, 2, 3, 4, 5)),
    )


def _discount(t, pillars, zeros, interpolation="zero_linear"):
    if interpolation == "zero_linear" or t <= pillars[0] or t >= pillars[-1]:
        return np.exp(-t * np.interp(t, pillars, zeros))
    return np.exp(-np.interp(t, pillars, pillars * zeros))


def _model(quote, pillars, zeros, interpolation):
    dfs = np.array([_discount(t, pillars, zeros, interpolation) for t in quote.times])
    if quote.kind == "deposit":
        return (1 / dfs[0] - 1) / quote.times[0]
    if quote.kind == "fra":
        return (dfs[0] / dfs[-1] - 1) / (quote.times[-1] - quote.times[0])
    if quote.kind == "bond":
        return np.dot(quote.cashflows, dfs)
    return (1 - dfs[-1]) / np.dot(np.diff((0, *quote.times)), dfs)


def _bootstrap(instruments, interpolation="zero_linear"):
    # Independent scalar brentq: it never calls the production model or Jacobian.
    pillars = np.array([q.times[-1] for q in instruments])
    zeros = np.zeros(len(instruments))
    for i, quote in enumerate(instruments):

        def residual(z, index=i, instrument=quote):
            trial = zeros.copy()
            trial[index] = z
            return _model(instrument, pillars, trial, interpolation) - instrument.value

        zeros[i] = brentq(residual, -0.2, 1, xtol=5e-16, rtol=1e-14)
    return pillars, zeros


def _pv(pillars, zeros, interpolation="zero_linear"):
    dfs = np.array([_discount(t, pillars, zeros, interpolation) for t in (1, 2, 3, 4)])
    return 10_000_000 * (0.032 * dfs.sum() + dfs[-1] - 1) - 3_000_000 * _discount(
        1.5, pillars, zeros, interpolation
    )


def _rebootstrap_pv(instruments, interpolation="zero_linear"):
    return _pv(*_bootstrap(instruments, interpolation), interpolation)


def _portfolio(calibration):
    swap, grad_swap = risk.receiver_swap_value(calibration, 10_000_000, 0.032, (1, 2, 3, 4))
    bond, grad_bond = risk.cashflow_value(calibration, (1.5,), (-3_000_000,))
    return swap + bond, grad_swap + grad_bond


def _bump(instruments, width, interpolation="zero_linear"):
    values = []
    for i, quote in enumerate(instruments):
        up, down = list(instruments), list(instruments)
        up[i] = replace(quote, value=quote.value + width)
        down[i] = replace(quote, value=quote.value - width)
        values.append(
            (_rebootstrap_pv(up, interpolation) - _rebootstrap_pv(down, interpolation))
            / (2 * width)
            * 1e-4
        )
    return np.array(values)


def _case(calibration):
    value, gradient = _portfolio(calibration)
    quote_risk = risk.quote_sensitivity(calibration, gradient)
    return {
        "pv": value,
        "zeros": calibration.zeros.tolist(),
        "parameter_risk_per_bp": (gradient * 1e-4).tolist(),
        "quote_risk_per_bp": quote_risk.per_step.tolist(),
        "jacobian": calibration.jacobian.tolist(),
        "amplification": calibration.amplification,
        "condition_number_raw": calibration.condition_number,
        "scaled_residual_norm": calibration.scaled_residual_norm,
        "iterations": calibration.iterations,
        "warnings": list(calibration.warnings),
        "adjoint_relative_residual": quote_risk.solve_relative_residual,
    }


def build():
    """Return prices, risks, independent comparisons and three figure datasets."""
    instruments = quotes()
    calibration = risk.calibrate(instruments)
    base = _case(calibration)
    _, reference_zeros = _bootstrap(instruments)
    base["brentq_zero_max_abs_error"] = float(np.max(np.abs(reference_zeros - calibration.zeros)))
    base["reference_pv"] = float(_pv(calibration.times, reference_zeros))

    widths = np.logspace(-2, -10, 9)
    bumped = np.array([_bump(instruments, h) for h in widths])
    expected = np.array(base["quote_risk_per_bp"])
    complex_jacobian, complex_gradient = np.empty((5, 5)), np.empty(5)
    logdf_jacobian, logdf_gradient, pv_jacobian = np.empty((5, 5)), np.empty(5), np.empty((5, 5))
    residual_scales = []
    for quote in instruments:
        dfs = np.array([_discount(t, calibration.times, calibration.zeros) for t in quote.times])
        scale = (
            (quote.times[-1] - (quote.times[0] if quote.kind == "fra" else 0)) * dfs[-1]
            if quote.kind in {"deposit", "fra"}
            else np.dot(np.diff((0, *quote.times)), dfs)
        )
        residual_scales.append(scale)
    for i in range(5):
        perturbed = calibration.zeros.astype(complex)
        perturbed[i] += 1e-25j
        complex_jacobian[:, i] = (
            np.array(
                [_model(q, calibration.times, perturbed, "zero_linear") for q in instruments]
            ).imag
            / 1e-25
        )
        complex_gradient[i] = _pv(calibration.times, perturbed).imag / 1e-25
        for row, quote in enumerate(instruments):
            dfs = np.array([_discount(t, calibration.times, perturbed) for t in quote.times])
            scale = (
                (quote.times[-1] - (quote.times[0] if quote.kind == "fra" else 0)) * dfs[-1]
                if quote.kind in {"deposit", "fra"}
                else np.dot(np.diff((0, *quote.times)), dfs)
            )
            pv_jacobian[row, i] = (
                scale * (_model(quote, calibration.times, perturbed, "zero_linear") - quote.value)
            ).imag / 1e-25
        shifted_logdf = (-calibration.times * calibration.zeros).astype(complex)
        shifted_logdf[i] += 1e-25j
        shifted_zeros = -shifted_logdf / calibration.times
        logdf_jacobian[:, i] = (
            np.array(
                [_model(q, calibration.times, shifted_zeros, "zero_linear") for q in instruments]
            ).imag
            / 1e-25
        )
        logdf_gradient[i] = _pv(calibration.times, shifted_zeros).imag / 1e-25
    cs_risk = np.linalg.solve(complex_jacobian.T, complex_gradient) * 1e-4
    logdf_risk = np.linalg.solve(logdf_jacobian.T, logdf_gradient) * 1e-4
    pv_residual_risk = (
        np.array(residual_scales) * np.linalg.solve(pv_jacobian.T, complex_gradient) * 1e-4
    )

    h = 1e-6
    up = [replace(q, value=q.value + h) for q in instruments]
    down = [replace(q, value=q.value - h) for q in instruments]
    parallel = (_rebootstrap_pv(up) - _rebootstrap_pv(down)) / (2 * h) * 1e-4

    alternative = _case(risk.calibrate(instruments, interpolation="logdf_linear"))
    alternative["bump_risk_per_bp"] = _bump(instruments, 1e-5, "logdf_linear").tolist()
    coverage = []
    for maturity in (5, 4, 3.5, 3.1, 3.01):
        schedule = (*(float(t) for t in range(1, int(np.ceil(maturity)))), maturity)
        sparse = (*instruments[:-1], risk.Quote("swap", 0.036, schedule))
        case = _case(risk.calibrate(sparse, pillar_times=(0.5, 1, 2, 3, 5)))
        case["last_swap_maturity"] = maturity
        coverage.append(case)
    try:
        risk.calibrate((*instruments[:-1], instruments[3]), pillar_times=(0.5, 1, 2, 3, 5))
    except ValueError as exc:
        singular = str(exc)
    else:
        raise AssertionError("the unsupported five-year pillar must be rejected")

    hand = risk.calibrate((risk.Quote("deposit", 0.03, (1,)), risk.Quote("swap", 0.035, (1, 2))))
    hand_pv, hand_gradient = risk.cashflow_value(hand, (1.5,), (1_000_000,))
    table = [(0.25, 0, 99.6), (0.5, 0, 99.0), (1, 0, 97.8), (1.5, 4, 102.5), (2, 5, 105)]
    bonds = []
    for maturity, coupon, price in table:
        times = np.arange(maturity, 0, -0.5)[::-1] if coupon else np.array([maturity])
        flows = np.full(times.size, coupon / 2)
        flows[-1] += 100
        bonds.append(risk.Quote("bond", price, tuple(times), tuple(flows)))
    table_curve = risk.calibrate(bonds)
    table_pv, table_gradient = risk.cashflow_value(table_curve, (1.75,), (1_000_000,))
    _, table_reference = rates.bootstrap_zero_curve(table)
    return {
        "schema_version": 1,
        "scope": "synthetic, exact square single curve; v1; no direct quote dependence",
        "labels": ["6m deposit", "6x12 FRA", "2y swap", "3y swap", "5y swap"],
        "times": calibration.times.tolist(),
        "quotes": [{"kind": q.kind, "value": q.value, "times": list(q.times)} for q in instruments],
        "base": base,
        "bump": {
            "widths": widths.tolist(),
            "risk_per_bp": bumped.tolist(),
            "max_abs_error_per_bp": np.max(np.abs(bumped - expected), axis=1).tolist(),
            "complex_step_max_abs_error_per_bp": float(np.max(np.abs(cs_risk - expected))),
        },
        "invariance": {
            "logdf_parameter_risk_per_1e4": (logdf_gradient * 1e-4).tolist(),
            "logdf_quote_risk_per_bp": logdf_risk.tolist(),
            "pv_residual_quote_risk_per_bp": pv_residual_risk.tolist(),
            "complex_step_jacobian_max_abs_error": float(
                np.max(np.abs(complex_jacobian - calibration.jacobian))
            ),
        },
        "parallel_shift": {
            "width": h,
            "sum_quote_risk_per_bp": float(expected.sum()),
            "rebootstrap_risk_per_bp": float(parallel),
        },
        "logdf_interpolation": alternative,
        "coverage": coverage,
        "singular_pillar_rejection": singular,
        "hand": {
            "pv": hand_pv,
            "zeros": hand.zeros.tolist(),
            "quote_risk_per_bp": risk.quote_sensitivity(hand, hand_gradient).per_step.tolist(),
        },
        "hull_table_4_3": {
            "inputs": table,
            "pv": table_pv,
            "zeros": table_curve.zeros.tolist(),
            "bootstrap_max_abs_zero_error": float(
                np.max(np.abs(table_curve.zeros - table_reference))
            ),
            "quote_risk_per_price_1": risk.quote_sensitivity(
                table_curve, table_gradient
            ).per_step.tolist(),
        },
    }


def check(data):
    """Check scientific fixtures with unit-specific tolerances, never SHA."""
    base = data["base"]
    expected = np.array(base["quote_risk_per_bp"])
    assert base["brentq_zero_max_abs_error"] < 2e-14
    np.testing.assert_allclose(base["pv"], base["reference_pv"], rtol=1e-12, atol=5e-8)
    assert abs(base["parameter_risk_per_bp"][0]) < 2e-8
    np.testing.assert_allclose(expected[0], 106.30, rtol=0, atol=0.01)
    bump = data["bump"]
    errors = bump["max_abs_error_per_bp"]
    np.testing.assert_allclose(
        errors,
        np.max(np.abs(np.array(bump["risk_per_bp"]) - expected), axis=1),
        rtol=1e-12,
        atol=2e-8,
    )
    assert 60 < errors[0] / errors[1] < 150
    np.testing.assert_allclose(bump["risk_per_bp"][3], expected, rtol=1e-8, atol=2e-6)
    assert bump["complex_step_max_abs_error_per_bp"] < 2e-8
    invariance = data["invariance"]
    for field in ("logdf_quote_risk_per_bp", "pv_residual_quote_risk_per_bp"):
        np.testing.assert_allclose(invariance[field], expected, rtol=1e-12, atol=2e-8)
    assert invariance["complex_step_jacobian_max_abs_error"] < 2e-12
    parallel = data["parallel_shift"]
    np.testing.assert_allclose(
        parallel["rebootstrap_risk_per_bp"], expected.sum(), rtol=1e-9, atol=2e-6
    )
    alternative = data["logdf_interpolation"]
    np.testing.assert_allclose(
        alternative["bump_risk_per_bp"], alternative["quote_risk_per_bp"], rtol=1e-8, atol=2e-6
    )
    assert abs(base["pv"] - alternative["pv"]) > 5000
    assert not data["coverage"][0]["warnings"]
    assert data["coverage"][-2]["warnings"] and data["coverage"][-2]["amplification"] > 10
    assert data["singular_pillar_rejection"]
    np.testing.assert_allclose(
        data["hand"]["quote_risk_per_bp"], [-68.17998013, -70.45357276], rtol=0, atol=1e-8
    )
    assert data["hull_table_4_3"]["bootstrap_max_abs_zero_error"] < 2e-14
    np.testing.assert_allclose(
        data["hull_table_4_3"]["quote_risk_per_price_1"],
        [0, -218.967, -218.967, 5574.455, 4299.115],
        rtol=0,
        atol=0.001,
    )


def _compare_stable(cached, fresh, path=""):
    if isinstance(fresh, dict):
        assert cached.keys() == fresh.keys(), path
        for key in fresh:
            _compare_stable(cached[key], fresh[key], f"{path}.{key}")
    elif isinstance(fresh, (list, tuple)):
        assert len(cached) == len(fresh), path
        for i, (left, right) in enumerate(zip(cached, fresh, strict=True)):
            _compare_stable(left, right, f"{path}.{i}")
    elif isinstance(fresh, (float, int)):
        if path.endswith("iterations"):
            return  # Fitted residuals gate convergence, not iteration count.
        atol = (
            2e-14
            if any(s in path for s in ("zeros", "zero_error", "times", "quotes", "inputs"))
            else 2e-8
        )
        if "pv" in path and "risk" not in path and "jacobian" not in path:
            atol = 5e-8
        if "jacobian" in path:
            atol = 2e-12
        rtol = 1e-10 if "condition_number" in path or "amplification" in path else 1e-12
        np.testing.assert_allclose(cached, fresh, rtol=rtol, atol=atol, err_msg=path)
    else:
        assert cached == fresh, path


def main():
    """Generate references, or validate cached and fresh scientific fixtures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = build()
    check(data)
    path = HERE / "reference.json"
    if args.check:
        cached = json.loads(path.read_text())
        check(cached)
        assert cached.keys() == data.keys()
        for key in data.keys() - {"bump"}:
            _compare_stable(cached[key], data[key], key)
        np.testing.assert_allclose(
            cached["bump"]["widths"], data["bump"]["widths"], rtol=1e-12, atol=0
        )
        # PV subtraction amplifies roundoff as 1/h; do not freeze a V-shaped tail.
        for i, width in enumerate(data["bump"]["widths"]):
            bound = max(2e-8, 40 * np.finfo(float).eps * abs(data["base"]["pv"]) * 1e-4 / width)
            np.testing.assert_allclose(
                cached["bump"]["risk_per_bp"][i],
                data["bump"]["risk_per_bp"][i],
                rtol=1e-12,
                atol=bound,
            )
        print("RB-F07 reference: cached + fresh independent numerical checks PASS")
    else:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        print(f"wrote {path.name}; independent numerical checks PASS")


if __name__ == "__main__":
    main()
