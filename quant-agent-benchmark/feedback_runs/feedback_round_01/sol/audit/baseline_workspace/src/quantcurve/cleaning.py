"""Auditable market-data validation, normalization, and weighting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .config import CurveConfig


@dataclass
class CleaningResult:
    audit: pd.DataFrame
    usable: pd.DataFrame


RATE_TYPES = {"deposit", "ois_swap"}


def _append_reason(existing: str, reason: str) -> str:
    return f"{existing}; {reason}" if existing else reason


def _local_rate_reference(frame: pd.DataFrame, index: int) -> float:
    row = frame.loc[index]
    candidates = frame[
        (frame["instrument_type"] == row["instrument_type"])
        & frame["quote_value"].notna()
        & (frame["quote_value"].abs() >= 0.25)
        & (frame["quote_value"].abs() <= 20.0)
    ].copy()
    if candidates.empty:
        return 0.02
    candidates["distance"] = (candidates["maturity_years"] - row["maturity_years"]).abs()
    nearest = candidates.nsmallest(min(12, len(candidates)), "distance")
    return float(nearest["quote_value"].median()) / 100.0


def clean_market_data(
    frame: pd.DataFrame,
    valuation_date: str | date,
    config: CurveConfig | None = None,
) -> CleaningResult:
    """Return one-row-per-input audit data and model-usable normalized rows."""
    cfg = config or CurveConfig()
    valuation = pd.Timestamp(valuation_date, tz="UTC")
    data = frame.copy().reset_index(drop=True)
    for name in ("quote_value", "bid", "ask", "maturity_years", "coupon_rate", "liquidity_score"):
        data[name] = pd.to_numeric(data[name], errors="coerce")
    data["parsed_timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce", utc=True)
    data["parsed_maturity_date"] = pd.to_datetime(data["maturity_date"], errors="coerce", utc=True)
    future_cutoff = valuation.to_pydatetime() + timedelta(days=1)

    audits: list[dict[str, object]] = []
    normalized_rows: list[dict[str, object]] = []
    for idx, row in data.iterrows():
        action = "keep"
        reason = "passed validation"
        excluded = False
        row_reasons: list[str] = []

        def reject(message: str) -> None:
            nonlocal action, reason, excluded
            action = "exclude"
            reason = message if reason == "passed validation" else _append_reason(reason, message)
            excluded = True

        instrument_type = str(row["instrument_type"])
        expected_quote = {"deposit": "simple_rate", "ois_swap": "par_rate", "bond": "clean_price"}
        expected_unit = {"deposit": "PERCENT", "ois_swap": "PERCENT", "bond": "PRICE_POINTS"}
        if not str(row["obs_id"]) or not str(row["instrument_id"]):
            reject("missing observation or instrument identifier")
        if instrument_type not in expected_quote:
            reject("unsupported instrument type")
        if str(row["currency"]) != "USD":
            reject("currency is not documented USD")
        if not np.isfinite(row["maturity_years"]) or not 0 < float(row["maturity_years"]) <= 50:
            reject("maturity is missing or outside (0, 50] years")
        if pd.isna(row["parsed_maturity_date"]):
            reject("maturity date is missing or malformed")
        elif row["parsed_maturity_date"] <= valuation:
            reject("maturity date is not after valuation date")
        elif np.isfinite(row["maturity_years"]):
            calendar_fraction = (row["parsed_maturity_date"] - valuation).total_seconds() / (365.0 * 86400.0)
            if abs(calendar_fraction - float(row["maturity_years"])) > 10.0 / 365.0:
                row_reasons.append("maturity date/year-fraction mismatch; retained authoritative maturity_years")
        if not np.isfinite(row["start_years"]) or abs(float(row["start_years"])) > 1e-12:
            reject("start_years is not documented spot start 0")
        if str(row["day_count"]) != "ACT/365F":
            reject("day-count differs from documented ACT/365F")
        if row["settlement_days"] != 2:
            reject("settlement lag differs from documented two days")
        if instrument_type in expected_quote:
            if str(row["quote_type"]) != expected_quote[instrument_type]:
                reject("quote type is inconsistent with instrument type")
            if str(row["quote_unit"]) != expected_unit[instrument_type]:
                reject("quote unit is inconsistent with documented convention")
        frequency = row["payment_frequency"]
        if not np.isfinite(frequency) or int(frequency) <= 0:
            reject("payment frequency is missing or non-positive")
        if instrument_type == "bond" and (not np.isfinite(row["coupon_rate"]) or row["coupon_rate"] < 0 or row["coupon_rate"] > 0.25):
            reject("bond coupon is missing or outside [0, 25%]")
        if instrument_type in {"deposit", "ois_swap"} and np.isfinite(frequency) and np.isfinite(row["maturity_years"]):
            documented_frequency = 1 if instrument_type == "deposit" or float(row["maturity_years"]) <= 2.0 else 2
            if int(frequency) != documented_frequency:
                reject("payment frequency is inconsistent with documented deposit/OIS schedule")
        if not np.isfinite(row["liquidity_score"]) or not 0 <= row["liquidity_score"] <= 1:
            reject("liquidity score is missing or outside [0, 1]")
        if pd.isna(row["parsed_timestamp"]):
            reject("timestamp is missing or malformed")
        elif row["parsed_timestamp"].to_pydatetime() > future_cutoff:
            reject("timestamp is after the valuation date")

        quote = float(row["quote_value"]) if np.isfinite(row["quote_value"]) else np.nan
        bid = float(row["bid"]) if np.isfinite(row["bid"]) else np.nan
        ask = float(row["ask"]) if np.isfinite(row["ask"]) else np.nan
        if np.isfinite(bid) and np.isfinite(ask) and bid > ask:
            bid, ask = ask, bid
            row_reasons.append("bid/ask inversion corrected by swapping endpoints")
        if not np.isfinite(quote) and np.isfinite(bid) and np.isfinite(ask):
            quote = 0.5 * (bid + ask)
            row_reasons.append("missing quote replaced by observable bid/ask midpoint")
        if not np.isfinite(quote):
            reject("quote and usable bid/ask midpoint are missing")

        factor = 1.0
        if instrument_type in RATE_TYPES and np.isfinite(quote):
            reference = _local_rate_reference(data, idx)
            standard = quote / 100.0
            already_decimal = quote
            if abs(already_decimal - reference) < 0.35 * max(abs(standard - reference), 1e-12):
                factor = 1.0
                row_reasons.append("rate mislabeled PERCENT detected from maturity-local peers; treated as decimal")
            else:
                factor = 0.01
        elif instrument_type == "bond" and np.isfinite(quote):
            if 0.2 <= abs(quote) < 20.0:
                factor = 100.0
                row_reasons.append("bond price in currency units detected; converted to points per 100")

        normalized_quote = quote * factor if np.isfinite(quote) else np.nan
        normalized_bid = bid * factor if np.isfinite(bid) else np.nan
        normalized_ask = ask * factor if np.isfinite(ask) else np.nan
        if np.isfinite(normalized_bid) and np.isfinite(normalized_ask):
            spread = normalized_ask - normalized_bid
        else:
            spread = np.nan
            row_reasons.append("bid/ask incomplete; conservative missing-spread weight applied")
        off_market = bool(
            np.isfinite(normalized_quote)
            and np.isfinite(normalized_bid)
            and np.isfinite(normalized_ask)
            and (normalized_quote < normalized_bid - 1e-12 or normalized_quote > normalized_ask + 1e-12)
        )
        if off_market:
            row_reasons.append("quote lies outside corrected bid/ask interval; retained but confidence reduced")

        if instrument_type in RATE_TYPES and np.isfinite(normalized_quote) and abs(normalized_quote) > 0.25:
            reject("normalized rate exceeds absolute 25% range")
        if instrument_type == "bond" and np.isfinite(normalized_quote) and not 20 <= normalized_quote <= 200:
            reject("normalized bond price outside [20, 200] points")

        if row_reasons and not excluded:
            action = "correct"
            reason = "; ".join(row_reasons)
        elif row_reasons:
            reason = _append_reason(reason, "; ".join(row_reasons))

        normalized = row.to_dict()
        normalized.update(
            normalized_quote=normalized_quote,
            normalized_bid=normalized_bid,
            normalized_ask=normalized_ask,
            spread=spread,
            off_market=off_market,
            _input_index=idx,
            _excluded=excluded,
            _initial_action=action,
            _initial_reason=reason,
        )
        normalized_rows.append(normalized)
        audits.append(
            {
                "obs_id": row["obs_id"],
                "instrument_id": row["instrument_id"],
                "action": action,
                "normalized_quote": normalized_quote,
                "weight": 0.0 if excluded else np.nan,
                "reason": reason,
            }
        )

    normalized = pd.DataFrame(normalized_rows)
    audit = pd.DataFrame(audits)

    # Deduplicate only after validation. Latest timestamp wins, then liquidity,
    # then a transparent source preference; every discarded row stays in audit.
    source_rank = {"COMPOSITE": 3, "VENUE_A": 2, "VENUE_B": 2, "BACKUP_FEED": 1}
    eligible = normalized[~normalized["_excluded"]].copy()
    eligible["_source_rank"] = eligible["source"].map(source_rank).fillna(0)
    for _, group in eligible.groupby("instrument_id", sort=False):
        if len(group) <= 1:
            continue
        winner = group.sort_values(
            ["parsed_timestamp", "liquidity_score", "_source_rank", "obs_id"],
            ascending=[False, False, False, True],
        ).index[0]
        for loser in group.index:
            if loser == winner:
                continue
            normalized.loc[loser, "_excluded"] = True
            audit.loc[loser, "action"] = "exclude"
            audit.loc[loser, "weight"] = 0.0
            audit.loc[loser, "reason"] = _append_reason(
                str(audit.loc[loser, "reason"]),
                f"duplicate instrument; retained newer/higher-quality obs_id {normalized.loc[winner, 'obs_id']}",
            )

    usable = normalized[~normalized["_excluded"]].copy()
    if usable.empty:
        raise ValueError("no usable observations remain after validation")

    typical_spread: dict[str, float] = {}
    for instrument_type, group in usable.groupby("instrument_type"):
        positive = group.loc[np.isfinite(group["spread"]) & (group["spread"] > 0), "spread"]
        floor = cfg.min_price_scale if instrument_type == "bond" else cfg.min_rate_scale
        typical_spread[instrument_type] = max(float(positive.median()) if len(positive) else floor, floor)

    weights = []
    for idx, row in usable.iterrows():
        typical = typical_spread[str(row["instrument_type"])]
        spread = float(row["spread"]) if np.isfinite(row["spread"]) and row["spread"] > 0 else 2.0 * typical
        spread_ratio = spread / typical
        liquidity = max(float(row["liquidity_score"]), 0.01)
        weight = np.sqrt(liquidity) / (1.0 + 0.25 * spread_ratio * spread_ratio)
        reasons: list[str] = []
        age_days = (valuation - row["parsed_timestamp"]).total_seconds() / 86400.0
        if age_days > cfg.stale_after_days:
            weight *= cfg.stale_weight
            reasons.append(f"stale by {age_days:.1f} days; weight multiplied by {cfg.stale_weight:.2f}")
        if liquidity < cfg.low_liquidity_cutoff:
            reasons.append(f"low liquidity score {liquidity:.3f}")
        if not np.isfinite(row["spread"]):
            reasons.append("missing spread reduced confidence")
        if bool(row["off_market"]):
            weight *= 0.25
            reasons.append("off-market quote weight multiplied by 0.25")
        weights.append(weight)
        if reasons:
            current = int(row["_input_index"])
            previous_action = str(audit.loc[current, "action"])
            audit.loc[current, "action"] = "downweight"
            if previous_action == "keep":
                audit.loc[current, "reason"] = "; ".join(reasons)
            else:
                audit.loc[current, "reason"] = _append_reason(str(audit.loc[current, "reason"]), "; ".join(reasons))
    usable["base_weight"] = np.asarray(weights)
    usable["fit_weight"] = usable["base_weight"]
    usable["robust_multiplier"] = 1.0
    usable = usable.reset_index(drop=True)
    for _, row in usable.iterrows():
        audit.loc[int(row["_input_index"]), "weight"] = float(row["base_weight"])
    return CleaningResult(audit=audit, usable=usable)


def apply_robust_audit(
    result: CleaningResult,
    robust_multipliers: np.ndarray,
    standardized_residuals: np.ndarray,
) -> CleaningResult:
    """Add iterative outlier weights to the immutable one-row input audit."""
    usable = result.usable.copy()
    audit = result.audit.copy()
    multipliers = np.asarray(robust_multipliers, dtype=float)
    residuals = np.asarray(standardized_residuals, dtype=float)
    if multipliers.shape != (len(usable),) or residuals.shape != (len(usable),):
        raise ValueError("robust arrays must match usable observations")
    usable["robust_multiplier"] = multipliers
    usable["fit_weight"] = usable["base_weight"] * multipliers
    for pos, row in usable.iterrows():
        source_index = int(row["_input_index"])
        audit.loc[source_index, "weight"] = float(usable.loc[pos, "fit_weight"])
        if multipliers[pos] < 0.999:
            message = f"iterative Huber outlier weight {multipliers[pos]:.4f} at standardized residual {residuals[pos]:.2f}"
            if audit.loc[source_index, "action"] in {"keep", "correct"}:
                audit.loc[source_index, "action"] = "downweight"
            audit.loc[source_index, "reason"] = _append_reason(str(audit.loc[source_index, "reason"]), message)
    return CleaningResult(audit=audit, usable=usable)
