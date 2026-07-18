"""Constant-product and concentrated-liquidity AMM teaching primitives.

The functions expose token conservation, fee income, and loss-versus-
rebalancing (LVR) separately.  Dynamic fees therefore cannot be presented as
an LVR reduction when they merely compensate the LP after the fact.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _positive(value: float, name: str) -> float:
    value = float(value)
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def _fee_rate(value: float) -> float:
    value = float(value)
    if not np.isfinite(value) or not 0.0 <= value < 1.0:
        raise ValueError("fee_rate must lie in [0, 1)")
    return value


def cpmm_invariant(reserve_x: float, reserve_y: float) -> float:
    """The constant-product invariant ``k = x*y``."""

    return _positive(reserve_x, "reserve_x") * _positive(reserve_y, "reserve_y")


def cpmm_spot_price(reserve_x: float, reserve_y: float) -> float:
    """Marginal price of token X in units of token Y."""

    return _positive(reserve_y, "reserve_y") / _positive(reserve_x, "reserve_x")


@dataclass(frozen=True)
class SwapResult:
    reserve_x_before: float
    reserve_y_before: float
    reserve_x_after: float
    reserve_y_after: float
    amount_in: float
    amount_out: float
    fee_amount: float
    input_token: str

    @property
    def invariant_before(self) -> float:
        return self.reserve_x_before * self.reserve_y_before

    @property
    def invariant_after(self) -> float:
        return self.reserve_x_after * self.reserve_y_after


def cpmm_swap_x_for_y(
    reserve_x: float,
    reserve_y: float,
    amount_x: float,
    *,
    fee_rate: float = 0.003,
) -> SwapResult:
    """Swap X into a CPMM; fees remain in the pool."""

    x = _positive(reserve_x, "reserve_x")
    y = _positive(reserve_y, "reserve_y")
    amount = _positive(amount_x, "amount_x")
    fee = _fee_rate(fee_rate)
    effective = amount * (1.0 - fee)
    amount_out = y - x * y / (x + effective)
    return SwapResult(x, y, x + amount, y - amount_out, amount, amount_out, amount * fee, "x")


def cpmm_swap_y_for_x(
    reserve_x: float,
    reserve_y: float,
    amount_y: float,
    *,
    fee_rate: float = 0.003,
) -> SwapResult:
    """Swap Y into a CPMM; fees remain in the pool."""

    x = _positive(reserve_x, "reserve_x")
    y = _positive(reserve_y, "reserve_y")
    amount = _positive(amount_y, "amount_y")
    fee = _fee_rate(fee_rate)
    effective = amount * (1.0 - fee)
    amount_out = x - x * y / (y + effective)
    return SwapResult(x, y, x - amount_out, y + amount, amount, amount_out, amount * fee, "y")


def cpmm_reserves_at_price(
    reserve_x: float, reserve_y: float, external_price: float
) -> tuple[float, float]:
    """No-fee arbitrage endpoint preserving ``x*y`` at an external price."""

    k = cpmm_invariant(reserve_x, reserve_y)
    price = _positive(external_price, "external_price")
    return float(np.sqrt(k / price)), float(np.sqrt(k * price))


@dataclass(frozen=True)
class LVRResult:
    old_price: float
    new_price: float
    rebalancing_value: float
    lp_value_before_fees: float
    gross_lvr: float
    fee_compensation: float
    net_lvr: float


def loss_versus_rebalancing(
    reserve_x: float,
    reserve_y: float,
    new_price: float,
    *,
    fee_compensation: float = 0.0,
) -> LVRResult:
    """One price-jump LVR and fee compensation as distinct quantities.

    The rebalancing baseline holds the pre-jump inventory through the jump;
    the AMM is then arbitraged to ``new_price`` on the same invariant.
    """

    x = _positive(reserve_x, "reserve_x")
    y = _positive(reserve_y, "reserve_y")
    price = _positive(new_price, "new_price")
    fee_income = float(fee_compensation)
    if not np.isfinite(fee_income) or fee_income < 0.0:
        raise ValueError("fee_compensation must be finite and non-negative")
    old_price = y / x
    rebalancing_value = x * price + y
    x_after, y_after = cpmm_reserves_at_price(x, y, price)
    lp_value = x_after * price + y_after
    gross = max(0.0, rebalancing_value - lp_value)
    return LVRResult(
        old_price=float(old_price),
        new_price=price,
        rebalancing_value=float(rebalancing_value),
        lp_value_before_fees=float(lp_value),
        gross_lvr=float(gross),
        fee_compensation=fee_income,
        net_lvr=float(gross - fee_income),
    )


def dynamic_fee_rate(
    base_fee: float,
    realized_volatility: float,
    *,
    inventory_skew: float = 0.0,
    volatility_sensitivity: float = 1.0,
    inventory_sensitivity: float = 0.0,
    max_fee: float = 0.10,
) -> float:
    """Transparent volatility/inventory fee schedule with an explicit cap."""

    base = _fee_rate(base_fee)
    maximum = _fee_rate(max_fee)
    if maximum < base:
        raise ValueError("max_fee cannot be below base_fee")
    for value, name in (
        (realized_volatility, "realized_volatility"),
        (inventory_skew, "inventory_skew"),
        (volatility_sensitivity, "volatility_sensitivity"),
        (inventory_sensitivity, "inventory_sensitivity"),
    ):
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if realized_volatility < 0.0 or volatility_sensitivity < 0.0 or inventory_sensitivity < 0.0:
        raise ValueError("volatility and sensitivities must be non-negative")
    raw = (
        base
        + volatility_sensitivity * realized_volatility
        + inventory_sensitivity * abs(inventory_skew)
    )
    return float(min(maximum, raw))


def concentrated_liquidity_amounts(
    liquidity: float,
    lower_price: float,
    upper_price: float,
    price: float,
) -> tuple[float, float]:
    """Token amounts for Uniswap-v3-style liquidity over one price range."""

    liquidity = _positive(liquidity, "liquidity")
    lower = _positive(lower_price, "lower_price")
    upper = _positive(upper_price, "upper_price")
    price = _positive(price, "price")
    if lower >= upper:
        raise ValueError("lower_price must be below upper_price")
    sqrt_lower = np.sqrt(lower)
    sqrt_upper = np.sqrt(upper)
    if price <= lower:
        return float(liquidity * (1.0 / sqrt_lower - 1.0 / sqrt_upper)), 0.0
    if price >= upper:
        return 0.0, float(liquidity * (sqrt_upper - sqrt_lower))
    sqrt_price = np.sqrt(price)
    amount_x = liquidity * (1.0 / sqrt_price - 1.0 / sqrt_upper)
    amount_y = liquidity * (sqrt_price - sqrt_lower)
    return float(amount_x), float(amount_y)


def concentrated_liquidity_value(
    liquidity: float,
    lower_price: float,
    upper_price: float,
    price: float,
) -> float:
    """Mark-to-market value in token-Y units."""

    amount_x, amount_y = concentrated_liquidity_amounts(
        liquidity,
        lower_price,
        upper_price,
        price,
    )
    return float(amount_x * price + amount_y)


def concentrated_loss_versus_rebalancing(
    liquidity: float,
    lower_price: float,
    upper_price: float,
    old_price: float,
    new_price: float,
    *,
    fee_compensation: float = 0.0,
) -> LVRResult:
    """Concentrated-liquidity LVR against the same-inventory baseline.

    The rebalancing baseline marks the inventory held immediately before the
    price move at ``new_price``.  Fee compensation is reported separately and
    never changes ``gross_lvr``.
    """

    old = _positive(old_price, "old_price")
    new = _positive(new_price, "new_price")
    fee_income = float(fee_compensation)
    if not np.isfinite(fee_income) or fee_income < 0.0:
        raise ValueError("fee_compensation must be finite and non-negative")
    old_x, old_y = concentrated_liquidity_amounts(
        liquidity,
        lower_price,
        upper_price,
        old,
    )
    new_x, new_y = concentrated_liquidity_amounts(
        liquidity,
        lower_price,
        upper_price,
        new,
    )
    rebalancing_value = old_x * new + old_y
    lp_value = new_x * new + new_y
    gross_lvr = max(0.0, rebalancing_value - lp_value)
    return LVRResult(
        old_price=old,
        new_price=new,
        rebalancing_value=float(rebalancing_value),
        lp_value_before_fees=float(lp_value),
        gross_lvr=float(gross_lvr),
        fee_compensation=fee_income,
        net_lvr=float(gross_lvr - fee_income),
    )
