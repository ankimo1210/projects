"""Health Planet OAuth contract using synthetic files and offline HTTP doubles."""

import json
import os
import stat
import traceback
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
from health.auth import AuthError
from health.healthplanet_auth import HealthPlanetAuth

SECRET = "synthetic-" + "client-secret"
CODE = "synthetic-" + "copied-code"
TOKEN = "synthetic-" + "access-token"


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, *, data, timeout, allow_redirects):
        self.calls.append((url, data, timeout, allow_redirects))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Real HTTP is forbidden in Health Planet auth tests")

    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    monkeypatch.delenv("HEALTHPLANET_CLIENT_ID", raising=False)
    monkeypatch.delenv("HEALTHPLANET_CLIENT_SECRET", raising=False)


def make_auth(tmp_path, session=None, clock=lambda: 1000.0, **kwargs):
    return HealthPlanetAuth(
        "synthetic-client",
        SECRET,
        tmp_path / "data",
        session=FakeSession() if session is None else session,
        clock=clock,
        **kwargs,
    )


def assert_redacted(error, capsys):
    rendered = "".join(traceback.format_exception(error.value))
    output = capsys.readouterr()
    for value in (SECRET, CODE, TOKEN):
        assert value not in rendered
        assert value not in output.out + output.err
    assert error.value.__cause__ is None


def test_begin_has_only_documented_parameters_and_fresh_private_pending(tmp_path):
    now = [1000.0]
    auth = make_auth(tmp_path, clock=lambda: now[0])
    url = urlsplit(auth.begin_auth())
    assert (url.scheme, url.netloc, url.path) == ("https", "www.healthplanet.jp", "/oauth/auth")
    assert parse_qs(url.query) == {
        "client_id": ["synthetic-client"],
        "redirect_uri": ["https://www.healthplanet.jp/success.html"],
        "scope": ["innerscan,sphygmomanometer,pedometer"],
        "response_type": ["code"],
    }
    assert auth.pending_path == tmp_path / "data/healthplanet/oauth_pending.json"
    assert json.loads(auth.pending_path.read_text()) == {"created_at": 1000.0}
    now[0] = 1010.0
    auth.begin_auth()
    assert json.loads(auth.pending_path.read_text()) == {"created_at": 1010.0}
    assert auth.session.calls == []


def test_exchange_form_persists_minimal_tokens_and_cannot_replay(tmp_path):
    session = FakeSession(
        FakeResponse(
            {
                "access_token": TOKEN,
                "expires_in": 3600,
                "refresh_token": "do-not-store",
                "unknown": SECRET,
            }
        )
    )
    auth = make_auth(tmp_path, session)
    auth.begin_auth()
    assert auth.complete_auth(CODE) is None
    assert session.calls == [
        (
            "https://www.healthplanet.jp/oauth/token",
            {
                "client_id": "synthetic-client",
                "client_secret": SECRET,
                "redirect_uri": "https://www.healthplanet.jp/success.html",
                "code": CODE,
                "grant_type": "authorization_code",
            },
            30,
            False,
        )
    ]
    assert auth.tokens_path == tmp_path / "data/healthplanet/tokens.json"
    assert json.loads(auth.tokens_path.read_text()) == {
        "access_token": TOKEN,
        "expires_at": 4600.0,
    }
    assert not auth.pending_path.exists()
    assert {
        p.relative_to(tmp_path / "data").as_posix()
        for p in (tmp_path / "data").rglob("*")
        if p.is_file()
    } == {"healthplanet/tokens.json"}
    assert make_auth(tmp_path).access_token() == TOKEN
    with pytest.raises(AuthError):
        auth.complete_auth(CODE)
    assert len(session.calls) == 1


def test_begin_and_code_file_can_use_separate_auth_instances(tmp_path):
    make_auth(tmp_path).begin_auth()
    code_path = tmp_path / "synthetic-code.txt"
    code_path.write_text(CODE + "\n")
    session = FakeSession(FakeResponse({"access_token": TOKEN}))
    resumed = make_auth(tmp_path, session, clock=lambda: 1001.0)
    resumed.complete_auth(code_path.read_text().strip())
    assert make_auth(tmp_path).access_token() == TOKEN
    assert not resumed.pending_path.exists()
    assert len(session.calls) == 1


