"""Spike: a hyperscaler page beside the megatech tracker.

The five companies that buy most of the AI data-center build-out: their cloud
units, the backlog customers have signed, and what the build-out costs in
capex, finance leases and depreciation. Reuses the tracker's SEC quarters and
market data; the cloud and backlog figures come from each filing's XBRL
instance (fetch.py keeps them in raw/segments_<ticker>.json).

Beside them, three neoclouds that rent out GPUs (CoreWeave, Nebius, IREN), with
their debt, interest and customer concentration. Nebius files 6-K, not 10-Q,
so its quarters come from Yahoo's statements.

Run after fetch.py:  .venv/bin/python -I megatech-tracker/hyperscalers.py
"""

from __future__ import annotations

import importlib.util
import json
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("build", HERE / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)
d, _r, _ratio, _sub = build.d, build._r, build._ratio, build._sub

OUT = build.ROOT / "_data/megatech-tracker/hyperscalers.html"
TEMPLATE = HERE / "hyperscalers.html"

REV = "RevenueFromContractWithCustomerExcludingAssessedTax"
OI = "OperatingIncomeLoss"
RPO = "RevenueRemainingPerformanceObligation"
SEG = "StatementBusinessSegmentsAxis"
PROD = "ProductOrServiceAxis"
LINE = "ProductsOrServicesSecondaryCategorizationAxis"

# The order fixes each company's slot. MSFT, GOOGL, AMZN and META keep their
# colors from the tracker; Oracle takes the slot Apple has there.
COMPANIES = [
    ("MSFT", "Microsoft", "cat-2", "hyper"),
    ("AMZN", "Amazon", "cat-4", "hyper"),
    ("GOOGL", "Alphabet", "cat-3", "hyper"),
    ("META", "Meta", "cat-5", "hyper"),
    ("ORCL", "Oracle", "cat-1", "hyper"),
    ("CRWV", "CoreWeave", "cat-6", "neo"),
    ("NBIS", "Nebius", "cat-7", "neo"),
    ("IREN", "IREN", "cat-8", "neo"),
]

