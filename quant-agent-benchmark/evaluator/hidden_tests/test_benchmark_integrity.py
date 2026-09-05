from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestBenchmarkIntegrity(unittest.TestCase):
    def test_public_hashes_match(self) -> None:
        manifest = json.loads((ROOT / "input" / "MANIFEST.json").read_text())
        for rel, expected in manifest["public_file_hashes"].items():
            self.assertEqual(sha(ROOT / "input" / rel), expected, rel)

    def test_visible_dataset_size_and_span(self) -> None:
        frame = pd.read_csv(ROOT / "input" / "market_data" / "market_observations.csv")
        self.assertGreaterEqual(len(frame), 120)
        self.assertLessEqual(len(frame), 180)
        self.assertLessEqual(frame["maturity_years"].min(), 1 / 12 + 1e-5)
        self.assertGreaterEqual(frame["maturity_years"].max(), 29.0)

    def test_visible_instrument_mix(self) -> None:
        kinds = set(pd.read_csv(ROOT / "input" / "market_data" / "market_observations.csv")["instrument_type"])
        self.assertEqual(kinds, {"deposit", "ois_swap", "bond"})

    def test_truth_curve_finite_and_positive(self) -> None:
        truth = pd.read_csv(ROOT / "evaluator" / "ground_truth" / "main_curve.csv")
        self.assertTrue(np.isfinite(truth.select_dtypes("number")).all().all())
        self.assertTrue((truth["discount_factor"] > 0).all())

    def test_ten_hidden_scenarios(self) -> None:
        scenarios = sorted((ROOT / "evaluator" / "hidden_scenarios").glob("s*"))
        self.assertEqual(len(scenarios), 10)
        for scenario in scenarios:
            self.assertTrue((scenario / "market_data.csv").is_file())
            self.assertTrue((scenario / "truth_curve.csv").is_file())

    def test_no_private_names_in_input(self) -> None:
        public_text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in (ROOT / "input").rglob("*") if p.is_file())
        for forbidden in ("negative_front_end", "multiple_large_outliers", "true_curve_parameters", "evaluator/ground_truth", "reference_solution"):
            self.assertNotIn(forbidden, public_text)

    def test_result_directories_empty(self) -> None:
        for name in ("astra", "sol", "opus", "fable"):
            path = ROOT / "results" / name
            self.assertTrue(path.is_dir())
            self.assertEqual(list(path.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
