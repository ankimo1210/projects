import numpy as np
import pandas as pd
import pytest

from quantcurve.cleaning import clean_market_data
from quantcurve.config import Config
from quantcurve.io import load_market_data


def test_one_audit_row_per_observation(raw, clean):
    f, audit = clean
    assert len(audit) == len(raw)
    assert audit.obs_id.tolist() == raw.obs_id.tolist()
    assert set(audit.action) <= {"keep", "correct", "downweight", "exclude"}
    assert audit.reason.str.len().min() > 0
    assert (audit.loc[audit.action == "exclude", "weight"] == 0).all()


def test_latest_valid_duplicate_and_staleness(raw, clean):
    f, a = clean
    assert f.instrument_id.is_unique
    assert len(a[a.reason.str.contains("duplicate instrument_id")]) == 7
    assert len(a[a.reason.str.contains("stale observation")]) == 5
    assert f.loc[f.instrument_id == "INS0001", "obs_id"].iloc[0] == "OBS0001"


def test_missing_quotes_recovered_without_discard(raw, clean):
    f, a = clean
    missing = raw.quote_value.isna()
    assert missing.sum() == 4
    assert (a.loc[missing, "action"] != "exclude").all()
    assert a.loc[missing, "reason"].str.contains("missing quote recovered").all()
    np.testing.assert_allclose(a.loc[missing, "normalized_quote"],
                               (a.loc[missing, "normalized_bid"] + a.loc[missing, "normalized_ask"]) / 2)


def test_inversions_are_swapped_and_logged(raw, clean):
    _, a = clean
    inverted = raw.bid > raw.ask
    assert inverted.sum() == 4
    assert a.loc[inverted, "reason"].str.contains("inverted bid/ask swapped").all()
    assert (a.loc[inverted, "normalized_bid"] <= a.loc[inverted, "normalized_ask"]).all()


def test_inferred_units_have_independent_evidence(clean):
    _, a = clean
    for oid in ("OBS0001", "OBS0088", "OBS0092", "OBS0094"):
        row = a[a.obs_id == oid].iloc[0]
        assert "mislabelled rate units" in row.reason
        assert row.normalized_quote == pytest.approx(row.quote_value)
    for oid in ("OBS0129", "OBS0134", "OBS0148"):
        row = a[a.obs_id == oid].iloc[0]
        assert "price-per-face unit mismatch" in row.reason
        assert row.normalized_quote == pytest.approx(row.quote_value * 100)


@pytest.mark.parametrize("unit,multiplier", [("DECIMAL", .01), ("BPS", 100.0)])
def test_explicit_rate_unit_conversion(raw, unit, multiplier):
    f = raw.copy()
    i = f.index[f.obs_id == "OBS0002"][0]
    expected = f.loc[i, "quote_value"] * .01
    f.loc[i, ["quote_value", "bid", "ask"]] *= multiplier
    f.loc[i, "quote_unit"] = unit
    _, audit = clean_market_data(f, "2026-01-15")
    assert audit.loc[i, "normalized_quote"] == pytest.approx(expected)


def test_valid_negative_and_small_rates_are_not_forced_positive(raw):
    f = raw.copy()
    m = (f.instrument_type == "deposit") & (f.maturity_years == .25)
    f.loc[m, ["quote_value", "bid", "ask"]] = [-.01, -.011, -.009]
    _, audit = clean_market_data(f, "2026-01-15")
    assert np.allclose(audit.loc[m, "normalized_quote"], -.0001)
    assert not audit.loc[m, "reason"].str.contains("mislabelled").any()


@pytest.mark.parametrize("field,value,reason", [
    ("maturity_years", np.nan, "maturity_years"),
    ("timestamp", "2030-01-01T00:00:00Z", "after valuation"),
    ("payment_frequency", 1.5, "integer"),
    ("currency", "EUR", "currency"),
    ("liquidity_score", 2.0, "liquidity_score"),
    ("quote_unit", "UNKNOWN", "quote_unit"),
])
def test_bad_fields_are_excluded_and_audited(raw, field, value, reason):
    f = raw.copy()
    f[field] = f[field].astype(object)
    i = f.index[f.obs_id == "OBS0002"][0]
    f.loc[i, field] = value
    _, a = clean_market_data(f, "2026-01-15")
    assert a.loc[i, "action"] == "exclude"
    assert reason in a.loc[i, "reason"]


def test_unrecoverable_missing_quote_excluded(raw):
    f = raw.copy()
    i = f.index[f.obs_id == "OBS0002"][0]
    f.loc[i, ["quote_value", "bid", "ask"]] = np.nan
    _, a = clean_market_data(f, "2026-01-15")
    assert a.loc[i, "action"] == "exclude"
    assert "recoverable" in a.loc[i, "reason"]


def test_malformed_numeric_is_not_silently_coerced(raw, tmp_path):
    f = raw.copy()
    f.quote_value = f.quote_value.astype(object)
    i = f.index[f.obs_id == "OBS0002"][0]
    f.loc[i, "quote_value"] = "not-a-number"
    path = tmp_path / "malformed.csv"
    f.to_csv(path, index=False)
    _, a = clean_market_data(load_market_data(path), "2026-01-15")
    assert "not-a-number" in a.loc[i, "reason"]
    assert "numeric coercion" in a.loc[i, "reason"]


def test_shuffling_does_not_change_clean_instruments(raw, clean):
    shuffled, _ = clean_market_data(raw.sample(frac=1, random_state=11).reset_index(drop=True), "2026-01-15")
    assert shuffled.instrument_id.tolist() == clean[0].instrument_id.tolist()
    np.testing.assert_allclose(shuffled.normalized_quote, clean[0].normalized_quote, rtol=0, atol=0)


def test_insufficient_data_has_actionable_error(raw):
    with pytest.raises(ValueError, match="insufficient usable data"):
        clean_market_data(raw.iloc[:3], "2026-01-15")


@pytest.mark.parametrize("kwargs", [{"grid_rows": 100}, {"huber_threshold": 0}, {"smoothing": -1}, {"removal_trials": 0}])
def test_configuration_rejects_invalid_limits(kwargs):
    with pytest.raises(ValueError):
        Config(**kwargs)
