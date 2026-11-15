"""Spike: download raw inputs once a day into _data/megatech-tracker/raw/.

Run: .venv/bin/python -I megatech-tracker/fetch.py [--refresh]
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

RAW = Path("/home/kazumasa/projects/_data/megatech-tracker/raw")
# Yahoo serves only today's consensus, so every snapshot is kept here; a
# surprise needs the last one taken before the results came out.
CONSENSUS = RAW.parent / "consensus.jsonl"
NY = ZoneInfo("America/New_York")
# data.sec.gov answers a plain project agent; no personal contact is sent.
SEC_UA = "megatech-tracker/0.1 (personal research)"
COMPANIES = {
    "AAPL": 320193,
    "MSFT": 789019,
    "GOOGL": 1652044,
    "AMZN": 1018724,
    "META": 1326801,
    "NVDA": 1045810,
    "TSLA": 1318605,
    "AVGO": 1730168,
    "MU": 723125,
    "AMD": 2488,
    "ORCL": 1341439,
    "INTC": 50863,
}
# GPU clouds beside the hyperscalers (hyperscalers.py); not in the tracker itself,
# so their prices go to their own file.
NEOCLOUDS = {
    "CRWV": 1769628,
    "NBIS": 1513845,
    "IREN": 1878848,
}
SEC_COMPANIES = {**COMPANIES, **NEOCLOUDS}
INDEX = "^GSPC"
# Segment figures exist only in each filing's XBRL instance on www.sec.gov, which
# refuses agents without a contact address. The address stays out of the public
# repository, in this untracked file.
CONTACT = RAW.parent / "sec_contact"
# Nebius files 20-F and 6-K, so it has no 10-Q or 10-K to read.
SEGMENT_TICKERS = ("MSFT", "AMZN", "GOOGL", "META", "ORCL", "CRWV", "IREN")
# Yahoo's quarterly statements stand in where SEC has no quarterly XBRL.
YAHOO_STATEMENTS = ("NBIS",)
FILINGS_FROM = "2020-07-01"
SEGMENT_AXES = {
    "StatementBusinessSegmentsAxis",
    "ConsolidationItemsAxis",
    "ProductOrServiceAxis",
    "ProductsOrServicesSecondaryCategorizationAxis",
    "MajorCustomersAxis",
}
# A customer's share of revenue (CoreWeave, IREN), a pure number.
CONCENTRATION = "ConcentrationRiskPercentage1"
CONCENTRATION_AXES = {
    "ConcentrationRiskByBenchmarkAxis",
    "ConcentrationRiskByTypeAxis",
    "MajorCustomersAxis",
}
SEGMENT_CONCEPT = re.compile(
    r"Revenue|OperatingIncome|Depreciation|RemainingPerformance|Expenditure|PropertyPlantAndEquipment|Cloud"
)
XBRLI = "{http://www.xbrl.org/2003/instance}"
XBRLDI = "{http://xbrl.org/2006/xbrldi}"
SPY_URL = (
    "https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/"
    "holdings-daily-us-en-spy.xlsx"
)


def _settled(t: datetime) -> datetime:
    """The last 16:30 New York time at or before `t`: that day's close is final."""
    t = t.astimezone(NY)
    cut = t.replace(hour=16, minute=30, second=0, microsecond=0)
    return cut if t >= cut else cut - timedelta(days=1)


def _fresh(path: Path, refresh: bool) -> bool:
    # A file stays fresh until the next New York close settles. A Japan calendar
    # day would keep a bar fetched mid-session, or a fetch made just before an
    # after-the-close release, until midnight in Tokyo.
    if refresh or not path.exists():
        return False
    fetched = datetime.fromtimestamp(path.stat().st_mtime, NY)
    return _settled(fetched) == _settled(datetime.now(NY))


