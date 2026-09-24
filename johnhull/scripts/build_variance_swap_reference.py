"""Offline, independent references for Hull GE section 26.16 (volatility and variance swaps).

No hullkit routines are imported: Black-Scholes-Merton, the Heston characteristic
function (Lewis single-integral form), the continuous strip integral of eq. (26.6),
the discrete strip of eq. (26.8), the moments of continuously monitored Heston
variance and the CIR Laplace transform are all written here with NumPy/SciPy.
Markets are synthetic apart from Hull's Examples 26.4 and 26.5. Time is years,
rates and yields continuously compounded, volatilities annualized decimals and
variance rates per year.
"""

import cmath
import math

import numpy as np
from scipy.integrate import quad
from scipy.special import ndtr

QUAD = dict(epsabs=1e-13, epsrel=1e-12, limit=500)
EX_SPOT, EX_RATE, EX_DIVIDEND, EX_EXPIRY = 1020.0, 0.04, 0.01, 0.25
EX_STRIKES = (800.0, 850.0, 900.0, 950.0, 1000.0, 1050.0, 1100.0, 1150.0, 1200.0)
EX_VOLS = (0.29, 0.28, 0.27, 0.26, 0.25, 0.24, 0.23, 0.22, 0.21)
EX_Q_PRINTED = (2.22, 5.22, 11.05, 21.27, 51.21, 38.94, 20.69, 9.44, 3.57)
EX_VARIANCE_STRIKE, EX_NOTIONAL = 0.045, 100.0
EX_VOL_STRIKE, EX_VAR_OF_VAR = 0.23, 0.0001
HESTON_MARKETS = (
    dict(name="skewed", v0=0.04, kappa=1.5, theta=0.04, xi=0.3, rho=-0.7, expiry=0.5),
    dict(name="mean-reverting-down", v0=0.09, kappa=2.0, theta=0.04, xi=0.6, rho=-0.5, expiry=0.25),
    dict(name="long-uncorrelated", v0=0.02, kappa=1.0, theta=0.05, xi=0.4, rho=0.0, expiry=1.0),
)
HESTON_SPOT, HESTON_RATE, HESTON_DIVIDEND = 100.0, 0.03, 0.01
HESTON_LOG_RANGE = (-4.0, 2.5)
FLAT_SIGMA, FLAT_EXPIRY = 0.25, 0.5
CONVEXITY = dict(v0=0.0621, kappa=2.0, theta=0.0621, expiry=0.25)
CONVEXITY_XI = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
CONVEXITY_MC_XI = (0.3, 0.6, 0.9)
MC_STEPS, MC_PATHS, MC_SEED = 250, 100_000, 20260925


def bsm_call_put(spot, strike, rate, dividend, sigma, expiry):
    """European call and put under BSM with a continuous dividend yield."""
    sd = sigma * math.sqrt(expiry)
    forward = spot * math.exp((rate - dividend) * expiry)
    d1 = (math.log(forward / strike) + sd * sd / 2) / sd
    d2 = d1 - sd
    discount = math.exp(-rate * expiry)
    call = discount * (forward * float(ndtr(d1)) - strike * float(ndtr(d2)))
    put = discount * (strike * float(ndtr(-d2)) - forward * float(ndtr(-d1)))
    return call, put


def flat_pricer(spot, rate, dividend, sigma, expiry):
    """Return ``strike -> (call, put)`` for one flat BSM volatility."""
    return lambda strike: bsm_call_put(spot, strike, rate, dividend, sigma, expiry)


def _heston_cf(u, expiry, v0, kappa, theta, xi, rho):
    """E[exp(i u X)] for X = ln(S_T / F), trap-stable branch (Albrecher et al. 2007)."""
    b = kappa - 1j * rho * xi * u
    d = cmath.sqrt(b * b + xi * xi * (1j * u + u * u))
    g = (b - d) / (b + d)
    edt = cmath.exp(-d * expiry)
    c = (kappa * theta / (xi * xi)) * (
        (b - d) * expiry - 2.0 * cmath.log((1.0 - g * edt) / (1.0 - g))
    )
    dterm = (b - d) / (xi * xi) * (1.0 - edt) / (1.0 - g * edt)
    return cmath.exp(c + dterm * v0)