# Per company: the cloud business (a product line or a segment), the operating
# segment that holds it (one entry per era when the segments were redrawn), the
# depreciation of property and equipment, and extra lines for its page. Each
# candidate list is tried in order per period, like build.FLOWS. A tuple of
# members is one line renamed; the names carry the same values over the overlap
# (Oracle's CloudServices and CloudRevenues for 2024-06..2025-02, Microsoft's
# Commercial Cloud and Microsoft Cloud for 2020-09..2021-03).
#
# Depreciation is us-gaap:Depreciation, not the cash-flow line: Microsoft's
# line ("depreciation, amortization, and other") jumped half again in October
# 2023 with the Activision intangibles, and Amazon's adds content and lease
# amortization (20.9 against 15.1 billion, July-September 2026). Microsoft gives
# quarters of it from July 2024, Amazon from January 2024.
SPEC = {
    "MSFT": {
        "cloud": "Microsoft Cloud",
        "cloud_def": "Azure・Microsoft 365 の法人向けクラウド・Dynamics 365・LinkedIn の法人向けなどの合計",
        "revenue": [(REV, {LINE: ("MicrosoftCloudMember", "CommercialCloudMember")})],
        "eras": [
            ("Intelligent Cloud", [{SEG: "IntelligentCloudMember"}]),
            ("Agents and Infra", [{SEG: "AgentsAndInfraMember"}]),
        ],
        "da": ["Depreciation"],
        "extra": {"Azure": [(REV, {PROD: "AzureMember"})]},
    },
    "AMZN": {
        "cloud": "AWS",
        "cloud_def": "AWS 部門の売上",
        "revenue": [(REV, {SEG: "AmazonWebServicesSegmentMember"})],
        "eras": [("AWS", [{SEG: "AmazonWebServicesSegmentMember"}])],
        "da": ["Depreciation"],
        "extra": {
            "AWS の減価償却": [("Depreciation", {SEG: "AmazonWebServicesSegmentMember"})],
            "AWS の設備の追加": [
                (
                    "SegmentExpenditureAdditionToLongLivedAssets",
                    {SEG: "AmazonWebServicesSegmentMember"},
                )
            ],
        },
    },
    "GOOGL": {
        "cloud": "Google Cloud",
        "cloud_def": "Google Cloud 部門の売上（GCP と Google Workspace など）",
        "revenue": [
            (REV, {SEG: ("GoogleCloudMember", "GoogleCloudSegmentMember")}),
            # 2020, before Google Cloud became a segment
            (REV, {PROD: "GoogleCloudMember", SEG: "GoogleInc.Member"}),
        ],
        "eras": [("Google Cloud", [{SEG: ("GoogleCloudMember", "GoogleCloudSegmentMember")}])],
        # depreciation "and impairment on disposition" until 2023
        "da": ["Depreciation", "DepreciationAndImpairmentOnDispositionOfPropertyAndEquipment"],
        "extra": {},
    },
    "META": {
        "cloud": None,
        "cloud_def": "クラウド事業はない（データセンターは自社のサービスと AI 用）",
        "revenue": [],
        "eras": [],
        "da": ["Depreciation"],
        "extra": {},
    },
    "ORCL": {
        "cloud": "Oracle Cloud",
        "cloud_def": "クラウドの売上（OCI＝インフラと、SaaS＝アプリケーションの合計）",
        "revenue": [(REV, {PROD: ("CloudRevenuesMember", "CloudServicesMember")})],
        "eras": [
            ("Cloud and License", [{SEG: "CloudAndLicenseBusinessMember"}]),
            ("Cloud and Software", [{SEG: "CloudAndSoftwareBusinessMember"}]),
        ],
        "da": ["Depreciation"],
        "extra": {
            "OCI": [(REV, {PROD: "CloudInfrastructureMember"})],
            "SaaS": [(REV, {PROD: "CloudApplicationsMember"})],
        },
    },
    "CRWV": {
        "cloud": "CoreWeave",
        "cloud_def": "全社の売上（GPU の計算資源の貸し出し）",
        "cloud_is_revenue": True,
        "revenue": [],
        "eras": [],
        "da": ["Depreciation"],
        "extra": {},
        # principal outstanding: the June 2026 10-Q stopped tagging LongTermDebt
        "debt": ["DebtInstrumentCarryingAmount"],
        # the income statement's "interest expense, net"
        "interest": [("InterestIncomeExpenseNonoperatingNet", -1)],
    },
    "NBIS": {
        "cloud": "Nebius",
        "cloud_def": "全社の売上（AI クラウドが大半。ほかに教育の TripleTen など）",
        "cloud_is_revenue": True,
        "yahoo": True,
        "revenue": [],
        "eras": [],
        "da": [],
        "extra": {},
    },
    "IREN": {
        "cloud": "AI Cloud",
        "cloud_def": "AI クラウド部門の売上（残りはビットコインのマイニング）",
        "revenue": [
            (REV, {SEG: "AICloudServicesMember"}),
            (REV, {PROD: "AICloudServicesMember"}),
        ],
        "eras": [],
        # IREN tags depreciation only together with amortization
        "da": ["DepreciationDepletionAndAmortization"],
        "extra": {
            "ビットコインのマイニング": [
                (REV, {SEG: ("BitcoinMiningMember", "BitcoinMiningRevenueMember")}),
                (REV, {PROD: ("BitcoinMiningMember", "BitcoinMiningRevenueMember")}),
            ]
        },
        # convertible notes until the project loans of 2026
        "debt": ["LongTermDebt", "ConvertibleNotesPayable"],
        # Microsoft's GPU contract is mostly a lease, outside the backlog (RPO)
        "contracted": "RemainingPerformanceObligationsAndContractedLeaseArrangementsAggregateValue",
    },
}
INTEREST = [("InterestExpenseNonoperating", 1), ("InterestExpense", 1), ("InterestExpenseDebt", 1)]
CONCENTRATION = "ConcentrationRiskPercentage1"
LEASE_ADDED = ["RightOfUseAssetObtainedInExchangeForFinanceLeaseLiability"]
LEASE_REPAID = ["FinanceLeasePrincipalPayments"]
# 24 quarters so the first of the 20 charted still has a year-ago quarter
QUARTERS_SHOWN = 24


# ------------------------------------------------------- facts from the filings


def _plain(dims: dict) -> dict:
    """Dimensions without the 'operating segments' qualifier some filers add."""
    return {
        a: m
        for a, m in dims.items()
        if not (a == "ConsolidationItemsAxis" and m == "OperatingSegmentsMember")
    }


def _matches(fdims: dict, dims: dict) -> bool:
    got = _plain(fdims)
    return got.keys() == dims.keys() and all(
        got[a] in m if isinstance(m, tuple) else got[a] == m for a, m in dims.items()
    )


