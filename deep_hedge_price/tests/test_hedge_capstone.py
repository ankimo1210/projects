import numpy as np

from deep_hedge_price.hedge_capstone import synthetic_hedge_capstone


def test_capstone_uses_common_paths_and_reports_economic_metrics():
    result = synthetic_hedge_capstone(n_paths=500, n_steps=10, seed=7)
    assert np.array_equal(result.path_ids, np.arange(500))
    assert set(result.pnl) == {"no hedge", "delta", "delta-gamma", "no-trade"}
    for strategy, values in result.pnl.items():
        assert values.shape == result.path_ids.shape
        assert {"mean_pnl", "hedging_rmse", "var95", "cvar95", "turnover"} <= result.metrics[
            strategy
        ].keys()
    assert result.metrics["delta"]["hedging_rmse"] < result.metrics["no hedge"]["hedging_rmse"]
    assert (
        result.metrics["delta-gamma"]["hedging_rmse"] < result.metrics["no hedge"]["hedging_rmse"]
    )


def test_real_phase1_positions_can_be_compared_without_fabricating_a_deep_label():
    positions = np.zeros((200, 8))
    result = synthetic_hedge_capstone(
        n_paths=200,
        n_steps=8,
        seed=2,
        deep_policy_positions=positions,
    )
    assert "deep-policy" in result.pnl
    np.testing.assert_allclose(result.pnl["deep-policy"], result.pnl["no hedge"])
