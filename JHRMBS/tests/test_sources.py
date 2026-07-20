from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from jhrmbs.exceptions import SourceFormatError
from jhrmbs.sources.dates import parse_japanese_month
from jhrmbs.sources.external import (
    parse_boj_m3,
    parse_flat35_current,
    parse_mlit_housing_starts,
    parse_mof_jgb,
)
from jhrmbs.sources.jhf import issue_identity, parse_jhf_workbook


def test_japanese_era_month() -> None:
    assert parse_japanese_month("R 8.7") == pd.Timestamp("2026-07-01")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("第220回", ("JHF-220", "monthly")),
        ("S種第4回", ("JHF-S-04", "s")),
        ("グリーン第12回", ("JHF-GREEN-12", "green")),
    ],
)
def test_issue_identity(name: str, expected: tuple[str, str]) -> None:
    assert issue_identity(name) == expected


def test_jhf_parser_discovers_header_and_skips_unrelated_sheet(tmp_path: Path) -> None:
    rows = [
        ["回号", "第1回", None, None, None, None, None],
        ["発行額面額", 100_000_000, None, None, None, None, None],
        ["利率", 1.25, None, None, None, None, None],
        ["発行日", pd.Timestamp("2008-01-10"), None, None, None, None, None],
        [None, None, None, None, None, None, None],
        [
            "債券年月",
            "当初予定ファクター",
            "ファクター(実績)",
            "加重平均金利",
            "加重平均残存年数",
            "任意繰上償還率",
            "加重平均経過期間",
        ],
        ["発行時", 1.0, 1.0, 3.0, 30.0, None, 0.0],
        ["H 20.2", 0.999, 0.995, 3.0, 29.9, 4.5, 1.0],
    ]
    path = tmp_path / "jhf.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name="第1回", index=False, header=False)
        pd.DataFrame([["payment status only"]]).to_excel(
            writer, sheet_name="参考", index=False, header=False
        )
    parsed = parse_jhf_workbook(path, source_filename=path.name, source_sha256="abc")
    assert parsed.issues.loc[0, "issue_id"] == "JHF-001"
    assert parsed.panel.loc[0, "payment_month"] == pd.Timestamp("2008-02-01")
    assert parsed.panel.loc[0, "voluntary_cpr_pct"] == pytest.approx(4.5)
    assert parsed.skipped_sheets == ("参考",)


def test_mof_parser_uses_last_observation_in_month(tmp_path: Path) -> None:
    path = tmp_path / "jgb.csv"
    path.write_bytes(
        "メタデータ行\n基準日,1年,10年\nR 8.7.1,0.8,1.5\nR 8.7.31,0.9,1.6\n".encode("cp932")
    )
    parsed = parse_mof_jgb(path)
    assert parsed.loc[0, "as_of_date"] == pd.Timestamp("2026-07-31")
    assert parsed.loc[0, "jgb_10y_pct"] == pytest.approx(1.6)


def test_boj_m3_yoy_uses_calendar_alignment_across_gaps(tmp_path: Path) -> None:
    lines = [
        "メタデータ行",
        "SERIES_CODE,SURVEY_DATES,VALUES",
        "M3,202301,100.0",
        "M3,202302,100.0",
        "M3,202401,110.0",
        "M3,202402,121.0",
    ]
    path = tmp_path / "boj_m3.csv"
    path.write_text("\n".join(lines), encoding="utf-8")
    parsed = parse_boj_m3(path)
    by_month = parsed.set_index("month")["m3_yoy_pct"]
    assert by_month[pd.Timestamp("2024-01-01")] == pytest.approx(10.0)
    assert by_month[pd.Timestamp("2024-02-01")] == pytest.approx(21.0)
    assert pd.isna(by_month[pd.Timestamp("2023-01-01")])


def _mlit_workbook(tmp_path: Path, *, yoy_offset: float) -> Path:
    rows: list[list[object]] = []
    total = 70_000.0
    totals: dict[pd.Timestamp, float] = {}
    for year, era_year in ((2023, 5), (2024, 6)):
        for month in range(1, 13):
            total = total * (1.01 if year == 2023 else 0.99)
            stamp = pd.Timestamp(year, month, 1)
            totals[stamp] = total
            previous = totals.get(pd.Timestamp(year - 1, month, 1))
            yoy = (
                (total / previous - 1.0) * 100.0 + yoy_offset
                if previous is not None
                else None
            )
            rows.append(
                [f"R{era_year}年{month}月", total, yoy] + [None] * 2 + [1.0]
                + [None] * 3 + [2.0] + [None] + [3.0] + [None] + [4.0]
            )
    path = tmp_path / "mlit.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name="jyuu", index=False, header=False)
    return path


def test_mlit_yoy_column_consistent_with_totals_passes(tmp_path: Path) -> None:
    parsed = parse_mlit_housing_starts(_mlit_workbook(tmp_path, yoy_offset=0.0))
    assert len(parsed) == 24
    assert parsed["housing_starts_yoy_pct"].notna().sum() == 12


def test_mlit_yoy_column_inconsistent_with_totals_raises(tmp_path: Path) -> None:
    with pytest.raises(SourceFormatError, match="YoY"):
        parse_mlit_housing_starts(_mlit_workbook(tmp_path, yoy_offset=40.0))


def test_flat35_current_parser(tmp_path: Path) -> None:
    path = tmp_path / "flat35.html"
    path.write_bytes(
        """<html><body>借入金利水準 (2026年 7月)
        <h2>21年以上35年以下</h2><table><tr><td>9割以下 年 1.50% - 年 2.00% 年 1.75%</td></tr></table>
        </body></html>""".encode("euc_jp")
    )
    parsed = parse_flat35_current(path)
    assert parsed.loc[0, "month"] == pd.Timestamp("2026-07-01")
    assert parsed.loc[0, "mortgage_rate_mode_pct"] == pytest.approx(1.75)
