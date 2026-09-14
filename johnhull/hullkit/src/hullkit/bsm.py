"""Black-Scholes-Merton analytic formulas (Hull 11e, Ch.15 / Ch.17).

The continuous yield ``q`` generalizes the formulas:
stock index -> q = dividend yield, currency -> q = foreign risk-free rate,
futures -> q = r (Black-76 with S = futures price).

Known cash dividends (Hull 11e GE §11.7, §15.12) use a dividend schedule
instead: `pv_dividends`, `call_price_cash_dividends`/`put_price_cash_dividends`,
`black_american_call_approx`, the early-exercise conditions and the bounds of
eqs. (11.8)-(11.11).
"""

import numpy as np
from scipy.stats import norm


def _validate_price_inputs(S, K, sigma, T):
    if np.any(~np.isfinite(np.asarray(S, dtype=float))) or np.any(np.asarray(S) <= 0.0):
        raise ValueError("S must contain only finite values > 0")
    if np.any(~np.isfinite(np.asarray(K, dtype=float))) or np.any(np.asarray(K) <= 0.0):
        raise ValueError("K must contain only finite values > 0")
    sigma_array = np.asarray(sigma, dtype=float)
    if np.any(~np.isfinite(sigma_array)) or np.any(sigma_array < 0.0):
        raise ValueError("sigma must be finite and >= 0")
    time_array = np.asarray(T, dtype=float)
    if np.any(~np.isfinite(time_array)) or np.any(time_array < 0.0):
        raise ValueError("T must be finite and >= 0")


def d1(S, K, r, sigma, T, q=0.0):
    """Hull eq. (15.20) numerator term."""
    _validate_price_inputs(S, K, sigma, T)
    if np.any(np.asarray(sigma) == 0.0) or np.any(np.asarray(T) == 0.0):
        raise ValueError("d1 is undefined when sigma or T is zero")
    return (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))


def d2(S, K, r, sigma, T, q=0.0):
    """Hull eq. (15.20): ``d1 - sigma * sqrt(T)``."""
    return d1(S, K, r, sigma, T, q) - sigma * np.sqrt(T)


def _price_mixed_boundaries(S, K, r, sigma, T, q, *, is_call):
    """Price element-wise when `T`/`sigma` mix zero and positive entries.

    Three exclusive regimes: `T == 0` -> intrinsic value; `T > 0, sigma == 0`
    -> discounted deterministic payoff; otherwise the BSM formula. `d1` is
    evaluated only on the diffusive elements, so the zero boundaries never
    reach the undefined `sigma * sqrt(T)` division.

    Reached only when a boundary and a diffusive element coexist. Uniform
    inputs keep the original whole-array expressions in `call_price`/
    `put_price`: `np.exp`/`np.log` can round differently in their SIMD and
    scalar paths, so recomputing a scalar-shaped call through the broadcast
    machinery here would shift results by ~1 ulp -- enough for a downstream
    calibration optimizer to land elsewhere and break artifact reproducibility.
    """
    broadcast = np.broadcast_arrays(*(np.asarray(v, dtype=float) for v in (S, K, r, sigma, T, q)))
    shape = broadcast[0].shape
    s, k, r_b, sigma_b, t, q_b = (np.atleast_1d(a) for a in broadcast)

    out = np.empty(s.shape, dtype=float)
    at_expiry = t == 0.0
    zero_vol = (~at_expiry) & (sigma_b == 0.0)
    diffusive = ~(at_expiry | zero_vol)

    intrinsic = s[at_expiry] - k[at_expiry]
    out[at_expiry] = np.maximum(intrinsic if is_call else -intrinsic, 0.0)

    forward = s[zero_vol] * np.exp(-q_b[zero_vol] * t[zero_vol]) - k[zero_vol] * np.exp(
        -r_b[zero_vol] * t[zero_vol]
    )
    out[zero_vol] = np.maximum(forward if is_call else -forward, 0.0)

    if np.any(diffusive):
        s_d, k_d, r_d, sigma_d, t_d, q_d = (a[diffusive] for a in (s, k, r_b, sigma_b, t, q_b))
        vol_time = sigma_d * np.sqrt(t_d)
        d_1 = (np.log(s_d / k_d) + (r_d - q_d + 0.5 * sigma_d**2) * t_d) / vol_time
        d_2 = d_1 - vol_time
        if is_call:
            out[diffusive] = s_d * np.exp(-q_d * t_d) * norm.cdf(d_1) - k_d * np.exp(
                -r_d * t_d
            ) * norm.cdf(d_2)
        else:
            out[diffusive] = k_d * np.exp(-r_d * t_d) * norm.cdf(-d_2) - s_d * np.exp(
                -q_d * t_d
            ) * norm.cdf(-d_1)

    return out[0] if shape == () else out.reshape(shape)


