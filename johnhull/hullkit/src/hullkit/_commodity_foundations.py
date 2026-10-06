"""Private Ch35 commodity futures, calibrated trees and conditional model components."""

import math

import numpy as np
from scipy.integrate import quad

from ._calibrated_rate_tree import _geometry
from ._rate_tree import discounted_rollback


def futures_growth(start_future, end_future, years):
    """Q log-growth per interval and annual continuous drift from two positive futures."""
    if min(start_future, end_future, years) <= 0:
        raise ValueError("positive futures and elapsed years required")
    change = math.log(end_future / start_future)
    return {"log_growth": change, "annual_growth": change / years}


def commodity_investment(
    initial, expense_times, expenses, sale_time, expected_quantity, future, rate
):
    """DCF using Q futures and independent, zero-systematic-risk expected sale quantity.

    Prices and quantities must use matching units. This does not price correlated
    volume-price risk; the quantity assumptions are Hull Example35.2's conditions.
    """
    from .rates import bond_price

    t = np.asarray(expense_times, dtype=float)
    cost = np.asarray(expenses, dtype=float)
    if (
        t.ndim != 1
        or t.shape != cost.shape
        or np.any(t < 0)
        or np.any(t > sale_time)
        or min(initial, sale_time, expected_quantity, future) < 0
    ):
        raise ValueError("matching costs/dates and nonnegative investment inputs required")
    return float(
        -initial + bond_price(np.r_[t, sale_time], np.r_[-cost, expected_quantity * future], rate)
    )


def seasonal_futures(quote_times, futures, quote_factors, times, factors):
    """Deseasonalize positive quotes, interpolate linearly, then restore supplied factors.

    Historical seasonality estimation and its information cutoff are caller inputs.
    This interpolates the nonseasonal price level, not its logarithm.
    """
    x = np.asarray(quote_times, dtype=float)
    F = np.asarray(futures, dtype=float)
    season = np.asarray(quote_factors, dtype=float)
    t = np.asarray(times, dtype=float)
    s = np.asarray(factors, dtype=float)
    if (
        x.ndim != 1
        or len(x) < 2
        or x.shape != F.shape
        or x.shape != season.shape
        or t.shape != s.shape
        or np.any(np.diff(x) <= 0)
        or np.any(F <= 0)
        or np.any(season <= 0)
        or np.any(s <= 0)
        or np.any(t < x[0])
        or np.any(t > x[-1])
    ):
        raise ValueError("ordered paired quotes, positive factors and in-range targets required")
    neutral = F / season
    interpolated = np.interp(t, x, neutral)
    return {"deseasonalized": neutral, "interpolated": interpolated, "futures": interpolated * s}


def build_commodity_tree(spot, futures, mean_reversion, volatility, *, dt=1):
    """Uniform-step Euler log-OU tree shifted to E_Q[S_i]=supplied futures.

    Ch32 geometry is shared; calibration uses ordinary reach probabilities with
    no discounting. Deterministic interest rates are required when a futures quote
    is interpreted as Q expected spot. Log prices exclude zero/negative spot.
    """
    F = np.asarray(futures, dtype=float)
    if (
        F.ndim != 1
        or len(F) < 1
        or not np.isfinite(F).all()
        or np.any(F <= 0)
        or not np.isfinite([spot, mean_reversion, volatility, dt]).all()
        or spot <= 0
        or mean_reversion < 0
        or volatility < 0
        or dt <= 0
        or mean_reversion * dt >= 1
    ):
        raise ValueError("positive futures/spot/step and valid Euler coefficients required")
    levels = [
        {
            "labels": np.array([0]),
            "x": np.array([0.0]),
            "alpha": math.log(spot),
            "spot": np.array([spot]),
            "reach_probabilities": np.array([1.0]),
        }
    ]
    spacing = 0.0
    for future in F:
        row = levels[-1]
        labels, spacing, children, p, _, _ = _geometry(
            row["labels"], spacing, mean_reversion, volatility, dt, "textbook", len(F)
        )
        reach = np.zeros(len(labels))
        np.add.at(reach, children.ravel(), (row["reach_probabilities"][:, None] * p).ravel())
        x = labels * spacing
        alpha = math.log(future) - math.log(reach @ np.exp(x))
        row.update(successors=children, probabilities=p)
        levels.append(
            {
                "labels": labels,
                "x": x,
                "alpha": alpha,
                "spot": np.exp(x + alpha),
                "reach_probabilities": reach,
            }
        )
    return {"levels": levels, "dt": dt, "times": np.arange(len(F) + 1) * dt, "spacing": spacing}