def _digits(v: float) -> int:
    """Significant digits of a whole-dollar figure: 7623000000 has 4, 7600000000 has 2."""
    return len(str(round(abs(v))).rstrip("0"))


def filing_facts(kept: dict, candidates: list[tuple[str, dict]], *, duration: bool) -> dict:
    """(start, end) -> latest-filed fact, in the shape build.merged returns.

    The first candidate that reports a period gives its value; the first filing
    date spans every candidate.
    """
    out: dict = {}
    first: dict = {}
    for concept, dims in candidates:
        best: dict = {}
        for f in kept.values():
            # A filing can give one figure twice, exactly and rounded to billions
            # in the text (Oracle's depreciation for fiscal 2026, 7.623 and 7.6);
            # files parsed before fetch.py kept only the precise one hold both.
            here: dict = {}
            for c, fdims, s, e, v in f["facts"]:
                if c != concept or (s is not None) != duration or not _matches(fdims, dims):
                    continue
                if (s, e) not in here or _digits(v) > _digits(here[(s, e)]):
                    here[(s, e)] = v
            for (s, e), v in here.items():
                key = (s, e)
                first[key] = min(first.get(key, f["filed"]), f["filed"])
                cur = best.get(key)
                if cur is None:
                    best[key] = {
                        "val": v,
                        "filed": f["filed"],
                        "concept": c,
                        "history": [(f["filed"], v)],
                    }
                    continue
                cur["history"].append((f["filed"], v))
                if f["filed"] > cur["filed"]:
                    best[key] = {**cur, "val": v, "filed": f["filed"]}
        for key, it in best.items():
            out.setdefault(key, it)
    for key, it in out.items():
        it["first_filed"] = first[key]
        it["history"].sort()
    return out


def _days(key: tuple) -> int:
    return (d(key[1]) - d(key[0])).days + 1


def _as_of(fact: dict, day: str) -> float | None:
    """A fact's value as it stood on `day` (its last filing on or before it)."""
    known = [v for filed, v in fact["history"] if filed <= day]
    return known[-1] if known else None


def quarters(facts: dict) -> dict:
    """end -> value per quarter: the three-month facts, then each fourth quarter from its year.

    The fourth quarter is the year as its 10-K first reported it, less the first
    nine months as they stood on that day. A later 10-K re-presents the year
    under redrawn segments while the quarters of that year keep the old ones;
    mixing the two put Microsoft's Intelligent Cloud margin at 12% for April-June
    2023. Some lines are tagged for the quarter and the year but not year to
    date (Microsoft Cloud, Oracle's cloud revenue), so the nine months are then
    the three quarters.
    """
    flows = build.quarterly_flows(facts)
    direct = {e: k for k in facts if 80 <= _days(k) <= 100 for e in [k[1]]}
    q = {e: v[1] for e, v in flows.items() if e in direct}
    for (s, e), it in facts.items():
        if not 350 <= _days((s, e)) <= 380 or e in direct:
            continue
        nine = next((k for k in facts if k[0] == s and 260 <= _days(k) <= 285 and k[1] < e), None)
        inside = [facts[k] for qe, k in direct.items() if d(s) <= d(k[0]) and qe < e]
        # The first 10-K whose day already knew the nine months: a year moved to a
        # new tag (Alphabet's depreciation, 2024) has its nine months under that
        # tag only from the next year's 10-Q.
        for filed, year in it["history"]:
            if nine is not None and _as_of(facts[nine], filed) is not None:
                q[e] = year - _as_of(facts[nine], filed)
                break
            before = [_as_of(f, filed) for f in inside]
            if len(before) == 3 and None not in before:
                q[e] = year - sum(before)
                break
    # second and third quarters that only year-to-date facts give (cash flows);
    # a fourth quarter left out above stays out rather than mixing vintages
    year_ends = {k[1] for k in facts if 350 <= _days(k) <= 380}
    for e, v in flows.items():
        if e not in year_ends:
            q.setdefault(e, v[1])
    return q


def series(kept: dict, candidates: list[tuple[str, dict]]) -> dict:
    """Quarters per candidate, then the first candidate that has each quarter.

    Differencing stays within one tag: a year under a new tag less nine months
    under the old one mixes definitions (Alphabet's depreciation and impairment
    became depreciation alone).
    """
    out: dict = {}
    for cand in candidates:
        for e, v in quarters(filing_facts(kept, [cand], duration=True)).items():
            out.setdefault(e, v)
    return out


def instants(kept: dict, candidates: list[tuple[str, dict]]) -> dict:
    return {e: it["val"] for (_, e), it in filing_facts(kept, candidates, duration=False).items()}


