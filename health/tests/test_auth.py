import json
import stat
from urllib.parse import parse_qs, urlparse

import pytest
import requests
from health.auth import AUTHORIZE_URL, SCOPES, TOKEN_URL, AuthError, GoogleHealthAuth

from tests.fakes import FakeResponse, FakeSession


def make_auth(tmp_path, session=None, clock=lambda: 1000.0):
    return GoogleHealthAuth("CID", "SECRET", tmp_path, session=session or FakeSession(),
                             clock=clock)


def token_payload(n=1, **extra):
    payload = {"access_token": f"AT{n}", "refresh_token": f"RT{n}", "expires_in": 3600,
               "scope": SCOPES}
    payload.update(extra)
    return payload


def pending_state(tmp_path):
    return json.loads((tmp_path / "oauth_pending.json").read_text())


def complete_with_new_pending(auth, tmp_path, code="C"):
    auth.begin_auth()
    pend = pending_state(tmp_path)
    auth.complete_auth(code, pend["state"])
    return pend


# -- authorization URL -------------------------------------------------------

def test_begin_auth_builds_google_pkce_url_with_required_params(tmp_path):
    auth = make_auth(tmp_path)
    url = auth.begin_auth()
    assert url.startswith(AUTHORIZE_URL + "?")
    q = parse_qs(urlparse(url).query)
    assert q["response_type"] == ["code"]
    assert q["client_id"] == ["CID"]
    assert q["code_challenge_method"] == ["S256"]
    assert q["access_type"] == ["offline"]
    assert q["prompt"] == ["consent"]
    assert q["include_granted_scopes"] == ["true"]
    assert q["redirect_uri"] == ["http://localhost:8501/"]
    assert "code_challenge" in q
    assert "state" in q
    scopes = set(q["scope"][0].split())
    assert scopes == {
        "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
        "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
        "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
    }
    assert "profile.readonly" not in q["scope"][0]


def test_begin_auth_second_call_reuses_unexpired_pending(tmp_path):
    now = [1000.0]
    auth = make_auth(tmp_path, clock=lambda: now[0])
    url1 = auth.begin_auth()
    now[0] += 599  # just under the 10-minute TTL
    url2 = auth.begin_auth()
    assert url1 == url2


# -- pending file storage -----------------------------------------------------

def test_begin_auth_persists_pending_state_verifier_created_at_mode_0600(tmp_path):
    now = [500.0]
    auth = make_auth(tmp_path, clock=lambda: now[0])
    url = auth.begin_auth()
    pend_path = tmp_path / "oauth_pending.json"
    pend = json.loads(pend_path.read_text())
    assert set(pend) == {"state", "verifier", "created_at"}
    assert pend["created_at"] == 500.0
    mode = stat.S_IMODE(pend_path.stat().st_mode)
    assert mode == 0o600
    q = parse_qs(urlparse(url).query)
    assert q["state"] == [pend["state"]]


def test_begin_auth_regenerates_pending_at_ttl_boundary(tmp_path):
    now = [1000.0]
    auth = make_auth(tmp_path, clock=lambda: now[0])
    url1 = auth.begin_auth()
    pend1 = pending_state(tmp_path)
    now[0] += 600  # exactly the 10-minute TTL: must not be reused
    url2 = auth.begin_auth()
    pend2 = pending_state(tmp_path)
    assert url1 != url2
    assert pend1["state"] != pend2["state"]
    assert pend2["created_at"] == 1600.0


def test_begin_auth_discards_corrupt_pending_file(tmp_path):
    auth = make_auth(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "oauth_pending.json").write_text("{not json")
    url = auth.begin_auth()
    q = parse_qs(urlparse(url).query)
    assert "state" in q
    pend = pending_state(tmp_path)
    assert "state" in pend and "verifier" in pend


# -- token exchange ------------------------------------------------------------

def test_complete_auth_sends_credentials_in_form_body_not_basic_auth(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload())])
    auth = make_auth(tmp_path, session=session)
    auth.begin_auth()
    pend = pending_state(tmp_path)
    auth.complete_auth("THECODE", pend["state"])
    call = session.calls[0]
    assert call["url"] == TOKEN_URL
    assert call["auth"] is None
    assert call["data"]["grant_type"] == "authorization_code"
    assert call["data"]["client_id"] == "CID"
    assert call["data"]["client_secret"] == "SECRET"
    assert call["data"]["code"] == "THECODE"
    assert call["data"]["code_verifier"] == pend["verifier"]


