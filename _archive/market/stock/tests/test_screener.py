import pandas as pd
from stockkit.analysis import screener as sc


def test_pe_below_rule():
    rule = sc.pe_below(15)
    assert rule({"pe": 10.0}, None) is True
    assert rule({"pe": 20.0}, None) is False
    assert rule({"pe": None}, None) is False
    assert rule({}, None) is False


def test_roe_above_rule():
    rule = sc.roe_above(0.1)
    assert rule({"roe": 0.2}, None) is True
    assert rule({"roe": 0.05}, None) is False
    assert rule({"roe": None}, None) is False


def test_above_sma_rule():
    idx = pd.date_range("2020-01-01", periods=5, freq="D")
    rising = pd.DataFrame({"close": [1, 2, 3, 4, 5]}, index=idx, dtype=float)
    rule = sc.above_sma(window=3)
    assert rule({}, rising) == True  # last close 5 > sma(3)=4  # noqa: E712
    assert rule({}, pd.DataFrame()) is False  # empty prices -> False


def test_rsi_between_full_range_true_and_empty_false():
    idx = pd.date_range("2020-01-01", periods=8, freq="D")
    mixed = pd.DataFrame({"close": [1, 2, 1, 3, 2, 4, 3, 5]}, index=idx, dtype=float)
    assert sc.rsi_between(-1, 101)(None, mixed) == True  # any finite RSI is in range  # noqa: E712
    assert sc.rsi_between(30, 70)(None, pd.DataFrame()) is False


def test_screen_filters_and_is_exception_safe(monkeypatch):
    idx = pd.date_range("2020-01-01", periods=3, freq="D")
    snaps = {
        "GOOD": {"symbol": "GOOD", "pe": 10.0},
        "BAD": {"symbol": "BAD", "pe": 30.0},
    }
    monkeypatch.setattr(sc.fundamental, "snapshot", lambda s: snaps[s])
    monkeypatch.setattr(
        sc, "get_prices", lambda s, period="1y": pd.DataFrame({"close": [1, 2, 3]}, index=idx)
    )

    out = sc.screen(["GOOD", "BAD"], [sc.pe_below(15)])
    assert list(out.index) == ["GOOD"]

    # a rule that raises is caught -> symbol excluded, no crash
    def boom(_snap, _prices):
        raise RuntimeError("boom")

    out2 = sc.screen(["GOOD", "BAD"], [boom])
    assert out2.empty