def ttm_from_ytd(facts: dict, end: str) -> float | None:
    """Twelve months to `end` = year to date + the last full year - the year to date a year before."""
    by = {k: it["val"] for k, it in facts.items()}
    for (s, e), ytd in by.items():
        if e != end or (d(e) - d(s)).days + 1 > 380:
            continue
        year = next(
            (
                v
                for (s0, e0), v in by.items()
                if abs((d(s) - d(e0)).days - 1) <= 3 and 350 <= (d(e0) - d(s0)).days + 1 <= 380
            ),
            None,
        )
        if (d(e) - d(s)).days + 1 >= 350:
            return ytd
        before = next(
            (
                v
                for (s0, e0), v in by.items()
                if abs((d(e0) - (d(e) - timedelta(days=364))).days) <= 7
                and abs((d(s0) - (d(s) - timedelta(days=364))).days) <= 7
            ),
            None,
        )
        if year is not None and before is not None:
            return year + ytd - before
    return None


def named_backlog(kept: dict) -> list[dict]:
    """Backlog the filings tie to one customer (Amazon names OpenAI and Anthropic)."""
    out: dict = {}
    for f in kept.values():
        for c, dims, s, e, v in f["facts"]:
            who = dims.get("MajorCustomersAxis")
            if not c.startswith(RPO) or who is None or len(dims) != 1:
                continue
            # Microsoft's commercial customers are a class, not one customer.
            if who == "CommercialCustomersMember":
                continue
            kind = "balance" if c == RPO else "added" if "Increase" in c else None
            if kind is None:
                continue
            key = (who, kind, s, e)
            if key not in out or f["filed"] > out[key]["filed"]:
                out[key] = {
                    "customer": who.removesuffix("Member"),
                    "kind": kind,
                    "start": s,
                    "end": e,
                    "value": v,
                    "filed": f["filed"],
                }
    return sorted(out.values(), key=lambda r: (r["customer"], r["end"], r["kind"]))


def concentration(kept: dict) -> dict:
    """end -> {customer: share of revenue} for each three-month period a filing gives."""
    out: dict = {}
    for f in sorted(kept.values(), key=lambda f: f["filed"]):
        for c, dims, s, e, v in f["facts"]:
            if (
                c != CONCENTRATION
                or s is None
                or not 80 <= _days((s, e)) <= 100
                or dims.get("ConcentrationRiskByBenchmarkAxis")
                != "RevenueFromContractWithCustomerMember"
                or "MajorCustomersAxis" not in dims
            ):
                continue
            out.setdefault(e, {})[dims["MajorCustomersAxis"].removesuffix("Member")] = v
    return out


def _quarter_start(end: str) -> str:
    e = d(end)
    m = e.month - 2
    return date(e.year - (m < 1), m + 12 * (m < 1), 1).isoformat()


def yahoo_rows(ticker: str) -> list[dict]:
    """Quarter rows like build.company_quarters, from Yahoo's statements.

    For a filer of 6-K (Nebius), whose quarterly figures SEC holds only as
    press releases. Debt leaves out finance leases, as for the SEC filers.
    """
    st = build.load(f"yahoo_{ticker}.json")["statements"]
    inc, cfl, bal = (
        st["quarterly_income_stmt"],
        st["quarterly_cashflow"],
        st["quarterly_balance_sheet"],
    )
    rows = []
    for e in sorted(inc):
        i, c, b = inc[e], cfl.get(e, {}), bal.get(e, {})
        if i.get("Total Revenue") is None:
            continue
        s = _quarter_start(e)
        capex = -c["Capital Expenditure"] if "Capital Expenditure" in c else None
        debt = b.get("Total Debt")
        if debt is not None:
            debt -= b.get("Capital Lease Obligations", 0)
        rows.append(
            {
                "end": e,
                "start": s,
                "available": None,
                "revenue": i["Total Revenue"],
                "operating_income": i.get("Operating Income"),
                "net_income": i.get("Net Income Common Stockholders"),
                "ocf": c.get("Operating Cash Flow"),
                "capex": capex,
                "buybacks": 0.0,
                "dividends": 0.0,
                "liquid": b.get("Cash Cash Equivalents And Short Term Investments"),
                "debt": debt,
                "debt_with_leases": False,
                "equity": b.get("Stockholders Equity"),
                "shares": i.get("Diluted Average Shares"),
                "label": build.quarter_label(s, e),
                "cal_q": build.cal_quarter(s, e),
                "eps": i.get("Diluted EPS"),
                "da": c.get("Depreciation"),
                "interest": i.get("Interest Expense"),
            }
        )
    for k, row in enumerate(rows):
        prior = build._year_ago(rows, k)
        row["rev_yoy"] = row["revenue"] / prior["revenue"] - 1 if prior else None
        row["op_margin"] = _ratio(row["operating_income"], row["revenue"])
        row["fcf"] = _sub(row["ocf"], row["capex"])
    return rows


