"""Private synthetic same-day cash-call teachers, with physical spot Greeks.

Carry uses ACT/365 UTC seconds; integrated diffusion variance uses 252
sessions. The final thirty session minutes carry a compensated lognormal
compound-Poisson pulse. Conditioning removes Brownian randomness exactly,
but preserves the original IID Poisson/mark sampling denominator.
"""

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np
from scipy.special import erf, log_ndtr
from scipy.stats import poisson

from .zero_dte import TradingSession, variance_clock_fraction


@dataclass(frozen=True)
class ClockState:
    """Separate integrated carry years, variance, jump count and UTC seconds."""

    carry_years: float
    variance: float
    jump_mean_count: float
    remaining_seconds: float
    status: str

    def __post_init__(self):
        """Reject negative/nonfinite clocks and inconsistent expiry states."""
        clocks = (self.carry_years, self.variance, self.jump_mean_count, self.remaining_seconds)
        if not all(math.isfinite(x) and x >= 0 for x in clocks):
            raise ValueError("clocks must be finite and nonnegative")
        if self.status not in ("active", "expiry"):
            raise ValueError("clock status must be active or expiry")
        if self.status == "expiry" and any(x != 0 for x in clocks):
            raise ValueError("expiry clocks must all be zero")
        if self.status == "active" and (self.variance <= 0 or self.remaining_seconds <= 0):
            raise ValueError("active variance and remaining seconds must be positive")


@dataclass(frozen=True)
class CallParameters:
    """Annual rates and the fixed risk-neutral normal log-jump law."""

    rate: float = 0.03
    dividend: float = 0.0
    jump_mean: float = -0.05
    jump_std: float = 0.10

    def __post_init__(self):
        """Require finite rates/mark coefficients and a nonnegative mark std."""
        if not all(
            math.isfinite(x) for x in (self.rate, self.dividend, self.jump_mean, self.jump_std)
        ):
            raise ValueError("call parameters must be finite")
        if self.jump_std < 0:
            raise ValueError("jump std must be nonnegative")


def clock_state(
    timestamp, expiry, *, event, session=TradingSession(), volatility=0.20, weights=(2.0, 0.5, 2.0)
):
    """Build an aware same-day synthetic session clock, including pulse overlap.

    Expiry must be the configured session close and settlement. The pulse is the
    last thirty minutes of that synthetic session, with full mean count .028.
    Calendar configuration is supplied explicitly; no market calendar is inferred.
    """
    if (
        not isinstance(timestamp, datetime)
        or not isinstance(expiry, datetime)
        or timestamp.utcoffset() is None
        or expiry.utcoffset() is None
    ):
        raise ValueError("timestamp and expiry must be timezone-aware datetimes")
    if not math.isfinite(volatility) or volatility <= 0:
        raise ValueError("volatility must be finite and positive")
    zone = session.validate()
    local, end = timestamp.astimezone(zone), expiry.astimezone(zone)
    if local.date() != end.date():
        raise ValueError("only same-day synthetic contracts are supported")
    opening, closing = session.bounds(end.date())
    if end != closing or end != session.settlement(end.date()):
        raise ValueError("expiry must equal session close and settlement")
    seconds = (expiry.astimezone(UTC) - timestamp.astimezone(UTC)).total_seconds()
    if seconds < 0:
        raise ValueError("timestamp is after expiry")
    if not opening <= local <= closing:
        raise ValueError("timestamp lies outside the session")
    # Also validates the supplied weights at expiry.
    cumulative = variance_clock_fraction(local, session, weights=weights)
    if seconds == 0:
        return ClockState(0.0, 0.0, 0.0, 0.0, "expiry")
    pulse_start = closing - timedelta(minutes=30)
    overlap = (closing.astimezone(UTC) - max(local, pulse_start).astimezone(UTC)).total_seconds()
    count = 0.028 * max(overlap, 0.0) / 1800 if event else 0.0
    return ClockState(
        seconds / (365 * 86400), volatility**2 * (1 - cumulative) / 252, count, seconds, "active"
    )


def _inputs(spot, strike, counts, z_jump):
    s, k, n, z = np.broadcast_arrays(
        *[np.asarray(x, dtype=float) for x in (spot, strike, counts, z_jump)]
    )
    if not np.all(np.isfinite(s)) or not np.all(np.isfinite(k)) or np.any(s <= 0) or np.any(k <= 0):
        raise ValueError("spot and strike must be finite and positive")
    if not np.all(np.isfinite(n)) or np.any(n < 0) or np.any(n != np.floor(n)):
        raise ValueError("counts must be finite nonnegative integers")
    if not np.all(np.isfinite(z)):
        raise ValueError("jump normals must be finite")
    return s, k, n, z


