"""Private §28.7 exchange option viewed in the given total-return numeraire.

U is given, V is received. Continuous income q is reinvested in the
numeraire; its ex-income spot alone is not the numeraire. Years and annual
relative volatility are explicit. A common stochastic rate integral cancels
from the discounted exchange payoff path by path.
"""

import numpy as np

from ._forward_black import forward_black_price


def _inputs(*values):
    arrays = [np.asarray(x, dtype=float) for x in values]
    if any(not np.all(np.isfinite(x)) for x in arrays):
        raise ValueError("finite exchange inputs required")
    return arrays


def _result(x):
    if not np.all(np.isfinite(x)):
        raise ValueError("exchange result is not representable")
    return float(x) if np.ndim(x) == 0 else x


def exchange_ratio_statistics(
    observed_ratio,
    volatility_given,
    volatility_received,
    correlation,
    horizon,
    income_given=0.0,
    income_received=0.0,
):
    """Relative drifts and conditional means of V/U under Q and given U.

    The U measure uses reinvested income. Its ratio drift is q_U-q_V; the Q
    drift also contains sigma_U^2-rho*sigma_U*sigma_V. This is a finite
    constant-loading GBM experiment, so exponential moments exist.
    """
    ratio, su, sv, rho, t, qu, qv = _inputs(
        observed_ratio,
        volatility_given,
        volatility_received,
        correlation,
        horizon,
        income_given,
        income_received,
    )
    if (
        np.any(ratio <= 0)
        or np.any(su < 0)
        or np.any(sv < 0)
        or np.any(abs(rho) > 1)
        or np.any(t < 0)
    ):
        raise ValueError("positive ratio, nonnegative vols/time and valid correlation required")
    ratio, su, sv, rho, t, qu, qv = np.broadcast_arrays(ratio, su, sv, rho, t, qu, qv)
    with np.errstate(over="raise", invalid="raise"):
        variance = (sv - su) ** 2 + 2 * (1 - rho) * su * sv
        drift = qu - qv
        qdrift = drift + su * su - rho * su * sv
        return {
            name: _result(value)
            for name, value in dict(
                spread_variance=variance,
                relative_volatility=np.sqrt(variance),
                relative_drift_given=drift,
                relative_drift_Q=qdrift,
                mean_given=ratio * np.exp(drift * t),
                mean_Q=ratio * np.exp(qdrift * t),
            ).items()
        }


def exchange_measure_price(
    given,
    received,
    volatility_given,
    volatility_received,
    correlation,
    horizon,
    income_given=0.0,
    income_received=0.0,
):
    """Price max(V_T-U_T,0) by a strike-one ratio call, Hull 28.30–28.32."""
    u, v, t, qu, qv = _inputs(given, received, horizon, income_given, income_received)
    if np.any(u <= 0) or np.any(v <= 0) or np.any(t < 0):
        raise ValueError("positive assets and nonnegative horizon required")
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        row = exchange_ratio_statistics(
            v / u, volatility_given, volatility_received, correlation, t, qu, qv
        )
        return forward_black_price(
            u * np.exp(-qu * t), row["mean_given"], 1.0, row["relative_volatility"], t
        )


def exchange_numeraire_density(
    given_terminal, given_initial, rate_integral, horizon, income_given=0.0
):
    """Raw dQ_U/dQ = exp(q_U*T-J)*U_T/U_0, without self normalization."""
    ut, u0, j, t, q = _inputs(given_terminal, given_initial, rate_integral, horizon, income_given)
    if np.any(ut <= 0) or np.any(u0 <= 0) or np.any(t < 0):
        raise ValueError("positive given assets and nonnegative horizon required")
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        return _result(np.exp(q * t - j) * ut / u0)
