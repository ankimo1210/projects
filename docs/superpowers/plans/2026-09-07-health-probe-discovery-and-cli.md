# Health: Probe Discovery + Headless CLI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Google Health の未実装 22 データ型それぞれについて request shape を実測で確定させ、Streamlit を起動せずに認可と同期を回せる CLI を用意する。

**Architecture:** 既存の `run_probe()` は `Metric` を受け取るが、未実装型は `method` / `filter_path` が未知なので `Metric` を作れない。そこで候補となる shape を順に試して最初に成功したものを記録する discovery 層を新設する（`src/health/discovery.py`）。CLI は `src/health/cli.py` に argparse で置き、OAuth は loopback HTTP サーバでコールバックを受ける。同期エンジンには一切手を入れない。

**Tech Stack:** Python 3.12+, requests, DuckDB, pytest（fake HTTP のみ。live API は自動テストで呼ばない）

**Spec:** `docs/superpowers/specs/2026-09-06-health-full-archive-and-nextjs-design.md`（Phase 1 と Phase 2-4 に対応）

## Global Constraints

- ワークスペース root から実行する: `uv run --no-sync pytest health/tests`。`uv` をメンバーディレクトリ内で走らせない。
- テストは fake HTTP と committed fixture のみを使う。**live Google Health API を自動テストから呼ばない。**
- `health/data/` と `.env` は private かつ gitignored。token・probe payload・実健康データを commit しない。
- probe の出力は**実際の健康データ**。共有・commit しない。
- 同期エンジン（`src/health/sync.py`）に sleep や自動 retry を足さない。pace と 401 retry は client の責務。
- Response が返す repeated field が欠けている場合は空ページ扱い、list でない場合は `PayloadError`（既存規約）。
- 既存 258 tests を壊さない。

---

### Task 1: Candidate request shapes for an unknown data type

**Files:**
- Create: `health/src/health/discovery.py`
- Create: `health/tests/test_discovery.py`
- Modify: `health/CLAUDE.md`（壊れた参照の修正）

**Interfaces:**
- Consumes: `health.endpoints.DAILY_ROLLUP`, `RECONCILE`, `Metric`, `ParsedRows`, `KNOWN_DATA_TYPES`
- Produces: `candidate_metrics(data_type: str, scope: str) -> list[Metric]` — 試す順に並んだ候補。各 `Metric` の `parse_pages` は `ParsedRows()` を返す no-op。

- [ ] **Step 1: Write the failing test**

```python
# health/tests/test_discovery.py
from health.endpoints import DAILY_ROLLUP, RECONCILE
from health.discovery import candidate_metrics


def test_daily_rollup_is_tried_first():
    candidates = candidate_metrics("floors", "activity_and_fitness")
    assert candidates[0].method == DAILY_ROLLUP
    assert candidates[0].filter_path is None
    assert candidates[0].data_type == "floors"


def test_reconcile_candidates_cover_the_known_filter_path_shapes():
    paths = [c.filter_path for c in candidate_metrics("floors", "activity_and_fitness")
             if c.method == RECONCILE]
    assert paths == [
        "floors.date",
        "floors.interval.civil_start_time",
        "floors.interval.civil_end_time",
        "floors.sample_time.civil_time",
    ]


def test_hyphenated_data_type_becomes_snake_case_in_the_filter_path():
    paths = [c.filter_path for c in candidate_metrics("core-body-temperature", "scope")
             if c.method == RECONCILE]
    assert paths[0] == "core_body_temperature.date"


def test_candidate_parsers_are_archive_only():
    for candidate in candidate_metrics("floors", "activity_and_fitness"):
        parsed = candidate.parse_pages([{"anything": 1}])
        assert parsed.daily == ()
        assert parsed.sleep == ()
        assert parsed.intraday == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest health/tests/test_discovery.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'health.discovery'`

- [ ] **Step 3: Write minimal implementation**

```python
# health/src/health/discovery.py
"""Determine the request shape of a Google Health data type by probing it.

`CATALOG` entries carry a hand-written `method` and `filter_path`. For a data
type nobody has implemented yet those are unknown, so this module builds the
plausible shapes and lets the API say which one is real: a wrong
`filter_path` is rejected with HTTP 400, while a right one with no data
returns 200 and an empty page.
"""

from __future__ import annotations

from health.endpoints import DAILY_ROLLUP, RECONCILE, Metric, ParsedRows

# Ordered by cost: dailyRollUp is a single POST, reconcile may paginate.
# The reconcile paths mirror every shape CATALOG uses today -- a daily
# summary keyed by `.date`, an interval, or a point sample.
RECONCILE_PATH_SUFFIXES = (
    "date",
    "interval.civil_start_time",
    "interval.civil_end_time",
    "sample_time.civil_time",
)

DISCOVERY_MAX_RANGE_DAYS = 7
DISCOVERY_PAGE_SIZE = 100


def _archive_only(_pages) -> ParsedRows:
    """Store the raw payload and derive nothing (spec decision D-1)."""
    return ParsedRows()


def candidate_metrics(data_type: str, scope: str) -> list[Metric]:
    """Every request shape worth trying for `data_type`, cheapest first."""
    snake = data_type.replace("-", "_")
    candidates = [
        Metric(
            name=data_type,
            data_type=data_type,
            method=DAILY_ROLLUP,
            max_range_days=DISCOVERY_MAX_RANGE_DAYS,
            scope=scope,
            full_history=True,
            series_names=(),
            parse_pages=_archive_only,
            page_size=DISCOVERY_PAGE_SIZE,
        )
    ]
    candidates += [
        Metric(
            name=data_type,
            data_type=data_type,
            method=RECONCILE,
            max_range_days=DISCOVERY_MAX_RANGE_DAYS,
            scope=scope,
            full_history=True,
            series_names=(),
            parse_pages=_archive_only,
            page_size=DISCOVERY_PAGE_SIZE,
            filter_path=f"{snake}.{suffix}",
        )
        for suffix in RECONCILE_PATH_SUFFIXES
    ]
    return candidates
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --no-sync pytest health/tests/test_discovery.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Fix the broken contract reference in CLAUDE.md**

`health/CLAUDE.md` は `.superpowers/sdd/health-google-api-contracts.md` を API shape の正本として参照しているが、このファイルはリポジトリに存在しない（`find . -name health-google-api-contracts.md` が空）。次の行に差し替える。

置換前:
```
  `endpoints.py`の14-entry `CATALOG`が実装metricのsingle source of truth。
  API shapeは`.superpowers/sdd/health-google-api-contracts.md`に従う。
