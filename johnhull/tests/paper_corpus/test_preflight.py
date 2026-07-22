"""Tests for deterministic PDF preflight normalization."""

from __future__ import annotations

from pathlib import Path

import pytest

from johnhull.scripts.paper_corpus.preflight import parse_qpdf_result, profile_pdf_pages
from johnhull.scripts.paper_corpus.schema import (
    BlockRecord,
    BoundingBox,
    ClaimRecord,
    EquationRecord,
    Provenance,
    TableCell,
    TableRecord,
    stable_record_id,
)

PAPER_ID = "1990-hull-white-interest-rate-derivative-securities"
SOURCE_HASH = "a" * 64


def provenance():
    return Provenance(SOURCE_HASH, "fixture", "1.0")


@pytest.mark.parametrize(
    ("return_code", "output", "status", "warnings", "errors"),
    [
        (0, "No syntax or stream encoding errors found", "clean", 0, 0),
        (3, "WARNING: damaged hint table\noperation succeeded", "warning", 1, 0),
        (2, "WARNING: recovered xref\nERROR: page 5 content stream", "error", 1, 1),
    ],
)
def test_parse_qpdf_result(return_code, output, status, warnings, errors):
    result = parse_qpdf_result(return_code, output)

    assert result.status == status
    assert result.warning_count == warnings
    assert result.error_count == errors


def test_bounding_box_rejects_inverted_and_non_finite_coordinates():
    with pytest.raises(ValueError, match="non-empty"):
        BoundingBox(4, 2, 1, 8).validate()
    with pytest.raises(ValueError, match="finite"):
        BoundingBox(0, 0, float("nan"), 8).validate()


def test_bounding_box_accepts_positive_pdf_rectangle():
    BoundingBox(1.5, 2.5, 40.0, 80.0).validate()


def test_stable_record_id_and_block_contract():
    block = BlockRecord(
        block_id=stable_record_id(PAPER_ID, 6, "block", 1),
        paper_id=PAPER_ID,
        page_number=6,
        block_type="paragraph",
        bbox=BoundingBox(1, 2, 40, 80),
        reading_order=0,
        raw_text="Term structure",
        normalized_text="Term structure",
        verification_status="auto",
        provenance=provenance(),
        confidence=0.9,
    )

    assert block.to_dict()["bbox"] == [1, 2, 40, 80]


def test_verified_equation_requires_latex_but_keeps_source_crop():
    equation = EquationRecord(
        equation_id=stable_record_id(PAPER_ID, 6, "equation", 1),
        paper_id=PAPER_ID,
        page_number=6,
        bbox=BoundingBox(1, 2, 40, 80),
        source_asset="assets/equations/eq-001.png",
        latex=None,
        equation_number="9",
        verification_status="verified",
        provenance=provenance(),
    )

    with pytest.raises(ValueError, match="require LaTeX"):
        equation.validate()


def test_verified_table_rejects_duplicate_cells_and_missing_exports():
    common = dict(
        table_id=stable_record_id(PAPER_ID, 17, "table", 1),
        paper_id=PAPER_ID,
        page_number=17,
        bbox=BoundingBox(1, 2, 400, 500),
        source_asset="assets/tables/table-001.png",
        caption="Option values",
        verification_status="verified",
        provenance=provenance(),
    )
    duplicate = TableRecord(
        cells=(TableCell(0, 0, "0.35", "0.35", numeric_value=0.35),) * 2,
        csv_path="tables/table-001.csv",
        html_path="tables/table-001.html",
        **common,
    )
    missing_exports = TableRecord(
        cells=(TableCell(0, 0, "0.35", "0.35", numeric_value=0.35),),
        **common,
    )

    with pytest.raises(ValueError, match="duplicate"):
        duplicate.validate()
    with pytest.raises(ValueError, match="CSV and HTML"):
        missing_exports.validate()


def test_claims_require_evidence_and_numeric_source():
    unsupported = ClaimRecord(
        claim_id=f"{PAPER_ID}:claim:0001",
        paper_id=PAPER_ID,
        claim_type="empirical_result",
        statement="The option value is 0.35.",
        page_numbers=(17,),
        evidence_block_ids=(stable_record_id(PAPER_ID, 17, "block", 1),),
        verification_status="auto",
    )

    with pytest.raises(ValueError, match="numeric claims"):
        unsupported.validate()

    supported = ClaimRecord(
        claim_id=f"{PAPER_ID}:claim:0002",
        paper_id=PAPER_ID,
        claim_type="empirical_result",
        statement="The option value is 0.35.",
        page_numbers=(17,),
        evidence_block_ids=(stable_record_id(PAPER_ID, 17, "block", 1),),
        table_ids=(stable_record_id(PAPER_ID, 17, "table", 1),),
        verification_status="verified",
    )
    supported.validate()


def test_hull_white_page_profile_detects_formula_image_density():
    pdf_path = (
        Path(__file__).resolve().parents[2]
        / "references/papers/1990-hull-white-interest-rate-derivative-securities.pdf"
    )

    profiles = profile_pdf_pages(pdf_path)

    assert len(profiles) == 20
    assert profiles[5].page_number == 6
    assert profiles[5].route == "hybrid"
    assert profiles[5].math_dense
