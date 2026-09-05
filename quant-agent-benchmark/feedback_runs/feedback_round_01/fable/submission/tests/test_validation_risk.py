from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from quantcurve.advanced import AdvancedConfig, fit_advanced
from quantcurve.baseline import fit_baseline
from quantcurve.cleaning import clean_market_data
from quantcurve.curve import PiecewiseLinearZeroCurve
from quantcurve.instruments import build_instrument
from quantcurve.pricing import analytic_dv01
from quantcurve.risk import compute_risk, risk_verification_summary
from quantcurve.validation import run_grouped_holdout, summarize_errors
from quantcurve.weights import base_scales

VAL = date(2026, 1, 15)


@pytest.fixture(scope="module")
def fitted(noisy_frame):
    res = clean_market_data(noisy_frame, VAL)
    tab = res.instruments
    insts = [build_instrument(r.instrument_id, r.instrument_type, r.maturity, r.quote, r.frequency, r.coupon_rate) for r in tab.itertuples()]
    flat = PiecewiseLinearZeroCurve(np.array([1.0]), np.array([0.02]))
    scale = base_scales(tab, insts, fit_baseline(insts, 1.0 / base_scales(tab, insts, flat) ** 2, tab["tenor_cluster"].to_numpy()))
    adv = fit_advanced(insts, scale, tab["instrument_type"].to_numpy(), tab["tenor_cluster"].to_numpy(), 30.0, AdvancedConfig(), lam=5.0, run_cv=False)
    return tab, insts, scale, adv


def test_summarize_errors_weighted():
    frame = pd.DataFrame({"instrument_type": ["a", "a", "b"], "err": [1.0, -3.0, 2.0], "precision": [1.0, 0.0, 4.0]})
    m = summarize_errors(frame, "err")
    assert m["overall"]["rmse_bp"] == pytest.approx(np.sqrt(14 / 3))
    assert m["overall"]["weighted_rmse_bp"] == pytest.approx(np.sqrt((1 + 16) / 5))
    assert m["by_type"]["a"]["max_abs_bp"] == 3.0


def test_grouped_holdout_runs_and_scores_every_usable_instrument_once(fitted):
    tab, insts, scale, adv = fitted
    cfg = AdvancedConfig()
    hold = run_grouped_holdout(insts, tab, scale, adv.fit.robust_factor, adv.fit.weights, tab["tenor_cluster"].to_numpy(), adv.folds, cfg, adv.lam, adv.power, adv.knots, 30.0)
    preds = hold.predictions
    assert not preds["instrument_id"].duplicated().any()
    anchors = set(tab["instrument_id"][adv.folds < 0])
    assert anchors.isdisjoint(set(preds["instrument_id"]))
    assert hold.metrics["advanced"]["overall"]["weighted_rmse_bp"] < 3.0
    assert hold.metrics["advanced"]["overall"]["rmse_bp"] <= hold.metrics["baseline"]["overall"]["rmse_bp"] * 1.5
    assert hold.temporal["available"] is False or hold.temporal["n_test"] > 0


def test_risk_table_and_verification(fitted):
    tab, insts, scale, adv = fitted
    risk = compute_risk(insts, adv.curve)
    assert len(risk) == len(insts)
    assert (risk["dv01"] > 0).all()
    np.testing.assert_allclose(risk["key_sum"], risk["dv01"], rtol=1e-4)
    np.testing.assert_allclose(risk["dv01"], risk["analytic_dv01"], rtol=1e-4)
    summary = risk_verification_summary(risk)
    assert summary["max_abs_rel_diff_fd_vs_analytic"] < 1e-4
    assert summary["max_abs_rel_diff_keysum_vs_dv01"] < 1e-4
    assert summary["all_receiver_dv01_positive"]
    # a 1M deposit only loads the 2Y key rate; a 30Y swap loads the 30Y key most
    dep = risk[(risk["instrument_type"] == "deposit")].iloc[0]
    assert dep["key_2y"] == pytest.approx(dep["dv01"], rel=1e-6) and abs(dep["key_10y"]) < 1e-9
    thirty = risk[(risk["instrument_type"] == "ois_swap") & np.isclose(risk["maturity_years"], 30.0)].iloc[0]
    assert thirty["key_30y"] > 0.5 * thirty["dv01"]


def test_deposit_dv01_closed_form():
    curve = PiecewiseLinearZeroCurve(np.array([1.0, 30.0]), np.array([0.02, 0.02]))
    inst = build_instrument("d", "deposit", 0.5, 0.0201)
    risk = compute_risk([inst], curve)
    expected = 1e6 * (1 + 0.0201 * 0.5) * 0.5 * np.exp(-0.02 * 0.5) * 1e-4
    assert risk["dv01"].iloc[0] == pytest.approx(expected, rel=1e-6)
    assert analytic_dv01(inst, curve) == pytest.approx(expected, rel=1e-12)
