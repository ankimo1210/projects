"""Spike: turn the raw inputs into one self-contained HTML tracker.

Run after fetch.py:  .venv/bin/python -I megatech-tracker/build.py
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime, time, timedelta
from itertools import pairwise
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path("/home/kazumasa/projects")
RAW = ROOT / "_data/megatech-tracker/raw"
CONSENSUS = ROOT / "_data/megatech-tracker/consensus.jsonl"
OUT = ROOT / "_data/megatech-tracker/tracker.html"
TEMPLATE = ROOT / "megatech-tracker/template.html"
TOKENS = ROOT / "docs/templates/claude-report/tokens.css"
NY = ZoneInfo("America/New_York")
JST = ZoneInfo("Asia/Tokyo")

# The order is fixed: each company keeps its slot (and so its color) in its group.
GROUPS = [("mag7", "Mag7"), ("ai", "AI 半導体と Oracle")]
COMPANIES = [
    ("AAPL", "Apple", "mag7"),
    ("MSFT", "Microsoft", "mag7"),
    ("GOOGL", "Alphabet", "mag7"),
    ("AMZN", "Amazon", "mag7"),
    ("META", "Meta", "mag7"),
    ("NVDA", "Nvidia", "mag7"),
    ("TSLA", "Tesla", "mag7"),
    ("AVGO", "Broadcom", "ai"),
    ("MU", "Micron", "ai"),
    ("AMD", "AMD", "ai"),
    ("ORCL", "Oracle", "ai"),
    ("INTC", "Intel", "ai"),
]
# Who pays for AI data centers, and who sells them the chips.
PAYERS = ("MSFT", "GOOGL", "AMZN", "META", "ORCL")
SELLERS = ("NVDA", "AVGO", "AMD", "MU")
SPY_CLASSES = {"GOOGL": ("GOOGL", "GOOG")}
PERIODIC = {"10-Q", "10-K", "10-Q/A", "10-K/A"}

# One metric may span several tags because filers rename them; per period the
# first tag that reports it wins.
FLOWS = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ],
    "operating_income": ["OperatingIncomeLoss"],
    # Broadcom tags only ProfitLoss (it has no material minority interest).
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "ocf": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "buybacks": ["PaymentsForRepurchaseOfCommonStock"],
    "dividends": [
        "PaymentsOfDividends",
        "PaymentsOfDividendsCommonStock",
        "PaymentsOfOrdinaryDividends",
    ],
}
INSTANTS = {
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "securities": [
        "MarketableSecuritiesCurrent",
        "ShortTermInvestments",
        "DebtSecuritiesCurrent",
        "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
    ],
    "securities_nc": ["MarketableSecuritiesNoncurrent"],
    "debt_total": ["LongTermDebt"],
    # Oracle calls its bonds notes.
    "debt_noncurrent": ["LongTermDebtNoncurrent", "LongTermNotesAndLoans", "LongTermNotesPayable"],
    "debt_noncurrent_leases": ["LongTermDebtAndCapitalLeaseObligations"],
    "debt_current": ["LongTermDebtCurrent", "NotesPayableCurrent"],
    "short_debt": ["CommercialPaper", "ShortTermBorrowings"],
    "debt_current_any": ["DebtCurrent"],
    "debt_and_leases": ["DebtAndCapitalLeaseObligations"],
    "lease": ["FinanceLeaseLiability"],
    "lease_current": ["FinanceLeaseLiabilityCurrent"],
    "lease_noncurrent": ["FinanceLeaseLiabilityNoncurrent"],
    "equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
}
# Return of capital is a cash outflow a filer stops tagging when it stops paying.
ZERO_WHEN_UNTAGGED = {"buybacks", "dividends"}


def d(s: str) -> date:
    return date.fromisoformat(s)


def load(name: str):
    return json.loads((RAW / name).read_text())


# ---------------------------------------------------------------- SEC facts


def merged(cf: dict, concepts: list[str], unit: str, *, duration: bool) -> dict:
    """(start, end) -> latest-filed fact, with its filing history and first filing date.

    The first tag that reports a period gives its value; the first filing date
    spans every tag, since filers re-tag old periods (Alphabet moved its
    revenue to Revenues in 2025, which made 2023 look first filed in 2026).
    """
    out: dict = {}
    first: dict = {}
    for concept in concepts:
        node = cf["facts"].get("us-gaap", {}).get(concept)
        best: dict = {}
        for it in (node or {}).get("units", {}).get(unit, []):
            if it.get("form") not in PERIODIC or ("start" in it) != duration:
                continue
            key = (it.get("start"), it["end"])
            first[key] = min(first.get(key, it["filed"]), it["filed"])
            cur = best.get(key)
            if cur is None:
                best[key] = {**it, "concept": concept, "history": [(it["filed"], it["val"])]}
                continue
            cur["history"].append((it["filed"], it["val"]))
            if it["filed"] > cur["filed"]:
                best[key] = {**it, "concept": concept, "history": cur["history"]}
        for key, it in best.items():
            out.setdefault(key, it)
    for key, it in out.items():
        it["first_filed"] = first[key]
        it["history"].sort()
    return out


def quarterly_flows(facts: dict) -> dict:
    """end -> (start, value, filed, first_filed); Q4 and cash-flow quarters by differencing YTD."""
    direct, chains, suspect = {}, {}, set()
    annual = {e: it["val"] for (s, e), it in facts.items() if 350 <= (d(e) - d(s)).days + 1 <= 380}
    for (s, e), it in facts.items():
        n = (d(e) - d(s)).days + 1
        if 80 <= n <= 100:
            direct[e] = (s, it["val"], it["filed"], it["first_filed"])
            if annual.get(e) == it["val"]:
                suspect.add(e)
        chains.setdefault(s, []).append((e, n, it))
    derived = {}
    for rows in chains.values():
        rows.sort(key=lambda r: r[0])
        for (e0, n0, a), (e1, n1, b) in pairwise(rows):
            if 80 <= n1 - n0 <= 100:
                start = (d(e0) + timedelta(days=1)).isoformat()
                # A later filing can restate the shorter period before any filing
                # re-presents the longer one (Alphabet's 2025 buybacks); take the
                # shorter one as it stood when the longer one was filed.
                short = a["val"]
                if a["filed"] > b["filed"]:
                    short = next((v for f, v in reversed(a["history"]) if f <= b["filed"]), short)
                derived[e1] = (
                    start,
                    b["val"] - short,
                    max(a["filed"], b["filed"]),
                    max(a["first_filed"], b["first_filed"]),
                )
    out = {**derived, **direct}
    # Oracle's FY2022 10-K gave its fourth quarter the full-year figure. A quarter
    # equal to a twelve-month figure yields to differencing where that exists;
    # Amazon's trailing-twelve-month columns can match a quarter honestly.
    for e in suspect & derived.keys():
        out[e] = derived[e]
    return out


def split_factor(splits: list, filed: str) -> float:
    """Multiply a share count reported on `filed` by this to reach today's share basis."""
    f = 1.0
    for day, ratio in splits:
        if day > filed:
            f *= ratio
    return f


