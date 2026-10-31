"""Real loopback HTTP tests: read-only browsing and explicit update boundary."""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
import urllib.error
import urllib.request
from html.parser import HTMLParser
from importlib import import_module

import pytest


class SnapshotParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.payload = ""
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts += 1
            self.active = dict(attrs).get("id") == "tracker-data"

    def handle_endtag(self, tag):
        if tag == "script":
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.payload += data


@pytest.fixture
def live_server(tmp_path, monkeypatch):
    module = import_module("market_research.megacap_server")

    def blocked(*_args, **_kwargs):
        raise AssertionError("GET must not trigger acquisition")

    monkeypatch.setattr(module, "collect_snapshot", blocked)
    server = module.TrackerServer(("127.0.0.1", 0), tmp_path / "snapshot.json")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}", module
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_html_embedding_preserves_json_without_injecting_script():
    module = import_module("market_research.megacap_server")
    snapshot = {
        "schema_version": 1,
        "companies": [],
        "note": '</script><script>alert("x")</script>&',
    }
    parser = SnapshotParser()
    parser.feed(module.render_html(snapshot))
    assert json.loads(parser.payload) == snapshot
    assert parser.scripts == 2  # JSON payload and the offline application.


def test_get_reads_snapshot_without_fetching(live_server):
    _, base, _ = live_server
    with urllib.request.urlopen(base + "/api/snapshot") as response:
        assert json.load(response)["companies"] == []
    with urllib.request.urlopen(base + "/") as response:
        assert response.status == 200
        parser = SnapshotParser()
        parser.feed(response.read().decode())
        assert json.loads(parser.payload)["companies"] == []


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-Tracker-Request": "refresh", "Origin": "https://other.example"},
        {"X-Tracker-Request": "refresh", "Host": "attacker.example"},
    ],
)
def test_cross_origin_or_implicit_update_is_rejected(live_server, headers):
    _, base, _ = live_server
    request = urllib.request.Request(
        base + "/api/refresh", data=b"{}", headers=headers, method="POST"
    )
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(request)
    assert caught.value.code == 403


def test_explicit_update_saves_snapshot_and_offline_document(live_server, monkeypatch):
    server, base, module = live_server
    snapshot = {"schema_version": 1, "attempted_at": "2026-10-27T01:00:00+00:00", "companies": []}
    monkeypatch.setattr(module, "collect_snapshot", lambda previous: snapshot)
    request = urllib.request.Request(
        base + "/api/refresh",
        data=b"{}",
        method="POST",
        headers={"X-Tracker-Request": "refresh", "Origin": base},
    )
    with urllib.request.urlopen(request) as response:
        assert json.load(response) == snapshot
    assert json.loads(server.snapshot_path.read_text()) == snapshot
    parser = SnapshotParser()
    parser.feed(server.snapshot_path.with_name("index.html").read_text())
    assert json.loads(parser.payload) == snapshot


NODE = shutil.which("node")


def run_logic(expression, **values):
    """Evaluate the page's DOM-free helpers in node, exactly as shipped in the template."""
    module = import_module("market_research.megacap_server")
    html = module.TEMPLATE.read_text(encoding="utf-8")
    block = html.split("/* tracker-logic:start */")[1].split("/* tracker-logic:end */")[0]
    bindings = "".join(f"const {key}={json.dumps(value)};" for key, value in values.items())
    code = f"{block}\n{bindings}\nprocess.stdout.write(JSON.stringify({expression}));"
    result = subprocess.run(
        [NODE, "-e", code], capture_output=True, text=True, check=True, timeout=30
    )
    return json.loads(result.stdout)


