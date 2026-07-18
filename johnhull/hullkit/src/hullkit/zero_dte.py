"""Calendar, variance-clock and SV+jump teaching tools for 0DTE options.

The implementation makes timestamps and settlement conventions explicit before
doing any pricing.  It is intentionally synthetic and does not infer dealer
causality from prices.  PIDE and Differential-ML surrogates remain optional
research tracks and are not implemented in this torch-free package.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]

RESEARCH_ONLY_MODELS = ("pide_surrogate", "differential_ml")
DEALER_FLOW_CAUSALITY_NOTE = (
    "Dealer-flow statistics are contextual diagnostics; this pricing model does not identify "
    "or claim a causal effect of dealer positioning."
)


@dataclass(frozen=True)
class TradingSession:
    """Exchange session and cash-settlement convention."""

    timezone: str = "America/New_York"
    open_time: time = time(9, 30)
    close_time: time = time(16, 0)
    settlement_time: time = time(16, 0)
    holidays: tuple[date, ...] = ()

    def validate(self) -> ZoneInfo:
        """Resolve the timezone and reject inconsistent session times or holidays."""
        try:
            zone = ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown timezone: {self.timezone}") from exc
        if self.open_time >= self.close_time:
            raise ValueError("open_time must be before close_time")
        if len(set(self.holidays)) != len(self.holidays):
            raise ValueError("holidays must be unique")
        return zone

    def is_trading_day(self, day: date) -> bool:
        """True on weekdays that are not configured holidays."""
        self.validate()
        return day.weekday() < 5 and day not in self.holidays

    def bounds(self, day: date) -> tuple[datetime, datetime]:
        """Return timezone-aware open/close datetimes for a trading day."""

        zone = self.validate()
        if not self.is_trading_day(day):
            raise ValueError(f"{day.isoformat()} is not a trading day")
        return datetime.combine(day, self.open_time, zone), datetime.combine(
            day, self.close_time, zone
        )

    def settlement(self, day: date) -> datetime:
        """Timezone-aware settlement datetime for a trading day."""
        zone = self.validate()
        if not self.is_trading_day(day):
            raise ValueError(f"{day.isoformat()} is not a trading day")
        return datetime.combine(day, self.settlement_time, zone)


def _in_session(
    timestamp: datetime, session: TradingSession
) -> tuple[datetime, datetime, datetime]:
    zone = session.validate()
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    local = timestamp.astimezone(zone)
    opening, closing = session.bounds(local.date())
    if not opening <= local <= closing:
        raise ValueError("timestamp lies outside the trading session")
    return local, opening, closing


def trading_seconds_to_settlement(
    timestamp: datetime,
    expiry: date,
    session: TradingSession = TradingSession(),
) -> float:
    """Count open-session seconds from ``timestamp`` to expiry settlement.

    Weekends and configured holidays contribute zero time.  For a same-day
    0DTE contract this is simply the active-session time to settlement.
    """

    zone = session.validate()
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    local = timestamp.astimezone(zone)
    settlement = session.settlement(expiry)
    if local > settlement:
        raise ValueError("timestamp is after settlement")
    total = 0.0
    current = local.date()
    while current <= expiry:
        if session.is_trading_day(current):
            opening, closing = session.bounds(current)
            endpoint = min(closing, settlement) if current == expiry else closing
            startpoint = max(opening, local) if current == local.date() else opening
            if endpoint > startpoint:
                total += (endpoint - startpoint).total_seconds()
        current += timedelta(days=1)
    return total


def _clock_segments(weights: tuple[float, float, float]) -> tuple[FloatArray, FloatArray]:
    values = np.asarray(weights, dtype=float)
    if values.shape != (3,) or np.any(~np.isfinite(values)) or np.any(values <= 0.0):
        raise ValueError("clock weights must contain three positive finite values")
    # Open 15%, middle 70%, close 15% of the session.
    edges = np.asarray([0.0, 0.15, 0.85, 1.0])
    normalizer = float(np.sum(np.diff(edges) * values))
    return edges, values / normalizer


def variance_clock_fraction(
    timestamp: datetime,
    session: TradingSession = TradingSession(),
    *,
    weights: tuple[float, float, float] = (2.0, 0.5, 2.0),
) -> float:
    r"""Integrated normalized variance time :math:`\tau(t)=\int_0^t w(s)ds`.

    The result is zero at the open and one at the close even when the open and
    close receive more variance mass than midday.
    """

    local, opening, closing = _in_session(timestamp, session)
    elapsed = (local - opening).total_seconds() / (closing - opening).total_seconds()
    edges, normalized = _clock_segments(weights)
    integrated = 0.0
    for left, right, weight in zip(edges[:-1], edges[1:], normalized, strict=True):
        integrated += max(0.0, min(elapsed, right) - left) * weight
    return float(np.clip(integrated, 0.0, 1.0))


def time_of_day_bucket(
    timestamp: datetime,
    session: TradingSession = TradingSession(),
) -> str:
    """Classify an in-session timestamp as open, midday or close."""

    local, opening, closing = _in_session(timestamp, session)
    fraction = (local - opening).total_seconds() / (closing - opening).total_seconds()
    if fraction < 0.15:
        return "open"
    if fraction >= 0.85:
        return "close"
    return "midday"


def intraday_jump_intensity(
    timestamp: datetime,
    session: TradingSession = TradingSession(),
    *,
    open_intensity: float,
    midday_intensity: float,
    close_intensity: float,
) -> float:
    """Piecewise annualized jump intensity for open/midday/close."""

    intensities = {
        "open": float(open_intensity),
        "midday": float(midday_intensity),
        "close": float(close_intensity),
    }
    if any(not np.isfinite(value) or value < 0.0 for value in intensities.values()):
        raise ValueError("jump intensities must be finite and non-negative")
    return intensities[time_of_day_bucket(timestamp, session)]


@dataclass(frozen=True)
class TotalVarianceCheck:
    """Adjacent-expiry total-variance consistency result."""

    ok: bool
    total_variance: FloatArray
    forward_variance: FloatArray
    violating_intervals: tuple[int, ...]


def total_variance_consistency(
    maturities: ArrayLike,
    implied_volatilities: ArrayLike,
    *,
    tolerance: float = 1e-12,
) -> TotalVarianceCheck:
    """Check non-decreasing ``T * IV(T)^2`` across adjacent expiries."""

    times = np.asarray(maturities, dtype=float)
    vols = np.asarray(implied_volatilities, dtype=float)
    if (
        times.ndim != 1
        or times.size < 2
        or vols.shape != times.shape
        or np.any(~np.isfinite(times))
        or np.any(~np.isfinite(vols))
        or np.any(times <= 0.0)
        or np.any(np.diff(times) <= 0.0)
        or np.any(vols < 0.0)
    ):
        raise ValueError("maturities/volatilities must be aligned, finite and ordered")
    if tolerance < 0.0:
        raise ValueError("tolerance must be non-negative")
    total = times * vols * vols
    forwards = np.diff(total) / np.diff(times)
    violations = tuple(int(index) for index in np.flatnonzero(forwards < -tolerance))
    return TotalVarianceCheck(
        ok=not violations,
        total_variance=np.asarray(total),
        forward_variance=np.asarray(forwards),
        violating_intervals=violations,
    )


@dataclass(frozen=True)
class ScheduledJump:
    """Publicly scheduled event and its additive variance contribution."""

    label: str
    timestamp: datetime
    variance: float

    def validate(self) -> None:
        """Require a label, an aware timestamp, and finite non-negative variance."""
        if not self.label or self.timestamp.tzinfo is None:
            raise ValueError("scheduled jumps require a label and aware timestamp")
        if not np.isfinite(self.variance) or self.variance < 0.0:
            raise ValueError("scheduled jump variance must be finite and non-negative")


def scheduled_variance(
    start: datetime,
    expiry: datetime,
    events: tuple[ScheduledJump, ...] | list[ScheduledJump],
) -> float:
    """Sum known event variances in ``(start, expiry]``."""

    if start.tzinfo is None or expiry.tzinfo is None or expiry <= start:
        raise ValueError("start/expiry must be ordered timezone-aware timestamps")
    total = 0.0
    for event in events:
        event.validate()
        if start < event.timestamp <= expiry:
            total += event.variance
    return float(total)


@dataclass(frozen=True)
class EventSplitMetrics:
    """RMSE reported separately for event and non-event observations."""

    event_rmse: float
    non_event_rmse: float
    event_count: int
    non_event_count: int


def event_non_event_metrics(
    predicted: ArrayLike,
    observed: ArrayLike,
    event_mask: ArrayLike,
) -> EventSplitMetrics:
    """Evaluate scheduled-event and ordinary observations separately."""

    lhs = np.asarray(predicted, dtype=float)
    rhs = np.asarray(observed, dtype=float)
    mask = np.asarray(event_mask, dtype=bool)
    if lhs.ndim != 1 or rhs.shape != lhs.shape or mask.shape != lhs.shape:
        raise ValueError("predicted, observed and event_mask must be aligned vectors")
    if np.any(~np.isfinite(lhs)) or np.any(~np.isfinite(rhs)) or not mask.any() or mask.all():
        raise ValueError("both finite event and non-event samples are required")
    errors = lhs - rhs
    return EventSplitMetrics(
        event_rmse=float(np.sqrt(np.mean(errors[mask] ** 2))),
        non_event_rmse=float(np.sqrt(np.mean(errors[~mask] ** 2))),
        event_count=int(mask.sum()),
        non_event_count=int((~mask).sum()),
    )


@dataclass(frozen=True)
class SVJumpTeacherResult:
    """Reproducible terminal samples and common-random-number Greeks."""

    terminal_spot: FloatArray
    price: float
    standard_error: float
    delta: float
    gamma: float


def sv_jump_teacher(
    S0: float,
    K: float,
    r: float,
    step_year_fractions: ArrayLike,
    jump_intensities: ArrayLike,
    *,
    v0: float,
    kappa: float,
    theta: float,
    vol_of_vol: float,
    rho: float,
    jump_mean: float = -0.05,
    jump_std: float = 0.10,
    kind: str = "call",
    n_paths: int = 20_000,
    seed: int = 0,
) -> SVJumpTeacherResult:
    """Synthetic Heston-plus-scheduled-intensity jump Monte Carlo teacher.

    Jump sizes are log-normal.  The compensator
    ``lambda * (E[exp(Y)] - 1)`` keeps the discounted spot a martingale up to
    time-discretization error.  Common terminal multipliers provide low-noise
    bump Greeks without retraining or resimulation.
    """

    dt = np.asarray(step_year_fractions, dtype=float)
    intensity = np.asarray(jump_intensities, dtype=float)
    if (
        dt.ndim != 1
        or dt.size == 0
        or intensity.shape != dt.shape
        or np.any(~np.isfinite(dt))
        or np.any(dt <= 0.0)
        or np.any(~np.isfinite(intensity))
        or np.any(intensity < 0.0)
    ):
        raise ValueError("step sizes and jump intensities must be positive aligned vectors")
    scalars = (S0, K, r, v0, kappa, theta, vol_of_vol, rho, jump_mean, jump_std)
    if any(not np.isfinite(value) for value in scalars):
        raise ValueError("model parameters must be finite")
    if S0 <= 0.0 or K < 0.0 or v0 < 0.0 or kappa <= 0.0 or theta < 0.0:
        raise ValueError("spot/strike/variance/mean reversion parameters are invalid")
    if vol_of_vol < 0.0 or not -1.0 <= rho <= 1.0 or jump_std < 0.0:
        raise ValueError("volatility, correlation or jump dispersion is invalid")
    if kind not in {"call", "put"} or n_paths < 2:
        raise ValueError("kind must be call/put and n_paths must be at least two")

    rng = np.random.default_rng(seed)
    log_multiplier = np.zeros(n_paths, dtype=float)
    variance = np.full(n_paths, v0, dtype=float)
    jump_compensator = np.exp(jump_mean + 0.5 * jump_std**2) - 1.0
    correlation_scale = np.sqrt(max(0.0, 1.0 - rho * rho))
    for delta, lam in zip(dt, intensity, strict=True):
        normals = rng.standard_normal((n_paths, 3))
        variance_positive = np.maximum(variance, 0.0)
        spot_shock = rho * normals[:, 0] + correlation_scale * normals[:, 1]
        counts = rng.poisson(lam * delta, size=n_paths)
        jump_sum = counts * jump_mean + np.sqrt(counts) * jump_std * normals[:, 2]
        log_multiplier += (
            (r - lam * jump_compensator - 0.5 * variance_positive) * delta
            + np.sqrt(variance_positive * delta) * spot_shock
            + jump_sum
        )
        variance += (
            kappa * (theta - variance_positive) * delta
            + vol_of_vol * np.sqrt(variance_positive * delta) * normals[:, 0]
        )
    multiplier = np.exp(log_multiplier)
    terminal = S0 * multiplier
    discount = np.exp(-r * float(dt.sum()))

    def estimate(spot: float) -> tuple[float, FloatArray]:
        terminal_bumped = spot * multiplier
        payoff = (
            np.maximum(terminal_bumped - K, 0.0)
            if kind == "call"
            else np.maximum(K - terminal_bumped, 0.0)
        )
        discounted = discount * payoff
        return float(discounted.mean()), discounted

    price, samples = estimate(S0)
    bump = 1e-3 * S0
    up, _ = estimate(S0 + bump)
    down, _ = estimate(S0 - bump)
    return SVJumpTeacherResult(
        terminal_spot=np.asarray(terminal),
        price=price,
        standard_error=float(samples.std(ddof=1) / np.sqrt(n_paths)),
        delta=float((up - down) / (2.0 * bump)),
        gamma=float((up - 2.0 * price + down) / (bump * bump)),
    )
