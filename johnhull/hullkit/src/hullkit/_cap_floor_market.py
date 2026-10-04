"""Private Hull §29.2 cap/floor market conventions and backward-RFR benchmarks.

All rates and accruals use declared annual/day-count units. Fixing controls
volatility time; payment controls discounting. Negative rates use normal or
shifted Black. Hull's observation-midpoint RFR formula is explicitly an
approximation; an exact discrete Gaussian overnight model is kept separate.
"""

import math
from itertools import pairwise

import numpy as np
from scipy.optimize import brentq
from scipy.special import ndtr

from ._forward_black import forward_black_price


def _value(x):
    if not np.all(np.isfinite(x)):
        raise ValueError("finite rate-option result required")
    return float(x) if np.ndim(x) == 0 else x


def rate_option_price(
    discount, forward, strike, volatility, expiry, kind="call", *, model="black", shift=0.0
):
    """Black relative vol, shifted relative vol, or Bachelier absolute rate vol."""
    if model in ("black", "shifted"):
        adjustment = shift if model == "shifted" else 0.0
        return forward_black_price(
            discount,
            np.asarray(forward) + adjustment,
            np.asarray(strike) + adjustment,
            volatility,
            expiry,
            kind,
        )
    if model != "normal" or kind not in ("call", "put"):
        raise ValueError("model/kind must be black, shifted or normal and call/put")
    p, F, K, s, T = np.broadcast_arrays(
        *[np.asarray(x, dtype=float) for x in (discount, forward, strike, volatility, expiry)]
    )
    if np.any(p <= 0) or np.any(s < 0) or np.any(T < 0):
        raise ValueError("positive discount and nonnegative vol/expiry required")
    w = s * np.sqrt(T)
    safe = np.where(w == 0, 1.0, w)
    sign = 1 if kind == "call" else -1
    d = sign * (F - K) / safe
    live = sign * (F - K) * ndtr(d) + w * np.exp(-d * d / 2) / math.sqrt(2 * math.pi)
    return _value(p * np.where(w == 0, np.maximum(sign * (F - K), 0), live))


def black_rate_d(forward, strike, volatility, expiry, shift=0.0):
    F, K, s, T = np.broadcast_arrays(
        *[
            np.asarray(x, dtype=float)
            for x in (np.asarray(forward) + shift, np.asarray(strike) + shift, volatility, expiry)
        ]
    )
    if np.any(F <= 0) or np.any(K <= 0) or np.any(s <= 0) or np.any(T <= 0):
        raise ValueError("positive forward/strike/volatility/expiry required for d values")
    w = s * np.sqrt(T)
    d1 = np.log(F / K) / w + w / 2
    return _value(d1), _value(d1 - w)


def _kind(kind):
    if kind not in ("cap", "floor"):
        raise ValueError("kind must be cap or floor")
    return "call" if kind == "cap" else "put"


def caplet_payment(notional, accrual, rate, strike, kind="cap"):
    sign = 1 if _kind(kind) == "call" else -1
    L, a, R, K = np.broadcast_arrays(
        *[np.asarray(x, dtype=float) for x in (notional, accrual, rate, strike)]
    )
    if np.any(L < 0) or np.any(a <= 0):
        raise ValueError("nonnegative notional and positive accrual required")
    return _value(L * a * np.maximum(sign * (R - K), 0))


def caplet_bond_payoff(notional, accrual, rate, strike, kind="cap"):
    """Value at fixing as ZCB put/call: face L*(1+K*alpha), strike L."""
    L, a, R, K = np.broadcast_arrays(
        *[np.asarray(x, dtype=float) for x in (notional, accrual, rate, strike)]
    )
    if np.any(1 + a * R <= 0):
        raise ValueError("positive simple accumulation factor required")
    sign = 1 if _kind(kind) == "call" else -1
    return _value(np.maximum(sign * (L - L * (1 + a * K) / (1 + a * R)), 0))


def caplet_price(
    notional,
    accrual,
    discount,
    forward,
    strike,
    volatility,
    fixing,
    kind="cap",
    *,
    model="black",
    shift=0.0,
):
    L, a = np.asarray(notional, dtype=float), np.asarray(accrual, dtype=float)
    if np.any(L < 0) or np.any(a <= 0):
        raise ValueError("nonnegative notional and positive accrual required")
    return _value(
        L
        * a
        * rate_option_price(
            discount, forward, strike, volatility, fixing, _kind(kind), model=model, shift=shift
        )
    )


