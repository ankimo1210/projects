from __future__ import annotations

import sys
from contextlib import nullcontext
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from health.client import ApiError  # noqa: E402
from health.sync import MetricFailure, SyncReport  # noqa: E402
from views import sync_view  # noqa: E402


class FakeCacheData:
    def __init__(self):
        self.clear_calls = 0

    def clear(self):
        self.clear_calls += 1


class FakeStore:
    """Stand-in for `Store` in `_run_sync`'s `finally` block, which always
    checkpoints -- even on the error paths -- since the engine commits one
    completed chunk at a time and a later failure can follow real writes."""

    def checkpoint(self):
        pass


class FakeStreamlit:
    def __init__(self):
        self.cache_data = FakeCacheData()
        self.session_state = {}
        self.errors = []
        self.warnings = []

    def status(self, *_args, **_kwargs):
        return nullcontext(type("Status", (), {"write": lambda *_args: None})())

    def error(self, message):
        self.errors.append(message)

    def warning(self, message):
        self.warnings.append(message)

    def caption(self, _message):
        pass

    def rerun(self):
        raise AssertionError("error outcomes must not rerun")


def test_run_sync_invalidates_cache_after_partial_success_then_api_error(monkeypatch):
    fake_st = FakeStreamlit()
    committed = []

    class FailingEngine:
        def __init__(self, _client, _store, max_requests=None):
            pass

        def sync_all(self, progress_cb):
            committed.append("chunk")
            progress_cb("steps", "2026-07-01 → 2026-07-20")
            raise ApiError(500, "later chunk failed")

    monkeypatch.setattr(sync_view, "st", fake_st)
    monkeypatch.setattr(sync_view, "SyncEngine", FailingEngine)
    monkeypatch.setattr(sync_view, "HealthClient", lambda _auth: object())
    monkeypatch.setattr(sync_view, "get_store", lambda: FakeStore())

    sync_view._run_sync(object(), 200)

    assert committed == ["chunk"]
    assert fake_st.cache_data.clear_calls == 1
    assert fake_st.session_state == {}
    assert fake_st.errors == ["Google Health API エラー（HTTP 500）: later chunk failed"]


def test_run_sync_passes_the_selected_cap_and_records_failures(monkeypatch):
    fake_st = FakeStreamlit()
    fake_st.rerun = lambda: None
    seen = {}

    class RecordingEngine:
        def __init__(self, _client, _store, max_requests=None):
            seen["max_requests"] = max_requests

        def sync_all(self, progress_cb):
            return SyncReport(
                failures=[MetricFailure("sleep", "api", 403, "insufficient scope")],
                history_remaining={"sleep": 4},
                requests_made=12,
            )

    monkeypatch.setattr(sync_view, "st", fake_st)
    monkeypatch.setattr(sync_view, "SyncEngine", RecordingEngine)
    monkeypatch.setattr(sync_view, "HealthClient", lambda _auth: object())
    monkeypatch.setattr(sync_view, "get_store", lambda: FakeStore())

    sync_view._run_sync(object(), 500)

    assert seen["max_requests"] == 500
    assert fake_st.session_state["last_sync_report"]["failures"] == [
        {"metric": "sleep", "kind": "api", "status_code": 403, "message": "insufficient scope"}
    ]
    assert fake_st.session_state["last_sync_report"]["history_remaining"] == 4