def diluted_shares(cf: dict, splits: list) -> dict:
    """end -> diluted weighted shares on today's basis (quarter facts, else annual)."""
    m = merged(cf, ["WeightedAverageNumberOfDilutedSharesOutstanding"], "shares", duration=True)
    q, a, days = {}, {}, {}
    for (s, e), it in m.items():
        n = (d(e) - d(s)).days + 1
        value = it["val"] * split_factor(splits, it["filed"])
        if 80 <= n <= 100:
            q[e], days[e] = value, n
        elif 350 <= n <= 380:
            a[(s, e)] = value
    eps = merged(cf, ["EarningsPerShareDiluted"], "USD/shares", duration=True)
    ni = merged(cf, ["NetIncomeLoss"], "USD", duration=True)
    implied = {}
    for key, it in eps.items():
        n = (d(key[1]) - d(key[0])).days + 1
        if 80 <= n <= 100 and key in ni and it["val"]:
            # Alphabet tags diluted shares only per share class before 2023.
            implied[key[1]] = ni[key]["val"] / (it["val"] / split_factor(splits, it["filed"]))
            days.setdefault(key[1], n)
    quarters = {**implied, **q}
    profit = quarterly_flows(merged(cf, FLOWS["net_income"], "USD", duration=True))
    # A year's average count weights its quarters by days, so the fourth quarter's
    # is what the year leaves after the first three. The year's own average runs
    # about 1% above it at Apple, which buys back steadily. A loss quarter reports
    # its basic count as diluted, off the year's basis (Broadcom, fiscal 2024), so
    # such years keep the year's average. Checked against the 10-Ks' own Q4 EPS
    # (to 2020) and Yahoo's GAAP actuals: 74 of 78 within $0.015, against 69.
    q4 = {}
    for (s, e), year in a.items():
        inside = [x for x in quarters if s < x < e]
        if e in q or len(inside) != 3:
            continue
        if any(profit[x][1] < 0 for x in [*inside, e] if x in profit):
            continue
        total = (d(e) - d(s)).days + 1
        rest = total - sum(days[x] for x in inside)
        q4[e] = (year * total - sum(quarters[x] * days[x] for x in inside)) / rest
    return {**implied, **{e: v for (_, e), v in a.items()}, **q4, **q}


