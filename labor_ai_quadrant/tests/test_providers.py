"""外部プロバイダの純粋な部分（パース・正規化・推計）をネットワーク無しで検証する。

HTTP そのものは叩けないが、壊れると静かに間違った数字が出るのはパース側なので、
そこをフィクスチャで固める。
"""

from __future__ import annotations

import csv
import io
import urllib.error
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
        jquants.fetch_listed_universe(scale="topix9999", api_key="dummy")


def test_v2_endpoints_are_used():
    """v1 は全エンドポイントが HTTP 410 Gone を返す（2026-08-16 実測）。"""
    assert jquants.API_ROOT.endswith("/v2")


def test_missing_jquants_key_fails_before_any_request(monkeypatch):
    monkeypatch.delenv("JQUANTS_API_KEY", raising=False)
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    with pytest.raises(jquants.JQuantsError, match="JQUANTS_API_KEY"):
        jquants._api_key()


def test_v1_refresh_token_is_accepted_as_the_v2_key(monkeypatch):
    """既存の .env は v1 時代の名前で同じ文字列を持っている。"""
    monkeypatch.delenv("JQUANTS_API_KEY", raising=False)
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "abc")
    assert jquants._api_key() == "abc"


class _Response(io.BytesIO):
    """urlopen の戻り値の最小形（with 文で使えて read できればよい）。"""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_rate_limited_calls_are_retried_not_dropped(monkeypatch):
    """429 で諦めると、TOPIX 500 の 9 割が黙って欠測になる（2026-08-17 に実際そうなった）。"""
    attempts = []

    def fake_urlopen(req, timeout=None):
        attempts.append(req.full_url)
        if len(attempts) < 3:
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)
        return _Response(b'{"data": [{"Code": "72030"}]}')

    monkeypatch.setattr(jquants.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(jquants.time, "sleep", lambda _seconds: None)

    assert jquants._get_json("fins/summary", "key") == {"data": [{"Code": "72030"}]}
    assert len(attempts) == 3


def test_a_non_429_error_is_not_retried(monkeypatch):
    attempts = []

    def fake_urlopen(req, timeout=None):
        attempts.append(req.full_url)
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(jquants.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(jquants.time, "sleep", lambda _seconds: None)

    with pytest.raises(jquants.JQuantsError, match="HTTP 403"):
        jquants._get_json("fins/summary", "key")
    assert len(attempts) == 1


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


def test_prior_years_are_not_mistaken_for_the_current_one():
    """有報は同じ要素IDを四期前から当期まで並べる。先頭は四期前。

    トヨタの単体従業員数なら、素直に最初のヒットを採ると当期末 73,133人ではなく
    四期前 70,710人を掴む。
    """
    rows = [
        {"要素ID": "jpcrp_cor:NumberOfEmployees",
         "コンテキストID": "Prior4YearInstant_NonConsolidatedMember", "値": "70710"},
        {"要素ID": "jpcrp_cor:NumberOfEmployees",
         "コンテキストID": "Prior1YearInstant_NonConsolidatedMember", "値": "71515"},
        {"要素ID": "jpcrp_cor:NumberOfEmployees",
         "コンテキストID": "CurrentYearInstant_NonConsolidatedMember", "値": "73133"},
    ]
    assert edinet._pick(rows, "jpcrp_cor:NumberOfEmployees") == "73133"


def test_segment_breakdowns_are_not_mistaken_for_the_company_total():
    """当期のセグメント別内訳も同じ要素IDで並ぶ。軸メンバー付きは全社値ではない。"""
    rows = [
        {"要素ID": "jpcrp_cor:NumberOfEmployees",
         "コンテキストID": "CurrentYearInstant_jpcrp030000-asr_E02144-000AutomotiveReportableSegmentsMember",
         "値": "343952"},
        {"要素ID": "jpcrp_cor:NumberOfEmployees",
         "コンテキストID": "CurrentYearInstant", "値": "390927"},
    ]
    assert edinet._pick(rows, "jpcrp_cor:NumberOfEmployees", "consolidated") == "390927"


def test_the_other_scope_is_not_silently_substituted():
    """単体が無いときに連結で埋めると、平均年収と従業員数が別会社の話になる。"""
    rows = [
        {"要素ID": "jppfs_cor:NetSales", "項目名": "売上高",
         "コンテキストID": "CurrentYearDuration", "値": "900"},
    ]
    assert edinet._pick(rows, "jppfs_cor:NetSales") is None
    assert edinet._pick(rows, "jppfs_cor:NetSales", "consolidated") == "900"


def test_revenue_falls_back_to_operating_revenue_for_holding_companies():
    """持株会社・サービス業は「売上高」ではなく「営業収益」で開示する。"""
    rows = [
        {"要素ID": "jppfs_cor:OperatingRevenue1",
         "コンテキストID": "CurrentYearDuration_NonConsolidatedMember", "値": "1,200"},
    ]
    facts = edinet.extract_company_facts(rows)
    assert facts["revenue"] == 1200.0


def test_consolidated_headcount_is_reported_separately():
    rows = [
        {"要素ID": "jpcrp_cor:NumberOfEmployees",
         "コンテキストID": "CurrentYearInstant", "値": "344196"},
        {"要素ID": "jpcrp_cor:NumberOfEmployees",
         "コンテキストID": "CurrentYearInstant_NonConsolidatedMember", "値": "2606"},
    ]
    facts = edinet.extract_company_facts(rows)
    assert facts["employees"] == 2606.0
    assert facts["employees_consolidated"] == 344196.0


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
