"""Tax-layer tests: after-tax math, loss carryforward (offset + expiry), NISA
zero-tax, and the pre-tax vs taxable vs NISA comparison.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from quantkit import tax as TX

RATE = 0.20315


def _yearly(returns_by_year: dict[str, float]) -> pd.Series:
    idx = pd.to_datetime([f"{y}-06-01" for y in returns_by_year])
    return pd.Series(list(returns_by_year.values()), index=idx)


def test_config_from_yaml_and_nisa():
    cfg = {"taxable_account": {"capital_gains_rate": 0.20315, "loss_carryforward_years": 3}}
    t = TX.TaxConfig.from_config(cfg)
    assert t.capital_gains_rate == pytest.approx(0.20315) and t.loss_carryforward_years == 3
    n = TX.TaxConfig.nisa()
    assert n.capital_gains_rate == 0.0 and n.name == "nisa"


def test_gain_is_taxed_at_rate():
    r = _yearly({"2020": 0.10})
    df = TX.annual_after_tax(r, TX.TaxConfig())
    assert df.loc[2020, "tax"] == pytest.approx(RATE * 0.10)
    assert df.loc[2020, "after_tax_return"] == pytest.approx(0.10 - RATE * 0.10)


def test_loss_carryforward_offsets_next_gain():
    r = _yearly({"2020": 0.10, "2021": -0.10, "2022": 0.10})
    df = TX.annual_after_tax(r, TX.TaxConfig())
    assert df.loc[2020, "tax"] == pytest.approx(RATE * 0.10)
    assert df.loc[2021, "tax"] == 0.0  # a loss year is never taxed
    assert df.loc[2022, "tax"] == pytest.approx(0.0)  # offset by 2021's banked loss
    assert df.loc[2022, "taxable_gain"] == pytest.approx(0.0)


def test_loss_carryforward_expires():
    # loss in 2020, next gain in 2024 (> 3-year window) -> loss expired, full tax
    r = _yearly({"2020": -0.10, "2024": 0.10})
    df = TX.annual_after_tax(r, TX.TaxConfig())
    assert df.loc[2024, "tax"] == pytest.approx(RATE * 0.10)


def test_dividends_are_taxed_even_in_a_loss_year():
    # total return -5%, of which 2% was dividend income (taxed) and -7% capital (banked)
    r = _yearly({"2020": -0.05})
    df = TX.annual_after_tax(r, TX.TaxConfig(), dividend_yield=0.02)
    assert df.loc[2020, "dividend_tax"] == pytest.approx(RATE * 0.02)  # income, no loss offset
    assert df.loc[2020, "capital_gains_tax"] == 0.0  # capital portion is a loss
    assert df.loc[2020, "tax"] == pytest.approx(RATE * 0.02)
    assert df.loc[2020, "after_tax_return"] == pytest.approx(-0.05 - RATE * 0.02)


def test_dividend_and_capital_split_sums_to_total_tax():
    r = _yearly({"2020": 0.10})  # 2% dividend + 8% capital gain
    df = TX.annual_after_tax(r, TX.TaxConfig(), dividend_yield=0.02)
    assert df.loc[2020, "dividend_tax"] == pytest.approx(RATE * 0.02)
    assert df.loc[2020, "capital_gains_tax"] == pytest.approx(RATE * 0.08)
    assert df.loc[2020, "tax"] == pytest.approx(RATE * 0.10)


def test_nisa_has_zero_tax():
    r = _yearly({"2020": 0.10, "2021": 0.20})
    df = TX.annual_after_tax(r, TX.TaxConfig.nisa())
    assert (df["tax"] == 0.0).all()
    assert df["after_tax_return"].tolist() == pytest.approx([0.10, 0.20])


def test_compare_accounts_orders_pretax_nisa_taxable():
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2015-01-01", periods=252 * 6)
    r = pd.Series(rng.normal(0.0006, 0.01, len(idx)), index=idx)  # positive drift
    cmp = TX.compare_accounts(r, TX.TaxConfig())
    assert cmp["nisa_cagr"] == pytest.approx(cmp["pretax_cagr"], abs=1e-9)  # NISA = pre-tax
    assert cmp["taxable_cagr"] < cmp["pretax_cagr"]  # tax drags
    assert cmp["total_tax_paid"] > 0 and cmp["annual_tax_drag"] > 0


def test_after_tax_equity_is_annual_curve():
    r = _yearly({"2020": 0.10, "2021": 0.10})
    eq = TX.after_tax_equity(r, TX.TaxConfig.nisa())
    assert len(eq) == 2 and eq.iloc[-1] == pytest.approx(1.10 * 1.10)
