import pytest


def test_water_energy_and_time_are_not_mixed():
    from basic_design.services import shower_kw, water_kw

    assert water_kw(1, 10, 1) == pytest.approx(11.6277777778)
    assert water_kw(1, 10, 2) == pytest.approx(5.8138888889)
    assert shower_kw(24, 25) == pytest.approx(41.86)


def test_chiller_rejects_cooling_plus_compressor_power():
    from basic_design.services import chiller

    c = chiller(18, 3)
    assert c == {"cooling_kw": 18, "electric_kw": 6, "heat_rejection_kw": 24}
    with pytest.raises(ValueError):
        chiller(18, 0)


def test_summer_ventilation_can_add_moisture():
    from basic_design.services import moisture_balance

    b = moisture_balance(1000, 32, 0.70, 28, 0.60, 4)
    assert b["dehumidification_kg_h"] > 4
    assert b["ventilation_added_kg_h"] > 0


def test_heatup_power_changes_with_warmup_time():
    from basic_design.services import sauna_load

    a = sauna_load(30, 50, 90, 25, 6, 0.4, 500, 100, 2, 1, 1)
    b = sauna_load(30, 50, 90, 25, 6, 0.4, 500, 100, 4, 1, 1)
    assert a["steady_kw"] == pytest.approx(b["steady_kw"])
    assert a["warmup_storage_kw"] == pytest.approx(2 * b["warmup_storage_kw"])
    assert a["suggested_evaluation_kw"] > a["steady_kw"]
