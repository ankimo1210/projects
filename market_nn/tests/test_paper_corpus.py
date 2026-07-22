from __future__ import annotations

import importlib.util
import json
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

VERIFY_SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "verify_arxiv_formulas.py"
VERIFY_SPEC = importlib.util.spec_from_file_location("verify_arxiv_formulas", VERIFY_SCRIPT_PATH)
assert VERIFY_SPEC and VERIFY_SPEC.loader
VERIFY_MODULE = importlib.util.module_from_spec(VERIFY_SPEC)
VERIFY_SPEC.loader.exec_module(VERIFY_MODULE)


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


def test_source_match_promotes_fallback_to_portable_latex() -> None:
    document = {
        "texts": [
            {
                "self_ref": "#/texts/1",
                "label": "formula",
                "orig": "PE pos 2i",
                "text": "",
                "prov": [{"page_no": 4, "bbox": {"l": 1, "t": 2, "r": 3, "b": 1}}],
            }
        ]
    }
    source_matches = {
        "sample:formula:0001": {
            "base_status": "text_layer_fallback",
            "document_ref": "#/texts/1",
            "source_pdf": "sources/papers/sample.pdf",
            "arxiv_version": "1706.03762v7",
            "source_file": "model_architecture.tex",
            "source_line": 148,
            "source_latex": r"PE_{(pos,2i)}=sin(pos/10000^{2i/\dmodel}) \\",
            "environment": "align*",
            "score": 1.0,
        }
    }

    records = FORMULA_MODULE.build_formula_records(
        "sample",
        document,
        source_pdf="sources/papers/sample.pdf",
        overrides={},
        source_matches=source_matches,
    )

    assert records[0]["status"] == "verified_source"
    assert records[0]["verification_methods"] == ["arxiv_tex"]
    assert r"\dmodel" not in records[0]["latex"]
    assert records[0]["latex"].startswith(r"\begin{aligned}")


def test_source_match_expands_author_macros_to_portable_latex() -> None:
    match = {
        "source_latex": (
            r"\small \mathcal{L}(\myvec{W}) + \vola + \upnu "
            r"+ \mathbf{x} \varoslash \bm{\sigma}"
        ),
        "environment": "equation",
    }

    latex = FORMULA_MODULE.portable_source_latex(match)

    assert r"\small" not in latex
    assert r"\myvec" not in latex
    assert r"\vola" not in latex
    assert r"\upnu" not in latex
    assert r"\varoslash" not in latex
    assert r"\mathbf{W}" in latex
    assert r"\oslash" in latex
    assert r"\boldsymbol{\sigma}" in latex


def test_semantic_reviews_replace_only_high_confidence_formulas() -> None:
    document = {
        "texts": [
            {
                "self_ref": f"#/texts/{index}",
                "label": "formula",
                "orig": original,
                "text": decoded,
                "prov": [{"page_no": 1, "bbox": {"l": 1, "t": 2, "r": 3, "b": 1}}],
            }
            for index, original, decoded in (
                (1, "x equals one", "x = l"),
                (2, "(11)", ""),
                (3, "ambiguous covariance", "C o v ( X )"),
            )
        ]
    }
    common = {
        "source_pdf": "sources/papers/sample.pdf",
        "source_page": 1,
        "evidence": ["Context and dimensions were reviewed."],
        "assumptions": [],
        "alternatives": [],
    }
    reviews = {
        "sample:formula:0001": {
            **common,
            "review_status": "high_confidence",
            "action": "reconstruct",
            "confidence": 0.99,
            "base_status": "decoded_unverified",
            "document_ref": "#/texts/1",
            "latex": "x = 1",
            "note": "Reconstructed from context.",
        },
        "sample:formula:0002": {
            **common,
            "review_status": "not_formula",
            "action": "exclude_spurious",
            "confidence": 1.0,
            "base_status": "text_layer_fallback",
            "document_ref": "#/texts/2",
            "note": "Equation-number artifact.",
        },
        "sample:formula:0003": {
            **common,
            "review_status": "ambiguous",
            "action": "flag_only",
            "confidence": 0.4,
            "base_status": "decoded_unverified",
            "document_ref": "#/texts/3",
            "note": "Insufficient assumptions to reconstruct.",
        },
    }

    records = FORMULA_MODULE.build_formula_records(
        "sample",
        document,
        source_pdf="sources/papers/sample.pdf",
        overrides={},
        semantic_reviews=reviews,
    )

    assert records[0]["status"] == "semantic_high_confidence"
    assert records[0]["latex"] == "x = 1"
    assert records[1]["status"] == "semantic_not_formula"
    assert records[1]["latex"] is None
    assert records[2]["status"] == "decoded_unverified"
    assert records[2]["latex"] == "C o v ( X )"
    assert all("semantic_context_review" in record["verification_methods"] for record in records)


