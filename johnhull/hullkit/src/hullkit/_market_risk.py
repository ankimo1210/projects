"""Private loss-risk calculations for Hull Ch22.

Losses and loss_mean are positive for a loss. Existing public risk functions
use positive profits for mu; wrappers below explicitly reverse that sign.
"""

import math

import numpy as np
from scipy.stats import norm, t

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
    if nearest >= 1 and abs(mass - nearest) <= 16 * np.finfo(float).eps * len(loss):
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


def _covariance(covariance, dimension):
    cov = np.asarray(covariance, dtype=float)
    if (
        cov.shape != (dimension, dimension)
        or not np.isfinite(cov).all()
        or not np.allclose(cov, cov.T, atol=1e-14, rtol=1e-12)
    ):
        raise ValueError("finite symmetric covariance of matching dimension required")
    if np.linalg.eigvalsh(cov).min() < -1e-12 * max(float(np.abs(cov).max()), 1e-30):
        raise ValueError("covariance must be positive semidefinite")
    return cov


def normal_portfolio_risk(
    amounts, daily_vols, correlation, confidence=0.99, *, horizon=1, daily_mean_returns=None
):
    """Money risk of a linear portfolio; means are positive-profit returns."""
    a = np.asarray(amounts, dtype=float)
    vol = np.asarray(daily_vols, dtype=float)
    corr = np.asarray(correlation, dtype=float)
    if (
        a.ndim != 1
        or not len(a)
        or vol.shape != a.shape
        or not np.isfinite(a).all()
        or not np.isfinite(vol).all()
        or np.any(vol < 0)
    ):
        raise ValueError("matching finite amounts and nonnegative daily volatilities required")
    if corr.shape != (len(a), len(a)) or not np.allclose(np.diag(corr), 1):
        raise ValueError("correlation must have matching dimensions and unit diagonal")
    cov = _covariance(corr * np.outer(vol, vol), len(a))
    mean = (
        np.zeros_like(a)
        if daily_mean_returns is None
        else np.asarray(daily_mean_returns, dtype=float)
    )
    if mean.shape != a.shape or not np.isfinite(mean).all():
        raise ValueError("daily profit means must match amounts")
    sd = math.sqrt(max(float(a @ cov @ a), 0))
    result = normal_loss_risk(sd, confidence, loss_mean=-float(a @ mean), horizon=horizon)
    result["daily_sigma"] = sd
    return result


def source_normal_es(sigma, density_z, confidence=0.99, *, horizon=1):
    """Evaluate the source ES formula with an explicitly rounded density z.

    This is a display-formula replay, not an exact normal ES when density_z
    differs from the confidence quantile. Hull's MSFT example uses 2.326.
    """
    _risk_inputs(sigma, confidence, horizon=horizon)
    if not np.isfinite(density_z):
        raise ValueError("finite density quantile required")
    return float(sigma * math.sqrt(horizon) * norm.pdf(density_z) / (1 - confidence))


def volatility_units(daily_vol, trading_days=252):
    """Daily/annual SD conversion under equal independent trading days."""
    if not np.isfinite([daily_vol, trading_days]).all() or daily_vol < 0 or trading_days <= 0:
        raise ValueError("nonnegative daily SD and positive trading-day count required")
    ratio = 1 / math.sqrt(trading_days)
    return {
        "daily": float(daily_vol),
        "annual": float(daily_vol / ratio),
        "daily_to_annual_ratio": ratio,
    }


def lognormal_position_risk(value, daily_vol, days=1, confidence=0.99, *, growth=0):
    """Exact GBM loss VaR/ES for one long asset, with daily expected growth.

    This returns the full horizon distribution, not square-root scaled VaR.
    Positive growth is the asset's arithmetic expected growth rate.
    """
    _risk_inputs(daily_vol, confidence, growth, days)
    if not np.isfinite(value) or value <= 0:
        raise ValueError("positive finite asset value required")
    vol = daily_vol * math.sqrt(days)
    z = norm.ppf(1 - confidence)
    cutoff = value * math.exp((growth - daily_vol**2 / 2) * days + vol * z)
    conditional = value * math.exp(growth * days) * norm.cdf(z - vol) / (1 - confidence)
    return {"var": float(value - cutoff), "es": float(value - conditional)}


