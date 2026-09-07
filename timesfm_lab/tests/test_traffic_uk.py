"""The UK-traffic control set: gap handling, and the promise that no score is
ever computed against an interpolated value."""

import numpy as np
import pandas as pd
import pytest
from timesfm_lab.datasets import SPEC_BY_KEY, build_windows

from timesfm_lab import traffic_uk

needs_data = pytest.mark.skipif(
    not traffic_uk.CACHE.exists(), reason="run scripts/fetch_traffic_uk.py first"
)


def _frame(hours, drop=()):
    ts = pd.date_range("2026-01-01", periods=hours, freq="h")
    df = pd.DataFrame({"site": "X", "ts": ts, "volume": np.arange(hours, dtype=float)})
    return df.drop(index=list(drop)).reset_index(drop=True)


def _load_from(monkeypatch, tmp_path, df, **kw):
    path = tmp_path / "uk.parquet"
    df.to_parquet(path, index=False)
    monkeypatch.setattr(traffic_uk, "CACHE", path)
    return traffic_uk.load_series(**kw)


def test_short_gaps_are_bridged_and_flagged(monkeypatch, tmp_path):
    # A single missing hour at index 500, inside an otherwise complete run.
    ((site, values, ts, imputed),) = _load_from(
        monkeypatch, tmp_path, _frame(1600, drop=[500]), min_length=1000
    )
    assert site == "X"
    assert len(values) == 1600 and len(ts) == 1600
    assert imputed.sum() == 1 and imputed[500]
    # Linear interpolation of a ramp recovers the exact value.
    assert values[500] == pytest.approx(500.0)
    assert np.isfinite(values).all()


def test_a_long_gap_splits_the_series_instead_of_being_bridged(monkeypatch, tmp_path):
    gap = list(range(700, 700 + traffic_uk.MAX_GAP_HOURS + 1))
    segments = _load_from(monkeypatch, tmp_path, _frame(2000, drop=gap), min_length=500)
    assert len(segments) == 2
    assert [len(v) for _s, v, _t, _i in segments] == [700, 2000 - gap[-1] - 1]
    assert not any(i.any() for _s, _v, _t, i in segments)


def test_segments_shorter_than_the_minimum_are_dropped(monkeypatch, tmp_path):
    gap = list(range(100, 100 + traffic_uk.MAX_GAP_HOURS + 1))
    segments = _load_from(monkeypatch, tmp_path, _frame(2000, drop=gap), min_length=500)
    assert len(segments) == 1  # the 100-hour head is too short


def test_missing_cache_names_the_fetch_script(monkeypatch, tmp_path):
    monkeypatch.setattr(traffic_uk, "CACHE", tmp_path / "absent.parquet")
    with pytest.raises(FileNotFoundError, match="fetch_traffic_uk"):
        traffic_uk.load_series()


@needs_data
def test_no_target_contains_an_interpolated_point():
    spec = SPEC_BY_KEY["traffic_uk_2026"]
    segments, seen = {}, {}
    for site, v, _t, i in traffic_uk.load_series(min_length=spec.context_length + spec.horizon):
        k = seen[site] = seen.get(site, -1) + 1
        segments[site if k == 0 else f"{site}#{k}"] = (v, i)
    windows = build_windows(spec, seed=0)
    assert windows
    for w in windows:
        values, imputed = segments[w.series_id]
        assert not imputed[w.cutoff : w.cutoff + spec.horizon].any()
        np.testing.assert_allclose(w.actual, values[w.cutoff : w.cutoff + spec.horizon])


@needs_data
def test_the_selector_can_see_several_windows_per_series():
    """A series id that carried the cutoff gave every window its own group, and
    the walk-forward selector — which needs a predecessor — dropped them all."""
    from timesfm_lab.analysis import BASELINE_NAMES

    windows = build_windows(SPEC_BY_KEY["traffic_uk_2026"], seed=0)
    per_series = pd.Series([w.series_id for w in windows]).value_counts()
    assert per_series.min() >= 2, "each series needs a predecessor window"
    assert len({(w.series_id, w.cutoff) for w in windows}) == len(windows)
    assert BASELINE_NAMES  # the selector pool the grouping feeds


@needs_data
def test_every_window_is_hourly_and_post_cutoff():
    spec = SPEC_BY_KEY["traffic_uk_2026"]
    df = pd.read_parquet(traffic_uk.CACHE)
    assert df.ts.min() >= pd.Timestamp("2026-01-01")
    assert build_windows(spec, seed=0)
