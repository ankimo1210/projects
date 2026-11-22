#!/usr/bin/env python3
"""Create a portable, verified, bounded handoff without rendering or changing inputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import struct
import zipfile
from pathlib import Path, PurePosixPath

DATE = "2026-11-15"
HANDOFF = Path("docs/handoff") / DATE
BLOCKED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "logs",
    "parent_check",
    "previews",
    "sessions",
}
TEXT_EXT = {
    ".md",
    ".json",
    ".csv",
    ".py",
    ".mjs",
    ".js",
    ".sh",
    ".html",
    ".css",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".svg",
}
COMPRESSED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".blend", ".zip", ".xlsx"}
SECRET = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-[A-Za-z0-9]{24,}|ghp_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{20,})"
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def unc(path: Path) -> str:
    return "\\\\wsl.localhost\\Ubuntu" + str(path).replace("/", "\\")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def safe_name(name: str) -> bool:
    p = PurePosixPath(name)
    return (
        bool(name)
        and not p.is_absolute()
        and ".." not in p.parts
        and "\\" not in name
        and ":" not in name
        and not name.startswith("/")
    )


def files_below(root: Path):
    if not root.exists():
        raise FileNotFoundError(unc(root))
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(
            d for d in dirs if d not in BLOCKED_DIRS and not (Path(base) / d).is_symlink()
        )
        for name in sorted(files):
            p = Path(base) / name
            if p.is_symlink():
                raise ValueError("Symlink input excluded: " + unc(p))
            if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
                continue
            if p.suffix.lower() == ".jsonl" or "-raw" in p.stem or p.name.endswith(".log"):
                continue
            if p.name.startswith("native-") or p.name.endswith(
                ("-output.json", "-start.json", "-error.txt", "_server.json")
            ):
                continue
            yield p


def select(project: Path, data: Path, config):
    chosen = {}

    def add(src: Path, rel: str, role: str):
        if not safe_name(rel) or not src.is_file():
            raise ValueError("Invalid selected input: " + rel)
        if rel in chosen and chosen[rel][0] != src:
            raise ValueError("Duplicate destination: " + rel)
        chosen[rel] = (src, role)

    for p in files_below(project):
        if p.suffix.lower() in config["source_extensions"]:
            add(p, "project_source/" + p.relative_to(project).as_posix(), "project_source_snapshot")
    for version in config["current_design_versions"]:
        root = data / version
        for p in files_below(root):
            rel = p.relative_to(root)
            if "tests" in rel.parts:
                continue
            if rel.parts[0] in {
                "assets",
                "model",
                "renders",
                "diagrams",
                "viewer",
                "verification",
                "sources",
            } or rel.as_posix() in {"README.md", "delivery_manifest.json"}:
                if p.suffix.lower() not in {".blend1", ".blend2", ".pyc"} and (
                    p.suffix.lower() != ".zip"
                    or p.name in {"reproduce-source.zip", "source-before.zip"}
                ):
                    add(p, f"artifacts/{version}/" + rel.as_posix(), "current_design")
    for version in config["history_design_versions"]:
        root = data / version
        for p in files_below(root):
            rel = p.relative_to(root)
            include = (
                rel.parts[0] in {"renders", "diagrams"}
                or rel.as_posix() == "delivery_manifest.json"
                or (rel.parts[0] == "verification" and p.suffix == ".json")
            )
            if version == config["native_reference_version"]:
                include |= rel.parts[0] == "assets" or rel.as_posix() == "model/sauna_a_v7.blend"
            if include:
                add(p, f"artifacts/{version}/" + rel.as_posix(), "design_history_or_reference")
    for family in config["full_artifact_families"]:
        root = data / family
        for p in files_below(root):
            rel = p.relative_to(root)
            if (
                "tests" in rel.parts
                or p.suffix.lower() in {".blend1", ".blend2", ".pyc"}
                or p.name.endswith("-preview.png")
            ):
                continue
            if p.suffix.lower() == ".zip" and p.name not in {
                "reproduce-source.zip",
                "source-before.zip",
            }:
                continue
            add(p, f"artifacts/{family}/" + rel.as_posix(), "analysis_or_reference_artifact")
    for version in (4, 5, 6, 7):
        for name in (f"source-v{version}.zip", f"source-v{version}-sha256.json"):
            add(data / "sessions" / name, "artifacts/source-history/" + name, "historical_source")
    for name, target in config["handoff_documents"].items():
        add(project / HANDOFF / name, target, "primary_handoff")
    for name in ("requirements_and_decisions.json", "open_issues.json", "revenue_assumptions.json"):
        add(project / HANDOFF / name, "analysis/" + name, "classified_handoff_input")
    return dict(sorted(chosen.items()))


def scan_input(path: Path):
    if path.suffix.lower() in TEXT_EXT:
        s = path.read_text(encoding="utf-8-sig")
        if SECRET.search(s):
            raise ValueError("Credential pattern detected; value suppressed: " + unc(path))
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                n = info.filename.rstrip("/")
                if not safe_name(n) or PurePosixPath(n).name == ".env":
                    raise ValueError("Unsafe nested source archive member")
                if not info.is_dir() and Path(n).suffix.lower() in TEXT_EXT:
                    if info.file_size > 8 * 1024 * 1024:
                        raise ValueError("Unexpected large source text in nested ZIP")
                    if SECRET.search(z.read(info).decode("utf-8-sig")):
                        raise ValueError(
                            "Credential pattern in nested source archive; value suppressed"
                        )


def write_csv(path: Path, rows, fields=None):
    rows = list(rows)
    if fields is None:
        fields = list(dict.fromkeys(k for row in rows for k in row))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow(
                {
                    k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                    for k, v in row.items()
                }
            )


def glb_metadata(path: Path, output: Path, version: str):
    with path.open("rb") as f:
        magic, v, length = struct.unpack("<4sII", f.read(12))
        size, kind = struct.unpack("<I4s", f.read(8))
        if (
            magic != b"glTF"
            or v != 2
            or length != path.stat().st_size
            or kind != b"JSON"
            or size > 32 * 1024 * 1024
        ):
            raise ValueError("Invalid GLB header: " + path.name)
        meta = json.loads(f.read(size).decode("utf-8").rstrip("\0 \t\r\n"))
    external = [
        x["uri"]
        for kind in ("buffers", "images")
        for x in meta.get(kind, [])
        if "uri" in x and not x["uri"].startswith("data:")
    ]
    if external:
        raise ValueError("GLB has unresolved external URI")
    dump(output / f"glb_{version}_metadata.json", meta)
    rows = [
        {
            "index": i,
            "name": node.get("name", ""),
            "mesh": node.get("mesh"),
            "camera": node.get("camera"),
            "children": node.get("children", []),
            "translation_local": node.get("translation", [0, 0, 0]),
            "rotation_xyzw_local": node.get("rotation", [0, 0, 0, 1]),
            "scale_local": node.get("scale", [1, 1, 1]),
            "matrix_local_column_major": node.get("matrix", []),
        }
        for i, node in enumerate(meta.get("nodes", []))
    ]
    write_csv(output / f"glb_{version}_nodes.csv", rows)
    return {
        "version": version,
        "file": path.name,
        "sha256": sha(path),
        "nodes": len(rows),
        "meshes": len(meta.get("meshes", [])),
        "materials": len(meta.get("materials", [])),
        "embedded_images": len(meta.get("images", [])),
        "external_uris": len(external),
        "scope": "JSON chunk only; no BIN decode, world transform, collision, or render",
    }


def revenue_model(a):
    cash, wages = a["anchor_monthly_cash_yen"], a["wages_no_vat_yen"]
    anchor_net = (cash - wages) / (1 + a["assumed_tax_rate"]) + wages
    fixed = (
        anchor_net
        - a["variable_cost_ex_yen_per_visit"] * a["reference_anchor_visits_month"]
        + a["advertising_ex_yen_month"]
    )
    rows, breaks = [], []
    for price in a["average_spend_incl_tax_cases"]:
        contribution = (
            price / (1 + a["assumed_tax_rate"])
            - a["variable_cost_ex_yen_per_visit"]
            - price * a["card_rate_on_gross_sales"]
        )
        breaks.append(
            {
                "average_spend_incl_tax_yen": price,
                "contribution_ex_reference_yen_per_visit": contribution,
                "daily_visits_break_even": fixed / contribution / a["operating_days_month"],
            }
        )
        for daily in a["daily_visits_cases"]:
            visits = daily * a["operating_days_month"]
            gross = visits * price
            net = gross / (1 + a["assumed_tax_rate"])
            variable = visits * a["variable_cost_ex_yen_per_visit"]
            card = gross * a["card_rate_on_gross_sales"]
            rows.append(
                {
                    "daily_visits": daily,
                    "monthly_visits": visits,
                    "average_spend_incl_tax_yen": price,
                    "gross_sales_yen_month": gross,
                    "net_sales_reference_yen_month": net,
                    "variable_cost_reference_yen_month": variable,
                    "card_fee_yen_month": card,
                    "fixed_cost_reference_yen_month": fixed,
                    "operating_surplus_reference_yen_month": net - variable - card - fixed,
                }
            )
    cap = a["capacity_scenario"]
    capacity = cap["concurrent_people"] * cap["hours_day"] / cap["average_stay_hours"]
    assert math.isclose(fixed, 8931997.482181817, abs_tol=0.01)
    assert math.isclose(
        next(
            x for x in rows if x["daily_visits"] == 200 and x["average_spend_incl_tax_yen"] == 3300
        )["operating_surplus_reference_yen_month"],
        6374002.517818183,
        abs_tol=0.01,
    )
    return {
        "assumptions": a,
        "anchor_net_reference_yen_month": anchor_net,
        "fixed_cost_reference_yen_month": fixed,
        "formula": "N=days*d; surplus=N*p/(1+tax)-N*variable-N*p*card-fixed",
        "break_even": breaks,
        "capacity": {
            **cap,
            "theoretical_daily_visits": capacity,
            "average_occupancy_at_200_daily": 200 * cap["average_stay_hours"] / cap["hours_day"],
            "average_utilization_at_200_daily": 200 / capacity,
        },
        "scenarios": rows,
    }


def source_catalog(selected):
    rows, seen = [], set()

    def visit(obj, filename, at="$", parent=None):
        if isinstance(obj, dict):
            scope = (
                obj if any(k in obj for k in ("id", "source_id", "publisher", "title")) else parent
            )
            for k, v in obj.items():
                if isinstance(v, str) and v.startswith(("https://", "http://")):
                    rec = scope or obj
                    key = (filename, at + "." + k, v)
                    if key not in seen:
                        seen.add(key)
                        rows.append(
                            {
                                "origin_file": filename,
                                "source_id_within_file": rec.get("source_id", rec.get("id", "")),
                                "json_path": at + "." + k,
                                "publisher": rec.get("publisher", ""),
                                "title": rec.get("title", rec.get("name", "")),
                                "url": v,
                                "checked_at": rec.get(
                                    "checked_at", rec.get("accessed_at", rec.get("as_of", ""))
                                ),
                                "note": rec.get("facts", rec.get("note", "")),
                            }
                        )
                visit(v, filename, at + "." + k, scope)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                visit(v, filename, f"{at}[{i}]", parent)

    for rel, (path, _) in selected.items():
        if path.suffix.lower() == ".json":
            visit(read_json(path), rel)
    return rows


def portable_reports(project, selected, payload):
    mapping = {str(src.resolve()): rel for rel, (src, _) in selected.items()}
    mapping.update({unc(src): rel for rel, (src, _) in selected.items()})
    warnings, records = [], []
    for src in sorted((project / "docs/basic_design").glob("*.md")):
        rel = "reports/" + src.name

        def replace(match, src=src, rel=rel):
            raw = match.group(1)
            dest = raw.strip("<>")
            if dest.startswith(("https://", "http://", "mailto:", "#")):
                return match.group(0)
            link, _, fragment = dest.partition("#")
            key = link if link.startswith("\\\\") else str((src.parent / link).resolve())
            target = mapping.get(key)
            if target:
                return (
                    "]("
                    + os.path.relpath(target, "reports").replace("\\", "/")
                    + ("#" + fragment if fragment else "")
                    + ")"
                )
            warnings.append(
                {
                    "file": rel,
                    "original_destination": raw,
                    "status": "historical_target_not_packaged",
                    "replacement": "#historical-reference",
                }
            )
            return "](#historical-reference)"

        original = src.read_text(encoding="utf-8-sig")
        body = (
            "> ZIP閲覧用コピー。元の絶対パス・コマンドは履歴。収録範囲外へのリンクは末尾の注記を参照。\n\n"
            + re.sub(r"\]\(([^)]+)\)", replace, original)
        )
        if any(x["file"] == rel for x in warnings):
            body += '\n\n<a id="historical-reference"></a>\n一部は当時の環境/過去出力への参照で、今回のZIPには含まれない。analysis/link_warnings.csvを参照。\n'
        dest = payload / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
        records.append(
            {
                "path": rel,
                "source_unc": unc(src),
                "source_sha256": sha(src),
                "role": "portable_report_links_rewritten",
            }
        )
    write_csv(
        payload / "analysis/link_warnings.csv",
        warnings,
        ["file", "original_destination", "status", "replacement"],
    )
    return records


VERIFIER = '''#!/usr/bin/env python3
"""Verify every payload byte without Blender, extraction, or network access."""
import argparse,csv,hashlib,io,json
from pathlib import Path,PurePosixPath
import zipfile
def safe(n):
    return bool(n) and not PurePosixPath(n).is_absolute() and ".." not in PurePosixPath(n).parts and chr(92) not in n and ":" not in n
def main():
    p=argparse.ArgumentParser();p.add_argument("--zipfile",type=Path);a=p.parse_args()
    root=Path(__file__).resolve().parent
    if a.zipfile:
        z=zipfile.ZipFile(a.zipfile);names=z.namelist()
        assert len(names)==len(set(names)) and all(safe(n) for n in names)
        top=names[0].split("/")[0]+"/";assert all(n.startswith(top) for n in names)
        read=lambda name:z.read(top+name)
        stream=lambda name:z.open(top+name)
        available={n[len(top):] for n in names}
        assert z.testzip() is None
    else:
        read=lambda name:(root/name).read_bytes()
        stream=lambda name:(root/name).open("rb")
        available={f.relative_to(root).as_posix() for f in root.rglob("*") if f.is_file()}
    m=json.loads(read("PACKAGE_MANIFEST.json"));meta=set(m["unhashed_self_metadata"])
    expected={r["path"] for r in m["files"]}
    assert available==expected|meta,("member_set_mismatch",len(available),len(expected))
    for r in m["files"]:
        assert safe(r["path"])
        h=hashlib.sha256();count=0
        with stream(r["path"]) as f:
            for block in iter(lambda:f.read(1048576),b""):
                h.update(block);count+=len(block)
        assert count==r["bytes"] and h.hexdigest()==r["sha256"],r["path"]
    index=list(csv.DictReader(io.StringIO(read("FILE_INDEX.csv").decode("utf-8-sig"))))
    assert {r["path"] for r in index}==expected|meta
    by={r["path"]:r for r in index}
    assert all(by[r["path"]]["sha256"]==r["sha256"] for r in m["files"])
    print(json.dumps({"status":"verified","hashed_payload_files":len(expected),"self_metadata_files":len(meta),"total_members":len(available),"payload_bytes":sum(r["bytes"] for r in m["files"]),"crc_checked":bool(a.zipfile)},ensure_ascii=False))
if __name__=="__main__":main()
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("project", "data", "output"):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    project, data, output = args.project.resolve(), args.data.resolve(), args.output.resolve()
    config = read_json(project / HANDOFF / "build_config.json")
    if (
        args.output.is_symlink()
        or output != data / config["output_name"]
        or not project.is_dir()
        or not data.is_dir()
    ):
        raise ValueError("Output must be the explicitly named canonical handoff root")
    selected = select(project, data, config)
    size = sum(p.stat().st_size for p, _ in selected.values())
    estimate = 3 * size + 32 * 1024 * 1024
    groups = {}
    for rel, (p, _) in selected.items():
        group = "/".join(PurePosixPath(rel).parts[:2])
        groups[group] = groups.get(group, 0) + p.stat().st_size
    plan = {
        "as_of": DATE,
        "selected_files": len(selected),
        "selected_input_bytes": size,
        "peak_disk_estimate_bytes": estimate,
        "output_budget_bytes": config["output_budget_bytes"],
        "memory_estimate_mib_upper": config["memory_estimate_mib_upper"],
        "output_unc": unc(output),
        "no_gpu_or_network": True,
        "bytes_by_family": groups,
        "largest_inputs": [
            {"path": r, "bytes": p.stat().st_size}
            for r, (p, _) in sorted(
                selected.items(), key=lambda kv: kv[1][0].stat().st_size, reverse=True
            )[:12]
        ],
    }
    if args.plan:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    if estimate > config["output_budget_bytes"] or size > config["archive_budget_bytes"]:
        raise ValueError("Selected inputs exceed preflight budget")
    if args.plan:
        return
    if output.exists() and not args.refresh:
        raise FileExistsError("Use --refresh only for this task's existing output root")
    output.mkdir(parents=True, exist_ok=True)
    payload = output / config["package_folder"]
    payload.mkdir(exist_ok=True)
    dump(output / "build_plan.json", plan)
    provenance = {}
    session = data / "sessions" / config["session_backup_name"]
    session_before = sha(session)
    for rel, (src, role) in selected.items():
        scan_input(src)
        before = sha(src)
        dest = payload / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        if sha(dest) != before or sha(src) != before:
            raise ValueError("Input changed during snapshot: " + rel)
        provenance[rel] = {"source_unc": unc(src), "source_sha256": before, "role": role}
    analysis = payload / "analysis"
    layout = read_json(project / "plan/plan_a.json")
    rooms = [
        {
            "id": x["id"],
            "name": x["name"],
            "x_m": x["rect"][0],
            "y_m": x["rect"][1],
            "width_m": x["rect"][2],
            "height_m": x["rect"][3],
            "zone_outer_area_m2": x["rect"][2] * x["rect"][3],
            "ceiling_m": x["ceiling"],
            "floor_condition": x["floor"],
        }
        for x in layout["rooms"]
    ]
    assert len(rooms) == 15 and math.isclose(sum(x["zone_outer_area_m2"] for x in rooms), 280)
    write_csv(analysis / "room_program.csv", rooms)
    pools = [
        {
            "id": x["id"],
            "name": x["name"],
            "x_m": x["rect"][0],
            "y_m": x["rect"][1],
            "width_m": x["rect"][2],
            "length_m": x["rect"][3],
            "depth_m": x["depth"],
            "surface_m2": x["rect"][2] * x["rect"][3],
            "gross_volume_before_steps_m3": x["rect"][2] * x["rect"][3] * x["depth"],
            "assumed_temperature_c": {"deep": 10, "seated": 16, "carbonPool": 37}[x["id"]],
            "temperature_status": "user_approved_calculation_assumption"
            if x["id"] != "carbonPool"
            else "author_assumption",
        }
        for x in layout["pools"]
    ]
    assert math.isclose(sum(x["gross_volume_before_steps_m3"] for x in pools), 10.2384)
    write_csv(analysis / "pools.csv", pools)
    glbs = [
        glb_metadata(payload / f"artifacts/fable-{v}/model/{name}", analysis, v)
        for v, name in (("v8", "sauna_a_v8.glb"), ("v9", "sauna_a_v9_light.glb"))
    ]
    dump(analysis / "glb_summary.json", glbs)
    assumptions = read_json(project / HANDOFF / "revenue_assumptions.json")
    finance = read_json(data / "one-ginza-detail-v1/calculations.json")
    assert math.isclose(
        assumptions["anchor_monthly_cash_yen"],
        finance["middle_case"]["monthly_outflow_reference_yen"],
        abs_tol=0.01,
    )
    revenue = revenue_model(assumptions)
    dump(analysis / "revenue_model.json", revenue)
    write_csv(analysis / "revenue_scenarios.csv", revenue["scenarios"])
    write_csv(
        analysis / "open_issues.csv", read_json(project / HANDOFF / "open_issues.json")["items"]
    )
    write_csv(analysis / "source_catalog.csv", source_catalog(selected))
    for rec in portable_reports(project, selected, payload):
        provenance[rec.pop("path")] = rec
    start = (payload / "00_START_HERE.md").read_text(encoding="utf-8")
    prompt = start.split("```text\n", 1)[1].split("```", 1)[0]
    (payload / "CHATGPT_PROMPT.txt").write_text(prompt, encoding="utf-8")
    dump(
        payload / "SESSION_PROVENANCE.json",
        {
            "session_id": session.stem,
            "recorded_model": "claude-fable-5-2",
            "user_requested_effort": "high",
            "canonical_backup_unc": unc(session),
            "canonical_backup_bytes": session.stat().st_size,
            "canonical_backup_sha256": session_before,
            "raw_conversation_included": False,
            "original_deleted_or_modified": False,
            "live_original_inspected_this_turn": False,
            "note": "UUID alone does not transfer or resume the conversation in ChatGPT; original backup retained",
        },
    )
    (payload / "VERIFY_BUNDLE.py").write_text(VERIFIER, encoding="utf-8")
    records = []
    for p in sorted(payload.rglob("*")):
        if not p.is_file() or (
            p.name in {"PACKAGE_MANIFEST.json", "FILE_INDEX.csv"} and p.parent == payload
        ):
            continue
        rel = p.relative_to(payload).as_posix()
        assert safe_name(rel)
        record = {
            "path": rel,
            "bytes": p.stat().st_size,
            "sha256": sha(p),
            **provenance.get(
                rel,
                {"source_unc": "", "source_sha256": "", "role": "generated_analysis_or_delivery"},
            ),
        }
        if p.suffix.lower() == ".json":
            read_json(p)
        records.append(record)
    metadata = ["PACKAGE_MANIFEST.json", "FILE_INDEX.csv"]
    dump(
        payload / "PACKAGE_MANIFEST.json",
        {
            "as_of": DATE,
            "package_folder": config["package_folder"],
            "scope": "Technical handoff snapshot, not complete chat transcript or approved construction documents",
            "config": config,
            "preflight": plan,
            "validation_scope": [
                "source/copy SHA256",
                "ZIP safe member names, CRC, all payload hashes",
                "JSON parse",
                "room/pool/revenue reconciliation",
                "GLB JSON only",
            ],
            "past_tests_and_renders_are_historical": True,
            "unhashed_self_metadata": metadata,
            "glb_json_inspection": glbs,
            "files": records,
        },
    )
    write_csv(
        payload / "FILE_INDEX.csv",
        records + [{"path": x, "role": "self_metadata_hash_excluded"} for x in metadata],
        ["path", "bytes", "sha256", "source_unc", "source_sha256", "role"],
    )
    archive = output / config["archive_name"]
    temporary = archive.with_suffix(".zip.building")
    with zipfile.ZipFile(temporary, "w", allowZip64=True, compresslevel=6) as z:
        for p in sorted(payload.rglob("*")):
            if not p.is_file():
                continue
            name = config["package_folder"] + "/" + p.relative_to(payload).as_posix()
            assert safe_name(name)
            info = zipfile.ZipInfo(name, (2026, 11, 15, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = (
                zipfile.ZIP_STORED if p.suffix.lower() in COMPRESSED_EXT else zipfile.ZIP_DEFLATED
            )
            with p.open("rb") as src, z.open(info, "w", force_zip64=True) as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
    with zipfile.ZipFile(temporary) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(records) + 2
        for r in records:
            h = hashlib.sha256()
            with z.open(config["package_folder"] + "/" + r["path"]) as f:
                for b in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(b)
            assert h.hexdigest() == r["sha256"], r["path"]
    assert temporary.stat().st_size < config["archive_budget_bytes"]
    for rel, (src, _) in selected.items():
        assert sha(src) == provenance[rel]["source_sha256"], "Source changed: " + rel
    assert sha(session) == session_before, "Fable backup changed"
    os.replace(temporary, archive)
    digest = sha(archive)
    archive.with_suffix(".zip.sha256").write_text(
        digest + "  " + archive.name + "\n", encoding="ascii"
    )
    measured = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
    assert measured < config["output_budget_bytes"]
    result = {
        "status": "verified",
        "as_of": DATE,
        "zip_unc": unc(archive),
        "zip_bytes": archive.stat().st_size,
        "zip_sha256": digest,
        "hashed_payload_files": len(records),
        "metadata_files": 2,
        "total_zip_members": len(records) + 2,
        "selected_inputs_unchanged": len(selected),
        "fable_backup_unchanged": True,
        "output_files_measured_bytes": measured,
        "gpu_blender_fable_network_used": False,
        "source_copy_hashes_match": True,
        "zip_crc_and_payload_hashes_match": True,
    }
    dump(output / "packaging_result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
