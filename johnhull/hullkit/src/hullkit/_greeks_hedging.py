"""Private Hull GE Ch19: Greek units, hedge cash replay and scenarios."""

import math
import sys

import numpy as np


def sold_option_valuation(
    spot, strike, rate, sigma, maturity, quantity, sale_cash, *, yield_rate=0, kind="call"
):
    """Time-zero European value vs total sale receipt, not guaranteed future P&L."""
    from ._index_currency import carry_option_details

    if (
        not all(math.isfinite(x) for x in (quantity, sale_cash))
        or quantity <= 0
        or sale_cash < 0
        or kind not in ("call", "put")
    ):
        raise ValueError("positive underlying units and nonnegative total sale cash required")
    unit = carry_option_details(spot, strike, rate, yield_rate, sigma, maturity)[kind]
    return {
        "unit_value": unit,
        "theoretical_value": quantity * unit,
        "sale_cash": sale_cash,
        "sale_difference": sale_cash - quantity * unit,
    }


def written_call_terminal(initial, terminal, strike, quantity, sale_cash, *, covered=False):
    """Terminal option payment and unfinanced stock gain, Hull 19.2 examples."""
    if (
        not all(math.isfinite(x) for x in (initial, terminal, strike, quantity, sale_cash))
        or min(initial, quantity) <= 0
        or min(terminal, strike, sale_cash) < 0
    ):
        raise ValueError(
            "positive initial/quantity and nonnegative terminal/strike/receipt required"
        )
    option_cash = quantity * max(terminal - strike, 0)
    stock_gain = quantity * (terminal - initial) if covered else 0
    return {
        "option_cash": option_cash,
        "stock_gain": stock_gain,
        "profit": sale_cash + stock_gain - option_cash,
    }


def _path_matrix(paths):
    values = np.atleast_2d(np.asarray(paths, dtype=float))
    if (
        values.ndim != 2
        or values.shape[1] < 2
        or values.shape[0] == 0
        or np.any(~np.isfinite(values))
        or np.any(values <= 0)
    ):
        raise ValueError("finite positive equity paths with at least one interval required")
    return values


def stop_loss_holdings(paths, strike):
    """Hold one share strictly above K at each pre-expiry grid observation."""
    prices = _path_matrix(paths)
    if not math.isfinite(strike) or strike < 0:
        raise ValueError("nonnegative finite strike required")
    return (prices[:, :-1] > strike).astype(float)


def hedge_cash_replay(paths, times, strike, rate, holdings, *, kind="call", quantity=1):
    """No-dividend hedge cash recurrence on caller-supplied paths and targets.

    Targets may cover pre-expiry times or the full grid. Grid trades are made
    after interest accrues. Close the final shares and pay the written option;
    no_interest_cost excludes both interest and discount as in Tables19.1/4.
    Returned debt_after_trade is before final liquidation/option settlement.
    """
    prices = _path_matrix(paths)
    times = np.asarray(times, dtype=float)
    target = np.atleast_2d(np.asarray(holdings, dtype=float))
    rows, columns = prices.shape
    if (
        times.shape != (columns,)
        or np.any(~np.isfinite(times))
        or times[0] != 0
        or np.any(np.diff(times) <= 0)
    ):
        raise ValueError("increasing grid starting at zero and matching prices required")
    if (
        not all(math.isfinite(x) for x in (strike, rate, quantity))
        or strike < 0
        or quantity <= 0
        or kind not in ("call", "put")
    ):
        raise ValueError("finite rate, nonnegative strike and positive quantity required")
    if target.shape not in ((rows, columns - 1), (rows, columns)) or np.any(~np.isfinite(target)):
        raise ValueError("holdings must match path rows and pre-expiry or full grid")
    if target.shape[1] == columns - 1:
        target = np.column_stack((target, target[:, -1]))
    trades = np.diff(np.column_stack((np.zeros(rows), target)), axis=1)
    trade_cash = quantity * trades * prices
    debt = np.zeros_like(prices)
    interest = np.zeros_like(prices)
    debt[:, 0] = trade_cash[:, 0]
    for i, dt in enumerate(np.diff(times), start=1):
        interest[:, i] = debt[:, i - 1] * math.expm1(rate * dt)
        debt[:, i] = debt[:, i - 1] + interest[:, i] + trade_cash[:, i]
    sign = 1 if kind == "call" else -1
    payoff = quantity * np.maximum(sign * (prices[:, -1] - strike), 0)
    close = -quantity * target[:, -1] * prices[:, -1]
    terminal = debt[:, -1] + close + payoff
    return {
        "trade_cash": trade_cash,
        "interest_cash": interest,
        "debt_after_trade": debt,
        "close_cash": close,
        "option_cash": payoff,
        "terminal_cost": terminal,
        "present_cost": terminal * math.exp(-rate * times[-1]),
        "no_interest_cost": trade_cash.sum(axis=1) + close + payoff,
    }


