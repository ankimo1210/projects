"""Cash-flow construction, discounting and model quotes for every instrument type.

All *quotes* are expressed in **normalised input units**:

============  ==================================  ==========================
type          quote                               unit
============  ==================================  ==========================
``deposit``   simple annual rate                  percentage points
``ois_swap``  par fixed rate                      percentage points
``bond``      clean price (no accrued interest)   points per 100 face
============  ==================================  ==========================

Residuals used for fitting are converted to a common **yield-equivalent basis
point** scale so that a bond price residual and a swap rate residual can enter
the same objective function.  For rate instruments the conversion is exact
(1 percentage point = 100 bp).  For bonds it is the first-order relation
``Delta y = -Delta P / (P * ModifiedDuration)``.
"""

from __future__ import annotations

import numpy as np

from .conventions import DECIMAL_TO_PERCENT, PERCENT_TO_DECIMAL
from .curve import DiscountCurve
from .instruments import BOND, BOND_FACE, DEPOSIT, OIS_SWAP, Instrument

__all__ = [
    "deposit_simple_rate",
    "deposit_pv",
    "swap_annuity",
    "swap_par_rate",
    "swap_receiver_pv",
    "bond_cashflows",
    "bond_price",
    "bond_pv",
    "model_quote",
    "instrument_pv",
    "residual_bp_scale",
    "residual_bp",
    "price_duration",
]


# --------------------------------------------------------------------------
# deposits
# --------------------------------------------------------------------------
def deposit_simple_rate(curve: DiscountCurve, maturity_years: float) -> float:
    """Model simple deposit rate implied by ``D(T) = 1 / (1 + r T)``."""
    d = float(curve.discount(np.asarray(maturity_years, dtype=float)))
    if d <= 0.0:
        raise ValueError("non-positive discount factor")
    return (1.0 / d - 1.0) / maturity_years


def deposit_pv(
    curve: DiscountCurve, maturity_years: float, rate_decimal: float, notional: float
) -> float:
    """PV of lending ``notional`` at a fixed simple rate, net of the initial cash.

    ``PV = N * (1 + r T) * D(T) - N``.  At the market rate this is zero, which
    mirrors the par-swap convention and makes the DV01 definition consistent
    across instrument types.
    """
    d = float(curve.discount(np.asarray(maturity_years, dtype=float)))
    return notional * ((1.0 + rate_decimal * maturity_years) * d - 1.0)


# --------------------------------------------------------------------------
# OIS swaps
# --------------------------------------------------------------------------
def swap_annuity(curve: DiscountCurve, times: np.ndarray, accrual: float) -> float:
    return float(accrual * np.sum(curve.discount(times)))


def swap_par_rate(curve: DiscountCurve, times: np.ndarray, accrual: float) -> float:
    """``r = (1 - D(T)) / sum(alpha_i D(t_i))`` (OIS starting at the valuation date)."""
    discounts = np.asarray(curve.discount(times), dtype=float)
    annuity = accrual * float(np.sum(discounts))
    if annuity <= 0.0:
        raise ValueError("non-positive swap annuity")
    return (1.0 - float(discounts[-1])) / annuity


def swap_receiver_pv(
    curve: DiscountCurve,
    times: np.ndarray,
    accrual: float,
    fixed_rate_decimal: float,
    notional: float,
) -> float:
    """PV of receiving the fixed leg and paying the OIS float leg."""
    discounts = np.asarray(curve.discount(times), dtype=float)
    annuity = accrual * float(np.sum(discounts))
    float_leg = 1.0 - float(discounts[-1])
    return notional * (fixed_rate_decimal * annuity - float_leg)


# --------------------------------------------------------------------------
# bonds
# --------------------------------------------------------------------------
def bond_cashflows(
    times: np.ndarray, coupon_rate: float, frequency: int, face: float = BOND_FACE
) -> np.ndarray:
    """Cash-flow amounts matching ``times`` (principal added at maturity)."""
    flows = np.full(times.shape, face * coupon_rate / float(frequency), dtype=float)
    flows[-1] += face
    return flows


def bond_price(
    curve: DiscountCurve,
    times: np.ndarray,
    coupon_rate: float,
    frequency: int,
    face: float = BOND_FACE,
) -> float:
    flows = bond_cashflows(times, coupon_rate, frequency, face)
    return float(np.sum(flows * np.asarray(curve.discount(times), dtype=float)))


