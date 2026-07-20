"""Japanese inflation-linked government bond convention and valuation tests."""

from dataclasses import replace
from datetime import date

import pytest
from hullkit import jgbi


def _monthly_cpi(*, falling: bool = False) -> dict[date, float]:
    values: dict[date, float] = {}
    index = 105.0
    for year in range(2025, 2030):
        for month in range(1, 13):
            values[date(year, month, 1)] = index
            index += -0.20 if falling else 0.15
    return values


def _terms(*, principal_floor: bool = True) -> jgbi.JGBITerms:
    return jgbi.JGBITerms(
        issue_date=date(2026, 7, 10),
        maturity_date=date(2028, 7, 10),
        coupon_dates=(
            date(2027, 1, 10),
            date(2027, 7, 10),
            date(2028, 1, 10),
            date(2028, 7, 10),
        ),
        coupon_rate=0.005,
        face_value=100_000_000.0,
        base_reference_date=date(2026, 7, 10),
        principal_floor=principal_floor,
    )


def test_reference_index_before_on_and_after_tenth_matches_hand_calculation() -> None:
    fixings = {
        date(2026, 3, 1): 100.0,
        date(2026, 4, 1): 103.1,
        date(2026, 5, 1): 104.8,
    }
    before = 100.0 + (103.1 - 100.0) * 25.0 / 30.0
    after = 103.1 + (104.8 - 103.1) * 10.0 / 31.0
    assert jgbi.jgbi_reference_index(date(2026, 7, 5), fixings) == pytest.approx(
        round(before, 3)
    )
    assert jgbi.jgbi_reference_index(date(2026, 7, 10), fixings) == 103.1
    assert jgbi.jgbi_reference_index(date(2026, 7, 20), fixings) == pytest.approx(
        round(after, 3)
    )


def test_index_ratio_rounds_only_after_reference_indices() -> None:
    terms = _terms()
    fixings = _monthly_cpi()
    reference = jgbi.jgbi_reference_index(date(2027, 2, 17), fixings)
    base = jgbi.jgbi_reference_index(terms.base_reference_date, fixings)
    expected = round(reference / base, 5)
    assert jgbi.jgbi_indexation_coefficient(
        date(2027, 2, 17), terms, fixings
    ) == pytest.approx(expected)


def test_reopened_issue_uses_explicit_original_base_reference_date() -> None:
    fixings = _monthly_cpi()
    original = _terms()
    reopened = replace(original, issue_date=date(2026, 11, 10))
    day = date(2028, 7, 10)
    assert jgbi.jgbi_indexation_coefficient(day, original, fixings) == (
        jgbi.jgbi_indexation_coefficient(day, reopened, fixings)
    )


def test_principal_floor_changes_redemption_only_and_never_coupons() -> None:
    fixings = _monthly_cpi(falling=True)
    floored = jgbi.jgbi_cashflows(_terms(principal_floor=True), fixings)
    unfloored = jgbi.jgbi_cashflows(_terms(principal_floor=False), fixings)
    assert [row.coupon for row in floored] == pytest.approx([row.coupon for row in unfloored])
    assert floored[-1].index_ratio < 1.0
    assert floored[-1].principal == _terms().face_value
    assert unfloored[-1].principal == pytest.approx(
        _terms().face_value * unfloored[-1].index_ratio
    )
    assert floored[-1].principal > unfloored[-1].principal


def test_clean_dirty_nominal_settlement_and_real_yield_reconcile() -> None:
    terms = _terms()
    fixings = _monthly_cpi()
    settlement = date(2027, 3, 17)
    clean = jgbi.jgbi_real_clean_price(0.008, settlement, terms)
    recovered_yield = jgbi.jgbi_real_yield(clean, settlement, terms)
    assert recovered_yield == pytest.approx(0.008, abs=1e-12)

    amount = jgbi.jgbi_nominal_settlement_amount(clean, settlement, terms, fixings)
    ratio = jgbi.jgbi_indexation_coefficient(settlement, terms, fixings)
    accrued = jgbi.jgbi_accrued_interest(settlement, terms, fixings)
    assert amount == pytest.approx(terms.face_value * ratio * clean / 100.0 + accrued)


def test_deterministic_nominal_present_value_and_exact_breakeven() -> None:
    terms = _terms(principal_floor=False)
    fixings = _monthly_cpi()
    curve = ((0.0, 1.0, 2.0, 3.0), (0.01, 0.01, 0.01, 0.01))
    valuation = date(2026, 7, 10)
    cashflows = jgbi.jgbi_cashflows(terms, fixings)
    undiscounted = sum(row.total for row in cashflows)
    assert jgbi.jgbi_nominal_present_value(valuation, terms, fixings, curve) < undiscounted
    assert jgbi.jgbi_breakeven_inflation(0.015, 0.005) == pytest.approx(
        1.015 / 1.005 - 1.0
    )


def test_invalid_jgbi_terms_are_rejected() -> None:
    with pytest.raises(ValueError, match="final coupon"):
        replace(_terms(), maturity_date=date(2029, 1, 10)).validate()
    with pytest.raises(ValueError, match="settlement"):
        jgbi.jgbi_real_clean_price(0.01, date(2030, 1, 1), _terms())