def cap_floor_price(
    notional,
    accruals,
    discounts,
    forwards,
    strike,
    volatilities,
    fixings,
    kind="cap",
    *,
    model="black",
    shift=0.0,
):
    """Sum future caplets; an already fixed initial coupon is declared separately."""
    return float(
        np.sum(
            caplet_price(
                notional,
                accruals,
                discounts,
                forwards,
                strike,
                volatilities,
                fixings,
                kind,
                model=model,
                shift=shift,
            )
        )
    )


def strip_cap_volatilities(notional, accruals, discounts, forwards, strike, fixings, cap_prices):
    """Black spot vols from nested cap prices, with per-leg arbitrage bounds."""
    a, p, F, T, prices = [
        np.asarray(x, dtype=float) for x in (accruals, discounts, forwards, fixings, cap_prices)
    ]
    if a.ndim != 1 or any(x.shape != a.shape for x in (p, F, T, prices)) or len(a) == 0:
        raise ValueError("matching nonempty cap vectors required")
    targets = np.diff(np.r_[0.0, prices])
    vols = []
    for al, df, f, t, target in zip(a, p, F, T, targets, strict=True):
        intrinsic = caplet_price(notional, al, df, f, strike, 0.0, t)
        upper = notional * al * df * f
        if target < intrinsic - 1e-8 or target >= upper:
            raise ValueError("cap increment outside Black caplet bounds")
        if abs(target - intrinsic) <= 1e-8:
            vols.append(0.0)
            continue
        if t == 0:
            raise ValueError("already fixed caplet cannot identify a spot volatility")

        def price(v, al=al, df=df, f=f, t=t):
            return caplet_price(notional, al, df, f, strike, v, t)

        hi = 1.0
        while price(hi) < target:
            hi *= 2
            if hi > 128:
                raise ValueError("spot volatility root could not be bracketed")
        vols.append(
            brentq(lambda v, price=price, target=target: price(v) - target, 0.0, hi, xtol=1e-13)
        )
    return np.array(vols)


def flat_cap_vols_to_spot(notional, accruals, discounts, forwards, strike, fixings, flat_vols):
    """Price each cap with its own quoted flat vol, then strip caplet increments."""
    a, p, F, t, q = [
        np.asarray(x, dtype=float) for x in (accruals, discounts, forwards, fixings, flat_vols)
    ]
    if a.ndim != 1 or any(x.shape != a.shape for x in (p, F, t, q)):
        raise ValueError("matching flat-vol quote and cap vectors required")
    caps = np.array(
        [
            cap_floor_price(notional, a[: i + 1], p[: i + 1], F[: i + 1], strike, q[i], t[: i + 1])
            for i in range(len(q))
        ]
    )
    return strip_cap_volatilities(notional, a, p, F, strike, t, caps)


def zero_cost_collar_floor_strike(
    notional, accruals, discounts, forwards, cap_strike, volatilities, fixings
):
    target = cap_floor_price(
        notional, accruals, discounts, forwards, cap_strike, volatilities, fixings
    )

    def floor(k):
        return cap_floor_price(
            notional, accruals, discounts, forwards, k, volatilities, fixings, "floor"
        )

    upper = max(float(np.max(forwards)), float(cap_strike), 0.1)
    while floor(upper) < target:
        upper *= 2
    return brentq(lambda k: floor(k) - target, 1e-12, upper, xtol=1e-14)


def backward_cap_schedule(start, end, tenor):
    """Work backward; merge a first stub shorter than half a normal period."""
    if not 0 <= start < end or tenor <= 0:
        raise ValueError("0<=start<end and positive tenor required")
    count = math.floor((end - start) / tenor)
    grid = [end - i * tenor for i in range(count + 1)]
    grid = sorted(x for x in grid if x > start + 1e-12)
    if len(grid) > 1 and grid[0] - start < tenor / 2 - 1e-12:
        grid = grid[1:]
    points = [start, *grid]
    return np.array(list(pairwise(points)))


def actual_year_fraction(start, end, basis=360):
    if basis <= 0 or end < start:
        raise ValueError("positive day-count basis and nonnegative date interval required")
    return (end - start).days / basis


def simple_forward_from_discounts(fixing_discount, payment_discount, accrual):
    p, q, a = np.broadcast_arrays(
        *[np.asarray(x, dtype=float) for x in (fixing_discount, payment_discount, accrual)]
    )
    if np.any(p <= 0) or np.any(q <= 0) or np.any(a <= 0):
        raise ValueError("positive discounts and accrual required")
    return _value((p / q - 1) / a)


