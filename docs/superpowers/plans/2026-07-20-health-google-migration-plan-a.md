# Google Health API Migration — Plan A (through the probe checkpoint)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Fitbit auth/client/catalog/sync layers of `health` with Google Health API equivalents, so the user can authorize against Google and run a sync that fills the raw JSON layer — everything needed to reach the probe checkpoint.

**Architecture:** In-place rewrite of `auth.py`, `endpoints.py`, `client.py`, and `sync.py`, plus the app wiring that names the provider. `store.py` and the four data-rendering views are untouched because the store is keyed by metric name only. Typed parsers are deliberately absent: every catalog entry carries `_parse_pending`, which returns no rows, so a Plan A sync populates `raw_json` and nothing else. Plan B swaps in real parsers written against probe output and reprocesses from `raw_json` without refetching.

**Tech Stack:** Python 3.12, requests, python-dotenv, DuckDB, Streamlit, pytest. No new dependencies.

## Global Constraints

- Work in the worktree `/home/kazumasa/projects/.claude/worktrees/health-google` on branch `claude/health-google-migration`. Never switch branches or stage files in the main checkout at `/home/kazumasa/projects` — a parallel session holds uncommitted work there.
- Run tests from the `health/` directory: `cd health && uv run --no-sync pytest tests`. The workspace-root `conftest.py` imports packages absent from the slim worktree venv.
- No new runtime or test dependencies. HTTP fakes are hand-rolled in `health/tests/fakes.py`.
- Base URL is `https://health.googleapis.com`; API version segment is `/v4`.
- Authorize URL `https://accounts.google.com/o/oauth2/v2/auth`; token URL `https://oauth2.googleapis.com/token`.
- The authorization URL MUST carry `access_type=offline` and `prompt=consent`. Without the former no refresh token is issued at all.
- Google does NOT return `refresh_token` on refresh responses. Persisting `payload["refresh_token"]` unconditionally destroys the credential. The stored value must be preserved when absent.
- Access tokens last 3600 s (not Fitbit's 28800).
- Scopes, verbatim and space-separated:
  `https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly https://www.googleapis.com/auth/googlehealth.sleep.readonly https://www.googleapis.com/auth/googlehealth.profile.readonly`
- Redirect URI stays `http://localhost:8501/`.
- Testing-mode refresh tokens expire after 7 days; `REFRESH_TOKEN_TTL_DAYS = 7`.
- Env var names are `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `HEALTH_BACKFILL_START`. The Fitbit names are gone.
- `Metric.name` is the `sync_state` primary key and must be unique across `CATALOG`. It is distinct from the series names written into `daily_series` / `intraday`.
- Metric names written to the store stay identical to the Fitbit implementation so `store.py` and the views need no change.
- Every commit message ends with:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_011b3F76ZJJXGstFzyki1PF9
  ```
- Commit subjects are English, imperative, `type(health): summary` form.

## Scope boundary

**In Plan A:** `.env.example`, `auth.py`, `endpoints.py` (catalog skeleton, no parsers), `client.py`, `sync.py`, `inventory.py` field rename, app wiring (`common.py`, `main.py`, `sync_view.py`), `scripts/probe_datatypes.py`, docs.

**Deferred to Plan B (do not implement here):** typed parsers, reprocessing `raw_json` into typed tables, `KNOWN_DATA_TYPES` and the inventory page's implemented/not-implemented listing, `activity_view.py`'s `minutes_very_active` → `minutes_active` rename, `seed_demo.py` updates.

## File structure

| File | Responsibility | Change |
|---|---|---|
| `health/.env.example` | Credential template | Rewrite |
| `health/src/health/auth.py` | Google OAuth 2.0 flow + token persistence | Rewrite |
| `health/src/health/endpoints.py` | Data-type catalog, request shapes, date helpers | Rewrite (no parsers) |
| `health/src/health/client.py` | HTTP: rollup POST, paged list GET, 401/429 | Rewrite |
| `health/src/health/sync.py` | Chunking, resume, request cap | Adapt |
| `health/src/health/inventory.py` | Inventory frame | One field rename |
| `health/app/common.py` | Cached app resources | Import rename |
| `health/app/main.py` | OAuth callback + navigation | Provider wording |
| `health/app/views/sync_view.py` | Sync page | Client rename, token expiry, reconnect |
| `health/scripts/probe_datatypes.py` | Shape discovery | Create |
| `health/README.md`, `health/CLAUDE.md`, `health/pyproject.toml` | Setup docs | Provider rewrite |

---

### Task 1: Google OAuth 2.0 authentication

**Files:**
- Rewrite: `health/src/health/auth.py`
- Rewrite: `health/.env.example`
- Rewrite: `health/tests/test_auth.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `GoogleHealthAuth(client_id: str, client_secret: str, data_dir: Path, redirect_uri: str = "http://localhost:8501/", session=None, clock=time.time)`; classmethod `from_env(data_dir: Path, env_path: Path | None = None) -> GoogleHealthAuth`; methods `begin_auth() -> str`, `complete_auth(code: str, state: str) -> None`, `refresh() -> dict`, `access_token() -> str`, `load_tokens() -> dict | None`, `forget_tokens() -> None`, `refresh_expires_in_days() -> float | None`. Module constants `AUTHORIZE_URL`, `TOKEN_URL`, `SCOPES`, `REFRESH_TOKEN_TTL_DAYS`. Exception `AuthError`.

- [ ] **Step 1: Write the failing tests**

Replace the entire contents of `health/tests/test_auth.py`:

```python
import json
import stat
from urllib.parse import parse_qs, urlparse

import pytest

from health.auth import TOKEN_URL, AuthError, GoogleHealthAuth
from tests.fakes import FakeResponse, FakeSession


def make_auth(tmp_path, session=None, clock=lambda: 1000.0):
    return GoogleHealthAuth("CID", "SECRET", tmp_path, session=session, clock=clock)


def token_payload(n=1, refresh=True):
    payload = {"access_token": f"AT{n}", "expires_in": 3600, "scope": "sleep"}
    if refresh:
        payload["refresh_token"] = f"RT{n}"
    return payload


def connect(auth):
    """Drive begin_auth + complete_auth so the auth object holds tokens."""
    auth.begin_auth()
    state = json.loads((auth.data_dir / "oauth_pending.json").read_text())["state"]
    auth.complete_auth("THECODE", state)


def test_begin_auth_requests_offline_access_and_forced_consent(tmp_path):
    auth = make_auth(tmp_path)
    q = parse_qs(urlparse(auth.begin_auth()).query)
    assert q["access_type"] == ["offline"]
    assert q["prompt"] == ["consent"]
    assert q["code_challenge_method"] == ["S256"]
    assert q["redirect_uri"] == ["http://localhost:8501/"]
    assert "googlehealth.sleep.readonly" in q["scope"][0]


def test_begin_auth_persists_pending_and_is_stable_across_calls(tmp_path):
    auth = make_auth(tmp_path)
    url = auth.begin_auth()
    pend = json.loads((tmp_path / "oauth_pending.json").read_text())
    assert parse_qs(urlparse(url).query)["state"] == [pend["state"]]
    assert auth.begin_auth() == url


def test_complete_auth_posts_client_secret_in_body_and_saves_tokens(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload())])
    auth = make_auth(tmp_path, session=session)
    connect(auth)
    call = session.calls[0]
    assert call["url"] == TOKEN_URL
    assert call["data"]["client_secret"] == "SECRET"
    assert call["data"]["code"] == "THECODE"
    assert call["auth"] is None  # Google takes credentials in the body, not Basic auth
    tokens = auth.load_tokens()
    assert tokens["access_token"] == "AT1"
    assert tokens["expires_at"] == 1000.0 + 3600
    assert stat.S_IMODE((tmp_path / "tokens.json").stat().st_mode) == 0o600
    assert not (tmp_path / "oauth_pending.json").exists()


