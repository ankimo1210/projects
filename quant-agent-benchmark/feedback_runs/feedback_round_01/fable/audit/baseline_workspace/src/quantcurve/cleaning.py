"""Validation, normalisation, deduplication and the cleaning audit trail.

The pipeline is rule based and deterministic. Every input observation ends up
with exactly one row in the audit table carrying ``action`` in
``{keep, correct, downweight, exclude}``, the normalised quote (percent for
rates, points for bond prices), a weight (filled in after the robust fit) and
a human-readable ``reason`` listing every flag raised.

Stages:

1. schema / type / range / unit / timestamp validation (row level);
2. unit normalisation and scale-defect correction (peer based);
3. missing-quote correction from bid/ask, crossed bid/ask handling;
4. duplicate resolution per ``instrument_id``;
5. cross-sectional outlier screen inside tenor clusters of rate instruments;
6. base quality weights from bid/ask spread and liquidity.

Model-based robust residual treatment happens later (``advanced.py``) and is
merged into the same audit table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from .instruments import INSTRUMENT_TYPES

EXPECTED_QUOTE_TYPE = {"deposit": "simple_rate", "ois_swap": "par_rate", "bond": "clean_price"}
RATE_UNIT_FACTORS_TO_PERCENT = {"PERCENT": 1.0, "PCT": 1.0, "DECIMAL": 100.0, "BASIS_POINTS": 0.01, "BP": 0.01, "BPS": 0.01}
PRICE_UNITS = {"PRICE_POINTS", "POINTS", "PRICE"}
VALID_FREQUENCIES = {1, 2, 4, 12}
ACTION_ORDER = {"keep": 0, "correct": 1, "downweight": 2, "exclude": 3}


@dataclass
class CleaningConfig:
    max_stale_days: int = 0
    rate_plausible_pct: tuple[float, float] = (-10.0, 50.0)
    price_plausible: tuple[float, float] = (10.0, 400.0)
    maturity_max_years: float = 100.0
    crossed_factor: float = 0.5
    outside_bid_ask_factor: float = 0.5
    bad_timestamp_factor: float = 0.5
    illiquid_liquidity: float = 0.3
    illiquid_spread_multiple: float = 5.0
    cluster_rel_gap: float = 0.02
    cluster_abs_gap: float = 0.01
    xs_min_group: int = 3
    xs_sigma_multiple: float = 6.0
    xs_floor_pct: float = 0.005  # 0.5bp robust-scale floor
    xs_min_dev_pct: float = 0.03  # never flag deviations below 3bp
    xs_max_passes: int = 3
    spread_floor_pct: float = 0.005  # 0.5bp half-spread floor for weights
    bond_spread_floor_points: float = 0.02


@dataclass
class ObservationState:
    idx: int
    flags: list[str] = field(default_factory=list)
    action: str = "keep"
    factor: float = 1.0

    def flag(self, text: str, action: str | None = None, factor: float | None = None) -> None:
        self.flags.append(text)
        if action is not None and ACTION_ORDER[action] > ACTION_ORDER[self.action]:
            self.action = action
        if factor is not None:
            self.factor *= factor

    def exclude(self, text: str) -> None:
        self.flag(text, action="exclude")


@dataclass
class CleaningResult:
    audit: pd.DataFrame
    instruments: pd.DataFrame
    summary: dict


def _tenor_clusters(maturities: np.ndarray, rel_gap: float, abs_gap: float) -> np.ndarray:
    """Single-linkage clusters of maturities; ids are ordered by maturity."""
    order = np.argsort(maturities, kind="stable")
    ids = np.zeros(len(maturities), dtype=int)
    current = 0
    last = None
    for pos in order:
        m = maturities[pos]
        if last is not None and (m - last) > max(rel_gap * m, abs_gap):
            current += 1
        ids[pos] = current
        last = m
    return ids


def _fmt_bp(x: float) -> str:
    return f"{x * 100:.1f}bp"


def clean_market_data(frame: pd.DataFrame, valuation_date: date, config: CleaningConfig | None = None) -> CleaningResult:
    cfg = config or CleaningConfig()
    df = frame.reset_index(drop=True).copy()
    n = len(df)
    states = [ObservationState(i) for i in range(n)]
    val_date = np.datetime64(valuation_date)

    # ---- identifiers -----------------------------------------------------
    obs_ids = df["obs_id"].fillna("").astype(str)
    for i in range(n):
        if obs_ids[i] == "" or obs_ids[i].lower() in ("nan", "<na>"):
            obs_ids[i] = f"ROW{i + 1:04d}"
            states[i].flag("obs_id missing; synthetic id assigned")
    df["obs_id"] = obs_ids.values
    dup_obs = df["obs_id"].duplicated(keep="first")
    for i in np.flatnonzero(dup_obs.values):
        states[i].exclude("duplicate obs_id (exact repeat of an earlier row)")
    inst_ids = df["instrument_id"].fillna("").astype(str)
    for i in range(n):
        if inst_ids[i] == "" or inst_ids[i].lower() in ("nan", "<na>"):
            inst_ids[i] = f"UNKNOWN_{df['obs_id'][i]}"
            states[i].flag("instrument_id missing; obs_id used as instrument id")
    df["instrument_id"] = inst_ids.values

    # ---- instrument type / quote type / currency / structural fields ----
    itype = df["instrument_type"].fillna("").astype(str).str.lower().str.strip()
    df["instrument_type"] = itype.values
    for i in range(n):
        if itype[i] not in INSTRUMENT_TYPES:
            states[i].exclude(f"unsupported instrument_type {itype[i]!r}")
    qtype = df["quote_type"].fillna("").astype(str).str.lower().str.strip()
    for i in range(n):
        if itype[i] in INSTRUMENT_TYPES and qtype[i] != EXPECTED_QUOTE_TYPE[itype[i]]:
            if qtype[i] in ("", "nan", "<na>"):
                states[i].flag("quote_type missing; assumed from instrument_type")
            else:
                states[i].exclude(f"quote_type {qtype[i]!r} inconsistent with {itype[i]}")
    currency = df["currency"].fillna("").astype(str).str.upper().str.strip()
    ccy_counts = currency[currency != ""].value_counts()
    main_ccy = ccy_counts.index[0] if len(ccy_counts) else ""
    for i in range(n):
        if currency[i] == "":
            states[i].flag("currency missing")
        elif currency[i] != main_ccy:
            states[i].exclude(f"currency {currency[i]} differs from dataset currency {main_ccy}")
    start_years = df["start_years"].to_numpy(dtype=float)
    for i in range(n):
        if np.isfinite(start_years[i]) and abs(start_years[i]) > 1e-9:
            states[i].exclude(f"forward-starting instrument (start_years={start_years[i]:g}) unsupported")
    day_count = df["day_count"].fillna("").astype(str).str.upper().str.replace(" ", "")
    for i in range(n):
        if day_count[i] not in ("ACT/365F", "ACT/365", "ACT/365FIXED"):
            states[i].flag(f"day_count {day_count[i] or 'missing'} not ACT/365F; maturity_years used as documented")

    # ---- maturity -------------------------------------------------------
    mat = df["maturity_years"].to_numpy(dtype=float)
    mat_dates = pd.to_datetime(df["maturity_date"], errors="coerce", utc=False)
    for i in range(n):
        if not np.isfinite(mat[i]) or mat[i] <= 0:
            states[i].exclude("maturity_years missing or non-positive")
            continue
        if mat[i] > cfg.maturity_max_years:
            states[i].exclude(f"maturity_years {mat[i]:g} exceeds {cfg.maturity_max_years:g}")
            continue
        md = mat_dates.iloc[i]
        if pd.isna(md):
            states[i].flag("maturity_date missing/unparseable; maturity_years authoritative")
        else:
            implied = (np.datetime64(md.date()) - val_date).astype(int) / 365.0
            if abs(implied - mat[i]) > 5.0 / 365.0:
                states[i].flag(f"maturity_date implies {implied:.4f}y vs maturity_years {mat[i]:.4f}y; maturity_years authoritative")

    # ---- timestamps -----------------------------------------------------
    ts = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, format="ISO8601")
    df["timestamp_parsed"] = ts
    age_days = np.full(n, np.nan)
    for i in range(n):
        if pd.isna(ts.iloc[i]):
            states[i].flag("timestamp missing/unparseable", action="downweight", factor=cfg.bad_timestamp_factor)
            continue
        age = (val_date - np.datetime64(ts.iloc[i].date())).astype(int)
        age_days[i] = age
        if age < 0:
            states[i].exclude(f"timestamp {ts.iloc[i].date()} is after the valuation date")
        elif age > cfg.max_stale_days:
            states[i].exclude(f"stale timestamp {ts.iloc[i].date()} ({age} days before valuation date)")
    df["age_days"] = age_days

    # ---- coupon / frequency / liquidity --------------------------------
    coupon = df["coupon_rate"].to_numpy(dtype=float)
    freq = df["payment_frequency"].to_numpy(dtype=float)
    liq = df["liquidity_score"].to_numpy(dtype=float)
    for i in range(n):
        if itype[i] == "bond":
            if not np.isfinite(coupon[i]):
                states[i].exclude("bond coupon_rate missing")
            elif coupon[i] < 0 or coupon[i] > 0.25:
                if 0.25 < coupon[i] <= 25.0:
                    coupon[i] = coupon[i] / 100.0
                    states[i].flag(f"coupon_rate looked like percent; normalised to {coupon[i]:.6f}", action="correct")
                else:
                    states[i].exclude(f"bond coupon_rate {coupon[i]:g} implausible")
        if itype[i] in ("ois_swap", "bond"):
            if not np.isfinite(freq[i]) or int(freq[i]) not in VALID_FREQUENCIES or abs(freq[i] - round(freq[i])) > 1e-9:
                if itype[i] == "ois_swap" and not np.isfinite(freq[i]):
                    freq[i] = 1.0 if mat[i] <= 2.0 else 2.0
                    states[i].flag(f"payment_frequency missing; convention default {int(freq[i])} applied", action="correct")
                else:
                    states[i].exclude(f"payment_frequency {freq[i]!r} invalid")
        else:
            freq[i] = 1.0
        if not np.isfinite(liq[i]):
            liq[i] = 0.5
            states[i].flag("liquidity_score missing; 0.5 assumed", action="downweight", factor=0.8)
        elif liq[i] < 0 or liq[i] > 1:
            liq[i] = float(np.clip(liq[i], 0.0, 1.0))
            states[i].flag(f"liquidity_score outside [0,1]; clipped to {liq[i]:g}")
    df["coupon_rate"] = coupon
    df["payment_frequency"] = freq
    df["liquidity_score"] = liq

    # ---- units and normalisation ----------------------------------------
    unit = df["quote_unit"].fillna("").astype(str).str.upper().str.strip()
    quote = df["quote_value"].to_numpy(dtype=float)
    bid = df["bid"].to_numpy(dtype=float)
    ask = df["ask"].to_numpy(dtype=float)
    factor_unit = np.ones(n)
    for i in range(n):
        if itype[i] not in INSTRUMENT_TYPES:
            continue
        if itype[i] == "bond":
            if unit[i] not in PRICE_UNITS:
                if unit[i] in ("", "NAN", "<NA>"):
                    states[i].flag("quote_unit missing; PRICE_POINTS assumed")
                else:
                    states[i].exclude(f"quote_unit {unit[i]!r} not a price unit for a bond")
        else:
            if unit[i] in RATE_UNIT_FACTORS_TO_PERCENT:
                factor_unit[i] = RATE_UNIT_FACTORS_TO_PERCENT[unit[i]]
                if factor_unit[i] != 1.0:
                    states[i].flag(f"quote_unit {unit[i]} converted to PERCENT", action="correct")
            elif unit[i] in ("", "NAN", "<NA>"):
                states[i].flag("quote_unit missing; PERCENT assumed")
            else:
                states[i].exclude(f"quote_unit {unit[i]!r} not a rate unit")
    quote = quote * factor_unit
    bid = bid * factor_unit
    ask = ask * factor_unit

    # ---- missing quote from bid/ask, crossed markets -------------------
    raw_quote = quote.copy()
    for i in range(n):
        has_bid, has_ask = np.isfinite(bid[i]), np.isfinite(ask[i])
        if has_bid and has_ask and bid[i] > ask[i]:
            bid[i], ask[i] = ask[i], bid[i]
            states[i].flag("crossed bid/ask (bid > ask); sides swapped", action="downweight", factor=cfg.crossed_factor)
        if not np.isfinite(quote[i]):
            if has_bid and has_ask:
                quote[i] = 0.5 * (bid[i] + ask[i])
                states[i].flag(f"quote_value missing; bid/ask mid {quote[i]:.6f} used", action="correct")
            else:
                states[i].exclude("quote_value missing and no usable bid/ask")
        elif not (has_bid and has_ask):
            states[i].flag("bid/ask incomplete; default spread applied", action="downweight", factor=0.8)

    # ---- scale defects (peer based) --------------------------------------
    active = np.array([s.action != "exclude" for s in states])
    for i in range(n):
        if not active[i] or not np.isfinite(quote[i]):
            continue
        if itype[i] == "bond":
            fac = None
            if quote[i] < 10.0 and cfg.price_plausible[0] <= quote[i] * 100.0 <= cfg.price_plausible[1]:
                fac = 100.0
            elif quote[i] > 1000.0 and cfg.price_plausible[0] <= quote[i] / 100.0 <= cfg.price_plausible[1]:
                fac = 0.01
            if fac is not None:
                states[i].flag(f"price scale defect: {quote[i]:.6g} x{fac:g} -> {quote[i] * fac:.4f}", action="correct")
                quote[i] *= fac
                bid[i] *= fac
                ask[i] *= fac
            continue
        peers = np.flatnonzero(active & (itype.values == itype[i]) & np.isfinite(quote) & (np.arange(n) != i))
        if len(peers) == 0:
            if 0 < abs(quote[i]) < 0.1 and np.isfinite(ask[i]) and np.isfinite(bid[i]) and (ask[i] - bid[i]) < 1e-3:
                states[i].flag(f"rate scale defect (no peers; heuristic): {quote[i]:.6g} x100", action="correct")
                quote[i] *= 100.0
                bid[i] *= 100.0
                ask[i] *= 100.0
            continue
        ratio = np.abs(np.log(np.maximum(mat[peers], 1e-6) / max(mat[i], 1e-6)))
        near = peers[ratio <= np.log(1.6)]
        if len(near) < 3:
            near = peers[np.argsort(ratio, kind="stable")[: min(len(peers), 5)]]
        ref = float(np.median(quote[near]))
        dev = abs(quote[i] - ref)
        if dev <= 0.25:
            continue
        # A rescaled value is accepted when it lands much closer to the peer
        # median than the raw value and within the peers' own dispersion
        # (neighbouring tenors legitimately differ by tens of basis points).
        tol_near = max(0.5, 1.5 * float(np.max(quote[near]) - np.min(quote[near])))
        best_fac, best_dev = 1.0, dev
        for fac in (100.0, 0.01):
            d = abs(quote[i] * fac - ref)
            if d < best_dev:
                best_fac, best_dev = fac, d
        if best_fac != 1.0 and best_dev < 0.5 * dev and best_dev <= tol_near:
            states[i].flag(f"rate scale defect: {quote[i]:.6g} x{best_fac:g} -> {quote[i] * best_fac:.6f} (peer median {ref:.4f})", action="correct")
            quote[i] *= best_fac
            bid[i] *= best_fac
            ask[i] *= best_fac

    # ---- plausibility ranges -------------------------------------------
    for i in range(n):
        if states[i].action == "exclude" or not np.isfinite(quote[i]):
            continue
        lo, hi = cfg.price_plausible if itype[i] == "bond" else cfg.rate_plausible_pct
        if not (lo <= quote[i] <= hi):
            states[i].exclude(f"normalised quote {quote[i]:.6g} outside plausible range [{lo:g}, {hi:g}]")

    # ---- spreads and quote-vs-bid/ask consistency ---------------------
    spread = np.where(np.isfinite(bid) & np.isfinite(ask), ask - bid, np.nan)
    for t in INSTRUMENT_TYPES:
        m = (itype.values == t) & np.isfinite(spread) & (spread > 0)
        med = float(np.median(spread[m])) if np.any(m) else (0.05 if t == "bond" else 0.003)
        fill = (itype.values == t) & ~np.isfinite(spread)
        spread[fill] = med
    df["type_median_spread"] = 0.0
    for t in INSTRUMENT_TYPES:
        m = (itype.values == t) & np.isfinite(spread) & (spread > 0)
        df.loc[itype.values == t, "type_median_spread"] = float(np.median(spread[m])) if np.any(m) else np.nan
    for i in range(n):
        if states[i].action == "exclude" or not np.isfinite(quote[i]):
            continue
        if np.isfinite(bid[i]) and np.isfinite(ask[i]) and raw_quote[i] == raw_quote[i]:
            tol = max(spread[i], 1e-9)
            if quote[i] < bid[i] - tol or quote[i] > ask[i] + tol:
                states[i].flag(f"quote outside bid/ask by {max(bid[i] - quote[i], quote[i] - ask[i]) / tol:.1f} spreads", action="downweight", factor=cfg.outside_bid_ask_factor)

    # ---- duplicates per instrument_id ------------------------------------
    df["quote_norm"] = quote
    df["bid_norm"] = bid
    df["ask_norm"] = ask
    df["spread_norm"] = spread
    for inst_id, group in df.groupby("instrument_id", sort=False):
        idx = group.index.to_numpy()
        candidates = [i for i in idx if states[i].action != "exclude"]
        if len(candidates) <= 1:
            continue

        def rank_key(i: int) -> tuple:
            inside = np.isfinite(bid[i]) and np.isfinite(ask[i]) and bid[i] - 1e-12 <= quote[i] <= ask[i] + 1e-12
            t_i = ts.iloc[i]
            return (int(inside), 0 if pd.isna(t_i) else t_i.value, float(liq[i]), -i)

        best = max(candidates, key=rank_key)
        for i in candidates:
            if i != best:
                states[i].exclude(f"duplicate of {inst_id}: superseded by {df['obs_id'][best]} (later/in-market quote)")
        states[best].flag(f"primary among {len(candidates)} quotes for {inst_id}")

    # ---- tenor clusters and cross-sectional screen ----------------------
    cluster = np.full(n, -1, dtype=int)
    valid = np.array([s.action != "exclude" for s in states]) & np.isfinite(mat) & np.isfinite(quote)
    if np.any(valid):
        cluster[valid] = _tenor_clusters(mat[valid], cfg.cluster_rel_gap, cfg.cluster_abs_gap)
    df["tenor_cluster"] = cluster
    for t in ("deposit", "ois_swap"):
        for cid in np.unique(cluster[valid & (itype.values == t)]):
            # Iterated median/MAD screen: a single pass breaks down when a small
            # cluster holds two gross outliers (the MAD is inflated), so the
            # screen is repeated on the survivors until nothing new is flagged.
            for _pass in range(cfg.xs_max_passes):
                members = np.flatnonzero(valid & (itype.values == t) & (cluster == cid) & np.array([s.action != "exclude" for s in states]))
                if len(members) < cfg.xs_min_group:
                    break
                q = quote[members]
                med = float(np.median(q))
                mad = float(np.median(np.abs(q - med)))
                sigma = max(1.4826 * mad, cfg.xs_floor_pct)
                threshold = max(cfg.xs_sigma_multiple * sigma, cfg.xs_min_dev_pct)
                flagged = False
                for i in members:
                    dev = quote[i] - med
                    if abs(dev) > threshold:
                        states[i].exclude(f"cross-sectional outlier: {_fmt_bp(dev)} from tenor-cluster median {med:.4f} (threshold {_fmt_bp(threshold)}, pass {_pass + 1})")
                        flagged = True
                if not flagged:
                    break
    valid = np.array([s.action != "exclude" for s in states]) & valid

    # ---- liquidity / spread flags ----------------------------------------
    for i in range(n):
        if not valid[i]:
            continue
        med_spread = df["type_median_spread"][i]
        if liq[i] < cfg.illiquid_liquidity or (np.isfinite(med_spread) and spread[i] > cfg.illiquid_spread_multiple * med_spread):
            states[i].flag(f"illiquid quote (liquidity={liq[i]:.2f}, spread={spread[i]:.4g} vs type median {med_spread:.4g})", action="downweight")

    # ---- assemble audit --------------------------------------------------
    actions = [s.action for s in states]
    for i in range(n):
        if actions[i] == "keep" and np.isfinite(raw_quote[i]) and np.isfinite(quote[i]) and abs(quote[i] - raw_quote[i]) > 1e-12:
            actions[i] = "correct"
    audit = pd.DataFrame(
        {
            "obs_id": df["obs_id"],
            "instrument_id": df["instrument_id"],
            "instrument_type": itype.values,
            "maturity_years": mat,
            "action": actions,
            "normalized_quote": np.where(np.isfinite(quote), quote, np.nan),
            "weight": [0.0 if a == "exclude" else np.nan for a in actions],
            "reason": ["; ".join(s.flags) if s.flags else "passed all checks" for s in states],
            "raw_quote": df["quote_value"].to_numpy(dtype=float),
            "bid": bid,
            "ask": ask,
            "spread": spread,
            "liquidity_score": liq,
            "rule_factor": [s.factor for s in states],
            "tenor_cluster": cluster,
            "source": df["source"].astype(str).values,
            "timestamp": df["timestamp"].astype(str).values,
        }
    )
    usable = audit.index[valid]
    instruments = pd.DataFrame(
        {
            "obs_id": df["obs_id"].values[usable],
            "instrument_id": df["instrument_id"].values[usable],
            "instrument_type": itype.values[usable],
            "maturity": mat[usable],
            "quote_norm": quote[usable],
            "quote": np.where(itype.values[usable] == "bond", quote[usable], quote[usable] / 100.0),
            "frequency": freq[usable].astype(int),
            "coupon_rate": np.where(itype.values[usable] == "bond", coupon[usable], 0.0),
            "half_spread_norm": 0.5 * spread[usable],
            "liquidity": liq[usable],
            "rule_factor": np.array([states[i].factor for i in usable]),
            "tenor_cluster": cluster[usable],
            "timestamp": ts.values[usable] if len(usable) else np.array([], dtype="datetime64[ns]"),
        }
    ).reset_index(drop=True)
    if instruments["instrument_id"].duplicated().any():  # pragma: no cover - defensive
        raise RuntimeError("duplicate instrument ids survived cleaning")
    counts = audit["action"].value_counts().to_dict()
    summary = {
        "n_observations": int(n),
        "n_usable_instruments": int(len(instruments)),
        "actions": {k: int(counts.get(k, 0)) for k in ACTION_ORDER},
        "by_type": {t: int((instruments["instrument_type"] == t).sum()) for t in INSTRUMENT_TYPES},
        "stale_excluded": int(sum("stale timestamp" in s.flags[-1] if s.flags else False for s in states)),
    }
    return CleaningResult(audit=audit, instruments=instruments, summary=summary)
