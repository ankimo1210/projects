"""Hull §10.4: stock adjustments, legacy expiry cycles and value decomposition."""

import importlib
from datetime import date, timedelta
from fractions import Fraction

import numpy as np
import pytest


def model():
    return importlib.import_module("hullkit._option_mechanics")


def test_printed_split_and_stock_dividend_examples():
    split = model().adjust_stock_option(30, 100, 2, 1)
    assert split["strike"] == pytest.approx(15)
    assert split["units"] == pytest.approx(200)
    dividend = model().stock_dividend_adjustment(15, 100, 0.25)
    assert dividend["strike"] == pytest.approx(12)
    assert dividend["units"] == pytest.approx(125)
    assert model().stock_dividend_adjustment(30, 100, 0.2)["price_scale"] == pytest.approx(5 / 6)


@pytest.mark.parametrize("new,old", [(2, 1), (6, 5), (5, 4), (1, 5)])
def test_fraction_reference_preserves_exercise_cash_and_adjusted_payoff(new, old):
    row = model().adjust_stock_option(30, 100, new, old)
    ratio = Fraction(new, old)
    expected_strike = Fraction(30) / ratio
    expected_units = Fraction(100) * ratio
    assert row["strike"] == pytest.approx(float(expected_strike))
    assert row["units"] == pytest.approx(float(expected_units))
    assert row["strike"] * row["units"] == pytest.approx(3000)
    for spot in (0, 20, 30, 35, 50):
        adjusted = model().option_cashflows(
            spot / float(ratio), row["strike"], 0, multiplier=row["units"]
        )["payoff"]
        cash = Fraction(100) * (spot - 30) if spot > 30 else Fraction(0)
        assert adjusted == pytest.approx(float(cash))


def test_printed_legacy_expiry_cycles_and_contract_count():
    m = model()
    first = m.legacy_option_expiries(2026, 1, 1)
    assert first == [(2026, 1), (2026, 2), (2026, 4), (2026, 7)]
    assert m.legacy_option_expiries(2026, 1, 1, after_current_expiry=True) == [
        (2026, 2),
        (2026, 3),
        (2026, 4),
        (2026, 7),
    ]
    assert m.legacy_option_expiries(2026, 5, 1) == [(2026, 5), (2026, 6), (2026, 7), (2026, 10)]
    assert len(first) * 5 * 2 == pytest.approx(40)


def test_legacy_cycle_calendar_against_independent_date_enumeration():
    for year in (2026, 2027):
        for month in range(1, 13):
            for cycle in (1, 2, 3):
                for expired in (False, True):
                    start = date(year, month, 15) + timedelta(days=31 * expired)
                    following = start + timedelta(days=31)
                    near = [
                        date(start.year, start.month, 1),
                        date(following.year, following.month, 1),
                    ]
                    quarterlies = sorted(
                        date(y, mo, 1)
                        for y in range(year, year + 3)
                        for mo in range(cycle, 13, 3)
                        if date(y, mo, 1) > near[1]
                    )
                    expected = [(d.year, d.month) for d in [*near, *quarterlies[:2]]]
                    assert (
                        model().legacy_option_expiries(
                            year, month, cycle, after_current_expiry=expired
                        )
                        == expected
                    )
    # Adopt the next two cycle months strictly after the two near months.
    assert model().legacy_option_expiries(2026, 3, 1) == [
        (2026, 3),
        (2026, 4),
        (2026, 7),
        (2026, 10),
    ]


@pytest.mark.parametrize("kind,spot", [("call", [90, 100, 110]), ("put", [110, 100, 90])])
def test_intrinsic_time_value_and_spot_moneyness(kind, spot):
    row = model().option_value_components(spot, 100, [4, 7, 12], kind=kind)
    assert row["intrinsic"] == pytest.approx([0, 0, 10])
    assert row["time_value"] == pytest.approx([4, 7, 2])
    assert row["moneyness"].tolist() == ["OTM", "ATM", "ITM"]
    assert np.allclose(row["intrinsic"] + row["time_value"], [4, 7, 12], atol=1e-12, rtol=1e-12)
    # A decomposition also exposes a price below the American intrinsic bound.
    assert model().option_value_components(spot[-1], 100, 5, kind=kind)[
        "time_value"
    ] == pytest.approx(-5)


@pytest.mark.parametrize(
    "call",
    [
        lambda m: m.adjust_stock_option(30, 100, 0, 1),
        lambda m: m.adjust_stock_option(30, 100, 2, 0),
        lambda m: m.stock_dividend_adjustment(30, 100, -1),
        lambda m: m.legacy_option_expiries(2026, 0, 1),
        lambda m: m.legacy_option_expiries(2026, 1, 4),
    ],
)
def test_undefined_contract_adjustment_or_calendar_rejected(call):
    with pytest.raises(ValueError):
        call(model())
