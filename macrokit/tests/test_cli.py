import pytest
from click.testing import CliRunner

from macrokit.cli import main


def test_catalog_list_prints_every_indicator():
    result = CliRunner().invoke(main, ["catalog", "list"])
    assert result.exit_code == 0
    assert "us_core_pce" in result.output


def test_status_runs_against_an_empty_database(tmp_path):
    result = CliRunner().invoke(main, ["--data-root", str(tmp_path), "status"])
    assert result.exit_code == 0
    assert "us_core_pce" in result.output
    assert "declared" in result.output


@pytest.mark.parametrize(
    "args",
    [
        ["--help"],
        ["rates", "--help"],
        ["gdp", "--help"],
        ["gdp", "releases", "--help"],
        ["gdp", "vintages", "--help"],
        ["gdp", "expectations", "--help"],
        ["gdp", "panel", "--help"],
    ],
)
def test_help_exits_zero_for_every_command(args):
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0


def test_gdp_panel_on_an_empty_store_reports_no_events_without_a_traceback(tmp_path):
    out = tmp_path / "panel.csv"
    result = CliRunner().invoke(
        main, ["--data-root", str(tmp_path), "gdp", "panel", "--out", str(out)]
    )
    assert result.exit_code == 0
    assert "no events" in result.output
    assert "Traceback" not in result.output
    assert not out.exists()


def test_gdp_vintages_on_an_empty_store_reports_zero_releases(tmp_path):
    # No releases table rows -> `_load_events` returns [] -> the fetch loop
    # never runs, so this stays network-free like every other test here.
    result = CliRunner().invoke(main, ["--data-root", str(tmp_path), "gdp", "vintages"])
    assert result.exit_code == 0
    assert "0 releases" in result.output
    assert "Traceback" not in result.output


def test_gdp_expectations_on_an_empty_store_reports_zero_events(tmp_path):
    result = CliRunner().invoke(main, ["--data-root", str(tmp_path), "gdp", "expectations"])
    assert result.exit_code == 0
    assert "0 events" in result.output
    assert "Traceback" not in result.output


def test_gdp_expectations_rejects_an_unknown_method_without_a_traceback(tmp_path):
    result = CliRunner().invoke(
        main,
        ["--data-root", str(tmp_path), "gdp", "expectations", "--methods", "bogus"],
    )
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "bogus" in result.output
