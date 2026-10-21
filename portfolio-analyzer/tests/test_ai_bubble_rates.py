"""The registered discount rate r_j = local 10-year yield + US implied ERP (spec 5.1)."""

from __future__ import annotations

import io
import zipfile

import pytest
from portfolio_analyzer.ai_bubble.rates import damodaran_erp, discount_rate, mof_10y, treasury_10y

AS_OF = "2026-10-21T00:00:00Z"  # 20:00 New York on the 20th, 09:00 Tokyo on the 21st

TREASURY = """Date,"1 Mo","10 Yr","30 Yr"
10/21/2026,4.10,5.30,5.40
10/20/2026,4.10,5.12,5.42
10/19/2026,4.11,5.15,5.48
"""

MOF = """国債金利情報 (令和8年10月),,,(単位 : %)
基準日,1年,10年,40年
R8.10.1,1.668,3.092,4.125
R8.10.20,1.644,2.927,4.002
R8.10.21,1.650,2.990,4.010
,,,
※最新のcsvデータがダウンロードできない場合,,,
"""


def test_treasury_yield_of_the_as_of_evening_is_published():
    # the 10-20 curve is out by 18:00 New York; the 10-21 row is not yet
    assert treasury_10y(TREASURY, AS_OF) == ("2026-10-20", 0.0512)


def test_treasury_yield_before_the_evening_publication_is_the_previous_day():
    assert treasury_10y(TREASURY, "2026-10-20T20:00:00Z") == ("2026-10-19", 0.0515)


def test_mof_reiwa_dates_and_the_ten_year_column():
    assert mof_10y(MOF, AS_OF) == ("2026-10-20", 0.02927)


def _xlsx(rows, date1904=True):
    """A minimal workbook: numbers inline, text (the header, text dates) as shared strings."""
    strings: list[str] = []
    cells = []
    for r, row in enumerate(rows, start=1):
        xml = []
        for c, value in enumerate(row):
            ref = f"{chr(65 + c)}{r}"
            if isinstance(value, str):
                strings.append(value)
                xml.append(f'<c r="{ref}" t="s"><v>{len(strings) - 1}</v></c>')
            elif value is not None:
                xml.append(f'<c r="{ref}"><v>{value}</v></c>')
        cells.append(f'<row r="{r}">{"".join(xml)}</row>')
    strings_xml = "".join(f"<si><t>{text}</t></si>" for text in strings)
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr(
            "xl/workbook.xml",
            f'<workbook {ns}><workbookPr date1904="{int(date1904)}"/><sheets><sheet name="Historical ERP"/></sheets></workbook>',
        )
        z.writestr("xl/sharedStrings.xml", f"<sst {ns}>{strings_xml}</sst>")
        z.writestr(
            "xl/worksheets/sheet1.xml",
            f"<worksheet {ns}><sheetData>{''.join(cells)}</sheetData></worksheet>",
        )
    return buffer.getvalue()


ERP_ROWS = [
    ["Start of month", "T.Bond Rate", "ERP (T12 m with sustainable payout)"],
    ["1-Sep-24", 0.0372, 0.0422],  # some months are typed as text
    [44804, 0.0475, 0.0414],  # 2026-09-01 in the 1904 date system
    [44834, 0.0529, 0.042],  # 2026-10-01
    [44865, 0.0500, 0.045],  # 2026-11-01, after the as-of
]


def test_damodaran_erp_uses_the_1904_date_system_and_the_registered_column():
    assert damodaran_erp(_xlsx(ERP_ROWS), AS_OF) == ("2026-10-01", 0.042)


def test_the_same_serial_in_the_1900_system_is_a_different_date():
    assert damodaran_erp(_xlsx(ERP_ROWS, date1904=False), AS_OF)[0] != "2026-10-01"


def test_discount_rate_adds_the_local_yield_and_the_us_erp():
    rates = {"US": ("2026-10-20", 0.0512), "JP": ("2026-10-20", 0.02927)}
    assert discount_rate("JP", rates, ("2026-10-01", 0.042)) == pytest.approx(0.07127)
    assert discount_rate("US", rates, ("2026-10-01", 0.042)) == pytest.approx(0.0932)
    with pytest.raises(ValueError, match="TW"):
        discount_rate("TW", rates, ("2026-10-01", 0.042))


def test_text_dates_in_the_workbook_are_read():
    assert damodaran_erp(_xlsx(ERP_ROWS[:2]), AS_OF) == ("2024-09-01", 0.0422)


def test_percent_text_in_the_erp_column_is_a_fraction():
    rows = [ERP_ROWS[0], ["1-Sep-24", 0.0372, "4.05%"]]
    assert damodaran_erp(_xlsx(rows), AS_OF) == ("2024-09-01", 0.0405)
