"""Private Hull Ch3 futures hedges and explicit cash/quantity conventions."""

import numpy as np


def asset_hedge(
    terminal_spot,
    futures_entry,
    futures_exit,
    *,
    units,
    contract_size,
    price_unit=1,
    obligation="sell",
):
    """Equal-unit futures hedge of a spot purchase/sale; net_cash is signed cash.

    Both quote types share underlying units. price_unit converts cents to cash.
    effective_price is receipt per unit for selling, cost per unit for buying.
    Daily settlement interest, fees and rounding to exchange lots are excluded.
    """
    s = np.asarray(terminal_spot, dtype=float)
    f = np.asarray(futures_exit, dtype=float)
    if (
        not np.isfinite(s).all()
        or not np.isfinite(f).all()
        or not np.isfinite([futures_entry, units, contract_size, price_unit]).all()
        or units < 0
        or min(contract_size, price_unit) <= 0
        or obligation not in ("buy", "sell")
    ):
        raise ValueError("finite quotes, valid units/scales and buy/sell obligation required")
    direction = 1 if obligation == "sell" else -1
    per_unit = direction * (futures_entry - f) * price_unit
    spot_cash = direction * units * s * price_unit
    profit = units * per_unit
    return {
        "contracts": units / contract_size,
        "per_unit_profit": per_unit,
        "futures_profit": profit,
        "spot_cash": spot_cash,
        "net_cash": spot_cash + profit,
        "effective_price": (s + futures_entry - f) * price_unit,
    }


def business_hedge_profit(
    base_sales, input_units, baseline_price, terminal_price, *, pass_through, hedge_cash
):
    """Attribute operating profits and separate derivative cash under stated cost transfer.

    Sales change by pass_through times the raw-material price change. This is a
    scenario accounting identity, not an estimated corporate pricing model.
    """
    if (
        not np.isfinite(
            [base_sales, input_units, baseline_price, terminal_price, pass_through, hedge_cash]
        ).all()
        or input_units < 0
    ):
        raise ValueError("finite scenario inputs and nonnegative input units required")
    sales = base_sales + pass_through * input_units * (terminal_price - baseline_price)
    operating = sales - input_units * terminal_price
    return {
        "sales": sales,
        "unhedged_profit": operating,
        "hedge_cash": hedge_cash,
        "hedged_profit": operating + hedge_cash,
    }


def basis_hedge(
    initial_spot,
    terminal_spot,
    futures_entry,
    futures_exit,
    *,
    units,
    contract_size,
    price_unit=1,
    obligation="sell",
    proxy_spot=None,
):
    """Hull S-F basis with maturity and cross-asset components, in quoted price units.

    Cash/effective_price use price_unit conversion; basis fields retain quote units.
    proxy_spot is the spot of the futures underlying when cross hedging.
    """
    if not np.isfinite(initial_spot):
        raise ValueError("finite initial spot required")
    a = asset_hedge(
        terminal_spot,
        futures_entry,
        futures_exit,
        units=units,
        contract_size=contract_size,
        price_unit=price_unit,
        obligation=obligation,
    )
    s = np.asarray(terminal_spot, dtype=float)
    f = np.asarray(futures_exit, dtype=float)
    proxy = s if proxy_spot is None else np.asarray(proxy_spot, dtype=float)
    if not np.isfinite(proxy).all():
        raise ValueError("finite proxy spot required")
    return dict(
        a,
        initial_basis=initial_spot - futures_entry,
        final_basis=s - f,
        maturity_basis=proxy - f,
        asset_basis=s - proxy,
    )


def minimum_variance_hedge(spot_changes, future_changes, *, exposure_units, contract_units):
    """Sample price-change hedge, with ddof=1 deviations and unrounded contract count.

    ratio is covariance/variance, not correlation. The in-sample effectiveness
    rho squared is an explanatory sample identity, not future hedging performance.
    """
    s = np.asarray(spot_changes, dtype=float)
    f = np.asarray(future_changes, dtype=float)
    if (
        s.ndim != 1
        or s.shape != f.shape
        or len(s) < 2
        or not np.isfinite(s).all()
        or not np.isfinite(f).all()
        or not np.isfinite([exposure_units, contract_units]).all()
        or exposure_units < 0
        or contract_units <= 0
    ):
        raise ValueError("paired samples and valid quantity scales required")
    vf = np.var(f, ddof=1)
    vs = np.var(s, ddof=1)
    if min(vf, vs) <= 0:
        raise ValueError("positive sample variances required")
    covariance = np.cov(s, f, ddof=1)[0, 1]
    ratio = covariance / vf
    rho = covariance / np.sqrt(vf * vs)
    return {
        "sd_spot": np.sqrt(vs),
        "sd_future": np.sqrt(vf),
        "rho": rho,
        "ratio": ratio,
        "contracts": ratio * exposure_units / contract_units,
        "effectiveness": rho**2,
    }


