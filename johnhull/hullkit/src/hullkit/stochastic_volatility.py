"""Stochastic-volatility building blocks for Hull 11e GE §27.2 (pp.646–649).

Hull's notation maps to the arguments as follows: the variance rate ``V`` of
equations (27.2)–(27.3) reverts at rate ``a`` (``reversion``) to ``V_L``
(``long_run``) with volatility ``xi`` (``vol_of_variance``). The square-root
case alpha=0.5 is Heston's model. Times are in years, rates and volatilities
are annualized decimals and prices are in currency. These are teaching
implementations for constant parameters, not calibration engines.

SABR smiles use :func:`hullkit.sabr.sabr_implied_vol`, which is Hull's printed
Hagan approximation (``alpha`` there is Hull's ``sigma_0``).
"""

import math

import numpy as np

from . import bsm, fourier, heston


def _finite(**values):
    for name, value in values.items():
        if not np.isscalar(value) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite scalar")


def _check_kind(kind):
    if kind not in ("call", "put"):
        raise ValueError("kind must be 'call' or 'put'")


def average_variance_rate(durations, volatilities):
    """Hull eq. (27.1): time-weighted average of the variance rate sigma(t)**2.

    ``durations`` are the lengths (years) of consecutive intervals on which the
    volatility is ``volatilities[i]``. Hull's example (0.5 years at 20% then
    0.5 years at 30%) returns 0.065, i.e. a Black–Scholes–Merton volatility
    of sqrt(0.065)=25.5%, not the arithmetic 25%.
    """
    durations = np.asarray(durations, dtype=float)
    volatilities = np.asarray(volatilities, dtype=float)
    if durations.ndim != 1 or durations.shape != volatilities.shape or durations.size == 0:
        raise ValueError("durations and volatilities must be equal-length 1-D sequences")
    if not (np.all(np.isfinite(durations)) and np.all(np.isfinite(volatilities))):
        raise ValueError("durations and volatilities must be finite")
    if np.any(durations <= 0.0) or np.any(volatilities < 0.0):
        raise ValueError("durations must be positive and volatilities nonnegative")
    return float(np.dot(durations, volatilities**2) / durations.sum())


def time_dependent_bsm_price(
    spot, strike, rate, durations, volatilities, dividend_yield=0.0, *, kind="call"
):
    """European price when volatility is a known step function of time (eq. 27.1).

    The option expires after ``sum(durations)`` years. The price is the
    Black–Scholes–Merton price with the average variance rate of
    :func:`average_variance_rate` over the option's life.
    """
    _finite(spot=spot, strike=strike, rate=rate, dividend_yield=dividend_yield)
    _check_kind(kind)
    if spot <= 0.0 or strike <= 0.0:
        raise ValueError("spot and strike must be positive")
    variance = average_variance_rate(durations, volatilities)
    expiry = float(np.sum(durations))
    pricer = bsm.call_price if kind == "call" else bsm.put_price
    return float(pricer(spot, strike, rate, math.sqrt(variance), expiry, dividend_yield))


def expected_average_variance(v0, reversion, long_run, expiry):
    """Risk-neutral mean of the average variance rate over ``[0, expiry]``.

    For ``dV=a(V_L-V)dt+...`` the mean path is ``V_L+(V_0-V_L)e^{-at}``, so
    ``E[V_bar]=V_L+(V_0-V_L)(1-e^{-aT})/(aT)`` (``V_0`` when ``a=0``).
    """
    _finite(v0=v0, reversion=reversion, long_run=long_run, expiry=expiry)
    if v0 < 0.0 or long_run < 0.0 or reversion < 0.0 or expiry <= 0.0:
        raise ValueError("require v0, long_run, reversion >= 0 and expiry > 0")
    scaled = reversion * expiry
    weight = -math.expm1(-scaled) / scaled if scaled > 0.0 else 1.0
    return float(long_run + (v0 - long_run) * weight)