def annual_20f(cf: dict, concept: str, *, duration: bool) -> dict:
    """(start, end) -> value from a 20-F (build.merged reads only 10-Q and 10-K)."""
    out: dict = {}
    for it in cf["facts"].get("us-gaap", {}).get(concept, {}).get("units", {}).get("USD", []):
        if not it["form"].startswith("20-F") or ("start" in it) != duration:
            continue
        key = (it.get("start"), it["end"])
        if key not in out or it["filed"] >= out[key][0]:
            out[key] = (it["filed"], it["val"])
    return {k: v for k, (_, v) in out.items()}


# -------------------------------------------------------------- one company


def company(ticker: str, name: str, color: str, group: str, base: dict | None, market) -> dict:
    """One company's page data; `base` is its tracker entry, or None for a neocloud."""
    spec = SPEC[ticker]
    cf = build.load(f"companyfacts_{ticker}.json")
    y = build.load(f"yahoo_{ticker}.json")
    seg_path = build.RAW / f"segments_{ticker}.json"
    kept = build.load(seg_path.name) if seg_path.exists() else {}
    rows = (
        yahoo_rows(ticker) if spec.get("yahoo") else build.company_quarters(cf, y.get("splits", []))
    )

    def flow(tags):
        return {
            e: v[1]
            for e, v in build.quarterly_flows(build.merged(cf, tags, "USD", duration=True)).items()
        }

    if "debt" in spec:
        debt = build.instants(cf, spec["debt"])
        for row in rows:
            row["debt"] = debt.get(row["end"])
    if base is None:
        prices, history, today = market
        annual = (
            [e for s, e in annual_20f(cf, "Revenues", duration=True)] if spec.get("yahoo") else None
        )
        base = build.company_block(
            ticker, name, group, prices, {}, history, today, rows=rows, annual_ends=annual
        )

    interest = {}
    if not spec.get("yahoo"):
        for tag, sign in spec.get("interest", INTEREST):
            for e, v in flow([tag]).items():
                interest.setdefault(e, sign * v)
    lease_facts = build.merged(cf, LEASE_ADDED, "USD", duration=True)
    lease_added, lease_repaid = flow(LEASE_ADDED), flow(LEASE_REPAID)
    da = series(kept, [(c, {}) for c in spec["da"]])
    cloud = series(kept, spec["revenue"]) if spec["revenue"] else {}
    if spec.get("cloud_is_revenue"):
        cloud = {r["end"]: r["revenue"] for r in rows}
    eras = [
        (
            era,
            series(kept, [(REV, dims) for dims in members]),
            series(kept, [(OI, dims) for dims in members]),
        )
        for era, members in spec["eras"]
    ]
    rpo = instants(kept, [(RPO, {})])
    if spec.get("yahoo"):
        rpo = {e: v for (_, e), v in annual_20f(cf, RPO, duration=False).items()}
    contracted = instants(kept, [(spec["contracted"], {})]) if "contracted" in spec else {}
    commercial = instants(kept, [(RPO, {"MajorCustomersAxis": "CommercialCustomersMember"})])
    customers = concentration(kept)
    extra = {k: series(kept, cands) for k, cands in spec["extra"].items()}

    out_rows = []
    for row in rows:
        e = row["end"]
        lease = lease_added.get(e)
        r = {
            "end": e,
            "start": row["start"],
            "label": row["label"],
            "cal_q": row["cal_q"],
            "revenue": row["revenue"],
            "operating_income": row["operating_income"],
            "ocf": row["ocf"],
            "capex": row["capex"],
            "lease": lease,
            "capex_all": build._add(row["capex"], lease),
            "lease_repaid": lease_repaid.get(e),
            "fcf": row["fcf"],
            "da": row["da"] if spec.get("yahoo") else da.get(e),
            "interest": row["interest"] if spec.get("yahoo") else interest.get(e),
            "debt": row["debt"],
            "op_margin": row["op_margin"],
            "cloud": cloud.get(e),
            "rpo": rpo.get(e),
            "rpo_commercial": commercial.get(e),
            "contracted": contracted.get(e),
            "customers": customers.get(e),
            "segments": {
                era: {"revenue": rev.get(e), "operating_income": oi.get(e)}
                for era, rev, oi in eras
                if rev.get(e) is not None
            },
            "extra": {k: v.get(e) for k, v in extra.items() if v.get(e) is not None},
        }
        r["fcf_after_leases"] = (
            _sub(r["fcf"], r["lease_repaid"]) if r["lease_repaid"] is not None else None
        )
        out_rows.append(r)

    for i, r in enumerate(out_rows):
        prior = build._year_ago(out_rows, i)
        for k in ("cloud", "capex", "da", "rpo", "revenue"):
            r[f"{k}_yoy"] = (
                _r(r[k] / prior[k] - 1) if prior and r[k] is not None and prior.get(k) else None
            )
        for era, seg in r["segments"].items():
            ago = (prior or {}).get("segments", {}).get(era)
            seg["margin"] = _r(_ratio(seg["operating_income"], seg["revenue"]))
            seg["revenue_yoy"] = (
                _r(seg["revenue"] / ago["revenue"] - 1) if ago and ago.get("revenue") else None
            )
        for k, v in r["extra"].items():
            ago = extra[k].get(prior["end"]) if prior else None
            r["extra"][k] = {"value": v, "yoy": _r(v / ago - 1) if ago else None}
        r["capex_rev"] = _r(_ratio(r["capex"], r["revenue"]))
        r["da_rev"] = _r(_ratio(r["da"], r["revenue"]))
        r["interest_rev"] = _r(_ratio(r["interest"], r["revenue"]))
        r["top_customer"] = max(r["customers"].values()) if r["customers"] else None

    last = out_rows[-1]
    n = len(out_rows) - 1

    def ttm(key, i=n):
        return build.ttm(out_rows, key, i)

    def ttm_yoy(key):
        now, ago = ttm(key), ttm(key, n - 4) if n >= 4 else None
        return _r(now / ago - 1) if now is not None and ago else None

    cloud_rows = [r for r in out_rows if r["cloud"] is not None]
    cloud_last = cloud_rows[-1] if cloud_rows else None
    era_last = None
    if eras:
        # the newest era with figures, and its newest quarter
        for era, rev, _ in reversed(eras):
            if rev:
                era_last = era
                break
    seg_rows = [r for r in out_rows if era_last in r["segments"]]
    seg_last = seg_rows[-1] if seg_rows else None
    rpo_rows = [r for r in out_rows if r["rpo"] is not None]
    rpo_last = rpo_rows[-1] if rpo_rows else None
    revenue_ttm = ttm("revenue")
    cloud_ttm = ttm("cloud")
    # backlog over the cloud revenue of the year to that quarter end
    rpo_cloud = None
    if rpo_last is not None:
        rpo_cloud = build.ttm(out_rows, "cloud", out_rows.index(rpo_last))
        if rpo_cloud is None and spec.get("yahoo"):
            # Nebius's backlog comes once a year, with the 20-F's revenue beside it
            rpo_cloud = next(
                (
                    v
                    for (st, e), v in annual_20f(cf, "Revenues", duration=True).items()
                    if e == rpo_last["end"] and 350 <= _days((st, e)) <= 380
                ),
                None,
            )
    cust_rows = [r for r in out_rows if r["customers"]]
    contracted_rows = [r for r in out_rows if r["contracted"] is not None]

    return {
        **{
            k: base[k]
            for k in (
                "ticker",
                "name",
                "price",
                "chg_1d",
                "ret_ytd",
                "ret_1y",
                "market_cap",
                "spy_weight",
                "per_ttm",
                "per_ntm",
                "eps_ntm",
                "next_earnings",
                "next_earnings_estimate",
                "events",
                "net_cash",
                "debt",
                "debt_change_1y",
                "liquid",
                "fiscal_year_end",
            )
        },
        "name": name,
        "color": color,
        "group": group,
        "source": "yahoo" if spec.get("yahoo") else "sec",
        "cloud_name": spec["cloud"],
        "cloud_is_revenue": bool(spec.get("cloud_is_revenue")),
        "cloud_def": spec["cloud_def"],
        "eras": [era for era, _, _ in eras],
        "latest_quarter": last["label"],
        "latest_end": last["end"],
        "revenue_ttm": revenue_ttm,
        "ocf_ttm": ttm("ocf"),
        "capex_ttm": ttm("capex"),
        # Oracle tags lease additions only for some quarters; its year-to-date
        # figures still give the twelve months.
        "lease_ttm": ttm("lease")
        if ttm("lease") is not None
        else ttm_from_ytd(lease_facts, last["end"]),
        "capex_ttm_yoy": ttm_yoy("capex"),
        "capex_rev_ttm": _r(_ratio(ttm("capex"), revenue_ttm)),
        "capex_ocf_ttm": _r(_ratio(ttm("capex"), ttm("ocf"))),
        "da_ttm": ttm("da"),
        "da_ttm_yoy": ttm_yoy("da"),
        "fcf_ttm": ttm("fcf"),
        "fcf_after_leases_ttm": ttm("fcf_after_leases"),
        "operating_income_ttm": ttm("operating_income"),
        "op_margin_ttm": _r(_ratio(ttm("operating_income"), revenue_ttm)),
        "interest_ttm": ttm("interest"),
        "interest_rev_ttm": _r(_ratio(ttm("interest"), revenue_ttm)),
        "revenue_last": {
            "label": last["label"],
            "end": last["end"],
            "value": last["revenue"],
            "yoy": last["revenue_yoy"],
        },
        "customers_last": None
        if not cust_rows
        else {
            "label": cust_rows[-1]["label"],
            "end": cust_rows[-1]["end"],
            "shares": cust_rows[-1]["customers"],
        },
        # data-center leases, outside the borrowing figures
        "operating_lease": build.instants(cf, ["OperatingLeaseLiability"]).get(last["end"]),
        "contracted_last": None
        if not contracted_rows
        else {
            "label": contracted_rows[-1]["label"],
            "end": contracted_rows[-1]["end"],
            "value": contracted_rows[-1]["contracted"],
        },
        "cloud_last": None
        if cloud_last is None
        else {
            "label": cloud_last["label"],
            "end": cloud_last["end"],
            "value": cloud_last["cloud"],
            "yoy": cloud_last["cloud_yoy"],
            "share": _r(_ratio(cloud_last["cloud"], cloud_last["revenue"])),
        },
        "cloud_ttm": cloud_ttm,
        "segment_last": None
        if seg_last is None
        else {
            "era": era_last,
            "label": seg_last["label"],
            "end": seg_last["end"],
            **seg_last["segments"][era_last],
        },
        "rpo_last": None
        if rpo_last is None
        else {
            "label": rpo_last["label"],
            "end": rpo_last["end"],
            "value": rpo_last["rpo"],
            "yoy": rpo_last["rpo_yoy"],
            "commercial": rpo_last["rpo_commercial"],
            # backlog in years of the cloud business it mostly belongs to
            "years": _r(_ratio(rpo_last["rpo"], rpo_cloud), 2),
        },
        "named_backlog": named_backlog(kept),
        "quarters": [
            {k: (_r(v, 6) if isinstance(v, float) else v) for k, v in r.items()}
            for r in out_rows[-QUARTERS_SHOWN:]
        ],
        "notes": build.data_notes(rows[-QUARTERS_SHOWN:]),
    }


