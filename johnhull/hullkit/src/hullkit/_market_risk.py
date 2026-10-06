"""Private loss-risk calculations for Hull Ch22.

Losses and loss_mean are positive for a loss. Existing public risk functions
use positive profits for mu; wrappers below explicitly reverse that sign.
"""

import math

import numpy as np
from scipy.stats import t

from . import risk


def _risk_inputs(scale, confidence, mean=0, horizon=1):
    if not np.isfinite([scale, confidence, mean, horizon]).all():
        raise ValueError("risk parameters must be finite")
    if scale < 0 or horizon < 0 or not 0 < confidence < 1:
        raise ValueError("nonnegative scale/horizon and 0 < confidence < 1 required")


def normal_loss_risk(sigma, confidence=0.99, *, loss_mean=0, horizon=1):
    """Normal daily losses aggregated over independent days, including mean."""
    _risk_inputs(sigma, confidence, loss_mean, horizon)
    return {
        "var": risk.normal_var(sigma, confidence, horizon, -loss_mean),
        "es": risk.normal_es(sigma, confidence, horizon, -loss_mean),
        "sigma": float(sigma * math.sqrt(horizon)),
        "mean": float(loss_mean * horizon),
    }


def student_loss_risk(scale, degrees, confidence=0.99, *, loss_mean=0):
    """Student-t loss location/scale risk; ES needs degrees > 1.

    scale is the distribution's scale, not its standard deviation. No
    square-root-time aggregation of a Student distribution is assumed.
    """
    _risk_inputs(scale, confidence, loss_mean)
    if not np.isfinite(degrees) or degrees <= 1:
        raise ValueError("Student ES requires degrees > 1")
    z = t.ppf(confidence, degrees)
    tail_mean = (degrees + z * z) / (degrees - 1) * t.pdf(z, degrees) / (1 - confidence)
    return {"var": float(loss_mean + scale * z), "es": float(loss_mean + scale * tail_mean)}


def ar1_horizon_risk(daily_sigma, phi, days, confidence=0.99, *, daily_loss_mean=0):
    """Exact normal risk for stationary AR(1) losses with marginal daily SD."""
    _risk_inputs(daily_sigma, confidence, daily_loss_mean)
    if not np.isfinite(phi) or abs(phi) >= 1 or days < 1 or int(days) != days:
        raise ValueError("stationary |phi| < 1 and positive integer days required")
    days = int(days)
    k = np.arange(1, days)
    variance_multiplier = float(days + 2 * np.sum((days - k) * phi**k))
    sigma = daily_sigma * math.sqrt(max(variance_multiplier, 0))
    result = normal_loss_risk(sigma, confidence, loss_mean=daily_loss_mean * days)
    result.update(
        variance_multiplier=variance_multiplier,
        sqrt_time_ratio=math.sqrt(max(variance_multiplier, 0) / days),
    )
    return result


def historical_scenarios(levels, *, current=None, amounts=None):
    """Adjacent historical ratios applied to current domestic-currency levels.

    Supply consecutive observations; gaps cannot reconstruct missing daily
    scenarios. amounts are today's money invested in each index, not shares.
    """
    levels = np.asarray(levels, dtype=float)
    if levels.ndim == 1:
        levels = levels[:, None]
    if (
        levels.ndim != 2
        or len(levels) < 2
        or not np.isfinite(levels).all()
        or np.any(levels[:-1] == 0)
    ):
        raise ValueError("finite consecutive levels and nonzero ratio denominators required")
    today = levels[-1] if current is None else np.asarray(current, dtype=float)
    if today.shape != (levels.shape[1],) or not np.isfinite(today).all():
        raise ValueError("current levels must match the historical variables")
    ratio = levels[1:] / levels[:-1]
    scenarios = today * ratio
    result = {"scenarios": scenarios, "returns": ratio - 1}
    if amounts is not None:
        amount = np.asarray(amounts, dtype=float)
        if amount.shape != today.shape or not np.isfinite(amount).all() or np.any(today == 0):
            raise ValueError("finite amounts and nonzero current levels required")
        value = ratio @ amount
        result.update(values=value, pnl=value - amount.sum())
    return result


