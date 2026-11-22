"""Audit the delivered V10 against its native model and preserved prior outputs."""

import hashlib
import json
import shutil
import struct
from datetime import UTC, datetime
from pathlib import Path

from compact_geometry import rectangle_metrics

ROOT = Path(__file__).resolve().parents[1]
DATA = Path("/home/kazumasa/projects/_data/sauna-design")
OUT = DATA / "fable-v10"


def sha(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def read(p):
    return json.loads(p.read_text())


def write(p, j):
    p.write_text(json.dumps(j, ensure_ascii=False, indent=2) + "\n")


model = OUT / "model/sauna_compact_v10.blend"
model_sha = sha(model)
plan = read(ROOT / "plan/compact_v10.json")
rect = rectangle_metrics([z["rect"] for z in plan["zones"]], plan["width"], plan["height"])
assert (
    abs(rect["union_area_m2"] - 170) < 1e-8
    and rect["overlap_area_m2"] < 1e-8
    and not rect["out_of_bounds_indices"]
)
write(OUT / "verification/parent_plan_rectangles.json", rect)
ver = read(OUT / "verification/v10_verification.json")
assert (
    not ver["failures"]
    and ver["model_file"]["sha256"] == model_sha
    and ver["model_unchanged_by_verify"]
)
assert ver["plan_sha256"] == sha(ROOT / "plan/compact_v10.json")
probe = read(OUT / "verification/native_probe.json")
assert (
    probe["model_sha256"] == model_sha
    and probe["model_unchanged"]
    and not probe["missing_texture_files"]
)
export = read(OUT / "verification/v10_glb.json")
assert export["source_model_sha256"] == model_sha and export["source_model_unchanged"]
glb = OUT / "model/sauna_compact_v10.glb"
assert export["file"]["sha256"] == sha(glb)
b = glb.read_bytes()
magic, version, length = struct.unpack_from("<4sII", b)
assert magic == b"glTF" and version == 2 and length == len(b)
n, kind = struct.unpack_from("<I4s", b, 12)
assert kind == b"JSON"
gltf = json.loads(b[20 : 20 + n])
uris = [
    x["uri"]
    for k in ("buffers", "images")
    for x in gltf.get(k, [])
    if "uri" in x and not x["uri"].startswith("data:")
]
assert not uris
expected = {
    "main",
    "self",
    "bath",
    "rest",
    "rest_detail",
    "change",
    "overview",
    "plan",
    "section_pools",
}
renders = [
    json.loads(s)
    for s in (OUT / "verification/v10_render_log.jsonl").read_text().splitlines()
    if s.strip()
]
finals = [r for r in renders if not r["test"]]
assert {r["view"] for r in finals} == expected and len(finals) == len(expected)
for r in finals:
    assert r["model_sha256"] == model_sha and r["model_unchanged_by_render"]
    assert r["resolution"] == [2400, 1600] and r["max_samples"] == 1024
    assert r["sha256"] == sha(OUT / "renders" / ("v10_" + r["view"] + ".png"))
floor = read(OUT / "verification/floor_map_provenance.json")
assert floor["source_model_sha256"] == model_sha and floor["source_render_sha256"] == sha(
    OUT / "renders/v10_plan.png"
)
assert floor["output_sha256"] == sha(OUT / "diagrams/sauna_floor_map_v10.png")
assert (OUT / "viewer/index.html").read_bytes() == (ROOT / "viewer-v10/index.html").read_bytes()
preserved = read(OUT / "verification/preserved_before.json")
changed = [
    name
    for name, old in preserved.items()
    if not (DATA / name).is_file() or sha(DATA / name) != old["sha256"]
]
assert not changed, "Frozen prior output changed"
write(
    OUT / "verification/preserved_after.json",
    {
        "checked_files": len(preserved),
        "changed": changed,
        "before_manifest_sha256": sha(OUT / "verification/preserved_before.json"),
    },
)
session = read(DATA / "sessions/fable-high-manifest.json")
assert session["conversation_id"] == "68de4adc-db0a-4644-a3a5-9be5012127a3"
a, bp = Path(session["session_file"]), Path(session["session_backup"])
assert sha(a) == sha(bp)
sr = read(OUT / "verification/fable_source_result.json")
assert sr["same_conversation"] and not sr["is_error"] and not sr["permission_denials"]
write(
    OUT / "verification/session_preserved.json",
    {
        "same_session": True,
        "session_id": session["conversation_id"],
        "model": sr["model"],
        "effort": sr["effort"],
        "backup_matches_original": True,
        "sha256": sha(bp),
        "bytes": bp.stat().st_size,
    },
)
source_files = [
    "plan/compact_v10.json",
    "blender/compact_v10.py",
    "blender/compact_v10_rooms.py",
    "blender/probe_compact_v10.py",
    "scripts/compact_geometry.py",
    "scripts/refine_compact_v10.py",
    "scripts/finish_compact_v10.py",
    "scripts/render_compact_v10.py",
    "scripts/compact_floor_map.py",
    "scripts/blender_v10.sh",
    "scripts/verify_compact_delivery.py",
    "docs/V10_BRIEF.md",
    "docs/V10_DESIGN.md",
    "docs/V10_PARENT_REVIEW.md",
]
for name in source_files:
    dst = OUT / "sources/final" / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, dst)
files = {
    str(p.relative_to(OUT)): {"bytes": p.stat().st_size, "sha256": sha(p)}
    for p in sorted(OUT.rglob("*"))
    if p.is_file() and p.name != "delivery_manifest.json"
}
total = sum(f["bytes"] for f in files.values())
assert total < 1024**3
manifest = {
    "version": 10,
    "date": datetime.now(UTC).isoformat(),
    "status": "comparison_only",
    "source_model_sha256": model_sha,
    "native_probe": {
        k: probe[k]
        for k in (
            "mesh_count",
            "evaluated_vertices",
            "material_count",
            "camera_count",
            "missing_texture_files",
        )
    },
    "gpu_renders": finals,
    "glb": {
        "bytes": glb.stat().st_size,
        "sha256": sha(glb),
        "cameras": len(gltf.get("cameras", [])),
        "external_uris": uris,
    },
    "rectangles": rect,
    "verification": {
        "internal_failures": 0,
        "open_issues": len(ver["open_issues"]),
        "not_measured": len(ver["not_measured"]),
        "not_a_building_approval": True,
    },
    "frozen_files_unchanged": len(preserved),
    "same_fable_session_preserved": True,
    "bytes_before_manifest": total,
    "files": files,
}
write(OUT / "delivery_manifest.json", manifest)
print(
    json.dumps(
        {
            "V10_DELIVERY_AUDIT_OK": True,
            "files": len(files) + 1,
            "model_sha256": model_sha,
            "renders": len(finals),
            "old_files_unchanged": len(preserved),
            "same_fable_session": True,
            "output_MB": round(total / 1e6, 2),
            "internal_failures": 0,
            "open_issues": len(ver["open_issues"]),
        },
        ensure_ascii=False,
    )
)