def rfr_forward_from_ois(known_factor, fixing_discount, payment_discount, total_accrual):
    if known_factor <= 0 or fixing_discount <= 0 or payment_discount <= 0 or total_accrual <= 0:
        raise ValueError("positive observed factor/discounts/accrual required")
    return (known_factor * fixing_discount / payment_discount - 1) / total_accrual


def compound_observed_rate(daily_rates, daily_accruals):
    r, a = np.broadcast_arrays(
        np.asarray(daily_rates, dtype=float), np.asarray(daily_accruals, dtype=float)
    )
    if np.any(a <= 0) or np.any(1 + r * a <= 0) or not a.size:
        raise ValueError("positive daily factors/accruals required")
    return _value(np.expm1(np.sum(np.log1p(r * a))) / np.sum(a))


def rfr_midpoint_caplet_price(
    notional,
    total_accrual,
    discount,
    forward,
    strike,
    volatility,
    remaining_observation_times,
    *,
    now=0.0,
    kind="cap",
    model="black",
    shift=0.0,
):
    """Hull quick-and-dirty average remaining observation time; model-dependent bias.

    Supply a forward that already includes the observed compounded factor;
    pass only the remaining observation dates. Relative Black vol and the
    midpoint alone do not reproduce an arbitrary daily-compounding model.
    """
    times = np.asarray(remaining_observation_times, dtype=float) - now
    if np.any(times < 0):
        raise ValueError("only remaining observation dates may be supplied")
    expiry = float(np.mean(times)) if times.size else 0.0
    return caplet_price(
        notional,
        total_accrual,
        discount,
        forward,
        strike,
        volatility,
        expiry,
        kind,
        model=model,
        shift=shift,
    )


def gaussian_backward_rfr_statistics(
    observation_times, daily_accruals, rate, rate_volatility, total_accrual, known_factor=1.0
):
    """Exact discrete Gaussian overnight bank account, conditional at current time.

    Daily factors are exp((r+eta*W_t)*alpha), with contiguous remaining days.
    Before accrual starts the bank account uses a continuous Brownian rate
    integral. The payment-measure tilt uses its covariance with the daily
    log product; once started, known_factor includes all observed factors.
    This synthetic benchmark is not an empirical OIS calibration.
    """
    t, a = np.asarray(observation_times, dtype=float), np.asarray(daily_accruals, dtype=float)
    if (
        t.ndim != 1
        or a.shape != t.shape
        or not t.size
        or np.any(t < 0)
        or np.any(a <= 0)
        or rate_volatility < 0
        or total_accrual <= 0
        or known_factor <= 0
        or not np.allclose(np.diff(t), a[:-1], atol=1e-12, rtol=1e-12)
    ):
        raise ValueError(
            "contiguous nonnegative observations and positive factors/accruals required"
        )
    start = float(t[0])
    remaining = float(a.sum())
    eta2 = rate_volatility**2
    core = float(a @ np.minimum.outer(t, t) @ a)
    va = eta2 * core
    cov = va + eta2 * start**2 * remaining / 2
    vj = eta2 * (start**3 / 3 + core + start**2 * remaining)
    mj = rate * (start + remaining)
    ma = rate * remaining
    discount = math.exp(-mj + vj / 2)
    fixing = math.exp(-rate * start + eta2 * start**3 / 6)
    growth = known_factor * math.exp(ma - cov + va / 2)
    return dict(
        discount=discount,
        fixing_discount=fixing,
        total_accrual=total_accrual,
        known_factor=known_factor,
        forward_growth=growth,
        forward_rate=(growth - 1) / total_accrual,
        log_growth_mean_Q=math.log(known_factor) + ma,
        log_growth_variance=va,
        log_growth_mean_payment=math.log(known_factor) + ma - cov,
        variance_integral=vj,
        cov_growth_integral=cov,
    )


def gaussian_backward_rfr_price(notional, strike, statistics, kind="cap"):
    """Exact transformed-growth Black value in the declared daily Gaussian model."""
    row = statistics
    cash_strike = 1 + row["total_accrual"] * strike
    return notional * forward_black_price(
        row["discount"],
        row["forward_growth"],
        cash_strike,
        math.sqrt(row["log_growth_variance"]),
        1.0,
        _kind(kind),
    )