def gaap_eps(cf: dict, splits: list) -> dict:
    """end -> reported diluted EPS of a three-month period, on today's share basis."""
    m = merged(cf, ["EarningsPerShareDiluted"], "USD/shares", duration=True)
    return {
        e: it["val"] / split_factor(splits, it["filed"])
        for (s, e), it in m.items()
        if 80 <= (d(e) - d(s)).days + 1 <= 100
    }


def instants(cf: dict, concepts: list[str]) -> dict:
    m = merged(cf, concepts, "USD", duration=False)
    return {e: it["val"] for (_, e), it in m.items()}


def quarter_label(start: str, end: str) -> str:
    # Fiscal quarters start and end a few days off the month (Nvidia's first
    # quarter runs 26 Jan - 26 Apr); the middle of each end month names it.
    a = d(start) + timedelta(days=15)
    b = d(end) - timedelta(days=15)
    if a.year == b.year:
        return f"{b.year}年{a.month}–{b.month}月"
    return f"{a.year}年{a.month}月–{b.year}年{b.month}月"


def cal_quarter(start: str, end: str) -> str:
    mid = d(start) + (d(end) - d(start)) / 2
    return f"{mid.year}Q{(mid.month - 1) // 3 + 1}"


def company_quarters(cf: dict, splits: list) -> list[dict]:
    flows = {k: quarterly_flows(merged(cf, v, "USD", duration=True)) for k, v in FLOWS.items()}
    inst = {k: instants(cf, v) for k, v in INSTANTS.items()}
    shares = diluted_shares(cf, splits)
    eps = gaap_eps(cf, splits)
    rows = []
    for e in sorted(flows["revenue"]):
        s, rev, _, first = flows["revenue"][e]
        row = {"end": e, "start": s, "available": first, "revenue": rev}
        for k in FLOWS:
            if k == "revenue":
                continue
            v = flows[k].get(e)
            row[k] = v[1] if v else None
            # The quarter is out when its revenue and profit are: buybacks and
            # dividends are often first tagged a year later, as comparatives.
            if v and k == "net_income":
                row["available"] = max(row["available"], v[3])
        cash = inst["cash"].get(e)
        row["liquid"] = (
            None
            if cash is None
            else cash + inst["securities"].get(e, 0) + inst["securities_nc"].get(e, 0)
        )
        row["debt"], row["debt_with_leases"] = debt_at(inst, e)
        row["equity"] = inst["equity"].get(e)
        row["shares"] = shares.get(e)
        row["label"] = quarter_label(s, e)
        row["cal_q"] = cal_quarter(s, e)
        rows.append(row)
    # forward-fill share counts where a quarter lacks one (Q4 before annual facts, etc.)
    last = None
    for row in rows:
        if row["shares"] is None:
            row["shares"] = last
        last = row["shares"]
    for k in ZERO_WHEN_UNTAGGED:
        tagged = [i for i, r in enumerate(rows) if r[k] is not None]
        # A gap of a year or more means the payments stopped, as does a tag that
        # disappears after reporting zero (Oracle's buybacks); any other short
        # gap is more likely a renamed tag, so it stays unknown.
        if not tagged or len(rows) - 1 - tagged[-1] >= 4 or rows[tagged[-1]][k] == 0:
            for r in rows[(tagged[-1] + 1 if tagged else 0) :]:
                r[k] = 0.0
    for i, row in enumerate(rows):
        # Q4 has no three-month EPS fact; net income over diluted shares stands in.
        row["eps"] = eps.get(row["end"]) or _ratio(row["net_income"], row["shares"])
        prior = _year_ago(rows, i)
        row["rev_yoy"] = (
            row["revenue"] / prior["revenue"] - 1 if prior and prior["revenue"] else None
        )
        row["op_margin"] = _ratio(row["operating_income"], row["revenue"])
        row["fcf"] = _sub(row["ocf"], row["capex"])
    return rows


def debt_at(inst: dict, e: str) -> tuple[float | None, bool]:
    """Borrowings without leases at quarter end `e`, and whether leases stayed in."""

    def g(k):
        return inst[k].get(e)

    short = g("short_debt") or 0
    # AMD tags its current notes as short-term borrowings as well.
    if g("debt_current") is not None and abs(short - g("debt_current")) < 1e6:
        short = 0
    # Micron reports debt together with finance leases, and the leases apart.
    if g("debt_and_leases") is not None and g("lease") is not None:
        return g("debt_and_leases") - g("lease") + short, False
    total, noncurrent, current = g("debt_total"), g("debt_noncurrent"), g("debt_current")
    with_leases = False
    if noncurrent is None and g("debt_noncurrent_leases") is not None:
        # Alphabet folded finance leases into long-term debt until 2024.
        lease_nc = g("lease_noncurrent")
        if lease_nc is None and g("lease") is not None and g("lease_current") is not None:
            lease_nc = g("lease") - g("lease_current")
        noncurrent = g("debt_noncurrent_leases") - (lease_nc or 0)
        with_leases = lease_nc is None
    # A zero total beside non-zero parts is a tagging slip (Oracle, May 2022).
    if not total and (noncurrent is not None or current is not None):
        total = (noncurrent or 0) + (current or 0)
    else:
        with_leases = False
    if total is None:
        return None, False
    # Tesla tags LongTermDebt as the non-current part only and puts the rest in
    # DebtCurrent; filers that split their debt never need this.
    if (
        g("debt_current_any") is not None
        and g("debt_noncurrent") is None
        and current is None
        and not short
    ):
        total += g("debt_current_any")
    return total + short, with_leases