def test_custom_registered_redirect_is_used_for_both_steps(tmp_path):
    session = FakeSession(FakeResponse({"access_token": TOKEN}))
    auth = make_auth(tmp_path, session, redirect_uri="https://localhost")
    assert parse_qs(urlsplit(auth.begin_auth()).query)["redirect_uri"] == ["https://localhost"]
    auth.complete_auth(CODE)
    assert session.calls[0][1]["redirect_uri"] == "https://localhost"


@pytest.mark.parametrize(
    "age,valid", [(0, True), (599.999, True), (600, False), (601, False), (-1, False)]
)
def test_pending_ttl_and_future_timestamp(tmp_path, age, valid):
    now = [1000.0]
    session = FakeSession(FakeResponse({"access_token": TOKEN}))
    auth = make_auth(tmp_path, session, clock=lambda: now[0])
    auth.begin_auth()
    now[0] += age
    if valid:
        auth.complete_auth(CODE)
    else:
        with pytest.raises(AuthError):
            auth.complete_auth(CODE)
    assert len(session.calls) == int(valid)
    assert not auth.pending_path.exists()


@pytest.mark.parametrize(
    "body",
    [
        None,
        b"not-json",
        b"\xff",
        b"[]",
        b"null",
        b"{}",
        b'{"created_at": true}',
        b'{"created_at": "1000"}',
        b'{"created_at": NaN}',
        b'{"created_at": Infinity}',
    ],
)
def test_missing_or_malformed_pending_fails_without_http_and_is_removed(tmp_path, body):
    auth = make_auth(tmp_path)
    if body is not None:
        auth.pending_path.parent.mkdir(parents=True)
        auth.pending_path.write_bytes(body)
    with pytest.raises(AuthError):
        auth.complete_auth(CODE)
    assert auth.session.calls == []
    assert not auth.pending_path.exists()


@pytest.mark.parametrize("code", [None, "", " ", "bad\ncode", "bad\x00code", 123])
def test_invalid_code_is_rejected_and_consumes_pending(tmp_path, code):
    auth = make_auth(tmp_path)
    auth.begin_auth()
    with pytest.raises(AuthError):
        auth.complete_auth(code)
    assert auth.session.calls == []
    assert not auth.pending_path.exists()


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "not an object",
        {},
        {"access_token": None},
        {"access_token": 123},
        {"access_token": True},
        {"access_token": ""},
        {"access_token": " "},
        {"access_token": "a\nb"},
        {"access_token": "a\x00b"},
        {"access_token": "非ASCII"},
        {"access_token": TOKEN, "error": SECRET},
        ValueError(SECRET + CODE + TOKEN),
    ],
)
def test_invalid_token_response_is_redacted_and_not_saved(tmp_path, payload, capsys):
    auth = make_auth(tmp_path, FakeSession(FakeResponse(payload)))
    auth.begin_auth()
    with pytest.raises(AuthError) as error:
        auth.complete_auth(CODE)
    assert_redacted(error, capsys)
    assert not auth.pending_path.exists()
    assert not auth.tokens_path.exists()


@pytest.mark.parametrize(
    "expires_in",
    [
        None,
        True,
        False,
        0,
        -1,
        "",
        "invalid",
        "NaN",
        "Infinity",
        float("nan"),
        float("inf"),
        [],
        {},
        10**400,
    ],
)
def test_invalid_expires_in_does_not_install_token(tmp_path, expires_in):
    auth = make_auth(
        tmp_path,
        FakeSession(
            FakeResponse(
                {
                    "access_token": TOKEN,
                    "expires_in": expires_in,
                }
            )
        ),
    )
    auth.begin_auth()
    with pytest.raises(AuthError):
        auth.complete_auth(CODE)
    assert not auth.tokens_path.exists()
    assert not auth.pending_path.exists()


