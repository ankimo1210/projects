import base64
import json
from datetime import UTC, date, datetime

import pytest
from market_research.alfred import AlfredRequest, fetch_alfred
from market_research.estat import EstatRequest, ingest_estat
from market_research.fetch import FetchError
from market_research.storage import ResearchStore

NOW = datetime(2026, 9, 27, 12, tzinfo=UTC)


class Client:
    def __init__(self, raw):
        self.raw = raw

    def get(self, url, *, params):
        return self.raw


def estat_request():
    return EstatRequest("0000000001", "JP_TEST", "人", "annual", (("area", "00000"),))


def alfred_request():
    return AlfredRequest(
        "GDP", "GDP", date(2025, 1, 1), date(2025, 12, 31), "billions", "quarterly", "sa"
    )


def test_escaped_credential_is_absent_after_decoding_saved_estat_pages(tmp_path):
    payload = {
        "GET_STATS_DATA": {
            "RESULT": {"STATUS": 0},
            "PARAMETER": {"APP_ID": "supersecret", "supersecret": "echo"},
            "STATISTICAL_DATA": {
                "TABLE_INF": {"@id": "0000000001"},
                "RESULT_INF": {},
                "DATA_INF": {
                    "VALUE": [{"@area": "00000", "@time": "2026000000", "@unit": "人", "$": "1"}]
                },
            },
        }
    }
    raw = json.dumps(payload).replace("supersecret", "\\u0073upersecret").encode()
    with ResearchStore(tmp_path) as store:
        result = ingest_estat(
            store, estat_request(), client=Client(raw), app_id="supersecret", now=lambda: NOW
        )
        envelope = json.loads(store.read_raw(result.snapshot))
        for page in envelope["pages"]:
            decoded = json.loads(base64.b64decode(page))
            assert "supersecret" not in json.dumps(decoded)


def test_escaped_credential_is_absent_after_decoding_alfred_pages():
    payload = {
        "count": 1,
        "offset": 0,
        "observations": [
            {
                "date": "2025-01-01",
                "realtime_start": "2025-04-01",
                "realtime_end": "9999-12-31",
                "value": "100",
            }
        ],
        "api_key": "supersecret",
    }
    raw = json.dumps(payload).replace("supersecret", "\\u0073upersecret").encode()
    batch = fetch_alfred(
        alfred_request(), client=Client(raw), api_key="supersecret", now=lambda: NOW
    )
    for page in json.loads(batch.raw)["pages"]:
        decoded = json.loads(base64.b64decode(page))
        assert "supersecret" not in json.dumps(decoded)


@pytest.mark.parametrize("provider", ["alfred", "estat"])
def test_malformed_json_does_not_retain_credential_in_exception(tmp_path, provider):
    raw = b'{"APP_ID":"supersecret",'
    with ResearchStore(tmp_path) as store, pytest.raises(FetchError) as exc:
        if provider == "alfred":
            fetch_alfred(
                alfred_request(), client=Client(raw), api_key="supersecret", now=lambda: NOW
            )
        else:
            ingest_estat(
                store, estat_request(), client=Client(raw), app_id="supersecret", now=lambda: NOW
            )
    assert "supersecret" not in str(exc.value)
    assert exc.value.__context__ is None