def test_complete_auth_rejects_state_mismatch(tmp_path):
    auth = make_auth(tmp_path, session=FakeSession())
    auth.begin_auth()
    with pytest.raises(AuthError):
        auth.complete_auth("C", "WRONG_STATE")


def test_refresh_preserves_stored_refresh_token_when_response_omits_it(tmp_path):
    # Google omits refresh_token on refresh; overwriting would destroy the credential.
    session = FakeSession([FakeResponse(200, token_payload(1)),
                           FakeResponse(200, token_payload(2, refresh=False))])
    auth = make_auth(tmp_path, session=session)
    connect(auth)
    auth.refresh()
    tokens = auth.load_tokens()
    assert tokens["access_token"] == "AT2"
    assert tokens["refresh_token"] == "RT1"


def test_refresh_adopts_a_new_refresh_token_when_present(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload(1)),
                           FakeResponse(200, token_payload(2))])
    auth = make_auth(tmp_path, session=session)
    connect(auth)
    auth.refresh()
    assert auth.load_tokens()["refresh_token"] == "RT2"


def test_refresh_sends_grant_and_credentials(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload(1)),
                           FakeResponse(200, token_payload(2, refresh=False))])
    auth = make_auth(tmp_path, session=session)
    connect(auth)
    auth.refresh()
    assert session.calls[1]["data"] == {
        "grant_type": "refresh_token", "client_id": "CID",
        "client_secret": "SECRET", "refresh_token": "RT1"}


def test_refresh_maps_invalid_grant_to_auth_error(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload(1)),
                           FakeResponse(400, {"error": "invalid_grant"})])
    auth = make_auth(tmp_path, session=session)
    connect(auth)
    with pytest.raises(AuthError, match="expired"):
        auth.refresh()


def test_refresh_without_tokens_raises(tmp_path):
    with pytest.raises(AuthError):
        make_auth(tmp_path).refresh()


def test_access_token_refreshes_when_expired(tmp_path):
    now = [1000.0]
    session = FakeSession([FakeResponse(200, token_payload(1)),
                           FakeResponse(200, token_payload(2, refresh=False))])
    auth = make_auth(tmp_path, session=session, clock=lambda: now[0])
    connect(auth)
    assert auth.access_token() == "AT1"
    now[0] = 1000.0 + 3600
    assert auth.access_token() == "AT2"


def test_access_token_without_tokens_raises(tmp_path):
    with pytest.raises(AuthError):
        make_auth(tmp_path).access_token()


def test_refresh_expires_in_days_counts_down_from_issue(tmp_path):
    now = [1000.0]
    session = FakeSession([FakeResponse(200, token_payload(1))])
    auth = make_auth(tmp_path, session=session, clock=lambda: now[0])
    connect(auth)
    assert auth.refresh_expires_in_days() == pytest.approx(7.0)
    now[0] = 1000.0 + 2 * 86400
    assert auth.refresh_expires_in_days() == pytest.approx(5.0)


def test_refresh_issue_time_survives_a_refresh_that_omits_the_token(tmp_path):
    now = [1000.0]
    session = FakeSession([FakeResponse(200, token_payload(1)),
                           FakeResponse(200, token_payload(2, refresh=False))])
    auth = make_auth(tmp_path, session=session, clock=lambda: now[0])
    connect(auth)
    now[0] = 1000.0 + 3 * 86400
    auth.refresh()
    assert auth.refresh_expires_in_days() == pytest.approx(4.0)


def test_forget_tokens_clears_both_files(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload(1))])
    auth = make_auth(tmp_path, session=session)
    connect(auth)
    auth.forget_tokens()
    assert auth.load_tokens() is None
    assert not (tmp_path / "oauth_pending.json").exists()
    auth.forget_tokens()  # idempotent


def test_from_env_requires_google_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    with pytest.raises(AuthError, match="GOOGLE_CLIENT_ID"):
        GoogleHealthAuth.from_env(tmp_path, env_path=tmp_path / "absent.env")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd health && uv run --no-sync pytest tests/test_auth.py -q`
Expected: collection error — `ImportError: cannot import name 'GoogleHealthAuth' from 'health.auth'`.

- [ ] **Step 3: Rewrite `health/src/health/auth.py`**

Replace the entire file:

```python
"""Google OAuth2 (authorization code + PKCE) for the Google Health API."""
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
    "https://www.googleapis.com/auth/googlehealth.sleep.readonly "
    "https://www.googleapis.com/auth/googlehealth.profile.readonly"
)
ACCESS_TOKEN_TTL_S = 3600
REFRESH_TOKEN_TTL_DAYS = 7  # Testing-mode publishing status expires refresh tokens weekly


class AuthError(Exception):
    pass


class GoogleHealthAuth:
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
    def from_env(cls, data_dir: Path, env_path: Path | None = None) -> "GoogleHealthAuth":
        load_dotenv(env_path or Path(data_dir).parent / ".env")
        cid = os.environ.get("GOOGLE_CLIENT_ID")
        secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        if not cid or not secret:
            raise AuthError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set (health/.env)")
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
            "state": pend["state"], "redirect_uri": self.redirect_uri,
            # offline is what makes Google issue a refresh token at all;
            # consent forces re-issue on repeat authorizations.
            "access_type": "offline", "prompt": "consent"})

    def complete_auth(self, code: str, state: str) -> None:
        pend = json.loads(self.pending_path.read_text())
        if state != pend["state"]:
            raise AuthError("OAuth state mismatch")
        resp = self.session.post(TOKEN_URL,
                                 data={"grant_type": "authorization_code",
                                       "client_id": self.client_id,
                                       "client_secret": self.client_secret,
                                       "code": code,
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
            raise AuthError("no tokens saved; connect Google Health first")
        resp = self.session.post(TOKEN_URL,
                                 data={"grant_type": "refresh_token",
                                       "client_id": self.client_id,
                                       "client_secret": self.client_secret,
                                       "refresh_token": tokens["refresh_token"]},
                                 timeout=30)
        if resp.status_code != 200:
            if self._error_code(resp) == "invalid_grant":
                raise AuthError(
                    "refresh token expired — Testing-mode tokens last "
                    f"{REFRESH_TOKEN_TTL_DAYS} days; reconnect Google Health")
            raise AuthError(f"token refresh failed: HTTP {resp.status_code}")
        return self._store_tokens(resp.json())

    def access_token(self) -> str:
        tokens = self.load_tokens()
        if tokens is None:
            raise AuthError("no tokens saved; connect Google Health first")
        if tokens["expires_at"] <= self.clock() + 60:
            tokens = self.refresh()
        return tokens["access_token"]

    # -- storage -----------------------------------------------------------
    def load_tokens(self) -> dict | None:
        if not self.tokens_path.exists():
            return None
        return json.loads(self.tokens_path.read_text())

    def forget_tokens(self) -> None:
        self.tokens_path.unlink(missing_ok=True)
        self.pending_path.unlink(missing_ok=True)

    def refresh_expires_in_days(self) -> float | None:
        tokens = self.load_tokens()
        if tokens is None:
            return None
        issued_at = tokens.get("refresh_issued_at", self.clock())
        return REFRESH_TOKEN_TTL_DAYS - (self.clock() - issued_at) / 86400

    @staticmethod
    def _error_code(resp: Any) -> str:
        try:
            return (resp.json() or {}).get("error", "")
        except Exception:
            return ""

    def _store_tokens(self, payload: dict) -> dict:
        existing = self.load_tokens() or {}
        if payload.get("refresh_token"):
            refresh = payload["refresh_token"]
            issued_at = self.clock()
        else:
            # Google omits refresh_token on refresh responses. Keeping the stored
            # one is mandatory: overwriting it with None destroys the credential.
            refresh = existing.get("refresh_token")
            issued_at = existing.get("refresh_issued_at", self.clock())
            if not refresh:
                raise AuthError("no refresh_token in response and none stored; "
                                "re-authorize (access_type=offline is required)")
        tokens = {"access_token": payload["access_token"],
                  "refresh_token": refresh,
                  "expires_at": self.clock() + payload.get("expires_in", ACCESS_TOKEN_TTL_S),
                  "scope": payload.get("scope", ""),
                  "refresh_issued_at": issued_at}
        self._write_private(self.tokens_path, tokens)
        return tokens

    def _write_private(self, path: Path, obj: dict) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj))
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
```

- [ ] **Step 4: Rewrite `health/.env.example`**

```
# Google Cloud OAuth client (Web application) for the Google Health API.
# console.cloud.google.com > APIs & Services > Credentials
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Optional. First date to backfill, YYYY-MM-DD. Defaults to five years ago.
HEALTH_BACKFILL_START=
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd health && uv run --no-sync pytest tests/test_auth.py -q`
Expected: 15 passed.

- [ ] **Step 6: Commit**

```bash
git add health/src/health/auth.py health/tests/test_auth.py health/.env.example
git commit -m "$(cat <<'EOF'
feat(health): Google OAuth 2.0 auth with non-rotating refresh tokens

