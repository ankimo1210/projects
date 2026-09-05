from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quantcurve.io import REQUIRED_COLUMNS, load_market_data


class TestInputLoading(unittest.TestCase):
    def test_missing_file_is_actionable(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_market_data("does-not-exist.csv")

    def test_missing_schema_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            pd.DataFrame({"obs_id": ["x"]}).to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "missing required columns"):
                load_market_data(path)

    def test_required_schema_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ok.csv"
            pd.DataFrame([{name: 1 for name in REQUIRED_COLUMNS}]).to_csv(path, index=False)
            self.assertEqual(load_market_data(path).shape, (1, len(REQUIRED_COLUMNS)))


if __name__ == "__main__":
    unittest.main()
