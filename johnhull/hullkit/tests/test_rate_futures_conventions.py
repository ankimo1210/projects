"""Hull §6.1 dates, T-bill and 32nds conventions."""

from fractions import Fraction

import pytest
from hullkit import _rate_futures as f


def test_source_day_counts_accrued_and_cash_quotes():
    actual = f.day_count("2018-03-01", "2018-07-03")
    period = f.day_count("2018-03-01", "2018-09-01")
    corporate = f.day_count("2018-03-01", "2018-07-03", convention="30/360-bond")
    corporate_period = f.day_count("2018-03-01", "2018-09-01", convention="30/360-bond")
    assert [actual, period, corporate, corporate_period] == pytest.approx([124, 184, 122, 180])
    assert f.accrued_coupon(4, "2018-03-01", "2018-07-03", "2018-09-01") == pytest.approx(
        2.6957, abs=0.00005
    )
    assert f.accrued_coupon(
        4, "2018-03-01", "2018-07-03", "2018-09-01", convention="30/360-bond"
    ) == pytest.approx(2.7111, abs=0.00005)
    assert [
        f.day_count("2018-02-28", "2018-03-01"),
        f.day_count("2018-02-28", "2018-03-01", convention="30/360-bond"),
    ] == pytest.approx([1, 3])
    bill = f.bill_price(8, 91)
    assert bill["discount_amount"] == pytest.approx(2.0222, abs=0.00005)
    assert 100 * bill["period_return"] == pytest.approx(2.064, abs=0.0005)
    assert f.bill_discount_quote(99, 90) == pytest.approx(4)
    assert f.parse_32nds("120-05") * 1000 == pytest.approx(120156.25)
    assert [
        f.day_count("2018-01-10", "2018-03-05"),
        f.day_count("2018-01-10", "2018-07-10"),
    ] == pytest.approx([54, 181])
    ai = f.accrued_coupon(5.5, "2018-01-10", "2018-03-05", "2018-07-10")
    dirty = f.clean_dirty(155.5, ai)
    assert ai == pytest.approx(1.64, abs=0.005)
    assert dirty["dirty_price"] == pytest.approx(157.14, abs=0.005)
    assert round(dirty["dirty_price"], 2) * 1000 == pytest.approx(157140)


def test_independent_month_counts_fraction_and_bill_repayment():
    month_days = [31, 30, 31, 30, 2]
    assert f.day_count("2018-03-01", "2018-07-03") == pytest.approx(sum(month_days))
    assert f.parse_32nds("120-05") == pytest.approx(float(Fraction(120) + Fraction(5, 32)))
    bill = f.bill_price(8, 91)
    cost = float(Fraction(100) - Fraction(8 * 91, 360))
    assert bill["price"] == pytest.approx(cost)
    assert cost * (1 + bill["period_return"]) == pytest.approx(100)
    assert f.bill_discount_quote(bill["price"], 91) == pytest.approx(8)
