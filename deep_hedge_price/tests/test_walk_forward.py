import numpy as np
import torch

from deep_hedge_price.walk_forward import (
    SequenceForecaster,
    block_bootstrap_metric_ci,
    ewma_forecast,
    fit_garch11,
    fit_regularized_linear,
    fit_sequence_forecaster,
    forecast_metrics,
    garch11_aggregate_forecast,
    garch11_variance_forecast,
    har_features,
    persistence_forecast,
)


def test_classical_baselines_and_har_are_well_defined():
    values = 0.04 + 0.01 * np.sin(np.arange(80) / 8)
    assert persistence_forecast(values).shape == values.shape
    assert ewma_forecast(values).shape == values.shape
    returns = 0.01 * np.sin(np.arange(80) / 8)
    garch = garch11_variance_forecast(
        returns,
        omega=1e-6,
        alpha=0.08,
        beta=0.90,
        initial_variance=1e-4,
    )
    assert garch.shape == returns.shape
    assert np.all(garch > 0.0)
    features, targets = har_features(np.log(values))
    model = fit_regularized_linear(features, targets)
    assert model.predict(features).shape == targets.shape


def test_garch_is_fit_on_the_supplied_window_and_aggregates_horizons():
    rng = np.random.default_rng(8)
    returns = rng.normal(0.0, 0.012, size=160)
    fitted = fit_garch11(returns[:120])
    assert fitted.omega > 0.0
    assert 0.0 <= fitted.alpha < 1.0
    assert 0.0 <= fitted.beta < 1.0
    assert fitted.alpha + fitted.beta < 1.0
    aggregate = garch11_aggregate_forecast(
        1.2e-4,
        horizon=5,
        omega=fitted.omega,
        alpha=fitted.alpha,
        beta=fitted.beta,
    )
    assert aggregate > 1.2e-4


def test_all_small_challengers_share_sequence_interface():
    torch.manual_seed(3)
    sequences = torch.randn(12, 24)
    targets = sequences[:, -4:].mean(dim=1)
    for kind in ("harnet", "tcn", "lstm", "transformer"):
        model = SequenceForecaster(kind, hidden=8)
        before = torch.mean((model(sequences) - targets) ** 2).item()
        history = fit_sequence_forecaster(model, sequences, targets, epochs=3)
        assert len(history) == 3
        assert np.isfinite(before)
        assert model(sequences).shape == targets.shape
        if kind == "transformer":
            assert model.last_attention is not None
            assert model.last_attention.shape[-2:] == (24, 24)


def test_qlike_and_block_bootstrap_ci():
    actual = np.linspace(0.02, 0.08, 80)
    predicted = actual * 1.05
    metrics = forecast_metrics(actual, predicted)
    assert metrics["qlike"] > 0
    estimate, low, high = block_bootstrap_metric_ci(
        (predicted - actual) ** 2, block_size=5, n_bootstrap=80
    )
    assert low <= estimate <= high
