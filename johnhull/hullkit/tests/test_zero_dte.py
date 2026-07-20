"""Calendar, clock, event and teacher gates for volume 22."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from hullkit import zero_dte

NY = ZoneInfo("America/New_York")


def test_session_calendar_holiday_timezone_and_settlement_are_explicit() -> None:
    session = zero_dte.TradingSession(holidays=(date(2026, 7, 3),))
    assert not session.is_trading_day(date(2026, 7, 3))
    assert not session.is_trading_day(date(2026, 7, 4))
    opening = datetime(2026, 7, 2, 9, 30, tzinfo=NY)
    assert zero_dte.trading_seconds_to_settlement(opening, date(2026, 7, 2), session) == 6.5 * 3600
    with pytest.raises(ValueError, match="timezone-aware"):
        zero_dte.trading_seconds_to_settlement(datetime(2026, 7, 2, 10), date(2026, 7, 2), session)


def test_variance_clock_is_normalized_and_u_shaped() -> None:
    session = zero_dte.TradingSession()
    opening, closing = session.bounds(date(2026, 7, 2))
    early = datetime(2026, 7, 2, 10, 0, tzinfo=NY)
    middle_start = datetime(2026, 7, 2, 12, 0, tzinfo=NY)
    middle_end = datetime(2026, 7, 2, 12, 30, tzinfo=NY)
    assert zero_dte.variance_clock_fraction(opening, session) == 0.0
    assert zero_dte.variance_clock_fraction(closing, session) == pytest.approx(1.0)
    early_mass = zero_dte.variance_clock_fraction(early, session)
    midday_mass = zero_dte.variance_clock_fraction(
        middle_end, session
    ) - zero_dte.variance_clock_fraction(middle_start, session)
    assert early_mass > midday_mass
    assert zero_dte.time_of_day_bucket(early, session) == "open"
    assert zero_dte.time_of_day_bucket(middle_start, session) == "midday"


def test_adjacent_expiry_total_variance_detects_calendar_inconsistency() -> None:
    good = zero_dte.total_variance_consistency([1 / 365, 2 / 365, 3 / 365], [0.20, 0.19, 0.18])
    assert good.ok
    bad = zero_dte.total_variance_consistency([1 / 365, 2 / 365], [0.50, 0.10])
    assert not bad.ok
    assert bad.violating_intervals == (0,)


def test_scheduled_events_and_event_split_stay_separate() -> None:
    start = datetime(2026, 7, 1, 9, 30, tzinfo=NY)
    expiry = datetime(2026, 7, 1, 16, 0, tzinfo=NY)
    events = [
        zero_dte.ScheduledJump("CPI", datetime(2026, 7, 1, 10, 0, tzinfo=NY), 0.0025),
        zero_dte.ScheduledJump("FOMC", datetime(2026, 7, 2, 14, 0, tzinfo=NY), 0.0040),
    ]
    assert zero_dte.scheduled_variance(start, expiry, events) == pytest.approx(0.0025)
    metrics = zero_dte.event_non_event_metrics(
        [1.2, 0.9, 1.0], [1.0, 1.0, 1.0], [True, False, False]
    )
    assert metrics.event_count == 1
    assert metrics.non_event_count == 2
    assert metrics.event_rmse == pytest.approx(0.2)


def test_time_of_day_jump_intensity_and_sv_jump_teacher_are_reproducible() -> None:
    session = zero_dte.TradingSession()
    timestamp = datetime(2026, 7, 2, 15, 30, tzinfo=NY)
    intensity = zero_dte.intraday_jump_intensity(
        timestamp,
        session,
        open_intensity=4.0,
        midday_intensity=1.0,
        close_intensity=5.0,
    )
    assert intensity == 5.0
    kwargs = dict(
        S0=100.0,
        K=90.0,
        r=0.0,
        step_year_fractions=[1 / (365 * 6)] * 6,
        jump_intensities=[0.0] * 6,
        v0=0.0,
        kappa=2.0,
        theta=0.0,
        vol_of_vol=0.0,
        rho=-0.5,
        n_paths=1000,
        seed=12,
    )
    first = zero_dte.sv_jump_teacher(**kwargs)
    second = zero_dte.sv_jump_teacher(**kwargs)
    np.testing.assert_array_equal(first.terminal_spot, second.terminal_spot)
    assert first.price == pytest.approx(10.0)
    assert first.delta == pytest.approx(1.0)
    assert abs(first.gamma) < 1e-8
    assert "does not identify" in zero_dte.DEALER_FLOW_CAUSALITY_NOTE
    assert set(zero_dte.RESEARCH_ONLY_MODELS) == {"pide_surrogate", "differential_ml"}