def brw_weights(count, decay=0.995):
    """Weights in chronological scenario order, oldest first; decay=1 is uniform."""
    if count < 1 or int(count) != count or not np.isfinite(decay) or not 0 < decay <= 1:
        raise ValueError("positive integer count and 0 < decay <= 1 required")
    count = int(count)
    if decay == 1:
        return np.full(count, 1 / count)
    log_decay = math.log(decay)
    return (
        np.exp(np.arange(count - 1, -1, -1) * log_decay)
        * (-math.expm1(log_decay))
        / (-math.expm1(count * log_decay))
    )


def _loss_vector(losses):
    losses = np.asarray(losses, dtype=float)
    if losses.ndim != 1 or not len(losses) or not np.isfinite(losses).all():
        raise ValueError("finite nonempty one-dimensional losses required")
    return losses


def weighted_tail_risk(losses, weights, confidence=0.99):
    """BRW strict cumulative crossing for VaR; integrate exactly the tail mass.

    Partial mass at the cutoff is included in ES, including an atom or ties.
    Input weights need not sum to one. This VaR convention is separate from
    Hull's equally weighted kth-worst sample convention.
    """
    _risk_inputs(1, confidence)
    losses = _loss_vector(losses)
    weights = np.asarray(weights, dtype=float)
    if (
        weights.shape != losses.shape
        or not np.isfinite(weights).all()
        or np.any(weights < 0)
        or weights.sum() <= 0
    ):
        raise ValueError("nonnegative finite weights with positive total required")
    positive = weights > 0
    order = np.argsort(-losses[positive], kind="stable")
    loss = losses[positive][order]
    weight = weights[positive][order] / weights.sum()
    cumulative = np.cumsum(weight)
    tail = 1 - confidence
    cutoff = min(int(np.searchsorted(cumulative, tail, side="right")), len(loss) - 1)
    included = np.minimum(weight, np.maximum(tail - np.r_[0, cumulative[:-1]], 0))
    return {"var": float(loss[cutoff]), "es": float(included @ loss / tail), "tail_mass": tail}


def empirical_risk(pnl, confidence=0.99, *, var_rule="hull", es_rule="hull"):
    """Sample losses from positive-gain P&L, with named finite-sample rules.

    hull: kth worst, ES=mean worst k, k=ceil(n*(1-alpha)); next/midpoint refer
    to kth and (k+1)th worst. excel uses linear interpolation. stressed uses
    the midpoint of floor/ceil tail ranks; for 250 points at 99%, ranks 2/3.
    tail_mass ES integrates the fractional tail (2.5 observations here).
    """
    _risk_inputs(1, confidence)
    loss = np.sort(-_loss_vector(pnl))[::-1]
    mass = (1 - confidence) * len(loss)
    nearest = round(mass)
    if abs(mass - nearest) <= 16 * np.finfo(float).eps * len(loss):
        mass = float(nearest)
    k = max(1, min(math.ceil(mass), len(loss)))
    a, b = loss[k - 1], loss[min(k, len(loss) - 1)]
    if var_rule == "hull":
        value = a
    elif var_rule == "next":
        value = b
    elif var_rule == "midpoint":
        value = (a + b) / 2
    elif var_rule == "excel":
        value = np.quantile(loss, confidence, method="linear")
    elif var_rule == "stressed":
        value = (loss[max(1, math.floor(mass)) - 1] + loss[k - 1]) / 2
    else:
        raise ValueError("unknown finite-sample VaR convention")
    if es_rule == "hull":
        es = float(loss[:k].mean())
    elif es_rule == "tail_mass":
        count = math.floor(mass)
        es = float((loss[:count].sum() + (mass - count) * loss[min(count, len(loss) - 1)]) / mass)
    else:
        raise ValueError("unknown finite-sample ES convention")
    return {"var": float(value), "es": es, "tail_rank": k, "sample_size": len(loss)}
