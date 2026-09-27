"""Historical research decisions only see snapshots already observed."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from market_research.backtest import run_prefix_strategy
from market_research.contracts import Instrument, PriceBar, PriceGap
from market_research.storage import CacheKey, ResearchStore

T1 = datetime(2026, 9, 24, 21, tzinfo=UTC)
T2 = datetime(2026, 9, 25, 21, tzinfo=UTC)
T3 = datetime(2026, 9, 28, 21, tzinfo=UTC)
IBM = Instrument("XNYS", "IBM", "USD", "America/New_York")
KEY = CacheKey("yfinance", "prices", IBM.instrument_id, "1d", "USD", "raw")


def _bar(instrument: Instrument, decision_at: datetime, close: float, revision: str) -> PriceBar:
    bar_end = decision_at - timedelta(hours=1)
    return PriceBar(
        instrument,
        "yfinance",
        "1d",
        bar_end - timedelta(hours=6),
        bar_end,
        decision_at,
        decision_at,
        close,
        "raw",
        revision,
    )


def test_future_correction_cannot_change_earlier_close_or_strategy_weight(tmp_path):
    from market_research.research.history import build_pit_close_frame

    with ResearchStore(tmp_path) as store:
        first = store.save(KEY, b"first", observed_at=T1, prices=(_bar(IBM, T1, 100, "v1"),))
        correction = PriceBar(
            IBM,
            "yfinance",
            "1d",
            T1 - timedelta(hours=7),
            T1 - timedelta(hours=1),
            T2,
            T2,
            900,
            "raw",
            "corrected",
        )
        second = store.save(
            KEY,
            b"second",
            observed_at=T2,
            prices=(correction, _bar(IBM, T2, 102, "v1")),
        )
        third = store.save(KEY, b"third", observed_at=T3, prices=(_bar(IBM, T3, 101, "v1"),))
        frame = build_pit_close_frame(
            store,
            {IBM.instrument_id: (first.snapshot_id, second.snapshot_id, third.snapshot_id)},
            (T1, T2, T3),
            currency="USD",
            adjustment="raw",
        )

    assert frame.index.equals(pd.DatetimeIndex((T1, T2, T3)))
    assert frame.columns.tolist() == ["XNYS:IBM"]
    assert frame["XNYS:IBM"].tolist() == [100, 102, 101]
    weights = run_prefix_strategy(
        frame, lambda prefix: pd.Series({"XNYS:IBM": prefix.iloc[-1, 0] / 100})
    )
    assert weights["XNYS:IBM"].tolist() == [1.0, 1.02, 1.01]


def test_old_bar_is_not_carried_into_a_new_decision(tmp_path):
    from market_research.research.history import build_pit_close_frame

    with ResearchStore(tmp_path) as store:
        saved = store.save(KEY, b"first", observed_at=T1, prices=(_bar(IBM, T1, 100, "v1"),))
        with pytest.raises(ValueError, match="new final close"):
            build_pit_close_frame(
                store,
                {IBM.instrument_id: (saved.snapshot_id,)},
                (T1, T2),
                currency="USD",
                adjustment="raw",
            )


def test_decision_times_must_be_aware_unique_and_ordered(tmp_path):
    from market_research.research.history import build_pit_close_frame

    with ResearchStore(tmp_path) as store:
        saved = store.save(KEY, b"first", observed_at=T1, prices=(_bar(IBM, T1, 100, "v1"),))
        selection = {IBM.instrument_id: (saved.snapshot_id,)}
        with pytest.raises(ValueError, match="unique and ordered"):
            build_pit_close_frame(store, selection, (T1, T1), currency="USD", adjustment="raw")
        with pytest.raises(ValueError, match="timezone-aware"):
            build_pit_close_frame(
                store,
                selection,
                (T1.replace(tzinfo=None),),
                currency="USD",
                adjustment="raw",
            )


@pytest.mark.parametrize("missing_kind", ["gap", "non_final"])
def test_gap_or_nonfinal_new_session_cannot_reuse_old_close(tmp_path, missing_kind):
    from market_research.research.history import build_pit_close_frame

    first_bar = _bar(IBM, T1, 100, "v1")
    with ResearchStore(tmp_path) as store:
        first = store.save(KEY, b"first", observed_at=T1, prices=(first_bar,))
        if missing_kind == "gap":
            gap = PriceGap(IBM, "yfinance", "IBM", "1d", T2.date(), T2, T2, "raw")
            second = store.save(KEY, b"gap", observed_at=T2, prices=(first_bar,), gaps=(gap,))
        else:
            unfinished = replace(
                _bar(IBM, T2, 101, "partial"), bar_end=T2 + timedelta(hours=1), is_final=False
            )
            second = store.save(KEY, b"partial", observed_at=T2, prices=(first_bar, unfinished))
        with pytest.raises(ValueError, match=missing_kind):
            build_pit_close_frame(
                store,
                {IBM.instrument_id: (first.snapshot_id, second.snapshot_id)},
                (T1, T2),
                currency="USD",
                adjustment="raw",
            )


def test_rejected_price_cannot_enter_point_in_time_return(tmp_path):
    from market_research.research.history import build_pit_close_frame

    bad_bar = replace(
        _bar(IBM, T2, 101, "bad"),
        quality="reject",
        quality_reasons=("manual_reject",),
    )
    with ResearchStore(tmp_path) as store:
        first = store.save(KEY, b"first", observed_at=T1, prices=(_bar(IBM, T1, 100, "v1"),))
        second = store.save(KEY, b"second", observed_at=T2, prices=(bad_bar,))
        with pytest.raises(ValueError, match="quality"):
            build_pit_close_frame(
                store,
                {IBM.instrument_id: (first.snapshot_id, second.snapshot_id)},
                (T1, T2),
                currency="USD",
                adjustment="raw",
            )


def test_provider_switch_cannot_splice_one_instrument_history(tmp_path):
    from market_research.research.history import build_pit_close_frame

    with ResearchStore(tmp_path) as store:
        first = store.save(KEY, b"first", observed_at=T1, prices=(_bar(IBM, T1, 100, "v1"),))
        second = store.save(
            replace(KEY, provider="stooq"),
            b"stooq",
            observed_at=T2,
            prices=(replace(_bar(IBM, T2, 102, "v1"), provider="stooq"),),
        )
        with pytest.raises(ValueError, match="provider"):
            build_pit_close_frame(
                store,
                {IBM.instrument_id: (first.snapshot_id, second.snapshot_id)},
                (T1, T2),
                currency="USD",
                adjustment="raw",
            )


def test_equal_time_snapshots_for_one_instrument_are_ambiguous(tmp_path):
    from market_research.research.history import build_pit_close_frame

    with ResearchStore(tmp_path) as store:
        first = store.save(KEY, b"first", observed_at=T1, prices=(_bar(IBM, T1, 100, "v1"),))
        second = store.save(KEY, b"second", observed_at=T1, prices=(_bar(IBM, T1, 101, "v2"),))
        with pytest.raises(ValueError, match="conflicting snapshots"):
            build_pit_close_frame(
                store,
                {IBM.instrument_id: (first.snapshot_id, second.snapshot_id)},
                (T1,),
                currency="USD",
                adjustment="raw",
            )


def test_two_assets_three_decisions_keep_literal_closes_in_column_order(tmp_path):
    from market_research.research.history import build_pit_close_frame

    msft = Instrument("XNAS", "MSFT", "USD", "America/New_York")
    expected = {"XNYS:IBM": (100, 102, 101), "XNAS:MSFT": (50, 52, 51)}
    with ResearchStore(tmp_path) as store:
        catalog = {}
        for instrument in (IBM, msft):
            key = CacheKey("yfinance", "prices", instrument.instrument_id, "1d", "USD", "raw")
            ids = []
            for decision, close in zip(
                (T1, T2, T3), expected[instrument.instrument_id], strict=True
            ):
                saved = store.save(
                    key,
                    f"{instrument.symbol}-{decision.isoformat()}".encode(),
                    observed_at=decision,
                    prices=(_bar(instrument, decision, close, "v1"),),
                )
                ids.append(saved.snapshot_id)
            catalog[instrument.instrument_id] = tuple(ids)
        frame = build_pit_close_frame(
            store, catalog, (T1, T2, T3), currency="USD", adjustment="raw"
        )
    assert frame.columns.tolist() == ["XNYS:IBM", "XNAS:MSFT"]
    assert frame.to_dict("list") == {
        "XNYS:IBM": [100, 102, 101],
        "XNAS:MSFT": [50, 52, 51],
    }


def test_future_only_and_wrong_price_contract_are_rejected(tmp_path):
    from market_research.research.history import build_pit_close_frame

    with ResearchStore(tmp_path) as store:
        future = store.save(KEY, b"future", observed_at=T2, prices=(_bar(IBM, T2, 102, "v1"),))
        with pytest.raises(ValueError, match="no snapshot available"):
            build_pit_close_frame(
                store,
                {IBM.instrument_id: (future.snapshot_id,)},
                (T1,),
                currency="USD",
                adjustment="raw",
            )
        with pytest.raises(ValueError, match="currency"):
            build_pit_close_frame(
                store,
                {IBM.instrument_id: (future.snapshot_id,)},
                (T2,),
                currency="JPY",
                adjustment="raw",
            )
        with pytest.raises(ValueError, match="adjustment"):
            build_pit_close_frame(
                store,
                {IBM.instrument_id: (future.snapshot_id,)},
                (T2,),
                currency="USD",
                adjustment="unknown",
            )
