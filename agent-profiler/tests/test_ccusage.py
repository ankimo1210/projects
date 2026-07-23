from __future__ import annotations

import json
from subprocess import CompletedProcess
from unittest.mock import patch

from agent_profiler.ccusage import CcusageAdapter


def test_ccusage_uses_json_and_matches_session() -> None:
    payload = {
        "sessions": [
            {
                "sessionId": "fixture-session",
                "inputTokens": 10,
                "cacheReadTokens": 20,
                "cacheCreationTokens": 3,
                "outputTokens": 4,
                "totalTokens": 34,
            }
        ]
    }
    results = [
        CompletedProcess(["ccusage", "--version"], 0, "ccusage 20.0.18\n", ""),
        CompletedProcess(
            ["ccusage", "codex", "session", "--json", "--offline"],
            0,
            json.dumps(payload),
            "",
        ),
    ]
    with (
        patch("agent_profiler.ccusage.shutil.which", return_value="/bin/ccusage"),
        patch("agent_profiler.ccusage.subprocess.run", side_effect=results) as run,
    ):
        usage = CcusageAdapter().reconcile("codex", "fixture-session")
    assert usage is not None
    assert usage.cached_input_tokens == 20
    assert usage.source_version == "ccusage 20.0.18"
    assert "--json" in run.call_args_list[1].args[0]
    assert "--offline" in run.call_args_list[1].args[0]
