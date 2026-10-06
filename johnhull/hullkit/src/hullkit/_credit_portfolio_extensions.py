"""Private Hull Ch25 basket/CDO extensions; years, rate fractions and explicit notionals.

Midpoint default settlement and half-period accrual match Hull's educational
pricing convention, rather than a calendar/ISDA or legal-contract engine.
"""

import numpy as np

from . import credit_portfolio as cp
from ._credit_contracts import cds_contract_cashflows


def basket_contract_cashflows(
    default_times, notional, spread, maturity, *, recoveries=0.4, k=1, kind="kth", frequency=4
):
    """Add-up per-name notionals or a single kth-trigger notional; ties follow input order.

    Each add-up name keeps its own premium until its default; kth premiums stop
    at the selected event. The recovery of the triggering name sets that loss.
    """
    defaults = np.asarray(default_times, dtype=float)
    recovery = np.broadcast_to(np.asarray(recoveries, dtype=float), defaults.shape)
    if defaults.ndim != 1 or defaults.size == 0 or np.isnan(defaults).any() or np.any(defaults < 0):
        raise ValueError("nonempty vector of nonnegative default times required")
    if not np.isfinite(recovery).all() or np.any((recovery < 0) | (recovery > 1)):
        raise ValueError("recovery must lie in [0,1]")
    if kind not in ("kth", "add_up") or int(k) != k or not 1 <= k <= defaults.size:
        raise ValueError("supported basket kind and integer rank in [1,n] required")
    selected = (
        np.arange(defaults.size)
        if kind == "add_up"
        else np.argsort(defaults, kind="stable")[[int(k) - 1]]
    )
    contracts = [
        cds_contract_cashflows(
            notional,
            spread,
            maturity,
            frequency=frequency,
            default_time=None if defaults[i] > maturity else float(defaults[i]),
            recovery=float(recovery[i]),
        )
        for i in selected
    ]
    times = np.unique(np.concatenate([v["times"] for v in contracts]))
    premium = np.zeros(times.size)
    protection = np.zeros(times.size)
    for contract in contracts:
        idx = np.searchsorted(times, contract["times"])
        np.add.at(premium, idx, contract["premium"])
        np.add.at(protection, idx, contract["protection"])
    return {
        "times": times,
        "premium": premium,
        "protection": protection,
        "buyer_cashflows": protection - premium,
        "seller_cashflows": premium - protection,
    }


def basket_valuation(k, names, hazard, recovery, rate, maturity, rho, *, frequency=1, nodes=60):
    """Existing factor valuation connected to kth contracts, per unit basket notional."""
    return cp.kth_to_default_valuation(
        k, names, hazard, recovery, rate, maturity, rho, freq=frequency, m=nodes
    )


def loss_waterfall(losses, notional, boundaries, *, spreads=None):
    """Allocate cumulative dollar losses junior first; optional annual remaining-notional premiums.

    Boundaries partition the full pool from 0 to 1. Losses may have arbitrary
    leading shape; the final result axis is tranche. No integer-name assumption.
    """
    bounds = np.asarray(boundaries, dtype=float)
    loss = np.asarray(losses, dtype=float)
    if (
        not np.isfinite(notional)
        or notional <= 0
        or bounds.ndim != 1
        or bounds.size < 2
        or not np.isfinite(bounds).all()
        or bounds[0] != 0
        or bounds[-1] != 1
        or np.any(np.diff(bounds) <= 0)
        or not np.isfinite(loss).all()
        or np.any((loss < 0) | (loss > notional))
    ):
        raise ValueError(
            "positive notional, full increasing boundaries and loss in [0,notional] required"
        )
    initial = notional * np.diff(bounds)
    allocated = np.clip(loss[..., None] - notional * bounds[:-1], 0, initial)
    remaining = initial - allocated
    result = {"initial": initial, "allocated_loss": allocated, "remaining": remaining}
    if spreads is not None:
        rates = np.broadcast_to(np.asarray(spreads, dtype=float), initial.shape)
        if not np.isfinite(rates).all() or np.any(rates < 0):
            raise ValueError("nonnegative finite annual premium rates required")
        result["annual_premium"] = remaining * rates
    return result


def default_count_distribution(names, cumulative_pd, rho, *, nodes=60):
    """Homogeneous count PMF at one horizon; PD is cumulative, not an annual hazard.

    rho=1 is the exact all/none limit. Interior correlations use Gaussian factor
    quadrature, and rho=0 the existing stable binomial formula.
    """
    if (
        not np.isfinite([names, cumulative_pd, rho]).all()
        or int(names) != names
        or names < 1
        or not 0 <= cumulative_pd <= 1
        or not 0 <= rho <= 1
    ):
        raise ValueError("positive integer names and probability/correlation in [0,1] required")
    n = int(names)
    if rho == 1 or cumulative_pd in (0, 1):
        result = np.zeros(n + 1)
        result[0], result[-1] = 1 - cumulative_pd, cumulative_pd
        return result
    if rho == 0:
        return cp.binomial_pmf(n, cumulative_pd)
    factor, weights = cp.gauss_hermite_factor(nodes)
    conditional = cp.conditional_default_prob(cumulative_pd, rho, factor)
    return weights @ cp.binomial_pmf(n, conditional)