def test_semantic_review_manifest_is_explicit_about_uncertainty() -> None:
    project_root = Path(__file__).parents[1]
    manifest = json.loads(
        (project_root / "manifests" / "formula_semantic_reviews.json").read_text(encoding="utf-8")
    )
    reviews = manifest["reviews"]

    assert len(reviews) == 15
    assert sum(review["review_status"] == "high_confidence" for review in reviews.values()) == 12
    assert sum(review["review_status"] == "not_formula" for review in reviews.values()) == 2
    assert sum(review["review_status"] == "ambiguous" for review in reviews.values()) == 1
    assert all(
        review["confidence"] >= manifest["policy"]["replacement_threshold"]
        for review in reviews.values()
        if review["review_status"] == "high_confidence"
    )
    assert all(
        "paper_as_printed_latex" in review
        for review in reviews.values()
        if review["action"] == "correct_suspected_paper_typo"
    )

    quality = json.loads((project_root / "corpus" / "papers" / "_index.json").read_text())[
        "formula_quality"
    ]
    assert quality["semantic_reviewed_total"] == 15
    assert quality["semantic_high_confidence"] == 12
    assert quality["semantic_not_formula"] == 2
    assert quality["semantic_ambiguous"] == 1


def test_arxiv_match_manifest_contains_only_reviewed_source_matches() -> None:
    manifest_path = Path(__file__).parents[1] / "manifests" / "formula_source_matches.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["threshold"] == 0.9
    assert manifest["summary"] == {
        "source_verified": 224,
        "manual_confirmed": 42,
        "decoded_corrected": 99,
        "fallback_recovered": 83,
        "visual_crop_checked": 119,
        "rejected_after_visual_review": 15,
    }
    assert len(manifest["rejected_matches"]) == 15
    assert not (set(manifest["matches"]) & set(manifest["rejected_matches"]))
    assert all(
        match["score"] >= 0.9 or match["acceptance"] == "visual_crop_review"
        for match in manifest["matches"].values()
    )
    assert all(
        match["visual_crop_checked"]
        for match in manifest["matches"].values()
        if match["acceptance"] == "visual_crop_review"
    )
    assert all(
        match["visual_crop_checked"]
        for match in manifest["matches"].values()
        if match["base_status"] == "text_layer_fallback"
    )

    corpus_root = Path(__file__).parents[1] / "corpus" / "papers"
    corpus_formulas = {
        formula["formula_id"]: formula
        for formulas_path in corpus_root.glob("*/formulas.jsonl")
        for formula in map(json.loads, formulas_path.read_text(encoding="utf-8").splitlines())
    }
    assert set(manifest["matches"]) <= corpus_formulas.keys()
    assert all(
        corpus_formulas[formula_id]["source_verification"] == match
        for formula_id, match in manifest["matches"].items()
    )


def test_arxiv_source_manifest_pins_exact_versions_and_hashes() -> None:
    manifest_path = Path(__file__).parents[1] / "manifests" / "arxiv_formula_sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    papers = manifest["papers"]

    assert len(papers) == 19
    assert sum(paper["source_kind"] == "tex" for paper in papers.values()) == 17
    assert sum(paper["source_kind"] == "pdf_wrapper" for paper in papers.values()) == 2
    assert all("v" in paper["arxiv_version"] for paper in papers.values())
    assert all(
        len(paper["archive_sha256"]) == 64
        and set(paper["archive_sha256"]) <= set("0123456789abcdef")
        for paper in papers.values()
    )


def test_arxiv_math_normalization_matches_pdf_text() -> None:
    source = {"source_latex": r"\mathrm{Attention}(Q,K,V)=\mathrm{softmax}(QK^T/\sqrt{d_k})V"}
    formula = {
        "latex": None,
        "docling_latex": None,
        "pdf_text": "Attention Q K V softmax QK T √ d k V",
    }

    score, matched_on = VERIFY_MODULE.formula_similarity(formula, source)

    assert matched_on == "pdf_text"
    assert score >= 0.9


def test_arxiv_alignment_ignores_previous_source_overlay() -> None:
    restored = VERIFY_MODULE.formula_alignment_input(
        {
            "latex": r"x = 1",
            "docling_latex": None,
            "pdf_text": "x equals one",
            "source_verification": {"base_status": "text_layer_fallback"},
        }
    )

    assert restored["latex"] is None
    assert restored["pdf_text"] == "x equals one"