def _has_mixed_boundaries(sigma, T) -> bool:
    """True when a zero-maturity/zero-vol element coexists with a diffusive one."""
    sigma_array = np.asarray(sigma, dtype=float)
    time_array = np.asarray(T, dtype=float)
    at_boundary = (time_array == 0.0) | (sigma_array == 0.0)
    return bool(np.any(at_boundary) and not np.all(at_boundary))


def call_price(S, K, r, sigma, T, q=0.0):
    """European call price, Hull eq. (15.20) / (17.4).

    Boundaries are handled per element, so `T` and `sigma` vectors may mix
    zero and positive entries: zero maturity gives the intrinsic value and
    zero volatility the discounted deterministic payoff.
    """
    _validate_price_inputs(S, K, sigma, T)
    if np.all(np.asarray(T) == 0.0):
        return np.maximum(np.asarray(S) - K, 0.0)
    if np.all(np.asarray(sigma) == 0.0):
        return np.maximum(np.asarray(S) * np.exp(-q * T) - K * np.exp(-r * T), 0.0)
    if _has_mixed_boundaries(sigma, T):
        return _price_mixed_boundaries(S, K, r, sigma, T, q, is_call=True)
    return S * np.exp(-q * T) * norm.cdf(d1(S, K, r, sigma, T, q)) - K * np.exp(-r * T) * norm.cdf(
        d2(S, K, r, sigma, T, q)
    )


def put_price(S, K, r, sigma, T, q=0.0):
    """European put price, Hull eq. (15.21) / (17.5).

    Same element-wise boundary handling as `call_price`.
    """
    _validate_price_inputs(S, K, sigma, T)
    if np.all(np.asarray(T) == 0.0):
        return np.maximum(K - np.asarray(S), 0.0)
    if np.all(np.asarray(sigma) == 0.0):
        return np.maximum(K * np.exp(-r * T) - np.asarray(S) * np.exp(-q * T), 0.0)
    if _has_mixed_boundaries(sigma, T):
        return _price_mixed_boundaries(S, K, r, sigma, T, q, is_call=False)
    return K * np.exp(-r * T) * norm.cdf(-d2(S, K, r, sigma, T, q)) - S * np.exp(-q * T) * norm.cdf(
        -d1(S, K, r, sigma, T, q)
    )


def call_delta(S, K, r, sigma, T, q=0.0):
    """Analytic call delta e^{-qT} N(d1) (Hull Ch.19; needed for tree comparisons)."""
    return np.exp(-q * T) * norm.cdf(d1(S, K, r, sigma, T, q))


def put_delta(S, K, r, sigma, T, q=0.0):
    """Analytic put delta e^{-qT} (N(d1) - 1)."""
    return np.exp(-q * T) * (norm.cdf(d1(S, K, r, sigma, T, q)) - 1.0)


def gamma(S, K, r, sigma, T, q=0.0):
    """Gamma d2V/dS2 — identical for calls and puts (Hull Ch.19, Table 19.6)."""
    return np.exp(-q * T) * norm.pdf(d1(S, K, r, sigma, T, q)) / (S * sigma * np.sqrt(T))


def vega(S, K, r, sigma, T, q=0.0):
    """Vega dV/dsigma per 1.0 of vol (divide by 100 for per-1%); same for calls/puts."""
    return S * np.exp(-q * T) * norm.pdf(d1(S, K, r, sigma, T, q)) * np.sqrt(T)


