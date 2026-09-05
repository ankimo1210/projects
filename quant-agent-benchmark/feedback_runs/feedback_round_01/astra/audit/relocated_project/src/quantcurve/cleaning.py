"""Auditable deterministic cleaning, independent of fitted curve residuals."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Config


def clean_market_data(frame: pd.DataFrame, valuation_date: str, config=Config()):
    """Return usable rows and an audit row for EVERY input row, in input order.

    No maturity/curve-shape filter is used. Mislabelled rate units require at
    least two same-tenor, same-type, current unique-instrument peers. Ambiguous
    values remain in the fit, where their robust weights are reported.
    """
    day = pd.Timestamp(valuation_date)
    if pd.isna(day):
        raise ValueError("valuation-date must be a valid ISO calendar date")
    day = day.tz_localize("UTC") if day.tz is None else day.tz_convert("UTC")
    day = day.normalize()
    f = frame.reset_index(drop=True).copy()
    if f.empty:
        raise ValueError("market data contains no observations")
    f["row_id"] = np.arange(len(f))
    f["parsed_timestamp"] = pd.to_datetime(f.timestamp, utc=True, errors="coerce")
    reasons = [[] for _ in range(len(f))]
    actions = np.full(len(f), "keep", dtype=object)
    severity = {"keep": 0, "correct": 1, "downweight": 2, "exclude": 3}

    def note(i, action, reason):
        reasons[i].append(reason)
        if severity[action] > severity[actions[i]]:
            actions[i] = action

    for issue in frame.attrs.get("numeric_coercions", []):
        note(issue["row"], "correct", f"numeric coercion: {issue['field']}={issue['original']!r} replaced with missing; field-specific validation follows")

    for c in ("normalized_quote", "normalized_bid", "normalized_ask", "sigma", "reliability", "weight"):
        f[c] = np.nan if c not in ("weight", "reliability") else 0.0
    for i, r in f.iterrows():
        for c in ("obs_id", "instrument_id", "source"):
            if pd.isna(r[c]) or not str(r[c]).strip():
                note(i, "exclude", f"missing {c}")
        if pd.isna(r.parsed_timestamp):
            note(i, "exclude", "missing or invalid timestamp")
        else:
            age = (day - r.parsed_timestamp.normalize()).total_seconds() / 86400
            if age < 0:
                note(i, "exclude", "timestamp after valuation day")
            elif age > config.stale_days:
                note(i, "exclude", f"stale observation: {age:g} calendar days old (limit {config.stale_days:g})")
        typ = r.instrument_type
        expected_quote = {"deposit": "simple_rate", "ois_swap": "par_rate", "bond": "clean_price"}
        if typ not in expected_quote:
            note(i, "exclude", "unsupported instrument_type")
        elif r.quote_type != expected_quote[typ]:
            note(i, "exclude", "quote_type inconsistent with instrument_type")
        if r.currency != "USD" or r.day_count != "ACT/365F":
            note(i, "exclude", "unsupported currency or day_count")
        if not np.isfinite(r.maturity_years) or not 0 < r.maturity_years <= 100:
            note(i, "exclude", "maturity_years must be finite and in (0,100]")
        md = pd.to_datetime(r.maturity_date, errors="coerce", utc=True)
        if pd.isna(md):
            note(i, "exclude", "missing or invalid maturity_date")
        elif np.isfinite(r.maturity_years):
            discrepancy = abs((md.normalize() - day).days - 365 * r.maturity_years)
            if discrepancy > 2:
                note(i, "downweight", "maturity_date discrepancy >2 days; authoritative maturity_years retained")
        if not np.isfinite(r.start_years) or r.start_years != 0:
            note(i, "exclude", "only valuation-date starts (start_years=0) are documented")
        if not np.isfinite(r.settlement_days) or r.settlement_days != 2:
            note(i, "exclude", "settlement_days must equal documented two calendar days")
        freq = r.payment_frequency
        if not np.isfinite(freq) or freq != int(freq) or not 1 <= freq <= 12:
            note(i, "exclude", "payment_frequency must be an integer in [1,12]")
        if typ == "ois_swap" and np.isfinite(r.maturity_years) and freq != (1 if r.maturity_years <= 2 else 2):
            note(i, "exclude", "OIS frequency inconsistent with documented tenor convention")
        if typ == "bond" and (not np.isfinite(r.coupon_rate) or not -0.2 <= r.coupon_rate <= 0.5):
            note(i, "exclude", "bond coupon must be finite annual decimal in [-0.2,0.5]")
        if not np.isfinite(r.liquidity_score):
            note(i, "downweight", "missing liquidity_score; conservative value 0.1 assigned")
            liq = 0.1
        elif not 0 <= r.liquidity_score <= 1:
            note(i, "exclude", "liquidity_score outside [0,1]")
            liq = 0
        else:
            liq = float(r.liquidity_score)
        if liq < 0.25:
            note(i, "downweight", "illiquid: reduced precision, observation retained")
        unit = str(r.quote_unit).upper()
        factors = {"PRICE_POINTS": 1.0} if typ == "bond" else {"PERCENT": 0.01, "DECIMAL": 1.0, "BPS": 0.0001}
        if unit not in factors:
            note(i, "exclude", f"unsupported quote_unit {unit}")
            factor = np.nan
        else:
            factor = factors[unit]
            note(i, "keep", f"normalization: {unit} times {factor:g}")
        q, bid, ask = [float(r[c]) * factor for c in ("quote_value", "bid", "ask")]
        if np.isfinite(bid) and np.isfinite(ask) and bid > ask:
            bid, ask = ask, bid
            note(i, "correct", "inverted bid/ask swapped")
        if not np.isfinite(q):
            if pd.isna(r.quote_value) and np.isfinite(bid) and np.isfinite(ask):
                q = (bid + ask) / 2
                note(i, "correct", "missing quote recovered from two-sided bid/ask midpoint")
            else:
                note(i, "exclude", "no finite quote or recoverable missing midpoint")
        if not (np.isfinite(bid) and np.isfinite(ask)):
            note(i, "downweight", "incomplete bid/ask; conservative uncertainty floor times five")
        elif np.isfinite(q) and (q < bid or q > ask):
            note(i, "downweight", "quote outside bid/ask; retained with quarter reliability")
        f.loc[i, ["normalized_quote", "normalized_bid", "normalized_ask"]] = [q, bid, ask]
        reliability = max(liq, 0.01)
        if any("discrepancy" in s or "outside bid/ask" in s or "incomplete bid/ask" in s for s in reasons[i]):
            reliability *= 0.25
        f.loc[i, "reliability"] = reliability

    # Choose the most recent valid observation per instrument, then liquidity,
    # then obs_id. Never let an invalid newest record displace a valid record.
    eligible = f.loc[actions != "exclude"].sort_values(
        ["parsed_timestamp", "liquidity_score", "obs_id"], ascending=[False, False, True], kind="stable")
    chosen = set(eligible.drop_duplicates("instrument_id").index)
    for i in eligible.index:
        if i not in chosen:
            note(i, "exclude", "duplicate instrument_id; newer or higher-quality deterministic representative retained")
    # Repeated observation identifiers must not be silently accepted either.
    seen = set()
    for i in sorted(chosen):
        oid = f.loc[i, "obs_id"]
        if oid in seen:
            note(i, "exclude", "duplicate obs_id")
        seen.add(oid)

    reference = f.loc[actions != "exclude"].copy()
    for i in reference.index:
        r = f.loc[i]
        if r.instrument_type == "bond" or r.quote_unit != "PERCENT":
            continue
        peers = reference[(reference.instrument_type == r.instrument_type)
                          & np.isclose(reference.maturity_years, r.maturity_years, atol=1e-6, rtol=0)
                          & (reference.instrument_id != r.instrument_id)].normalized_quote
        peers = peers[np.isfinite(peers)]
        if len(peers) < 2:
            continue
        med = float(peers.median())
        mad = float(np.median(abs(peers - med)))
        q = r.normalized_quote
        if abs(med) < 0.0005 or mad > 0.1 * abs(med) or q * med <= 0:
            continue
        for multiplier in (100.0, 0.01):
            if abs(q * multiplier - med) < 0.1 * abs(med) and abs(q - med) > 0.8 * abs(med):
                f.loc[i, ["normalized_quote", "normalized_bid", "normalized_ask"]] *= multiplier
                note(i, "correct", f"inferred mislabelled rate units: all quotes times {multiplier:g}; {len(peers)} same-tenor unique peers, median={med:.8g}")
                break

    # Price-per-one mislabelling: require independent nearby price and rate
    # evidence. This is an explicit, reversible heuristic, never a price floor.
    bonds = f[(actions != "exclude") & (f.instrument_type == "bond")].copy()
    rates = f[(actions != "exclude") & (f.instrument_type != "bond")].copy()
    for i, r in bonds.iterrows():
        peers = bonds[(abs(bonds.maturity_years - r.maturity_years) <= 5)
                      & (bonds.instrument_id != r.instrument_id)]
        peer_prices = peers.normalized_quote
        close_rates = rates.iloc[np.argsort(abs(rates.maturity_years.to_numpy() - r.maturity_years))[:8]]
        if len(peers) < 3 or len(close_rates) < 3:
            continue
        pm = float(peer_prices.median())
        indicative_yield = float(close_rates.normalized_quote.median())
        from .pricing import bond_cashflows
        ts, cf = bond_cashflows(r.maturity_years, int(r.payment_frequency), r.coupon_rate)
        indicative_price = float(cf @ np.exp(-indicative_yield * ts))
        q = r.normalized_quote
        for multiplier in (100.0, 0.01):
            if (q > 0 and pm > 0 and indicative_price > 0
                    and abs(q * multiplier / pm - 1) < 0.25
                    and abs(q * multiplier / indicative_price - 1) < 0.25
                    and abs(q / indicative_price - 1) > 0.8):
                f.loc[i, ["normalized_quote", "normalized_bid", "normalized_ask"]] *= multiplier
                note(i, "correct", f"inferred price-per-face unit mismatch: all quotes times {multiplier:g}; {len(peers)} bonds within 5Y and nearby rate-implied PV agree within 25%")
                break

    for i, r in f.iterrows():
        q, bid, ask = r.normalized_quote, r.normalized_bid, r.normalized_ask
        if np.isfinite(q):
            if r.instrument_type == "deposit" and q * r.maturity_years <= -1:
                note(i, "exclude", "simple deposit implies nonpositive discount factor")
            if r.instrument_type == "bond" and q <= 0:
                note(i, "exclude", "bond price must be positive")
            if r.instrument_type != "bond" and abs(q) > 1:
                note(i, "exclude", "normalized rate exceeds supported absolute 100% range")
        floor = config.price_sigma_floor if r.instrument_type == "bond" else config.rate_sigma_floor
        sigma = max((ask - bid) / 2, floor) if np.isfinite(bid) and np.isfinite(ask) else 5 * floor
        f.loc[i, "sigma"] = sigma
        f.loc[i, "weight"] = r.reliability / sigma**2 if actions[i] != "exclude" else 0.0
    f["action"] = actions
    f["reason"] = ["; ".join(rs) for rs in reasons]
    f["base_weight"] = f.weight
    audit = f.copy()
    usable = f.loc[f.action != "exclude"].sort_values(
        ["maturity_years", "instrument_type", "instrument_id"], kind="stable").reset_index(drop=True)
    if len(usable) < 8 or usable.maturity_years.nunique() < 4:
        raise ValueError("insufficient usable data: require at least 8 instruments and 4 distinct maturities after cleaning")
    return usable, audit
