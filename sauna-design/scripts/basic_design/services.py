"""First-order balances. Inputs/units and excluded loads accompany the outputs."""

import math


def water_kw(volume_m3, delta_c, hours):
    if volume_m3 < 0 or delta_c < 0 or hours <= 0:
        raise ValueError("Nonnegative water/temperature and positive time required")
    return 1000 * 4.186 * volume_m3 * delta_c / 3600 / hours


def shower_kw(l_min, delta_c):
    return l_min * 4.186 * delta_c / 60


def chiller(cooling_kw, cop):
    if cooling_kw < 0 or cop <= 0:
        raise ValueError("Positive COP required")
    return {
        "cooling_kw": cooling_kw,
        "electric_kw": cooling_kw / cop,
        "heat_rejection_kw": cooling_kw * (1 + 1 / cop),
    }


def humidity_ratio(t_c, rh):
    if not 0 <= rh <= 1:
        raise ValueError("Relative humidity must be a fraction")
    # Magnus approximation, pressure in kPa; adequate for this room-air sensitivity study only.
    pv = 0.61094 * math.exp(17.625 * t_c / (t_c + 243.04)) * rh
    return 0.62198 * pv / (101.325 - pv)


def moisture_balance(flow_m3_h, out_c, out_rh, in_c, in_rh, internal_kg_h):
    delta = 1.2 * flow_m3_h * (humidity_ratio(out_c, out_rh) - humidity_ratio(in_c, in_rh))
    removal = max(0, internal_kg_h + delta)
    return {
        "ventilation_added_kg_h": delta,
        "internal_kg_h": internal_kg_h,
        "dehumidification_kg_h": removal,
        "latent_kw": removal * 2450 / 3600,
    }


def sauna_load(
    volume, heated_area, target_c, supply_c, ach, u, wood_kg, stone_kg, warmup_h, water_l_h, door_kw
):
    if min(volume, heated_area, ach, u, wood_kg, stone_kg, water_l_h, door_kw) < 0 or warmup_h <= 0:
        raise ValueError("Invalid heat-balance input")
    dt = max(0, target_c - supply_c)
    ventilation = 0.335 * volume * ach * dt / 1000
    transmission = u * heated_area * dt / 1000
    # Assumed mean lining rise 60% of air delta, stones to 200C. No bench temperature prediction.
    storage_kwh = (
        wood_kg * 1.5 * 0.6 * dt
        + stone_kg * 0.84 * max(0, 200 - supply_c)
        + 1.2 * volume * 1.005 * dt
    ) / 3600
    latent = water_l_h * 2257 / 3600
    steady = ventilation + transmission + door_kw + latent
    return {
        "ventilation_m3_h": volume * ach,
        "ventilation_kw": ventilation,
        "transmission_kw": transmission,
        "water_evaporation_kw": latent,
        "door_allowance_kw": door_kw,
        "steady_kw": steady,
        "warmup_storage_kwh": storage_kwh,
        "warmup_storage_kw": storage_kwh / warmup_h,
        "suggested_evaluation_kw": steady + storage_kwh / warmup_h,
        "selection_status": "conditional_balance_not_manufacturer_sizing",
    }


def electrical_envelopes(items, heater_evaluation, dhw_cases, cop, power_factor, reserve):
    if cop <= 0 or not 0 < power_factor <= 1 or reserve < 0:
        raise ValueError("Invalid COP, power factor or reserve")
    rows = []
    for profile in ["candidate", "thermal_envelope"]:
        loads = dict(items)
        if profile == "thermal_envelope":
            for key, kw in heater_evaluation.items():
                loads[key] = max(loads.get(key, 0), kw)
        for case, heat_kw in [("gas", None), *dhw_cases.items()]:
            components = {**loads, "DHW": 1.0 if heat_kw is None else heat_kw / cop}
            total = sum(components.values())
            rows.append(
                {
                    "case": case,
                    "heater_basis": profile,
                    "connected_electric_kw": total,
                    "planning_kva_with_reserve": total / power_factor * (1 + reserve),
                    "dhw_electric_kw": components["DHW"],
                    "components_kw": components,
                    "note": "Planning connection envelope, not service sizing. HVAC/pumps are provisional; diversity, starting, defrost and backup heat not selected.",
                }
            )
    return rows
