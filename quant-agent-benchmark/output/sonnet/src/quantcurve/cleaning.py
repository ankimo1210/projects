"""Validation, correction, deduplication, and weighting of raw observations.

Pipeline (each stage only touches rows not already excluded):

1. Schema/range/timestamp validation -> exclude hard violations.
2. Missing-quote imputation from bid/ask midpoint -> correct.
3. Crossed bid/ask (bid > ask) -> correct by reordering.
4. Within-instrument duplicate pre-selection using only observation-
   intrinsic signals (freshness, source, self bid/ask consistency) ->
   exclude the inferior sibling(s). This must run *before* the
   cross-instrument peer check below, otherwise a duplicated bad quote
   would bias the very peer reference used to judge it.
5. Cross-instrument peer-consistency check on the surviving primary
   candidates: deposits/swaps are grouped by maturity, bonds by a
   rolling window of own-yield-to-maturity. A robust (MAD-based) local
   reference is used to test candidate unit-scale factors {1, 100,
   0.01}; the best fit is applied as a correction if within tolerance,
   otherwise the observation is excluded as an uncorrectable outlier.
6. Wide bid/ask spread or low liquidity relative to peers -> downweight
   (kept, but with reduced confidence).
7. Final spread- and liquidity-aware weight for every non-excluded row.

Every action is written to an audit trail (`action`, `reason`) alongside
the (possibly corrected) `normalized_quote` and final `weight`.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from .cashflows import bond_ytm

VALID_TYPES = {"deposit", "ois_swap", "bond"}
CANDIDATE_FACTORS = (1.0, 100.0, 0.01)
Z_THRESHOLD = 6.0
REL_FLOOR = 0.02
ABS_FLOOR_RATE = 1e-4
ABS_FLOOR_YIELD = 0.0015
BOND_YTM_WINDOW = 7
SPREAD_Z_THRESHOLD = 6.0
PREFERRED_SOURCES = {"BACKUP_FEED"}  # sources treated as lower priority


def clean_market_data(raw: pd.DataFrame, valuation_date: datetime | None = None) -> pd.DataFrame:
    df = raw.copy().reset_index(drop=True)
    df["action"] = "keep"
    df["reason"] = ""
    df["normalized_quote"] = pd.to_numeric(df["quote_value"], errors="coerce")
    df["bid_n"] = pd.to_numeric(df["bid"], errors="coerce")
    df["ask_n"] = pd.to_numeric(df["ask"], errors="coerce")
    df["weight"] = 0.0
    df["applied_factor"] = 1.0
    df["excluded"] = False
    df["wide_spread_flag"] = False

    _validate_schema(df, valuation_date)
    _impute_missing_quotes(df)
    _fix_crossed_bid_ask(df)
    _resolve_duplicates(df)
    _detect_scale_errors(df)
    _flag_wide_spread(df)
    _finalize_weights(df)

    df.loc[df["excluded"], "action"] = "exclude"
    return df.drop(columns=["excluded", "wide_spread_flag"])


def _append_reason(df: pd.DataFrame, idx, text: str) -> None:
    for i in np.atleast_1d(idx):
        current = df.at[i, "reason"]
        df.at[i, "reason"] = f"{current}; {text}" if current else text


def _exclude(df: pd.DataFrame, idx, text: str) -> None:
    for i in np.atleast_1d(idx):
        df.at[i, "excluded"] = True
    _append_reason(df, idx, text)


def _validate_schema(df: pd.DataFrame, valuation_date: datetime | None) -> None:
    bad_type = ~df["instrument_type"].isin(VALID_TYPES)
    _exclude(df, df.index[bad_type], "unsupported instrument_type")

    bad_maturity = df["maturity_years"].isna() | (df["maturity_years"] <= 0)
    _exclude(df, df.index[bad_maturity], "maturity_years must be positive")

    bad_freq = df["payment_frequency"].isna() | (df["payment_frequency"] <= 0)
    _exclude(df, df.index[bad_freq], "payment_frequency must be positive")

    bad_liq = df["liquidity_score"].isna() | (df["liquidity_score"] < 0) | (df["liquidity_score"] > 1)
    _exclude(df, df.index[bad_liq], "liquidity_score out of [0, 1]")

    bond_mask = df["instrument_type"] == "bond"
    bad_coupon = bond_mask & (df["coupon_rate"].isna() | (df["coupon_rate"] < 0))
    _exclude(df, df.index[bad_coupon], "bond requires a non-negative coupon_rate")

    if valuation_date is not None:
        ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        val_ts = pd.Timestamp(valuation_date)
        if val_ts.tzinfo is None:
            val_ts = val_ts.tz_localize("UTC")
        future = ts.isna() | (ts > val_ts + timedelta(days=1))
        _exclude(df, df.index[future], "timestamp unparseable or after the valuation date")


def _impute_missing_quotes(df: pd.DataFrame) -> None:
    active = ~df["excluded"]
    missing_quote = active & df["normalized_quote"].isna()
    have_bid_ask = missing_quote & df["bid_n"].notna() & df["ask_n"].notna()
    idx = df.index[have_bid_ask]
    df.loc[idx, "normalized_quote"] = (df.loc[idx, "bid_n"] + df.loc[idx, "ask_n"]) / 2.0
    df.loc[idx, "action"] = "correct"
    _append_reason(df, idx, "missing quote_value imputed from bid/ask midpoint")

    still_missing = missing_quote & ~have_bid_ask
    _exclude(df, df.index[still_missing], "missing quote_value with no bid/ask fallback")


def _fix_crossed_bid_ask(df: pd.DataFrame) -> None:
    active = ~df["excluded"]
    crossed = active & df["bid_n"].notna() & df["ask_n"].notna() & (df["bid_n"] > df["ask_n"])
    idx = df.index[crossed]
    if len(idx) == 0:
        return
    old_bid = df.loc[idx, "bid_n"].copy()
    df.loc[idx, "bid_n"] = df.loc[idx, "ask_n"]
    df.loc[idx, "ask_n"] = old_bid
    df.loc[idx, "action"] = "correct"
    _append_reason(df, idx, "crossed bid/ask (bid > ask) corrected by reordering")


def _resolve_duplicates(df: pd.DataFrame) -> None:
    active = ~df["excluded"]
    for instrument_id, group in df[active].groupby("instrument_id"):
        if len(group) <= 1:
            continue
        parsed_ts = pd.to_datetime(df.loc[group.index, "timestamp"], utc=True, errors="coerce")

        def _sort_key(i):
            ts = parsed_ts.at[i]
            epoch = ts.timestamp() if pd.notna(ts) else 0.0
            return (
                0 if df.at[i, "source"] not in PREFERRED_SOURCES else 1,
                -_self_consistency_score(df, i),
                -epoch,
            )

        ranked = sorted(group.index, key=_sort_key)
        primary, *rest = ranked
        _exclude(
            df,
            rest,
            f"duplicate observation for {instrument_id}; superseded by obs_id={df.at[primary, 'obs_id']}",
        )


def _self_consistency_score(df: pd.DataFrame, i) -> float:
    """Higher is better: 1 if the quote lies within its own bid/ask, else 0."""
    bid, ask, q = df.at[i, "bid_n"], df.at[i, "ask_n"], df.at[i, "normalized_quote"]
    if pd.isna(bid) or pd.isna(ask) or pd.isna(q):
        return 0.0
    return 1.0 if bid <= q <= ask else 0.0


def _robust_reference(values: np.ndarray) -> tuple[float, float]:
    """Median and a MAD-based scale (unscaled; caller applies its own floor)."""
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median))) * 1.4826
    return median, mad


def _best_factor(value: float, reference: float, scale: float) -> tuple[float, float]:
    """Return (best_factor, best_z) among CANDIDATE_FACTORS."""
    best_factor, best_z = 1.0, np.inf
    for factor in CANDIDATE_FACTORS:
        candidate = value * factor
        z = abs(candidate - reference) / scale
        if z < best_z:
            best_factor, best_z = factor, z
    return best_factor, best_z


def _apply_correction(df: pd.DataFrame, i, factor: float) -> None:
    df.at[i, "normalized_quote"] *= factor
    if pd.notna(df.at[i, "bid_n"]):
        df.at[i, "bid_n"] *= factor
    if pd.notna(df.at[i, "ask_n"]):
        df.at[i, "ask_n"] *= factor
    df.at[i, "applied_factor"] = factor
    df.at[i, "action"] = "correct"


def _detect_scale_errors(df: pd.DataFrame) -> None:
    active = df.index[~df["excluded"]]

    rate_mask = df.loc[active, "instrument_type"].isin(["deposit", "ois_swap"])
    rate_idx = active[rate_mask]
    buckets = df.loc[rate_idx, "maturity_years"].round(6)
    for _, idx in pd.Series(rate_idx, index=rate_idx).groupby(buckets):
        idx = list(idx)
        if len(idx) < 2:
            values = df.loc[idx, "normalized_quote"].to_numpy()
            reference, mad = values[0], 0.0
        else:
            values = df.loc[idx, "normalized_quote"].to_numpy()
            reference, mad = _robust_reference(values)
        scale = max(mad, REL_FLOOR * abs(reference), ABS_FLOOR_RATE)
        for i in idx:
            value = df.at[i, "normalized_quote"]
            factor, z = _best_factor(value, reference, scale)
            if z <= Z_THRESHOLD:
                if factor != 1.0:
                    _apply_correction(df, i, factor)
                    _append_reason(
                        df, i, f"unit-scale correction (x{factor:g}) aligns with local maturity-peer reference"
                    )
            else:
                _exclude(
                    df,
                    i,
                    "quote deviates from robust local maturity-peer reference beyond tolerance "
                    "under every candidate unit-scale factor",
                )

    bond_idx = active[df.loc[active, "instrument_type"] == "bond"]
    if len(bond_idx) == 0:
        return
    bond_rows = df.loc[bond_idx].copy()
    bond_rows["_ytm"] = [
        _safe_ytm(row.maturity_years, row.coupon_rate, row.payment_frequency, row.normalized_quote)
        for row in bond_rows.itertuples()
    ]
    bond_rows = bond_rows.sort_values("maturity_years")
    ordered = list(bond_rows.index)
    n = len(ordered)
    half = BOND_YTM_WINDOW // 2

    def _window(pos: int) -> list:
        lo, hi = max(0, pos - half), min(n, pos + half + 1)
        return [ordered[k] for k in range(lo, hi)]

    # Pass 1: flag candidate problem bonds from the raw (uncorrected) YTMs.
    flagged = set()
    for pos, i in enumerate(ordered):
        ytms = np.array([bond_rows.at[j, "_ytm"] for j in _window(pos)], dtype=float)
        ytms = ytms[np.isfinite(ytms)]
        if len(ytms) < 2:
            continue
        reference, mad = _robust_reference(ytms)
        scale = max(mad, ABS_FLOOR_YIELD)
        own_ytm = bond_rows.at[i, "_ytm"]
        z = abs(own_ytm - reference) / scale if np.isfinite(own_ytm) else np.inf
        if z > Z_THRESHOLD:
            flagged.add(i)

    # Pass 2: recompute each flagged bond's reference excluding *other* flagged
    # peers from its window (a flagged neighbour's own bad YTM should not be
    # allowed to bias the reference used to judge this bond), then decide
    # correction vs. exclusion.
    for i in flagged:
        pos = ordered.index(i)
        window = [j for j in _window(pos) if j == i or j not in flagged]
        ytms = np.array([bond_rows.at[j, "_ytm"] for j in window], dtype=float)
        ytms = ytms[np.isfinite(ytms)]
        if len(ytms) < 2:
            window = _window(pos)
            ytms = np.array([bond_rows.at[j, "_ytm"] for j in window], dtype=float)
            ytms = ytms[np.isfinite(ytms)]
        if len(ytms) < 2:
            continue
        reference, mad = _robust_reference(ytms)
        scale = max(mad, ABS_FLOOR_YIELD)
        row = bond_rows.loc[i]
        own_ytm = bond_rows.at[i, "_ytm"]
        z = abs(own_ytm - reference) / scale if np.isfinite(own_ytm) else np.inf
        best_factor, best_z = 1.0, z
        for factor in CANDIDATE_FACTORS:
            if factor == 1.0:
                continue
            candidate_price = row["normalized_quote"] * factor
            candidate_ytm = _safe_ytm(row["maturity_years"], row["coupon_rate"], row["payment_frequency"], candidate_price)
            if not np.isfinite(candidate_ytm):
                continue
            cz = abs(candidate_ytm - reference) / scale
            if cz < best_z:
                best_factor, best_z = factor, cz
        if best_z <= Z_THRESHOLD and best_factor != 1.0:
            _apply_correction(df, i, best_factor)
            _append_reason(
                df, i, f"unit-scale correction (x{best_factor:g}) aligns bond YTM with local maturity-window reference"
            )
        else:
            _exclude(
                df,
                i,
                "bond yield-to-maturity deviates from local maturity-window reference beyond tolerance "
                "under every candidate unit-scale factor",
            )


def _safe_ytm(maturity_years: float, coupon_rate: float, frequency: float, price: float) -> float:
    try:
        if price <= 0 or not np.isfinite(price):
            return np.nan
        return bond_ytm(maturity_years, coupon_rate, int(frequency), price)
    except Exception:
        return np.nan


def _flag_wide_spread(df: pd.DataFrame) -> None:
    active = df.index[~df["excluded"]]
    mid = (df.loc[active, "bid_n"] + df.loc[active, "ask_n"]) / 2.0
    spread_bp = 1e4 * (df.loc[active, "ask_n"] - df.loc[active, "bid_n"]).abs() / mid.abs().replace(0, np.nan)
    for itype, idx in pd.Series(active, index=active).groupby(df.loc[active, "instrument_type"]):
        idx = list(idx)
        s = spread_bp.loc[idx].dropna()
        if len(s) < 2:
            continue
        med, mad = _robust_reference(s.to_numpy())
        scale = max(mad, 0.05 * med, 1e-6)
        for i in s.index:
            z = (s.at[i] - med) / scale
            if z <= SPREAD_Z_THRESHOLD:
                continue
            df.at[i, "wide_spread_flag"] = True
            if df.at[i, "action"] != "correct":
                df.at[i, "action"] = "downweight"
                _append_reason(df, i, "bid/ask spread is an extreme outlier versus same-type peers")
            else:
                _append_reason(df, i, "bid/ask spread is an extreme outlier versus same-type peers (also downweighted)")


def _finalize_weights(df: pd.DataFrame) -> None:
    active = df.index[~df["excluded"]]
    mid = (df.loc[active, "bid_n"] + df.loc[active, "ask_n"]) / 2.0
    spread_bp = 1e4 * (df.loc[active, "ask_n"] - df.loc[active, "bid_n"]).abs() / mid.abs().replace(0, np.nan)
    spread_bp = spread_bp.fillna(spread_bp.median() if spread_bp.notna().any() else 1.0)
    liquidity = df.loc[active, "liquidity_score"].clip(lower=0.01)
    raw_weight = liquidity / (1.0 + spread_bp / 25.0)
    for itype, idx in pd.Series(active, index=active).groupby(df.loc[active, "instrument_type"]):
        idx = list(idx)
        vals = raw_weight.loc[idx]
        med = vals.median()
        norm = vals / med if med > 0 else vals
        df.loc[idx, "weight"] = norm.clip(lower=0.02)
    # Applied by flag, not by the `action` label: a row can already be
    # `correct` (e.g. a rescaled quote) and *also* have an extreme spread,
    # in which case the audit reason says "(also downweighted)" and this
    # must actually reduce its weight even though `action` stays "correct".
    flagged = df.index[df["wide_spread_flag"] & ~df["excluded"]]
    df.loc[flagged, "weight"] = df.loc[flagged, "weight"] * 0.1