def commodity_option(tree, strike, rate, *, kind="put", american=True):
    """Spot option values and exercise nodes on a supplied commodity tree with constant r."""
    if not np.isfinite([strike, rate]).all() or strike < 0 or kind not in ["put", "call"]:
        raise ValueError("nonnegative strike, finite rate and call/put kind required")
    levels = tree["levels"]
    dt = tree["dt"]
    payoff = [
        np.maximum((strike - layer["spot"]) if kind == "put" else (layer["spot"] - strike), 0)
        for layer in levels
    ]
    values = discounted_rollback(
        [np.full(len(layer["spot"]), rate) for layer in levels[:-1]],
        [layer["successors"] for layer in levels[:-1]],
        [layer["probabilities"] for layer in levels[:-1]],
        np.full(len(levels) - 1, dt),
        payoff[-1],
        exercise_values=payoff[:-1] if american else None,
    )
    exercise = []
    for i, layer in enumerate(levels[:-1]):
        continuation = math.exp(-rate * dt) * np.sum(
            layer["probabilities"] * values[i + 1][layer["successors"]], axis=1
        )
        exercise.append(
            (payoff[i] > 0) & (payoff[i] >= continuation)
            if american
            else np.zeros(len(payoff[i]), dtype=bool)
        )
    exercise.append(payoff[-1] > 0)
    return {
        "value": float(values[0][0]),
        "values": values,
        "exercise": exercise,
        "intrinsic": payoff,
    }


def commodity_terminal_law(future, mean_reversion, volatility, maturity):
    """Continuous log-OU Gaussian endpoint calibrated to a positive terminal future."""
    from ._short_rate_models import mean_reversion_loading

    if min(future, mean_reversion, volatility, maturity) < 0 or future == 0:
        raise ValueError("positive future and nonnegative model coefficients/time required")
    variance = volatility**2 * mean_reversion_loading(2 * mean_reversion, maturity)
    return {"mean_log": math.log(future) - variance / 2, "variance": variance}


def log_ou_jump_growth(mean_reversion, maturity, intensity, log_jumps, probabilities):
    """Log expected jump multiplier for finite-size independent compound-Poisson log-OU.

    Reversion attenuates a jump of age u by exp(-a*u). Divide an observed future
    by exp(result) before calibrating its independent no-jump component; this is
    not a jump-branch tree or a fit of jump parameters absent from the textbook.
    """
    j = np.asarray(log_jumps, dtype=float)
    p = np.asarray(probabilities, dtype=float)
    if (
        j.ndim != 1
        or j.shape != p.shape
        or len(j) == 0
        or not np.isfinite(j).all()
        or not np.isfinite(p).all()
        or np.any(p < 0)
        or not np.isclose(p.sum(), 1)
        or min(mean_reversion, maturity, intensity) < 0
    ):
        raise ValueError("finite jump distribution and nonnegative a/time/intensity required")
    return float(
        intensity
        * quad(
            lambda age: p @ np.expm1(j * math.exp(-mean_reversion * age)), 0, maturity, epsabs=1e-12
        )[0]
    )