@pytest.mark.parametrize("expires_in", [60, 60.0, "60"])
def test_access_token_expires_at_boundary_without_refresh(tmp_path, expires_in):
    now = [1000.0]
    session = FakeSession(FakeResponse({"access_token": TOKEN, "expires_in": expires_in}))
    auth = make_auth(tmp_path, session, clock=lambda: now[0])
    auth.begin_auth()
    auth.complete_auth(CODE)
    now[0] = 1059.999
    assert auth.access_token() == TOKEN
    now[0] = 1060.0
    with pytest.raises(AuthError, match="expired"):
        auth.access_token()
    assert len(session.calls) == 1


def test_absent_expiry_does_not_invent_lifetime_or_refresh(tmp_path):
    session = FakeSession(FakeResponse({"access_token": TOKEN}))
    auth = make_auth(tmp_path, session)
    auth.begin_auth()
    auth.complete_auth(CODE)
    assert json.loads(auth.tokens_path.read_text()) == {"access_token": TOKEN}
    assert make_auth(tmp_path, clock=lambda: 10**10).access_token() == TOKEN
    assert len(session.calls) == 1


@pytest.mark.parametrize("status", [201, 302, 400, 401, 429, 500])
def test_http_failure_is_fixed_and_does_not_echo_response(tmp_path, status, capsys):
    auth = make_auth(
        tmp_path,
        FakeSession(
            FakeResponse(
                {
                    "error": SECRET,
                    "error_description": CODE + TOKEN,
                },
                status,
            )
        ),
    )
    auth.begin_auth()
    with pytest.raises(AuthError) as error:
        auth.complete_auth(CODE)
    assert str(error.value) == "Health Planet token request failed"
    assert_redacted(error, capsys)
    assert not auth.pending_path.exists()
    assert not auth.tokens_path.exists()
    assert len(auth.session.calls) == 1


@pytest.mark.parametrize(
    "exception", [requests.ConnectionError, requests.Timeout, requests.TooManyRedirects]
)
def test_network_errors_hide_secret_exception_context(tmp_path, exception, capsys):
    auth = make_auth(tmp_path, FakeSession(exception(SECRET + CODE + TOKEN)))
    auth.begin_auth()
    with pytest.raises(AuthError) as error:
        auth.complete_auth(CODE)
    assert_redacted(error, capsys)
    assert not auth.pending_path.exists()
    assert len(auth.session.calls) == 1


@pytest.mark.parametrize(
    "body",
    [
        None,
        b"broken",
        b"\xff",
        b"null",
        b"[]",
        b"{}",
        b'{"access_token": 1}',
        b'{"access_token": ""}',
        b'{"access_token": "a\\rb"}',
        b'{"access_token": "valid", "expires_at": null}',
        b'{"access_token": "valid", "expires_at": true}',
        b'{"access_token": "valid", "expires_at": "1200"}',
        b'{"access_token": "valid", "expires_at": NaN}',
        b'{"access_token": "valid", "expires_at": Infinity}',
        b'{"access_token": "valid", "expires_at": 0}',
    ],
)
def test_local_token_validation_never_uses_network(tmp_path, body):
    auth = make_auth(tmp_path)
    if body is not None:
        auth.tokens_path.parent.mkdir(parents=True)
        auth.tokens_path.write_bytes(body)
    with pytest.raises(AuthError):
        auth.access_token()
    assert auth.session.calls == []


def test_failed_reauthorization_preserves_existing_token(tmp_path):
    auth = make_auth(
        tmp_path,
        FakeSession(
            FakeResponse({"access_token": TOKEN}),
            FakeResponse({"access_token": ""}),
        ),
    )
    auth.begin_auth()
    auth.complete_auth(CODE)
    original = auth.tokens_path.read_bytes()
    auth.begin_auth()
    with pytest.raises(AuthError):
        auth.complete_auth(CODE)
    assert auth.tokens_path.read_bytes() == original
    assert auth.access_token() == TOKEN


