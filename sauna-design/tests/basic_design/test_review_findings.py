import pytest


def test_section_description_tracks_changed_service_band():
    from basic_design.sections import describe_case, section_case

    q = section_case(1.2, 0.06, -0.20, 0.25, 0.70, 3, 0.35)
    assert "2.04" in describe_case(q)
    assert "2.09" not in describe_case(q)


def test_external_landing_exceeds_the_sauna_wall_in_plan():
    from basic_design.sections import external_stair_footprint, section_case

    b = external_stair_footprint(section_case(1.2, 0.06, -0.2, 0.25, 0, 3, 0.35), 11.84, 9.0)
    assert b["landing_xyxy"] == pytest.approx((11.84, 10.96, 12.74, 11.86))
    assert b["overrun_past_finished_wall_m"] == pytest.approx(1.472)


def test_normal_cycle_reaches_rest_after_water():
    from basic_design.operations import normal_cycle

    path = normal_cycle()
    water_indices = [i for i, (x, y) in enumerate(path) if 10.84 <= x <= 12.62 and 6.8 <= y <= 8.7]
    assert water_indices
    assert any(x < 6 and 3.6 < y < 9 for x, y in path[max(water_indices) + 1 :])


def test_all_sauna_alarm_points_are_inside_their_rooms():
    from basic_design.audit import load_basis
    from basic_design.plans import alarm_points

    plan = load_basis()[2]
    points = alarm_points(plan)
    for rid in ["main", "self", "dry"]:
        r = next(r for r in plan["rooms"] if r["id"] == rid)
        x, y, w, h = r["rect"]
        a, b = points[rid]
        assert x < a < x + w and y < b < y + h
    assert 0 < points["receiver"][0] < 4 and 0 < points["receiver"][1] < 3.6


def test_known_tank_delivery_deficit_is_reported():
    from basic_design.sections import delivery_clearance

    r = delivery_clearance(1.0, 0.9, 0.05)
    assert r["frame_clear_width_m"] == pytest.approx(0.8)
    assert r["deficit_m"] == pytest.approx(0.2)
    assert r["can_pass_as_one_piece"] is False


def test_power_profiles_include_named_auxiliaries_and_heater_shortfall():
    from basic_design.services import electrical_envelopes

    rows = electrical_envelopes(
        {"H-main": 10, "CHEM": 0.5, "CO2": 0.3, "TV": 0.2},
        {"H-main": 12},
        {"normal": 12},
        3,
        0.9,
        0.2,
    )
    gas = next(q for q in rows if q["heater_basis"] == "candidate" and q["case"] == "gas")
    hp = next(q for q in rows if q["heater_basis"] == "thermal_envelope" and q["case"] == "normal")
    assert gas["connected_electric_kw"] == pytest.approx(12)
    assert hp["connected_electric_kw"] == pytest.approx(17)
    assert hp["components_kw"]["CHEM"] == 0.5
    assert hp["components_kw"]["H-main"] == 12
