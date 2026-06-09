import pandas as pd

import strategy


def test_baseline_equal_weight_shape_and_values():
    idx = pd.date_range("2020-01-01", periods=10, freq="B")
    cols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    prices = pd.DataFrame(100.0, index=idx, columns=cols)
    w = strategy.generate_weights(prices)
    assert list(w.columns) == cols
    assert len(w) == len(idx)
    assert abs(w.iloc[0]["AAPL"] - 1.0 / 7.0) < 1e-9
    assert abs(w.iloc[0].sum() - 1.0) < 1e-9