def hedge_contracts(ratio, exposure_value, contract_value, *, growth=1):
    """Value-based futures count, divided by positive cash growth for optional tailing.

    rounded uses nearest integer, with ties to even; contract count sign is retained.
    Rates/cash convention are caller inputs, and growth=1 omits tailing.
    """
    if (
        not np.isfinite([ratio, exposure_value, contract_value, growth]).all()
        or exposure_value < 0
        or min(contract_value, growth) <= 0
    ):
        raise ValueError("valid exposure and positive contract value/growth required")
    count = ratio * exposure_value / (contract_value * growth)
    return {
        "exposure_value": exposure_value,
        "contract_value": contract_value,
        "contracts": count,
        "rounded": np.rint(count),
    }


def beta_contracts(exposure_value, contract_value, beta, *, target=0):
    """Signed short-contract count to move systematic beta to a stated target.

    Positive counts sell futures; negative counts buy. Residual stock risk remains.
    """
    return hedge_contracts(beta - target, exposure_value, contract_value)


def index_hedge_scenarios(
    portfolio_value,
    beta,
    index_entry,
    futures_entry,
    terminal_index,
    terminal_futures,
    *,
    multiplier,
    rate,
    dividend_yield,
    maturity,
    short_contracts=None,
):
    """Hull's deterministic CAPM scenario approximation with simple period returns.

    Market return includes q*T. Full correlation/constant beta is illustrative;
    resulting beta neutrality does not eliminate unsystematic risk in real holdings.
    Dollar outputs retain decimals; source tables may truncate below one dollar.
    """
    index = np.asarray(terminal_index, dtype=float)
    future = np.asarray(terminal_futures, dtype=float)
    if (
        not np.isfinite(
            [
                portfolio_value,
                beta,
                index_entry,
                futures_entry,
                multiplier,
                rate,
                dividend_yield,
                maturity,
            ]
        ).all()
        or not np.isfinite(index).all()
        or not np.isfinite(future).all()
        or min(index_entry, futures_entry, multiplier) <= 0
        or min(portfolio_value, maturity) < 0
    ):
        raise ValueError("finite scenarios and positive index/future/multiplier required")
    value = futures_entry * multiplier
    n = (
        beta_contracts(portfolio_value, value, beta)["contracts"]
        if short_contracts is None
        else short_contracts
    )
    if not np.isfinite(n):
        raise ValueError("finite contract count required")
    market = index / index_entry - 1 + dividend_yield * maturity
    returns = rate * maturity + beta * (market - rate * maturity)
    stock = portfolio_value * (1 + returns)
    profit = n * multiplier * (futures_entry - future)
    return {
        "market_return": market,
        "portfolio_return": returns,
        "portfolio_value": stock,
        "futures_profit": profit,
        "total_value": stock + profit,
        "contract_value": value,
        "short_contracts": n,
    }


def stock_picking_profit(
    shares, stock_entry, stock_exit, futures_entry, futures_exit, *, short_contracts, multiplier
):
    """Separate stock P&L and index hedge P&L, ignoring dividend/funding cash."""
    if (
        not np.isfinite(
            [
                shares,
                stock_entry,
                stock_exit,
                futures_entry,
                futures_exit,
                short_contracts,
                multiplier,
            ]
        ).all()
        or shares < 0
        or multiplier <= 0
    ):
        raise ValueError("finite cashflow inputs and valid quantities required")
    stock = shares * (stock_exit - stock_entry)
    future = short_contracts * multiplier * (futures_entry - futures_exit)
    return {"stock_profit": stock, "futures_profit": future, "total_profit": stock + future}


def stack_roll(entries, exits, *, units, contract_size, initial_spot, terminal_spot):
    """Short successive futures then sell spot; each pair is one closed contract.

    All cash is nominal, without interest, transaction costs or tailing adjustments.
    Price gaps between expiry contracts are not themselves profits of a trade.
    """
    starts = np.asarray(entries, dtype=float)
    ends = np.asarray(exits, dtype=float)
    if (
        starts.ndim != 1
        or starts.shape != ends.shape
        or not len(starts)
        or not np.isfinite(starts).all()
        or not np.isfinite(ends).all()
        or not np.isfinite([units, contract_size, initial_spot, terminal_spot]).all()
        or units < 0
        or contract_size <= 0
    ):
        raise ValueError("paired trade prices and valid quantity scales required")
    gains = starts - ends
    total = float(gains.sum())
    return {
        "contracts": units / contract_size,
        "per_unit_profit": gains,
        "cash_profit": units * gains,
        "total_per_unit": total,
        "spot_decline": initial_spot - terminal_spot,
        "effective_sale_price": terminal_spot + total,
        "net_cash": units * (terminal_spot + total),
    }
