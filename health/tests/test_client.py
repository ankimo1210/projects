"""Tests for health.client: dailyRollUp / reconcile request shapes, paging,
request budget, pacing, and the Google Health error taxonomy.

Every physical HTTP send goes through FakeSession so nothing here touches a
real network or sleeps for real time (pacing uses tests.fakes.FakeClock).
"""

from datetime import UTC, date, datetime, timedelta
from email.utils import format_datetime

import pytest
import requests
from health.auth import AuthError, GoogleHealthAuth
from health.client import (
    API,
    ApiError,
    HealthClient,
    RateLimited,
    RequestBudget,
    RequestCapExceeded,
)
from health.endpoints import CATALOG, closed_open_filter, daily_rollup_body

from tests.fakes import FakeClock, FakeResponse, FakeSession

START = date(2026, 7, 1)
END = date(2026, 7, 3)


def by_name(name: str):
    return next(m for m in CATALOG if m.name == name)


def make_auth(tmp_path, access_token="AT1", refresh_token="RT1", clock=lambda: 1000.0,
              session=None):
    """A GoogleHealthAuth with an already-stored, non-expiring token, so
    `access_token()` returns it directly without an HTTP call. `session` is
    the auth's *token-endpoint* session -- separate from the client's API
    session -- and only used when a test drives a 401 refresh."""
    auth = GoogleHealthAuth("CID", "SECRET", tmp_path, session=session or FakeSession(),
                             clock=clock)
    auth._store_tokens(
        {"access_token": access_token, "refresh_token": refresh_token, "expires_in": 3600,
         "scope": "irrelevant"},
        existing=None,
    )
    return auth


def _no_wait(_seconds):
    """Default `wait=` for tests that don't care about pacing: a same fake
    clock value every call means `_pace()` will call this every send after
    the first, but since nothing here asserts on it, a no-op keeps those
    tests focused on what they're actually checking."""


def make_client(tmp_path, api_queue, clock=lambda: 0.0, wait=_no_wait,
                 min_interval_s=0.5, auth=None):
    auth = auth or make_auth(tmp_path)
    session = FakeSession(api_queue)
    client = HealthClient(auth, session=session, clock=clock, wait=wait,
                           min_interval_s=min_interval_s)
    return client, auth


# -- daily_rollup: URL / body / headers ---------------------------------------


