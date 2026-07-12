"""Tests for command-line orchestration and thin script entry points."""

from dataclasses import replace
from pathlib import Path

import pytest
from rough_volatility.cli import main
from rough_volatility.config import ProjectConfig, save_config


def _paths_config() -> ProjectConfig:
    base = ProjectConfig(profile="cli-test", seed=1210)
    return replace(
        base,
        fbm=replace(
            base.fbm, h_values=(0.1, 0.5), n_steps=96, n_paths=8, n_display_paths=2, n_lags=7
        ),
        hurst=replace(
            base.hurst, h_values=(0.1, 0.5), sample_sizes=(64, 96), n_replications=3, n_lags=7
        ),
        ou=replace(base.ou, n_steps=96, n_paths=5, burn_in_steps=24),
        bergomi=replace(base.bergomi, n_steps=20, n_paths=100, chunk_size=100, keep_paths=2),
        options=replace(
            base.options, maturities=(0.25, 0.5, 1.0), n_strikes=7, skew_maturity_steps=16
        ),
        hawkes=replace(base.hawkes, horizon=40.0, target_rate=2.0, max_events=2000),
        noise=replace(base.noise, n_steps=128, n_replications=3),
    )


def test_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_paths_command_writes_a_to_c_artifacts(tmp_path: Path) -> None:
    config_path = save_config(_paths_config(), tmp_path / "tiny.yaml")
    result = main(
        [
            "paths",
            "--config",
            str(config_path),
            "--root",
            str(tmp_path),
            "--force",
        ]
    )
    assert result == 0
    assert (tmp_path / "artifacts/data/fbm_paths.csv").exists()
    assert (tmp_path / "artifacts/data/hurst_estimator_recovery.csv").exists()
    assert (tmp_path / "artifacts/data/ou_fou_paths.csv").exists()


def test_expected_thin_scripts_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in (
        "run_path_experiments.py",
        "run_option_experiments.py",
        "run_microstructure_experiments.py",
        "run_all.py",
    ):
        assert (root / "scripts" / name).exists()