def _drift(state, parameters):
    try:
        compensator = math.expm1(parameters.jump_mean + parameters.jump_std**2 / 2)
        return (
            parameters.rate - parameters.dividend
        ) * state.carry_years - compensator * state.jump_mean_count
    except OverflowError as exc:
        raise ValueError("overflow in jump compensator") from exc


def _expiry_values(s, k):
    at_strike = s == k
    return np.stack(
        (
            np.maximum(s - k, 0.0),
            np.where(at_strike, np.nan, (s > k).astype(float)),
            np.where(at_strike, np.nan, 0.0),
        ),
        axis=-1,
    )


def _expiry_metadata(s, k):
    undefined = bool(np.any(s == k))
    return dict(
        delta_status="undefined_atm" if undefined else "defined",
        gamma_status="undefined_atm" if undefined else "defined",
        reason="ordinary_greeks_undefined_atm_expiry" if undefined else None,
    )


def _lognormal_values(s, k, log_multiplier, variance, discount_log):
    """Evaluate lognormal call values with stable OTM difference/ITM parity.

    Using expm1/log-CDF avoids subtracting nearly equal prices, including tiny
    positive variance. The ATM extrinsic value uses erf rather than CDF minus .5.
    This numerical rearrangement never clips individual teacher spot Greeks.
    """
    shape = s.shape
    s, k, a, v = np.broadcast_arrays(s, k, log_multiplier, variance)
    shape = s.shape
    s, k, a, v = [x.ravel() for x in (s, k, a, v)]
    root = np.sqrt(v)
    log_m = np.log(s) - np.log(k) + a
    d2 = (log_m - v / 2) / root
    d1 = d2 + root
    price = np.empty(s.shape)
    atm = log_m == 0
    otm = log_m < 0
    itm = log_m > 0
    price[atm] = np.exp(discount_log) * k[atm] * erf(root[atm] / (2 * np.sqrt(2)))
    if np.any(otm):
        left = log_m[otm] + log_ndtr(d1[otm])
        ratio = np.minimum(log_ndtr(d2[otm]) - left, 0.0)
        price[otm] = np.exp(discount_log + np.log(k[otm]) + left) * (-np.expm1(ratio))
    if np.any(itm):
        left = log_ndtr(-d2[itm])
        ratio = np.minimum(log_m[itm] + log_ndtr(-d1[itm]) - left, 0.0)
        put = np.exp(discount_log + np.log(k[itm]) + left) * (-np.expm1(ratio))
        price[itm] = put + np.exp(discount_log) * k[itm] * np.expm1(log_m[itm])
    delta = np.exp(discount_log + a + log_ndtr(d1))
    gamma = np.exp(
        discount_log + a - d1 * d1 / 2 - np.log(s) - np.log(root) - math.log(2 * math.pi) / 2
    )
    result = np.stack((price, delta, gamma), axis=-1).reshape((*shape, 3))
    if not np.all(np.isfinite(result)):
        raise ValueError("nonfinite lognormal teacher result")
    return result


def conditional_values(S, K, state, parameters, counts, z_jump):
    """Return [...,3] price, physical Delta and Gamma after Brownian conditioning."""
    s, k, n, z = _inputs(S, K, counts, z_jump)
    if state.status == "expiry":
        return _expiry_values(s, k)
    with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
        try:
            log_a = (
                _drift(state, parameters)
                + n * parameters.jump_mean
                + np.sqrt(n) * parameters.jump_std * z
            )
            return _lognormal_values(
                s, k, log_a, state.variance, -parameters.rate * state.carry_years
            )
        except FloatingPointError as exc:
            raise ValueError("nonfinite or overflow in conditional teacher") from exc


