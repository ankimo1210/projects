"""Hull §5.14 symbolic risk-premium relation with independent DCF and P-law MC."""

import math

import numpy as np
import pytest
from hullkit import _forward_pricing as f
from scipy.optimize import brentq


def test_source_three_symbolic_required_return_cases():
    for k in [0.03, 0.05, 0.08]:
        price = f.expected_spot_forward(100, 0.05, k, 2)
        root = brentq(lambda x, k=k: -x * math.exp(-0.05 * 2) + 100 * math.exp(-k * 2), 0, 200)
        assert price == pytest.approx(root)
        assert np.sign(price - 100) == pytest.approx(np.sign(0.05 - k))


def test_independent_seeded_physical_expected_discounted_cash():
    samples = 100 * np.exp(-(0.3**2) / 2 + 0.3 * np.random.default_rng(514).standard_normal(200000))
    price = f.expected_spot_forward(100, 0.05, 0.08, 2)
    cash = samples * math.exp(-0.08 * 2) - price * math.exp(-0.05 * 2)
    se = np.std(cash, ddof=1) / math.sqrt(len(cash))
    assert abs(np.mean(cash)) < 6 * se
