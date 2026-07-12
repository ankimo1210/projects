"""TCA tests (spec §21.8): signs, hand example, identity, risk metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from optimal_execution.evaluation import classical_world_run
from optimal_execution.impact import ImpactChannels, classical_execution
from optimal_execution.tca import (
    bootstrap_mean_ci,
    classical_tca,
    summarize,
    var_cvar,
)


def test_is_sign_hand_example(cfg):
    """Trades execute at step-START mids (documented convention): with mids
    [100, 99.9, 99.8], two lots of 500 hit 100 and 99.9 vs arrival 100:
    IS = 100*1000 - (500*100 + 500*99.9) = 50 currency, all timing cost."""
    c = cfg.with_overrides(
        {
            "initial_inventory": 1000,
            "n_decision_steps": 2,
            "fee_bps": 0.0,
            "spread_bps": 0.0,
            "impact": {"temporary_eta": 1e-12, "permanent_gamma": 0.0, "transient_eta": 0.0},
        }
    )
    q = np.array([[500.0, 500.0]])
    mids = np.array([[100.0, 99.9, 99.8]])
    # build exec prices equal to the mids at each step (impact ~ 0)
    res = classical_execution(
        c, q, mids, spreads=np.zeros((1, 2)), channels=ImpactChannels(False, False, False)
    )
    df = classical_tca(c, q, res, mids)
    assert df["is_total"].iloc[0] == pytest.approx(50.0, abs=1e-6)
    # all of it is timing cost (price drifted down while selling)
    assert df["comp_timing"].iloc[0] == pytest.approx(50.0, abs=1e-6)


def test_buy_sell_symmetry_flat_market(cfg):
    """In a flat market with symmetric costs, buy and sell IS coincide."""
    n = cfg.n_decision_steps
    q = np.full((1, n), cfg.initial_inventory / n)
    mids = np.full((1, n + 1), cfg.arrival_price)
    sell = classical_execution(cfg, q, mids)
    buy_cfg = cfg.with_overrides({"side": "buy"})
    buy = classical_execution(buy_cfg, q, mids)
    df_s = classical_tca(cfg, q, sell, mids)
    df_b = classical_tca(buy_cfg, q, buy, mids)
    assert df_s["is_total"].iloc[0] == pytest.approx(df_b["is_total"].iloc[0])
    assert df_s["is_total"].iloc[0] > 0


def test_components_sum_to_total(cfg):
    res = classical_world_run(cfg, purpose="tcatest", n_paths=64)
    for name, df in res.items():
        assert (df["residual"].abs() < 1e-6 * cfg.notional).all(), name


def test_var_cvar_and_quantiles():
    x = np.arange(1, 1001, dtype=float)  # 1..1000
    var95, cvar95 = var_cvar(x, 0.95)
    assert var95 == pytest.approx(np.quantile(x, 0.95))
    assert cvar95 > var95
    assert cvar95 == pytest.approx(x[x >= var95].mean())


def test_summarize_fields(cfg):
    df = pd.DataFrame(
        {
            "is_total": np.random.default_rng(0).normal(100, 30, 500),
            "is_bps": np.random.default_rng(0).normal(1.0, 0.3, 500),
            "executed": np.full(500, cfg.initial_inventory),
        }
    )
    s = summarize(df, cfg, "test_strat")
    for key in (
        "is_mean_bps",
        "is_median_bps",
        "is_std_bps",
        "is_rmse_bps",
        "q01_bps",
        "q99_bps",
        "var95_bps",
        "cvar99_bps",
        "worst_bps",
        "is_mean_ci_lo_bps",
        "turnover",
    ):
        assert key in s and np.isfinite(s[key]), key
    assert s["strategy_id"] == "test_strat"
    assert s["cvar99_bps"] >= s["var99_bps"]
    assert s["q01_bps"] <= s["is_median_bps"] <= s["q99_bps"]


def test_bootstrap_ci_contains_mean():
    x = np.random.default_rng(1).normal(5.0, 1.0, 400)
    lo, hi = bootstrap_mean_ci(x, seed=2)
    assert lo < x.mean() < hi
    assert hi - lo < 1.0  # reasonably tight at n=400


def test_immediate_dominated_by_twap_in_cost_mean(cfg):
    """Immediate pays far more impact; TWAP carries more variance."""
    res = classical_world_run(cfg, purpose="tcatest2", n_paths=256)
    imm, twap = res["immediate"], res["twap"]
    assert imm["is_bps"].mean() > twap["is_bps"].mean()
    assert imm["is_bps"].std() < twap["is_bps"].std()


def test_vwap_slippage_present_and_sane(cfg):
    res = classical_world_run(cfg, purpose="tcatest3", n_paths=64)
    for df in res.values():
        assert "vwap_slippage_bps" in df
        assert np.isfinite(df["vwap_slippage_bps"]).all()
