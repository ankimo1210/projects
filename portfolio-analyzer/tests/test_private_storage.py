"""Machine-local paths keep personal inputs outside the public checkout."""

import ast
import json
from pathlib import Path

import pytest
from portfolio_analyzer.private_storage import configure, data_dir


@pytest.fixture
def paths(tmp_path, monkeypatch):
    monkeypatch.delenv("PORTFOLIO_PRIVATE_DATA_DIR", raising=False)
    workspace = tmp_path / "public"
    (workspace / ".git").mkdir(parents=True)
    project = workspace / "portfolio-analyzer"
    project.mkdir()
    return project, tmp_path / "端末設定.json", tmp_path / "My Drive" / "Repo" / "data"


def test_unconfigured_checkout_keeps_existing_sample_workflow(paths):
    project, config, _private = paths
    assert data_dir(project, config=config) == project / "data"


def test_configured_external_directory_survives_reopening(paths):
    project, config, private = paths
    private.mkdir(parents=True)
    configure(project, private, config=config)
    assert data_dir(project, config=config) == private
    assert set(json.loads(config.read_text())) == {"schema_version", "data_dir"}


def test_explicit_environment_overrides_machine_configuration(paths, monkeypatch):
    project, config, private = paths
    private.mkdir(parents=True)
    configure(project, private, config=config)
    another = private.parent / "Other Drive"
    monkeypatch.setenv("PORTFOLIO_PRIVATE_DATA_DIR", str(another))
    assert data_dir(project, config=config) == another


def test_missing_configured_directory_does_not_fall_back_to_repository(paths):
    project, config, private = paths
    private.mkdir(parents=True)
    configure(project, private, config=config)
    private.rmdir()
    assert data_dir(project, config=config) == private


def test_repository_destination_is_rejected_before_config_write(paths):
    project, config, _private = paths
    with pytest.raises(ValueError, match="outside"):
        configure(project, project / "data", config=config)
    assert not config.exists()


def test_invalid_configuration_is_not_ignored(paths):
    project, config, _private = paths
    config.write_text('{"schema_version": 1, "data_dir": null}')
    with pytest.raises(ValueError, match="configuration"):
        data_dir(project, config=config)


def test_public_regressions_do_not_load_personal_snapshots():
    source = Path(__file__).with_name("test_core.py").read_text(encoding="utf-8")
    assert ".private." not in source
    personal_names = {
        node.id
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Name)
        and node.id in {"PRIVATE_DATA", "PRIVATE_REFERENCE", "PRIVATE_PROPOSAL"}
    }
    assert not personal_names, "Public regressions must use synthetic fixtures"


def prepare_refresh(tmp_path):
    from portfolio_analyzer.private_storage import INPUT_FILES, refresh_inputs

    drive = tmp_path / "Drive 日本語"
    source, cache = drive / "projects/portfolio-analyzer/data", tmp_path / "local copy"
    source.mkdir(parents=True)
    for name in INPUT_FILES:
        (source / name).write_bytes(("synthetic-" + name).encode())

    def refresh(source, cache):
        return refresh_inputs(source, cache, connection_root=drive)

    return refresh, source, cache


def test_refresh_only_copies_authoritative_inputs(tmp_path):
    refresh, source, cache = prepare_refresh(tmp_path)
    (source / "unrelated.private.json").write_text("not an input")
    assert refresh(source, cache)
    assert (cache / "portfolio.private.json").read_bytes() == (
        source / "portfolio.private.json"
    ).read_bytes()
    assert not (cache / "unrelated.private.json").exists()


def test_offline_copy_must_be_complete_and_match_its_record(tmp_path):
    refresh, source, cache = prepare_refresh(tmp_path)
    refresh(source, cache)
    drive = source.parents[2]
    drive.rename(drive.with_name("disconnected"))
    assert refresh(source, cache) is False
    (cache / "portfolio.private.json").write_text("changed locally")
    with pytest.raises(ValueError, match="copy"):
        refresh(source, cache)


def test_connected_drive_missing_input_does_not_partially_update_cache(tmp_path):
    refresh, source, cache = prepare_refresh(tmp_path)
    refresh(source, cache)
    previous = (cache / "portfolio.private.json").read_bytes()
    (source / "portfolio.private.json").write_text("new synthetic snapshot")
    (source / "dc-holding.private.json").unlink()
    with pytest.raises(ValueError, match="missing"):
        refresh(source, cache)
    assert (cache / "portfolio.private.json").read_bytes() == previous


def test_refresh_does_not_overwrite_local_edits(tmp_path):
    refresh, source, cache = prepare_refresh(tmp_path)
    refresh(source, cache)
    (cache / "portfolio.private.json").write_text("local edit")
    (source / "portfolio.private.json").write_text("remote edit")
    with pytest.raises(ValueError, match="changed"):
        refresh(source, cache)
    assert (cache / "portfolio.private.json").read_text() == "local edit"


def test_unverified_offline_copy_is_rejected(tmp_path):
    refresh, source, cache = prepare_refresh(tmp_path)
    drive = source.parents[2]
    drive.rename(drive.with_name("disconnected"))
    with pytest.raises(ValueError, match="verified"):
        refresh(source, cache)


def test_missing_input_directory_is_not_an_offline_drive(tmp_path):
    refresh, source, cache = prepare_refresh(tmp_path)
    refresh(source, cache)
    source.rename(source.with_name("data-renamed"))
    with pytest.raises(ValueError, match="missing"):
        refresh(source, cache)
