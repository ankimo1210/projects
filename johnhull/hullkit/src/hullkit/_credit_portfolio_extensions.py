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


def cdo_valuation_table(
    hazard, recovery, rate, maturity, attach, detach, names, rho, *, frequency=4, nodes=60
):
    """Existing Hull factor valuation with all Table25.7 per-period rows exposed privately."""
    val = cp.cdo_tranche_valuation(
        hazard, recovery, rate, maturity, attach, detach, names, rho, freq=frequency, m=nodes
    )
    times = val.payment_times
    dt = np.diff(np.r_[0, times])
    mid = times - dt / 2
    loss = -np.diff(val.expected_principal, axis=1)
    return {
        "valuation": val,
        "default_boundaries": np.array([attach, detach]) * names / (1 - recovery),
        "annuity_rows": dt * val.expected_principal[:, 1:] * np.exp(-rate * times),
        "accrual_rows": dt / 2 * loss * np.exp(-rate * mid),
        "protection_rows": loss * np.exp(-rate * mid),
    }


def kth_valuation_table(k, names, hazard, recovery, rate, maturity, rho, *, frequency=1, nodes=60):
    """Ex25.3 conditional PD, trigger probabilities and existing per-unit valuation."""
    val = basket_valuation(
        k, names, hazard, recovery, rate, maturity, rho, frequency=frequency, nodes=nodes
    )
    pd = -np.expm1(-np.asarray(hazard) * val.payment_times)
    return {
        "valuation": val,
        "marginal_pd": pd,
        "conditional_pd": cp.conditional_default_prob(pd[None, :], rho, val.factor_nodes[:, None]),
        "trigger_probability": np.diff(val.cumulative_prob, axis=1),
    }


def gaussian_default_times(hazards, loadings, paths, *, seed):
    """Direct exponential default times from a common/individual Gaussian latent sample.

    One annual hazard and signed factor loading per name. Latent correlations
    are a_i*a_j. Zero hazard produces infinite survival. These are Q inputs for
    pricing, not a P-to-Q conversion or a dynamic credit-spread process.
    """
    from scipy.stats import norm

    hazard = np.asarray(hazards, dtype=float)
    a = np.broadcast_to(np.asarray(loadings, dtype=float), hazard.shape)
    if (
        hazard.ndim != 1
        or hazard.size == 0
        or not np.isfinite(hazard).all()
        or np.any(hazard < 0)
        or not np.isfinite(a).all()
        or np.any(abs(a) > 1)
        or paths < 2
        or int(paths) != paths
    ):
        raise ValueError(
            "nonnegative hazard vector, loadings in [-1,1] and at least two paths required"
        )
    rng = np.random.default_rng(seed)
    latent = a * rng.normal(size=(int(paths), 1)) + np.sqrt(1 - a * a) * rng.normal(
        size=(int(paths), hazard.size)
    )
    result = np.full(latent.shape, np.inf)
    np.divide(-norm.logsf(latent), hazard, out=result, where=hazard > 0)
    return result


def _principal_legs(principal, times, rate, *, protection_scale=1):
    """Midpoint-settled unit-principal paths or one deterministic expected-principal curve."""
    dt = np.diff(np.r_[0, times])
    loss = -np.diff(principal, axis=1)
    mid = times - dt / 2
    a = (dt * principal[:, 1:] * np.exp(-rate * times)).sum(axis=1)
    b = (dt / 2 * loss * np.exp(-rate * mid)).sum(axis=1)
    c = (protection_scale * loss * np.exp(-rate * mid)).sum(axis=1)
    result = {"expected_principal": principal.mean(axis=0)}
    for name, values in (("annuity", a), ("accrual", b), ("protection", c)):
        result[name] = float(values.mean())
        result[name + "_se"] = (
            float(values.std(ddof=1) / np.sqrt(values.size)) if values.size > 1 else 0.0
        )
    duration = result["annuity"] + result["accrual"]
    if duration <= 0:
        raise ValueError("positive risky premium annuity required")
    spread = result["protection"] / duration
    result["spread"] = spread
    influence = (c - spread * (a + b)) / duration
    result["spread_se"] = float(influence.std(ddof=1) / np.sqrt(a.size)) if a.size > 1 else 0.0
    return result


