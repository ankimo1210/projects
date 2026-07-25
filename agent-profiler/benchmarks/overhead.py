"""Compare JSONL parsing alone with the normalized metrics pipeline."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from agent_profiler.adapters.codex import CodexAdapter
from agent_profiler.metrics import MetricsEngine


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=100_000)
    args = parser.parse_args()
    fixture = Path(__file__).parents[1] / "tests" / "fixtures" / "codex-session.jsonl"
    lines = fixture.read_text(encoding="utf-8").splitlines()

    started = time.perf_counter()
    for index in range(args.events):
        json.loads(lines[index % len(lines)])
    baseline = time.perf_counter() - started

    adapter = CodexAdapter()
    metrics = MetricsEngine(max_recent_events=100)
    started = time.perf_counter()
    for index in range(args.events):
        raw = json.loads(lines[index % len(lines)])
        for event in adapter.normalize(raw, datetime.now(UTC)):
            metrics.process(event)
    profiled = time.perf_counter() - started
    incremental = max(0.0, profiled - baseline)
    print(
        json.dumps(
            {
                "input_events": args.events,
                "baseline_json_parse_seconds": round(baseline, 6),
                "profiled_parse_normalize_metrics_seconds": round(profiled, 6),
                "incremental_seconds": round(incremental, 6),
                "incremental_microseconds_per_event": round(incremental / args.events * 1e6, 3),
                "scope": "in-process ingestion; excludes model/network and TUI rendering",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
