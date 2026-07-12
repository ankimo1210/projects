"""Tests for configuration dataclasses, YAML profiles and provenance."""

from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest
from rough_volatility.config import (
    BergomiConfig,
    FbmConfig,
    HawkesConfig,
    ProjectConfig,
    load_config,
    provenance_stamp,
    save_config,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "configs"


@pytest.fixture(scope="module")
def quick() -> ProjectConfig:
    return load_config(CONFIG_DIR / "quick.yaml")


def test_all_profiles_load_and_validate() -> None:
    for name in ("quick", "default", "full"):
        config = load_config(CONFIG_DIR / f"{name}.yaml")
        assert config.profile == name
        assert config.seed == 1210


def test_quick_profile_values(quick: ProjectConfig) -> None:
    assert quick.fbm.n_steps == 2048
    assert quick.hurst.n_replications == 100
    assert quick.bergomi.n_paths == 10_000
    assert quick.bergomi.n_steps == 200
    assert 0.02 not in quick.options.maturities
    assert quick.hawkes.max_events == 100_000


def test_yaml_round_trip(tmp_path: Path, quick: ProjectConfig) -> None:
    out = tmp_path / "roundtrip.yaml"
    save_config(quick, out)
    again = load_config(out)
    assert again.to_dict() == quick.to_dict()
    assert again.fingerprint() == quick.fingerprint()


def test_fingerprint_changes_with_params(quick: ProjectConfig) -> None:
    modified = replace(quick, bergomi=replace(quick.bergomi, eta=2.0))
    assert modified.fingerprint() != quick.fingerprint()
    assert len(quick.fingerprint()) == 12


def test_invalid_hurst_rejected() -> None:
    with pytest.raises(ValueError, match=r"[Hh]urst"):
        FbmConfig(h_values=(0.1, 1.2)).validate()


def test_invalid_rho_rejected() -> None:
    with pytest.raises(ValueError, match="rho"):
        BergomiConfig(rho=1.5).validate()


def test_near_critical_branching_rejected() -> None:
    with pytest.raises(ValueError, match="branching"):
        HawkesConfig(branching_critical=0.999).validate()


def test_maturity_grid_misalignment_rejected(quick: ProjectConfig) -> None:
    bad = replace(
        quick,
        options=replace(quick.options, maturities=(0.033, 0.25, 1.0)),
    )
    with pytest.raises(ValueError, match="maturit"):
        bad.validate()


def test_spec_252_grid_would_be_rejected(quick: ProjectConfig) -> None:
    # The spec's n_steps=252 does not contain the 0.02y maturity (5.04 steps).
    bad = replace(
        quick,
        bergomi=replace(quick.bergomi, n_steps=252),
        options=replace(quick.options, maturities=(0.02, 0.25, 1.0)),
    )
    with pytest.raises(ValueError, match="maturit"):
        bad.validate()


def test_unknown_yaml_key_rejected(tmp_path: Path) -> None:
    text = (CONFIG_DIR / "quick.yaml").read_text(encoding="utf-8")
    bad = tmp_path / "bad.yaml"
    bad.write_text(text + "\ntypo_section:\n  a: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="typo_section"):
        load_config(bad)


def test_provenance_stamp_keys(quick: ProjectConfig) -> None:
    stamp = provenance_stamp(quick, sample_size=123)
    assert set(stamp) == {
        "seed",
        "profile",
        "params_fingerprint",
        "sample_size",
        "timestamp_utc",
        "git_commit",
        "package_version",
    }
    assert stamp["seed"] == 1210
    assert stamp["sample_size"] == 123
    assert stamp["git_commit"] == "unknown" or len(stamp["git_commit"]) == 40
    datetime.fromisoformat(stamp["timestamp_utc"])  # parses
