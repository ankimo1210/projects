from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from quantcurve.cleaning import CleaningConfig, clean_market_data
from synthetic import synthetic_frame

VAL = date(2026, 1, 15)


def _audit(frame: pd.DataFrame, **cfg):
    res = clean_market_data(frame, VAL, CleaningConfig(**cfg))
    return res, res.audit.set_index("obs_id")


def test_clean_frame_passes_unchanged(clean_frame):
    res, audit = _audit(clean_frame)
    assert (audit["action"] == "keep").all()
    assert len(res.instruments) == len(clean_frame)
    assert audit["normalized_quote"].notna().all()


def test_scale_defect_rate_corrected(clean_frame):
    f = clean_frame.copy()
    i = f.index[f["instrument_type"] == "ois_swap"][3]
    for col in ("quote_value", "bid", "ask"):
        f.loc[i, col] = f.loc[i, col] / 100.0
    res, audit = _audit(f)
    row = audit.loc[f.loc[i, "obs_id"]]
    assert row["action"] == "correct"
    assert "scale defect" in row["reason"]
    assert row["normalized_quote"] == pytest.approx(clean_frame.loc[i, "quote_value"])


def test_scale_defect_bond_price_corrected(clean_frame):
    f = clean_frame.copy()
    i = f.index[f["instrument_type"] == "bond"][2]
    for col in ("quote_value", "bid", "ask"):
        f.loc[i, col] = f.loc[i, col] / 100.0
    _, audit = _audit(f)
    row = audit.loc[f.loc[i, "obs_id"]]
    assert row["action"] == "correct" and "price scale defect" in row["reason"]
    assert row["normalized_quote"] == pytest.approx(clean_frame.loc[i, "quote_value"])


def test_units_decimal_and_bp_normalised(clean_frame):
    f = clean_frame.copy()
    i, j = f.index[f["instrument_type"] == "deposit"][:2]
    for col in ("quote_value", "bid", "ask"):
        f.loc[i, col] = f.loc[i, col] / 100.0
        f.loc[j, col] = f.loc[j, col] * 100.0
    f.loc[i, "quote_unit"] = "DECIMAL"
    f.loc[j, "quote_unit"] = "BASIS_POINTS"
    _, audit = _audit(f)
    assert audit.loc[f.loc[i, "obs_id"], "normalized_quote"] == pytest.approx(clean_frame.loc[i, "quote_value"])
    assert audit.loc[f.loc[j, "obs_id"], "normalized_quote"] == pytest.approx(clean_frame.loc[j, "quote_value"])
    assert audit.loc[f.loc[i, "obs_id"], "action"] == "correct"


def test_missing_quote_uses_mid_and_missing_everything_excluded(clean_frame):
    f = clean_frame.copy()
    i, j = f.index[f["instrument_type"] == "ois_swap"][:2]
    f.loc[i, "quote_value"] = np.nan
    f.loc[j, ["quote_value", "bid", "ask"]] = np.nan
    _, audit = _audit(f)
    assert audit.loc[f.loc[i, "obs_id"], "action"] == "correct"
    assert audit.loc[f.loc[i, "obs_id"], "normalized_quote"] == pytest.approx(0.5 * (f.loc[i, "bid"] + f.loc[i, "ask"]))
    assert audit.loc[f.loc[j, "obs_id"], "action"] == "exclude"
    assert audit.loc[f.loc[j, "obs_id"], "weight"] == 0.0


def test_crossed_bid_ask_downweighted(clean_frame):
    f = clean_frame.copy()
    i = f.index[f["instrument_type"] == "ois_swap"][5]
    f.loc[i, ["bid", "ask"]] = f.loc[i, ["ask", "bid"]].values
    res, audit = _audit(f)
    assert audit.loc[f.loc[i, "obs_id"], "action"] == "downweight"
    assert "crossed" in audit.loc[f.loc[i, "obs_id"], "reason"]
    row = res.instruments.set_index("obs_id").loc[f.loc[i, "obs_id"]]
    assert row["rule_factor"] == pytest.approx(0.5)
    assert row["half_spread_norm"] > 0


def test_duplicates_resolved_to_fresh_in_market_quote(clean_frame):
    f = clean_frame.copy()
    i = f.index[f["instrument_type"] == "deposit"][0]
    dup = f.loc[[i]].copy()
    dup["obs_id"] = "DUP0001"
    dup["source"] = "BACKUP_FEED"
    dup["timestamp"] = "2026-01-15T14:00:00Z"
    dup["quote_value"] = dup["quote_value"] + 0.006  # outside bid/ask, stale
    f = pd.concat([dup, f], ignore_index=True)
    res, audit = _audit(f)
    assert audit.loc["DUP0001", "action"] == "exclude"
    assert "duplicate" in audit.loc["DUP0001", "reason"]
    assert audit.loc[clean_frame.loc[i, "obs_id"], "action"] == "keep"
    assert not res.instruments["instrument_id"].duplicated().any()