```

置換後:
```
  `endpoints.py`の14-entry `CATALOG`が実装metricのsingle source of truth。
  API shapeはGoogle公式リファレンスに従う(`dailyRollUp` / `reconcile` /
  `list` filter syntax)。未実装データ型のshapeは`src/health/discovery.py`で
  実測して確定させる。
```

- [ ] **Step 6: Commit**

```bash
git add health/src/health/discovery.py health/tests/test_discovery.py health/CLAUDE.md
git commit -m "feat(health): build candidate request shapes for unknown data types"
```

---

### Task 2: Probe one unknown data type and record which shape worked

**Files:**
- Modify: `health/src/health/discovery.py`
- Modify: `health/tests/test_discovery.py`

**Interfaces:**
- Consumes: `candidate_metrics()` (Task 1), `health.client.ApiError`, `RequestBudget`, `RequestCapExceeded`, `health.endpoints.response_points`, `PayloadError`
- Produces: `discover_shape(client, data_type: str, scope: str, start: date, end: date) -> dict` — `{"data_type", "status", "method", "filter_path", "page_count", "data_point_count", "attempts"}`。`status` は `"ok"`（データあり）/ `"empty"`（shape は通ったがデータ 0 件）/ `"unknown"`（全候補が失敗）。

- [ ] **Step 1: Write the failing test**

```python
# append to health/tests/test_discovery.py
from datetime import date

import pytest
from health.auth import AuthError
from health.client import ApiError
from health.discovery import discover_shape
from health.endpoints import DAILY_ROLLUP, RECONCILE


class FakeDiscoveryClient:
    """Answers per (method, filter_path); anything unlisted raises HTTP 400."""

    def __init__(self, answers):
        self.answers = answers
        self.attempts = []

    def daily_rollup(self, metric, start, end, _budget):
        return self._answer(metric)

    def iter_reconciled(self, metric, start, end, _budget):
        return iter([self._answer(metric)])

    def _answer(self, metric):
        key = (metric.method, metric.filter_path)
        self.attempts.append(key)
        if key not in self.answers:
            raise ApiError(400, "INVALID_ARGUMENT", "unknown field")
        return self.answers[key]


def test_daily_rollup_wins_without_trying_reconcile():
    client = FakeDiscoveryClient({
        (DAILY_ROLLUP, None): {"rollupDataPoints": [{"a": 1}, {"a": 2}]},
    })
    row = discover_shape(client, "floors", "activity_and_fitness",
                         date(2026, 9, 1), date(2026, 9, 7))
    assert row["status"] == "ok"
    assert row["method"] == DAILY_ROLLUP
    assert row["filter_path"] is None
    assert row["data_point_count"] == 2
    assert client.attempts == [(DAILY_ROLLUP, None)]


def test_falls_through_to_the_reconcile_path_that_the_api_accepts():
    client = FakeDiscoveryClient({
        (RECONCILE, "exercise.interval.civil_start_time"): {"dataPoints": [{"a": 1}]},
    })
    row = discover_shape(client, "exercise", "activity_and_fitness",
                         date(2026, 9, 1), date(2026, 9, 7))
    assert row["status"] == "ok"
    assert row["method"] == RECONCILE
    assert row["filter_path"] == "exercise.interval.civil_start_time"
    assert client.attempts[0] == (DAILY_ROLLUP, None)


def test_an_accepted_shape_with_no_data_is_empty_not_unknown():
    client = FakeDiscoveryClient({(DAILY_ROLLUP, None): {"rollupDataPoints": []}})
    row = discover_shape(client, "blood-glucose", "health_metrics_and_measurements",
                         date(2026, 9, 1), date(2026, 9, 7))
    assert row["status"] == "empty"
    assert row["method"] == DAILY_ROLLUP
    assert row["data_point_count"] == 0


def test_every_candidate_rejected_reports_unknown_and_keeps_the_attempts():
    client = FakeDiscoveryClient({})
    row = discover_shape(client, "swim-lengths-data", "activity_and_fitness",
                         date(2026, 9, 1), date(2026, 9, 7))
    assert row["status"] == "unknown"
    assert row["method"] is None
    assert len(row["attempts"]) == 5
    assert all(a["error_status"] == 400 for a in row["attempts"])


def test_auth_error_stops_discovery_instead_of_being_recorded():
    class AuthFailingClient:
        def daily_rollup(self, *_args):
            raise AuthError("refresh token expired")

    with pytest.raises(AuthError):
        discover_shape(AuthFailingClient(), "floors", "activity_and_fitness",
                       date(2026, 9, 1), date(2026, 9, 7))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest health/tests/test_discovery.py -v`
Expected: FAIL with `ImportError: cannot import name 'discover_shape'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to health/src/health/discovery.py
from datetime import date

from health.auth import AuthError
from health.client import ApiError, RequestBudget, RequestCapExceeded
from health.endpoints import PayloadError, response_points

DISCOVERY_REQUEST_LIMIT_PER_CANDIDATE = 20


