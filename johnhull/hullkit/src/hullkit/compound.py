"""European compound options under constant GBM (Hull GE §26.7, pp.618–619)."""

import math

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import ndtr

from . import bsm

_KINDS = {"call_on_call", "put_on_call", "call_on_put", "put_on_put"}


def _bivariate_normal(a, b, rho):
    """Deterministic bivariate normal CDF via a correlation-angle integral.

    Integrating the bivariate density's derivative with respect to rho,
    then substituting rho=sin(theta), removes the square-root singularity.
    This is not the randomized multivariate-normal CDF routine.
    """
    if rho == 1:
        return float(ndtr(min(a, b)))
    if rho == -1:
        return max(float(ndtr(a) + ndtr(b) - 1), 0.0)

    def density_angle(theta):
        sine, cosine = math.sin(theta), math.cos(theta)
        exponent = ((a - b) ** 2 + 2 * a * b * (1 - sine)) / (2 * cosine * cosine)
        return math.exp(-max(exponent, 0.0))

    correction, _ = quad(density_angle, 0, math.asin(rho), epsabs=2e-13, epsrel=2e-13, limit=200)
    value = float(ndtr(a) * ndtr(b) + correction / (2 * math.pi))
    lower, upper = max(float(ndtr(a) + ndtr(b) - 1), 0), float(min(ndtr(a), ndtr(b)))
    if not math.isfinite(value) or value < lower - 2e-12 or value > upper + 2e-12:
        raise ValueError("bivariate normal integration failed")
    return min(max(value, lower), upper)


def _critical_spot(K1, K2, r, sigma, tau, q, inner):
    """Return the finite positive V(S*,tau)=K1 threshold, or None at a bound."""
    if K1 == 0 or (inner == "put" and K1 >= K2 * math.exp(-r * tau)):
        return None
    target = K1 / K2
    vanilla = getattr(bsm, inner + "_price")

    def residual(log_spot):
        return float(vanilla(math.exp(log_spot), 1, r, sigma, tau, q)) - target

    lo, hi = -1.0, 1.0
    for _ in range(10):
        if residual(lo) * residual(hi) <= 0:
            return K2 * math.exp(brentq(residual, lo, hi, xtol=1e-13, rtol=1e-14))
        lo, hi = lo * 2, hi * 2
    raise ValueError("compound critical spot is outside the representable range")


def _price(S, K1, K2, r, sigma, T1, T2, q, kind):
    outer, inner = kind.split("_on_")
    vanilla = getattr(bsm, inner + "_price")
    if K1 == 0:
        return float(vanilla(S, K2, r, sigma, T2, q)) if outer == "call" else 0.0
    strike_pv = K1 * math.exp(-r * T1)
    if sigma == 0:
        spot1 = S * math.exp((r - q) * T1)
        value1 = float(vanilla(spot1, K2, r, 0, T2 - T1, q))
        return math.exp(-r * T1) * max(value1 - K1 if outer == "call" else K1 - value1, 0)
    if inner == "put" and K1 >= K2 * math.exp(-r * (T2 - T1)):
        return 0.0 if outer == "call" else strike_pv - float(vanilla(S, K2, r, sigma, T2, q))
    threshold = _critical_spot(K1, K2, r, sigma, T2 - T1, q, inner)
    vol1, vol2 = sigma * math.sqrt(T1), sigma * math.sqrt(T2)
    a1 = (math.log(S / threshold) + (r - q + sigma * sigma / 2) * T1) / vol1
    a2 = a1 - vol1
    b1 = (math.log(S / K2) + (r - q + sigma * sigma / 2) * T2) / vol2
    b2 = b1 - vol2
    rho = math.sqrt(T1 / T2)
    asset, bond = S * math.exp(-q * T2), K2 * math.exp(-r * T2)
    M = _bivariate_normal
    if kind == "call_on_call":
        value = asset * M(a1, b1, rho) - bond * M(a2, b2, rho) - strike_pv * ndtr(a2)
    elif kind == "put_on_call":
        value = bond * M(-a2, b2, -rho) - asset * M(-a1, b1, -rho) + strike_pv * ndtr(-a2)
    elif kind == "call_on_put":
        value = bond * M(-a2, -b2, rho) - asset * M(-a1, -b1, rho) - strike_pv * ndtr(-a2)
    else:
        value = asset * M(a1, -b1, -rho) - bond * M(a2, -b2, -rho) + strike_pv * ndtr(a2)
    if value < -2e-10 * max(1, asset, bond, strike_pv):
        raise ValueError("compound formula produced a negative option value")
    return max(float(value), 0.0)


def compound_price(S, K1, K2, r, sigma, T1, T2, q=0.0, *, kind="call_on_call"):
    """Value an option on a European vanilla option, in currency per underlying.

    At T1, the outer call pays max(V1-K1,0); the outer put pays max(K1-V1,0).
    V1 is the T1 value of an inner call/put with strike K2 and expiry T2.
    Select call_on_call, put_on_call, call_on_put or put_on_put with ``kind``.
    Rates/yield are continuously compounded per year; times are years from now.

    Inputs broadcast; scalars return float, arrays ndarray. Require S,K2>0,
    K1>=0, sigma>=0 and 0<T1<T2, all finite real numbers. Zero volatility and
    zero outer strike use exact limits. For an inner put, K1 at/above its
    discounted strike bound has no finite critical spot but valid prices.
    Invalid or unrepresentable inputs/calculations raise ValueError.
    This is the constant-parameter GBM European model, not American exercise.
    """
    if not isinstance(kind, str) or kind not in _KINDS:
        raise ValueError("unknown compound option kind")
    values = []
    for name, value in zip(
        ("S", "K1", "K2", "r", "sigma", "T1", "T2", "q"),
        (S, K1, K2, r, sigma, T1, T2, q),
        strict=True,
    ):
        if np.iscomplexobj(value):
            raise ValueError(f"{name} must be real")
        try:
            array = np.asarray(value, dtype=float)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{name} must be a representable real number") from exc
        if np.any(~np.isfinite(array)):
            raise ValueError(f"{name} must be finite")
        values.append(array)
    arrays = np.broadcast_arrays(*values)
    s, k1, k2, _rate, vol, start, expiry, _yield = arrays
    if (
        np.any(s <= 0)
        or np.any(k1 < 0)
        or np.any(k2 <= 0)
        or np.any(vol < 0)
        or np.any(start <= 0)
        or np.any(expiry <= start)
    ):
        raise ValueError("require S,K2>0, K1,sigma>=0 and 0<T1<T2")
    result = np.empty(s.shape)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            for index in np.ndindex(s.shape):
                result[index] = _price(*(float(v[index]) for v in arrays), kind)
    except (FloatingPointError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError("compound calculation is outside the representable range") from exc
    if np.any(~np.isfinite(result)):
        raise ValueError("compound calculation is outside the representable range")
    return result.item() if result.ndim == 0 else result
