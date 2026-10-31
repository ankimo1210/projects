"""Real loopback HTTP tests: read-only browsing and explicit update boundary."""

from __future__ import annotations

import json
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


def test_offline_download_has_attachment_header(live_server):
    _, base, _ = live_server
    with urllib.request.urlopen(base + "/download.html") as response:
        assert "attachment" in response.headers["Content-Disposition"]
        assert response.headers["Content-Type"].startswith("text/html")
