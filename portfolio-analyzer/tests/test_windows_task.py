"""The Windows task's cmd, run the way wsl.exe runs it (no Windows needed).

``wsl.exe -- <command line>`` hands the command line to the default Linux shell,
which expands ``$`` before the inner ``bash -lc`` has sourced the env file. An
unescaped ``${PL_MAIL_TO:+--email ...}`` therefore always came out empty and the
scheduled runs never mailed (2026-09-14 .. 09-16), while exiting 0.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

CMD = Path(__file__).resolve().parents[1] / "scripts" / "windows" / "run_daily_pl.cmd"
SCRIPT = "portfolio-analyzer/scripts/daily_pl_report.py"


def wsl_command_line(cmd_text: str, args: str) -> str:
    """The text wsl.exe receives after ``--``, with cmd's own %-expansion applied."""
    line = next(ln for ln in cmd_text.splitlines() if ln.startswith("wsl.exe "))
    command = line.split(" -- ", 1)[1]
    command = command.split(' >> "%OUTDIR%', 1)[0]
    return command.replace("%*", args).replace("%USERNAME%", "someone")


def run_as_wsl(cmd_text: str, args: str, home: Path) -> str:
    """Run the command line through an outer shell and an inner login bash, echoing the script's argv."""
    command = wsl_command_line(cmd_text, args)
    command = re.sub(r"\S+/uv run --no-sync python " + re.escape(SCRIPT), "echo ARGV", command)
    command = re.sub(r"cd \S+ &&", "cd / &&", command)
    done = subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", command],
        capture_output=True,
        text=True,
        timeout=30,
        env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
        check=True,
    )
    return next(ln for ln in done.stdout.splitlines() if ln.startswith("ARGV"))


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_the_env_file_adds_the_email_flag(tmp_path: Path) -> None:
    (tmp_path / ".config").mkdir()
    (tmp_path / ".config" / "pl-daily.env").write_text(
        "PL_MAIL_TO=me@example.com\nPL_SMTP_USER=me@example.com\nPL_SMTP_PASS=x\n"
    )
    argv = run_as_wsl(CMD.read_text(), "--edition tokyo", tmp_path)
    assert "--edition tokyo" in argv
    assert argv.endswith("--email me@example.com")


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_no_env_file_means_no_email_flag(tmp_path: Path) -> None:
    argv = run_as_wsl(CMD.read_text(), "--edition ny", tmp_path)
    assert "--edition ny" in argv
    assert "--email" not in argv