def _year_ago(rows: list[dict], i: int) -> dict | None:
    target = d(rows[i]["end"]) - timedelta(days=364)
    for r in rows[:i]:
        if abs((d(r["end"]) - target).days) <= 10:
            return r
    return None


def _ratio(a, b):
    return None if a is None or not b else a / b


def _sub(a, b):
    return None if a is None or b is None else a - b


def _add(a, b):
    return None if a is None or b is None else a + b


def data_notes(rows: list[dict]) -> list[str]:
    """Gaps and definition changes a reader of the quarter table should know about."""
    notes = []
    gaps = [r["label"] for r in rows if r["capex"] is None]
    if gaps:
        notes.append(
            f"{'、'.join(gaps)}の設備投資は SEC の XBRL 集計（標準タグ）に値が無いため空欄"
            "（FCF も空欄）。"
        )
    leased = [r["label"] for r in rows if r["debt_with_leases"]]
    if leased:
        notes.append(
            f"{leased[0]}〜{leased[-1]}の借入は、当時の貸借対照表の表示どおりファイナンスリースを含む。"
        )
    return notes


def ttm(rows: list[dict], key: str, i: int | None = None) -> float | None:
    i = len(rows) - 1 if i is None else i
    if i < 3:
        return None
    window = rows[i - 3 : i + 1]
    if (d(window[-1]["end"]) - d(window[0]["start"])).days > 380:
        return None
    vals = [r[key] for r in window]
    return None if any(v is None for v in vals) else sum(vals)


# ------------------------------------------------------------ market data


def earnings_events(sub: dict) -> list[tuple[str, str]]:
    """(New York date, acceptance time) of after-the-close results releases.

    8-K item 2.02 accepted 15:55–20:30 New York. Tesla also furnishes its
    delivery numbers under 2.02, before the open; the time window keeps those out.
    """
    rec = sub["filings"]["recent"]
    out: dict = {}
    for form, items, stamp in zip(
        rec["form"], rec["items"], rec["acceptanceDateTime"], strict=True
    ):
        if form != "8-K" or "2.02" not in items.split(","):
            continue
        t = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(NY)
        if time(15, 55) <= t.time() <= time(20, 30):
            day = t.date().isoformat()
            out[day] = min(out.get(day, t), t)
    return [(day, t.isoformat()) for day, t in sorted(out.items())]


def reaction(px: pd.Series, spx: pd.Series, day: str) -> dict | None:
    """The next session's move after a release; None until that session has closed."""
    before = px.index[px.index <= pd.Timestamp(day)]
    after = px.index[px.index > pd.Timestamp(day)]
    if len(before) == 0 or len(after) == 0:
        return None
    a, b = before[-1], after[0]
    r = float(px[b] / px[a] - 1)
    idx = spx.reindex([a, b])
    m = None if idx.isna().any() else float(idx.iloc[1] / idx.iloc[0] - 1)
    return {"session": b.date().isoformat(), "move": r, "vs_index": None if m is None else r - m}


def spy_weights() -> tuple[dict, str]:
    x = pd.read_excel(RAW / "spy_holdings.xlsx", header=None, engine="openpyxl")
    asof = str(x.iloc[2, 1]).replace("As of ", "")
    head = x.index[x[0] == "Name"][0]
    body = x.iloc[head + 1 :, [1, 4]]
    body = body.assign(w=pd.to_numeric(body[4], errors="coerce")).dropna(subset=[1, "w"])
    w = {str(t): float(v) / 100 for t, v in zip(body[1], body["w"], strict=True)}
    out = {}
    for ticker, _, _ in COMPANIES:
        out[ticker] = sum(w.get(c, 0.0) for c in SPY_CLASSES.get(ticker, (ticker,)))
    return out, datetime.strptime(asof, "%d-%b-%Y").date().isoformat()


