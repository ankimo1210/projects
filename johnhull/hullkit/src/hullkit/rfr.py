"""Risk-free-rate conventions, exact daily compounding and curve layers.

The exact discrete coupon is the source of truth.  Continuous compounding is
provided only as an approximation for comparison.  The implementation is
index-agnostic (for example SOFR or TONA) and keeps forecasting, discounting,
policy jumps and collateral currency as separate scenario inputs.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
FixingSource = Mapping[date, float] | Callable[[date], float]


@dataclass(frozen=True)
class BusinessCalendar:
    """Weekend/holiday calendar with preceding and business-day shifts."""

    holidays: tuple[date, ...] = ()
    weekend: tuple[int, ...] = (5, 6)

    def validate(self) -> None:
        """Reject duplicate holidays and malformed weekend definitions."""
        if len(set(self.holidays)) != len(self.holidays):
            raise ValueError("holidays must be unique")
        if not self.weekend or len(set(self.weekend)) != len(self.weekend):
            raise ValueError("weekend must contain unique weekday numbers")
        if any(day < 0 or day > 6 for day in self.weekend):
            raise ValueError("weekend weekdays must lie in [0, 6]")

    def is_business_day(self, day: date) -> bool:
        """True when the day is neither a weekend day nor a holiday."""
        self.validate()
        return day.weekday() not in self.weekend and day not in self.holidays

    def preceding(self, day: date) -> date:
        """Return ``day`` if valid, otherwise the preceding business day."""

        current = day
        while not self.is_business_day(current):
            current -= timedelta(days=1)
        return current

    def shift(self, day: date, business_days: int) -> date:
        """Shift a business date by a signed number of business days."""

        if not self.is_business_day(day):
            raise ValueError("business-day shifts require a business start date")
        current = day
        direction = 1 if business_days >= 0 else -1
        remaining = abs(int(business_days))
        while remaining:
            current += timedelta(days=direction)
            if self.is_business_day(current):
                remaining -= 1
        return current

    def business_dates(self, start: date, end: date) -> tuple[date, ...]:
        """Business dates in the half-open interval ``[start, end)``."""

        if end <= start:
            raise ValueError("end must be after start")
        dates: list[date] = []
        current = start
        while current < end:
            if self.is_business_day(current):
                dates.append(current)
            current += timedelta(days=1)
        return tuple(dates)


@dataclass(frozen=True)
class RFRConvention:
    """Compounded-in-arrears observation convention."""

    day_count_basis: int = 360
    lookback_business_days: int = 0
    lockout_business_days: int = 0
    observation_shift: bool = False

    def validate(self) -> None:
        """Reject a non-positive day-count basis and negative lookback/lockout."""
        if self.day_count_basis <= 0:
            raise ValueError("day_count_basis must be positive")
        if self.lookback_business_days < 0 or self.lockout_business_days < 0:
            raise ValueError("lookback and lockout cannot be negative")


@dataclass(frozen=True)
class DailyAccrual:
    """One exact factor ``1 + fixing * day_count / basis``."""

    accrual_start: date
    accrual_end: date
    observation_date: date
    day_count: int
    fixing: float


@dataclass(frozen=True)
class CompoundedRFR:
    """Exact accumulation factor and annualized simple rate."""

    accumulation_factor: float
    annualized_rate: float
    accrual_year_fraction: float
    observations: tuple[DailyAccrual, ...]


def _fixing(source: FixingSource, day: date) -> float:
    try:
        value = source(day) if callable(source) else source[day]
    except KeyError as exc:
        raise ValueError(f"missing RFR fixing for {day.isoformat()}") from exc
    value = float(value)
    if not np.isfinite(value):
        raise ValueError(f"RFR fixing for {day.isoformat()} is not finite")
    return value


def daily_accrual_schedule(
    start: date,
    end: date,
    fixings: FixingSource,
    *,
    calendar: BusinessCalendar = BusinessCalendar(),
    convention: RFRConvention = RFRConvention(),
) -> tuple[DailyAccrual, ...]:
    """Build exact daily observations including weekends and holidays.

    A business-day fixing accrues until the next business date, so Friday's
    observation normally receives three calendar days.  A lookback changes the
    fixing date only; with observation shift, the shifted observation interval
    also supplies the day weight.  Lockout freezes the last ``n`` observations
    at the fixing immediately before the lockout window.
    """

    calendar.validate()
    convention.validate()
    if not calendar.is_business_day(start) or not calendar.is_business_day(end):
        raise ValueError("RFR accrual start/end must be business dates")
    if end <= start:
        raise ValueError("end must be after start")
    accrual_starts = calendar.business_dates(start, end)
    if not accrual_starts:
        raise ValueError("accrual period has no business observations")
    accrual_ends = (*accrual_starts[1:], end)
    observations = tuple(
        calendar.shift(day, -convention.lookback_business_days) for day in accrual_starts
    )
    if convention.lockout_business_days >= len(observations):
        raise ValueError("lockout must leave at least one independently observed fixing")
    if convention.lockout_business_days:
        freeze_index = len(observations) - convention.lockout_business_days - 1
        observations = (
            *observations[: freeze_index + 1],
            *((observations[freeze_index],) * convention.lockout_business_days),
        )

    rows: list[DailyAccrual] = []
    for index, (accrual_start, accrual_end, observation) in enumerate(
        zip(accrual_starts, accrual_ends, observations, strict=True)
    ):
        if convention.observation_shift:
            # Preserve the shifted observation interval.  Under lockout the
            # frozen rate remains, but the original shifted day weight is used.
            shifted_start = calendar.shift(accrual_start, -convention.lookback_business_days)
            shifted_end = calendar.shift(accrual_end, -convention.lookback_business_days)
            day_count = (shifted_end - shifted_start).days
        else:
            day_count = (accrual_end - accrual_start).days
        if day_count <= 0:
            raise ValueError(f"non-positive daily accrual at index {index}")
        rows.append(
            DailyAccrual(
                accrual_start=accrual_start,
                accrual_end=accrual_end,
                observation_date=observation,
                day_count=day_count,
                fixing=_fixing(fixings, observation),
            )
        )
    return tuple(rows)


def compounded_rfr(
    start: date,
    end: date,
    fixings: FixingSource,
    *,
    calendar: BusinessCalendar = BusinessCalendar(),
    convention: RFRConvention = RFRConvention(),
) -> CompoundedRFR:
    r"""Compute the exact annualized RFR.

    .. math:: R=\frac{\prod_i(1+r_i d_i/D)-1}{\sum_i d_i/D}.
    """

    rows = daily_accrual_schedule(
        start,
        end,
        fixings,
        calendar=calendar,
        convention=convention,
    )
    factors = [1.0 + row.fixing * row.day_count / convention.day_count_basis for row in rows]
    if any(factor <= 0.0 for factor in factors):
        raise ValueError("a daily fixing makes the accumulation factor non-positive")
    accumulation = float(np.prod(factors))
    year_fraction = float(sum(row.day_count for row in rows) / convention.day_count_basis)
    return CompoundedRFR(
        accumulation_factor=accumulation,
        annualized_rate=(accumulation - 1.0) / year_fraction,
        accrual_year_fraction=year_fraction,
        observations=rows,
    )


def rfr_coupon(
    notional: float,
    accrual_start: date,
    accrual_end: date,
    fixings: FixingSource,
    *,
    determination: str = "in_arrears",
    advance_observation_period: tuple[date, date] | None = None,
    calendar: BusinessCalendar = BusinessCalendar(),
    convention: RFRConvention = RFRConvention(),
) -> float:
    """Pay a compounded RFR coupon determined in advance or in arrears.

    In-advance coupons use the explicitly supplied prior observation period but
    pay on the current accrual period.  This avoids silently pretending that a
    future compounded-in-arrears rate was known at the period start.
    """

    if not np.isfinite(notional):
        raise ValueError("notional must be finite")
    accrual_days = (accrual_end - accrual_start).days
    if accrual_days <= 0:
        raise ValueError("accrual_end must be after accrual_start")
    if determination == "in_arrears":
        observation_start, observation_end = accrual_start, accrual_end
    elif determination == "in_advance":
        if advance_observation_period is None:
            raise ValueError("in_advance requires an explicit prior observation period")
        observation_start, observation_end = advance_observation_period
        if observation_end > accrual_start:
            raise ValueError("in-advance observation period must finish by accrual start")
    else:
        raise ValueError("determination must be in_arrears or in_advance")
    rate = compounded_rfr(
        observation_start,
        observation_end,
        fixings,
        calendar=calendar,
        convention=convention,
    ).annualized_rate
    return float(notional * rate * accrual_days / convention.day_count_basis)


def continuous_compounding_approximation(observations: Sequence[DailyAccrual], basis: int) -> float:
    """Annualized rate from ``exp(sum(r_i d_i/D))`` for limit comparisons."""

    if not observations or basis <= 0:
        raise ValueError("observations must be non-empty and basis positive")
    year_fraction = sum(row.day_count for row in observations) / basis
    exponent = sum(row.fixing * row.day_count / basis for row in observations)
    return float(np.expm1(exponent) / year_fraction)


@dataclass(frozen=True)
class RfrCurve:
    """Zero-rate interpolated OIS/RFR curve (for example SOFR or TONA)."""

    name: str
    valuation_date: date
    pillar_dates: tuple[date, ...]
    discount_factors: tuple[float, ...]
    currency: str

    def _validated_nodes(self) -> tuple[FloatArray, FloatArray]:
        if (
            not self.name
            or not self.currency
            or len(self.pillar_dates) != len(self.discount_factors)
        ):
            raise ValueError("curve label/currency/nodes are invalid")
        if not self.pillar_dates or tuple(sorted(set(self.pillar_dates))) != self.pillar_dates:
            raise ValueError("pillar_dates must be unique and increasing")
        if self.pillar_dates[0] <= self.valuation_date:
            raise ValueError("pillar_dates must follow valuation_date")
        times = np.asarray([(day - self.valuation_date).days / 365.0 for day in self.pillar_dates])
        discounts = np.asarray(self.discount_factors, dtype=float)
        if np.any(~np.isfinite(discounts)) or np.any(discounts <= 0.0):
            raise ValueError("discount factors must be finite and positive")
        return times, discounts

    def discount(self, day: date) -> float:
        """Linear zero interpolation with flat continuously compounded extrapolation."""

        times, discounts = self._validated_nodes()
        target = (day - self.valuation_date).days / 365.0
        if target < 0.0:
            raise ValueError("cannot discount before valuation_date")
        if target == 0.0:
            return 1.0
        zeros = -np.log(discounts) / times
        zero = float(np.interp(target, times, zeros))
        return float(np.exp(-zero * target))

    def simple_forward(self, start: date, end: date, *, basis: int = 360) -> float:
        """Simple money-market forward rate between two dates from discount factors."""
        if end <= start or basis <= 0:
            raise ValueError("forward interval/basis is invalid")
        year_fraction = (end - start).days / basis
        return float((self.discount(start) / self.discount(end) - 1.0) / year_fraction)


@dataclass(frozen=True)
class MultiCurveScenario:
    """Separate forecast/discount curves and collateral currency."""

    forecast_curve: RfrCurve
    discount_curve: RfrCurve
    collateral_currency: str

    def validate(self) -> None:
        """Check both curves and require discounting in the collateral currency."""
        self.forecast_curve._validated_nodes()
        self.discount_curve._validated_nodes()
        if not self.collateral_currency:
            raise ValueError("collateral_currency is required")
        if self.discount_curve.currency != self.collateral_currency:
            raise ValueError("discount curve currency must match collateral currency")


def curve_basis_spread(
    first: RfrCurve,
    second: RfrCurve,
    start: date,
    end: date,
    *,
    basis: int = 360,
) -> float:
    """Simple-forward spread ``first - second`` on a shared interval."""

    return first.simple_forward(start, end, basis=basis) - second.simple_forward(
        start, end, basis=basis
    )


def futures_forward_from_covariance(
    forward_rate: float,
    rate_discount_covariance: float,
    expected_discount_factor: float,
) -> tuple[float, float]:
    r"""Convert a forward to a futures rate using the covariance identity.

    With ``F = E[D R] / E[D]`` and futures ``E[R]``, the adjustment is
    ``-Cov(D,R)/E[D]``.  In the usual positive-rate setting this covariance is
    negative, so the futures rate exceeds the forward.
    """

    values = (forward_rate, rate_discount_covariance, expected_discount_factor)
    if any(not np.isfinite(value) for value in values) or expected_discount_factor <= 0.0:
        raise ValueError("forward/covariance/discount inputs are invalid")
    adjustment = -rate_discount_covariance / expected_discount_factor
    return float(forward_rate + adjustment), float(adjustment)


@dataclass(frozen=True)
class PolicyJump:
    """Deterministic scheduled change in the overnight policy-rate path."""

    effective_date: date
    rate_change: float
    label: str = "policy"


def policy_jump_path(
    observation_dates: Sequence[date],
    base_rate: float,
    jumps: Sequence[PolicyJump],
) -> FloatArray:
    """Apply scheduled jumps cumulatively without mixing them into curve basis."""

    if not observation_dates or tuple(sorted(observation_dates)) != tuple(observation_dates):
        raise ValueError("observation_dates must be non-empty and ordered")
    if not np.isfinite(base_rate):
        raise ValueError("base_rate must be finite")
    if any(not jump.label or not np.isfinite(jump.rate_change) for jump in jumps):
        raise ValueError("policy jumps require labels and finite changes")
    ordered = sorted(jumps, key=lambda jump: jump.effective_date)
    return np.asarray(
        [
            base_rate + sum(jump.rate_change for jump in ordered if jump.effective_date <= day)
            for day in observation_dates
        ]
    )


def collateralized_present_value(
    cashflows: ArrayLike,
    payment_dates: Sequence[date],
    scenario: MultiCurveScenario,
) -> float:
    """Discount deterministic cash flows under the named collateral curve."""

    scenario.validate()
    values = np.asarray(cashflows, dtype=float)
    if values.ndim != 1 or values.size != len(payment_dates) or np.any(~np.isfinite(values)):
        raise ValueError("cashflows and payment_dates must be finite and aligned")
    return float(
        sum(
            cashflow * scenario.discount_curve.discount(day)
            for cashflow, day in zip(values, payment_dates, strict=True)
        )
    )
