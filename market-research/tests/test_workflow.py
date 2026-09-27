import json
from pathlib import Path

import pytest
from market_research.cli import main
from market_research.macro import as_of
from market_research.services import build_demo_run
from streamlit.testing.v1 import AppTest


def test_demo_is_deterministic_and_explicitly_synthetic():
    one = build_demo_run()
    two = build_demo_run()
    assert one.run_id == two.run_id
    assert one.mode == "synthetic-demo"
    assert len(one.prices) == 60
    assert set(one.prices.columns) == {"DEMO:ALPHA", "DEMO:BETA"}
    assert one.prices.equals(two.prices)
    assert one.backtest.held_weights.iloc[1].tolist() == one.target_weights.iloc[0].tolist()


def test_demo_releases_are_gated_by_as_of_time():
    demo = build_demo_run()
    first, revision = demo.macro_observations
    assert as_of(demo.macro_observations, "DEMO_CPI", first.release_at)[0].value == 100.0
    assert as_of(demo.macro_observations, "DEMO_CPI", revision.release_at)[0].value == 101.0


def test_demo_does_not_use_network(monkeypatch):
    import socket
    import urllib.request

    def blocked(*_args, **_kwargs):
        raise AssertionError("unexpected network access")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    assert build_demo_run().mode == "synthetic-demo"


def test_cli_json_uses_same_run_and_no_account_fields(capsys):
    expected = build_demo_run()
    assert main(["demo", "--json"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["run_id"] == expected.run_id
    assert value["mode"] == "synthetic-demo"
    assert value["observations"] == 60
    assert value["assets"] == ["DEMO:ALPHA", "DEMO:BETA"]
    assert "holdings" not in value and "account" not in value


def test_streamlit_opens_seven_demo_views_without_exceptions():
    path = Path(__file__).resolve().parents[1] / "app" / "main.py"
    app = AppTest.from_file(str(path), default_timeout=15).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "市場概要",
        "銘柄・バスケット",
        "シグナル・スクリーナー",
        "戦略比較",
        "マクロと公表",
        "仮想配分・リスク",
        "品質・実行履歴",
    ]
    assert any("合成デモ" in item.value for item in app.caption)


def test_installed_market_research_command_runs_offline():
    import subprocess

    command = Path(__file__).resolve().parents[2] / ".venv/bin/market-research"
    result = subprocess.run(
        [str(command), "demo", "--json"], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout)["mode"] == "synthetic-demo"
