"""Hull §2.6 historical gold quote and price-unit conversion."""

from decimal import Decimal

import pytest
from hullkit import _futures_market as f


def test_source_gold_quote_loss():
    a = f.quote_cash_change(1752.1, 1725.5, multiplier=100)
    assert a["cash_change"] == pytest.approx(-2660)


def test_independent_decimal_purchase_sale_and_cents_units():
    purchase = Decimal("1752.1") * Decimal(100)
    sale = Decimal("1725.5") * Decimal(100)
    expected = float(sale - purchase)
    assert f.quote_cash_change(1752.1, 1725.5)["cash_change"] == pytest.approx(expected)
    assert f.quote_cash_change(175210, 172550, price_unit=0.01)["cash_change"] == pytest.approx(
        expected
    )
    assert f.quote_cash_change(1752.1, 1725.5, side="short", contracts=2)[
        "cash_change"
    ] == pytest.approx(-2 * expected)
