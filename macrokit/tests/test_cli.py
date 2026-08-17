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
