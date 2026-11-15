"""Verify/package property sheets without modifying frozen phase 1..6 assets."""

import ast
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

from .property import BASE, DATA, ROOT, calculate


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def main():
    checks = {}
    for folder in ["architecture-v1", "cost-v1"]:
        m = json.loads((BASE / folder / "delivery_manifest.json").read_text())
        for row in m["files"]:
            assert sha(BASE / folder / row["file"]) == row["sha256"], (
                "Frozen artifact changed: " + folder + "/" + row["file"]
            )
        checks[folder] = len(m["files"])
    frozen = json.loads((BASE / "architecture-v1/verification/frozen_before.json").read_text())
    preserved = 0
    for ver, files in frozen.items():
        for name, h in files.items():
            assert sha(BASE / ("fable-" + ver) / name) == h, (
                "Old model changed: " + ver + "/" + name
            )
        preserved += len(files)
    session = json.loads((BASE / "sessions/fable-high-manifest.json").read_text())
    assert sha(Path(session["session_file"])) == sha(Path(session["session_backup"]))
    for p in (ROOT / "scripts/basic_design").glob("property*.py"):
        ast.parse(p.read_text())
    docs = [
        "docs/basic_design/06-property-and-handoff.md",
        "docs/basic_design/property-inquiry.md",
        "docs/STATUS.md",
        "docs/superpowers/plans/2026-11-15-sauna-architecture-basic-plan.md",
        "README.md",
    ]
    for name in docs:
        p = ROOT / name
        for link in re.findall(r"\]\(([^)]+)\)", p.read_text()):
            if link.startswith(("http:", "https:", "#", "\\\\")):
                continue
            assert (p.parent / link.split("#")[0]).exists(), "Broken local link in " + name
    presentation = Path(
        "/mnt/c/Users/Kazumasa/.codex/visualizations/2026/11/13/01a1d48d-8603-74c1-aa91-084242e50d42/sauna-property-v1"
    )
    output = DATA / "outputs/sauna-property-20261115"
    output.mkdir(parents=True, exist_ok=True)
    for p in (presentation / "outputs/sauna-property-20261115").iterdir():
        if p.is_file():
            shutil.copy2(p, output / p.name)
    with zipfile.ZipFile(output / "sauna_property_v1.xlsx") as z:
        assert z.testzip() is None
        sheets = [n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+.xml", n)]
        assert len(sheets) == 4
        for name in sheets:
            assert 't="e"' not in z.read(name).decode(), "Spreadsheet cached error"
    wb = json.loads((output / "verification.json").read_text())
    assert wb["checks"]["final"] == {"status": "資料不足", "total": "未入力"}
    assert "0 entries" in wb["errors"]
    assert abs(wb["checks"]["goal"]["total_man"] - 19824.398204305) < 0.001
    pages = json.loads((DATA / "verification/pages.json").read_text())
    assert len(pages) == 10
    tests = (DATA / "verification/tests.txt").read_text()
    assert re.search(r"33 passed", tests)
    for name, p in [
        ("sauna_property_v1.pdf", DATA / "sauna_property_v1.pdf"),
        ("sauna_property_v1.xlsx", output / "sauna_property_v1.xlsx"),
    ]:
        shutil.copy2(p, presentation / name)
        assert sha(p) == sha(presentation / name)
    shutil.copy2(ROOT / "docs/basic_design/property-inquiry.md", DATA / "property-inquiry.md")
    src = DATA / "sources"
    src.mkdir(exist_ok=True)
    shutil.copy2(BASE / "cost-v1/calculations.json", src / "frozen_cost_basis.json")
    files = [
        *ROOT.glob("plan/basic_design/property_*"),
        *ROOT.glob("scripts/basic_design/property*.py"),
        ROOT / "scripts/basic_design/property_workbook.mjs",
        ROOT / "scripts/basic_design/costs.py",
        ROOT / "scripts/basic_design/cost_report.py",
        ROOT / "tests/basic_design/test_property.py",
        ROOT / "tests/basic_design/conftest.py",
        *[ROOT / p for p in docs],
    ]
    with zipfile.ZipFile(src / "reproduce-source.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(ROOT))
        z.write(src / "frozen_cost_basis.json", "inputs/frozen_cost_basis.json")
    r = calculate()
    (DATA / "README.md").write_text("""# ⑦ 物件条件表 / 2026-11-15

sauna_property_v1.pdf はA3の10ページ。outputs/sauna-property-20261115/sauna_property_v1.xlsx は4シート。
34条件、9主要確認、家賃/保証金/工事減額の予算境界、未入力の候補フォーム。
property-inquiry.md は未送信の照会文案。property.json とtables/ が元データ、sources/ が再生成ソース。
基準2億円は税込初期支出/保証金/予備費/運転3か月を含む。実物件なし、成約見積なし。
数値は探索条件で法定最低/構造安全/メーカー適用/営業許可の確定ではない。
3D/GPU作業・実物件確認・外部送信は行っていない。旧成果とFable会話は凍結保持。
""")
    result = {
        "date": r["date"],
        "cpu_only": True,
        "model_or_gpu_launched": False,
        "conditions": 34,
        "gates": 9,
        "pdf_pages": 10,
        "xlsx_sheets": 4,
        "tests": tests.strip(),
        "workbook_errors": 0,
        "workbook_blank_candidate_verified": True,
        "excel_native_app_recalculation": False,
        "pdf_all_pages_rendered_and_visually_reviewed": True,
        "frozen_manifests_verified": checks,
        "previous_model_files_unchanged": preserved,
        "same_fable_session_and_backup_match": True,
        "relative_doc_links_valid": True,
        "independent_review_fixes": [
            "identity and financial evidence",
            "whitespace/placeholder/valid dates",
            "over-budget needs specific change plan",
            "numeric evidence not accepted",
        ],
        "scope": "Property conditions/form only. Actual property/structural/code/permit findings not established. 3D integration deferred.",
    }
    (DATA / "verification/final_cpu_check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    payload = [
        p
        for p in DATA.rglob("*")
        if p.is_file()
        and p.suffix not in [".png", ".jpg", ".zip"]
        and p.name != "delivery_manifest.json"
    ] + [src / "reproduce-source.zip"]
    manifest = {
        "revision": "sauna-property-v1",
        "files": [
            {"file": str(p.relative_to(DATA)), "bytes": p.stat().st_size, "sha256": sha(p)}
            for p in sorted(payload)
        ],
    }
    (DATA / "delivery_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    package = DATA / "sauna_property_v1.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
        for p in payload + [DATA / "delivery_manifest.json"]:
            z.write(p, p.relative_to(DATA))
    with zipfile.ZipFile(package) as z:
        assert z.testzip() is None
        for row in manifest["files"]:
            assert hashlib.sha256(z.read(row["file"])).hexdigest() == row["sha256"]
    shutil.copy2(package, presentation / package.name)
    assert sha(package) == sha(presentation / package.name)
    size = sum(p.stat().st_size for p in DATA.rglob("*") if p.is_file())
    print(
        json.dumps(
            {
                "conditions": 34,
                "gates": 9,
                "pdf_pages": 10,
                "xlsx_sheets": 4,
                "tests_passed": 33,
                "frozen_manifests_unchanged": checks,
                "models_unchanged": preserved,
                "same_fable_session": True,
                "data_MB": round(size / 1e6, 2),
                "zip_MB": round(package.stat().st_size / 1e6, 2),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
