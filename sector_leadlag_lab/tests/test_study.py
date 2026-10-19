import pandas as pd
import pytest
from sector_leadlag.data import yf
from sector_leadlag.data.jpx import ETF_TICKERS
from sector_leadlag.data.store import store_bytes
from sector_leadlag.study import load_study

DATES = ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"]


def _store_prices(root, ticker, history, dates=DATES, **columns):
    frame = history(dates, open_=[100.0] * len(dates), close=[101.0] * len(dates), **columns)
    content = yf.to_csv(frame, pd.Timestamp("2026-12-31").date())
    store_bytes(root, "yf", ticker, content, url=f"yfinance:{ticker}", filename=f"{ticker}.csv")


def test_the_study_puts_every_series_on_the_japanese_days(tmp_path, listing_bytes, yf_history):
    rows = [("7203", 6, "TOPIX Core30"), ("6758", 9, "TOPIX Core30"), ("9999", 9, "TOPIX Small 1")]
    store_bytes(tmp_path, "jpx", "data_j", listing_bytes(rows), url="u", filename="data_j.xlsx")
    for ticker in yf.US_SECTORS:  # the 6th is a US holiday
        _store_prices(tmp_path, ticker, yf_history, [*DATES[:1], *DATES[2:]], tz="America/New_York")
    for ticker in ETF_TICKERS:
        _store_prices(tmp_path, ticker, yf_history)
    _store_prices(tmp_path, "7203.T", yf_history, volume=[10, 10, 0, 10])
    study = load_study(tmp_path)
    assert study.missing == ("6758",)  # 9999 is not in TOPIX500; 6758 has no prices
    assert list(study.stocks.close.columns) == ["7203"]
    assert study.stocks.sector.to_dict() == {"7203": 6}
    # the 7th: the only listed stock did not trade
    assert [str(d.date()) for d in study.jp_days] == ["2026-01-05", "2026-01-06", "2026-01-08"]
    assert list(study.etf.close.columns) == list(range(1, 18))
    assert study.s_map.to_dict() == {
        pd.Timestamp("2026-01-06"): pd.Timestamp("2026-01-05"),
        pd.Timestamp("2026-01-08"): pd.Timestamp("2026-01-07"),
    }
    assert study.us_returns().shape == (3, 11)


def test_a_store_without_stock_prices_is_refused(tmp_path, listing_bytes):
    store_bytes(
        tmp_path,
        "jpx",
        "data_j",
        listing_bytes([("7203", 6, "TOPIX Core30")]),
        url="u",
        filename="data_j.xlsx",
    )
    with pytest.raises(FileNotFoundError, match="sector-leadlag snapshot"):
        load_study(tmp_path)
