import numpy as np
import openpyxl
import pandas as pd
import pytest
from bond_timing.data.liuwu import parse_liuwu


def workbook(tmp_path) -> bytes:
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(['Data source: Yan Liu and Jing Cynthia Wu, "Reconstructing the Yield Curve"'])
    sheet.append(['Date (first column) in "YYYYMM"'])
    sheet.append(
        ["Data: Annualized continuously-compounded zero-coupon yields in percentage points."]
    )
    sheet.append([None])
    sheet.append([None, "  1 m", "  2 m", " 12 m"])
    sheet.append([196106, 2.0, 2.1, 3.0])
    sheet.append([196108, 2.2, None, 3.1])
    path = tmp_path / "liuwu.xlsx"
    book.save(path)
    return path.read_bytes()


def test_parse_liuwu_reads_months_maturities_and_blanks(tmp_path):
    frame = parse_liuwu(workbook(tmp_path))
    assert list(frame.columns) == [1, 2, 12]
    assert list(frame.index.astype(str)) == ["1961-06", "1961-07", "1961-08"]
    assert frame.loc[pd.Period("1961-06", "M"), 12] == pytest.approx(0.03)
    assert np.isnan(frame.loc[pd.Period("1961-08", "M"), 2])
    assert frame.loc[pd.Period("1961-07", "M")].isna().all()