def consensus_history() -> dict[str, list[dict]]:
    out: dict = {}
    if CONSENSUS.exists():
        for line in CONSENSUS.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out.setdefault(r["ticker"], []).append(r)
    for snaps in out.values():
        # by the instant, not the string: a fetch from another time zone writes
        # another offset, and "…T01:00+00:00" sorts before "…T08:00+09:00"
        snaps.sort(key=lambda r: datetime.fromisoformat(r["taken"]))
    return out


def estimate_quarter(rows: list[dict], events: list[dict], rev: dict | None, on: date):
    """The quarter a Yahoo quarterly revenue estimate is for, with its release once out.

    An estimate names its quarter only through the year-ago revenue, which
    pins down the quarter one year earlier in the SEC rows. Only quarters that
    can be a year-ago quarter are searched: older ones can repeat the figure.
    """
    ago = (rev or {}).get("yearAgoRevenue")
    base = next(
        (
            r
            for r in rows
            if ago
            and r["revenue"]
            and 200 <= (on - d(r["end"])).days <= 460
            and abs(r["revenue"] / ago - 1) < 0.002
        ),
        None,
    )
    if base is None:
        return None
    start = (d(base["start"]) + timedelta(days=364)).isoformat()
    end = d(base["end"]) + timedelta(days=364)
    row = next((r for r in rows if abs((d(r["end"]) - end).days) <= 10), None)
    return {
        "base_end": base["end"],
        "row": row,
        "label": row["label"] if row else quarter_label(start, end.isoformat()),
        "end": row["end"] if row else end.isoformat(),
        "cal_q": row["cal_q"] if row else cal_quarter(start, end.isoformat()),
        "release": next((e for e in events if 0 < (d(e["date"]) - end).days <= 75), None),
    }


def revenue_checks(rows: list[dict], events: list[dict], snaps: list[dict]) -> list[dict]:
    """Each quarter's revenue against the last consensus saved before its release."""
    by_end: dict = {}
    for snap in snaps:
        rev = snap.get("revenue") or {}
        taken = datetime.fromisoformat(snap["taken"])
        q = estimate_quarter(rows, events, rev, taken.date())
        if q is None or rev.get("avg") is None:
            continue
        ev, row = q["release"], q["row"]
        # The wire release goes out minutes before its 8-K is accepted, and no
        # after-the-close release comes before the close itself.
        if ev and taken >= min(
            datetime.fromisoformat(ev["accepted"]), datetime.combine(d(ev["date"]), time(16, 0), NY)
        ):
            continue
        eps = snap.get("eps") or {}
        by_end[q["base_end"]] = {
            "label": q["label"],
            "end": q["end"],
            "cal_q": q["cal_q"],
            "release": ev["date"] if ev else None,
            "taken": taken.astimezone(JST).date().isoformat(),
            "estimate": rev["avg"],
            "analysts": rev.get("numberOfAnalysts"),
            "eps_estimate": eps.get("avg"),
            "revenue": row["revenue"] if row else None,
            "surprise": row["revenue"] / rev["avg"] - 1 if row else None,
            "eps": row["eps"] if row else None,
        }
    return [by_end[k] for k in sorted(by_end)]


def ntm_eps(estimates: list[dict], fy_end: date, today: date) -> float | None:
    """Next-twelve-months EPS: the two fiscal-year consensus figures weighted by time left."""
    by = {r["period"]: r for r in estimates}
    if "0y" not in by or "+1y" not in by:
        return None
    left = max(0, min(365, (fy_end - today).days)) / 365
    return left * by["0y"]["avg"] + (1 - left) * by["+1y"]["avg"]


def week_ends(x):
    """Last trading day of each week, dated by that day (resample would date it Friday)."""
    return x.groupby(x.index.to_period("W-FRI")).tail(1)


def _r(v, n=4):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return None
    return round(float(v), n)


# ------------------------------------------------------------------- build


def closes(path: Path) -> pd.DataFrame:
    """Daily closes, without a last row that is incomplete or from a session still open.

    yfinance can return the last day before every column is in, and during the
    session it returns that session's bar so far; neither is a close.
    """
    prices = pd.read_csv(path, index_col=0, parse_dates=True).sort_index().dropna(how="all")
    full = prices.notna().all(axis=1)
    prices = prices.loc[: full[full].index[-1]]
    fetched = datetime.fromtimestamp(path.stat().st_mtime, NY)
    if prices.index[-1].date() == fetched.date() and fetched.time() < time(16, 30):
        prices = prices.iloc[:-1]
    return prices


