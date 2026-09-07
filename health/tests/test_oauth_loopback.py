import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest
from health.auth import AuthError
from health.oauth_loopback import authorize


class Auth:
    def __init__(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.redirect_uri = f"http://localhost:{port}/"
        self.ready = threading.Event()
        self.completed = []

    def begin_auth(self):
        self.ready.set()
        return "https://accounts.google.com/consent"

    def complete_auth(self, code, state, error=None, error_description=None):
        if state != "expected" or error:
            raise AuthError("invalid authorization")
        self.completed.append(code)


def test_ignores_non_callback_and_finishes_once(capsys):
    auth = Auth()
    with ThreadPoolExecutor() as pool:
        future = pool.submit(authorize, auth, open_browser=False, timeout_s=3)
        assert auth.ready.wait(1)
        with pytest.raises(HTTPError) as error:
            urlopen(auth.redirect_uri + "favicon.ico", timeout=1)
        assert error.value.code == 404
        assert not auth.completed
        response = urlopen(auth.redirect_uri + "?code=secret-code&state=expected", timeout=1)
        assert response.status == 200
        future.result(timeout=2)
    assert auth.completed == ["secret-code"]
    assert "secret-code" not in capsys.readouterr().err


def test_timeout_releases_port():
    auth = Auth()
    with pytest.raises(AuthError, match="timed out"):
        authorize(auth, open_browser=False, timeout_s=0.01)
    from urllib.parse import urlparse

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", urlparse(auth.redirect_uri).port))


def test_mismatch_is_reported_and_does_not_save_token():
    auth = Auth()
    with ThreadPoolExecutor() as pool:
        future = pool.submit(authorize, auth, open_browser=False, timeout_s=3)
        assert auth.ready.wait(1)
        with pytest.raises(HTTPError) as error:
            urlopen(auth.redirect_uri + "?code=secret&state=wrong", timeout=1)
        assert error.value.code == 400
        with pytest.raises(AuthError):
            future.result(timeout=2)
    assert not auth.completed


def test_silent_tcp_client_cannot_extend_authorization_deadline():
    from urllib.parse import urlparse

    auth = Auth()
    with ThreadPoolExecutor() as pool:
        future = pool.submit(authorize, auth, open_browser=False, timeout_s=0.1)
        assert auth.ready.wait(1)
        with socket.create_connection(("127.0.0.1", urlparse(auth.redirect_uri).port), timeout=1):
            with pytest.raises(AuthError, match="timed out"):
                future.result(timeout=0.5)