def covariance_risk(exposures, covariance, confidence=0.99, *, horizon=1, daily_profit_mean=None):
    """Linear money risk from a covariance matrix of fractional daily changes."""
    a = _loss_vector(exposures)
    cov = _covariance(covariance, len(a))
    mean = (
        np.zeros_like(a)
        if daily_profit_mean is None
        else np.asarray(daily_profit_mean, dtype=float)
    )
    if mean.shape != a.shape or not np.isfinite(mean).all():
        raise ValueError("profit means must match exposures")
    sigma = math.sqrt(max(float(a @ cov @ a), 0))
    result = normal_loss_risk(sigma, confidence, loss_mean=-float(a @ mean), horizon=horizon)
    result["daily_sigma"] = sigma
    return result


def delta_exposures(spots, deltas):
    """S_i delta_i maps fractional stock changes to money P&L, eq22.6."""
    s = np.asarray(spots, dtype=float)
    d = np.asarray(deltas, dtype=float)
    if s.ndim != 1 or d.shape != s.shape or not np.isfinite(s).all() or not np.isfinite(d).all():
        raise ValueError("matching finite spots and deltas required")
    return s * d


def bond_cashflows(principal, coupon_rate, maturity, *, frequency=2):
    """Remaining regular coupons counted backward from maturity.

    The first remaining payment may be sooner than a full coupon period; its
    coupon is unchanged (this is an existing bond, not a newly issued stub).
    """
    if (
        not np.isfinite([principal, coupon_rate, maturity, frequency]).all()
        or maturity <= 0
        or frequency < 1
        or int(frequency) != frequency
    ):
        raise ValueError("finite bond terms, positive maturity/integer frequency required")
    count = math.ceil(maturity * frequency - 1e-12)
    times = maturity - np.arange(count - 1, -1, -1) / frequency
    cash = np.full(count, principal * coupon_rate / frequency)
    cash[-1] += principal
    return {"times": times, "cashflows": cash}


def bond_parallel_risk(
    times,
    cashflows,
    rate,
    rate_sigma,
    *,
    confidence=0.99,
    horizon=1,
    compounding="continuous",
    frequency=2,
):
    """Money duration exposure to parallel daily rate changes.

    Periodic compounding returns modified duration. Zero-net-PV books still
    have a dollar duration; their normalized duration is undefined (None).
    """
    times = np.asarray(times, dtype=float)
    cash = np.asarray(cashflows, dtype=float)
    if (
        times.ndim != 1
        or cash.shape != times.shape
        or not np.isfinite(times).all()
        or not np.isfinite(cash).all()
        or np.any(times < 0)
        or not np.isfinite(rate)
    ):
        raise ValueError("finite matching future times/cashflows and rate required")
    if compounding == "continuous":
        discounted = cash * np.exp(-rate * times)
        duration_terms = times
    elif compounding == "periodic":
        if frequency <= 0 or 1 + rate / frequency <= 0:
            raise ValueError("positive compounding base/frequency required")
        discounted = cash * (1 + rate / frequency) ** (-frequency * times)
        duration_terms = times / (1 + rate / frequency)
    else:
        raise ValueError("unknown compounding convention")
    value = float(discounted.sum())
    dollar_duration = float(discounted @ duration_terms)
    result = normal_loss_risk(abs(dollar_duration) * rate_sigma, confidence, horizon=horizon)
    result.update(
        value=value,
        dollar_duration=dollar_duration,
        daily_sigma=abs(dollar_duration) * rate_sigma,
        modified_duration=dollar_duration / value if value != 0 else None,
    )
    return result


