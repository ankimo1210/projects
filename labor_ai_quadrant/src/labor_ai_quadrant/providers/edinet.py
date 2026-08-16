"""EDINET loader for the company-level facts that actually separate companies.

The quadrant position is sector-driven; what ranks one company above another in
the same sector is how much labour cost it carries and how far AI reaches into
it. Those facts live in the 有価証券報告書, not in a price feed:

    従業員数     jpcrp_cor:NumberOfEmployees
    平均年間給与  jpcrp_cor:AverageAnnualSalaryInformationAbout...Employees
    平均年齢     jpcrp_cor:AverageAgeYearsInformationAbout...Employees

This uses EDINET API v2's **CSV** output (``type=5``) rather than the XBRL
bundle: same facts, one order of magnitude less parsing, and no namespace
handling. Only the standard library is used, so no production dependency is
added.

Credentials::

    EDINET_API_KEY   (EDINET API v2 subscription key, sent as Ocp-Apim-Subscription-Key)

Network required. ``labor_ai_quadrant`` runs entirely offline without it — this
module is only imported when the caller explicitly asks for live data.
"""

from __future__ import annotations

import csv
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

API_ROOT = "https://api.edinet-fsa.go.jp/api/v2"

#: 府令コード 010 + 様式コード 030000 = 有価証券報告書。四半期報告書や訂正報告書は
#: 従業員数を載せないか、載せても期中値なので除外する。
ANNUAL_REPORT_ORDINANCE = "010"
ANNUAL_REPORT_FORM = "030000"

#: EDINET CSV の要素ID → こちらの列名。ContextRef で連結/単体が分かれるため、
#: 「提出会社」（単体）の値を優先し、無ければ最初に見つかった値を使う。
ELEMENT_MAP = {
    "jpcrp_cor:NumberOfEmployees": "employees",
    "jpcrp_cor:AverageAnnualSalaryInformationAboutReportingCompanyInformationAboutEmployees": "average_salary",
    "jpcrp_cor:AverageAgeYearsInformationAboutReportingCompanyInformationAboutEmployees": "average_age",
    "jppfs_cor:NetSales": "revenue",
    "jppfs_cor:OperatingIncome": "operating_profit",
}

#: 単体を表す ContextRef の接頭辞。連結（Consolidated）より優先する。
NON_CONSOLIDATED_HINT = "NonConsolidatedMember"


class EdinetError(RuntimeError):
    """Raised when the EDINET API is unreachable or returns an unusable payload."""


@dataclass(frozen=True)
class AnnualReport:
    """One 有価証券報告書 filing, keyed by the securities code we score on."""

    doc_id: str
    code: str  # 4-character securities code
    filer_name: str
    submit_date: str


def _api_key(explicit: str | None = None) -> str:
    key = explicit or os.environ.get("EDINET_API_KEY")
    if not key:
        raise EdinetError(
            "EDINET_API_KEY が未設定です。オフラインで動かす場合は --financials を省略してください。"
        )
    return key


def _get(url: str, api_key: str) -> bytes:
    req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.URLError as exc:
        raise EdinetError(f"GET {url} failed: {exc}") from exc


def normalise_sec_code(sec_code: str | None) -> str | None:
    """EDINET reports 5-character codes ('72030'); the framework uses 4 ('7203')."""
    if not sec_code:
        return None
    sec_code = str(sec_code).strip()
    if len(sec_code) == 5 and sec_code.endswith("0"):
        return sec_code[:4]
    return sec_code or None


