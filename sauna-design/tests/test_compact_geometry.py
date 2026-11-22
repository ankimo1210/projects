"""Independent plan checks: total area alone must not conceal overlaps and gaps."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class CompactGeometryTests(unittest.TestCase):
    def test_touching_zones_do_not_overlap(self):
        from compact_geometry import rectangle_metrics

        m = rectangle_metrics([[0, 0, 10, 10], [10, 0, 7, 10]], 17, 10)
        self.assertAlmostEqual(m["union_area_m2"], 170)
        self.assertAlmostEqual(m["overlap_area_m2"], 0)
        self.assertAlmostEqual(m["uncovered_area_m2"], 0)

    def test_equal_sum_can_hide_overlap_and_uncovered_floor(self):
        from compact_geometry import rectangle_metrics

        m = rectangle_metrics([[0, 0, 6, 10], [5, 0, 4, 10]], 10, 10)
        self.assertAlmostEqual(m["summed_area_m2"], 100)
        self.assertAlmostEqual(m["overlap_area_m2"], 10)
        self.assertAlmostEqual(m["uncovered_area_m2"], 10)

    def test_outside_floor_is_reported_separately(self):
        from compact_geometry import rectangle_metrics

        m = rectangle_metrics([[-1, 0, 2, 2]], 10, 10)
        self.assertEqual(m["out_of_bounds_indices"], [0])
        self.assertAlmostEqual(m["union_area_m2"], 2)
        self.assertAlmostEqual(m["uncovered_area_m2"], 98)

    def test_invalid_dimensions_are_rejected(self):
        from compact_geometry import rectangle_metrics

        for rect in ([0, 0, -1, 2], [0, 0, float("nan"), 2]):
            with self.assertRaises(ValueError):
                rectangle_metrics([rect], 17, 10)


if __name__ == "__main__":
    unittest.main()
