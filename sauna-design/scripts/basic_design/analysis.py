"""Assemble section, operation and service balances from the common input register."""

import json

from .audit import DATA, ROOT, build_audit, dump, load_basis, write_csv
from .operations import normal_cycle, rest_demand, simulate_pool
from .sections import delivery_clearance, describe_case, external_stair_footprint, section_case
from .services import (
    chiller,
    electrical_envelopes,
    moisture_balance,
    sauna_load,
    shower_kw,
    water_kw,
)


def calculate():
    basis = build_audit()
    config, p, plan = load_basis()
    variants = json.loads((ROOT / "plan/basic_design/variants.json").read_text())["variants"]
    cases = []
    for v in variants:
        s = section_case(
            1.2,
            0.06,
            p["slab_top_z"],
            p["pool_assembly"],
            v["pit_m"],
            p["soffit_z"],
            p["service_depth"],
        )
        cases.append(
            {
                **v,
                **s,
                "decision": describe_case(s),
                "external_access_plan": external_stair_footprint(s, 11.84, 9.0),
            }
        )
    loads = []
    for pool in basis["pools"]:
        a = pool["surface_m2"]
        d = pool["depth"]
        # Geometric mass inventory, not slab load verification. Structure/finish are explicit allowances.
        shell = (
            2 * ((pool["rect"][2] + 0.3) + (pool["rect"][3] + 0.3)) * d * 0.12 * 2300
            + a * 0.15 * 2300
        )
        finish = (a + 2 * (pool["rect"][2] + pool["rect"][3]) * d) * 0.02 * 2200
        people = {"deep": 3, "seated": 3, "carbonPool": 5}[pool["id"]] * 90
        loads.append(
            {
                "pool_id": pool["id"],
                "water_gross_kg": pool["gross_water_m3"] * 1000,
                "water_less_known_steps_kg": None
                if pool["water_less_known_steps_m3"] is None
                else pool["water_less_known_steps_m3"] * 1000,
                "hypothetical_RC_shell_kg": shell,
                "finish_allowance_kg": finish,
                "people_allowance_kg": people,
                "water_pressure_at_bottom_kpa": d * 9.80665,
                "gross_mass_inventory_kg": pool["gross_water_m3"] * 1000 + shell + finish + people,
                "note": "RC150mm floor/120mm walls and finish20mm are inventory assumptions, not structural design; stairs and support not included.",
            }
        )
    operations = {
        "rest": [rest_demand(20, 17, 24, 40), rest_demand(20, 20, 24, 40)],
        "pool_cases": [],
        "routes": basis["water_routes"],
        "normal_cycle": normal_cycle(),
        "waiting_zone_provided": False,
        "note": "Pool positions5 is a static layout assumption; entry/exit time and temperature-choice preference reduce real service capacity.",
    }
    for label, arrivals in [
        ("一斉20人", [0] * 20),
        ("2分に20人", [i * 120 / 19 for i in range(20)]),
        ("5分に20人", [i * 300 / 19 for i in range(20)]),
    ]:
        for duration in [45, 60, 90]:
            q = simulate_pool(arrivals, 5, duration)
            operations["pool_cases"].append({"case": label, **q})
    sauna = []
    for rid in ["main", "self", "dry"]:
        d = basis["sauna_dimensions"][rid]
        w, h = d["room_inner"]
        height = d["ceiling"]
        area = 2 * (w + h) * height + w * h
        room_cases = []
        for ach in [4, 6, 8]:
            for hours in [2, 4]:
                q = sauna_load(
                    w * h * height,
                    area,
                    p[rid + "_C"],
                    p["dry_air_C"],
                    ach,
                    p["wall_U"],
                    p[rid + "_wood_kg"],
                    p[rid + "_stone_kg"],
                    hours,
                    0 if rid == "dry" else p[rid + "_loyly_l_h"],
                    p["main_door_kw"] if rid == "main" else p["sub_door_kw"],
                )
                room_cases.append({"ach": ach, "warmup_h": hours, **q})
        base = next(q for q in room_cases if q["ach"] == 6 and q["warmup_h"] == 2)
        sauna.append(
            {
                "room": rid,
                "volume_m3": w * h * height,
                "heat_area_m2": area,
                "base": base,
                "sensitivity": room_cases,
            }
        )
    cooling = []
    circulation = []
    for pool in basis["pools"]:
        rid = pool["id"]
        vol = pool["gross_water_m3"]
        circulation.append(
            {
                "pool_id": rid,
                "gross_water_m3": vol,
                "flow_1_turnover_m3_h": vol,
                "flow_base_2_turnovers_m3_h": vol * p["bath_turnovers"],
                "flow_3_turnovers_m3_h": 3 * vol,
                "pump_head_m": None,
                "pump_selection": "未選定・揚程/配管損失/逆洗条件が必要",
            }
        )
        if rid == "carbonPool":
            continue
        target = p[rid + "_C"]
        hold = p[rid + "_user_heat"]
        for hours in [2, 4, 6]:
            pull = water_kw(vol, p["fill_water_C"] - target, hours)
            c = chiller(pull + hold, p["chiller_COP"])
            cooling.append(
                {
                    "pool_id": rid,
                    "cooldown_h": hours,
                    "target_C": target,
                    "pull_down_kw": pull,
                    "maintenance_allowance_kw": hold,
                    **c,
                }
            )
    hot = []
    for feed in [5, 15, 25]:
        for n in [3, 6]:
            flow = n * p["shower_l_min"]
            thermal = shower_kw(flow, p["shower_C"] - feed)
            hot.append(
                {
                    "feed_C": feed,
                    "fixtures_simultaneous": n,
                    "mixed_l_min": flow,
                    "thermal_kw": thermal,
                    "hot_60C_l_min": flow * (p["shower_C"] - feed) / (p["hot_store_C"] - feed),
                }
            )
    carbon = next(q for q in basis["pools"] if q["id"] == "carbonPool")
    carbon_fill = water_kw(carbon["gross_water_m3"], p["carbon_C"] - p["cold_feed_C"], 4)
    water_day = []
    poolfill = sum(q["gross_water_m3"] for q in basis["pools"])
    for guests in [150, 200, 300]:
        shower = guests * p["shower_min_visit"] * p["shower_l_min"] / 1000
        makeup = guests * p["fresh_makeup_l_person"] / 1000
        water_day.append(
            {
                "visitors": guests,
                "shower_m3": shower,
                "assumed_full_pool_fill_m3": poolfill,
                "makeup_allowance_m3": makeup,
                "backwash_allowance_m3": p["backwash_day_m3"],
                "daily_total_m3": shower + poolfill + makeup + p["backwash_day_m3"],
                "note": "Full fill once/day is an assumption; carbon steps ignored. Toilets/laundry/cleaning not included.",
            }
        )
    wet_area = sum(
        r["zone_area_m2"] for r in basis["rooms"] if r["id"] in ("water", "wash", "carbon")
    )
    wet_vol = wet_area * (p["soffit_z"] - p["service_depth"])
    wet_air = wet_vol * p["bath_ACH"]
    vent = []
    for r in basis["rooms"]:
        rid = r["id"]
        if rid in ("main", "self", "dry"):
            ach = p["sauna_ACH"]
        elif rid in ("water", "wash", "carbon"):
            ach = p["bath_ACH"]
        elif rid in ("rest", "restExt"):
            ach = p["rest_ACH"]
        elif rid in ("change", "entry"):
            ach = p["locker_ACH"]
        elif rid == "wc":
            ach = p["wc_ACH"]
        elif rid == "plant":
            ach = p[
                "plant_ACH"
            ]  # heat balance below takes precedence over this initial air-change screen
        else:
            continue
        vent.append(
            {
                "room": rid,
                "volume_basis": r["basis"],
                "volume_m3": r["calculation_volume_m3"],
                "ach": ach,
                "flow_m3_h": r["calculation_volume_m3"] * ach,
            }
        )
    moisture = []
    for season, t, rh in [
        ("夏", p["outside_summer_C"], p["outside_summer_RH"]),
        ("冬", p["outside_winter_C"], p["outside_winter_RH"]),
    ]:
        for internal in [2, 4, 6]:
            moisture.append(
                {
                    "season": season,
                    "outside_C": t,
                    "outside_RH": rh,
                    **moisture_balance(wet_air, t, rh, p["bath_air_C"], p["bath_RH"], internal),
                }
            )
    base_cooling = [q for q in cooling if q["cooldown_h"] == 4]
    electric = {
        "H-main": 24.8,
        "H-self": 12,
        "H-dry": 9,
        "CH-deep": base_cooling[0]["electric_kw"],
        "CH-seated": base_cooling[1]["electric_kw"],
        "pumps": 3.0,
        "fans": 3.0,
        "dehumidification_AC": 8.0,
        "lighting": 2.0,
        "TV_controls": 0.2,
        "CO2": 0.3,
        "CHEM": 0.5,
        "other_allowance": 3.0,
    }
    peak = lambda feed, n: next(
        q["thermal_kw"] for q in hot if q["feed_C"] == feed and q["fixtures_simultaneous"] == n
    )
    dhw_cases = {
        "HP-normal": peak(15, 3) + p["carbon_hold_heat"],
        "HP-startup": peak(15, 3) + carbon_fill + p["carbon_hold_heat"],
        "HP-winter6": peak(5, 6)
        + water_kw(carbon["gross_water_m3"], p["carbon_C"] - 5, 4)
        + p["carbon_hold_heat"],
    }
    heater_evaluation = {"H-" + q["room"]: q["base"]["suggested_evaluation_kw"] for q in sauna}
    electric_cases = electrical_envelopes(
        electric,
        heater_evaluation,
        dhw_cases,
        p["dhw_COP"],
        p["power_factor"],
        p["electrical_reserve"],
    )
    plant_air_for_3kw = 3.0 / (0.335 * 8) * 1000
    result = {
        "sections": cases,
        "mass_inventory": loads,
        "operations": operations,
        "sauna_heat": sauna,
        "pool_cooling": cooling,
        "circulation": circulation,
        "hot_water_peaks": hot,
        "carbon_fill_4h_kw": carbon_fill,
        "carbon_hold_allowance_kw": p["carbon_hold_heat"],
        "daily_water": water_day,
        "ventilation": vent,
        "wet_volume_gross_m3": wet_vol,
        "wet_exhaust_m3_h": wet_air,
        "humidity_sensitivity": moisture,
        "electrical_connected_items_kw": electric,
        "electrical_cases": electric_cases,
        "dhw_thermal_cases_kw": dhw_cases,
        "heater_evaluation_kw": heater_evaluation,
        "tank_delivery": delivery_clearance(1.0, 0.90, 0.05),
        "duct_screen": {
            "wet_main_internal_mm": [600, 250],
            "wet_main_velocity_m_s": wet_air / 3600 / (0.6 * 0.25),
            "wet_main_vertical_envelope_m": 0.25 + 0.05 + 0.05,
            "nominal_band_m": p["service_depth"],
            "crossings_and_hangers_finalized": False,
        },
        "plant_ventilation_screen": {
            "initial_6ach_m3_h": 21 * 2.7 * 6,
            "assumed_internal_sensible_kw": 3.0,
            "assumed_allowed_delta_C": 8,
            "heat_balance_min_m3_h": plant_air_for_3kw,
            "note": "6ACH alone fails this 3kW sensible case. CO2/chemical local exhaust and boiler conditions still require separate design.",
        },
    }
    dump(DATA / "calculations/design_balances.json", result)
    for key in [
        "sections",
        "mass_inventory",
        "pool_cooling",
        "circulation",
        "hot_water_peaks",
        "daily_water",
        "ventilation",
        "humidity_sensitivity",
        "electrical_cases",
    ]:
        rows = result[key]
        write_csv(DATA / "tables" / f"{key}.csv", rows)
    write_csv(
        DATA / "tables/pool_queue_sensitivity.csv",
        [{k: v for k, v in q.items() if k != "customers"} for q in operations["pool_cases"]],
    )
    return basis, result


if __name__ == "__main__":
    _, r = calculate()
    print(
        json.dumps(
            {
                "sections": [
                    (q["id"], round(q["deck_z_m"], 3), round(q["clear_headroom_m"], 3))
                    for q in r["sections"]
                ],
                "cooling_4h_kw": [
                    round(q["cooling_kw"], 2) for q in r["pool_cooling"] if q["cooldown_h"] == 4
                ],
                "wet_exhaust_m3_h": round(r["wet_exhaust_m3_h"]),
                "electrical_kva": [
                    round(q["planning_kva_with_reserve"]) for q in r["electrical_cases"]
                ],
            }
        )
    )
