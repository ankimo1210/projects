"""Private §28.4 synthetic flat-curve HW experiment, all times in years.

Q uses zero-mean OU x and r=x+phi, phi=zero+eta² B(0,t)²/2.
Joint order is (future x, integral of r, future Wiener increment).
Exact Gaussian moments retain rank two; this is not a market calibration.
Term fixes at T, overnight realizes at U, both pay at U. Annuity uses
OIS discount bonds and deterministic additive projection-rate basis.
"""

import math
from dataclasses import dataclass
from functools import wraps

import numpy as np
from scipy.special import ndtr


def _real(value, name):
    raw = np.asarray(value)
    if raw.ndim != 0 or raw.dtype.kind not in "iuf" or raw.dtype.kind == "b":
        raise ValueError(f"{name} must be a finite real scalar, with years converted explicitly")
    result = float(raw)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _states(value):
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf" or not np.all(np.isfinite(raw)):
        raise ValueError("state must contain finite real numbers, not temporal units")
    return raw.astype(float)


def _finite(value):
    result = np.asarray(value)
    if not np.all(np.isfinite(result)):
        raise ValueError("result is not representable")
    return float(result) if result.ndim == 0 else result


def _exp(value):
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        result = np.exp(value)
    if np.any(result <= 0):
        raise ValueError("positive numeraire or moment underflowed")
    return _finite(result)