def call_theta(S, K, r, sigma, T, q=0.0):
    """Call theta per YEAR (divide by 365 for per-calendar-day), Hull Table 19.6."""
    d_1 = d1(S, K, r, sigma, T, q)
    d_2 = d_1 - sigma * np.sqrt(T)
    return (
        -S * np.exp(-q * T) * norm.pdf(d_1) * sigma / (2.0 * np.sqrt(T))
        - r * K * np.exp(-r * T) * norm.cdf(d_2)
        + q * S * np.exp(-q * T) * norm.cdf(d_1)
    )


def put_theta(S, K, r, sigma, T, q=0.0):
    """Put theta per YEAR, Hull Table 19.6."""
    d_1 = d1(S, K, r, sigma, T, q)
    d_2 = d_1 - sigma * np.sqrt(T)
    return (
        -S * np.exp(-q * T) * norm.pdf(d_1) * sigma / (2.0 * np.sqrt(T))
        + r * K * np.exp(-r * T) * norm.cdf(-d_2)
        - q * S * np.exp(-q * T) * norm.cdf(-d_1)
    )


def call_rho(S, K, r, sigma, T, q=0.0):
    """Call rho dV/dr, Hull Table 19.6."""
    return K * T * np.exp(-r * T) * norm.cdf(d2(S, K, r, sigma, T, q))


def put_rho(S, K, r, sigma, T, q=0.0):
    """Put rho dV/dr (negative), Hull Table 19.6."""
    return -K * T * np.exp(-r * T) * norm.cdf(-d2(S, K, r, sigma, T, q))


def vanna(S, K, r, sigma, T, q=0.0):
    """Vanna = d^2V/(dS dsigma) = dDelta/dsigma (Hull Ch.19, higher-order)."""
    d_1 = d1(S, K, r, sigma, T, q)
    d_2 = d_1 - sigma * np.sqrt(T)
    return -np.exp(-q * T) * norm.pdf(d_1) * d_2 / sigma


def vomma(S, K, r, sigma, T, q=0.0):
    """Vomma (volga) = d^2V/dsigma^2 = vega * d1 d2 / sigma (Hull Ch.19)."""
    d_1 = d1(S, K, r, sigma, T, q)
    d_2 = d_1 - sigma * np.sqrt(T)
    return vega(S, K, r, sigma, T, q) * d_1 * d_2 / sigma


# ---------------------------------------------------------------------------
# Known cash dividends: Hull 11e GE §11.7 pp.262-263 and §15.12 pp.360-363.
#
# Unlike the continuous yield ``q`` above, these functions take a dividend
# schedule (ex-dividend times in years, cash amounts). Following §15.12 p.360,
# a dividend is counted only if its ex-dividend date falls within the option's
# life (``t_i <= T``) and is discounted from its ex-dividend date at ``r``.
# ---------------------------------------------------------------------------


def _validate_finite_scalar(value, name, *, minimum=None, strict=False):
    array = np.asarray(value, dtype=float)
    if array.ndim != 0 or not np.isfinite(array):
        raise ValueError(f"{name} must be a finite scalar")
    if minimum is not None and (array <= minimum if strict else array < minimum):
        raise ValueError(f"{name} must be {'>' if strict else '>='} {minimum:g}")
    return float(array)


def _validate_dividend_schedule(dividend_times, dividend_amounts):
    times = np.asarray(dividend_times, dtype=float)
    amounts = np.asarray(dividend_amounts, dtype=float)
    if times.ndim != 1 or amounts.ndim != 1:
        raise ValueError("dividend_times and dividend_amounts must be 1-D sequences")
    if times.shape != amounts.shape:
        raise ValueError("dividend_times and dividend_amounts must have equal length")
    if np.any(~np.isfinite(times)) or np.any(times < 0.0):
        raise ValueError("dividend_times must contain only finite values >= 0")
    if np.any(np.diff(times) <= 0.0):
        raise ValueError("dividend_times must be strictly increasing (t1 < t2 < ... < tn)")
    if np.any(~np.isfinite(amounts)) or np.any(amounts < 0.0):
        raise ValueError("dividend_amounts must contain only finite values >= 0")
    return times, amounts


def _discounted_sum(times, amounts, r, mask):
    return float(np.sum(amounts[mask] * np.exp(-r * times[mask])))


