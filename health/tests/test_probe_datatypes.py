from datetime import date

import pytest
from health.auth import AuthError
from health.client import ApiError
from health.endpoints import DAILY_ROLLUP, RECONCILE, Metric, ParsedRows
from health.probe import probe_range, run_probe


def metric(name, method, full_history=True):
    return Metric(
        name=name,
        data_type=name,
        method=method,
        max_range_days=90,
        scope="scope",
        full_history=full_history,
        series_names=(name,),
        parse_pages=lambda _pages: ParsedRows(),
        filter_path="point.date" if method == RECONCILE else None,
    )


class FakeClient:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def daily_rollup(self, item, start, end, _budget):
        return self._result(item, start, end)[0]

    def iter_reconciled(self, item, start, end, _budget):
        yield from self._result(item, start, end)

    def _result(self, item, start, end):
        self.calls.append((item.name, start, end))
        value = self.results[item.name]
        if isinstance(value, Exception):
            raise value
        return value


def test_probe_ranges_are_seven_thirty_and_one_day():
    today = date(2026, 7, 20)
    assert probe_range(metric("rollup", DAILY_ROLLUP), today) == (
        date(2026, 7, 14),
        today,
    )
    assert probe_range(metric("daily", RECONCILE), today) == (
        date(2026, 6, 21),
        today,
    )
    assert probe_range(metric("intraday", RECONCILE, False), today) == (today, today)


def test_probe_saves_every_page_and_shape_manifest(tmp_path):
    item = metric("paged", RECONCILE)
    pages = [
        {"dataPoints": [{"x": 1}], "nextPageToken": "next"},
        {"dataPoints": [{"x": 2}, {"x": 3}]},
    ]
    manifest = run_probe(FakeClient({"paged": pages}), tmp_path, [item], date(2026, 7, 20))
    entry = manifest["metrics"]["paged"]
    assert entry["status"] == "ok"
    assert entry["page_count"] == 2
    assert entry["data_point_count"] == 3
    assert entry["top_level_keys"] == ["dataPoints", "nextPageToken"]
    assert (tmp_path / "paged" / "page-000.json").exists()
    assert (tmp_path / "paged" / "page-001.json").exists()
    assert (tmp_path / "manifest.json").exists()


def test_api_error_is_recorded_and_next_metric_continues(tmp_path):
    failing = metric("forbidden", RECONCILE)
    empty = metric("empty", DAILY_ROLLUP)
    client = FakeClient(
        {
            "forbidden": ApiError(403, "missing scope"),
            "empty": [{"rollupDataPoints": []}],
        }
    )
    manifest = run_probe(client, tmp_path, [failing, empty], date(2026, 7, 20))
    assert manifest["metrics"]["forbidden"]["status"] == "error"
    assert manifest["metrics"]["forbidden"]["error_status"] == 403
    assert manifest["metrics"]["empty"]["status"] == "empty"
    assert [call[0] for call in client.calls] == ["forbidden", "empty"]


def test_auth_error_stops_remaining_metrics(tmp_path):
    first = metric("expired", RECONCILE)
    second = metric("never", RECONCILE)
    client = FakeClient({"expired": AuthError("expired"), "never": [{"dataPoints": []}]})
    with pytest.raises(AuthError, match="expired"):
        run_probe(client, tmp_path, [first, second], date(2026, 7, 20))
    assert [call[0] for call in client.calls] == ["expired"]
    saved = (tmp_path / "manifest.json").read_text()
    assert '"expired"' in saved and '"status": "error"' in saved


def _load_probe_script():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "probe_script_for_test", Path(__file__).parents[1] / "scripts" / "probe_datatypes.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_sources_cli_uses_bounded_runner_without_real_credentials(tmp_path, monkeypatch):
    script = _load_probe_script()
    auth = object()
    calls = []
    monkeypatch.setattr(script.GoogleHealthAuth, "from_env", lambda *_a, **_kw: auth)
    monkeypatch.setattr(script, "HealthClient", lambda value: value)

    def run(client, out, sources, **kwargs):
        calls.append((client, out, sources, kwargs))
        return {"stopped_reason": None, "sources": {}}

    monkeypatch.setattr(script, "run_source_probe", run)
    assert script.main(["--all-sources", "--max-requests", "3", "--output-dir", str(tmp_path)]) == 0
    assert calls[0][0] is auth
    assert calls[0][1] == tmp_path
    assert calls[0][2]
    assert calls[0][3]["max_requests"] == 3


def test_probe_cli_bad_budget_does_not_load_credentials(monkeypatch):
    script = _load_probe_script()

    def forbidden(*_a, **_kw):
        pytest.fail("must validate arguments before loading auth")

    monkeypatch.setattr(script.GoogleHealthAuth, "from_env", forbidden)
    with pytest.raises(SystemExit) as exc:
        script.main(["--all-sources", "--max-requests", "-1"])
    assert exc.value.code == 2
