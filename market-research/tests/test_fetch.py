from datetime import UTC, datetime

import pytest
from market_research.fetch import FetchError, HttpClient


def scripted(responses, waits):
    calls = []

    def transport(url, headers, timeout):
        calls.append((url, headers, timeout))
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    client = HttpClient(
        transport=transport, sleep=waits.append, now=lambda: datetime(2026, 9, 25, tzinfo=UTC)
    )
    return client, calls


@pytest.mark.parametrize(
    "status,category",
    [(401, "authentication"), (403, "authentication"), (404, "not_found"), (302, "redirect")],
)
def test_permanent_error_is_single_attempt_and_secret_free(status, category):
    client, calls = scripted([(status, {}, b"fixture-token")], [])
    with pytest.raises(FetchError) as caught:
        client.get("https://example.test/data", params={"api_key": "fixture-token"})
    assert caught.value.category == category
    assert "fixture-token" not in str(caught.value)
    assert caught.value.__context__ is None
    assert len(calls) == 1


def test_retry_after_and_timeout_are_bounded():
    waits = []
    client, calls = scripted(
        [(429, {"Retry-After": "2"}, b"no"), TimeoutError("private"), (200, {}, b"ok")], waits
    )
    assert client.get("https://example.test") == b"ok"
    assert waits == [2.0, 2.0]
    assert len(calls) == 3


def test_long_retry_after_does_not_retry_early():
    waits = []
    client, calls = scripted([(429, {"Retry-After": "600"}, b"no")], waits)
    with pytest.raises(FetchError, match="rate_limit"):
        client.get("https://example.test")
    assert len(calls) == 1 and waits == []


def test_retries_exhaust_without_original_exception_context():
    client, calls = scripted([TimeoutError("api_key=fixture-token")] * 3, [])
    with pytest.raises(FetchError) as caught:
        client.get("https://example.test")
    assert len(calls) == 3
    assert caught.value.category == "network"
    assert caught.value.__context__ is None
    assert "fixture-token" not in repr(caught.value)


def test_empty_response_is_distinct_and_is_not_retried():
    client, calls = scripted([(200, {}, b"")], [])
    with pytest.raises(FetchError, match="empty"):
        client.get("https://example.test")
    assert len(calls) == 1
