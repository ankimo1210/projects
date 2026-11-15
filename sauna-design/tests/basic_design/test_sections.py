import pytest


def test_raising_deck_preserves_water_depth_and_reveals_lost_headroom():
    from basic_design.sections import section_case

    a = section_case(1.20, 0.06, -0.20, 0.25, 1.31, 3.0, 0.30)
    b = section_case(1.20, 0.06, -0.20, 0.25, 0.0, 3.0, 0.30)
    assert a["deck_z_m"] == pytest.approx(0.0)
    assert b["deck_z_m"] == pytest.approx(1.31)
    assert b["water_z_m"] - b["bottom_z_m"] == pytest.approx(1.20)
    assert b["clear_headroom_m"] == pytest.approx(1.39)
    assert b["n_risers"] == 8
    assert b["stair_run_m"] == pytest.approx(1.96)
    assert b["structural_adequacy"] == "unknown"


def test_hybrid_needs_floor_area_even_when_pit_is_smaller():
    from basic_design.sections import section_case

    c = section_case(1.20, 0.06, -0.20, 0.25, 0.70, 3.0, 0.30)
    assert c["deck_z_m"] == pytest.approx(0.61)
    assert c["clear_headroom_m"] == pytest.approx(2.09)
    assert c["n_risers"] == 4
    assert c["stair_and_landing_area_m2"] == pytest.approx(1.566)


def test_negative_depth_is_rejected():
    from basic_design.sections import section_case

    with pytest.raises(ValueError):
        section_case(-1, 0.06, -0.2, 0.25, 0, 3.0, 0.3)
