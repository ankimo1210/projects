"""Combined preparation is seven single-session runs, not a 28-run factorial."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "owner"))
from prepare_combined import combined, fingerprint
from prepare_run import CONFIG, KIT, prepare


class CombinedTests(unittest.TestCase):
    def test_all_seven_models_one_run_each(self):
        with tempfile.TemporaryDirectory(prefix="quant-combined-test-") as directory:
            parent = Path(directory)
            legacy = parent / "pilot"
            legacy.mkdir()
            (legacy / "original.txt").write_text("keep previous pilot unchanged\n")
            before = fingerprint(legacy)
            root = parent / "combined_all_models"
            with patch("prepare_combined.prepare") as stage:
                combined(root, parent / "suite", parent / "materials", parent / "python")
            plan = json.loads((root / "run_plan.json").read_text())
            self.assertEqual(stage.call_count, 7)
            self.assertEqual(
                {r["model"] for r in plan["runs"]}, set(CONFIG["starting_submissions"])
            )
            self.assertTrue(all(r["arm"] == "D" and r["repeat"] == 1 for r in plan["runs"]))
            self.assertTrue(
                all(c.kwargs["campaign"] == "combined_all_models" for c in stage.call_args_list)
            )
            self.assertEqual(plan["maximum_agent_minutes"], 420)
            self.assertFalse(plan["launch_ready"])
            self.assertFalse(plan["separate_resource_effects_identifiable"])
            self.assertEqual(fingerprint(legacy), before)
            with self.assertRaises(FileExistsError):
                combined(root, parent / "suite", parent / "materials", parent / "python")

    def test_noncombined_arm_rejected_before_writes(self):
        with tempfile.TemporaryDirectory(prefix="quant-combined-test-") as directory:
            root = Path(directory) / "run"
            with self.assertRaises(ValueError):
                prepare(
                    "astra",
                    "A",
                    1,
                    root,
                    root / "suite",
                    root / "materials",
                    root / "python",
                    campaign="combined_all_models",
                )
            self.assertFalse(root.exists())

    def test_prompt_contains_checkpoints_and_no_four_arm_work(self):
        prompt = (KIT / "public/combined_prompt.md").read_text()
        self.assertIn("4パターンを作る必要はない", prompt)
        self.assertIn("audit/convention_only/", prompt)
        self.assertIn("実行可能なソース", prompt)
        self.assertIn("TIME_LIMIT_MINUTES = 60", prompt)
        self.assertNotIn("- A:", prompt)
        self.assertNotIn("- B:", prompt)


if __name__ == "__main__":
    unittest.main()
