from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from click.testing import CliRunner

from macrokit import cli, store
from macrokit.cli import main
from macrokit.sources.esri_gdp import EsriGdpAdapter, EsriGdpError

JST = ZoneInfo("Asia/Tokyo")


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


def test_gdp_vintages_skips_a_release_whose_parse_fails_and_still_ingests_the_next(
    tmp_path, monkeypatch, make_event
):
    """Regression test for a real bug: `adapter.parse()` used to sit outside the
    `try/except EsriGdpError` that wraps `fetch_release`, so one release with
    an unexpected CSV shape (a real one had English-only headers) crashed the
    whole backfill instead of being skipped. This must fail if the `try` is
    ever narrowed back around `parse` -- verified by hand: narrowing it back
    made this test fail with a raw EsriGdpError traceback (see the fix report).
    """
    db = store.connect(tmp_path / "macrokit.duckdb")
    first = make_event(
        date(2010, 1, 1), "2nd_prelim", datetime(2010, 5, 20, 8, 50, tzinfo=JST)
    )
    second = make_event(
        date(2010, 4, 1), "2nd_prelim", datetime(2010, 8, 16, 8, 50, tzinfo=JST)
    )
    store.insert_releases(db, [first, second])
    db.close()

    seen_periods = []

    def fake_fetch_release(self, event, *, series_label, stem_prefix):
        return b"stub bytes", f"https://example.invalid/{event.period_start}.csv", 200

    def fake_parse(self, event, content, *, indicator, column, source_url, ingested_at):
        seen_periods.append(event.period_start)
        if event.period_start == date(2010, 1, 1):
            raise EsriGdpError("stub: unexpected column layout")
        return [
            store.Observation(
                indicator=indicator, period_start=event.period_start,
                period_end=event.period_end, release_date=event.release_date,
                vintage_seq=2, value=1.0, unit="percent_saar", sa="sa", freq="Q",
                source="esri_gdp", source_url=source_url, ingested_at=ingested_at,
                vintage_kind="actual",
            )
        ]

    monkeypatch.setattr(EsriGdpAdapter, "fetch_release", fake_fetch_release)
    monkeypatch.setattr(EsriGdpAdapter, "parse", fake_parse)
    monkeypatch.setattr(cli.time, "sleep", lambda _seconds: None)

    result = CliRunner().invoke(main, ["--data-root", str(tmp_path), "gdp", "vintages"])

    assert result.exit_code == 0
    assert "Traceback" not in result.output
    # Both releases were attempted -- the first failing did not stop the loop.
    assert seen_periods == [date(2010, 1, 1), date(2010, 4, 1)]
    assert "1 skipped" in result.output
    assert "1 inserted" in result.output

    check = store.connect(tmp_path / "macrokit.duckdb")
    rows = check.execute(
        "SELECT period_start FROM observations WHERE source = 'esri_gdp'"
    ).fetchall()
    assert rows == [(date(2010, 4, 1),)]


def test_gdp_expectations_rejects_an_unknown_method_without_a_traceback(tmp_path):
    result = CliRunner().invoke(
        main,
        ["--data-root", str(tmp_path), "gdp", "expectations", "--methods", "bogus"],
    )
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "bogus" in result.output
