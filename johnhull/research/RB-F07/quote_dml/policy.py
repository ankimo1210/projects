"""Explicit domain and calibration routing for quote-DML saved-array predictions.

Raw surrogate output and analytic fallback remain separate. Passing these
checks establishes domain, calibration and price-bound compatibility only;
it does not establish accurate model Greeks or suitability for market use.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
from hullkit import _quote_dml_teachers as teacher

_SPEC = importlib.util.spec_from_file_location(
    "quote_dml_policy_replay", Path(__file__).with_name("replay.py")
)
replay = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(replay)


def _result(status, reason, *, raw=None, safe=None, fallback=False):
    return {"status": status, "reason": reason, "raw": raw, "safe": safe, "fallback": fallback}


def _same_numbers(left, right):
    try:
        a, b = np.asarray(left, dtype=float), np.asarray(right, dtype=float)
        return a.shape == b.shape and np.allclose(a, b, atol=1e-12, rtol=0)
    except (TypeError, ValueError):
        return False


def _same_schedules(left, right):
    try:
        return len(left) == len(right) and all(
            _same_numbers(a, b) for a, b in zip(left, right, strict=True)
        )
    except (TypeError, ValueError):
        return False


def _curve_context_reason(curve, contract, context):
    supported = {
        "pillar_times",
        "quote_times",
        "interpolation",
        "quote_kinds",
        "quote_unit",
        "payout",
        "strike",
        "sigma",
    }
    if context.keys() - supported:
        return "unknown_context"
    fixed = {
        "pillar_times": [times[-1] for times in teacher.QUOTE_TIMES],
        "quote_times": teacher.QUOTE_TIMES,
        "interpolation": "zero_linear",
        "quote_kinds": teacher.QUOTE_KINDS,
        "quote_unit": "rate_decimal",
    }
    for source in (curve, context):
        for key, expected in fixed.items():
            if key not in source:
                continue
            if key == "quote_times":
                matches = _same_schedules(source[key], expected)
            elif key == "pillar_times":
                matches = _same_numbers(source[key], expected)
            elif key == "quote_kinds":
                matches = tuple(source[key]) == expected
            else:
                matches = source[key] == expected
            if not matches:
                return f"unsupported_{key}"
    if contract.get("payout", 1) != 1 or context.get("payout", 1) != 1:
        return "unsupported_payout"
    return None


def _outside(value, lower, upper):
    # Include mathematical boundaries despite binary representation roundoff.
    rounding = 64 * np.finfo(float).eps * max(1.0, abs(lower), abs(upper))
    return value < lower - rounding or value > upper + rounding


def _raw_prediction(exported, market, q, spot, maturity, discount, a_quote):
    if exported["kind"] == "nn":
        coordinates = market.calibration.zeros if exported["mode"].startswith("theta") else q
        row = np.r_[coordinates, spot, maturity][None]
        prediction = replay.nn_predict(exported, row, market.dz_dq[None])
    elif exported["kind"] == "ridge":
        data = {
            "x_quote": np.r_[q, spot, maturity][None],
            "integrated_rate": np.array([-np.log(discount)]),
            "a_quote": a_quote[None],
        }
        prediction = replay.ridge_predict(exported, data)
    else:
        raise ValueError("unsupported saved model kind")
    return {
        "price": float(prediction["price"][0]),
        "g_quote": np.asarray(prediction["g_quote"][0], dtype=float).copy(),
    }


def safe_prediction(exported, q, spot, maturity, protocol, *, context=None, market=None):
    """Replay one saved surrogate and return raw/safe predictions with routing.

    Each prediction has scalar ``price`` and raw ``g_quote[6]`` (spot, q5).
    Supported but out-of-domain inputs, changed strike/sigma, amplification
    warnings and price-bound violations use the changed contract's analytic
    price and full Greeks. Unsupported curve contexts and invalid mathematics
    return no prediction. A supplied Market avoids recalibration but must
    correspond to q and the fixed protocol curve. Values are never clipped.
    """
    try:
        context = {} if context is None else dict(context)
        if protocol["schema_version"] != 1:
            return _result("failure", "unsupported_protocol_version")
        curve, contract = protocol["curve"], protocol["contract"]
        incompatible = _curve_context_reason(curve, contract, context)
        if incompatible:
            return _result("unsupported_context", incompatible)
        q = np.asarray(q, dtype=float)
        if q.shape != (5,) or not np.isfinite(q).all():
            return _result("failure", "invalid_quote_values")
        spot, maturity = float(spot), float(maturity)
        strike = float(context.get("strike", contract["strike"]))
        sigma = float(context.get("sigma", contract["sigma"]))
        parameters = np.asarray([spot, maturity, strike, sigma])
        if not np.isfinite(parameters).all() or np.any(parameters <= 0):
            return _result("failure", "invalid_contract_math")
    except (KeyError, TypeError, ValueError):
        return _result("failure", "invalid_protocol_or_inputs")

    try:
        if market is None:
            market = teacher.prepare_market(q)
        elif not np.allclose(market.quotes, q, atol=1e-14, rtol=1e-12):
            return _result("failure", "market_quote_mismatch")
        calibration = market.calibration
        if calibration.rank != 5:
            return _result("failure", "calibration_rank_failure")
        teacher.risk._rank(calibration.jacobian, calibration.quote_steps)
        if not _same_numbers(calibration.times, curve["pillar_times"]):
            return _result("unsupported_context", "unsupported_market_pillar_times")
        if calibration.interpolation != curve["interpolation"]:
            return _result("unsupported_context", "unsupported_market_interpolation")
        if not np.isfinite(calibration.amplification):
            return _result("failure", "invalid_calibration_diagnostics")
        fitted_quotes = tuple(
            teacher.risk.Quote(kind, value, times)
            for kind, value, times in zip(teacher.QUOTE_KINDS, q, teacher.QUOTE_TIMES, strict=True)
        )
        fitted, fitted_j = teacher.risk.model_quotes(
            fitted_quotes,
            calibration.times,
            calibration.zeros,
            interpolation=calibration.interpolation,
        )
        if not np.allclose(fitted, q, atol=1e-11, rtol=1e-10):
            return _result("failure", "market_curve_quote_mismatch")
        if not np.allclose(fitted_j, calibration.jacobian, atol=1e-10, rtol=1e-10):
            return _result("failure", "market_jacobian_mismatch")
        response = np.asarray(market.dz_dq, dtype=float)
        if response.shape != (5, 5) or not np.allclose(
            calibration.jacobian @ response, np.eye(5), atol=1e-10, rtol=1e-10
        ):
            return _result("failure", "market_quote_response_mismatch")
        discount, _, a_quote = teacher._curve(market, maturity)
    except (
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
        np.linalg.LinAlgError,
    ) as exc:
        return _result("failure", f"calibration_failure: {exc}")

    reasons = []
    center = np.asarray(curve["base_quotes"], dtype=float)
    width = float(curve["halfwidth"])
    if any(
        _outside(value, base - width, base + width) for value, base in zip(q, center, strict=True)
    ):
        reasons.append("quote_ood")
    if _outside(spot, *contract["spot_bounds"]):
        reasons.append("spot_ood")
    if _outside(maturity, *contract["maturity_bounds"]):
        reasons.append("maturity_ood")
    if strike != contract["strike"]:
        reasons.append("strike_ood")
    if sigma != contract["sigma"]:
        reasons.append("sigma_ood")
    if calibration.amplification > protocol["ood"]["amplification_limit"] or calibration.warnings:
        reasons.append("amplification_warning")

    try:
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            raw = _raw_prediction(exported, market, q, spot, maturity, discount, a_quote)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return _result("failure", f"saved_prediction_failure: {exc}")
    if not np.isfinite(raw["price"]) or not np.isfinite(raw["g_quote"]).all():
        reasons.append("nonfinite_prediction")
    elif raw["price"] < -1e-12 or raw["price"] > discount + 1e-12:
        reasons.append("price_bounds")
    if not reasons:
        safe = {"price": raw["price"], "g_quote": raw["g_quote"].copy()}
        return _result("ok", "inside_domain", raw=raw, safe=safe)

    try:
        exact = teacher.analytic(market, spot, maturity, strike=strike, sigma=sigma)
        safe = {"price": float(exact["price"]), "g_quote": exact["g_quote"].copy()}
    except (ValueError, RuntimeError, ArithmeticError, np.linalg.LinAlgError) as exc:
        return _result("failure", f"analytic_fallback_failure: {exc}", raw=raw)
    return _result("fallback", ",".join(reasons), raw=raw, safe=safe, fallback=True)
