import numpy as np
import pandas as pd

import plot


def test_build_figure_has_four_panels():
    idx = pd.bdate_range("2018-01-01", periods=1500)
    cols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    rng = np.random.default_rng(1)
    prices = pd.DataFrame(
        np.cumprod(1 + rng.normal(0.0005, 0.02, size=(1500, len(cols))), axis=0) * 100,
        index=idx,
        columns=cols,
    )
    fig = plot.build_figure(prices)
    assert len(fig.axes) == 4  # renders all panels without error

    import matplotlib.pyplot as plt

    plt.close(fig)
