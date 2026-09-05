"""Shared maturity grids used across calibration, risk, and reporting."""

from __future__ import annotations

import numpy as np

# Calibration knots: matches the deposit/OIS pillar tenors present in the
# benchmark convention set, extended out to 30Y. Bonds fall between knots
# and are priced by interpolation/spline, which is standard (bonds are
# denser but individually less liquid than the deposit/OIS pillars).
CALIBRATION_KNOTS = np.array(
    [
        1 / 12, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0,
        4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0,
    ],
    dtype=float,
)

# Dense output grid for curve.csv: >= 361 rows spanning [1/12Y, 30Y].
OUTPUT_GRID = np.linspace(1 / 12, 30.0, 400)

KEY_RATE_POINTS = (2.0, 5.0, 10.0, 30.0)