def delta_stock_hedge(quantities, deltas):
    """Stock units required to neutralize an option book's weighted delta."""
    quantities = np.asarray(quantities, dtype=float)
    deltas = np.asarray(deltas, dtype=float)
    if (
        quantities.ndim != 1
        or quantities.shape != deltas.shape
        or np.any(~np.isfinite(quantities))
        or np.any(~np.isfinite(deltas))
    ):
        raise ValueError("matching finite vectors of quantities and per-unit deltas required")
    return -float(np.dot(quantities, deltas))


def delta_holdings(paths, times, strike, rate, sigma, *, kind="call"):
    """Nondividend European deltas at pre-expiry observations, per written option.

    At zero volatility use the deterministic payoff slope, with half-delta at
    the forward-strike kink as a convention (a two-sided derivative is absent).
    """
    from scipy.special import ndtr

    prices = _path_matrix(paths)
    times = np.asarray(times, dtype=float)
    if (
        times.shape != (prices.shape[1],)
        or np.any(~np.isfinite(times))
        or times[0] != 0
        or np.any(np.diff(times) <= 0)
    ):
        raise ValueError("increasing grid starting at zero and matching prices required")
    if (
        not all(math.isfinite(x) for x in (strike, rate, sigma))
        or min(strike, sigma) < 0
        or kind not in ("call", "put")
    ):
        raise ValueError("finite rate, nonnegative strike/volatility and call/put required")
    remaining = times[-1] - times[:-1]
    if strike == 0:
        delta = np.ones_like(prices[:, :-1])
    elif sigma == 0:
        forward = prices[:, :-1] * np.exp(rate * remaining)
        delta = np.where(forward > strike, 1.0, np.where(forward < strike, 0.0, 0.5))
    else:
        d1 = (np.log(prices[:, :-1] / strike) + (rate + sigma * sigma / 2) * remaining) / (
            sigma * np.sqrt(remaining)
        )
        delta = ndtr(d1)
    return delta if kind == "call" else delta - 1


def theta_units(spot, strike, rate, sigma, maturity, *, kind="call", yield_rate=0):
    """Calendar-time theta per year/calendar day/trading day, T in years."""
    from . import bsm

    if kind not in ("call", "put") or sigma <= 0 or maturity <= 0:
        raise ValueError("call/put and positive diffusive time/volatility required")
    function = bsm.call_theta if kind == "call" else bsm.put_theta
    annual = float(function(spot, strike, rate, sigma, maturity, q=yield_rate))
    return {"annual": annual, "per_calendar_day": annual / 365, "per_trading_day": annual / 252}


def gamma_delta_hedge(portfolio_delta, portfolio_gamma, option_delta, option_gamma):
    """One option position then stock position to neutralize gamma and delta."""
    if (
        not all(
            math.isfinite(x) for x in (portfolio_delta, portfolio_gamma, option_delta, option_gamma)
        )
        or option_gamma == 0
    ):
        raise ValueError("finite Greeks and nonzero option gamma required")
    weight = -portfolio_gamma / option_gamma
    stock = -(portfolio_delta + weight * option_delta)
    return {
        "option_quantity": weight,
        "stock_quantity": stock,
        "delta_residual": portfolio_delta + weight * option_delta + stock,
        "gamma_residual": portfolio_gamma + weight * option_gamma,
    }


