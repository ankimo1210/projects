from __future__ import annotations

import numpy as np
import pandas as pd

from quantcurve.pricing import model_quote_from_discount


def _discount(t):
    values = np.asarray(t, dtype=float)
    return np.exp(-(0.01 + 0.001 * values) * values)


def test_direct_discount_deposit_uses_simple_rate_in_decimal_units() -> None:
    row = pd.Series({"instrument_type": "deposit", "maturity_years": 0.25})
    expected = (1.0 / float(_discount(0.25)) - 1.0) / 0.25
    assert model_quote_from_discount(row, _discount) == expected


def test_direct_discount_fractional_ois_uses_terminal_stub_accrual() -> None:
    row = pd.Series({"instrument_type": "ois_swap", "maturity_years": 2.25})
    times = np.array([0.5, 1.0, 1.5, 2.0, 2.25])
    accruals = np.array([0.5, 0.5, 0.5, 0.5, 0.25])
    expected = (1.0 - float(_discount(2.25))) / float(np.dot(accruals, _discount(times)))
    assert abs(model_quote_from_discount(row, _discount) - expected) < 1e-15


def test_direct_discount_fractional_bond_has_regular_coupons_and_principal_at_maturity() -> None:
    row = pd.Series({"instrument_type": "bond", "maturity_years": 2.25, "payment_frequency": 2, "coupon_rate": 0.03})
    times = np.array([0.5, 1.0, 1.5, 2.0, 2.25])
    cashflows = np.array([1.5, 1.5, 1.5, 1.5, 100.0])
    expected = float(np.dot(cashflows, _discount(times)))
    assert abs(model_quote_from_discount(row, _discount) - expected) < 1e-13


def test_direct_discount_pricing_is_finite_with_negative_rates() -> None:
    discount = lambda t: np.exp(0.01 * np.asarray(t, dtype=float))
    rows = [
        pd.Series({"instrument_type": "deposit", "maturity_years": 1.0}),
        pd.Series({"instrument_type": "ois_swap", "maturity_years": 3.25}),
        pd.Series({"instrument_type": "bond", "maturity_years": 4.25, "payment_frequency": 2, "coupon_rate": 0.02}),
    ]
    assert all(np.isfinite(model_quote_from_discount(row, discount)) for row in rows)
