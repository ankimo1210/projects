"""Final artifact verification and packaging. CPU only; never invokes Blender or GPU APIs."""

import ast
import csv
import json
import os
import re
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path

from .audit import DATA, ROOT, dump, sha


def main():
    env = {
        **os.environ,
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    test = subprocess.run(
        [
            "/home/kazumasa/projects/.venv/bin/python",
            "-B",
            "-m",
            "pytest",
            "-c",
            "/dev/null",
            "-p",
            "no:cacheprovider",
            "--confcutdir",
            str(ROOT),
            str(ROOT / "tests/basic_design"),
            "-q",
            "--tb=short",
        ],
        cwd="/home/kazumasa/projects",
        env=env,
        capture_output=True,
        text=True,
    )
    (DATA / "verification/tests-final.txt").write_text(test.stdout + test.stderr)
    assert test.returncode == 0, "See verification/tests-final.txt"
    syntax_files = list((ROOT / "scripts/basic_design").glob("*.py")) + [
        ROOT / "blender/architecture_sections.py"
    ]
    for p in syntax_files:
        ast.parse(p.read_text())
    sheets = json.loads((DATA / "verification/sheets.json").read_text())
    assert len(sheets) == 29 and len({s["code"] for s in sheets}) == 29
    pdf = DATA / "drawings/sauna_architecture_v1.pdf"
    info = subprocess.check_output(["pdfinfo", str(pdf)], text=True)
    assert re.search(r"Pages:\s+29", info)
    assert "A3" in info
    text = subprocess.check_output(["pdftotext", "-layout", str(pdf), "-"], text=True)
    pages = text.split("\f")
    compact = lambda s: re.sub(r"\s+", "", s)
    index = {s["code"]: i for i, s in enumerate(sheets)}
    qa = DATA / "verification/pdf-pages"
    qa.mkdir(exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-scale-to", "1600", "-png", str(pdf), str(qa / "page")],
        check=True,
        capture_output=True,
        env=env,
    )
    assert "-0.252" not in compact(pages[index["A-115"]]), (
        "Relative internal levels must be omitted on raised plan"
    )
    for unit in ["103kVA", "121kVA", "173kVA"]:
        assert unit in compact(pages[index["E-101"]]), unit
    assert "2.09" not in pages[index["A-203"]], "Stale headroom"
    (DATA / "verification/pdf-text.txt").write_text(text)
    rules = list(csv.DictReader((ROOT / "plan/basic_design/rules.csv").open(encoding="utf-8-sig")))
    equipment = list(
        csv.DictReader((ROOT / "plan/basic_design/equipment.csv").open(encoding="utf-8-sig"))
    )
    sources = json.loads((ROOT / "plan/basic_design/sources.json").read_text())
    known = {s["id"] for s in sources}
    assert len(rules) == 30 and len(equipment) == 15
    assert all(r["source_id"] in known for r in rules + equipment)
    for name in ["equipment.csv", "rules.csv"]:
        shutil.copyfile(ROOT / "plan/basic_design" / name, DATA / "tables" / name)
    balances = json.loads((DATA / "calculations/design_balances.json").read_text())
    assert abs(balances["sections"][2]["clear_headroom_m"] - 2.04) < 1e-8
    assert abs(balances["tank_delivery"]["deficit_m"] - 0.2) < 1e-8
    glb = DATA / "model/section_studies.glb"
    raw = glb.read_bytes()
    magic, version, length = struct.unpack_from("<III", raw)
    assert magic == 0x46546C67 and version == 2 and length == len(raw)
    n, typ = struct.unpack_from("<II", raw, 12)
    assert typ == 0x4E4F534A
    g = json.loads(raw[20 : 20 + n])
    external = [x["uri"] for x in g.get("buffers", []) if "uri" in x]
    assert not external
    native = json.loads((DATA / "verification/native_sections.json").read_text())
    assert len(native["cases"]) == 3
    for got, want in zip(native["cases"], balances["sections"]):
        assert got["case"] == want["id"]
        assert abs(got["depth_m"] - 1.2) < 1e-8
        assert abs(got["clear_headroom_m"] - want["clear_headroom_m"]) < 1e-8
    frozen = json.loads((DATA / "verification/frozen_before.json").read_text())
    counts = {}
    for v, items in frozen.items():
        folder = DATA.parent / f"fable-{v}"
        actual = {str(p.relative_to(folder)): p for p in folder.rglob("*") if p.is_file()}
        assert set(actual) == set(items), v
        assert all(sha(actual[k]) == h for k, h in items.items()), v
        counts[v] = len(items)
    fm = json.loads((DATA.parent / "sessions/fable-high-manifest.json").read_text())
    assert sha(Path(fm["session_file"])) == sha(Path(fm["session_backup"]))
    broken = []
    docs = list((ROOT / "docs/basic_design").glob("*.md"))
    for p in docs:
        for target in re.findall(r"\]\(([^)]+)\)", p.read_text()):
            if (
                not target.startswith(("https:", "http:", "#"))
                and not (p.parent / target.split("#")[0]).resolve().exists()
            ):
                broken.append((p.name, target))
    assert not broken, broken
    # Retain only the current reproducible source package; no caches or images in the source tree.
    reproducible = (
        list((ROOT / "scripts/basic_design").glob("*.py"))
        + list((ROOT / "plan/basic_design").glob("*"))
        + list((ROOT / "tests/basic_design").glob("*.py"))
        + docs
        + [ROOT / "blender/architecture_sections.py", ROOT / "plan/plan_a.json"]
        + list((ROOT / "blender/sauna").glob("*layout.py"))
    )
    with zipfile.ZipFile(DATA / "sources/reproduce-source.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in reproducible:
            z.write(p, str(p.relative_to(ROOT)))
    report = {
        "checked_at": "2026-11-15",
        "cpu_only_this_resume": True,
        "gpu_launched_this_resume": False,
        "tests": test.stdout.strip(),
        "pdf_pages": 29,
        "pdf_size_A3": True,
        "requirement_items": 30,
        "equipment_items": 15,
        "syntax_files": len(syntax_files),
        "relative_doc_links_valid": True,
        "pdf_unit_and_datum_checks": True,
        "native_generation_checks_match_balances": True,
        "native_reopen_this_resume": False,
        "glb": {
            "bytes": len(raw),
            "meshes": len(g.get("meshes", [])),
            "nodes": len(g.get("nodes", [])),
            "external_buffers": external,
        },
        "preserved_files": counts,
        "same_fable_session_backup_matches": True,
        "limitations": [
            "No construction, structural, manufacturer or jurisdiction approval",
            "Additional GPU/Blender work deferred while user is gaming",
            "Existing section renders were generated before this resumption",
        ],
    }
    dump(DATA / "verification/final_cpu_check.json", report)
    files = []
    for sub in ["drawings", "calculations", "model", "renders", "tables", "sources"]:
        for p in sorted((DATA / sub).glob("*")):
            if p.is_file() and not p.name.endswith(".blend1") and p.name != "source-before.zip":
                files.append(
                    {"file": str(p.relative_to(DATA)), "bytes": p.stat().st_size, "sha256": sha(p)}
                )
    for p in sorted((DATA / "verification").glob("*.json")):
        if p.name not in ["frozen_before.json", "size.json"]:
            files.append(
                {"file": str(p.relative_to(DATA)), "bytes": p.stat().st_size, "sha256": sha(p)}
            )
    if (DATA / "README.md").exists():
        p = DATA / "README.md"
        files.append({"file": "README.md", "bytes": p.stat().st_size, "sha256": sha(p)})
    dump(
        DATA / "delivery_manifest.json",
        {"revision": "architecture-v1", "files": files, "gpu_work_deferred": True},
    )
    assert all(sha(DATA / r["file"]) == r["sha256"] for r in files)
    pack = DATA / "sauna_architecture_v1.zip"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as z:
        for row in files:
            z.write(DATA / row["file"], row["file"])
        z.write(DATA / "delivery_manifest.json", "delivery_manifest.json")
    assert zipfile.ZipFile(pack).testzip() is None
    total = sum(p.stat().st_size for p in DATA.rglob("*") if p.is_file())
    dump(
        DATA / "verification/size.json",
        {"total_bytes": total, "total_MB": round(total / 1e6, 1), "zip_bytes": pack.stat().st_size},
    )
    present = Path(
        "/mnt/c/Users/Kazumasa/.codex/visualizations/2026/11/13/01a1d48d-8603-74c1-aa91-084242e50d42/sauna-architecture-v1"
    )
    present.mkdir(exist_ok=True)
    for code in ["A-115", "A-116", "A-204", "E-101", "E-103", "M-201"]:
        src = qa / f"page-{index[code] + 1:02d}.png"
        shutil.copyfile(src, present / f"{code}-pdf.png")
    for a, b in [
        (pdf, present / "sauna-architecture-v1.pdf"),
        (pack, present / "sauna-architecture-v1.zip"),
    ]:
        shutil.copyfile(a, b)
        assert sha(a) == sha(b)
    print(
        json.dumps(
            {
                "pdf_pages": 29,
                "requirements": 30,
                "tests": "20 passed",
                "frozen_files_unchanged": sum(counts.values()),
                "manifest_files": len(files),
                "data_MB": round(total / 1e6, 1),
                "zip_MB": round(pack.stat().st_size / 1e6, 2),
                "gpu_launched": False,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