def heston_call_put(spot, strike, rate, dividend, expiry, v0, kappa, theta, xi, rho):
    """Heston call by Lewis's single integral; put by exact parity."""
    forward = spot * math.exp((rate - dividend) * expiry)
    k = math.log(forward / strike)

    def integrand(u):
        value = cmath.exp(1j * u * k) * _heston_cf(u - 0.5j, expiry, v0, kappa, theta, xi, rho)
        return value.real / (u * u + 0.25)

    integral, _ = quad(integrand, 0.0, math.inf, **QUAD)
    prefactor = math.sqrt(spot * strike) * math.exp(-(rate + dividend) * expiry / 2) / math.pi
    call = spot * math.exp(-dividend * expiry) - prefactor * integral
    put = call - spot * math.exp(-dividend * expiry) + strike * math.exp(-rate * expiry)
    return call, put


def heston_pricer(spot, rate, dividend, expiry, v0, kappa, theta, xi, rho):
    """Return a cached ``strike -> (call, put)`` for one Heston market."""
    cache = {}

    def price(strike):
        key = float(strike)
        if key not in cache:
            cache[key] = heston_call_put(
                spot, key, rate, dividend, expiry, v0, kappa, theta, xi, rho
            )
        return cache[key]

    return price


def continuous_expected_variance(pricer, forward, rate, expiry, s_star, log_range):
    """Eq. (26.6) with the strike integrals done by quadrature in x = ln(K/F).

    ``dK/K^2 = e^{-x} dx / F``. Returns (E(V), QUADPACK error estimate of the two
    finite-range integrals scaled like E(V)). Strikes outside ``log_range`` are
    omitted; callers choose a range whose tails are negligible.
    """
    lo, hi = log_range
    split = math.log(s_star / forward)
    if not lo < split < hi:
        raise ValueError("S* must lie inside the integration range")

    def put_part(x):
        return pricer(forward * math.exp(x))[1] * math.exp(-x) / forward

    def call_part(x):
        return pricer(forward * math.exp(x))[0] * math.exp(-x) / forward

    puts, put_error = quad(put_part, lo, split, **QUAD)
    calls, call_error = quad(call_part, split, hi, **QUAD)
    ratio = forward / s_star
    scale = 2.0 / expiry * math.exp(rate * expiry)
    value = 2.0 / expiry * (math.log(ratio) - (ratio - 1.0)) + scale * (puts + calls)
    return value, scale * (put_error + call_error)


def hull_spacing(strikes):
    """``Delta K_i`` of eq. (26.8)."""
    k = np.asarray(strikes, dtype=float)
    spacing = np.empty_like(k)
    spacing[1:-1] = 0.5 * (k[2:] - k[:-2])
    spacing[0] = k[1] - k[0]
    spacing[-1] = k[-1] - k[-2]
    return spacing


def discrete_strip_expected_variance(
    pricer, strikes, forward, rate, expiry, s_star=None, q_out=None
):
    """Eq. (26.6) with the integrals replaced by the strip of eq. (26.8).

    ``q_out``, when a list, receives the ``Q(K_i)`` used (for noise-floor records).
    """
    k = np.asarray(strikes, dtype=float)
    if s_star is None:
        s_star = float(k[k <= forward][-1])
    q = []
    for strike in k:
        call, put = pricer(float(strike))
        if math.isclose(strike, s_star, rel_tol=1e-12, abs_tol=0.0):
            q.append(0.5 * (call + put))
        else:
            q.append(put if strike < s_star else call)
    if q_out is not None:
        q_out.extend(q)
    strip = math.fsum(hull_spacing(k) / k**2 * math.exp(rate * expiry) * np.asarray(q))
    ratio = forward / s_star
    return 2.0 / expiry * (math.log(ratio) - (ratio - 1.0)) + 2.0 / expiry * strip