Google omits refresh_token from refresh responses, so the stored value is
preserved rather than overwritten. Authorization requests access_type=offline
and prompt=consent, without which no refresh token is issued.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011b3F76ZJJXGstFzyki1PF9
EOF
)"
```

---

### Task 2: Data-type catalog skeleton

**Files:**
- Rewrite: `health/src/health/endpoints.py`
- Modify: `health/src/health/inventory.py` (one field rename)
- Rewrite: `health/tests/test_endpoints.py`
- Modify: `health/tests/test_inventory.py` (catalog count)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: module constants `API = "https://health.googleapis.com"`, `ROLLUP = "dailyRollUp"`, `LIST = "list"`, `CATALOG: list[Metric]`. Dataclasses `ParsedRows(daily, sleep, intraday)` and `Metric(name, data_type, method, max_range_days, scope, full_history, parse, page_size=1000, filter_field="date")`. Functions `civil(d: date, utc_offset_seconds: int = 0) -> dict[str, int]`, `list_filter(field_name: str, start: date, end: date) -> str`, `chunk_ranges(start: date, end: date, max_days: int) -> list[tuple[date, date]]`, `_parse_pending(payload) -> ParsedRows`.

- [ ] **Step 1: Write the failing tests**

Replace the entire contents of `health/tests/test_endpoints.py`:

```python
from datetime import date

from health.endpoints import (
    CATALOG,
    LIST,
    ROLLUP,
    ParsedRows,
    _parse_pending,
    chunk_ranges,
    civil,
    list_filter,
)


def test_civil_renders_google_civil_datetime():
    assert civil(date(2026, 7, 20)) == {
        "year": 2026, "month": 7, "day": 20, "utcOffsetSeconds": 0}


def test_civil_carries_utc_offset():
    assert civil(date(2026, 1, 1), 32400)["utcOffsetSeconds"] == 32400


def test_list_filter_is_closed_open_over_whole_days():
    # end is inclusive for us, so the expression stops at end + 1 day
    got = list_filter("date", date(2026, 7, 1), date(2026, 7, 3))
    assert got == 'date >= "2026-07-01" AND date < "2026-07-04"'


def test_list_filter_uses_the_given_field_name():
    got = list_filter("sample_time", date(2026, 7, 1), date(2026, 7, 1))
    assert got.startswith('sample_time >= "2026-07-01"')


def test_chunk_ranges_covers_the_span_without_gaps_or_overlap():
    chunks = chunk_ranges(date(2026, 1, 1), date(2026, 1, 10), 4)
    assert chunks == [(date(2026, 1, 1), date(2026, 1, 4)),
                      (date(2026, 1, 5), date(2026, 1, 8)),
                      (date(2026, 1, 9), date(2026, 1, 10))]


def test_chunk_ranges_single_day():
    assert chunk_ranges(date(2026, 1, 1), date(2026, 1, 1), 90) == [
        (date(2026, 1, 1), date(2026, 1, 1))]


def test_parse_pending_returns_no_rows():
    rows = _parse_pending({"anything": [1, 2, 3]})
    assert isinstance(rows, ParsedRows)
    assert list(rows.daily) == [] and list(rows.sleep) == [] and list(rows.intraday) == []


def test_catalog_names_are_unique():
    names = [m.name for m in CATALOG]
    assert len(names) == len(set(names)), "Metric.name is the sync_state primary key"


def test_catalog_has_thirteen_entries():
    assert len(CATALOG) == 13


def test_rollup_entries_use_documented_max_ranges():
    for m in CATALOG:
        if m.method == ROLLUP:
            assert m.max_range_days in (14, 90), m.name


def test_heart_and_calorie_rollups_are_capped_at_fourteen_days():
    by_name = {m.name: m for m in CATALOG}
    assert by_name["calories"].max_range_days == 14
    assert by_name["active_minutes"].max_range_days == 14
    assert by_name["steps"].max_range_days == 90


def test_sleep_uses_the_reduced_page_size():
    by_name = {m.name: m for m in CATALOG}
    assert by_name["sleep"].page_size == 25
    assert by_name["resting_hr"].page_size == 1000


def test_intraday_entries_are_not_full_history():
    by_name = {m.name: m for m in CATALOG}
    assert by_name["intraday_hr"].full_history is False
    assert by_name["intraday_steps"].full_history is False
    assert by_name["steps"].full_history is True


