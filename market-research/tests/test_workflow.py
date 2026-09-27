import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from market_research.cli import main
from market_research.contracts import FundamentalObservation, Instrument, MacroObservation, PriceBar
from market_research.esri import CALENDAR_KEY
from market_research.macro import as_of
from market_research.prices import select_bars_as_of
from market_research.services import build_demo_run
from market_research.storage import CacheKey, ResearchStore
from streamlit.testing.v1 import AppTest


def test_demo_is_deterministic_and_explicitly_synthetic():
    one = build_demo_run()
    two = build_demo_run()
    assert one.run_id == two.run_id
    assert one.mode == "synthetic-demo"
    assert len(one.prices) == 60
    assert set(one.prices.columns) == {"DEMO:ALPHA", "DEMO:BETA"}
    assert one.prices.equals(two.prices)
    assert one.backtest.held_weights.iloc[1].tolist() == one.target_weights.iloc[0].tolist()


def test_demo_releases_are_gated_by_as_of_time():
    demo = build_demo_run()
    first, revision = demo.macro_observations
    assert as_of(demo.macro_observations, "DEMO_CPI", first.release_at)[0].value == 100.0
    assert as_of(demo.macro_observations, "DEMO_CPI", revision.release_at)[0].value == 101.0


def test_demo_does_not_use_network(monkeypatch):
    import socket
    import urllib.request

    def blocked(*_args, **_kwargs):
        raise AssertionError("unexpected network access")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    assert build_demo_run().mode == "synthetic-demo"