def test_stale_and_future_timestamps(clean_frame):
    f = clean_frame.copy()
    i, j = f.index[f["instrument_type"] == "ois_swap"][2:4]
    f.loc[i, "timestamp"] = "2026-01-02T15:00:00Z"
    f.loc[j, "timestamp"] = "2026-01-16T09:00:00Z"
    _, audit = _audit(f)
    assert audit.loc[f.loc[i, "obs_id"], "action"] == "exclude" and "stale" in audit.loc[f.loc[i, "obs_id"], "reason"]
    assert audit.loc[f.loc[j, "obs_id"], "action"] == "exclude" and "after" in audit.loc[f.loc[j, "obs_id"], "reason"]
    _, audit2 = _audit(f, max_stale_days=20)
    assert audit2.loc[f.loc[i, "obs_id"], "action"] == "keep"


def test_unparseable_timestamp_downweighted(clean_frame):
    f = clean_frame.copy()
    i = f.index[0]
    f.loc[i, "timestamp"] = "not-a-date"
    _, audit = _audit(f)
    assert audit.loc[f.loc[i, "obs_id"], "action"] == "downweight"


def test_cross_sectional_outlier_iterated(clean_frame):
    f = clean_frame.copy()
    idx = f.index[(f["instrument_type"] == "ois_swap") & (f["maturity_years"] == 5.0)]
    extra = f.loc[idx].copy()
    extra["obs_id"] = ["X1", "X2"]
    extra["instrument_id"] = ["IX1", "IX2"]
    f = pd.concat([f, extra], ignore_index=True)
    # four quotes at 5Y: two good, one gross (-170bp), one moderate (-16bp)
    f.loc[f["obs_id"] == "X1", ["quote_value", "bid", "ask"]] -= 1.70
    f.loc[f["obs_id"] == "X2", ["quote_value", "bid", "ask"]] -= 0.16
    _, audit = _audit(f)
    assert audit.loc["X1", "action"] == "exclude"
    assert audit.loc["X2", "action"] == "exclude"
    assert "pass 2" in audit.loc["X2", "reason"]
    good = [o for o in f.loc[idx, "obs_id"]]
    assert (audit.loc[good, "action"] == "keep").all()


def test_structural_rejections(clean_frame):
    f = clean_frame.copy()
    ids = f.index[:6]
    f.loc[ids[0], "currency"] = "EUR"
    f.loc[ids[1], "start_years"] = 1
    f.loc[ids[2], "quote_type"] = "clean_price"  # a deposit with a price quote type
    f.loc[ids[3], "maturity_years"] = -1
    f.loc[ids[4], "instrument_type"] = "future"
    bond = f.index[f["instrument_type"] == "bond"][0]
    f.loc[bond, "coupon_rate"] = np.nan
    _, audit = _audit(f)
    for i in list(ids[:5]) + [bond]:
        assert audit.loc[f.loc[i, "obs_id"], "action"] == "exclude", f.loc[i, "obs_id"]


def test_illiquid_quote_flagged_downweight(clean_frame):
    f = clean_frame.copy()
    i = f.index[f["instrument_type"] == "deposit"][1]
    f.loc[i, "liquidity_score"] = 0.1
    f.loc[i, "bid"] = f.loc[i, "quote_value"] - 0.04
    f.loc[i, "ask"] = f.loc[i, "quote_value"] + 0.04
    _, audit = _audit(f)
    assert audit.loc[f.loc[i, "obs_id"], "action"] == "downweight"
    assert "illiquid" in audit.loc[f.loc[i, "obs_id"], "reason"]


def test_audit_has_one_row_per_input_and_valid_actions(noisy_frame):
    res = clean_market_data(noisy_frame, VAL)
    assert len(res.audit) == len(noisy_frame)
    assert set(res.audit["action"]).issubset({"keep", "correct", "downweight", "exclude"})
    assert list(res.audit.columns[:6]) == ["obs_id", "instrument_id", "instrument_type", "maturity_years", "action", "normalized_quote"]


def test_tenor_clusters_group_same_tenor(clean_frame):
    res = clean_market_data(clean_frame, VAL)
    t = res.instruments
    for m, g in t[t["instrument_type"] == "ois_swap"].groupby("maturity"):
        assert g["tenor_cluster"].nunique() == 1
    # deposits and OIS at 1Y share a cluster
    one_year = t[np.isclose(t["maturity"], 1.0)]
    assert one_year["tenor_cluster"].nunique() == 1