def test_every_entry_carries_a_method_and_data_type():
    for m in CATALOG:
        assert m.method in (ROLLUP, LIST), m.name
        assert m.data_type, m.name
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd health && uv run --no-sync pytest tests/test_endpoints.py -q`
Expected: collection error — `ImportError: cannot import name 'civil' from 'health.endpoints'`.

- [ ] **Step 3: Rewrite `health/src/health/endpoints.py`**

Replace the entire file:

```python
"""Google Health API catalog: data types, request shapes, date helpers.

Typed parsers are intentionally absent in Plan A. Every entry carries
``_parse_pending``, so a sync fills ``raw_json`` and writes no typed rows.
Plan B replaces the parsers once real response shapes are known, and
reprocesses from ``raw_json`` without refetching.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

API = "https://health.googleapis.com"

ROLLUP = "dailyRollUp"   # POST .../dataPoints:dailyRollUp with a civil range body
LIST = "list"            # GET  .../dataPoints?filter=...&pageSize=...&pageToken=...


@dataclass(frozen=True)
class ParsedRows:
    daily: Any = ()      # [(series_name, "YYYY-MM-DD", value)]
    sleep: Any = ()      # [dict] matching sleep_sessions columns
    intraday: Any = ()   # [(series_name, "YYYY-MM-DD HH:MM:SS", value)]


@dataclass(frozen=True)
class Metric:
    name: str            # catalog id and sync_state key; unique across CATALOG
    data_type: str       # Google dataType id used in the URL path
    method: str          # ROLLUP | LIST
    max_range_days: int  # request cap for ROLLUP; window width for LIST
    scope: str
    full_history: bool   # False: backfill only the trailing 30 days
    parse: Callable[[Any], ParsedRows] = field(repr=False)
    page_size: int = 1000   # LIST only; sleep and exercise cap at 25
    filter_field: str = "date"  # LIST only; the AIP-160 field to range over


def civil(d: date, utc_offset_seconds: int = 0) -> dict[str, int]:
    """Google represents dates as civil datetimes, not ISO strings."""
    return {"year": d.year, "month": d.month, "day": d.day,
            "utcOffsetSeconds": utc_offset_seconds}


def list_filter(field_name: str, start: date, end: date) -> str:
    """AIP-160 filter over [start, end] inclusive, expressed closed-open."""
    stop = end + timedelta(days=1)
    return f'{field_name} >= "{start.isoformat()}" AND {field_name} < "{stop.isoformat()}"'


def chunk_ranges(start: date, end: date, max_days: int) -> list[tuple[date, date]]:
    out, cur = [], start
    while cur <= end:
        stop = min(cur + timedelta(days=max_days - 1), end)
        out.append((cur, stop))
        cur = stop + timedelta(days=1)
    return out


def _parse_pending(payload: Any) -> ParsedRows:
    """Plan A writes the raw layer only; see the module docstring."""
    return ParsedRows()


_ACTIVITY = "activity_and_fitness"
_METRICS = "health_metrics_and_measurements"
_SLEEP = "sleep"

CATALOG: list[Metric] = [
    Metric("steps", "steps", ROLLUP, 90, _ACTIVITY, True, _parse_pending),
    Metric("distance", "distance", ROLLUP, 90, _ACTIVITY, True, _parse_pending),
    Metric("calories", "total-calories", ROLLUP, 14, _ACTIVITY, True, _parse_pending),
    Metric("active_minutes", "active-minutes", ROLLUP, 14, _ACTIVITY, True, _parse_pending),
    Metric("weight", "weight", ROLLUP, 90, _METRICS, True, _parse_pending),
    Metric("resting_hr", "daily-resting-heart-rate", LIST, 30, _METRICS, True,
           _parse_pending, filter_field="date"),
    Metric("hrv", "daily-heart-rate-variability", LIST, 30, _METRICS, True,
           _parse_pending, filter_field="date"),
    Metric("spo2", "daily-oxygen-saturation", LIST, 30, _METRICS, True,
           _parse_pending, filter_field="date"),
    Metric("temp_skin", "daily-sleep-temperature-derivations", LIST, 30, _METRICS, True,
           _parse_pending, filter_field="date"),
    Metric("br", "respiratory-rate-sleep-summary", LIST, 30, _METRICS, True,
           _parse_pending, filter_field="sample_time"),
    Metric("sleep", "sleep", LIST, 30, _SLEEP, True,
           _parse_pending, page_size=25, filter_field="start_time"),
    Metric("intraday_hr", "heart-rate", LIST, 1, _METRICS, False,
           _parse_pending, filter_field="sample_time"),
    Metric("intraday_steps", "steps", LIST, 1, _ACTIVITY, False,
           _parse_pending, filter_field="start_time"),
]
```

- [ ] **Step 4: Rename the inventory field**

In `health/src/health/inventory.py`, the row dict reads `"kind": m.kind`. The
Fitbit `kind` field is gone; the equivalent is `method`. Change that one line:

```python
            "metric": m.name, "source": "catalog", "kind": m.method, "scope": m.scope,
```

- [ ] **Step 5: Update the inventory catalog-count assertion**

In `health/tests/test_inventory.py`, `test_inventory_lists_all_catalog_metrics_even_empty`
asserts `>= 15`. The Google catalog has 13 entries. Change that line:

```python
    assert (inv["source"] == "catalog").sum() >= 13
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd health && uv run --no-sync pytest tests/test_endpoints.py tests/test_inventory.py -q`
Expected: 16 passed.

- [ ] **Step 7: Commit**

```bash
git add health/src/health/endpoints.py health/src/health/inventory.py \
        health/tests/test_endpoints.py health/tests/test_inventory.py
git commit -m "$(cat <<'EOF'
feat(health): Google Health data-type catalog without parsers

Thirteen entries across dailyRollUp and list methods, with the documented
14/90-day range caps and sleep's 25-item page size. Parsers are pending
until probe output lands, so entries write the raw layer only.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011b3F76ZJJXGstFzyki1PF9
EOF
)"
```

---

### Task 3: HTTP client

**Files:**
- Rewrite: `health/src/health/client.py`
- Modify: `health/tests/fakes.py` (accept `params` and `json`)
- Rewrite: `health/tests/test_client.py`

**Interfaces:**
- Consumes: `GoogleHealthAuth` (Task 1); `API`, `civil`, `list_filter` (Task 2).
- Produces: `HealthClient(auth, session=None)` with `daily_rollup(data_type: str, start: date, end: date) -> dict` and `iter_list(data_type: str, start: date, end: date, page_size: int, filter_field: str = "date") -> Iterator[dict]`. Exception `RateLimited(retry_after_s: int)`. Constant `DEFAULT_RETRY_AFTER_S = 60`.

- [ ] **Step 1: Extend the HTTP fakes**

`FakeSession.get` must accept `params` and `FakeSession.post` must accept `json`,
because the Google client sends query parameters and JSON bodies where the Fitbit
client sent neither. Replace the two methods in `health/tests/fakes.py`:

```python
    def get(self, url, params=None, headers=None, timeout=None):
        return self._record("GET", url, params=params, headers=headers)

    def post(self, url, data=None, json=None, auth=None, headers=None, timeout=None):
        return self._record("POST", url, data=data, json=json, auth=auth, headers=headers)
```

- [ ] **Step 2: Write the failing tests**

Replace the entire contents of `health/tests/test_client.py`:

```python
import json
from datetime import date

import pytest

from health.auth import GoogleHealthAuth
from health.client import API, DEFAULT_RETRY_AFTER_S, HealthClient, RateLimited
from tests.fakes import FakeResponse, FakeSession


def make_client(tmp_path, api_queue):
    auth_session = FakeSession([FakeResponse(200, {"access_token": "AT1",
                                                   "refresh_token": "RT1",
                                                   "expires_in": 3600})])
    auth = GoogleHealthAuth("CID", "SECRET", tmp_path, session=auth_session,
                            clock=lambda: 0.0)
    auth.begin_auth()
    state = json.loads((tmp_path / "oauth_pending.json").read_text())["state"]
    auth.complete_auth("C", state)
    return HealthClient(auth, session=FakeSession(api_queue)), auth


def test_daily_rollup_posts_a_civil_range_body(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(200, {"rollupDataPoints": []})])
    out = client.daily_rollup("steps", date(2026, 7, 1), date(2026, 7, 3))
    assert out == {"rollupDataPoints": []}
    call = client.session.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == f"{API}/v4/users/me/dataTypes/steps/dataPoints:dailyRollUp"
    assert call["json"] == {
        "range": {"start": {"year": 2026, "month": 7, "day": 1, "utcOffsetSeconds": 0},
                  "end": {"year": 2026, "month": 7, "day": 3, "utcOffsetSeconds": 0}},
        "windowSizeDays": 1}
    assert call["headers"]["Authorization"] == "Bearer AT1"


def test_iter_list_yields_one_page_when_there_is_no_next_token(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(200, {"dataPoints": [{"a": 1}]})])
    pages = list(client.iter_list("sleep", date(2026, 7, 1), date(2026, 7, 1), 25))
    assert pages == [{"dataPoints": [{"a": 1}]}]
    call = client.session.calls[0]
    assert call["method"] == "GET"
    assert call["url"] == f"{API}/v4/users/me/dataTypes/sleep/dataPoints"
    assert call["params"]["pageSize"] == 25
    assert "pageToken" not in call["params"]


def test_iter_list_follows_next_page_token_until_absent(tmp_path):
    client, _ = make_client(tmp_path, [
        FakeResponse(200, {"dataPoints": [{"a": 1}], "nextPageToken": "T1"}),
        FakeResponse(200, {"dataPoints": [{"a": 2}], "nextPageToken": "T2"}),
        FakeResponse(200, {"dataPoints": [{"a": 3}]}),
    ])
    pages = list(client.iter_list("heart-rate", date(2026, 7, 1), date(2026, 7, 1), 1000))
    assert [p["dataPoints"][0]["a"] for p in pages] == [1, 2, 3]
    assert "pageToken" not in client.session.calls[0]["params"]
    assert client.session.calls[1]["params"]["pageToken"] == "T1"
    assert client.session.calls[2]["params"]["pageToken"] == "T2"


def test_iter_list_passes_the_requested_filter_field(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(200, {"dataPoints": []})])
    list(client.iter_list("heart-rate", date(2026, 7, 1), date(2026, 7, 2), 1000,
                          filter_field="sample_time"))
    assert client.session.calls[0]["params"]["filter"] == (
        'sample_time >= "2026-07-01" AND sample_time < "2026-07-03"')


def test_401_triggers_a_single_refresh_and_retry(tmp_path):
    client, auth = make_client(tmp_path, [FakeResponse(401, {}),
                                          FakeResponse(200, {"rollupDataPoints": []})])
    auth.session.queue.append(FakeResponse(200, {"access_token": "AT2", "expires_in": 3600}))
    client.daily_rollup("steps", date(2026, 7, 1), date(2026, 7, 1))
    assert client.session.calls[1]["headers"]["Authorization"] == "Bearer AT2"


def test_repeated_401_propagates_as_http_error(tmp_path):
    client, auth = make_client(tmp_path, [FakeResponse(401, {}), FakeResponse(401, {})])
    auth.session.queue.append(FakeResponse(200, {"access_token": "AT2", "expires_in": 3600}))
    with pytest.raises(RuntimeError):
        client.daily_rollup("steps", date(2026, 7, 1), date(2026, 7, 1))


def test_429_raises_rate_limited_with_retry_after(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(429, {}, headers={"Retry-After": "900"})])
    with pytest.raises(RateLimited) as exc:
        client.daily_rollup("steps", date(2026, 7, 1), date(2026, 7, 1))
    assert exc.value.retry_after_s == 900


def test_429_without_retry_after_uses_the_default(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(429, {})])
    with pytest.raises(RateLimited) as exc:
        client.daily_rollup("steps", date(2026, 7, 1), date(2026, 7, 1))
    assert exc.value.retry_after_s == DEFAULT_RETRY_AFTER_S


def test_429_during_paging_propagates(tmp_path):
    client, _ = make_client(tmp_path, [
        FakeResponse(200, {"dataPoints": [], "nextPageToken": "T1"}),
        FakeResponse(429, {}),
    ])
    pages = client.iter_list("sleep", date(2026, 7, 1), date(2026, 7, 1), 25)
    assert next(pages) == {"dataPoints": [], "nextPageToken": "T1"}
    with pytest.raises(RateLimited):
        next(pages)


def test_http_error_propagates(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(500, {})])
    with pytest.raises(RuntimeError):
        client.daily_rollup("steps", date(2026, 7, 1), date(2026, 7, 1))
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd health && uv run --no-sync pytest tests/test_client.py -q`
Expected: collection error — `ImportError: cannot import name 'HealthClient' from 'health.client'`.

- [ ] **Step 4: Rewrite `health/src/health/client.py`**

Replace the entire file:

```python
"""Google Health API client: bearer auth, one-shot refresh retry, rollup + paged list."""
from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any

import requests

from health.auth import GoogleHealthAuth
from health.endpoints import API, civil, list_filter

DEFAULT_RETRY_AFTER_S = 60


class RateLimited(Exception):
    def __init__(self, retry_after_s: int):
        super().__init__(f"rate limited; retry after {retry_after_s}s")
        self.retry_after_s = retry_after_s


class HealthClient:
    def __init__(self, auth: GoogleHealthAuth, session: Any = None):
        self.auth = auth
        self.session = session or requests.Session()

    def daily_rollup(self, data_type: str, start: date, end: date) -> dict:
        body = {"range": {"start": civil(start), "end": civil(end)},
                "windowSizeDays": 1}
        return self._request(
            "POST", f"/v4/users/me/dataTypes/{data_type}/dataPoints:dailyRollUp",
            json_body=body)

    def iter_list(self, data_type: str, start: date, end: date, page_size: int,
                  filter_field: str = "date") -> Iterator[dict]:
        path = f"/v4/users/me/dataTypes/{data_type}/dataPoints"
        token: str | None = None
        while True:
            params: dict[str, Any] = {
                "filter": list_filter(filter_field, start, end),
                "pageSize": page_size}
            if token:
                params["pageToken"] = token
            page = self._request("GET", path, params=params)
            yield page
            token = page.get("nextPageToken")
            if not token:
                return

    # -- transport ---------------------------------------------------------
    def _request(self, method: str, path: str, json_body: dict | None = None,
                 params: dict | None = None) -> dict:
        resp = self._send(method, path, json_body, params)
        if resp.status_code == 401:
            self.auth.refresh()
            resp = self._send(method, path, json_body, params)
        if resp.status_code == 429:
            raise RateLimited(int(resp.headers.get("Retry-After", DEFAULT_RETRY_AFTER_S)))
        resp.raise_for_status()
        return resp.json()

    def _send(self, method: str, path: str, json_body: dict | None, params: dict | None):
        headers = {"Authorization": f"Bearer {self.auth.access_token()}"}
        url = API + path
        if method == "POST":
            return self.session.post(url, json=json_body, headers=headers, timeout=30)
        return self.session.get(url, params=params, headers=headers, timeout=30)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd health && uv run --no-sync pytest tests/test_client.py -q`
Expected: 10 passed.

- [ ] **Step 6: Commit**

```bash
git add health/src/health/client.py health/tests/test_client.py health/tests/fakes.py
git commit -m "$(cat <<'EOF'
feat(health): Google Health client with rollup POST and paged list GET

Replaces the Fitbit header-based rate-limit budget with clean 429 handling:
Google publishes no remaining-quota header, so the engine stops on 429 and
resumes from the sync_state watermark.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011b3F76ZJJXGstFzyki1PF9
EOF
)"
```

---

### Task 4: Sync engine

**Files:**
- Rewrite: `health/src/health/sync.py`
- Rewrite: `health/tests/test_sync.py`

**Interfaces:**
- Consumes: `RateLimited` (Task 3), `CATALOG`, `Metric`, `chunk_ranges`, `ROLLUP`, `LIST` (Task 2), `Store` (unchanged).
- Produces: `SyncEngine(client, store, catalog=CATALOG, today=None, max_requests_per_run=MAX_REQUESTS_PER_RUN, start_date=None)` with `sync_all(progress_cb=None) -> SyncReport`. Dataclasses `MetricProgress(metric, fetched_ranges=0, done=False)` and `SyncReport(progress, paused=False, resume_in_s=None, stopped_early=False, requests_made=0)`. Function `backfill_start(today: date) -> date`. Constants `TRAILING_REFETCH_DAYS = 2`, `TRAILING_BACKFILL_DAYS = 29`, `DEFAULT_BACKFILL_YEARS = 5`, `MAX_REQUESTS_PER_RUN = 200`.

- [ ] **Step 1: Write the failing tests**

Replace the entire contents of `health/tests/test_sync.py`:

```python
from datetime import date

import pytest

from health.client import RateLimited
from health.endpoints import LIST, ROLLUP, Metric, _parse_pending
from health.store import Store
from health.sync import MAX_REQUESTS_PER_RUN, SyncEngine, backfill_start


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.duckdb")
    yield s
    s.close()


class FakeClient:
    """Records calls; each list call yields `pages_per_call` pages."""

    def __init__(self, pages_per_call=1, raise_on_call=None):
        self.rollup_calls = []
        self.list_calls = []
        self.pages_per_call = pages_per_call
        self.raise_on_call = raise_on_call
        self.n_calls = 0

    def _tick(self):
        self.n_calls += 1
        if self.raise_on_call is not None and self.n_calls == self.raise_on_call:
            raise RateLimited(300)

    def daily_rollup(self, data_type, start, end):
        self._tick()
        self.rollup_calls.append((data_type, start, end))
        return {"rollupDataPoints": []}

    def iter_list(self, data_type, start, end, page_size, filter_field="date"):
        self.list_calls.append((data_type, start, end, page_size, filter_field))
        for i in range(self.pages_per_call):
            self._tick()
            yield {"dataPoints": [], "page": i}


def rollup_metric(name="steps", max_days=90, full_history=True):
    return Metric(name, name, ROLLUP, max_days, "activity_and_fitness",
                  full_history, _parse_pending)


def list_metric(name="sleep", max_days=30, page_size=25, filter_field="start_time"):
    return Metric(name, name, LIST, max_days, "sleep", True, _parse_pending,
                  page_size=page_size, filter_field=filter_field)


def test_rollup_metric_is_chunked_and_watermarked(store):
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=[rollup_metric(max_days=2)],
                        today=date(2026, 7, 5), start_date=date(2026, 7, 1))
    report = engine.sync_all()
    assert client.rollup_calls == [
        ("steps", date(2026, 7, 1), date(2026, 7, 2)),
        ("steps", date(2026, 7, 3), date(2026, 7, 4)),
        ("steps", date(2026, 7, 5), date(2026, 7, 5))]
    assert store.get_sync_state("steps") == date(2026, 7, 5)
    assert report.requests_made == 3
    assert report.progress[0].done is True


def test_list_metric_stores_every_page_under_a_distinct_key(store):
    client = FakeClient(pages_per_call=3)
    engine = SyncEngine(client, store, catalog=[list_metric()],
                        today=date(2026, 7, 1), start_date=date(2026, 7, 1))
    report = engine.sync_all()
    assert client.list_calls == [("sleep", date(2026, 7, 1), date(2026, 7, 1), 25,
                                 "start_time")]
    keys = store.con.execute(
        "SELECT date_key FROM raw_json WHERE endpoint = 'sleep' ORDER BY date_key"
    ).fetchall()
    assert [k[0] for k in keys] == ["2026-07-01_2026-07-01_p0",
                                    "2026-07-01_2026-07-01_p1",
                                    "2026-07-01_2026-07-01_p2"]
    assert report.requests_made == 3


def test_pending_parsers_write_no_typed_rows(store):
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=[rollup_metric()],
                        today=date(2026, 7, 1), start_date=date(2026, 7, 1))
    engine.sync_all()
    assert store.series_stats().empty
    assert store.con.execute("SELECT count(*) FROM raw_json").fetchone()[0] == 1


def test_rate_limit_pauses_and_leaves_the_watermark_resumable(store):
    client = FakeClient(raise_on_call=2)
    engine = SyncEngine(client, store, catalog=[rollup_metric(max_days=1)],
                        today=date(2026, 7, 3), start_date=date(2026, 7, 1))
    report = engine.sync_all()
    assert report.paused is True and report.resume_in_s == 300
    # the first chunk committed; the second did not
    assert store.get_sync_state("steps") == date(2026, 7, 1)


def test_request_cap_stops_the_run_early(store):
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=[rollup_metric(max_days=1)],
                        today=date(2026, 7, 10), start_date=date(2026, 7, 1),
                        max_requests_per_run=3)
    report = engine.sync_all()
    assert report.stopped_early is True
    assert report.requests_made == 3
    assert store.get_sync_state("steps") == date(2026, 7, 3)


def test_resume_refetches_a_trailing_window(store):
    store.set_sync_state("steps", date(2026, 7, 10))
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=[rollup_metric(max_days=90)],
                        today=date(2026, 7, 12), start_date=date(2026, 1, 1))
    engine.sync_all()
    assert client.rollup_calls == [("steps", date(2026, 7, 8), date(2026, 7, 12))]


def test_non_full_history_metrics_start_from_the_trailing_window(store):
    client = FakeClient()
    engine = SyncEngine(client, store,
                        catalog=[rollup_metric("intraday_hr", max_days=90,
                                               full_history=False)],
                        today=date(2026, 7, 30), start_date=date(2020, 1, 1))
    engine.sync_all()
    assert client.rollup_calls == [("intraday_hr", date(2026, 7, 1), date(2026, 7, 30))]


def test_backfill_start_defaults_to_five_years_ago(monkeypatch):
    monkeypatch.delenv("HEALTH_BACKFILL_START", raising=False)
    assert backfill_start(date(2026, 7, 20)) == date(2021, 7, 21)


def test_backfill_start_honours_the_env_override(monkeypatch):
    monkeypatch.setenv("HEALTH_BACKFILL_START", "2019-03-04")
    assert backfill_start(date(2026, 7, 20)) == date(2019, 3, 4)


def test_backfill_start_rejects_a_malformed_override(monkeypatch):
    monkeypatch.setenv("HEALTH_BACKFILL_START", "March 2019")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        backfill_start(date(2026, 7, 20))


def test_default_request_cap_is_two_hundred():
    assert MAX_REQUESTS_PER_RUN == 200


def test_progress_callback_reports_each_chunk(store):
    seen = []
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=[rollup_metric(max_days=1)],
                        today=date(2026, 7, 2), start_date=date(2026, 7, 1))
    engine.sync_all(progress_cb=lambda metric, msg: seen.append((metric, msg)))
    assert seen == [("steps", "2026-07-01 → 2026-07-01"),
                    ("steps", "2026-07-02 → 2026-07-02")]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd health && uv run --no-sync pytest tests/test_sync.py -q`
Expected: collection error — `ImportError: cannot import name 'backfill_start' from 'health.sync'`.

- [ ] **Step 3: Rewrite `health/src/health/sync.py`**

Replace the entire file:

```python
"""Resumable backfill/incremental sync over the Google Health catalog."""
from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta

from health.client import RateLimited
from health.endpoints import CATALOG, ROLLUP, Metric, chunk_ranges
from health.store import Store

TRAILING_REFETCH_DAYS = 2    # re-fetch last_synced - 2d .. today (3-day window)
TRAILING_BACKFILL_DAYS = 29  # non-full-history metrics: today - 29d start
DEFAULT_BACKFILL_YEARS = 5
MAX_REQUESTS_PER_RUN = 200   # soft ceiling: Google publishes no quota figure


def backfill_start(today: date) -> date:
    """First date to backfill: HEALTH_BACKFILL_START, else five years back."""
    raw = os.environ.get("HEALTH_BACKFILL_START", "").strip()
    if not raw:
        return today - timedelta(days=365 * DEFAULT_BACKFILL_YEARS)
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(
            f"HEALTH_BACKFILL_START must be YYYY-MM-DD, got {raw!r}") from exc


@dataclass
class MetricProgress:
    metric: str
    fetched_ranges: int = 0
    done: bool = False


@dataclass
class SyncReport:
    progress: list[MetricProgress] = field(default_factory=list)
    paused: bool = False
    resume_in_s: int | None = None
    stopped_early: bool = False
    requests_made: int = 0


class SyncEngine:
    def __init__(self, client, store: Store, catalog: list[Metric] = CATALOG,
                 today: date | None = None,
                 max_requests_per_run: int = MAX_REQUESTS_PER_RUN,
                 start_date: date | None = None):
        self.client = client
        self.store = store
        self.catalog = catalog
        self.today = today or date.today()
        self.max_requests_per_run = max_requests_per_run
        self.start_date = start_date

    def _start_date(self, m: Metric, default_start: date) -> date:
        default = default_start if m.full_history else (
            self.today - timedelta(days=TRAILING_BACKFILL_DAYS))
        last = self.store.get_sync_state(m.name)
        if last is None:
            return default
        return max(default, min(last - timedelta(days=TRAILING_REFETCH_DAYS), self.today))

    def sync_all(self, progress_cb: Callable[[str, str], None] | None = None) -> SyncReport:
        report = SyncReport()
        default_start = self.start_date or backfill_start(self.today)
        for m in self.catalog:
            prog = MetricProgress(metric=m.name)
            report.progress.append(prog)
            start = self._start_date(m, default_start)
            for s, e in chunk_ranges(start, self.today, m.max_range_days):
                # The cap is checked between chunks only: a list chunk spans an
                # unknown number of pages, and abandoning it mid-way would advance
                # no watermark and waste the pages already fetched.
                if report.requests_made >= self.max_requests_per_run:
                    report.stopped_early = True
                    return report
                try:
                    self._fetch_chunk(m, s, e, report)
                except RateLimited as exc:
                    report.paused = True
                    report.resume_in_s = exc.retry_after_s
                    return report
                self.store.set_sync_state(m.name, e)
                prog.fetched_ranges += 1
                if progress_cb:
                    progress_cb(m.name, f"{s} → {e}")
            prog.done = True
        return report

    def _fetch_chunk(self, m: Metric, s: date, e: date, report: SyncReport) -> None:
        if m.method == ROLLUP:
            payload = self.client.daily_rollup(m.data_type, s, e)
            report.requests_made += 1
            self._store_payload(m, f"{s}_{e}", payload)
            return
        pages = self.client.iter_list(m.data_type, s, e, m.page_size, m.filter_field)
        for i, page in enumerate(pages):
            report.requests_made += 1
            self._store_payload(m, f"{s}_{e}_p{i}", page)

    def _store_payload(self, m: Metric, date_key: str, payload) -> None:
        self.store.upsert_raw(m.name, date_key, payload)
        rows = m.parse(payload)
        self.store.upsert_daily(rows.daily)
        self.store.upsert_sleep(rows.sleep)
        self.store.upsert_intraday(rows.intraday)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd health && uv run --no-sync pytest tests/test_sync.py -q`
Expected: 12 passed.

- [ ] **Step 5: Run the whole suite**

Run: `cd health && uv run --no-sync pytest tests -q`
Expected: 62 passed (auth 15, endpoints 14, client 10, sync 12, store 9, inventory 2).

- [ ] **Step 6: Commit**

```bash
git add health/src/health/sync.py health/tests/test_sync.py
git commit -m "$(cat <<'EOF'
feat(health): adapt sync engine to rollup/list dispatch and a request cap

Shrinking max ranges from 1095 to 90/14 days multiplies backfill requests,
so runs stop at max_requests_per_run (200) and resume from the watermark.
memberSince is replaced by HEALTH_BACKFILL_START, removing an API call.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011b3F76ZJJXGstFzyki1PF9
EOF
)"
```

---

### Task 5: App wiring

**Files:**
- Modify: `health/app/common.py`
- Modify: `health/app/main.py`
- Rewrite: `health/app/views/sync_view.py`

**Interfaces:**
- Consumes: `GoogleHealthAuth`, `AuthError`, `forget_tokens`, `refresh_expires_in_days` (Task 1); `HealthClient` (Task 3); `SyncEngine`, `SyncReport` fields `paused`, `resume_in_s`, `stopped_early`, `requests_made` (Task 4).
- Produces: a runnable app — the user can authorize and press sync. No new module APIs.

There are no unit tests for the Streamlit layer in this project (the existing
suite does not test views), so this task is verified by import checks and by the
manual run in Task 6.

- [ ] **Step 1: Update `health/app/common.py`**

Replace the two Fitbit references:

```python
"""Shared app context: paths and cached resources."""
from pathlib import Path

import streamlit as st

from health.auth import GoogleHealthAuth
from health.store import Store

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@st.cache_resource
def get_store() -> Store:
    return Store(DATA_DIR / "health.duckdb")


def get_auth() -> GoogleHealthAuth:
    return GoogleHealthAuth.from_env(DATA_DIR)
```

- [ ] **Step 2: Update the provider wording in `health/app/main.py`**

Three lines change. In the callback branch:

```python
            st.success("Google Health と接続しました")
```

And in the not-yet-connected branch:

```python
        st.markdown(f"[Google Health と接続する]({auth.begin_auth()})")
        st.caption("Google Cloud の OAuth クライアント (Client ID/Secret) を "
                   "health/.env に設定してから接続してください。")
```

- [ ] **Step 3: Rewrite `health/app/views/sync_view.py`**

Replace the entire file:

```python
"""Sync page: on-demand sync with progress, token status, reconnect."""
from datetime import datetime

import streamlit as st

from health.auth import AuthError
from health.client import HealthClient
from health.sync import SyncEngine

from common import get_auth, get_store


def sync_page() -> None:
    st.title("同期")
    auth = get_auth()
    store = get_store()

    last = st.session_state.pop("last_sync_report", None)
    if last is not None:
        if last["paused"]:
            mins = (last["resume_in_s"] or 60) // 60 + 1
            st.warning(f"レート制限に達しました。進捗は保存済みです。"
                       f"約 {mins} 分後にもう一度同期してください。")
        elif last["stopped_early"]:
            st.info(f"今回の実行上限（{last['requests_made']} リクエスト）に達しました。"
                    "進捗は保存済みです。続きは、もう一度同期を押してください。")
        else:
            st.success(f"同期が完了しました（{last['requests_made']} リクエスト）")

    tokens = auth.load_tokens()
    if tokens is None:
        st.warning("未接続です。概要ページから接続してください。")
        return

    exp = datetime.fromtimestamp(tokens["expires_at"]).strftime("%H:%M")
    days = auth.refresh_expires_in_days()
    st.caption(f"アクセストークン有効期限: {exp} / スコープ: {tokens.get('scope', '-')}")
    if days is not None:
        if days <= 0:
            st.error("再認証トークンが失効しました（Testing モードは7日で失効します）。"
                     "下の「再接続」を押してから、概要ページで接続し直してください。")
        elif days <= 2:
            st.warning(f"再認証トークンの残り: 約 {days:.1f} 日")
        else:
            st.caption(f"再認証トークンの残り: 約 {days:.1f} 日")

    if st.button("再接続（トークンを破棄）"):
        auth.forget_tokens()
        st.rerun()

    states = store.sync_states()
    if not states.empty:
        st.dataframe(states, use_container_width=True)

    if st.button("Google Health からデータを同期", type="primary"):
        try:
            client = HealthClient(auth)
            engine = SyncEngine(client, store)
            with st.status("同期中...", expanded=True) as status:
                report = engine.sync_all(
                    progress_cb=lambda metric, msg: status.write(f"{metric}: {msg}"))
        except AuthError as exc:
            st.error(f"認証エラー: {exc}\n\n「再接続」を押してから接続し直してください。")
        else:
            st.session_state["last_sync_report"] = {
                "paused": report.paused, "resume_in_s": report.resume_in_s,
                "stopped_early": report.stopped_early,
                "requests_made": report.requests_made}
            st.rerun()
```

- [ ] **Step 4: Verify the app modules import cleanly**

Run:
```bash
cd health && uv run --no-sync python -c "
import sys; sys.path[:0] = ['app', 'src']
import common, views.sync_view, views.overview_view, views.sleep_view
import views.activity_view, views.heart_view, views.body_view, views.inventory_view
print('imports ok')"
```
Expected: `imports ok`.

- [ ] **Step 5: Run the whole suite to confirm nothing regressed**

Run: `cd health && uv run --no-sync pytest tests -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add health/app/common.py health/app/main.py health/app/views/sync_view.py
git commit -m "$(cat <<'EOF'
feat(health): wire the app to Google Health auth and client

Sync page gains refresh-token remaining days, a reconnect action that drops
stored tokens, and a stopped-early report for the per-run request cap.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011b3F76ZJJXGstFzyki1PF9
EOF
)"
```

---

### Task 6: Probe script and setup documentation

**Files:**
- Create: `health/scripts/probe_datatypes.py`
- Rewrite: `health/README.md`
- Modify: `health/CLAUDE.md`
- Modify: `health/pyproject.toml` (description line)

**Interfaces:**
- Consumes: `GoogleHealthAuth`, `AuthError` (Task 1); `CATALOG`, `ROLLUP` (Task 2); `HealthClient`, `RateLimited` (Task 3).
- Produces: `health/data/probe/<metric-name>.json` files plus a printed shape summary. Nothing imports the script.

- [ ] **Step 1: Create `health/scripts/probe_datatypes.py`**

```python
"""Fetch one narrow window per catalog data type and dump raw responses.