def test_cli_json_uses_same_run_and_no_account_fields(capsys):
    expected = build_demo_run()
    assert main(["demo", "--json"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["run_id"] == expected.run_id
    assert value["mode"] == "synthetic-demo"
    assert value["observations"] == 60
    assert value["assets"] == ["DEMO:ALPHA", "DEMO:BETA"]
    assert "holdings" not in value and "account" not in value


def test_streamlit_opens_seven_demo_views_without_exceptions(monkeypatch):
    import socket
    import urllib.request

    def blocked(*_args, **_kwargs):
        raise AssertionError("unexpected network access")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    path = Path(__file__).resolve().parents[1] / "app" / "main.py"
    app = AppTest.from_file(str(path), default_timeout=15).run()
    app.run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "市場概要",
        "銘柄・バスケット",
        "シグナル・スクリーナー",
        "戦略比較",
        "マクロと公表",
        "仮想配分・リスク",
        "品質・実行履歴",
    ]
    assert any("合成デモ" in item.value for item in app.caption)


def test_streamlit_has_separate_saved_data_mode_without_fetching(monkeypatch, tmp_path):
    import socket
    import urllib.request

    def blocked(*_args, **_kwargs):
        raise AssertionError("unexpected network access")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    monkeypatch.setenv("MARKET_RESEARCH_DATA_ROOT", str(tmp_path))
    path = Path(__file__).resolve().parents[1] / "app" / "main.py"
    app = AppTest.from_file(str(path), default_timeout=15).run()
    app.sidebar.radio[0].set_value("保存データ").run()
    assert not app.exception
    assert any("保存済み" in item.value for item in app.caption)


def test_streamlit_saved_snapshot_shows_research_tables_offline(monkeypatch, tmp_path):
    import socket
    import urllib.request

    def blocked(*_args, **_kwargs):
        raise AssertionError("unexpected network access")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    monkeypatch.setenv("MARKET_RESEARCH_DATA_ROOT", str(tmp_path))
    instrument = Instrument("XNAS", "AAPL", "USD", "America/New_York")
    decisions = tuple(datetime(2026, 9, 22 + offset, 21, tzinfo=UTC) for offset in range(3))
    bars = tuple(
        PriceBar(
            instrument,
            "yfinance",
            "1d",
            decision - timedelta(hours=7),
            decision - timedelta(hours=1),
            decision,
            decision,
            close,
            "raw",
            decision.isoformat(),
        )
        for decision, close in zip(decisions, (100, 105, 110), strict=True)
    )
    key = CacheKey("yfinance", "prices", instrument.instrument_id, "1d", "USD", "raw")
    benchmark = Instrument("XNYS", "SPY", "USD", "America/New_York")
    benchmark_bars = tuple(
        PriceBar(
            benchmark,
            "yfinance",
            "1d",
            decision - timedelta(hours=7),
            decision - timedelta(hours=1),
            decision,
            decision,
            close,
            "raw",
            decision.isoformat(),
        )
        for decision, close in zip(decisions, (300, 330, 310), strict=True)
    )
    fact = FundamentalObservation(
        320193,
        "us-gaap",
        "Assets",
        "USD",
        None,
        date(2025, 9, 27),
        date(2026, 9, 24),
        decisions[-1],
        None,
        100,
        "10-K",
        "accession",
    )
    fundamental_key = CacheKey(
        "sec",
        "fundamental",
        "CIK0000320193:us-gaap:Assets:USD:10-K",
        "annual",
        "USD",
        "none",
    )
    with ResearchStore(tmp_path) as store:
        saved = store.save(key, b"fixture", observed_at=decisions[-1], prices=bars)
        benchmark_saved = store.save(
            CacheKey("yfinance", "prices", benchmark.instrument_id, "1d", "USD", "raw"),
            b"benchmark",
            observed_at=decisions[-1],
            prices=benchmark_bars,
        )
        filing = store.save(
            fundamental_key,
            b"filing",
            observed_at=decisions[-1],
            fundamentals=(fact,),
        )
        macro_saved = store.save(
            CacheKey("alfred", "macro", "DEMO_CPI", "monthly", "index", "none"),
            b"macro",
            observed_at=decisions[-1],
            macro=(
                MacroObservation(
                    "DEMO_CPI",
                    date(2026, 8, 1),
                    decisions[-1],
                    103.0,
                    "alfred",
                    "initial",
                    unit="index",
                    frequency="monthly",
                ),
            ),
        )
        calendar_saved = store.save(
            CALENDAR_KEY,
            """<e-stat><class_1 name="四半期別ＧＤＰ速報">
            <class_2 name="2026年10-12月期"><class_3 name="2次速報"><class_5>
            <release_year>2027</release_year><release_month>3</release_month>
            <release_day>9</release_day><release_hour>8</release_hour>
            <release_minute>50</release_minute>
            </class_5></class_3></class_2></class_1></e-stat>""".encode(),
            observed_at=decisions[-1],
        )
    path = Path(__file__).resolve().parents[1] / "app" / "main.py"
    app = AppTest.from_file(str(path), default_timeout=15).run()
    app.sidebar.radio[0].set_value("保存データ").run()
    app.sidebar.multiselect[0].set_value([saved.snapshot_id]).run()
    assert not app.exception
    assert len(app.tabs) == 7
    assert any("retrospective" in item.value for item in app.caption)
    assert any("PAF=1" in item.value for item in app.caption)
    assert len(app.dataframe) >= 3
    assert any("momentum_rank" in frame.value.columns for frame in app.dataframe)
    assert any("相関の有効組数" in caption.value for caption in app.caption)
    assert any(metric.label == "年率ボラティリティ" for metric in app.metric)
    cash_floor = next(
        box for box in app.sidebar.number_input if box.label == "仮想配分の最低現金比率"
    )
    cash_floor.set_value(0.25).run()
    assert any("仮想リスクを計算できません" in item.value for item in app.warning)
    cash_floor.set_value(0.0).run()
    assert any(metric.label == "年率ボラティリティ" for metric in app.metric)
    macro_widget = next(box for box in app.sidebar.selectbox if box.label == "マクロsnapshot")
    macro_widget.set_value(macro_saved.snapshot_id).run()
    assert any(metric.label == "DEMO_CPI" for metric in app.metric)
    assert any(date(2026, 8, 1) in frame.value.index for frame in app.dataframe)
    calendar_widget = next(
        box for box in app.sidebar.selectbox if box.label == "公表calendar snapshot"
    )
    calendar_widget.set_value(calendar_saved.snapshot_id).run()
    assert any("公表予定" in caption.value for caption in app.caption)
    benchmark_widget = next(
        box for box in app.sidebar.selectbox if box.label == "比較対象の価格snapshot"
    )
    benchmark_widget.set_value(benchmark_saved.snapshot_id).run()
    assert any("比較対象" in item.value for item in app.caption)
    financial_widget = next(box for box in app.sidebar.selectbox if box.label == "財務snapshot")
    financial_widget.set_value(filing.snapshot_id).run()
    assert not any(
        ("XNAS:AAPL", "assets") in frame.value.index
        for frame in app.dataframe
        if hasattr(frame.value, "index")
    )
    confirmation = next(
        box
        for box in app.sidebar.text_input
        if "XNAS:AAPL" in box.label and "CIK0000320193" in box.label
    )
    confirmation.set_value("CIK0000320193").run()
    assert not app.exception
    assert any("研究run未保存" in item.value for item in app.caption)
    assert any(
        ("XNAS:AAPL", "assets") in frame.value.index
        for frame in app.dataframe
        if hasattr(frame.value, "index")
    )


def test_saved_macro_can_be_opened_without_any_price_snapshot(monkeypatch, tmp_path):
    import socket
    import urllib.request

    def blocked(*_args, **_kwargs):
        raise AssertionError("unexpected network access")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    monkeypatch.setenv("MARKET_RESEARCH_DATA_ROOT", str(tmp_path))
    observed = datetime(2026, 9, 25, 12, tzinfo=UTC)
    with ResearchStore(tmp_path) as store:
        key = CacheKey("alfred", "macro", "DEMO_CPI", "monthly", "index", "none")
        initial = MacroObservation(
            "DEMO_CPI",
            date(2026, 8, 1),
            observed,
            103.0,
            "alfred",
            "first",
            unit="index",
            frequency="monthly",
        )
        saved = store.save(key, b"macro-only", observed_at=observed, macro=(initial,))
        revised_at = observed + timedelta(days=1)
        revised = store.save(
            key,
            b"macro-revised",
            observed_at=revised_at,
            macro=(
                initial,
                MacroObservation(
                    "DEMO_CPI",
                    date(2026, 8, 1),
                    revised_at,
                    105.0,
                    "alfred",
                    "revised",
                    unit="index",
                    frequency="monthly",
                ),
            ),
        )
    original_snapshots = ResearchStore.snapshots
    monkeypatch.setattr(
        ResearchStore,
        "snapshots",
        lambda self, limit=50: original_snapshots(self, min(limit, 1)),
    )
    path = Path(__file__).resolve().parents[1] / "app" / "main.py"
    app = AppTest.from_file(str(path), default_timeout=15).run()
    app.sidebar.radio[0].set_value("保存データ").run()
    macro_widget = next(box for box in app.sidebar.selectbox if box.label == "マクロsnapshot")
    macro_widget.set_value(revised.snapshot_id).run()
    assert (
        saved.snapshot_id
        not in next(
            box for box in app.sidebar.selectbox if box.label == "比較する過去のマクロsnapshot"
        ).options
    )
    extra_ids = next(box for box in app.sidebar.text_area if "追加snapshot ID" in box.label)
    extra_ids.set_value(saved.snapshot_id).run()
    macro_widget = next(box for box in app.sidebar.selectbox if box.label == "マクロsnapshot")
    macro_widget.set_value(revised.snapshot_id).run()
    previous_widget = next(
        box for box in app.sidebar.selectbox if box.label == "比較する過去のマクロsnapshot"
    )
    previous_widget.set_value(saved.snapshot_id).run()
    assert not app.exception
    assert len(app.tabs) == 7
    assert any(metric.label == "DEMO_CPI" for metric in app.metric)
    assert any(
        frame.value.loc[date(2026, 8, 1), "revision"] == 2
        for frame in app.dataframe
        if "revision" in frame.value.columns
    )


def test_installed_market_research_command_runs_offline():
    import subprocess

    command = Path(__file__).resolve().parents[2] / ".venv/bin/market-research"
    result = subprocess.run(
        [str(command), "demo", "--json"], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout)["mode"] == "synthetic-demo"


def test_demo_decisions_only_use_bars_available_by_that_time():
    demo = build_demo_run()
    for position, decision_at in enumerate(demo.prices.index, start=1):
        known = select_bars_as_of(demo.bars, decision_at)
        assert len(known) == 2 * position
        assert max(bar.bar_end for bar in known) <= decision_at
