from __future__ import annotations

import pytest
from jhrmbs.cli import main


def test_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    assert "build-dataset" in capsys.readouterr().out
