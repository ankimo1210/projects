"""CPI conventions, deterministic seasonality, and inflation-swap cash flows.

Observed fixings, forward-index construction, and discounted cash flows remain
separate so that model convexity enters through explicit expected ratios.
"""

from __future__ import annotations

import calendar
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

import numpy as np

from .rates import discount_factor

CPISource = Mapping[date, float]
ZeroCurve = tuple[Sequence[float], Sequence[float]]


def _month_start(day: date) -> date:
    return day.replace(day=1)


def _shift_month(day: date, months: int) -> date:
    month_index = day.year * 12 + day.month - 1 + months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def _validated_fixings(fixings: CPISource) -> None:
    if not fixings:
        raise ValueError("CPI fixings cannot be empty")
    for month, value in fixings.items():
        if month.day != 1:
            raise ValueError("monthly CPI keys must be first-of-month dates")
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError("monthly CPI values must be positive and finite")


@dataclass(frozen=True)
class CPIObservationConvention:
    """Lag and interpolation rule used to turn monthly CPI into a daily index."""

    lag_months: int = 3
    interpolation: Literal["linear", "flat"] = "linear"

    def validate(self) -> None:
        """Reject negative lags and unsupported interpolation names."""
        if self.lag_months < 0:
            raise ValueError("lag_months cannot be negative")
        if self.interpolation not in {"linear", "flat"}:
            raise ValueError("interpolation must be 'linear' or 'flat'")