def convenience_yield_coefficients(
    yield_state, rate, kappa, level, spot_vol, yield_vol, correlation
):
    """Gibson-Schwartz drift/covariance for (log S,y) under constant supplied Q inputs."""
    if min(kappa, spot_vol, yield_vol) < 0 or abs(correlation) > 1:
        raise ValueError("nonnegative speeds/volatilities and correlation in [-1,1] required")
    covariance = np.array(
        [
            [spot_vol**2, correlation * spot_vol * yield_vol],
            [correlation * spot_vol * yield_vol, yield_vol**2],
        ]
    )
    return {
        "drift": np.array([rate - yield_state - spot_vol**2 / 2, kappa * (level - yield_state)]),
        "covariance": covariance,
    }


def stochastic_variance_coefficients(log_spot, variance, a, b, c, d, e, correlation):
    """Eydeland-Geman drift/covariance for (log S,V), including the Ito -V/2 term.

    Caller-supplied nonnegative variance is a state, not an unconstrained Euler
    update. This computes the source SDE coefficients, not a full positivity-
    preserving variance simulator or a calibration from unspecified data.
    """
    if min(variance, a, c, d, e) < 0 or abs(correlation) > 1:
        raise ValueError(
            "nonnegative state/speeds/variance coefficients and valid correlation required"
        )
    covariance = variance * np.array([[1, correlation * e], [correlation * e, e * e]])
    return {
        "drift": np.array([a * (b - log_spot) - variance / 2, c * (d - variance)]),
        "covariance": covariance,
    }


def degree_days_from_extremes(highs, lows, *, base=65):
    """Daily mean and period HDD/CDD; default temperatures/base are Fahrenheit.

    Sum over the last (day) axis using the existing weather index kernel. Celsius
    requires converting the base and cash tick together, not using 18C as 65F.
    """
    from .weather import degree_day_index

    high = np.atleast_1d(np.asarray(highs, dtype=float))
    low = np.atleast_1d(np.asarray(lows, dtype=float))
    if high.shape != low.shape or np.any(high < low) or not np.isfinite(base):
        raise ValueError("matching high/low observations with high>=low required")
    average = (high + low) / 2
    return {
        "average": average,
        "hdd": degree_day_index(average, base=base, kind="hdd"),
        "cdd": degree_day_index(average, base=base, kind="cdd"),
    }


def index_call_cash(index, strike, tick, *, cap=None, side="long", premium=0):
    """Cumulative-index call cash and same-unit premium net; a cap makes a call spread."""
    observed = np.asarray(index, dtype=float)
    if (
        not np.isfinite(observed).all()
        or np.any(observed < 0)
        or min(strike, premium) < 0
        or tick <= 0
        or side not in ["long", "short"]
        or (cap is not None and cap < 0)
    ):
        raise ValueError(
            "nonnegative index/strike/cap/premium, positive tick and valid side required"
        )
    payoff = tick * np.maximum(observed - strike, 0)
    if cap is not None:
        payoff = np.minimum(payoff, cap)
    sign = 1 if side == "long" else -1
    return {
        "gross": sign * payoff,
        "net": sign * (payoff - premium),
        "upper_strike": None if cap is None else strike + cap / tick,
    }


def proportional_reinsurance(losses, ceded_share):
    """Gross indemnity/retained losses under a stated proportional cession; no premium."""
    loss = np.asarray(losses, dtype=float)
    if np.any(loss < 0) or not np.isfinite(loss).all() or not 0 <= ceded_share <= 1:
        raise ValueError("nonnegative losses and cession in [0,1] required")
    return {"ceded_loss": loss * ceded_share, "retained_loss": loss * (1 - ceded_share)}


def reinsurance_layer(losses, attachment, width, *, premium=0):
    """Protection buyer's positive layer indemnity and writer's opposite net cash.

    Hull's prose about the reinsurer holding a long spread conflicts with its
    writer role. The long lower/short upper call pays the protection buyer.
    """
    loss = np.asarray(losses, dtype=float)
    if np.any(loss < 0) or not np.isfinite(loss).all() or min(attachment, width, premium) < 0:
        raise ValueError("nonnegative loss/layer/premium inputs required")
    paid = np.minimum(np.maximum(loss - attachment, 0), width)
    return {
        "indemnity": paid,
        "retained_loss": loss - paid,
        "buyer_net": paid - premium,
        "writer_net": premium - paid,
    }


