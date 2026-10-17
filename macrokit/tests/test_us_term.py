from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import numpy as np
import openpyxl
import pytest

from macrokit.sources import us_term

FIXTURES = Path(__file__).parent / "fixtures"


def _days():
    return us_term.parse_gsw((FIXTURES / "gsw_sample.csv").read_bytes())


def test_gsw_skips_na_rows_and_reproduces_the_published_10y():
    days = {d.obs_date: d for d in _days()}
    assert date(1961, 7, 3) not in days
    assert us_term.gsw_zero(days[date(2024, 7, 31)], np.array([120]))[0] == pytest.approx(
        4.078, abs=5e-4
    )
    assert us_term.gsw_zero(days[date(2026, 6, 30)], np.array([120]))[0] == pytest.approx(
        4.491, abs=5e-4
    )


def test_a_nelson_siegel_day_drops_the_second_hump():
    day = next(d for d in _days() if d.obs_date == date(1961, 6, 30))
    assert day.params[3] == 0.0 and day.params[5] == 1.0
    assert np.isfinite(us_term.gsw_zero(day, np.arange(1, 121))).all()


def test_month_ends_keep_the_last_day_of_each_month():
    ends = us_term.month_end_days(_days())
    assert [d.obs_date for d in ends] == [date(1961, 6, 30), date(2024, 7, 31), date(2026, 6, 30)]


def test_acm_rows_are_keyed_by_year_and_month():
    rows = [
        ["DATE", "ACMY10", "ACMTP10"],
        ["30-Jun-1961", 3.8675066636819664, -0.08],
        ["31-Jul-2024", 4.1, 0.2],
        ["", "", ""],
    ]
    parsed = us_term.parse_acm_rows(rows)
    assert parsed[(1961, 6)]["ACMY10"] == pytest.approx(3.8675066636819664)
    assert parsed[(2024, 7)]["ACMTP10"] == 0.2
    assert len(parsed) == 2


def test_acm_rows_refuse_an_unexpected_header():
    with pytest.raises(us_term.UsTermError, match="DATE"):
        us_term.parse_acm_rows([["Date", "ACMTP10"]])


def test_wuxia_reads_the_shadow_column_and_skips_blank_months():
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Data"
    sheet.append([None, "Effective federal funds rate", "Wu-Xia shadow federal funds rate"])
    sheet.append([datetime(2008, 12, 1), 0.16, None])
    sheet.append([datetime(2009, 1, 1), 0.15, -0.5])
    sheet.append([datetime(2022, 2, 1), 0.08, 0.206380642030308])
    buffer = BytesIO()
    book.save(buffer)
    assert us_term.parse_wuxia(buffer.getvalue()) == {
        (2009, 1): -0.5,
        (2022, 2): pytest.approx(0.206380642030308),
    }
