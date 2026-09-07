"""UK motorway sensor counts for 2026 — the control for Monash ``traffic_hourly``.

The weakest point in the contamination argument is that the tier that is
verified-trained happens to be sensor networks, while the tiers that cannot have
been trained on are synthetic series and market data.  Domain and exposure move
together, so the gradient has two explanations.

This dataset separates them.  National Highways' WebTRIS publishes per-site
traffic counts on English motorways with no key and no registration; taking 2026
gives a series with the *same* shape as Monash ``traffic_hourly`` — many
independent roadside sensors, hourly counts, a strong daily cycle and a weekday /
weekend split — that no 2023-cutoff corpus can contain.

If the traffic advantage survives here, it was the domain. If it collapses to the
level of the other unseen tiers, it was the exposure.
"""

from __future__ import annotations

import json
import time
import urllib.request

import numpy as np
import pandas as pd

from .paths import DATA_DIR

CACHE = DATA_DIR / "traffic_uk_2026.parquet"
SITES_URL = "https://webtris.highwaysengland.co.uk/api/v1.0/sites"
REPORT_URL = (
    "https://webtris.highwaysengland.co.uk/api/v1.0/reports/daily"
    "?sites={site}&start_date={start}&end_date={end}&page={page}&page_size={size}"
)
# The API answers 400 above roughly 20k rows per page, so six months of
# 15-minute data (17,280 rows) has to be paged rather than asked for at once.
PAGE_SIZE = 10000

# WebTRIS carries 2026 data through the end of June at the time of the run.
START, END = "01012026", "30062026"
N_SITES = 40
REQUEST_PAUSE_S = 0.4  # be a polite client of a free public API


def _get(url: str, timeout: int = 90) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:  # fixed https host
        return json.loads(r.read().decode("utf-8"))


def _fetch_rows(site: str) -> list[dict]:
    """All rows for one site over the window, following the pagination."""
    rows: list[dict] = []
    page = 1
    while True:
        payload = _get(REPORT_URL.format(site=site, start=START, end=END, page=page, size=PAGE_SIZE))
        got = payload.get("Rows") or []
        rows.extend(got)
        total = int(payload["Header"]["row_count"])
        if len(rows) >= total or not got:
            return rows
        page += 1
        time.sleep(REQUEST_PAUSE_S)


def active_sites(limit: int = N_SITES, seed: int = 0) -> list[str]:
    """A deterministic sample of active sites, spread across the site list."""
    sites = _get(SITES_URL)["sites"]
    active = sorted(s["Id"] for s in sites if s.get("Status") == "Active")
    if len(active) <= limit:
        return active
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(active), size=limit, replace=False)
    return [active[int(i)] for i in sorted(idx)]


def fetch(limit: int = N_SITES, seed: int = 0) -> pd.DataFrame:
    """Download 15-minute counts and fold them up to hourly totals."""
    frames = []
    for i, site in enumerate(active_sites(limit, seed), start=1):
        try:
            rows = _fetch_rows(site)
        except Exception as exc:  # one dead sensor must not stop the pull
            print(f"  site {site}: {type(exc).__name__}")
            continue
        if not rows:
            print(f"  site {site}: empty")
            continue
        df = pd.DataFrame(rows)
        vol = pd.to_numeric(df["Total Volume"], errors="coerce")
        ts = pd.to_datetime(df["Report Date"]).dt.normalize() + pd.to_timedelta(
            pd.to_numeric(df["Time Interval"], errors="coerce") * 15, unit="m"
        )
        hourly = (
            pd.DataFrame({"ts": ts.dt.floor("h"), "volume": vol})
            .dropna()
            .groupby("ts", as_index=False)
            .agg(volume=("volume", "sum"), n=("volume", "size"))
        )
        # A partial hour is a gap, not a low-traffic hour; drop it rather than
        # letting a missing quarter read as a 25% traffic drop.
        hourly = hourly[hourly.n == 4].drop(columns="n")
        hourly["site"] = site
        frames.append(hourly)
        print(f"  site {site}: {len(hourly)} hours  ({i} done)")
        time.sleep(REQUEST_PAUSE_S)

    out = pd.concat(frames, ignore_index=True)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(CACHE, index=False)
    return out


MAX_GAP_HOURS = 6


def load_series(
    min_length: int = 1400,
) -> list[tuple[str, np.ndarray, np.ndarray, np.ndarray]]:
    """Hourly series per site as ``(site, values, timestamps, imputed_mask)``.

    The feed drops 0.7-0.9% of hours, in network-wide outages of one to six
    hours, and those scattered gaps cut the longest uninterrupted run down to
    about 900 hours — too short for the 1,024-point context that makes this
    comparable to Monash ``traffic_hourly``.

    So gaps of at most ``MAX_GAP_HOURS`` are interpolated and *flagged*. The
    flag is what makes this honest: the window builder refuses any window whose
    held-out target contains an interpolated point, so no score is ever computed
    against a number this module invented. Longer gaps are never bridged; they
    split the series instead.
    """
    if not CACHE.exists():
        raise FileNotFoundError(f"{CACHE} missing; run scripts/fetch_traffic_uk.py first")
    df = pd.read_parquet(CACHE)
    out = []
    for site, g in df.groupby("site", sort=True):
        g = g.sort_values("ts")
        full = pd.date_range(g.ts.min(), g.ts.max(), freq="h")
        v = g.set_index("ts").volume.reindex(full)
        missing = v.isna().to_numpy()

        # Split on any gap longer than MAX_GAP_HOURS; bridge the rest.
        long_gap = np.zeros(len(full), dtype=bool)
        idx = np.where(missing)[0]
        if idx.size:
            for block in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1):
                if len(block) > MAX_GAP_HOURS:
                    long_gap[block] = True

        filled = v.interpolate(method="time", limit=MAX_GAP_HOURS, limit_area="inside")
        segment_id = np.cumsum(long_gap)
        for seg in np.unique(segment_id):
            sel = (segment_id == seg) & ~long_gap
            if sel.sum() < min_length:
                continue
            vals = filled.to_numpy()[sel]
            if not np.isfinite(vals).all():
                continue
            out.append(
                (str(site), vals.astype(float), full.to_numpy()[sel], missing[sel])
            )
    return out
