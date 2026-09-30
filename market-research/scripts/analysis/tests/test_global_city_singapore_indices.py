"""Singapore government price/rent indices are aligned without yield claims."""

import pytest
from global_city_singapore_indices import align_indices, parse_price, parse_rent


def test_parse_long_price_and_wide_rent_with_labels():
    price = parse_price(
        [
            {"quarter": "2015-Q1", "market_segment": "Core Central Region", "price_index": "100"},
            {"quarter": "2015-Q2", "market_segment": "Core Central Region", "price_index": "110"},
        ]
    )
    rent = parse_rent(
        [{"DataSeries": "Core Central Region", "20151Q": "100", "20152Q": "105", "_id": 1}]
    )
    assert price == {("2015Q1", "Core Central Region"): 100, ("2015Q2", "Core Central Region"): 110}
    assert rent == {("2015Q1", "Core Central Region"): 100, ("2015Q2", "Core Central Region"): 105}


def test_alignment_rebases_both_and_does_not_infer_absolute_yield():
    price = {("2015Q1", "Core Central Region"): 80, ("2026Q2", "Core Central Region"): 160}
    rent = {("2015Q1", "Core Central Region"): 120, ("2026Q2", "Core Central Region"): 180}
    result = align_indices(price, rent, base="2015Q1")
    assert result[0]["relative_price_rent_base_100"] == 100
    assert result[1]["price_base_100"] == 200
    assert result[1]["rent_base_100"] == 150
    assert result[1]["relative_price_rent_base_100"] == pytest.approx(133.3333333333)
    assert "gross_yield" not in result[1] and "noi" not in result[1]


def test_reject_duplicate_and_missing_pairs():
    item = {"quarter": "2015-Q1", "market_segment": "Core Central Region", "price_index": "100"}
    with pytest.raises(ValueError, match="Duplicate"):
        parse_price([item, item])
    with pytest.raises(ValueError, match="different coverage"):
        align_indices({("2015Q1", "Core Central Region"): 100}, {}, base="2015Q1")
