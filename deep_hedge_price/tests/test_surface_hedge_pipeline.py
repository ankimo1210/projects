import numpy as np

from deep_hedge_price.surface_hedge_pipeline import run_synthetic_surface_hedge_pipeline


def test_surface_calibration_forecast_and_hedge_share_one_scenario():
    result = run_synthetic_surface_hedge_pipeline(seed=11, n_paths=300, n_steps=10)
    assert result.calibration.repricing_rmse < 1e-4
    assert result.forecast_variance > 0
    assert result.forecast_volatility == np.sqrt(result.forecast_variance)
    assert set(result.hedge.pnl) == {"no hedge", "delta", "delta-gamma", "no-trade"}
    assert all(values.shape == result.hedge.path_ids.shape for values in result.hedge.pnl.values())


def test_pipeline_is_seed_reproducible():
    first = run_synthetic_surface_hedge_pipeline(seed=5, n_paths=200, n_steps=8)
    second = run_synthetic_surface_hedge_pipeline(seed=5, n_paths=200, n_steps=8)
    np.testing.assert_array_equal(first.hedge.pnl["delta"], second.hedge.pnl["delta"])
    assert first.forecast_variance == second.forecast_variance
