"""Curve construction, valuation, diagnostics, and risk calculations.

The implementation deliberately keeps discount factors positive by parameterising
the curve with continuously compounded zero rates.  Cash-flow dates are evaluated
from the documented ACT/365F year fractions rather than reconstructed from a
calendar so that the supplied benchmark convention remains authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Iterable

import numpy as np
import pandas as pd
from scipy.optimize import least_squares


RATE_TYPES = {"deposit", "ois_swap"}
EXPECTED_TYPES = {"deposit", "ois_swap", "bond"}
KEY_RATES = (2.0, 5.0, 10.0, 30.0)
HOLDOUT_TARGETS = (2.0, 5.0, 10.0, 20.0, 30.0)
NOTIONAL = 1_000_000.0
BP = 1.0e-4


def _finite(value: object) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    weights = np.maximum(np.asarray(weights, dtype=float), 1e-12)
    order = np.argsort(values)
    cumulative = np.cumsum(weights[order])
    return float(values[order][np.searchsorted(cumulative, 0.5 * cumulative[-1])])


def _payment_schedule(maturity: float, frequency: int) -> tuple[np.ndarray, np.ndarray]:
    """Return payment times and accruals, including a final stub if needed."""
    if maturity <= 0 or frequency <= 0:
        raise ValueError("maturity and payment frequency must be positive")
    interval = 1.0 / float(frequency)
    regular_count = int(np.floor(maturity / interval + 1e-10))
    times = [interval * i for i in range(1, regular_count + 1)]
    if not times or times[-1] < maturity - 1e-9:
        times.append(float(maturity))
    else:
        times[-1] = float(maturity)
    times_array = np.asarray(times, dtype=float)
    accruals = np.diff(np.concatenate(([0.0], times_array)))
    return times_array, accruals


@dataclass(frozen=True)
class PiecewiseZeroCurve:
    """Piecewise-linear continuously compounded zero curve."""

    knots: np.ndarray
    zeros: np.ndarray

    def __post_init__(self) -> None:
        knots = np.asarray(self.knots, dtype=float)
        zeros = np.asarray(self.zeros, dtype=float)
        if knots.ndim != 1 or zeros.ndim != 1 or knots.size != zeros.size:
            raise ValueError("knots and zeros must be equally-sized one-dimensional arrays")
        if knots.size < 2 or np.any(~np.isfinite(knots)) or np.any(~np.isfinite(zeros)):
            raise ValueError("curve knots and zeros must be finite and contain at least two points")
        if knots[0] < 0 or np.any(np.diff(knots) <= 0):
            raise ValueError("curve knots must be strictly increasing and non-negative")
        object.__setattr__(self, "knots", knots)
        object.__setattr__(self, "zeros", zeros)

    def zero(self, maturity: float | np.ndarray) -> float | np.ndarray:
        values = np.asarray(maturity, dtype=float)
        result = np.interp(values, self.knots, self.zeros)
        # Constant-zero extrapolation is explicit and stable for a long-end tail.
        result = np.where(values < self.knots[0], self.zeros[0], result)
        result = np.where(values > self.knots[-1], self.zeros[-1], result)
        return float(result) if values.ndim == 0 else result

    def discount(self, maturity: float | np.ndarray) -> float | np.ndarray:
        values = np.asarray(maturity, dtype=float)
        if np.any(values < 0):
            raise ValueError("maturity must be non-negative")
        result = np.exp(-np.asarray(self.zero(values), dtype=float) * values)
        return float(result) if values.ndim == 0 else result

    def forward(self, maturity: float | np.ndarray, method: str = "analytical") -> float | np.ndarray:
        """Return the instantaneous continuously compounded forward rate.

        For a piecewise-linear zero rate, ``-d log(D)/dT`` is analytic within
        each segment and equals ``z(T) + T * dz/dT``.  At an interior knot the
        left/right derivatives differ; their midpoint is used deterministically
        so a reporting grid does not create a one-cell finite-difference spike.
        The explicit ``finite_difference`` option is retained for audit
        comparison with the previous output construction.
        """
        values = np.asarray(maturity, dtype=float)
        if np.any(values < 0):
            raise ValueError("maturity must be non-negative")
        if method == "finite_difference":
            flat = values.reshape(-1)
            if flat.size == 1:
                h = 1.0e-5
                left = float(self.discount(max(float(flat[0]) - h, 0.0)))
                right = float(self.discount(float(flat[0]) + h))
                result = np.asarray([-(np.log(right) - np.log(left)) / (2.0 * h)], dtype=float)
            else:
                log_discount = np.log(np.asarray(self.discount(flat), dtype=float))
                result = -np.gradient(log_discount, flat, edge_order=2)
            result = result.reshape(values.shape)
            return float(result) if values.ndim == 0 else result
        if method != "analytical":
            raise ValueError("forward method must be analytical or finite_difference")

        flat = values.reshape(-1)
        zero = np.asarray(self.zero(flat), dtype=float)
        spacings = np.diff(self.knots)
        slopes = np.diff(self.zeros) / spacings
        segment = np.searchsorted(self.knots, flat, side="right") - 1
        segment = np.clip(segment, 0, len(slopes) - 1)
        result = zero + flat * slopes[segment]
        # The zero rate is held constant beyond the last knot, hence the
        # extrapolated instantaneous forward is the terminal zero rate.
        result = np.where(flat > self.knots[-1], self.zeros[-1], result)
        for index in range(1, len(self.knots) - 1):
            at_knot = np.isclose(flat, self.knots[index], rtol=0.0, atol=1.0e-12)
            if np.any(at_knot):
                result[at_knot] = zero[at_knot] + flat[at_knot] * 0.5 * (slopes[index - 1] + slopes[index])
        result = result.reshape(values.shape)
        return float(result) if values.ndim == 0 else result

    def shifted(self, shift: float | np.ndarray | Callable[[np.ndarray], np.ndarray]) -> "ShiftedCurve":
        return ShiftedCurve(self, shift)

    def grid(
        self,
        start: float = 1.0 / 12.0,
        end: float = 30.0,
        count: int = 601,
        forward_method: str = "analytical",
    ) -> pd.DataFrame:
        maturities = np.linspace(start, end, count)
        discounts = np.asarray(self.discount(maturities), dtype=float)
        zeros = np.asarray(self.zero(maturities), dtype=float)
        forwards = np.asarray(self.forward(maturities, method=forward_method), dtype=float)
        return pd.DataFrame(
            {
                "maturity_years": maturities,
                "zero_rate": zeros,
                "discount_factor": discounts,
                "forward_rate": forwards,
            }
        )


@dataclass(frozen=True)
class ShiftedCurve:
    """A curve with a deterministic zero-rate shift, used for finite differences."""

    base: PiecewiseZeroCurve
    shift: float | np.ndarray | Callable[[np.ndarray], np.ndarray]

    def zero(self, maturity: float | np.ndarray) -> float | np.ndarray:
        values = np.asarray(maturity, dtype=float)
        if callable(self.shift):
            shift_values = np.asarray(self.shift(values), dtype=float)
        else:
            shift_values = np.asarray(self.shift, dtype=float)
            if shift_values.ndim == 0:
                shift_values = np.full_like(values, float(shift_values))
            else:
                shift_values = np.broadcast_to(shift_values, values.shape)
        result = np.asarray(self.base.zero(values), dtype=float) + shift_values
        return float(result) if values.ndim == 0 else result

    def discount(self, maturity: float | np.ndarray) -> float | np.ndarray:
        values = np.asarray(maturity, dtype=float)
        if np.any(values < 0):
            raise ValueError("maturity must be non-negative")
        result = np.exp(-np.asarray(self.zero(values), dtype=float) * values)
        return float(result) if values.ndim == 0 else result


def _market_quote(row: pd.Series, target_col: str = "normalized_quote") -> float:
    value = row.get(target_col)
    if not _finite(value):
        raise ValueError(f"missing normalized quote for {row.get('instrument_id', 'unknown')}")
    return float(value)


def model_quote(row: pd.Series, curve: PiecewiseZeroCurve | ShiftedCurve) -> float:
    """Price an instrument using the conventions in market_data/CONVENTIONS.md."""
    maturity = float(row["maturity_years"])
    instrument_type = str(row["instrument_type"])
    frequency = int(row["payment_frequency"])
    if instrument_type == "deposit":
        discount = float(curve.discount(maturity))
        return (1.0 / discount - 1.0) / maturity
    if instrument_type == "ois_swap":
        times, accruals = _payment_schedule(maturity, frequency)
        discounts = np.asarray(curve.discount(times), dtype=float)
        denominator = float(np.dot(accruals, discounts))
        if denominator <= 0:
            raise ValueError("swap annuity must be positive")
        return (1.0 - float(curve.discount(maturity))) / denominator
    if instrument_type == "bond":
        coupon = float(row["coupon_rate"])
        times, _ = _payment_schedule(maturity, frequency)
        discounts = np.asarray(curve.discount(times), dtype=float)
        coupon_cashflow = 100.0 * coupon / frequency
        return float(np.sum(coupon_cashflow * discounts) + 100.0 * float(curve.discount(maturity)))
    raise ValueError(f"unsupported instrument type: {instrument_type}")


def receiver_pv(row: pd.Series, curve: PiecewiseZeroCurve | ShiftedCurve) -> float:
    """PV of the receiver-fixed representation used for benchmark risk."""
    maturity = float(row["maturity_years"])
    typ = str(row["instrument_type"])
    quote = _market_quote(row)
    if typ == "deposit":
        return NOTIONAL * ((1.0 + quote * maturity) * float(curve.discount(maturity)) - 1.0)
    if typ == "ois_swap":
        times, accruals = _payment_schedule(maturity, int(row["payment_frequency"]))
        discounts = np.asarray(curve.discount(times), dtype=float)
        annuity = float(np.dot(accruals, discounts))
        return NOTIONAL * (quote * annuity - (1.0 - float(curve.discount(maturity))))
    if typ == "bond":
        times, _ = _payment_schedule(maturity, int(row["payment_frequency"]))
        discounts = np.asarray(curve.discount(times), dtype=float)
        coupon_cashflow = 100.0 * float(row["coupon_rate"]) / int(row["payment_frequency"])
        return float(np.sum(coupon_cashflow * discounts) + 100.0 * float(curve.discount(maturity)))
    raise ValueError(f"unsupported instrument type: {typ}")


def _analytic_parallel_dv01(row: pd.Series, curve: PiecewiseZeroCurve) -> float:
    """First-order check for the central finite difference, in PV currency units."""
    maturity = float(row["maturity_years"])
    typ = str(row["instrument_type"])
    quote = _market_quote(row)
    discount_maturity = float(curve.discount(maturity))
    if typ == "deposit":
        return NOTIONAL * (1.0 + quote * maturity) * maturity * discount_maturity * BP
    times, accruals = _payment_schedule(maturity, int(row["payment_frequency"]))
    discounts = np.asarray(curve.discount(times), dtype=float)
    time_weighted_annuity = float(np.dot(accruals * times, discounts))
    if typ == "ois_swap":
        return NOTIONAL * (quote * time_weighted_annuity + maturity * discount_maturity) * BP
    coupon_cashflow = 100.0 * float(row["coupon_rate"]) / int(row["payment_frequency"])
    return float((np.sum(coupon_cashflow * times * discounts) + 100.0 * maturity * discount_maturity) * BP)


def _key_basis(maturity: np.ndarray | float) -> np.ndarray:
    """Partition-of-unity triangular key-rate bumps on the four requested keys."""
    values = np.atleast_1d(np.asarray(maturity, dtype=float))
    keys = np.asarray(KEY_RATES, dtype=float)
    result = np.zeros((values.size, keys.size), dtype=float)
    for i, value in enumerate(values):
        if value <= keys[0]:
            result[i, 0] = 1.0
        elif value >= keys[-1]:
            result[i, -1] = 1.0
        else:
            right = int(np.searchsorted(keys, value))
            left = right - 1
            fraction = (value - keys[left]) / (keys[right] - keys[left])
            result[i, left] = 1.0 - fraction
            result[i, right] = fraction
    return result[0] if np.ndim(maturity) == 0 else result


def key_rate_shift(key_index: int) -> Callable[[np.ndarray], np.ndarray]:
    if key_index < 0 or key_index >= len(KEY_RATES):
        raise IndexError("invalid key rate index")

    def shift(values: np.ndarray) -> np.ndarray:
        basis = _key_basis(values)
        return BP * (basis[:, key_index] if basis.ndim == 2 else basis[key_index])

    return shift


def calculate_risk(frame: pd.DataFrame, curve: PiecewiseZeroCurve) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for _, row in frame.iterrows():
        if not _finite(row.get("normalized_quote")) or row.get("action") == "exclude":
            continue
        down = receiver_pv(row, curve.shifted(-BP))
        up = receiver_pv(row, curve.shifted(BP))
        dv01 = (down - up) / 2.0
        analytic = _analytic_parallel_dv01(row, curve)
        risk: dict[str, float | str] = {
            "instrument_id": str(row["instrument_id"]),
            "dv01": float(dv01),
            "dv01_analytic": float(analytic),
            "dv01_fd_relative_error": float(abs(dv01 - analytic) / max(abs(analytic), 1e-12)),
        }
        for i, key in enumerate(KEY_RATES):
            down_key = receiver_pv(row, curve.shifted(lambda values, i=i: -key_rate_shift(i)(values)))
            up_key = receiver_pv(row, curve.shifted(key_rate_shift(i)))
            risk[f"key_{int(key)}y"] = float((down_key - up_key) / 2.0)
        risk["key_sum"] = float(sum(float(risk[f"key_{int(key)}y"]) for key in KEY_RATES))
        risk["key_sum_relative_error"] = float(abs(float(risk["key_sum"]) - dv01) / max(abs(dv01), 1e-12))
        rows.append(risk)
    return pd.DataFrame(rows)


def _interpolate_log_discount(times: list[float], discounts: list[float], maturity: float) -> float:
    x = np.asarray(times, dtype=float)
    y = np.log(np.maximum(np.asarray(discounts, dtype=float), 1e-300))
    if maturity <= x[-1] + 1e-12:
        return float(np.exp(np.interp(maturity, x, y)))
    # Constant zero-rate extrapolation beyond the last bootstrap point.
    last_zero = -y[-1] / x[-1]
    return float(np.exp(-last_zero * maturity))


def _group_quote(group: pd.DataFrame, target_col: str = "normalized_quote") -> float:
    values = group[target_col].astype(float).to_numpy()
    weights = group["weight"].astype(float).to_numpy()
    return _weighted_median(values, np.maximum(weights, 1e-8))


def fit_baseline(frame: pd.DataFrame) -> PiecewiseZeroCurve:
    """Bootstrap deposits and OIS swaps, then log-linearly interpolate D(T)."""
    usable = frame.loc[(frame["action"] != "exclude") & frame["normalized_quote"].notna()].copy()
    deposits = usable.loc[usable["instrument_type"] == "deposit"]
    swaps = usable.loc[usable["instrument_type"] == "ois_swap"]
    time_to_discount: dict[float, float] = {0.0: 1.0}
    # Front-end deposits are necessary to value semiannual OIS cash flows.
    for maturity in sorted(deposits["maturity_years"].unique().tolist()):
        group = deposits.loc[np.isclose(deposits["maturity_years"], maturity)]
        rate = _group_quote(group)
        discount = 1.0 / (1.0 + rate * float(maturity))
        if np.isfinite(discount) and discount > 0:
            time_to_discount[float(maturity)] = float(discount)
    for maturity in sorted(swaps["maturity_years"].unique().tolist()):
        group = swaps.loc[np.isclose(swaps["maturity_years"], maturity)]
        rate = _group_quote(group)
        times, accruals = _payment_schedule(float(maturity), int(round(group["payment_frequency"].median())))
        known_times = sorted(time_to_discount)
        earlier = np.asarray(
            [_interpolate_log_discount(known_times, [time_to_discount[t] for t in known_times], float(t)) for t in times[:-1]],
            dtype=float,
        )
        numerator = 1.0 - rate * float(np.dot(accruals[:-1], earlier))
        denominator = 1.0 + rate * float(accruals[-1])
        discount = numerator / denominator
        if np.isfinite(discount) and discount > 0:
            time_to_discount[float(maturity)] = float(discount)
    if len(time_to_discount) < 2:
        raise ValueError("baseline could not bootstrap at least one positive maturity")
    times = np.asarray(sorted(time_to_discount), dtype=float)
    discounts = np.asarray([time_to_discount[t] for t in times], dtype=float)
    zeros = np.zeros_like(times)
    zeros[0] = zeros[1] if times[0] == 0 else -np.log(discounts[0]) / times[0]
    zeros[1:] = -np.log(discounts[1:]) / times[1:]
    # Keep the t=0 value equal to the first finite zero to avoid a 0/0 convention.
    zeros[0] = zeros[1]
    return PiecewiseZeroCurve(times, zeros)


DEFAULT_KNOTS = np.asarray(
    [0.0, 1 / 12, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0,
     6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0],
    dtype=float,
)


def _smoothness_residual(zero_rates: np.ndarray, knots: np.ndarray, strength: float) -> np.ndarray:
    if zero_rates.size < 3 or strength <= 0:
        return np.empty(0, dtype=float)
    spacings = np.diff(knots)
    slopes = np.diff(zero_rates) / spacings
    # Curvature in zero-rate slope per year, scaled by 1%/year as a natural unit.
    curvature = np.diff(slopes) / np.maximum((spacings[1:] + spacings[:-1]) / 2.0, 1e-9)
    return np.sqrt(strength) * curvature / 0.01


def _initial_curve(frame: pd.DataFrame) -> PiecewiseZeroCurve:
    try:
        return fit_baseline(frame)
    except ValueError:
        return PiecewiseZeroCurve(np.asarray([0.0, 30.0]), np.asarray([0.02, 0.02]))


def fit_advanced(
    frame: pd.DataFrame,
    smoothness: float = 100.0,
    target_col: str = "normalized_quote",
    initial: PiecewiseZeroCurve | None = None,
    knots: np.ndarray | None = None,
) -> tuple[PiecewiseZeroCurve, dict[str, object]]:
    """Fit a robust weighted spline-like zero curve in quote space.

    The curve is smooth only through a curvature penalty; instrument pricing
    remains the objective.  Four re-fits update Huber-like residual weights so
    a narrow-spread bad print cannot dominate the long end.
    """
    usable = frame.loc[(frame["action"] != "exclude") & frame[target_col].notna()].copy().reset_index(drop=True)
    if usable.empty:
        raise ValueError("advanced fit has no usable observations")
    fit_knots = DEFAULT_KNOTS.copy() if knots is None else np.asarray(knots, dtype=float)
    if fit_knots.ndim != 1 or fit_knots.size < 2 or np.any(~np.isfinite(fit_knots)) or np.any(np.diff(fit_knots) <= 0) or fit_knots[0] < 0:
        raise ValueError("advanced fit knots must be finite, increasing, and non-negative")
    baseline = initial or _initial_curve(usable)
    initial_zero = np.asarray(baseline.zero(fit_knots), dtype=float)
    # Quote-space uncertainty: use half-spread but retain conservative floors.
    floors = np.where(usable["instrument_type"].eq("bond"), 0.02, 0.0001)
    spreads = np.abs(usable["normalized_ask"].astype(float) - usable["normalized_bid"].astype(float)) / 2.0
    scales = np.maximum(spreads.to_numpy(dtype=float), floors)
    base_weights = np.maximum(usable["weight"].astype(float).to_numpy(), 1e-6)
    # Start with a baseline residual screen so a bad bond cannot move the
    # entire curve before the first robust refit.  The weights are then updated
    # from the advanced residuals below, so this is still an iterative method.
    baseline_quotes = np.asarray([model_quote(row, baseline) for _, row in usable.iterrows()], dtype=float)
    baseline_standardized = (baseline_quotes - usable[target_col].astype(float).to_numpy()) / scales
    robust_weights = np.clip(1.5 / np.maximum(np.abs(baseline_standardized), 1.5), 0.05, 1.0)
    iteration_summaries: list[dict[str, float]] = []

    def residuals(zero_rates: np.ndarray, weights: np.ndarray) -> np.ndarray:
        curve = PiecewiseZeroCurve(fit_knots, zero_rates)
        model = np.asarray([model_quote(row, curve) for _, row in usable.iterrows()], dtype=float)
        scaled = (model - usable[target_col].astype(float).to_numpy()) / scales
        data_residual = np.sqrt(base_weights * weights) * scaled
        reg = _smoothness_residual(zero_rates, fit_knots, smoothness)
        return np.concatenate([data_residual, reg])

    z = initial_zero.copy()
    for iteration in range(4):
        result = least_squares(
            lambda values: residuals(values, robust_weights),
            z,
            bounds=(-0.25, 0.25),
            method="trf",
            loss="soft_l1",
            f_scale=1.0,
            max_nfev=900,
            xtol=1e-11,
            ftol=1e-11,
            gtol=1e-11,
        )
        z = result.x
        fitted = PiecewiseZeroCurve(fit_knots, z)
        model = np.asarray([model_quote(row, fitted) for _, row in usable.iterrows()], dtype=float)
        standardized = (model - usable[target_col].astype(float).to_numpy()) / scales
        # Huber-like iterative robust treatment; retain 20% of any extreme point.
        robust_weights = np.clip(1.5 / np.maximum(np.abs(standardized), 1.5), 0.05, 1.0)
        iteration_summaries.append(
            {
                "iteration": float(iteration + 1),
                "cost": float(result.cost),
                "max_abs_standardized_residual": float(np.max(np.abs(standardized))),
                "min_robust_weight": float(np.min(robust_weights)),
            }
        )
    final_curve = PiecewiseZeroCurve(fit_knots, z)
    return final_curve, {
        "n_observations": int(len(usable)),
        "smoothness": float(smoothness),
        "knots": fit_knots.tolist(),
        "robust_iterations": iteration_summaries,
        "target_col": target_col,
        "final_robust_weights": robust_weights.tolist(),
        "instrument_ids": usable["instrument_id"].astype(str).tolist(),
    }


def score_model(frame: pd.DataFrame, curve: PiecewiseZeroCurve, ids: Iterable[str] | None = None) -> dict[str, object]:
    subset = frame.loc[(frame["action"] != "exclude") & frame["normalized_quote"].notna()].copy()
    if ids is not None:
        wanted = set(str(v) for v in ids)
        subset = subset.loc[subset["instrument_id"].astype(str).isin(wanted)]
    if subset.empty:
        return {"n": 0, "weighted_standardized_rmse": None, "raw_rmse": {}, "mae": {}}
    model_values = np.asarray([model_quote(row, curve) for _, row in subset.iterrows()], dtype=float)
    market_values = subset["normalized_quote"].astype(float).to_numpy()
    floors = np.where(subset["instrument_type"].eq("bond"), 0.02, 0.0001)
    scales = np.maximum(
        np.abs(subset["normalized_ask"].astype(float).to_numpy() - subset["normalized_bid"].astype(float).to_numpy()) / 2.0,
        floors,
    )
    residual = model_values - market_values
    weights = np.maximum(subset["weight"].astype(float).to_numpy(), 1e-8)
    out: dict[str, object] = {
        "n": int(len(subset)),
        "weighted_standardized_rmse": float(np.sqrt(np.sum(weights * (residual / scales) ** 2) / np.sum(weights))),
        "raw_rmse": {},
        "mae": {},
        "max_abs_residual": {},
    }
    for typ in sorted(EXPECTED_TYPES):
        mask = subset["instrument_type"].to_numpy() == typ
        if not np.any(mask):
            continue
        out["raw_rmse"][typ] = float(np.sqrt(np.mean(residual[mask] ** 2)))
        out["mae"][typ] = float(np.mean(np.abs(residual[mask])))
        out["max_abs_residual"][typ] = float(np.max(np.abs(residual[mask])))
    return out


def score_segments(frame: pd.DataFrame, curve: PiecewiseZeroCurve, ids: Iterable[str] | None = None) -> dict[str, dict[str, object]]:
    """Score products and tenor bands separately using the same normalized error."""
    subset = frame.loc[(frame["action"] != "exclude") & frame["normalized_quote"].notna()].copy()
    if ids is not None:
        wanted = set(str(v) for v in ids)
        subset = subset.loc[subset["instrument_id"].astype(str).isin(wanted)]
    if subset.empty:
        return {}
    repriced = reprice_frame(subset, curve)
    if repriced.empty:
        return {}
    out: dict[str, dict[str, object]] = {}

    def add(label: str, values: pd.DataFrame) -> None:
        if values.empty:
            return
        weights = np.maximum(values["weight"].to_numpy(dtype=float), 1.0e-8)
        standardized = values["standardized_residual"].to_numpy(dtype=float)
        out[label] = {
            "n": int(len(values)),
            "weighted_standardized_rmse": float(np.sqrt(np.sum(weights * standardized**2) / np.sum(weights))),
        }

    for typ in sorted(EXPECTED_TYPES):
        add(f"product:{typ}", repriced.loc[repriced["instrument_type"] == typ])
    bands = (
        ("<2Y", 0.0, 2.0, False),
        ("2-5Y", 2.0, 5.0, False),
        ("5-10Y", 5.0, 10.0, False),
        ("10-20Y", 10.0, 20.0, False),
        ("20Y+", 20.0, np.inf, True),
    )
    for label, lower, upper, include_upper in bands:
        if include_upper:
            mask = repriced["maturity_years"] >= lower
        else:
            mask = (repriced["maturity_years"] >= lower) & (repriced["maturity_years"] < upper)
        add(f"tenor:{label}", repriced.loc[mask])
    return out


def reprice_frame(frame: pd.DataFrame, curve: PiecewiseZeroCurve) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        if row.get("action") == "exclude" or not _finite(row.get("normalized_quote")):
            continue
        market = _market_quote(row)
        fitted = model_quote(row, curve)
        floor = 0.02 if str(row["instrument_type"]) == "bond" else 0.0001
        scale = max(abs(float(row["normalized_ask"]) - float(row["normalized_bid"])) / 2.0, floor)
        rows.append(
            {
                "instrument_id": str(row["instrument_id"]),
                "instrument_type": str(row["instrument_type"]),
                "market_quote": float(market),
                "model_quote": float(fitted),
                "residual": float(fitted - market),
                "standardized_residual": float((fitted - market) / scale),
                "weight": float(row["weight"]),
                "maturity_years": float(row["maturity_years"]),
                "action": str(row["action"]),
            }
        )
    return pd.DataFrame(rows)


def choose_holdout(frame: pd.DataFrame) -> tuple[set[str], dict[str, object]]:
    """Hold out whole maturity clusters near 2/5/10/20/30Y, never random rows."""
    usable = frame.loc[(frame["action"] != "exclude") & frame["normalized_quote"].notna()].copy()
    unique = np.sort(usable["maturity_years"].unique())
    selected: list[float] = []
    for target in (*HOLDOUT_TARGETS, 1.0):
        if not len(unique):
            break
        distances = np.abs(unique - target)
        for value in unique[np.argsort(distances)]:
            if not any(np.isclose(value, old) for old in selected):
                # 1Y is an anchor when the dataset has no other short-end group;
                # otherwise the five key maturities provide a cleaner long-range test.
                if target == 1.0 and any(abs(s - target) < 0.75 for s in selected):
                    continue
                selected.append(float(value))
                break
    # Prefer exactly the requested five key clusters where available; the 1Y
    # fallback is only used on small/nonstandard datasets.
    selected_keys = [s for s in selected if any(np.isclose(s, k) for k in HOLDOUT_TARGETS)]
    if len(selected_keys) >= 3:
        selected = selected_keys
    holdout = usable.loc[usable["maturity_years"].apply(lambda x: any(np.isclose(x, s) for s in selected))]
    ids = set(holdout["instrument_id"].astype(str))
    if len(ids) == len(usable["instrument_id"].astype(str).unique()) and len(selected) > 1:
        selected = selected[:-1]
        holdout = usable.loc[usable["maturity_years"].apply(lambda x: any(np.isclose(x, s) for s in selected))]
        ids = set(holdout["instrument_id"].astype(str))
    return ids, {
        "method": "whole maturity clusters nearest to 2Y, 5Y, 10Y, 20Y, and 30Y; no random row split",
        "holdout_maturities": [float(v) for v in sorted(selected)],
        "holdout_instruments": int(len(ids)),
        "train_instruments": int(len(usable) - len(ids)),
    }


def cleaning_audit(raw: pd.DataFrame, valuation_date: date) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Validate, normalize, and audit every raw observation."""
    work = raw.copy()
    parsed_ts = pd.to_datetime(work["timestamp"], utc=True, errors="coerce")
    parsed_mat = pd.to_datetime(work["maturity_date"], errors="coerce")
    work["_timestamp_parsed"] = parsed_ts
    work["_maturity_parsed"] = parsed_mat
    duplicate_ids = work["instrument_id"].astype(str).duplicated(keep=False)
    keep_indices: set[int] = set()
    for instrument_id, group in work.groupby("instrument_id", sort=False):
        if len(group) == 1:
            keep_indices.add(int(group.index[0]))
            continue
        # Prefer a non-backup venue, then the freshest timestamp, then liquidity.
        candidates = group.copy()
        candidates["_priority"] = candidates["source"].ne("BACKUP_FEED").astype(int)
        candidates = candidates.sort_values(["_priority", "_timestamp_parsed", "liquidity_score"], ascending=[False, False, False])
        keep_indices.add(int(candidates.index[0]))

    records: list[dict[str, object]] = []
    for index, row in work.iterrows():
        action = "keep"
        reasons: list[str] = []
        q_raw = row.get("quote_value")
        bid_raw = row.get("bid")
        ask_raw = row.get("ask")
        unit = str(row.get("quote_unit", ""))
        typ = str(row.get("instrument_type", ""))
        q = float(q_raw) if _finite(q_raw) else np.nan
        bid = float(bid_raw) if _finite(bid_raw) else np.nan
        ask = float(ask_raw) if _finite(ask_raw) else np.nan
        scale = 1.0
        if unit == "PERCENT":
            reference = [abs(v) for v in (q, bid, ask) if np.isfinite(v)]
            if reference and max(reference) <= 0.1:
                scale = 100.0
                reasons.append("rate quote/bid/ask normalized from decimal fraction to percentage points")
            normalized_q = q * scale / 100.0 if np.isfinite(q) else np.nan
            normalized_bid = bid * scale / 100.0 if np.isfinite(bid) else np.nan
            normalized_ask = ask * scale / 100.0 if np.isfinite(ask) else np.nan
        elif unit == "PRICE_POINTS":
            reference = [abs(v) for v in (q, bid, ask) if np.isfinite(v)]
            if reference and max(reference) <= 5.0:
                scale = 100.0
                reasons.append("bond quote/bid/ask normalized from decimal fraction to price points")
            normalized_q = q * scale if np.isfinite(q) else np.nan
            normalized_bid = bid * scale if np.isfinite(bid) else np.nan
            normalized_ask = ask * scale if np.isfinite(ask) else np.nan
        else:
            normalized_q = normalized_bid = normalized_ask = np.nan
            reasons.append("unsupported quote unit")

        if np.isfinite(normalized_bid) and np.isfinite(normalized_ask) and normalized_bid > normalized_ask:
            normalized_bid, normalized_ask = normalized_ask, normalized_bid
            reasons.append("crossed bid/ask reordered")
        if not np.isfinite(normalized_q) and np.isfinite(normalized_bid) and np.isfinite(normalized_ask):
            normalized_q = (normalized_bid + normalized_ask) / 2.0
            reasons.append("missing quote replaced by bid/ask midpoint")

        hard_issues: list[str] = []
        if not str(row.get("obs_id", "")).strip() or not str(row.get("instrument_id", "")).strip():
            hard_issues.append("empty identifier")
        if typ not in EXPECTED_TYPES:
            hard_issues.append("unsupported instrument type")
        expected_quote = {"deposit": "simple_rate", "ois_swap": "par_rate", "bond": "clean_price"}.get(typ)
        expected_unit = {"deposit": "PERCENT", "ois_swap": "PERCENT", "bond": "PRICE_POINTS"}.get(typ)
        if expected_quote is not None and str(row.get("quote_type")) != expected_quote:
            hard_issues.append(f"quote_type does not match {typ}")
        if expected_unit is not None and str(row.get("quote_unit")) != expected_unit:
            hard_issues.append(f"quote_unit does not match {typ}")
        if not _finite(row.get("maturity_years")) or float(row["maturity_years"]) <= 0:
            hard_issues.append("non-positive maturity")
        if not _finite(row.get("payment_frequency")) or int(row["payment_frequency"]) <= 0:
            hard_issues.append("invalid payment frequency")
        if str(row.get("currency")) != "USD":
            hard_issues.append("currency is not USD")
        if str(row.get("day_count")) != "ACT/365F":
            hard_issues.append("unsupported day count")
        if not _finite(row.get("start_years")) or abs(float(row["start_years"])) > 1e-10:
            hard_issues.append("non-zero start_years")
        if not _finite(row.get("settlement_days")) or int(row["settlement_days"]) != 2:
            hard_issues.append("settlement lag is not two days")
        if not np.isfinite(normalized_bid) or not np.isfinite(normalized_ask) or normalized_bid > normalized_ask:
            hard_issues.append("invalid bid/ask")
        if typ == "bond" and (not _finite(row.get("coupon_rate")) or float(row["coupon_rate"]) < 0):
            hard_issues.append("invalid bond coupon")
        if typ == "bond" and (np.isfinite(normalized_bid) and normalized_bid <= 0 or np.isfinite(normalized_ask) and normalized_ask <= 0):
            hard_issues.append("bond price must be positive")
        if not pd.isna(row["_maturity_parsed"]):
            valuation_timestamp = pd.Timestamp(valuation_date)
            if row["_maturity_parsed"] <= valuation_timestamp:
                hard_issues.append("maturity_date is not after valuation date")
        if not _finite(row.get("liquidity_score")) or not 0 <= float(row["liquidity_score"]) <= 1:
            hard_issues.append("liquidity score outside [0, 1]")
        if not np.isfinite(normalized_q):
            hard_issues.append("no usable quote or valid bid/ask midpoint")
        if index in duplicate_ids.index[duplicate_ids].tolist() and index not in keep_indices:
            hard_issues.append("duplicate instrument_id; retained highest-priority observation")

        stale = True
        if not pd.isna(row["_timestamp_parsed"]):
            age_days = (pd.Timestamp(valuation_date, tz="UTC") - row["_timestamp_parsed"]).total_seconds() / 86400.0
            stale = age_days > 2.0
            if stale:
                reasons.append(f"timestamp is {age_days:.1f} days before valuation date")
        else:
            hard_issues.append("unparseable timestamp")
        if pd.isna(row["_maturity_parsed"]):
            hard_issues.append("unparseable maturity_date")

        liquidity = float(row["liquidity_score"]) if _finite(row.get("liquidity_score")) else 0.0
        low_liquidity = liquidity < 0.25
        if low_liquidity:
            reasons.append("low liquidity score downweighted")
        if hard_issues:
            action = "exclude"
            reasons = hard_issues + reasons
        elif reasons:
            # Correct is reserved for deterministic transformations; a stale or
            # illiquid but otherwise valid quote is downweighted instead.
            deterministic = any("normalized" in r or "reordered" in r or "midpoint" in r for r in reasons)
            action = "correct" if deterministic else ("downweight" if stale or low_liquidity else "keep")
        elif stale or low_liquidity:
            action = "downweight"

        # Base quality weight: liquidity and spread enter before robust residual
        # treatment, while stale observations retain only a small influence.
        width = abs(normalized_ask - normalized_bid) if np.isfinite(normalized_bid) and np.isfinite(normalized_ask) else np.nan
        spread_quality = 1.0
        if np.isfinite(width) and width > 0:
            spread_quality = 1.0 / (1.0 + 5.0 * width / (0.0002 if typ in RATE_TYPES else 0.05))
        quality = (0.05 + 0.95 * liquidity * liquidity) * spread_quality * (0.35 if stale else 1.0)
        if low_liquidity:
            quality *= 0.35
        if action == "exclude":
            quality = 0.0
        records.append(
            {
                **{col: row[col] for col in raw.columns},
                "normalized_quote": float(normalized_q) if np.isfinite(normalized_q) else np.nan,
                "normalized_bid": float(normalized_bid) if np.isfinite(normalized_bid) else np.nan,
                "normalized_ask": float(normalized_ask) if np.isfinite(normalized_ask) else np.nan,
                "action": action,
                "weight": float(quality),
                "reason": "; ".join(reasons) if reasons else "validated against documented schema and conventions",
                "stale": bool(stale),
                "unit_scale": float(scale),
            }
        )

    cleaned = pd.DataFrame(records)
    # Same-maturity rate outliers are excluded only when there are at least
    # three independent observations; this prevents a single bond from being
    # rejected merely because it has no same-maturity peer.
    peer_exclusions = 0
    for (typ, maturity), group in cleaned.loc[(cleaned["action"] != "exclude") & cleaned["normalized_quote"].notna()].groupby(["instrument_type", "maturity_years"]):
        if typ not in RATE_TYPES or len(group) < 3:
            continue
        values = group["normalized_quote"].astype(float).to_numpy()
        median = float(np.median(values))
        half_spread = float(np.median(np.abs(group["normalized_ask"].astype(float) - group["normalized_bid"].astype(float))) / 2.0)
        threshold = max(0.0010, 10.0 * half_spread)
        bad = group.index[np.abs(values - median) > threshold]
        for bad_index in bad:
            cleaned.loc[bad_index, "action"] = "exclude"
            cleaned.loc[bad_index, "weight"] = 0.0
            prior = str(cleaned.loc[bad_index, "reason"])
            cleaned.loc[bad_index, "reason"] = prior + "; gross same-maturity quote outlier excluded, not deterministically correctable"
            peer_exclusions += 1

    audit_cols = ["obs_id", "instrument_id", "action", "normalized_quote", "weight", "reason"]
    audit = cleaned.loc[:, audit_cols].copy()
    stats = {
        "input_rows": int(len(raw)),
        "usable_rows": int((cleaned["action"] != "exclude").sum()),
        "excluded_rows": int((cleaned["action"] == "exclude").sum()),
        "actions": {str(k): int(v) for k, v in cleaned["action"].value_counts().to_dict().items()},
        "unit_corrections": int((cleaned["unit_scale"] != 1.0).sum()),
        "peer_outlier_exclusions": int(peer_exclusions),
        "duplicate_instrument_ids": int(raw["instrument_id"].duplicated(keep=False).sum()),
        "missing_quote_values": int(raw["quote_value"].isna().sum()),
        "crossed_bid_ask": int((raw["bid"] > raw["ask"]).sum()),
        "stale_rows": int(cleaned["stale"].sum()),
        "low_liquidity_rows": int((raw["liquidity_score"] < 0.25).sum()),
    }
    return cleaned, audit, stats
