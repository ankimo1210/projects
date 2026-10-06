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