Plan B's parsers are written against these files. Nothing here touches DuckDB.
Every data type is attempted independently: one failure is reported and the
run continues, because a wrong filter field or a missing scope on one type
must not hide the shapes of the others.

    uv run --no-sync python health/scripts/probe_datatypes.py
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from health.auth import AuthError, GoogleHealthAuth
from health.client import HealthClient, RateLimited
from health.endpoints import CATALOG, ROLLUP

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
OUT_DIR = DATA_DIR / "probe"
DAILY_WINDOW_DAYS = 7
INTRADAY_WINDOW_DAYS = 1


def describe(payload) -> str:
    """One line naming the top-level keys and the shape of the first record."""
    if not isinstance(payload, dict):
        return type(payload).__name__
    parts = []
    for key, value in payload.items():
        if isinstance(value, list):
            head = value[0] if value else None
            inner = ",".join(sorted(head)) if isinstance(head, dict) else type(head).__name__
            parts.append(f"{key}[{len(value)}]{{{inner}}}")
        else:
            parts.append(f"{key}={value!r}")
    return " ".join(parts) or "(empty object)"


def main() -> None:
    try:
        auth = GoogleHealthAuth.from_env(DATA_DIR)
    except AuthError as exc:
        raise SystemExit(str(exc)) from exc
    if auth.load_tokens() is None:
        raise SystemExit("not connected — authorize in the Streamlit app first")
    client = HealthClient(auth)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    today = date.today()
    for m in CATALOG:
        span = INTRADAY_WINDOW_DAYS if not m.full_history else DAILY_WINDOW_DAYS
        end = today - timedelta(days=1)      # yesterday: today may be incomplete
        start = end - timedelta(days=span - 1)
        try:
            if m.method == ROLLUP:
                payload = client.daily_rollup(m.data_type, start, end)
            else:
                payload = next(iter(
                    client.iter_list(m.data_type, start, end, m.page_size,
                                     m.filter_field)))
        except RateLimited as exc:
            print(f"{m.name:16s} RATE LIMITED — retry in {exc.retry_after_s}s")
            continue
        except AuthError as exc:
            raise SystemExit(f"auth failed: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - one bad type must not stop the sweep
            print(f"{m.name:16s} ERROR {type(exc).__name__}: {exc}")
            continue
        out = OUT_DIR / f"{m.name}.json"
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"{m.name:16s} {m.data_type:38s} {describe(payload)}")

    print(f"\nraw responses written to {OUT_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the script fails cleanly without credentials**

Run: `cd health && uv run --no-sync python scripts/probe_datatypes.py`
Expected: exits with `GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set (health/.env)`
(or, if `.env` exists with credentials but no tokens, `not connected — authorize
in the Streamlit app first`). Either message is a pass: the script must not
traceback.

- [ ] **Step 3: Rewrite `health/README.md`**

```markdown
# health — Personal Google Health dashboard

Streamlit + Plotly + DuckDB over the Google Health API (OAuth 2.0 + PKCE).
Spec: `docs/superpowers/specs/2026-07-20-health-google-health-api-migration-design.md`.

The legacy Fitbit Web API this app originally targeted is turned down in
September 2026; Google Health is its replacement.

## Setup (one-time, ~15 min)

1. Create a project at <https://console.cloud.google.com/projectcreate>.
2. Enable the API:
   <https://console.cloud.google.com/apis/library/health.googleapis.com>
3. OAuth consent screen — User type **External**, publishing status **Testing**,
   and add your own Google account under **Test users**. All Google Health scopes
   are Restricted; Testing status is what makes personal use possible without a
   verification review. The cost is that refresh tokens expire after 7 days, so
   expect to reconnect weekly.
4. Credentials > Create credentials > OAuth client ID > **Web application**.
   Authorized redirect URI: `http://localhost:8501/`
5. `cp health/.env.example health/.env` and fill `GOOGLE_CLIENT_ID` /
   `GOOGLE_CLIENT_SECRET`. Optionally set `HEALTH_BACKFILL_START=YYYY-MM-DD`
   (defaults to five years ago).
6. From the workspace root: `uv sync --all-packages`
   (or `uv sync --package health` in a worktree).

## Run

    uv run --no-sync streamlit run health/app/main.py

First visit: click "Google Health と接続する", authorize (you will pass an
"unverified app" warning — that is expected for Testing status), and you land
back in the app. Then open 管理 > 同期 and press the sync button.

A full backfill needs hundreds of requests because Google caps ranges at 90 days
(14 for calories and active minutes). Each run stops after 200 requests and
saves progress; press sync again to continue.

## Probe

    uv run --no-sync python health/scripts/probe_datatypes.py

Fetches one narrow window per data type into `health/data/probe/*.json` and
prints a shape summary. This is how response shapes are established before
parsers are written.

## Data

- `health/data/health.duckdb` — raw JSON + typed layer (`daily_series`,
  `sleep_sessions`, `intraday`, `sync_state`). Gitignored.
- `health/data/tokens.json` — OAuth tokens (mode 600). Gitignored.
  Use 管理 > 同期 > 再接続 to drop them.
- `health/data/probe/` — raw probe responses. Gitignored; never commit these.

## Tests

    uv run --no-sync pytest health/tests        # from workspace root
    cd health && uv run --no-sync pytest tests  # standalone (slim worktree venv)
```

- [ ] **Step 4: Update `health/CLAUDE.md`**

Two edits. Replace the second line:

```markdown
Personal Fitbit dashboard. Respond in Japanese; code/identifiers/commits in English.
```

with:

```markdown
Personal Google Health dashboard (`health.googleapis.com`, OAuth 2.0 + PKCE; the
legacy Fitbit Web API it replaced is turned down in September 2026). Respond in
Japanese; code/identifiers/commits in English.
```

Then replace the bullet that says a new metric needs `new Metric entry + parser`,
because Plan A ships the catalog without parsers:

```markdown
- `endpoints.py` CATALOG is the single source of truth for metrics. Entries carry
  a `method` (`dailyRollUp` POST or `list` GET) and, for `list`, a `page_size` and
  `filter_field`. Parsers are `_parse_pending` until Plan B: sync fills `raw_json`
  and writes no typed rows.
```

- [ ] **Step 5: Update the package description and docstring**

In `health/pyproject.toml`:

```toml
description = "Personal Google Health dashboard (Streamlit + Plotly + DuckDB)"
```

And the whole of `health/src/health/__init__.py`, which still names the old
provider and is inside the grep scope of the next step:

```python
"""Personal Google Health dashboard: OAuth2 client, DuckDB store, sync engine."""
```

- [ ] **Step 6: Confirm no stale provider references remain in code**

Run:
```bash
cd health && grep -rin fitbit src app scripts tests pyproject.toml || echo "no fitbit references in code"
```
Expected: `no fitbit references in code`. README.md and CLAUDE.md legitimately
mention Fitbit when explaining the turndown, so they are excluded from this check.

- [ ] **Step 7: Run the whole suite**

Run: `cd health && uv run --no-sync pytest tests -q`
Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add health/scripts/probe_datatypes.py health/README.md health/CLAUDE.md \
        health/pyproject.toml health/src/health/__init__.py
git commit -m "$(cat <<'EOF'
feat(health): probe script and Google Cloud setup docs

probe_datatypes.py fetches one narrow window per data type into
data/probe/*.json and prints a shape summary, so Plan B's parsers are
written against observed responses rather than guessed ones.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011b3F76ZJJXGstFzyki1PF9
EOF
)"
```

---

## Checkpoint — hand back to the user

Plan A ends here. Do not start Plan B work.

Report to the user that they need to complete, in order:

1. Google Cloud setup, steps 1–5 of `health/README.md`.
2. `uv sync --package health` (or `uv sync --all-packages` from the workspace root).
3. `uv run --no-sync streamlit run health/app/main.py`, connect, and authorize.
4. `uv run --no-sync python health/scripts/probe_datatypes.py`.
5. Paste back the printed shape summary, or confirm the files exist under
   `health/data/probe/`.

Flag these specific things to watch for, because each one invalidates an
assumption this plan encodes:

- Whether `http://localhost:8501/` was accepted as a redirect URI.
- Which data types returned `ERROR` — a wrong `filter_field` is the likely cause,
  and the fix belongs in `endpoints.py`.
- Whether the `sleep` payload carries stage segments. If it does not, Plan B's
  sleep parser cannot be written and the design needs revisiting.

Plan B covers: typed parsers per data type, reprocessing `raw_json` into the
typed tables without refetching, `KNOWN_DATA_TYPES` plus the inventory page's
implemented/not-implemented listing, `activity_view.py`'s `minutes_very_active`
→ `minutes_active` rename, and `seed_demo.py`.
