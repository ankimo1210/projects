"""Build and execution tests for the shared 26-section notebook."""

from dataclasses import replace
from pathlib import Path

import nbformat
import pytest
from rough_volatility.config import ProjectConfig, save_config
from rough_volatility.experiments import run_all
from rough_volatility.notebook import SECTIONS, build_notebook, execute_and_export_notebook


def _notebook_config() -> ProjectConfig:
    base = ProjectConfig(profile="notebook-test", seed=1210)
    return replace(
        base,
        fbm=replace(
            base.fbm, h_values=(0.1, 0.5), n_steps=96, n_paths=8, n_display_paths=2, n_lags=7
        ),
        hurst=replace(
            base.hurst, h_values=(0.1, 0.5), sample_sizes=(64, 96), n_replications=3, n_lags=7
        ),
        ou=replace(base.ou, n_steps=96, n_paths=5, burn_in_steps=24),
        bergomi=replace(
            base.bergomi, n_steps=20, n_paths=200, chunk_size=100, keep_paths=4, h_grid=(0.1, 0.5)
        ),
        options=replace(
            base.options, maturities=(0.25, 0.5, 1.0), n_strikes=7, skew_maturity_steps=16
        ),
        hawkes=replace(
            base.hawkes, horizon=40.0, target_rate=2.0, max_events=2000, intensity_grid_points=100
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


def test_built_notebook_has_shared_26_anchors(tmp_path: Path) -> None:
    config_path = save_config(_notebook_config(), tmp_path / "config.yaml")
    notebook_path = build_notebook(tmp_path, config_path)
    notebook = nbformat.read(notebook_path, as_version=4)
    assert len(SECTIONS) == 26
    markdown = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "markdown")
    for section in SECTIONS:
        assert f'id="{section.anchor}"' in markdown
    assert notebook.cells[0].cell_type == "code"
    assert "load_artifact_manifest" in notebook.cells[0].source
    assert "generate_static_figures" in notebook.cells[0].source


@pytest.mark.slow
def test_notebook_executes_and_exports_html(tmp_path: Path) -> None:
    config = _notebook_config()
    config_path = save_config(config, tmp_path / "config.yaml")
    run_all(config, tmp_path, force=True)
    notebook_path, html_path = execute_and_export_notebook(tmp_path, config_path, timeout=300)
    executed = nbformat.read(notebook_path, as_version=4)
    assert not [
        output
        for cell in executed.cells
        if cell.cell_type == "code"
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]
    assert html_path.exists() and html_path.stat().st_size > 100_000
    html = html_path.read_text(encoding="utf-8")
    for section in SECTIONS:
        assert section.anchor in html


def test_notebook_scripts_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "scripts/build_notebook.py").exists()
    assert (root / "scripts/execute_notebook.py").exists()