def heston_expected_variance(v0, kappa, theta, expiry):
    """E(V) = E[(1/T) ∫ v dt] for the Heston/CIR variance process."""
    return theta + (v0 - theta) * (1.0 - math.exp(-kappa * expiry)) / (kappa * expiry)


def heston_variance_of_variance(v0, kappa, theta, xi, expiry):
    """var(V) of V = (1/T) ∫ v dt: xi^2 ∫ b(s)^2 E[v_s] ds / T^2 (Itô isometry)."""

    def integrand(s):
        b = (1.0 - math.exp(-kappa * (expiry - s))) / kappa
        return b * b * (theta + (v0 - theta) * math.exp(-kappa * s))

    value, _ = quad(integrand, 0.0, expiry, **QUAD)
    return xi * xi * value / expiry**2


def _cir_log_laplace(s, v0, kappa, theta, xi, expiry):
    """ln E[exp(-s ∫_0^T v dt)] from the CIR bond formula, overflow- and cancellation-free.

    With gamma = sqrt(kappa^2 + 2 xi^2 s) and delta = gamma - kappa = 2 xi^2 s / (gamma + kappa),
    the log of the bond-formula factor A is
    (2 kappa theta / xi^2)[log1p(delta/(gamma+kappa)) - delta T/2 - log1p(delta e^{-gamma T}/(gamma+kappa))],
    so no O(1) logs are subtracted when xi^2 s is small.
    """
    gamma = math.sqrt(kappa * kappa + 2.0 * xi * xi * s)
    total = gamma + kappa
    delta = 2.0 * xi * xi * s / total
    decay = math.exp(-gamma * expiry)
    bracket = math.log1p(delta / total) - delta * expiry / 2.0 - math.log1p(delta * decay / total)
    log_a = (2.0 * kappa * theta / (xi * xi)) * bracket
    b = -2.0 * math.expm1(-gamma * expiry) / (total + delta * decay)
    return log_a - b * s * v0


def cir_laplace_sqrt_mean(v0, kappa, theta, xi, expiry, split=1e-2):
    """E[sqrt V] = E[sqrt X]/sqrt(T), E[sqrt X] = pi^{-1/2} ∫_0^∞ (1 - E e^{-t^2 X}) t^{-2} dt.

    Below ``split`` the integrand uses its Taylor expansion E[X] - t^2 E[X^2]/2
    (the exact form cancels catastrophically there).
    """
    mean_x = heston_expected_variance(v0, kappa, theta, expiry) * expiry
    var_x = heston_variance_of_variance(v0, kappa, theta, xi, expiry) * expiry**2
    second_x = var_x + mean_x * mean_x
    head = split * mean_x - split**3 * second_x / 6.0

    def integrand(t):
        return -math.expm1(_cir_log_laplace(t * t, v0, kappa, theta, xi, expiry)) / (t * t)

    tail, _ = quad(integrand, split, math.inf, **QUAD)
    return (head + tail) / math.sqrt(math.pi) / math.sqrt(expiry)


def cir_integrated_variance_mc(v0, kappa, theta, xi, expiry, steps, paths, seed, chunk=25_000):
    """Exact CIR transitions (noncentral chi-square) with trapezoid time integration."""
    rng = np.random.default_rng(seed)
    dt = expiry / steps
    scale = xi * xi * (1.0 - math.exp(-kappa * dt)) / (4.0 * kappa)
    dof = 4.0 * kappa * theta / (xi * xi)
    decay = math.exp(-kappa * dt)
    values = []
    for start in range(0, paths, chunk):
        n = min(chunk, paths - start)
        v = np.full(n, v0)
        integral = 0.5 * v * dt
        for step in range(steps):
            v = scale * rng.noncentral_chisquare(dof, np.maximum(v * decay / scale, 0.0))
            integral += (0.5 if step == steps - 1 else 1.0) * v * dt
        values.append(integral / expiry)
    realized = np.concatenate(values)
    root = np.sqrt(realized)
    return {
        "mean": float(realized.mean()),
        "mean_se": float(realized.std(ddof=1) / math.sqrt(paths)),
        "sqrt_mean": float(root.mean()),
        "sqrt_mean_se": float(root.std(ddof=1) / math.sqrt(paths)),
        "variance": float(realized.var(ddof=1)),
    }


