"""Japanese inflation-linked government bond conventions and valuation.

Monthly inputs represent Japan CPI excluding fresh food.  The implementation
keeps the official reference-index rounding separate from index-ratio rounding
and applies the post-2013 principal guarantee to redemption only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
from scipy.optimize import brentq
from scipy.special import ndtr

from .inflation import monthly_cpi_value
from .jarrow_yildirim import (
    JarrowYildirimParams,
    jy_cpi_total_variance,
    jy_payment_forward_cpi,
    simulate_jy_forward_levels,
)
from .rates import discount_factor, forward_discount

CPISource = Mapping[date, float]
ZeroCurve = tuple[Sequence[float], Sequence[float]]


def _month_start(day: date, shift: int = 0) -> date:
    month_index = day.year * 12 + day.month - 1 + shift
    year, zero_based_month = divmod(month_index, 12)
    return date(year, zero_based_month + 1, 1)


def _round_half_up(value: float, decimals: int) -> float:
    quantum = Decimal(1).scaleb(-decimals)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class JGBITerms:
    """Contract terms needed for JGBi indexation and semiannual cash flows."""

    issue_date: date
    maturity_date: date
    coupon_dates: tuple[date, ...]
    coupon_rate: float
    face_value: float
    base_reference_date: date
    principal_floor: bool
    reference_index_decimals: int = 3
    index_ratio_decimals: int = 5

    def validate(self) -> None:
        """Reject inconsistent dates, coupon grids, rates, face values, and rounding."""
        if self.maturity_date <= self.issue_date:
            raise ValueError("maturity_date must be after issue_date")
        if not self.coupon_dates or tuple(sorted(self.coupon_dates)) != self.coupon_dates:
            raise ValueError("coupon_dates must be non-empty and strictly ordered")
        if len(set(self.coupon_dates)) != len(self.coupon_dates):
            raise ValueError("coupon_dates must not contain duplicates")
        if self.coupon_dates[-1] != self.maturity_date:
            raise ValueError("the final coupon date must equal maturity_date")
        if self.coupon_dates[0] <= self.issue_date:
            raise ValueError("coupon dates must follow issue_date")
        if not np.isfinite(self.coupon_rate) or self.coupon_rate < 0.0:
            raise ValueError("coupon_rate must be non-negative and finite")
        if not np.isfinite(self.face_value) or self.face_value <= 0.0:
            raise ValueError("face_value must be positive and finite")
        if self.reference_index_decimals < 0 or self.index_ratio_decimals < 0:
            raise ValueError("rounding decimals cannot be negative")


@dataclass(frozen=True)
class JGBICashflow:
    """One inflation-adjusted JGBi coupon and optional redemption payment."""

    payment_date: date
    index_ratio: float
    coupon: float
    principal: float

    @property
    def total(self) -> float:
        """Return coupon plus principal paid on the cash-flow date."""
        return self.coupon + self.principal


@dataclass(frozen=True)
class JGBIFloorMonteCarlo:
    """Monte Carlo value and standard error for the JGBi redemption floor."""

    value: float
    standard_error: float


@dataclass(frozen=True)
class JGBIFloorRisk:
    """JGBi floor value, CPI-level delta, and CPI-volatility vega."""

    value: float
    cpi_delta: float
    inflation_vega: float


def jgbi_reference_index(
    day: date,
    monthly_cpi: CPISource,
    *,
    decimals: int = 3,
) -> float:
    """Compute the three-month-lagged JGBi reference index around the tenth.

    The tenth of month ``m`` uses CPI for ``m-3``. Other calendar days are
    linearly interpolated between adjacent tenth-day reference indices, then
    rounded once to the requested number of decimals.
    """
    if decimals < 0:
        raise ValueError("decimals cannot be negative")
    current_tenth = date(day.year, day.month, 10)
    if day == current_tenth:
        value = monthly_cpi_value(_month_start(day, -3), monthly_cpi)
    elif day > current_tenth:
        next_month = _month_start(day, 1)
        next_tenth = date(next_month.year, next_month.month, 10)
        start_value = monthly_cpi_value(_month_start(day, -3), monthly_cpi)
        end_value = monthly_cpi_value(_month_start(day, -2), monthly_cpi)
        weight = (day - current_tenth).days / (next_tenth - current_tenth).days
        value = (1.0 - weight) * start_value + weight * end_value
    else:
        previous_month = _month_start(day, -1)
        previous_tenth = date(previous_month.year, previous_month.month, 10)
        start_value = monthly_cpi_value(_month_start(day, -4), monthly_cpi)
        end_value = monthly_cpi_value(_month_start(day, -3), monthly_cpi)
        weight = (day - previous_tenth).days / (current_tenth - previous_tenth).days
        value = (1.0 - weight) * start_value + weight * end_value
    return _round_half_up(value, decimals)


def jgbi_indexation_coefficient(day: date, terms: JGBITerms, monthly_cpi: CPISource) -> float:
    """Return the rounded reference-index ratio to the explicit bond base date."""
    terms.validate()
    reference = jgbi_reference_index(
        day, monthly_cpi, decimals=terms.reference_index_decimals
    )
    base = jgbi_reference_index(
        terms.base_reference_date,
        monthly_cpi,
        decimals=terms.reference_index_decimals,
    )
    return _round_half_up(reference / base, terms.index_ratio_decimals)


def jgbi_cashflows(terms: JGBITerms, monthly_cpi: CPISource) -> tuple[JGBICashflow, ...]:
    """Build indexed coupons and redemption, flooring principal only at maturity."""
    terms.validate()
    rows: list[JGBICashflow] = []
    for payment_date in terms.coupon_dates:
        ratio = jgbi_indexation_coefficient(payment_date, terms, monthly_cpi)
        coupon = terms.face_value * ratio * terms.coupon_rate / 2.0
        principal = 0.0
        if payment_date == terms.maturity_date:
            redemption_ratio = max(ratio, 1.0) if terms.principal_floor else ratio
            principal = terms.face_value * redemption_ratio
        rows.append(JGBICashflow(payment_date, ratio, coupon, principal))
    return tuple(rows)


def jgbi_accrued_interest(settlement: date, terms: JGBITerms, monthly_cpi: CPISource) -> float:
    """Return nominal indexed accrued interest using an actual coupon-period fraction."""
    terms.validate()
    if settlement < terms.issue_date or settlement >= terms.maturity_date:
        raise ValueError("settlement must lie from issue_date up to but excluding maturity")
    if settlement in terms.coupon_dates:
        return 0.0
    previous_dates = [day for day in terms.coupon_dates if day < settlement]
    previous = previous_dates[-1] if previous_dates else terms.issue_date
    next_payment = next(day for day in terms.coupon_dates if day > settlement)
    fraction = (settlement - previous).days / (next_payment - previous).days
    ratio = jgbi_indexation_coefficient(settlement, terms, monthly_cpi)
    return float(terms.face_value * ratio * terms.coupon_rate / 2.0 * fraction)


def _real_accrued_price(settlement: date, terms: JGBITerms) -> float:
    if settlement in terms.coupon_dates:
        return 0.0
    previous_dates = [day for day in terms.coupon_dates if day < settlement]
    previous = previous_dates[-1] if previous_dates else terms.issue_date
    next_payment = next(day for day in terms.coupon_dates if day > settlement)
    fraction = (settlement - previous).days / (next_payment - previous).days
    return 100.0 * terms.coupon_rate / 2.0 * fraction


def jgbi_real_clean_price(real_yield: float, settlement: date, terms: JGBITerms) -> float:
    """Return unindexed clean price per 100 using semiannual yield compounding."""
    terms.validate()
    if settlement < terms.issue_date or settlement >= terms.maturity_date:
        raise ValueError("settlement must lie from issue_date up to but excluding maturity")
    if not np.isfinite(real_yield) or real_yield <= -2.0:
        raise ValueError("semiannual-compounded real_yield must exceed -200%")
    dirty = 0.0
    for payment_date in terms.coupon_dates:
        if payment_date <= settlement:
            continue
        years = (payment_date - settlement).days / 365.25
        cashflow = 100.0 * terms.coupon_rate / 2.0
        if payment_date == terms.maturity_date:
            cashflow += 100.0
        dirty += cashflow * (1.0 + real_yield / 2.0) ** (-2.0 * years)
    return float(dirty - _real_accrued_price(settlement, terms))


def jgbi_nominal_settlement_amount(
    real_clean_price: float,
    settlement: date,
    terms: JGBITerms,
    monthly_cpi: CPISource,
) -> float:
    """Convert a real clean quote per 100 into indexed nominal settlement amount."""
    terms.validate()
    if not np.isfinite(real_clean_price) or real_clean_price < 0.0:
        raise ValueError("real_clean_price must be non-negative and finite")
    real_dirty_price = real_clean_price + _real_accrued_price(settlement, terms)
    ratio = jgbi_indexation_coefficient(settlement, terms, monthly_cpi)
    return float(terms.face_value * ratio * real_dirty_price / 100.0)


def jgbi_real_yield(
    real_clean_price: float,
    settlement: date,
    terms: JGBITerms,
    *,
    lower: float = -1.99,
    upper: float = 2.0,
) -> float:
    """Invert the unindexed clean price to a semiannual-compounded real yield."""
    if not np.isfinite(real_clean_price) or real_clean_price <= 0.0:
        raise ValueError("real_clean_price must be positive and finite")
    if lower <= -2.0 or upper <= lower:
        raise ValueError("yield bracket must satisfy -2 < lower < upper")
    def _objective(value: float) -> float:
        return jgbi_real_clean_price(value, settlement, terms) - real_clean_price

    try:
        return float(brentq(_objective, lower, upper))
    except ValueError as exc:
        raise ValueError("real clean price is not bracketed by the yield bounds") from exc


def jgbi_nominal_present_value(
    valuation_date: date,
    terms: JGBITerms,
    monthly_cpi: CPISource,
    nominal_curve: ZeroCurve,
) -> float:
    """Discount deterministic indexed JGBi cash flows on a nominal zero curve."""
    if valuation_date >= terms.maturity_date:
        raise ValueError("valuation_date must precede maturity")
    value = 0.0
    for cashflow in jgbi_cashflows(terms, monthly_cpi):
        if cashflow.payment_date > valuation_date:
            time = (cashflow.payment_date - valuation_date).days / 365.25
            value += discount_factor(time, nominal_curve) * cashflow.total
    return float(value)


def jgbi_breakeven_inflation(nominal_yield: float, real_yield: float) -> float:
    """Return exact Fisher breakeven inflation from comparable annual yields."""
    if not np.isfinite(nominal_yield) or not np.isfinite(real_yield):
        raise ValueError("nominal and real yields must be finite")
    if nominal_yield <= -1.0 or real_yield <= -1.0:
        raise ValueError("nominal and real yields must exceed -100%")
    return float((1.0 + nominal_yield) / (1.0 + real_yield) - 1.0)


def jgbi_deflation_floor_black(
    notional: float,
    forward_index_ratio: float,
    total_variance: float,
    payment_time: float,
    nominal_curve: ZeroCurve,
    *,
    strike_ratio: float = 1.0,
    valuation_time: float = 0.0,
) -> float:
    """Price ``N (K-R)^+`` from a lognormal forward ratio and total variance."""
    values = (
        notional,
        forward_index_ratio,
        total_variance,
        payment_time,
        strike_ratio,
        valuation_time,
    )
    if not all(np.isfinite(value) for value in values):
        raise ValueError("floor inputs must be finite")
    if notional < 0.0 or forward_index_ratio <= 0.0 or strike_ratio <= 0.0:
        raise ValueError("notional cannot be negative and floor ratios must be positive")
    if total_variance < 0.0 or valuation_time < 0.0 or payment_time < valuation_time:
        raise ValueError("variance must be non-negative and payment cannot precede valuation")
    discount = forward_discount(valuation_time, payment_time, nominal_curve)
    if total_variance <= 1e-16:
        return float(notional * discount * max(strike_ratio - forward_index_ratio, 0.0))
    total_volatility = np.sqrt(total_variance)
    d1 = np.log(forward_index_ratio / strike_ratio) / total_volatility + 0.5 * total_volatility
    d2 = d1 - total_volatility
    return float(
        notional
        * discount
        * (strike_ratio * ndtr(-d2) - forward_index_ratio * ndtr(-d1))
    )


def jgbi_deflation_floor_jy(
    face_value: float,
    base_index: float,
    t: float,
    observation: float,
    payment: float,
    spot_cpi: float,
    nominal_curve: ZeroCurve,
    real_curve: ZeroCurve,
    params: JarrowYildirimParams,
) -> float:
    """Price the JGBi principal guarantee under Jarrow--Yildirim."""
    if not np.isfinite(base_index) or base_index <= 0.0:
        raise ValueError("base_index must be positive and finite")
    forward_index = jy_payment_forward_cpi(
        t, observation, payment, spot_cpi, nominal_curve, real_curve, params
    )
    variance = jy_cpi_total_variance(t, observation, payment, params)
    return jgbi_deflation_floor_black(
        face_value,
        forward_index / base_index,
        variance,
        payment,
        nominal_curve,
        valuation_time=t,
    )


def jgbi_deflation_floor_jy_mc(
    face_value: float,
    base_index: float,
    t: float,
    observation: float,
    payment: float,
    spot_cpi: float,
    nominal_curve: ZeroCurve,
    real_curve: ZeroCurve,
    params: JarrowYildirimParams,
    *,
    n_paths: int = 100_000,
    seed: int = 42,
) -> JGBIFloorMonteCarlo:
    """Estimate the JGBi floor with exact payment-forward CPI sampling."""
    if not np.isfinite(face_value) or face_value < 0.0:
        raise ValueError("face_value must be non-negative and finite")
    if not np.isfinite(base_index) or base_index <= 0.0:
        raise ValueError("base_index must be positive and finite")
    levels = simulate_jy_forward_levels(
        (observation,),
        payment,
        spot_cpi,
        nominal_curve,
        real_curve,
        params,
        t=t,
        n_paths=n_paths,
        seed=seed,
    )[:, 0]
    discounted_payoffs = (
        face_value
        * forward_discount(t, payment, nominal_curve)
        * np.maximum(1.0 - levels / base_index, 0.0)
    )
    return JGBIFloorMonteCarlo(
        float(discounted_payoffs.mean()),
        float(discounted_payoffs.std(ddof=1) / np.sqrt(n_paths)),
    )


def jgbi_floor_adjusted_price(
    unfloored_price: float,
    floor_value: float,
    terms: JGBITerms,
) -> float:
    """Add the redemption option only when contract terms contain a principal floor."""
    terms.validate()
    if not np.isfinite(unfloored_price) or not np.isfinite(floor_value):
        raise ValueError("floor-adjusted price inputs must be finite")
    if unfloored_price < 0.0 or floor_value < 0.0:
        raise ValueError("unfloored price and floor value cannot be negative")
    return float(unfloored_price + floor_value if terms.principal_floor else unfloored_price)


def jgbi_floor_risk(
    face_value: float,
    base_index: float,
    t: float,
    observation: float,
    payment: float,
    spot_cpi: float,
    nominal_curve: ZeroCurve,
    real_curve: ZeroCurve,
    params: JarrowYildirimParams,
    *,
    cpi_bump: float = 0.01,
    volatility_bump: float = 1e-4,
) -> JGBIFloorRisk:
    """Return finite-difference CPI delta and inflation-volatility vega of the floor."""
    if cpi_bump <= 0.0 or cpi_bump >= spot_cpi or volatility_bump <= 0.0:
        raise ValueError("risk bumps must be positive and CPI bump smaller than spot CPI")

    def _value(cpi: float, model: JarrowYildirimParams) -> float:
        return jgbi_deflation_floor_jy(
            face_value,
            base_index,
            t,
            observation,
            payment,
            cpi,
            nominal_curve,
            real_curve,
            model,
        )

    value = _value(spot_cpi, params)
    delta = (_value(spot_cpi + cpi_bump, params) - _value(spot_cpi - cpi_bump, params)) / (
        2.0 * cpi_bump
    )
    bumped_up = replace(
        params, inflation_volatility=params.inflation_volatility + volatility_bump
    )
    if params.inflation_volatility >= volatility_bump:
        bumped_down = replace(
            params, inflation_volatility=params.inflation_volatility - volatility_bump
        )
        vega = (_value(spot_cpi, bumped_up) - _value(spot_cpi, bumped_down)) / (
            2.0 * volatility_bump
        )
    else:
        vega = (_value(spot_cpi, bumped_up) - value) / volatility_bump
    return JGBIFloorRisk(value, float(delta), float(vega))
