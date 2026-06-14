"""Cache round-trip + data-quality diagnostics (which must NOT repair data)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from quantkit.data.cache import CacheManager
from quantkit.data.quality import assess


def _frame():
    idx = pd.bdate_range("2024-01-01", periods=10)
    return pd.DataFrame({"close": np.arange(10.0)}, index=idx)


def test_cache_roundtrip_and_ttl(tmp_path):
    cm = CacheManager(root=tmp_path)
    f = _frame()
    assert not cm.exists("processed", "src", "k")
    cm.write("processed", "src", "k", f)
    assert cm.exists("processed", "src", "k")
    back = cm.read("processed", "src", "k")
    # parquet doesn't round-trip the DatetimeIndex freq attribute (values match)
    pd.testing.assert_frame_equal(back, f, check_freq=False)
    # fresh within TTL, stale with TTL=0
    assert cm.is_fresh("processed", "src", "k", ttl_seconds=3600)
    assert not cm.is_fresh("processed", "src", "k", ttl_seconds=0)
    assert cm.is_fresh("processed", "src", "k", ttl_seconds=None)  # None = never expires


def test_quality_flags_missing_without_repair():
    f = _frame()
    f.iloc[3, 0] = np.nan
    rep = assess(f, required_columns=["close"])
    assert rep.missing_pct["close"] > 0
    assert any("missing" in w for w in rep.warnings)
    # assess must NOT have filled the NaN
    assert np.isnan(f.iloc[3, 0])


def test_quality_detects_gaps_and_dupes():
    idx = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-05"])  # missing 03,04
    f = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=idx)
    rep = assess(f, required_columns=["close"])
    assert rep.business_day_gaps == 2
    dup = pd.concat([f, f.iloc[[0]]])
    rep2 = assess(dup, required_columns=["close"])
    assert rep2.duplicate_index == 1
    assert not rep2.ok


def test_quality_missing_required_column():
    f = _frame().rename(columns={"close": "px"})
    rep = assess(f, required_columns=["close"])
    assert not rep.schema_ok
