"""Thin Fitbit Web API client: auth header, auto-refresh, rate-limit tracking."""
from __future__ import annotations

from typing import Any

import requests

from health.auth import FitbitAuth
from health.endpoints import API


class RateLimited(Exception):
    def __init__(self, retry_after_s: int):
        super().__init__(f"rate limited; retry after {retry_after_s}s")
        self.retry_after_s = retry_after_s


class FitbitClient:
    def __init__(self, auth: FitbitAuth, session: Any = None):
        self.auth = auth
        self.session = session or requests.Session()
        self.remaining: int | None = None
        self.reset_s: int | None = None

    def get(self, path: str) -> Any:
        resp = self._get(path)
        if resp.status_code == 401:
            self.auth.refresh()
            resp = self._get(path)
        if resp.status_code == 429:
            raise RateLimited(int(resp.headers.get("Fitbit-Rate-Limit-Reset", 3600)))
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str):
        resp = self.session.get(
            API + path,
            headers={"Authorization": f"Bearer {self.auth.access_token()}"},
            timeout=30)
        if "Fitbit-Rate-Limit-Remaining" in resp.headers:
            self.remaining = int(resp.headers["Fitbit-Rate-Limit-Remaining"])
            self.reset_s = int(resp.headers.get("Fitbit-Rate-Limit-Reset", 3600))
        return resp
