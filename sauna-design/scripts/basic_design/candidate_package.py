"""Verify and package the public-listing comparison, keeping earlier revisions intact."""

import ast
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

from .candidates import BASE, DATA, ROOT, calculate


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    frozen = {}
    for version in ["architecture-v1", "cost-v1", "property-v1"]:
        records = json.loads((BASE / version / "delivery_manifest.json").read_text())["files"]
        for row in records:
            assert sha(BASE / version / row["file"]) == row["sha256"], "Earlier artifact changed"
        frozen[version] = len(records)
    old = json.loads((BASE / "architecture-v1/verification/frozen_before.json").read_text())
    models = 0
    for version, files in old.items():
        for name, expected in files.items():
            assert sha(BASE / ("fable-" + version) / name) == expected, "Earlier model changed"
            models += 1
    session = json.loads((BASE / "sessions/fable-high-manifest.json").read_text())
    assert sha(Path(session["session_file"])) == sha(Path(session["session_backup"]))
    workbook = DATA / "sauna_candidates_20261115.xlsx"
    with zipfile.ZipFile(workbook) as z:
        assert z.testzip() is None
        sheets = [n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+.xml", n)]
        assert len(sheets) == 2
        assert not any('t="e"' in z.read(n).decode() for n in sheets)
    wb = json.loads((DATA / "workbook_verification.json").read_text())
    assert "0 entries" in wb["errors"]
    d = calculate()
    for expected, got in zip(d["candidates"], wb["checks"]["results"]):
        assert expected["id"] == got["id"]
        for value, case in zip(got["totals"], expected["cases"]):
            assert abs(value * 10000 - case["reference_total_yen"]) < 0.05
    pages = json.loads((DATA / "verification/report_pages.json").read_text())
    assert len(pages) == 6
    assert len(list((DATA / "verification/pdf-render").glob("page-*.png"))) == 6
    docs = [
        ROOT / p
        for p in ["README.md", "docs/STATUS.md", "docs/basic_design/07-candidate-search.md"]
    ]
    for p in docs:
        for link in re.findall(r"\]\(([^)]+)\)", p.read_text()):
            if link.startswith(("http:", "https:", "#", "\\\\")):
                continue
            assert (p.parent / link.split("#")[0]).exists(), "Broken project documentation link"
    source_files = [
        ROOT / "plan/basic_design/candidate_search_20261115.json",
        ROOT / "scripts/basic_design/candidates.py",
        ROOT / "scripts/basic_design/candidate_report.py",
        ROOT / "scripts/basic_design/candidate_workbook.mjs",
        Path(__file__),
        ROOT / "scripts/basic_design/costs.py",
        ROOT / "scripts/basic_design/property.py",
        ROOT / "tests/basic_design/test_candidates.py",
        ROOT / "tests/basic_design/conftest.py",
        *docs,
    ]
    for p in source_files:
        if p.suffix == ".py":
            ast.parse(p.read_text())
    with zipfile.ZipFile(DATA / "reproduce-source.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in source_files:
            z.write(p, p.relative_to(ROOT))
        z.write(BASE / "cost-v1/calculations.json", "inputs/frozen_cost_basis.json")
    shutil.copy2(ROOT / "docs/basic_design/07-candidate-search.md", DATA / "candidate-search.md")
    result = dict(
        date="2026-11-15",
        candidates=4,
        holds=3,
        excluded=6,
        test_result="38 passed",
        pdf_pages=6,
        pdf_all_pages_cpu_rendered_and_visually_checked=True,
        xlsx_sheets=2,
        workbook_formula_errors=0,
        native_excel_app_recalculation=False,
        all_candidate_use_fit_reuse_and_extra_costs_unverified=True,
        broker_contact_or_application_sent=False,
        previous_model_files_unchanged=models,
        frozen_manifests_verified=frozen,
        same_fable_session_backup_matches=True,
        independent_numeric_review="No important calculation issues; unpriced extras and fee sensitivities retained",
    )
    (DATA / "verification/final_check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)
    )
    payload = [
        DATA / n
        for n in [
            "calculations.json",
            "sauna_candidates_20261115.pdf",
            "sauna_candidates_20261115.xlsx",
            "candidate-search.md",
            "workbook_verification.json",
            "verification/final_check.json",
            "verification/report_pages.json",
            "reproduce-source.zip",
        ]
    ]
    manifest = {
        "revision": "sauna-candidates-20261115",
        "files": [
            {"file": str(p.relative_to(DATA)), "bytes": p.stat().st_size, "sha256": sha(p)}
            for p in payload
        ],
    }
    (DATA / "delivery_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(DATA / "sauna_candidates_20261115.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in payload + [DATA / "delivery_manifest.json"]:
            z.write(p, p.relative_to(DATA))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