def _denominator(n, denominator):
    if denominator == "n-2":
        return n - 2
    if denominator == "n-1":
        return n - 1
    raise ValueError("denominator must be 'n-2' or 'n-1'")


def realized_variance_expectation(n, sigma, drift, denominator="n-2", periods=252):
    """Exact E of Hull's zero-mean estimator for GBM daily log returns N(m, s^2)."""
    m, s2 = drift / periods, sigma * sigma / periods
    return periods * (n - 1) * (s2 + m * m) / _denominator(n, denominator)


def realized_variance_mc(n, sigma, drift, denominator, paths, seed, periods=252):
    """MC of the same estimator; returns the mean and its standard error."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(drift / periods, sigma / math.sqrt(periods), size=(paths, n - 1))
    estimate = periods * np.sum(returns * returns, axis=1) / _denominator(n, denominator)
    return {
        "mean": float(estimate.mean()),
        "mean_se": float(estimate.std(ddof=1) / math.sqrt(paths)),
    }


def vix_truncation_gap(ratio):
    """Eq. (26.6) minus eq. (26.10), in cumulative variance: 2[ln x - (x-1) + (x-1)^2/2]."""
    return 2.0 * (math.log(ratio) - (ratio - 1.0) + 0.5 * (ratio - 1.0) ** 2)


def vix_interpolate(near_term, near_cumulative, next_term, next_cumulative, target=30 / 365):
    """Interpolate cumulative variance linearly in time, annualize by 1/target, take the root."""
    weight = (next_term - target) / (next_term - near_term)
    cumulative = weight * near_cumulative + (1.0 - weight) * next_cumulative
    return math.sqrt(cumulative / target)


def example_26_4():
    """Hull Example 26.4 recomputed with this module's BSM."""
    forward = EX_SPOT * math.exp((EX_RATE - EX_DIVIDEND) * EX_EXPIRY)
    strikes = np.asarray(EX_STRIKES)
    s_star = float(strikes[strikes <= forward][-1])
    spacing = hull_spacing(strikes)
    rows = []
    for strike, vol, dk, printed in zip(EX_STRIKES, EX_VOLS, spacing, EX_Q_PRINTED, strict=True):
        call, put = bsm_call_put(EX_SPOT, strike, EX_RATE, EX_DIVIDEND, vol, EX_EXPIRY)
        if strike == s_star:
            q, kind = 0.5 * (call + put), "average"
        else:
            q, kind = (put, "put") if strike < s_star else (call, "call")
        weight = float(dk) / strike**2 * math.exp(EX_RATE * EX_EXPIRY)
        rows.append(
            dict(
                strike=strike,
                implied_volatility=vol,
                call=call,
                put=put,
                q=q,
                q_kind=kind,
                printed_q=printed,
                delta_k=float(dk),
                weight=weight,
                contribution=weight * q,
            )
        )
    ratio = forward / s_star
    boundary = 2.0 / EX_EXPIRY * (math.log(ratio) - (ratio - 1.0))
    strip = math.fsum(row["contribution"] for row in rows)
    printed_strip = math.fsum(row["weight"] * row["printed_q"] for row in rows)
    expected = boundary + 2.0 / EX_EXPIRY * strip
    printed_expected = boundary + 2.0 / EX_EXPIRY * printed_strip
    discount = math.exp(-EX_RATE * EX_EXPIRY)
    return dict(
        spot=EX_SPOT,
        rate=EX_RATE,
        dividend=EX_DIVIDEND,
        expiry=EX_EXPIRY,
        forward=forward,
        s_star=s_star,
        rows=rows,
        q_values=[row["q"] for row in rows],
        boundary_terms=boundary,
        strip_sum=strip,
        printed_q_strip_sum=printed_strip,
        expected_variance=expected,
        printed_q_expected_variance=printed_expected,
        swap_value=EX_NOTIONAL * (expected - EX_VARIANCE_STRIKE) * discount,
        printed_q_swap_value=EX_NOTIONAL * (printed_expected - EX_VARIANCE_STRIKE) * discount,
    )


