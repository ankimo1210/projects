"""Hull §24.5 Tables24.2/3: observed P/Q intensities, derived ratios/spreads."""

from decimal import Decimal

import numpy as np
import pytest
from hullkit import _credit_risk as c
from scipy.optimize import brentq


def test_source_all_ratio_difference_compensation_excess_columns():
    historical = np.array([0.04, 0.06, 0.13, 0.47, 2.40, 7.49, 16.90]) / 100
    pricing = np.array([0.67, 0.78, 1.28, 2.38, 5.07, 9.02, 21.30]) / 100
    spreads = np.array([40, 47, 77, 143, 304, 542, 1278]) / 10000
    result = c.hazard_comparison(historical, pricing, recovery=0.4, total_spreads=spreads)
    assert result["display_ratio"] == pytest.approx([16.8, 13.0, 9.8, 5.1, 2.1, 1.2, 1.3])
    assert result["difference"] * 100 == pytest.approx([0.63, 0.72, 1.15, 1.91, 2.67, 1.53, 4.40])
    assert result["display_compensation_bp"] == pytest.approx([2, 4, 8, 28, 144, 449, 1014])
    assert result["display_excess_bp"] == pytest.approx([38, 43, 69, 115, 160, 93, 264])
    for h, q, ratio, spread in zip(
        historical, pricing, result["ratio"], result["compensation_spread"], strict=True
    ):
        assert ratio == pytest.approx(float(Decimal(str(q)) / Decimal(str(h))))
        assert spread == pytest.approx(float(Decimal(str(h)) * Decimal("0.6")))


def test_source_bbb_seven_year_inverse_hazard_and_pricing_three_percent():
    result = c.historical_pd([7], [0.0233])
    hazard = result["average_hazard"][0]
    independent = brentq(lambda rate: 1 - np.exp(-7 * rate) - 0.0233, 0, 0.1)
    assert hazard == pytest.approx(independent, abs=1e-12)
    assert hazard * 100 == pytest.approx(0.34, abs=0.005)
    assert c.spread_hazards([7], [0.018], 0.4)["average"][0] == pytest.approx(0.03)
    assert c.hazard_comparison([0.0047], [0.0238], recovery=0.4)["compensation_spread"][
        0
    ] == pytest.approx(0.00282)