def build() -> dict:
    prices = closes(RAW / "prices.csv")
    spx = prices["^GSPC"].dropna()
    asof = prices.index[-1]
    today = datetime.now(JST).date()
    weights, spy_asof = spy_weights()
    history = consensus_history()

    companies = []
    for ticker, name, group in COMPANIES:
        cf = load(f"companyfacts_{ticker}.json")
        sub = load(f"submissions_{ticker}.json")
        y = load(f"yahoo_{ticker}.json")
        splits = y.get("splits", [])
        rows = company_quarters(cf, splits)
        px = prices[ticker].dropna()

        # Results come at least five days after a quarter closes (Oracle, the
        # quickest here, takes about nine). Tesla's delivery figures, filed under
        # the same item a day or two after the close, sometimes after hours, do not.
        ends = [*(r["end"] for r in rows), (d(rows[-1]["end"]) + timedelta(days=91)).isoformat()]
        events = []
        for day, accepted in earnings_events(sub):
            closed = [e for e in ends if 5 <= (d(day) - d(e)).days <= 75]
            if not closed:
                continue
            row = next((r for r in rows if r["end"] == closed[-1]), None)
            if row:
                quarter = row["label"]
            elif closed[-1] == ends[-1]:
                # out before its 10-Q: the quarter after the last one in the SEC facts
                quarter = quarter_label(
                    (d(rows[-1]["end"]) + timedelta(days=1)).isoformat(), ends[-1]
                )
            else:
                quarter = None
            # A release counts from its 8-K; the reaction waits for the next close.
            rx = reaction(px, spx, day) or {"session": None, "move": None, "vs_index": None}
            events.append({"date": day, "accepted": accepted, **rx, "quarter": quarter})

        snaps = history.get(ticker, [])
        checks = revenue_checks(rows, events, snaps)
        current = next((r for r in y["revenue_estimate"] if r.get("period") == "0q"), None)
        now_q = estimate_quarter(rows, events, current, today)

        # trailing P/E through time: price over TTM diluted EPS known at that date
        eps_steps = []
        for i in range(3, len(rows)):
            ni = ttm(rows, "net_income", i)
            sh = rows[i]["shares"]
            if ni is not None and sh:
                eps_steps.append((pd.Timestamp(rows[i]["available"]), ni / sh))
        weekly = week_ends(px[px.index >= asof - pd.DateOffset(years=5)]).dropna()
        per_series = []
        for t, p in weekly.items():
            known = [e for at, e in eps_steps if at <= t]
            if known:
                # A loss-making TTM has no P/E; None breaks the line instead of bridging it.
                per = _r(p / known[-1], 2) if known[-1] > 0 else None
                per_series.append([t.date().isoformat(), per])
        eps_ttm = eps_steps[-1][1] if eps_steps else None

        annual_ends = [
            e
            for (s, e) in merged(cf, FLOWS["revenue"], "USD", duration=True)
            if 350 <= (d(e) - d(s)).days + 1 <= 380
        ]
        # the fiscal year after the last 10-K in the SEC facts
        fy_end = d(max(annual_ends)) + timedelta(days=364)
        # Yahoo moves its current year on once the fourth quarter is reported,
        # before the 10-K reaches the SEC facts (a week or more for Broadcom,
        # Micron and Oracle); its own last reported quarter says when.
        reported = [
            r["quarter"][:10] for r in y["earnings_history"] if r.get("epsActual") is not None
        ]
        fy0_end = fy_end
        if reported and d(max(reported)) >= fy_end - timedelta(days=10):
            fy0_end += timedelta(days=364)
        eps_ntm = ntm_eps(y["earnings_estimate"], fy0_end, today)

        last = rows[-1]
        price = float(px.iloc[-1])
        year_start = px[px.index < pd.Timestamp(asof.year, 1, 1)]
        one_year = px[px.index <= asof - pd.DateOffset(years=1)]
        info = y["info"]
        companies.append(
            {
                "ticker": ticker,
                "name": name,
                "group": group,
                "price": _r(price, 2),
                "chg_1d": _r(price / float(px.iloc[-2]) - 1),
                "ret_ytd": _r(price / float(year_start.iloc[-1]) - 1) if len(year_start) else None,
                "ret_1y": _r(price / float(one_year.iloc[-1]) - 1) if len(one_year) else None,
                "market_cap": info.get("marketCap"),
                "spy_weight": _r(weights[ticker]),
                "per_ttm": _r(price / eps_ttm, 2) if eps_ttm and eps_ttm > 0 else None,
                "per_ntm": _r(price / eps_ntm, 2) if eps_ntm and eps_ntm > 0 else None,
                "eps_ntm": _r(eps_ntm, 3),
                "eps_ttm": _r(eps_ttm, 3),
                "yahoo_trailing_pe": _r(info.get("trailingPE"), 2),
                "yahoo_forward_pe": _r(info.get("forwardPE"), 2),
                "next_earnings": (y.get("next_earnings") or {}).get("date"),
                "next_earnings_estimate": (y.get("next_earnings") or {}).get("estimate"),
                "fiscal_year_end": fy_end.isoformat(),
                "consensus_from": snaps[0]["taken"] if snaps else None,
                # Yahoo keeps a reported quarter as its current one for a while.
                "estimate_quarter": None
                if now_q is None
                else {
                    "label": now_q["label"],
                    "end": now_q["end"],
                    "released": now_q["release"] is not None,
                },
                "latest_quarter": last["label"],
                "latest_end": last["end"],
                "rev_yoy": _r(last["rev_yoy"]),
                "op_margin_ttm": _r(_ratio(ttm(rows, "operating_income"), ttm(rows, "revenue"))),
                "capex_rev_ttm": _r(_ratio(ttm(rows, "capex"), ttm(rows, "revenue"))),
                "revenue_ttm": ttm(rows, "revenue"),
                "ocf_ttm": ttm(rows, "ocf"),
                "capex_ttm": ttm(rows, "capex"),
                "fcf_ttm": ttm(rows, "fcf"),
                "net_income_ttm": ttm(rows, "net_income"),
                "returns_ttm": _add(ttm(rows, "buybacks"), ttm(rows, "dividends")),
                "liquid": last["liquid"],
                "debt": last["debt"],
                "net_cash": _sub(last["liquid"], last["debt"]),
                "debt_change_1y": _sub(last["debt"], rows[-5]["debt"]) if len(rows) > 4 else None,
                "quarters": [
                    {
                        k: (_r(v, 6) if isinstance(v, float) else v)
                        for k, v in r.items()
                        if k not in ("available", "debt_with_leases")
                    }
                    for r in rows[-20:]
                ],
                "notes": data_notes(rows[-20:]),
                "events": events[-12:],
                "eps_history": y["earnings_history"],
                "estimates": {
                    "eps": y["earnings_estimate"],
                    "revenue": y["revenue_estimate"],
                },
                "per_series": per_series,
                "revenue_checks": checks,
            }
        )

    saved = [datetime.fromisoformat(s["taken"]) for snaps in history.values() for s in snaps]
    return {
        "asof": {
            "prices": asof.date().isoformat(),
            "spy": spy_asof,
            "built": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
            # first consensus snapshot, Japan date as shown with each snapshot
            "consensus_from": min(saved).astimezone(JST).date().isoformat() if saved else None,
        },
        "groups": [
            {"key": k, "name": n, "tickers": [t for t, _, g in COMPANIES if g == k]}
            for k, n in GROUPS
        ],
        "companies": companies,
        "prices": price_block(prices, asof),
        "world": world_block(companies, prices, weights, asof, spy_asof),
        "season": season_block(companies, today),
    }


