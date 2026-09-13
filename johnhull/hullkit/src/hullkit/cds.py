"""Single-name CDS valuation (Hull 11e, §25.2–25.5).

Discrete legs with payments in arrears and defaults at interval midpoints,
exactly as in Tables 25.1–25.5: annuity, accrual-on-default, protection.
Also the fixed-coupon/upfront convention (Example 25.1), a CDS-quote
bootstrap, forward CDS spreads, and Black-type CDS options.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

from .credit_curve import HazardCurve


@dataclass(frozen=True)
class CDSLegs:
    """Present values per unit notional and per unit spread (Hull Tables 25.2–25.4)."""

    annuity: float
    accrual: float
    protection: float

    @property
    def risky_duration(self) -> float:
        """Annuity + accrual: the multiplier of the spread (4.1150 in Hull's example)."""
        return self.annuity + self.accrual

    @property
    def par_spread(self) -> float:
        """Breakeven spread: protection / (annuity + accrual)."""
        return self.protection / self.risky_duration


def _as_curve(curve) -> HazardCurve:
    return curve if isinstance(curve, HazardCurve) else HazardCurve.from_constant(float(curve))


def _grid(start: float, maturity: float, freq: int) -> np.ndarray:
    if freq < 1 or int(freq) != freq:
        raise ValueError("freq must be a positive integer")
    if maturity <= start:
        raise ValueError("maturity must exceed start")
    n = round((maturity - start) * freq)
    if n <= 0 or abs(start + n / freq - maturity) > 1e-9:
        raise ValueError("maturity - start must be a whole number of payment periods")
    return start + np.arange(1, n + 1) / freq


def cds_legs(
    curve,
    recovery: float,
    r: float,
    maturity: float,
    freq: int = 1,
    binary: bool = False,
    start: float = 0.0,
) -> CDSLegs:
    """Annuity, accrual and protection PVs for a CDS paying ``freq`` times a year.

    ``curve`` is a :class:`HazardCurve` or a constant hazard. Defaults occur at the
    midpoint of each period; the accrual is half a period's spread. ``binary=True``
    pays 1 (not 1-R) on default (Table 25.5). ``start > 0`` values a forward-start
    CDS that knocks out on default before ``start`` (unconditional survival weights).
    """
    if not 0.0 <= recovery < 1.0:
        raise ValueError("recovery must lie in [0, 1)")
    hazard = _as_curve(curve)
    times = _grid(start, maturity, freq)
    dt = 1.0 / freq
    previous = times - dt
    mid = times - 0.5 * dt
    survival = hazard.survival(times)
    default_in_period = hazard.survival(previous) - survival
    payoff = 1.0 if binary else 1.0 - recovery
    annuity = float(np.sum(survival * dt * np.exp(-r * times)))
    accrual = float(np.sum(0.5 * dt * default_in_period * np.exp(-r * mid)))
    protection = float(np.sum(payoff * default_in_period * np.exp(-r * mid)))
    return CDSLegs(annuity, accrual, protection)


def cds_par_spread(curve, recovery: float, r: float, maturity: float, freq: int = 1) -> float:
    """Breakeven CDS spread (Hull §25.2: 123 bp for λ=2%, R=40%, r=5%, 5y annual)."""
    return cds_legs(curve, recovery, r, maturity, freq).par_spread


def cds_risky_duration(curve, recovery: float, r: float, maturity: float, freq: int = 1) -> float:
    """Spread multiplier D = annuity + accrual (Hull §25.4 "duration")."""
    return cds_legs(curve, recovery, r, maturity, freq).risky_duration


def cds_mtm(
    contract_spread: float,
    curve,
    recovery: float,
    r: float,
    maturity: float,
    freq: int = 1,
    side: str = "seller",
) -> float:
    """Mark-to-market per unit notional: D·s − protection to the seller (Hull: 0.0111 at 150 bp)."""
    legs = cds_legs(curve, recovery, r, maturity, freq)
    value = legs.risky_duration * contract_spread - legs.protection
    if side == "seller":
        return value
    if side == "buyer":
        return -value
    raise ValueError("side must be 'seller' or 'buyer'")


def binary_cds_spread(curve, r: float, maturity: float, freq: int = 1) -> float:
    """Par spread of a binary CDS paying 1 on default (Hull Table 25.5: 205 bp)."""
    return cds_legs(curve, 0.0, r, maturity, freq, binary=True).par_spread


def implied_hazard(
    spread: float, recovery: float, r: float, maturity: float, freq: int = 1
) -> float:
    """Constant hazard that reproduces a par spread (Hull: 100 bp ⇒ 1.63%; Ex 25.1 ⇒ 0.5717%)."""
    if spread <= 0.0:
        raise ValueError("spread must be > 0")

    def gap(h: float) -> float:
        return cds_par_spread(h, recovery, r, maturity, freq) - spread

    try:
        return float(brentq(gap, 1e-10, 5.0, xtol=1e-14))
    except ValueError as exc:
        raise ValueError("implied_hazard: no constant hazard in (0, 5] matches the spread") from exc


def bootstrap_from_cds(tenors, spreads, recovery: float, r: float, freq: int = 4) -> HazardCurve:
    """Piecewise-constant hazards that reprice a term structure of par CDS spreads."""
    tenors = np.asarray(tenors, dtype=float)
    quotes = np.asarray(spreads, dtype=float)
    if tenors.shape != quotes.shape or tenors.ndim != 1 or tenors.size == 0:
        raise ValueError("tenors and spreads must be 1-D and equal length")
    if tenors[0] <= 0.0 or np.any(np.diff(tenors) <= 0.0):
        raise ValueError("tenors must be positive and strictly increasing")
    hazards: list[float] = []
    for i, (tenor, quote) in enumerate(zip(tenors, quotes, strict=True)):

        def gap(h: float, i: int = i, tenor: float = float(tenor), quote: float = float(quote)):
            trial = HazardCurve(tuple(tenors[: i + 1]), (*hazards, h))
            return cds_par_spread(trial, recovery, r, tenor, freq) - quote

        try:
            hazards.append(float(brentq(gap, 1e-10, 5.0, xtol=1e-14)))
        except ValueError as exc:
            raise ValueError(
                f"bootstrap_from_cds: no hazard in (0, 5] reprices tenor {tenor}"
            ) from exc
    return HazardCurve(tuple(tenors), tuple(hazards))


def actual360_to_actual_actual(rate: float) -> float:
    """Convert an actual/360 quote to actual/actual (×365/360), as in Hull Example 25.1."""
    return rate * 365.0 / 360.0


def fixed_coupon_price(spread: float, coupon: float, duration: float) -> float:
    """Price per 100 of a fixed-coupon CDS: P = 100 − 100·D·(s − c) (Hull §25.4)."""
    return 100.0 - 100.0 * duration * (spread - coupon)


def upfront_payment(
    spread: float, coupon: float, duration: float, notional: float = 100.0
) -> float:
    """Amount the protection buyer pays up front, (100 − P)/100·notional; negative ⇒ the seller pays."""
    return (100.0 - fixed_coupon_price(spread, coupon, duration)) / 100.0 * notional


def cds_forward_spread(
    curve, recovery: float, r: float, start: float, maturity: float, freq: int = 1
) -> float:
    """Par spread of a forward-start CDS on (start, maturity] that knocks out on early default."""
    if start < 0.0:
        raise ValueError("start must be >= 0")
    return cds_legs(curve, recovery, r, maturity, freq, start=start).par_spread


def cds_option(
    forward_spread: float,
    strike: float,
    sigma: float,
    expiry: float,
    risky_annuity: float,
    kind: str = "payer",
) -> float:
    """Black-type CDS option: A·[F N(d₁) − K N(d₂)] (payer) or A·[K N(−d₂) − F N(−d₁)] (receiver).

    ``risky_annuity`` is the forward risky annuity of the underlying CDS; the option
    knocks out if the reference entity defaults before ``expiry`` (Hull §25.5;
    Hull & White 2003).
    """
    if kind not in ("payer", "receiver"):
        raise ValueError("kind must be 'payer' or 'receiver'")
    if (
        forward_spread <= 0.0
        or strike <= 0.0
        or sigma < 0.0
        or expiry <= 0.0
        or risky_annuity <= 0.0
    ):
        raise ValueError(
            "forward_spread, strike, expiry and risky_annuity must be > 0 and sigma >= 0"
        )
    vol = sigma * math.sqrt(expiry)
    if vol < 1e-12:
        intrinsic = forward_spread - strike if kind == "payer" else strike - forward_spread
        return risky_annuity * max(intrinsic, 0.0)
    d1 = (math.log(forward_spread / strike) + 0.5 * vol * vol) / vol
    d2 = d1 - vol
    if kind == "payer":
        return risky_annuity * (forward_spread * norm.cdf(d1) - strike * norm.cdf(d2))
    return risky_annuity * (strike * norm.cdf(-d2) - forward_spread * norm.cdf(-d1))