def _stock_less_pv_dividends(S, pv):
    adjusted = np.asarray(S, dtype=float) - pv
    if np.any(adjusted <= 0.0):
        raise ValueError("S - PV(dividends) must be > 0 (dividends exceed the stock price)")
    return adjusted


def pv_dividends(dividend_times, dividend_amounts, r, T=None):
    """Present value D of known cash dividends, Hull 11e GE §11.7 p.263 / §15.12 p.360.

    ``D = sum_i D_i exp(-r t_i)``, each dividend discounted from its
    ex-dividend time ``t_i`` at the continuously compounded rate ``r``. When
    ``T`` is given only dividends with ``t_i <= T`` (during the option's life)
    count. Example 15.9: 0.5 at 2 and 5 months, r = 9% -> 0.9742.
    """
    times, amounts = _validate_dividend_schedule(dividend_times, dividend_amounts)
    r = _validate_finite_scalar(r, "r")
    if T is None:
        return _discounted_sum(times, amounts, r, np.ones(times.shape, dtype=bool))
    T = _validate_finite_scalar(T, "T", minimum=0.0)
    return _discounted_sum(times, amounts, r, times <= T)


def call_price_cash_dividends(S, K, r, sigma, T, dividend_times, dividend_amounts):
    """European call on a stock with known cash dividends, Hull 11e GE §15.12 pp.360-361.

    Black-Scholes-Merton eq. (15.20) with ``S0`` replaced by ``S0 - D``, where
    ``D = pv_dividends(dividend_times, dividend_amounts, r, T)`` and ``sigma``
    is the volatility of the risky component ``S - D``. ``S``/``K``/``sigma``
    may be arrays; ``r``, ``T`` and the schedule are scalars/1-D sequences.
    With no dividends in the option's life this is exactly `call_price`.
    Raises ValueError if ``S - D <= 0``.
    """
    _validate_price_inputs(S, K, sigma, T)
    D = pv_dividends(dividend_times, dividend_amounts, r, T)
    return call_price(_stock_less_pv_dividends(S, D) if D else S, K, r, sigma, T)


def put_price_cash_dividends(S, K, r, sigma, T, dividend_times, dividend_amounts):
    """European put on a stock with known cash dividends, Hull 11e GE §15.12 p.360.

    Eq. (15.21) with ``S0 - D`` in place of ``S0``; same conventions and
    validation as `call_price_cash_dividends`. Satisfies the dividend
    put-call parity ``c + D + K e^{-rT} = p + S0`` of eq. (11.10).
    """
    _validate_price_inputs(S, K, sigma, T)
    D = pv_dividends(dividend_times, dividend_amounts, r, T)
    return put_price(_stock_less_pv_dividends(S, D) if D else S, K, r, sigma, T)


def black_american_call_approx(S, K, r, sigma, T, dividend_times, dividend_amounts):
    """Black's approximation to an American call with cash dividends, Hull 11e GE §15.12 p.363.

    The greater of two European calls priced as in `call_price_cash_dividends`:
    one maturing at ``T`` (all dividends with ``t_i <= T`` removed) and one
    maturing immediately before the final ex-dividend date ``t_n`` (only the
    dividends with ``t_i < t_n`` removed, because exercise just before
    ``t_n`` captures the cum-dividend price). It is never below the European
    value. It assumes the exercise date is chosen at time zero, and its two
    legs apply ``sigma`` to different risky components, so it is an
    approximation rather than a bound on any single model's American price
    (it can exceed an escrowed-dividend tree, see ``test_dividends.py``).
    Without dividends in the option's life it returns the European call.
    """
    _validate_price_inputs(S, K, sigma, T)
    times, amounts = _validate_dividend_schedule(dividend_times, dividend_amounts)
    T = _validate_finite_scalar(T, "T", minimum=0.0)
    european_at_T = call_price_cash_dividends(S, K, r, sigma, T, times, amounts)
    in_life = times <= T
    if not np.any(in_life):
        return european_at_T
    t_n = float(times[in_life][-1])
    D_before = _discounted_sum(times, amounts, float(r), times < t_n)
    european_at_t_n = call_price(
        _stock_less_pv_dividends(S, D_before) if D_before else S, K, r, sigma, t_n
    )
    return np.maximum(european_at_T, european_at_t_n)


