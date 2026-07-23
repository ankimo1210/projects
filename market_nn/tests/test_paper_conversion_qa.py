from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parents[1]


def load_script(name: str):  # type: ignore[no-untyped-def]
    path = PROJECT_DIR / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AUDIT = load_script("audit_paper_conversion")
ROBUSTNESS = load_script("evaluate_paper_retrieval_robustness")
REPORT = load_script("build_paper_conversion_qa_report")


def test_conversion_audit_passes_full_corpus_quality_gates() -> None:
    visual_manifest = PROJECT_DIR / "manifests" / "paper_conversion_visual_checks.json"

    result = AUDIT.audit(PROJECT_DIR, visual_manifest)

    assert result["status"] == "pass"
    assert result["threshold_failures"] == []
    assert result["summary"]["paper_count"] == 22
    assert result["summary"]["page_count"] == 449
    assert result["summary"]["chunk_count"] == 1320
    assert result["summary"]["empty_converted_pages"] == 0
    assert result["threshold_actuals"]["oversized_chunks"] == 0
    assert result["threshold_actuals"]["missing_picture_files"] == 0
    assert result["threshold_actuals"]["missing_formula_crop_files"] == 0


def test_visual_checks_cover_every_page_below_point_eight() -> None:
    committed = json.loads(
        (PROJECT_DIR / "reports/paper_conversion_qa/conversion_results.json").read_text(
            encoding="utf-8"
        )
    )
    reviewed = {
        (check["paper_id"], check["page"]) for check in committed["visual_checks"]["checks"]
    }
    low_pages = {
        (page["paper_id"], page["page"])
        for page in committed["lowest_recall_pages"]
        if page["token_recall"] < 0.80
    }

    assert low_pages <= reviewed
    assert ("ref_tran_bin_2003.00598", 6) in reviewed


def test_retrieval_robustness_records_known_lexical_limit() -> None:
    result = ROBUSTNESS.evaluate_robustness(
        PROJECT_DIR,
        PROJECT_DIR / "manifests/paper_retrieval_gold.json",
        PROJECT_DIR / "manifests/paper_retrieval_robustness.json",
    )

    assert result["status"] == "fail"
    assert result["canonical"]["query_count"] == 66
    assert result["variants"]["strong_english_paraphrase"]["query_count"] == 66
    assert result["variants"]["japanese"]["query_count"] == 66
    assert result["canonical"]["metrics"]["overall"]["exact_evidence_recall_at_5"] == 0.9242
    assert (
        result["variants"]["strong_english_paraphrase"]["metrics"]["overall"]["page_recall_at_5"]
        == 0.7121
    )


def test_committed_conversion_report_artifact_is_current() -> None:
    report_dir = PROJECT_DIR / "reports" / "paper_conversion_qa"
    conversion = json.loads((report_dir / "conversion_results.json").read_text(encoding="utf-8"))
    robustness = json.loads((report_dir / "robustness_results.json").read_text(encoding="utf-8"))
    artifact = json.loads((report_dir / "artifact.json").read_text(encoding="utf-8"))

    assert REPORT.build_artifact(conversion, robustness) == artifact