def discover_shape(
    client, data_type: str, scope: str, start: date, end: date
) -> dict:
    """Try each candidate shape and return the first the API accepts.

    An `AuthError` aborts: every later request would fail the same way. An
    `ApiError` only rules out that one candidate, which is the whole point --
    a rejected `filter_path` is the signal, not a failure.
    """
    attempts: list[dict] = []
    for candidate in candidate_metrics(data_type, scope):
        budget = RequestBudget(DISCOVERY_REQUEST_LIMIT_PER_CANDIDATE)
        try:
            if candidate.method == DAILY_ROLLUP:
                pages = [client.daily_rollup(candidate, start, end, budget)]
            else:
                pages = list(client.iter_reconciled(candidate, start, end, budget))
            points = sum(len(response_points(candidate, page)) for page in pages)
        except AuthError:
            raise
        except (ApiError, PayloadError, RequestCapExceeded) as exc:
            attempts.append(
                {
                    "method": candidate.method,
                    "filter_path": candidate.filter_path,
                    "error_status": getattr(exc, "status_code", None),
                    "error_message": str(exc),
                }
            )
            continue

        return {
            "data_type": data_type,
            "scope": scope,
            "status": "ok" if points else "empty",
            "method": candidate.method,
            "filter_path": candidate.filter_path,
            "page_count": len(pages),
            "data_point_count": points,
            "top_level_keys": sorted({key for page in pages for key in page}),
            "attempts": attempts,
        }

    return {
        "data_type": data_type,
        "scope": scope,
        "status": "unknown",
        "method": None,
        "filter_path": None,
        "page_count": 0,
        "data_point_count": 0,
        "top_level_keys": [],
        "attempts": attempts,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --no-sync pytest health/tests/test_discovery.py -v`
Expected: PASS (9 tests total)

- [ ] **Step 5: Commit**

```bash
git add health/src/health/discovery.py health/tests/test_discovery.py
git commit -m "feat(health): discover a data type's request shape by probing candidates"
```

---

### Task 3: Run discovery across every unimplemented data type

**Files:**
- Modify: `health/src/health/discovery.py`
- Modify: `health/tests/test_discovery.py`

**Interfaces:**
- Consumes: `discover_shape()` (Task 2), `health.endpoints.KNOWN_DATA_TYPES`, `CATALOG`
- Produces: `unimplemented_data_types(catalog=CATALOG, known=KNOWN_DATA_TYPES) -> list[tuple[str, str]]`（`(data_type, scope)`）と `run_discovery(client, output_dir: Path, today=None, report=None) -> dict`。`output_dir/discovery.json` を mode 600 で書く。

- [ ] **Step 1: Write the failing test**

```python
# append to health/tests/test_discovery.py
import json

from health.discovery import run_discovery, unimplemented_data_types


def test_unimplemented_excludes_every_data_type_the_catalog_covers():
    pairs = unimplemented_data_types()
    names = [data_type for data_type, _scope in pairs]
    assert "steps" not in names          # implemented
    assert "heart-rate" not in names     # implemented (intraday_hr)
    assert "exercise" in names           # not implemented
    assert "oxygen-saturation" in names  # sample stream is not implemented
    assert len(names) == len(set(names))


def test_run_discovery_writes_a_private_manifest_and_reports_each_type(tmp_path):
    client = FakeDiscoveryClient({(DAILY_ROLLUP, None): {"rollupDataPoints": []}})
    lines = []
    manifest = run_discovery(
        client, tmp_path, today=date(2026, 9, 7), report=lines.append,
        pairs=[("floors", "activity_and_fitness"), ("height", "health_metrics_and_measurements")],
    )

    assert set(manifest["data_types"]) == {"floors", "height"}
    assert manifest["data_types"]["floors"]["status"] == "empty"
    assert len(lines) == 2

    written = json.loads((tmp_path / "discovery.json").read_text())
    assert written["data_types"]["height"]["method"] == DAILY_ROLLUP
    assert (tmp_path / "discovery.json").stat().st_mode & 0o777 == 0o600
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest health/tests/test_discovery.py -v`
Expected: FAIL with `ImportError: cannot import name 'run_discovery'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to health/src/health/discovery.py
import json
import os
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from pathlib import Path

from health.endpoints import CATALOG, KNOWN_DATA_TYPES

DISCOVERY_WINDOW_DAYS = 7


def unimplemented_data_types(
    catalog: Sequence[Metric] = CATALOG,
    known: dict[str, tuple[str, str]] = KNOWN_DATA_TYPES,
) -> list[tuple[str, str]]:
    """Published data types with no CATALOG entry, as (data_type, scope)."""
    implemented = {metric.data_type for metric in catalog}
    return [
        (data_type, scope)
        for data_type, (_label, scope) in known.items()
        if data_type not in implemented
    ]


def run_discovery(
    client,
    output_dir: Path,
    today: date | None = None,
    report: Callable[[str], None] | None = None,
    pairs: Sequence[tuple[str, str]] | None = None,
) -> dict:
    """Probe every unimplemented data type and persist one manifest."""
    today = today or date.today()
    start = today - timedelta(days=DISCOVERY_WINDOW_DAYS - 1)
    pairs = unimplemented_data_types() if pairs is None else pairs

    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_dir, 0o700)
    manifest = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "window": {"start": start.isoformat(), "end": today.isoformat()},
        "data_types": {},
    }

    for data_type, scope in pairs:
        row = discover_shape(client, data_type, scope, start, today)
        manifest["data_types"][data_type] = row
        if report:
            report(
                f"{data_type}: {row['status']} "
                f"method={row['method']} filter={row['filter_path']} "
                f"points={row['data_point_count']}"
            )

    path = output_dir / "discovery.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    os.chmod(path, 0o600)
    return manifest
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --no-sync pytest health/tests/test_discovery.py -v`
Expected: PASS (11 tests total)

- [ ] **Step 5: Commit**

```bash
git add health/src/health/discovery.py health/tests/test_discovery.py
git commit -m "feat(health): run shape discovery across every unimplemented data type"
```

---

### Task 4: Loopback OAuth callback server

**Files:**
- Create: `health/src/health/oauth_loopback.py`
- Create: `health/tests/test_oauth_loopback.py`

**Interfaces:**
- Consumes: stdlib `http.server`, `urllib.parse`
- Produces: `LOOPBACK_PORT = 8765`, `REDIRECT_URI = "http://localhost:8765/"`, `serve_callback(port: int = LOOPBACK_PORT, timeout: float = 300.0) -> dict` — 1 リクエストだけ受けて `{"code", "state", "error", "error_description"}` を返す（欠けたキーは `None`）。タイムアウトで `TimeoutError`。

- [ ] **Step 1: Write the failing test**

```python
# health/tests/test_oauth_loopback.py
import threading
import urllib.request

