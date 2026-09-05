"""Curve construction, validation, pricing, diagnostics, and risk reporting.

The implementation works in log-discount-factor space.  That representation
keeps discount factors strictly positive, including when rates are negative.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from scipy.optimize import least_squares


RATE_TYPES = {"deposit", "ois_swap"}
TYPE_FLOORS = {"deposit": 0.00005, "ois_swap": 0.00005, "bond": 0.05}
KNOTS = np.array(
    [0.0, 1 / 12, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0,
     4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0],
    dtype=float,
)


@dataclass
class LogDiscountCurve:
    """Continuously compounded curve represented by log discount factors."""

    knots: np.ndarray
    log_discounts: np.ndarray
    method: str

    def __post_init__(self) -> None:
        self.knots = np.asarray(self.knots, dtype=float)
        self.log_discounts = np.asarray(self.log_discounts, dtype=float)
        if self.knots.ndim != 1 or len(self.knots) < 2:
            raise ValueError("at least two increasing curve knots are required")
        if self.knots.shape != self.log_discounts.shape:
            raise ValueError("knots and log_discounts must have equal length")
        if not np.all(np.diff(self.knots) > 0) or self.knots[0] != 0.0:
            raise ValueError("curve knots must be strictly increasing and start at zero")
        if not np.isfinite(self.log_discounts).all() or abs(self.log_discounts[0]) > 1e-12:
            raise ValueError("log discount factors must be finite with D(0)=1")
        self._spline = (
            CubicSpline(self.knots, self.log_discounts, bc_type="natural", extrapolate=True)
            if self.method == "advanced" else None
        )

    def log_discount(self, maturity: float | np.ndarray) -> np.ndarray:
        t = np.asarray(maturity, dtype=float)
        if np.any(t < 0):
            raise ValueError("maturity must be non-negative")
        if self._spline is not None:
            return np.asarray(self._spline(t), dtype=float)
        return np.interp(t, self.knots, self.log_discounts)

    def discount(self, maturity: float | np.ndarray) -> np.ndarray:
        # exp of a finite log discount is always strictly positive.
        return np.exp(np.clip(self.log_discount(maturity), -700.0, 700.0))

    def zero(self, maturity: float | np.ndarray) -> np.ndarray:
        t = np.asarray(maturity, dtype=float)
        safe_t = np.maximum(t, 1e-12)
        return -self.log_discount(t) / safe_t

    def forward(self, maturity: float | np.ndarray) -> np.ndarray:
        t = np.asarray(maturity, dtype=float)
        if self._spline is not None:
            return -np.asarray(self._spline(t, 1), dtype=float)
        idx = np.searchsorted(self.knots, t, side="right") - 1
        idx = np.clip(idx, 0, len(self.knots) - 2)
        slopes = np.diff(self.log_discounts) / np.diff(self.knots)
        return -slopes[idx]


class BumpedCurve:
    """A deterministic zero-rate bump of an existing curve."""

    def __init__(self, base: LogDiscountCurve, bump: float, shape: Callable[[np.ndarray], np.ndarray]) -> None:
        self.base = base
        self.bump = bump
        self.shape = shape

    def discount(self, maturity: float | np.ndarray) -> np.ndarray:
        t = np.asarray(maturity, dtype=float)
        return self.base.discount(t) * np.exp(-self.bump * t * self.shape(t))


@dataclass
class FitResult:
    curve: LogDiscountCurve
    robust_factors: np.ndarray
    objective: float
    iterations: int


def _reason_add(frame: pd.DataFrame, index: int, reason: str) -> None:
    current = frame.at[index, "reason"]
    frame.at[index, "reason"] = reason if not current else f"{current}; {reason}"


def _set_action(frame: pd.DataFrame, index: int, action: str, reason: str) -> None:
    priority = {"keep": 0, "correct": 1, "downweight": 2, "exclude": 3}
    if priority[action] >= priority[frame.at[index, "action"]]:
        frame.at[index, "action"] = action
    _reason_add(frame, index, reason)


def validate_and_clean(raw: pd.DataFrame, valuation_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate observations and return usable data plus one audit row per input.

    Quotes are normalized to annual decimals for rates and points per 100 for
    bonds.  The original input is never altered.
    """
    val_date = pd.Timestamp(valuation_date).date()
    audit = raw.copy().reset_index(drop=True)
    # Keep this public validation function robust when called directly, rather
    # than requiring callers to remember the loader's coercion step.
    audit["timestamp"] = pd.to_datetime(audit["timestamp"], errors="coerce", utc=True)
    audit["maturity_date"] = pd.to_datetime(audit["maturity_date"], errors="coerce")
    audit["action"] = "keep"
    audit["reason"] = "validated"
    audit["normalized_quote"] = np.nan
    audit["quote_spread"] = np.nan
    audit["weight"] = 0.0
    audit["stale"] = False

    expected = {
        "deposit": ("simple_rate", "PERCENT"),
        "ois_swap": ("par_rate", "PERCENT"),
        "bond": ("clean_price", "PRICE_POINTS"),
    }
    text_columns = ["obs_id", "instrument_id", "source", "currency", "instrument_type", "quote_type", "quote_unit", "day_count"]
    for i, row in audit.iterrows():
        invalid: list[str] = []
        for column in text_columns:
            if pd.isna(row[column]) or not str(row[column]).strip():
                invalid.append(f"missing {column}")
        typ = row["instrument_type"]
        if typ not in expected:
            invalid.append("unsupported instrument_type")
        if row["currency"] != "USD":
            invalid.append("currency must be USD")
        if row["day_count"] != "ACT/365F":
            invalid.append("day_count must be ACT/365F")
        if pd.isna(row["timestamp"]):
            invalid.append("invalid timestamp")
        if pd.isna(row["maturity_date"]):
            invalid.append("invalid maturity_date")
        if not np.isfinite(row["maturity_years"]) or not (0 < row["maturity_years"] <= 60):
            invalid.append("maturity_years outside (0, 60]")
        if not np.isfinite(row["start_years"]) or abs(row["start_years"]) > 1e-8:
            invalid.append("only spot-starting instruments are supported")
        if not np.isfinite(row["payment_frequency"]) or row["payment_frequency"] not in (1, 2, 4, 12):
            invalid.append("unsupported payment_frequency")
        if not np.isfinite(row["settlement_days"]) or row["settlement_days"] != 2:
            invalid.append("settlement_days must equal 2")
        if not np.isfinite(row["liquidity_score"]) or not 0 <= row["liquidity_score"] <= 1:
            invalid.append("liquidity_score outside [0, 1]")
        if typ in expected and (row["quote_type"], row["quote_unit"]) != expected[typ]:
            invalid.append("quote_type or quote_unit conflicts with conventions")
        if typ == "bond" and (not np.isfinite(row["coupon_rate"]) or not 0 <= row["coupon_rate"] < 0.25):
            invalid.append("bond coupon_rate missing or outside [0, 25%)")
        if typ != "bond" and np.isfinite(row["coupon_rate"]):
            invalid.append("non-bond coupon_rate must be blank")
        if not np.isfinite(row["quote_value"]):
            invalid.append("missing or non-finite quote_value")
        if not np.isfinite(row["bid"]) or not np.isfinite(row["ask"]):
            invalid.append("missing or non-finite bid/ask")
        if invalid:
            _set_action(audit, i, "exclude", ", ".join(invalid))
            continue

        divisor = 100.0 if typ in RATE_TYPES else 1.0
        quote = float(row["quote_value"]) / divisor
        bid = float(row["bid"]) / divisor
        ask = float(row["ask"]) / divisor
        low, high = min(bid, ask), max(bid, ask)
        if bid > ask:
            _set_action(audit, i, "correct", "bid/ask inverted; ordered before calculating spread")
        if quote < low or quote > high:
            quote = (low + high) / 2.0
            _set_action(audit, i, "correct", "quote outside bid/ask; replaced with bid/ask midpoint")
        if typ in RATE_TYPES and not (-0.25 < quote < 0.50):
            _set_action(audit, i, "exclude", "normalized rate outside defensible range")
            continue
        # Prices are points per 100.  The intentionally broad 40--160 range
        # admits distressed-but-plausible sovereign-style prices while catching
        # a decimal/PERCENT unit mix-up such as 1.04 instead of 104.
        if typ == "bond" and not (40.0 < quote < 160.0):
            _set_action(audit, i, "exclude", "bond clean price outside defensible range")
            continue
        spread = high - low
        floor = TYPE_FLOORS[typ]
        quality = max(float(row["liquidity_score"]), 0.05) * min(1.0, (floor / max(spread, floor)) ** 2)
        timestamp_date = row["timestamp"].date()
        if timestamp_date < val_date:
            quality *= 0.25
            audit.at[i, "stale"] = True
            _set_action(audit, i, "downweight", "stale timestamp; retained at 25% quality weight")
        audit.at[i, "normalized_quote"] = quote
        audit.at[i, "quote_spread"] = spread
        audit.at[i, "weight"] = quality

    # Keep exactly one valid quote for a repeated economic instrument.  Latest
    # timestamp wins; liquidity deterministically breaks a timestamp tie.
    candidates = audit.index[audit["action"] != "exclude"]
    for instrument_id, group in audit.loc[candidates].groupby("instrument_id", sort=False):
        if len(group) <= 1:
            continue
        winner = group.sort_values(["timestamp", "liquidity_score", "obs_id"], kind="stable").index[-1]
        for index in group.index:
            if index != winner:
                _set_action(audit, index, "exclude", f"duplicate {instrument_id}; fresher observation retained")
                audit.at[index, "weight"] = 0.0

    usable = audit.loc[audit["action"] != "exclude"].copy().reset_index(drop=True)
    if len(usable) < 12:
        raise ValueError("fewer than 12 usable observations remain after validation")
    return usable, audit


