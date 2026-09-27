"""The synthetic CLI can materialize the already computed offline run."""

from __future__ import annotations

import json
import socket
import urllib.request

from market_research.cli import main
from market_research.services import build_demo_run


def test_demo_cli_writes_identical_html_after_restart(tmp_path, monkeypatch, capsys):
    def blocked(*_args, **_kwargs):
        raise AssertionError("unexpected network access")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    path = tmp_path / "report.html"
    args = ["demo", "--json", "--html", str(path)]

    assert main(args) == 0
    first = json.loads(capsys.readouterr().out)
    content = path.read_text(encoding="utf-8")
    assert first["run_id"] == build_demo_run().run_id
    assert first["html"] == str(path)
    assert first["run_id"] in content and "<html" in content

    assert main(args) == 0
    second = json.loads(capsys.readouterr().out)
    assert second == first
    assert path.read_text(encoding="utf-8") == content


def test_demo_cli_saves_immutable_run_and_reopens_offline(tmp_path, capsys):
    from market_research.research.run_store import load_demo_run

    args = ["--data-root", str(tmp_path), "demo", "--json", "--save-run"]
    assert main(args) == 0
    first = json.loads(capsys.readouterr().out)
    artifact = load_demo_run(tmp_path / "runs", first["artifact_id"], expected=build_demo_run())
    assert artifact.manifest["source_run_id"] == first["run_id"]
    assert artifact.html is not None and first["run_id"] in artifact.html
    assert main(args) == 0
    second = json.loads(capsys.readouterr().out)
    assert first == second