def price_block(prices: pd.DataFrame, asof) -> dict:
    p = prices[prices.index >= asof - pd.DateOffset(years=5)].ffill()
    out = {"dates": [t.date().isoformat() for t in p.index]}
    for col in p.columns:
        out["SPX" if col == "^GSPC" else col] = [_r(v, 2) for v in p[col]]
    return out


def world_block(
    companies: list[dict], prices: pd.DataFrame, weights: dict, asof, spy_asof: str
) -> dict:
    p = prices[prices.index >= asof - pd.DateOffset(years=10)].ffill()
    weekly = week_ends(p).dropna()
    mag7 = [c for c in companies if c["group"] == "mag7"]
    by_q: dict = {}
    for c in companies:
        for r in c["quarters"]:
            by_q.setdefault(r["cal_q"], {})[c["ticker"]] = r
    flows = []
    for q in sorted(by_q):
        slot = by_q[q]
        capex = [slot[t]["capex"] if t in slot else None for t in PAYERS]
        ocf = [slot[t]["ocf"] if t in slot else None for t in PAYERS]
        sales = [slot[t]["revenue"] if t in slot else None for t in SELLERS]
        flows.append(
            {
                "q": q,
                "payers_complete": None not in capex and None not in ocf,
                "sellers_complete": None not in sales,
                "have": [t for t in (*PAYERS, *SELLERS) if t in slot],
                "capex": sum(v for v in capex if v is not None),
                "ocf": sum(v for v in ocf if v is not None),
                "sales": sum(v for v in sales if v is not None),
            }
        )
    payers = [c for c in companies if c["ticker"] in PAYERS]
    # a payer without both twelve-month figures would put capex over a larger OCF
    counted = [c for c in payers if c["capex_ttm"] is not None and c["ocf_ttm"] is not None]
    return {
        "share_now_mag7": _r(sum(weights[c["ticker"]] for c in mag7)),
        "share_now_all": _r(sum(weights.values())),
        "share_series_mag7": index_share(mag7, p, weekly, weights, spy_asof),
        "share_series_all": index_share(companies, p, weekly, weights, spy_asof),
        "market_cap_mag7": sum(c["market_cap"] or 0 for c in mag7),
        "market_cap_all": sum(c["market_cap"] or 0 for c in companies),
        "payers": list(PAYERS),
        "sellers": list(SELLERS),
        "payer_ttm_have": [c["ticker"] for c in counted],
        "payer_capex_ttm": sum(c["capex_ttm"] for c in counted),
        "payer_ocf_ttm": sum(c["ocf_ttm"] for c in counted),
        "flows": flows,
    }


