from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from jhrmbs.sources.dates import parse_japanese_month
from jhrmbs.sources.external import parse_flat35_current, parse_mof_jgb
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
