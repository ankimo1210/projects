from __future__ import annotations

import io
import re
import unicodedata
from pathlib import Path
from typing import Literal

import pandas as pd

from jhrmbs.exceptions import SourceFormatError
from jhrmbs.sources.dates import parse_japanese_date, parse_japanese_month
from jhrmbs.util import safe_float


def _decode(data: bytes, encodings: tuple[str, ...]) -> str:
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise SourceFormatError(f"文字コードを判定できません: {encodings}")


def parse_mof_jgb(path: Path) -> pd.DataFrame:
    text = _decode(path.read_bytes(), ("cp932", "shift_jis", "utf-8-sig"))
    frame = pd.read_csv(io.StringIO(text), skiprows=1, na_values=["-", "－"])
    if "基準日" not in frame.columns or "10年" not in frame.columns:
        raise SourceFormatError("財務省JGB CSVの必須列がありません")
    frame["date"] = frame["基準日"].map(parse_japanese_date)
    tenor_columns = {
        column: f"jgb_{str(column).replace('年', 'y')}_pct"
        for column in frame.columns
        if str(column).endswith("年")
    }
    frame = frame.rename(columns=tenor_columns)
    numeric_columns = list(tenor_columns.values())
    frame[numeric_columns] = frame[numeric_columns].apply(pd.to_numeric, errors="coerce")
    frame["month"] = frame["date"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        frame.sort_values("date")
        .groupby("month", as_index=False)
        .tail(1)[["month", "date", *numeric_columns]]
        .rename(columns={"date": "as_of_date"})
        .reset_index(drop=True)
    )
    return monthly


def parse_flat35_current(path: Path) -> pd.DataFrame:
    text = _decode(path.read_bytes(), ("euc_jp", "cp932", "utf-8"))
    text = unicodedata.normalize("NFKC", text)
    month_match = re.search(r"借入金利水準\s*\((\d{4})年\s*(\d{1,2})月\)", text)
    section_match = re.search(r"21年以上35年以下(.*?)</table>", text, flags=re.DOTALL)
    if not month_match or not section_match:
        raise SourceFormatError("フラット35現行金利の対象月または対象表を検出できません")
    section = re.sub(r"<[^>]+>", " ", section_match.group(1))
    section = " ".join(section.split())
    row_match = re.search(
        r"9割以下\s+年\s*([0-9.]+)%\s*[^0-9]+年\s*([0-9.]+)%\s+年\s*([0-9.]+)%",
        section,
    )
    if not row_match:
        raise SourceFormatError("フラット35の9割以下金利行を検出できません")
    minimum, maximum, mode = (float(value) for value in row_match.groups())
    year, month = (int(value) for value in month_match.groups())
    return pd.DataFrame(
        [
            {
                "month": pd.Timestamp(year, month, 1),
                "mortgage_rate_min_pct": minimum,
                "mortgage_rate_max_pct": maximum,
                "mortgage_rate_mode_pct": mode,
                "mortgage_rate_definition": "FLAT35 21-35 years, LTV <= 90%, with new JHF group credit life insurance",
            }
        ]
    )


def parse_mlit_housing_starts(path: Path) -> pd.DataFrame:
    engine: Literal["xlrd", "openpyxl"] = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    try:
        frame = pd.read_excel(path, sheet_name="jyuu", header=None, engine=engine, dtype=object)
    except Exception as exc:
        raise SourceFormatError(f"国交省住宅着工Excelを読めません: {exc}") from exc
    rows: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        label = unicodedata.normalize("NFKC", str(row.iloc[0] or ""))
        if not re.search(r"[SHR]\s*(?:\d+|元)\s*年?\s*\d+\s*月", label, flags=re.IGNORECASE):
            continue
        try:
            month = parse_japanese_month(label)
        except ValueError:
            continue
        total = safe_float(row.iloc[1])
        if total is None:
            continue
        rows.append(
            {
                "month": month,
                "housing_starts_total": total,
                "housing_starts_yoy_pct": safe_float(row.iloc[2]),
                "owner_occupied_starts": safe_float(row.iloc[5]),
                "rental_starts": safe_float(row.iloc[9]),
                "employee_housing_starts": safe_float(row.iloc[11]),
                "built_for_sale_starts": safe_float(row.iloc[13]),
            }
        )
    result = pd.DataFrame(rows).drop_duplicates("month", keep="last").sort_values("month")
    if result.empty:
        raise SourceFormatError("国交省住宅着工Excelから月次行を検出できません")
    result = result.reset_index(drop=True)
    _check_mlit_yoy_consistency(result)
    return result


def _check_mlit_yoy_consistency(result: pd.DataFrame) -> None:
    """Guard against silent column drift by reconciling the YoY column with totals."""
    previous = result[["month", "housing_starts_total"]].copy()
    previous["month"] = previous["month"] + pd.DateOffset(years=1)
    merged = result.merge(
        previous.rename(columns={"housing_starts_total": "prior_year_total"}),
        on="month",
        how="left",
    )
    comparable = merged[
        merged["housing_starts_yoy_pct"].notna() & (merged["prior_year_total"] > 0.0)
    ]
    if len(comparable) < 6:
        return
    implied = (comparable["housing_starts_total"] / comparable["prior_year_total"] - 1.0) * 100.0
    deviation = float((comparable["housing_starts_yoy_pct"] - implied).abs().median())
    if deviation > 1.0:
        raise SourceFormatError(
            "国交省住宅着工のYoY列が総戸数から計算した前年比と一致しません "
            f"(median deviation {deviation:.1f}pt); 列位置のずれを確認してください"
        )


def parse_boj_m3(path: Path) -> pd.DataFrame:
    text = _decode(path.read_bytes(), ("utf-8-sig", "cp932"))
    lines = text.splitlines()
    header_index = next(
        (index for index, line in enumerate(lines) if line.startswith("SERIES_CODE,")),
        None,
    )
    if header_index is None:
        raise SourceFormatError("日銀APIレスポンスにデータheaderがありません")
    frame = pd.read_csv(io.StringIO("\n".join(lines[header_index:])), dtype={"SURVEY_DATES": str})
    required = {"SURVEY_DATES", "VALUES"}
    if not required.issubset(frame.columns):
        raise SourceFormatError("日銀APIレスポンスの必須列がありません")
    frame["month"] = pd.to_datetime(frame["SURVEY_DATES"], format="%Y%m", errors="coerce")
    frame["m3_100m_jpy"] = pd.to_numeric(frame["VALUES"], errors="coerce")
    frame = frame.dropna(subset=["month", "m3_100m_jpy"]).sort_values("month")
    # YoY is aligned on the calendar month, not row position, so gaps stay null.
    previous = frame[["month", "m3_100m_jpy"]].copy()
    previous["month"] = previous["month"] + pd.DateOffset(years=1)
    frame = frame.merge(
        previous.rename(columns={"m3_100m_jpy": "m3_prior_year_100m_jpy"}),
        on="month",
        how="left",
    )
    frame["m3_yoy_pct"] = (frame["m3_100m_jpy"] / frame["m3_prior_year_100m_jpy"] - 1.0) * 100.0
    return frame[["month", "m3_100m_jpy", "m3_yoy_pct"]].reset_index(drop=True)
