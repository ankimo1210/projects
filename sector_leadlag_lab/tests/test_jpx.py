import io
from datetime import date

import pandas as pd
import pytest
from sector_leadlag.data.jpx import ETF_TICKERS, parse_listing, stock_ticker, topix500


def test_parse_keeps_stocks_with_a_sector_and_their_size(listing_bytes):
    content = listing_bytes(
        [
            ("1301", 1, "TOPIX Small 1"),
            ("7203", 6, "TOPIX Core30"),
            ("285A", 9, "TOPIX Mid400"),
            ("1617", 0, ""),
        ]
    )
    listing = parse_listing(content)
    assert listing.as_of == date(2026, 9, 30)
    assert list(listing.stocks.index) == ["1301", "7203", "285A"]
    assert listing.stocks.loc["7203", "sector"] == 6
    assert list(topix500(listing).index) == ["7203", "285A"]
    assert stock_ticker("285A") == "285A.T"


def test_etf_tickers_follow_the_sector_codes():
    assert (ETF_TICKERS[0], ETF_TICKERS[16], len(ETF_TICKERS)) == ("1617.T", "1633.T", 17)


def test_a_reshuffled_sector_code_is_refused(listing_bytes):
    frame = pd.read_excel(io.BytesIO(listing_bytes([("7203", 6, "TOPIX Core30")])), dtype=str)
    frame.loc[0, "17業種区分"] = "食品"
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False)
    with pytest.raises(ValueError, match="17-sector code 6"):
        parse_listing(buffer.getvalue())
