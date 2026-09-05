from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from quantcurve.advanced import AdvancedConfig, fit_advanced, grouped_folds
from quantcurve.baseline import fit_baseline
from quantcurve.cleaning import clean_market_data
from quantcurve.curve import PiecewiseLinearZeroCurve
from quantcurve.instruments import build_instrument
from quantcurve.pricing import rate_residual
from quantcurve.weights import base_scales
from synthetic import synthetic_frame, true_zero

VAL = date(2026, 1, 15)


def _prepare(frame: pd.DataFrame):
    res = clean_market_data(frame, VAL)
    tab = res.instruments
    insts = [build_instrument(r.instrument_id, r.instrument_type, r.maturity, r.quote, r.frequency, r.coupon_rate) for r in tab.itertuples()]
    flat = PiecewiseLinearZeroCurve(np.array([1.0]), np.array([0.02]))
    prelim = fit_baseline(insts, 1.0 / base_scales(tab, insts, flat) ** 2, tab["tenor_cluster"].to_numpy())
    scale = base_scales(tab, insts, prelim)
    return tab, insts, scale


def test_baseline_reprices_rate_instruments_exactly(clean_frame):
    tab, insts, scale = _prepare(clean_frame)
    curve = fit_baseline(insts, 1.0 / scale**2, tab["tenor_cluster"].to_numpy())
    for inst in insts:
        if inst.is_rate:
            assert abs(rate_residual(inst, curve)) < 1e-9
    grid = np.array([0.25, 1.0, 5.0, 10.0, 30.0])
    np.testing.assert_allclose(curve.zero(grid), true_zero(grid), atol=2e-5)


def test_advanced_recovers_true_curve(clean_frame):
    tab, insts, scale = _prepare(clean_frame)
    types = tab["instrument_type"].to_numpy()
    cl = tab["tenor_cluster"].to_numpy()
    adv = fit_advanced(insts, scale, types, cl, 30.0, AdvancedConfig())
    grid = np.linspace(1 / 12, 30, 400)
    err_bp = (adv.curve.zero(grid) - true_zero(grid)) * 1e4
    assert np.sqrt(np.mean(err_bp**2)) < 1.0
    assert np.max(np.abs(err_bp)) < 3.0
    assert np.all(adv.curve.discount(grid) > 0)
    assert (adv.fit.robust_factor > 0).all()
    assert adv.cv is not None and len(adv.cv.table) == len(AdvancedConfig().lambda_grid)


def test_advanced_handles_negative_rates():
    frame = synthetic_frame(level=-0.012, noise_bp=0.0)
    tab, insts, scale = _prepare(frame)
    adv = fit_advanced(insts, scale, tab["instrument_type"].to_numpy(), tab["tenor_cluster"].to_numpy(), 30.0, AdvancedConfig(), lam=1.0, run_cv=False)
    grid = np.linspace(1 / 12, 30, 200)
    assert np.all(adv.curve.discount(grid) > 0)
    assert np.any(adv.curve.zero(grid) < 0)
    err_bp = (adv.curve.zero(grid) - true_zero(grid, -0.012)) * 1e4
    assert np.sqrt(np.mean(err_bp**2)) < 1.5


def test_robust_fit_rejects_isolated_outlier_and_keeps_consensus(noisy_frame):
    f = noisy_frame.copy()
    # a single liquid 9M deposit 16bp too high (the other 9M quote becomes illiquid)
    nine = f.index[(f["instrument_type"] == "deposit") & np.isclose(f["maturity_years"], 0.75)]
    f.loc[nine[0], ["quote_value", "bid", "ask"]] += 0.16
    f.loc[nine[1], "liquidity_score"] = 0.15
    f.loc[nine[1], "bid"] -= 0.04
    f.loc[nine[1], "ask"] += 0.04
    # a bond 5 points too rich
    bond = f.index[f["instrument_type"] == "bond"][4]
    f.loc[bond, ["quote_value", "bid", "ask"]] += 5.0
    # both 7Y OIS quotes 3bp high: concordant, must not be rejected wholesale
    seven = f.index[(f["instrument_type"] == "ois_swap") & np.isclose(f["maturity_years"], 7.0)]
    f.loc[seven, ["quote_value", "bid", "ask"]] += 0.03
    tab, insts, scale = _prepare(f)
    adv = fit_advanced(insts, scale, tab["instrument_type"].to_numpy(), tab["tenor_cluster"].to_numpy(), 30.0, AdvancedConfig())
    ids = tab["obs_id"].to_numpy()
    factor = dict(zip(ids, adv.fit.robust_factor))
    assert factor[f.loc[nine[0], "obs_id"]] == 0.0
    assert factor[f.loc[nine[1], "obs_id"]] > 0.5
    assert factor[f.loc[bond, "obs_id"]] == 0.0
    assert all(factor[f.loc[i, "obs_id"]] > 0 for i in seven)
    grid = np.linspace(1 / 12, 30, 300)
    err_bp = (adv.curve.zero(grid) - true_zero(grid)) * 1e4
    assert np.sqrt(np.mean(err_bp**2)) < 2.0


def test_grouped_folds_keep_clusters_together_and_anchors_in_train():
    cl = np.array([0, 0, 1, 1, 2, 3, 3, 4, 5, 5, 6])
    mat = np.array([0.1, 0.1, 1, 1, 2, 5, 5, 10, 20, 20, 30])
    folds = grouped_folds(cl, mat, 3)
    assert (folds[cl == 0] == -1).all() and (folds[cl == 6] == -1).all()
    for c in np.unique(cl):
        assert len(set(folds[cl == c])) == 1
    assert set(folds[(cl != 0) & (cl != 6)]) == {0, 1, 2}
