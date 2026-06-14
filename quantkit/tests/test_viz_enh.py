"""Enhanced-visualization tests: tearsheet figures, multi-strategy dashboard,
factor-exposure heatmap, and an interactive parameter explorer.

As with the existing viz tests: no browser, no network. We assert on the Figure
objects (trace types, shapes, interactivity controls) and on the written HTML
(plotly.js embedded inline — never a CDN <script src> — and the expected sections).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from quantkit import backtest as B
from quantkit import visualization as V


def _result(seed=0, n=400, drift=0.0004):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    assets = ["A", "B", "C"]
    rets = pd.DataFrame(rng.normal(drift, 0.01, (n, 3)), index=idx, columns=assets)
    w = pd.DataFrame(1.0 / 3, index=idx, columns=assets)
    return B.run_backtest(w, rets, cost_model=B.CostModel(5, 2)), rets


# --- new tearsheet figures ----------------------------------------------------
def test_monthly_returns_heatmap_shape():
    res, _ = _result()
    fig = V.monthly_returns_heatmap(res)
    assert isinstance(fig, go.Figure)
    hm = fig.data[0]
    assert isinstance(hm, go.Heatmap)
    assert len(hm.x) == 12  # twelve calendar months on the x-axis


def test_rolling_volatility_is_a_line():
    res, _ = _result()
    fig = V.rolling_volatility(res, window=63)
    assert isinstance(fig, go.Figure)
    assert isinstance(fig.data[0], go.Scatter)


def test_risk_return_scatter_one_point_per_strategy():
    res, rets = _result()
    cmp = B.compare({"strategy": res, "equal_weight": B.buy_and_hold(rets)})
    fig = V.risk_return_scatter(cmp)
    pts = fig.data[0]
    assert len(pts.x) == 2 and len(pts.y) == 2  # vol/return point per strategy
    assert set(pts.text) == {"strategy", "equal_weight"}


# --- factor exposure heatmap --------------------------------------------------
def test_factor_heatmap_matches_frame():
    df = pd.DataFrame(
        np.arange(12).reshape(4, 3), index=list("ABCD"), columns=["PC1", "PC2", "PC3"]
    )
    fig = V.factor_heatmap(df, title="loadings")
    hm = fig.data[0]
    assert isinstance(hm, go.Heatmap)
    assert list(hm.x) == ["PC1", "PC2", "PC3"]
    assert list(hm.y) == list("ABCD")


# --- interactive parameter explorer ------------------------------------------
def test_parameter_explorer_single_metric_is_heatmap():
    grid = pd.DataFrame(
        [[0.5, 0.7], [0.9, 0.4]],
        index=pd.Index([10, 50], name="lookback"),
        columns=pd.Index([5, 21], name="skip"),
    )
    fig = V.parameter_explorer(grid)
    assert isinstance(fig.data[0], go.Heatmap)


def test_parameter_explorer_multi_metric_has_dropdown():
    grid = pd.DataFrame([[0.5, 0.7], [0.9, 0.4]], index=[10, 50], columns=[5, 21])
    grid.index.name, grid.columns.name = "lookback", "skip"
    fig = V.parameter_explorer({"sharpe": grid, "turnover": grid * 2})
    # interactivity: a dropdown (updatemenu) switches which metric is displayed
    assert fig.layout.updatemenus
    assert len(fig.data) == 2  # one heatmap per metric, toggled by the dropdown


# --- report builders: tearsheet + comparison dashboard ------------------------
def _assert_offline(html: str):
    assert 'src="https://cdn.plot.ly' not in html  # plotly.js inline, not from a CDN
    assert "Plotly.newPlot" in html
    assert len(html) > 1_000_000  # inline plotly bundle makes it large


def test_tearsheet_writes_self_contained_html(tmp_path):
    res, rets = _result()
    out = V.tearsheet(res, tmp_path / "ts.html", benchmark=B.buy_and_hold(rets), title="TS")
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    _assert_offline(html)
    for heading in ("TS", "Monthly returns", "Rolling volatility", "Drawdown"):
        assert heading in html


def test_comparison_dashboard_overlays_strategies(tmp_path):
    res, rets = _result()
    results = {"strategy": res, "equal_weight": B.buy_and_hold(rets)}
    out = V.comparison_dashboard(results, tmp_path / "dash.html", title="DASH")
    html = out.read_text(encoding="utf-8")
    _assert_offline(html)
    for heading in ("DASH", "Risk vs return", "Equity curves"):
        assert heading in html