def path_values(S, K, state, parameters, counts, z_brown, z_jump):
    """Raw payoff, PW/LR Delta, LR-PW/LR2 Gamma and zero naive-Gamma samples.

    All Brownian/Poisson/mark draws are caller-supplied. Gamma scores require
    positive integrated variance. Individual payoffs/Greeks have no spot bound.
    """
    s, k, n, zj, zb = np.broadcast_arrays(
        *_inputs(S, K, counts, z_jump), np.asarray(z_brown, dtype=float)
    )
    if not np.all(np.isfinite(zb)):
        raise ValueError("Brownian normals must be finite")
    if state.status == "expiry":
        values = _expiry_values(s, k)
        return dict(
            price=values[..., 0],
            pw_delta=values[..., 1],
            lr_delta=values[..., 1],
            lrpw_gamma=values[..., 2],
            lr2_gamma=values[..., 2],
            naive_gamma=np.zeros(s.shape),
            terminal_spot=s.copy(),
            **_expiry_metadata(s, k),
        )
    with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
        try:
            root = math.sqrt(state.variance)
            terminal = s * np.exp(
                _drift(state, parameters)
                - state.variance / 2
                + root * zb
                + n * parameters.jump_mean
                + np.sqrt(n) * parameters.jump_std * zj
            )
            discount = math.exp(-parameters.rate * state.carry_years)
            payoff = discount * np.maximum(terminal - k, 0.0)
            indicator = terminal > k
            result = dict(
                price=payoff,
                pw_delta=discount * terminal / s * indicator,
                lr_delta=payoff * zb / (s * root),
                lrpw_gamma=discount * terminal / (s * s) * indicator * (zb / root - 1),
                lr2_gamma=payoff * (zb * zb - zb * root - 1) / (s * s * state.variance),
                naive_gamma=np.zeros(s.shape),
                terminal_spot=terminal,
            )
            if any(not np.all(np.isfinite(x)) for x in result.values()):
                raise ValueError("nonfinite raw teacher result")
            return {**result, "delta_status": "defined", "gamma_status": "defined", "reason": None}
        except (FloatingPointError, OverflowError) as exc:
            raise ValueError("nonfinite or overflow in raw teacher") from exc


def _integer_count(value, name, minimum=0):
    if not isinstance(value, (int, np.integer)) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(value)


def mixture_values(S, K, state, parameters, nmax=8):
    """Ordinary-Poisson count mixture and separate rigorous C/Delta/Gamma tails.

    The Gamma bound uses physical units 1/spot and the original positive W.
    The tilted Poisson mean Lambda*exp(mu+sigma²/2) enters only the tail bound.
    """
    nmax = _integer_count(nmax, "nmax")
    s, k, _, _ = _inputs(S, K, 0, 0.0)
    if state.status == "expiry":
        return dict(
            values=_expiry_values(s, k),
            tail_bounds=np.zeros((*s.shape, 3)),
            terms=1,
            status="expiry",
            **_expiry_metadata(s, k),
        )
    counts = np.arange(1 if state.jump_mean_count == 0 else nmax + 1)
    probabilities = poisson.pmf(counts, state.jump_mean_count)
    with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
        try:
            log_a = _drift(state, parameters) + counts * (
                parameters.jump_mean + parameters.jump_std**2 / 2
            )
            variance = state.variance + counts * parameters.jump_std**2
            term_values = _lognormal_values(
                s[..., None], k[..., None], log_a, variance, -parameters.rate * state.carry_years
            )
            values = np.sum(term_values * probabilities[:, None], axis=-2)
            tilted = state.jump_mean_count * math.exp(
                parameters.jump_mean + parameters.jump_std**2 / 2
            )
            tail = poisson.sf(nmax, tilted)
            base = math.exp(-parameters.dividend * state.carry_years) * tail
            tail_bounds = np.stack(
                (
                    s * base,
                    np.full(s.shape, base),
                    base / (s * math.sqrt(2 * math.pi * state.variance)),
                ),
                axis=-1,
            )
            if not np.all(np.isfinite(values)) or not np.all(np.isfinite(tail_bounds)):
                raise ValueError("nonfinite mixture values or tail bounds")
        except (FloatingPointError, OverflowError) as exc:
            raise ValueError("nonfinite or overflow in mixture") from exc
    return dict(
        values=values,
        tail_bounds=tail_bounds,
        terms=len(counts),
        per_term_values=term_values,
        probabilities=probabilities,
        status="analytic_deterministic" if state.jump_mean_count == 0 else "truncated_mixture",
        delta_status="defined",
        gamma_status="defined",
        reason=None,
    )


