"""Google Health API OAuth 2.0 (authorization code + PKCE) with non-rotating
refresh-token store."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = (
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly "
    "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly "
    "https://www.googleapis.com/auth/googlehealth.sleep.readonly"
)
PENDING_TTL_SECONDS = 600  # 10 minutes; stale pending files are discarded, not reused


class AuthError(Exception):
    pass


class GoogleHealthAuth:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        data_dir: Path,
        redirect_uri: str = "http://localhost:8501/",
        session: Any = None,
        clock=time.time,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.data_dir = Path(data_dir)
        self.redirect_uri = redirect_uri
        self.session = session or requests.Session()
        self.clock = clock
        self.tokens_path = self.data_dir / "tokens.json"
        self.pending_path = self.data_dir / "oauth_pending.json"

    @classmethod
    def from_env(cls, data_dir: Path, env_path: Path | None = None) -> GoogleHealthAuth:
        load_dotenv(env_path or Path(data_dir).parent / ".env")
        cid = os.environ.get("GOOGLE_CLIENT_ID")
        secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        if not cid or not secret:
            raise AuthError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set (health/.env)")
        return cls(cid, secret, Path(data_dir))

    # -- flow ----------------------------------------------------------------
    def begin_auth(self) -> str:
        pend = self._read_pending()
        if pend is None:
            pend = {
                "verifier": secrets.token_urlsafe(64),
                "state": secrets.token_urlsafe(16),
                "created_at": self.clock(),
            }
            self._write_private(self.pending_path, pend)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(pend["verifier"].encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        return (
            AUTHORIZE_URL
            + "?"
            + urlencode(
                {
                    "response_type": "code",
                    "client_id": self.client_id,
                    "scope": SCOPES,
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                    "state": pend["state"],
                    "redirect_uri": self.redirect_uri,
                    "access_type": "offline",
                    "prompt": "consent",
                    "include_granted_scopes": "true",
                }
            )
        )

    def complete_auth(
        self,
        code: str | None,
        state: str | None,
        error: str | None = None,
        error_description: str | None = None,
    ) -> None:
        pend = self._read_pending()
        try:
            if error:
                raise AuthError(error_description or error)
            if pend is None:
                raise AuthError(
                    "no pending sign-in (expired or never started); restart from begin_auth"
                )
            if state != pend["state"]:
                raise AuthError("OAuth state mismatch")
            resp = self._post_token(
                {
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "code_verifier": pend["verifier"],
                    "redirect_uri": self.redirect_uri,
                }
            )
            if resp.status_code != 200:
                raise self._token_error(resp)
            self._store_tokens(resp.json(), existing=None)
        finally:
            # The callback is single-use: discard pending on every outcome
            # (success, denial, or mismatch) so it cannot be replayed.
            self.pending_path.unlink(missing_ok=True)

    def refresh(self) -> dict:
        tokens = self.load_tokens()
        if tokens is None:
            raise AuthError("no tokens saved; connect Google Health first")
        resp = self._post_token(
            {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": tokens["refresh_token"],
            }
        )
        if resp.status_code != 200:
            raise self._token_error(resp)
        return self._store_tokens(resp.json(), existing=tokens)

    def access_token(self) -> str:
        tokens = self.load_tokens()
        if tokens is None:
            raise AuthError("no tokens saved; connect Google Health first")
        if tokens["expires_at"] <= self.clock() + 60:
            tokens = self.refresh()
        return tokens["access_token"]

    def refresh_expires_in_days(self) -> float | None:
        tokens = self.load_tokens()
        if tokens is None or "refresh_expires_at" not in tokens:
            return None
        return (tokens["refresh_expires_at"] - self.clock()) / 86400

    # -- token endpoint --------------------------------------------------------
    def _post_token(self, data: dict) -> Any:
        # Credentials travel in the form body (never HTTP Basic auth).
        try:
            return self.session.post(TOKEN_URL, data=data, timeout=30)
        except requests.RequestException as exc:
            raise AuthError(f"token request network error: {exc}") from exc

    def _token_error(self, resp) -> AuthError:
        try:
            payload = resp.json() or {}
        except ValueError:
            payload = {}
        detail = (
            payload.get("error_description") or payload.get("error") or f"HTTP {resp.status_code}"
        )
        return AuthError(f"token request failed: {detail}")

    # -- storage ---------------------------------------------------------------
    def load_tokens(self) -> dict | None:
        if not self.tokens_path.exists():
            return None
        try:
            return json.loads(self.tokens_path.read_text())
        except json.JSONDecodeError:
            return None  # corrupt token file: behave like "not connected"

    def forget_tokens(self) -> None:
        self.tokens_path.unlink(missing_ok=True)
        self.pending_path.unlink(missing_ok=True)

    def _store_tokens(self, payload: dict, existing: dict | None) -> dict:
        existing = existing or {}
        now = self.clock()
        tokens = {
            "access_token": payload["access_token"],
            "refresh_token": payload.get("refresh_token") or existing.get("refresh_token"),
            "expires_at": now + payload.get("expires_in", 3600),
            "scope": payload.get("scope", existing.get("scope", "")),
        }
        refresh_expires_in = payload.get("refresh_token_expires_in")
        if refresh_expires_in is not None:
            tokens["refresh_expires_at"] = now + refresh_expires_in
        elif "refresh_expires_at" in existing:
            tokens["refresh_expires_at"] = existing["refresh_expires_at"]
        self._write_private(self.tokens_path, tokens)
        return tokens

    # -- pending state -----------------------------------------------------------
    def _read_pending(self) -> dict | None:
        if not self.pending_path.exists():
            return None
        try:
            pend = json.loads(self.pending_path.read_text())
            if self.clock() - pend["created_at"] >= PENDING_TTL_SECONDS:
                return None  # stale: caller regenerates rather than reusing it
        except (json.JSONDecodeError, KeyError, TypeError):
            return None  # corrupt pending file: safe to discard and regenerate
        return pend

    def _write_private(self, path: Path, obj: dict) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj))
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)  # atomic: never leave a half-written token/pending file