def cat_bond_principal(principal, trigger_loss, attachment):
    """Principal split for a supplied loss-index layer whose width equals principal.

    trigger_loss follows the term sheet; it need not be the insurer's actual loss.
    Coupons/other trigger rules are separate contractual inputs, not guessed here.
    """
    paid = reinsurance_layer(trigger_loss, attachment, principal)["indemnity"]
    return {"released_principal": paid, "remaining_principal": principal - paid}


def lognormal_weather_call(mean, log_sd, strike, tick, rate, maturity, *, cap=None):
    """Discounted expectation for a nontraded lognormal cumulative weather index.

    Hull assumes zero priced systematic risk. log_sd is the SD of log(period
    index), not an annual volatility. Payment maturity only discounts the supplied
    index distribution. These assumptions do not establish a unique market price.
    """
    from scipy.special import ndtr

    if (
        not np.isfinite([mean, log_sd, strike, tick, rate, maturity]).all()
        or min(mean, log_sd, strike, maturity) < 0
        or tick <= 0
        or (cap is not None and (not np.isfinite(cap) or cap < 0))
    ):
        raise ValueError("nonnegative index/distribution/strike/time and positive tick required")

    def expected_call(K):
        """Call expectation under this period's supplied mean/log-SD."""
        if mean == 0 or log_sd == 0:
            return max(mean - K, 0), None, None
        if K == 0:
            return mean, None, None
        d1 = math.log(mean / K) / log_sd + log_sd / 2
        d2 = d1 - log_sd
        return mean * ndtr(d1) - K * ndtr(d2), d1, d2

    expected, d1, d2 = expected_call(strike)
    if cap is not None:
        expected -= expected_call(strike + cap / tick)[0]
    cash = tick * expected
    return {
        "expected_payoff": float(cash),
        "value": float(cash * math.exp(-rate * maturity)),
        "d1": d1,
        "d2": d2,
    }


def joint_energy_weather_hedge(profits, energy_index, weather_index, *, ticks=(1, 1)):
    """Fit Y=a+bP+cT on a supplied training sample; signed contracts are (-b/tickP,-c/tickT).

    Rank deficiency makes the individual positions unidentified and is rejected.
    Fitted historical coefficients are P regression exposures, not Q model drift.
    """
    y = np.asarray(profits, dtype=float)
    P = np.asarray(energy_index, dtype=float)
    T = np.asarray(weather_index, dtype=float)
    tick = np.asarray(ticks, dtype=float)
    if (
        y.ndim != 1
        or y.shape != P.shape
        or y.shape != T.shape
        or len(y) < 3
        or not np.isfinite(np.r_[y, P, T]).all()
        or tick.shape != (2,)
        or np.any(tick <= 0)
    ):
        raise ValueError("matching finite observations and two positive contract ticks required")
    X = np.column_stack([np.ones(len(y)), P, T])
    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    if rank < 3:
        raise ValueError("full regression rank required for unique hedge positions")
    residual = y - X @ beta
    return {
        "intercept": float(beta[0]),
        "coefficients": beta[1:],
        "positions": -beta[1:] / tick,
        "ticks": tick,
        "training_residual": residual,
    }


def energy_weather_hedge_cash(
    model, profits, energy_index, weather_index, *, energy_entry, weather_entry
):
    """Realized profit plus frozen positions' forward cash on a separate evaluation sample."""
    y = np.asarray(profits, dtype=float)
    P = np.asarray(energy_index, dtype=float)
    T = np.asarray(weather_index, dtype=float)
    if y.shape != P.shape or y.shape != T.shape:
        raise ValueError("matching evaluation cash/index shapes required")
    changes = np.stack([P - energy_entry, T - weather_entry], axis=-1)
    return y + changes @ (model["positions"] * model["ticks"])
