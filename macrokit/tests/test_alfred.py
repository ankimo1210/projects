import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest

from macrokit.catalog import Indicator
from macrokit.sources.alfred import AlfredAdapter

FIXTURES = Path(__file__).parent / "fixtures"

INDICATOR = Indicator(
    name="us_core_pce",
    country="US",
    block="prices",
    title_ja="コア PCE デフレーター",
    source="alfred",
    source_ref={"series_id": "PCEPILFE"},
    freq="M",
    unit="index_2017_100",
    sa="sa",
    release_lag_days=30,
    vintage="alfred",
)


def _parse():
    adapter = AlfredAdapter(api_key="dummy")
    raw = (FIXTURES / "alfred_pcepilfe.json").read_bytes()
    return adapter.parse(INDICATOR, raw, ingested_at=datetime(2026, 8, 17, tzinfo=UTC))


def test_each_realtime_start_becomes_one_vintage_row():
    rows = _parse()
    january = [r for r in rows if r.period_start == date(2024, 1, 1)]
    assert len(january) > 1, "core PCE for 2024-01 was revised more than once"
    assert len({r.release_date for r in january}) == len(january)


def test_realtime_start_is_used_as_the_release_date():
    rows = _parse()
    first = min(
        (r for r in rows if r.period_start == date(2024, 1, 1)), key=lambda r: r.release_date
    )
    assert first.release_date == datetime(2024, 4, 1, tzinfo=UTC)
    assert first.value == pytest.approx(120.849)


def test_vintage_seq_is_dense_from_one_per_period():
    rows = _parse()
    january = sorted(
        (r for r in rows if r.period_start == date(2024, 1, 1)), key=lambda r: r.release_date
    )
    assert [r.vintage_seq for r in january] == list(range(1, len(january) + 1))


def test_us_rows_are_actual_vintages_not_snapshots():
    # ALFRED publishes the real release date, which is exactly what Japanese
    # sources cannot do. Mislabelling this would erase the distinction.
    assert all(r.vintage_kind == "actual" for r in _parse())


def test_period_end_is_filled_in_from_the_frequency():
    rows = _parse()
    january = next(r for r in rows if r.period_start == date(2024, 1, 1))
    assert january.period_end == date(2024, 1, 31)


def test_missing_values_are_dropped_not_stored_as_zero():
    # FRED encodes "no value" as the string ".", which float() would reject and
    # a careless parser might coerce to 0.0.
    adapter = AlfredAdapter(api_key="dummy")
    payload = json.dumps(
        {
            "observations": [
                {
                    "realtime_start": "2024-04-01",
                    "realtime_end": "9999-12-31",
                    "date": "2024-01-01",
                    "value": ".",
                },
                {
                    "realtime_start": "2024-04-01",
                    "realtime_end": "9999-12-31",
                    "date": "2024-02-01",
                    "value": "121.1",
                },
            ]
        }
    ).encode()
    rows = adapter.parse(INDICATOR, payload, ingested_at=datetime(2026, 8, 17, tzinfo=UTC))
    assert [r.period_start for r in rows] == [date(2024, 2, 1)]


def test_missing_api_key_fails_with_a_clear_message():
    adapter = AlfredAdapter(api_key=None)
    with pytest.raises(RuntimeError, match="FRED_API_KEY is not set"):
        adapter.fetch_raw(INDICATOR, date(2024, 1, 1))


def test_fetch_raw_strips_only_the_key_and_keeps_the_request_window():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"observations": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = AlfredAdapter(api_key="not-a-real-key", client=client)
    _raw, url, status = adapter.fetch_raw(INDICATOR, date(2024, 1, 1))

    assert status == 200
    # the request really did carry the key ...
    assert "api_key=not-a-real-key" in captured["url"]
    # ... but the recorded URL must not, in any form
    assert "api_key" not in url
    assert "not-a-real-key" not in url
    # ... and must still say what was asked for
    assert "series_id=PCEPILFE" in url
    assert "observation_start=2024-01-01" in url
    assert "realtime_start=1776-07-04" in url
    assert "realtime_end=9999-12-31" in url


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("FRED_API_KEY"), reason="FRED_API_KEY is not set")
def test_live_fetch_returns_multiple_vintages_for_a_revised_month():
    adapter = AlfredAdapter()
    raw, url, status = adapter.fetch_raw(INDICATOR, date(2024, 1, 1))
    assert status == 200
    assert "api.stlouisfed.org" in url
    rows = adapter.parse(INDICATOR, raw, ingested_at=datetime.now(UTC))
    january = [r for r in rows if r.period_start == date(2024, 1, 1)]
    assert len(january) > 1


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("FRED_API_KEY"), reason="FRED_API_KEY is not set")
def test_live_probe_returns_the_most_recent_vintage_date():
    # probe() is the cheap "did anything change" check that Plan 2 leans on for
    # every source; it is exercised here so it does not ship untested.
    latest_vintage = AlfredAdapter().probe(INDICATOR)
    assert latest_vintage is not None
    assert date.fromisoformat(latest_vintage) > date(2024, 1, 1)