# ------------------------------------------------------------------- build


def build_page() -> dict:
    base = build.build()
    by = {c["ticker"]: c for c in base["companies"]}
    # The neoclouds' closes, cut at the tracker's last close so both pages agree.
    asof = build.pd.Timestamp(base["asof"]["prices"])
    neo = build.closes(build.RAW / "prices_neocloud.csv")
    neo = neo[neo.index <= asof]
    market = (neo, build.consensus_history(), datetime.now(build.JST).date())
    cos = [company(t, name, color, g, by.get(t), market) for t, name, color, g in COMPANIES]
    keep = {"dates", "SPX", *(t for t, _, _, _ in COMPANIES)}
    prices = {k: v for k, v in base["prices"].items() if k in keep}
    aligned = neo.reindex(build.pd.to_datetime(prices["dates"])).ffill()
    for t, _, _, g in COMPANIES:
        if g == "neo":
            prices[t] = [_r(v, 2) for v in aligned[t]]
    return {
        "asof": base["asof"],
        "companies": cos,
        "prices": prices,
        "totals": totals([c for c in cos if c["group"] == "hyper"]),
        "neo_totals": neo_totals([c for c in cos if c["group"] == "neo"]),
    }


def neo_totals(cos: list[dict]) -> dict:
    """Neocloud sums for the headline tiles."""
    grown = [c for c in cos if c["revenue_last"]["yoy"] is not None]
    rev = sum(c["revenue_last"]["value"] for c in grown)
    rev_ago = sum(c["revenue_last"]["value"] / (1 + c["revenue_last"]["yoy"]) for c in grown)
    capex = [c for c in cos if c["capex_ttm"] is not None and c["revenue_ttm"]]
    debt = [c for c in cos if c["debt"] is not None]
    interest = [c for c in cos if c["interest_ttm"] is not None]
    return {
        "revenue_q": rev,
        "revenue_q_yoy": _r(rev / rev_ago - 1) if rev_ago else None,
        "revenue_have": [c["ticker"] for c in grown],
        "capex_ttm": sum(c["capex_ttm"] for c in capex),
        "capex_rev": _r(
            _ratio(sum(c["capex_ttm"] for c in capex), sum(c["revenue_ttm"] for c in capex))
        ),
        "capex_have": [c["ticker"] for c in capex],
        "debt": sum(c["debt"] for c in debt),
        "debt_change_1y": sum(c["debt_change_1y"] for c in debt if c["debt_change_1y"] is not None),
        "debt_change_have": [c["ticker"] for c in debt if c["debt_change_1y"] is not None],
        "debt_have": [c["ticker"] for c in debt],
        "interest_ttm": sum(c["interest_ttm"] for c in interest),
        "operating_income_ttm": sum(
            c["operating_income_ttm"] for c in interest if c["operating_income_ttm"] is not None
        ),
        "interest_have": [c["ticker"] for c in interest],
    }


