"""Evidence-claim and semantic-retrieval regression tests."""

from __future__ import annotations

import pytest

from johnhull.scripts.paper_corpus.retrieval import rank_chunks, tokenize
from johnhull.scripts.paper_corpus.schema import ClaimRecord, SemanticChunkRecord

PAPER_ID = "2024-mof-jgbi-bei-guide"
SOURCE_SHA256 = "0" * 64
TEXT_SHA256 = "1" * 64


def test_verified_claim_requires_manual_page_review():
    claim = ClaimRecord(
        claim_id=f"{PAPER_ID}:claim:floor",
        paper_id=PAPER_ID,
        claim_type="payoff",
        statement="The redemption principal has a deflation floor.",
        page_numbers=(5,),
        evidence_block_ids=(f"{PAPER_ID}:p0005:block:0004",),
        source_pdf_sha256=SOURCE_SHA256,
        verification_status="verified",
        source_excerpts=("The source describes the principal floor.",),
        evidence_text_sha256=(TEXT_SHA256,),
    )

    with pytest.raises(ValueError, match="reviewer"):
        claim.validate()


def test_semantic_chunk_retains_source_relationships():
    chunk = SemanticChunkRecord(
        chunk_id=f"{PAPER_ID}:p0005:chunk:0001",
        paper_id=PAPER_ID,
        page_numbers=(5,),
        section_title="Principal floor",
        block_ids=(f"{PAPER_ID}:p0005:block:0004",),
        equation_ids=(),
        table_ids=(),
        claim_ids=(f"{PAPER_ID}:claim:floor",),
        text="The redemption principal has a deflation floor.",
        retrieval_text="JGBI 元本保証 デフレフロア option value",
        source_pdf_sha256=SOURCE_SHA256,
        content_sha256=TEXT_SHA256,
    )

    assert chunk.to_dict()["claim_ids"] == (f"{PAPER_ID}:claim:floor",)


def test_bm25_retrieval_supports_english_and_japanese_finance_terms():
    chunks = [
        {
            "chunk_id": "paper-a:p0001:chunk:0001",
            "paper_id": "paper-a",
            "page_numbers": [1],
            "claim_ids": ["paper-a:claim:sabr"],
            "equation_ids": [],
            "table_ids": [],
            "retrieval_text": "SABR forward measure stochastic volatility beta rho calibration",
        },
        {
            "chunk_id": "paper-b:p0005:chunk:0001",
            "paper_id": "paper-b",
            "page_numbers": [5],
            "claim_ids": ["paper-b:claim:floor"],
            "equation_ids": [],
            "table_ids": [],
            "retrieval_text": "JGBI 物価連動国債 元本保証 デフレフロア オプション価値",
        },
    ]

    assert "元本" in tokenize("元本保証")
    assert rank_chunks("SABR rho forward volatility", chunks)[0]["paper_id"] == "paper-a"
    assert rank_chunks("物価連動国債の元本保証", chunks)[0]["paper_id"] == "paper-b"
