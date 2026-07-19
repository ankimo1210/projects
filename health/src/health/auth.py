"""Fitbit OAuth2 (authorization code + PKCE) with rotating-refresh token store."""
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

AUTHORIZE_URL = "https://www.fitbit.com/oauth2/authorize"
TOKEN_URL = "https://api.fitbit.com/oauth2/token"
SCOPES = ("activity heartrate sleep weight oxygen_saturation "
          "respiratory_rate temperature profile")


class AuthError(Exception):
    pass


class FitbitAuth:
    def __init__(self, client_id: str, client_secret: str, data_dir: Path,
                 redirect_uri: str = "http://localhost:8501/",
                 session: Any = None, clock=time.time):
        self.client_id = client_id
        self.client_secret = client_secret
        self.data_dir = Path(data_dir)
        self.redirect_uri = redirect_uri
        self.session = session or requests.Session()
        self.clock = clock
        self.tokens_path = self.data_dir / "tokens.json"
        self.pending_path = self.data_dir / "oauth_pending.json"

    @classmethod
    def from_env(cls, data_dir: Path, env_path: Path | None = None) -> "FitbitAuth":
        load_dotenv(env_path or Path(data_dir).parent / ".env")
        cid = os.environ.get("FITBIT_CLIENT_ID")
        secret = os.environ.get("FITBIT_CLIENT_SECRET")
        if not cid or not secret:
            raise AuthError("FITBIT_CLIENT_ID / FITBIT_CLIENT_SECRET not set (health/.env)")
        return cls(cid, secret, Path(data_dir))

    # -- flow --------------------------------------------------------------
    def begin_auth(self) -> str:
        if self.pending_path.exists():
            pend = json.loads(self.pending_path.read_text())
        else:
            pend = {"verifier": secrets.token_urlsafe(64),
                    "state": secrets.token_urlsafe(16)}
            self._write_private(self.pending_path, pend)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(pend["verifier"].encode()).digest()).rstrip(b"=").decode()
        return AUTHORIZE_URL + "?" + urlencode({
            "response_type": "code", "client_id": self.client_id, "scope": SCOPES,
            "code_challenge": challenge, "code_challenge_method": "S256",
            "state": pend["state"], "redirect_uri": self.redirect_uri})

    def complete_auth(self, code: str, state: str) -> None:
        pend = json.loads(self.pending_path.read_text())
        if state != pend["state"]:
            raise AuthError("OAuth state mismatch")
        resp = self.session.post(TOKEN_URL, auth=(self.client_id, self.client_secret),
                                 data={"grant_type": "authorization_code",
                                       "client_id": self.client_id, "code": code,
                                       "code_verifier": pend["verifier"],
                                       "redirect_uri": self.redirect_uri},
                                 timeout=30)
        if resp.status_code != 200:
            raise AuthError(f"token exchange failed: HTTP {resp.status_code}")
        self._store_tokens(resp.json())
        self.pending_path.unlink()

    def refresh(self) -> dict:
        tokens = self.load_tokens()
        if tokens is None:
            raise AuthError("no tokens saved; connect Fitbit first")
        resp = self.session.post(TOKEN_URL, auth=(self.client_id, self.client_secret),
                                 data={"grant_type": "refresh_token",
                                       "refresh_token": tokens["refresh_token"]},
                                 timeout=30)
        if resp.status_code != 200:
            raise AuthError(f"token refresh failed: HTTP {resp.status_code}")
        return self._store_tokens(resp.json())

    def access_token(self) -> str:
        tokens = self.load_tokens()
        if tokens is None:
            raise AuthError("no tokens saved; connect Fitbit first")
        if tokens["expires_at"] <= self.clock() + 60:
            tokens = self.refresh()
        return tokens["access_token"]

    # -- storage -----------------------------------------------------------
    def load_tokens(self) -> dict | None:
        if not self.tokens_path.exists():
            return None
        return json.loads(self.tokens_path.read_text())

    def _store_tokens(self, payload: dict) -> dict:
        tokens = {"access_token": payload["access_token"],
                  "refresh_token": payload["refresh_token"],
                  "expires_at": self.clock() + payload.get("expires_in", 28800),
                  "scope": payload.get("scope", "")}
        self._write_private(self.tokens_path, tokens)
        return tokens

    def _write_private(self, path: Path, obj: dict) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj))
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)  # atomic: rotating refresh tokens must never be half-written
