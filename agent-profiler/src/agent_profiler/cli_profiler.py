"""Public session management and reporting CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agent_profiler.config import load_config
from agent_profiler.report import (
    format_count,
    format_duration,
    format_duration_delta,
    terminal_summary,
)
from agent_profiler.storage import SessionStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-profiler",
        description="Inspect, export, and compare Agent Profiler sessions",
    )
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--config", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("sessions", help="list saved sessions")
    show = subparsers.add_parser("show", help="show session summary")
    show.add_argument("session_id")
    report = subparsers.add_parser("report", help="print Markdown report")
    report.add_argument("session_id")
    export = subparsers.add_parser("export", help="export a session")
    export.add_argument("session_id")
    export.add_argument("--format", choices=("json",), default="json")
    compare = subparsers.add_parser("compare", help="compare two sessions")
    compare.add_argument("session_a")
    compare.add_argument("session_b")
    return parser


def _session_export(store: SessionStore, session_id: str) -> dict[str, Any]:
    path = store.session_path(session_id)
    events: list[dict[str, Any]] = []
    normalized = path / "events.normalized.jsonl"
    if normalized.is_file():
        with normalized.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    events.append(value)
    return {
        "metadata": store.read_json(session_id, "metadata.json"),
        "summary": store.read_json(session_id, "summary.json"),
        "events": events,
    }


def _compare(store: SessionStore, session_a: str, session_b: str) -> str:
    a = store.read_json(session_a, "summary.json")
    b = store.read_json(session_b, "summary.json")
    a_tokens = a.get("tokens", {})
    b_tokens = b.get("tokens", {})
    a_tokens = a_tokens if isinstance(a_tokens, dict) else {}
    b_tokens = b_tokens if isinstance(b_tokens, dict) else {}
    a_time = a.get("inclusive_ms", {})
    b_time = b.get("inclusive_ms", {})
    a_time = a_time if isinstance(a_time, dict) else {}
    b_time = b_time if isinstance(b_time, dict) else {}

    def combined(values: dict[str, Any], *categories: str) -> int:
        return sum(
            value if isinstance((value := values.get(category)), int) else 0
            for category in categories
        )

    rows = [
        ("Elapsed", a.get("elapsed_ms"), b.get("elapsed_ms"), "duration"),
        (
            "Model/API wait",
            combined(a_time, "model_wait"),
            combined(b_time, "model_wait"),
            "duration",
        ),
        (
            "Shell/tests",
            combined(a_time, "shell", "test"),
            combined(b_time, "shell", "test"),
            "duration",
        ),
        (
            "Search/read",
            combined(a_time, "search", "read"),
            combined(b_time, "search", "read"),
            "duration",
        ),
        (
            "Input tokens",
            a_tokens.get("actual_input_tokens"),
            b_tokens.get("actual_input_tokens"),
            "count",
        ),
        (
            "Cached input",
            a_tokens.get("actual_cached_input_tokens"),
            b_tokens.get("actual_cached_input_tokens"),
            "count",
        ),
        (
            "Output tokens",
            a_tokens.get("actual_output_tokens"),
            b_tokens.get("actual_output_tokens"),
            "count",
        ),
    ]
    lines = [
        f"{'Metric':<22}{session_a[:14]:>16}{session_b[:14]:>16}{'Delta B-A':>16}",
        "-" * 70,
    ]
    for label, left, right, kind in rows:
        delta = right - left if isinstance(left, int) and isinstance(right, int) else None
        if kind == "duration":
            values = (
                format_duration(left),
                format_duration(right),
                format_duration_delta(delta),
            )
        else:
            values = (format_count(left), format_count(right), format_count(delta))
        lines.append(f"{label:<22}{values[0]:>16}{values[1]:>16}{values[2]:>16}")
    return "\n".join(lines)


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.data_dir is not None:
            config.data_dir = args.data_dir.expanduser()
        store = SessionStore(config.data_dir)
        if args.command == "sessions":
            sessions = store.list_sessions()
            if not sessions:
                print("No sessions found.")
                return
            print(f"{'SESSION':<35} {'PROVIDER':<9} {'MODEL':<24} {'EXIT':>4}")
            for item in sessions:
                print(
                    f"{item.get('profiler_session_id', '')!s:<35} "
                    f"{item.get('provider', '')!s:<9} "
                    f"{item.get('model') or 'unavailable'!s:<24} "
                    f"{item.get('exit_code', '-')!s:>4}"
                )
        elif args.command == "show":
            metadata = store.read_json(args.session_id, "metadata.json")
            summary = store.read_json(args.session_id, "summary.json")
            print(
                f"{metadata.get('provider', 'unknown')} · "
                f"{metadata.get('model') or 'unavailable'} · "
                f"exit {metadata.get('exit_code', '-')}\n"
            )
            print(terminal_summary(summary))
        elif args.command == "report":
            report_path = store.session_path(args.session_id) / "report.md"
            print(report_path.read_text(encoding="utf-8"), end="")
        elif args.command == "export":
            print(
                json.dumps(
                    _session_export(store, args.session_id),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "compare":
            print(_compare(store, args.session_a, args.session_b))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"agent-profiler: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
