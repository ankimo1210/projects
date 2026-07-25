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

    def __init__(self):
        self.checkpoint_calls = 0

    def checkpoint(self):
        self.checkpoint_calls += 1


class FakeStreamlit:
    def __init__(self):
        self.cache_data = FakeCacheData()
        self.session_state = {}
        self.errors = []
        self.warnings = []
        self.infos = []

    def status(self, *_args, **_kwargs):
        return nullcontext(type("Status", (), {"write": lambda *_args: None})())

    def error(self, message):
        self.errors.append(message)

    def warning(self, message):
        self.warnings.append(message)

    def info(self, message):
        self.infos.append(message)

    def caption(self, _message):
        pass

    def rerun(self):
        raise AssertionError("error outcomes must not rerun")


def test_run_sync_invalidates_cache_after_partial_success_then_api_error(monkeypatch):
    fake_st = FakeStreamlit()
    fake_store = FakeStore()
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
    monkeypatch.setattr(sync_view, "get_store", lambda: fake_store)

    sync_view._run_sync(object(), 200)

    assert committed == ["chunk"]
    assert fake_st.cache_data.clear_calls == 1
    assert fake_st.session_state == {}
    assert fake_st.errors == ["Google Health API エラー（HTTP 500）: later chunk failed"]
    assert fake_store.checkpoint_calls == 1


def test_run_sync_passes_the_selected_cap_and_records_failures(monkeypatch):
    fake_st = FakeStreamlit()
    fake_st.rerun = lambda: None
    fake_store = FakeStore()
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
    monkeypatch.setattr(sync_view, "get_store", lambda: fake_store)

    sync_view._run_sync(object(), 500)

    assert seen["max_requests"] == 500
    assert fake_st.session_state["last_sync_report"]["failures"] == [
        {"metric": "sleep", "kind": "api", "status_code": 403, "message": "insufficient scope"}
    ]
    assert fake_st.session_state["last_sync_report"]["history_remaining"] == 4
    assert fake_st.session_state["last_sync_report"]["max_requests"] == 500
    assert fake_store.checkpoint_calls == 1


def test_show_last_report_renders_selected_cap_and_localized_failures(monkeypatch):
    fake_st = FakeStreamlit()
    monkeypatch.setattr(sync_view, "st", fake_st)
    fake_st.session_state["last_sync_report"] = {
        "paused": False,
        "resume_in_s": None,
        "stopped_early": True,
        "requests_made": 500,
        "max_requests": 500,
        "history_remaining": 3,
        "failures": [
            {"metric": "sleep", "kind": "api", "status_code": 403, "message": "insufficient scope"},
            {"metric": "steps", "kind": "payload", "status_code": None, "message": "bad json"},
        ],
    }

    sync_view._show_last_report()

    # Finding 1: the stopped-early warning must name the selected cap, not the
    # module default (200), and the report dict is gone from session_state
    # afterwards regardless of outcome.
    stopped_early_warning = next(m for m in fake_st.warnings if "実行上限" in m)
    assert "500 requests" in stopped_early_warning
    assert "200 requests" not in stopped_early_warning
    assert "last_sync_report" not in fake_st.session_state

    # Finding 2: kind is localized, the HTTP fragment only appears when there
    # is a status code, and no double space is left behind when it is absent.
    api_warning = next(m for m in fake_st.warnings if "sleep" in m)
    assert "API エラー" in api_warning
    assert "HTTP 403" in api_warning

    payload_warning = next(m for m in fake_st.warnings if "steps" in m)
    assert "データ解析エラー" in payload_warning
    assert "HTTP" not in payload_warning
    assert "  " not in payload_warning

    assert any("3 chunk" in message for message in fake_st.infos)
