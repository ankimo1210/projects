from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "build_paper_corpus.py"
SPEC = importlib.util.spec_from_file_location("build_paper_corpus", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

FORMULA_SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "repair_paper_formulas.py"
FORMULA_SPEC = importlib.util.spec_from_file_location("repair_paper_formulas", FORMULA_SCRIPT_PATH)
assert FORMULA_SPEC and FORMULA_SPEC.loader
FORMULA_MODULE = importlib.util.module_from_spec(FORMULA_SPEC)
FORMULA_SPEC.loader.exec_module(FORMULA_MODULE)


def test_normalize_document_artifact_paths() -> None:
    paper_id = "sample-paper"
    document = {
        "pictures": [
            {"uri": ("/tmp/paper-corpus/docling/sample-paper_artifacts/image_000001_deadbeef.png")}
        ],
        "pages": {"1": {"image": {"uri": "sample-paper_artifacts/page_000001_deadbeef.png"}}},
        "source": {"filename": "sample-paper.pdf"},
    }

    normalized = MODULE.normalize_document_artifact_paths(document, paper_id)

    assert normalized["pictures"][0]["uri"] == "images/image_000001_deadbeef.png"
    assert normalized["pages"]["1"]["image"]["uri"] == "images/page_000001_deadbeef.png"
    assert normalized["source"]["filename"] == "sample-paper.pdf"


def test_formula_overlay_distinguishes_verified_and_fallback_content() -> None:
    document = {
        "texts": [
            {
                "self_ref": "#/texts/1",
                "label": "formula",
                "orig": "x = 1",
                "text": "x = l",
                "prov": [{"page_no": 2, "bbox": {"l": 1, "t": 2, "r": 3, "b": 1}}],
            },
            {
                "self_ref": "#/texts/2",
                "label": "formula",
                "orig": "y = 2",
                "text": "",
                "prov": [{"page_no": 3, "bbox": {"l": 1, "t": 2, "r": 3, "b": 1}}],
            },
        ]
    }
    overrides = {
        "sample": {
            "#/texts/1": {
                "latex": "x = 1",
                "note": "Checked against the PDF.",
            }
        }
    }

    records = FORMULA_MODULE.build_formula_records(
        "sample", document, source_pdf="sources/papers/sample.pdf", overrides=overrides
    )
    repaired = FORMULA_MODULE.replace_formula_blocks(
        "Before\n$$x = l$$\n<!-- formula-not-decoded -->\nAfter", records
    )

    assert [record["status"] for record in records] == [
        "verified_manual",
        "text_layer_fallback",
    ]
    assert records[0]["docling_latex"] == "x = l"
    assert records[1]["docling_latex"] is None
    assert "$$\nx = 1\n$$" in repaired
    assert "PDF text layer: y = 2" in repaired
    assert "formula-not-decoded" not in repaired
    assert repaired.count("<!-- formula-start") == 2
    assert FORMULA_MODULE.replace_formula_blocks(repaired, records) == repaired


def test_formula_override_manifest_has_expected_reviewed_set() -> None:
    overrides = FORMULA_MODULE.load_overrides()

    assert sum(len(paper) for paper in overrides.values()) == 49
    assert len(overrides["deeplob_1808.03668v6"]) == 7
    assert len(overrides["fi2010_1705.03233v5"]) == 17