def test_complete_auth_stores_tokens_and_removes_pending(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload())])
    auth = make_auth(tmp_path, session=session)
    complete_with_new_pending(auth, tmp_path, code="THECODE")
    tokens = auth.load_tokens()
    assert tokens["access_token"] == "AT1"
    assert tokens["refresh_token"] == "RT1"
    assert tokens["expires_at"] == 1000.0 + 3600
    mode = stat.S_IMODE((tmp_path / "tokens.json").stat().st_mode)
    assert mode == 0o600
    assert not (tmp_path / "oauth_pending.json").exists()


# -- callback error handling ---------------------------------------------------

def test_complete_auth_raises_on_state_mismatch_and_clears_pending(tmp_path):
    auth = make_auth(tmp_path, session=FakeSession())
    auth.begin_auth()
    with pytest.raises(AuthError):
        auth.complete_auth("C", "WRONG_STATE")
    assert not (tmp_path / "oauth_pending.json").exists()


def test_complete_auth_raises_when_pending_file_missing(tmp_path):
    auth = make_auth(tmp_path, session=FakeSession())
    with pytest.raises(AuthError):
        auth.complete_auth("C", "S")


def test_complete_auth_raises_on_oauth_error_with_description(tmp_path):
    auth = make_auth(tmp_path, session=FakeSession())
    auth.begin_auth()
    with pytest.raises(AuthError, match="user denied access"):
        auth.complete_auth(None, None, error="access_denied",
                            error_description="user denied access")
    assert not (tmp_path / "oauth_pending.json").exists()


def test_complete_auth_callback_cannot_be_replayed(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload())])
    auth = make_auth(tmp_path, session=session)
    pend = complete_with_new_pending(auth, tmp_path, code="THECODE")
    with pytest.raises(AuthError):
        auth.complete_auth("THECODE", pend["state"])  # pending already discarded


def test_complete_auth_raises_on_invalid_grant(tmp_path):
    session = FakeSession([FakeResponse(400, {"error": "invalid_grant",
                                               "error_description": "Malformed auth code."})])
    auth = make_auth(tmp_path, session=session)
    auth.begin_auth()
    pend = pending_state(tmp_path)
    with pytest.raises(AuthError, match="Malformed auth code"):
        auth.complete_auth("BADCODE", pend["state"])
    assert not (tmp_path / "oauth_pending.json").exists()


def test_complete_auth_raises_on_network_error(tmp_path):
    session = FakeSession([requests.ConnectionError("dns lookup failed")])
    auth = make_auth(tmp_path, session=session)
    auth.begin_auth()
    pend = pending_state(tmp_path)
    with pytest.raises(AuthError):
        auth.complete_auth("C", pend["state"])
    assert not (tmp_path / "oauth_pending.json").exists()


# -- refresh --------------------------------------------------------------------

def test_refresh_preserves_refresh_token_when_response_omits_it(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload(1)),
                            FakeResponse(200, {"access_token": "AT2", "expires_in": 3600,
                                                "scope": SCOPES})])
    auth = make_auth(tmp_path, session=session)
    complete_with_new_pending(auth, tmp_path)
    auth.refresh()
    call = session.calls[1]
    assert call["data"]["grant_type"] == "refresh_token"
    assert call["data"]["refresh_token"] == "RT1"
    assert call["auth"] is None
    tokens = auth.load_tokens()
    assert tokens["access_token"] == "AT2"
    assert tokens["refresh_token"] == "RT1"  # preserved, not lost


def test_refresh_adopts_new_refresh_token_when_present(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload(1)),
                            FakeResponse(200, token_payload(2))])
    auth = make_auth(tmp_path, session=session)
    complete_with_new_pending(auth, tmp_path)
    auth.refresh()
    assert auth.load_tokens()["refresh_token"] == "RT2"


