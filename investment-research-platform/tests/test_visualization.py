"""Visualization tests: figures build from platform objects, and the HTML report
is self-contained (offline) and contains the expected sections.

No network and no browser — we assert on the Figure objects and the written HTML
string (plotly.js embedded inline, headings present).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
from irp import backtest as B
from irp import visualization as V


def _result(seed=0, n=300):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    assets = ["A", "B", "C"]
    rets = pd.DataFrame(rng.normal(0.0004, 0.01, (n, 3)), index=idx, columns=assets)
    w = pd.DataFrame(1.0 / 3, index=idx, columns=assets)
    return B.run_backtest(w, rets, cost_model=B.CostModel(5, 2)), rets


def test_figure_builders_return_figures():
    res, rets = _result()
    results = {"strategy": res, "equal_weight": B.buy_and_hold(rets)}
    cmp = B.compare(results)
    assert isinstance(V.equity_curves(results), go.Figure)
    assert len(V.equity_curves(results).data) == 2  # one trace per strategy
    assert isinstance(V.drawdown(res), go.Figure)
    assert isinstance(V.returns_histogram(res), go.Figure)
    assert isinstance(V.rolling_sharpe(res), go.Figure)
    assert isinstance(V.metrics_table(cmp), go.Figure)
    ic = pd.Series({"ridge": 0.01, "rf": 0.02, "mean": np.nan})
    assert isinstance(V.ic_bar(ic), go.Figure)


def test_metrics_table_lists_all_strategies():
    res, rets = _result()
    cmp = B.compare({"s": res, "eq": B.buy_and_hold(rets)})
    fig = V.metrics_table(cmp)
    header = list(fig.data[0].header.values)  # plotly stores values as a tuple
    assert header == ["metric", "s", "eq"]


def test_strategy_report_writes_self_contained_html(tmp_path):
    res, rets = _result()
    results = {"momentum": res, "equal_weight": B.buy_and_hold(rets)}
    ic = pd.Series({"momentum": 0.015, "mean": np.nan})
    sweep = pd.DataFrame({"sharpe": [0.9, 0.7, 0.4]}, index=pd.Index([0, 10, 30], name="cost_bps"))
    out = V.strategy_report(
        results, tmp_path / "rep.html", title="Test report", ic=ic, cost_sweep=sweep
    )
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    # offline self-contained: plotly.js is embedded inline, never loaded from a CDN
    # (the inline bundle does contain a topojson URL string, so we only forbid a
    # <script src="...cdn..."> load, which is what "cdn" mode would emit).
    assert 'src="https://cdn.plot.ly' not in html
    assert "Plotly.newPlot" in html  # inline plotly bundle + plot call present
    for heading in (
        "Test report",
        "Summary metrics",
        "Equity curves",
        "Drawdown",
        "Information coefficient",
        "Cost sensitivity",
        "Notes &amp; caveats",
    ):
        assert heading in html
    assert len(html) > 1_000_000  # inline plotly bundle makes it large


def test_build_report_embeds_plotlyjs_once(tmp_path):
    fig1, fig2 = go.Figure(go.Scatter(y=[1, 2])), go.Figure(go.Bar(y=[3, 1]))
    sections = [
        {"heading": "One", "description": "first", "figures": [fig1]},
        {"heading": "Two", "figures": [fig2], "note": "a caveat"},
    ]
    out = V.build_report("Title", sections, tmp_path / "r.html")
    html = out.read_text(encoding="utf-8")
    # one plot div per figure; the inline plotly bundle (embedded once) makes it large
    assert html.count('class="plotly-graph-div"') == 2  # two plots
    assert len(html) > 1_000_000  # plotly.js embedded inline exactly once
    assert "a caveat" in html and "<h2>One</h2>" in html
