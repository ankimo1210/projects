import json
from datetime import UTC, date, datetime, timedelta

import pytest
from market_research.sec import SecRequest, ingest_sec_companyfacts
from market_research.storage import ResearchStore

NOW = datetime(2026, 9, 27, 12, tzinfo=UTC)
FACTS = {
    "cik": 320193,
    "entityName": "Example Inc.",
    "facts": {
        "us-gaap": {
            "Assets": {
                "units": {
                    "USD": [
                        {
                            "end": "2025-09-27",
                            "val": 100,
                            "accn": "0000320193-25-000001",
                            "form": "10-K",
                            "filed": "2025-10-31",
                            "fy": 2025,
                            "fp": "FY",
                        },
                        {
                            "end": "2025-09-27",
                            "val": 101,
                            "accn": "0000320193-26-000001",
                            "form": "10-K",
                            "filed": "2026-09-01",
                            "fy": 2025,
                            "fp": "FY",
                        },
                        {
                            "start": "2025-07-01",
                            "end": "2025-09-27",
                            "val": 2,
                            "accn": "0000320193-25-000002",
                            "form": "10-Q",
                            "filed": "2025-11-01",
                        },
                    ],
                    "shares": [
                        {
                            "end": "2025-09-27",
                            "val": 999,
                            "accn": "0000320193-25-000001",
                            "form": "10-K",
                            "filed": "2025-10-31",
                        }
                    ],
                }
            }
        }
    },
}


class Client:
    def __init__(self, payload=FACTS):
        self.payload = payload
        self.calls = []

    def get(self, url, *, headers):
        self.calls.append((url, headers))
        return json.dumps(self.payload).encode()


def test_sec_filing_date_is_estimated_next_ny_day_and_period_is_separate(tmp_path):
    request = SecRequest(320193, "us-gaap", "Assets", "USD", "10-K")
    client = Client()
    with ResearchStore(tmp_path) as store:
        first = ingest_sec_companyfacts(
            store,
            request,
            client=client,
            user_agent="Research example@example.org",
            now=lambda: NOW,
        )
        assert client.calls[0][0].endswith("CIK0000320193.json")
        assert client.calls[0][1]["User-Agent"] == "Research example@example.org"
        assert len(first.rows) == 2
        assert first.rows[0].period_start is None
        assert first.rows[0].period_end == date(2025, 9, 27)
        assert first.rows[0].available_at == datetime(2025, 11, 1, 4, tzinfo=UTC)
        assert first.rows[0].vintage_kind == "estimated"
        before = store.fundamental_view(
            320193, "us-gaap", "Assets", "USD", "10-K", datetime(2025, 11, 1, 3, 59, tzinfo=UTC)
        )
        assert before == ()
        first_visible = store.fundamental_view(
            320193, "us-gaap", "Assets", "USD", "10-K", datetime(2025, 11, 1, 4, tzinfo=UTC)
        )
        assert first_visible[0].value == 100
        latest = store.fundamental_view(320193, "us-gaap", "Assets", "USD", "10-K", NOW)
        assert latest[0].value == 101
        assert first.snapshot.raw_hash == store.get_snapshot(first.snapshot.snapshot_id).raw_hash


def test_sec_refetch_of_same_facts_is_idempotent_across_observation_times(tmp_path):
    request = SecRequest(320193, "us-gaap", "Assets", "USD", "10-K")
    with ResearchStore(tmp_path) as store:
        first = ingest_sec_companyfacts(
            store,
            request,
            client=Client(),
            user_agent="Research example@example.org",
            now=lambda: NOW,
        )
        second = ingest_sec_companyfacts(
            store,
            request,
            client=Client(),
            user_agent="Research example@example.org",
            now=lambda: NOW + timedelta(days=1),
        )
        assert second.snapshot.snapshot_id != first.snapshot.snapshot_id
        assert (
            len(
                store.fundamental_view(
                    320193, "us-gaap", "Assets", "USD", "10-K", NOW + timedelta(days=1)
                )
            )
            == 1
        )


def test_sec_requires_identifying_user_agent_and_rejects_cik_mismatch(tmp_path):
    request = SecRequest(320193, "us-gaap", "Assets", "USD", "10-K")
    with ResearchStore(tmp_path) as store:
        with pytest.raises(ValueError, match="SEC_USER_AGENT"):
            ingest_sec_companyfacts(store, request, client=Client(), user_agent="", now=lambda: NOW)
        with pytest.raises(ValueError, match="CIK"):
            ingest_sec_companyfacts(
                store,
                request,
                client=Client({**FACTS, "cik": 1}),
                user_agent="Research example@example.org",
                now=lambda: NOW,
            )
