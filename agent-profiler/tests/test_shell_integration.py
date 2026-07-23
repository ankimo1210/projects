from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from agent_profiler.shell_integration import (
    END_MARKER,
    START_MARKER,
    default_rc_path,
    detect_shell,
    install_shell_hook,
    shell_init,
    uninstall_shell_hook,
)


def test_detect_shell_and_default_rc() -> None:
    assert detect_shell({"SHELL": "/bin/bash"}) == "bash"
    assert default_rc_path("zsh", Path("/home/example")) == Path("/home/example/.zshrc")
    with pytest.raises(ValueError, match="supported shell"):
        detect_shell({"SHELL": "/bin/fish"})


def test_shell_init_is_valid_bash_and_has_safe_bypasses() -> None:
    source = shell_init("bash")
    process = subprocess.run(
        ["bash", "-n"],
        input=source,
        check=False,
        capture_output=True,
        text=True,
    )
    assert process.returncode == 0, process.stderr
    assert "agenttop wrap codex" in source
    assert "exec|e" in source
    assert "--json" in source
    assert "AGENTTOP_AUTO_WRAP" in source
    assert "[ ! -t 0 ]" in source


@pytest.mark.skipif(shutil.which("script") is None, reason="script(1) is required for a PTY")
def test_shell_init_routes_codex_exec_but_not_codex_options(tmp_path: Path) -> None:
    bin_path = tmp_path / "bin"
    bin_path.mkdir()
    codex = bin_path / "codex"
    agenttop = bin_path / "agenttop"
    init = tmp_path / "agenttop-init.sh"
    codex.write_text("#!/bin/sh\nprintf 'CODEX:%s\\n' \"$*\"\n", encoding="utf-8")
    agenttop.write_text("#!/bin/sh\nprintf 'AGENTTOP:%s\\n' \"$*\"\n", encoding="utf-8")
    init.write_text(shell_init("bash"), encoding="utf-8")
    codex.chmod(0o755)
    agenttop.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = f"{bin_path}:{env['PATH']}"

    wrapped = _run_in_pty(f"source {shlex.quote(str(init))}; codex exec task", env)
    version = _run_in_pty(f"source {shlex.quote(str(init))}; codex --version", env)
    explicit_json = _run_in_pty(
        f"source {shlex.quote(str(init))}; codex exec --json task",
        env,
    )

    assert "AGENTTOP:wrap codex -- task" in wrapped.stdout
    assert "CODEX:--version" in version.stdout
    assert "CODEX:exec --json task" in explicit_json.stdout


def test_install_is_idempotent_reversible_and_preserves_mode(tmp_path: Path) -> None:
    rc_path = tmp_path / ".bashrc"
    rc_path.write_text("export EXAMPLE=1\n", encoding="utf-8")
    rc_path.chmod(0o640)

    assert install_shell_hook("bash", rc_path) is True
    installed = rc_path.read_text(encoding="utf-8")
    assert installed.startswith("export EXAMPLE=1\n")
    assert installed.count(START_MARKER) == 1
    assert installed.count(END_MARKER) == 1
    assert "function codex" in installed
    assert "eval " not in installed
    assert stat_mode(rc_path) == 0o640

    assert install_shell_hook("bash", rc_path) is False
    assert rc_path.read_text(encoding="utf-8") == installed

    assert uninstall_shell_hook(rc_path) is True
    assert rc_path.read_text(encoding="utf-8") == "export EXAMPLE=1\n"
    assert uninstall_shell_hook(rc_path) is False


def test_install_rejects_incomplete_markers(tmp_path: Path) -> None:
    rc_path = tmp_path / ".zshrc"
    rc_path.write_text(f"{START_MARKER}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete"):
        install_shell_hook("zsh", rc_path)


def stat_mode(path: Path) -> int:
    return os.stat(path).st_mode & 0o777


def _run_in_pty(command: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["script", "-qfec", f"bash -c {shlex.quote(command)}", "/dev/null"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
