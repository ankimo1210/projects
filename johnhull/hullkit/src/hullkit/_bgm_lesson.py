"""Private single-curve lognormal LMM experiments for Hull 11e §33.2.

The tenor is T_0=0<...<T_N, delta_i=T_(i+1)-T_i, with positive simple
F_i=(P(T_i)/P(T_(i+1))-1)/delta_i. F_0 is fixed at time zero. On
[T_j,T_(j+1)) only i>=j+1 evolve; fixings are recorded before advancing the
integer event index. Rates and spreads are decimal annual simple rates,
times/accruals are years, and relative factor loadings have units year^-1/2.
Factors are independent Brownian motions; correlation is the row inner
product. The same factor increment is shared by all live rates.

"rolling" uses the discrete reinvestment account, "terminal" the final
tenor bond, and "payment" a specified unexpired tenor bond. The returned
discount weights belong to that measure; a terminal path must not be
discounted with its rolling account. All priced events are on tenor dates:
live forwards alone do not specify non-tenor stub-bond dynamics. Log Euler
and simultaneous predictor-corrector are finite-step approximations.

Raw Tables 33.4/5 retain their rounded components. Rescaling their norms
is an explicit, separate synthetic marginal-preservation experiment.
Ratchet and sticky contracts start at reset T_1; sticky requires caller K_0.
The flexicap is caller-strike, first-positive-exercises with a quota, not
an optimal selection of future coupons. The source prices 3.43/3.58/3.61
lack the strike and complete schedule needed for a numerical price pin.

Frozen swaption diffusion uses gamma_i=F_i/S*dS/dF_i, including the
forward-dependent annuity; freezing simple annuity weights is different.
Coarse swap tenors are products of fine simple-rate accrual factors.
This product Jacobian avoids the undefined lower index n printed in
Eq. 33.19; summing all swap subperiods gives the Eq. 33.18 special case.
PCA inputs are relative log-forward changes. The small calibration helper
fits two-factor directions to frozen European prices with caplet norms
fixed, and is a synthetic teaching fit, not empirical market recovery.
CEV, Bermudan exercise, multicurve dynamics, and production calibration
are outside this private lognormal experiment.
"""

import numpy as np
from scipy.optimize import least_squares

from ._forward_black import _real, forward_black_price


def _vector(value, name):
    result = _real(value, name)
    if result.ndim != 1 or result.size == 0:
        raise ValueError(f"{name} must be a nonempty real vector")
    return result


def _integer(value, name, lower=0):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < lower:
        raise ValueError(f"{name} must be an integer >= {lower}")
    return int(value)


def _tenor(times):
    t = _vector(times, "times")
    if t.size < 2 or t[0] != 0 or np.any(np.diff(t) <= 0):
        raise ValueError("times must be a strictly increasing tenor starting at zero")
    return t, np.diff(t)


def _curve(forwards, accruals):
    f = _real(forwards, "forwards")
    delta = _vector(accruals, "accruals")
    if f.ndim < 1 or f.shape[-1] != delta.size or np.any(f <= 0) or np.any(delta <= 0):
        raise ValueError("positive forwards and matching positive accruals required")
    return f, delta


def _loadings(value, rows=None):
    loading = _real(value, "loadings")
    if loading.ndim != 2 or min(loading.shape) == 0 or (rows is not None and loading.shape[0] != rows):
        raise ValueError("loadings must have matching rate rows and at least one factor")
    return loading


def tenor_forwards(times, discounts):
    """Convert a normalized positive zero-bond curve into annual simple forwards."""
    _, delta = _tenor(times)
    p = _vector(discounts, "discounts")
    if p.size != delta.size + 1 or p[0] != 1 or np.any(p <= 0):
        raise ValueError("discounts must be positive, match the tenor, and start at one")
    f = np.expm1(np.log(p[:-1]) - np.log(p[1:])) / delta
    if np.any(f <= 0):
        raise ValueError("this lognormal lesson requires positive simple forwards")
    return f