def compact_teacher(S, K, state, parameters, *, sample_count, count_seed, jump_seed):
    """Generate original IID counts and save only nonzero-count normal marks.

    All N count draws are performed before the independent active-only normal
    stream. Sorted original indices preserve prefix sampling. Lambda=0 performs
    zero random draws and keeps its reservation separate from observed MC count.
    """
    n = _integer_count(sample_count, "sample_count", 2)
    zero_values = conditional_values(S, K, state, parameters, 0, 0.0)
    if zero_values.shape != (3,):
        raise ValueError("compact teacher requires scalar spot and strike")
    analytic = state.jump_mean_count == 0
    if analytic:
        indices = counts = np.empty(0, dtype=np.int64)
        marks = np.empty(0)
        active_values = np.empty((0, 3))
    else:
        original_counts = np.random.default_rng(count_seed).poisson(state.jump_mean_count, n)
        indices = np.flatnonzero(original_counts).astype(np.int64)
        counts = original_counts[indices].astype(np.int64)
        marks = np.random.default_rng(jump_seed).standard_normal(len(indices))
        active_values = conditional_values(S, K, state, parameters, counts, marks)
    active = len(indices)
    status = (
        "analytic_deterministic"
        if analytic
        else "rare_event_unobserved"
        if active == 0
        else "rare_event_unresolved"
        if active < 100
        else "ready"
    )
    return dict(
        sample_count=n,
        reserved_sample_count=n,
        observed_mc_count=0 if analytic else n,
        zero_count=0 if analytic else n - active,
        zero_values=zero_values,
        active_indices=indices,
        active_counts=counts,
        z_jump=marks,
        active_values=active_values,
        normal_draw_policy="active_only",
        count_draws=0 if analytic else n,
        normal_draws=active,
        actual_random_draws=0 if analytic else n + active,
        status=status,
        **_expiry_metadata(np.asarray(S), np.asarray(K)) if state.status == "expiry" else {},
    )


def _active_moments(values, origin):
    """Shift by a shared zero-block origin before 3-vector Chan aggregation."""
    n = len(values)
    if n == 0:
        return 0, np.zeros(3), np.zeros((3, 3))
    shifted = values - origin
    average = shifted.mean(axis=0)
    deviations = shifted - average
    return n, average, deviations.T @ deviations


def compact_moments(compact, *, sample_count=None):
    """Reconstruct original-N joint IID moments, optionally at a saved prefix.

    The zero block is constant and merged with shifted active moments using
    Chan's covariance identity. Rare-component warnings retain the original
    finite moments; they do not certify precision or change the estimator.
    Prefix moments keep the full generation's actual random-draw count;
    ``prefix_equivalent_draws`` describes the selected prefix only.
    """
    reservation = _integer_count(compact["sample_count"], "sample_count", 2)
    n = (
        reservation
        if sample_count is None
        else _integer_count(sample_count, "prefix sample_count", 2)
    )
    if n > reservation:
        raise ValueError("prefix cannot exceed original sample_count")
    zero = np.asarray(compact["zero_values"], dtype=float)
    if zero.shape != (3,):
        raise ValueError("zero_values must have three components")
    if compact["status"] == "analytic_deterministic":
        return dict(
            count=0,
            reserved_sample_count=n,
            mean=zero.copy(),
            m2_matrix=np.zeros((3, 3)),
            covariance=np.zeros((3, 3)),
            se=np.zeros(3),
            active_count=0,
            zero_count=0,
            actual_random_draws=0,
            prefix_equivalent_draws=0,
            status="analytic_deterministic",
            reason=compact.get("reason"),
            delta_status=compact.get("delta_status", "defined"),
            gamma_status=compact.get("gamma_status", "defined"),
        )
    indices = np.asarray(compact["active_indices"])
    values = np.asarray(compact["active_values"], dtype=float)
    if (
        indices.ndim != 1
        or not np.issubdtype(indices.dtype, np.integer)
        or np.any(indices < 0)
        or np.any(indices >= reservation)
        or np.any(np.diff(indices) <= 0)
        or values.shape != (len(indices), 3)
        or not np.all(np.isfinite(values))
        or not np.all(np.isfinite(zero))
        or compact["zero_count"] != reservation - len(indices)
    ):
        raise ValueError("invalid compact original counts, indices or teacher values")
    with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
        try:
            active, delta, m2 = _active_moments(values[indices < n], zero)
            zeros = n - active
            m2 += np.outer(delta, delta) * (active * zeros / n)
            mean = zero + delta * (active / n)
            covariance = m2 / (n - 1)
            se = np.sqrt(np.maximum(np.diag(m2), 0.0) / (n * (n - 1)))
            if not np.all(np.isfinite(mean)) or not np.all(np.isfinite(m2)):
                raise ValueError("nonfinite compact moments")
        except FloatingPointError as exc:
            raise ValueError("nonfinite or overflow in compact moments") from exc
    status = (
        "rare_event_unobserved"
        if active == 0
        else "rare_event_unresolved"
        if active < 100
        else "ready"
    )
    return dict(
        count=n,
        reserved_sample_count=n,
        mean=mean,
        m2_matrix=m2,
        covariance=covariance,
        se=se,
        active_count=active,
        zero_count=zeros,
        actual_random_draws=compact["actual_random_draws"],
        prefix_equivalent_draws=n + active,
        status=status,
    )
