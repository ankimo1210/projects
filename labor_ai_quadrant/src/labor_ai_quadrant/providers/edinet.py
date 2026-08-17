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

An element ID alone does not identify a value. One filing repeats the same
element for five fiscal years and again for each reportable segment, so the
period and the consolidation scope have to come from the context ID — see
:data:`CURRENT_CONTEXTS`.

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

#: 当期の値を指すコンテキストID。**完全一致で判定する。**
#:
#: EDINET は同じ要素IDを5期分（四期前〜当期）並べ、さらにセグメント別の内訳を
#: 軸メンバー付きのコンテキストで並べる。要素IDだけで拾うと最初にヒットする
#: 四期前の値（トヨタの従業員数なら 73,133 ではなく 70,710）や、セグメント単位の
#: 内訳（同 343,952）を掴む。接頭辞一致でも軸メンバー付きを弾けないので完全一致。
CURRENT_CONTEXTS: dict[str, tuple[str, ...]] = {
    "non_consolidated": (
        "CurrentYearInstant_NonConsolidatedMember",
        "CurrentYearDuration_NonConsolidatedMember",
    ),
    "consolidated": ("CurrentYearInstant", "CurrentYearDuration"),
}

#: 提出会社（単体）ベースの項目。候補は上から順に試す。
#:
#: 平均年間給与は単体でしか開示されないため、人件費に掛ける従業員数・比率の分母に
#: なる売上・営業利益もすべて単体で揃える。連結の営業利益と単体の人件費を割ると、
#: 海外子会社を持つ会社ほど押上げ余地が過小に出る（NTT は単体 2,606人 / 連結
#: 344,196人）。売上は業種によって表示科目が変わるので候補を並べる（売上高が無い
#: 持株会社・サービス業は営業収益）。
NON_CONSOLIDATED_FIELDS: dict[str, tuple[str, ...]] = {
    "employees": ("jpcrp_cor:NumberOfEmployees",),
    "average_salary": (
        "jpcrp_cor:AverageAnnualSalaryInformationAboutReportingCompanyInformationAboutEmployees",
    ),
    "average_age": (
        "jpcrp_cor:AverageAgeYearsInformationAboutReportingCompanyInformationAboutEmployees",
    ),
    "revenue": (
        # 主要な経営指標等（提出会社）→ 単体損益計算書 の順。表示科目は
        # 売上高 / 営業収益 / 売上収益 のいずれかで、業種と適用基準で変わる。
        "jpcrp_cor:NetSalesSummaryOfBusinessResults",
        "jpcrp_cor:OperatingRevenue1SummaryOfBusinessResults",
        "jpcrp_cor:RevenueKeyFinancialData",
        "jppfs_cor:NetSales",
        "jppfs_cor:OperatingRevenue1",
        "jppfs_cor:Revenue",
    ),
    "operating_profit": ("jppfs_cor:OperatingIncome",),
}

#: 連結ベースの項目。人件費の推計には使わない（平均年収が単体しか無いため）が、
#: 単体の値がグループ全体のどれだけを覆っているかを読む手掛かりとして残す。
CONSOLIDATED_FIELDS: dict[str, tuple[str, ...]] = {
    "employees_consolidated": ("jpcrp_cor:NumberOfEmployees",),
}

#: これだけ連続で日次取得に失敗したらスイープを打ち切る。キー不正やエンドポイント
#: 廃止は全日で同じように失敗するので、最後まで回しても空の結果が返るだけになる。
MAX_CONSECUTIVE_DAY_FAILURES = 5


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
        raise _fail(url, exc) from exc


def _fail(url: str, exc: urllib.error.URLError) -> EdinetError:
    """Carry EDINET's own error body into the exception.

    A bare status code cannot distinguish a bad subscription key from a date
    outside the retention window; EDINET says which in the response body.
    """
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:  # body already consumed, or not readable
            body = ""
        detail = f"HTTP {exc.code} {exc.reason}"
        if body:
            detail = f"{detail}: {body[:500]}"
    else:
        detail = str(getattr(exc, "reason", exc))
    return EdinetError(f"GET {url} failed: {detail}")


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
        # EDINET answers auth and quota failures with HTTP 200 and an error body,
        # so the transport layer never sees them. The reason is in StatusCode /
        # message; reporting only the absent results block hides it entirely.
        status = payload.get("StatusCode")
        message = payload.get("message") or payload.get("metadata")
        raise EdinetError(
            f"documents.json for {day.isoformat()} returned no results "
            f"(StatusCode={status}): {message}"
        )

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


def _pick(rows: list[dict[str, str]], element_id: str, scope: str = "non_consolidated") -> str | None:
    """Current-period value for an element in the requested scope.

    Returns ``None`` rather than falling back to the other scope: silently
    swapping consolidated for non-consolidated is how a headcount and an average
    salary end up describing different companies.
    """
    contexts = CURRENT_CONTEXTS[scope]
    for row in rows:
        if row.get("要素ID") == element_id and row.get("コンテキストID") in contexts:
            return row.get("値")
    return None


def _pick_first(rows: list[dict[str, str]], element_ids: tuple[str, ...], scope: str) -> str | None:
    """First element in ``element_ids`` that this filing actually reports."""
    for element_id in element_ids:
        value = _pick(rows, element_id, scope)
        if value not in (None, ""):
            return value
    return None


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
    return extract_company_facts(rows)


def extract_company_facts(rows: list[dict[str, str]]) -> dict[str, float | None]:
    """Reduce one filing's CSV rows to the scored facts (no network)."""
    facts: dict[str, float | None] = {
        column: _to_number(_pick_first(rows, element_ids, "non_consolidated"))
        for column, element_ids in NON_CONSOLIDATED_FIELDS.items()
    }
    facts.update(
        {
            column: _to_number(_pick_first(rows, element_ids, "consolidated"))
            for column, element_ids in CONSOLIDATED_FIELDS.items()
        }
    )
    return facts


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
    consecutive_failures = 0

    for offset in range(lookback_days):
        day = today - timedelta(days=offset)
        try:
            reports = list_annual_reports(day, key)
        except EdinetError as exc:  # a single bad day must not sink the sweep
            consecutive_failures += 1
            if consecutive_failures >= MAX_CONSECUTIVE_DAY_FAILURES:
                # A rejected key or a dead endpoint fails every day alike. Without
                # this the sweep skips all 400 days and reports an empty result,
                # which reads like "no filings" rather than "never authenticated".
                raise EdinetError(
                    f"{consecutive_failures} consecutive days failed; aborting the sweep. "
                    f"Last error: {exc}"
                ) from exc
            if progress:
                print(f"  {day}: skipped ({exc})")
            continue
        consecutive_failures = 0

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
