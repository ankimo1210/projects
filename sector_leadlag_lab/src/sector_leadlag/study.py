"""Every input of the study in one object (design §4), and the periods of design §3.2."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

from . import corrections, timing
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
    signal_jp: pd.DataFrame | None = None  # corrected data: the signal's Japanese side (C7, C3)
    us_breaks: pd.DataFrame | None = None  # corrected data: US days after a jump in the close (C1)
    corrections: tuple[dict, ...] = ()  # corrected data: every change the rules made

    def us_returns(self) -> pd.DataFrame:
        returns = timing.close_to_close(self.us_adj, self.us_days)
        if self.us_breaks is None:
            return returns
        hidden = self.us_breaks.reindex(
            index=returns.index, columns=returns.columns, fill_value=False
        )
        return returns.mask(hidden)

    def etf_c2c(self) -> pd.DataFrame:
        """The Japanese side of the signal: ETF adjusted close to adjusted close (design §6).

        On the corrected data it is the C7 return on the days the signal's rows may use (C3).
        """
        if self.signal_jp is not None:
            return self.signal_jp
        return timing.close_to_close(self.etf.adj_close, self.jp_days)


def build_panel(frames: dict, days: pd.DatetimeIndex, sector: pd.Series) -> Panel:
    """One frame per field with a column per entry of ``frames``, on ``days``."""
    stacked = pd.concat(frames, axis=1, sort=True)
    parts = {
        field: stacked.xs(field, axis=1, level=1).reindex(days, columns=list(frames))
        for field in FIELDS
    }
    return Panel(**parts, sector=sector)


def with_corrections(study: Study, us_close: pd.DataFrame, us_splits: pd.DataFrame) -> Study:
    """``study`` after the rules of PREREG §5; the US closes and splits are on the US days."""
    fixed = corrections.correct(study.etf, study.stocks, us_close, us_splits)
    return replace(
        study,
        etf=fixed.etf,
        stocks=fixed.stocks,
        signal_jp=fixed.signal,
        us_breaks=fixed.us_breaks,
        corrections=tuple(fixed.changes),
    )


def load_study(root: Path = RAW_ROOT, *, corrected: bool = False) -> Study:
    """Every input from the snapshot store; with ``corrected``, after the rules of PREREG §5."""
    listing = jpx.parse_listing(read_latest(root, "jpx", "data_j"))
    stored = set(indicators(root, "yf"))

    def prices(ticker: str) -> pd.DataFrame:
        return yf.parse_csv(read_latest(root, "yf", ticker))

    members = jpx.topix500(listing)
    have = [code for code in members.index if jpx.stock_ticker(code) in stored]
    if not have:
        raise FileNotFoundError(f"no TOPIX500 prices under {root}; run `sector-leadlag snapshot`")
    stock_frames = {code: prices(jpx.stock_ticker(code)) for code in have}
    volume = pd.concat(
        {code: frame["volume"] for code, frame in stock_frames.items()}, axis=1, sort=True
    )
    jp_days = timing.jp_trading_days(volume.loc[PANEL_START:])
    us_frames = {ticker: prices(ticker) for ticker in yf.US_SECTORS}
    us_days = timing.us_trading_days(us_frames["XLK"]["volume"].loc[PANEL_START:])
    us_adj = pd.concat({t: f["adj_close"] for t, f in us_frames.items()}, axis=1, sort=True)
    etf_frames = {k: prices(ticker) for k, ticker in enumerate(jpx.ETF_TICKERS, start=1)}
    study = Study(
        listing=listing,
        us_adj=us_adj.reindex(us_days),
        us_days=us_days,
        jp_days=jp_days,
        s_map=timing.last_us_before(jp_days, us_days),
        etf=build_panel(etf_frames, jp_days, pd.Series(list(SECTORS), index=list(SECTORS))),
        stocks=build_panel(stock_frames, jp_days, members.loc[have, "sector"].astype(int)),
        missing=tuple(code for code in members.index if code not in set(have)),
    )
    if not corrected:
        return study
    us = {
        field: pd.concat({t: f[field] for t, f in us_frames.items()}, axis=1, sort=True)
        for field in ("close", "splits")
    }
    return with_corrections(study, us["close"].reindex(us_days), us["splits"].reindex(us_days))
