from urllib.parse import parse_qs, urlsplit

import pytest
from health.auth import AuthError, GoogleHealthAuth


def test_additional_readonly_scopes_are_present_in_consent_url(tmp_path):
    scope = "https://www.googleapis.com/auth/googlehealth.ecg.readonly"
    auth = GoogleHealthAuth("client", "secret", tmp_path, scopes=scope)
    assert parse_qs(urlsplit(auth.begin_auth()).query)["scope"] == [scope]


def test_write_permissions_are_rejected(tmp_path):
    with pytest.raises(AuthError, match="readonly"):
        GoogleHealthAuth(
            "client",
            "secret",
            tmp_path,
            scopes="https://www.googleapis.com/auth/googlehealth.sleep.writeonly",
        )
