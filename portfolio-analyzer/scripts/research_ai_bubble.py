"""Manual entry point for the AI bubble study (spec: docs/2026-10-21-ai-bubble-research-design.md).

Every subcommand writes into one run root under ``_data/portfolio-analyzer/ai-bubble``:
``public/`` holds market data and market results, ``private/`` anything derived from
holdings. Raw downloads are kept with their sha256 in the run manifest.

    uv run --no-sync python portfolio-analyzer/scripts/research_ai_bubble.py new-run
    uv run --no-sync python portfolio-analyzer/scripts/research_ai_bubble.py fetch-sec RUN NVDA MSFT
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from portfolio_analyzer.ai_bubble import funding, history, jp, portfolio, rates, sec
from portfolio_analyzer.ai_bubble.fundamentals import base_from_rows, quarters, ttm
from portfolio_analyzer.ai_bubble.inputs import audit_inputs, reconcile, select_as_of
from portfolio_analyzer.ai_bubble.runs import (
    DATA_ROOT,
    new_run,
    record_outputs,
    record_prereg_amendment,
    recorded_inputs,
    sha256_file,
)
from portfolio_analyzer.ai_bubble.universe import (
    last_final_close,
    market_cap_usd,
    select_universe,
    shares_at,
)
from portfolio_analyzer.ai_bubble.valuation import (
    cycle_per,
    enterprise_value,
    layer_consistency,
    multiples,
    price_decomposition,
    project_fcff,
    scenario_paths,
    value_company,
)

PROJECT = Path(__file__).resolve().parent.parent
PREREG = PROJECT / "docs" / "ai-bubble" / "prereg.json"
REFERENCES = PROJECT / "docs" / "ai-bubble" / "reconciliation-refs.json"
MANUAL = PROJECT / "docs" / "ai-bubble" / "manual-inputs.json"

# Verified against data.sec.gov submissions (name and ticker) on every fetch.
CIKS = {
    "MSFT": 789019,
    "AMZN": 1018724,
    "GOOGL": 1652044,
    "META": 1326801,
    "ORCL": 1341439,
    "NVDA": 1045810,
    "AVGO": 1730168,
    "AMD": 2488,
    "MRVL": 1835632,
    "TSM": 1046179,
    "MU": 723125,
    "ASML": 937966,
    "AMAT": 6951,
    "LRCX": 707549,
    "KLAC": 319201,
    "TER": 97210,
    "ANET": 1596532,
    "VRT": 1674101,
    "CRWV": 1769628,
}

US_GAAP = {
    "revenue": [
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap:Revenues",
        "us-gaap:SalesRevenueNet",
    ],
    "operating_income": ["us-gaap:OperatingIncomeLoss"],
    # parts of operating income, for filers that stopped tagging it (KLA after 2015)
    "cost_of_revenue": ["us-gaap:CostOfRevenue", "us-gaap:CostOfGoodsAndServicesSold"],
    "rnd": ["us-gaap:ResearchAndDevelopmentExpense"],
    "sga": ["us-gaap:SellingGeneralAndAdministrativeExpense"],
    "pretax_income": [
        "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],
    "income_tax": ["us-gaap:IncomeTaxExpenseBenefit"],
    # Broadcom tags only ProfitLoss (including non-controlling interests, nil there)
    "net_income": ["us-gaap:NetIncomeLoss", "us-gaap:ProfitLoss"],
    "nonoperating_income": [
        "us-gaap:NonoperatingIncomeExpense",
        "us-gaap:OtherNonoperatingIncomeExpense",
    ],
    "operating_cf": ["us-gaap:NetCashProvidedByUsedInOperatingActivities"],
    "capex": [
        "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
        "us-gaap:PaymentsToAcquireProductiveAssets",
    ],
    "d_and_a": [
        "us-gaap:DepreciationDepletionAndAmortization",
        "us-gaap:DepreciationAmortizationAndAccretionNet",
        "us-gaap:DepreciationAndAmortization",
    ],
    "sbc": ["us-gaap:ShareBasedCompensation", "us-gaap:AllocatedShareBasedCompensationExpense"],
    "cash": [
        "us-gaap:CashAndCashEquivalentsAtCarryingValue",
        "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "short_term_investments": [
        "us-gaap:MarketableSecuritiesCurrent",
        "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent",
        "us-gaap:ShortTermInvestments",
        "us-gaap:DebtSecuritiesCurrent",
    ],
    "lt_marketable": [
        "us-gaap:MarketableSecuritiesNoncurrent",
        "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
    ],
    "marketable_total": ["us-gaap:AvailableForSaleSecuritiesDebtSecurities"],
    "depreciation": ["us-gaap:Depreciation"],
    "amortization_intangibles": ["us-gaap:AmortizationOfIntangibleAssets"],
    # Debt is tagged in several ways; fundamentals.DEBT_RECIPES picks one per balance date.
    "debt_total": ["us-gaap:LongTermDebt"],
    "debt_lt_current": ["us-gaap:LongTermDebtCurrent"],
    "debt_lt_noncurrent": ["us-gaap:LongTermDebtNoncurrent"],
    "debt_combined": ["us-gaap:DebtLongtermAndShorttermCombinedAmount"],
    "notes_and_loans_noncurrent": ["us-gaap:LongTermNotesAndLoans", "us-gaap:LongTermNotesPayable"],
    "notes_payable_current": ["us-gaap:NotesPayableCurrent"],
    "debt_instruments": ["us-gaap:DebtInstrumentCarryingAmount"],
    "short_term_borrowings": ["us-gaap:ShortTermBorrowings"],
    "commercial_paper": ["us-gaap:CommercialPaper"],
    "debt_due_y1": ["us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"],
    "debt_due_y2": ["us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo"],
    "debt_due_y3": ["us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree"],
    "debt_due_remainder_fy": [
        "us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalRemainderOfFiscalYear"
    ],
    # committed purchases (display only: the funding path keeps capital expenditure at its run rate)
    "purchase_obligation_total": [
        "us-gaap:PurchaseObligation",
        "us-gaap:UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount",
    ],
    "purchase_obligation_y1": [
        "us-gaap:PurchaseObligationDueInNextTwelveMonths",
        "us-gaap:UnrecordedUnconditionalPurchaseObligationBalanceOnFirstAnniversary",
    ],
    "contractual_obligation_total": ["us-gaap:ContractualObligation"],
    "contractual_obligation_y1": ["us-gaap:ContractualObligationDueInNextTwelveMonths"],
    "operating_lease_due_y1": ["us-gaap:LesseeOperatingLeaseLiabilityPaymentsDueNextTwelveMonths"],
    "operating_lease_due_y2": ["us-gaap:LesseeOperatingLeaseLiabilityPaymentsDueYearTwo"],
    "finance_lease_due_y1": ["us-gaap:FinanceLeaseLiabilityPaymentsDueNextTwelveMonths"],
    "finance_lease_due_y2": ["us-gaap:FinanceLeaseLiabilityPaymentsDueYearTwo"],
    "operating_lease_payments": ["us-gaap:OperatingLeasePayments"],
    "finance_lease_rou_obtained": [
        "us-gaap:RightOfUseAssetObtainedInExchangeForFinanceLeaseLiability"
    ],
    "operating_lease_rou_obtained": [
        "us-gaap:RightOfUseAssetObtainedInExchangeForOperatingLeaseLiability"
    ],
    "operating_lease_liability": ["us-gaap:OperatingLeaseLiability"],
    "finance_lease_liability": ["us-gaap:FinanceLeaseLiability"],
    "finance_lease_current": ["us-gaap:FinanceLeaseLiabilityCurrent"],
    "finance_lease_noncurrent": ["us-gaap:FinanceLeaseLiabilityNoncurrent"],
    "finance_lease_principal_payments": ["us-gaap:FinanceLeasePrincipalPayments"],
    "debt_repayments": [
        "us-gaap:RepaymentsOfLongTermDebt",
        "us-gaap:RepaymentsOfDebt",
        "us-gaap:RepaymentsOfDebtMaturingInMoreThanThreeMonths",
    ],
    "debt_issued": [
        "us-gaap:ProceedsFromIssuanceOfLongTermDebt",
        "us-gaap:ProceedsFromIssuanceOfSeniorLongTermDebt",
        "us-gaap:ProceedsFromIssuanceOfDebt",
    ],
    "buybacks": ["us-gaap:PaymentsForRepurchaseOfCommonStock"],
    "dividends_paid": ["us-gaap:PaymentsOfDividendsCommonStock", "us-gaap:PaymentsOfDividends"],
    "receivables": ["us-gaap:AccountsReceivableNetCurrent"],
    "inventory": ["us-gaap:InventoryNet"],
    # long-term investments outside operations (fundamentals.balance picks one recipe)
    "lt_investments": ["us-gaap:LongTermInvestments"],
    "other_lt_investments": ["us-gaap:OtherLongTermInvestments"],
    "equity_securities_combined": [
        "us-gaap:EquitySecuritiesFvNiAndWithoutReadilyDeterminableFairValue"
    ],
    "equity_securities_fv": ["us-gaap:EquitySecuritiesFvNi"],
    "equity_securities_nrdfv": [
        "us-gaap:EquitySecuritiesWithoutReadilyDeterminableFairValueAmount"
    ],
    "equity_method": ["us-gaap:EquityMethodInvestments"],
    "equity": [
        "us-gaap:StockholdersEquity",
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "total_assets": ["us-gaap:Assets"],
    "rpo": ["us-gaap:RevenueRemainingPerformanceObligation"],
    "contract_liabilities": [
        "us-gaap:ContractWithCustomerLiability",
        "us-gaap:ContractWithCustomerLiabilityCurrent",
    ],
    "eps_diluted": ["us-gaap:EarningsPerShareDiluted"],
    "diluted_shares": ["us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"],
    "shares_outstanding": ["dei:EntityCommonStockSharesOutstanding"],
}


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _manifest(run: Path) -> dict[str, Any]:
    return json.loads((run / "manifest.json").read_text())


def _save_manifest(run: Path, manifest: dict[str, Any]) -> None:
    (run / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def record_input(run: Path, path: Path, url: str, sha256: str, retrieved_at: str) -> None:
    manifest = _manifest(run)
    manifest["inputs"].append(
        {
            "path": str(path.relative_to(run)),
            "url": url,
            "sha256": sha256,
            "bytes": path.stat().st_size,
            "retrieved_at": retrieved_at,
        }
    )
    _save_manifest(run, manifest)


def cmd_new_run(args: argparse.Namespace) -> int:
    run = new_run(Path(args.root), args.as_of, Path(args.prereg))
    for part in ("public", "private"):
        (run / part).mkdir()
    print(run)
    return 0


def cmd_fetch_sec(args: argparse.Namespace) -> int:
    run = Path(args.run)
    raw_dir = run / "public" / "raw" / "sec"
    rows_dir = run / "public" / "rows"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for ticker in args.tickers:
        cik = CIKS[ticker]
        retrieved = _now()
        submissions, sub_sha, sub_body = sec.fetch_json(sec.submissions_url(cik))
        if ticker not in submissions.get("tickers", []):
            raise SystemExit(f"{ticker}: CIK {cik} lists tickers {submissions.get('tickers')}")
        pages = [submissions]
        sub_path = raw_dir / f"{ticker}-submissions.json"
        sub_path.write_bytes(sub_body)
        record_input(run, sub_path, sec.submissions_url(cik), sub_sha, retrieved)
        for extra in submissions.get("filings", {}).get("files", []):
            url = f"https://data.sec.gov/submissions/{extra['name']}"
            page, sha, body = sec.fetch_json(url)
            path = raw_dir / f"{ticker}-{extra['name']}"
            path.write_bytes(body)
            record_input(run, path, url, sha, _now())
            pages.append(page)
        _facts, facts_sha, facts_body = sec.fetch_json(sec.companyfacts_url(cik))
        facts_path = raw_dir / f"{ticker}-companyfacts.json"
        facts_path.write_bytes(facts_body)
        record_input(run, facts_path, sec.companyfacts_url(cik), facts_sha, retrieved)
        report[ticker] = parse_saved(run, ticker, retrieved)
    _write_report(run, report)
    return 0


def parse_saved(run: Path, ticker: str, retrieved: str | None = None) -> dict[str, Any]:
    """Re-parse the saved raw files of one filer into ``public/rows/<ticker>.jsonl``."""
    raw_dir = run / "public" / "raw" / "sec"
    submissions = json.loads((raw_dir / f"{ticker}-submissions.json").read_text())
    pages = [submissions] + [
        json.loads((raw_dir / f"{ticker}-{extra['name']}").read_text())
        for extra in submissions.get("filings", {}).get("files", [])
    ]
    if retrieved is None:
        facts_rel = f"public/raw/sec/{ticker}-companyfacts.json"
        retrieved = recorded_inputs(run, facts_rel)[facts_rel]["retrieved_at"]
    facts = json.loads((raw_dir / f"{ticker}-companyfacts.json").read_text())
    rows = sec.parse_companyfacts(
        facts, ticker, sec.accepted_times(pages), US_GAAP, retrieved_at=retrieved
    )
    rows_dir = run / "public" / "rows"
    rows_dir.mkdir(parents=True, exist_ok=True)
    with (rows_dir / f"{ticker}.jsonl").open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    audit = audit_inputs(rows)
    return {
        "name": submissions.get("name"),
        "sic": submissions.get("sic"),
        "fiscal_year_end": submissions.get("fiscalYearEnd"),
        "rows": len(rows),
        "ok": audit["ok"],
        "errors": len(audit["errors"]),
        "missing_metrics": sorted(set(US_GAAP) - {r["metric"] for r in rows}),
    }


def _write_report(run: Path, report: dict[str, Any]) -> None:
    path = run / "public" / "sec-fetch-report.json"
    merged = json.loads(path.read_text()) if path.exists() else {}
    merged.update(report)
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
    for ticker, entry in report.items():
        print(
            ticker,
            entry["name"],
            entry["rows"],
            "ok" if entry["ok"] else "ERRORS",
            "missing:",
            ",".join(entry["missing_metrics"]) or "-",
        )


def cmd_parse_sec(args: argparse.Namespace) -> int:
    run = Path(args.run)
    _write_report(run, {ticker: parse_saved(run, ticker) for ticker in args.tickers})
    return 0


JP_SOURCES = {
    "6857.T": {
        "index": "https://www.advantest.com/ja/investors/ir-library/result/",
        "base": "https://www.advantest.com",
        "pattern": r"/document/ja/investors/ir-library/result/J_FR_FY\d{4}_(?:1Q|2Q|3Q|FN|IFRS)\.pdf",
    },
    "8035.T": {
        "index": "https://www.tel.co.jp/ir/library/report/",
        "base": "https://www.tel.co.jp",
        "pattern": r"/ir/library/report/[0-9a-z]+-att/[^\"/]*tanshin[^\"/]*\.pdf",
        # annual financial data book, an independent IR source for reconciliation
        "extras": ["/ir/library/db/negqvb0000000ey6-att/db2026.xlsx"],
    },
    # Kioxia's IR page loads its list by script; the exchange (JPX) hosts the TDnet
    # documents. Its summaries add Non-GAAP columns, so the inline XBRL is parsed and
    # the PDFs are kept for the balance sheet pages.
    "285A.T": {
        "base": "https://www2.jpx.co.jp",
        "documents": [
            "/disc/285A0/140120250515552869.pdf",  # FY2025 (2025-05-15)
            "/disc/285A0/140120250808536248.pdf",  # FY2026 1Q (2025-08-08)
            "/disc/285A0/140120260515537803.pdf",  # FY2026 (2026-05-15)
            "/disc/285A0/140120260731505265.pdf",  # FY2027 1Q (2026-07-31)
            "/disc/285A0/081220250515552869_tse-acedifsm-285A0-202505153285A0-ixbrl.htm",
            "/disc/285A0/081220250808536248_tse-qcedifsm-285A0-202508083285A0-ixbrl.htm",
            "/disc/285A0/081220260515537803_tse-acedifsm-285A0-202605153285A0-ixbrl.htm",
            "/disc/285A0/081220260731505265_tse-qcedifsm-285A0-202607313285A0-ixbrl.htm",
        ],
    },
}


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": sec.USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def page_text_range(pdf: Path, first: int, last: int) -> str:
    """Pages of a release as layout text (needs poppler's pdftotext)."""
    return subprocess.run(
        ["pdftotext", "-layout", "-f", str(first), "-l", str(last), str(pdf), "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def page_text(pdf: Path, page: int) -> str:
    return page_text_range(pdf, page, page)


def parse_release(pdf: Path, **kw: str) -> list[dict[str, Any]]:
    """The summary sits on page 1, or page 2 behind a cover page; the share counts
    are on the summary page or one of the two pages after it."""

    def notes_after(page: int) -> str:
        try:  # pdftotext refuses a first page beyond the end
            return page_text_range(pdf, page + 1, page + 2)
        except subprocess.CalledProcessError:
            return ""

    def attempt(page: int) -> list[dict[str, Any]]:
        notes = notes_after(page)
        return jp.parse_summary(page_text(pdf, page), notes=notes, **kw)

    try:
        return attempt(1)
    except ValueError as first:
        try:
            return attempt(2)
        except ValueError:
            raise first from None


def _save_names(links: list[str]) -> dict[str, str]:
    """File name per link: the basename, or ``<folder>__<basename>`` where basenames repeat."""
    counts: dict[str, int] = {}
    for link in links:
        counts[link.rsplit("/", 1)[-1]] = counts.get(link.rsplit("/", 1)[-1], 0) + 1
    names = {}
    for link in links:
        folder, base = link.rsplit("/", 2)[-2:]
        names[link] = base if counts[base] == 1 else f"{folder}__{base}"
    return names


def fetch_jp_documents(run: Path, issuer: str) -> int:
    """Download the releases listed on the issuer's IR index that are not saved yet."""
    source = JP_SOURCES[issuer]
    raw_dir = run / "public" / "raw" / "jp" / issuer
    raw_dir.mkdir(parents=True, exist_ok=True)
    if "documents" in source:
        links = list(source["documents"])
    else:
        index = _get(source["index"]).decode("utf-8", "replace")
        links = sorted(set(re.findall(source["pattern"], index))) + list(source.get("extras", []))
    fetched = 0
    for link, name in _save_names(links).items():
        path = raw_dir / name
        if path.exists():
            continue
        url = source["base"] + link
        retrieved = _now()
        body = _get(url)
        path.write_bytes(body)
        record_input(run, path, url, hashlib.sha256(body).hexdigest(), retrieved)
        fetched += 1
        time.sleep(1)
    return fetched


def parse_saved_jp(run: Path, issuer: str) -> dict[str, Any]:
    """Re-parse the saved releases of one issuer into ``public/rows/<issuer>.jsonl``."""
    rows, failures = [], []
    records = recorded_inputs(run, f"public/raw/jp/{issuer}/")
    inline = sorted(rel for rel in records if rel.endswith("-ixbrl.htm"))
    pdfs = inline or sorted(rel for rel in records if rel.endswith(".pdf"))
    for rel in pdfs:
        entry = records[rel]
        kw = {
            "issuer_id": issuer,
            "source_url": entry["url"],
            "retrieved_at": entry["retrieved_at"],
        }
        try:
            if rel.endswith("-ixbrl.htm"):
                rows += jp.parse_summary_ixbrl((run / rel).read_bytes(), **kw)
            else:
                rows += parse_release(run / rel, **kw)
        except ValueError as exc:
            failures.append({"document": Path(rel).name, "error": str(exc)})
    rows_dir = run / "public" / "rows"
    rows_dir.mkdir(parents=True, exist_ok=True)
    with (rows_dir / f"{issuer}.jsonl").open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    audit = audit_inputs(rows)
    report = {
        "documents": len(pdfs),
        "rows": len(rows),
        "ok": audit["ok"],
        "errors": audit["errors"][:5],
        "parse_failures": failures,
    }
    (run / "public" / f"jp-fetch-report-{issuer}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        issuer,
        json.dumps({k: v for k, v in report.items() if k != "parse_failures"}, ensure_ascii=False),
        f"parse_failures={len(failures)}",
    )
    return report


def cmd_fetch_jp(args: argparse.Namespace) -> int:
    run = Path(args.run)
    for issuer in args.issuers:
        print(issuer, "fetched", fetch_jp_documents(run, issuer))
        parse_saved_jp(run, issuer)
    return 0


def cmd_parse_jp(args: argparse.Namespace) -> int:
    run = Path(args.run)
    for issuer in args.issuers:
        parse_saved_jp(run, issuer)
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    """Values copied by hand from original documents against the parsed as-of rows."""
    run, refs_path = Path(args.run), Path(args.refs)
    refs = json.loads(refs_path.read_text())
    as_of = _manifest(run)["as_of_utc"]
    checks, summary = [], {}
    for issuer in sorted({r["issuer_id"] for r in refs}):
        with (run / "public" / "rows" / f"{issuer}.jsonl").open() as handle:
            rows = [json.loads(line) for line in handle]
        mine = reconcile(rows, [r for r in refs if r["issuer_id"] == issuer], as_of)
        summary[issuer] = {"checked": len(mine), "matched": sum(c["match"] for c in mine)}
        checks += mine
    report = {
        "as_of_utc": as_of,
        "references": str(refs_path),
        "references_sha256": sha256_file(refs_path),
        "summary": summary,
        "checks": checks,
    }
    (run / "public" / "reconciliation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    for issuer, counts in summary.items():
        print(issuer, f"{counts['matched']}/{counts['checked']}")
    for check in checks:
        if not check["match"]:
            print(
                "MISMATCH",
                check["issuer_id"],
                check["metric"],
                check["period_end"],
                check["value"],
                check["parsed"],
                check.get("reason", ""),
            )
    return 0


# Quote per candidate: (yfinance ticker, currency, ordinary shares per quoted share).
QUOTES = {t: (t, "USD", 1) for t in CIKS}
QUOTES["TSM"] = ("TSM", "USD", 5)  # one ADR = five common shares
QUOTES.update({t: (t, "JPY", 1) for t in ("285A.T", "8035.T", "6857.T", "6146.T")})
FX = "JPY=X"


def cmd_fetch_prices(args: argparse.Namespace) -> int:
    """Raw daily closes (not dividend-adjusted) and yfinance's share counts, saved with sha256."""
    import warnings

    import pandas as pd
    import yfinance as yf

    run = Path(args.run)
    raw_dir = run / "public" / "raw" / "prices"
    raw_dir.mkdir(parents=True, exist_ok=True)
    as_of = datetime.fromisoformat(_manifest(run)["as_of_utc"])
    tickers = sorted({q[0] for q in QUOTES.values()} | {FX})
    retrieved = _now()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw = yf.download(
            tickers,
            start=(as_of - pd.Timedelta(days=45)).date().isoformat(),
            end=(as_of + pd.Timedelta(days=2)).date().isoformat(),
            auto_adjust=False,
            progress=False,
            group_by="column",
        )
    closes = raw["Close"]
    closes.index = pd.to_datetime(closes.index).tz_localize(None).normalize()
    path = raw_dir / "closes.csv"
    closes.sort_index().to_csv(path, float_format="%.6f")
    record_input(run, path, "yfinance download auto_adjust=False", sha256_file(path), retrieved)
    for ticker in tickers:
        if ticker == FX:
            continue
        retrieved = _now()
        info = yf.Ticker(ticker).get_info()
        keep = {
            k: info.get(k)
            for k in (
                "symbol",
                "currency",
                "sharesOutstanding",
                "impliedSharesOutstanding",
                "marketCap",
                "quoteType",
                "exchange",
            )
        }
        splits = yf.Ticker(ticker).splits
        keep["splits"] = [[str(day.date()), float(ratio)] for day, ratio in splits.items()]
        path = raw_dir / f"info-{ticker}.json"
        path.write_text(json.dumps(keep, indent=2) + "\n")
        record_input(
            run, path, f"yfinance Ticker({ticker}).get_info()", sha256_file(path), retrieved
        )
        time.sleep(0.5)
    print("saved", len(tickers), "series")
    return 0


def cmd_fetch_price_history(args: argparse.Namespace) -> int:
    """Daily closes (split-adjusted, not dividend-adjusted) from 400 days before the as-of
    date, for the one-year price decomposition."""
    import warnings

    import pandas as pd
    import yfinance as yf

    run = Path(args.run)
    as_of = datetime.fromisoformat(_manifest(run)["as_of_utc"])
    tickers = sorted({q[0] for q in QUOTES.values()} | {FX})
    retrieved = _now()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw = yf.download(
            tickers,
            start=(as_of - pd.Timedelta(days=400)).date().isoformat(),
            end=(as_of + pd.Timedelta(days=2)).date().isoformat(),
            auto_adjust=False,
            progress=False,
            group_by="column",
        )
    closes = raw["Close"]
    closes.index = pd.to_datetime(closes.index).tz_localize(None).normalize()
    path = run / "public" / "raw" / "prices" / "closes-history.csv"
    closes.sort_index().to_csv(path, float_format="%.6f")
    record_input(
        run, path, "yfinance download auto_adjust=False (400 days)", sha256_file(path), retrieved
    )
    print("saved", len(closes), "days x", len(tickers), "series")
    return 0


def _filing_shares(run: Path, issuer: str, as_of: str) -> tuple[float | None, str | None, str]:
    """Shares outstanding from the issuer's own filings at the as-of time:
    (count, count date, source). Multi-class SEC filers tag their cover counts by
    class, which companyfacts omits; their latest diluted weighted average stands in."""
    path = run / "public" / "rows" / f"{issuer}.jsonl"
    if not path.exists():
        return None, None, "no filings parsed"
    with path.open() as handle:
        rows = select_as_of([json.loads(line) for line in handle], as_of)
    latest = {}
    for metric in ("shares_outstanding", "shares_issued", "treasury_shares", "diluted_shares"):
        found = [r for r in rows if r["metric"] == metric and r["value"] is not None]
        if metric == "treasury_shares":  # a blank treasury count (－) in a release means none
            found += [
                dict(r, value=0.0) for r in rows if r["metric"] == metric and r["value"] is None
            ]
        if found:
            latest[metric] = max(
                found, key=lambda r: (r["period_end"], r["period_start"], r["value"] or 0)
            )
    if "shares_outstanding" in latest:
        row = latest["shares_outstanding"]
        return (
            row["value"],
            row["period_end"],
            f"cover page {row['form']} {row['period_end']} ({row['document_id']})",
        )
    if "shares_issued" in latest and "treasury_shares" in latest:
        issued, treasury = latest["shares_issued"], latest["treasury_shares"]
        if issued["period_end"] == treasury["period_end"]:
            return (
                issued["value"] - treasury["value"],
                issued["period_end"],
                f"決算短信 issued less treasury {issued['period_end']} ({issued['document_id']})",
            )
    if "diluted_shares" in latest:
        row = latest["diluted_shares"]
        return (
            row["value"],
            row["period_end"],
            f"diluted weighted average {row['period_start']}..{row['period_end']} ({row['document_id']}); class counts not in companyfacts",
        )
    return None, None, "no share count in filings"


def cmd_universe(args: argparse.Namespace) -> int:
    """Market caps at the as-of time and the spec 3.1 layer rule."""
    import csv

    run = Path(args.run)
    as_of = _manifest(run)["as_of_utc"]
    prereg = json.loads(PREREG.read_text())["universe"]
    with (run / "public" / "raw" / "prices" / "closes.csv").open() as handle:
        table = list(csv.DictReader(handle))
    date_col = next(iter(table[0]))

    def bars(ticker: str) -> list[tuple[str, float | None]]:
        return [(r[date_col][:10], float(r[ticker]) if r[ticker] else None) for r in table]

    fx_date, jpy_per_usd = last_final_close(bars(FX), FX, as_of)
    caps, detail = {}, []
    for layer in prereg["layers"]:
        for issuer in layer["candidates"]:
            ticker, currency, ratio = QUOTES[issuer]
            close_date, close = last_final_close(bars(ticker), ticker, as_of)
            info = json.loads(
                (run / "public" / "raw" / "prices" / f"info-{ticker}.json").read_text()
            )
            splits = [tuple(x) for x in info.get("splits", [])]
            filed, count_date, source = _filing_shares(run, issuer, as_of)
            yahoo = info.get("sharesOutstanding")
            if filed:
                used, applied = shares_at(filed, count_date, splits)
                used_source = source + (f"; splits applied {applied}" if applied else "")
            else:
                used, applied = yahoo, []
                later = [x for x in splits if x[0] >= "2025-01-01"]
                used_source = "yfinance sharesOutstanding, count date unknown" + (
                    f"; splits since 2025 {later} may be missing from it" if later else ""
                )
            cap = market_cap_usd(
                price=close,
                shares=used,
                currency=currency,
                jpy_per_usd=jpy_per_usd,
                adr_ratio=ratio,
            )
            caps[issuer] = cap
            detail.append(
                {
                    "issuer_id": issuer,
                    "layer": layer["id"],
                    "ticker": ticker,
                    "close": close,
                    "close_date": close_date,
                    "currency": currency,
                    "ordinary_per_quote": ratio,
                    "shares": used,
                    "shares_source": used_source,
                    "yfinance_shares": yahoo,
                    "filing_vs_yfinance": (used / (yahoo * ratio)) if filed and yahoo else None,
                    "market_cap_usd": cap,
                }
            )
    selected = select_universe(prereg["layers"], caps, must_include=prereg["must_include"])
    report = {
        "as_of_utc": as_of,
        "fx": {
            "pair": "JPY per USD",
            "close": jpy_per_usd,
            "date": fx_date,
            "source": "yfinance JPY=X",
        },
        "rule": "spec 3.1: full layers take every candidate; ranked layers take the largest market caps",
        "selected": selected,
        "candidates": detail,
    }
    (run / "public" / "universe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    for row in sorted(detail, key=lambda r: (r["layer"], -r["market_cap_usd"])):
        chosen = row["issuer_id"] in selected[row["layer"]]
        ratio = row["filing_vs_yfinance"]
        print(
            f"{row['layer']:17s} {row['issuer_id']:7s} {'*' if chosen else ' '} cap ${row['market_cap_usd'] / 1e9:8.1f}bn"
            f"  close {row['close']:>10.2f} {row['currency']} {row['close_date']}"
            f"  filing/yf {ratio:.3f}"
            if ratio
            else f"{row['layer']:17s} {row['issuer_id']:7s} {'*' if chosen else ' '} cap ${row['market_cap_usd'] / 1e9:8.1f}bn  ({row['shares_source']})"
        )
    print("JPY per USD", jpy_per_usd, fx_date)
    return 0


TREASURY_CSV = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve"
    "&field_tdr_date_value={year}&page&_format=csv"
)
MOF_CSV = "https://www.mof.go.jp/jgbs/reference/interest_rate/jgbcm.csv"
ERP_XLSX = "https://pages.stern.nyu.edu/~adamodar/pc/implprem/ERPbymonth.xlsx"


def cmd_fetch_rates(args: argparse.Namespace) -> int:
    """The registered r_j inputs: 10-year yields (US Treasury, 財務省) and Damodaran's ERP."""
    run = Path(args.run)
    as_of = _manifest(run)["as_of_utc"]
    raw_dir = run / "public" / "raw" / "rates"
    raw_dir.mkdir(parents=True, exist_ok=True)
    saved = {}
    for key, url, name in (
        ("treasury", TREASURY_CSV.format(year=as_of[:4]), f"treasury-{as_of[:4]}.csv"),
        ("mof", MOF_CSV, "jgbcm.csv"),
        ("erp", ERP_XLSX, "ERPbymonth.xlsx"),
    ):
        retrieved = _now()
        body = _get(url)
        path = raw_dir / name
        path.write_bytes(body)
        record_input(run, path, url, hashlib.sha256(body).hexdigest(), retrieved)
        saved[key] = (path, url)
        time.sleep(1)
    yields = {
        "US": rates.treasury_10y(saved["treasury"][0].read_text(), as_of),
        "JP": rates.mof_10y(saved["mof"][0].read_bytes().decode("shift_jis"), as_of),
    }
    erp = rates.damodaran_erp(saved["erp"][0].read_bytes(), as_of)
    report = {
        "as_of_utc": as_of,
        "rule": "r_j = local 10-year government yield (a day's row counts from 18:00 local time) + US implied ERP of the latest month started by the as-of date",
        "yields": {
            c: {"date": d, "yield": v, "source": saved[k][1]}
            for (c, (d, v)), k in zip(yields.items(), ("treasury", "mof"), strict=True)
        },
        "erp": {
            "month": erp[0],
            "erp": erp[1],
            "column": rates.ERP_COLUMN,
            "source": saved["erp"][1],
        },
        "r_j": {c: round(rates.discount_rate(c, yields, erp), 6) for c in yields},
    }
    (run / "public" / "rates.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({k: report[k] for k in ("yields", "erp", "r_j")}, ensure_ascii=False))
    return 0


FRENCH = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FRENCH_FILES = (
    "49_Industry_Portfolios_CSV.zip",
    "F-F_Research_Data_Factors_CSV.zip",
    "Siccodes49.zip",
)


def cmd_fetch_french(args: argparse.Namespace) -> int:
    """Kenneth French's 49 industry portfolios, the market factor and the SIC map (spec 7)."""
    run = Path(args.run)
    raw_dir = run / "public" / "raw" / "french"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name in FRENCH_FILES:
        retrieved = _now()
        body = _get(FRENCH + name)
        path = raw_dir / name
        path.write_bytes(body)
        record_input(run, path, FRENCH + name, hashlib.sha256(body).hexdigest(), retrieved)
        print("saved", name, len(body), "bytes")
        time.sleep(1)
    return 0


# Japanese issuers have no EDGAR SIC code: the code of their product line, as their US peers.
JP_SIC = {
    "6857.T": (3825, "semiconductor test equipment, as Teradyne"),
    "8035.T": (3559, "wafer processing equipment, as Lam Research and ASML"),
    "285A.T": (3674, "memory chips, as Micron"),
}
ADJUSTED = "closes-adjusted-5y.csv"


def cmd_fetch_adjusted_prices(args: argparse.Namespace) -> int:
    """Dividend- and split-adjusted daily closes from June 2021 for the selected issuers and
    the yen rate: their own 24- and 60-month returns (spec 7.2 現在の位置)."""
    import warnings

    import pandas as pd
    import yfinance as yf

    run = Path(args.run)
    as_of = datetime.fromisoformat(_manifest(run)["as_of_utc"])
    selected = [
        t
        for group in json.loads(PREREG.read_text())["universe"]["selected"].values()
        for t in group
    ]
    tickers = sorted({QUOTES[t][0] for t in selected} | {FX})
    retrieved = _now()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw = yf.download(
            tickers,
            start="2021-06-01",
            end=(as_of + pd.Timedelta(days=2)).date().isoformat(),
            auto_adjust=True,
            progress=False,
            group_by="column",
        )
    closes = raw["Close"]
    closes.index = pd.to_datetime(closes.index).tz_localize(None).normalize()
    path = run / "public" / "raw" / "prices" / ADJUSTED
    closes.sort_index().to_csv(path, float_format="%.6f")
    record_input(
        run,
        path,
        "yfinance download auto_adjust=True (from 2021-06-01)",
        sha256_file(path),
        retrieved,
    )
    print("saved", len(closes), "days x", len(tickers), "series")
    return 0


def _zip_text(path: Path) -> str:
    import zipfile

    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if not n.endswith("/")]
        if len(names) != 1:
            raise SystemExit(f"{path.name}: expected one file, found {names}")
        return archive.read(names[0]).decode("utf-8")


def _rules(registered: dict[str, Any]) -> dict[str, dict[str, Any]]:
    def kwargs(rule: dict[str, Any], net: str = "difference") -> dict[str, Any]:
        return {
            "threshold": rule["raw_24m"],
            "net_threshold": rule["net_24m"],
            "five_year": rule["raw_60m"],
            "net": net,
        }

    rules = {"primary": kwargs(registered["primary"])}
    rules |= {rule["id"]: kwargs(rule) for rule in registered["secondary"]}
    rules["primary_compounded"] = kwargs(registered["primary"], net="compounded")
    return rules


def _by_year(episodes: list[dict[str, Any]], key: str) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for e in episodes:
        if e[key] is not None:
            out.setdefault(e["month"][:4], []).append(float(e[key]))
    return out


def _summarize(episodes: list[dict[str, Any]], reps: int, seed: int) -> dict[str, Any]:
    """Counts, the crash rate and the mean returns after a start, with calendar-year intervals."""
    resolved = [e for e in episodes if e["crash"] is not None]
    out: dict[str, Any] = {
        "episodes": len(episodes),
        "resolved": len(resolved),
        "unresolved": len(episodes) - len(resolved),
        "crashes": sum(bool(e["crash"]) for e in resolved),
        "clusters": len({e["month"][:4] for e in resolved}),
    }
    for key, name in (
        ("crash", "crash_rate"),
        ("raw_12m", "raw_12m"),
        ("net_12m", "net_12m"),
        ("raw_24m", "raw_24m"),
        ("net_24m", "net_24m"),
    ):
        values = _by_year(episodes, key)
        if not values:
            out[name] = None
            continue
        draws = history.cluster_bootstrap(values, reps, seed)
        out[name] = {
            "mean": history.pooled_mean(values),
            "ci95": list(history.percentile_interval(draws)),
            "n": sum(len(v) for v in values.values()),
        }
    return out


def cmd_history(args: argparse.Namespace) -> int:
    """Spec 7 / Task 4: run-ups and crashes of the French industries, the GSY check, the
    current position of the selected issuers' industries and prices, and S."""
    import csv

    run = Path(args.run)
    as_of = _manifest(run)["as_of_utc"]
    prereg = json.loads(PREREG.read_text())
    reg = prereg["s_history"]
    raw = run / "public" / "raw" / "french"
    panel = history.parse_french_industry(_zip_text(raw / "49_Industry_Portfolios_CSV.zip"))
    factors = history.parse_french_factors(_zip_text(raw / "F-F_Research_Data_Factors_CSV.zip"))
    sic_ranges = history.parse_french_sic(_zip_text(raw / "Siccodes49.zip"))
    months = panel["months"]
    if factors["months"] != months:
        raise SystemExit("the industry and factor files cover different months")
    mkt = history.levels([a + b for a, b in zip(factors["mkt_rf"], factors["rf"], strict=True)])
    names = [n for n in panel["industries"] if n != "Other"]
    lv = {n: history.levels(panel["vw"][n]) for n in names}
    firms = panel["nfirms"]
    crash = {"months": reg["crash"]["window_months"], "drawdown": reg["crash"]["drawdown"]}
    reps, seed = reg["bootstrap"]["reps"], reg["bootstrap"]["seed"]
    rules = _rules(reg)
    flags = {
        rule: {
            n: history.runup_flags(lv[n], mkt, firms[n], min_firms=reg["min_firms"], **kw)
            for n in names
        }
        for rule, kw in rules.items()
    }
    episodes = {
        rule: [
            {"industry": n, "month": months[t], **history.outcome(lv[n], mkt, t, **crash)}
            for n in names
            for t in history.episode_starts(flags[rule][n], gap=reg["episode_gap_months"])
        ]
        for rule in rules
    }
    unconditional_by_year: dict[str, list[float]] = {}
    for n in names:
        for t, flag in enumerate(
            history.crash_flags(lv[n], firms[n], min_firms=reg["min_firms"], **crash)
        ):
            if flag is not None:
                unconditional_by_year.setdefault(months[t][:4], []).append(1.0 if flag else 0.0)

    def unconditional(lo: str, hi: str) -> dict[str, Any]:
        years = {y: v for y, v in unconditional_by_year.items() if lo[:4] <= y <= hi[:4]}
        return {
            "window": [lo, hi],
            "industry_months": sum(len(v) for v in years.values()),
            "crash_rate": history.pooled_mean(years),
        }

    check = reg["gsy_check"]
    in_window = [
        e
        for e in episodes["primary"]
        if check["runup_window"][0] <= e["month"] <= check["runup_window"][1]
    ]
    gsy = {
        "ours": {
            "episodes": len(in_window),
            "crashes": sum(bool(e["crash"]) for e in in_window),
            "clusters": len({e["month"][:4] for e in in_window}),
            "unconditional": unconditional(*check["unconditional_window"])["crash_rate"],
        },
        "gsy": {k: check[k] for k in ("episodes", "crashes", "unconditional")},
        "windows": {"runup": check["runup_window"], "unconditional": check["unconditional_window"]},
    }
    table = {rule: _summarize(eps, reps, seed) for rule, eps in episodes.items()}
    base_rate = unconditional(months[0], months[-1])
    primary_ci_low = table["primary"]["crash_rate"]["ci95"][0]
    last = len(months) - 1
    now: dict[str, Any] = {}
    for n in names:
        nets = []
        for t in range(last + 1):
            raw24, mkt24 = (
                history.trailing_return(lv[n], t, 24),
                history.trailing_return(mkt, t, 24),
            )
            if raw24 is not None and mkt24 is not None and (firms[n][t] or 0) >= reg["min_firms"]:
                nets.append((t, raw24 - mkt24))
        net_now = nets[-1][1] if nets and nets[-1][0] == last else None
        q75 = (
            history.quantile([x for _, x in nets], reg["s_weaken_net24_quantile"]) if nets else None
        )
        flag = flags["primary"][n][last]
        now[n] = {
            "run_up": flag,
            "raw_24m": history.trailing_return(lv[n], last, 24),
            "net_24m": net_now,
            "raw_60m": history.trailing_return(lv[n], last, 60),
            "net_24m_q75_to_date": q75,
            "firms": firms[n][last],
            "s": history.s_classify(
                flag,
                net_now,
                q75,
                crash_ci_low=primary_ci_low,
                unconditional=base_rate["crash_rate"],
            ),
        }
    with (run / "public" / "raw" / "prices" / ADJUSTED).open() as handle:
        rows = list(csv.DictReader(handle))
    date_col = next(iter(rows[0]))
    month_end: dict[str, dict[str, float]] = {}
    for r in rows:
        for k, v in r.items():
            if k != date_col and v:
                month_end.setdefault(r[date_col][:7], {})[k] = float(
                    v
                )  # the last day of each month wins
    span = [months[last - 60], months[last - 24], months[last]]
    companies = []
    for layer, group in prereg["universe"]["selected"].items():
        for issuer in group:
            if issuer in JP_SIC:
                sic, sic_source = JP_SIC[issuer][0], f"assigned: {JP_SIC[issuer][1]}"
            else:
                sub = json.loads(
                    (run / "public" / "raw" / "sec" / f"{issuer}-submissions.json").read_text()
                )
                sic, sic_source = int(sub["sic"]), f"EDGAR: {sub.get('sicDescription')}"
            industry = history.industry_for_sic(sic, sic_ranges)
            ticker = QUOTES[issuer][0]

            def usd(month: str, ticker: str = ticker) -> float | None:
                price = month_end.get(month, {}).get(ticker)
                if price is None or not ticker.endswith(".T"):
                    return price
                fx = month_end.get(month, {}).get(FX)
                return None if fx is None else price / fx

            p60, p24, p0 = (usd(m) for m in span)
            own = {
                "raw_24m": p0 / p24 - 1 if p0 and p24 else None,
                "raw_60m": p0 / p60 - 1 if p0 and p60 else None,
            }
            mkt24 = history.trailing_return(mkt, last, 24)
            own["net_24m"] = (
                None if own["raw_24m"] is None or mkt24 is None else own["raw_24m"] - mkt24
            )
            own["meets_primary_rule"] = (
                None
                if None in own.values()
                else own["raw_24m"] >= 1.0 and own["net_24m"] >= 1.0 and own["raw_60m"] >= 0.5
            )
            companies.append(
                {
                    "issuer_id": issuer,
                    "layer": layer,
                    "sic": sic,
                    "sic_source": sic_source,
                    "industry": industry,
                    "s": now[industry]["s"] if industry in now else "データ不足",
                    "own_price_usd": own,
                }
            )
    years = [e["month"][:4] for e in episodes["primary"] if e["crash"] is not None]
    report = {
        "as_of_utc": as_of,
        "label": f"取得版を固定した疑似時点順検証（French {panel['version']} 版、取得 {as_of[:10]}）",
        "data_version": panel["version"],
        "last_month": months[last],
        "own_price_months": span,
        "industries": len(names),
        "gsy_check": gsy,
        "unconditional": base_rate,
        "table": table,
        "episodes": episodes,
        "now": now,
        "companies": companies,
        "task6": history.predictive_splits(
            years, min_per_split=reg["predictive_min_clusters_per_split"]
        ),
    }
    (run / "public" / "history.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    text = _history_summary(report)
    (run / "public" / "history-summary.md").write_text(text)
    print(text)
    return 0


def _history_summary(report: dict[str, Any]) -> str:
    gsy, ours = report["gsy_check"]["gsy"], report["gsy_check"]["ours"]
    w = report["gsy_check"]["windows"]
    lines = [
        f"# 急騰と崩落の基底率（{report['label']}、{report['industries']}業種、{report['last_month']} まで）",
        "",
        f"## GSY との検算（急騰 {w['runup'][0]}〜{w['runup'][1]}、無条件 {w['unconditional'][0]}〜{w['unconditional'][1]}）",
        "",
        "| | 急騰件数 | うち崩落 | 崩落率 | 無条件の崩落確率 | 暦年クラスタ |",
        "|---|---:|---:|---:|---:|---:|",
        f"| GSY（2019） | {gsy['episodes']} | {gsy['crashes']} | {_pct(gsy['crashes'] / gsy['episodes'])} | {_pct(gsy['unconditional'])} | — |",
        f"| French 版 | {ours['episodes']} | {ours['crashes']} | {_pct(ours['crashes'] / ours['episodes'] if ours['episodes'] else None)} | {_pct(ours['unconditional'], 1)} | {ours['clusters']} |",
        "",
        f"## 全期間（結果の確定したエピソード、区間は暦年クラスタの bootstrap 95%）。無条件の崩落確率 {_pct(report['unconditional']['crash_rate'], 1)}（{report['unconditional']['industry_months']:,} 業種月）",
        "",
        "| 規則 | 急騰件数 | 未確定 | 崩落 | 崩落率 [95%] | 暦年クラスタ | 1年後 生 | 1年後 対市場 | 2年後 生 | 2年後 対市場 |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|---:|",
    ]

    def ci(x: dict[str, Any] | None) -> str:
        return (
            "—" if x is None else f"{_pct(x['mean'])} [{_pct(x['ci95'][0])}, {_pct(x['ci95'][1])}]"
        )

    for rule, t in report["table"].items():
        lines.append(
            f"| {rule} | {t['episodes']} | {t['unresolved']} | {t['crashes']} | {ci(t['crash_rate'])} | {t['clusters']} | "
            f"{ci(t['raw_12m'])} | {ci(t['net_12m'])} | {ci(t['raw_24m'])} | {ci(t['net_24m'])} |"
        )
    lines += [
        "",
        f"## 現在の位置（{report['last_month']}、業種は SIC から FF49、自社株価はドル建て・配当込み {report['own_price_months'][0]}〜{report['own_price_months'][2]}）",
        "",
        "| 層 | 銘柄 | SIC | 業種 | 業種の急騰 | 業種24か月 生 | 業種24か月 対市場 | 業種60か月 生 | 対市場の75分位（当時まで） | S | 自社24か月 生 | 自社24か月 対市場 | 自社60か月 生 |",
        "|---|---|---:|---|---|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    for c in report["companies"]:
        n = report["now"].get(c["industry"], {})
        o = c["own_price_usd"]
        run_up = {True: "該当", False: "非該当", None: "—"}[n.get("run_up")]
        lines.append(
            f"| {c['layer']} | {c['issuer_id']} | {c['sic']} | {c['industry']} | {run_up} | {_pct(n.get('raw_24m'))} | {_pct(n.get('net_24m'))} | "
            f"{_pct(n.get('raw_60m'))} | {_pct(n.get('net_24m_q75_to_date'))} | {c['s']} | {_pct(o['raw_24m'])} | {_pct(o['net_24m'])} | {_pct(o['raw_60m'])} |"
        )
    t6 = report["task6"]
    lines += [
        "",
        f"Task 6（予測検証）: 結果の確定した主定義のエピソードの暦年クラスタは {t6['clusters']}。"
        + (
            "3分割それぞれに10以上あるので実施できる。"
            if t6["feasible"]
            else "3分割それぞれに10以上（計30以上）が要るので行わない。"
        ),
        "",
        "崩落率は価格イベントの頻度で、バブルである確率ではない。",
        "",
    ]
    return "\n".join(lines)


HOLDINGS = PROJECT / "data" / "mtm-history.private.jsonl"
REFERENCE = PROJECT / "data" / "analysis_reference.private.json"
H10_URL = "https://www.federalreserve.gov/releases/h10/hist/dat00_ja.htm"
# Issuer names in the fund look-through of the analysis reference.
ISSUER_NAMES = {
    "Microsoft": "MSFT",
    "Amazon": "AMZN",
    "Alphabet": "GOOGL",
    "Meta Platforms": "META",
    "Oracle": "ORCL",
    "Nvidia": "NVDA",
    "Broadcom": "AVGO",
    "Advanced Micro Devices": "AMD",
    "Taiwan Semiconductor Manufacturing": "TSM",
    "Micron Technology": "MU",
    "Kioxia Holdings": "285A.T",
    "ASML": "ASML",
    "Lam Research": "LRCX",
    "Applied Materials": "AMAT",
    "KLA": "KLAC",
    "Advantest": "6857.T",
    "Tokyo Electron": "8035.T",
    "Arista Networks": "ANET",
    "Vertiv": "VRT",
    "CoreWeave": "CRWV",
}


def _proxy_map(run: Path) -> dict[str, Any]:
    return json.loads((run / "private" / "proxy-map.json").read_text())


def _proxy_currency(ticker: str) -> str:
    return "JPY" if ticker.endswith(".T") or ticker in ("^N225", "JPY") else "USD"


def cmd_fetch_proxies(args: argparse.Namespace) -> int:
    """Daily closes of the proxies in the private proxy map (saved on the private side:
    the tickers name the holdings) and the Fed H.10 yen rate from 2000."""
    import warnings

    import pandas as pd
    import yfinance as yf

    run = Path(args.run)
    holdings = _proxy_map(run)["holdings"]
    tickers = sorted(
        {
            t
            for h in holdings.values()
            for t in (h.get("proxy"), h.get("fallback"))
            if t and t != "JPY"
        }
    )
    retrieved = _now()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw = yf.download(
            tickers,
            start="1999-12-01",
            end="2023-01-01",
            auto_adjust=True,
            progress=False,
            group_by="column",
        )
    closes = raw["Close"]
    if isinstance(closes, pd.Series):
        closes = closes.to_frame(tickers[0])
    closes.index = pd.to_datetime(closes.index).tz_localize(None).normalize()
    out = run / "private" / "raw" / "proxies"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "closes.csv"
    closes.sort_index().to_csv(path, float_format="%.6f")
    record_input(
        run,
        path,
        "yfinance download auto_adjust=True, 1999-12 to 2022-12 (tickers in private/proxy-map.json)",
        sha256_file(path),
        retrieved,
    )
    retrieved = _now()
    body = _get(H10_URL)
    h10 = run / "public" / "raw" / "rates" / "h10-jpy-2000.htm"
    h10.write_bytes(body)
    record_input(run, h10, H10_URL, hashlib.sha256(body).hexdigest(), retrieved)
    print("saved", len(closes), "days x", len(tickers), "proxies and", len(body), "bytes of H.10")
    return 0


def _proxy_prices(run: Path) -> tuple[list[str], dict[str, list[float | None]]]:
    """Yen proxy series on one calendar: each close carried forward at most five rows,
    dollar series times the H.10 rate of the same day, yen cash constant."""
    import csv

    with (run / "private" / "raw" / "proxies" / "closes.csv").open() as handle:
        table = list(csv.DictReader(handle))
    date_col = next(iter(table[0]))
    fx = {
        d: v
        for d, v in portfolio.parse_h10(
            (run / "public" / "raw" / "rates" / "h10-jpy-2000.htm").read_text()
        )
        if v
    }
    dates = sorted(
        {r[date_col][:10] for r in table} | {d for d in fx if d <= table[-1][date_col][:10]}
    )

    def carried(raw: dict[str, float]) -> list[float | None]:
        out: list[float | None] = []
        last, age = None, 0
        for d in dates:
            if d in raw:
                last, age = raw[d], 0
            else:
                age += 1
            out.append(last if last is not None and age <= 5 else None)
        return out

    usdjpy = carried(fx)
    prices: dict[str, list[float | None]] = {"JPY": [1.0] * len(dates)}
    for ticker in (c for c in table[0] if c != date_col):
        series = carried({r[date_col][:10]: float(r[ticker]) for r in table if r[ticker]})
        if _proxy_currency(ticker) == "USD":
            series = [
                None if a is None or b is None else a * b
                for a, b in zip(series, usdjpy, strict=True)
            ]
        prices[ticker] = series
    return dates, prices


def _holdings(path: Path, as_of: str) -> dict[str, Any]:
    """Today's holdings from the daily mark-to-market history (read only): the latest
    record written before the as-of time, values summed by symbol across accounts, and
    the cash left in the accounts (yen, as in the account snapshots)."""
    cutoff = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    usable = [r for r in records if datetime.fromisoformat(r["generated_at"]) <= cutoff]
    if not usable:
        raise SystemExit(f"no holdings record written before {as_of}")
    record = max(usable, key=lambda r: datetime.fromisoformat(r["generated_at"]))
    values: dict[str, float] = {}
    for key, position in record["positions"].items():
        symbol = key.split(":", 1)[1]
        values[symbol] = values.get(symbol, 0.0) + position["value_jpy"]
    cash = record["total_jpy"] - sum(p["value_jpy"] for p in record["positions"].values())
    if cash > 0:
        values["CASH_JPY"] = cash
    return {
        "as_of": record["as_of"],
        "generated_at": record["generated_at"],
        "values": values,
        "total_jpy": record["total_jpy"],
        "cash_jpy": cash,
    }


def _economics(instrument: dict[str, Any]) -> tuple[str | None, float | None, float]:
    """Economic currency, hedge ratio and foreign share of a holding: a US-listed fund is
    dollars and unhedged, a Japanese listing of Japanese assets is yen, and a fund
    mixing currencies without a disclosed hedge is unknown (spec 8.1: never inferred)."""
    mix = instrument.get("currency_mix") or {}
    if len([w for w in mix.values() if w > 0]) > 1:
        return "mixed", None, 1 - mix.get("JPY", 0.0)
    country = instrument.get("country_default")
    if country == "米国":
        return "USD", 0.0, 1.0
    if country == "日本":
        return "JPY", None, 0.0
    return None, None, 1.0


def _fund_paths(
    holdings: dict[str, Any], reference: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, Any]]:
    """Look-through paths of every holding but cash, the theme of each issuer, and each
    holding's reference date, known issuer share and currency."""
    instruments = {i["symbol"]: i for i in reference["instruments"]}
    paths: list[dict[str, Any]] = []
    themes: dict[str, str] = {}
    funds: dict[str, Any] = {}
    for symbol, value in holdings["values"].items():
        if symbol == "CASH_JPY":
            continue
        instrument = instruments.get(symbol, {})
        weights: dict[str, float] = {}
        for e in instrument.get("exposures", []):
            if e["group"] == "issuer":
                issuer = ISSUER_NAMES.get(e["category"], e["category"])
                weights[issuer] = weights.get(issuer, 0.0) + e["weight"]
                if e.get("theme"):
                    themes[issuer] = e["theme"]
        currency, hedge, foreign = _economics(instrument)
        paths += portfolio.lookthrough_paths(
            symbol,
            value,
            weights,
            economic_currency=currency,
            fx_hedge_ratio=hedge,
            as_of=instrument.get("as_of"),
        )
        funds[symbol] = {
            "value_jpy": value,
            "reference_as_of": instrument.get("as_of"),
            "known_share": sum(weights.values()),
            "economic_currency": currency,
            "fx_hedge_ratio": hedge,
            "foreign_share": foreign,
            "weights": weights,
        }
    return paths, themes, funds


def _path_impact(path: dict[str, Any], change: float, fx: float) -> float | None:
    if path["economic_currency"] == "JPY":
        return path["value_jpy"] * change
    if path["economic_currency"] == "USD" and path["fx_hedge_ratio"] == 0.0:
        return path["value_jpy"] * portfolio.fx_compose(change, fx)
    return None


def _total(values: list[float | None]) -> float | None:
    return None if any(v is None for v in values) else sum(v for v in values if v is not None)


def cmd_portfolio(args: argparse.Namespace) -> int:
    """Spec 8.1 / Task 5: the private holdings impact. Exposure through the funds, the
    idiosyncratic layer at r* and the systematic replay, side by side and never added.
    Writes only under private/."""
    run = Path(args.run)
    as_of = _manifest(run)["as_of_utc"]
    prereg = json.loads(PREREG.read_text())
    reg, g_inf = prereg["portfolio"], prereg["valuation"]["g_inf"]
    holdings = _holdings(Path(args.holdings), as_of)
    reference = json.loads(Path(args.reference).read_text())
    proxy_map = _proxy_map(run)
    valuation = {
        c["issuer_id"]: c
        for c in json.loads((run / "public" / "valuation.json").read_text())["companies"]
    }
    paths, themes, funds = _fund_paths(holdings, reference)
    exposure = portfolio.issuer_exposure(paths)
    nav = holdings["total_jpy"]
    theme = reg["ai_exposure"]["theme"]
    shocks = sorted({0.0, *reg["fx_shocks"], *reg["fx_display"]})
    ai_rows = []
    for issuer in sorted(
        (i for i in exposure["issuers"] if themes.get(i) == theme),
        key=lambda i: -exposure["issuers"][i]["value_jpy"],
    ):
        item, entry = exposure["issuers"][issuer], valuation.get(issuer)
        row: dict[str, Any] = {
            "issuer_id": issuer,
            "value_jpy": item["value_jpy"],
            "share_of_nav": item["value_jpy"] / nav,
            "via": sorted({p["position_symbol"] for p in item["paths"]}),
        }
        ai_rows.append(row)
        if entry is None or entry.get("status") != "評価":
            reason = (
                "not among the selected issuers"
                if entry is None
                else entry["status"].removeprefix("未評価: ")
            )
            row |= {"status": "unevaluated", "reason": reason}
            continue
        row["flags"] = [
            f for f in entry.get("flags", []) if f.startswith("trailing revenue growth")
        ]
        flows = entry["flows"]

        def value_at(kind: str, r: float, flows: dict[str, Any] = flows) -> float:
            return enterprise_value(flows[kind]["fcff"], flows[kind]["terminal_fcff"], r, g_inf)

        market = entry["market"]
        layer = portfolio.idiosyncratic_layer(
            market["ev_observed"],
            market["ev_observed"] - market["market_cap"],
            value_at,
            shift=reg["stress_discount_rate_shift"],
            bounds=(g_inf + 0.01, 0.30),
        )
        row |= {
            "status": layer["status"],
            "r_star": layer["r_star"],
            "r_j": entry["r_j"],
            "change": layer["change"],
        }
        if layer["status"] != "ok":
            row["reason"] = layer.get("reason")
            continue
        row["impact_jpy"] = {
            "optimistic": _total(
                [_path_impact(p, layer["change"]["optimistic"], 0.0) for p in item["paths"]]
            ),
            "central": 0.0,
            "stress": {
                f"{fx:+.0%}": _total(
                    [_path_impact(p, layer["change"]["stress"], fx) for p in item["paths"]]
                )
                for fx in shocks
            },
        }
    evaluated = {r["issuer_id"] for r in ai_rows if r.get("status") == "ok"}
    usd_other = sum(
        p["value_jpy"]
        for p in paths
        if p["issuer_id"] not in evaluated and p["economic_currency"] == "USD"
    )
    fx_unknown = sum(
        f["value_jpy"] * f["foreign_share"]
        for f in funds.values()
        if f["economic_currency"] in ("mixed", None)
    )
    ai_total = sum(r["value_jpy"] for r in ai_rows)
    known_ai = sum(r["value_jpy"] for r in ai_rows if r.get("status") == "ok")
    ok_rows = [r for r in ai_rows if r.get("status") == "ok"]
    scenarios = {
        "optimistic": {"evaluated_ai": sum(r["impact_jpy"]["optimistic"] or 0.0 for r in ok_rows)},
        "central": {"evaluated_ai": 0.0},
        "stress": {
            key: {
                "evaluated_ai": sum(r["impact_jpy"]["stress"][key] or 0.0 for r in ok_rows),
                "fx_only_other_dollar_paths": usd_other * fx,
            }
            for fx in shocks
            for key in [f"{fx:+.0%}"]
        },
    }
    dates, prices = _proxy_prices(run)
    mapped = proxy_map["holdings"]
    systematic = portfolio.systematic_layer(
        holdings["values"],
        {s: h["proxy"] for s, h in mapped.items() if h.get("proxy")},
        prices,
        dates,
        reg["episodes"],
        fallback_map={s: h["fallback"] for s, h in mapped.items() if h.get("fallback")},
    )
    held_on = holdings["as_of"]
    report = {
        "as_of_utc": as_of,
        "holdings": {k: holdings[k] for k in ("as_of", "generated_at", "total_jpy", "cash_jpy")}
        | {"values": holdings["values"]},
        "reference_as_of": reference.get("as_of"),
        "funds": {
            s: {k: v for k, v in f.items() if k != "weights"}
            | {
                "age_days": (
                    date.fromisoformat(held_on) - date.fromisoformat(f["reference_as_of"])
                ).days
                if f["reference_as_of"]
                else None,
                "evaluated_share": sum(w for i, w in f["weights"].items() if i in evaluated),
            }
            for s, f in funds.items()
        },
        "ai_exposure": {
            "theme": theme,
            "total_jpy": ai_total,
            "share_of_nav": ai_total / nav,
            "evaluated_jpy": known_ai,
            "evaluated_share": known_ai / ai_total if ai_total else None,
            "coverage_target": reg["coverage_target"],
            "unclassified_fund_remainder_jpy": exposure["unknown_jpy"],
        },
        "idiosyncratic": {
            "issuers": ai_rows,
            "scenarios": scenarios,
            "fx_unknown_hedge_jpy": fx_unknown,
            "dollar_paths_outside_evaluated_jpy": usd_other,
        },
        "systematic": systematic,
        "proxy_map": mapped,
        "unproxied": sorted(
            s for s in holdings["values"] if not (mapped.get(s) or {}).get("proxy")
        ),
    }
    out = run / "private"
    (out / "portfolio-impact.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    text = _portfolio_summary(report)
    (out / "portfolio-impact.md").write_text(text)
    print(f"wrote {out / 'portfolio-impact.md'}")
    return 0


def _man(x: float | None) -> str:
    """Yen in units of 10,000 (万円)."""
    return "—" if x is None else f"{x / 1e4:,.0f}"


def _portfolio_summary(r: dict[str, Any]) -> str:
    h, ai, idio = r["holdings"], r["ai_exposure"], r["idiosyncratic"]
    nav = h["total_jpy"]
    lines = [
        f"# 保有への影響（私有、基準 {r['as_of_utc']}、保有 {h['as_of']}、単位 万円）",
        "",
        "固有層と系統層は同じ下落を別の見方で測るので、足し合わせない。確率は付けない。",
        "",
        f"- 評価額 {_man(nav)}（うち円の現金 {_man(h['cash_jpy'])}）。参照データ {r['reference_as_of']}。",
        f"- AI サプライチェーンの発行体（{ai['theme']}）への露出 {_man(ai['total_jpy'])}（評価額の {_pct(ai['share_of_nav'], 1)}）。"
        f"うち再評価できたのは {_pct(ai['evaluated_share'], 1)}（目標 {_pct(ai['coverage_target'])}）。",
        f"- 発行体の内訳が分からない残り {_man(ai['unclassified_fund_remainder_jpy'])} は未分類（債券・バランス型の全額と、株式ファンドの開示外の部分。後者は AI 発行体を含みうる）。",
        "",
        "## 固有層（r* で再評価、中央の変化は0）",
        "",
        "| 発行体 | 露出 | 評価額比 | 経路 | r* | r_j | 楽観 | ストレス（r*+2pt） | 楽観の影響 | ストレス・為替0 | ストレス・円高10% | ストレス・円安10% | 状態 |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in idio["issuers"]:
        ch, imp = row.get("change") or {}, row.get("impact_jpy") or {}
        stress = imp.get("stress", {})
        lines.append(
            f"| {row['issuer_id']} | {_man(row['value_jpy'])} | {_pct(row['share_of_nav'], 1)} | {'・'.join(row['via'])} | "
            f"{_pct(row.get('r_star'), 1)} | {_pct(row.get('r_j'), 2)} | {_pct(ch.get('optimistic'))} | {_pct(ch.get('stress'))} | "
            f"{_man(imp.get('optimistic'))} | {_man(stress.get('+0%'))} | {_man(stress.get('-10%'))} | {_man(stress.get('+10%'))} | "
            f"{'評価' if row.get('status') == 'ok' else '未評価: ' + str(row.get('reason'))} |"
        )
    flagged = [
        f"{row['issuer_id']}（{row['flags'][0]}）" for row in idio["issuers"] if row.get("flags")
    ]
    if flagged:
        lines += [
            "",
            "楽観の値が大きい会社: "
            + "、".join(flagged)
            + "。登録した楽観の減衰（φ=0.85）が循環の山の伸びを延ばした値。",
        ]
    sc = idio["scenarios"]
    lines += [
        "",
        "| シナリオ | 評価できた AI 発行体 | 他のドル建て経路（為替だけ） | 計（既知の部分） |",
        "|---|---:|---:|---:|",
        f"| 1 需要が成長を続ける（楽観） | {_man(sc['optimistic']['evaluated_ai'])} | — | {_man(sc['optimistic']['evaluated_ai'])} |",
        "| 2 成長が正常化（中央、基準） | 0 | — | 0 |",
    ]
    for key, label in (
        ("-20%", "円高20%"),
        ("-10%", "円高10%"),
        ("+0%", "為替0"),
        ("+10%", "円安10%"),
        ("+20%", "円安20%"),
    ):
        s = sc["stress"].get(key)
        if s:
            total = s["evaluated_ai"] + s["fx_only_other_dollar_paths"]
            lines.append(
                f"| 3 資金・需要が同時に悪化（ストレス、{label}） | {_man(s['evaluated_ai'])} | {_man(s['fx_only_other_dollar_paths'])} | {_man(total)}（{_pct(total / nav, 1)}） |"
            )
    lines += [
        "",
        f"未評価: AI 発行体のうち再評価できない分 {_man(ai['total_jpy'] - ai['evaluated_jpy'])}、"
        f"為替ヘッジが開示されていない外貨部分 {_man(idio['fx_unknown_hedge_jpy'])}（為替ショックを当てていない）。",
        "",
        "## 系統層（過去局面の再生、代理系列は円建て）",
        "",
        "| 局面 | 期間 | 影響 | 評価額比 | 完全 | 価格の付いた比率 | 代理 | 理由 |",
        "|---|---|---:|---:|---|---:|---|---|",
    ]
    for e in r["systematic"]:
        proxies = ", ".join(f"{k}→{v}" for k, v in sorted(e["proxies"].items()))
        lines.append(
            f"| {e['label']} | {e['start']}〜{e['end']} | {_man(e['impact_jpy'])} | {_pct(e['impact_pct'], 1)} | {'はい' if e['complete'] else 'いいえ'} | "
            f"{_pct(e['priced_nav_ratio'], 1)} | {proxies} | {e['reason']} |"
        )
    lines += [
        "",
        f"代理の無い保有（未評価）: {', '.join(r['unproxied']) or 'なし'}。",
        "",
        "## ファンドの構成の鮮度と残り",
        "",
        "| 保有 | 評価額 | 経済的通貨 | ヘッジ | 参照日 | 経過日数 | 発行体が分かる比率 | 再評価できた比率 |",
        "|---|---:|---|---|---|---:|---:|---:|",
    ]
    for symbol, f in sorted(r["funds"].items(), key=lambda kv: -kv[1]["value_jpy"]):
        hedge = "—" if f["fx_hedge_ratio"] is None else _pct(f["fx_hedge_ratio"])
        lines.append(
            f"| {symbol} | {_man(f['value_jpy'])} | {f['economic_currency'] or '不明'} | {hedge} | {f['reference_as_of'] or '—'} | "
            f"{f['age_days'] if f['age_days'] is not None else '—'} | {_pct(f['known_share'])} | {_pct(f['evaluated_share'])} |"
        )
    lines += [
        "",
        "代理と保有の違い: "
        + "; ".join(f"{s}: {h.get('difference') or h['kind']}" for s, h in r["proxy_map"].items()),
        "",
    ]
    return "\n".join(lines) + "\n"


def cmd_report(args: argparse.Namespace) -> int:
    """The public market summary (spec 8): V, F and S of every selected issuer. No holdings."""
    run = Path(args.run)
    valuation = json.loads((run / "public" / "valuation.json").read_text())
    funding_by = {
        c["issuer_id"]: c
        for c in json.loads((run / "public" / "funding.json").read_text())["companies"]
    }
    hist = json.loads((run / "public" / "history.json").read_text())
    s_by = {c["issuer_id"]: c for c in hist["companies"]}
    rows = []
    for c in valuation["companies"]:
        issuer = c["issuer_id"]
        evaluated = c.get("status") == "評価"
        val = c.get("valuation", {}) if evaluated else {}
        irr = val.get("implied_irr", {})
        rows.append(
            {
                "issuer_id": issuer,
                "layer": c["layer"],
                "v": val.get("v", "未評価"),
                "ev_ratio_central": (val.get("ev_ratio") or {}).get("central"),
                "r_star": irr["solutions"][0] if irr.get("status") == "ok" else None,
                "r_j": c.get("r_j"),
                "f": funding_by.get(issuer, {}).get("f", "未評価"),
                "s": s_by.get(issuer, {}).get("s", "データ不足"),
                "industry": s_by.get(issuer, {}).get("industry"),
            }
        )
    report = {"as_of_utc": valuation["as_of_utc"], "s_label": hist.get("label"), "companies": rows}
    (run / "public" / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    lines = [
        f"# AI バブル仮説の判定（市場のみ、基準 {report['as_of_utc']}）",
        "",
        "V は価格の正当化、F は資金の脆さ、S は業種の価格の過熱。どれも「仮説を支持／弱める／混在／データ不足」で、一つのスコアにまとめない。",
        "",
        "| 層 | 銘柄 | V | 中央/観測 | r* | r_j | F | S（業種） |",
        "|---|---|---|---:|---:|---:|---|---|",
    ]
    for row in rows:
        ratio = "—" if row["ev_ratio_central"] is None else f"{row['ev_ratio_central']:.2f}"
        lines.append(
            f"| {row['layer']} | {row['issuer_id']} | {row['v']} | {ratio} | "
            f"{_pct(row['r_star'], 1)} | {_pct(row['r_j'], 2)} | {row['f']} | {row['s']}（{row['industry'] or '—'}） |"
        )
    counts = {k: {} for k in ("v", "f", "s")}
    for row in rows:
        for k in counts:
            counts[k][row[k]] = counts[k].get(row[k], 0) + 1
    lines += [
        "",
        "件数: "
        + "; ".join(
            f"{k.upper()} " + "・".join(f"{lab}{n}" for lab, n in sorted(v.items()))
            for k, v in counts.items()
        ),
        "",
    ]
    (run / "public" / "report.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


# Selected issuers the first table leaves out, and why (spec 3.1: 未評価, not filled in).
NOT_EVALUATED = {
    "TSM": "未評価: quarterly statements are not in machine-readable filings (20-F annual, IFRS) and no 10-year yield source for TWD is registered",
    "ASML": "未評価: quarterly statements are not in machine-readable filings (20-F annual) and no 10-year yield source for EUR is registered",
}
SEMI_LAYERS = ("design", "fab_memory", "equipment")
SUPPLY_LAYERS = SEMI_LAYERS
BUYER_LAYER = "buyers"


def _country(issuer: str) -> str:
    return "JP" if issuer.endswith(".T") else "US"


def load_rows(run: Path, issuer: str) -> list[dict[str, Any]]:
    """Parsed rows of one issuer plus its hand-copied rows (docs/ai-bubble/manual-inputs.json)."""
    with (run / "public" / "rows" / f"{issuer}.jsonl").open() as handle:
        rows = [json.loads(line) for line in handle]
    manual = json.loads(MANUAL.read_text())["rows"]
    return rows + [r for r in manual if r["issuer_id"] == issuer]


def _bars(run: Path, name: str, ticker: str) -> list[tuple[str, float | None]]:
    import csv

    with (run / "public" / "raw" / "prices" / name).open() as handle:
        table = list(csv.DictReader(handle))
    date_col = next(iter(table[0]))
    return [(r[date_col][:10], float(r[ticker]) if r[ticker] else None) for r in table]


def _shares_now(
    run: Path, issuer: str, as_of: str, splits: list[tuple[str, float]]
) -> tuple[float, str]:
    """Issuer share count at ``as_of`` on the split basis of the (split-adjusted) closes."""
    count, count_date, source = _filing_shares(run, issuer, as_of)
    if count is None:
        raise ValueError(f"{issuer}: {source}")
    shares, applied = shares_at(count, count_date, splits)
    return shares, source + (f"; splits applied {applied}" if applied else "")


def _stale_leases(rows: list[dict[str, Any]], on: str) -> dict[str, Any] | None:
    metrics = ("finance_lease_liability", "finance_lease_current", "finance_lease_noncurrent")
    found = [
        r
        for r in rows
        if r["metric"] in metrics and r["period_start"] == r["period_end"] and r["value"]
    ]
    if not found or any(r["period_end"] == on for r in found):
        return None
    latest = max(r["period_end"] for r in found)
    at = {r["metric"]: r["value"] for r in found if r["period_end"] == latest}
    value = at.get(
        "finance_lease_liability",
        at.get("finance_lease_current", 0.0) + at.get("finance_lease_noncurrent", 0.0),
    )
    return {"date": latest, "value": value}


def _decomposition(
    run: Path, issuer: str, ticker: str, as_of: str, rows_all, ni_metric, splits, price1, eps1
):
    then = (datetime.fromisoformat(as_of) - __import__("datetime").timedelta(days=365)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    try:
        _, price0 = last_final_close(_bars(run, "closes-history.csv", ticker), ticker, then)
        rows0 = select_as_of(rows_all, then)
        ni0 = ttm(rows0, ni_metric)
        shares0, _ = _shares_now(run, issuer, then, splits)
    except (ValueError, KeyError) as exc:
        return {"status": f"not built: {exc}"}
    if ni0 is None:
        return {"status": "not built: no trailing net income a year earlier"}
    eps0 = ni0["value"] / shares0
    out = price_decomposition(price0=price0, price1=price1, eps0=eps0, eps1=eps1)
    base = {
        "from": then,
        "price0": price0,
        "eps0": eps0,
        "ni0_end": ni0["end"],
        "price1": price1,
        "eps1": eps1,
    }
    return {**base, **(out or {"status": "EPS not positive at both ends"})}


def cmd_valuation(args: argparse.Namespace) -> int:
    """Spec 5 / Task 2: multiples and the reverse DCF of every selected issuer at r_j."""
    run = Path(args.run)
    as_of = _manifest(run)["as_of_utc"]
    prereg = json.loads(PREREG.read_text())
    details, registered = prereg["valuation_details"], prereg["valuation"]
    universe = json.loads((run / "public" / "universe.json").read_text())
    rates_report = json.loads((run / "public" / "rates.json").read_text())
    jpy_per_usd = universe["fx"]["close"]
    quotes = {c["issuer_id"]: c for c in universe["candidates"]}
    years, g_inf, band = registered["T"], registered["g_inf"], registered["v_band"]
    solver = details["solver_bounds"]
    companies, paths = [], {}
    for layer, issuers in universe["selected"].items():
        for issuer in issuers:
            entry: dict[str, Any] = {"issuer_id": issuer, "layer": layer, "flags": []}
            companies.append(entry)
            if issuer in NOT_EVALUATED:
                entry["status"] = NOT_EVALUATED[issuer]
                continue
            country = _country(issuer)
            quote = quotes[issuer]
            currency = quote["currency"]
            fx = jpy_per_usd if currency == "JPY" else 1.0
            r_j = rates_report["r_j"][country]
            rows_all = load_rows(run, issuer)
            rows = select_as_of(rows_all, as_of)
            base = base_from_rows(rows, statutory_tax=details["statutory_tax"][country])
            entry.update(country=country, currency=currency, r_j=r_j, base=base)
            entry["flags"] += base.get("flags", [])
            if base.get("g0") is not None and base["g0"] > 1.0:
                entry["flags"].append(
                    f"trailing revenue growth {base['g0']:.0%}: the registered fade carries a cyclical peak forward (read with the cycle PER and the stress case)"
                )
            if not base["evaluable"]:
                entry["status"] = f"未評価: {base['not_evaluable_because']}"
                continue
            info = json.loads(
                (run / "public" / "raw" / "prices" / f"info-{quote['ticker']}.json").read_text()
            )
            splits = [tuple(x) for x in info.get("splits", [])]
            shares, shares_source = _shares_now(run, issuer, as_of, splits)
            cap = quote["close"] * shares / quote["ordinary_per_quote"]
            bal = base["balance"]
            ev = cap + bal["debt"] + bal["finance_leases"] - bal["cash_like"] - bal["investments"]
            entry["market"] = {
                "close": quote["close"],
                "close_date": quote["close_date"],
                "shares": shares,
                "shares_source": shares_source,
                "market_cap": cap,
                "market_cap_usd": cap / fx,
                "ev_observed": ev,
                "ev_observed_usd": ev / fx,
                "ev_parts": {
                    k: bal[k] for k in ("debt", "finance_leases", "cash_like", "investments")
                },
            }
            stale = _stale_leases(rows, bal["date"])
            if stale:
                entry["flags"].append(
                    f"finance leases not tagged at {bal['date']}: {stale['value']:,.0f} at {stale['date']} left out ({stale['value'] / ev:.2%} of EV)"
                )
            result = value_company(
                base,
                r_j=r_j,
                ev_observed=ev,
                years=years,
                g_inf=g_inf,
                band=band,
                growth_bounds=tuple(solver["g0"]),
                margin_bounds=tuple(solver["target_margin"]),
            )
            entry["valuation"] = result
            entry["flows"] = {
                kind: {k: flow[k] for k in ("fcff", "terminal_fcff")}
                for kind in ("central", "optimistic", "stress")
                for flow in [
                    project_fcff(
                        base, scenario_paths(base, kind, r_j=r_j, years=years, g_inf=g_inf), years
                    )
                ]
            }
            if bal["investments"]:
                capital = bal["invested_capital"] + bal["investments"]
                gross = dict(
                    base,
                    sales_to_capital=base["revenue"] / capital,
                    roic=(base["roic"] * bal["invested_capital"]) / capital,
                )
                ev_gross = ev + bal["investments"]
                alt = value_company(
                    gross,
                    r_j=r_j,
                    ev_observed=ev_gross,
                    years=years,
                    g_inf=g_inf,
                    band=band,
                    growth_bounds=tuple(solver["g0"]),
                    margin_bounds=tuple(solver["target_margin"]),
                )
                entry["sensitivity_investments_not_netted"] = {
                    "ev_observed": ev_gross,
                    "v": alt["v"],
                    "ev_ratio": alt["ev_ratio"],
                }
            ni_metric = "net_income_parent" if country == "JP" else "net_income"
            ni = ttm(rows, ni_metric)
            ocf, capex = ttm(rows, "operating_cf"), ttm(rows, "capex")

            def same(x: dict[str, Any] | None, end: str = base["end"]) -> float | None:
                return x["value"] if x and x["end"] == end else None

            if ni is None or ni["end"] != base["end"]:
                entry["flags"].append("net income of the revenue's twelve months not available")
            else:
                entry["multiples"] = multiples(
                    market_cap=cap,
                    ev=ev,
                    net_income=ni["value"],
                    ebit=base["ebit"],
                    operating_cf=same(ocf),
                    capex=same(capex),
                )
                entry["multiples"]["net_income_ttm"] = ni["value"]
                eps1 = ni["value"] / shares
                entry["decomposition_1y"] = _decomposition(
                    run,
                    issuer,
                    quote["ticker"],
                    as_of,
                    rows_all,
                    ni_metric,
                    splits,
                    quote["close"] / quote["ordinary_per_quote"],
                    eps1,
                )
            if layer in SEMI_LAYERS:
                q = quarters(rows, ni_metric)
                if q:
                    entry["cycle"] = cycle_per(cap, q)
            pretax = ttm(rows, "pretax_income")
            entry["non_operating"] = {
                "pretax_less_operating_income": same(pretax) - base["ebit"]
                if same(pretax) is not None
                else None,
                "nonoperating_income_tagged": same(ttm(rows, "nonoperating_income")),
                "sbc": same(ttm(rows, "sbc")),
                "net_income": ni["value"] if ni else None,
            }
            entry["base_rate"] = "データ不足"
            entry["status"] = "評価"
            prev = base["revenue"] / (1 + base["g0"])
            paths[issuer] = {"layer": layer, "fx": fx, "prev": prev, "base": base, "r_j": r_j}
    consistency = {}
    for kind in ("central", "optimistic", "stress"):
        buyers, suppliers = [], []
        for p in paths.values():
            sc = scenario_paths(p["base"], kind, r_j=p["r_j"], years=years, g_inf=g_inf)
            revenue = [x / p["fx"] for x in project_fcff(p["base"], sc, years)["revenue"]]
            now = p["base"]["revenue"] / p["fx"]
            if p["layer"] == BUYER_LAYER:
                buyers.append(
                    {
                        "revenue": [p["prev"] / p["fx"], now, *revenue],
                        "sales_to_capital": p["base"]["sales_to_capital"],
                    }
                )
            elif p["layer"] in SUPPLY_LAYERS:
                suppliers.append({"revenue": [now, *revenue]})
        consistency[kind] = layer_consistency(buyers, suppliers, years=5)
    included = {
        layer: [i for i, p in paths.items() if p["layer"] == layer]
        for layer in (BUYER_LAYER, *SUPPLY_LAYERS)
    }
    report = {
        "as_of_utc": as_of,
        "r_j": rates_report["r_j"],
        "fx_jpy_per_usd": jpy_per_usd,
        "registered": {"T": years, "g_inf": g_inf, "v_band": band, "solver_bounds": solver},
        "base_rates": "データ不足 (spec 5.3 literature distributions not obtainable; V history comparison not made)",
        "companies": companies,
        "layer_consistency": {
            "included": included,
            "by_scenario": consistency,
            "missing": [
                i for i in NOT_EVALUATED if any(i in v for v in universe["selected"].values())
            ],
        },
    }
    (run / "public" / "valuation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    (run / "public" / "valuation-summary.md").write_text(_summary_table(report))
    print(_summary_table(report))
    return 0


def _pct(x: float | None, digits: int = 0) -> str:
    return "—" if x is None else f"{x * 100:.{digits}f}%"


def _summary_table(report: dict[str, Any]) -> str:
    lines = [
        f"# 逆算DCF（基準 {report['as_of_utc']}、r_j 米国 {report['r_j']['US']:.2%}・日本 {report['r_j']['JP']:.2%}、T=10・g∞=3%）",
        "",
        "| 層 | 銘柄 | 観測EV（$bn） | 中央/観測 | 楽観/観測 | ストレス/観測 | 中央/観測（T=5） | V | 必要 g0（5年CAGR） | 必要利益率 | r* | 終端比率 | PER | EV/EBIT | 注記 |",
        "|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for c in report["companies"]:
        if c.get("status") != "評価":
            lines.append(
                f"| {c['layer']} | {c['issuer_id']} | — | — | — | — | — | 未評価 | — | — | — | — | — | — | {c['status'].removeprefix('未評価: ')} |"
            )
            continue
        v, m, mult = c["valuation"], c["market"], c.get("multiples", {})
        g = v["required_growth"]
        growth = (
            "解なし"
            if g["status"] == "no_solution"
            else "; ".join(
                f"{s:.0%}（{cg:.0%}）" for s, cg in zip(g["solutions"], g["cagr_5y"], strict=True)
            )
        )
        margin = v["required_margin"]
        margin_text = (
            "解なし"
            if margin["status"] == "no_solution"
            else "; ".join(f"{s:.0%}" for s in margin["solutions"])
        )
        irr = v["implied_irr"]
        irr_text = (
            "範囲外"
            if irr["status"] == "no_solution"
            else "; ".join(f"{s:.1%}" for s in irr["solutions"])
        )
        ratio = v["ev_ratio"] or {}
        notes = "; ".join(c["flags"])
        lines.append(
            f"| {c['layer']} | {c['issuer_id']} | {m['ev_observed_usd'] / 1e9:,.0f} | {ratio.get('central', 0):.2f} | {ratio.get('optimistic', 0):.2f} | {ratio.get('stress', 0):.2f} | {v['ev_central_T5'] / v['ev_observed']:.2f} | {v['v']} | {growth} | {margin_text} | {irr_text} | {_pct(v['terminal_share'])} | "
            f"{'対象外' if mult.get('per') is None else f'{mult["per"]:.1f}'} | {'—' if mult.get('ev_ebit') is None else f'{mult["ev_ebit"]:.1f}'} | {notes} |"
        )
    lines += [
        "",
        "## 実績倍率（直近4四半期、同じ会計基準）",
        "",
        "| 銘柄 | 益回り | PER | EV/EBIT | 営業CF/純利益 | 設備投資後CF利回り | PER（直近四半期×4） | PER（直近20四半期の平均） |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for c in report["companies"]:
        if c.get("status") != "評価" or "multiples" not in c:
            continue
        m, cy = c["multiples"], c.get("cycle")
        per_text = "対象外" if m["per"] is None else f"{m['per']:.1f}"
        x4 = (
            "—"
            if not cy
            else ("対象外" if cy["per_latest_x4"] is None else f"{cy['per_latest_x4']:.1f}")
        )
        cyc = (
            "—"
            if not cy
            else ("対象外" if cy["per_cycle"] is None else f"{cy['per_cycle']:.1f}")
            + (f"（{cy['quarters']}四半期、参考）" if cy and cy["reference_only"] else "")
        )
        lines.append(
            f"| {c['issuer_id']} | {_pct(m['earnings_yield'], 1)} | {per_text} | {'—' if m['ev_ebit'] is None else f'{m["ev_ebit"]:.1f}'} | "
            f"{'—' if m['ocf_to_net_income'] is None else f'{m["ocf_to_net_income"]:.2f}'} | {_pct(m['fcf_yield'], 1)} | {x4} | {cyc} |"
        )
    lines += [
        "",
        "## 非営業損益と株式報酬（直近4四半期、純利益に対する比率）",
        "",
        "| 銘柄 | 税引前利益−営業利益 | 非営業損益（タグ） | 株式報酬 |",
        "|---|---:|---:|---:|",
    ]
    for c in report["companies"]:
        if c.get("status") != "評価":
            continue
        n = c["non_operating"]
        ni = n["net_income"]
        cells = [
            "—" if x is None or not ni else f"{x / ni:.0%}"
            for x in (n["pretax_less_operating_income"], n["nonoperating_income_tagged"], n["sbc"])
        ]
        lines.append(f"| {c['issuer_id']} | {' | '.join(cells)} |")
    lines += [
        "",
        "## 株価の1年変化の分解（Δlog株価 = Δlog EPS + Δlog PER、恒等式）",
        "",
        "| 銘柄 | Δlog 株価 | Δlog EPS | Δlog PER |",
        "|---|---:|---:|---:|",
    ]
    for c in report["companies"]:
        d = c.get("decomposition_1y")
        if not d:
            continue
        if "dlog_price" in d:
            lines.append(
                f"| {c['issuer_id']} | {d['dlog_price']:+.2f} | {d['dlog_eps']:+.2f} | {d['dlog_per']:+.2f} |"
            )
        else:
            lines.append(f"| {c['issuer_id']} | — | — | — （{d.get('status', '')}） |")
    lines += ["", "基底率: " + report["base_rates"], ""]
    for kind, rows in report["layer_consistency"]["by_scenario"].items():
        warn = [r["year"] for r in rows if r["warning"]]
        lines.append(
            f"- 層の整合（{kind}）: 買い手の投資の変化 "
            + ", ".join(_pct(r["buyers_investment_change"]) for r in rows)
            + " / 供給側の売上の変化 "
            + ", ".join(_pct(r["suppliers_revenue_change"]) for r in rows)
            + (f" → 警告の年 {warn}" if warn else " → 警告なし")
        )
    missing = report["layer_consistency"]["missing"]
    if missing:
        lines.append(f"- 整合の計算に入っていない採用銘柄: {', '.join(missing)}")
    return "\n".join(lines) + "\n"


QUARTERLY_FLOWS = (
    "revenue",
    "operating_cf",
    "capex",
    "net_income",
    "net_income_parent",
    "cost_of_revenue",
    "d_and_a",
    "depreciation",
    "operating_income",
    "pretax_income",
    "sbc",
)
QUARTER_STOCKS = ("receivables", "inventory", "rpo", "contract_liabilities", "cash")
COMMITMENTS = (
    "purchase_obligation_total",
    "purchase_obligation_y1",
    "contractual_obligation_total",
    "contractual_obligation_y1",
)


def _plan(
    rows: list[dict[str, Any]], bal: dict[str, Any], *, first: bool = False
) -> dict[str, Any]:
    """Principal over the window from the balance at ``bal['date']`` and the current schedules."""
    on = bal["date"]
    at = {
        r["metric"]: r["value"]
        for r in rows
        if r["period_start"] == r["period_end"] == on and r["value"] is not None
    }
    schedules = {
        "debt maturity schedule": funding.current_schedule(rows, funding.DEBT_SCHEDULE, on),
        "finance lease schedule": funding.current_schedule(rows, funding.LEASE_SCHEDULE, on),
    }
    plan = funding.principal_plan(
        debt=bal["debt"],
        leases=bal["finance_leases"],
        at=at,
        debt_schedule=schedules["debt maturity schedule"]["values"],
        lease_schedule=schedules["finance lease schedule"]["values"],
        first=first,
    )
    dated = [f"{k} at {v['date']}" for k, v in schedules.items() if v["date"]]
    stale = [
        f"{k} last tagged {v['stale_date']}, not used"
        for k, v in schedules.items()
        if v["stale_date"]
    ]
    return plan | {"notes": dated + stale + plan["notes"]}


def _quarter_table(rows: list[dict[str, Any]], n: int = 8) -> list[dict[str, Any]]:
    """The last ``n`` single quarters: cash conversion, working capital days, investment and backlog."""
    flows = {
        m: {q["end"]: q for q in funding.quarterize([r for r in rows if r["metric"] == m])}
        for m in QUARTERLY_FLOWS
    }
    stocks = {
        m: {
            r["period_end"]: r["value"]
            for r in rows
            if r["metric"] == m and r["period_start"] == r["period_end"]
        }
        for m in QUARTER_STOCKS
    }
    table = []
    for end in sorted(e for e, q in flows["revenue"].items() if q["status"] == "ok")[-n:]:

        def get(metric: str, end: str = end) -> float | None:
            return flows[metric].get(end, {}).get("value")

        revenue, ocf, capex, cogs = (
            get("revenue"),
            get("operating_cf"),
            get("capex"),
            get("cost_of_revenue"),
        )
        pretax, operating = get("pretax_income"), get("operating_income")
        ni = get("net_income_parent") if get("net_income_parent") is not None else get("net_income")
        receivables, inventory = stocks["receivables"].get(end), stocks["inventory"].get(end)
        table.append(
            {
                "end": end,
                "revenue": revenue,
                "operating_cf": ocf,
                "net_income": ni,
                "ocf_to_net_income": ocf / ni if ocf is not None and ni and ni > 0 else None,
                "pretax_less_operating_income": pretax - operating
                if pretax is not None and operating is not None
                else None,
                "sbc": get("sbc"),
                "capex": capex,
                "fcf_after_capex": ocf - capex if ocf is not None and capex is not None else None,
                "d_and_a": get("d_and_a"),
                "depreciation": get("depreciation"),
                "dso_days": receivables / revenue * 91.25
                if receivables is not None and revenue
                else None,
                "dio_days": inventory / cogs * 91.25 if inventory is not None and cogs else None,
                "rpo": stocks["rpo"].get(end),
                "contract_liabilities": stocks["contract_liabilities"].get(end),
                "cash": stocks["cash"].get(end),
            }
        )
    return table


def _f_company(
    entry: dict[str, Any], rows: list[dict[str, Any]], years: int, g_inf: float
) -> dict[str, Any]:
    """One evaluated company's funding paths, sensitivities and boundaries (prereg funding_details)."""
    base, r_j = entry["base"], entry["r_j"]
    bal = base["balance"]
    ocf_t, capex_t = ttm(rows, "operating_cf"), ttm(rows, "capex")
    out: dict[str, Any] = {
        "inputs": {
            "balance_date": bal["date"],
            "operating_margin": base["margin"],
            "start_cash": bal["cash_like"] - bal["cash_parts"].get("lt_marketable", 0.0),
            "start_cash_parts": {
                k: v for k, v in bal["cash_parts"].items() if k != "lt_marketable"
            },
            "operating_cf_ttm": ocf_t and ocf_t["value"],
            "operating_cf_end": ocf_t and ocf_t["end"],
            "capex_ttm": capex_t and capex_t["value"],
            "capex_end": capex_t and capex_t["end"],
            "debt": bal["debt"],
            "finance_leases": bal["finance_leases"],
        }
    }
    missing = [
        n
        for n, x in (("operating cash flow", ocf_t), ("capital expenditure", capex_t))
        if x is None or x["end"] != base["end"]
    ]
    if missing:
        return out | {
            "status": f"未評価: no trailing {' or '.join(missing)} for {base['end']}",
            "f": "データ不足",
        }
    cash0, ocf_ttm, capex = out["inputs"]["start_cash"], ocf_t["value"], capex_t["value"]
    plan, plan_first = _plan(rows, bal), _plan(rows, bal, first=True)
    payments = [{"id": i["name"], "category": "debt_principal"} for i in plan["items"]] + [
        {"id": "capital expenditure", "category": "investment"}
    ]
    if funding.duplicate_payments([{"payments": payments}]):
        raise SystemExit(f"{entry['issuer_id']}: a payment is counted in two categories")
    out["payments"] = {k: plan[k] for k in ("items", "notes", "worst_case")}
    nopat0 = base["ebit"] * (1 - base["tax_rate"]) if base["ebit"] > 0 else base["ebit"]
    paths = {}
    for kind in ("central", "stress"):
        nopat = project_fcff(
            base, scenario_paths(base, kind, r_j=r_j, years=years, g_inf=g_inf), years
        )["nopat"]
        ocf = [(ocf_ttm + nopat[0 if q < 4 else 1] - nopat0) / 4 for q in range(funding.WINDOW)]
        paths[kind] = funding.payment_path(cash0, ocf, plan, capex / 4)
    keep = (
        "status",
        "reason",
        "balances",
        "end_shortfall",
        "max_intra_shortfall",
        "shortfall_without_unknown_timing",
    )
    out["paths"] = {
        k: {x: v[x] for x in keep if x in v}
        | {"operating_cf": [q["operating_cf"] for q in v["quarters"]]}
        for k, v in paths.items()
    }
    out["f"] = funding.f_classify(paths["central"], paths["stress"])
    central_ocf = out["paths"]["central"]["operating_cf"]
    out["sensitivities"] = {
        name: {x: path[x] for x in ("status", "max_intra_shortfall")}
        for name, path in (
            ("principal_first", funding.payment_path(cash0, central_ocf, plan_first, capex / 4)),
            ("capex_x1_25", funding.payment_path(cash0, central_ocf, plan, capex * 1.25 / 4)),
        )
    }
    for metric in ("depreciation", "d_and_a"):  # property depreciation, else D&A with intangibles
        dep = ttm(rows, metric)
        if dep and dep["end"] == base["end"]:
            out["sensitivities"]["margin_if_depreciation_x1_5"] = (
                base["margin"] - 0.5 * dep["value"] / base["revenue"]
            )
            out["sensitivities"]["depreciation_basis"] = metric
            break
    fcf = ocf_ttm - capex
    out["boundary"] = funding.funding_boundary(cash0, paths["central"]["quarters"]) | {
        "fcf_after_capex_ttm": fcf,
        "margin_at_zero_fcf": base["margin"] - fcf / (base["revenue"] * (1 - base["tax_rate"]))
        if base["ebit"] > 0
        else None,
    }
    out["commitments"] = funding.current_schedule(rows, COMMITMENTS, bal["date"])
    out["quarters"] = _quarter_table(rows)
    return out | {"status": "評価"}


def cmd_funding(args: argparse.Namespace) -> int:
    """Spec 6 / Task 3: the eight-quarter funding path, its sensitivities and boundaries, and F."""
    run = Path(args.run)
    as_of = _manifest(run)["as_of_utc"]
    registered = json.loads(PREREG.read_text())["valuation"]
    valuation = json.loads((run / "public" / "valuation.json").read_text())
    companies = []
    for entry in valuation["companies"]:
        head = {
            "issuer_id": entry["issuer_id"],
            "layer": entry["layer"],
            "flags": entry.get("flags", []),
        }
        if entry.get("status") != "評価":
            companies.append(head | {"status": entry["status"], "f": "未評価"})
            continue
        rows = select_as_of(load_rows(run, entry["issuer_id"]), as_of)
        companies.append(head | _f_company(entry, rows, registered["T"], registered["g_inf"]))
    report = {
        "as_of_utc": as_of,
        "rule": "prereg funding_details; F per spec 8 (a central intra-window shortfall supports fragility)",
        "concentration": "未収集: companyfacts carries no customer dimensions and no filing text was read (spec 6: disclosed values only, no estimates)",
        "companies": companies,
    }
    (run / "public" / "funding.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    text = _funding_table(report, valuation["fx_jpy_per_usd"])
    (run / "public" / "funding-summary.md").write_text(text)
    print(text)
    return 0


def _bn(x: float | None, fx: float) -> str:
    if x is None:
        return "—"
    return "<0.1" if 0 < x / fx / 1e9 < 0.05 else f"{x / fx / 1e9:,.1f}"


def _shortfall(path: dict[str, Any], fx: float) -> str:
    if path["status"] != "ok":
        return f"未評価（最悪の満期仮定では {_bn(path['max_intra_shortfall'], fx)}）"
    return _bn(path["max_intra_shortfall"], fx)


def _funding_details(report: dict[str, Any], jpy_per_usd: float) -> list[str]:
    """Sensitivities and the single-quarter bridge of the evaluated companies."""
    evaluated = [c for c in report["companies"] if c["status"] == "評価"]
    lines = [
        "## 感応度（中央の経路の最大途中不足、$bn）",
        "",
        "| 銘柄 | 登録どおり | 元本を各年の最初の四半期に払う | 設備投資×1.25 | 営業利益率（直近4Q） | 減価償却×1.5（耐用年数6→4年）後の営業利益率 | 償却の基礎 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for c in evaluated:
        fx = jpy_per_usd if c["issuer_id"].endswith(".T") else 1.0
        sens = c["sensitivities"]
        lines.append(
            f"| {c['issuer_id']} | {_shortfall(c['paths']['central'], fx)} | {_shortfall(sens['principal_first'], fx)} | "
            f"{_shortfall(sens['capex_x1_25'], fx)} | {_pct(c['inputs']['operating_margin'])} | "
            f"{_pct(sens.get('margin_if_depreciation_x1_5'))} | {sens.get('depreciation_basis', '—')} |"
        )
    lines += [
        "",
        "## 単独四半期の橋渡し（$bn、日数 = 四半期末残高 ÷ 四半期の売上または売上原価 × 91.25）",
        "",
        "| 銘柄 | 四半期末 | 売上 | 営業CF | 純利益 | 営業CF/純利益 | 税引前−営業利益 | 株式報酬 | 設備投資 | 減価償却 | 設備投資後CF | DSO | DIO | RPO | 契約負債 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for c in evaluated:
        fx = jpy_per_usd if c["issuer_id"].endswith(".T") else 1.0
        for q in c["quarters"]:
            dep = q["depreciation"] if q["depreciation"] is not None else q["d_and_a"]
            ratio = "—" if q["ocf_to_net_income"] is None else f"{q['ocf_to_net_income']:.2f}"
            days = ["—" if q[k] is None else f"{q[k]:.0f}" for k in ("dso_days", "dio_days")]
            money = [
                _bn(q[k], fx) if q[k] is None or q[k] >= 0 else f"-{_bn(-q[k], fx)}"
                for k in ("revenue", "operating_cf", "net_income")
            ]
            rest = [
                _bn(x, fx) if x is None or x >= 0 else f"-{_bn(-x, fx)}"
                for x in (
                    q["pretax_less_operating_income"],
                    q["sbc"],
                    q["capex"],
                    dep,
                    q["fcf_after_capex"],
                )
            ]
            lines.append(
                f"| {c['issuer_id']} | {q['end']} | {' | '.join(money)} | {ratio} | {' | '.join(rest)} | {days[0]} | {days[1]} | "
                f"{_bn(q['rpo'], fx)} | {_bn(q['contract_liabilities'], fx)} |"
            )
    return lines


def _funding_table(report: dict[str, Any], jpy_per_usd: float) -> str:
    lines = [
        f"# 資金の持続性（基準 {report['as_of_utc']}、8四半期、新規調達なし、設備投資は直近4四半期の水準で継続、$bn）",
        "",
        "| 層 | 銘柄 | 起点の現金 | 営業CF（直近4Q） | 設備投資（直近4Q） | 設備投資後CF | 2年内の元本 | 中央の最大途中不足 | ストレスの最大途中不足 | F | 失っても途中不足が出ない営業CFの割合 | 設備投資後CFがゼロになる営業利益率 | 注記 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|",
    ]
    for c in report["companies"]:
        if c["status"] != "評価":
            lines.append(
                f"| {c['layer']} | {c['issuer_id']} | — | — | — | — | — | — | — | {c['f']} | — | — | {c['status'].removeprefix('未評価: ')} |"
            )
            continue
        fx = jpy_per_usd if c["issuer_id"].endswith(".T") else 1.0
        i, p, b = c["inputs"], c["paths"], c["boundary"]

        principal = sum(item["amount"] for item in c["payments"]["items"])
        notes = "; ".join(c["payments"]["notes"] + c["flags"])
        lines.append(
            f"| {c['layer']} | {c['issuer_id']} | {_bn(i['start_cash'], fx)} | {_bn(i['operating_cf_ttm'], fx)} | {_bn(i['capex_ttm'], fx)} | "
            f"{_bn(b['fcf_after_capex_ttm'], fx)} | {_bn(principal, fx)} | {_shortfall(p['central'], fx)} | {_shortfall(p['stress'], fx)} | {c['f']} | "
            f"{_pct(b['ocf_loss_tolerated'])} | {_pct(b['margin_at_zero_fcf'])} | {notes} |"
        )
    lines += ["", f"集中: {report['concentration']}", ""]
    return "\n".join([*lines, *_funding_details(report, jpy_per_usd)]) + "\n"


def cmd_amend_prereg(args: argparse.Namespace) -> int:
    record_prereg_amendment(Path(args.run), PREREG, args.reason)
    print(_manifest(Path(args.run))["prereg_amendments"][-1])
    return 0


def cmd_record_outputs(args: argparse.Namespace) -> int:
    outputs = record_outputs(Path(args.run))
    print(len(outputs), "outputs,", sum(o["bytes"] for o in outputs), "bytes")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("new-run", help="create a run root and its manifest")
    p.add_argument("--as-of", default=json.loads(PREREG.read_text())["as_of_utc"])
    p.add_argument("--prereg", default=str(PREREG))
    p.add_argument("--root", default=str(DATA_ROOT))
    p.set_defaults(func=cmd_new_run)
    p = sub.add_parser("fetch-sec", help="companyfacts + submissions into public/raw/sec")
    p.add_argument("run")
    p.add_argument("tickers", nargs="+", choices=sorted(CIKS))
    p.set_defaults(func=cmd_fetch_sec)
    p = sub.add_parser("parse-sec", help="re-parse saved SEC raw files")
    p.add_argument("run")
    p.add_argument("tickers", nargs="+", choices=sorted(CIKS))
    p.set_defaults(func=cmd_parse_sec)
    p = sub.add_parser("fetch-jp", help="決算短信 summary pages into public/raw/jp")
    p.add_argument("run")
    p.add_argument("issuers", nargs="+", choices=sorted(JP_SOURCES))
    p.set_defaults(func=cmd_fetch_jp)
    p = sub.add_parser("parse-jp", help="re-parse saved 決算短信 without fetching")
    p.add_argument("run")
    p.add_argument("issuers", nargs="+", choices=sorted(JP_SOURCES))
    p.set_defaults(func=cmd_parse_jp)
    p = sub.add_parser(
        "fetch-prices", help="closes and share counts from yfinance into public/raw/prices"
    )
    p.add_argument("run")
    p.set_defaults(func=cmd_fetch_prices)
    p = sub.add_parser("fetch-price-history", help="400 days of closes for the price decomposition")
    p.add_argument("run")
    p.set_defaults(func=cmd_fetch_price_history)
    p = sub.add_parser("universe", help="market caps at as-of and the layer rule")
    p.add_argument("run")
    p.set_defaults(func=cmd_universe)
    p = sub.add_parser("fetch-rates", help="10-year yields and the ERP into public/raw/rates")
    p.add_argument("run")
    p.set_defaults(func=cmd_fetch_rates)
    p = sub.add_parser(
        "fetch-french", help="French 49 industries, factors and SIC map into public/raw/french"
    )
    p.add_argument("run")
    p.set_defaults(func=cmd_fetch_french)
    p = sub.add_parser(
        "fetch-adjusted-prices",
        help="dividend-adjusted daily closes from 2021-06 (own-price returns)",
    )
    p.add_argument("run")
    p.set_defaults(func=cmd_fetch_adjusted_prices)
    p = sub.add_parser(
        "history", help="run-ups and crashes of the French industries, the GSY check and S"
    )
    p.add_argument("run")
    p.set_defaults(func=cmd_history)
    p = sub.add_parser(
        "fetch-proxies",
        help="proxy closes for the systematic layer (private) and the H.10 yen rate",
    )
    p.add_argument("run")
    p.set_defaults(func=cmd_fetch_proxies)
    p = sub.add_parser(
        "portfolio", help="private holdings impact: exposure, idiosyncratic and systematic layers"
    )
    p.add_argument("run")
    p.add_argument("--holdings", default=str(HOLDINGS))
    p.add_argument("--reference", default=str(REFERENCE))
    p.set_defaults(func=cmd_portfolio)
    p = sub.add_parser("report", help="public V/F/S summary of the selected issuers (no holdings)")
    p.add_argument("run")
    p.set_defaults(func=cmd_report)
    p = sub.add_parser("valuation", help="multiples and the reverse DCF of the selected issuers")
    p.add_argument("run")
    p.set_defaults(func=cmd_valuation)
    p = sub.add_parser("funding", help="eight-quarter funding paths and F (after valuation)")
    p.add_argument("run")
    p.set_defaults(func=cmd_funding)
    p = sub.add_parser("amend-prereg", help="note a prereg.json change in the run manifest")
    p.add_argument("run")
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_amend_prereg)
    p = sub.add_parser("record-outputs", help="list derived files with sha256 in the manifest")
    p.add_argument("run")
    p.set_defaults(func=cmd_record_outputs)
    p = sub.add_parser("reconcile", help="check hand-copied document values against parsed rows")
    p.add_argument("run")
    p.add_argument("--refs", default=str(REFERENCES))
    p.set_defaults(func=cmd_reconcile)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
