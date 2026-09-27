import stockkit


def test_package_imports():
    assert hasattr(stockkit, "__version__")


def test_ohlcv_fixture(ohlcv):
    assert list(ohlcv.columns) == ["open", "high", "low", "close", "adj_close", "volume"]
    assert len(ohlcv) == 10
