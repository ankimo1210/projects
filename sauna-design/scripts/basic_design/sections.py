"""Level arithmetic for conditional pool construction, metres and kPa."""

import math


def section_case(depth, drop, slab_z, build_up, pit_depth, soffit_z, services_depth):
    if depth <= 0 or min(drop, build_up, pit_depth, services_depth) < 0:
        raise ValueError("Positive depth and nonnegative allowances required")
    deck = max(0.0, slab_z - pit_depth + depth + drop + build_up)
    bottom = deck - drop - depth
    outer_bottom = bottom - build_up
    risers = math.ceil(round(deck / 0.18, 10)) if deck > 1e-9 else 0
    run = max(0, risers - 1) * 0.28
    headroom = soffit_z - services_depth - deck
    return {
        "deck_z_m": deck,
        "water_z_m": deck - drop,
        "bottom_z_m": bottom,
        "assembly_bottom_z_m": outer_bottom,
        "slab_top_z_m": slab_z,
        "pit_depth_m": pit_depth,
        "clear_headroom_m": headroom,
        "required_soffit_z_for_2_1m_headroom": deck + services_depth + 2.10,
        "n_risers": risers,
        "riser_m": deck / risers if risers else 0.0,
        "stair_run_m": run,
        "landing_m": 0.90 if risers else 0.0,
        "stair_and_landing_area_m2": (run + 0.90) * 0.90 if risers else 0.0,
        "north_aisle_overrun_m": max(0, run + 0.90 - 1.388) if risers else 0.0,
        "water_floor_pressure_kpa": 9.80665 * depth,
        "headroom_screen": "below_planning_2_10m" if headroom < 2.10 - 1e-8 else "planning_only",
        "structural_adequacy": "unknown",
    }


def describe_case(case):
    return (
        f"床下{case['pit_depth_m']:.2f}m、デッキ+{case['deck_z_m']:.2f}m、頭上{case['clear_headroom_m']:.2f}m。"
        + (
            "専用階段区画と梁下の余裕が必要。現平面のまま採用できない。"
            if case["n_risers"]
            else "床下空間・構造・防水の確認を条件としてV8に近い。"
        )
    )


def external_stair_footprint(case, x, y, width=0.90, finished_wall_y=10.388):
    run = case["stair_run_m"]
    landing = 0.90 if case["n_risers"] else 0
    return {
        "stair_xyxy": (x, y, x + width, y + run),
        "landing_xyxy": (x, y + run, x + width, y + run + landing),
        "overrun_past_finished_wall_m": max(0, y + run + landing - finished_wall_y),
    }


def delivery_clearance(diameter, opening, jamb):
    clear = opening - 2 * jamb
    return {
        "diameter_m": diameter,
        "wall_opening_m": opening,
        "frame_clear_width_m": clear,
        "deficit_m": max(0, diameter - clear),
        "can_pass_as_one_piece": diameter <= clear,
    }
