"""Private Black forward pricing and an exact Gaussian §28.6 experiment.

Black assumes a lognormal terminal forward under its payment measure. The
synthetic Ho-Lee rate/stock example has deterministic diffusion loadings, so
that assumption holds with the integrated forward variance. It is separate
from the flat initial-curve Hull-White experiment in §28.4. All time inputs
are years; rate is year^-1 and both volatilities are year^-1/2.
"""

import numpy as np
from scipy.special import erf, log_ndtr


def _has_boolean(value):
    if isinstance(value, (bool, np.bool_)):
        return True
    if isinstance(value, (list, tuple)):
        return any(_has_boolean(item) for item in value)
    return isinstance(value, np.ndarray) and value.dtype.kind == "b"


def _real(value, name):
    try:
        if _has_boolean(value):
            raise ValueError(f"{name} must not contain booleans")
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or not np.all(np.isfinite(raw)):
            raise ValueError(f"{name} requires finite real numbers with explicit years")
        result = raw.astype(float)
        if not np.all(np.isfinite(result)):
            raise ValueError(f"{name} is not representable")
        return result
    except (TypeError, OverflowError, FloatingPointError) as exc:
        raise ValueError(f"{name} requires representable real numbers") from exc


def _output(value):
    if not np.all(np.isfinite(value)):
        raise ValueError("result is not representable")
    return float(value) if value.ndim == 0 else value


def forward_black_price(discount, forward, strike, volatility, horizon, kind="call"):
    """Return DF times a same-maturity lognormal forward call or put.

    DF, forward, strike > 0; volatility, horizon >= 0. Negative rates may
    give DF > 1. A market forward is provided, including consumption assets.
    No spot cost-of-carry formula is imposed. Scalars return floats; leading
    batch dimensions broadcast after validation, including empty batches.
    Zero volatility/time returns discounted intrinsic value. Exact ATM uses
    erf to retain tiny time value; the OTM leg is evaluated in log space.
    Unrepresentably small tails may underflow to zero. Whole-float-domain
    relative precision is not a contract of this teaching function.
    """
    if not isinstance(kind, str) or kind not in ("call", "put"):
        raise ValueError("kind must be call or put")
    p, f, k, sigma, t = (
        _real(value, name)
        for value, name in zip(
            (discount, forward, strike, volatility, horizon),
            ("discount", "forward", "strike", "volatility", "horizon"),
            strict=True,
        )
    )
    if any(np.any(x <= 0) for x in (p, f, k)) or np.any(sigma < 0) or np.any(t < 0):
        raise ValueError("positive DF/forward/strike and nonnegative volatility/time required")
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            p, f, k, sigma, t = np.broadcast_arrays(p, f, k, sigma, t)
            width = sigma * np.sqrt(t)
            low, high = np.minimum(f, k), np.maximum(f, k)
            otm = np.zeros_like(width)
            live = width > 0
            atm = live & (f == k)
            otm[atm] = f[atm] * erf(width[atm] / (2 * np.sqrt(2.0)))
            tail = live & ~atm
            w = width[tail]
            loglow, loghigh = np.log(low[tail]), np.log(high[tail])
            d1 = (loglow - loghigh) / w + 0.5 * w
            d2 = d1 - w
            loga = loglow + log_ndtr(d1)
            logb = loghigh + log_ndtr(d2)
            represented = np.isfinite(loga)
            small = np.zeros_like(w)
            small[represented] = np.exp(loga[represented]) * (
                -np.expm1(np.minimum(logb[represented] - loga[represented], 0.0))
            )
            otm[tail] = small
            intrinsic = np.maximum(f - k if kind == "call" else k - f, 0.0)
            return _output(p * (intrinsic + otm))
    except (FloatingPointError, ValueError) as exc:
        raise ValueError("Black inputs cannot be broadcast or result represented") from exc


def gaussian_forward_statistics(
    spot, rate, rate_volatility, stock_volatility, correlation, horizon
):
    """Exact moments of J=integral(r dt), Y=log(S_T) in a Ho-Lee Q model.

    dr=eta dW_r, dS/S=r dt+sigma dW_s, corr(W_r,W_s)=rho. Girsanov's
    T-forward tilt shifts the log mean by -cov(J,Y), leaving variance fixed.
    F=S0/DF, whereas futures=E_Q S_T; their difference is generally nonzero.
    At T=0, forward_sigma is its continuous sigma limit. No guarantee for
    a general state-dependent diffusion or a differently fitted rate model
    is inferred. Scalar/broadcast and strict input rules match Black above.
    """
    s, r, eta, sigma, rho, t = (
        _real(value, name)
        for value, name in zip(
            (spot, rate, rate_volatility, stock_volatility, correlation, horizon),
            ("spot", "rate", "rate volatility", "stock volatility", "correlation", "horizon"),
            strict=True,
        )
    )
    if (
        np.any(s <= 0)
        or np.any(eta < 0)
        or np.any(sigma < 0)
        or np.any(np.abs(rho) > 1)
        or np.any(t < 0)
    ):
        raise ValueError("positive spot, nonnegative vols/time and correlation in [-1,1] required")
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            s, r, eta, sigma, rho, t = np.broadcast_arrays(s, r, eta, sigma, rho, t)
            out = {
                "discount": np.ones_like(t),
                "forward": s.copy(),
                "futures": s.copy(),
                "forward_sigma": sigma.copy(),
                "terminal_variance": np.zeros_like(t),
                "mean_integral": np.zeros_like(t),
                "variance_integral": np.zeros_like(t),
                "mean_log_spot_Q": np.array(np.log(s)),
                "mean_log_spot_T": np.array(np.log(s)),
                "cov_integral_log_spot": np.zeros_like(t),
            }
            live = t > 0
            h, a, b, c = t[live], eta[live], sigma[live], rho[live]
            mj = r[live] * h
            vj = (a * h) ** 2 * h / 3
            cov = vj + c * a * b * h**2 / 2
            # Sum of nonnegative terms, even at singular rho = +/-1.
            vy = h * (b + c * a * h / 2) ** 2 + (a * h) ** 2 * h * (1 / 3 - c**2 / 4)
            my = np.log(s[live]) + mj - b**2 * h / 2
            df = np.exp(-mj + vj / 2)
            out["discount"][live] = df
            out["forward"][live] = s[live] / df
            out["futures"][live] = s[live] * np.exp(mj + vj / 2 + c * a * b * h**2 / 2)
            out["forward_sigma"][live] = np.sqrt(vy / h)
            out["terminal_variance"][live] = vy
            out["mean_integral"][live] = mj
            out["variance_integral"][live] = vj
            out["mean_log_spot_Q"][live] = my
            out["mean_log_spot_T"][live] = my - cov
            out["cov_integral_log_spot"][live] = cov
            if any(np.any(out[name] <= 0) for name in ("discount", "forward", "futures")):
                raise ValueError("positive model prices underflowed")
            return {name: _output(value) for name, value in out.items()}
    except (FloatingPointError, ValueError) as exc:
        raise ValueError("Gaussian inputs cannot be broadcast or results represented") from exc