def example_26_5(expected_variance):
    """Hull Example 26.5 from a given E(V) (Hull uses the rounded 0.0621)."""
    expected_vol = math.sqrt(expected_variance) * (
        1.0 - EX_VAR_OF_VAR / (8.0 * expected_variance**2)
    )
    discount = math.exp(-EX_RATE * EX_EXPIRY)
    return dict(
        expected_variance=expected_variance,
        variance_of_variance=EX_VAR_OF_VAR,
        expected_volatility=expected_vol,
        naive_volatility=math.sqrt(expected_variance),
        swap_value=EX_NOTIONAL * (expected_vol - EX_VOL_STRIKE) * discount,
    )


def _heston_forward(expiry):
    return HESTON_SPOT * math.exp((HESTON_RATE - HESTON_DIVIDEND) * expiry)


def _heston_params(market):
    return {key: market[key] for key in ("v0", "kappa", "theta", "xi", "rho")}


def _flat_replication():
    forward = _heston_forward(FLAT_EXPIRY)
    pricer = flat_pricer(HESTON_SPOT, HESTON_RATE, HESTON_DIVIDEND, FLAT_SIGMA, FLAT_EXPIRY)
    width = 12.0 * FLAT_SIGMA * math.sqrt(FLAT_EXPIRY)
    rows = []
    for ratio in (0.8, 0.9, 1.0, 1.1, 1.25):
        value, error = continuous_expected_variance(
            pricer, forward, HESTON_RATE, FLAT_EXPIRY, forward * ratio, (-width, width)
        )
        rows.append(
            dict(
                s_star_over_forward=ratio,
                expected_variance=value,
                quadrature_error=error,
                exact=FLAT_SIGMA**2,
                difference=value - FLAT_SIGMA**2,
            )
        )
    return dict(sigma=FLAT_SIGMA, expiry=FLAT_EXPIRY, log_range=[-width, width], rows=rows)


def _heston_replication(pricers):
    rows = []
    for market in HESTON_MARKETS:
        expiry = market["expiry"]
        forward = _heston_forward(expiry)
        value, error = continuous_expected_variance(
            pricers[market["name"]], forward, HESTON_RATE, expiry, forward, HESTON_LOG_RANGE
        )
        exact = heston_expected_variance(market["v0"], market["kappa"], market["theta"], expiry)
        rows.append(
            dict(
                market=market["name"],
                params=_heston_params(market),
                expiry=expiry,
                forward=forward,
                expected_variance=value,
                quadrature_error=error,
                closed_form=exact,
                difference=value - exact,
            )
        )
    return dict(
        spot=HESTON_SPOT,
        rate=HESTON_RATE,
        dividend=HESTON_DIVIDEND,
        log_range=list(HESTON_LOG_RANGE),
        rows=rows,
    )


def _strip_convergence(pricers):
    market = HESTON_MARKETS[0]
    expiry = market["expiry"]
    forward = _heston_forward(expiry)
    exact = heston_expected_variance(market["v0"], market["kappa"], market["theta"], expiry)
    ranges = {"narrow": (70.0, 140.0), "medium": (40.0, 220.0), "wide": (10.0, 400.0)}
    families = []
    for name, (lo, hi) in ranges.items():
        rows = []
        for step in (10.0, 5.0, 2.5, 1.25):
            strikes = np.arange(lo, hi + step / 2, step)
            q_used = []
            value = discrete_strip_expected_variance(
                pricers[market["name"]], strikes, forward, HESTON_RATE, expiry, q_out=q_used
            )
            q_array = np.asarray(q_used)
            weights = (
                2.0 / expiry * hull_spacing(strikes) / strikes**2 * math.exp(HESTON_RATE * expiry)
            )
            negative = q_array < 0.0
            rows.append(
                dict(
                    delta_k=step,
                    strikes=len(strikes),
                    s_star=float(strikes[strikes <= forward][-1]),
                    expected_variance=value,
                    error=value - exact,
                    min_q=min(q_used),
                    negative_q_weight=float(np.sum(weights[negative] * -q_array[negative])),
                )
            )
        families.append(dict(range=name, strike_low=lo, strike_high=hi, rows=rows))
    return dict(
        market=market["name"], expiry=expiry, forward=forward, exact=exact, families=families
    )


