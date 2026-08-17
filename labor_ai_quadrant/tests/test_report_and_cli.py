"""レポート生成と CLI のスモークテスト（いずれもネットワーク不要）。"""

from __future__ import annotations

import pytest
from labor_ai_quadrant.cli import main
from labor_ai_quadrant.config import SCENARIOS, Config
from labor_ai_quadrant.report import build_report


def test_config_rejects_out_of_range_values():
    with pytest.raises(ValueError, match="realization_rate"):
        Config(realization_rate=-0.1).validate()
    with pytest.raises(ValueError, match="threshold_method"):
        Config(threshold_method="mean").validate()


def test_every_shipped_scenario_is_valid():
    for name, cfg in SCENARIOS.items():
        cfg.validate(), name


def _contains(doc: str, token: str) -> bool:
    """Plotly serialises figure data with \\uXXXX escapes, so Japanese labels
    inside a chart never appear literally. Check both forms."""
    return token in doc or token.encode("ascii", "backslashreplace").decode() in doc


def test_report_is_self_contained(tmp_path):
    out = build_report(tmp_path / "r.html")
    doc = out.read_text(encoding="utf-8")
    assert doc.startswith("<!doctype html>")
    # Plotly is inlined, so the page must not load anything at view time.
    assert "<script src=" not in doc
    assert "<link " not in doc
    assert "<script" in doc
    assert len(doc) > 1_000_000


def test_report_contains_the_framework_landmarks(tmp_path):
    doc = build_report(tmp_path / "r.html").read_text(encoding="utf-8")
    for token in ("AI解放", "人手依存", "AI増益", "低感応"):
        assert token in doc, token
    for token in ("情報・通信業", "建設業", "陸運業"):
        assert _contains(doc, token), token


def test_report_honours_the_scenario(tmp_path):
    doc = build_report(tmp_path / "r.html", cfg=SCENARIOS["conservative_adoption"]).read_text(encoding="utf-8")
    assert "realization_rate=0.15" in doc


def test_cli_sectors_runs(capsys):
    assert main(["sectors"]) == 0
    out = capsys.readouterr().out
    assert "情報・通信業" in out
    assert "象限別サマリー" in out


def test_cli_top_company_runs(capsys):
    assert main(["top", "--level", "company", "-n", "5"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    # pandas prints a column header row plus an index-name row before the data.
    assert len(lines) == 7
    assert lines[1].startswith("code")


def test_cli_build_writes_the_report(tmp_path, capsys):
    out = tmp_path / "report.html"
    assert main(["build", "--out", str(out)]) == 0
    assert out.exists()
    assert "レポートを書き出しました" in capsys.readouterr().out


def test_cli_scenario_flag_is_applied(capsys):
    assert main(["sectors", "--scenario", "base"]) == 0
    base = capsys.readouterr().out
    assert main(["sectors", "--scenario", "absolute_threshold"]) == 0
    fixed = capsys.readouterr().out
    assert base != fixed
