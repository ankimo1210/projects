"""SEC EDGAR fundamentals (company facts) — point-in-time by filing date.

The free ``companyfacts`` API returns XBRL financial facts per company. Each fact
carries the period it covers (``end``) and the date it was **filed** (``filed``) —
so, exactly like macro vintages, a value is only knowable on/after its filing
date. :func:`concept_observations` parses one concept into a point-in-time frame
and :func:`fundamental_as_of` returns what was filed-and-visible on a date. These
feed the value/quality signals (e.g. earnings yield = net income / market cap).

Network use requires a descriptive User-Agent (SEC policy); set ``SEC_USER_AGENT``
or pass ``user_agent``. The parser is tested offline against a fixture (no network),
mirroring how the price connectors are tested.
"""

from __future__ import annotations

import json

import pandas as pd
import requests

from ..utils.config import env
from ..utils.dates import to_ts
from ..utils.paths import external_dir

_FACT_COLUMNS = ["period_end", "filed", "value", "form", "fy", "fp"]


class SecEdgarConnector:
    source = "sec_edgar"
    BASE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

    def __init__(self, user_agent: str | None = None, *, timeout: float = 30.0):
        self.user_agent = user_agent or env("SEC_USER_AGENT") or "quantkit research (set SEC_USER_AGENT)"
        self.timeout = timeout

    def _cache_path(self, cik: int):
        d = external_dir() / self.source
        d.mkdir(parents=True, exist_ok=True)
        return d / f"CIK{int(cik):010d}.json"

    def fetch_facts(self, cik: int, *, force: bool = False) -> dict:
        """Company facts JSON for a CIK (cached to data/external/sec_edgar)."""
        path = self._cache_path(cik)
        if path.exists() and not force:
            return json.loads(path.read_text(encoding="utf-8"))
        url = self.BASE.format(cik=int(cik))
        r = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=self.timeout)
        r.raise_for_status()
        facts = r.json()
        path.write_text(json.dumps(facts), encoding="utf-8")
        return facts

    @staticmethod
    def concept_observations(
        facts: dict, concept: str, *, unit: str = "USD", taxonomy: str = "us-gaap"
    ) -> pd.DataFrame:
        """Parse one XBRL concept into a point-in-time frame (sorted by filing date).

        Columns: period_end, filed, value, form, fy, fp. Entries without an ``end``
        or ``filed`` are skipped (never fabricated).
        """
        try:
            entries = facts["facts"][taxonomy][concept]["units"][unit]
        except KeyError:
            return pd.DataFrame(columns=_FACT_COLUMNS)
        rows = []
        for e in entries:
            if not e.get("end") or not e.get("filed"):
                continue
            rows.append(
                {
                    "period_end": pd.to_datetime(e["end"]),
                    "filed": pd.to_datetime(e["filed"]),
                    "value": float(e["val"]),
                    "form": e.get("form", ""),
                    "fy": e.get("fy"),
                    "fp": e.get("fp"),
                }
            )
        if not rows:
            return pd.DataFrame(columns=_FACT_COLUMNS)
        return pd.DataFrame(rows).sort_values(["filed", "period_end"]).reset_index(drop=True)


def fundamental_as_of(obs: pd.DataFrame, date) -> float:
    """Latest filed value visible on ``date`` (most recent ``period_end`` among rows
    with ``filed <= date``). NaN if nothing was filed yet — never back-filled."""
    if obs.empty:
        return float("nan")
    d = to_ts(date)
    visible = obs[pd.to_datetime(obs["filed"]) <= d]
    if visible.empty:
        return float("nan")
    return float(visible.sort_values("period_end").iloc[-1]["value"])


class EdinetConnector:
    """EDINET (JP disclosures) — the document-discovery layer (requires a key).

    EDINET API v2 lists the documents submitted on a date; full financials require
    a further step (download each ``docID``'s ZIP and parse its XBRL). This
    connector implements the discovery endpoint (key-gated) and parses the metadata
    list; XBRL extraction is left as a documented next step. Set ``EDINET_API_KEY``.
    """

    source = "edinet"
    BASE = "https://api.edinet-fsa.go.jp/api/v2/documents.json"

    def __init__(self, api_key: str | None = None, *, timeout: float = 30.0):
        self.api_key = api_key or env("EDINET_API_KEY")
        self.timeout = timeout

    @staticmethod
    def parse_documents(payload: dict) -> pd.DataFrame:
        """Parse the ``results`` list of an EDINET documents.json payload."""
        results = (payload or {}).get("results", [])
        if not results:
            return pd.DataFrame(
                columns=["docID", "filerName", "secCode", "docTypeCode", "periodEnd"]
            )
        keep = ["docID", "filerName", "secCode", "docTypeCode", "periodEnd", "submitDateTime"]
        return pd.DataFrame(results)[[c for c in keep if any(c in r for r in results)]]

    def list_documents(self, date) -> pd.DataFrame:
        """Documents submitted on ``date`` (type=2 = metadata + results)."""
        import requests

        if not self.api_key:
            raise RuntimeError("EDINET_API_KEY not set (free key from EDINET API v2 registration)")
        params = {"date": pd.Timestamp(date).strftime("%Y-%m-%d"), "type": 2}
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        r = requests.get(self.BASE, params=params, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        return self.parse_documents(r.json())
