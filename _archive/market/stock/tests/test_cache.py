import pandas as pd


def _price_df():
    idx = pd.date_range("2020-01-01", periods=3, freq="D", name="date")
    return pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0],
            "high": [10.5, 11.5, 12.5],
            "low": [9.5, 10.5, 11.5],
            "close": [10.2, 11.2, 12.2],
            "adj_close": [10.2, 11.2, 12.2],
            "volume": [1000.0, 1100.0, 1200.0],
        },
        index=idx,
    )


def test_prices_roundtrip(temp_cache):
    n = temp_cache.upsert_prices("TEST", _price_df())
    assert n == 3
    out = temp_cache.read_prices("TEST")
    assert len(out) == 3
    assert out["close"].iloc[-1] == 12.2


def test_prices_upsert_is_idempotent(temp_cache):
    temp_cache.upsert_prices("TEST", _price_df())
    temp_cache.upsert_prices("TEST", _price_df())  # same PKs -> replace, not duplicate
    assert len(temp_cache.read_prices("TEST")) == 3


def test_prices_date_filter(temp_cache):
    temp_cache.upsert_prices("TEST", _price_df())
    out = temp_cache.read_prices("TEST", start="2020-01-02")
    assert len(out) == 2


def test_latest_cached_date(temp_cache):
    temp_cache.upsert_prices("TEST", _price_df())
    assert temp_cache.latest_cached_date("TEST") == pd.Timestamp("2020-01-03")
    assert temp_cache.latest_cached_date("MISSING") is None


def test_empty_upsert_writes_nothing(temp_cache):
    assert temp_cache.upsert_prices("TEST", pd.DataFrame()) == 0
    assert temp_cache.read_prices("TEST").empty


def test_macro_roundtrip(temp_cache):
    s = pd.Series(
        [1.0, 2.0, 3.0],
        index=pd.date_range("2020-01-01", periods=3, freq="MS"),
        name="CPIAUCSL",
    )
    assert temp_cache.upsert_macro("CPIAUCSL", s) == 3
    out = temp_cache.read_macro("CPIAUCSL")
    assert len(out) == 3
    assert out.iloc[-1] == 3.0
    assert temp_cache.latest_macro_date("CPIAUCSL") == pd.Timestamp("2020-03-01")