@dataclass(frozen=True)
class MonthlySeasonality:
    """Twelve deterministic monthly log factors whose annual sum is zero."""

    log_factors: tuple[float, ...]

    def validate(self) -> None:
        """Require twelve finite factors normalized to an annual product of one."""
        if len(self.log_factors) != 12:
            raise ValueError("seasonality requires exactly twelve monthly log factors")
        values = np.asarray(self.log_factors, dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError("seasonality log factors must be finite")
        if abs(float(values.sum())) > 1e-12:
            raise ValueError("seasonality log factors must sum to zero")

    def factor(self, month: int) -> float:
        """Return the multiplicative factor for a calendar month numbered 1 to 12."""
        self.validate()
        if month < 1 or month > 12:
            raise ValueError("month must lie in [1, 12]")
        return float(np.exp(self.log_factors[month - 1]))

    def multiplier(self, start: date, end: date) -> float:
        """Return accumulated seasonality across complete calendar-month steps."""
        self.validate()
        start_index = start.year * 12 + start.month - 1
        end_index = end.year * 12 + end.month - 1
        if end_index < start_index:
            return 1.0 / self.multiplier(end, start)
        total = 0.0
        for month_index in range(start_index + 1, end_index + 1):
            total += self.log_factors[month_index % 12]
        return float(np.exp(total))


@dataclass(frozen=True)
class ZeroCouponInflationCurve:
    """Annualized zero-inflation curve with deterministic monthly seasonality."""

    base_date: date
    base_index: float
    maturities: tuple[float, ...]
    zero_rates: tuple[float, ...]
    seasonality: MonthlySeasonality

    def validate(self) -> None:
        """Validate the base index, pillar grid, rates, and seasonality."""
        if not np.isfinite(self.base_index) or self.base_index <= 0.0:
            raise ValueError("base_index must be positive and finite")
        maturities = np.asarray(self.maturities, dtype=float)
        rates = np.asarray(self.zero_rates, dtype=float)
        if len(maturities) == 0 or len(maturities) != len(rates):
            raise ValueError("maturities and zero_rates must have equal non-zero length")
        if not np.all(np.isfinite(maturities)) or not np.all(np.isfinite(rates)):
            raise ValueError("inflation curve pillars must be finite")
        if np.any(maturities <= 0.0) or np.any(np.diff(maturities) <= 0.0):
            raise ValueError("maturities must be positive and strictly increasing")
        if np.any(rates <= -1.0):
            raise ValueError("zero inflation rates must exceed -100%")
        self.seasonality.validate()

    def zero_rate(self, maturity: float) -> float:
        """Interpolate a zero-inflation rate, flat outside the pillar range."""
        self.validate()
        if not np.isfinite(maturity) or maturity < 0.0:
            raise ValueError("maturity must be non-negative and finite")
        return float(np.interp(maturity, self.maturities, self.zero_rates))


def monthly_cpi_value(month: date, fixings: CPISource) -> float:
    """Read a positive monthly CPI fixing keyed by the first day of its month."""
    _validated_fixings(fixings)
    if month.day != 1:
        raise ValueError("month must be a first-of-month date")
    try:
        return float(fixings[month])
    except KeyError as exc:
        raise ValueError(f"missing CPI fixing for {month.isoformat()}") from exc


def interpolated_cpi(
    day: date,
    fixings: CPISource,
    convention: CPIObservationConvention = CPIObservationConvention(),
) -> float:
    """Return lagged CPI using flat or calendar-day linear interpolation.

    Linear interpolation blends the lagged reference month and its successor
    with weight ``(day-of-month - 1) / days-in-payment-month``.
    """
    convention.validate()
    reference_month = _month_start(_shift_month(day, -convention.lag_months))
    first = monthly_cpi_value(reference_month, fixings)
    if convention.interpolation == "flat":
        return first
    second = monthly_cpi_value(_month_start(_shift_month(reference_month, 1)), fixings)
    weight = (day.day - 1) / calendar.monthrange(day.year, day.month)[1]
    return float((1.0 - weight) * first + weight * second)


def cpi_observation(
    day: date,
    known_fixings: CPISource,
    forecast_fixings: CPISource,
    convention: CPIObservationConvention = CPIObservationConvention(),
) -> float:
    """Use known CPI first and explicit forecast months only where needed."""
    _validated_fixings(known_fixings)
    _validated_fixings(forecast_fixings)
    if set(known_fixings).intersection(forecast_fixings):
        raise ValueError("known and forecast CPI sources must not overlap")
    return interpolated_cpi(day, {**forecast_fixings, **known_fixings}, convention)


def apply_cpi_rebase(value: float, bridge_factor: float) -> float:
    """Convert an index level to a rebased series using a positive bridge factor."""
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError("CPI value must be positive and finite")
    if not np.isfinite(bridge_factor) or bridge_factor <= 0.0:
        raise ValueError("bridge_factor must be positive and finite")
    return float(value * bridge_factor)


def seasonal_forward_index(day: date, curve: ZeroCouponInflationCurve) -> float:
    """Forecast CPI from zero inflation and deterministic month factors."""
    curve.validate()
    if day < curve.base_date:
        raise ValueError("forward CPI date cannot precede curve base_date")
    maturity = (day - curve.base_date).days / 365.25
    if maturity == 0.0:
        return float(curve.base_index)
    trend = (1.0 + curve.zero_rate(maturity)) ** maturity
    return float(curve.base_index * trend * curve.seasonality.multiplier(curve.base_date, day))


def zcis_cashflow(
    notional: float,
    start_index: float,
    end_index: float,
    fixed_rate: float,
    accrual_years: float,
) -> float:
    """Return the receive-inflation ZCIS terminal cash flow before discounting."""
    values = (notional, start_index, end_index, fixed_rate, accrual_years)
    if not all(np.isfinite(value) for value in values):
        raise ValueError("ZCIS inputs must be finite")
    if notional < 0.0 or start_index <= 0.0 or end_index <= 0.0:
        raise ValueError("notional cannot be negative and index levels must be positive")
    if fixed_rate <= -1.0 or accrual_years <= 0.0:
        raise ValueError("fixed_rate must exceed -100% and accrual_years must be positive")
    fixed_log_growth = accrual_years * np.log1p(fixed_rate)
    log_difference = np.log(end_index / start_index) - fixed_log_growth
    return float(notional * np.exp(fixed_log_growth) * np.expm1(log_difference))


def zcis_npv(
    notional: float,
    start_index: float,
    expected_end_index: float,
    fixed_rate: float,
    accrual_years: float,
    payment_time: float,
    nominal_curve: ZeroCurve,
    *,
    pay_fixed: bool = True,
) -> float:
    """Discount a ZCIS using a nominal curve and explicit expected end index."""
    cashflow = zcis_cashflow(
        notional, start_index, expected_end_index, fixed_rate, accrual_years
    )
    direction = 1.0 if pay_fixed else -1.0
    return float(direction * discount_factor(payment_time, nominal_curve) * cashflow)


def zcis_par_rate(start_index: float, expected_end_index: float, accrual_years: float) -> float:
    """Return the annualized fixed rate that makes a ZC inflation swap par."""
    values = (start_index, expected_end_index, accrual_years)
    if not all(np.isfinite(value) for value in values) or any(value <= 0.0 for value in values):
        raise ValueError("index levels and accrual_years must be positive and finite")
    return float(np.expm1(np.log(expected_end_index / start_index) / accrual_years))


def bootstrap_zc_inflation_curve(
    base_date: date,
    base_index: float,
    maturities: Sequence[float],
    par_rates: Sequence[float],
    *,
    seasonality: MonthlySeasonality = MonthlySeasonality((0.0,) * 12),
) -> ZeroCouponInflationCurve:
    """Bootstrap independent ZCIS quotes into zero rates on the quote pillars."""
    curve = ZeroCouponInflationCurve(
        base_date,
        float(base_index),
        tuple(float(value) for value in maturities),
        tuple(float(value) for value in par_rates),
        seasonality,
    )
    curve.validate()
    return curve


def yoy_rate(start_index: float, end_index: float) -> float:
    """Return a year-on-year realization from two positive index levels."""
    if not np.isfinite(start_index) or not np.isfinite(end_index):
        raise ValueError("YoY index levels must be finite")
    if start_index <= 0.0 or end_index <= 0.0:
        raise ValueError("YoY index levels must be positive")
    return float(end_index / start_index - 1.0)


def yoy_swap_npv(
    notional: float,
    expected_index_ratios: Sequence[float],
    payment_times: Sequence[float],
    fixed_rate: float,
    nominal_curve: ZeroCurve,
    *,
    pay_fixed: bool = True,
) -> float:
    """Value YoY coupons from expected ratios under each payment measure."""
    ratios = np.asarray(expected_index_ratios, dtype=float)
    times = np.asarray(payment_times, dtype=float)
    if ratios.ndim != 1 or times.ndim != 1 or len(ratios) == 0 or len(ratios) != len(times):
        raise ValueError("expected_index_ratios and payment_times need equal non-zero length")
    if not np.all(np.isfinite(ratios)) or np.any(ratios <= 0.0):
        raise ValueError("expected index ratios must be positive and finite")
    if not np.all(np.isfinite(times)) or np.any(times < 0.0):
        raise ValueError("payment_times must be non-negative and finite")
    if not np.isfinite(notional) or notional < 0.0 or not np.isfinite(fixed_rate):
        raise ValueError("notional must be non-negative and swap rates must be finite")
    discounts = np.asarray([discount_factor(time, nominal_curve) for time in times])
    receive_inflation = float(notional * np.sum(discounts * (ratios - 1.0 - fixed_rate)))
    return receive_inflation if pay_fixed else -receive_inflation