def _volatility_convexity():
    base = CONVEXITY
    rows = []
    for xi in CONVEXITY_XI:
        mean_v = heston_expected_variance(base["v0"], base["kappa"], base["theta"], base["expiry"])
        var_v = heston_variance_of_variance(
            base["v0"], base["kappa"], base["theta"], xi, base["expiry"]
        )
        exact = cir_laplace_sqrt_mean(base["v0"], base["kappa"], base["theta"], xi, base["expiry"])
        approx = math.sqrt(mean_v) * (1.0 - var_v / (8.0 * mean_v**2))
        row = dict(
            xi=xi,
            expected_variance=mean_v,
            variance_of_variance=var_v,
            exact_expected_volatility=exact,
            approximation=approx,
            naive=math.sqrt(mean_v),
            approximation_error=approx - exact,
            naive_error=math.sqrt(mean_v) - exact,
            mc=None,
        )
        if xi in CONVEXITY_MC_XI:
            mc = cir_integrated_variance_mc(
                base["v0"],
                base["kappa"],
                base["theta"],
                xi,
                base["expiry"],
                steps=MC_STEPS,
                paths=MC_PATHS,
                seed=MC_SEED + round(100 * xi),
            )
            mc["sqrt_mean_zscore"] = (mc["sqrt_mean"] - exact) / mc["sqrt_mean_se"]
            mc["mean_zscore"] = (mc["mean"] - mean_v) / mc["mean_se"]
            mc["variance_relative_gap"] = mc["variance"] / var_v - 1.0
            row["mc"] = mc
        rows.append(row)
    return dict(
        base=base,
        mc=dict(
            steps=MC_STEPS, paths=MC_PATHS, seed=MC_SEED, method="exact CIR transitions, trapezoid"
        ),
        rows=rows,
    )


def _realized_variance():
    n, sigma = 64, 0.25
    drift = HESTON_RATE - HESTON_DIVIDEND - sigma * sigma / 2
    rows = []
    # Separate draws per denominator: with shared draws the two estimates differ
    # only by the factor (n-1)/(n-2) and would be one check, not two.
    for offset, denominator in enumerate(("n-2", "n-1")):
        exact = realized_variance_expectation(n, sigma, drift, denominator=denominator)
        mc = realized_variance_mc(
            n, sigma, drift, denominator, paths=200_000, seed=MC_SEED + 1000 * (offset + 1)
        )
        rows.append(
            dict(
                denominator=denominator,
                exact_expectation=exact,
                bias_vs_sigma_squared=exact - sigma * sigma,
                mc_mean=mc["mean"],
                mc_se=mc["mean_se"],
                zscore=(mc["mean"] - exact) / mc["mean_se"],
            )
        )
    return dict(observations=n, sigma=sigma, log_drift=drift, periods_per_year=252, rows=rows)


