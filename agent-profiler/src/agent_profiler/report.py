"""Markdown and terminal report formatting."""

from __future__ import annotations

from typing import Any


def format_duration(milliseconds: int | float | None) -> str:
    total = max(0, round((milliseconds or 0) / 1000))
    hours, remaining = divmod(total, 3600)
    minutes, seconds = divmod(remaining, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


def format_duration_delta(milliseconds: int | float | None) -> str:
    if milliseconds is None:
        return "unavailable"
    sign = "+" if milliseconds > 0 else "-" if milliseconds < 0 else ""
    return sign + format_duration(abs(milliseconds))


def format_count(value: int | None) -> str:
    if value is None:
        return "unavailable"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def format_bytes(value: int) -> str:
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value} B"


def terminal_summary(summary: dict[str, Any]) -> str:
    inclusive = summary.get("inclusive_ms", {})
    inclusive = inclusive if isinstance(inclusive, dict) else {}
    tokens = summary.get("tokens", {})
    tokens = tokens if isinstance(tokens, dict) else {}
    shell_tests = int(inclusive.get("shell", 0)) + int(inclusive.get("test", 0))
    search_read = int(inclusive.get("search", 0)) + int(inclusive.get("read", 0))
    elapsed = int(summary.get("elapsed_ms", 0))
    idle = int(summary.get("idle_or_unclassified_ms", elapsed))
    lines = [
        f"{'Elapsed':<22}{format_duration(elapsed):>12}",
        f"{'Model/API wait':<22}{format_duration(inclusive.get('model_wait', 0)):>12}",
        f"{'Shell/tests':<22}{format_duration(shell_tests):>12}",
        f"{'Search/read':<22}{format_duration(search_read):>12}",
        f"{'Idle/unclassified':<22}{format_duration(idle):>12}",
        "",
        "Actual tokens",
        f"{'Input':<22}{format_count(tokens.get('actual_input_tokens')):>12}",
        f"{'Cached input':<22}{format_count(tokens.get('actual_cached_input_tokens')):>12}",
        f"{'Cache write':<22}{format_count(tokens.get('actual_cache_write_input_tokens')):>12}",
        f"{'Output':<22}{format_count(tokens.get('actual_output_tokens')):>12}",
        f"{'Reasoning':<22}{format_count(tokens.get('actual_reasoning_tokens')):>12}",
    ]
    outputs = summary.get("largest_outputs")
    if isinstance(outputs, list) and outputs:
        lines.extend(["", "Largest outputs (next-turn tokens are estimated)"])
        for item in outputs[:5]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "output"))[:28]
            size = format_bytes(int(item.get("output_bytes", 0)))
            estimated = format_count(int(item.get("estimated_next_turn_tokens", 0)))
            lines.append(f"{label:<30}{size:>10}  ~{estimated} tokens")
    return "\n".join(lines)


def build_report(metadata: dict[str, Any], summary: dict[str, Any]) -> str:
    tokens = summary.get("tokens", {})
    tokens = tokens if isinstance(tokens, dict) else {}
    inclusive = summary.get("inclusive_ms", {})
    inclusive = inclusive if isinstance(inclusive, dict) else {}

    def token_value(name: str) -> int | str:
        value = tokens.get(name)
        return value if isinstance(value, int) else "unavailable"

    lines = [
        "# Agent Profiler session report",
        "",
        f"- Profiler session: `{metadata.get('profiler_session_id', 'pending')}`",
        f"- Provider: `{metadata.get('provider', 'unknown')}`",
        f"- Model: `{metadata.get('model') or 'unavailable'}`",
        f"- CLI version: `{metadata.get('provider_version') or 'unavailable'}`",
        f"- Elapsed: {format_duration(summary.get('elapsed_ms', 0))}",
        "",
        "## Time",
        "",
        "| Category | Inclusive | Overlap-adjusted exclusive | Measurement |",
        "|---|---:|---:|---|",
    ]
    exclusive = summary.get("exclusive_ms", {})
    exclusive = exclusive if isinstance(exclusive, dict) else {}
    estimated_categories = {
        str(span.get("category"))
        for span in summary.get("spans", [])
        if isinstance(span, dict) and span.get("measurement") == "estimated"
    }
    for category in sorted(set(inclusive) | set(exclusive)):
        measurement = "estimated/mixed" if category in estimated_categories else "actual"
        lines.append(
            f"| {category} | {format_duration(inclusive.get(category, 0))} | "
            f"{format_duration(exclusive.get(category, 0))} | {measurement} |"
        )
    lines.extend(
        [
            "",
            "Inclusive time can exceed elapsed time when tools run in parallel. "
            "Overlap-adjusted exclusive time divides concurrent wall time among active categories.",
            "",
            "## Actual token usage",
            "",
            "| Metric | Tokens |",
            "|---|---:|",
            f"| Input | {token_value('actual_input_tokens')} |",
            f"| Cached input | {token_value('actual_cached_input_tokens')} |",
            f"| Cache write input | {token_value('actual_cache_write_input_tokens')} |",
            f"| Output | {token_value('actual_output_tokens')} |",
            f"| Reasoning output | {token_value('actual_reasoning_tokens')} |",
            "",
            "## Largest tool outputs",
            "",
            "| Output | Size | Estimated next-turn contribution |",
            "|---|---:|---:|",
        ]
    )
    outputs = summary.get("largest_outputs")
    if isinstance(outputs, list) and outputs:
        for item in outputs:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"| {item.get('label', 'output')} | "
                f"{format_bytes(int(item.get('output_bytes', 0)))} | "
                f"~{item.get('estimated_next_turn_tokens', 0)} tokens (estimated) |"
            )
    else:
        lines.append("| unavailable | - | - |")
    reconciled = summary.get("reconciled_tokens")
    if isinstance(reconciled, dict):
        lines.extend(
            [
                "",
                "## Reconciled token usage",
                "",
                f"- Source: {reconciled.get('source', 'unknown')} "
                f"({reconciled.get('source_version') or 'version unavailable'})",
                f"- Input: {reconciled.get('input_tokens', 'unavailable')}",
                f"- Cached input: {reconciled.get('cached_input_tokens', 'unavailable')}",
                f"- Cache write input: {reconciled.get('cache_write_input_tokens', 'unavailable')}",
                f"- Output: {reconciled.get('output_tokens', 'unavailable')}",
                "",
                "Reconciled values are reported separately and do not overwrite provider actuals.",
            ]
        )
    lines.extend(
        [
            "",
            "## Data quality and limitations",
            "",
            f"- Unknown/incomplete spans: {summary.get('incomplete_span_count', 0)}.",
            f"- Errors: {summary.get('error_count', 0)}; retries/rate limits: "
            f"{summary.get('retry_count', 0)}.",
            "- Context-window capacity is reported only when a provider emits an official value; "
            "otherwise it remains unavailable.",
            "- Estimated attribution uses `ceil(UTF-8 output bytes / 4)` and is not billing usage.",
            "- Raw logs may contain prompts, code, personal data, and tool output even after "
            "best-effort secret redaction.",
            "",
        ]
    )
    return "\n".join(lines)
