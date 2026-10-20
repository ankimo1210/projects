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


def _store_closes(root, ticker, history, closes, dates=DATES):
    frame = history(dates, open_=closes, close=closes)
    content = yf.to_csv(frame, pd.Timestamp("2026-12-31").date())
    store_bytes(root, "yf", ticker, content, url=f"yfinance:{ticker}", filename=f"{ticker}.csv")


def test_the_corrected_study_applies_the_rules(tmp_path, listing_bytes, yf_history):
    rows = [("7203", 6, "TOPIX Core30")]
    store_bytes(tmp_path, "jpx", "data_j", listing_bytes(rows), url="u", filename="data_j.xlsx")
    for ticker in yf.US_SECTORS:
        _store_prices(tmp_path, ticker, yf_history, tz="America/New_York")
    for ticker in ETF_TICKERS[1:]:
        _store_prices(tmp_path, ticker, yf_history)
    _store_prices(tmp_path, ETF_TICKERS[0], yf_history, [*DATES[:2], *DATES[3:]])  # no 7th
    _store_closes(tmp_path, "7203.T", yf_history, [100.0, 100.0, 300.0, 300.0])  # no split
    record = load_study(tmp_path)
    study = load_study(tmp_path, corrected=True)
    assert record.signal_jp is None and record.us_breaks is None and record.corrections == ()
    assert [(c["rule"], c["series"], c["date"]) for c in study.corrections] == [
        ("C1", "7203.T", "2026-01-07"),
        ("C3", "1617.T", "2026-01-07"),
    ]
    assert list(study.etf_c2c().index) == [pd.Timestamp(d) for d in (DATES[0], DATES[1], DATES[3])]
    assert study.stocks.breaks.loc["2026-01-07", "7203"]
    pd.testing.assert_frame_equal(study.us_returns(), record.us_returns())


def test_the_corrected_study_carries_its_etf_panel_and_hides_a_us_jump(
    tmp_path, listing_bytes, yf_history
):
    rows = [("7203", 6, "TOPIX Core30")]
    store_bytes(tmp_path, "jpx", "data_j", listing_bytes(rows), url="u", filename="data_j.xlsx")
    for ticker in yf.US_SECTORS:
        if ticker != "XLK":
            _store_prices(tmp_path, ticker, yf_history, tz="America/New_York")
    _store_closes(tmp_path, "XLK", yf_history, [100.0, 100.0, 300.0, 300.0])  # no split
    for ticker in [*ETF_TICKERS, "7203.T"]:
        _store_prices(tmp_path, ticker, yf_history)
    record = load_study(tmp_path)
    study = load_study(tmp_path, corrected=True)
    assert [(c["rule"], c["kind"], c["series"], c["date"]) for c in study.corrections] == [
        ("C1", "us", "XLK", "2026-01-07")
    ]
    assert record.etf.breaks is None
    assert study.etf.breaks is not None and not study.etf.breaks.to_numpy().any()
    assert study.us_breaks.to_numpy().sum() == 1 and study.us_breaks.loc["2026-01-07", "XLK"]
    assert record.us_returns().loc["2026-01-07", "XLK"] == 2.0
    hidden = study.us_returns()
    assert pd.isna(hidden.loc["2026-01-07", "XLK"])
    assert hidden.loc["2026-01-08", "XLK"] == 0.0
    pd.testing.assert_frame_equal(
        hidden.drop(columns="XLK"), record.us_returns().drop(columns="XLK")
    )