def taylor_pnl(
    delta, gamma, theta, spot_change, elapsed, *, vega=0, vol_change=0, vanna=0, vomma=0
):
    """Ch19 appendix spot/parallel-IV expansion with calendar time in years.

    Rate/q are fixed. Vanna's mixed term has no half factor; gamma and
    vomma's square terms do. Time-cross and higher-order terms are omitted.
    """
    if (
        not all(
            math.isfinite(x)
            for x in (delta, gamma, theta, spot_change, elapsed, vega, vol_change, vanna, vomma)
        )
        or elapsed < 0
    ):
        raise ValueError("finite Greeks/shocks and nonnegative elapsed years required")
    terms = {
        "delta": delta * spot_change,
        "gamma": 0.5 * gamma * spot_change**2,
        "theta": theta * elapsed,
        "vega": vega * vol_change,
        "vanna": vanna * spot_change * vol_change,
        "vomma": 0.5 * vomma * vol_change**2,
    }
    return {**terms, "total": sum(terms.values())}


def greek_pde_residual(spot, rate, sigma, value, theta, delta, gamma, *, yield_rate=0):
    """Eq19.4 residual; theta is calendar-time, value includes the whole book."""
    from ._index_currency import carry_pde_residual

    return carry_pde_residual(spot, rate, yield_rate, sigma, value, theta, delta, gamma)


def vega_units(spot, strike, rate, sigma, maturity, *, yield_rate=0):
    """European call/put vega per absolute volatility 1.0 and 0.01 point."""
    from .bsm import vega

    if sigma <= 0 or maturity <= 0:
        raise ValueError("positive diffusive time/volatility required")
    value = float(vega(spot, strike, rate, sigma, maturity, q=yield_rate))
    return {"per_unit_volatility": value, "per_volatility_point": 0.01 * value}


def vega_delta_hedge(
    portfolio_delta, portfolio_gamma, portfolio_vega, option_delta, option_gamma, option_vega
):
    """One option and stock hedge for a parallel IV move; gamma generally remains."""
    if (
        not all(
            math.isfinite(x)
            for x in (
                portfolio_delta,
                portfolio_gamma,
                portfolio_vega,
                option_delta,
                option_gamma,
                option_vega,
            )
        )
        or option_vega == 0
    ):
        raise ValueError("finite Greeks and nonzero option vega required")
    weight = -portfolio_vega / option_vega
    return {
        "option_quantity": weight,
        "stock_quantity": -(portfolio_delta + weight * option_delta),
        "vega_residual": portfolio_vega + weight * option_vega,
        "gamma_after": portfolio_gamma + weight * option_gamma,
    }


def gamma_vega_delta_hedge(
    portfolio_delta, portfolio_gamma, portfolio_vega, option_deltas, option_gammas, option_vegas
):
    """Two traded options for gamma/parallel-vega, then stock for delta."""
    data = np.asarray([option_deltas, option_gammas, option_vegas], dtype=float)
    book = np.asarray([portfolio_delta, portfolio_gamma, portfolio_vega], dtype=float)
    if data.shape != (3, 2) or np.any(~np.isfinite(data)) or np.any(~np.isfinite(book)):
        raise ValueError("two options with finite delta/gamma/vega required")
    try:
        weights = np.linalg.solve(data[1:], -book[1:])
    except np.linalg.LinAlgError as exc:
        raise ValueError("option gamma/vega exposures must be linearly independent") from exc
    residual = book + data @ weights
    stock = -residual[0]
    residual[0] += stock
    return {"option_quantities": weights, "stock_quantity": float(stock), "residuals": residual}


def rho_units(spot, strike, rate, sigma, maturity, *, kind="call", yield_rate=0):
    """Domestic rho at fixed spot/q, per absolute rate 1.0, 0.01 and 1bp."""
    from . import bsm

    if kind not in ("call", "put") or sigma <= 0 or maturity <= 0:
        raise ValueError("call/put and positive diffusive time/volatility required")
    function = bsm.call_rho if kind == "call" else bsm.put_rho
    value = float(function(spot, strike, rate, sigma, maturity, q=yield_rate))
    return {
        "per_unit_rate": value,
        "per_rate_point": 0.01 * value,
        "per_basis_point": 0.0001 * value,
    }


def scenario_extremes(spot_changes, vol_changes, pnl):
    """Read the worst cell; rows are absolute IV shocks, columns spot shocks."""
    dx = np.asarray(spot_changes, dtype=float)
    dv = np.asarray(vol_changes, dtype=float)
    values = np.asarray(pnl, dtype=float)
    if (
        dx.ndim != 1
        or dv.ndim != 1
        or min(dx.size, dv.size) == 0
        or values.shape != (dv.size, dx.size)
        or any(np.any(~np.isfinite(x)) for x in (dx, dv, values))
    ):
        raise ValueError("finite nonempty axes and matching P&L grid required")
    row, column = np.unravel_index(np.argmin(values), values.shape)
    return {
        "worst_pnl": float(values[row, column]),
        "spot_change": float(dx[column]),
        "vol_change": float(dv[row]),
    }