def default_time_legs(
    default_times, recovery, rate, maturity, *, frequency=4, attach=0, detach=1, k=None
):
    """Value simulated default-time tranche or kth cashflows at Hull period midpoints.

    k selects a basket (unit basket notional and loss 1-R); otherwise principal
    is unit tranche notional. Report path standard errors; spread SE uses the
    paired ratio influence function, not independent numerator/denominator SEs.
    """
    defaults = np.asarray(default_times, dtype=float)
    if (
        defaults.ndim != 2
        or defaults.shape[0] < 2
        or defaults.shape[1] < 1
        or np.isnan(defaults).any()
        or np.any(defaults < 0)
        or not np.isfinite([recovery, rate]).all()
        or not 0 <= recovery <= 1
    ):
        raise ValueError("nonnegative path/name default times and valid recovery/rate required")
    names = defaults.shape[1]
    if k is not None and (int(k) != k or not 1 <= k <= names):
        raise ValueError("integer basket rank in [1,n] required")
    if k is None and not 0 <= attach < detach <= 1:
        raise ValueError("tranche must lie in [0,1] with positive width")
    times, _, _ = cp._payment_grid(maturity, frequency)
    principal = np.ones((defaults.shape[0], times.size + 1))
    for j, time in enumerate(times, 1):
        counts = np.sum(defaults <= time, axis=1)
        principal[:, j] = (
            (counts < k)
            if k is not None
            else 1 - np.clip((counts * (1 - recovery) / names - attach) / (detach - attach), 0, 1)
        )
    return _principal_legs(
        principal, times, rate, protection_scale=1 - recovery if k is not None else 1
    )


def concave_loss_interpolation(detachments, losses, points):
    """Piecewise-linear increasing concave loss versus detachment, with no extrapolation.

    Last axis is detachment; leading axes may be payment times. Losses are pool
    principal fractions (undiscounted or positive-rate loss PV), not tranche
    principal fractions. All input nodes are preserved; invalid curves fail.
    """
    x = np.asarray(detachments, dtype=float)
    y = np.asarray(losses, dtype=float)
    target = np.asarray(points, dtype=float)
    if (
        x.ndim != 1
        or x.size < 2
        or not np.isfinite(x).all()
        or x[0] < 0
        or x[-1] > 1
        or np.any(np.diff(x) <= 0)
        or y.ndim < 1
        or y.shape[-1] != x.size
        or not np.isfinite(y).all()
        or not np.isfinite(target).all()
        or np.any((target < x[0]) | (target > x[-1]))
    ):
        raise ValueError(
            "matching increasing detachment nodes and in-range interpolation points required"
        )
    slopes = np.diff(y, axis=-1) / np.diff(x)
    if (
        np.any(y < -1e-12)
        or np.any(y > x + 1e-12)
        or np.any(slopes < -1e-10)
        or np.any(slopes > 1 + 1e-10)
        or np.any(np.diff(slopes, axis=-1) > 1e-10)
    ):
        raise ValueError("loss must be increasing, concave and within principal bounds")
    i = np.clip(np.searchsorted(x, target, side="right") - 1, 0, x.size - 2)
    fraction = (target - x[i]) / (x[i + 1] - x[i])
    return y[..., i] + fraction * (y[..., i + 1] - y[..., i])


def interpolated_tranche_legs(payment_times, detachments, cumulative_losses, rate, attach, detach):
    """Interpolate complete expected-loss time curves and value a nonstandard tranche.

    Include time-zero loss row and each payment row. Supplying cumulative curves
    assembled from standard compound-calibrated legs preserves their A/B/C and
    quotes. A base-correlation PV curve alone cannot determine premium annuity.
    """
    times = np.asarray(payment_times, dtype=float)
    losses = np.asarray(cumulative_losses, dtype=float)
    if (
        times.ndim != 1
        or times.size == 0
        or not np.isfinite(times).all()
        or times[0] <= 0
        or np.any(np.diff(times) <= 0)
        or not np.isfinite(rate)
        or not 0 <= attach < detach <= 1
        or losses.ndim != 2
        or losses.shape[0] != times.size + 1
        or np.any(abs(losses[0]) > 1e-12)
        or np.any(np.diff(losses, axis=0) < -1e-12)
    ):
        raise ValueError(
            "initial-zero, increasing time loss curves on a positive payment grid required"
        )
    interval = concave_loss_interpolation(detachments, losses, [attach, detach])
    principal = 1 - np.diff(interval, axis=1)[:, 0] / (detach - attach)
    if (
        np.any(principal < -1e-10)
        or np.any(principal > 1 + 1e-10)
        or np.any(np.diff(principal) > 1e-10)
    ):
        raise ValueError("interpolated tranche principal must decrease in [0,1]")
    return _principal_legs(principal[None, :], times, rate)
