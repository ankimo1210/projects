"""Public ``agenttop`` command."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

from agent_profiler.config import AppConfig, load_config
from agent_profiler.replay import replay_file
from agent_profiler.report import terminal_summary
from agent_profiler.runner import RunResult, run_provider, run_provider_args
from agent_profiler.shell_integration import (
    SUPPORTED_SHELLS,
    default_rc_path,
    detect_shell,
    install_shell_hook,
    shell_init,
    uninstall_shell_hook,
)
from agent_profiler.tui import AgentTopApp


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agenttop",
        description="Real-time local profiler for Codex CLI and Claude Code",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="run a provider under the profiler")
    run.add_argument("provider", choices=("codex", "claude"))
    run.add_argument("--cwd", type=Path, default=Path.cwd())
    run.add_argument("--data-dir", type=Path)
    run.add_argument("--config", type=Path)
    run.add_argument("--no-tui", action="store_true")
    run.add_argument("--no-raw-log", action="store_true")
    redaction = run.add_mutually_exclusive_group()
    redaction.add_argument("--redact", action="store_true", default=None)
    redaction.add_argument("--no-redact", action="store_false", dest="redact")
    run.add_argument("--retention-days", type=int)
    run.add_argument("prompt", nargs="+")

    wrap = subparsers.add_parser(
        "wrap",
        help="profile an existing provider command (used by shell integration)",
    )
    wrap.add_argument("provider", choices=("codex",))
    wrap.add_argument("--cwd", type=Path, default=Path.cwd())
    wrap.add_argument("--data-dir", type=Path)
    wrap.add_argument("--config", type=Path)
    wrap.add_argument("--no-tui", action="store_true")
    wrap.add_argument("--no-raw-log", action="store_true")
    wrap.add_argument("provider_args", nargs=argparse.REMAINDER)

    replay = subparsers.add_parser("replay", help="replay a raw JSONL session")
    replay.add_argument("path", type=Path)
    replay.add_argument("--provider", choices=("codex", "claude"))
    replay.add_argument("--speed", type=float, default=1.0)
    replay.add_argument("--data-dir", type=Path)
    replay.add_argument("--config", type=Path)
    replay.add_argument("--no-tui", action="store_true")
    replay.add_argument("--no-raw-log", action="store_true")

    shell_init_parser = subparsers.add_parser(
        "shell-init",
        help="print shell code that automatically profiles codex exec",
    )
    shell_init_parser.add_argument("shell", nargs="?", choices=SUPPORTED_SHELLS)

    install = subparsers.add_parser(
        "install-shell-hook",
        help="enable automatic profiling of codex exec in a shell",
    )
    install.add_argument("--shell", choices=SUPPORTED_SHELLS)
    install.add_argument("--rc", type=Path)

    uninstall = subparsers.add_parser(
        "uninstall-shell-hook",
        help="remove the agenttop block from a shell rc file",
    )
    uninstall.add_argument("--shell", choices=SUPPORTED_SHELLS)
    uninstall.add_argument("--rc", type=Path)
    return parser


def _configure(args: argparse.Namespace) -> AppConfig:
    config = load_config(args.config)
    if args.data_dir is not None:
        config.data_dir = args.data_dir.expanduser()
    if getattr(args, "no_raw_log", False):
        config.storage.save_raw_events = False
    if getattr(args, "redact", None) is not None:
        config.privacy.redact_secrets = bool(args.redact)
    if getattr(args, "retention_days", None) is not None:
        if args.retention_days < 0:
            raise ValueError("--retention-days must be non-negative")
        config.storage.retention_days = args.retention_days
    return config


async def _headless_run(args: argparse.Namespace, config: AppConfig) -> RunResult:
    def log_event(_event: Any, raw: str) -> None:
        if raw:
            print(raw, flush=True)

    if args.command == "run":
        prompt = " ".join(args.prompt).strip()
        return await run_provider(
            args.provider,
            prompt,
            config,
            cwd=args.cwd,
            callback=log_event,
        )
    if args.command == "wrap":
        return await run_provider_args(
            args.provider,
            _provider_args(args),
            config,
            cwd=args.cwd,
            callback=log_event,
        )
    return await replay_file(
        args.path,
        config,
        provider=args.provider,
        speed=args.speed,
        callback=log_event,
    )


def _run_tui(args: argparse.Namespace, config: AppConfig) -> RunResult | None:
    if args.command == "run":
        prompt = " ".join(args.prompt).strip()

        async def factory(callback: Any) -> RunResult:
            return await run_provider(
                args.provider,
                prompt,
                config,
                cwd=args.cwd,
                callback=callback,
            )

        provider = args.provider
    elif args.command == "wrap":

        async def factory(callback: Any) -> RunResult:
            return await run_provider_args(
                args.provider,
                _provider_args(args),
                config,
                cwd=args.cwd,
                callback=callback,
            )

        provider = args.provider
    else:

        async def factory(callback: Any) -> RunResult:
            return await replay_file(
                args.path,
                config,
                provider=args.provider,
                speed=args.speed,
                callback=callback,
            )

        provider = args.provider or "auto"
    app = AgentTopApp(
        provider,
        factory,
        refresh_ms=config.display.refresh_ms,
        max_timeline_rows=config.display.max_timeline_rows,
    )
    return app.run()


def _provider_args(args: argparse.Namespace) -> list[str]:
    values = list(args.provider_args)
    return values[1:] if values and values[0] == "--" else values


def _shell_and_rc(args: argparse.Namespace) -> tuple[str, Path]:
    shell = args.shell or detect_shell()
    rc_path = args.rc.expanduser() if args.rc is not None else default_rc_path(shell)
    return shell, rc_path


def _handle_shell_command(args: argparse.Namespace) -> bool:
    if args.command == "shell-init":
        print(shell_init(args.shell or detect_shell()), end="")
        return True
    if args.command == "install-shell-hook":
        shell, rc_path = _shell_and_rc(args)
        changed = install_shell_hook(shell, rc_path)
        state = "Installed" if changed else "Already installed"
        print(f"{state}: {rc_path}")
        print(f"Activate now: source {rc_path}")
        print("Disable for one command: AGENTTOP_AUTO_WRAP=0 codex exec ...")
        return True
    if args.command == "uninstall-shell-hook":
        _shell, rc_path = _shell_and_rc(args)
        changed = uninstall_shell_hook(rc_path)
        state = "Removed" if changed else "Not installed"
        print(f"{state}: {rc_path}")
        return True
    return False


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    try:
        if _handle_shell_command(args):
            return
        config = _configure(args)
        if args.command == "run":
            if not " ".join(args.prompt).strip():
                parser.error("run requires a prompt after --")
        if args.command == "wrap" and not _provider_args(args):
            parser.error("wrap requires provider arguments after --")
        if args.command == "replay" and not args.path.is_file():
            parser.error(f"replay file does not exist: {args.path}")
        result = asyncio.run(_headless_run(args, config)) if args.no_tui else _run_tui(args, config)
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except (OSError, ValueError) as exc:
        print(f"agenttop: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    if result is None:
        raise SystemExit(130)
    print(terminal_summary(result.summary))
    print(f"\nSession: {result.profiler_session_id}")
    print(f"Saved: {result.session_path}")
    raise SystemExit(result.exit_code)


if __name__ == "__main__":
    main()
