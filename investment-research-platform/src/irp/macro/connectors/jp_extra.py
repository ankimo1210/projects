"""BoJ and MoF connectors — Japanese macro/rates from public CSV (no key).

Both publish CSV; the parsers below are tolerant (find date-like first column,
numeric values) and tested offline against sample CSV. Formats can change, so the
download URL/series code is a parameter. No vintages -> ``vintage_available=False``.
"""

from __future__ import annotations

import io

import pandas as pd

from ..base import MacroConnector
from ..schema import MacroObservation


def _to_period(token: str) -> pd.Timestamp | None:
    ts = pd.to_datetime(str(token).strip(), errors="coerce")
    if pd.isna(ts):
        return None
    return ts + pd.offsets.MonthEnd(0) if ts.day == 1 else ts


class BoJConnector(MacroConnector):
    """Bank of Japan time-series (e.g. policy rate, monetary base). CSV by series code."""

    source = "boj"
    country = "JP"
    BASE = "https://www.stat-search.boj.or.jp/ssi/mtshtml/csv"

    @staticmethod
    def parse_csv(text: str) -> pd.DataFrame:
        """Rows whose first column is a date and second is numeric (skips headers)."""
        rows = []
        for line in io.StringIO(text):
            parts = [p.strip().strip('"') for p in line.split(",")]
            if len(parts) < 2:
                continue
            period = _to_period(parts[0])
            if period is None:
                continue
            try:
                val = float(parts[1].replace(",", ""))
            except ValueError:
                continue
            rows.append({"period": period, "value": val})
        return pd.DataFrame(rows)

    def _download(self, indicator, start, end, *, point_in_time, url=None, **_) -> pd.DataFrame:
        import requests

        if not url:
            raise RuntimeError(
                "boj: pass url= for the series CSV (BoJ Time-Series Data Search export)"
            )
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        return self.parse_csv(r.text)

    def to_observations(self, raw: pd.DataFrame, indicator, **_) -> list[MacroObservation]:
        return _frame_to_obs(raw, indicator, "JP", "BoJ", "https://www.stat-search.boj.or.jp/")


class MofConnector(MacroConnector):
    """Ministry of Finance JGB par-yield curve (jgbcm.csv): Date + tenor columns."""

    source = "mof"
    country = "JP"
    BASE = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcm.csv"

    @staticmethod
    def parse_csv(text: str, tenor: str = "10Y") -> pd.DataFrame:
        """Pick one tenor column from the JGB rate CSV (header row names the tenors)."""
        df = pd.read_csv(io.StringIO(text))
        date_col = df.columns[0]
        if tenor not in df.columns:
            raise KeyError(f"tenor {tenor!r} not in {list(df.columns)[1:]}")
        out = pd.DataFrame(
            {
                "period": pd.to_datetime(df[date_col], errors="coerce"),
                "value": pd.to_numeric(df[tenor], errors="coerce"),
            }
        )
        return out.dropna(subset=["period"])

    def _download(self, indicator, start, end, *, point_in_time, url=None, **_) -> pd.DataFrame:
        import requests

        r = requests.get(url or self.BASE, timeout=60)
        r.raise_for_status()
        return self.parse_csv(r.text, tenor=indicator or "10Y")

    def to_observations(self, raw: pd.DataFrame, indicator, **_) -> list[MacroObservation]:
        return _frame_to_obs(raw, indicator, "JP", "MoF", "https://www.mof.go.jp/")


def _frame_to_obs(raw, indicator, country, source, url) -> list[MacroObservation]:
    if raw is None or raw.empty:
        return []
    obs = []
    for _, row in raw.iterrows():
        val = row.get("value")
        if pd.isna(val):
            continue
        period = row["period"]
        obs.append(
            MacroObservation(
                indicator_name=indicator,
                country=country,
                period_start=period,
                period_end=period,
                release_date=period,
                value=float(val),
                source=source,
                source_url=url,
                vintage_available=False,
            )
        )
    return obs