import pytest
from health.oauth_loopback import REDIRECT_URI, serve_callback


def _call(port, query):
    urllib.request.urlopen(f"http://127.0.0.1:{port}/?{query}", timeout=5).read()


def _serve_then_request(query, port=8799):
    captured = {}

    def run():
        captured.update(serve_callback(port=port, timeout=10))

    thread = threading.Thread(target=run)
    thread.start()
    # The server binds before serving; retry briefly so the test is not racy.
    for _ in range(50):
        try:
            _call(port, query)
            break
        except OSError:
            threading.Event().wait(0.05)
    thread.join(timeout=10)
    return captured


def test_redirect_uri_matches_the_port_that_is_served():
    assert REDIRECT_URI == "http://localhost:8765/"


def test_authorization_code_and_state_are_captured():
    captured = _serve_then_request("code=abc123&state=xyz")
    assert captured["code"] == "abc123"
    assert captured["state"] == "xyz"
    assert captured["error"] is None


def test_denial_is_captured_as_an_error_not_a_code():
    captured = _serve_then_request("error=access_denied&error_description=denied", port=8798)
    assert captured["code"] is None
    assert captured["error"] == "access_denied"
    assert captured["error_description"] == "denied"


def test_timeout_raises_instead_of_blocking_forever():
    with pytest.raises(TimeoutError):
        serve_callback(port=8797, timeout=0.2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest health/tests/test_oauth_loopback.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'health.oauth_loopback'`

- [ ] **Step 3: Write minimal implementation**

```python
# health/src/health/oauth_loopback.py
"""One-shot loopback HTTP server that receives the OAuth callback.

Google's installed-app flow redirects to a localhost port. The CLI owns both
ends of the exchange, so this serves exactly one request and stops -- an
authorization code is single-use and a listener left running is a way to
replay it.
"""

from __future__ import annotations

import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

LOOPBACK_PORT = 8765
REDIRECT_URI = f"http://localhost:{LOOPBACK_PORT}/"

_PAGE = b"""<!doctype html><meta charset="utf-8">
<title>Health</title>
<p>Google Health への接続処理が完了しました。このタブは閉じて構いません。</p>
"""


class _CallbackHandler(BaseHTTPRequestHandler):
    captured: dict | None = None

    def do_GET(self) -> None:  # noqa: N802 -- BaseHTTPRequestHandler's fixed name
        query = parse_qs(urlparse(self.path).query)
        type(self).captured = {
            key: (query[key][0] if key in query else None)
            for key in ("code", "state", "error", "error_description")
        }
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(_PAGE)))
        self.end_headers()
        self.wfile.write(_PAGE)

    def log_message(self, *_args) -> None:
        """Silence the default stderr access log: the query holds an auth code."""


def serve_callback(port: int = LOOPBACK_PORT, timeout: float = 300.0) -> dict:
    """Serve exactly one callback request and return its query parameters."""
    handler = type("_OneShotHandler", (_CallbackHandler,), {"captured": None})
    server = HTTPServer(("127.0.0.1", port), handler)
    server.timeout = timeout
    try:
        server.handle_request()  # returns after one request or after `timeout`
    finally:
        server.server_close()

    if handler.captured is None:
        raise TimeoutError(f"no OAuth callback received on port {port} within {timeout}s")
    return handler.captured


