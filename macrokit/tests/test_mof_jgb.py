# Live probe (2026-08-18, run by hand -- see task-1 Step 7): fetching the real
# HISTORY_URL + CURRENT_URL and unioning them returned 163417 rows, latest
# obs_date = 2026-08-17 (Monday), one calendar day before the probe date
# (Tuesday). That is a same-day-minus-1 lag, well inside "a few business
# days" -- a daily batch run in the morning JST can expect yesterday's close
# to already be published.
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from macrokit.sources import mof_jgb

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("S49.9.24", date(1974, 9, 24)),
        ("H1.1.4", date(1989, 1, 4)),
        ("R8.7.31", date(2026, 7, 31)),
    ],
)
def test_parse_wareki_covers_every_era_in_the_file(token, expected):
    assert mof_jgb.parse_wareki(token) == expected


def test_parse_skips_the_title_row_and_reads_every_tenor():
    content = (FIXTURES / "mof_jgbcm_all.csv").read_bytes()
    rows = mof_jgb.parse_jgb_csv(content, source_url="u", ingested_at=NOW)

    latest = {r.tenor_y: r.yield_pct for r in rows if r.obs_date == date(2026, 7, 31)}
    assert len(latest) == 15
    assert latest[10.0] == 2.801
    assert latest[40.0] == 3.967


def test_a_missing_tenor_produces_no_row_rather_than_a_zero():
    content = (FIXTURES / "mof_jgbcm_all.csv").read_bytes()
    rows = mof_jgb.parse_jgb_csv(content, source_url="u", ingested_at=NOW)

    oldest = {r.tenor_y for r in rows if r.obs_date == date(1974, 9, 24)}
    assert oldest == {1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0}
    assert 10.0 not in oldest


def test_the_current_month_trailer_and_blank_line_are_not_parsed_as_data():
    content = (FIXTURES / "mof_jgbcm_current.csv").read_bytes()
    rows = mof_jgb.parse_jgb_csv(content, source_url="u", ingested_at=NOW)

    assert {r.obs_date for r in rows} == {date(2026, 8, 14), date(2026, 8, 17)}


def test_the_two_files_are_unioned_without_duplicating_a_date():
    history = (FIXTURES / "mof_jgbcm_all.csv").read_bytes()
    current = (FIXTURES / "mof_jgbcm_current.csv").read_bytes()
    adapter = mof_jgb.MofJgbAdapter()

    rows = adapter.parse(
        [(history, "history-url", 200), (current, "current-url", 200)],
        ingested_at=NOW,
    )

    keys = [(r.obs_date, r.tenor_y) for r in rows]
    assert len(keys) == len(set(keys))
    assert date(2026, 8, 17) in {r.obs_date for r in rows}
    assert date(1974, 9, 24) in {r.obs_date for r in rows}
