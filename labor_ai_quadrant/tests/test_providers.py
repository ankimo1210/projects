"""外部プロバイダの純粋な部分（パース・正規化・推計）をネットワーク無しで検証する。

HTTP そのものは叩けないが、壊れると静かに間違った数字が出るのはパース側なので、
そこをフィクスチャで固める。
"""

from __future__ import annotations

import csv
import io
import zipfile

import pandas as pd
import pytest
from labor_ai_quadrant.company import DEFAULT_BENEFITS_MULTIPLIER, estimate_labor_cost
from labor_ai_quadrant.providers import edinet, jquants

# --- J-Quants ---------------------------------------------------------------

@pytest.mark.parametrize(
    ("raw", "expected"),
    [("72030", "7203"), ("7203", "7203"), ("13010", "1301"), ("130A0", "130A")],
)
def test_jquants_code_normalisation(raw, expected):
    assert jquants.normalise_code(raw) == expected


def test_jquants_five_char_code_not_ending_in_zero_is_left_alone():
    # 英字入り新コード体系（例 '135A0'）は末尾0を落とすが、そうでないものは触らない。
    assert jquants.normalise_code("1301A") == "1301A"


def test_topix500_is_the_three_scale_categories():
    assert jquants.SCALE_SETS["topix500"] == (
        "TOPIX Core30",
        "TOPIX Large70",
        "TOPIX Mid400",
    )
    assert jquants.SCALE_SETS["all"] == ()


def test_unknown_scale_is_rejected_before_any_network_call():
    with pytest.raises(ValueError, match="unknown scale"):
        jquants.fetch_listed_universe(scale="topix9999", token="dummy")


# --- EDINET -----------------------------------------------------------------

def _csv_zip(rows: list[dict[str, str]]) -> bytes:
    """Build an EDINET-shaped payload: ZIP of UTF-16, tab-separated CSV."""
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=["要素ID", "項目名", "コンテキストID", "値"], delimiter="\t"
    )
    writer.writeheader()
    writer.writerows(rows)

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("XBRL_TO_CSV/jpcrp030000.csv", buf.getvalue().encode("utf-16"))
    return out.getvalue()


def test_decode_csv_reads_the_utf16_tab_separated_bundle():
    blob = _csv_zip([
        {"要素ID": "jpcrp_cor:NumberOfEmployees", "項目名": "従業員数",
         "コンテキストID": "CurrentYearInstant_NonConsolidatedMember", "値": "1,234"},
    ])
    rows = edinet._decode_csv(blob)
    assert rows[0]["要素ID"] == "jpcrp_cor:NumberOfEmployees"
    assert rows[0]["値"] == "1,234"


def test_bundle_without_a_csv_is_an_error():
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("readme.txt", b"nope")
    with pytest.raises(edinet.EdinetError, match=r"no \.csv entries"):
        edinet._decode_csv(out.getvalue())


def test_non_consolidated_context_wins():
    """連結と単体が両方載っているとき、単体を採る。

    平均年間給与は単体（提出会社）でしか開示されないため、従業員数だけ連結を
    拾うとスコープが混ざって人件費が過大に出る。
    """
    rows = [
        {"要素ID": "jpcrp_cor:NumberOfEmployees", "項目名": "従業員数",
         "コンテキストID": "CurrentYearInstant", "値": "50000"},
        {"要素ID": "jpcrp_cor:NumberOfEmployees", "項目名": "従業員数",
         "コンテキストID": "CurrentYearInstant_NonConsolidatedMember", "値": "8000"},
    ]
    assert edinet._pick(rows, "jpcrp_cor:NumberOfEmployees") == "8000"


def test_first_match_is_used_when_no_non_consolidated_context_exists():
    rows = [
        {"要素ID": "jppfs_cor:NetSales", "項目名": "売上高",
         "コンテキストID": "CurrentYearDuration", "値": "900"},
    ]
    assert edinet._pick(rows, "jppfs_cor:NetSales") == "900"


def test_missing_element_yields_none():
    assert edinet._pick([], "jpcrp_cor:NumberOfEmployees") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,234", 1234.0),
        ("8,123,456", 8123456.0),
        ("△500", -500.0),  # 有報の負値表記
        ("42.5", 42.5),
        ("", None),
        ("-", None),
        ("－", None),
        ("N/A", None),
        ("該当事項なし", None),
        (None, None),
    ],
)
def test_number_parsing_handles_the_report_conventions(raw, expected):
    assert edinet._to_number(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("72030", "7203"), ("7203", "7203"), (None, None), ("", None), ("  ", None)],
)
def test_edinet_sec_code_normalisation(raw, expected):
    assert edinet.normalise_sec_code(raw) == expected


def test_only_annual_reports_are_selected():
    assert edinet.ANNUAL_REPORT_ORDINANCE == "010"
    assert edinet.ANNUAL_REPORT_FORM == "030000"


def test_missing_api_key_fails_before_any_request(monkeypatch):
    monkeypatch.delenv("EDINET_API_KEY", raising=False)
    with pytest.raises(edinet.EdinetError, match="EDINET_API_KEY"):
        edinet._api_key()


# --- labour cost estimator --------------------------------------------------

def test_labour_cost_is_headcount_times_salary_times_benefits():
    employees = pd.Series([1000.0, 500.0])
    salary = pd.Series([8_000_000.0, 6_000_000.0])
    out = estimate_labor_cost(employees, salary)
    assert out.tolist() == [
        1000.0 * 8_000_000.0 * DEFAULT_BENEFITS_MULTIPLIER,
        500.0 * 6_000_000.0 * DEFAULT_BENEFITS_MULTIPLIER,
    ]


def test_benefits_multiplier_is_tunable():
    employees = pd.Series([100.0])
    salary = pd.Series([5_000_000.0])
    assert estimate_labor_cost(employees, salary, 1.0).iloc[0] == 500_000_000.0


def test_missing_inputs_propagate_as_nan_not_zero():
    """欠損を0で埋めると「人件費ゼロの会社」が最上位に来てしまう。"""
    employees = pd.Series([1000.0, float("nan")])
    salary = pd.Series([float("nan"), 6_000_000.0])
    assert estimate_labor_cost(employees, salary).isna().all()