def cashflow_map(
    cashflow,
    maturity,
    standard_times,
    zero_rates,
    bond_vols,
    correlation,
    *,
    compounding="continuous",
):
    """Map a cashflow to adjacent standard tenors, preserving PV and its variance.

    Interpolate zero rates and daily bond-price SD linearly in maturity. Solve
    the quadratic variance equation for a long weight in [0,1]. If two such
    weights exist choose the one closest to the linear maturity weight.
    This preserves each cashflow's variance, not every book cross covariance.
    """
    grid = np.asarray(standard_times, dtype=float)
    rates = np.asarray(zero_rates, dtype=float)
    vols = np.asarray(bond_vols, dtype=float)
    if (
        grid.ndim != 1
        or len(grid) < 2
        or rates.shape != grid.shape
        or vols.shape != grid.shape
        or not np.isfinite([cashflow, maturity]).all()
        or not np.isfinite(grid).all()
        or not np.isfinite(rates).all()
        or not np.isfinite(vols).all()
        or np.any(np.diff(grid) <= 0)
        or grid[0] < 0
        or np.any(vols < 0)
        or not grid[0] <= maturity <= grid[-1]
    ):
        raise ValueError("finite ordered standard tenors bracketing the cashflow required")
    corr = _covariance(correlation, len(grid))
    if not np.allclose(np.diag(corr), 1):
        raise ValueError("unit-diagonal correlation required")
    if compounding == "annual":
        if np.any(rates <= -1):
            raise ValueError("annual rate must exceed -1")
        discount = (1 + rates) ** (-grid)
        rate = float(np.interp(maturity, grid, rates))
        pv = cashflow * (1 + rate) ** (-maturity)
    elif compounding == "continuous":
        discount = np.exp(-rates * grid)
        pv = cashflow * math.exp(-float(np.interp(maturity, grid, rates)) * maturity)
    else:
        raise ValueError("unknown mapping compounding convention")
    target_vol = float(np.interp(maturity, grid, vols))
    weights = np.zeros_like(grid)
    node = int(np.argmin(abs(grid - maturity)))
    if abs(grid[node] - maturity) <= 8 * np.finfo(float).eps * max(1, abs(maturity)):
        weights[node] = 1
    else:
        high = int(np.searchsorted(grid, maturity))
        low = high - 1
        time_weight = (grid[high] - maturity) / (grid[high] - grid[low])
        v1, v2, rho = vols[low], vols[high], corr[low, high]
        coefficients = np.array(
            [
                v1 * v1 + v2 * v2 - 2 * rho * v1 * v2,
                2 * rho * v1 * v2 - 2 * v2 * v2,
                v2 * v2 - target_vol**2,
            ]
        )
        scale = max(float(np.abs(coefficients).max()), v1 * v1, v2 * v2, target_vol**2)
        if scale == 0:
            weight = time_weight
        else:
            normalized = coefficients / scale
            if abs(normalized[0]) < 1e-14:
                if abs(normalized[1]) < 1e-14:
                    roots = [time_weight] if abs(normalized[2]) < 1e-14 else []
                else:
                    roots = [-normalized[2] / normalized[1]]
            else:
                roots = np.roots(normalized)
            candidates = [
                float(np.real(root))
                for root in roots
                if abs(np.imag(root)) < 1e-12 and -1e-12 <= np.real(root) <= 1 + 1e-12
            ]
            if not candidates:
                raise ValueError("no variance-preserving weight in [0,1]")
            weight = min(candidates, key=lambda w: abs(w - time_weight))
            weight = min(max(weight, 0), 1)
        weights[low], weights[high] = weight, 1 - weight
    present = pv * weights
    return {
        "value": float(pv),
        "target_vol": target_vol,
        "weights": weights,
        "present_values": present,
        "principals": present / discount,
    }


def fx_forward_bond_legs(spot, foreign_notional, strike, domestic_df, foreign_df):
    """Buy-foreign FX forward = foreign zero bond - domestic zero bond."""
    if (
        not np.isfinite([spot, foreign_notional, strike, domestic_df, foreign_df]).all()
        or spot <= 0
        or domestic_df <= 0
        or foreign_df <= 0
    ):
        raise ValueError("finite terms and positive spot/discounts required")
    foreign = spot * foreign_notional * foreign_df
    domestic = -strike * foreign_notional * domestic_df
    return {"foreign": foreign, "domestic": domestic, "value": foreign + domestic}