def simulate_average_variance(
    v0, reversion, long_run, vol_of_variance, expiry, *, n_steps, n_paths, seed
):
    """Sample the average variance rate of the alpha=0.5 process of eq. (27.3).

    Each step uses the exact square-root (CIR) transition, a scaled noncentral
    chi-square draw, so no discretization bias enters the variance path. The
    time average over ``n_steps`` equal steps uses the trapezoid rule; that
    quadrature is the only discretization error. Returns ``n_paths`` averages.
    """
    _finite(
        v0=v0,
        reversion=reversion,
        long_run=long_run,
        vol_of_variance=vol_of_variance,
        expiry=expiry,
    )
    if v0 < 0.0 or reversion <= 0.0 or long_run <= 0.0 or vol_of_variance <= 0.0:
        raise ValueError("require v0 >= 0 and positive reversion, long_run, vol_of_variance")
    if expiry <= 0.0:
        raise ValueError("expiry must be > 0")
    for name, value in (("n_steps", n_steps), ("n_paths", n_paths)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    rng = np.random.default_rng(seed)
    dt = expiry / n_steps
    decay = math.exp(-reversion * dt)
    scale = vol_of_variance**2 * -math.expm1(-reversion * dt) / (4.0 * reversion)
    degrees = 4.0 * reversion * long_run / vol_of_variance**2
    variance = np.full(n_paths, float(v0))
    total = 0.5 * variance
    for step in range(n_steps):
        variance = scale * rng.noncentral_chisquare(degrees, variance * decay / scale)
        total = total + (0.5 * variance if step == n_steps - 1 else variance)
    return total * dt / expiry


def mixing_price(spot, strike, rate, expiry, average_variances, dividend_yield=0.0, *, kind="call"):
    """Hull–White price: the BSM price averaged over the average variance rate.

    Valid when volatility is uncorrelated with the asset price (Hull §27.2):
    ``c = integral c_BSM(V_bar) g(V_bar) dV_bar``. ``average_variances`` are
    equally weighted draws of ``V_bar``, e.g. from
    :func:`simulate_average_variance`. Returns ``(price, standard_error)``.
    """
    _finite(spot=spot, strike=strike, rate=rate, expiry=expiry, dividend_yield=dividend_yield)
    _check_kind(kind)
    if spot <= 0.0 or strike <= 0.0 or expiry <= 0.0:
        raise ValueError("spot, strike and expiry must be positive")
    samples = np.asarray(average_variances, dtype=float)
    if samples.ndim != 1 or samples.size < 2:
        raise ValueError("average_variances must hold at least two draws")
    if not np.all(np.isfinite(samples)) or np.any(samples <= 0.0):
        raise ValueError("average variances must be finite and positive")
    pricer = bsm.call_price if kind == "call" else bsm.put_price
    values = np.asarray(
        pricer(spot, strike, rate, np.sqrt(samples), expiry, dividend_yield), dtype=float
    )
    return float(values.mean()), float(values.std(ddof=1) / math.sqrt(values.size))


def heston_price(
    spot,
    strike,
    rate,
    expiry,
    v0,
    reversion,
    long_run,
    vol_of_variance,
    rho,
    dividend_yield=0.0,
    *,
    kind="call",
    terms=1024,
    truncation=30.0,
):
    """European price for Hull's correlated alpha=0.5 model (Heston) by COS.

    ``dS/S=(r-q)dt+sqrt(V)dz_S`` and ``dV=a(V_L-V)dt+xi sqrt(V)dz_V`` with
    correlation ``rho``. Uses :func:`hullkit.heston.heston_cf` (trap-stable)
    with drift ``r-q`` and :func:`hullkit.fourier.cos_price` with ``terms``
    cosine terms on ``truncation`` standard deviations. The put is priced by
    COS and the call by put-call parity, because a heavy right tail (positive
    ``rho``) truncates badly for calls. ``vol_of_variance`` below 1e-3 is
    rejected: the characteristic function loses precision there, and the
    xi->0 limit is the BSM price with :func:`expected_average_variance`.
    Negative ``rho`` produces the downward equity skew.
    """
    _finite(
        spot=spot,
        strike=strike,
        rate=rate,
        expiry=expiry,
        v0=v0,
        reversion=reversion,
        long_run=long_run,
        vol_of_variance=vol_of_variance,
        rho=rho,
        dividend_yield=dividend_yield,
    )
    _check_kind(kind)
    if spot <= 0.0 or strike <= 0.0 or expiry <= 0.0:
        raise ValueError("spot, strike and expiry must be positive")
    if v0 < 0.0 or reversion <= 0.0 or long_run <= 0.0:
        raise ValueError("require v0 >= 0 and positive reversion and long_run")
    if vol_of_variance < 1e-3:
        raise ValueError("vol_of_variance must be >= 1e-3 (use the BSM limit below that)")
    if not -1.0 < rho < 1.0:
        raise ValueError("rho must lie in (-1, 1)")
    drift = rate - dividend_yield

    def characteristic(u):
        return heston.heston_cf(u, drift, expiry, v0, reversion, long_run, vol_of_variance, rho)

    put = fourier.cos_price(
        characteristic, spot, strike, rate, expiry, kind="put", N=terms, L=truncation
    )
    if kind == "put":
        return float(put)
    return float(
        put + spot * math.exp(-dividend_yield * expiry) - strike * math.exp(-rate * expiry)
    )