def bootstrap_forward_vols(reset_times, spot_vols):
    """Solve sigma_k^2 T_k=sum_(i=1)^k Lambda_(k-i)^2 delta_(i-1).

    reset_times includes zero and the last reset. This triangular solution
    also handles unequal accruals. Only 64 floating-point epsilons of scaled
    variance cancellation are tolerated; incompatible negative variances
    are rejected, not silently floored as a calibration policy.
    """
    t, delta = _tenor(reset_times)
    sigma = _vector(spot_vols, "spot_vols")
    if sigma.size != delta.size or np.any(sigma < 0):
        raise ValueError("nonnegative spot vols must match reset times")
    total = sigma**2 * t[1:]
    variance = np.zeros_like(sigma)
    for k in range(sigma.size):
        old = np.dot(variance[:k][::-1], delta[1:k + 1])
        remaining = total[k] - old
        tolerance = 64 * np.finfo(float).eps * max(total[k], old, np.finfo(float).tiny)
        if remaining < -tolerance:
            raise ValueError("negative implied forward variance")
        variance[k] = max(remaining, 0) / delta[0]
    return np.sqrt(variance)


def loading_diagnostics(loadings, printed_norms=None):
    """Return raw norms, covariance/correlation and signed rounding residuals.

    Zero-vol rows have zero reported correlations, including their diagonal.
    No normalization is performed here.
    """
    loading = _loadings(loadings)
    covariance = loading @ loading.T
    norms = np.linalg.norm(loading, axis=1)
    outer = np.outer(norms, norms)
    correlation = np.divide(covariance, outer, out=np.zeros_like(covariance), where=outer > 0)
    result = {"norms": norms, "covariance": covariance, "correlation": correlation}
    if printed_norms is not None:
        printed = _vector(printed_norms, "printed_norms")
        if printed.size != norms.size or np.any(printed < 0):
            raise ValueError("printed norms must be matching nonnegative decimal vols")
        result["rounding_difference"] = norms - printed
    return result


def rescale_loading_norms(loadings, target_norms):
    """Explicitly preserve directions while setting row norms for synthetic checks."""
    loading = _loadings(loadings)
    target = _vector(target_norms, "target_norms")
    if target.size != loading.shape[0] or np.any(target < 0):
        raise ValueError("matching nonnegative target norms required")
    current = np.linalg.norm(loading, axis=1)
    if np.any((current == 0) & (target > 0)):
        raise ValueError("positive target norm has an undefined zero factor direction")
    scale = np.divide(target, current, out=np.zeros_like(target), where=current > 0)
    return loading * scale[:, None]


def _measure_index(measure, payment_index, n, alive):
    if measure == "rolling":
        if payment_index is not None:
            raise ValueError("payment_index applies only to the payment measure")
        return alive
    if measure == "terminal":
        if payment_index is not None:
            raise ValueError("terminal numeraire is the final tenor bond")
        return n
    if measure == "payment":
        p = _integer(payment_index, "payment_index", 1)
        if p > n or p < alive:
            raise ValueError("payment numeraire must be an unexpired tenor bond")
        return p
    raise ValueError("measure must be rolling, terminal, or payment")


def _drift(f, delta, loading, alive, p):
    w = delta * f / (1 + delta * f)
    out = np.zeros_like(f)
    # Cumulated vector exposures avoid forming a path-by-rate covariance cube.
    if p <= alive:
        exposure = np.cumsum(w[..., alive:, None] * loading[alive:], axis=-2)
        out[..., alive:] = np.sum(exposure * loading[alive:], axis=-1)
    else:
        terms = w[..., alive:, None] * loading[alive:]
        cumulative = np.cumsum(terms, axis=-2)
        zero = np.zeros((*f.shape[:-1], 1, loading.shape[1]))
        prefix = np.concatenate([zero, cumulative], axis=-2)
        # exposure v_p-v_(k+1) = prefix(k+1)-prefix(p).
        exposures = prefix[..., 1:, :] - prefix[..., p - alive:p - alive + 1, :]
        out[..., alive:] = np.sum(exposures * loading[alive:], axis=-1)
    return out


