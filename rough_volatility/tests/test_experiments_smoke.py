"""End-to-end smoke tests for experiments A--G and artifact provenance."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from rough_volatility.config import ProjectConfig
from rough_volatility.experiments import load_artifact_manifest, run_all


@pytest.fixture
def tiny_config() -> ProjectConfig:
    base = ProjectConfig(profile="test", seed=1210)
    return replace(
        base,
        fbm=replace(
            base.fbm,
            h_values=(0.1, 0.5),
            n_steps=128,
            n_paths=12,
            n_display_paths=2,
            n_lags=8,
        ),
        hurst=replace(
            base.hurst,
            h_values=(0.1, 0.5),
            sample_sizes=(64, 128),
            n_replications=4,
            n_lags=8,
        ),
        ou=replace(base.ou, n_steps=128, n_paths=6, burn_in_steps=32),
        bergomi=replace(
            base.bergomi,
            n_steps=20,
            n_paths=400,
            chunk_size=200,
            keep_paths=5,
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
            bin_width=1.0,
            intensity_grid_points=100,
        ),
        microstructure=replace(base.microstructure, rv_window=5, intensity_window=5),
        noise=replace(
            base.noise,
            n_steps=128,
            n_replications=4,
            noise_stds=(0.0, 0.1),
            strides=(1, 2),
            estimators=("variogram", "madogram"),
        ),
    )


def test_run_all_writes_complete_reusable_manifest_with_provenance(
    tiny_config: ProjectConfig, tmp_path: Path
) -> None:
    manifest = run_all(tiny_config, tmp_path, force=True)
    required = {
        "fbm_paths",
        "fbm_structure",
        "hurst_recovery",
        "ou_paths",
        "model_paths",
        "terminal_distributions",
        "option_surface",
        "skew_term_structure",
        "hawkes_events",
        "hawkes_series",
        "noise_fragility",
        "validation_checks",
        "manifest",
    }
    assert required <= set(manifest)
    assert all(manifest[key].exists() for key in required)

    provenance_keys = {
        "seed",
        "profile",
        "params_fingerprint",
        "sample_size",
        "timestamp_utc",
        "git_commit",
        "package_version",
    }
    metrics_dir = tmp_path / "artifacts" / "metrics"
    metric_files = list(metrics_dir.glob("*.json"))
    assert metric_files
    for path in metric_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert provenance_keys <= set(payload), path.name

    marker = manifest["experiment_a_metrics"]
    initial_mtime = marker.stat().st_mtime_ns
    reused = run_all(tiny_config, tmp_path, force=False)
    assert reused["experiment_a_metrics"].stat().st_mtime_ns == initial_mtime
    loaded = load_artifact_manifest(tiny_config, tmp_path)
    assert loaded["option_surface"] == manifest["option_surface"]


def test_manifest_fingerprint_mismatch_is_actionable(
    tiny_config: ProjectConfig, tmp_path: Path
) -> None:
    run_all(tiny_config, tmp_path, force=True)
    changed = replace(tiny_config, seed=999)
    with pytest.raises(ValueError, match=r"fingerprint|re-run"):
        load_artifact_manifest(changed, tmp_path)
