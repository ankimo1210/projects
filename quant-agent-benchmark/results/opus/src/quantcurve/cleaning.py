"""Cleaning decisions and the audit trail behind them.

Every input observation receives exactly one of the four mandated actions:

``keep``
    Used as quoted.
``correct``
    A deterministic, documented repair was applied (unit rescaling, quote
    reconstructed from the bid/ask mid, crossed market un-crossed).
``downweight``
    Usable but less trustworthy: wide market, illiquid, stale-but-tolerable,
    or repaired.  The weight column carries the size of the penalty.
``exclude``
    Not used for calibration at all.

The rules are applied in a fixed order so that the reason recorded for a row is
reproducible and explainable.  Weights combine a bid/ask-and-liquidity based
statistical precision with a multiplicative data-quality penalty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from .conventions import annual_frequency_for_swap
from .instruments import BOND, DEPOSIT, OIS_SWAP, Instrument
from .io import LoadedMarketData, MarketDataError
from .validation import ValidationConfig, ValidationReport

__all__ = [
    "CleaningConfig",
    "CleaningResult",
    "clean",
    "apply_exclusions",
    "estimate_model_error",
    "reweight_instruments",
    "audit_with_weights",
    "ACTIONS",
]

ACTIONS = ("keep", "correct", "downweight", "exclude")

# Ranking used when several rules fire on the same row.  A materially repaired
# observation is reported as ``correct`` even when it is also downweighted: the
# size of the downweight is already visible in the weight column, whereas the
# fact that the quote was altered would otherwise be lost.
_ACTION_RANK = {"keep": 0, "downweight": 1, "correct": 2, "exclude": 3}


@dataclass(frozen=True)
class CleaningConfig:
    """Weighting and penalty parameters."""

    #: Floor and cap applied to the yield-equivalent half bid/ask spread (bp)
    #: before it is turned into a precision weight.
    sigma_floor_bp: float = 0.1
    sigma_cap_bp: float = 20.0
    #: Liquidity scores are clipped into this range before inflating sigma.
    liquidity_floor: float = 0.10
    #: Final weights are clipped to this band around the median weight.
    weight_clip: tuple[float, float] = (0.02, 50.0)
    #: Multiplicative quality penalties.
    penalty_corrected_quote: float = 0.50
    penalty_crossed_market: float = 0.50
    penalty_wide_spread: float = 0.60
    penalty_illiquid: float = 0.70
    penalty_quote_outside_band: float = 0.50
    penalty_unit_rescaled: float = 0.80
    #: Fallback half-spread (bp) when no usable two-way market is available.
    fallback_half_spread_bp: float = 5.0
    #: Bounds on the empirically estimated per-type model error (bp).
    min_model_error_bp: float = 0.25
    max_model_error_bp: float = 25.0
    #: Irreducible model error (bp) added in quadrature to the quote uncertainty.
    #: Without it an implausibly tight two-way market would claim a precision the
    #: curve model cannot deliver, and ordinary smoothing bias would be mistaken
    #: for a bad quote by the robust screen.
    model_error_bp: float = 1.0


@dataclass
class CleaningResult:
    """Cleaned instruments plus the full per-observation audit trail."""

    instruments: list[Instrument]
    audit: pd.DataFrame
    findings: list[str] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)


def _duration_proxy(maturity_years: float, instrument_type: str) -> float:
    """Rough modified duration used only to convert a bond price spread into bp."""
    if instrument_type != BOND:
        return 1.0
    # A par bond's duration is close to (1 - exp(-yT)) / y; with y unknown at this
    # stage a level of 2.5% is a perfectly adequate scaling constant.
    y = 0.025
    return float((1.0 - np.exp(-y * maturity_years)) / y)


def clean(
    loaded: LoadedMarketData,
    report: ValidationReport,
    valuation_date: datetime,
    config: CleaningConfig | None = None,
    validation_config: ValidationConfig | None = None,
) -> CleaningResult:
    """Apply the documented cleaning policy and build the audit trail."""
    config = config or CleaningConfig()
    validation_config = validation_config or ValidationConfig()
    frame = loaded.frame
    flags = report.flags
    n = len(frame)

    action = np.array(["keep"] * n, dtype=object)
    reasons: list[list[str]] = [[] for _ in range(n)]
    penalty = np.ones(n, dtype=float)
    quote = frame["quote_value"].to_numpy(dtype=float).copy()
    bid = frame["bid"].to_numpy(dtype=float).copy()
    ask = frame["ask"].to_numpy(dtype=float).copy()
    itype = frame["instrument_type"].astype(str).to_numpy()
    maturity = frame["maturity_years"].to_numpy(dtype=float)
    scale = (
        np.ones(n)
        if report.scale_factor is None
        else np.asarray(report.scale_factor, dtype=float)
    )
    age_hours = (
        np.zeros(n) if report.age_hours is None else np.asarray(report.age_hours, float)
    )

    def escalate(i: int, new_action: str, reason: str) -> None:
        if _ACTION_RANK[new_action] > _ACTION_RANK[action[i]]:
            action[i] = new_action
        if reason not in reasons[i]:
            reasons[i].append(reason)

    # ---- 1. hard schema / range failures -------------------------------
    fatal = {
        "unknown_instrument_type": "unsupported instrument_type",
        "unparseable_number": "non-numeric value in a numeric column",
        "bad_maturity": "maturity_years missing, non-positive or implausible",
        "forward_starting": "forward-starting instrument (start_years != 0) is unsupported",
        "bad_frequency": "payment_frequency outside {1,2,4,12}",
        "missing_coupon": "bond without a coupon_rate",
        "bad_coupon": "bond coupon_rate outside a plausible range",
        "bad_timestamp": "timestamp is not ISO-8601",
        "future_timestamp": "timestamp is after the valuation date",
        "unexpected_quote_type": "quote_type does not match instrument_type",
    }
    for flag, reason in fatal.items():
        for i in np.flatnonzero(flags[flag].to_numpy()):
            escalate(int(i), "exclude", reason)

    # ---- 2. unit normalisation -----------------------------------------
    for i in np.flatnonzero(scale != 1.0):
        i = int(i)
        if action[i] == "exclude":
            continue
        factor = float(scale[i])
        quote[i] *= factor
        if np.isfinite(bid[i]):
            bid[i] *= factor
        if np.isfinite(ask[i]):
            ask[i] *= factor
        penalty[i] *= config.penalty_unit_rescaled
        escalate(
            i,
            "correct",
            f"quote unit rescaled by {factor:g} to match documented "
            f"{'PRICE_POINTS' if itype[i] == BOND else 'PERCENT'} units",
        )

    # ---- 3. crossed / degenerate two-way markets ------------------------
    for i in np.flatnonzero(flags["crossed_market"].to_numpy()):
        i = int(i)
        if action[i] == "exclude":
            continue
        bid[i], ask[i] = ask[i], bid[i]
        penalty[i] *= config.penalty_crossed_market
        escalate(
            i,
            "correct",
            f"crossed market: bid and ask swapped, weight scaled by "
            f"{config.penalty_crossed_market:g}",
        )

    # ---- 4. missing quotes reconstructed from the two-way market --------
    for i in np.flatnonzero(flags["missing_quote"].to_numpy()):
        i = int(i)
        if action[i] == "exclude":
            continue
        if np.isfinite(bid[i]) and np.isfinite(ask[i]):
            quote[i] = 0.5 * (bid[i] + ask[i])
            penalty[i] *= config.penalty_corrected_quote
            escalate(i, "correct", "missing quote_value reconstructed from bid/ask mid")
        else:
            escalate(i, "exclude", "quote_value missing and no usable bid/ask")

    # ---- 5. quotes outside their own two-way market ---------------------
    for i in np.flatnonzero(flags["quote_outside_band"].to_numpy()):
        i = int(i)
        if action[i] == "exclude" or not (np.isfinite(bid[i]) and np.isfinite(ask[i])):
            continue
        lo, hi = min(bid[i], ask[i]), max(bid[i], ask[i])
        distance = quote[i] - np.clip(quote[i], lo, hi)
        quote[i] = 0.5 * (lo + hi)
        penalty[i] *= config.penalty_quote_outside_band
        escalate(
            i,
            "correct",
            f"quote {distance:+.6g} outside its own bid/ask band; reset to the mid",
        )

    # ---- 6. staleness ---------------------------------------------------
    for i in np.flatnonzero(flags["stale_timestamp"].to_numpy()):
        i = int(i)
        if action[i] == "exclude":
            continue
        escalate(
            i,
            "exclude",
            f"stale quote: {age_hours[i]:.1f}h older than the latest observation "
            f"(limit {validation_config.max_quote_age_hours:.0f}h)",
        )

    # ---- 7. duplicate observations of the same instrument ---------------
    stamps = pd.to_datetime(frame["timestamp"], format="ISO8601", utc=True, errors="coerce")
    spread_abs = np.abs(ask - bid)
    order_key = pd.DataFrame(
        {
            "instrument_id": frame["instrument_id"].astype(str).to_numpy(),
            "excluded": [action[i] == "exclude" for i in range(n)],
            "stamp": stamps.to_numpy(),
            "spread": np.where(np.isfinite(spread_abs), spread_abs, np.inf),
            "obs_id": frame["obs_id"].astype(str).to_numpy(),
            "row": np.arange(n),
        }
    )
    for instrument_id, group in order_key.groupby("instrument_id", sort=True):
        if len(group) < 2:
            continue
        ranked = group.sort_values(
            by=["excluded", "stamp", "spread", "obs_id"],
            ascending=[True, False, True, True],
            kind="stable",
        )
        survivor = int(ranked.iloc[0]["row"])
        for row in ranked.iloc[1:]["row"].to_numpy():
            i = int(row)
            if action[i] == "exclude":
                continue
            escalate(
                i,
                "exclude",
                f"duplicate observation of {instrument_id}; superseded by "
                f"{frame['obs_id'].iloc[survivor]}",
            )
        if action[survivor] != "exclude":
            reasons[survivor].append(
                f"retained as the freshest observation of {instrument_id}"
            )

    # ---- 8. liquidity / spread penalties --------------------------------
    for i in np.flatnonzero(flags["wide_spread"].to_numpy()):
        i = int(i)
        if action[i] == "exclude":
            continue
        penalty[i] *= config.penalty_wide_spread
        escalate(i, "downweight", "bid/ask width far above the peer median")
    for i in np.flatnonzero(flags["illiquid"].to_numpy()):
        i = int(i)
        if action[i] == "exclude":
            continue
        penalty[i] *= config.penalty_illiquid
        escalate(
            i,
            "downweight",
            f"liquidity_score {frame['liquidity_score'].iloc[i]:.2f} at or below "
            f"{validation_config.illiquid_threshold:.2f}",
        )

    # ---- 9. non-fatal advisory findings ---------------------------------
    advisory = {
        "unexpected_quote_unit": "quote_unit differs from the documented convention",
        "unexpected_currency": "currency differs from the dominant currency",
        "unexpected_day_count": "day_count differs from ACT/365F",
        "unexpected_coupon": "coupon_rate supplied for a non-bond instrument (ignored)",
        "bad_settlement_days": "settlement_days outside [0, 10]",
        "bad_liquidity": "liquidity_score outside [0, 1]; clipped",
        "zero_spread": "degenerate bid/ask (zero width)",
        "maturity_date_mismatch": "maturity_date inconsistent with maturity_years "
        "(maturity_years is authoritative)",
    }
    for flag, reason in advisory.items():
        for i in np.flatnonzero(flags[flag].to_numpy()):
            i = int(i)
            if action[i] == "exclude":
                continue
            if flag in ("zero_spread", "bad_liquidity"):
                escalate(i, "downweight", reason)
            else:
                if reason not in reasons[i]:
                    reasons[i].append(reason)

    # ---- 10. statistical weights ----------------------------------------
    liquidity = np.clip(
        np.nan_to_num(frame["liquidity_score"].to_numpy(dtype=float), nan=0.5),
        config.liquidity_floor,
        1.0,
    )
    half_spread_native = 0.5 * np.abs(ask - bid)
    duration = np.array([_duration_proxy(m, t) for m, t in zip(maturity, itype)])
    with np.errstate(divide="ignore", invalid="ignore"):
        half_spread_bp = np.where(
            itype == BOND,
            half_spread_native / np.maximum(np.abs(quote) * duration, 1.0e-9) * 1.0e4,
            half_spread_native * 100.0,
        )
    half_spread_bp = np.where(
        np.isfinite(half_spread_bp) & (half_spread_bp > 0.0),
        half_spread_bp,
        config.fallback_half_spread_bp,
    )
    sigma_quote_bp = np.clip(half_spread_bp, config.sigma_floor_bp, config.sigma_cap_bp)
    sigma_quote_bp = sigma_quote_bp / np.sqrt(liquidity)
    sigma_bp = np.sqrt(np.square(sigma_quote_bp) + config.model_error_bp**2)
    raw_weight = penalty / np.square(sigma_bp)

    usable = np.array([a != "exclude" for a in action])
    if usable.sum() == 0:
        raise MarketDataError(
            "every observation was rejected by validation; no curve can be built. "
            "Check instrument_type, maturity_years, quote_value and timestamp columns."
        )
    reference = float(np.median(raw_weight[usable]))
    if not np.isfinite(reference) or reference <= 0:
        reference = 1.0
    weight = np.clip(raw_weight / reference, *config.weight_clip)
    weight = np.where(usable, weight, 0.0)

    # ---- 11. build the instrument list ----------------------------------
    instruments: list[Instrument] = []
    for i in range(n):
        if not usable[i]:
            continue
        freq_raw = frame["payment_frequency"].iloc[i]
        frequency = int(freq_raw) if np.isfinite(freq_raw) else 1
        if itype[i] == OIS_SWAP:
            frequency = annual_frequency_for_swap(float(maturity[i]))
        coupon = frame["coupon_rate"].iloc[i]
        instruments.append(
            Instrument(
                obs_id=str(frame["obs_id"].iloc[i]),
                instrument_id=str(frame["instrument_id"].iloc[i]),
                instrument_type=str(itype[i]),
                maturity_years=float(maturity[i]),
                coupon_rate=None if not np.isfinite(coupon) else float(coupon),
                payment_frequency=frequency,
                quote=float(quote[i]),
                half_spread=float(
                    half_spread_native[i]
                    if np.isfinite(half_spread_native[i]) and half_spread_native[i] > 0
                    else 0.0
                ),
                liquidity_score=float(liquidity[i]),
                weight=float(weight[i]),
                source=str(frame["source"].iloc[i]),
                timestamp=str(frame["timestamp"].iloc[i]),
                quality_factor=float(penalty[i]),
                sigma_quote_bp=float(sigma_quote_bp[i]),
                notes=tuple(reasons[i]),
            )
        )
    instruments.sort(key=lambda x: (x.maturity_years, x.instrument_id))

    audit = pd.DataFrame(
        {
            "obs_id": frame["obs_id"].astype(str).to_numpy(),
            "instrument_id": frame["instrument_id"].astype(str).to_numpy(),
            "action": action,
            "normalized_quote": quote,
            "weight": weight,
            "reason": [
                "; ".join(r) if r else "passed all validation checks" for r in reasons
            ],
            "instrument_type": itype,
            "maturity_years": maturity,
            "raw_quote": frame["quote_value"].to_numpy(dtype=float),
            "normalized_bid": bid,
            "normalized_ask": ask,
            "quality_factor": penalty,
            "source": frame["source"].astype(str).to_numpy(),
            "timestamp": frame["timestamp"].astype(str).to_numpy(),
        }
    )

    summary = {name: int((action == name).sum()) for name in ACTIONS}
    findings = [f"{name}: {count} observation(s)" for name, count in summary.items()]
    return CleaningResult(
        instruments=instruments, audit=audit, findings=findings, summary=summary
    )


def apply_exclusions(
    result: CleaningResult, obs_ids: dict[str, str]
) -> CleaningResult:
    """Return a copy of ``result`` with additional observations excluded.

    ``obs_ids`` maps ``obs_id`` to the reason for the exclusion.  Used by the
    robust outlier screen, which can only run once a preliminary curve exists.
    """
    if not obs_ids:
        return result
    audit = result.audit.copy()
    mask = audit["obs_id"].isin(obs_ids.keys())
    audit.loc[mask, "action"] = "exclude"
    audit.loc[mask, "weight"] = 0.0
    audit.loc[mask, "reason"] = [
        f"{existing}; {obs_ids[obs]}" if existing else obs_ids[obs]
        for existing, obs in zip(audit.loc[mask, "reason"], audit.loc[mask, "obs_id"])
    ]
    instruments = [i for i in result.instruments if i.obs_id not in obs_ids]
    summary = {name: int((audit["action"] == name).sum()) for name in ACTIONS}
    findings = [f"{name}: {count} observation(s)" for name, count in summary.items()]
    return CleaningResult(
        instruments=instruments, audit=audit, findings=findings, summary=summary
    )


def estimate_model_error(
    instruments: list[Instrument],
    residuals_bp: np.ndarray,
    config: CleaningConfig | None = None,
    minimum_sample: int = 5,
) -> dict[str, float]:
    """Robust per-type dispersion of repricing residuals, in basis points.

    A two-way market measures how tightly a *quote* can be transacted, not how
    tightly a single discount curve can reprice it.  Coupon bonds in particular
    trade with idiosyncratic spreads that no OIS-consistent curve can absorb, so
    their bid/ask width badly overstates the precision with which they pin the
    curve.  Estimating the residual dispersion per instrument type and adding it
    to the quote uncertainty in quadrature is a standard variance-component
    correction and it is what stops bond noise from dragging the curve around.
    """
    config = config or CleaningConfig()
    out: dict[str, float] = {}
    residuals_bp = np.asarray(residuals_bp, dtype=float)
    for name in (DEPOSIT, OIS_SWAP, BOND):
        mask = np.array([i.instrument_type == name for i in instruments])
        values = residuals_bp[mask]
        values = values[np.isfinite(values)]
        if values.size < minimum_sample:
            out[name] = config.model_error_bp
            continue
        scale = 1.4826 * float(np.median(np.abs(values - np.median(values))))
        out[name] = float(np.clip(scale, config.min_model_error_bp, config.max_model_error_bp))
    return out


def reweight_instruments(
    instruments: list[Instrument],
    model_error_bp: dict[str, float],
    config: CleaningConfig | None = None,
) -> list[Instrument]:
    """Rebuild calibration weights with an empirically estimated model error."""
    config = config or CleaningConfig()
    sigma = np.array(
        [
            np.sqrt(
                inst.sigma_quote_bp**2
                + model_error_bp.get(inst.instrument_type, config.model_error_bp) ** 2
            )
            for inst in instruments
        ],
        dtype=float,
    )
    raw = np.array([inst.quality_factor for inst in instruments], dtype=float) / np.square(sigma)
    reference = float(np.median(raw)) if raw.size else 1.0
    if not np.isfinite(reference) or reference <= 0:
        reference = 1.0
    weights = np.clip(raw / reference, *config.weight_clip)
    return [inst.with_weight(float(w)) for inst, w in zip(instruments, weights)]


def audit_with_weights(audit: pd.DataFrame, instruments: list[Instrument]) -> pd.DataFrame:
    """Refresh the audit weight column from the current instrument list."""
    lookup = {inst.obs_id: inst.weight for inst in instruments}
    updated = audit.copy()
    updated["weight"] = [
        float(lookup.get(obs_id, 0.0)) for obs_id in updated["obs_id"].astype(str)
    ]
    return updated
