from datetime import UTC, date, datetime, timedelta

import pytest
from market_research.contracts import Instrument, MacroObservation, PriceBar


def sample_bar(**changes):
    instrument = Instrument("XTKS", "7203", "JPY", "Asia/Tokyo")
    end = datetime(2026, 9, 25, 6, tzinfo=UTC)
    values = dict(
        instrument=instrument,
        provider="yfinance",
        interval="1d",
        bar_start=end - timedelta(days=1),
        bar_end=end,
        available_at=end + timedelta(minutes=20),
        observed_at=end + timedelta(hours=1),
        close=100.0,
        adjustment="raw",
        revision_id="first",
    )
    values.update(changes)
    return PriceBar(**values)


def test_market_participates_in_instrument_id():
    tokyo = Instrument("XTKS", "7203", "JPY", "Asia/Tokyo")
    other = Instrument("XNAS", "7203", "USD", "America/New_York")
    assert tokyo.instrument_id != other.instrument_id
    assert tokyo.instrument_id == "XTKS:7203"


def test_price_bar_rejects_naive_available_at():
    with pytest.raises(ValueError, match="timezone-aware"):
        sample_bar(available_at=datetime(2026, 9, 25, 6))


def test_price_bar_rejects_premature_availability():
    with pytest.raises(ValueError, match="bar_end"):
        sample_bar(available_at=datetime(2026, 9, 25, 5, tzinfo=UTC))


def test_unknown_adjustment_remains_explicit():
    assert sample_bar(adjustment="unknown").adjustment == "unknown"


def test_price_bar_is_immutable_and_normalizes_utc():
    from dataclasses import FrozenInstanceError
    from zoneinfo import ZoneInfo

    bar = sample_bar(observed_at=datetime(2026, 9, 25, 16, tzinfo=ZoneInfo("Asia/Tokyo")))
    assert bar.observed_at == datetime(2026, 9, 25, 7, tzinfo=UTC)
    with pytest.raises(FrozenInstanceError):
        bar.close = 101


def test_invalid_timezone_is_rejected():
    with pytest.raises(ValueError, match="timezone"):
        Instrument("XTKS", "7203", "JPY", "NoSuch/Zone")


def test_nonpositive_close_is_rejected():
    with pytest.raises(ValueError, match="close"):
        sample_bar(close=0.0)


def test_macro_release_time_is_aware_and_keeps_vintage_kind():
    with pytest.raises(ValueError, match="timezone-aware"):
        MacroObservation("CPI", date(2026, 8, 1), datetime(2026, 9, 1), 3.0, "BLS", "v1")
    row = MacroObservation(
        "CPI", date(2026, 8, 1), datetime(2026, 9, 1, tzinfo=UTC), 3.0, "BLS", "v1", "actual"
    )
    assert row.vintage_kind == "actual"
