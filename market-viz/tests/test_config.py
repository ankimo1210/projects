"""Config loading must be CWD-independent.

Regression tests for the src-layout reorganisation: config files moved to
src/market_viz/config/ but readers kept opening "src/config/..." relative
to the current working directory, so every launch path raised
FileNotFoundError.
"""

from market_viz.config import (
    CONFIG_DIR,
    PROJECT_ROOT,
    load_instruments,
    load_instruments_config,
    load_settings,
)


def test_config_files_live_in_package():
    assert (CONFIG_DIR / "settings.yaml").is_file()
    assert (CONFIG_DIR / "instruments.yaml").is_file()


def test_project_root_is_the_project_dir():
    assert (PROJECT_ROOT / "pyproject.toml").is_file()
    assert PROJECT_ROOT.name == "market-viz"


def test_load_settings_from_any_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = load_settings()
    assert settings["app"]["title"]
    assert settings["data"]["db_path"]


def test_load_instruments_raw_and_flat_agree(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw = load_instruments_config()
    assert raw.get("instruments")
    flat = load_instruments()
    assert flat
    assert all("ticker" in i for i in flat)
    assert len(flat) == sum(len(g) for g in raw["instruments"].values())


def test_update_module_loaders_cwd_independent(tmp_path, monkeypatch):
    from market_viz.data.update import _load_instruments, _load_settings

    monkeypatch.chdir(tmp_path)
    assert _load_settings()["app"]["title"]
    assert _load_instruments()
