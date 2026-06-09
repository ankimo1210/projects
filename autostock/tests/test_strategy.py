import pandas as pd

import strategy


def test_generate_weights_shape_and_valid_rows():
    """generate_weights returns a DataFrame with correct shape.

    The momentum-tilt strategy (LOOKBACK=126) needs >126 rows before weights
    are non-NaN; this test checks shape and that a sufficiently long price
    series produces valid (positive, sum-to-1) weights.
    """
    import numpy as np

    # Short series: shape must match even when all weights are NaN.
    idx_short = pd.date_range("2020-01-01", periods=10, freq="B")
    cols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    prices_short = pd.DataFrame(100.0, index=idx_short, columns=cols)
    w_short = strategy.generate_weights(prices_short)
    assert list(w_short.columns) == cols
    assert len(w_short) == len(idx_short)

    # Long series with a price trend: weights in the last row must be positive
    # and sum to 1.
    n = 200
    idx_long = pd.date_range("2020-01-01", periods=n, freq="B")
    rng = np.random.default_rng(42)
    prices_long = pd.DataFrame(
        np.cumprod(1 + rng.normal(0.001, 0.02, size=(n, len(cols))), axis=0) * 100,
        index=idx_long,
        columns=cols,
    )
    w_long = strategy.generate_weights(prices_long)
    assert list(w_long.columns) == cols
    assert len(w_long) == n
    last = w_long.iloc[-1]
    assert (last >= 0).all(), "weights must be non-negative"
    assert abs(last.sum() - 1.0) < 1e-9, "weights must sum to 1"