def ois_bond_legs(fixed_cashflows, discounts, floating_value, *, receive_fixed=True):
    """Fixed bond minus known floating-bond value; principal is in both bonds."""
    cash = _loss_vector(fixed_cashflows)
    df = np.asarray(discounts, dtype=float)
    if (
        df.shape != cash.shape
        or not np.isfinite(df).all()
        or np.any(df <= 0)
        or not np.isfinite(floating_value)
    ):
        raise ValueError("finite matching cashflows/positive discounts and float value required")
    fixed = float(cash @ df)
    return {
        "fixed": fixed,
        "floating": float(floating_value),
        "value": (1 if receive_fixed else -1) * (fixed - floating_value),
    }


def _quadratic_inputs(linear, beta, constant):
    a = _loss_vector(linear)
    b = np.asarray(beta, dtype=float)
    if (
        b.shape != (a.size, a.size)
        or not np.isfinite(b).all()
        or not np.allclose(b, b.T, atol=1e-14, rtol=1e-12)
        or not np.isfinite(constant)
    ):
        raise ValueError("finite symmetric quadratic coefficients and constant required")
    return a, b


def quadratic_pnl(changes, linear, beta, *, constant=0):
    """a'x + x'Bx + constant; B includes one-half the spot-scaled Hessian.

    Full cross terms are included. The constant may represent a separately
    chosen theta/carry shift; Hull's default short-horizon example omits it.
    """
    a, b = _quadratic_inputs(linear, beta, constant)
    x = np.asarray(changes, dtype=float)
    if x.ndim not in (1, 2) or x.shape[-1] != a.size or not np.isfinite(x).all():
        raise ValueError("finite scenario returns matching the coefficients required")
    return constant + x @ a + np.einsum("...i,ij,...j->...", x, b, x)


def quadratic_moments(linear, beta, covariance, *, constant=0):
    """First three moments of a'x+x'Bx for zero-mean Gaussian x (TN10).

    skewness=0 is a reporting convention when variance is zero.
    """
    a, b = _quadratic_inputs(linear, beta, constant)
    cov = _covariance(covariance, a.size)
    bc = b @ cov
    mean = float(constant + np.trace(bc))
    variance = max(float(a @ cov @ a + 2 * np.trace(bc @ bc)), 0)
    third = float(6 * a @ cov @ b @ cov @ a + 8 * np.trace(bc @ bc @ bc))
    return {
        "mean": mean,
        "variance": variance,
        "sigma": math.sqrt(variance),
        "central_third": third,
        "skewness": third / variance**1.5 if variance > 0 else 0.0,
        "raw_second": variance + mean**2,
        "raw_third": third + 3 * mean * variance + mean**3,
    }


def cornish_fisher_pnl_quantile(mean, sigma, skewness, probability, *, z=None):
    """TN10 third-moment correction, not an exact or always-monotone quantile.

    z optionally replays a rounded printed normal quantile. With z omitted the
    exact normal quantile at probability is used. No kurtosis term is included.
    """
    _risk_inputs(sigma, probability, mean)
    if not np.isfinite(skewness) or (z is not None and not np.isfinite(z)):
        raise ValueError("finite skewness/normal quantile required")
    normal_z = float(norm.ppf(probability)) if z is None else z
    return float(mean + sigma * (normal_z + (normal_z**2 - 1) * skewness / 6))


def quadratic_normal_quantile(linear, quadratic, probability, *, constant=0):
    """Exact quantile of bZ+cZ^2+constant for one standard normal Z."""
    from scipy.stats import ncx2

    if not np.isfinite([linear, quadratic, constant, probability]).all() or not 0 < probability < 1:
        raise ValueError("finite coefficients and interior probability required")
    if quadratic == 0:
        return float(constant + abs(linear) * norm.ppf(probability))
    noncentrality = (linear / (2 * quadratic)) ** 2
    point = (
        ncx2.ppf(probability, 1, noncentrality)
        if quadratic > 0
        else ncx2.isf(probability, 1, noncentrality)
    )
    return float(constant + quadratic * (point - noncentrality))


def quantile_standard_error(samples, confidence, density):
    """Asymptotic quantile SE; density is the loss density at the true quantile."""
    if (
        samples < 1
        or int(samples) != samples
        or not 0 < confidence < 1
        or not np.isfinite(density)
        or density <= 0
    ):
        raise ValueError("positive count/density and interior confidence required")
    return float(math.sqrt(confidence * (1 - confidence) / samples) / density)


