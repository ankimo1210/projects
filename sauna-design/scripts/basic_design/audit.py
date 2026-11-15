"""Read the frozen model's shared layout data and retain traceable planning inputs."""

import csv
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
DATA = Path("/home/kazumasa/projects/_data/sauna-design/architecture-v1")
FROZEN_SHA = "1213509aa6fef497125d3d41cef5bb5682cd410acc0c588ee6048c4b2f5e0f94"
sys.path.insert(0, str(ROOT / "blender"))
from sauna import bath_layout as BL
from sauna import main_layout as ML
from sauna import rest_layout as RL
from sauna import sub_layout as SL
from sauna import water_layout as WL


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def load_basis():
    config = json.loads((ROOT / "plan/basic_design/inputs.json").read_text())
    params = {r["id"]: r["value"] for r in config["parameters"]}
    assert len(params) == len(config["parameters"])
    assert all(r["unit"] and r["status"] and r["source"] for r in config["parameters"])
    plan = json.loads((ROOT / "plan/plan_a.json").read_text())
    return config, params, plan


def build_audit():
    if DATA.resolve().name != "architecture-v1":
        raise ValueError("Output must be architecture-v1")
    model = DATA.parent / "fable-v8/model/sauna_a_v8.blend"
    assert sha(model) == FROZEN_SHA
    config, params, plan = load_basis()
    pools = []
    for p in plan["pools"]:
        x, y, w, h = p["rect"]
        gross = w * h * p["depth"]
        displacement = None
        if p["id"] in ("deep", "seated"):
            q = WL.pool(p["id"])
            displacement = sum(
                (b - a) * (d - c) * (z - q["floor_z"]) for a, c, b, d, z in q["treads"]
            )
        pools.append(
            {
                **p,
                "surface_m2": w * h,
                "gross_water_m3": gross,
                "step_displacement_m3": displacement,
                "water_less_known_steps_m3": gross - displacement
                if displacement is not None
                else None,
                "water_volume_note": "Only known staircase solids deducted; bathers/rails/linings ignored. Carbon steps not deducted.",
            }
        )
    dimensions = {"main": ML.dims(), "self": SL.self_dims(), "dry": SL.dry_dims()}
    rooms = []
    for r in plan["rooms"]:
        x, y, w, h = r["rect"]
        area = w * h
        calc_height = (
            params["soffit_z"] - params["service_depth"] if r["floor"] == "wet" else r["ceiling"]
        )
        v = area * calc_height
        label = "計画ゾーン外形（壁厚控除前）"
        if r["id"] in dimensions:
            a, b = dimensions[r["id"]]["room_inner"]
            area = a * b
            calc_height = r["ceiling"]
            v = area * calc_height
            label = "仕上内法から算出"
        rooms.append(
            {
                **r,
                "zone_area_m2": w * h,
                "calculation_area_m2": area,
                "calculation_volume_m3": v,
                "calculation_ceiling_m": calc_height,
                "basis": label,
            }
        )
    seats = {
        "main": ML.seats(),
        "self": SL.self_seats(),
        "dry": SL.dry_seats(),
        "rest": RL.layout_v5()["seats"],
        "annex": WL.loungers(),
        "perch": BL.perch_seats(),
        "built_in": BL.built_in_seats(),
    }
    report = {
        "revision": config["revision"],
        "model_sha256": FROZEN_SHA,
        "units": "m, m2, m3",
        "fixture_inventory": {
            "changing_lockers": 48,
            "existing_shoe_compartments": 20,
            "proposed_shoe_compartments": 40,
            "showers": 6,
            "toilet_bowls": 2,
            "washbasins": 2,
            "note": "Counts from room_other.py and wash model; actual fixture standards/access are not approved.",
        },
        "rooms": rooms,
        "pools": pools,
        "sauna_dimensions": dimensions,
        "seats": seats,
        "clearances": WL.clearances(),
        "water_routes": WL.routes(),
        "source_notes": [
            "main_layout circular heater reference values are legacy v6; actual v8 uses ZL-300 box",
            "The old rest floor and all front/back-of-house furniture remain conceptual, not fitted for a real building.",
        ],
        "status_counts": {
            s: sum(r["status"] == s for r in config["parameters"])
            for s in sorted({r["status"] for r in config["parameters"]})
        },
    }
    dump(DATA / "calculations/basis.json", report)
    write_csv(DATA / "tables/parameters.csv", config["parameters"])
    write_csv(
        DATA / "tables/rooms.csv",
        [
            {
                k: r[k]
                for k in (
                    "id",
                    "name",
                    "zone_area_m2",
                    "calculation_area_m2",
                    "calculation_volume_m3",
                    "ceiling",
                    "basis",
                )
            }
            for r in rooms
        ],
    )
    for name in ["inputs.json", "variants.json", "sources.json"]:
        dump(DATA / "sources" / name, json.loads((ROOT / "plan/basic_design" / name).read_text()))
    return report


if __name__ == "__main__":
    b = build_audit()
    print(
        json.dumps(
            {
                "rooms": len(b["rooms"]),
                "pools": len(b["pools"]),
                "parameters": sum(b["status_counts"].values()),
                "baseline_unchanged": True,
            }
        )
    )
