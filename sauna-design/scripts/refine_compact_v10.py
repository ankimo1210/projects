"""Apply the parent's independently reviewed refinements to the new comparison only."""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("/home/kazumasa/projects/_data/sauna-design/fable-v10")


def main():
    result = json.loads((OUT / "verification/fable_source_result.json").read_text())
    assert result["same_conversation"] and result["is_error"] is False
    path = ROOT / "plan/compact_v10.json"
    j = json.loads(path.read_text())
    if j.get("parent_revision"):
        raise SystemExit("Parent revision already applied; do not repeat")
    snapshot = OUT / "sources/fable-authored"
    snapshot.mkdir(parents=True, exist_ok=True)
    for name in [
        "plan/compact_v10.json",
        "blender/compact_v10.py",
        "blender/compact_v10_rooms.py",
        "docs/V10_DESIGN.md",
    ]:
        src = ROOT / name
        dest = snapshot / Path(name).name
        assert not dest.exists()
        shutil.copyfile(src, dest)
    zones = {z["id"]: z for z in j["zones"]}
    for zid, rect in {
        "main": [0, 4.4, 4.7, 5.6],
        "self": [4.7, 5.5, 2.2, 4.5],
        "wash": [4.7, 3.5, 4, 2],
        "linen": [2.5, 3.5, 2.2, 0.9],
        "lobby": [8.7, 3.5, 4, 2],
    }.items():
        zones[zid]["rect"] = rect
    j["zones"] = [z for z in j["zones"] if z["id"] != "saunaLobby"]
    zones["self"]["name"] = "セルフロウリュ（5席）"
    zones["rest"]["name"] = "屋内休憩（14席＋浴室2席）"
    for z in j["zones"]:
        if z["id"] not in ("main", "self"):
            z["ceiling"] = 2.45
    for s in j["walls"]:
        if s == [0, 4.4, 4.0, 4.4]:
            s[2] = 4.7
        if s == [4.0, 3.5, 4.0, 10]:
            s[0] = s[2] = 4.7
        if s == [4.0, 6.55, 6.9, 6.55]:
            s[:] = [4.7, 5.5, 6.9, 5.5]
        if s == [6.9, 6.55, 6.9, 10]:
            s[1] = 5.5
    j["screens"]["wash_lobby"] = [8.7, 3.5, 8.7, 4.9]
    j["screens"]["lobby_hall"] = [10.0, 5.5, 12.7, 5.5]
    for d in j["doors"]:
        if d["id"] == "main":
            d["seg"] = [4.7, 4.55, 4.7, 5.45]
        if d["id"] == "self":
            d["seg"] = [5.0, 5.5, 5.9, 5.5]
        if d["id"] == "rest":
            d["seg"] = [12.7, 6.0, 12.7, 7.1]
        if d["id"] == "entry":
            d["seg"] = [0.55, 0, 1.65, 0]
        if d["id"] == "rec-change":
            d["seg"] = [2.5, 0.85, 2.5, 1.85]
        if d["id"] == "rec-staff":
            d["seg"] = [1.4, 2.4, 2.35, 2.4]
        if d["id"] == "staff-change":
            d["seg"] = [2.5, 2.5, 2.5, 3.4]
        if d["id"] == "change-wc":
            d["seg"] = [10.2, 0.55, 10.2, 1.45]
    j["main"]["heater"]["centre"][0] = 2.35
    j["main"]["performer"]["centre"] = [2.1, 6.1]
    j["main"]["performer"]["search_rect"] = [0.2, 4.6, 4.5, 7.4]
    for s in j["main"]["seats"]:
        if s["id"].startswith("N"):
            s["x"] = round(0.427 + (int(s["id"][1:]) - 1) * (4.273 - 0.427) / 5, 4)
        elif s["id"].startswith("E"):
            s["x"] = 4.548
    north = [s for s in j["self"]["seats"] if s["id"] in ("S1", "S2", "S3")]
    for s, x in zip(north, [5.15, 5.78, 6.41], strict=False):
        s["x"] = x
    west = [s for s in j["self"]["seats"] if s["id"] in ("S5", "S6")]
    for s in west:
        s["x"] = 4.852
    j["self"]["seats"] = north + west
    j["self"]["heater"]["centre"] = [6.10, 6.40]
    j["self"]["bucket"] = [6.55, 8.30]
    j["self"]["seat_note"] = "北の上段3＋西の低い段2＝5位置。主室幅と通行を優先した比較修正。"
    j["wash"]["showers"] = [round(x + 0.7, 4) for x in j["wash"]["showers"]]
    j["wash"]["dividers"] = [round(x + 0.7, 4) for x in j["wash"]["dividers"]]
    j["wash"]["divider"]["depth"] = 0.95
    j["wash"]["drain"]["x0"] += 0.7
    j["wash"]["drain"]["x1"] += 0.7
    chairs = []
    for k, y in enumerate([4.430, 5.910, 7.780, 9.250], 1):
        for n, x in zip("ab", [13.19, 13.89], strict=False):
            chairs.append({"id": f"L{k}{n}", "foot": [x, y], "heading": [0, -1]})
    for k, y in enumerate([6.850, 8.350], 1):
        for n, x in zip("ab", [15.81, 16.51], strict=False):
            chairs.append({"id": f"R{k}{n}", "foot": [x, y], "heading": [0, -1]})
    j["rest"]["chairs"] = chairs
    screens = [[12.84, y, 14.24, y + 0.04] for y in [5.065, 6.935, 8.410]] + [
        [15.46, y, 16.86, y + 0.04] for y in [6.0, 7.5]
    ]
    j["rest"]["screens"] = screens
    j["rest"]["wings"] = (
        [[14.24, y, 14.27, y + 0.53] for y in [5.065, 6.935, 8.410]]
        + [[15.43, y, 15.46, y + 0.53] for y in [6.0, 7.5]]
        + [[15.43, 3.66, 15.46, 4.5]]
    )
    j["rest"]["builtin"] = {
        "rect": [10.8, 5.594, 12.0, 5.994],
        "top": 0.45,
        "zone": "bathHall",
        "seats": [
            {"id": "B1", "x": 11.1, "y": 5.60, "facing": "N", "seat_z": 0.45, "foot_z": 0},
            {"id": "B2", "x": 11.7, "y": 5.60, "facing": "N", "seat_z": 0.45, "foot_z": 0},
        ],
    }
    j["rest"]["note"] = (
        "休憩室14（椅子12＋寝椅子2）＋浴室造付2＝16。全席同方向、列内は横向き一人通行の比較値。造付と予備を二重計上しない。"
    )
    j["hall"]["perch"]["rect"] = [9.6, 5.594, 10.8, 5.994]
    j["hall"]["perch"]["seats"] = j["hall"]["perch"]["seats"][:2]
    j["hall"]["perch"]["note"] = "休憩16とは別の予備2。隣の正式造付2と物理的に分ける。"
    j["hall"]["waiting_standing"][0]["x"] = 9.0
    for eq in j["plant"]["equipment"]:
        if eq["id"] == "heater_1":
            eq["rect"] = [13.8, 3.2, 14.4, 3.42]
        if eq["id"] == "carbon_filter":
            eq["c"] = [16.5, 2.35]
    routes = {
        "entry_to_changing": [[1.1, 0.4], [1.1, 1.25], [2.2, 1.35], [2.9, 1.35]],
        "locker_front": [[3.1, 1.08], [8.6, 1.08]],
        "hall_lane": [[7.5, 6.84], [12.0, 6.84]],
        "hall_lane_waiting": [[7.5, 6.84], [12.0, 6.84]],
        "hall_to_rest": [[11.8, 6.84], [12.0, 6.84], [12.25, 6.70], [12.5, 6.505], [13.0, 6.505]],
        "rest_cross_aisle": [[13.0, 6.505], [14.85, 6.505]],
        "rest_centre_aisle": [[14.85, 4.25], [14.85, 9.3]],
        "rest_row_entry": [[14.1, 8.18], [13.19, 8.18]],
        "rest_lounger_foot": [[15.7, 5.75], [16.51, 5.75]],
        "rest_builtin_front": [[11.1, 6.84], [11.7, 6.84]],
        "sauna_lobby": [[7.5, 6.2], [7.25, 5.0], [5.5, 4.97], [4.9, 4.97]],
        "self_door": [[5.45, 4.97], [5.45, 5.4], [5.2, 5.8]],
        "wash_walk": [[5.1, 4.966], [8.3, 4.966]],
        "main_entry_lane": [[4.65, 5.0], [4.1, 5.0], [3.8, 6.5], [3.434, 7.3], [3.434, 8.15]],
        "main_entry_lane_seated": [
            [4.65, 5.0],
            [4.1, 5.0],
            [3.8, 6.5],
            [3.434, 7.3],
            [3.434, 8.15],
        ],
        "main_west_gap": [[1.266, 7.3], [1.266, 8.15]],
        "self_floor": [[5.2, 5.8], [5.18, 6.8], [5.65, 7.4], [6.0, 7.6], [6.0, 8.15]],
        "plant_arm": [
            [11.1, 3.3],
            [11.1, 3.01],
            [11.9, 3.01],
            [12.15, 2.79],
            [13.2, 2.79],
            [13.35, 2.45],
            [13.4, 1.85],
        ],
        "plant_aisle": [[13.4, 1.85], [15.5, 1.85]],
        "staff_to_changing": [[2.0, 2.95], [2.35, 2.95], [3.0, 2.95], [3.6, 2.5]],
    }
    for p in j["passages"]:
        if p["id"] in routes:
            p["line"] = routes[p["id"]]
        if p["id"] == "rest_cross_aisle":
            p["target"] = 0.80
            p["with_bodies"] = True
        if p["id"].startswith("rest_") or p["id"] in ("hall_lane_waiting", "hall_to_rest"):
            p["with_bodies"] = True
        if p["id"] == "rest_builtin_front":
            p["target"] = 0.8
        if p["id"] == "sauna_lobby":
            p["target"] = 0.8
        if p["id"] == "locker_front":
            p["target"] = 0.9
    j["hall"]["return_route"] = [[13.0, 6.505], [12.5, 6.505], [12.25, 6.70], [11.7, 6.84]]
    j["hall"]["wash_route"] = [[11.7, 6.84], [9.2, 6.3], [7.5, 6.0], [7.25, 4.966]]
    for c in j["cameras"]:
        if c["name"] == "self":
            c["loc"] = [5.20, 5.85, 1.55]
            c["target"] = [5.9, 9.6]
        if c["name"] == "rest_door":
            c["loc"][1] = 6.505
    groups = {}
    for z in j["zones"]:
        groups[z["group"]] = groups.get(z["group"], 0) + z["rect"][2] * z["rect"][3]
    j["area_changes"] = [
        {
            "group": g,
            "delta": round(groups.get(g, 0) - target, 5),
            "reason": "親の実メッシュ/独立レビューを反映。主室の着席時通路を優先し共通動線へ再配分。壁芯面積で、内法ではない。",
        }
        for g, target in j["targets_m2"].items()
        if abs(groups.get(g, 0) - target) > 0.001
    ]
    j["operations"]["scenarios"] = [
        {
            "name": "event10_other14",
            "in_room_rest": 14,
            "hall_official_rest": 0,
            "cold": 4,
            "queue_on_hall_official": 2,
            "queue_on_spare_perch": 2,
            "queue_standing": 2,
            "total": 24,
        },
        {
            "name": "event8_rest16",
            "in_room_rest": 14,
            "hall_official_rest": 2,
            "cold": 4,
            "queue_on_spare_perch": 2,
            "queue_standing": 2,
            "total": 24,
        },
    ]
    j["operations"]["note"] += (
        " 正式休憩は室内14＋浴室2、予備2。状態ごとに24人以内で共有席を配分し、全員同時の休憩8不足は残る。"
    )
    j["parent_revision"] = {
        "date": "2026-11-16",
        "status": "comparison_only",
        "changes": [
            "main width4.7/26.32m2, self5 positions",
            "rest14 inside +2 built-in in bath, spare2",
            "routes and plant equipment relocated",
            "non-sauna ceilings2.45 to clear assumed service band",
        ],
        "cost_reaudited": False,
    }
    path.write_text(json.dumps(j, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "parent_revision_applied": True,
                "area_m2": sum(groups.values()),
                "main_m2": groups["main"],
                "self_positions": len(j["self"]["seats"]),
                "rest_positions": len(chairs)
                + len(j["rest"]["loungers"])
                + len(j["rest"]["builtin"]["seats"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
