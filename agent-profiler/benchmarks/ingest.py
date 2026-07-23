"""Measure parser/normalizer/metrics overhead without making model calls."""

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
    raw_events = [json.loads(line) for line in fixture.read_text(encoding="utf-8").splitlines()]
    adapter = CodexAdapter()
    metrics = MetricsEngine(max_recent_events=100)
    started = time.perf_counter()
    for index in range(args.events):
        raw = raw_events[index % len(raw_events)]
        for event in adapter.normalize(raw, datetime.now(UTC)):
            metrics.process(event)
    elapsed = time.perf_counter() - started
    print(
        json.dumps(
            {
                "input_events": args.events,
                "elapsed_seconds": round(elapsed, 6),
                "events_per_second": round(args.events / elapsed),
                "microseconds_per_input_event": round(elapsed / args.events * 1e6, 3),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