def test_refresh_token_expires_in_sets_refresh_expires_at(tmp_path):
    now = [1000.0]
    session = FakeSession([FakeResponse(200, token_payload(1, refresh_token_expires_in=15552000))])
    auth = make_auth(tmp_path, session=session, clock=lambda: now[0])
    complete_with_new_pending(auth, tmp_path)
    tokens = auth.load_tokens()
    assert tokens["refresh_expires_at"] == 1000.0 + 15552000
    assert auth.refresh_expires_in_days() == pytest.approx(180.0, rel=1e-6)


def test_refresh_preserves_existing_refresh_expires_at_when_response_omits_it(tmp_path):
    now = [1000.0]
    session = FakeSession([FakeResponse(200, token_payload(1, refresh_token_expires_in=5000.0)),
                            FakeResponse(200, token_payload(2))])  # no refresh_token_expires_in
    auth = make_auth(tmp_path, session=session, clock=lambda: now[0])
    complete_with_new_pending(auth, tmp_path)
    first_expiry = auth.load_tokens()["refresh_expires_at"]
    now[0] = 2000.0
    auth.refresh()
    assert auth.load_tokens()["refresh_expires_at"] == first_expiry


def test_refresh_expires_in_days_is_none_when_never_set(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload())])  # no refresh_token_expires_in
    auth = make_auth(tmp_path, session=session)
    complete_with_new_pending(auth, tmp_path)
    assert auth.refresh_expires_in_days() is None


def test_refresh_raises_on_invalid_grant(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload()),
                            FakeResponse(400, {"error": "invalid_grant",
                                                "error_description": "Token has been expired or revoked."})])
    auth = make_auth(tmp_path, session=session)
    complete_with_new_pending(auth, tmp_path)
    with pytest.raises(AuthError, match="expired or revoked"):
        auth.refresh()


def test_refresh_raises_on_network_error(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload()), requests.ConnectionError("boom")])
    auth = make_auth(tmp_path, session=session)
    complete_with_new_pending(auth, tmp_path)
    with pytest.raises(AuthError):
        auth.refresh()


def test_refresh_without_tokens_raises(tmp_path):
    auth = make_auth(tmp_path, session=FakeSession())
    with pytest.raises(AuthError):
        auth.refresh()


# -- access_token ------------------------------------------------------------

def test_access_token_refreshes_within_60s_of_expiry(tmp_path):
    now = [1000.0]
    session = FakeSession([FakeResponse(200, token_payload(1)),
                            FakeResponse(200, token_payload(2))])
    auth = make_auth(tmp_path, session=session, clock=lambda: now[0])
    complete_with_new_pending(auth, tmp_path)
    assert auth.access_token() == "AT1"
    now[0] = 1000.0 + 3600 - 61  # just outside the 60s refresh window
    assert auth.access_token() == "AT1"
    now[0] = 1000.0 + 3600 - 60  # exactly at the 60s boundary -> refresh
    assert auth.access_token() == "AT2"


def test_access_token_without_tokens_raises(tmp_path):
    with pytest.raises(AuthError):
        make_auth(tmp_path, session=FakeSession()).access_token()


# -- forget_tokens -------------------------------------------------------------

def test_forget_tokens_removes_tokens_and_pending_idempotently(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload())])
    auth = make_auth(tmp_path, session=session)
    complete_with_new_pending(auth, tmp_path)
    auth.begin_auth()  # leave a fresh pending file behind too
    assert (tmp_path / "tokens.json").exists()
    assert (tmp_path / "oauth_pending.json").exists()
    auth.forget_tokens()
    assert not (tmp_path / "tokens.json").exists()
    assert not (tmp_path / "oauth_pending.json").exists()
    auth.forget_tokens()  # idempotent: no error on an already-clean data dir


# -- from_env -------------------------------------------------------------------

def test_from_env_reads_google_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "ENVCID")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "ENVSECRET")
    auth = GoogleHealthAuth.from_env(tmp_path / "data", env_path=tmp_path / "missing.env")
    assert auth.client_id == "ENVCID"
    assert auth.client_secret == "ENVSECRET"


def test_from_env_raises_when_credentials_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    with pytest.raises(AuthError):
        GoogleHealthAuth.from_env(tmp_path / "data", env_path=tmp_path / "missing.env")
