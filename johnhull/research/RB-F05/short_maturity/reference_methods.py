"""Independent synthetic cash-call references, with physical spot Greeks.

The ordinary Poisson mixture uses math.erfc normal CDFs. The density route
integrates payoff times likelihood scores and retains a separate Gamma
boundary-density witness. It never calls the private teacher or clock code.
Broadie--Glasserman (1996), doi:10.1287/mnsc.42.2.269, supports the LR method;
the deterministic clock/pulse extension is independently derived here.
Merton's original full paper was not retrieved for this work: the existing
Hullkit implementation is only a separate numerical price comparator.
"""

import math

import numpy as np
from scipy.integrate import quad
from scipy.stats import poisson

_SQRT_2 = math.sqrt(2.0)
_SQRT_2PI = math.sqrt(2.0 * math.pi)


def _cdf(x):
    return 0.5 * math.erfc(-x / _SQRT_2)


def _phi(x):
    return math.exp(-x * x / 2.0) / _SQRT_2PI


def _inputs(S, K, state, parameters, nmax):
    if isinstance(nmax, bool) or not isinstance(nmax, (int, np.integer)) or nmax < 0:
        raise ValueError("nmax must be a nonnegative integer")
    try:
        S, K = float(S), float(K)
        tau, W, L, seconds = (
            float(getattr(state, field))
            for field in ("carry_years", "variance", "jump_mean_count", "remaining_seconds")
        )
        r, q, mu, sd = (
            float(getattr(parameters, field))
            for field in ("rate", "dividend", "jump_mean", "jump_std")
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("scalar clock and parameter attributes are required") from exc
    if not all(math.isfinite(x) for x in (S, K, tau, W, L, seconds, r, q, mu, sd)):
        raise ValueError("inputs must be finite")
    if S <= 0 or K <= 0 or min(tau, W, L, seconds, sd) < 0:
        raise ValueError("spot/strike positive and clocks/mark std nonnegative required")
    status = getattr(state, "status", None)
    if status == "expiry":
        if any(x != 0 for x in (tau, W, L, seconds)):
            raise ValueError("expiry requires all four clocks to be zero")
    elif status != "active" or tau <= 0 or W <= 0 or seconds <= 0:
        raise ValueError("active references require positive carry/variance/remaining seconds")
    return S, K, tau, W, L, r, q, mu, sd


def _expiry(S, K):
    at_strike = S == K
    return {
        "values": np.array(
            [
                max(S - K, 0.0),
                math.nan if at_strike else float(S > K),
                math.nan if at_strike else 0.0,
            ]
        ),
        "tail_bounds": np.zeros(3),
        "terms": [],
        "status": "expiry_undefined_atm" if at_strike else "expiry",
        "reason": "ordinary_greeks_undefined_atm_expiry" if at_strike else None,
    }


def _count_state(S, K, tau, W, L, r, q, mu, sd, n):
    # Ordinary count law: the forward multiplier includes E[e^J | N=n].
    eta = mu + sd * sd / 2.0
    drift = (r - q) * tau - math.expm1(eta) * L
    v = W + n * sd * sd
    root = math.sqrt(v)
    log_b = drift + n * eta
    a = -(math.log(S / K) + drift - W / 2.0 + n * mu) / root
    return root, log_b, a, math.exp(-r * tau)


def _count_cdf(S, K, root, log_b, a, discount):
    d2, d1 = -a, -a + root
    log_m = math.log(S / K) + log_b
    # ITM parity avoids subtraction of two almost equal large terms.
    if log_m > 0:
        put = K * _cdf(-d2) - S * math.exp(log_b) * _cdf(-d1)
        price = discount * (K * math.expm1(log_m) + put)
    elif log_m == 0:
        price = discount * K * math.erf(root / (2.0 * _SQRT_2))
    else:
        price = discount * math.fsum((S * math.exp(log_b) * _cdf(d1), -K * _cdf(d2)))
    delta = discount * math.exp(log_b) * _cdf(d1)
    gamma = discount * math.exp(log_b) * _phi(d1) / (S * root)
    return np.array([price, delta, gamma])


def _tail_bounds(S, tau, W, L, q, mu, sd, nmax):
    # p_L(n)*D*B_n = exp(-q*tau)*p_{L*exp(eta)}(n).
    tilted_mean = L * math.exp(mu + sd * sd / 2.0)
    weighted_tail = math.exp(-q * tau) * float(poisson.sf(nmax, tilted_mean))
    return np.array(
        [
            S * weighted_tail,
            weighted_tail,
            weighted_tail / (S * _SQRT_2PI * math.sqrt(W + (nmax + 1) * sd * sd)),
        ]
    )


def independent_mixture(S, K, state, parameters, *, nmax=8):
    """Sum ordinary Poisson conditional prices/Delta/Gamma without core calls.

    values and tail_bounds have order [cash price, physical Delta, physical
    Gamma]. Bounds cover omitted positive count terms, not floating point error.
    W=0 before expiry is outside this v1 route; expiry ATM Greeks remain NaN.
    """
    S, K, tau, W, L, r, q, mu, sd = _inputs(S, K, state, parameters, nmax)
    if state.status == "expiry":
        return _expiry(S, K)
    terms = []
    for n in range(nmax + 1):
        weight = float(poisson.pmf(n, L))
        root, log_b, a, discount = _count_state(S, K, tau, W, L, r, q, mu, sd, n)
        values = _count_cdf(S, K, root, log_b, a, discount)
        terms.append({"count": n, "weight": weight, "values": values})
    values = np.array([math.fsum(t["weight"] * t["values"][j] for t in terms) for j in range(3)])
    return {
        "values": values,
        "tail_bounds": _tail_bounds(S, tau, W, L, q, mu, sd, nmax),
        "terms": terms,
        "status": "ok" if np.isfinite(values).all() else "nonfinite",
    }


def _split_quad(function, a, root, epsabs, epsrel):
    # For very negative a, a single (a,infinity) transform misses the normal
    # peak. Integrating from -infinity with a zero integrand below a is exact.
    lower = -math.inf if a < -8.0 else a
    cuts = sorted(set(x for x in (-8.0, 0.0, root, root + 8.0) if x > lower))
    cuts.append(math.inf)

    def integrate(relative_tolerance):
        values, errors, messages = [], [], []
        segment_lower = lower
        for upper in cuts:
            result = quad(
                function,
                segment_lower,
                upper,
                epsabs=epsabs / len(cuts),
                epsrel=relative_tolerance,
                limit=200,
                full_output=1,
            )
            values.append(result[0])
            errors.append(result[1])
            if len(result) > 3:
                messages.append(result[3])
            segment_lower = upper
        return math.fsum(values), math.fsum(errors), messages

    result = integrate(epsrel)
    # Relative accuracy of large signed segments need not give relative
    # accuracy of their small sum. Refine against the final absolute budget.
    if result[1] > max(epsabs, epsrel * abs(result[0])):
        refined = integrate(0.0)
        if refined[1] < result[1]:
            result = refined
    return result


def density_quad(S, K, state, parameters, *, nmax=8, epsabs=1e-10, epsrel=1e-10):
    """Integrate normal density times payoff, first score and second score.

    Primary Gamma is D*K*phi(a)/(S^2*sqrt(v)), the boundary-density identity.
    The LR2 Gamma integral is retained in lr_gamma with its quadrature error.
    error_estimates excludes Poisson truncation; primary Gamma has zero
    quadrature error because its density value needs no integration. QUADPACK
    errors are numerical estimates, not rigorous bounds or statistical CIs.
    """
    if not all(math.isfinite(x) and x > 0 for x in (epsabs, epsrel)):
        raise ValueError("quadrature tolerances must be finite and positive")
    S, K, tau, W, L, r, q, mu, sd = _inputs(S, K, state, parameters, nmax)
    if state.status == "expiry":
        result = _expiry(S, K)
        result.update(
            error_estimates=np.zeros(3),
            lr_gamma=result["values"][2],
            lr_gamma_error_estimate=0.0,
            quadrature_messages=[],
        )
        return result
    terms = []
    for n in range(nmax + 1):
        weight = float(poisson.pmf(n, L))
        root, log_b, a, discount = _count_state(S, K, tau, W, L, r, q, mu, sd, n)
        forward = S * math.exp(log_b)

        def payoff_density(z, *, a=a, root=root, forward=forward):
            if z <= a:
                return 0.0
            exponent = root * (z - a)
            if exponent < 0.5:
                return K * _phi(z) * math.expm1(exponent)
            # Complete the square, avoiding exp(root*z) overflow at infinity.
            return forward * _phi(z - root) - K * _phi(z)

        def first_score(z, *, discount=discount, root=root, payoff=payoff_density):
            return discount * payoff(z) * z / (S * root)

        def second_score(z, *, discount=discount, root=root, payoff=payoff_density):
            return discount * payoff(z) * (z * z - z * root - 1.0) / (S * S * root * root)

        c, c_error, c_messages = _split_quad(
            lambda z, discount=discount, payoff=payoff_density: discount * payoff(z),
            a,
            root,
            epsabs,
            epsrel,
        )
        delta, d_error, d_messages = _split_quad(first_score, a, root, epsabs, epsrel)
        lr_gamma, g_error, g_messages = _split_quad(second_score, a, root, epsabs, epsrel)
        boundary_gamma = discount * K * _phi(a) / (S * S * root)
        terms.append(
            {
                "count": n,
                "weight": weight,
                "values": np.array([c, delta, boundary_gamma]),
                "error_estimates": np.array([c_error, d_error, 0.0]),
                "lr_gamma": lr_gamma,
                "lr_gamma_error_estimate": g_error,
                "quadrature_messages": c_messages + d_messages + g_messages,
                "primary_quadrature_messages": c_messages + d_messages,
            }
        )
    values = np.array([math.fsum(t["weight"] * t["values"][j] for t in terms) for j in range(3)])
    errors = np.array(
        [math.fsum(t["weight"] * t["error_estimates"][j] for t in terms) for j in range(3)]
    )
    lr_gamma = math.fsum(t["weight"] * t["lr_gamma"] for t in terms)
    lr_error = math.fsum(t["weight"] * t["lr_gamma_error_estimate"] for t in terms)
    messages = [message for t in terms if t["weight"] > 0 for message in t["quadrature_messages"]]
    primary_messages = [
        m for t in terms if t["weight"] > 0 for m in t["primary_quadrature_messages"]
    ]
    status = "ok"
    if not np.isfinite(values).all() or not math.isfinite(lr_gamma):
        status = "nonfinite"
    elif primary_messages:
        status = "quadrature_warning"
    elif abs(lr_gamma - values[2]) > 8.0 * lr_error + 8.0 * epsabs:
        status = "lr_gamma_cancellation"
    return {
        "values": values,
        "error_estimates": errors,
        "tail_bounds": _tail_bounds(S, tau, W, L, q, mu, sd, nmax),
        "terms": terms,
        "lr_gamma": lr_gamma,
        "lr_gamma_error_estimate": lr_error,
        "quadrature_messages": messages,
        "status": status,
    }


def terminal_moment(order, state, parameters):
    """Return E[(S_T/S)^order] from the compensated compound-Poisson MGF."""
    if not math.isfinite(order):
        raise ValueError("moment order must be finite")
    _, _, tau, W, L, r, q, mu, sd = _inputs(1.0, 1.0, state, parameters, 0)
    eta = mu + sd * sd / 2.0
    exponent = (
        order * (r - q) * tau
        + (order * order - order) * W / 2.0
        + L * (math.expm1(order * mu + order * order * sd * sd / 2.0) - order * math.expm1(eta))
    )
    return math.exp(exponent)


def merton_price_check(S, K, state, parameters, *, nmax=8):
    """Compare the independent price against existing reweighted Merton code.

    The equivalent constant sigma/intensity reproduce integrated W/Lambda
    for this European terminal payoff; they do not validate an intraday path,
    stochastic volatility or the original Merton paper's implementation.
    """
    S, K, tau, W, L, r, q, mu, sd = _inputs(S, K, state, parameters, nmax)
    independent = independent_mixture(S, K, state, parameters, nmax=nmax)
    if state.status == "expiry":
        return {
            "price": independent["values"][0],
            "difference": 0.0,
            "status": independent["status"],
        }
    from hullkit.alternative_models import merton_jump_price

    price = merton_jump_price(
        S, K, r, math.sqrt(W / tau), tau, L / tau, mu, sd, dividend_yield=q, kind="call"
    )
    return {
        "price": float(price),
        "difference": float(price - independent["values"][0]),
        "independent_tail_bound": float(independent["tail_bounds"][0]),
        "status": "ok" if math.isfinite(price) else "nonfinite",
    }


def spot_finite_differences(
    S, K, state, parameters, *, nmax=8, relative_steps=(1e-4, 5e-5, 2.5e-5)
):
    """Return centered Delta/Gamma at three decreasing positive spot widths.

    Finite differences have truncation and rounding error; the rows are
    independent diagnostics, not unbiased Greek labels or confidence bounds.
    """
    S, K, *_ = _inputs(S, K, state, parameters, nmax)
    widths = tuple(float(x) for x in relative_steps)
    if len(widths) != 3 or not all(math.isfinite(x) and 0 < x < 1 for x in widths):
        raise ValueError("exactly three finite relative widths in (0,1) are required")
    if not widths[0] > widths[1] > widths[2]:
        raise ValueError("relative widths must be strictly decreasing")
    if state.status == "expiry":
        expiry = _expiry(S, K)
        return [
            {
                "relative_step": relative,
                "step": S * relative,
                "delta": float(expiry["values"][1]),
                "gamma": float(expiry["values"][2]),
                "status": expiry["status"],
                "reason": expiry["reason"],
            }
            for relative in widths
        ]
    center = independent_mixture(S, K, state, parameters, nmax=nmax)["values"][0]
    rows = []
    for relative in widths:
        h = S * relative
        lower = independent_mixture(S - h, K, state, parameters, nmax=nmax)["values"][0]
        upper = independent_mixture(S + h, K, state, parameters, nmax=nmax)["values"][0]
        rows.append(
            {
                "relative_step": relative,
                "step": h,
                "delta": (upper - lower) / (2.0 * h),
                "gamma": math.fsum((upper, lower, -2.0 * center)) / (h * h),
            }
        )
    return rows
