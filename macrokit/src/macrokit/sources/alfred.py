"""FRED / ALFRED adapter.

ALFRED is the archival face of FRED: with `realtime_start`/`realtime_end` set to
a range, one observation date returns several rows, one per vintage, and
`realtime_start` is that vintage's release date. That is why US indicators get
`vintage_kind="actual"` while every Japanese source gets "snapshot".

FRED also mirrors BLS, BEA and Census, so CPI, PCE, GDP, NFP and JOLTS all
arrive here with revision history attached -- which is why this project does not
hold API keys for those three agencies.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime
from itertools import groupby

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..catalog import Indicator
from ..periods import period_end_for
from ..store import Observation

BASE = "https://api.stlouisfed.org/fred"
FAR_FUTURE = "9999-12-31"
_UNSET = object()


def _redact(url: httpx.URL) -> str:
    """``url`` with the ``api_key`` query parameter removed.

    Shared by ``_request`` and ``fetch_raw`` so their redaction can never drift
    apart: both must scrub the same key the same way, or one of them leaks it.
    """
    return str(url.copy_remove_param("api_key"))


class AlfredRequestError(RuntimeError):
    """A FRED/ALFRED HTTP request failed. Safe to print: never carries the key."""


class AlfredAdapter:
    source = "alfred"

    def __init__(
        self, api_key: str | None | object = _UNSET, *, client: httpx.Client | None = None
    ):
        # The sentinel distinguishes "caller passed nothing, read the env" from
        # "caller passed None on purpose", which is how the missing-key test
        # forces the error path even on a machine where FRED_API_KEY is set.
        self.api_key = os.environ.get("FRED_API_KEY") if api_key is _UNSET else api_key
        self._client = client

    def _require_key(self) -> str:
        if not self.api_key:
            raise RuntimeError("FRED_API_KEY is not set (free key from fred.stlouisfed.org)")
        return self.api_key

    def _get(self, path: str, params: dict) -> httpx.Response:
        client = self._client or httpx.Client(timeout=60.0)
        try:
            return self._request(client, path, params)
        finally:
            if self._client is None:
                client.close()

    # reraise=True: without it, tenacity wraps the final failure in RetryError
    # instead of propagating AlfredRequestError, which would both hide the
    # status code from a plain str(exc) and defeat the redaction below (the
    # exhausted-retries exception has to actually be ours for it to be safe).
    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
    )
    def _request(self, client: httpx.Client, path: str, params: dict) -> httpx.Response:
        response = client.get(f"{BASE}/{path}", params=params)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # httpx's own message embeds the full request URL, api_key and all,
            # and that survives on __cause__ through tenacity's retry wrapping --
            # a printed traceback would put the key on the terminal, in cron
            # logs, and in CI logs. Re-raise with a redacted URL instead of
            # letting the original propagate. We cannot chain the original as
            # __cause__ either: its own str() re-embeds the raw URL, so any
            # traceback that prints the chain leaks the key right back. `from
            # None` suppresses that implicit chain in the default traceback
            # output.
            raise AlfredRequestError(
                f"FRED request failed: {exc.response.status_code} {_redact(exc.request.url)}"
            ) from None
        return response

    def probe(self, indicator: Indicator) -> str | None:
        """Latest vintage date for the series, or None if it has never been revised.

        `series/vintagedates` omits release dates on which the values did not
        change, so a stable tail here means there is genuinely nothing new.
        """
        response = self._get(
            "series/vintagedates",
            {
                "series_id": indicator.source_ref["series_id"],
                "api_key": self._require_key(),
                "file_type": "json",
            },
        )
        dates = response.json().get("vintage_dates", [])
        return dates[-1] if dates else None

    def fetch_raw(self, indicator: Indicator, start: date) -> tuple[bytes, str, int]:
        """All vintages from ``start`` onward. Returns (content, url, status)."""
        response = self._get(
            "series/observations",
            {
                "series_id": indicator.source_ref["series_id"],
                "api_key": self._require_key(),
                "file_type": "json",
                "observation_start": start.isoformat(),
                "realtime_start": "1776-07-04",  # FRED's documented earliest realtime
                "realtime_end": FAR_FUTURE,
            },
        )
        # Redact by removing the parameter, not by cutting the string: this
        # preserves the rest of the request window (file_type, observation_start,
        # realtime_start/end) for provenance, and it cannot leak the key even if
        # api_key's position in the query string ever changes.
        return response.content, _redact(response.url), response.status_code

    def parse(
        self, indicator: Indicator, raw: bytes, *, ingested_at: datetime
    ) -> list[Observation]:
        """Turn one ``series/observations`` payload into one row per vintage.

        ``vintage_seq`` (assigned below) means "which release this is, 1 = first"
        only because ``fetch_raw`` currently requests the entire realtime window
        (``realtime_start=1776-07-04`` .. ``9999-12-31``). If a future caller
        narrows that window -- a natural optimisation once incremental fetching
        arrives -- ``seq=1`` would silently start meaning "first release inside
        the requested window" instead of "first release ever", with no error to
        signal the change.
        """
        payload = json.loads(raw)
        parsed = []
        for item in payload.get("observations", []):
            if item["value"] == ".":  # FRED's missing-value marker
                continue
            parsed.append(
                (
                    date.fromisoformat(item["date"]),
                    # ALFRED's realtime_start is a date with no time of day, so we
                    # map it to 00:00 UTC. US releases are typically ~8:30 ET
                    # (13:30 UTC), so this makes a vintage look knowable up to
                    # ~13.5 hours before it actually was -- in ET terms, from the
                    # evening before. Defensible for now (it never makes a
                    # revision *disappear*, only shifts as_of's granularity to
                    # the day), but the true publication time-of-day is not
                    # preserved anywhere in this table.
                    datetime.fromisoformat(item["realtime_start"]).replace(tzinfo=UTC),
                    float(item["value"]),
                )
            )

        rows: list[Observation] = []
        parsed.sort(key=lambda triple: (triple[0], triple[1]))
        for period_start, group in groupby(parsed, key=lambda triple: triple[0]):
            for seq, (_period, release_date, value) in enumerate(group, start=1):
                rows.append(
                    Observation(
                        indicator=indicator.name,
                        period_start=period_start,
                        period_end=period_end_for(period_start, indicator.freq),
                        release_date=release_date,
                        vintage_seq=seq,
                        value=value,
                        unit=indicator.unit,
                        sa=indicator.sa,
                        freq=indicator.freq,
                        source=self.source,
                        source_url=f"{BASE}/series/observations",
                        ingested_at=ingested_at,
                        vintage_kind="actual",
                    )
                )
        return rows
