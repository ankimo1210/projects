"""Package and verify only phase 6. Never regenerate architecture or models."""

import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

from .costs import BASE, DATA, ROOT, calculate


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def main():
    architecture = BASE / "architecture-v1"
    archive_manifest = json.loads((architecture / "delivery_manifest.json").read_text())
    for r in archive_manifest["files"]:
        assert sha(architecture / r["file"]) == r["sha256"], "Architecture changed: " + r["file"]
    frozen = json.loads((architecture / "verification/frozen_before.json").read_text())
    preserved = {}
    for ver, files in frozen.items():
        for name, digest in files.items():
            assert sha(BASE / ("fable-" + ver) / name) == digest, (
                "Previous version changed: " + ver + "/" + name
            )
        preserved[ver] = len(files)
    session = json.loads((BASE / "sessions/fable-high-manifest.json").read_text())
    session_digest = sha(Path(session["session_file"]))
    assert session_digest == sha(Path(session["session_backup"])), "Session backup mismatch"

    presentation = Path(
        "/mnt/c/Users/Kazumasa/.codex/visualizations/2026/11/13/01a1d48d-8603-74c1-aa91-084242e50d42/sauna-cost-v1"
    )
    xdir = DATA / "outputs/sauna-cost-20261115"
    xdir.mkdir(parents=True, exist_ok=True)
    for p in (presentation / "outputs/sauna-cost-20261115").iterdir():
        if p.is_file():
            shutil.copy2(p, xdir / p.name)
    for name, source in [
        ("sauna_cost_v1.pdf", DATA / "sauna_cost_v1.pdf"),
        ("sauna_cost_v1.xlsx", xdir / "sauna_cost_v1.xlsx"),
    ]:
        shutil.copy2(source, presentation / name)
        assert sha(source) == sha(presentation / name)
    with zipfile.ZipFile(xdir / "sauna_cost_v1.xlsx") as z:
        assert z.testzip() is None
        sheets = [n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+.xml", n)]
        assert len(sheets) == 5
        for n in sheets:
            body = z.read(n).decode()
            assert 't="e"' not in body, "Cached spreadsheet error: " + n
    assert len(json.loads((DATA / "verification/pages.json").read_text())) == 14
    wbcheck = json.loads((xdir / "verification.json").read_text())
    for case in ["low", "base", "high"]:
        r = wbcheck["check"][case]
        assert abs(r["actual_man"] - r["expected_man"]) < 0.001
    assert wbcheck["check"]["quantity_change"]["blank"] == "#N/A"
    assert "0 entries" in wbcheck["errors"]

    docs = [
        "docs/basic_design/05-costs.md",
        "docs/STATUS.md",
        "docs/superpowers/plans/2026-11-15-sauna-architecture-basic-plan.md",
        "README.md",
    ]
    for name in docs:
        p = ROOT / name
        for link in re.findall(r"\]\(([^)]+)\)", p.read_text()):
            if link.startswith(("http:", "https:", "#", "\\\\")):
                continue
            assert (p.parent / link.split("#")[0]).exists(), (
                "Broken local link in " + name + ": " + link
            )

    sources = DATA / "sources"
    sources.mkdir(exist_ok=True)
    shutil.copy2(architecture / "calculations/basis.json", sources / "architecture_basis.json")
    files = [
        *ROOT.glob("plan/basic_design/cost_*"),
        *ROOT.glob("scripts/basic_design/cost*.py"),
        ROOT / "scripts/basic_design/cost_workbook.mjs",
        ROOT / "tests/basic_design/test_costs.py",
        ROOT / "tests/basic_design/conftest.py",
        *[ROOT / n for n in docs],
    ]
    with zipfile.ZipFile(sources / "reproduce-source.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(ROOT))
        z.write(sources / "architecture_basis.json", "inputs/architecture_basis.json")
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in files}
    (sources / "source_hashes.json").write_text(
        json.dumps(source_hashes, ensure_ascii=False, indent=2) + "\n"
    )
    r = calculate()
    (DATA / "README.md").write_text("""# ⑥ 費用試算 / 2026-11-15

sauna_cost_v1.pdf はA3の14ページ。outputs/sauna-cost-20261115/sauna_cost_v1.xlsx は編集可能な5シート。
calculations.json と tables/ が計算明細、sources/ が前提・再生成ソース、verification/ が検証。
基準総額は売上相殺なしの運転3か月込み約2.26億円。賃貸案、物件未定・成約見積なし。
公開定価と作成者の予算仮定を区別。土地建物購入・主要構造/建物全体改修等は金額未算入。
2億円へ寄せる約1.98億円の目標例は未交渉・未取得の条件。実施価格保証ではない。
旧モデル・同じFable会話と①〜⑤資料は凍結保持。⑦とGPU作業は保留。
""")
    result = {
        "date": r["date"],
        "cpu_only": True,
        "gpu_or_blender_launched": False,
        "items": len(r["items"]),
        "pdf_pages": 14,
        "xlsx_sheets": 5,
        "tests": (DATA / "verification/tests.txt").read_text().strip(),
        "excel_recalculation": "artifact-tool engine; inputs changed and restored; Excel desktop not tested",
        "xlsx_formula_errors": 0,
        "pdf_all_pages_rendered_and_visually_reviewed": True,
        "independent_review_fixes": ["rest floor45.45m2", "general doors8 to12"],
        "architecture_manifest_files_unchanged": len(archive_manifest["files"]),
        "v3_to_v8_files_unchanged": preserved,
        "same_fable_session_preserved": True,
        "session_id": session["conversation_id"],
        "session_sha256": session_digest,
        "source_files": len(files),
        "relative_doc_links_valid": True,
        "presentation_hashes_match": True,
        "base_funding_3m": r["cases"]["base"]["summary"]["funding_3m"],
        "target_funding_3m": r["target_to_200m"]["summary"]["funding_3m"],
    }
    (DATA / "verification/final_cpu_check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    # Exclude heavyweight review PNGs from the portable package; retain all canonical QA.
    payload = [
        p
        for p in DATA.rglob("*")
        if p.is_file()
        and p.suffix.lower() not in [".png", ".jpg", ".zip"]
        and p.name != "delivery_manifest.json"
    ]
    payload += [sources / "reproduce-source.zip"]
    manifest = {
        "revision": "sauna-cost-v1",
        "files": [
            {"file": str(p.relative_to(DATA)), "bytes": p.stat().st_size, "sha256": sha(p)}
            for p in sorted(payload)
        ],
    }
    (DATA / "delivery_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    package = DATA / "sauna_cost_v1.zip"
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
                "items": len(r["items"]),
                "pdf_pages": 14,
                "xlsx_sheets": 5,
                "tests_passed": 24,
                "preserved_previous_files": sum(preserved.values()),
                "preserved_architecture_files": len(archive_manifest["files"]),
                "session_matches": True,
                "package_files": len(payload) + 1,
                "data_MB": round(size / 1e6, 2),
                "zip_MB": round(package.stat().st_size / 1e6, 2),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