def payment_schedule(maturity: float, frequency: int, anchored_to_maturity: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Return payment dates and ACT/365F accruals, including a final stub.

    OIS schedules start at the valuation date.  Bonds with irregular maturity
    fractions instead roll their regular coupon dates backward from maturity;
    this avoids inventing a tiny terminal coupon stub.
    """
    interval = 1.0 / frequency
    if anchored_to_maturity:
        count = int(np.ceil(maturity / interval - 1e-12))
        times = maturity - interval * np.arange(count - 1, -1, -1, dtype=float)
    else:
        times = np.arange(interval, maturity - 1e-10, interval, dtype=float)
        if len(times) == 0 or abs(times[-1] - maturity) > 1e-10:
            times = np.append(times, maturity)
    times = np.unique(np.round(times, 12))
    accruals = np.diff(np.concatenate(([0.0], times)))
    return times, accruals


def model_quote(curve: LogDiscountCurve | BumpedCurve, row: pd.Series) -> float:
    maturity = float(row["maturity_years"])
    typ = row["instrument_type"]
    if typ == "deposit":
        return float((1.0 / curve.discount(maturity) - 1.0) / maturity)
    times, accruals = payment_schedule(maturity, int(row["payment_frequency"]), anchored_to_maturity=typ == "bond")
    discounts = curve.discount(times)
    if typ == "ois_swap":
        annuity = float(np.dot(accruals, discounts))
        return float((1.0 - curve.discount(maturity)) / annuity)
    if typ == "bond":
        coupon = float(row["coupon_rate"])
        cashflows = 100.0 * coupon * accruals
        cashflows[-1] += 100.0
        return float(np.dot(cashflows, discounts))
    raise ValueError(f"unsupported instrument type {typ}")


def receiver_fixed_pv(curve: LogDiscountCurve | BumpedCurve, row: pd.Series) -> float:
    """PV of receiver/fixed exposure, with documented benchmark notionals."""
    maturity = float(row["maturity_years"])
    typ = row["instrument_type"]
    if typ == "deposit":
        notional = 1_000_000.0
        rate = float(row["normalized_quote"])
        return notional * ((1.0 + rate * maturity) * curve.discount(maturity) - 1.0)
    times, accruals = payment_schedule(maturity, int(row["payment_frequency"]), anchored_to_maturity=typ == "bond")
    discounts = curve.discount(times)
    if typ == "ois_swap":
        notional = 1_000_000.0
        rate = float(row["normalized_quote"])
        fixed_leg = rate * float(np.dot(accruals, discounts))
        floating_leg = 1.0 - float(curve.discount(maturity))
        return notional * (fixed_leg - floating_leg)
    if typ == "bond":
        coupon = float(row["coupon_rate"])
        cashflows = 100.0 * coupon * accruals
        cashflows[-1] += 100.0
        return float(np.dot(cashflows, discounts))
    raise ValueError(f"unsupported instrument type {typ}")


def _initial_log_discounts(frame: pd.DataFrame, knots: np.ndarray) -> np.ndarray:
    rate_rows = frame.loc[frame["instrument_type"].isin(RATE_TYPES)]
    if len(rate_rows):
        times = rate_rows["maturity_years"].to_numpy(float)
        rates = rate_rows["normalized_quote"].to_numpy(float)
        order = np.argsort(times)
        initial_rates = np.interp(knots[1:], times[order], rates[order], left=rates[order][0], right=rates[order][-1])
    else:
        initial_rates = np.full(len(knots) - 1, 0.02)
    return np.concatenate(([0.0], -initial_rates * knots[1:]))


def _curve_from_params(params: np.ndarray, method: str) -> LogDiscountCurve:
    return LogDiscountCurve(KNOTS, np.concatenate(([0.0], np.asarray(params, dtype=float))), method)


def _model_residuals(curve: LogDiscountCurve, frame: pd.DataFrame) -> np.ndarray:
    return np.array([model_quote(curve, row) - float(row["normalized_quote"]) for _, row in frame.iterrows()])


def _fit_once(frame: pd.DataFrame, method: str, smoothing: float, robust: np.ndarray, initial: np.ndarray | None) -> FitResult:
    if initial is None:
        initial = _initial_log_discounts(frame, KNOTS)[1:]
    floors = frame["instrument_type"].map(TYPE_FLOORS).to_numpy(float)
    quality = frame["weight"].to_numpy(float)

    def residual_vector(params: np.ndarray) -> np.ndarray:
        curve = _curve_from_params(params, method)
        raw = _model_residuals(curve, frame)
        market = raw / floors * np.sqrt(quality * robust)
        if method != "advanced" or smoothing <= 0:
            return market
        q = np.concatenate(([0.0], params))
        slopes = np.diff(q) / np.diff(KNOTS)
        # Penalise changes in the instantaneous forward rate.  The 10bp scale
        # makes smoothing strength legible and independent of unit conventions.
        penalty = np.sqrt(smoothing) * np.diff(slopes) / 0.001
        return np.concatenate((market, penalty))

    solution = least_squares(
        residual_vector,
        initial,
        bounds=(np.full(len(KNOTS) - 1, -2.4), np.full(len(KNOTS) - 1, 1.2)),
        method="trf",
        xtol=1e-10,
        ftol=1e-10,
        gtol=1e-10,
        max_nfev=1500,
    )
    if not solution.success or not np.isfinite(solution.x).all():
        raise RuntimeError(f"curve optimisation failed: {solution.message}")
    return FitResult(_curve_from_params(solution.x, method), robust, float(np.dot(solution.fun, solution.fun)), int(solution.nfev))


def fit_curve(frame: pd.DataFrame, method: str, smoothing: float = 0.25, robust_iterations: int = 3) -> FitResult:
    """Fit a baseline or regularised curve, with Huber-style IRLS if advanced."""
    if method not in {"baseline", "advanced"}:
        raise ValueError("method must be baseline or advanced")
    robust = np.ones(len(frame), dtype=float)
    current: FitResult | None = None
    rounds = 1 if method == "baseline" else robust_iterations
    initial: np.ndarray | None = None
    for _ in range(rounds):
        current = _fit_once(frame, method, smoothing if method == "advanced" else 0.0, robust, initial)
        initial = current.curve.log_discounts[1:]
        raw = _model_residuals(current.curve, frame)
        standardized = np.abs(raw / frame["instrument_type"].map(TYPE_FLOORS).to_numpy(float))
        robust = np.where(standardized <= 3.0, 1.0, 3.0 / np.maximum(standardized, 1e-12))
    assert current is not None
    # Refit once against the final robust weights so reported factors match the curve.
    if method == "advanced":
        current = _fit_once(frame, method, smoothing, robust, initial)
    return FitResult(current.curve, robust, current.objective, current.iterations)


def maturity_holdout(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deterministic blocked-by-maturity holdout without duplicate leakage."""
    maturities = np.array(sorted(frame["maturity_years"].unique()), dtype=float)
    bucket = {float(maturity): i for i, maturity in enumerate(maturities)}
    # Every fifth maturity bucket supplies interpolation-style validation.  All
    # records at the same maturity are held out together.
    holdout_mask = frame["maturity_years"].map(lambda value: bucket[float(value)] % 5 == 2).to_numpy(bool)
    train, holdout = frame.loc[~holdout_mask].copy(), frame.loc[holdout_mask].copy()
    if len(train) < 12 or len(holdout) < 4:
        raise ValueError("maturity-aware split did not leave enough observations")
    return train.reset_index(drop=True), holdout.reset_index(drop=True)


def _metrics(curve: LogDiscountCurve, frame: pd.DataFrame) -> dict[str, object]:
    residual = _model_residuals(curve, frame)
    floors = frame["instrument_type"].map(TYPE_FLOORS).to_numpy(float)
    weights = frame["weight"].to_numpy(float)
    weighted_rmse = float(np.sqrt(np.sum(weights * (residual / floors) ** 2) / np.sum(weights)))
    by_type: dict[str, dict[str, float]] = {}
    for typ, group in frame.assign(_residual=residual).groupby("instrument_type"):
        values = group["_residual"].to_numpy(float)
        by_type[str(typ)] = {"rmse": float(np.sqrt(np.mean(values ** 2))), "median_abs_error": float(np.median(np.abs(values)))}
    return {
        "n": int(len(frame)),
        "weighted_normalized_rmse": weighted_rmse,
        "median_abs_standardized_error": float(np.median(np.abs(residual / floors))),
        "by_instrument_type": by_type,
    }


def compare_models(usable: pd.DataFrame, smoothing: float = 0.25) -> tuple[dict[str, object], str]:
    train, holdout = maturity_holdout(usable)
    baseline = fit_curve(train, "baseline", smoothing=0.0)
    # Use the blocked visible holdout to choose regularisation.  We select the
    # smoothest candidate whose error is within 1% of the best candidate: that
    # makes the stability preference explicit rather than hiding it in a hand-
    # picked lambda.
    candidate_strengths = (smoothing, 1.0, 3.0, 10.0)
    advanced_candidates: list[tuple[float, FitResult, dict[str, object]]] = []
    for strength in dict.fromkeys(candidate_strengths):
        candidate = fit_curve(train, "advanced", smoothing=float(strength))
        advanced_candidates.append((float(strength), candidate, _metrics(candidate.curve, holdout)))
    best_error = min(float(metric["weighted_normalized_rmse"]) for _, _, metric in advanced_candidates)
    eligible = [item for item in advanced_candidates if float(item[2]["weighted_normalized_rmse"]) <= best_error * 1.01]
    chosen_smoothing, advanced, advanced_holdout = max(eligible, key=lambda item: item[0])
    comparison: dict[str, object] = {
        "holdout_method": "every fifth ordered maturity bucket, with all same-maturity records held out together",
        "smoothing_strength": chosen_smoothing,
        "advanced_smoothing_candidates": [
            {"strength": strength, "holdout_weighted_normalized_rmse": float(metric["weighted_normalized_rmse"])}
            for strength, _, metric in advanced_candidates
        ],
        "advanced_smoothing_selection": "largest candidate within 1% of best advanced holdout weighted RMSE",
        "baseline": {"train": _metrics(baseline.curve, train), "holdout": _metrics(baseline.curve, holdout)},
        "advanced": {"train": _metrics(advanced.curve, train), "holdout": advanced_holdout},
    }
    base_error = comparison["baseline"]["holdout"]["weighted_normalized_rmse"]  # type: ignore[index]
    advanced_error = comparison["advanced"]["holdout"]["weighted_normalized_rmse"]  # type: ignore[index]
    if advanced_error < base_error * 0.98:
        selected = "advanced"
        rationale = "Advanced curve reduced the blocked maturity-holdout weighted error by more than 2%."
    else:
        selected = "baseline"
        rationale = "Baseline was within 2% of the advanced holdout error; the simpler piecewise-log-discount curve was preferred."
    comparison["selected_model"] = selected
    comparison["selection_rationale"] = rationale
    comparison["holdout_maturity_years"] = sorted(float(x) for x in holdout["maturity_years"].unique())
    return comparison, selected


def apply_robust_audit(audit: pd.DataFrame, final_frame: pd.DataFrame, robust_factors: np.ndarray) -> pd.DataFrame:
    """Record final IRLS downweights in the row-level cleaning audit."""
    result = audit.copy()
    factor_by_obs = dict(zip(final_frame["obs_id"], robust_factors, strict=True))
    for index, row in result.iterrows():
        factor = factor_by_obs.get(row["obs_id"])
        if factor is None:
            continue
        result.at[index, "weight"] = float(row["weight"]) * float(factor)
        if factor < 0.999:
            _set_action(result, index, "downweight", f"robust IRLS factor {factor:.4f} after pricing residual review")
    return result


def parallel_shape(t: np.ndarray) -> np.ndarray:
    return np.ones_like(t, dtype=float)


def key_shape(key: float) -> Callable[[np.ndarray], np.ndarray]:
    """Partition-of-unity key-rate tent shape for 2Y/5Y/10Y/30Y keys."""
    keys = np.array([2.0, 5.0, 10.0, 30.0])
    position = int(np.where(keys == key)[0][0])

    def shape(t: np.ndarray) -> np.ndarray:
        x = np.asarray(t, dtype=float)
        values = np.zeros_like(x)
        if position == 0:
            values[x <= keys[0]] = 1.0
            between = (x > keys[0]) & (x < keys[1])
            values[between] = (keys[1] - x[between]) / (keys[1] - keys[0])
        elif position == len(keys) - 1:
            between = (x > keys[-2]) & (x < keys[-1])
            values[between] = (x[between] - keys[-2]) / (keys[-1] - keys[-2])
            values[x >= keys[-1]] = 1.0
        else:
            left = (x > keys[position - 1]) & (x <= key)
            right = (x > key) & (x < keys[position + 1])
            values[left] = (x[left] - keys[position - 1]) / (key - keys[position - 1])
            values[right] = (keys[position + 1] - x[right]) / (keys[position + 1] - key)
        return values

    return shape


def build_risk(curve: LogDiscountCurve, frame: pd.DataFrame) -> pd.DataFrame:
    bump = 0.0001
    records: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        def sensitivity(shape: Callable[[np.ndarray], np.ndarray]) -> float:
            down = receiver_fixed_pv(BumpedCurve(curve, -bump, shape), row)
            up = receiver_fixed_pv(BumpedCurve(curve, bump, shape), row)
            return (down - up) / 2.0

        item: dict[str, object] = {"instrument_id": row["instrument_id"], "dv01": sensitivity(parallel_shape)}
        for key in (2.0, 5.0, 10.0, 30.0):
            item[f"key_{int(key)}y"] = sensitivity(key_shape(key))
        records.append(item)
    risk = pd.DataFrame(records)
    risk["key_sum"] = risk[["key_2y", "key_5y", "key_10y", "key_30y"]].sum(axis=1)
    risk["key_sum_minus_dv01"] = risk["key_sum"] - risk["dv01"]
    return risk


def _max_zero_difference(left: LogDiscountCurve, right: LogDiscountCurve) -> float:
    grid = np.linspace(1 / 12, 30.0, 361)
    return float(np.max(np.abs(left.zero(grid) - right.zero(grid))) * 10_000.0)


def sensitivity_checks(curve: LogDiscountCurve, usable: pd.DataFrame, selected: str, smoothing: float, robust: np.ndarray) -> dict[str, object]:
    """Run independent refit perturbations and report maximum zero-rate impact."""
    checks: list[dict[str, object]] = []
    if selected == "advanced":
        half = fit_curve(usable, "advanced", smoothing=smoothing / 2)
        double = fit_curve(usable, "advanced", smoothing=smoothing * 2)
        checks.extend([
            {"name": "half_smoothing", "smoothing_strength": smoothing / 2, "max_zero_rate_change_bp": _max_zero_difference(curve, half.curve)},
            {"name": "double_smoothing", "smoothing_strength": smoothing * 2, "max_zero_rate_change_bp": _max_zero_difference(curve, double.curve)},
        ])
    else:
        advanced = fit_curve(usable, "advanced", smoothing=smoothing)
        checks.append({"name": "advanced_model_alternative", "smoothing_strength": smoothing, "max_zero_rate_change_bp": _max_zero_difference(curve, advanced.curve)})
        baseline_refit = fit_curve(usable, "baseline", smoothing=0.0)
        checks.append({"name": "baseline_refit", "smoothing_strength": 0.0, "max_zero_rate_change_bp": _max_zero_difference(curve, baseline_refit.curve)})
    inlier = usable.loc[robust >= 0.999].copy()
    if len(inlier) >= 12:
        no_outliers = fit_curve(inlier, selected, smoothing=smoothing)
        checks.append({"name": "exclude_robust_outliers", "observations_removed": int(len(usable) - len(inlier)), "max_zero_rate_change_bp": _max_zero_difference(curve, no_outliers.curve)})
    fresh = usable.loc[~usable["stale"]].copy()
    if len(fresh) >= 12:
        fresh_fit = fit_curve(fresh, selected, smoothing=smoothing)
        checks.append({"name": "exclude_stale_quotes", "observations_removed": int(len(usable) - len(fresh)), "max_zero_rate_change_bp": _max_zero_difference(curve, fresh_fit.curve)})
    return {"base_model": selected, "checks": checks}


def _write_charts(output: Path, grid: pd.DataFrame, repricing: pd.DataFrame, comparison: dict[str, object]) -> list[Path]:
    chart_dir = output / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    saved: list[Path] = []
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(grid["maturity_years"], grid["zero_rate"] * 100, color="#145a8d", linewidth=2)
    ax.set(xlabel="Maturity (years)", ylabel="Continuously compounded zero rate (%)", title="Zero curve")
    fig.tight_layout(); path = chart_dir / "zero_curve.png"; fig.savefig(path, dpi=150); plt.close(fig); saved.append(path)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(grid["maturity_years"], grid["forward_rate"] * 100, color="#b13e19", linewidth=2)
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set(xlabel="Maturity (years)", ylabel="Instantaneous forward rate (%)", title="Forward curve")
    fig.tight_layout(); path = chart_dir / "forward_curve.png"; fig.savefig(path, dpi=150); plt.close(fig); saved.append(path)
    fig, (rate_ax, bond_ax) = plt.subplots(2, 1, figsize=(9, 6.5), sharex=True, constrained_layout=True)
    for typ, group in repricing.loc[repricing["instrument_type"].isin(RATE_TYPES)].groupby("instrument_type"):
        rate_ax.scatter(group["maturity_years"], group["residual"] * 10_000, s=24, alpha=0.75, label=typ)
    rate_ax.axhline(0, color="black", linewidth=0.7)
    rate_ax.set(ylabel="Rate residual (bp)", title="Repricing residuals")
    rate_ax.legend(fontsize=8)
    bonds = repricing.loc[repricing["instrument_type"] == "bond"]
    bond_ax.scatter(bonds["maturity_years"], bonds["residual"], s=24, alpha=0.75, color="#4c78a8", label="bond")
    bond_ax.axhline(0, color="black", linewidth=0.7)
    bond_ax.set(xlabel="Maturity (years)", ylabel="Bond residual (price points)")
    bond_ax.legend(fontsize=8)
    path = chart_dir / "repricing.png"; fig.savefig(path, dpi=150); plt.close(fig); saved.append(path)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    names = ["Baseline", "Advanced"]
    values = [comparison["baseline"]["holdout"]["weighted_normalized_rmse"], comparison["advanced"]["holdout"]["weighted_normalized_rmse"]]  # type: ignore[index]
    colors = ["#6c8ebf", "#70ad47"]
    ax.bar(names, values, color=colors)
    ax.set(ylabel="Weighted normalized holdout RMSE", title="Blocked maturity-holdout comparison")
    for i, value in enumerate(values): ax.text(i, value, f"{value:.3f}", ha="center", va="bottom")
    fig.tight_layout(); path = chart_dir / "model_comparison.png"; fig.savefig(path, dpi=150); plt.close(fig); saved.append(path)
    return saved


def run_workflow(market_data: Path, output: Path, valuation_date: str) -> dict[str, object]:
    """Execute deterministic validation, fitting, reporting, and output checks."""
    from .io import load_market_data
    from .report import render_report

    raw = load_market_data(market_data)
    usable, audit = validate_and_clean(raw, valuation_date)
    comparison, selected = compare_models(usable)
    smoothing = float(comparison["smoothing_strength"])
    final_fit = fit_curve(usable, selected, smoothing=smoothing)
    audited = apply_robust_audit(audit, usable, final_fit.robust_factors)
    curve = final_fit.curve
    output = Path(output)
    curves_dir, diagnostics_dir = output / "curves", output / "diagnostics"
    curves_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    grid_times = np.linspace(1 / 12, 30.0, 361)
    grid = pd.DataFrame({
        "maturity_years": grid_times,
        "zero_rate": curve.zero(grid_times),
        "discount_factor": curve.discount(grid_times),
        "forward_rate": curve.forward(grid_times),
    })
    if not np.isfinite(grid.to_numpy(float)).all() or not (grid["discount_factor"] > 0).all():
        raise RuntimeError("fitted curve contains non-finite values or non-positive discount factors")
    grid.to_csv(curves_dir / "curve.csv", index=False)
    cleaning_columns = ["obs_id", "instrument_id", "action", "normalized_quote", "weight", "reason"]
    audited.loc[:, cleaning_columns].to_csv(diagnostics_dir / "cleaning.csv", index=False)
    repricing = usable[["instrument_id", "instrument_type", "maturity_years", "normalized_quote", "weight"]].copy()
    repricing = repricing.rename(columns={"normalized_quote": "market_quote"})
    repricing["model_quote"] = [model_quote(curve, row) for _, row in usable.iterrows()]
    repricing["residual"] = repricing["model_quote"] - repricing["market_quote"]
    repricing = repricing[["instrument_id", "instrument_type", "maturity_years", "market_quote", "model_quote", "residual", "weight"]]
    repricing.to_csv(diagnostics_dir / "repricing.csv", index=False)
    risk = build_risk(curve, usable)
    risk.to_csv(diagnostics_dir / "risk.csv", index=False)
    with (diagnostics_dir / "model_comparison.json").open("w", encoding="utf-8") as handle:
        json.dump(comparison, handle, indent=2, allow_nan=False)
    sensitivity = sensitivity_checks(curve, usable, selected, smoothing, final_fit.robust_factors)
    with (diagnostics_dir / "sensitivity.json").open("w", encoding="utf-8") as handle:
        json.dump(sensitivity, handle, indent=2, allow_nan=False)
    chart_paths = _write_charts(output, grid, repricing, comparison)
    report_path = output.parent / "reports" / "research_report.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    render_report(report_path, valuation_date, raw, audited, comparison, sensitivity, repricing, risk, chart_paths)
    # A compact report also travels with an arbitrary alternate CLI output directory.
    portable_report = output / "reports" / "research_report.html"
    portable_report.parent.mkdir(parents=True, exist_ok=True)
    portable_report.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")
    return {
        "raw_observations": int(len(raw)),
        "usable_observations": int(len(usable)),
        "selected_model": selected,
        "robust_downweighted": int(np.sum(final_fit.robust_factors < 0.999)),
        "curve_rows": int(len(grid)),
        "reports": [str(report_path), str(portable_report)],
    }
