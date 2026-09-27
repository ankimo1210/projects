"""A saved-data strategy comparison requires genuine observed snapshot history."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from market_research.contracts import Instrument, PriceBar
from market_research.storage import CacheKey, ResearchStore

ASSET = Instrument("XNYS", "IBM", "USD", "America/New_York")
START = datetime(2026, 9, 1, 21, tzinfo=UTC)


def _snapshots(store: ResearchStore, *, count: int = 14) -> tuple[str, ...]:
    ids = []
    for offset in range(count):
        observed = START + timedelta(days=offset)
        bar = PriceBar(
            instrument=ASSET,
            provider="fixture",
            provider_symbol="IBM",
            interval="1d",
            bar_start=observed - timedelta(hours=7),
            bar_end=observed - timedelta(hours=1),
            available_at=observed,
            observed_at=observed,
            close=100.0 + offset * 2.0,
            adjustment="raw",
            revision_id=str(offset),
        )
        key = CacheKey("fixture", "prices", ASSET.instrument_id, "1d", "USD", "raw")
        ids.append(
            store.save(
                key, f"fixture-{offset}".encode(), observed_at=observed, prices=(bar,)
            ).snapshot_id
        )
    return tuple(ids)


def test_compares_models_using_only_observed_saved_closes(tmp_path):
    from market_research.research.saved_strategy import compare_saved_strategies

    with ResearchStore(tmp_path) as store:
        ids = _snapshots(store)
        result = compare_saved_strategies(
            store,
            ids,
            instrument_id=ASSET.instrument_id,
            as_of=START + timedelta(days=14),
            train_size=5,
            test_size=1,
            commission_bps=5,
            slippage_bps=2,
        )

    assert set(result.backtests) == {"zero", "mean", "ridge", "tree", "buy_hold"}
    assert result.evaluation.snapshot_ids == ids
    assert result.evaluation.table.index.max() < START + timedelta(days=14)
    assert result.commission_bps == 5 and result.slippage_bps == 2


def test_rejects_future_or_repeated_saved_close(tmp_path):
    from market_research.research.saved_strategy import compare_saved_strategies

    with ResearchStore(tmp_path) as store:
        ids = _snapshots(store)
        kwargs = dict(
            instrument_id=ASSET.instrument_id,
            as_of=START + timedelta(days=10),
            train_size=5,
            test_size=1,
        )
        with pytest.raises(ValueError, match="future snapshot"):
            compare_saved_strategies(store, ids, **kwargs)
        with pytest.raises(ValueError, match=r"duplicate|unique"):
            compare_saved_strategies(
                store,
                (ids[0], ids[0], *ids[1:]),
                **{**kwargs, "as_of": START + timedelta(days=14)},
            )


def test_saved_strategy_screen_runs_offline_from_observed_snapshots(monkeypatch, tmp_path):
    import socket
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(
        socket,
        "create_connection",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network forbidden")),
    )
    monkeypatch.setenv("MARKET_RESEARCH_DATA_ROOT", str(tmp_path))
    bars = []
    ids = []
    with ResearchStore(tmp_path) as store:
        for offset in range(14):
            observed = START + timedelta(days=offset)
            bars.append(
                PriceBar(
                    instrument=ASSET,
                    provider="fixture",
                    provider_symbol="IBM",
                    interval="1d",
                    bar_start=observed - timedelta(hours=7),
                    bar_end=observed - timedelta(hours=1),
                    available_at=observed,
                    observed_at=observed,
                    close=100.0 + offset * 2.0,
                    adjustment="raw",
                    revision_id=str(offset),
                )
            )
            key = CacheKey("fixture", "prices", ASSET.instrument_id, "1d", "USD", "raw")
            ids.append(
                store.save(
                    key, f"fixture-{offset}".encode(), observed_at=observed, prices=tuple(bars)
                ).snapshot_id
            )
    path = Path(__file__).resolve().parents[1] / "app" / "main.py"
    app = AppTest.from_file(str(path), default_timeout=20).run()
    app.sidebar.radio[0].set_value("保存データ").run()
    as_of = next(item for item in app.sidebar.text_input if item.label.startswith("基準時刻"))
    as_of.set_value((START + timedelta(days=15)).isoformat()).run()
    price = next(item for item in app.sidebar.multiselect if item.label == "価格snapshot")
    price.set_value([ids[-1]]).run()
    strategy = next(
        item for item in app.sidebar.multiselect if item.label == "戦略用の履歴snapshot"
    )
    strategy.set_value(ids).run()
    assert not app.exception
    assert not any("戦略比較を計算できません" in item.value for item in app.warning)
    assert any("zero" in frame.value.columns for frame in app.dataframe)
    assert any("lag1" in item.value for item in app.caption)