def port_is_free(port: int = LOOPBACK_PORT) -> bool:
    """True when nothing is already listening on the loopback port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --no-sync pytest health/tests/test_oauth_loopback.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add health/src/health/oauth_loopback.py health/tests/test_oauth_loopback.py
git commit -m "feat(health): add a one-shot loopback server for the OAuth callback"
```

---

### Task 5: `health auth` — headless authorization

**Files:**
- Create: `health/src/health/cli.py`
- Create: `health/tests/test_cli.py`
- Modify: `health/src/health/auth.py:56-62`（`from_env` に `redirect_uri` を通す）
- Modify: `health/pyproject.toml`（`[project.scripts]`）
- Modify: `health/README.md`

**Interfaces:**
- Consumes: `GoogleHealthAuth.from_env`, `begin_auth`, `complete_auth`, `serve_callback` / `REDIRECT_URI` / `port_is_free` (Task 4)
- Produces: `main(argv: Sequence[str] | None = None) -> int`。`health auth` は 0 = 成功、2 = 認証エラー、3 = ポート使用中。

**Spec deviation (rationale):** spec は `auth.py` の `redirect_uri` **デフォルト**を変更するとしていたが、それだと Streamlit の接続導線が即座に壊れる。代わりに `from_env()` へ `redirect_uri` 引数を足し、CLI だけが loopback URI を渡す。デフォルトの `http://localhost:8501/` は据え置き。Streamlit は P4 で削除するまで無傷で動き、Console には**両方の URI を登録**する。

- [ ] **Step 1: Write the failing test**

```python
# health/tests/test_cli.py
import json
from pathlib import Path

import pytest
from health import cli
from health.auth import AuthError


class FakeAuth:
    def __init__(self, complete_error=None):
        self.complete_error = complete_error
        self.completed = None

    def begin_auth(self):
        return "https://accounts.google.com/o/oauth2/v2/auth?client_id=x"

    def complete_auth(self, code, state, error=None, error_description=None):
        if self.complete_error:
            raise self.complete_error
        self.completed = (code, state, error, error_description)


def test_auth_prints_the_url_and_completes_the_exchange(monkeypatch, capsys):
    auth = FakeAuth()
    monkeypatch.setattr(cli, "_build_auth", lambda _redirect: auth)
    monkeypatch.setattr(cli, "port_is_free", lambda _port: True)
    monkeypatch.setattr(cli, "serve_callback", lambda **_kw: {
        "code": "c1", "state": "s1", "error": None, "error_description": None})
    monkeypatch.setattr(cli, "_open_browser", lambda _url: None)

    assert cli.main(["auth"]) == 0
    assert auth.completed == ("c1", "s1", None, None)
    assert "accounts.google.com" in capsys.readouterr().out


def test_auth_refuses_to_start_when_the_loopback_port_is_taken(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_build_auth", lambda _redirect: FakeAuth())
    monkeypatch.setattr(cli, "port_is_free", lambda _port: False)

    assert cli.main(["auth"]) == 3
    assert "8765" in capsys.readouterr().err


def test_auth_reports_a_denied_consent_as_an_auth_error(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_build_auth",
                        lambda _redirect: FakeAuth(complete_error=AuthError("access_denied")))
    monkeypatch.setattr(cli, "port_is_free", lambda _port: True)
    monkeypatch.setattr(cli, "serve_callback", lambda **_kw: {
        "code": None, "state": None, "error": "access_denied", "error_description": None})
    monkeypatch.setattr(cli, "_open_browser", lambda _url: None)

    assert cli.main(["auth"]) == 2
    assert "access_denied" in capsys.readouterr().err


def test_from_env_passes_the_redirect_uri_through(tmp_path, monkeypatch):
    from health.auth import GoogleHealthAuth

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    auth = GoogleHealthAuth.from_env(
        tmp_path, env_path=tmp_path / "missing.env", redirect_uri="http://localhost:8765/"
    )
    assert auth.redirect_uri == "http://localhost:8765/"


def test_from_env_still_defaults_to_the_streamlit_redirect(tmp_path, monkeypatch):
    from health.auth import GoogleHealthAuth

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    auth = GoogleHealthAuth.from_env(tmp_path, env_path=tmp_path / "missing.env")
    assert auth.redirect_uri == "http://localhost:8501/"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest health/tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'health.cli'`

- [ ] **Step 3: Add the `redirect_uri` passthrough**

`health/src/health/auth.py` の `from_env` を置換する。

置換前:
```python
    @classmethod
    def from_env(cls, data_dir: Path, env_path: Path | None = None) -> GoogleHealthAuth:
        load_dotenv(env_path or Path(data_dir).parent / ".env")
        cid = os.environ.get("GOOGLE_CLIENT_ID")
        secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        if not cid or not secret:
            raise AuthError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set (health/.env)")
        return cls(cid, secret, Path(data_dir))
```

置換後:
```python
    @classmethod
    def from_env(
        cls,
        data_dir: Path,
        env_path: Path | None = None,
        redirect_uri: str | None = None,
    ) -> GoogleHealthAuth:
        """Build from `.env`. `redirect_uri` overrides the Streamlit default so
        the CLI can use its loopback port; both must be registered in the
        Google Cloud Console, which matches them exactly."""
        load_dotenv(env_path or Path(data_dir).parent / ".env")
        cid = os.environ.get("GOOGLE_CLIENT_ID")
        secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        if not cid or not secret:
            raise AuthError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set (health/.env)")
        if redirect_uri is None:
            return cls(cid, secret, Path(data_dir))
        return cls(cid, secret, Path(data_dir), redirect_uri=redirect_uri)
```

- [ ] **Step 4: Write the CLI**

```python
# health/src/health/cli.py
"""Headless entry point: authorize and synchronize without Streamlit."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from collections.abc import Sequence
from pathlib import Path

from health.auth import AuthError, GoogleHealthAuth
from health.oauth_loopback import LOOPBACK_PORT, REDIRECT_URI, port_is_free, serve_callback

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

EXIT_OK = 0
EXIT_AUTH = 2
EXIT_PORT_BUSY = 3


def _build_auth(redirect_uri: str | None) -> GoogleHealthAuth:
    return GoogleHealthAuth.from_env(DATA_DIR, redirect_uri=redirect_uri)


def _open_browser(url: str) -> None:
    """Best effort: under WSL there may be no browser, so the printed URL is
    the contract and this is only a convenience."""
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001 -- a missing browser must not fail the flow
        pass


def cmd_auth(args: argparse.Namespace) -> int:
    if not port_is_free(args.port):
        print(
            f"port {args.port} is already in use; stop whatever is listening and retry",
            file=sys.stderr,
        )
        return EXIT_PORT_BUSY

    auth = _build_auth(REDIRECT_URI if args.port == LOOPBACK_PORT
                       else f"http://localhost:{args.port}/")
    url = auth.begin_auth()
    print("Open this URL to authorize Google Health:")
    print(url)
    _open_browser(url)

    callback = serve_callback(port=args.port, timeout=args.timeout)
    try:
        auth.complete_auth(
            callback["code"],
            callback["state"],
            callback["error"],
            callback["error_description"],
        )
    except AuthError as exc:
        print(f"authorization failed: {exc}", file=sys.stderr)
        return EXIT_AUTH

    print("connected to Google Health")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="health", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    auth_parser = sub.add_parser("auth", help="authorize via a loopback redirect")
    auth_parser.add_argument("--port", type=int, default=LOOPBACK_PORT)
    auth_parser.add_argument("--timeout", type=float, default=300.0)
    auth_parser.set_defaults(func=cmd_auth)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except AuthError as exc:
        print(f"Google Health authentication error: {exc}", file=sys.stderr)
        return EXIT_AUTH


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Register the console script**

