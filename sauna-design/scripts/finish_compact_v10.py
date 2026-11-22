"""Finish reviewed paths and viewing cameras without modifying frozen versions."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "plan/compact_v10.json"
j = json.loads(p.read_text())
assert j["parent_revision"]["status"] == "comparison_only"
routes = {
    "lobby_to_hall": [[9.55, 3.9], [9.3, 4.3], [9.3, 5.0], [9.22, 5.3], [8.75, 5.8], [8.75, 6.3]],
    "sauna_lobby": [[7.5, 6.2], [7.5, 4.95], [5.45, 4.95], [4.9, 5.0]],
    "self_door": [[5.45, 4.966], [5.45, 5.7]],
    "wash_walk": [[5.2, 4.966], [8.1, 4.966]],
    "main_entry_lane": [[4.65, 5.0], [4.1, 5.0], [3.8, 6.5], [3.434, 7.05], [3.434, 8.15]],
    "main_entry_lane_seated": [[4.65, 5.0], [4.1, 5.0], [3.8, 6.5], [3.434, 7.05], [3.434, 8.15]],
    "self_floor": [[5.45, 5.7], [5.18, 5.95], [5.18, 6.8], [5.65, 7.4], [6.0, 7.6], [6.0, 8.15]],
    "plant_arm": [[11.3, 3.3], [11.3, 3.1], [11.9, 2.96], [13.2, 2.96], [13.4, 2.45], [13.4, 1.85]],
}
for r in j["passages"]:
    if r["id"] in routes:
        r["line"] = routes[r["id"]]
    if r["id"] == "locker_front":
        r["name"] = "ロッカー前の固定物間（扉開き・更衣動作は未検査）"
    if r["id"] == "hall_lane_waiting":
        r["name"] = "同・腰掛け4＋立ち2の人体を配置した時（場面共用）"
for d in j["doors"]:
    if d["id"] == "plant":
        d["seg"] = [10.5, 3.5, 12.0, 3.5]
for e in j["plant"]["equipment"]:
    if e["id"] == "heater_2":
        e["rect"] = [14.65, 3.2, 15.1, 3.42]
if not any(c["name"] == "rest_detail" for c in j["cameras"]):
    j["cameras"].append(
        {
            "name": "rest_detail",
            "kind": "overview",
            "loc": [14.85, 3.95, 2.2],
            "target": [14.85, 7.3, 0.55],
            "lens": 17,
            "exposure": 3.6,
        }
    )
j["parent_revision"]["final_checks"] = [
    "path centres corrected at corners, main seated route checked separately",
    "heater_2 moved off plant entry; service/carry-in not validated",
    "rest_detail camera above seated eye, for layout inspection",
]
p.write_text(json.dumps(j, ensure_ascii=False, indent=2) + "\n")
print("V10_FINISH_PLAN_OK")
