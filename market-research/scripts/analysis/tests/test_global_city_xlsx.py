"""Keep Japanese phonetic annotations out of actual spreadsheet text."""

import io
from zipfile import ZipFile

import pytest
from global_city_xlsx import xlsx_rows


@pytest.mark.parametrize("inline", [False, True])
def test_phonetic_reading_is_not_part_of_cell_value(inline):
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    text = '<t>売却</t><rPh sb="0" eb="2"><t>バイキャク</t></rPh>'
    cell = (
        f'<c r="B1" t="inlineStr"><is>{text}</is></c>' if inline else '<c r="B1" t="s"><v>0</v></c>'
    )
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{main}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Data" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        archive.writestr("xl/sharedStrings.xml", f'<sst xmlns="{main}"><si>{text}</si></sst>')
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{main}"><sheetData><row r="1">{cell}</row></sheetData></worksheet>',
        )
    assert list(xlsx_rows(stream.getvalue(), "Data")) == [(1, {"B": "売却"})]