def _representable(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                return function(*args, **kwargs)
        except (OverflowError, FloatingPointError, ZeroDivisionError) as exc:
            raise ValueError("result is not representable") from exc

    return wrapped


@dataclass(frozen=True)
class FlatHW:
    """Synthetic flat initial OIS zero curve; a>0, eta>=0, signed zero rate."""

    a: float = 0.2
    eta: float = 0.02
    zero: float = 0.04

    def __post_init__(self):
        for name in ("a", "eta", "zero"):
            object.__setattr__(self, name, _real(getattr(self, name), name))
        if self.a <= 0 or self.eta < 0:
            raise ValueError("positive a and nonnegative eta required")


def _times(t, end):
    t, end = _real(t, "time"), _real(end, "end")
    if t < 0 or end < t:
        raise ValueError("times must satisfy 0<=t<=end")
    return t, end


def _b(h, model):
    return -math.expm1(-model.a * h) / model.a


@_representable
def ou_moments(h, model):
    """VarX, VarI, CovXI, CovXW, CovIW for future OU noise only.

    Small-a*h series evaluate integrated-noise moments without subtracting
    nearly equal exponentials. For eta=0 all rate noise is zero.
    """
    _, h = _times(0, h)
    a, eta = model.a, model.eta
    z = a * h
    b = _b(h, model)
    if z < 0.1:
        # Integral of squared OU-integral kernel and its Wiener covariance.
        e = sum(
            (-z) ** k * (2 ** (k + 2) - 2) / (math.factorial(k + 2) * (k + 3)) for k in range(16)
        )
        d = sum((-z) ** k / math.factorial(k + 2) for k in range(16))
        vi = eta**2 * h**3 * e
        ciw = eta * h**2 * d
    else:
        vi = eta**2 / a**2 * (h - 2 * b - math.expm1(-2 * z) / (2 * a))
        ciw = eta / a * (h - b)
    q = eta**2 * (-math.expm1(-2 * z)) / (2 * a)
    if eta > 0 and h > 0 and (q <= 0 or vi <= 0):
        raise ValueError("positive rate variance is not representable")
    return _finite([q, vi, 0.5 * eta**2 * b * b, eta * b, ciw])


@_representable
def bond(t, maturity, state, model):
    """Conditional OIS P(t,U) for the documented Q OU coordinate."""
    t, maturity = _times(t, maturity)
    x = _states(state)
    q, _, c, _, _ = ou_moments(t, model)
    b = _b(maturity - t, model)
    return _exp(-model.zero * (maturity - t) - b * (x + c) - 0.5 * b * b * q)


@_representable
def joint_moments(t, end, state, model, payment=None):
    """Conditional Gaussian moments; payment U>=end tilts Q by exp(-I-BX).

    payment=None is Q. payment=end is the terminal-bond measure.
    Covariance is measure invariant. Negative rates/states are allowed.
    """
    t, end = _times(t, end)
    x = _real(state, "state")
    h = end - t
    q, vi, c, cxw, ciw = ou_moments(h, model)
    qt, _, ct, _, _ = ou_moments(t, model)
    b = _b(h, model)
    mean = np.array(
        [
            math.exp(-model.a * h) * x,
            model.zero * h + b * (x + ct) + 0.5 * b * b * qt + 0.5 * vi,
            0.0,
        ]
    )
    cov = np.array([[q, c, cxw], [c, vi, ciw], [cxw, ciw, h]])
    if payment is not None:
        _, payment = _times(end, payment)
        mean -= cov @ np.array([_b(payment - end, model), 1.0, 0.0])
    return _finite(mean), _finite(cov)


@_representable
def sample_joint(t, end, state, model, count, seed, payment=None):
    """Sample exact rank-two noise without Cholesky jitter or time stepping."""
    if (
        isinstance(count, (bool, np.bool_))
        or not isinstance(count, (int, np.integer))
        or not 1 <= count <= 2**20
    ):
        raise ValueError("count must be an integer in 1..1048576")
    if (
        isinstance(seed, (bool, np.bool_))
        or not isinstance(seed, (int, np.integer))
        or not 0 <= seed < 2**64
    ):
        raise ValueError("seed must be an integer in 0..2**64-1")
    mean, _cov = joint_moments(t, end, state, model, payment)
    h = float(end) - float(t)
    if h == 0:
        return np.tile(mean, (count, 1))
    _, vi, _, _, ciw = ou_moments(h, model)
    z = np.random.default_rng(seed).standard_normal((count, 2))
    w = math.sqrt(h) * z[:, 0]
    i = ciw / math.sqrt(h) * z[:, 0] + math.sqrt(max(vi - ciw * ciw / h, 0.0)) * z[:, 1]
    x = model.eta * w - model.a * i
    return _finite(np.column_stack([x, i, w]) + mean)


def _call(mean, variance, strike):
    if variance < 0:
        raise ValueError("negative log variance")
    if variance == 0:
        return max(_exp(mean) - strike, 0.0)
    sd = math.sqrt(variance)
    d2 = (mean - math.log(strike)) / sd
    return _finite(_exp(mean + 0.5 * variance) * ndtr(d2 + sd) - strike * ndtr(d2))


@_representable
def stock_statistics(t, end, state, spot, strike, loading, model):
    """Same no-income stock call, Q path discount vs payment-bond measure.

    dS/S=r dt+loading dW shares the rate Wiener source. Signed loading is
    intentional. Q outer deterministic discount is a displayed wrong control.
    """
    spot, strike, loading = _real(spot, "spot"), _real(strike, "strike"), _real(loading, "loading")
    if spot <= 0 or strike <= 0:
        raise ValueError("positive spot and strike required")
    mq, cov = joint_moments(t, end, state, model)
    mt, _ = joint_moments(t, end, state, model, payment=end)
    h = float(end) - float(t)
    linear = np.array([0.0, 1.0, loading])
    offset = math.log(spot) - 0.5 * loading * loading * h
    my = offset + linear @ mq
    vy = _finite(linear @ cov @ linear)
    cyi = linear @ cov[:, 1]
    discount = bond(t, end, state, model)
    price_q = _exp(-mq[1] + 0.5 * cov[1, 1]) * _call(my - cyi, vy, strike)
    return {
        "price_q": _finite(price_q),
        "price_payment": _finite(discount * _call(offset + linear @ mt, vy, strike)),
        "price_wrong_q_outer_discount": _finite(discount * _call(my, vy, strike)),
        "forward": _finite(spot / discount),
        "futures": _exp(my + 0.5 * vy),
        "discount": discount,
        "log_variance": vy,
        "mean_q": float(my),
        "mean_payment": float(offset + linear @ mt),
    }


@_representable
def rate_statistics(t, fixing, payment, state, model):
    """Term fixing T and overnight realizing U, each paid at U=T+delta."""
    t, fixing = _times(t, fixing)
    _, payment = _times(fixing, payment)
    state = _real(state, "state")
    delta = payment - fixing
    if delta <= 0:
        raise ValueError("payment strictly after fixing required")
    mq, cov = joint_moments(t, fixing, state, model)
    mp, _ = joint_moments(t, fixing, state, model, payment=payment)
    mf, _ = joint_moments(t, fixing, state, model, payment=fixing)
    b = _b(delta, model)
    const = -math.log(bond(fixing, payment, 0, model))

    def term(mean):
        return math.expm1(const + b * mean[0] + 0.5 * b * b * cov[0, 0]) / delta

    q, vi, _, _, _ = ou_moments(delta, model)
    del q
    qt, _, ct, _, _ = ou_moments(fixing, model)
    mi = model.zero * delta + b * (mq[0] + ct) + 0.5 * b * b * qt + 0.5 * vi
    variance = b * b * cov[0, 0] + vi
    ci_fix = b * cov[0, 1]
    ci_pay = ci_fix + b * b * cov[0, 0] + vi

    def overnight(tilt):
        return math.expm1(mi - tilt + 0.5 * variance) / delta

    forward = (bond(t, fixing, state, model) / bond(t, payment, state, model) - 1) / delta
    result = {
        "forward": forward,
        "term_q": term(mq),
        "term_payment": term(mp),
        "term_wrong_fix": term(mf),
        "overnight_q": overnight(0),
        "overnight_payment": overnight(ci_pay),
        "overnight_wrong_fix": overnight(ci_fix),
        "fra_pv": delta * bond(t, payment, state, model) * (forward - term(mp)),
        "fixing": fixing,
        "payment": payment,
        "accrual": delta,
    }
    for value in result.values():
        _finite(value)
    return result


def _schedule(expiry, payments, basis):
    payments = np.asarray(payments)
    if (
        payments.ndim != 1
        or not payments.size
        or payments.dtype.kind not in "iuf"
        or not np.all(np.isfinite(payments))
    ):
        raise ValueError("finite nonempty real payment vector required")
    payments = payments.astype(float)
    deltas = np.diff(np.r_[expiry, payments])
    if np.any(deltas <= 0):
        raise ValueError("strictly increasing payments after expiry required")
    spread = np.zeros(len(payments)) if basis is None else _states(basis)
    if spread.shape != payments.shape:
        raise ValueError("one projection-rate basis per payment required")
    return payments, deltas, spread


@_representable
def annuity_values(t, expiry, payments, state, model, basis=None):
    """A(OIS), V(projected coupons), s=V/A, unit notional; negative V valid."""
    t, expiry = _times(t, expiry)
    payments, deltas, spread = _schedule(expiry, payments, basis)
    x = _states(state)
    bonds = np.array([bond(t, u, x, model) for u in payments])
    annuity = np.tensordot(deltas, bonds, axes=1)
    value = bond(t, expiry, x, model) - bonds[-1] + np.tensordot(deltas * spread, bonds, axes=1)
    return _finite(annuity), _finite(value), _finite(value / annuity)


@_representable
def annuity_statistics(t, expiry, payments, state, model, basis=None):
    """Exact conditional annuity measure as payment-Gaussian mixture."""
    t, expiry = _times(t, expiry)
    state = _real(state, "state")
    payments, deltas, spread = _schedule(expiry, payments, basis)
    annuity, value, rate = annuity_values(t, expiry, payments, state, model, spread)
    weights = deltas * np.array([bond(t, u, state, model) for u in payments]) / annuity
    means = np.array([joint_moments(t, expiry, state, model, payment=u)[0][0] for u in payments])
    variance = joint_moments(t, expiry, state, model)[1][0, 0]
    return {
        "annuity": annuity,
        "value": value,
        "rate": rate,
        "weights": weights,
        "component_means": means,
        "state_variance": variance,
        "basis": spread,
    }
