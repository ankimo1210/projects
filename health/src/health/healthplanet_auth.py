"""Health Planet's documented authorization-code flow with manual code entry.

The caller displays the authorization URL and obtains the copied code with
getpass. This module opens no browser or callback listener. No refresh grant,
state parameter, or PKCE extension is assumed to be supported by the provider.
"""

from __future__ import annotations

import io
import json
import math
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import dotenv_values

from health.archive import atomic_private_write
from health.auth import AuthError
from health.privacy import ensure_private_dir

AUTHORIZE_URL = "https://www.healthplanet.jp/oauth/auth"
TOKEN_URL = "https://www.healthplanet.jp/oauth/token"
DEFAULT_REDIRECT_URI = "https://www.healthplanet.jp/success.html"
SCOPES = "innerscan,sphygmomanometer,pedometer"
PENDING_TTL_SECONDS = 600

_PENDING_ERROR = "No active Health Planet sign-in; restart authorization"
_TOKEN_ERROR = "Invalid Health Planet token data; authorize again"
_CONFIG_ERROR = "HEALTHPLANET_CLIENT_ID / HEALTHPLANET_CLIENT_SECRET must be set"


def _opaque_string(value: object) -> bool:
    # Tokens become HTTP headers; reject whitespace, controls and non-ASCII.
    return isinstance(value, str) and re.fullmatch(r"[\x21-\x7e]+", value) is not None


def _timestamp(value: object, message: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AuthError(message)
    try:
        result = float(value)
    except (ValueError, OverflowError):
        raise AuthError(message) from None
    if not math.isfinite(result):
        raise AuthError(message)
    return result


class HealthPlanetAuth:
    """Store credentials below the main health data root, isolated from Google."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        data_dir: Path,
        redirect_uri: str = DEFAULT_REDIRECT_URI,
        session: requests.Session | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if any(
            not isinstance(value, str) or not value.strip() for value in (client_id, client_secret)
        ):
            raise AuthError(_CONFIG_ERROR)
        self.client_id = client_id
        self.client_secret = client_secret
        self.data_dir = Path(data_dir)
        self.redirect_uri = redirect_uri
        self.session = requests.Session() if session is None else session
        self.clock = clock
        self.tokens_path = self.data_dir / "healthplanet" / "tokens.json"
        self.pending_path = self.data_dir / "healthplanet" / "oauth_pending.json"

    @classmethod
    def from_env(cls, data_dir: Path, env_path: Path | None = None) -> HealthPlanetAuth:
        """Read an explicit env file (default: data_dir.parent/.env) and environ.

        Process environment takes precedence. Parsing neither interpolates
        credentials nor modifies the process environment or prints values.
        """
        path = Path(env_path) if env_path is not None else Path(data_dir).parent / ".env"
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            if env_path is not None:
                raise AuthError("Cannot read Health Planet environment file") from None
            content = ""
        except (OSError, UnicodeError):
            raise AuthError("Cannot read Health Planet environment file") from None
        values = dotenv_values(stream=io.StringIO(content), interpolate=False)
        client_id = os.environ.get("HEALTHPLANET_CLIENT_ID", values.get("HEALTHPLANET_CLIENT_ID"))
        secret = os.environ.get(
            "HEALTHPLANET_CLIENT_SECRET", values.get("HEALTHPLANET_CLIENT_SECRET")
        )
        if not client_id or not secret:
            raise AuthError(_CONFIG_ERROR)
        return cls(client_id, secret, Path(data_dir))

    def begin_auth(self) -> str:
        """Start a fresh ten-minute attempt and return the provider's GET URL."""
        self._write_private(self.pending_path, {"created_at": self._now()})
        return (
            AUTHORIZE_URL
            + "?"
            + urlencode(
                {
                    "client_id": self.client_id,
                    "redirect_uri": self.redirect_uri,
                    "scope": SCOPES,
                    "response_type": "code",
                }
            )
        )

    def complete_auth(self, code: str) -> None:
        """Exchange a manually copied code once; consume pending on every outcome."""
        try:
            pending = self._read_json(self.pending_path, _PENDING_ERROR)
            created_at = _timestamp(pending.get("created_at"), _PENDING_ERROR)
            if not 0 <= self._now() - created_at < PENDING_TTL_SECONDS:
                raise AuthError(_PENDING_ERROR)
            if not _opaque_string(code):
                raise AuthError("Invalid Health Planet authorization code")
            try:
                response = self.session.post(
                    TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uri": self.redirect_uri,
                        "code": code,
                        "grant_type": "authorization_code",
                    },
                    timeout=30,
                    allow_redirects=False,
                )
            except requests.RequestException:
                raise AuthError("Health Planet token request failed") from None
            if response.status_code != 200:
                # Never surface or archive token endpoint bodies or error details.
                raise AuthError("Health Planet token request failed")
            try:
                payload = response.json()
            except ValueError:
                raise AuthError(_TOKEN_ERROR) from None
            self._store_tokens(payload)
        finally:
            try:
                self.pending_path.unlink(missing_ok=True)
            except OSError:
                raise AuthError("Cannot remove Health Planet pending sign-in") from None

    def access_token(self) -> str:
        """Read and validate the local token; expiration requires authorization."""
        tokens = self._read_json(self.tokens_path, _TOKEN_ERROR)
        if not _opaque_string(tokens.get("access_token")):
            raise AuthError(_TOKEN_ERROR)
        if "expires_at" in tokens:
            expires_at = _timestamp(tokens["expires_at"], _TOKEN_ERROR)
            if expires_at <= self._now():
                raise AuthError("Health Planet access token expired; authorize again")
        return tokens["access_token"]

    def _now(self) -> float:
        return _timestamp(self.clock(), "Invalid Health Planet clock")

    def _store_tokens(self, payload: object) -> None:
        if (
            not isinstance(payload, dict)
            or "error" in payload
            or not _opaque_string(payload.get("access_token"))
        ):
            raise AuthError(_TOKEN_ERROR)
        tokens = {"access_token": payload["access_token"]}
        if "expires_in" in payload:
            value = payload["expires_in"]
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise AuthError(_TOKEN_ERROR)
            try:
                lifetime = float(value)
            except (ValueError, OverflowError):
                raise AuthError(_TOKEN_ERROR) from None
            if not math.isfinite(lifetime) or lifetime <= 0:
                raise AuthError(_TOKEN_ERROR)
            now = self._now()
            expires_at = now + lifetime
            if not math.isfinite(expires_at) or expires_at <= now:
                raise AuthError(_TOKEN_ERROR)
            tokens["expires_at"] = expires_at
        self._write_private(self.tokens_path, tokens)

    @staticmethod
    def _read_json(path: Path, message: str) -> dict:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError):
            raise AuthError(message) from None
        if not isinstance(payload, dict):
            raise AuthError(message)
        return payload

    def _write_private(self, path: Path, payload: dict) -> None:
        try:
            ensure_private_dir(self.data_dir)
            atomic_private_write(path, json.dumps(payload, allow_nan=False).encode("utf-8"))
        except (OSError, ValueError):
            raise AuthError("Cannot save Health Planet authorization data") from None