def bond_pv(
    curve: DiscountCurve,
    times: np.ndarray,
    coupon_rate: float,
    frequency: int,
    face: float = BOND_FACE,
) -> float:
    """A bond's PV *is* its clean price under the documented no-accrual convention."""
    return bond_price(curve, times, coupon_rate, frequency, face)


def price_duration(
    curve: DiscountCurve,
    times: np.ndarray,
    coupon_rate: float,
    frequency: int,
    face: float = BOND_FACE,
) -> tuple[float, float]:
    """Return ``(price, duration)`` where duration is the PV-weighted mean time."""
    flows = bond_cashflows(times, coupon_rate, frequency, face)
    discounts = np.asarray(curve.discount(times), dtype=float)
    pv = flows * discounts
    price = float(np.sum(pv))
    if price <= 0.0:
        return price, float(times[-1])
    return price, float(np.sum(times * pv) / price)


# --------------------------------------------------------------------------
# generic dispatch
# --------------------------------------------------------------------------
def model_quote(curve: DiscountCurve, inst: Instrument) -> float:
    """Model-implied quote in normalised input units."""
    times = inst.schedule()
    if inst.instrument_type == DEPOSIT:
        return deposit_simple_rate(curve, inst.maturity_years) * DECIMAL_TO_PERCENT
    if inst.instrument_type == OIS_SWAP:
        accrual = 1.0 / float(inst.fixed_frequency)
        return swap_par_rate(curve, times, accrual) * DECIMAL_TO_PERCENT
    if inst.instrument_type == BOND:
        return bond_price(curve, times, float(inst.coupon_rate), inst.fixed_frequency)
    raise ValueError(f"unsupported instrument type: {inst.instrument_type}")


def instrument_pv(curve: DiscountCurve, inst: Instrument) -> float:
    """PV of the receiver / fixed-rate-asset position used for risk reporting."""
    times = inst.schedule()
    if inst.instrument_type == DEPOSIT:
        return deposit_pv(
            curve, inst.maturity_years, inst.quote * PERCENT_TO_DECIMAL, inst.notional()
        )
    if inst.instrument_type == OIS_SWAP:
        accrual = 1.0 / float(inst.fixed_frequency)
        return swap_receiver_pv(
            curve, times, accrual, inst.quote * PERCENT_TO_DECIMAL, inst.notional()
        )
    if inst.instrument_type == BOND:
        return bond_pv(curve, times, float(inst.coupon_rate), inst.fixed_frequency)
    raise ValueError(f"unsupported instrument type: {inst.instrument_type}")


def residual_bp_scale(curve: DiscountCurve, inst: Instrument) -> float:
    """Multiplier converting a native-unit residual into yield-equivalent bp.

    Rate quotes: 1 percentage point = 100 bp.  Bond prices: a *positive* price
    residual corresponds to a *negative* yield residual, hence the sign.
    """
    if inst.is_rate_quote:
        return 100.0
    times = inst.schedule()
    price, duration = price_duration(
        curve, times, float(inst.coupon_rate), inst.fixed_frequency
    )
    denom = price * duration
    if not np.isfinite(denom) or abs(denom) < 1.0e-8:
        return 0.0
    return -1.0e4 / denom


def residual_bp(curve: DiscountCurve, inst: Instrument) -> float:
    """Yield-equivalent residual (market minus model) in basis points."""
    native = inst.quote - model_quote(curve, inst)
    return native * residual_bp_scale(curve, inst)