def lmm_drift(forwards, accruals, loadings, alive, measure="rolling", payment_index=None):
    """Return relative drifts under rolling, terminal, or a common payment bond.

    Under rolling Q^B the sum runs alive..k including self, with a plus sign.
    Under Q^p it runs p..k for k>=p, or -(k+1)..(p-1) for k<p. Thus only
    F_(p-1) has zero drift under its own payment measure. Fixed rates return
    zero, including any nonzero loading supplied on their unused rows.
    Leading path dimensions broadcast; all forwards are updated together.
    """
    f, delta = _curve(forwards, accruals)
    n = delta.size
    a = _integer(alive, "alive")
    if a > n:
        raise ValueError("alive must be within the tenor")
    loading = _loadings(loadings, n)
    p = _measure_index(measure, payment_index, n, a)
    if a == n:
        return np.zeros_like(f)
    return _drift(f, delta, loading, a, p)


def simulate_lmm(
    times, initial_forwards, loadings, paths, steps_per_period, rng, *,
    measure="rolling", payment_index=None, stationary=False, scheme="pc",
    antithetic=True, stop_reset=None
):
    """Simulate a positive single-curve LMM and return tenor-event estimators.

    Constant loadings have N rows. stationary=True instead takes N-1 rows,
    assigning row i-alive to rate i on each period (Tables 33.1/4/5).
    steps_per_period is an integer; unequal periods each receive that many
    equal substeps. "euler" is log Euler; "pc" recomputes every drift from
    one simultaneous predictor and averages old/predicted drifts.

    fixings, payment_weights, reset_discount_weights and bank_accounts are
    shaped (paths, observed resets); reset_states is (reset, paths, N).
    payment_weights multiply cashflows known at T_k and paid T_(k+1).
    reset_discount_weights multiply immediate exercise values at T_k.
    These weights include initial numeraire value. Payment measure stops
    before its numeraire expires. No stub interpolation is implied.

    Antithetic ordering is [Z paths, -Z paths] for every shared factor step;
    mc_estimate must average those pairs before estimating uncertainty.
    The supplied Generator controls reproducibility, not printed-price fits.
    """
    t, delta = _tenor(times)
    initial = _vector(initial_forwards, "initial_forwards")
    if initial.size != delta.size or np.any(initial <= 0):
        raise ValueError("positive initial forwards must match the tenor")
    n = initial.size
    count = _integer(paths, "paths", 2)
    substeps = _integer(steps_per_period, "steps_per_period", 1)
    if not isinstance(antithetic, (bool, np.bool_)) or not isinstance(stationary, (bool, np.bool_)):
        raise ValueError("antithetic and stationary must be booleans")
    if antithetic and (count % 2 or count < 4):
        raise ValueError("antithetic simulation needs an even number of paths >= 4")
    if not isinstance(rng, np.random.Generator):
        raise ValueError("rng must be a NumPy Generator")
    if scheme not in ("euler", "pc"):
        raise ValueError("scheme must be euler or pc")
    if stationary and n < 2:
        raise ValueError("stationary loading schedule needs at least two rates")
    source = _loadings(loadings, n - 1 if stationary else n)
    p = _measure_index(measure, payment_index, n, 1 if n > 1 else 0)
    maximum = min(n - 1, p - 1) if measure == "payment" else n - 1
    last = maximum if stop_reset is None else _integer(stop_reset, "stop_reset")
    if last > maximum:
        raise ValueError("stop_reset exceeds the last fixing or numeraire maturity")
    f = np.broadcast_to(initial, (count, n)).copy()
    initial_discounts = np.r_[1, 1 / np.cumprod(1 + delta * initial)]
    bank = np.ones(count)
    fixings = np.empty((count, last + 1))
    payment_weights = np.empty_like(fixings)
    reset_weights = np.empty_like(fixings)
    banks = np.empty_like(fixings)
    states = np.empty((last + 1, count, n))
    for j in range(last + 1):
        # Save left-limit fixing, then freeze this rate on the next interval.
        states[j] = f
        fixings[:, j] = f[:, j]
        banks[:, j] = bank
        if measure == "rolling":
            reset_weights[:, j] = 1 / bank
        else:
            reset_weights[:, j] = initial_discounts[p] * np.prod(
                1 + delta[j:p] * f[:, j:p], axis=1
            )
        payment_weights[:, j] = reset_weights[:, j] / (1 + delta[j] * f[:, j])
        bank *= 1 + delta[j] * f[:, j]
        if j == last:
            break
        alive = j + 1
        loading = np.zeros((n, source.shape[1])) if stationary else source
        if stationary:
            loading[alive:] = source[:n - alive]
        variance = np.sum(loading[alive:]**2, axis=1)
        current_p = alive if measure == "rolling" else p
        dt = delta[j] / substeps
        for _ in range(substeps):
            z = rng.standard_normal((count // 2 if antithetic else count, source.shape[1]))
            if antithetic:
                z = np.concatenate([z, -z], axis=0)
            noise = (z @ loading[alive:].T) * np.sqrt(dt)
            mu = _drift(f, delta, loading, alive, current_p)[..., alive:]
            exponent = (mu - 0.5 * variance) * dt + noise
            if scheme == "pc":
                predicted = f.copy()
                predicted[:, alive:] *= np.exp(exponent)
                new_mu = _drift(predicted, delta, loading, alive, current_p)[:, alive:]
                exponent = (0.5 * (mu + new_mu) - 0.5 * variance) * dt + noise
            with np.errstate(over="raise", invalid="raise", under="ignore"):
                try:
                    f[:, alive:] *= np.exp(exponent)
                except FloatingPointError as exc:
                    raise ValueError("LMM step is not representable") from exc
            if np.any(f[:, alive:] <= 0) or not np.all(np.isfinite(f[:, alive:])):
                raise ValueError("positive LMM forward underflowed or overflowed")
    if not np.all(np.isfinite(payment_weights)) or not np.all(np.isfinite(states)):
        raise ValueError("LMM event values are not representable")
    return {
        "fixings": fixings, "payment_weights": payment_weights,
        "reset_discount_weights": reset_weights, "bank_accounts": banks,
        "reset_states": states, "initial_discounts": initial_discounts,
        "times": t[:last + 1], "measure": measure, "payment_index": p,
        "antithetic": bool(antithetic), "scheme": scheme
    }


def mc_estimate(discounted_values, *, antithetic=True):
    """Mean and sample standard error of independent paths or antithetic pairs.

    Axis zero contains paths; trailing coupon dimensions remain separate.
    Sum coupons pathwise before calling for a total price: the total SE
    includes their covariance and cannot be obtained by summing coupon SEs.
    """
    values = _real(discounted_values, "discounted_values")
    if values.ndim < 1 or values.shape[0] < 2:
        raise ValueError("at least two independent observations required")
    if not isinstance(antithetic, (bool, np.bool_)):
        raise ValueError("antithetic must be boolean")
    if antithetic:
        if values.shape[0] % 2 or values.shape[0] < 4:
            raise ValueError("at least two complete antithetic pairs required")
        half = values.shape[0] // 2
        samples = 0.5 * (values[:half] + values[half:])
    else:
        samples = values
    return {
        "mean": np.mean(samples, axis=0),
        "standard_error": np.std(samples, axis=0, ddof=1) / np.sqrt(samples.shape[0]),
        "independent_observations": samples.shape[0]
    }


def cap_cashflows(
    fixings, accruals, kind, *, strike=None, spread=0, initial_strike=None,
    max_exercises=None, first_reset=1, last_reset=None, notional=1
):
    """Return undiscounted cashflows, strikes, and first-ITM exercise flags.

    fixings is path-by-reset with the known F_0 in column zero. Eligible
    resets are the caller's inclusive [first_reset,last_reset], default
    1..last observed. Ratchet K_j=R_(j-1)+spread. Sticky recursively uses
    K_j=min(R_(j-1),K_(j-1))+spread and requires caller K_0; skipped early
    eligible dates still advance that contractual recurrence.

    fixed and flexicap require caller strike (scalar or reset vector).
    flexicap uses the first strictly positive eligible payoffs, up to the
    nonnegative integer quota. There is no look-ahead or optimal exercise.
    Notional>=0; annual simple spread may have either sign, while all
    resulting contractual strikes must be positive in this lognormal lesson.
    """
    f, delta = _curve(fixings, accruals)
    if f.ndim != 2:
        raise ValueError("fixings must be a path-by-reset matrix")
    n = delta.size
    first = _integer(first_reset, "first_reset", 1)
    last = n - 1 if last_reset is None else _integer(last_reset, "last_reset")
    if first > n or last >= n or last < first - 1:
        raise ValueError("eligible reset range must be within observed fixings")
    nominal = _real(notional, "notional")
    offset = _real(spread, "spread")
    if nominal.ndim != 0 or nominal < 0 or offset.ndim != 0:
        raise ValueError("scalar nonnegative notional and scalar spread required")
    strikes = np.zeros_like(f)
    if kind in ("fixed", "flexicap"):
        if strike is None:
            raise ValueError("fixed and flexicap contracts require caller strike")
        k = _real(strike, "strike")
        if k.ndim > 1 or (k.ndim == 1 and k.size != n) or np.any(k <= 0):
            raise ValueError("strike must be positive scalar or one value per observed reset")
        strikes[:] = k
    elif kind == "ratchet":
        strikes[:, 1:] = f[:, :-1] + offset
    elif kind == "sticky":
        if initial_strike is None:
            raise ValueError("sticky contract requires caller initial_strike K_0")
        initial = _real(initial_strike, "initial_strike")
        if initial.ndim != 0 or initial <= 0:
            raise ValueError("initial_strike must be a positive scalar annual simple rate")
        strikes[:, 0] = initial
        for j in range(1, n):
            strikes[:, j] = np.minimum(f[:, j - 1], strikes[:, j - 1]) + offset
    else:
        raise ValueError("kind must be fixed, ratchet, sticky, or flexicap")
    if np.any(strikes[:, first:last + 1] <= 0):
        raise ValueError("contractual strikes must be positive")
    positive = f > strikes
    eligible = np.zeros(n, dtype=bool)
    eligible[first:last + 1] = True
    exercised = positive & eligible
    if kind == "flexicap":
        quota = _integer(max_exercises, "max_exercises")
        exercised &= np.cumsum(exercised, axis=1) <= quota
    elif max_exercises is not None:
        raise ValueError("exercise quota applies only to flexicap")
    cashflows = nominal * delta * np.maximum(f - strikes, 0) * exercised
    return {"cashflows": cashflows, "strikes": strikes, "exercised": exercised}


def _groups(groups, n):
    if groups is None:
        return np.arange(n + 1)
    raw = np.asarray(groups)
    if raw.ndim != 1 or raw.size < 2 or raw.dtype.kind not in "iu":
        raise ValueError("groups must be integer boundaries covering every fine subperiod")
    result = raw.astype(int)
    if result[0] != 0 or result[-1] != n or np.any(np.diff(result) <= 0):
        raise ValueError("groups must start at zero, end at the fine tenor count, and increase")
    return result


def swap_rate_statistics(forwards, accruals, groups=None):
    """Return swap rate, coarse annuity and its full fine-forward Jacobian.

    The swap starts at the observation date; forward/accrual vectors cover
    its entire contiguous underlying tenor. Coarse payment groups must be
    exact boundaries of the fine tenor. P(start)=1; at payment boundary b,
    P_b=prod_(i<b)(1+delta_i F_i)^-1. For group [a,b),
    G=(prod_(a<=i<b)(1+delta_i F_i)-1)/sum_(a<=i<b)delta_i.
    A=sum_g tau_g P_(b_g), S=(1-P_end)/A.

    Differentiating both numerator and annuity gives dS/dF_i; no frozen
    annuity-weight approximation is substituted. Leading path dimensions
    are supported for immediate European exercise values.
    """
    f, delta = _curve(forwards, accruals)
    boundaries = _groups(groups, delta.size)
    ends = boundaries[1:]
    tenors = np.array([np.sum(delta[a:b]) for a, b in zip(boundaries[:-1], ends, strict=True)])
    discounts = 1 / np.cumprod(1 + delta * f, axis=-1)
    annuity_terms = tenors * discounts[..., ends - 1]
    annuity = np.sum(annuity_terms, axis=-1)
    end_discount = discounts[..., -1]
    numerator = 1 - end_discount
    rate = numerator / annuity
    sensitivity = delta / (1 + delta * f)
    future_annuity = np.stack([
        np.sum(annuity_terms[..., ends > i], axis=-1) for i in range(delta.size)
    ], axis=-1)
    gradient = sensitivity * (
        end_discount[..., None] * annuity[..., None] + numerator[..., None] * future_annuity
    ) / annuity[..., None]**2
    coarse = np.stack([
        np.expm1(np.sum(np.log1p(delta[a:b] * f[..., a:b]), axis=-1)) / tenor
        for a, b, tenor in zip(boundaries[:-1], ends, tenors, strict=True)
    ], axis=-1)
    return {
        "rate": rate, "annuity": annuity, "gradient": gradient,
        "relative_weights": gradient * f / rate[..., None],
        "coarse_forwards": coarse, "coarse_accruals": tenors,
        "discounts": discounts, "groups": boundaries
    }


def frozen_swaption_price(
    forwards, accruals, loading_segments, durations, expiry, expiry_discount,
    strike, *, groups=None, notional=1, kind="payer"
):
    """Frozen-forward European price using full product/annuity sensitivities.

    All swap forwards reset at or after exercise. Each loading segment is
    (fine forwards,factors), with constant loadings over its positive
    duration; durations sum to expiry in years. Integrating
    ||sum_i gamma_i lambda_i||^2 uses initial gamma_i from the full Jacobian.
    expiry_discount times the conditional initial annuity is the time-zero
    Black annuity. This is an approximation to joint LMM dynamics.
    """
    f, delta = _curve(forwards, accruals)
    if f.ndim != 1:
        raise ValueError("frozen initial forwards must be one vector")
    stats = swap_rate_statistics(f, delta, groups)
    segments = _real(loading_segments, "loading_segments")
    dt = _vector(durations, "durations")
    e = _real(expiry, "expiry")
    discount = _real(expiry_discount, "expiry_discount")
    nominal = _real(notional, "notional")
    if (
        segments.ndim != 3 or segments.shape[:2] != (dt.size, f.size)
        or segments.shape[2] == 0 or np.any(dt < 0)
        or e.ndim != 0 or e < 0 or not np.isclose(np.sum(dt), e, rtol=0, atol=1e-12)
        or discount.ndim != 0 or discount <= 0 or nominal.ndim != 0 or nominal < 0
    ):
        raise ValueError("matching factor segments, expiry durations, positive DF and notional required")
    if kind not in ("payer", "receiver"):
        raise ValueError("kind must be payer or receiver")
    factor_diffusion = np.einsum("i,sip->sp", stats["relative_weights"], segments)
    variance = np.dot(dt, np.sum(factor_diffusion**2, axis=1))
    volatility = np.sqrt(variance / e) if e > 0 else 0.0
    price = nominal * forward_black_price(
        discount * stats["annuity"], stats["rate"], strike, volatility, e,
        "call" if kind == "payer" else "put"
    )
    return {
        **stats, "price": float(price), "integrated_variance": float(variance),
        "volatility": float(volatility), "factor_diffusion": factor_diffusion
    }


def pca_factor_loadings(relative_log_changes, target_norms, factors):
    """PCA of supplied log-forward changes followed by explicit row scaling.

    Rows are historical observations and columns are forward tenor buckets.
    The covariance uses ddof=1. Eigenvalues retain input sampling-time
    units; target_norms supply annualized relative diffusion units. Only
    PCA directions are transferred: no absolute-rate units are inferred.
    """
    changes = _real(relative_log_changes, "relative_log_changes")
    if changes.ndim != 2 or changes.shape[0] < 2 or changes.shape[1] < 1:
        raise ValueError("at least two observations of each forward are required")
    count = _integer(factors, "factors", 1)
    if count > changes.shape[1]:
        raise ValueError("factor count cannot exceed forward count")
    covariance = np.atleast_2d(np.cov(changes, rowvar=False, ddof=1))
    eigenvalues, directions = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues, directions = eigenvalues[order], directions[:, order]
    raw = directions[:, :count] * np.sqrt(np.maximum(eigenvalues[:count], 0))
    return {
        "loadings": rescale_loading_norms(raw, target_norms),
        "eigenvalues": eigenvalues, "directions": directions,
        "historical_covariance": covariance
    }


def calibrate_frozen_two_factor(
    forwards, accruals, target_norms, quotes, initial_angles, *, smoothness=0
):
    """Fit synthetic constant two-factor directions to frozen European prices.

    Caplet row norms remain the caller's bootstrapped targets. Row zero has
    angle zero to remove the global rotation gauge; the N-1 remaining
    angles lie in [-pi,pi]. Mirrored directions can have identical prices,
    so covariance, quote errors and Jacobian rank, not unique factor
    coordinates, are the relevant diagnostics. Quotes provide expiry,
    expiry discount, strike, positive price and optional coarse groups.

    Objective residuals are (model-market)/market; optional sqrt(smoothness)
    times successive angle differences are appended. No curve parameters,
    caplet norms or market data are silently fitted. This constant-loading
    teaching fit does not claim empirical or multicurve recovery.
    """
    f, delta = _curve(forwards, accruals)
    target = _vector(target_norms, "target_norms")
    angles = _vector(initial_angles, "initial_angles")
    penalty = _real(smoothness, "smoothness")
    if (
        f.ndim != 1 or f.size < 2 or target.size != f.size or np.any(target <= 0)
        or angles.size != f.size - 1 or np.any(np.abs(angles) > np.pi)
        or penalty.ndim != 0 or penalty < 0 or not isinstance(quotes, (list, tuple)) or not quotes
    ):
        raise ValueError("matching positive caplet norms, N-1 angles and quotes required")
    markets = []
    for quote in quotes:
        if not isinstance(quote, dict) or not {"expiry", "discount", "strike", "price"} <= quote.keys():
            raise ValueError("quotes require expiry, discount, strike and price")
        market = _real(quote["price"], "quote price")
        if market.ndim != 0 or market <= 0:
            raise ValueError("calibration quote prices must be positive")
        markets.append(float(market))
    markets = np.array(markets)

    def directions(theta):
        full = np.r_[0.0, theta]
        return target[:, None] * np.c_[np.cos(full), np.sin(full)]

    def prices(theta):
        loading = directions(theta)[None, :, :]
        return np.array([
            frozen_swaption_price(
                f, delta, loading, [quote["expiry"]], quote["expiry"], quote["discount"],
                quote["strike"], groups=quote.get("groups"), kind=quote.get("kind", "payer")
            )["price"] for quote in quotes
        ])

    def residuals(theta):
        errors = (prices(theta) - markets) / markets
        if penalty > 0:
            errors = np.r_[errors, np.sqrt(penalty) * np.diff(np.r_[0.0, theta])]
        return errors

    fit = least_squares(
        residuals, angles, bounds=(-np.pi, np.pi), xtol=1e-12, ftol=1e-12, gtol=1e-12,
        max_nfev=300
    )
    quote_jacobian = fit.jac[:len(quotes)]
    singular = np.linalg.svd(quote_jacobian, compute_uv=False)
    tolerance = max(quote_jacobian.shape) * np.finfo(float).eps * (singular[0] if singular.size else 0)
    fitted_prices = prices(fit.x)
    return {
        "loadings": directions(fit.x), "angles": np.r_[0, fit.x],
        "model_prices": fitted_prices, "residuals": fitted_prices - markets,
        "quote_jacobian": quote_jacobian, "singular_values": singular,
        "rank": int(np.sum(singular > tolerance)), "success": bool(fit.success),
        "objective": float(np.dot(fit.fun, fit.fun))
    }
