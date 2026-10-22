"""SEC companyfacts and submissions as point-in-time long rows.

Network access stays with the caller; this module only parses. Availability is
taken from the filing date alone: a fact becomes usable at 00:00 New York time
on the weekday after ``filed``. The submissions field ``acceptanceDateTime`` is
labelled UTC but runs ahead of true UTC by the Eastern offset (NVIDIA's earnings
8-Ks, furnished at 16:20 ET, read 00:21Z; nothing is stamped 09-13Z while 246
filings sit at 03-08Z, when EDGAR is closed), so it is kept for audit only.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
PERIODIC_FORMS = frozenset(
    {"10-K", "10-K/A", "10-Q", "10-Q/A", "10-KT", "10-QT", "20-F", "20-F/A", "40-F", "40-F/A"}
)
ANNUAL_FORMS = frozenset({"10-K", "10-K/A", "10-KT", "20-F", "20-F/A", "40-F", "40-F/A"})
_BASIS = {"us-gaap": "US-GAAP", "ifrs-full": "IFRS", "dei": "DEI"}
# data.sec.gov answers this; www.sec.gov (filing documents) refuses any agent
# without a contact address, and the user's address is not ours to send.
USER_AGENT = "portfolio-analyzer-ai-bubble/0.1 (personal research)"


def companyfacts_url(cik: int) -> str:
    return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"


def submissions_url(cik: int) -> str:
    return f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"


def fetch_json(
    url: str, *, opener: Callable[..., Any] = urllib.request.urlopen, timeout: float = 60
) -> tuple[Any, str, bytes]:
    """Parsed JSON, the sha256 of the bytes received, and the bytes themselves."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener(request, timeout=timeout) as response:
        body = response.read()
    return json.loads(body), hashlib.sha256(body).hexdigest(), body


def _midnight_ny_utc(day: date) -> str:
    return datetime.combine(day, time(0), NY).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _next_weekday(day: date) -> date:
    nxt = day + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt


def accepted_times(pages: list[dict[str, Any]]) -> dict[str, str]:
    """accession -> raw acceptanceDateTime from the main submissions file and its older pages."""
    out: dict[str, str] = {}
    for page in pages:
        block = page.get("filings", {}).get("recent", page)
        numbers = block.get("accessionNumber", [])
        stamps = block.get("acceptanceDateTime", [])
        for accession, stamp in zip(numbers, stamps, strict=True):
            out[str(accession)] = str(stamp)
    return out


def _has_periodic(fact: dict[str, Any] | None) -> bool:
    return any(
        item.get("form") in PERIODIC_FORMS
        for items in (fact or {}).get("units", {}).values()
        for item in items
    )


def choose_concepts(raw: dict[str, Any], candidates: dict[str, list[str]]) -> dict[str, str]:
    """For each metric, the first candidate concept this filer reports in periodic forms.

    One concept per metric keeps two differently scoped tags (say ``Revenues``
    and the ASC 606 revenue tag) from colliding on the same period.
    """
    chosen: dict[str, str] = {}
    for metric, refs in candidates.items():
        for ref in refs:
            taxonomy, name = ref.split(":", 1)
            if _has_periodic(raw.get("facts", {}).get(taxonomy, {}).get(name)):
                chosen[metric] = ref
                break
    return chosen


def parse_companyfacts(
    raw: dict[str, Any],
    issuer_id: str,
    accepted: dict[str, str],
    concepts: dict[str, str | list[str]],
    *,
    retrieved_at: str,
) -> list[dict[str, Any]]:
    """Rows for each metric from periodic reports only.

    A metric may name several concepts in priority order (filers change tags,
    e.g. ``Revenues`` before ASC 606). For one filing and period the first
    concept that reports it wins, so tags never collide; older periods are
    still filled from the later candidates.

    Two reports filed the same day can disagree on one period (Arista's 10-K
    and 10-Q of 2015-05-15 on 2012 year-end cash). The annual report's value is
    kept and the other is listed in ``same_day_conflict``; two reports of the
    same kind are both kept, so the as-of selection refuses them.
    """
    cik = int(raw["cik"])
    rows: list[dict[str, Any]] = []
    for metric, refs in concepts.items():
        seen: set[tuple[str, str, str, str]] = set()
        for ref in [refs] if isinstance(refs, str) else refs:
            taxonomy, name = ref.split(":", 1)
            fact = raw.get("facts", {}).get(taxonomy, {}).get(name)
            for unit, items in (fact or {}).get("units", {}).items():
                for item in items:
                    if item.get("form") not in PERIODIC_FORMS:
                        continue
                    accession = str(item["accn"])
                    start = item.get("start", item["end"])
                    key = (unit, start, item["end"], accession)
                    if key in seen:
                        continue
                    seen.add(key)
                    filed = date.fromisoformat(item["filed"])
                    rows.append(
                        {
                            "issuer_id": issuer_id,
                            "metric": metric,
                            "value": float(item["val"]),
                            "unit": unit,
                            "period_start": start,
                            "period_end": item["end"],
                            "published_at": _midnight_ny_utc(filed),
                            "available_at": _midnight_ny_utc(_next_weekday(filed)),
                            "retrieved_at": retrieved_at,
                            "source_url": (
                                f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                                f"{accession.replace('-', '')}/"
                            ),
                            "document_id": accession,
                            "accounting_basis": _BASIS.get(taxonomy, taxonomy),
                            "quality": "ok",
                            "concept": ref,
                            "form": item.get("form"),
                            "fy": item.get("fy"),
                            "fp": item.get("fp"),
                            "filed": item["filed"],
                            "sec_acceptance_raw": accepted.get(accession),
                        }
                    )
    return _settle_same_day(rows)


def _settle_same_day(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["metric"], row["unit"], row["period_start"], row["period_end"], row["filed"])
        groups.setdefault(key, []).append(row)
    dropped: set[int] = set()
    for group in groups.values():
        if len({r["value"] for r in group}) < 2:
            continue
        annual = [r for r in group if r["form"] in ANNUAL_FORMS]
        other = [r for r in group if r["form"] not in ANNUAL_FORMS]
        if not annual or not other or len({r["value"] for r in annual}) > 1:
            continue
        for row in annual:
            row["same_day_conflict"] = [
                {"document_id": r["document_id"], "form": r["form"], "value": r["value"]}
                for r in other
                if r["value"] != row["value"]
            ]
        dropped.update(id(r) for r in other if r["value"] != annual[0]["value"])
    return [row for row in rows if id(row) not in dropped]
