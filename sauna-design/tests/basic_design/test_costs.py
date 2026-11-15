import pytest


def test_cash_tax_and_refundable_deposit_are_distinct():
    from basic_design.costs import funding

    r = funding(100, 0.10, 0.20, 10, 20, 30, 40, 3)
    # Direct 100 + contractor10 + contingency22 =132; tax13.2.
    assert r["construction_ex_tax"] == pytest.approx(132)
    assert r["construction_cash"] == pytest.approx(145.2)
    assert r["opening_nonrefundable"] == pytest.approx(175.2)
    assert r["opening_cash"] == pytest.approx(205.2)
    assert r["funding_3m"] == pytest.approx(325.2)
    assert r["funding_6m"] == pytest.approx(445.2)


def test_missing_prices_and_duplicate_work_scope_are_rejected():
    from basic_design.costs import validate_items

    good = dict(
        id="x",
        category="floor",
        quantity=1,
        low=1,
        base=2,
        high=3,
        scope_key="tile_material",
        quantity_basis="A01",
        source_ids="A00",
    )
    validate_items([good])
    with pytest.raises(ValueError):
        validate_items([{**good, "base": None}])
    with pytest.raises(ValueError):
        validate_items([good, {**good, "id": "y"}])
    with pytest.raises(ValueError):
        validate_items([{**good, "high": 0}])


def test_large_meter_water_tariff_uses_general_business_rate():
    from basic_design.costs import tokyo_water_month

    assert tokyo_water_month(700) == pytest.approx(510180)
    assert tokyo_water_month(600) == pytest.approx(435160)
    assert tokyo_water_month(800) == pytest.approx(585200)


def test_detail_quantities_return_to_geometry_and_source():
    from basic_design.costs import load_items, quantities

    q = quantities()
    assert q["wet_floor"] == pytest.approx(64.918)
    assert q["pool_lining_net"] == pytest.approx(33.314)
    assert q["sauna_floor"] == pytest.approx(47.412528)
    rows = load_items(q)
    assert all(r["quantity_basis"] and r["scope_key"] and r["source_ids"] for r in rows)
    assert all(r["low"] > 0 for r in rows)