`health/pyproject.toml` の `[build-system]` の直前へ次を挿入する。

```toml
[project.scripts]
health = "health.cli:main"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run --no-sync pytest health/tests/test_cli.py health/tests/test_auth.py -v`
Expected: PASS（`test_auth.py:70` の `redirect_uri == "http://localhost:8501/"` はデフォルト据え置きのためそのまま通る）

- [ ] **Step 7: Document the second redirect URI**

`health/README.md` の手順 4 を置換する。

置換前:
```
4. Web application OAuth clientを作り、Authorized redirect URIへ
   `http://localhost:8501/`を完全一致で登録します。
```

置換後:
```
4. Web application OAuth clientを作り、Authorized redirect URIへ次の2つを
   完全一致で登録します。

   - `http://localhost:8501/` — Streamlit UIからの接続用
   - `http://localhost:8765/` — CLI（`health auth`）からの接続用

   CLIだけを使う場合も、Streamlit UIを残すあいだは両方を登録しておきます。
```

さらに「起動・接続・同期」節の冒頭へ次を追記する。

```
Streamlitを起動せずに認可と同期を実行できます。

```bash
uv run --no-sync health auth   # ブラウザで同意し、loopbackでcodeを受ける
```

`health auth`は`http://localhost:8765/`で1リクエストだけ待ち受け、受け取ったら
即座に停止します。ポートが塞がっている場合はexit code 3で止まります。
```

- [ ] **Step 8: Commit**

```bash
git add health/src/health/cli.py health/src/health/auth.py health/tests/test_cli.py \
        health/pyproject.toml health/README.md
git commit -m "feat(health): add a headless 'health auth' command over a loopback redirect"
```

---

### Task 6: `health sync` — headless synchronization

**Files:**
- Modify: `health/src/health/cli.py`
- Modify: `health/tests/test_cli.py`
- Modify: `health/README.md`

**Interfaces:**
- Consumes: `health.sync.SyncEngine`, `SyncReport`, `MetricFailure`, `MAX_REQUESTS_PER_RUN`, `health.store.Store`, `health.client.HealthClient`
- Produces: `cmd_sync(args) -> int`。exit code は 0 = 全メトリクス成功、1 = 一部失敗、2 = 引数/認証エラー、4 = rate limited で中断、5 = リクエスト上限で中断。

**実シグネチャの確認結果（読んで確定済み。推測で書かないこと）:**

| 事実 | 値 |
|---|---|
| コンストラクタ | `SyncEngine(client, store, catalog=CATALOG, today=None, environ=None, max_requests=MAX_REQUESTS_PER_RUN)` — **`client` が第1引数、`store` が第2引数** |
| `sync_all` | `sync_all(progress_cb: Callable[[str, str], None] \| None = None) -> SyncReport` |
| `progress_cb` の第2引数 | phase ではなく `"{request_start} → {request_end} ({used} requests)"` という詳細文字列 |
| **429 の扱い** | `RateLimited` は `sync_all` の外へ**出ない**。`_guarded` が捕まえて `report.paused = True` / `report.resume_in_s = exc.retry_after_s` を立て、`_RunFinished` として run を止める |
| リクエスト上限 | 同様に `report.stopped_early = True` になる。例外は出ない |
| `SyncReport` のフィールド | `progress` / `failures` / `history_remaining` / `paused` / `resume_in_s` / `stopped_early` / `requests_made` |

したがって `cmd_sync` は **`RateLimited` を except しない**。`report.paused` と `report.stopped_early` を見て分岐する。

- [ ] **Step 1: Write the failing test**

```python
# append to health/tests/test_cli.py
from health.sync import MetricFailure, SyncReport


class FakeEngine:
    def __init__(self, report):
        self.report = report
        self.progress = []

    def sync_all(self, progress_cb=None):
        if progress_cb:
            # Mirrors the real callback: (metric name, detail string).
            progress_cb("steps", "2026-09-01 → 2026-09-07 (3 requests)")
            self.progress.append("steps")
        return self.report


def test_sync_reports_progress_on_stderr_and_exits_zero(monkeypatch, capsys):
    engine = FakeEngine(SyncReport())
    monkeypatch.setattr(cli, "_build_engine", lambda _cap: engine)

    assert cli.main(["sync"]) == 0
    captured = capsys.readouterr()
    assert "steps" in captured.err
    assert "3 requests" in captured.err
    assert engine.progress == ["steps"]


def test_sync_exits_one_and_names_each_failed_metric(monkeypatch, capsys):
    report = SyncReport(failures=[
        MetricFailure(metric="spo2", kind="api", status_code=403, message="forbidden")
    ])
    monkeypatch.setattr(cli, "_build_engine", lambda _cap: FakeEngine(report))

    assert cli.main(["sync"]) == 1
    err = capsys.readouterr().err
    assert "spo2" in err and "403" in err


def test_rate_limiting_is_read_off_the_report_not_caught_as_an_exception(monkeypatch, capsys):
    report = SyncReport()
    report.paused = True
    report.resume_in_s = 90
    monkeypatch.setattr(cli, "_build_engine", lambda _cap: FakeEngine(report))

    assert cli.main(["sync"]) == 4
    assert "90" in capsys.readouterr().err


def test_hitting_the_request_cap_exits_five_so_the_user_knows_to_rerun(monkeypatch, capsys):
    report = SyncReport()
    report.stopped_early = True
    monkeypatch.setattr(cli, "_build_engine", lambda _cap: FakeEngine(report))

    assert cli.main(["sync"]) == 5
    assert "again" in capsys.readouterr().err.lower()


