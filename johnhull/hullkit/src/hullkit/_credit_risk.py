"""Private Hull Ch24 credit calculations. Probabilities are fractions, times years.

P denotes real-world/historical probabilities, Q pricing probabilities. Numerical
transformations do not convert between these measures; the caller supplies the
appropriate inputs. Exposure amounts inherit the supplied contract's money unit.
"""

import math

import numpy as np
from scipy.stats import norm

from . import credit, credit_curve


def _vector(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or x.size < 1 or not np.isfinite(x).all():
        raise ValueError("finite nonempty vector required")
    return x


def _recovery(recovery):
    if not np.isfinite(recovery) or not 0 <= recovery <= 1:
        raise ValueError("recovery fraction in [0,1] required")


def constant_pd(hazard, maturity):
    if not np.isfinite([hazard, maturity]).all() or min(hazard, maturity) < 0:
        raise ValueError("nonnegative finite hazard/maturity required")
    return {"survival": math.exp(-hazard * maturity), "pd": -math.expm1(-hazard * maturity)}


def historical_pd(times, cumulative_pd, *, measure="P"):
    """Interval PDs and annual piecewise hazards from cumulative probabilities."""
    t, q = _vector(times), _vector(cumulative_pd)
    if (
        t.shape != q.shape
        or t[0] <= 0
        or np.any(np.diff(t) <= 0)
        or np.any(q < 0)
        or np.any(q >= 1)
        or np.any(np.diff(q) < 0)
        or measure not in ("P", "Q")
    ):
        raise ValueError(
            "increasing positive times, increasing finite PD in [0,1), and P/Q label required"
        )
    survival = 1 - q
    previous = np.r_[1, survival[:-1]]
    interval = previous - survival
    cumulative_hazard = -np.log1p(-q)
    forward = np.diff(np.r_[0, cumulative_hazard]) / np.diff(np.r_[0, t])
    curve = credit_curve.HazardCurve(tuple(t), tuple(forward))
    return {
        "survival": survival,
        "interval_pd": interval,
        "conditional_pd": interval / previous,
        "average_hazard": cumulative_hazard / t,
        "forward_hazard": forward,
        "curve": curve,
        "measure": measure,
    }


def spread_hazards(times, spreads, recovery):
    _recovery(recovery)
    t, s = _vector(times), _vector(spreads)
    if recovery == 1 or t.shape != s.shape or np.any(s < 0):
        raise ValueError("matching nonnegative spreads and recovery below one required")
    average = credit_curve.average_hazards_from_spreads(s, recovery)
    return {
        "average": average,
        "curve": credit_curve.forward_hazards_from_average(t, average),
        "measure": "Q",
    }


def bond_credit_table(
    curve, face, coupon_rate, maturity, rate, recovery, *, frequency=2, default_step=0.5
):
    """Direct coupon/principal survival and par-recovery PV under midpoint default.

    Default mass from each interval is placed at its midpoint, before any coupon
    at the same time. Coupons stop on default and recovery is recovery*face.
    This reproduces Hull's educational convention, not an ISDA schedule model.
    """
    _recovery(recovery)
    if (
        not np.isfinite([face, coupon_rate, maturity, rate, default_step]).all()
        or face < 0
        or maturity <= 0
        or default_step <= 0
        or frequency < 1
        or int(frequency) != frequency
    ):
        raise ValueError("finite bond terms and positive maturity/frequency/default step required")
    periods = round(maturity * frequency)
    defaults = round(maturity / default_step)
    if (
        periods < 1
        or defaults < 1
        or not math.isclose(periods / frequency, maturity, abs_tol=1e-10)
        or not math.isclose(defaults * default_step, maturity, abs_tol=1e-10)
    ):
        raise ValueError("maturity must contain complete coupon and default intervals")
    times = np.arange(1, periods + 1) / frequency
    cash = np.full(periods, face * coupon_rate / frequency)
    cash[-1] += face
    end = np.arange(1, defaults + 1) * default_step
    default_times = end - default_step / 2
    pd = curve.survival(end - default_step) - curve.survival(end)
    cumulative_pd = np.r_[0, np.cumsum(pd)]
    survival = 1 - cumulative_pd[np.searchsorted(default_times, times, side="right")]
    coupon_pv = cash * survival * np.exp(-rate * times)
    recovery_pv = recovery * face * pd * np.exp(-rate * default_times)
    promised = float(cash @ np.exp(-rate * times))
    forward_values = np.array(
        [
            sum(
                float(amount) * math.exp(-rate * (time - tau))
                for time, amount in zip(times, cash, strict=True)
                if time > tau
            )
            for tau in default_times
        ]
    )
    losses = (forward_values - recovery * face) * np.exp(-rate * default_times)
    value = float(coupon_pv.sum() + recovery_pv.sum())
    return {
        "cash_times": times,
        "cashflows": cash,
        "survival": survival,
        "default_times": default_times,
        "default_pd": pd,
        "surviving_cash_pv": coupon_pv,
        "recovery_pv": recovery_pv,
        "default_forward_values": forward_values,
        "discounted_default_losses": losses,
        "value": value,
        "promised_value": promised,
        "loss_pv": promised - value,
    }


def bond_curve_from_yields(
    maturities, yields, coupon_rate, rate, recovery, *, face=100, frequency=2, default_step=0.5
):
    """Existing Hull loss bootstrap with direct cashflow tables for comparison."""
    t, y = _vector(maturities), _vector(yields)
    if t.shape != y.shape:
        raise ValueError("matching maturity and yield vectors required")
    prices = np.array(
        [
            credit_curve.bond_price_from_yield(
                face, coupon_rate, float(time), float(yield_rate), frequency
            )
            for time, yield_rate in zip(t, y, strict=True)
        ]
    )
    result = credit_curve.bootstrap_from_bonds(
        prices, coupon_rate, t, rate, recovery, face, frequency, default_step
    )
    return {
        "curve": result.curve,
        "prices": prices,
        "risk_free": np.array(result.risk_free_prices),
        "loss_pv": np.array(result.expected_loss_pv),
        "measure": "Q",
    }


def hazard_comparison(historical, pricing, *, recovery=0.4, total_spreads=None):
    """Compare observed P/Q hazards; no measure conversion is inferred.

    Display columns replay Tables24.2/3: positive half-up rounding, then subtract
    the displayed compensation bp from the observed total spread bp.
    """
    h, q = _vector(historical), _vector(pricing)
    _recovery(recovery)
    if h.shape != q.shape or np.any(h < 0) or np.any(q < 0):
        raise ValueError("matching nonnegative annual hazards required")
    ratio = np.full_like(h, np.nan)
    np.divide(q, h, out=ratio, where=h > 0)
    compensation = h * (1 - recovery)
    rounded = np.floor(compensation * 10000 + 0.5)
    result = {
        "ratio": ratio,
        "display_ratio": np.floor(ratio * 10 + 0.5) / 10,
        "difference": q - h,
        "compensation_spread": compensation,
        "display_compensation_bp": rounded,
    }
    if total_spreads is not None:
        spreads = _vector(total_spreads)
        if spreads.shape != h.shape:
            raise ValueError("total spread vector must match hazards")
        result.update(
            excess_spread=spreads - compensation, display_excess_bp=spreads * 10000 - rounded
        )
    return result


def merton_values(equity, equity_vol, debt, rate, maturity, *, physical_drift=None):
    """Existing Merton Q calibration plus debt/expected-loss accounting.

    An optional caller-specified P asset drift gives a structural P probability,
    not the proprietary empirical KMV EDF mapping. Default occurs only at T.
    """
    if not np.isfinite([equity, equity_vol, debt, rate, maturity]).all():
        raise ValueError("finite Merton terms required")
    asset, vol, pd = credit.merton_default_prob(equity, equity_vol, debt, rate, maturity)
    sd = vol * math.sqrt(maturity)
    d1 = (math.log(asset / debt) + (rate + 0.5 * vol * vol) * maturity) / sd
    d2 = d1 - sd
    risk_free = debt * math.exp(-rate * maturity)
    bond = asset - equity
    result = {
        "asset_value": asset,
        "asset_vol": vol,
        "d1": d1,
        "d2": d2,
        "pricing_pd": pd,
        "debt_value": bond,
        "risk_free_debt": risk_free,
        "expected_loss_rate": (risk_free - bond) / risk_free,
        "physical_pd": None,
        "edf": None,
    }
    if physical_drift is not None:
        if not np.isfinite(physical_drift):
            raise ValueError("finite physical asset drift required")
        distance = (math.log(asset / debt) + (physical_drift - 0.5 * vol * vol) * maturity) / sd
        result["physical_pd"] = float(norm.cdf(-distance))
    return result


def _interval_weights(weights, paths, periods):
    probabilities = np.asarray(weights, dtype=float)
    if probabilities.shape == (periods,):
        probabilities = np.broadcast_to(probabilities, (paths, periods))
    if (
        probabilities.shape != (paths, periods)
        or not np.isfinite(probabilities).all()
        or np.any(probabilities < 0)
        or np.any(probabilities.sum(axis=1) > 1 + 1e-12)
    ):
        raise ValueError(
            "nonnegative unconditional/conditional interval PDs summing to at most one required"
        )
    return probabilities


def single_payoff_credit_value(no_default_value, spread, maturity, recovery):
    """Ex24.5 exact bond-ratio form and approximate spread-to-hazard route."""
    _recovery(recovery)
    if (
        not np.isfinite([no_default_value, spread, maturity]).all()
        or min(no_default_value, spread, maturity) < 0
        or recovery == 1
    ):
        raise ValueError("nonnegative single-payoff terms and recovery below one required")
    pd = constant_pd(spread / (1 - recovery), maturity)["pd"]
    return {
        "bond_ratio_value": no_default_value * math.exp(-spread * maturity),
        "hazard_value": no_default_value * (1 - (1 - recovery) * pd),
    }


def forward_credit_value(
    forward, strike, volatility, rate, maturity, default_times, interval_pd, recovery, *, notional=1
):
    """Ex24.6 discounted positive forward exposure, with independent interval Q PD.

    notional=1 reports per underlying unit (per ounce in Hull). LGD and discount
    are applied once. Forward price is a lognormal Q martingale in this example.
    """
    from . import bsm

    t = _vector(default_times)
    _recovery(recovery)
    if (
        not np.isfinite([forward, strike, volatility, rate, maturity, notional]).all()
        or min(forward, strike) <= 0
        or min(volatility, maturity, notional) < 0
        or np.any(t < 0)
        or np.any(t > maturity)
    ):
        raise ValueError("positive forward/strike and valid vol/default times/maturity required")
    pd = _interval_weights(interval_pd, 1, t.size)[0]
    sd = volatility * np.sqrt(t)
    d1 = np.full_like(sd, np.nan)
    valid = sd > 0
    d1[valid] = (math.log(forward / strike) + 0.5 * sd[valid] ** 2) / sd[valid]
    d2 = d1 - sd
    exposure = (
        notional
        * math.exp(-rate * maturity)
        * (1 - recovery)
        * bsm.call_price(forward, strike, 0, volatility, t)
    )
    cva = float(pd @ exposure)
    value = notional * (forward - strike) * math.exp(-rate * maturity)
    return {
        "d1": d1,
        "d2": d2,
        "discounted_lgd_exposure": exposure,
        "cva": cva,
        "no_default_value": value,
        "value": value - cva,
    }


def gbm_book_paths(
    spots, volatilities, correlation, times, books, *, drifts, samples=5000, seed=0, normals=None
):
    """Common correlated log-GBM paths for vectorized book(spots, time) callbacks.

    times are years from valuation time, drifts/vols annual. Each callback
    supplies its own maturity/cashflow marking convention. No new market model
    calibration is inferred. All trades share the same simulated spot paths.
    """
    from ._market_risk import _covariance

    s, vol, mu, t = _vector(spots), _vector(volatilities), _vector(drifts), _vector(times)
    if (
        s.shape != vol.shape
        or s.shape != mu.shape
        or np.any(s <= 0)
        or np.any(vol < 0)
        or t[0] < 0
        or np.any(np.diff(t) <= 0)
        or not books
    ):
        raise ValueError(
            "matching positive spots/nonnegative vols, increasing nonnegative times and books required"
        )
    corr = _covariance(correlation, s.size)
    if not np.allclose(np.diag(corr), 1):
        raise ValueError("unit diagonal correlation required")
    covariance = corr * np.outer(vol, vol)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    factor = eigenvectors * np.sqrt(np.maximum(eigenvalues, 0))
    if normals is None:
        if int(samples) != samples or samples < 1:
            raise ValueError("positive integer sample count required")
        z = np.random.default_rng(seed).normal(size=(int(samples), t.size, s.size))
    else:
        z = np.asarray(normals, dtype=float)
        if (
            z.ndim != 3
            or z.shape[1:] != (t.size, s.size)
            or z.shape[0] < 1
            or not np.isfinite(z).all()
        ):
            raise ValueError("finite (paths,times,assets) standard normals required")
    dt = np.diff(np.r_[0, t])
    increments = (z @ factor.T) * np.sqrt(dt)[None, :, None] + (mu - 0.5 * vol**2)[
        None, None, :
    ] * dt[None, :, None]
    simulated = s[None, None, :] * np.exp(np.cumsum(increments, axis=1))
    values = np.empty((z.shape[0], t.size, len(books)))
    for j, book in enumerate(books):
        for i, time in enumerate(t):
            mark = _vector(book(simulated[:, i, :], float(time)))
            if mark.size != z.shape[0]:
                raise ValueError("book callback must return one value per path")
            values[:, i, j] = mark
    return {"spots": simulated, "values": values, "times": t}


def conditional_event_weights(cumulative_pd, factor, loading):
    """Interval probabilities conditional on one Gaussian factor (explicit coupling).

    Coupling exposure to this same factor supplies an illustrative wrong/right-way
    model. It does not model feedback, dynamic contagion or first-to-default.
    """
    q, f = _vector(cumulative_pd), _vector(factor)
    if (
        np.any(q < 0)
        or np.any(q > 1)
        or np.any(np.diff(q) < 0)
        or not np.isfinite(loading)
        or abs(loading) >= 1
    ):
        raise ValueError(
            "increasing cumulative PD and factor loading strictly inside (-1,1) required"
        )
    cumulative = norm.cdf((norm.ppf(q)[None, :] - loading * f[:, None]) / math.sqrt(1 - loading**2))
    return np.diff(np.c_[np.zeros(f.size), cumulative], axis=1)


def path_credit_adjustments(
    values,
    times,
    interval_pd,
    *,
    own_pd=None,
    recovery=0.4,
    own_recovery=0.4,
    rate=0,
    netting=True,
    collateral_lag=None,
    lagged_values=None,
    threshold=0,
    pfe_confidence=0.975,
):
    """CVA/DVA on supplied common marks, with independent or path-conditional PDs.

    values is (paths,times,trades). lagged_values supplies earlier marks used to
    set collateral, not collateral cash amounts. collateral_lag is a number of
    supplied grid steps, whose early missing marks default to zero; supply
    lagged_values when prior collateral history is known. Unnetted trades have
    separate collateral sets. Bilateral terms are the educational additive
    CVA/DVA decomposition, not a simultaneous-default/first-to-default solution.
    """
    from . import xva
    from ._market_risk import empirical_risk

    marks, t = np.asarray(values, dtype=float), _vector(times)
    _recovery(recovery)
    _recovery(own_recovery)
    if (
        marks.ndim != 3
        or min(marks.shape) < 1
        or marks.shape[1] != t.size
        or not np.isfinite(marks).all()
        or t[0] < 0
        or np.any(np.diff(t) <= 0)
        or not np.isfinite([rate, threshold]).all()
        or threshold < 0
    ):
        raise ValueError(
            "finite aligned common marks, increasing times and nonnegative collateral threshold required"
        )
    n = marks.shape[0]
    value = marks.sum(axis=2) if netting else marks
    if collateral_lag is not None and lagged_values is not None:
        raise ValueError("choose supplied lagged marks or a grid lag")
    lagged = None
    if lagged_values is not None:
        lagged = np.asarray(lagged_values, dtype=float)
        if lagged.shape != value.shape or not np.isfinite(lagged).all():
            raise ValueError("lagged marks must match netted values or separate trades")
    elif collateral_lag is not None:
        if int(collateral_lag) != collateral_lag or collateral_lag < 0:
            raise ValueError("nonnegative integer grid lag required")
        lag = int(collateral_lag)
        lagged = np.zeros_like(value)
        if lag == 0:
            lagged = value.copy()
        elif lag < t.size:
            lagged[:, lag:] = value[:, :-lag]
    if lagged is None:
        positive, negative = np.maximum(value, 0), np.maximum(-value, 0)
    else:
        positive = xva.collateralized_exposure(value, lagged, threshold)
        negative = xva.collateralized_exposure(-value, -lagged, threshold)
    if not netting:
        positive, negative = positive.sum(axis=2), negative.sum(axis=2)
    cp = _interval_weights(interval_pd, n, t.size)
    own = np.zeros_like(cp) if own_pd is None else _interval_weights(own_pd, n, t.size)
    discounts = np.exp(-rate * t)
    cva_paths = ((1 - recovery) * positive * cp * discounts).sum(axis=1)
    dva_paths = ((1 - own_recovery) * negative * own * discounts).sum(axis=1)

    def se(sample):
        return float(np.std(sample, ddof=1) / math.sqrt(n)) if n > 1 else 0.0

    return {
        "positive": positive,
        "negative": negative,
        "ee": positive.mean(axis=0),
        "ene": negative.mean(axis=0),
        "pfe": np.array(
            [empirical_risk(-positive[:, i], pfe_confidence)["var"] for i in range(t.size)]
        ),
        "cva": float(cva_paths.mean()),
        "dva": float(dva_paths.mean()),
        "cva_se": se(cva_paths),
        "dva_se": se(dva_paths),
        "adjustment": float(dva_paths.mean() - cva_paths.mean()),
    }


def incremental_credit_adjustment(base_values, added_values, times, interval_pd, **kwargs):
    """New-minus-existing adjustments on identical market paths."""
    base, added = np.asarray(base_values, dtype=float), np.asarray(added_values, dtype=float)
    if base.ndim != 3 or added.ndim != 3 or base.shape[:2] != added.shape[:2]:
        raise ValueError("base and new trades must share path/time dimensions")
    before = path_credit_adjustments(base, times, interval_pd, **kwargs)
    after = path_credit_adjustments(
        np.concatenate([base, added], axis=2), times, interval_pd, **kwargs
    )
    return {key: after[key] - before[key] for key in ("cva", "dva", "adjustment")}
