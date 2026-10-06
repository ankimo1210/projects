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
