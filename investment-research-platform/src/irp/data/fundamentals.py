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
        self.user_agent = user_agent or env("SEC_USER_AGENT") or "irp research (set SEC_USER_AGENT)"
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
