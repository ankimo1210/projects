"""Offline HTML export of an already computed synthetic research run."""

from __future__ import annotations

import importlib
import socket
import urllib.request
from dataclasses import replace
from html.parser import HTMLParser

import pandas as pd
import pytest
from market_research.services import build_demo_run


def _render(run):
    return importlib.import_module("market_research.reports").render_demo_report(run)


class _ElementNames(HTMLParser):
    def __init__(self):
        super().__init__()
        self.names = set()

    def handle_starttag(self, tag, attrs):
        self.names.add(tag)


def test_demo_report_is_deterministic_standalone_and_offline(monkeypatch):
    def blocked(*_args, **_kwargs):
        raise AssertionError("unexpected network access")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    run = build_demo_run()

    document = _render(run)

    assert document == _render(run)
    assert document.startswith("<!doctype html>")
    assert '<html lang="ja">' in document
    assert "<style>" in document and "--ground:#F0EEE6" in document
    elements = _ElementNames()
    elements.feed(document)
    assert {"link", "script", "iframe", "img"}.isdisjoint(elements.names)
    assert run.run_id in document and run.input_hash in document
    assert "synthetic-demo" in document
    assert "DEMO:ALPHA" in document and "DEMO:BETA" in document
    assert "5.00 bps" in document
    assert 'aria-label="累積資産の推移"' in document
    assert 'aria-label="ドローダウンの推移"' in document
    assert "1期遅れ" in document


def test_demo_report_calculates_return_and_peak_to_trough_drawdown():
    run = build_demo_run()
    equity = pd.Series(
        [1.0, 1.1, 0.99, 1.2] + [1.2] * (len(run.backtest.equity) - 4),
        index=run.backtest.equity.index,
    )
    changed = replace(run, backtest=replace(run.backtest, equity=equity))

    document = _render(changed)

    assert "+20.00%" in document
    assert "-10.00%" in document
    assert "1.2000" in document
    assert "0.9900" in document


def test_demo_report_escapes_untrusted_labels():
    run = build_demo_run()
    bar = replace(run.bars[0], provider='<img src=x onerror="alert(1)">')
    changed = replace(
        run,
        mode='<script>alert("mode")</script>',
        run_id='<script>alert("id")</script>',
        bars=(bar, *run.bars[1:]),
    )

    document = _render(changed)

    assert "&lt;script&gt;alert(&quot;mode&quot;)&lt;/script&gt;" in document
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in document
    assert "<script" not in document and "<img" not in document


def test_demo_report_rejects_incomplete_equity():
    run = build_demo_run()
    equity = run.backtest.equity.iloc[:-1]
    changed = replace(run, backtest=replace(run.backtest, equity=equity))

    with pytest.raises(ValueError, match="equity"):
        _render(changed)