def test_sync_passes_the_requested_cap_to_the_engine(monkeypatch):
    seen = {}

    def build(cap):
        seen["cap"] = cap
        return FakeEngine(SyncReport())

    monkeypatch.setattr(cli, "_build_engine", build)
    assert cli.main(["sync", "--cap", "500"]) == 0
    assert seen["cap"] == 500


def test_sync_rejects_a_cap_below_the_forward_pass_floor(capsys):
    assert cli.main(["sync", "--cap", "1"]) == 2
    assert "cap" in capsys.readouterr().err.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest health/tests/test_cli.py -v`
Expected: FAIL with `AttributeError: module 'health.cli' has no attribute '_build_engine'`

- [ ] **Step 3: Write the implementation**

```python
# append to health/src/health/cli.py
from health.client import HealthClient
from health.store import Store
from health.sync import MAX_REQUESTS_PER_RUN, SyncEngine

EXIT_PARTIAL = 1
EXIT_RATE_LIMITED = 4
EXIT_CAPPED = 5

# The forward pass must be able to touch every metric at least once, or a run
# makes no progress at all and silently looks like success.
MIN_CAP = 50


def _build_engine(cap: int) -> SyncEngine:
    """`SyncEngine` takes the client first and the store second."""
    auth = _build_auth(None)
    store = Store(DATA_DIR / "health.duckdb")
    return SyncEngine(HealthClient(auth), store, max_requests=cap)


def cmd_sync(args: argparse.Namespace) -> int:
    if args.cap < MIN_CAP:
        print(f"--cap must be at least {MIN_CAP}", file=sys.stderr)
        return EXIT_AUTH

    engine = _build_engine(args.cap)
    # 429 and the request cap never escape sync_all: the engine records them
    # on the report and stops the run, so read the report rather than catching.
    report = engine.sync_all(
        progress_cb=lambda metric, detail: print(f"{metric}: {detail}", file=sys.stderr)
    )

    for failure in report.failures:
        status = f" HTTP {failure.status_code}" if failure.status_code else ""
        print(f"failed: {failure.metric}{status} — {failure.message}", file=sys.stderr)

    if report.paused:
        print(f"rate limited; retry after {report.resume_in_s}s", file=sys.stderr)
        return EXIT_RATE_LIMITED
    if report.failures:
        return EXIT_PARTIAL
    if report.stopped_early:
        print("hit the request cap; run sync again to continue", file=sys.stderr)
        return EXIT_CAPPED

    print(f"sync complete ({report.requests_made} requests)")
    return EXIT_OK
```

`build_parser()` の `return parser` の直前へ次を挿入する。

```python
    sync_parser = sub.add_parser("sync", help="fetch new data into the local DuckDB")
    sync_parser.add_argument(
        "--cap",
        type=int,
        default=MAX_REQUESTS_PER_RUN,
        help=f"maximum API requests for this run (minimum {MIN_CAP})",
    )
    sync_parser.set_defaults(func=cmd_sync)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync pytest health/tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Run the whole health suite for regressions**

Run: `uv run --no-sync pytest health/tests -q`
Expected: PASS、件数は 258 + 新規分

- [ ] **Step 6: Document the sync command**

`health/README.md` の Task 5 で追記したブロックへ続けて書く。

```
```bash
uv run --no-sync health sync              # 既定200 requests
uv run --no-sync health sync --cap 500    # 1回で多く進める
```

exit codeは 0=全メトリクス成功 / 1=一部失敗（失敗したメトリクス名をstderrへ）/
2=引数・認証エラー / 3=ポート使用中 / 4=rate limitedで中断 / 5=リクエスト上限で中断。
5のときはもう一度`health sync`を実行すると続きから進みます。
```

- [ ] **Step 7: Commit**

```bash
git add health/src/health/cli.py health/tests/test_cli.py health/README.md
git commit -m "feat(health): add a headless 'health sync' command"
```

---

### Task 7: Wire discovery into the probe script

**Files:**
- Modify: `health/scripts/probe_datatypes.py`
- Modify: `health/tests/test_probe_datatypes.py`
- Modify: `health/README.md`

**Interfaces:**
- Consumes: `run_discovery()` (Task 3), `run_probe()`
- Produces: `probe_datatypes.py --discover` が `data/probe/discovery.json` を書く。引数なしの既存挙動は変えない。

- [ ] **Step 1: Write the failing test**

```python
# append to health/tests/test_probe_datatypes.py
#
# `scripts/` is not a package on sys.path by default. `tests/test_export_data.py`
# already establishes the house pattern for reaching it; copy it exactly rather
# than inventing a second one.
import sys
from pathlib import Path

HEALTH_DIR = Path(__file__).resolve().parents[1]
if str(HEALTH_DIR) not in sys.path:
    sys.path.insert(0, str(HEALTH_DIR))

import scripts.probe_datatypes as probe_script  # noqa: E402


def test_discover_flag_runs_discovery_instead_of_the_catalog_probe(monkeypatch, tmp_path, capsys):
    called = {}

    def fake_run_discovery(_client, output_dir, report=None):
        called["output_dir"] = output_dir
        if report:
            report("floors: empty method=daily_rollup filter=None points=0")
        return {"data_types": {}}

    monkeypatch.setattr(probe_script, "DEFAULT_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(probe_script, "GoogleHealthAuth", type(
        "A", (), {"from_env": staticmethod(lambda _d: object())}))
    monkeypatch.setattr(probe_script, "HealthClient", lambda _auth: object())
    monkeypatch.setattr(probe_script, "run_discovery", fake_run_discovery)
    monkeypatch.setattr(probe_script, "run_probe", lambda *a, **k:
                        pytest.fail("run_probe must not run with --discover"))

    assert probe_script.main(["--discover"]) == 0
    assert called["output_dir"] == tmp_path
    assert "discovery.json" in capsys.readouterr().out


def test_no_flag_still_runs_the_catalog_probe(monkeypatch, tmp_path):
    ran = {}
    monkeypatch.setattr(probe_script, "DEFAULT_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(probe_script, "GoogleHealthAuth", type(
        "A", (), {"from_env": staticmethod(lambda _d: object())}))
    monkeypatch.setattr(probe_script, "HealthClient", lambda _auth: object())
    monkeypatch.setattr(probe_script, "run_probe", lambda *a, **k: ran.setdefault("yes", True))

    assert probe_script.main([]) == 0
    assert ran["yes"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest health/tests/test_probe_datatypes.py -v`