def test_daily_rollup_posts_url_body_and_bearer_header(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    client, _ = make_client(tmp_path, [FakeResponse(200, {"rollupDataPoints": []})])
    result = client.daily_rollup(metric, START, END, budget)
    assert result == {"rollupDataPoints": []}
    call = client.session.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == f"{API}/v4/users/me/dataTypes/steps/dataPoints:dailyRollUp"
    assert call["json"] == daily_rollup_body(START, END)
    assert call["headers"]["Authorization"] == "Bearer AT1"
    assert budget.used == 1


# -- iter_reconciled: URL / filter / page size / paging -----------------------


def test_iter_reconciled_url_and_exact_filter_and_page_size(tmp_path):
    metric = by_name("resting_hr")
    budget = RequestBudget(5)
    client, _ = make_client(tmp_path, [FakeResponse(200, {"dataPoints": [{"a": 1}]})])
    pages = list(client.iter_reconciled(metric, START, END, budget))
    assert pages == [{"dataPoints": [{"a": 1}]}]
    call = client.session.calls[0]
    assert call["method"] == "GET"
    assert call["url"] == (
        f"{API}/v4/users/me/dataTypes/daily-resting-heart-rate/dataPoints:reconcile"
    )
    assert call["params"] == {
        "filter": closed_open_filter("daily_resting_heart_rate.date", START, END),
        "pageSize": 1000,
    }
    assert "pageToken" not in call["params"]


def test_sleep_metric_sends_page_size_25(tmp_path):
    metric = by_name("sleep")
    budget = RequestBudget(5)
    client, _ = make_client(tmp_path, [FakeResponse(200, {"dataPoints": []})])
    list(client.iter_reconciled(metric, START, END, budget))
    assert client.session.calls[0]["params"]["pageSize"] == 25


def test_iter_reconciled_follows_next_page_token_through_every_page(tmp_path):
    metric = by_name("resting_hr")
    budget = RequestBudget(5)
    client, _ = make_client(tmp_path, [
        FakeResponse(200, {"dataPoints": [{"a": 1}], "nextPageToken": "TOK1"}),
        FakeResponse(200, {"dataPoints": [{"a": 2}], "nextPageToken": "TOK2"}),
        FakeResponse(200, {"dataPoints": [{"a": 3}]}),
    ])
    pages = list(client.iter_reconciled(metric, START, END, budget))
    assert len(pages) == 3
    calls = client.session.calls
    assert "pageToken" not in calls[0]["params"]
    assert calls[1]["params"]["pageToken"] == "TOK1"
    assert calls[2]["params"]["pageToken"] == "TOK2"
    # filter and pageSize are identical on every page; only pageToken changes
    for call in calls:
        assert call["params"]["filter"] == calls[0]["params"]["filter"]
        assert call["params"]["pageSize"] == calls[0]["params"]["pageSize"]


# -- request budget -------------------------------------------------------------


def test_budget_increments_once_per_physical_send_across_pages(tmp_path):
    metric = by_name("resting_hr")
    budget = RequestBudget(10)
    client, _ = make_client(tmp_path, [
        FakeResponse(200, {"dataPoints": [], "nextPageToken": "TOK1"}),
        FakeResponse(200, {"dataPoints": [], "nextPageToken": "TOK2"}),
        FakeResponse(200, {"dataPoints": []}),
    ])
    list(client.iter_reconciled(metric, START, END, budget))
    assert budget.used == 3


def test_request_cap_exceeded_before_any_send(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(0)
    client, _ = make_client(tmp_path, [])
    with pytest.raises(RequestCapExceeded):
        client.daily_rollup(metric, START, END, budget)
    assert client.session.calls == []


def test_request_cap_exceeded_mid_paging_stops_further_sends(tmp_path):
    metric = by_name("resting_hr")
    budget = RequestBudget(1)
    client, _ = make_client(tmp_path, [
        FakeResponse(200, {"dataPoints": [], "nextPageToken": "TOK1"}),
        FakeResponse(200, {"dataPoints": []}),  # never sent: cap already spent
    ])
    gen = client.iter_reconciled(metric, START, END, budget)
    next(gen)  # first page: consumes the only budget slot
    with pytest.raises(RequestCapExceeded):
        next(gen)
    assert len(client.session.calls) == 1


# -- 401 refresh / retry ---------------------------------------------------------


def test_401_refreshes_once_and_retries_counting_two_budget_uses(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    auth_session = FakeSession([FakeResponse(200, {"access_token": "AT2",
                                                     "refresh_token": "RT2",
                                                     "expires_in": 3600, "scope": "s"})])
    auth = make_auth(tmp_path, access_token="AT1", session=auth_session)
    client, _ = make_client(tmp_path, [
        FakeResponse(401, {}),
        FakeResponse(200, {"rollupDataPoints": []}),
    ], auth=auth)
    result = client.daily_rollup(metric, START, END, budget)
    assert result == {"rollupDataPoints": []}
    assert budget.used == 2
    assert client.session.calls[0]["headers"]["Authorization"] == "Bearer AT1"
    assert client.session.calls[1]["headers"]["Authorization"] == "Bearer AT2"


def test_second_401_after_retry_raises_autherror_and_still_counts_two(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    auth_session = FakeSession([FakeResponse(200, {"access_token": "AT2",
                                                     "refresh_token": "RT2",
                                                     "expires_in": 3600, "scope": "s"})])
    auth = make_auth(tmp_path, access_token="AT1", session=auth_session)
    client, _ = make_client(tmp_path, [
        FakeResponse(401, {}),
        FakeResponse(401, {}),
    ], auth=auth)
    with pytest.raises(AuthError):
        client.daily_rollup(metric, START, END, budget)
    assert budget.used == 2
    assert len(client.session.calls) == 2


# -- 403 / general API errors -----------------------------------------------------


def test_403_apierror_preserves_google_error_message(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    payload = {"error": {"code": 403, "status": "PERMISSION_DENIED",
                          "message": "User does not have sufficient permission."}}
    client, _ = make_client(tmp_path, [FakeResponse(403, payload)])
    with pytest.raises(ApiError) as exc:
        client.daily_rollup(metric, START, END, budget)
    assert exc.value.message == "User does not have sufficient permission."


def test_403_keeps_http_status_and_google_code_status_message_separate(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    # Google's canonical error code (7 == PERMISSION_DENIED) intentionally
    # differs from the HTTP status (403) here, to prove the two are stored
    # independently rather than one being derived from the other.
    payload = {"error": {"code": 7, "status": "PERMISSION_DENIED",
                          "message": "insufficient scope"}}
    client, _ = make_client(tmp_path, [FakeResponse(403, payload)])
    with pytest.raises(ApiError) as exc:
        client.daily_rollup(metric, START, END, budget)
    assert exc.value.status_code == 403
    assert exc.value.code == 7
    assert exc.value.status == "PERMISSION_DENIED"
    assert exc.value.message == "insufficient scope"


def test_error_without_google_envelope_falls_back_to_response_text(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    client, _ = make_client(
        tmp_path, [FakeResponse(500, None, text="internal server error", malformed_json=True)]
    )
    with pytest.raises(ApiError) as exc:
        client.daily_rollup(metric, START, END, budget)
    assert exc.value.status_code == 500
    assert exc.value.code is None
    assert exc.value.status is None
    assert exc.value.message == "internal server error"


# -- 429 rate limiting ------------------------------------------------------------


def test_429_numeric_retry_after(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    client, _ = make_client(
        tmp_path, [FakeResponse(429, {}, headers={"Retry-After": "120"})]
    )
    with pytest.raises(RateLimited) as exc:
        client.daily_rollup(metric, START, END, budget)
    assert exc.value.status_code == 429
    assert exc.value.retry_after_s == 120


def test_429_http_date_retry_after(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    target = datetime.now(UTC) + timedelta(seconds=90)
    client, _ = make_client(
        tmp_path, [FakeResponse(429, {}, headers={"Retry-After": format_datetime(target)})]
    )
    with pytest.raises(RateLimited) as exc:
        client.daily_rollup(metric, START, END, budget)
    # Wide tolerance: this is a real wall-clock read (see client._retry_after_s
    # docstring), not the injected monotonic clock, so exact equality would be
    # flaky under test-runner scheduling jitter.
    assert 80 <= exc.value.retry_after_s <= 95


def test_429_missing_retry_after_defaults_to_60(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    client, _ = make_client(tmp_path, [FakeResponse(429, {})])
    with pytest.raises(RateLimited) as exc:
        client.daily_rollup(metric, START, END, budget)
    assert exc.value.retry_after_s == 60


# -- network errors and malformed success bodies -----------------------------------


def test_network_error_raises_apierror(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    client, _ = make_client(tmp_path, [requests.ConnectionError("dns lookup failed")])
    with pytest.raises(ApiError) as exc:
        client.daily_rollup(metric, START, END, budget)
    assert exc.value.status_code == 0
    assert "dns lookup failed" in exc.value.message
    assert budget.used == 1  # the attempt still counted as a physical send


def test_malformed_json_on_200_raises_apierror(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    client, _ = make_client(tmp_path, [FakeResponse(200, None, malformed_json=True)])
    with pytest.raises(ApiError) as exc:
        client.daily_rollup(metric, START, END, budget)
    assert exc.value.status_code == 200


# -- pacing -----------------------------------------------------------------------


def test_first_send_never_waits(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    clock = FakeClock(start=100.0)
    client, _ = make_client(tmp_path, [FakeResponse(200, {"rollupDataPoints": []})],
                             clock=clock.now, wait=clock.sleep)
    client.daily_rollup(metric, START, END, budget)
    assert clock.waits == []


def test_consecutive_sends_are_at_least_min_interval_apart(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    clock = FakeClock(start=0.0)
    client, _ = make_client(tmp_path, [
        FakeResponse(200, {"rollupDataPoints": []}),
        FakeResponse(200, {"rollupDataPoints": []}),
    ], clock=clock.now, wait=clock.sleep, min_interval_s=0.5)
    client.daily_rollup(metric, START, END, budget)
    assert clock.waits == []  # first send: no wait yet
    client.daily_rollup(metric, START, END, budget)
    # no wall-clock time passed between the two calls (fake clock is static
    # apart from wait()), so the second send must wait the full interval
    assert clock.waits == [0.5]
    assert clock.value >= 0.5


def test_pacing_skips_wait_when_interval_already_elapsed(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    clock = FakeClock(start=0.0)
    client, _ = make_client(tmp_path, [
        FakeResponse(200, {"rollupDataPoints": []}),
        FakeResponse(200, {"rollupDataPoints": []}),
    ], clock=clock.now, wait=clock.sleep, min_interval_s=0.5)
    client.daily_rollup(metric, START, END, budget)
    clock.advance(1.0)  # simulate a full second of real work between sends
    client.daily_rollup(metric, START, END, budget)
    assert clock.waits == []  # already >= min_interval_s apart; no wait needed


def test_pacing_applies_to_every_reconcile_page(tmp_path):
    metric = by_name("resting_hr")
    budget = RequestBudget(5)
    clock = FakeClock(start=0.0)
    client, _ = make_client(tmp_path, [
        FakeResponse(200, {"dataPoints": [], "nextPageToken": "TOK1"}),
        FakeResponse(200, {"dataPoints": [], "nextPageToken": "TOK2"}),
        FakeResponse(200, {"dataPoints": []}),
    ], clock=clock.now, wait=clock.sleep, min_interval_s=0.5)
    list(client.iter_reconciled(metric, START, END, budget))
    assert clock.waits == [0.5, 0.5]  # 3 sends, 2 gaps, no real time elapsed


# -- token resolution must precede budget consumption and pacing -----------------
#
# auth.access_token() (built from headers) has to succeed before a physical
# send is even attempted -- acquiring a token is a precondition for sending,
# not itself a Health API send. If it raises (no tokens stored yet, or a
# failed proactive near-expiry refresh inside auth.py), no budget slot and no
# pacing tick may be spent, since zero HTTP requests reached the Health API.


def test_access_token_failure_leaves_budget_and_session_untouched(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    # No tokens ever stored: auth.access_token() raises AuthError immediately,
    # before client._dispatch() would otherwise consume budget/pace/send.
    auth = GoogleHealthAuth("CID", "SECRET", tmp_path, session=FakeSession(),
                             clock=lambda: 1000.0)
    client, _ = make_client(tmp_path, [], auth=auth)
    with pytest.raises(AuthError):
        client.daily_rollup(metric, START, END, budget)
    assert budget.used == 0
    assert client.session.calls == []


def test_next_send_after_access_token_failure_still_never_waits(tmp_path):
    metric = by_name("steps")
    budget = RequestBudget(5)
    auth = GoogleHealthAuth("CID", "SECRET", tmp_path, session=FakeSession(),
                             clock=lambda: 1000.0)
    clock = FakeClock(start=0.0)
    client, _ = make_client(tmp_path, [FakeResponse(200, {"rollupDataPoints": []})],
                             clock=clock.now, wait=clock.sleep, auth=auth)
    with pytest.raises(AuthError):
        client.daily_rollup(metric, START, END, budget)  # phantom attempt: no send
    # simulate completing OAuth after the failed attempt
    auth._store_tokens(
        {"access_token": "AT1", "refresh_token": "RT1", "expires_in": 3600, "scope": "s"},
        existing=None,
    )
    result = client.daily_rollup(metric, START, END, budget)  # the actual first send
    assert result == {"rollupDataPoints": []}
    assert budget.used == 1  # only the real send counted, not the phantom attempt
    assert clock.waits == []  # pacing state wasn't corrupted by the earlier failure
