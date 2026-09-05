import unittest
import json
import tempfile
from pathlib import Path

from recover_tokens import counter_segment_totals, normalized_usage, is_actual_claude_prompt, parse_claude


class RecoveryTests(unittest.TestCase):
    def test_reasoning_and_cache_are_not_double_counted_codex(self):
        usage = normalized_usage({"input_tokens": 100, "cached_input_tokens": 80,
                                  "output_tokens": 50, "reasoning_output_tokens": 30,
                                  "total_tokens": 150}, "codex")
        self.assertEqual(usage["uncached_input"], 20)
        self.assertEqual(usage["output_nonreasoning"], 20)
        self.assertEqual(sum(usage[k] for k in ("uncached_input", "cache_read_input", "cache_creation_input", "output_nonreasoning", "output_reasoning")), 150)

    def test_claude_cache_inputs_are_additive(self):
        usage = normalized_usage({"input_tokens": 2, "cache_read_input_tokens": 80,
                                  "cache_creation_input_tokens": 18, "output_tokens": 50,
                                  "output_tokens_details": {"thinking_tokens": 30}}, "claude")
        self.assertEqual(usage["input_total"], 100)
        self.assertEqual(usage["total_tokens"], 150)

    def test_repeated_counters_and_reset(self):
        totals, repeats, resets = counter_segment_totals([
            {"total_tokens": 100}, {"total_tokens": 200}, {"total_tokens": 200},
            {"total_tokens": 50}, {"total_tokens": 80}])
        self.assertEqual(totals["total_tokens"], 280)
        self.assertEqual((repeats, resets), (1, 1))

    def test_tool_result_is_not_new_user_turn(self):
        self.assertFalse(is_actual_claude_prompt({"type": "user", "message": {"content": [{"type": "tool_result", "content": "done"}]}}))

    def test_compaction_and_local_commands_not_human_turns(self):
        for text in ("This session is being continued from a previous conversation...", "<command-name>/model</command-name>"):
            self.assertFalse(is_actual_claude_prompt({"type": "user", "message": {"content": text}}))

    def test_normal_human_prompt_is_turn(self):
        self.assertTrue(is_actual_claude_prompt({"type": "user", "message": {"content": "Build the benchmark candidate."}}))

    def test_unknown_thinking_is_not_assumed_zero(self):
        with self.assertRaises(ValueError):
            normalized_usage({"input_tokens": 100, "output_tokens": 10}, "claude")

    def test_multiple_content_blocks_count_as_one_api_response(self):
        usage = {"input_tokens": 2, "cache_read_input_tokens": 80, "cache_creation_input_tokens": 18,
                 "output_tokens": 50, "output_tokens_details": {"thinking_tokens": 30}}
        records = [{"type": "user", "uuid": "u", "timestamp": "2026-09-05T01:00:00Z", "message": {"content": "Build it"}}]
        for number in (1, 2):
            records.append({"type": "assistant", "uuid": f"block-{number}", "sessionId": "s", "requestId": "req-1",
                            "timestamp": f"2026-09-05T01:00:0{number}Z", "message": {
                                "id": "msg-1", "model": "example", "usage": usage, "content": [{"type": "text", "text": "test"}]}})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"transcript.jsonl"
            path.write_text("\n".join(json.dumps(x) for x in records), encoding="utf-8")
            turns, api, calls, audit = parse_claude({"path": str(path), "turn_labels": ["test"], "primary_turn": 1})
        self.assertEqual(len(turns), 1)
        self.assertEqual(len(api), 1)
        self.assertEqual(api[0]["total_tokens"], 150)
        self.assertEqual(audit["duplicate_api_blocks_removed"], 1)


if __name__ == "__main__":
    unittest.main()
