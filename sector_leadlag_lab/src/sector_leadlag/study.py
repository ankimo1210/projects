"""Every input of the study in one object (design §4), and the periods of design §3.2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import timing
from .baskets import SECTORS, Panel
from .data import jpx, yf
from .data.store import RAW_ROOT, indicators, read_latest

PANEL_START = pd.Timestamp("2009-06-01")  # C_full (2010-2014) needs a little history before it
A = (pd.Timestamp("2015-01-05"), pd.Timestamp("2026-03-18"))
B = (pd.Timestamp("2026-03-19"), pd.Timestamp("2026-10-05"))
B1 = (pd.Timestamp("2026-03-19"), pd.Timestamp("2026-07-23"))
B2 = (pd.Timestamp("2026-07-24"), pd.Timestamp("2026-10-05"))
C = (pd.Timestamp("2026-10-06"), pd.Timestamp("2099-12-31"))
ORIGINAL = (pd.Timestamp("2015-01-01"), pd.Timestamp("2025-12-31"))  # the strategy paper's span
LONGER_SESSION = pd.Timestamp("2024-11-05")  # the TSE close moved to 15:30
FIELDS = ("open", "close", "adj_close", "volume", "dividends", "splits")


@dataclass(frozen=True)
class Study:
    listing: jpx.Listing
    us_adj: pd.DataFrame  # dividend-adjusted closes of the 11 US sector ETFs on US trading days
    us_days: pd.DatetimeIndex
    jp_days: pd.DatetimeIndex
    s_map: pd.Series  # each Japanese day d -> s(d), the last US trading day before it
    etf: Panel  # the 17 NEXT FUNDS ETFs on Japanese days; columns are the sector codes 1-17
    stocks: Panel  # the TOPIX500 names with stored prices; columns are their codes
    missing: tuple[str, ...]  # TOPIX500 codes without stored prices

    def us_returns(self) -> pd.DataFrame:
        return timing.close_to_close(self.us_adj, self.us_days)

    def etf_c2c(self) -> pd.DataFrame:
        """The Japanese side of the signal: ETF adjusted close to adjusted close (design §6)."""
        return timing.close_to_close(self.etf.adj_close, self.jp_days)


def build_panel(frames: dict, days: pd.DatetimeIndex, sector: pd.Series) -> Panel:
    """One frame per field with a column per entry of ``frames``, on ``days``."""
    stacked = pd.concat(frames, axis=1)
    parts = {
        field: stacked.xs(field, axis=1, level=1).reindex(days, columns=list(frames))
        for field in FIELDS
    }
    return Panel(**parts, sector=sector)


def load_study(root: Path = RAW_ROOT) -> Study:
    listing = jpx.parse_listing(read_latest(root, "jpx", "data_j"))
    stored = set(indicators(root, "yf"))

    def prices(ticker: str) -> pd.DataFrame:
        return yf.parse_csv(read_latest(root, "yf", ticker))

    members = jpx.topix500(listing)
    have = [code for code in members.index if jpx.stock_ticker(code) in stored]
    if not have:
        raise FileNotFoundError(f"no TOPIX500 prices under {root}; run `sector-leadlag snapshot`")
    stock_frames = {code: prices(jpx.stock_ticker(code)) for code in have}
    volume = pd.concat({code: frame["volume"] for code, frame in stock_frames.items()}, axis=1)
    jp_days = timing.jp_trading_days(volume.loc[PANEL_START:])
    us_frames = {ticker: prices(ticker) for ticker in yf.US_SECTORS}
    us_days = timing.us_trading_days(us_frames["XLK"]["volume"].loc[PANEL_START:])
    us_adj = pd.concat({t: f["adj_close"] for t, f in us_frames.items()}, axis=1)
    etf_frames = {k: prices(ticker) for k, ticker in enumerate(jpx.ETF_TICKERS, start=1)}
    return Study(
        listing=listing,
        us_adj=us_adj.reindex(us_days),
        us_days=us_days,
        jp_days=jp_days,
        s_map=timing.last_us_before(jp_days, us_days),
        etf=build_panel(etf_frames, jp_days, pd.Series(list(SECTORS), index=list(SECTORS))),
        stocks=build_panel(stock_frames, jp_days, members.loc[have, "sector"].astype(int)),
        missing=tuple(code for code in members.index if code not in set(have)),
    )