def call_early_exercise_thresholds(K, r, T, dividend_times):
    """Dividend thresholds ``K(1 - e^{-r(t_{i+1} - t_i)})``, Hull 11e GE §15.12 p.362.

    One entry per ex-dividend date ``t_i <= T`` in order, with ``t_{n+1} = T``:
    the last entry is eq. (15.23)/(15.24), the others eq. (15.25). If the
    dividend ``D_i`` does not exceed its threshold it is never optimal to
    exercise an American call immediately before ``t_i``.
    """
    K = _validate_finite_scalar(K, "K", minimum=0.0, strict=True)
    r = _validate_finite_scalar(r, "r")
    T = _validate_finite_scalar(T, "T", minimum=0.0)
    times, _ = _validate_dividend_schedule(dividend_times, np.zeros(np.shape(dividend_times)))
    times = times[times <= T]
    next_times = np.append(times[1:], T)
    return K * (1.0 - np.exp(-r * (next_times - times)))


def call_early_exercise_can_be_optimal(K, r, T, dividend_times, dividend_amounts):
    """Whether early exercise of an American call may be optimal before each dividend.

    Hull 11e GE §15.12 p.362: element ``i`` is ``D_i > K(1 - e^{-r(t_{i+1}-t_i)})``
    (``t_{n+1} = T``), one entry per ex-dividend date ``t_i <= T``. False means
    exercise immediately before ``t_i`` is never optimal (eqs. 15.23, 15.25);
    for the final date True means exercise is optimal for a sufficiently high
    ``S(t_n)`` (eq. 15.24). If every entry is False the American call equals
    the European call (§11.5, §15.12).
    """
    times, amounts = _validate_dividend_schedule(dividend_times, dividend_amounts)
    thresholds = call_early_exercise_thresholds(K, r, T, times)
    return amounts[: thresholds.size] > thresholds


def _validate_bound_inputs(S, K, T, D):
    _validate_price_inputs(S, K, 0.0, T)
    D_array = np.asarray(D, dtype=float)
    if np.any(~np.isfinite(D_array)) or np.any(D_array < 0.0):
        raise ValueError("D (present value of dividends) must be finite and >= 0")


def european_call_lower_bound(S, K, r, T, D=0.0):
    """Lower bound ``max(S0 - D - K e^{-rT}, 0)``, Hull 11e GE §11.7 eq. (11.8) p.263.

    ``D`` is the present value of the dividends during the option's life
    (`pv_dividends`); ``D = 0`` gives eq. (11.4).
    """
    _validate_bound_inputs(S, K, T, D)
    return np.maximum(S - D - K * np.exp(-r * T), 0.0)


def european_put_lower_bound(S, K, r, T, D=0.0):
    """Lower bound ``max(D + K e^{-rT} - S0, 0)``, Hull 11e GE §11.7 eq. (11.9) p.263.

    ``D = 0`` gives eq. (11.5).
    """
    _validate_bound_inputs(S, K, T, D)
    return np.maximum(D + K * np.exp(-r * T) - S, 0.0)


def put_call_parity_residual(c, p, S, K, r, T, D=0.0):
    """Residual ``c + D + K e^{-rT} - p - S0`` of Hull 11e GE §11.7 eq. (11.10) p.263.

    Zero for arbitrage-free European prices on a stock whose dividends have
    present value ``D``; ``D = 0`` gives eq. (11.6).
    """
    _validate_bound_inputs(S, K, T, D)
    return c + D + K * np.exp(-r * T) - p - S


def american_call_put_bounds(S, K, r, T, D=0.0):
    """Bounds ``(S0 - D - K, S0 - K e^{-rT})`` on ``C - P``, Hull 11e GE §11.7 eq. (11.11) p.263.

    American call minus American put on a stock paying dividends with present
    value ``D``: ``S0 - D - K <= C - P <= S0 - K e^{-rT}``. ``D = 0`` gives
    eq. (11.7).
    """
    _validate_bound_inputs(S, K, T, D)
    return S - D - K, S - K * np.exp(-r * T)