def index_share(
    companies: list[dict], p: pd.DataFrame, weekly: pd.DataFrame, weights: dict, spy_asof: str
):
    """Weekly S&P 500 share of a set of companies, rolled from the SPY weights.

    w_i(t) = w_i(0) * [P_i(t) S_i(t) / P_i(0) S_i(0)] / [SPX(t) / SPX(0)], where 0 is
    the last close on or before the holdings date (later closes roll it forward).
    Ignores index divisor and float changes, so it is an estimate.
    """
    ref = p.index[p.index <= pd.Timestamp(spy_asof)][-1]
    spx_ref = float(p.loc[ref, "^GSPC"])
    share = pd.Series(0.0, index=weekly.index)
    for c in companies:
        full = _all_shares(c["ticker"])
        span = weekly.index.union(full.index).union([ref])
        shares = full.reindex(span).sort_index().ffill().bfill()
        cap = float(p.loc[ref, c["ticker"]]) * shares.loc[ref]
        mc_ratio = (weekly[c["ticker"]] * shares.reindex(weekly.index)) / cap
        share += weights[c["ticker"]] * (mc_ratio / (weekly["^GSPC"] / spx_ref)).fillna(0)
    return [[t.date().isoformat(), _r(v)] for t, v in share.items()]


_SHARES_CACHE: dict = {}


def _all_shares(ticker: str) -> pd.Series:
    """Every quarter's diluted share count (today's basis) back to the start of the facts."""
    if ticker not in _SHARES_CACHE:
        cf = load(f"companyfacts_{ticker}.json")
        splits = load(f"yahoo_{ticker}.json").get("splits", [])
        rows = company_quarters(cf, splits)
        _SHARES_CACHE[ticker] = pd.Series(
            {pd.Timestamp(r["end"]): r["shares"] for r in rows if r["shares"]}, dtype=float
        )
    return _SHARES_CACHE[ticker]


def season_block(companies: list[dict], today: date) -> dict:
    """Where each company stands on the last finished calendar quarter.

    A fiscal quarter belongs to the season when its middle falls in that
    calendar quarter, so Micron's June-August and Oracle's June-August
    quarters count for July-September and were already out in September.
    """
    q_end = date(today.year, 3 * ((today.month - 1) // 3) + 1, 1) - timedelta(days=1)
    season_q = f"{q_end.year}Q{(q_end.month - 1) // 3 + 1}"
    rows = []
    for c in companies:
        qs = c["quarters"]
        row = next((r for r in qs if r["cal_q"] == season_q), None)
        check = next((k for k in c["revenue_checks"] if k["cal_q"] == season_q), None)
        if row:
            end = d(row["end"])
        elif check:
            end = d(check["end"])
        else:
            end = d(qs[-1]["end"]) + timedelta(days=91)
        event = next((e for e in c["events"] if 0 < (d(e["date"]) - end).days <= 75), None)
        missing = None
        if event and not check:
            # no snapshot saved before the 8-K, or none whose year-ago revenue names
            # this quarter (a restated year-ago figure can miss the 0.2% match)
            first = c["consensus_from"]
            accepted = datetime.fromisoformat(event["accepted"])
            early = first is None or datetime.fromisoformat(first) >= accepted
            missing = "before_saving" if early else "unmatched"
        rows.append(
            {
                "ticker": c["ticker"],
                "reported": event is not None,
                "event": event,
                "label": row["label"] if row else check["label"] if check else None,
                # SEC numbers lag the press release until the 10-Q/10-K is filed.
                "in_sec": row is not None,
                "filing": "10-K" if abs((end - d(c["fiscal_year_end"])).days) <= 10 else "10-Q",
                "end": row["end"] if row else None,
                "next": None if event else c["next_earnings"],
                "next_estimate": None if event else c["next_earnings_estimate"],
                "check": check,
                "check_missing": missing,
            }
        )
    label = f"{q_end.year}年{q_end.month - 2}–{q_end.month}月期"
    return {"label": label, "quarter": season_q, "rows": rows}


def main() -> None:
    data = build()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.read_text()
    html = html.replace("/*__TOKENS__*/", TOKENS.read_text())
    html = html.replace("/*__DATA__*/null", payload)
    OUT.write_text(html)
    print(f"wrote {OUT} ({len(html) // 1024} KiB)")


if __name__ == "__main__":
    main()
