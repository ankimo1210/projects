import json

import pytest

from health.auth import FitbitAuth
from health.client import FitbitClient, RateLimited
from tests.fakes import FakeResponse, FakeSession


def make_client(tmp_path, api_queue):
    auth_session = FakeSession([FakeResponse(200, {"access_token": "AT1", "refresh_token": "RT1",
                                                   "expires_in": 28800})])
    auth = FitbitAuth("CID", "SECRET", tmp_path, session=auth_session, clock=lambda: 0.0)
    auth.begin_auth()
    pend = json.loads((tmp_path / "oauth_pending.json").read_text())
    auth.complete_auth("C", pend["state"])
    return FitbitClient(auth, session=FakeSession(api_queue)), auth


def test_get_returns_json_and_tracks_budget(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(200, {"ok": 1},
                            headers={"Fitbit-Rate-Limit-Remaining": "42",
                                     "Fitbit-Rate-Limit-Reset": "1200"})])
    assert client.get("/1/user/-/profile.json") == {"ok": 1}
    assert client.remaining == 42 and client.reset_s == 1200
    call = client.session.calls[0]
    assert call["url"].endswith("/1/user/-/profile.json")
    assert call["headers"]["Authorization"] == "Bearer AT1"


def test_401_triggers_single_refresh_and_retry(tmp_path):
    client, auth = make_client(tmp_path, [FakeResponse(401, {}), FakeResponse(200, {"ok": 2})])
    auth.session.queue.append(FakeResponse(200, {"access_token": "AT2", "refresh_token": "RT2",
                                                 "expires_in": 28800}))
    assert client.get("/x.json") == {"ok": 2}
    assert client.session.calls[1]["headers"]["Authorization"] == "Bearer AT2"


def test_429_raises_rate_limited_with_reset(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(429, {}, headers={"Fitbit-Rate-Limit-Reset": "900"})])
    with pytest.raises(RateLimited) as exc:
        client.get("/x.json")
    assert exc.value.retry_after_s == 900


def test_http_error_propagates(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(500, {})])
    with pytest.raises(RuntimeError):
        client.get("/x.json")