def totals(cos: list[dict]) -> dict:
    """Five-company sums for the headline tiles; each says which companies it holds."""

    def summed(key, among=cos):
        have = [c for c in among if c[key] is not None]
        return sum(c[key] for c in have), [c["ticker"] for c in have]

    capex, capex_have = summed("capex_ttm")
    ocf = sum(c["ocf_ttm"] for c in cos if c["ticker"] in capex_have and c["ocf_ttm"] is not None)
    grown = [c for c in cos if c["ticker"] in capex_have and c["capex_ttm_yoy"] is not None]
    ago = sum(c["capex_ttm"] / (1 + c["capex_ttm_yoy"]) for c in grown)
    now = sum(c["capex_ttm"] for c in grown)
    da = [c for c in cos if c["da_ttm_yoy"] is not None]
    da_now = sum(c["da_ttm"] for c in da)
    da_ago = sum(c["da_ttm"] / (1 + c["da_ttm_yoy"]) for c in da)
    rpo = [c for c in cos if c["rpo_last"] and c["rpo_last"]["yoy"] is not None]
    rpo_now = sum(c["rpo_last"]["value"] for c in rpo)
    rpo_ago = sum(c["rpo_last"]["value"] / (1 + c["rpo_last"]["yoy"]) for c in rpo)
    cloud = [c for c in cos if c["cloud_last"] and c["cloud_last"]["yoy"] is not None]
    cloud_now = sum(c["cloud_last"]["value"] for c in cloud)
    cloud_ago = sum(c["cloud_last"]["value"] / (1 + c["cloud_last"]["yoy"]) for c in cloud)
    return {
        "capex_ttm": capex,
        "capex_have": capex_have,
        "capex_ttm_yoy": _r(now / ago - 1) if ago else None,
        "capex_yoy_have": [c["ticker"] for c in grown],
        "capex_ocf": _r(_ratio(capex, ocf)),
        "da_ttm": da_now,
        "da_ttm_yoy": _r(da_now / da_ago - 1) if da_ago else None,
        "lease_ttm": sum(c["lease_ttm"] for c in cos if c["lease_ttm"] is not None),
        "lease_have": [c["ticker"] for c in cos if c["lease_ttm"] is not None],
        "rpo": rpo_now,
        "rpo_yoy": _r(rpo_now / rpo_ago - 1) if rpo_ago else None,
        "rpo_have": [c["ticker"] for c in rpo],
        "cloud_q": cloud_now,
        "cloud_q_yoy": _r(cloud_now / cloud_ago - 1) if cloud_ago else None,
        "cloud_have": [c["ticker"] for c in cloud],
    }


def main() -> None:
    data = build_page()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.read_text()
    html = html.replace("/*__TOKENS__*/", build.TOKENS.read_text())
    html = html.replace("/*__DATA__*/null", payload)
    OUT.write_text(html)
    print(f"wrote {OUT} ({len(html) // 1024} KiB)")


if __name__ == "__main__":
    main()
