"""Private Hull §29.3 market swaption and annuity numeraire contracts."""

import numpy as np

from ._cap_floor_market import rate_option_price


def _value(x):
    if not np.all(np.isfinite(x)):
        raise ValueError("finite swaption result required")
    return float(x) if np.ndim(x) == 0 else x


def _kind(kind):
    if kind not in ("payer", "receiver"):
        raise ValueError("kind must be payer or receiver")
    return "call" if kind == "payer" else "put"


def swap_annuity(accruals, discounts):
    """Sum alpha_i*P(0,T_i) on the final payment axis, with actual day counts."""
    a, p = np.broadcast_arrays(
        np.asarray(accruals, dtype=float), np.asarray(discounts, dtype=float)
    )
    if not a.size or np.any(a <= 0) or np.any(p <= 0):
        raise ValueError("nonempty positive accruals and discounts required")
    return _value(np.sum(a * p, axis=-1))


def swaption_market_price(
    notional,
    annuity,
    swap_forward,
    strike,
    volatility,
    expiry,
    kind="payer",
    *,
    model="black",
    shift=0.0,
):
    """L*A*option(s_F,K), Hull 29.10/29.11.

    swap_forward is supplied independently of the discount curve. Example
    29.4's 6.1% continuous forward must not be replaced by the 6% discount
    zero rate. Black/shifted vol is relative; normal vol is absolute rate.
    """
    L, A = np.asarray(notional, dtype=float), np.asarray(annuity, dtype=float)
    if np.any(L < 0) or np.any(A <= 0):
        raise ValueError("nonnegative notional and positive annuity required")
    return _value(
        L
        * A
        * rate_option_price(
            1.0, swap_forward, strike, volatility, expiry, _kind(kind), model=model, shift=shift
        )
    )


def swaption_coupon_bond_payoff(
    notional, discounts_at_exercise, accruals, fixed_rate, kind="payer"
):
    """Payer=put/receiver=call on a coupon bond at par, BS29.2.

    Exercise equals swap start and the single-curve floating leg is par.
    This identity does not silently replace a separate projection curve in
    a market-price contract. Coupon cashflows include final principal.
    """
    bonds = np.asarray(discounts_at_exercise, dtype=float)
    if bonds.ndim == 0 or bonds.shape[-1] == 0 or notional < 0:
        raise ValueError("nonempty payment axis and nonnegative notional required")
    A = swap_annuity(accruals, bonds)
    bond_value = bonds[..., -1] + fixed_rate * A
    sign = 1 if _kind(kind) == "call" else -1
    return _value(notional * np.maximum(sign * (1 - bond_value), 0))


def annuity_numeraire_density(discounted_bank_factor, terminal_annuity, current_annuity):
    """Raw dQ_A/dQ = exp(-J)*A_T/A_0, before the first annuity payment."""
    d, a, a0 = np.broadcast_arrays(
        *[
            np.asarray(x, dtype=float)
            for x in (discounted_bank_factor, terminal_annuity, current_annuity)
        ]
    )
    if np.any(d <= 0) or np.any(a <= 0) or np.any(a0 <= 0):
        raise ValueError("positive bank discount and annuities required")
    return _value(d * a / a0)