Expected: FAIL — `main()` が引数を受け取らない（`TypeError`）

- [ ] **Step 3: Write the implementation**

`health/scripts/probe_datatypes.py` の `main` を置換する。

置換前:
```python
def main() -> int:
    try:
        auth = GoogleHealthAuth.from_env(DATA_DIR)
        run_probe(HealthClient(auth), DEFAULT_OUTPUT_DIR, report=print)
    except AuthError as exc:
        print(f"Google Health authentication error: {exc}", file=sys.stderr)
        return 2
    print(f"manifest: {DEFAULT_OUTPUT_DIR / 'manifest.json'}")
    return 0
```

置換後:
```python
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--discover",
        action="store_true",
        help="probe the UNIMPLEMENTED data types to learn their request shape",
    )
    args = parser.parse_args(argv)

    try:
        auth = GoogleHealthAuth.from_env(DATA_DIR)
        client = HealthClient(auth)
        if args.discover:
            run_discovery(client, DEFAULT_OUTPUT_DIR, report=print)
            print(f"manifest: {DEFAULT_OUTPUT_DIR / 'discovery.json'}")
            return 0
        run_probe(client, DEFAULT_OUTPUT_DIR, report=print)
    except AuthError as exc:
        print(f"Google Health authentication error: {exc}", file=sys.stderr)
        return 2
    print(f"manifest: {DEFAULT_OUTPUT_DIR / 'manifest.json'}")
    return 0
```

import を追加する。

```python
import argparse
from collections.abc import Sequence

from health.discovery import run_discovery
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync pytest health/tests/test_probe_datatypes.py -v`
Expected: PASS

- [ ] **Step 5: Document the discovery run**

`health/README.md` の「Acceptance probe」節の末尾へ追記する。

```
未実装データ型のrequest shapeを実測するには`--discover`を付けます。

```bash
uv run --no-sync python health/scripts/probe_datatypes.py --discover
```

各データ型についてdailyRollUpを先に試し、拒否されたらreconcileのfilter path候補を
順に試します。結果は`health/data/probe/discovery.json`へ書かれ、DuckDBには
書きません。`status`は`ok`（データあり）/`empty`（shapeは通ったがデータ0件）/
`unknown`（全候補が拒否された）です。

**discovery.jsonも実際のprivate health dataです。共有・commitしないでください。**
```

- [ ] **Step 6: Commit**

```bash
git add health/scripts/probe_datatypes.py health/tests/test_probe_datatypes.py health/README.md
git commit -m "feat(health): add --discover to probe unimplemented data type shapes"
```

---

### Task 8: Verify the whole suite and record the discovery result

**Files:**
- Modify: `health/docs/2026-09-07-data-type-discovery.md`（新規作成）

**Interfaces:**
- Consumes: 全タスクの成果物
- Produces: 22 型の shape 表。Plan B（CATALOG 拡張）の入力になる。

- [ ] **Step 1: Run the full health suite**

Run: `uv run --no-sync pytest health/tests -q`
Expected: PASS。失敗が出たら次へ進まず原因を特定する。

- [ ] **Step 2: Run lint**

Run: `uv run ruff check health/`
Expected: エラーなし。`ruff check --select` を付けたまま `--fix` しないこと（必要な noqa が消える）。

- [ ] **Step 3: Authorize with the new CLI**

Run: `uv run --no-sync health auth`

**先に Google Cloud Console で `http://localhost:8765/` を Authorized redirect URI へ完全一致登録しておくこと。** 未登録だと Google 側が `redirect_uri_mismatch` を返す。

- [ ] **Step 4: Run discovery against the live API**

Run: `uv run --no-sync python health/scripts/probe_datatypes.py --discover`

これは live API を叩く**手動**の確認であり、自動テストではない。22 型 × 最大 5 候補 = 最大 110 requests。429 が出たら表示された秒数を待って再実行する。

- [ ] **Step 5: Record the findings**

`health/data/probe/discovery.json` を読み、`health/docs/2026-09-07-data-type-discovery.md` へ**データ値を含めずに** shape だけを書き出す。

必須の列: `data_type` / `status` / `method` / `filter_path` / `data_point_count` / 備考。
`status=unknown` の型は「未確定」として残し、Plan B では CATALOG に追加しない。

`intraday` を 30 日より深く取れるかの確認結果もこのファイルに記録する（spec の R-2）。

- [ ] **Step 6: Commit**

```bash
git add health/docs/2026-09-07-data-type-discovery.md
git commit -m "docs(health): record the discovered request shapes for unimplemented data types"
```

**`health/data/probe/discovery.json` は commit しない**（`health/.gitignore` の `/data/` が既にカバーしている)。

---

## Out of scope for this plan

- `CATALOG` の 35 型拡張 — Task 8 の結果を入力として **Plan B** で扱う。
- エクスポート層と Next.js フロント — **Plan C**。
- `INTRADAY_LOOKBACK_DAYS` の変更 — Task 8 で事実を確定させるだけ。変更は Plan B。
- Streamlit の削除 — Plan C の最後。
