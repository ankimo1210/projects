"""Bounded HTTP requests with secret-free failures and no implicit redirects."""

from __future__ import annotations

import json
import math
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class FetchError(RuntimeError):
    def __init__(
        self,
        category: str,
        *,
        status: int | None = None,
        partial_raw: bytes | None = None,
        cursor: str | None = None,
    ):
        super().__init__(f"fetch failed: {category}" + (f" (HTTP {status})" if status else ""))
        self.category = category
        self.status = status
        self.partial_raw = partial_raw
        self.cursor = cursor


def parse_json_response(raw: bytes) -> dict:
    """Discard malformed source text before raising a printable error."""
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        payload = None
    if not isinstance(payload, dict):
        raise FetchError("invalid_response")
    return payload


def redact_json_response(raw: bytes, credential: str) -> tuple[dict, bytes]:
    """Remove decoded credential echoes before a JSON response is retained."""
    payload = parse_json_response(raw)

    def scrub(value):
        if isinstance(value, dict):
            return {
                key.replace(credential, "[REDACTED]"): (
                    "[REDACTED]"
                    if "".join(ch for ch in key.lower() if ch.isalnum()) in {"apikey", "appid"}
                    else scrub(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [scrub(item) for item in value]
        if isinstance(value, str):
            return value.replace(credential, "[REDACTED]")
        return value

    safe = scrub(payload)
    content = json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return safe, content.encode()


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _transport(url, headers, timeout):
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(Request(url, headers=headers), timeout=timeout) as response:
            content = response.read(32 * 1024 * 1024 + 1)
            if len(content) > 32 * 1024 * 1024:
                raise FetchError("response_too_large")
            return response.status, dict(response.headers), content
    except HTTPError as error:
        return error.code, dict(error.headers), b""


class HttpClient:
    def __init__(
        self,
        *,
        transport=_transport,
        sleep=time.sleep,
        now=lambda: datetime.now(UTC),
        attempts=3,
        timeout=10,
        max_wait=30,
    ):
        if not 1 <= attempts <= 3 or timeout <= 0 or max_wait < 0:
            raise ValueError("invalid request bounds")
        self.transport, self.sleep, self.now = transport, sleep, now
        self.attempts, self.timeout, self.max_wait = attempts, timeout, max_wait

    def get(self, url: str, *, params=None, headers=None) -> bytes:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("HTTP source must be an HTTPS URL without credentials")
        if params:
            url += ("&" if parsed.query else "?") + urlencode(params)
        category, status = "network", None
        for attempt in range(self.attempts):
            response = None
            try:
                response = self.transport(url, dict(headers or {}), self.timeout)
            except (OSError, URLError, TimeoutError):
                pass
            # Raise outside the except block, so raw URLs cannot survive in __context__.
            retry_after = None
            if response is not None:
                status, response_headers, content = response
                if 200 <= status < 300:
                    if not content or not content.strip():
                        raise FetchError("empty", status=status)
                    return content
                category = (
                    "authentication"
                    if status in (401, 403)
                    else "rate_limit"
                    if status == 429
                    else "server"
                    if status >= 500
                    else "redirect"
                    if 300 <= status < 400
                    else "not_found"
                    if status == 404
                    else "request"
                )
                if category not in {"rate_limit", "server"}:
                    raise FetchError(category, status=status)
                retry_after = {k.lower(): v for k, v in response_headers.items()}.get("retry-after")
            else:
                category, status = "network", None
            delay = float(2**attempt)
            if retry_after:
                try:
                    delay = float(retry_after)
                except ValueError:
                    try:
                        delay = max(
                            0.0, (parsedate_to_datetime(retry_after) - self.now()).total_seconds()
                        )
                    except (TypeError, ValueError):
                        delay = float(2**attempt)
            if not math.isfinite(delay) or delay < 0:
                delay = float(2**attempt)
            if delay > self.max_wait or attempt + 1 == self.attempts:
                break
            self.sleep(delay)
        raise FetchError(category, status=status)
