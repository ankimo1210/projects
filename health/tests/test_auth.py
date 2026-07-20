import json
import stat
from urllib.parse import parse_qs, urlparse

import pytest

from health.auth import TOKEN_URL, AuthError, FitbitAuth
from tests.fakes import FakeResponse, FakeSession


def make_auth(tmp_path, session=None, clock=lambda: 1000.0):
    return FitbitAuth("CID", "SECRET", tmp_path, session=session, clock=clock)


def token_payload(n=1):
    return {"access_token": f"AT{n}", "refresh_token": f"RT{n}",
            "expires_in": 28800, "scope": "activity"}


def test_begin_auth_builds_pkce_url_and_persists_pending(tmp_path):
    auth = make_auth(tmp_path)
    url = auth.begin_auth()
    q = parse_qs(urlparse(url).query)
    assert q["response_type"] == ["code"]
    assert q["code_challenge_method"] == ["S256"]
    pend = json.loads((tmp_path / "oauth_pending.json").read_text())
    assert q["state"] == [pend["state"]]
    # second call reuses the pending verifier (the rendered link stays valid)
    assert auth.begin_auth() == url


def test_complete_auth_exchanges_code_and_saves_tokens(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload())])
    auth = make_auth(tmp_path, session=session)
    auth.begin_auth()
    pend = json.loads((tmp_path / "oauth_pending.json").read_text())
    auth.complete_auth("THECODE", pend["state"])
    call = session.calls[0]
    assert call["url"] == TOKEN_URL and call["auth"] == ("CID", "SECRET")
    assert call["data"]["code"] == "THECODE"
    assert call["data"]["code_verifier"] == pend["verifier"]
    tokens = auth.load_tokens()
    assert tokens["access_token"] == "AT1" and tokens["expires_at"] == 1000.0 + 28800
    mode = stat.S_IMODE((tmp_path / "tokens.json").stat().st_mode)
    assert mode == 0o600
    assert not (tmp_path / "oauth_pending.json").exists()


def test_complete_auth_rejects_state_mismatch(tmp_path):
    auth = make_auth(tmp_path, session=FakeSession())
    auth.begin_auth()
    with pytest.raises(AuthError):
        auth.complete_auth("C", "WRONG_STATE")


def test_refresh_rotates_tokens(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload(1)),
                           FakeResponse(200, token_payload(2))])
    auth = make_auth(tmp_path, session=session)
    auth.begin_auth()
    auth.complete_auth("C", json.loads((tmp_path / "oauth_pending.json").read_text())["state"])
    auth.refresh()
    assert session.calls[1]["data"] == {"grant_type": "refresh_token", "refresh_token": "RT1"}
    assert auth.load_tokens()["refresh_token"] == "RT2"


def test_refresh_failure_raises(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload()), FakeResponse(401, {})])
    auth = make_auth(tmp_path, session=session)
    auth.begin_auth()
    auth.complete_auth("C", json.loads((tmp_path / "oauth_pending.json").read_text())["state"])
    with pytest.raises(AuthError):
        auth.refresh()


def test_access_token_refreshes_when_expired(tmp_path):
    now = [1000.0]
    session = FakeSession([FakeResponse(200, token_payload(1)),
                           FakeResponse(200, token_payload(2))])
    auth = make_auth(tmp_path, session=session, clock=lambda: now[0])
    auth.begin_auth()
    auth.complete_auth("C", json.loads((tmp_path / "oauth_pending.json").read_text())["state"])
    assert auth.access_token() == "AT1"
    now[0] = 1000.0 + 28800  # past expiry
    assert auth.access_token() == "AT2"


def test_access_token_without_tokens_raises(tmp_path):
    with pytest.raises(AuthError):
        make_auth(tmp_path).access_token()