def test_files_are_private_under_permissive_umask_and_on_replacement(tmp_path):
    auth = make_auth(tmp_path, FakeSession(FakeResponse({"access_token": TOKEN})))
    previous = os.umask(0)
    try:
        auth.begin_auth()
        assert stat.S_IMODE(auth.pending_path.stat().st_mode) == 0o600
        for directory in (tmp_path / "data", tmp_path / "data/healthplanet"):
            assert stat.S_IMODE(directory.stat().st_mode) == 0o700
        auth.tokens_path.write_text("old")
        auth.tokens_path.chmod(0o666)
        auth.complete_auth(CODE)
    finally:
        os.umask(previous)
    assert stat.S_IMODE(auth.tokens_path.stat().st_mode) == 0o600
    assert not list(auth.tokens_path.parent.glob(".write-*"))


def test_from_env_explicit_path_parses_quotes_without_mutating_environment(tmp_path, capsys):
    env_path = tmp_path / "synthetic.env"
    env_path.write_text(
        "# synthetic credentials\nexport HEALTHPLANET_CLIENT_ID='synthetic-client'\n"
        f'HEALTHPLANET_CLIENT_SECRET="{SECRET}" # comment\n'
    )
    auth = HealthPlanetAuth.from_env(tmp_path / "data", env_path)
    assert auth.client_id == "synthetic-client"
    assert auth.client_secret == SECRET
    assert auth.tokens_path == tmp_path / "data/healthplanet/tokens.json"
    assert "HEALTHPLANET_CLIENT_SECRET" not in os.environ
    assert capsys.readouterr() == ("", "")


def test_from_env_defaults_to_main_data_root_parent_and_env_takes_precedence(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        f"HEALTHPLANET_CLIENT_ID=file-client\nHEALTHPLANET_CLIENT_SECRET={SECRET}\n"
    )
    monkeypatch.setenv("HEALTHPLANET_CLIENT_ID", "environment-client")
    auth = HealthPlanetAuth.from_env(tmp_path / "data")
    assert auth.client_id == "environment-client"
    assert auth.client_secret == SECRET


def test_from_env_works_without_env_file_and_does_not_expand_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("HEALTHPLANET_CLIENT_ID", "environment-client")
    monkeypatch.setenv("HEALTHPLANET_CLIENT_SECRET", SECRET)
    assert HealthPlanetAuth.from_env(tmp_path / "data").client_secret == SECRET
    monkeypatch.delenv("HEALTHPLANET_CLIENT_SECRET")
    (tmp_path / ".env").write_text("HEALTHPLANET_CLIENT_SECRET='${DO_NOT_EXPAND}'\n")
    assert HealthPlanetAuth.from_env(tmp_path / "data").client_secret == "${DO_NOT_EXPAND}"


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"HEALTHPLANET_CLIENT_ID=only-id",
        b"\xff",
        f"HEALTHPLANET_CLIENT_SECRET={SECRET}".encode(),
    ],
)
def test_bad_environment_raises_fixed_error_without_values(tmp_path, content, capsys):
    env_path = tmp_path / "synthetic.env"
    env_path.write_bytes(content)
    with pytest.raises(AuthError) as error:
        HealthPlanetAuth.from_env(tmp_path / "data", env_path)
    assert_redacted(error, capsys)


def test_explicit_missing_env_file_is_redacted(tmp_path, capsys):
    with pytest.raises(AuthError) as error:
        HealthPlanetAuth.from_env(tmp_path / "data", tmp_path / SECRET)
    assert_redacted(error, capsys)


def test_failed_token_write_is_redacted_cleans_pending_and_retains_old_token(
    tmp_path, monkeypatch, capsys
):
    from health import healthplanet_auth

    auth = make_auth(tmp_path, FakeSession(FakeResponse({"access_token": TOKEN})))
    auth.begin_auth()
    auth.tokens_path.write_text('{"access_token": "old-token"}')

    def fail_write(*args, **kwargs):
        raise OSError(SECRET + CODE + TOKEN)

    monkeypatch.setattr(healthplanet_auth, "atomic_private_write", fail_write)
    with pytest.raises(AuthError) as error:
        auth.complete_auth(CODE)
    assert_redacted(error, capsys)
    assert not auth.pending_path.exists()
    assert auth.access_token() == "old-token"
