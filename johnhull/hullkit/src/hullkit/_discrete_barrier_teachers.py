"""Teachers and integration references for a discretely monitored GBM up-and-out call.

The fixed monitoring set is {0, T/m, ..., T}; equality with H knocks out.
No Brownian-bridge or continuous-barrier correction is used. K and H remain
fixed when differentiating spot. A finite-monitor contract jumps at S=H, so
Delta there is undefined (except for the identically zero H<=K contract).

MC arrays contain actual path samples. First-transition likelihood ratios
differentiate the whole monitored payoff, including all knockout boundaries.
Last-step conditioning integrates only the final increment and, for m>=2,
retains the *first* increment's score. Naive pathwise labels deliberately omit
earlier knockout-boundary contributions and are negative controls.
"""

from itertools import pairwise

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.special import ndtr, ndtri

_DEFAULT_STRIKE = 100.0
_DEFAULT_BARRIER = 120.0
_DEFAULT_RATE = 0.03
_DEFAULT_VOLATILITY = 0.2


def _contract(spot, maturity, strike, barrier, rate, volatility):
    values = np.asarray([spot, maturity, strike, barrier, rate, volatility], dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("contract inputs must be finite")
    if spot <= 0 or maturity <= 0 or barrier <= 0 or strike < 0 or volatility <= 0:
        raise ValueError(
            "positive spot, maturity, barrier and volatility; nonnegative strike required"
        )


def _count(value, name):
    if not np.isfinite(value) or int(value) != value or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def monitoring_times(maturity, monitoring=12):
    """Return m+1 monitoring dates, including zero and terminal maturity."""
    if not np.isfinite(maturity) or maturity <= 0:
        raise ValueError("maturity must be finite and positive")
    count = _count(monitoring, "monitoring")
    return np.linspace(0.0, maturity, count + 1)


def _cdf_interval(high, low):
    """Phi(high)-Phi(low), evaluated by survival probabilities in the right tail."""
    return np.where(
        low > 0,
        ndtr(-low) - ndtr(-high),
        ndtr(high) - ndtr(low),
    )


def _truncated(spot, duration, strike, barrier, rate, volatility):
    """Terminal truncated-call expectation and its derivative, without a t0 kill.

    Both are discounted over duration. Input spot may be a vector of previous
    states; the caller handles survival through the previous monitoring date.
    """
    spot = np.asarray(spot, dtype=float)
    if barrier <= strike:
        zero = np.zeros_like(spot)
        return zero, zero, zero, zero
    width = volatility * np.sqrt(duration)
    d2h = (np.log(spot / barrier) + (rate - 0.5 * volatility**2) * duration) / width
    d2k = (
        (np.log(spot / strike) + (rate - 0.5 * volatility**2) * duration) / width
        if strike > 0
        else np.full_like(spot, np.inf)
    )
    asset_probability = _cdf_interval(d2k + width, d2h + width)
    cash_probability = _cdf_interval(d2k, d2h)
    discount = np.exp(-rate * duration)
    price = spot * asset_probability - strike * discount * cash_probability
    boundary = (
        discount
        * (barrier - strike)
        * np.exp(-0.5 * d2h**2)
        / (np.sqrt(2.0 * np.pi) * spot * width)
    )
    delta = asset_probability - boundary
    return price, delta, asset_probability, boundary


def one_step(
    spot,
    maturity,
    *,
    strike=_DEFAULT_STRIKE,
    barrier=_DEFAULT_BARRIER,
    rate=_DEFAULT_RATE,
    volatility=_DEFAULT_VOLATILITY,
):
    """One positive monitoring date: analytic price, true Delta and naive mean."""
    _contract(spot, maturity, strike, barrier, rate, volatility)
    if barrier <= strike or spot > barrier:
        return dict(price=0.0, delta=0.0, naive_pw_mean=0.0, boundary_term=0.0, delta_defined=True)
    if spot == barrier:
        return dict(
            price=0.0,
            delta=np.nan,
            naive_pw_mean=np.nan,
            boundary_term=np.nan,
            delta_defined=False,
        )
    price, delta, naive, boundary = _truncated(spot, maturity, strike, barrier, rate, volatility)
    return dict(
        price=float(price),
        delta=float(delta),
        naive_pw_mean=float(naive),
        boundary_term=float(boundary),
        delta_defined=True,
    )


def samples(
    spot,
    maturity,
    z,
    *,
    strike=_DEFAULT_STRIKE,
    barrier=_DEFAULT_BARRIER,
    rate=_DEFAULT_RATE,
    volatility=_DEFAULT_VOLATILITY,
):
    """Sample discounted payoff and Delta teachers from supplied IID N(0,1) draws.

    z has shape (paths, m). No RNG is invoked. LRM units are price/spot.
    For m>=2, last_conditional and last_conditional_lrm are unbiased price and
    Delta teachers obtained by integrating the last increment exactly.
    last_conditional_pw differentiates the smoothed terminal payoff while
    holding all earlier survival indicators fixed; it is a biased control.
    """
    _contract(spot, maturity, strike, barrier, rate, volatility)
    z = np.asarray(z, dtype=float)
    if z.ndim != 2 or z.shape[0] < 1 or z.shape[1] < 1 or not np.isfinite(z).all():
        raise ValueError("z must be a nonempty finite paths-by-monitoring array")
    count = z.shape[1]
    dt = maturity / count
    width = volatility * np.sqrt(dt)
    log_spot = np.log(spot)
    log_paths = np.column_stack(
        (
            np.full(z.shape[0], log_spot),
            log_spot + np.cumsum((rate - 0.5 * volatility**2) * dt + width * z, axis=1),
        )
    )
    paths = np.exp(log_paths)
    paths[:, 0] = spot
    alive = (spot < barrier) & np.all(log_paths[:, 1:] < np.log(barrier), axis=1)
    discount = np.exp(-rate * maturity)
    terminal = paths[:, -1]
    payoff = discount * np.maximum(terminal - strike, 0.0) * alive
    score = z[:, 0] / (spot * width)
    lrm = payoff * score
    naive = discount * terminal / spot * alive * (terminal > strike)
    delta_defined = spot != barrier or barrier <= strike
    if not delta_defined:
        lrm[:] = np.nan
        naive[:] = np.nan
    result = dict(
        paths=paths,
        survival=alive,
        payoff=payoff,
        score=score,
        lrm=lrm,
        naive_pw=naive,
        delta_defined=delta_defined,
    )
    if count >= 2:
        prior_alive = (spot < barrier) & np.all(log_paths[:, 1:-1] < np.log(barrier), axis=1)
        previous = paths[:, -2]
        last_price, last_delta, _, _ = _truncated(previous, dt, strike, barrier, rate, volatility)
        prior_discount = np.exp(-rate * (maturity - dt))
        conditioned = prior_discount * last_price * prior_alive
        conditioned_lrm = conditioned * score
        conditioned_pw = prior_discount * last_delta * previous / spot * prior_alive
        if not delta_defined:
            conditioned_lrm[:] = np.nan
            conditioned_pw[:] = np.nan
        result.update(
            last_conditional=conditioned,
            last_conditional_lrm=conditioned_lrm,
            last_conditional_pw=conditioned_pw,
        )
    return result


def summarize(values):
    """IID sample mean and standard error, with sample variance (ddof=1)."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or values.size < 2 or not np.isfinite(values).all():
        raise ValueError("at least two finite scalar IID samples required")
    return dict(
        mean=float(np.mean(values)), se=float(np.std(values, ddof=1) / np.sqrt(values.size))
    )


def markov_reference(
    spot,
    maturity,
    *,
    monitoring=12,
    order=128,
    tail_sigma=10.0,
    log_lower=None,
    strike=_DEFAULT_STRIKE,
    barrier=_DEFAULT_BARRIER,
    rate=_DEFAULT_RATE,
    volatility=_DEFAULT_VOLATILITY,
):
    """Gauss-Legendre Markov integration, including first-transition score Delta.

    The price and naive asset moment propagate backwards over the exact normal
    transition density. The final first-state integral differentiates only its
    density, using (x1-log(S)-mu*dt)/(S*sigma**2*dt). It does not differentiate
    later states or reuse the analytic one-monitor value.

    order is the number of nodes *per interval*, split at log(K) when inside
    the integration domain. Default log_lower is anchored at min(log(S),log(K)),
    or log(S) for K=0, capped at log(H) for already knocked-out contracts.
    Delta holds that computed cutoff fixed. Supplying an explicit log_lower
    also holds it fixed. The omitted lower-tail path contribution is bounded
    separately from the quadrature error. tail_price_bound and tail_delta_bound
    bound only truncation, not grid error; compare orders to assess the latter.

    For U={some monitored log(S_t)<log_lower}, P(U) is bounded by a union
    bound. Payoff <= C=exp(-r*T)*max(H-K,0) gives C*P(U) for price, while
    Cauchy-Schwarz and E[Z1**2]=1 give C*sqrt(P(U))/(S*sigma*sqrt(dt)) for Delta.
    """
    _contract(spot, maturity, strike, barrier, rate, volatility)
    count = _count(monitoring, "monitoring")
    order = _count(order, "order")
    if not np.isfinite(tail_sigma) or tail_sigma <= 0:
        raise ValueError("tail_sigma must be finite and positive")
    times = monitoring_times(maturity, count)
    mu = rate - 0.5 * volatility**2
    dt = maturity / count
    width = volatility * np.sqrt(dt)
    log_spot = np.log(spot)
    upper = np.log(barrier)
    default_lower = log_lower is None
    if default_lower:
        anchor = min(log_spot, np.log(strike)) if strike > 0 else log_spot
        log_lower = (
            min(anchor, upper)
            + min(0.0, mu * maturity)
            - tail_sigma * volatility * np.sqrt(maturity)
        )
    if not np.isfinite(log_lower) or log_lower >= upper:
        raise ValueError("log_lower must be finite and below log(barrier)")
    log_lower = float(log_lower)
    marginal_scores = (log_lower - log_spot - mu * times[1:]) / (volatility * np.sqrt(times[1:]))
    probability = float(min(1.0, np.sum(ndtr(marginal_scores))))
    cap = float(np.exp(-rate * maturity) * max(barrier - strike, 0.0))
    metadata = dict(
        monitoring=count,
        monitoring_times=times,
        order=order,
        log_lower=log_lower,
        log_upper=float(upper),
        log_lower_depends_on_spot=bool(
            default_lower and spot <= barrier and (strike == 0 or spot <= strike)
        ),
        log_lower_policy="default_spot_strike_anchor" if default_lower else "explicit_fixed",
        tail_probability_bound=probability,
        tail_price_bound=cap * probability,
        tail_delta_bound=cap * np.sqrt(probability) / (spot * width),
    )
    if barrier <= strike or spot >= barrier:
        return dict(
            price=0.0,
            delta=np.nan if spot == barrier and barrier > strike else 0.0,
            naive_pw_mean=0.0,
            delta_defined=spot != barrier or barrier <= strike,
            nodes=np.array([], dtype=float),
            row_mass_max=0.0,
            **metadata,
        )
    endpoints = [log_lower, upper]
    if strike > 0 and log_lower < np.log(strike) < upper:
        endpoints.insert(1, float(np.log(strike)))
    gl_x, gl_w = leggauss(order)
    node_groups, weight_groups = [], []
    for lower, higher in pairwise(endpoints):
        half = 0.5 * (higher - lower)
        node_groups.append(0.5 * (higher + lower) + half * gl_x)
        weight_groups.append(half * gl_w)
    nodes = np.concatenate(node_groups)
    weights = np.concatenate(weight_groups)
    increments = (nodes[None, :] - nodes[:, None] - mu * dt) / width
    transition = np.exp(-0.5 * increments**2) * weights[None, :] / (np.sqrt(2 * np.pi) * width)
    asset = np.exp(nodes)
    continuation = np.column_stack(
        (
            np.maximum(asset - strike, 0.0),
            asset * (asset > strike),
        )
    )
    for _ in range(count - 1):
        continuation = transition @ continuation
    first_z = (nodes - log_spot - mu * dt) / width
    first_weights = np.exp(-0.5 * first_z**2) * weights / (np.sqrt(2 * np.pi) * width)
    discount = np.exp(-rate * maturity)
    price, asset_mean = discount * (first_weights @ continuation)
    delta = discount * (first_weights * first_z / (spot * width)) @ continuation[:, 0]
    return dict(
        price=float(price),
        delta=float(delta),
        naive_pw_mean=float(asset_mean / spot),
        delta_defined=True,
        nodes=nodes,
        row_mass_max=float(transition.sum(axis=1).max()),
        **metadata,
    )


def _oss_diagnostics(result):
    """Keep rare/unsupported samples visible instead of converting NaN to zero."""
    values = result["payoff"]
    deltas = result["delta"]
    count = values.size
    price_se = (
        float(np.std(values, ddof=1) / np.sqrt(count))
        if count >= 2 and np.isfinite(values).all()
        else np.nan
    )
    delta_se = (
        float(np.std(deltas, ddof=1) / np.sqrt(count))
        if count >= 2 and np.isfinite(deltas).all()
        else np.nan
    )
    positive = int(np.count_nonzero(result["valid"] & (values > 0)))
    result.update(
        positive_payoff_count=positive,
        payoff_se=price_se,
        delta_se=delta_se,
        zero_price_se=bool(price_se == 0),
        zero_delta_se=bool(delta_se == 0),
        statistically_informative=bool(
            result["valid"].all() and positive > 0 and price_se > 0 and delta_se > 0
        ),
    )
    if result["status"] == "ok" and positive == 0:
        result["status"] = "no_positive_payoffs"
    return result


def one_step_survival(
    spot,
    maturity,
    u,
    *,
    strike=_DEFAULT_STRIKE,
    barrier=_DEFAULT_BARRIER,
    rate=_DEFAULT_RATE,
    volatility=_DEFAULT_VOLATILITY,
):
    """Explicit-uniform one-step-survival price and pathwise Delta teachers.

    u has shape (paths,m), with entries strictly inside (0,1). Each normal
    increment is drawn by inverse CDF conditional on the next state being
    below H. The likelihood weight is the product of the step survival
    probabilities. Both the conditional path and this weight are differentiated
    with respect to S, holding supplied u, K, H, r, sigma and monitoring fixed.

    Writing x=log(S_t), dx=dx/dS, w=sigma*sqrt(dt), a=(log(H)-x-mu*dt)/w:
    p=Phi(a), z=Phi^-1(u*p), dp/p=-phi(a)*dx/(w*p),
    dz=(u*p/phi(z))*(dp/p), and dx_next=dx+w*dz.
    The accumulated log weight derivative is sum(dp/p). Delta includes both
    the terminal payoff derivative and the weight derivative. The returned
    without_weight_delta is an intentionally biased negative control.

    probability_underflow, quantile_underflow, weight_underflow and
    numerical_failure are per-path flags. Unsupported outputs remain NaN.
    SE=0 and positive-payoff counts are exposed; no_positive_payoffs does not
    establish accuracy, and statistically_informative is only a sampling
    diagnostic, never an accuracy guarantee. No internal RNG is invoked.
    """
    _contract(spot, maturity, strike, barrier, rate, volatility)
    u = np.asarray(u, dtype=float)
    if u.ndim != 2 or u.shape[0] < 1 or u.shape[1] < 1 or not np.isfinite(u).all():
        raise ValueError("u must be a nonempty finite paths-by-monitoring array")
    if np.any((u <= 0) | (u >= 1)):
        raise ValueError("uniform draws must be strictly inside (0,1)")
    n_paths, count = u.shape
    flags = {
        name: np.zeros(n_paths, dtype=bool)
        for name in (
            "probability_underflow",
            "quantile_underflow",
            "weight_underflow",
            "numerical_failure",
        )
    }
    if spot >= barrier or barrier <= strike:
        delta_defined = spot != barrier or barrier <= strike
        zero = np.zeros(n_paths)
        delta = zero.copy() if delta_defined else np.full(n_paths, np.nan)
        return _oss_diagnostics(
            dict(
                paths=np.full((n_paths, count + 1), spot),
                payoff=zero,
                delta=delta,
                without_weight_delta=delta.copy(),
                weight_delta=delta.copy(),
                survival_weight=zero.copy(),
                log_survival_weight=np.full(n_paths, -np.inf),
                log_spot_derivative=np.full(n_paths, 1.0 / spot),
                log_weight_derivative=zero.copy(),
                min_step_probability=np.full(n_paths, np.nan),
                delta_defined=delta_defined,
                valid=np.full(n_paths, delta_defined),
                positive_terminal_payoff_count=0,
                status="deterministic_zero" if delta_defined else "undefined_delta_at_barrier",
                **flags,
            )
        )
    dt = maturity / count
    width = volatility * np.sqrt(dt)
    mu = rate - 0.5 * volatility**2
    upper = np.log(barrier)
    log_state = np.full(n_paths, np.log(spot))
    derivative = np.full(n_paths, 1.0 / spot)
    log_weight = np.zeros(n_paths)
    log_weight_derivative = np.zeros(n_paths)
    min_probability = np.ones(n_paths)
    paths = np.full((n_paths, count + 1), np.nan)
    paths[:, 0] = spot
    valid = np.ones(n_paths, dtype=bool)
    log_normal_constant = 0.5 * np.log(2.0 * np.pi)
    for step in range(count):
        active = np.flatnonzero(valid)
        if active.size == 0:
            break
        a = (upper - log_state[active] - mu * dt) / width
        probability = ndtr(a)
        min_probability[active] = np.minimum(min_probability[active], probability)
        bad_probability = probability == 0
        bad_indices = active[bad_probability]
        flags["probability_underflow"][bad_indices] = True
        valid[bad_indices] = False
        log_weight[bad_indices] = -np.inf
        good = ~bad_probability
        active, a, probability = active[good], a[good], probability[good]
        if active.size == 0:
            continue
        quantile = u[active, step] * probability
        log_probability = np.log(probability)
        log_weight[active] += log_probability
        bad_quantile = (quantile <= 0) | (quantile >= 1)
        bad_indices = active[bad_quantile]
        flags["quantile_underflow"][bad_indices] = True
        valid[bad_indices] = False
        good = ~bad_quantile
        active, a, probability = active[good], a[good], probability[good]
        quantile, log_probability = quantile[good], log_probability[good]
        if active.size == 0:
            continue
        z = ndtri(quantile)
        # Log ratios avoid dividing two underflowing normal densities.
        with np.errstate(over="ignore", invalid="ignore"):
            inverse_mills = np.exp(-0.5 * a**2 - log_normal_constant - log_probability)
            dlog_probability = -inverse_mills * derivative[active] / width
            quantile_over_density = np.exp(np.log(quantile) + 0.5 * z**2 + log_normal_constant)
            derivative[active] += width * quantile_over_density * dlog_probability
            log_weight_derivative[active] += dlog_probability
            log_state[active] += mu * dt + width * z
        bad_numeric = (
            ~np.isfinite(log_state[active])
            | ~np.isfinite(derivative[active])
            | ~np.isfinite(log_weight_derivative[active])
            | (log_state[active] >= upper)
        )
        bad_indices = active[bad_numeric]
        flags["numerical_failure"][bad_indices] = True
        valid[bad_indices] = False
        paths[active, step + 1] = np.exp(log_state[active])
    conditional_path_valid = valid.copy()
    weight = np.exp(log_weight)
    flags["weight_underflow"] = valid & (weight == 0)
    valid &= ~flags["weight_underflow"]
    terminal = np.exp(log_state)
    terminal_payoff = np.maximum(terminal - strike, 0.0)
    with np.errstate(over="ignore", invalid="ignore"):
        discounted_weight = np.exp(-rate * maturity) * weight
        value = discounted_weight * terminal_payoff
        path_component = discounted_weight * (terminal > strike) * terminal * derivative
        weight_component = value * log_weight_derivative
        delta = path_component + weight_component
    bad_numeric = valid & (
        ~np.isfinite(value)
        | ~np.isfinite(delta)
        | ~np.isfinite(path_component)
        | ~np.isfinite(weight_component)
    )
    flags["numerical_failure"] |= bad_numeric
    valid &= ~bad_numeric
    for array in (value, delta, path_component, weight_component):
        array[~valid] = np.nan
    if any(
        flags[name].any()
        for name in (
            "probability_underflow",
            "quantile_underflow",
            "weight_underflow",
        )
    ):
        status = "unsupported_underflow"
    elif flags["numerical_failure"].any():
        status = "unsupported_numerical"
    else:
        status = "ok"
    return _oss_diagnostics(
        dict(
            paths=paths,
            payoff=value,
            delta=delta,
            without_weight_delta=path_component,
            weight_delta=weight_component,
            survival_weight=weight,
            log_survival_weight=log_weight,
            log_spot_derivative=derivative,
            log_weight_derivative=log_weight_derivative,
            min_step_probability=min_probability,
            delta_defined=True,
            valid=valid,
            positive_terminal_payoff_count=int(
                np.count_nonzero(conditional_path_valid & (terminal_payoff > 0))
            ),
            status=status,
            **flags,
        )
    )


def _batch_markov_kernel(lower, upper, strike, mu, dt, volatility, count, gl_x, gl_w):
    """Construct one exact-normal transition quadrature for a maturity group."""
    endpoints = [lower, upper]
    if strike > 0 and lower < np.log(strike) < upper:
        endpoints.insert(1, float(np.log(strike)))
    nodes_list, weights_list = [], []
    for left, right in pairwise(endpoints):
        half = 0.5 * (right - left)
        nodes_list.append(0.5 * (right + left) + half * gl_x)
        weights_list.append(half * gl_w)
    nodes, weights = np.concatenate(nodes_list), np.concatenate(weights_list)
    width = volatility * np.sqrt(dt)
    normal = (nodes[None, :] - nodes[:, None] - mu * dt) / width
    transition = np.exp(-0.5 * normal**2) * weights[None, :] / (np.sqrt(2 * np.pi) * width)
    asset = np.exp(nodes)
    continuation = np.column_stack((np.maximum(asset - strike, 0.0), asset * (asset > strike)))
    for _ in range(count - 1):
        continuation = transition @ continuation
    return nodes, weights, continuation, float(transition.sum(axis=1).max())


def markov_batch(
    inputs,
    *,
    monitoring=12,
    order=128,
    tail_sigma=12.0,
    log_lower=None,
    check_order=None,
    strike=_DEFAULT_STRIKE,
    barrier=_DEFAULT_BARRIER,
    rate=_DEFAULT_RATE,
    volatility=_DEFAULT_VOLATILITY,
):
    """Batch price and first-transition-score Delta, sharing only same-call setup.

    inputs is a nonempty (N,2) array of physical [S,T] rows. Price, Delta,
    naive_pw_mean and individual tail bounds have shape (N,1). tail_bounds
    has shape (N,3), with columns probability, price and Delta truncation bounds.
    No interpolation, approximate maturity grouping or cross-call memoization
    is used. Each *exactly equal* T group builds one normal-transition matrix
    and backward continuation; all living S rows then share a vectorized
    first-transition density/score integral.

    A group's default fixed lower cutoff is
    min(min(log(S_group)), log(K)) + min(0,mu*T) - tail_sigma*sigma*sqrt(T);
    K=0 omits log(K). The anchor is capped at log(H) for groups already KO.
    Each spot Delta holds that group cutoff fixed. log_lower can instead be
    an explicit scalar held fixed for all groups. These truncation bounds
    are separate from quadrature error, exactly as in markov_reference.

    groups retains per-group indices, nodes, order, cutoff, monitoring times
    and row mass for saving refinement evidence. Optional check_order>order
    recomputes at higher order and returns absolute differences and its tail
    bounds/metadata in refinement. It is disabled by default, so a timed
    primary evaluation need not pay for a verification calculation.
    """
    inputs = np.asarray(inputs, dtype=float)
    if (
        inputs.ndim != 2
        or inputs.shape[1] != 2
        or inputs.shape[0] < 1
        or not np.isfinite(inputs).all()
        or np.any(inputs <= 0)
    ):
        raise ValueError("finite nonempty positive [spot,maturity] rows required")
    _contract(inputs[0, 0], inputs[0, 1], strike, barrier, rate, volatility)
    count, order = _count(monitoring, "monitoring"), _count(order, "order")
    if not np.isfinite(tail_sigma) or tail_sigma <= 0:
        raise ValueError("tail_sigma must be finite and positive")
    upper = np.log(barrier)
    if log_lower is not None and (
        np.ndim(log_lower) != 0 or not np.isfinite(log_lower) or log_lower >= upper
    ):
        raise ValueError("explicit log_lower must be a finite scalar below log(barrier)")
    if check_order is not None:
        check_order = _count(check_order, "check_order")
        if check_order <= order:
            raise ValueError("check_order must exceed primary order")
    n_rows = len(inputs)
    price, delta, naive = (np.zeros((n_rows, 1)) for _ in range(3))
    defined = np.ones((n_rows, 1), dtype=bool)
    contact = (inputs[:, 0] == barrier) & (barrier > strike)
    delta[contact, 0] = np.nan
    defined[contact, 0] = False
    lower_values, row_mass = np.empty((n_rows, 1)), np.zeros((n_rows, 1))
    bounds = np.empty((n_rows, 3))
    group_index = np.empty(n_rows, dtype=int)
    groups, setup_count = [], 0
    mu = rate - 0.5 * volatility**2
    gl_x, gl_w = leggauss(order)
    for group_id, maturity in enumerate(np.unique(inputs[:, 1])):
        indices = np.flatnonzero(inputs[:, 1] == maturity)
        spots = inputs[indices, 0]
        group_index[indices] = group_id
        if log_lower is None:
            anchor = float(np.min(np.log(spots)))
            if strike > 0:
                anchor = min(anchor, np.log(strike))
            lower = (
                min(anchor, upper)
                + min(0.0, mu * maturity)
                - tail_sigma * volatility * np.sqrt(maturity)
            )
        else:
            lower = float(log_lower)
        dt = maturity / count
        width = volatility * np.sqrt(dt)
        times = monitoring_times(maturity, count)
        lower_values[indices, 0] = lower
        normal = (lower - np.log(spots[:, None]) - mu * times[None, 1:]) / (
            volatility * np.sqrt(times[None, 1:])
        )
        probability = np.minimum(1.0, ndtr(normal).sum(axis=1))
        cap = np.exp(-rate * maturity) * max(barrier - strike, 0.0)
        bounds[indices, 0] = probability
        bounds[indices, 1] = cap * probability
        bounds[indices, 2] = cap * np.sqrt(probability) / (spots * width)
        live = spots < barrier
        metadata = dict(
            maturity=float(maturity),
            indices=indices,
            monitoring=count,
            monitoring_times=times,
            order=order,
            log_lower=float(lower),
            log_upper=float(upper),
            log_lower_policy="shared_min_spot_strike" if log_lower is None else "explicit_fixed",
            nodes=np.array([], dtype=float),
            row_mass_max=0.0,
        )
        if barrier > strike and np.any(live):
            nodes, weights, continuation, mass = _batch_markov_kernel(
                lower,
                upper,
                strike,
                mu,
                dt,
                volatility,
                count,
                gl_x,
                gl_w,
            )
            setup_count += 1
            live_indices, live_spots = indices[live], spots[live]
            first_z = (nodes[None, :] - np.log(live_spots[:, None]) - mu * dt) / width
            first_weights = (
                np.exp(-0.5 * first_z**2) * weights[None, :] / (np.sqrt(2 * np.pi) * width)
            )
            discount = np.exp(-rate * maturity)
            means = discount * (first_weights @ continuation)
            price[live_indices, 0] = means[:, 0]
            naive[live_indices, 0] = means[:, 1] / live_spots
            delta[live_indices, 0] = (
                discount * (first_weights * first_z / (live_spots[:, None] * width))
            ) @ continuation[:, 0]
            row_mass[indices, 0] = mass
            metadata.update(nodes=nodes, row_mass_max=mass)
        groups.append(metadata)
    result = dict(
        price=price,
        delta=delta,
        naive_pw_mean=naive,
        delta_defined=defined,
        tail_bounds=bounds,
        tail_probability_bound=bounds[:, 0:1],
        tail_price_bound=bounds[:, 1:2],
        tail_delta_bound=bounds[:, 2:3],
        log_lower=lower_values,
        row_mass_max=row_mass,
        group_index=group_index,
        groups=groups,
        transition_setup_count=setup_count,
        refinement=None,
    )
    if check_order is not None:
        higher = markov_batch(
            inputs,
            monitoring=count,
            order=check_order,
            tail_sigma=tail_sigma,
            log_lower=log_lower,
            strike=strike,
            barrier=barrier,
            rate=rate,
            volatility=volatility,
        )
        result["refinement"] = dict(
            order=check_order,
            **{
                key: np.abs(higher[key] - result[key])
                for key in ("price", "delta", "naive_pw_mean")
            },
            tail_bounds=higher["tail_bounds"],
            groups=higher["groups"],
            transition_setup_count=higher["transition_setup_count"],
        )
    return result
