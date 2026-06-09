import numpy as np
import pandas as pd

import report


def test_build_report_is_self_contained_html():
    idx = pd.bdate_range("2018-01-01", periods=1500)
    cols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    rng = np.random.default_rng(2)
    prices = pd.DataFrame(
        np.cumprod(1 + rng.normal(0.0005, 0.02, size=(1500, len(cols))), axis=0) * 100,
        index=idx,
        columns=cols,
    )
    out = report.build_report(prices, generated="2026-06-09 00:00")

    assert out.lstrip().startswith("<!doctype html>")
    assert "</html>" in out
    # charts embedded inline (self-contained, no external refs)
    assert "data:image/png;base64," in out
    assert "http://" not in out and "https://" not in out
    # key sections present
    for marker in ("OOS test Sharpe", "Methodology", "Caveats", "Annual Sharpe"):
        assert marker in out