def simulation_risk(
    spots,
    covariance,
    book,
    confidence=0.99,
    *,
    normals=None,
    samples=5000,
    seed=0,
    horizon=1,
    future_book=None,
    linear=None,
    beta=None,
    constant=0,
):
    """Full revaluation under zero-mean Gaussian arithmetic returns.

    book/future_book accept an (n, assets) array and return n book values.
    A future_book callback explicitly controls maturity shortening and carry;
    using book for both callbacks holds valuation time fixed. No clipping of
    negative shocked prices is applied. covariance is per-day return covariance.
    Optional linear/beta produce a partial simulation using identical shocks.
    """
    spot = _loss_vector(spots)
    cov = _covariance(covariance, spot.size)
    _risk_inputs(0, confidence, horizon=horizon)
    if normals is None:
        if samples < 1 or int(samples) != samples:
            raise ValueError("positive integer sample count required")
        z = np.random.default_rng(seed).normal(size=(int(samples), spot.size))
    else:
        z = np.asarray(normals, dtype=float)
        if z.ndim != 2 or z.shape[1] != spot.size or z.shape[0] < 1 or not np.isfinite(z).all():
            raise ValueError("finite (samples, assets) normals required")
    values, vectors = np.linalg.eigh(cov)
    factor = vectors * np.sqrt(np.maximum(values, 0) * horizon)
    changes = z @ factor.T
    shocked = spot * (1 + changes)
    initial = _loss_vector(book(spot[None, :]))
    future = _loss_vector((book if future_book is None else future_book)(shocked))
    if initial.size != 1 or future.size != z.shape[0]:
        raise ValueError("book callback must return one value per scenario")
    pnl = future - initial[0]
    result = {
        "changes": changes,
        "spots": shocked,
        "pnl": pnl,
        "risk": empirical_risk(pnl, confidence),
        "initial_value": float(initial[0]),
    }
    if (linear is None) != (beta is None):
        raise ValueError("linear and beta must be specified together")
    if linear is not None:
        partial = quadratic_pnl(changes, linear, beta, constant=constant)
        result.update(partial_pnl=partial, partial_risk=empirical_risk(partial, confidence))
    return result


def rolling_var(pnl, window, forecast):
    """Forecast day t using pnl[t-window:t] only, then align to pnl[t]."""
    profits = _loss_vector(pnl)
    if window < 1 or int(window) != window or window >= profits.size:
        raise ValueError("positive integer window shorter than the series required")
    indices = np.arange(int(window), profits.size)
    predictions = np.array([forecast(profits[t - window : t].copy()) for t in indices], dtype=float)
    if predictions.shape != indices.shape or not np.isfinite(predictions).all():
        raise ValueError("forecast must return one finite VaR per day")
    return {"indices": indices, "forecasts": predictions, "pnl": profits[indices].copy()}


def backtest_summary(pnl, forecasts, confidence=0.99):
    """Exception count, exact one-sided binomial tail and existing LR tests.

    realized_tail_mean is descriptive: it is not an ES calibration test.
    """
    from scipy.stats import binom

    from . import var_backtest

    _risk_inputs(0, confidence)
    profits = _loss_vector(pnl)
    if profits.size < 2:
        raise ValueError("at least two observations for transition tests required")
    flags = var_backtest.exceedance_series(profits, forecasts)
    count, n = int(flags.sum()), flags.size
    transitions = np.zeros((2, 2), dtype=int)
    np.add.at(transitions, (flags[:-1], flags[1:]), 1)
    return {
        "exceedances": flags,
        "count": count,
        "exceedance_rate": count / n,
        "binomial_upper_tail": float(binom.sf(count - 1, n, 1 - confidence)),
        "transitions": transitions,
        "kupiec": var_backtest.kupiec_pof(count, n, confidence),
        "independence": var_backtest.christoffersen_independence(flags),
        "realized_tail_mean": float((-profits)[flags.astype(bool)].mean()) if count else None,
    }