# --------------------------------------------------------------------------
# vectorised calibration set
# --------------------------------------------------------------------------
class CalibrationSet:
    """Pre-computed cash flows for a fixed instrument list.

    Fitting evaluates the objective thousands of times, so every schedule,
    cash-flow amount and index map is built once here and each objective
    evaluation reduces to a single vectorised discount-factor lookup plus
    segment sums.  The results agree with the scalar functions above to machine
    precision; ``tests/test_pricing.py`` pins that equivalence.
    """

    __slots__ = (
        "instruments", "times", "owner", "flows", "accrual", "is_deposit",
        "is_swap", "is_bond", "maturities", "last_index", "quotes", "weights",
        "n",
    )

    def __init__(self, instruments: list[Instrument]) -> None:
        self.instruments = list(instruments)
        self.n = len(self.instruments)
        times: list[np.ndarray] = []
        owner: list[np.ndarray] = []
        flows: list[np.ndarray] = []
        accrual = np.zeros(self.n, dtype=float)
        is_deposit = np.zeros(self.n, dtype=bool)
        is_swap = np.zeros(self.n, dtype=bool)
        is_bond = np.zeros(self.n, dtype=bool)
        maturities = np.zeros(self.n, dtype=float)
        last_index = np.zeros(self.n, dtype=np.int64)
        cursor = 0
        for k, inst in enumerate(self.instruments):
            schedule = np.atleast_1d(np.asarray(inst.schedule(), dtype=float))
            times.append(schedule)
            owner.append(np.full(schedule.size, k, dtype=np.int64))
            maturities[k] = inst.maturity_years
            cursor += schedule.size
            last_index[k] = cursor - 1
            if inst.instrument_type == DEPOSIT:
                is_deposit[k] = True
                flows.append(np.zeros(schedule.size))
            elif inst.instrument_type == OIS_SWAP:
                is_swap[k] = True
                accrual[k] = 1.0 / float(inst.fixed_frequency)
                flows.append(np.zeros(schedule.size))
            elif inst.instrument_type == BOND:
                is_bond[k] = True
                flows.append(
                    bond_cashflows(schedule, float(inst.coupon_rate), inst.fixed_frequency)
                )
            else:  # pragma: no cover - guarded upstream
                raise ValueError(f"unsupported instrument type: {inst.instrument_type}")
        self.times = np.concatenate(times) if times else np.zeros(0)
        self.owner = np.concatenate(owner) if owner else np.zeros(0, dtype=np.int64)
        self.flows = np.concatenate(flows) if flows else np.zeros(0)
        self.accrual = accrual
        self.is_deposit = is_deposit
        self.is_swap = is_swap
        self.is_bond = is_bond
        self.maturities = maturities
        self.last_index = last_index
        self.quotes = np.array([i.quote for i in self.instruments], dtype=float)
        self.weights = np.array([i.weight for i in self.instruments], dtype=float)

    def _segment_sum(self, values: np.ndarray) -> np.ndarray:
        return np.bincount(self.owner, weights=values, minlength=self.n)

    def model_quotes(self, curve: DiscountCurve) -> np.ndarray:
        """Model quotes in normalised input units for every instrument."""
        if self.n == 0:
            return np.zeros(0)
        d = np.asarray(curve.discount(self.times), dtype=float)
        d_last = d[self.last_index]
        out = np.zeros(self.n, dtype=float)
        if self.is_deposit.any():
            m = self.is_deposit
            out[m] = (1.0 / d_last[m] - 1.0) / self.maturities[m] * DECIMAL_TO_PERCENT
        if self.is_swap.any():
            m = self.is_swap
            annuity = self.accrual * self._segment_sum(d)
            out[m] = (1.0 - d_last[m]) / annuity[m] * DECIMAL_TO_PERCENT
        if self.is_bond.any():
            m = self.is_bond
            out[m] = self._segment_sum(self.flows * d)[m]
        return out

    def residual_scales(self, curve: DiscountCurve) -> np.ndarray:
        """Native-unit to yield-equivalent-bp multipliers."""
        scales = np.full(self.n, 100.0, dtype=float)
        if not self.is_bond.any():
            return scales
        d = np.asarray(curve.discount(self.times), dtype=float)
        pv = self.flows * d
        price = self._segment_sum(pv)
        weighted_time = self._segment_sum(self.times * pv)
        m = self.is_bond
        denom = np.where(np.abs(price) > 1.0e-9, price, np.nan)
        duration = weighted_time / denom
        product = price * duration
        with np.errstate(divide="ignore", invalid="ignore"):
            bond_scale = -1.0e4 / product
        scales[m] = np.where(np.isfinite(bond_scale[m]), bond_scale[m], 0.0)
        return scales

    def residuals_bp(self, curve: DiscountCurve) -> np.ndarray:
        """Yield-equivalent repricing residuals (market minus model), in bp."""
        if self.n == 0:
            return np.zeros(0)
        return (self.quotes - self.model_quotes(curve)) * self.residual_scales(curve)


__all__.append("CalibrationSet")
