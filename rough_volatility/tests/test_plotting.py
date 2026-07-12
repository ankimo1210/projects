"""Smoke and export tests for the static visualization suite."""

from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from rough_volatility.config import ProjectConfig
from rough_volatility.experiments import run_all
from rough_volatility.plotting import (
    CHART_CONTRACTS,
    generate_static_figures,
    save_figure,
    thin,
)


def _tiny_config() -> ProjectConfig:
    base = ProjectConfig(profile="plot-test", seed=1210)
    return replace(
        base,
        fbm=replace(
            base.fbm,
            h_values=(0.1, 0.5),
            n_steps=96,
            n_paths=8,
            n_display_paths=2,
            n_lags=7,
        ),
        hurst=replace(
            base.hurst,
            h_values=(0.1, 0.5),
            sample_sizes=(64, 96),
            n_replications=3,
            n_lags=7,
        ),
        ou=replace(base.ou, n_steps=96, n_paths=5, burn_in_steps=24),
        bergomi=replace(
            base.bergomi,
            n_steps=20,
            n_paths=300,
            chunk_size=150,
            keep_paths=4,
            h_grid=(0.1, 0.5),
        ),
        options=replace(
            base.options,
            maturities=(0.25, 0.5, 1.0),
            n_strikes=7,
            skew_maturity_steps=16,
        ),
        hawkes=replace(
            base.hawkes,
            horizon=40.0,
            target_rate=2.0,
            max_events=2000,
            intensity_grid_points=100,
        ),
        microstructure=replace(base.microstructure, rv_window=5, intensity_window=5),
        noise=replace(
            base.noise,
            n_steps=128,
            n_replications=3,
            noise_stds=(0.0, 0.1),
            strides=(1, 2),
            estimators=("variogram",),
        ),
    )


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> tuple[list[Path], Path]:
    root = tmp_path_factory.mktemp("plot-artifacts")
    config = _tiny_config()
    manifest = run_all(config, root, force=True)
    paths = generate_static_figures(config, root, manifest)
    return paths, root


def test_chart_map_covers_required_static_narrative() -> None:
    assert len(CHART_CONTRACTS) >= 22
    assert {
        "fbm_paths",
        "hurst_bias",
        "ou_vs_fou",
        "iv_smiles",
        "skew_scaling",
        "hawkes_events",
        "noise_bias",
    } <= set(CHART_CONTRACTS)
    for contract in CHART_CONTRACTS.values():
        assert contract.question
        assert contract.takeaway
        assert contract.family
        assert contract.palette_policy


def test_thin_preserves_endpoints_and_bound() -> None:
    x = np.arange(10_000)
    y = x**2
    thinned_x, thinned_y = thin(x, y, max_points=250)
    assert len(thinned_x) <= 250
    assert thinned_x[0] == 0 and thinned_x[-1] == 9999
    np.testing.assert_array_equal(thinned_y, thinned_x**2)


def test_save_figure_writes_png_and_svg(tmp_path: Path) -> None:
    figure, axis = plt.subplots()
    axis.plot([0, 1], [0, 1])
    png, svg = save_figure(figure, tmp_path / "simple")
    plt.close(figure)
    assert png.exists() and png.stat().st_size > 1000
    assert svg.exists() and svg.stat().st_size > 1000


def test_generate_static_figures_exports_every_contract(generated: tuple[list[Path], Path]) -> None:
    paths, _ = generated
    assert len(paths) == 2 * len(CHART_CONTRACTS)
    assert all(path.exists() and path.stat().st_size > 1000 for path in paths)
    assert all(path.stat().st_size < 2_000_000 for path in paths if path.suffix == ".svg")
