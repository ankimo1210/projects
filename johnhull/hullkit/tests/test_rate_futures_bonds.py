"""Hull §6.2 conversion factors and Examples6.1/6.2."""

import math
from fractions import Fraction

import numpy as np
import pytest
from hullkit import _rate_futures as f


def test_source_all_quote_invoice_cf_ctd_and_forward_values():
    quotes = ["179-20", "139-025", "125-132", "110-127", "93-08"]
    assert [f.parse_32nds(q) for q in quotes] == pytest.approx(
        [179.625, 139.078125, 125.4140625, 110.3984375, 93.25]
    )
    invoice = f.treasury_invoice(120, 1.38, 3)
    assert [invoice["price"], invoice["cash"]] == pytest.approx([168.60, 168600])
    a = f.conversion_factor(0.1, 242)
    b = f.conversion_factor(0.08, 220)
    assert [a["dirty_price"], a["factor"]] == pytest.approx([146.23, 1.4623], abs=0.005)
    assert b["first_coupon_value"] == pytest.approx(125.8323, abs=0.00005)
    assert 100 * (math.sqrt(1.03) - 1) == pytest.approx(1.4889, abs=0.00005)
    assert [b["dirty_price"], b["clean_price"]] == pytest.approx([123.99, 121.99], abs=0.005)
    assert b["factor"] == pytest.approx(1.2199, abs=0.00005)
    c = f.cheapest_delivery([99.5, 143.5, 119.75], [1.0382, 1.5188, 1.2615], 93.25)
    assert c["costs"] == pytest.approx([2.69, 1.87, 2.12], abs=0.005)
    assert c["index"] == 1
    x = f.bond_futures_quote(115, 6, 60, 122, 270, 148, 35, 0.1, 1.6)
    assert x["cash_spot"] == pytest.approx(116.978, abs=0.0005)
    assert x["coupon_time"] == pytest.approx(0.3342, abs=0.00005)
    assert x["income_pv"] == pytest.approx(5.803, abs=0.0005)
    assert x["delivery_time"] == pytest.approx(0.7397, abs=0.00005)
    assert [x["cash_forward"], x["clean_forward"], x["futures_quote"]] == pytest.approx(
        [119.711, 114.859, 71.79], abs=0.005
    )


def test_independent_annuity_and_financing_ledger():
    g = 1.03
    n = 40
    annuity = 5 * (1 - g ** (-n)) / 0.03 + 100 * g ** (-n)
    assert f.conversion_factor(0.1, 242)["factor"] == pytest.approx(annuity / 100)
    # At the first quarter coupon: that coupon plus 36 regular future payments.
    quarter_value = 4 + 4 * (1 - g ** (-36)) / 0.03 + 100 * g ** (-36)
    quarter_clean = quarter_value / math.sqrt(g) - 2
    assert f.conversion_factor(0.08, 220)["factor"] == pytest.approx(quarter_clean / 100)
    x = f.bond_futures_quote(115, 6, 60, 122, 270, 148, 35, 0.1, 1.6)
    initial = 115 + float(Fraction(60, 182)) * 6
    loan = initial * math.exp(0.1 * 122 / 365) - 6
    loan *= math.exp(0.1 * 148 / 365)
    quote = (loan - float(Fraction(148, 183)) * 6) / 1.6
    assert x["futures_quote"] == pytest.approx(quote, abs=1e-10)
    assert f.conversion_factor(0.1, 240)["factor"] == pytest.approx(
        f.conversion_factor(0.1, 242)["factor"]
    )
    assert f.conversion_factor(0.1, 243)["factor"] != pytest.approx(
        f.conversion_factor(0.1, 242)["factor"]
    )
    for rate in [0.04, 0.08]:
        coupons = np.array([0.04, 0.10])
        periods = np.arange(1, 41)
        prices = np.array(
            [
                np.sum(100 * c / 2 * (1 + rate / 2) ** (-periods)) + 100 * (1 + rate / 2) ** (-40)
                for c in coupons
            ]
        )
        factors = np.array([f.conversion_factor(c, 240)["factor"] for c in coupons])
        costs = prices / factors
        # Futures quoted off the cheapest deliverable; choice switches with yield.
        selected = f.cheapest_delivery(prices, factors, costs.min())["index"]
        assert selected == (1 if rate < 0.06 else 0)