def _vix(example):
    ratio = example["forward"] / example["s_star"]
    cumulative_26_6 = example["expected_variance"] * EX_EXPIRY
    cumulative_26_10 = -((ratio - 1.0) ** 2) + 2.0 * example["strip_sum"]
    market = HESTON_MARKETS[1]
    near, following, target = 23 / 365, 37 / 365, 30 / 365

    def cumulative(term):
        return heston_expected_variance(market["v0"], market["kappa"], market["theta"], term) * term

    interpolated = vix_interpolate(near, cumulative(near), following, cumulative(following))
    exact = math.sqrt(cumulative(target) / target)
    return dict(
        example_26_4=dict(
            forward_over_s_star=ratio,
            cumulative_variance_26_6=cumulative_26_6,
            cumulative_variance_26_10=cumulative_26_10,
            gap=cumulative_26_6 - cumulative_26_10,
            gap_formula=vix_truncation_gap(ratio),
            cubic_leading_term=2.0 * (ratio - 1.0) ** 3 / 3.0,
        ),
        interpolation=dict(
            market=market["name"],
            near_days=23,
            next_days=37,
            target_days=30,
            interpolated_volatility=interpolated,
            exact_30_day_volatility=exact,
            error=interpolated - exact,
        ),
    )


def build_artifacts():
    """Return (reference, numerical record) as JSON-ready dictionaries."""
    import hashlib
    import json
    from pathlib import Path

    example4 = example_26_4()
    example5 = example_26_5(0.0621)
    example5_unrounded = example_26_5(example4["expected_variance"])
    pricers = {
        market["name"]: heston_pricer(
            HESTON_SPOT,
            HESTON_RATE,
            HESTON_DIVIDEND,
            market["expiry"],
            **_heston_params(market),
        )
        for market in HESTON_MARKETS
    }
    flat = _flat_replication()
    replication = _heston_replication(pricers)
    convergence = _strip_convergence(pricers)
    convexity = _volatility_convexity()
    realized = _realized_variance()
    vix = _vix(example4)
    reference = dict(
        schema_version=1,
        section="26.16",
        source_pages=[629, 630, 631, 632],
        units=dict(
            price="currency",
            time="years",
            rates="continuously compounded annual",
            volatility="annualized decimal",
            variance="variance rate per year",
            cumulative_variance="dimensionless E(V)T",
            notional="$ millions per unit volatility or variance (Hull's examples)",
        ),
        example_26_4=example4,
        example_26_5=example5,
        example_26_5_unrounded=example5_unrounded,
        flat_replication=flat,
        heston_replication=replication,
        strip_convergence=convergence,
        volatility_convexity=convexity,
        realized_variance=realized,
        vix=vix,
    )
    mc_rows = [row["mc"] for row in convexity["rows"] if row["mc"] is not None]
    checks = {
        "example_26_4_printed_q_2dp": max(
            abs(row["q"] - row["printed_q"]) for row in example4["rows"]
        )
        < 5e-3,
        "example_26_4_expected_variance": abs(example4["expected_variance"] - 0.0621) < 5e-5,
        "example_26_4_value": abs(example4["swap_value"] - 1.69) < 5e-3,
        "example_26_5_expected_volatility": abs(example5["expected_volatility"] - 0.2484) < 5e-5,
        "example_26_5_value": abs(example5["swap_value"] - 1.82) < 5e-3,
        "flat_replication_s_star_invariant": max(abs(row["difference"]) for row in flat["rows"])
        < 1e-9,
        "heston_replication_closed_form": max(abs(row["difference"]) for row in replication["rows"])
        < 1e-8,
        "wide_fine_strip_converges": abs(convergence["families"][2]["rows"][-1]["error"]) < 1e-4,
        "convexity_mc_within_4se": all(abs(mc["sqrt_mean_zscore"]) < 4 for mc in mc_rows),
        "variance_mc_within_4se": all(abs(mc["mean_zscore"]) < 4 for mc in mc_rows),
        "realized_variance_mc_within_4se": all(abs(row["zscore"]) < 4 for row in realized["rows"]),
        "vix_gap_matches_formula": abs(
            vix["example_26_4"]["gap"] - vix["example_26_4"]["gap_formula"]
        )
        < 1e-12,
    }
    record = dict(
        schema_version=1,
        section="26.16",
        status="PASS" if all(checks.values()) else "FAIL",
        scope=(
            "Independent numerical reference for §26.16 (M8a): printed examples, replication, "
            "strip error, convexity, daily estimator and VIX. The section's status is kept in "
            "the section ledger, not here."
        ),
        source_pages=[629, 630, 631, 632],
        printed_anchors=dict(
            example_26_4=dict(
                strip_sum=example4["strip_sum"],
                expected_variance=example4["expected_variance"],
                swap_value=example4["swap_value"],
                printed=dict(strip_sum=0.008139, expected_variance=0.0621, swap_value=1.69),
            ),
            example_26_5=dict(
                expected_volatility=example5["expected_volatility"],
                swap_value=example5["swap_value"],
                printed=dict(expected_volatility=0.2484, swap_value=1.82),
            ),
        ),
        checks=checks,
        method=dict(
            options=(
                "Own BSM; Heston by Lewis single integral of the trap-stable CF (quad to infinity). "
                "Deep out-of-the-money Heston prices carry about 1e-11 of cancellation noise "
                "(strip_min_q); the negative ones weigh at most strip_negative_q_max_weight "
                "(about 2e-14) in E(V) after the 1/K^2 weights"
            ),
            replication="Eq. 26.6 by quad in x=ln(K/F) over a declared finite range; tails omitted",
            strip="Eq. 26.8 with Hull's spacing, S* = largest strike <= F0, Q average at S*",
            variance_of_variance="xi^2 ∫ b(s)^2 E[v_s] ds / T^2 from the Itô isometry",
            expected_volatility="CIR Laplace transform integral with a Taylor head below t=1e-2",
            mc="Exact CIR transitions (noncentral chi-square), trapezoid in time, fixed seeds",
            reproducibility="No timestamps; --check regenerates both files byte for byte",
        ),
        tolerances=dict(
            quad_epsabs=QUAD["epsabs"],
            quad_epsrel=QUAD["epsrel"],
            mc_standard_errors=4.0,
        ),
        measured=dict(
            flat_max_abs_difference=max(abs(row["difference"]) for row in flat["rows"]),
            heston_max_abs_difference=max(abs(row["difference"]) for row in replication["rows"]),
            heston_max_quadrature_error=max(row["quadrature_error"] for row in replication["rows"]),
            convexity_max_abs_approximation_error=max(
                abs(row["approximation_error"]) for row in convexity["rows"]
            ),
            convexity_max_abs_zscore=max(abs(mc["sqrt_mean_zscore"]) for mc in mc_rows),
            strip_min_q=min(
                row["min_q"] for family in convergence["families"] for row in family["rows"]
            ),
            strip_negative_q_max_weight=max(
                row["negative_q_weight"]
                for family in convergence["families"]
                for row in family["rows"]
            ),
            vix_truncation_gap=vix["example_26_4"]["gap"],
            vix_interpolation_error=vix["interpolation"]["error"],
        ),
        caveat=(
            "Synthetic Heston markets and a fixed strike grid; the measured errors are not bounds. "
            "Continuous monitoring and continuous paths are assumed except in the daily-estimator check."
        ),
    )
    project = Path(__file__).resolve().parents[1]
    record["source_sha256"] = {
        name: hashlib.sha256((project / name).read_bytes()).hexdigest()
        for name in (
            "scripts/build_variance_swap_reference.py",
            "hullkit/tests/test_variance_swap_reference.py",
        )
    }
    serialized = json.dumps(reference, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    record["artifact_sha256"] = {
        "docs/validation/section-26-16/reference.json": hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()
    }
    return reference, record


def main():
    """Write reference JSON or check byte reproducibility with --check."""
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = Path(__file__).resolve().parents[1] / "docs" / "validation" / "section-26-16"
    objects = build_artifacts()
    for name, value in zip(("reference.json", "numerical-check.json"), objects, strict=True):
        content = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        path = output / name
        if args.check:
            if not path.is_file() or path.read_bytes() != content.encode("utf-8"):
                raise SystemExit(f"FAIL: {name} is stale")
        else:
            output.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(
        "PASS: variance-swap reference " + ("byte reproducibility" if args.check else "generated")
    )


if __name__ == "__main__":
    main()