def _get(url: str, agent: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": agent})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch_sec(refresh: bool) -> None:
    for ticker, cik in SEC_COMPANIES.items():
        for kind, url in (
            ("companyfacts", f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"),
            ("submissions", f"https://data.sec.gov/submissions/CIK{cik:010d}.json"),
        ):
            path = RAW / f"{kind}_{ticker}.json"
            if _fresh(path, refresh):
                continue
            path.write_bytes(_get(url, SEC_UA))
            time.sleep(0.25)
        print("sec", ticker)


def _frame_json(df: pd.DataFrame | None) -> list[dict]:
    if df is None or len(df) == 0:
        return []
    out = df.reset_index()
    out.columns = [str(c) for c in out.columns]
    return json.loads(out.to_json(orient="records", date_format="iso"))


def _recorded() -> set[tuple[str, str]]:
    if not CONSENSUS.exists():
        return set()
    rows = (json.loads(line) for line in CONSENSUS.read_text().splitlines() if line.strip())
    return {(r["ticker"], r["taken"]) for r in rows}


def _current_quarter(rows: list[dict]) -> dict | None:
    return next((r for r in rows if r.get("period") == "0q"), None)


def record_consensus(ticker: str, path: Path) -> None:
    """Append the current-quarter consensus in `path`, stamped with when it was fetched."""
    y = json.loads(path.read_text())
    # Files written before the stamp existed fall back to their time on disk,
    # which a copy without -p would reset.
    taken = y.get("fetched") or datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(
        timespec="seconds"
    )
    if (ticker, taken) in _recorded():
        return
    history = y.get("earnings_history") or []
    row = {
        "ticker": ticker,
        "taken": taken,
        "last_reported": history[-1]["quarter"][:10] if history else None,
        "eps": _current_quarter(y.get("earnings_estimate", [])),
        "revenue": _current_quarter(y.get("revenue_estimate", [])),
    }
    with CONSENSUS.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _next_earnings(info: dict) -> dict | None:
    # t.calendar gives the date in the machine's zone (a day late in Japan);
    # the timestamp converted to New York is the date the company announces.
    stamp = info.get("earningsTimestampStart") or info.get("earningsTimestamp")
    if not stamp:
        return None
    return {
        "date": datetime.fromtimestamp(stamp, NY).date().isoformat(),
        "estimate": bool(info.get("isEarningsDateEstimate")),
    }


def _statements(t: yf.Ticker, kept: dict) -> dict:
    """Yahoo's quarterly statements, {statement: {end: {line: value}}}.

    Yahoo serves the last five or so quarters; the ones fetched before stay.
    """
    out = {}
    for name in ("quarterly_income_stmt", "quarterly_cashflow", "quarterly_balance_sheet"):
        quarters = dict(kept.get(name, {}))
        for col, values in getattr(t, name).items():
            got = {k: float(v) for k, v in values.items() if pd.notna(v)}
            if got:
                quarters[str(col.date())] = got
        out[name] = dict(sorted(quarters.items()))
    return out


def fetch_yahoo(refresh: bool) -> None:
    # The neoclouds' closes go to their own file so the tracker's stays as it is.
    for path, tickers in (
        (RAW / "prices.csv", COMPANIES),
        (RAW / "prices_neocloud.csv", NEOCLOUDS),
    ):
        # A company added today still needs its column.
        if not _fresh(path, refresh) or not set(tickers) <= set(pd.read_csv(path, nrows=0).columns):
            df = yf.download(
                [*tickers, INDEX], period="11y", interval="1d", auto_adjust=False, progress=False
            )
            df["Close"].to_csv(path)
            print(path.name, df.shape)
    for ticker in SEC_COMPANIES:
        path = RAW / f"yahoo_{ticker}.json"
        if _fresh(path, refresh):
            continue
        if path.exists():
            record_consensus(ticker, path)
        t = yf.Ticker(ticker)
        info = t.info
        payload = {
            "info": {
                k: info.get(k)
                for k in (
                    "longName",
                    "marketCap",
                    "forwardPE",
                    "trailingPE",
                    "forwardEps",
                    "trailingEps",
                    "sharesOutstanding",
                    "currency",
                )
            },
            "next_earnings": _next_earnings(info),
            "earnings_history": _frame_json(t.earnings_history),
            "earnings_estimate": _frame_json(t.earnings_estimate),
            "revenue_estimate": _frame_json(t.revenue_estimate),
            "splits": [[str(d.date()), float(r)] for d, r in t.splits.items()],
            **(
                {
                    "statements": _statements(
                        t, load_json(path).get("statements", {}) if path.exists() else {}
                    )
                }
                if ticker in YAHOO_STATEMENTS
                else {}
            ),
            "fetched": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
        record_consensus(ticker, path)
        print("yahoo", ticker)


def _get_patiently(url: str, agent: str) -> bytes:
    """_get, retried with growing pauses: www.sec.gov answers 503 to bursts."""
    for wait in (2, 5, 15, 30):
        try:
            return _get(url, agent)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
            time.sleep(wait)
    return _get(url, agent)


def _filings(ticker: str, cik: int) -> list[dict]:
    """Every 10-Q and 10-K filed since FILINGS_FROM, oldest first.

    SEC's recent list holds about 1,000 filings, which for Alphabet reaches back
    only to 2023; the older pages are fetched (and kept) when it falls short.
    """
    filings = load_json(RAW / f"submissions_{ticker}.json")["filings"]
    pages = [filings["recent"]]
    if min(pages[0]["filingDate"]) > FILINGS_FROM:
        for page in filings.get("files", []):
            if page["filingTo"] < FILINGS_FROM:
                continue
            path = RAW / f"submissions_{ticker}_{page['name'].split('-')[-1]}"
            if not path.exists():
                path.write_bytes(_get(f"https://data.sec.gov/submissions/{page['name']}", SEC_UA))
                time.sleep(0.25)
            pages.append(load_json(path))
    out = {}
    for p in pages:
        for form, acc, filed, period in zip(
            p["form"], p["accessionNumber"], p["filingDate"], p["reportDate"], strict=True
        ):
            if form in ("10-Q", "10-K") and filed >= FILINGS_FROM:
                out[acc] = {"form": form, "filed": filed, "period": period}
    return [{"accession": a, **v} for a, v in sorted(out.items(), key=lambda kv: kv[1]["filed"])]


def load_json(path: Path):
    return json.loads(path.read_text())


def _instance_name(index: dict) -> str | None:
    names = [x["name"] for x in index["directory"]["item"]]
    inline = [n for n in names if n.endswith("_htm.xml")]
    if inline:
        return inline[0]
    linkbases = ("_cal.xml", "_def.xml", "_lab.xml", "_pre.xml")
    plain = [n for n in names if n.endswith(".xml") and not n.endswith(linkbases)]
    return next((n for n in plain if n != "FilingSummary.xml"), None)


def segment_facts(xml: bytes) -> list[list]:
    """USD facts split by segment, product or customer, plus backlog and depreciation.

    Also each customer's share of revenue (a pure number), for the neoclouds.

    Each is [concept, {axis: member}, start, end, value]; start is None for an
    instant. companyfacts carries only facts without dimensions, so segment
    revenue lives only here.
    """
    root = ET.fromstring(xml)
    contexts = {}
    for c in root.iter(XBRLI + "context"):
        dims = {
            m.get("dimension").split(":")[-1]: m.text.split(":")[-1]
            for m in c.iter(XBRLDI + "explicitMember")
        }
        # A typed member (IREN's backlog by when it turns into revenue) is a slice
        # too; without it the slice would pass for the total.
        dims.update(
            {m.get("dimension").split(":")[-1]: "typed" for m in c.iter(XBRLDI + "typedMember")}
        )
        period = c.find(XBRLI + "period")
        start = period.find(XBRLI + "startDate")
        end = period.find(XBRLI + "endDate")
        if end is None:
            end = period.find(XBRLI + "instant")
        contexts[c.get("id")] = (dims, None if start is None else start.text, end.text)
    # Unit ids are the filer's own (Microsoft writes U_USD); the measure is not.
    usd = {
        u.get("id")
        for u in root.iter(XBRLI + "unit")
        if [m.text for m in u.iter(XBRLI + "measure")] == ["iso4217:USD"]
    }
    pure = {
        u.get("id")
        for u in root.iter(XBRLI + "unit")
        # CoreWeave writes the xbrli namespace as the default, so "pure" alone
        if [(m.text or "").split(":")[-1] for m in u.iter(XBRLI + "measure")] == ["pure"]
    }
    # One fact can appear twice, in thousands and rounded to billions in the text
    # (Amazon's depreciation, 41.86 and 41.9); the more precise one is kept.
    out: dict = {}

    def keep(concept, dims, start, end, fact):
        try:
            value = float(fact.text)
        except ValueError:
            return
        dec = fact.get("decimals")
        precision = 99 if dec in (None, "INF") else int(dec)
        key = (concept, tuple(sorted(dims.items())), start, end)
        if key not in out or precision > out[key][0]:
            out[key] = (precision, value)

    for fact in root:
        ctx = fact.get("contextRef")
        if ctx is None or fact.text is None:
            continue
        concept = fact.tag.split("}")[-1]
        if concept == CONCENTRATION and fact.get("unitRef") in pure:
            dims, start, end = contexts[ctx]
            if dims and set(dims) <= CONCENTRATION_AXES:
                keep(concept, dims, start, end, fact)
            continue
        if fact.get("unitRef") not in usd:
            continue
        if not SEGMENT_CONCEPT.search(concept):
            continue
        dims, start, end = contexts[ctx]
        if dims and not set(dims) <= SEGMENT_AXES:
            continue
        # Without dimensions, keep only what companyfacts lacks: the backlog (Amazon
        # stopped reaching it after 2020), and depreciation, which Microsoft tags
        # only under its own name.
        if not dims and not (
            "RemainingPerformanceObligation" in concept
            or (
                "Depreciation" in concept
                and not concept.startswith(("Accumulated", "PropertyPlant"))
            )
        ):
            continue
        keep(concept, dims, start, end, fact)
    return [[c, dict(d), s, e, v] for (c, d, s, e), (_, v) in sorted(out.items(), key=str)]


def fetch_segments() -> None:
    """Segment facts of each filing, parsed once and kept (filings never change)."""
    contact = CONTACT.read_text().strip() if CONTACT.exists() else ""
    if not contact:
        print(f"segments skipped: write a contact e-mail for SEC to {CONTACT}")
        return
    agent = f"megatech-tracker {contact}"
    for ticker in SEGMENT_TICKERS:
        cik = SEC_COMPANIES[ticker]
        path = RAW / f"segments_{ticker}.json"
        kept = load_json(path) if path.exists() else {}
        new = 0
        for f in _filings(ticker, cik):
            if f["accession"] in kept:
                continue
            base = (
                f"https://www.sec.gov/Archives/edgar/data/{cik}/{f['accession'].replace('-', '')}"
            )
            index = json.loads(_get_patiently(f"{base}/index.json", agent))
            time.sleep(0.25)
            name = _instance_name(index)
            facts = segment_facts(_get_patiently(f"{base}/{name}", agent)) if name else []
            time.sleep(0.25)
            kept[f["accession"]] = {**f, "instance": name, "facts": facts}
            new += 1
            # written after each filing so an interrupted run resumes where it stopped
            path.write_text(json.dumps(kept, ensure_ascii=False, separators=(",", ":")))
        print("segments", ticker, f"{new} new of {len(kept)}")


def fetch_spy(refresh: bool) -> None:
    path = RAW / "spy_holdings.xlsx"
    if not _fresh(path, refresh):
        path.write_bytes(_get(SPY_URL, "Mozilla/5.0"))
        print("spy holdings")


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    RAW.mkdir(parents=True, exist_ok=True)
    fetch_sec(refresh)
    fetch_segments()
    fetch_yahoo(refresh)
    fetch_spy(refresh)
