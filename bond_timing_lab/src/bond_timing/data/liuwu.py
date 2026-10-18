"""Liu-Wu monthly zero curve (design §4.1).

Verified 2026-10-19: one sheet; a few note rows, then a header row whose cells read
``'  1 m'`` .. ``'360 m'``; data rows start with an integer ``YYYYMM``; yields are annual
percent, continuously compounded; long maturities are blank early in the sample. The author's
page links the file as a Google Drive spreadsheet (sample 1961-06..2025-12 at download).
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

from .store import RAW_ROOT, read_latest

FILE_ID = "1-wmStGZHLx55dSYi3gQK2vb3F8dMw_Nb"
URLS = (
    f"https://docs.google.com/spreadsheets/d/{FILE_ID}/export?format=xlsx",
    f"https://drive.google.com/uc?export=download&id={FILE_ID}",
)


def parse_liuwu(content: bytes) -> pd.DataFrame:
    book = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    rows = list(book.worksheets[0].iter_rows(values_only=True))
    header_at = next(
        i
        for i, row in enumerate(rows)
        if len(row) > 1 and isinstance(row[1], str) and row[1].strip() == "1 m"
    )
    labels = [cell for cell in rows[header_at][1:] if cell is not None]
    maturities = [int(str(label).split()[0]) for label in labels]
    months, values = [], []
    for row in rows[header_at + 1 :]:
        if not row or row[0] is None:
            continue
        code = int(row[0])
        months.append(pd.Period(year=code // 100, month=code % 100, freq="M"))
        cells = list(row[1 : 1 + len(maturities)])
        cells += [None] * (len(maturities) - len(cells))
        values.append([np.nan if cell is None else float(cell) / 100.0 for cell in cells])
    frame = pd.DataFrame(values, index=pd.PeriodIndex(months, freq="M"), columns=maturities)
    return frame.reindex(pd.period_range(frame.index[0], frame.index[-1], freq="M"))


def load_liuwu(root: Path = RAW_ROOT) -> pd.DataFrame:
    return parse_liuwu(read_latest(root, "liuwu", "monthly"))