def scenario_reprice(book, spot, rate, spot_changes, vol_changes, *, elapsed=0, yield_rate=0):
    """Mark-to-market change for a synthetic European book, not Table19.5's book.

    Each book item is (underlying quantity, kind, strike, remaining years, IV).
    Spot shocks and parallel IV shocks are absolute, not relative percentages.
    All maturities must cover the horizon; value changes exclude funding,
    hedging and dividends paid during the horizon. Yield q stays fixed.
    """
    from ._index_currency import carry_option_details

    dx = np.asarray(spot_changes, dtype=float)
    dv = np.asarray(vol_changes, dtype=float)
    book = tuple(book)
    if (
        not all(math.isfinite(x) for x in (spot, rate, elapsed, yield_rate))
        or spot <= 0
        or elapsed < 0
        or not book
    ):
        raise ValueError("finite market, positive spot and nonnegative horizon required")
    if (
        dx.ndim != 1
        or dv.ndim != 1
        or min(dx.size, dv.size) == 0
        or np.any(~np.isfinite(dx))
        or np.any(~np.isfinite(dv))
        or np.any(spot + dx <= 0)
    ):
        raise ValueError("finite nonempty shocks with positive resulting spots required")
    for quantity, kind, strike, maturity, sigma in book:
        if (
            not all(math.isfinite(x) for x in (quantity, strike, maturity, sigma))
            or kind not in ("call", "put")
            or min(strike, sigma) < 0
            or (maturity < elapsed and not math.isclose(maturity, elapsed, rel_tol=8*sys.float_info.epsilon, abs_tol=0))
            or np.any(sigma + dv < 0)
        ):
            raise ValueError("finite European book with nonnegative resulting time/IV required")

    def value(current_spot, vol_shock, time_passed):
        return sum(
            quantity
            * carry_option_details(
                current_spot, strike, rate, yield_rate, sigma + vol_shock, max(maturity - time_passed, 0)
            )[kind]
            for quantity, kind, strike, maturity, sigma in book
        )

    initial = value(spot, 0, 0)
    values = np.array([[value(spot + x, v, elapsed) for x in dx] for v in dv])
    pnl = values - initial
    return {
        "initial_value": initial,
        "scenario_values": values,
        "pnl": pnl,
        "worst": scenario_extremes(dx, dv, pnl),
    }


def option_greek_details(spot, strike, rate, sigma, maturity, *, kind="call", yield_rate=0):
    """Table19.6 European Greeks, per unit shock; rho_yield is foreign rho for FX.

    Spot and q are held fixed for rho_domestic; spot and r for rho_yield.
    Theta uses calendar years, vega uses absolute IV 1.0, gamma spot units^2.
    """
    from . import bsm
    from ._index_currency import carry_option_details

    if (
        not all(math.isfinite(x) for x in (spot, strike, rate, sigma, maturity, yield_rate))
        or min(spot, strike, sigma, maturity) <= 0
        or kind not in ("call", "put")
    ):
        raise ValueError("positive spot/strike/diffusive IV/time and finite rates required")
    delta = bsm.call_delta if kind == "call" else bsm.put_delta
    args = (spot, strike, rate, sigma, maturity)
    d = float(delta(*args, q=yield_rate))
    return {
        "value": carry_option_details(spot, strike, rate, yield_rate, sigma, maturity)[kind],
        "delta": d,
        "gamma": float(bsm.gamma(*args, q=yield_rate)),
        "theta": theta_units(*args, kind=kind, yield_rate=yield_rate)["annual"],
        "vega": vega_units(*args, yield_rate=yield_rate)["per_unit_volatility"],
        "rho_domestic": rho_units(*args, kind=kind, yield_rate=yield_rate)["per_unit_rate"],
        "rho_yield": -maturity * spot * d,
        "vanna": float(bsm.vanna(*args, q=yield_rate)),
        "vomma": float(bsm.vomma(*args, q=yield_rate)),
    }