def list_annual_reports(day: date, api_key: str | None = None) -> list[AnnualReport]:
    """Every 有価証券報告書 submitted on ``day``."""
    key = _api_key(api_key)
    params = urllib.parse.urlencode({"date": day.isoformat(), "type": "2"})
    payload = json.loads(_get(f"{API_ROOT}/documents.json?{params}", key))

    results = payload.get("results")
    if results is None:
        raise EdinetError(f"documents.json returned no results block: {payload.get('metadata')}")

    reports: list[AnnualReport] = []
    for row in results:
        if row.get("ordinanceCode") != ANNUAL_REPORT_ORDINANCE:
            continue
        if row.get("formCode") != ANNUAL_REPORT_FORM:
            continue
        code = normalise_sec_code(row.get("secCode"))
        if not code:  # unlisted filers have no securities code
            continue
        reports.append(
            AnnualReport(
                doc_id=row["docID"],
                code=code,
                filer_name=row.get("filerName", ""),
                submit_date=row.get("submitDateTime", "")[:10],
            )
        )
    return reports


def _decode_csv(blob: bytes) -> list[dict[str, str]]:
    """EDINET type=5 returns a ZIP holding UTF-16LE, tab-separated CSVs."""
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise EdinetError("EDINET CSV bundle contained no .csv entries")
        for name in names:
            text = zf.read(name).decode("utf-16", errors="replace")
            rows.extend(csv.DictReader(io.StringIO(text), delimiter="\t"))
    return rows


def _pick(rows: list[dict[str, str]], element_id: str) -> str | None:
    """Value for an element, preferring the parent-company (non-consolidated) context."""
    matches = [r for r in rows if r.get("要素ID") == element_id]
    if not matches:
        return None
    for row in matches:
        if NON_CONSOLIDATED_HINT in (row.get("コンテキストID") or ""):
            return row.get("値")
    return matches[0].get("値")


def _to_number(raw: str | None) -> float | None:
    if raw is None:
        return None
    cleaned = raw.replace(",", "").replace("△", "-").strip()
    if not cleaned or cleaned in {"-", "－", "N/A"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def fetch_company_facts(doc_id: str, api_key: str | None = None) -> dict[str, float | None]:
    """Pull the labour and P/L facts out of one filing."""
    key = _api_key(api_key)
    rows = _decode_csv(_get(f"{API_ROOT}/documents/{doc_id}?type=5", key))
    return {
        column: _to_number(_pick(rows, element_id))
        for element_id, column in ELEMENT_MAP.items()
    }


def build_financials(
    lookback_days: int = 400,
    today: date | None = None,
    api_key: str | None = None,
    codes: set[str] | None = None,
    progress: bool = True,
) -> pd.DataFrame:
    """Assemble a financials table by sweeping EDINET's filing calendar.

    Annual reports cluster in June (March year-ends), so a 400-day lookback
    covers one full cycle for every filer regardless of year-end.

    Parameters
    ----------
    codes:
        Restrict to these securities codes. Passing the scored universe avoids
        downloading thousands of filings you will not use.
    """
    key = _api_key(api_key)
    today = today or date.today()

    records: dict[str, dict[str, float | None]] = {}
    names: dict[str, str] = {}

    for offset in range(lookback_days):
        day = today - timedelta(days=offset)
        try:
            reports = list_annual_reports(day, key)
        except EdinetError as exc:  # a single bad day must not sink the sweep
            if progress:
                print(f"  {day}: skipped ({exc})")
            continue

        for report in reports:
            if codes is not None and report.code not in codes:
                continue
            if report.code in records:  # keep the most recent filing only
                continue
            try:
                facts = fetch_company_facts(report.doc_id, key)
            except EdinetError as exc:
                if progress:
                    print(f"  {report.code} {report.filer_name}: skipped ({exc})")
                continue
            records[report.code] = facts
            names[report.code] = report.filer_name

        if progress and reports:
            print(f"  {day}: {len(records)} 社を取得済み")
        if codes is not None and len(records) >= len(codes):
            break

    if not records:
        raise EdinetError("EDINET から1件も取得できませんでした（API キー・期間・コードを確認）")

    df = pd.DataFrame.from_dict(records, orient="index")
    df.index.name = "code"
    df["filer_name"] = pd.Series(names)
    return df