@pytest.mark.skipif(NODE is None, reason="node is required to run the page logic")
def test_browser_marks_results_announced_after_the_snapshot():
    company = {
        "fetched_at": "2026-10-27T15:01:15+00:00",
        "earnings": {"timestamp": "2026-10-28T20:05:00+00:00"},
    }
    window = {
        "fetched_at": "2026-10-27T15:01:15+00:00",
        "earnings": {
            "timestamp": "2026-10-26T21:00:00+00:00",
            "window_end": "2026-10-30T21:00:00+00:00",
            "is_estimate": True,
        },
    }
    # MSFT pattern: the last release sits in `previous`, the next estimate on top.
    rolled = {
        "fetched_at": "2026-10-27T15:01:15+00:00",
        "earnings": {
            "timestamp": "2027-01-27T20:00:00+00:00",
            "date_et": "2027-01-27",
            "previous": {"timestamp": "2026-10-28T20:00:00+00:00", "date_et": "2026-10-28"},
        },
    }
    kinds = run_logic(
        "[earningsState(c, Date.parse('2026-10-28T12:00:00Z')).kind,"
        " earningsState(c, Date.parse('2026-10-31T03:00:00Z')).kind,"
        " earningsState({...c, fetched_at: '2026-10-29T00:00:00Z'}, Date.parse('2026-10-31T03:00:00Z')).kind,"
        " earningsState({fetched_at: c.fetched_at, earnings: {}}, 0).kind,"
        " earningsState(w, Date.parse('2026-10-28T12:00:00Z')).kind,"
        " earningsState(r, Date.parse('2026-10-31T03:00:00Z')).event.date_et,"
        " earningsState({...r, fetched_at: '2026-10-31T03:56:00Z'}, Date.parse('2026-10-31T05:00:00Z')).kind]",
        c=company,
        w=window,
        r=rolled,
    )
    assert kinds == [
        "upcoming",
        "needs_refresh",
        "reported",
        "none",
        "upcoming",
        "2026-10-28",
        "upcoming",
    ]


@pytest.mark.skipif(NODE is None, reason="node is required to run the page logic")
def test_browser_reports_snapshot_age():
    ages = run_logic(
        "[snapshotAge(t, Date.parse('2026-10-31T03:10:00Z')),"
        " snapshotAge(t, Date.parse('2026-10-27T17:30:00Z')), snapshotAge(null, 0)]",
        t="2026-10-27T15:01:17+00:00",
    )
    assert ages[0]["text"] == "3日前" and ages[0]["stale"] is True
    assert ages[1]["text"] == "2時間前" and ages[1]["stale"] is False
    assert ages[2] is None


@pytest.mark.skipif(NODE is None, reason="node is required to run the page logic")
def test_bar_scale_clips_outliers_instead_of_flattening_the_rest():
    # PER (TTM) on 2026-10-27: TSLA's 442.8 made the other six bars 3.6-9% wide.
    widths = run_logic(
        "(() => { const s = barScale(v); return v.map(x => [barWidth(x, s), barClipped(x, s)]); })()",
        v=[39.8, 29.7, 16.1, 20.3, 21.4, 27.5, 442.8, None],
    )
    assert widths[-2] == [100, True]
    assert widths[0][0] == pytest.approx(39.8 / (27.5 * 3) * 100)
    assert widths[0][1] is False
    assert widths[-1] == [0, False]


@pytest.mark.skipif(NODE is None, reason="node is required to run the page logic")
def test_basis_groups_list_each_distinct_period():
    groups = run_logic(
        "[basisGroups(a), basisGroups(b), basisGroups({})]",
        a={
            "basis": {
                "eps": "2026-06-30",
                "provider": "2026-06-30",
                "income_ttm": "2026-03-31",
                "cashflow_ttm": "2026-03-31",
                "balance": "2026-03-31",
            }
        },
        b={"basis": {"eps": "2026-09-30", "income_ttm": "2026-09-30"}},
    )
    assert groups[0] == [["2026-06-30", ["EPS", "BPS"]], ["2026-03-31", ["損益", "CF", "BS"]]]
    assert groups[1] == [["2026-09-30", ["EPS", "損益"]]]
    assert groups[2] == []


def test_offline_download_has_attachment_header(live_server):
    _, base, _ = live_server
    with urllib.request.urlopen(base + "/download.html") as response:
        assert "attachment" in response.headers["Content-Disposition"]
        assert response.headers["Content-Type"].startswith("text/html")
