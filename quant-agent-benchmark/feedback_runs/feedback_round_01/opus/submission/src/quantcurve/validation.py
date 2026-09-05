"""Schema, type, range, timestamp, unit, bid/ask, duplicate and missing-data checks.

The validator is deliberately *non-destructive*: it only records what it finds.
:mod:`quantcurve.cleaning` turns the findings into keep / correct / downweight /
exclude decisions so that the audit trail and the decision logic stay separable
and independently testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from .instruments import BOND, DEPOSIT, OIS_SWAP, SUPPORTED_TYPES
from .io import LoadedMarketData, MarketDataError

__all__ = ["ValidationConfig", "ValidationReport", "validate", "parse_valuation_date"]


EXPECTED_QUOTE_TYPE = {DEPOSIT: "simple_rate", OIS_SWAP: "par_rate", BOND: "clean_price"}
EXPECTED_QUOTE_UNIT = {DEPOSIT: "PERCENT", OIS_SWAP: "PERCENT", BOND: "PRICE_POINTS"}
ALLOWED_FREQUENCIES = (1, 2, 4, 12)

#: Every boolean flag column produced by :func:`validate`.
FLAG_COLUMNS = (
    "unknown_instrument_type",
    "unparseable_number",
    "missing_quote",
    "missing_bid_ask",
    "bad_maturity",
    "forward_starting",
    "bad_frequency",
    "bad_liquidity",
    "bad_settlement_days",
    "unexpected_quote_type",
    "unexpected_quote_unit",
    "unexpected_currency",
    "unexpected_day_count",
    "missing_coupon",
    "bad_coupon",
    "unexpected_coupon",
    "bad_timestamp",
    "future_timestamp",
    "stale_timestamp",
    "crossed_market",
    "zero_spread",
    "wide_spread",
    "quote_outside_band",
    "maturity_date_mismatch",
    "suspect_unit_scale",
    "duplicate_observation",
    "illiquid",
)


@dataclass(frozen=True)
class ValidationConfig:
    """Tunable validation thresholds (all documented in ``MODEL_RISKS.md``)."""

    #: A quote whose timestamp is older than this many hours relative to the most
    #: recent timestamp in the file is treated as stale.
    max_quote_age_hours: float = 24.0
    #: Tolerance, as a fraction of the bid/ask width, before a quote counts as
    #: lying outside its own two-way market.
    quote_band_tolerance: float = 0.05
    #: Relative bid/ask width (vs. the cross-sectional median for the same
    #: instrument type) above which a market counts as unusually wide.
    wide_spread_multiple: float = 5.0
    #: Liquidity score at or below which an observation counts as illiquid.
    illiquid_threshold: float = 0.20
    #: Largest maturity accepted, in years.
    max_maturity_years: float = 100.0
    #: Absolute bound on a plausible bond coupon (decimal).
    max_coupon_rate: float = 0.50
    #: Bounds on a plausible normalised rate quote in percentage points.
    plausible_rate_percent: tuple[float, float] = (-25.0, 40.0)
    #: Bounds on a plausible normalised bond price in points per 100 face.
    plausible_price_points: tuple[float, float] = (5.0, 500.0)
    #: Tolerance in days between ``maturity_date`` and ``maturity_years``.
    maturity_date_tolerance_days: float = 5.0


@dataclass
class ValidationReport:
    """Per-row flags plus file-level findings."""

    flags: pd.DataFrame
    findings: list[str] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    latest_timestamp: datetime | None = None
    valuation_date: datetime | None = None
    #: Power-of-100 rescaling implied for each row (1.0 where the unit is fine).
    scale_factor: np.ndarray | None = None
    #: Age of each quote in hours relative to the most recent timestamp.
    age_hours: np.ndarray | None = None

    def flagged(self, name: str) -> pd.Series:
        return self.flags[name]

    def any_flag(self) -> pd.Series:
        return self.flags[list(FLAG_COLUMNS)].any(axis=1)


def parse_valuation_date(text: str) -> datetime:
    """Parse the mandatory ``--valuation-date`` argument (ISO ``YYYY-MM-DD``)."""
    if not isinstance(text, str) or not text.strip():
        raise MarketDataError("valuation date must be a non-empty ISO-8601 date")
    cleaned = text.strip()
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise MarketDataError(
            f"invalid --valuation-date {text!r}: expected ISO-8601 such as 2026-01-15"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_timestamps(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, format="ISO8601", utc=True, errors="coerce")
    return parsed


def _scaled_quote_candidates(quote: float, unit_lo: float, unit_hi: float) -> float | None:
    """Return the power-of-100 factor that moves ``quote`` into a plausible band."""
    if not np.isfinite(quote) or quote == 0.0:
        return None
    for factor in (100.0, 0.01):
        scaled = quote * factor
        if unit_lo <= abs(scaled) <= unit_hi and not (unit_lo <= abs(quote) <= unit_hi):
            return factor
    return None


def validate(
    loaded: LoadedMarketData,
    valuation_date: datetime,
    config: ValidationConfig | None = None,
) -> ValidationReport:
    """Run every documented check and return the per-row flag table."""
    config = config or ValidationConfig()
    frame = loaded.frame
    n = len(frame)
    flags = pd.DataFrame(False, index=frame.index, columns=list(FLAG_COLUMNS))
    findings: list[str] = []

    itype = frame["instrument_type"].astype(str)
    flags["unknown_instrument_type"] = ~itype.isin(SUPPORTED_TYPES)

    flags["unparseable_number"] = loaded.unparseable.any(axis=1).to_numpy()

    quote = frame["quote_value"]
    bid = frame["bid"]
    ask = frame["ask"]
    flags["missing_quote"] = quote.isna().to_numpy()
    flags["missing_bid_ask"] = (bid.isna() | ask.isna()).to_numpy()

    maturity = frame["maturity_years"]
    flags["bad_maturity"] = (
        maturity.isna()
        | ~np.isfinite(maturity.fillna(np.nan).to_numpy(dtype=float))
        | (maturity <= 0)
        | (maturity > config.max_maturity_years)
    ).to_numpy()

    start = frame["start_years"].fillna(0.0)
    flags["forward_starting"] = (start.abs() > 1.0e-9).to_numpy()

    freq = frame["payment_frequency"]
    flags["bad_frequency"] = (
        freq.isna() | ~freq.fillna(-1).isin(ALLOWED_FREQUENCIES)
    ).to_numpy()

    liq = frame["liquidity_score"]
    flags["bad_liquidity"] = (liq.isna() | (liq < 0.0) | (liq > 1.0)).to_numpy()
    flags["illiquid"] = (liq.fillna(0.0) <= config.illiquid_threshold).to_numpy()

    settle = frame["settlement_days"]
    flags["bad_settlement_days"] = (
        settle.isna() | (settle < 0) | (settle > 10)
    ).to_numpy()

    expected_qt = itype.map(EXPECTED_QUOTE_TYPE)
    flags["unexpected_quote_type"] = (
        expected_qt.notna() & (frame["quote_type"].astype(str) != expected_qt)
    ).to_numpy()
    expected_qu = itype.map(EXPECTED_QUOTE_UNIT)
    flags["unexpected_quote_unit"] = (
        expected_qu.notna() & (frame["quote_unit"].astype(str) != expected_qu)
    ).to_numpy()

    currency = frame["currency"].astype(str)
    dominant_ccy = currency.mode()
    if len(dominant_ccy):
        flags["unexpected_currency"] = (currency != dominant_ccy.iloc[0]).to_numpy()
    flags["unexpected_day_count"] = (
        frame["day_count"].astype(str).str.upper() != "ACT/365F"
    ).to_numpy()

    is_bond = (itype == BOND).to_numpy()
    coupon = frame["coupon_rate"]
    flags["missing_coupon"] = (is_bond & coupon.isna().to_numpy())
    flags["bad_coupon"] = (
        is_bond
        & coupon.notna().to_numpy()
        & (coupon.abs().fillna(0.0) > config.max_coupon_rate).to_numpy()
    )
    flags["unexpected_coupon"] = (~is_bond) & coupon.notna().to_numpy()

    stamps = _parse_timestamps(frame["timestamp"])
    flags["bad_timestamp"] = stamps.isna().to_numpy()
    latest = stamps.max() if stamps.notna().any() else None
    reference = latest if latest is not None else pd.Timestamp(valuation_date)
    horizon = pd.Timestamp(valuation_date) + timedelta(days=1)
    flags["future_timestamp"] = (stamps.notna() & (stamps > horizon)).to_numpy()
    age_hours = (reference - stamps).dt.total_seconds() / 3600.0
    flags["stale_timestamp"] = (
        stamps.notna() & (age_hours > config.max_quote_age_hours)
    ).to_numpy()

    lo = np.minimum(bid, ask)
    hi = np.maximum(bid, ask)
    width = (ask - bid).astype(float)
    flags["crossed_market"] = (bid.notna() & ask.notna() & (bid > ask)).to_numpy()
    flags["zero_spread"] = (
        bid.notna() & ask.notna() & (np.abs(width) <= 0.0)
    ).to_numpy()

    tol = config.quote_band_tolerance * np.abs(hi - lo)
    flags["quote_outside_band"] = (
        quote.notna()
        & bid.notna()
        & ask.notna()
        & ((quote < lo - tol) | (quote > hi + tol))
    ).to_numpy()

    abs_width = np.abs(width)
    wide = np.zeros(n, dtype=bool)
    for name in SUPPORTED_TYPES:
        mask = (itype == name).to_numpy()
        # ``mask.sum() >= 4`` is not enough: a type may have four rows and no
        # usable bid/ask at all, and np.nanmedian of an all-NaN slice warns and
        # returns NaN.  Require four *finite* widths before taking the median.
        finite = mask & np.isfinite(abs_width)
        if mask.sum() >= 4 and finite.sum() >= 1:
            med = float(np.median(abs_width[finite]))
            if np.isfinite(med) and med > 0:
                wide |= mask & (abs_width > config.wide_spread_multiple * med)
    flags["wide_spread"] = wide

    # maturity_date is supplied for auditability only; cross-check it.
    mdates = pd.to_datetime(frame["maturity_date"], errors="coerce", utc=True)
    implied_years = (mdates - pd.Timestamp(valuation_date)).dt.total_seconds() / (
        365.0 * 24.0 * 3600.0
    )
    tol_years = config.maturity_date_tolerance_days / 365.0
    flags["maturity_date_mismatch"] = (
        mdates.notna()
        & maturity.notna()
        & ((implied_years - maturity).abs() > tol_years)
    ).to_numpy()

    # Unit-scale suspicion.  Two independent detectors are combined: an absolute
    # plausibility band (only meaningful for bond prices, which must live near
    # par) and a local peer comparison (which works for any rate level).
    scale_factor = peer_scale_factor(frame, itype, quote)
    lo_p, hi_p = config.plausible_price_points
    for i, (t, q) in enumerate(zip(itype, quote)):
        if t != BOND or q is None or not np.isfinite(q):
            continue
        factor = _scaled_quote_candidates(float(q), lo_p, hi_p)
        if factor is not None:
            scale_factor[i] = factor
    flags["suspect_unit_scale"] = scale_factor != 1.0
    report_scale = scale_factor

    dup_mask = frame["instrument_id"].duplicated(keep=False).to_numpy()
    flags["duplicate_observation"] = dup_mask

    counts = {name: int(flags[name].sum()) for name in FLAG_COLUMNS}
    for name, value in counts.items():
        if value:
            findings.append(f"{name}: {value} observation(s)")
    if flags["unknown_instrument_type"].all():
        raise MarketDataError(
            "no supported instrument types found; expected one of "
            + ", ".join(SUPPORTED_TYPES)
        )

    return ValidationReport(
        flags=flags,
        findings=findings,
        summary=counts,
        latest_timestamp=None if latest is None else latest.to_pydatetime(),
        valuation_date=valuation_date,
        scale_factor=report_scale,
        age_hours=age_hours.to_numpy(dtype=float),
    )


def peer_scale_factor(
    frame: pd.DataFrame,
    itype: pd.Series,
    quote: pd.Series,
    neighbours: int = 6,
) -> np.ndarray:
    """Power-of-100 rescaling implied by each quote's nearest maturity peers.

    For every observation the routine builds a robust local reference -- the
    median quote of the ``neighbours`` closest *other* instruments of the same
    type -- and asks whether multiplying or dividing the quote by 100 moves it
    dramatically closer to that reference.  A local reference is used rather than
    a whole-sample one so that steeply sloped curves (where a 1M rate can be two
    orders of magnitude below a 30Y rate) are not misdiagnosed.

    Returns an array of factors: ``1.0`` where no rescaling is implied.
    """
    n = len(frame)
    factors = np.ones(n, dtype=float)
    values = quote.to_numpy(dtype=float)
    maturities = frame["maturity_years"].to_numpy(dtype=float)
    for name in SUPPORTED_TYPES:
        mask = (itype == name).to_numpy() & np.isfinite(values) & np.isfinite(maturities)
        idx = np.flatnonzero(mask)
        if idx.size < 4:
            continue
        for i in idx:
            others = idx[idx != i]
            order = np.argsort(np.abs(maturities[others] - maturities[i]), kind="stable")
            take = others[order[: min(neighbours, others.size)]]
            reference = float(np.median(values[take]))
            if not np.isfinite(reference) or abs(reference) < 1.0e-9:
                continue
            candidates = {1.0: abs(values[i] - reference)}
            for factor in (100.0, 0.01):
                candidates[factor] = abs(values[i] * factor - reference)
            best = min(candidates, key=lambda k: candidates[k])
            if best == 1.0:
                continue
            # Two conditions must hold before the documented unit is overridden:
            # the rescaled quote must be at least four times closer to the local
            # reference than the quote as given, *and* it must land materially
            # inside the local level.  The second condition is what stops a
            # steeply sloped front end -- where a 1M rate can legitimately sit far
            # below its 1Y neighbour -- from being "corrected".
            if (
                candidates[best] < 0.25 * candidates[1.0]
                and candidates[best] < 0.35 * abs(reference)
            ):
                factors[i] = best
    return factors
