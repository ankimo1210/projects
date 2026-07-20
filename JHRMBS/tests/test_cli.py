from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from jhrmbs.cli import main
from jhrmbs.config import AppConfig


def test_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    assert "build-dataset" in capsys.readouterr().out


def _config_file(tmp_path: Path, config: AppConfig) -> Path:
    path = tmp_path / "jhrmbs-test.yml"
    path.write_text(f"data_root: {config.data_root}\n", encoding="utf-8")
    return path


def test_cashflow_cli_warns_on_ignored_arguments(
    pipeline_config: AppConfig,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = _config_file(tmp_path, pipeline_config)
    with caplog.at_level(logging.WARNING, logger="jhrmbs.cli"):
        code = main(
            [
                "--config",
                str(config_path),
                "cashflow",
                "--issue",
                "JHF-001",
                "--scenario",
                "model",
                "--psj-terminal-cpr-pct",
                "5",
            ]
        )
    assert code == 0
    assert any("--psj-terminal-cpr-pct" in message for message in caplog.messages)
    payload = json.loads(capsys.readouterr().out)
    assert payload["scenario"] == "model_rate"

    with caplog.at_level(logging.WARNING, logger="jhrmbs.cli"):
        code = main(
            [
                "--config",
                str(config_path),
                "cashflow",
                "--issue",
                "JHF-001",
                "--scenario",
                "psj",
                "--model",
                "full",
            ]
        )
    assert code == 0
    assert any("--model" in message for message in caplog.messages)


def test_cashflow_cli_supports_total_decrement_scenario(
    pipeline_config: AppConfig,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = _config_file(tmp_path, pipeline_config)
    code = main(
        [
            "--config",
            str(config_path),
            "cashflow",
            "--issue",
            "JHF-001",
            "--include-other-decrements",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert str(payload["scenario"]).endswith("_totaldec")
    assert payload["published_decrements_included"] is True