def futures_option_greeks(future, strike, rate, sigma, maturity, *, kind="call"):
    """Black futures Greeks at fixed F; rho moves r and q=r together."""
    result = option_greek_details(future, strike, rate, sigma, maturity, kind=kind, yield_rate=rate)
    result["rho_domestic"] = -maturity * result["value"]
    result.pop("rho_yield")
    return result


def futures_hedge_units(asset_hedge, rate, yield_rate, maturity, *, contract_size=1):
    """Signed desired asset hedge converted using immediate futures price delta.

    The input is the hedge itself (already opposite to portfolio delta).
    Contract counts retain the sign. Rounded counts leave residual exposure.
    Forward delta is the derivative of PV, futures delta of its settled quote.
    """
    if (
        not all(math.isfinite(x) for x in (asset_hedge, rate, yield_rate, maturity, contract_size))
        or maturity < 0
        or contract_size <= 0
    ):
        raise ValueError("finite units/rates, nonnegative time and positive contract size required")
    futures_delta = math.exp((rate - yield_rate) * maturity)
    units = asset_hedge / futures_delta
    contracts = units / contract_size
    return {
        "asset_units": asset_hedge,
        "futures_units": units,
        "contracts": contracts,
        "rounded_contracts": round(contracts),
        "futures_delta": futures_delta,
        "forward_delta": math.exp(-yield_rate * maturity),
    }


def portfolio_insurance_target(value, floor, rate, yield_rate, sigma, maturity):
    """Eq19.8 put-delta sale fraction; original portfolio value is the underlying.

    A target holding is not a guarantee under gaps or discrete rebalancing.
    The put's cost is not removed by creating it synthetically.
    """
    from scipy.special import ndtr

    from .bsm import d1

    if (
        not all(math.isfinite(x) for x in (value, floor, rate, yield_rate, sigma, maturity))
        or min(value, floor, sigma, maturity) <= 0
    ):
        raise ValueError("positive portfolio/floor/diffusive IV/time and finite rates required")
    first = float(d1(value, floor, rate, sigma, maturity, q=yield_rate))
    fraction = math.exp(-yield_rate * maturity) * float(ndtr(-first))
    return {
        "d1": first,
        "put_delta": -fraction,
        "sell_fraction": fraction,
        "sale_value": value * fraction,
        "target_risky_value": value * (1 - fraction),
    }


def insurance_futures_target(
    value, floor, rate, yield_rate, sigma, maturity, index_spot, multiplier, futures_maturity
):
    """Ex19.10 short index futures for a portfolio that mirrors the index (beta=1)."""
    result = portfolio_insurance_target(value, floor, rate, yield_rate, sigma, maturity)
    if not math.isfinite(index_spot) or index_spot <= 0:
        raise ValueError("positive finite index required")
    futures = futures_hedge_units(
        -result["sale_value"] / index_spot,
        rate,
        yield_rate,
        futures_maturity,
        contract_size=multiplier,
    )
    return {
        **result,
        "contracts_to_short": -futures["contracts"],
        "rounded_contracts_to_short": -futures["rounded_contracts"],
    }


def synthetic_put_replay(paths, times, strike, rate, sigma):
    """Nondividend synthetic put cash replay, initially funded with fair premium.

    The bank initially holds put_value - delta*S0. The insured benchmark and
    synthetic strategy both start with S0 + put_value capital; no free floor
    is implied. There are no dividends, transaction costs or intermediate gaps
    observed between the caller's grid points.
    """
    from ._index_currency import carry_option_details

    prices = _path_matrix(paths)
    targets = delta_holdings(prices, times, strike, rate, sigma, kind="put")
    times = np.asarray(times, dtype=float)
    replay = hedge_cash_replay(prices, times, strike, rate, targets, kind="put")
    initial = np.array(
        [carry_option_details(s, strike, rate, 0, sigma, times[-1])["put"] for s in prices[:, 0]]
    )
    payoff = np.maximum(strike - prices[:, -1], 0)
    synthetic = initial * math.exp(rate * times[-1]) - replay["terminal_cost"] + payoff
    return {
        "initial_put_value": initial,
        "synthetic_put_terminal": synthetic,
        "insured_terminal": prices[:, -1] + synthetic,
        "true_put_insured_terminal": prices[:, -1] + payoff,
        "terminal_replication_error": synthetic - payoff,
    }
