"""Google Health API v4 HTTP client: request pacing, a hard request budget,
and a Google-error-aware exception taxonomy.

Only two request shapes exist for the metrics this app syncs:
`dailyRollUp` (POST, one JSON body) and `reconcile` (GET, paged). Both share
one physical-send path (`_dispatch`) so pacing, budgeting, one-shot 401
refresh/retry, and error normalization are implemented exactly once.

`API` is the Google Health API base URL. It is defined here (not imported
from `health.endpoints`) because this task's file scope is limited to
`client.py` / `tests/test_client.py` / `tests/fakes.py`; `endpoints.py` does
not currently export a base-URL constant.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import requests

from health.auth import AuthError, GoogleHealthAuth
from health.endpoints import Metric, closed_open_filter, daily_rollup_body

API = "https://health.googleapis.com"

_DEFAULT_RETRY_AFTER_S = 60


class ApiError(Exception):
    """A non-2xx Google Health API response, a network failure, or a
    malformed 200 body. `status_code` is the HTTP status (0 for a request
    that never got an HTTP response, e.g. a network error). `code` / `status`
    carry Google's `error.code` / `error.status` when the body is a Google
    error envelope; both are None otherwise (e.g. a plain-text 5xx body)."""

    def __init__(self, status_code: int, message: str, code: int | None = None,
                 status: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.status = status
        self.message = message


class RateLimited(ApiError):  # noqa: N818 -- fixed name from the task interface
    """HTTP 429. `retry_after_s` is parsed from the `Retry-After` header
    (numeric seconds or an HTTP-date), defaulting to 60 when absent."""

    def __init__(self, status_code: int, message: str, retry_after_s: int,
                 code: int | None = None, status: str | None = None):
        super().__init__(status_code, message, code=code, status=status)
        self.retry_after_s = retry_after_s


class RequestCapExceeded(Exception):  # noqa: N818 -- fixed name from the task interface
    """Raised by `RequestBudget.consume()` when the hard request cap for a
    sync run has already been reached. No HTTP request is sent for the call
    that raises this."""


@dataclass
class RequestBudget:
    """Counts physical HTTP sends to the Google Health API for one sync run.
    Every send counts, including a 401 retry's second send and every
    `reconcile` page; OAuth token-endpoint calls (inside `auth.py`) do not,
    since they are not Google Health API requests."""

    limit: int
    used: int = 0

    def consume(self) -> None:
        if self.used >= self.limit:
            raise RequestCapExceeded(
                f"request budget exhausted: {self.used}/{self.limit}")
        self.used += 1


class HealthClient:
    """Paced, budgeted client for `dailyRollUp` and `reconcile`.

    `clock`/`wait` are injected (default `time.monotonic`/`time.sleep`) so
    tests can pace without a real sleep. Only physical HTTP sends to the
    Google Health API are paced/budgeted; OAuth refresh calls made by `auth`
    are not.
    """

    def __init__(self, auth: GoogleHealthAuth, session: Any = None,
                 clock=time.monotonic, wait=time.sleep, min_interval_s: float = 0.5):
        self.auth = auth
        self.session = session or requests.Session()
        self.clock = clock
        self.wait = wait
        self.min_interval_s = min_interval_s
        self._last_sent_at: float | None = None

    def daily_rollup(self, metric: Metric, start: date, end: date,
                      budget: RequestBudget) -> dict:
        """POST .../dataTypes/{metric.data_type}/dataPoints:dailyRollUp and
        return the parsed JSON response."""
        url = f"{API}/v4/users/me/dataTypes/{metric.data_type}/dataPoints:dailyRollUp"
        body = daily_rollup_body(start, end)
        return self._request("POST", url, budget, json=body)

    def iter_reconciled(self, metric: Metric, start: date, end: date,
                         budget: RequestBudget) -> Iterator[dict]:
        """GET .../dataTypes/{metric.data_type}/dataPoints:reconcile, yielding
        each page's parsed JSON. `filter` and `pageSize` stay identical on
        every page; only `pageToken` changes, and only once a page carries
        `nextPageToken`."""
        url = f"{API}/v4/users/me/dataTypes/{metric.data_type}/dataPoints:reconcile"
        base_params = {
            "filter": closed_open_filter(metric.filter_path, start, end),
            "pageSize": metric.page_size,
        }
        page_token: str | None = None
        while True:
            params = dict(base_params)
            if page_token is not None:
                params["pageToken"] = page_token
            page = self._request("GET", url, budget, params=params)
            yield page
            page_token = page.get("nextPageToken")
            if not page_token:
                return

    # -- one physical send, with one-shot 401 refresh/retry -------------------

    def _request(self, method: str, url: str, budget: RequestBudget, **kwargs) -> dict:
        resp = self._dispatch(method, url, budget, **kwargs)
        if resp.status_code == 401:
            self.auth.refresh()  # not paced/budgeted: token endpoint, not Health API
            resp = self._dispatch(method, url, budget, **kwargs)
            if resp.status_code == 401:
                raise AuthError(
                    "Google Health API returned 401 after a token refresh and retry")
        return self._parse(resp)

    def _dispatch(self, method: str, url: str, budget: RequestBudget, **kwargs):
        # Resolving a token (and therefore any auth-internal near-expiry
        # refresh) is a precondition for attempting a send, not itself a
        # physical Health API send. It must happen -- and be allowed to
        # raise AuthError -- before budget/pace are touched, or a failed
        # token resolution burns a budget slot and a pacing tick for zero
        # HTTP traffic to the Health API.
        headers = {"Authorization": f"Bearer {self.auth.access_token()}"}
        budget.consume()  # before send: an exhausted budget sends nothing
        self._pace()
        try:
            if method == "GET":
                return self.session.get(url, headers=headers, timeout=30, **kwargs)
            return self.session.post(url, headers=headers, timeout=30, **kwargs)
        except requests.RequestException as exc:
            raise ApiError(0, f"network error calling {url}: {exc}") from exc

    def _pace(self) -> None:
        """Ensure this send is >= min_interval_s after the previous one. The
        first send never waits."""
        now = self.clock()
        if self._last_sent_at is not None:
            remaining = self.min_interval_s - (now - self._last_sent_at)
            if remaining > 0:
                self.wait(remaining)
                now = self.clock()
        self._last_sent_at = now

    # -- response -> dict or error ---------------------------------------------

    def _parse(self, resp) -> dict:
        if resp.status_code == 429:
            raise self._rate_limited(resp)
        if resp.status_code >= 400:
            raise self._api_error(resp)
        try:
            return resp.json()
        except ValueError as exc:
            raise ApiError(resp.status_code,
                            f"malformed JSON in {resp.status_code} response: {exc}") from exc

    def _api_error(self, resp) -> ApiError:
        code, status, message = self._google_error(resp)
        return ApiError(resp.status_code, message or self._fallback_message(resp),
                         code=code, status=status)

    def _rate_limited(self, resp) -> RateLimited:
        code, status, message = self._google_error(resp)
        return RateLimited(resp.status_code, message or self._fallback_message(resp),
                            self._retry_after_s(resp.headers), code=code, status=status)

    @staticmethod
    def _google_error(resp) -> tuple[int | None, str | None, str | None]:
        """Pull `error.code` / `error.status` / `error.message` out of a
        Google error JSON envelope; (None, None, None) if absent or the body
        isn't JSON at all."""
        try:
            payload = resp.json()
        except ValueError:
            return None, None, None
        err = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(err, dict):
            return None, None, None
        return err.get("code"), err.get("status"), err.get("message")

    @staticmethod
    def _fallback_message(resp) -> str:
        text = getattr(resp, "text", "") or ""
        return text or f"HTTP {resp.status_code}"

    @staticmethod
    def _retry_after_s(headers) -> int:
        """Parse `Retry-After` as numeric seconds or an HTTP-date (RFC 7231);
        60 when absent or unparsable.

        The HTTP-date branch is the client's one wall-clock read
        (`datetime.now`): pacing and the request budget only ever use the
        injected monotonic `clock`, but an HTTP-date is an absolute
        timestamp, and `HealthClient`'s constructor (fixed by the task
        interface) has no injectable wall-clock `now`. This keeps that read
        isolated to header math that never drives control flow inside a
        test loop.
        """
        raw = headers.get("Retry-After")
        if not raw:
            return _DEFAULT_RETRY_AFTER_S
        raw = raw.strip()
        try:
            return max(0, int(raw))
        except ValueError:
            pass
        try:
            target = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return _DEFAULT_RETRY_AFTER_S
        if target.tzinfo is None:
            target = target.replace(tzinfo=UTC)
        delta = (target - datetime.now(UTC)).total_seconds()
        return max(0, round(delta))
